"""非门禁测试 · 钉死 `capture` 本身在读什么。

门禁那两条 L1（`test_snapshot_diff_structured.py`）在**零条目**快照上成立，
信息量很低：两个空快照当然相等。本文件用**非空夹具目录**把 `capture` 的真实读取路径
压出来——它必须真的按 `<root>/<scope>/*.json` 去读，而不是被写死成「永远返回空」。

夹具形状与 `agenerp.snapshot.OfflineSnapshotSource` 的文档一致，
载荷会先过 `agenerp.pack.normalize`（剥易变字段、稳定排序）。
"""

import json

import pytest

from agenerp.site import ADMIN_PASSWORD_ENV, API_KEY_ENV, API_SECRET_ENV, SiteError
from agenerp.snapshot import (
    OFFLINE_ROOT_ENV,
    SITE_ENV,
    OfflineSnapshotSource,
    SiteSnapshotSource,
    capture,
    diff,
    resolve_source,
)


def _write_doctype(root, scope, doctype, fields):
    scope_dir = root / scope
    scope_dir.mkdir(parents=True, exist_ok=True)
    payload = {"doctype": doctype, "custom_fields": fields}
    (scope_dir / f"{doctype}.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def offline_root(tmp_path, monkeypatch):
    """把离线来源指向一个临时夹具根，并保证测试不受本机站点配置影响。"""
    monkeypatch.delenv(SITE_ENV, raising=False)
    monkeypatch.setenv(OFFLINE_ROOT_ENV, str(tmp_path))
    return tmp_path


def test_capture_reads_fixture_entries(offline_root):
    """夹具里有几个字段就该读出几个。为零 = `capture` 根本没在读，只是返回常量。"""
    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data"},
        {"fieldname": "shelf_life_days", "fieldtype": "Int"},
    ])
    _write_doctype(offline_root, "doctypes", "Customer", [
        {"fieldname": "credit_tier", "fieldtype": "Select"},
    ])

    snap = capture(scope="doctypes")

    assert len(snap) == 3, f"夹具有 3 个字段，快照读出 {len(snap)} 个"
    assert {(e.doctype, e.fieldname) for e in snap.entries} == {
        ("Item", "brand_code"),
        ("Item", "shelf_life_days"),
        ("Customer", "credit_tier"),
    }
    brand = next(e for e in snap.entries if e.fieldname == "brand_code")
    assert brand.attributes["fieldtype"] == "Data", "条目属性没带出来，diff 就算不出 changed"


def test_capture_twice_on_unchanged_fixture_is_equal(offline_root):
    """同一夹具连读两次必须相等。不相等 = 快照混进了采集时刻之类的易变量（Spike 06 的坑）。"""
    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data"},
    ])

    assert capture(scope="doctypes") == capture(scope="doctypes")


def test_capture_reflects_fixture_change(offline_root):
    """改了夹具就该读出不同的快照。相等 = 它没在读文件，前一条测试的「相等」是假的。"""
    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data"},
    ])
    before = capture(scope="doctypes")

    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data"},
        {"fieldname": "shelf_life_days", "fieldtype": "Int"},
    ])
    after = capture(scope="doctypes")

    assert before != after
    assert len(after) == len(before) + 1


def test_capture_strips_volatile_fields(offline_root):
    """易变字段必须被剥掉，否则「什么都没改重新导出」也会 diff 出差异。"""
    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data", "modified": "2026-08-20 10:00:00"},
    ])
    before = capture(scope="doctypes")

    _write_doctype(offline_root, "doctypes", "Item", [
        {"fieldname": "brand_code", "fieldtype": "Data", "modified": "2026-08-21 23:59:59"},
    ])
    after = capture(scope="doctypes")

    assert before == after, "只有 modified 变了，快照不该跟着变"
    assert "modified" not in before.entries[0].attributes


def test_capture_on_missing_location_is_empty_not_error(offline_root):
    """位置不存在 = 零条目，**不是异常**。抛异常会让两条 L1 门禁永远红在环境而非实现。"""
    snap = capture(scope="doctypes")

    assert len(snap) == 0
    assert snap.scope == "doctypes"


