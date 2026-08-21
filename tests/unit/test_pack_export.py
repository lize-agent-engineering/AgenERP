"""非门禁测试 · 钉死定制包**导出**的往返不变量（`agenerp.pack.export_customizations`）。

**不连真站点**：站点来源收一个可注入的假客户端（`SiteSnapshotSource(site, client=...)`），
所以本文件在 `GATE_VERIFY` 的默认环境里就能跑，不依赖 docker、不依赖端口。

五条往返不变量各有一条用例（编号与 plan
`docs/plans/p0-foundation/2026-08-21-1922-2-export-customizations-live.md` 一致）：

1. 双向相等：`read_pack(into)` 里属于该 DocType 的条目 == `capture` 里同一子集，**属性逐键相等**
2. 零定制也必须落盘（`git diff` 看不见未跟踪文件，基线不落盘 → 门禁恒红）
3. 幂等：站点未变时重复导出，文件**逐字节**相同
4. 产物是**严格** JSON（门禁 fixture 用 `json.loads` 读它）
5. scope 完整性：站点上该 DocType 的全部 Custom Field 都进包，且关分页口径没被绕开

另有三条：同目录别的 DocType 文件逐字节未变、站点抛错时**不产生任何文件**、
以及复刻门禁那条逐行断言的**排版回归**。

排版回归**不 import `tests/gates/` 的任何东西**（红线 1 + 判据独立性）：断言在本文件里自带，
差分用 `difflib`（`n=0`）而不是起 git —— 判定的是「插入一个条目会改动哪些行」，
两者对纯插入给出同一组新增行，而 difflib 不需要在 tmp 目录里配 git 身份。
"""

import difflib
import json

import pytest

from agenerp import snapshot as snapshot_mod
from agenerp.apply import PACK_SCOPE, read_pack
from agenerp.pack import (
    PACK_DOCTYPE_KEY,
    PACK_ENTRIES_KEY,
    export_customizations,
    render_doctype_file,
)
from agenerp.site import (
    PAGE_LENGTH_PARAM,
    UNLIMITED_PAGE_LENGTH,
    SiteClient,
    SiteError,
    SiteResponse,
)
from agenerp.snapshot import SITE_ENV, SiteSnapshotSource, capture

PROBE_FIELD = "agenerp_gate_roundtrip"


def _site_row(doctype, fieldname, **extra):
    """一行站点 Custom Field。刻意带上易变键——它们必须在两侧同时被 `normalize` 剥掉。"""
    row = {
        "dt": doctype,
        "fieldname": fieldname,
        "fieldtype": "Data",
        "label": fieldname.replace("_", " ").title(),
        "insert_after": "item_name",
        "reqd": 0,
        "hidden": 0,
        "modified": "2026-08-21 09:00:00.000000",
        "modified_by": "Administrator",
        "creation": "2026-08-21 08:00:00.000000",
        "owner": "Administrator",
    }
    row.update(extra)
    return row


class FakeSiteClient:
    """`SiteClient` 的只读替身：只答 `list_resource`，并记下被问过哪些 DocType。"""

    def __init__(self, rows, error=None):
        self.rows = list(rows)
        self.error = error
        self.asked = []

    def list_resource(self, doctype, fields=("*",)):
        self.asked.append(doctype)
        if self.error is not None:
            raise self.error
        return [dict(row) for row in self.rows]


def _source(rows, error=None):
    return SiteSnapshotSource("gate.invalid", client=FakeSiteClient(rows, error))


ROWS = [
    _site_row("Item", "brand_code"),
    _site_row("Item", "shelf_life_days", fieldtype="Int"),
    _site_row("Customer", "credit_tier", fieldtype="Select", insert_after="customer_name"),
]


@pytest.fixture(autouse=True)
def no_site_env(monkeypatch):
    """默认清掉站点配置：用例要么显式注入 source，要么正是在测「没配置就该抛」。"""
    monkeypatch.delenv(SITE_ENV, raising=False)


def _exported_file(into, doctype="Item"):
    return into / PACK_SCOPE / f"{doctype}.json"


# --------------------------------------------------------------------------
# 往返不变量 1 —— 双向相等（不是「⊇」）
# --------------------------------------------------------------------------
def test_roundtrip_entries_equal_capture_subset(tmp_path):
    """导出再读回，必须与 `capture` 的同一 DocType 子集**集合相等且属性逐键相等**。

    少一条 → 差集 apply 会把它算成 `deletes`（误删）；属性投影不同源 → 全部算成 `updates`。
    """
    source = _source(ROWS)
    export_customizations(doctype="Item", into=str(tmp_path), source=source)

    from_pack = {e.key: e.attributes for e in read_pack(str(tmp_path)).entries}
    from_site = {
        e.key: e.attributes
        for e in capture(PACK_SCOPE, source=_source(ROWS)).entries
        if e.doctype == "Item"
    }

    assert from_pack.keys() == from_site.keys(), (
        f"包与站点的条目集合不等：包 {sorted(from_pack)} vs 站点 {sorted(from_site)}"
    )
    for key, attributes in from_site.items():
        assert from_pack[key] == attributes, f"{key} 的属性两侧不等，apply 会把它算成 changed"
    assert from_pack, "夹具里 Item 有两个定制字段，读回却是空的"


