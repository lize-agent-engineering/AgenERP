"""非门禁测试 · 钉死 `capture` 本身在读什么。

门禁那两条 L1（`test_snapshot_diff_structured.py`）在**零条目**快照上成立，
信息量很低：两个空快照当然相等。本文件用**非空夹具目录**把 `capture` 的真实读取路径
压出来——它必须真的按 `<root>/<scope>/*.json` 去读，而不是被写死成「永远返回空」。

夹具形状与 `agenerp.snapshot.OfflineSnapshotSource` 的文档一致，
载荷会先过 `agenerp.pack.normalize`（剥易变字段、稳定排序）。
"""

import json

import pytest

from agenerp.snapshot import (
    OFFLINE_ROOT_ENV,
    SITE_ENV,
    OfflineSnapshotSource,
    SiteSnapshotSource,
    capture,
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
    """有站点配置就该选站点来源（其 `read` 仍是工作项 4 的 NotImplementedError）。"""
    monkeypatch.setenv(SITE_ENV, "gate.invalid")

    resolved = resolve_source()

    assert isinstance(resolved, SiteSnapshotSource)
    with pytest.raises(NotImplementedError):
        resolved.read("doctypes")


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