def test_capture_carries_its_scope(offline_root):
    """快照必须记住自己是哪个 scope 的，否则 `diff` 无从拒绝跨 scope 比较。"""
    _write_doctype(offline_root, "doctypes", "Item", [{"fieldname": "brand_code"}])
    _write_doctype(offline_root, "permissions", "Item", [
        {"fieldname": "role_profile"},
        {"fieldname": "share_policy"},
    ])

    doctypes = capture(scope="doctypes")
    permissions = capture(scope="permissions")

    assert doctypes.scope == "doctypes"
    assert permissions.scope == "permissions"
    assert len(doctypes) == 1 and len(permissions) == 2


def test_capture_accepts_an_explicit_source(tmp_path, monkeypatch):
    """显式来源优先于环境——工作项 4 接站点来源时靠的就是这条接缝。"""
    monkeypatch.delenv(SITE_ENV, raising=False)
    monkeypatch.delenv(OFFLINE_ROOT_ENV, raising=False)
    _write_doctype(tmp_path, "doctypes", "Item", [{"fieldname": "brand_code"}])

    snap = capture(scope="doctypes", source=OfflineSnapshotSource(tmp_path))

    assert len(snap) == 1
    assert snap.source == f"offline:{tmp_path}"


def test_resolve_source_prefers_site_when_configured(monkeypatch):
    """有站点配置就该选站点来源。缺凭据时它抛 `SiteError` 并指名变量，**不返回空快照**。"""
    monkeypatch.setenv(SITE_ENV, "gate.invalid")
    for name in (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV):
        monkeypatch.delenv(name, raising=False)

    resolved = resolve_source()

    assert isinstance(resolved, SiteSnapshotSource)
    with pytest.raises(SiteError) as excinfo:
        resolved.read("doctypes")
    assert ADMIN_PASSWORD_ENV in str(excinfo.value)


def test_snapshot_source_identity_does_not_affect_equality(tmp_path, monkeypatch):
    """来源身份只是溯源信息。让它参与相等性，两个来源读出同样内容也会被判成不同。"""
    monkeypatch.delenv(SITE_ENV, raising=False)
    other = tmp_path / "mirror"
    for root in (tmp_path / "primary", other):
        _write_doctype(root, "doctypes", "Item", [{"fieldname": "brand_code"}])

    a = capture(scope="doctypes", source=OfflineSnapshotSource(tmp_path / "primary"))
    b = capture(scope="doctypes", source=OfflineSnapshotSource(other))

    assert a.source != b.source
    assert a == b


# ---------------------------------------------------------------------------
# 站点来源（`SiteSnapshotSource.read`）—— 全部喂假客户端，不连真站点。
# 假客户端只答「站点会怎么答」，投影与排序是被测的那一半。
# ---------------------------------------------------------------------------
class FakeSiteClient:
    """按预设行答复的假站点客户端。记下被问过哪些 DocType。"""

    def __init__(self, rows, error=None):
        self.rows = rows
        self.error = error
        self.asked = []

    def list_resource(self, doctype, fields=("*",)):
        self.asked.append(doctype)
        if self.error is not None:
            raise self.error
        return [dict(row) for row in self.rows]


def _site(rows, error=None):
    return SiteSnapshotSource("frontend", FakeSiteClient(rows, error))


def test_site_read_projects_dt_into_doctype():
    """Custom Field 的归属 DocType 存在 `dt` 列，**不叫 `doctype`**。这一格错了整份快照就错了。"""
    snap = capture(scope="doctypes", source=_site([
        {"dt": "Item", "fieldname": "brand_code", "fieldtype": "Data"},
    ]))

    assert [(e.doctype, e.fieldname) for e in snap.entries] == [("Item", "brand_code")]
    assert snap.entries[0].attributes["fieldtype"] == "Data"
    assert "dt" not in snap.entries[0].attributes, "身份键不该同时留在属性里"
    assert snap.source == "site:frontend"