def test_roundtrip_strips_volatile_keys_on_both_sides(tmp_path):
    """易变键（modified / creation / owner）不得进包——否则「什么都没改」也会 diff 出差异。"""
    export_customizations(doctype="Item", into=str(tmp_path), source=_source(ROWS))

    text = _exported_file(tmp_path).read_text(encoding="utf-8")
    for volatile in ("modified", "creation", "owner"):
        assert volatile not in text, f"包文件里夹带了易变键 {volatile}：{text[:400]}"


# --------------------------------------------------------------------------
# 往返不变量 2 —— 零定制也必须落盘
# --------------------------------------------------------------------------
def test_zero_customizations_still_writes_file(tmp_path):
    """站点上该 DocType 一条定制都没有时，照样写出空数组文件。

    门禁先 export 再 commit，随后走 `git diff HEAD`——**它看不见未跟踪文件**。
    基线不落盘的话，加字段后新文件是 untracked，`assert changed` 直接红。
    """
    export_customizations(doctype="Item", into=str(tmp_path), source=_source([]))

    target = _exported_file(tmp_path)
    assert target.is_file(), "站点答出零条目时也必须落盘，否则门禁的 baseline 是空的"
    assert json.loads(target.read_text(encoding="utf-8")) == {
        PACK_DOCTYPE_KEY: "Item",
        PACK_ENTRIES_KEY: [],
    }


def test_empty_array_does_not_collapse_to_a_single_line(tmp_path):
    """空数组不能写成 `"custom_fields": []`：从空变非空会改到那一行，而它不含新字段名。

    判据不是「`[` 长什么样」，而是**那一行在从空变非空时一个字节都不变**——所以直接比它。
    """
    export_customizations(doctype="Item", into=str(tmp_path), source=_source([]))
    empty_lines = _exported_file(tmp_path).read_text(encoding="utf-8").splitlines()

    export_customizations(
        doctype="Item", into=str(tmp_path), source=_source([_site_row("Item", PROBE_FIELD)])
    )
    filled_lines = _exported_file(tmp_path).read_text(encoding="utf-8").splitlines()

    opener = f'  "{PACK_ENTRIES_KEY}": ['
    assert opener in empty_lines, empty_lines
    assert opener in filled_lines, filled_lines
    assert empty_lines[-2].strip() == "]", empty_lines


# --------------------------------------------------------------------------
# 往返不变量 3 —— 幂等
# --------------------------------------------------------------------------
def test_repeated_export_is_byte_identical(tmp_path):
    """站点未变（哪怕行序被打乱）时重复导出，文件逐字节相同——否则 `git diff` 永远不干净。"""
    export_customizations(doctype="Item", into=str(tmp_path), source=_source(ROWS))
    first = _exported_file(tmp_path).read_bytes()

    export_customizations(doctype="Item", into=str(tmp_path), source=_source(list(reversed(ROWS))))
    assert _exported_file(tmp_path).read_bytes() == first, "重复导出产生了字节差异"


# --------------------------------------------------------------------------
# 往返不变量 4 —— 严格 JSON
# --------------------------------------------------------------------------
def test_export_is_strict_json(tmp_path):
    """门禁 fixture 用 `json.loads` 读产物，不是宽松解析。"""
    export_customizations(doctype="Item", into=str(tmp_path), source=_source(ROWS))

    payload = json.loads(_exported_file(tmp_path).read_text(encoding="utf-8"))
    assert payload[PACK_DOCTYPE_KEY] == "Item"
    assert [row["fieldname"] for row in payload[PACK_ENTRIES_KEY]] == [
        "brand_code",
        "shelf_life_days",
    ], "条目必须按 fieldname 稳定排序"


# --------------------------------------------------------------------------
# 往返不变量 5 —— scope 完整性（关分页口径没被绕开）
# --------------------------------------------------------------------------
def test_export_reads_every_row_without_paging(tmp_path):
    """导出必须拿到该 DocType 的**全部**行，且走的仍是显式关分页的那条查询。

    这是一条回归性质的断言：导出复用 `capture` + `SiteSnapshotSource`，不新开第二条查询，
    所以关分页由 `SiteClient.list_resource` 保证——本用例用真的 `SiteClient` + 假传输，
    验证请求 URL 里 `limit_page_length=0` 确实在。分页截断在包里长得跟
    「站点本来就只有这些」一模一样，而它的后果是 apply 误删。
    """
    many = [_site_row("Item", f"probe_{i:03d}") for i in range(50)]
    requests = []

    def transport(request):
        requests.append(request)
        return SiteResponse(200, json.dumps({"data": many}))

    client = SiteClient("gate.invalid", base_url="http://site.invalid",
                        api_key="k", api_secret="s", transport=transport)
    export_customizations(
        doctype="Item", into=str(tmp_path), source=SiteSnapshotSource("gate.invalid", client=client)
    )

    payload = json.loads(_exported_file(tmp_path).read_text(encoding="utf-8"))
    assert len(payload[PACK_ENTRIES_KEY]) == 50, "有行没进包 —— 包里看不出截断，apply 会误删"
    assert any(f"{PAGE_LENGTH_PARAM}={UNLIMITED_PAGE_LENGTH}" in r.url for r in requests), (
        f"导出绕开了关分页口径：{[r.url for r in requests]}"
    )