def test_site_read_twice_is_identical():
    """同一站点连读两次必须逐条相同，否则「未改动 → diff 为空」在活站点上不成立。"""
    rows = [
        {"dt": "Item", "fieldname": "brand_code", "fieldtype": "Data"},
        {"dt": "Customer", "fieldname": "credit_tier", "fieldtype": "Select"},
    ]
    source = _site(rows)

    assert capture(scope="doctypes", source=source) == capture(scope="doctypes", source=source)


def test_site_read_strips_volatile_columns():
    """站点行带 modified / creation / owner，剥不干净则同站点两次快照必然 diff 出差异。"""
    base = {"dt": "Item", "fieldname": "brand_code", "fieldtype": "Data"}
    before = capture(scope="doctypes", source=_site([
        {**base, "modified": "2026-08-20 10:00:00", "creation": "2026-08-01 09:00:00",
         "owner": "Administrator", "modified_by": "Administrator"},
    ]))
    after = capture(scope="doctypes", source=_site([
        {**base, "modified": "2026-08-21 23:59:59", "creation": "2026-08-01 09:00:00",
         "owner": "Administrator", "modified_by": "Administrator"},
    ]))

    assert before == after, f"只有 modified 变了，快照不该跟着变：{diff(before, after).summary()}"
    attributes = before.entries[0].attributes
    for volatile in ("modified", "creation", "owner", "modified_by"):
        assert volatile not in attributes, f"{volatile} 没被剥掉"


def test_site_read_keeps_same_fieldname_on_two_doctypes_apart():
    """身份是 `(doctype, fieldname)` 二元组：只按字段名去重会把两条混成一条（§11.5）。"""
    snap = capture(scope="doctypes", source=_site([
        {"dt": "Item", "fieldname": "note", "fieldtype": "Data"},
        {"dt": "Customer", "fieldname": "note", "fieldtype": "Text"},
    ]))

    assert len(snap) == 2
    assert {(e.doctype, e.fieldname) for e in snap.entries} == {
        ("Item", "note"), ("Customer", "note"),
    }


def test_site_read_is_sorted_by_key():
    """按 `key` 排序：站点返回次序不稳定时，未排序会让两次快照无谓地 diff。"""
    snap = capture(scope="doctypes", source=_site([
        {"dt": "Item", "fieldname": "zeta"},
        {"dt": "Customer", "fieldname": "alpha"},
        {"dt": "Item", "fieldname": "alpha"},
    ]))

    assert [e.key for e in snap.entries] == sorted(e.key for e in snap.entries)


def test_site_read_returns_every_row_even_past_the_default_page_length():
    """假客户端喂 25 条（超过 Frappe 默认页长 20）→ 必须原样拿到 25 条。

    分页截断与「站点真的只有这么多」在快照层长得一模一样，是一条最难发现的假绿。
    关分页的**请求参数**由 `tests/unit/test_site_client.py` 断言，live 层的条目数在 Phase 3 实测。
    """
    rows = [{"dt": "Item", "fieldname": f"probe_{i:02d}"} for i in range(25)]

    snap = capture(scope="doctypes", source=_site(rows))

    assert len(snap) == 25


def test_site_read_asks_for_custom_field():
    """站点来源问的是 Custom Field 这张表；问错表会静默读回一份完全无关的快照。"""
    source = _site([])

    capture(scope="doctypes", source=source)

    assert source.client.asked == ["Custom Field"]


def test_site_read_rejects_unknown_scope():
    """未知 scope 显式抛，**不返回空元组**：返回空会让拼错的 scope 和「没有定制」长得一样。"""
    with pytest.raises(ValueError) as excinfo:
        _site([]).read("permissions")

    assert "permissions" in str(excinfo.value)


def test_site_read_rejects_a_row_without_identity():
    """缺 `dt` / `fieldname` 的行定不了身份，抛；跳过它会静默丢条目。"""
    with pytest.raises(ValueError) as excinfo:
        _site([{"fieldname": "brand_code"}]).read("doctypes")

    assert "dt" in str(excinfo.value)


def test_capture_does_not_swallow_site_errors():
    """站点答不上话时 `capture` 不吞异常。吞掉 = 站点宕机被读成「站点上什么都没有」。"""
    source = _site([], error=SiteError("connection refused"))

    with pytest.raises(SiteError):
        capture(scope="doctypes", source=source)