# --------------------------------------------------------------------------
# 只动该 DocType 的文件 / 失败不留残骸
# --------------------------------------------------------------------------
def test_export_leaves_other_doctype_files_untouched(tmp_path):
    """同目录里别的 DocType 文件必须逐字节未变——导出的作用域是一个 DocType。"""
    scope_dir = tmp_path / PACK_SCOPE
    scope_dir.mkdir(parents=True)
    neighbor = scope_dir / "Customer.json"
    neighbor.write_text(
        render_doctype_file("Customer", [{"fieldname": "credit_tier"}]), encoding="utf-8"
    )
    before = neighbor.read_bytes()

    export_customizations(doctype="Item", into=str(tmp_path), source=_source(ROWS))

    assert neighbor.read_bytes() == before, "导出 Item 时改到了 Customer 的包文件"


def test_site_failure_raises_and_writes_nothing(tmp_path):
    """站点答不上话必须抛且**不留下任何文件**。

    写出一个空包比抛异常危险得多：空包在 apply 眼里等同于「这个 DocType 的定制全被删了」。
    """
    with pytest.raises(SiteError):
        export_customizations(
            doctype="Item", into=str(tmp_path), source=_source([], error=SiteError("站点宕了"))
        )

    scope_dir = tmp_path / PACK_SCOPE
    assert not scope_dir.exists() or not list(scope_dir.glob("*.json")), "站点读取失败却留下了包文件"


def test_missing_site_config_raises_instead_of_falling_back_offline(tmp_path):
    """没配 `AGENERP_SITE` 时抛，**不许**退回 `resolve_source` 的离线来源。

    退回的后果就是上一条说的那个空包：离线来源在空目录上返回零条目、不抛。
    """
    with pytest.raises(SiteError):
        export_customizations(doctype="Item", into=str(tmp_path))

    assert not (tmp_path / PACK_SCOPE).exists(), "没有站点配置却写出了包文件"


# --------------------------------------------------------------------------
# 排版回归 —— 复刻门禁那条逐行断言，断言自带
# --------------------------------------------------------------------------
def _changed_lines(before: str, after: str) -> list[str]:
    """复刻 `PackRepo.changed_lines`：取变动的**内容行**，去掉 diff 头，strip 后丢空行。"""
    out = []
    for line in difflib.unified_diff(before.splitlines(), after.splitlines(), n=0, lineterm=""):
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith(("+", "-")):
            out.append(line[1:].strip())
    return [line for line in out if line]


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param([], id="empty-array"),
        pytest.param(["zz_last"], id="insert-at-front"),
        pytest.param(["aaa_first"], id="insert-at-end"),
        pytest.param(["aaa_first", "zz_last"], id="insert-in-middle"),
    ],
)
def test_added_field_changes_only_probe_and_bracket_lines(tmp_path, existing):
    """门禁 `test_export_produces_readable_diff_only` 的逐行断言，四种插入位置各跑一遍。

    断言逐字与门禁一致：每一行**要么含探针名，要么 `line.strip() in "{}[],"`**。
    注意 `},` 不满足它（`}` 与 `,` 在 `"{}[],"` 里不相邻），所以行尾逗号排版在
    「插到末尾」那一格会红——本用例正是把那一格钉住的地方。
    """
    base_rows = [_site_row("Item", name) for name in existing]
    export_customizations(doctype="Item", into=str(tmp_path), source=_source(base_rows))
    before = _exported_file(tmp_path).read_text(encoding="utf-8")

    export_customizations(
        doctype="Item",
        into=str(tmp_path),
        source=_source(base_rows + [_site_row("Item", PROBE_FIELD)]),
    )
    after = _exported_file(tmp_path).read_text(encoding="utf-8")

    changed = _changed_lines(before, after)
    assert changed, "改了定制却没产生任何 diff"
    assert all(PROBE_FIELD in line or line.strip() in "{}[]," for line in changed), (
        f"diff 里夹带了与本次改动无关的内容：{[x for x in changed if PROBE_FIELD not in x][:5]}"
    )


def test_pack_keys_match_the_read_side(tmp_path):
    """写口径的两个键必须与读口径（`agenerp.snapshot`）逐字一致。

    不一致时往返测试也会红，但红因会指向「条目丢了」；这条把红因指到键名本身。
    """
    assert PACK_DOCTYPE_KEY == snapshot_mod._DOCTYPE_KEY
    assert PACK_ENTRIES_KEY == snapshot_mod._ENTRIES_KEY
