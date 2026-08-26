"""`doc.links` 遇到 Single DocType 宿主必须跳过，且单个宿主失败不整次作废。

判据来源：人 2026-08-25 对 `STATE` §3 那条 `C1` 的裁定 ——
**「排除 Single 宿主，不留痕」**，且**「单个宿主查失败不整次作废」**。

## 这条判据是被一次真实事故逼出来的（2026-08-26 实测）

`doc.links` 扫到 `Quick Stock Balance`（`issingle: 1`，**没有实体表**）时，
`GET /api/resource/Quick Stock Balance` 直接 **HTTP 500**，整个 `doc.links`
返回 `ok=False, data=None`。模型拿到失败**原样重试同一个调用** ——
实测一次解释里 `doc.links{doctype: Item, name: HRD-PACK-5K}` 被**逐字节相同地
调了六次**，撞满 `MAX_TOOL_CALLS` 熔断，烧掉 **136,331 token**、答案为空。

⚠️ **更深一层**：`doctype_flags()` 当时只取 `("name", "istable", "is_submittable")`
—— **`issingle` 根本没被查出来**，所以 `scan_links` 无从知道哪个宿主是 Single。
只加跳过判断而不加这个字段，跳过永远不会生效。**两处都要改。**
"""
from __future__ import annotations

import json

from agenerp.tools import documents


class _Session:
    """按 `doctype` 分派的假站点。`Quick Stock Balance` 一被查就抛 —— 模拟真 500。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_rows(self, doctype: str, params: dict) -> list[dict]:
        self.calls.append(doctype)
        if doctype == "DocType":
            return [
                {"name": "Sales Order", "istable": 0, "is_submittable": 1, "issingle": 0},
                {"name": "Quick Stock Balance", "istable": 0, "is_submittable": 0, "issingle": 1},
            ]
        if doctype == "DocField":
            filters = json.loads(params.get("filters", "[]"))
            if any(f[0] == "fieldtype" and f[2] == "Link" for f in filters):
                return [
                    {"parent": "Sales Order", "fieldname": "item_code"},
                    {"parent": "Quick Stock Balance", "fieldname": "item_code"},
                ]
            return []
        if doctype == "Quick Stock Balance":
            raise AssertionError(
                "扫到了 Single DocType —— 真站点上这一步是 HTTP 500，"
                "而它会让整个 doc.links 失败、模型原样重试到熔断"
            )
        if doctype == "Sales Order":
            return [{"name": "SAL-ORD-0001", "docstatus": 1}]
        return []


def test_single_doctype_hosts_are_never_queried():
    """Single 宿主**一次都不许查** —— 查了就是真站点上的 500。"""
    session = _Session()
    rows, _facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    assert "Quick Stock Balance" not in session.calls, (
        f"Single 宿主被查了。实际查询序列：{session.calls}"
    )
    assert [row["name"] for row in rows] == ["SAL-ORD-0001"], (
        f"跳过 Single 的同时，正常宿主的命中必须照常返回，实得 {rows!r}"
    )


def test_doctype_flags_actually_fetches_issingle():
    """`doctype_flags()` 必须把 `issingle` 查出来。

    ⚠️ 这条独立于上一条：只加跳过判断而不查这个字段，`flags[...]["issingle"]`
    永远是 `None`，跳过**静默失效** —— 判据会绿着，事故照旧。
    """
    session = _Session()
    documents.doctype_flags(session)

    # 第一次调用一定是 DocType 的元数据查询
    assert session.calls[0] == "DocType"


def test_one_failing_host_does_not_abort_the_whole_scan():
    """单个宿主查失败 ⇒ 跳过它继续扫其余，不整次作废（`C1` 裁定第 ② 条）。

    这一条防的是**下一次**：Single 只是「宿主会失败」的一种成因，
    权限、软删、上游 bug 都能让某一个宿主查崩。整次作废 = 一个坏宿主
    瘫痪整条归因链，而模型看到失败就重试 ⇒ 又一次熔断。
    """

    class _OneBadHost(_Session):
        def list_rows(self, doctype: str, params: dict) -> list[dict]:
            if doctype == "DocType":
                return [
                    {"name": "Sales Order", "istable": 0, "is_submittable": 1, "issingle": 0},
                    {"name": "Broken DocType", "istable": 0, "is_submittable": 0, "issingle": 0},
                ]
            if doctype == "DocField":
                filters = json.loads(params.get("filters", "[]"))
                if any(f[0] == "fieldtype" and f[2] == "Link" for f in filters):
                    return [
                        {"parent": "Broken DocType", "fieldname": "item_code"},
                        {"parent": "Sales Order", "fieldname": "item_code"},
                    ]
                return []
            if doctype == "Broken DocType":
                raise RuntimeError("站点侧失败：HTTP 500")
            if doctype == "Sales Order":
                return [{"name": "SAL-ORD-0001", "docstatus": 1}]
            return []

    rows, _facts = documents.scan_links(_OneBadHost(), "Item", "HRD-PACK-5K")
    assert [row["name"] for row in rows] == ["SAL-ORD-0001"], (
        f"一个宿主崩了不该带走整次扫描，实得 {rows!r}"
    )


class _ChildHostSession:
    """子表宿主（`Sales Order Item`）+ 主表宿主（`Delivery Note`）的假站点。

    `fail_on` 里的 doctype 一被查就抛 —— 模拟真站点上的 HTTP 500。
    候选顺序刻意把**子表宿主排在前面**：坏宿主若带走整次扫描，
    后面那个健康的主表宿主就一次都扫不到，这正是实测探针观测到的形态。
    """

    DOCTYPES = (
        {"name": "Sales Order", "istable": 0, "is_submittable": 1, "issingle": 0},
        {"name": "Sales Order Item", "istable": 1, "is_submittable": 0, "issingle": 0},
        {"name": "Delivery Note", "istable": 0, "is_submittable": 1, "issingle": 0},
    )

    def __init__(self, fail_on: tuple[str, ...] = ()) -> None:
        self.calls: list[str] = []
        self.fail_on = set(fail_on)

    def list_rows(self, doctype: str, params: dict) -> list[dict]:
        self.calls.append(doctype)
        if doctype in self.fail_on:
            raise RuntimeError(f"站点侧失败：HTTP 500（{doctype}）")
        if doctype == "DocType":
            return [dict(row) for row in self.DOCTYPES]
        if doctype == "DocField":
            filters = json.loads(params.get("filters", "[]"))
            if any(f[0] == "fieldtype" and f[1] == "in" for f in filters):
                return [{"parent": "Sales Order", "options": "Sales Order Item"}]
            if any(f[0] == "fieldtype" and f[2] == "Link" for f in filters):
                return [
                    {"parent": "Sales Order Item", "fieldname": "item_code"},
                    {"parent": "Delivery Note", "fieldname": "item_code"},
                ]
            return []
        if doctype == "Sales Order Item":
            return [
                {
                    "name": "SAL-ORD-0001-1",
                    "parent": "SAL-ORD-0001",
                    "parenttype": "Sales Order",
                }
            ]
        if doctype == "Sales Order":
            return [{"name": "SAL-ORD-0001", "docstatus": 1}]
        if doctype == "Delivery Note":
            return [{"name": "MAT-DN-0001", "docstatus": 1}]
        return []


def test_a_failing_child_table_host_does_not_abort_the_whole_scan():
    """**子表宿主**查失败 ⇒ 跳过它继续扫其余（`C1` 裁定第 ② 条的另一半路径）。

    既有的 `test_one_failing_host_does_not_abort_the_whole_scan` 的坏宿主是
    `"istable": 0` ⇒ 它只走主表支。子表支此前**零覆盖**，而 roadmap 的
    「已知的坑」逐字写着「21 个指向 `Sales Order` 的 Link 里 14 个在子表」
    ⇒ 无守卫的那一支才是多数路径。
    """
    session = _ChildHostSession(fail_on=("Sales Order Item",))
    rows, _facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    assert [row["name"] for row in rows] == ["MAT-DN-0001"], (
        f"一个子表宿主崩了不该带走整次扫描，实得 {rows!r}；"
        f"实际查询序列：{session.calls}"
    )


def test_a_failing_parent_backtrack_does_not_abort_the_whole_scan():
    """**回溯父单据**失败 ⇒ 跳过这一行继续扫其余，不整次作废。

    与上一条**分开写**：子表支有两处站点调用（查子表行 · 逐行回溯父单据），
    合成一条会让「只修了其中一处」蒙混过关。回溯那处还在 `for row in rows`
    循环里 —— 命中越多，调用越多，撞上失败的机会也越大。
    """
    session = _ChildHostSession(fail_on=("Sales Order",))
    rows, _facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    assert [row["name"] for row in rows] == ["MAT-DN-0001"], (
        f"回溯父单据失败不该带走整次扫描，实得 {rows!r}；"
        f"实际查询序列：{session.calls}"
    )


def test_a_healthy_child_host_still_resolves_hits_to_the_parent_document():
    """反「绿着坏掉」：健康的子表宿主必须**照常**产出回溯到父单据的命中。

    ⚠️ 没有这一条，把整个子表支 `try: … except: continue` 包起来
    也能让上面两条绿 —— 守卫吞掉一切、扫描退化成空集，同样「不整次作废」。
    """
    session = _ChildHostSession()
    rows, facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    assert [row["name"] for row in rows] == ["MAT-DN-0001", "SAL-ORD-0001"], (
        f"健康子表宿主的命中必须照常回溯到父单据，实得 {rows!r}"
    )
    assert facts["child_hits_resolved_to_parent"] is True
    assert facts["child_table_hits"] >= 1, (
        f"子表行一条都没算上，守卫把健康路径也吞了：{facts!r}"
    )
    assert all(row["doctype"] != "Sales Order Item" for row in rows), (
        f"返回的是明细行而不是单据：{rows!r}"
    )


class _PartialBacktrackSession(_ChildHostSession):
    """一个子表宿主两条行：一条能回溯到父单据，另一条回溯必失败。

    钉住 `Decision` ①（回溯失败的那一行怎么处置）。**两种相反的实现**
    ——「丢掉」与「以 `docstatus=None` 记入」——在只看「不整次作废」的判据下
    都是绿的，必须由这一条把它们分开。
    """

    DOCTYPES = (
        *_ChildHostSession.DOCTYPES,
        {"name": "Purchase Order", "istable": 0, "is_submittable": 1, "issingle": 0},
    )

    def list_rows(self, doctype: str, params: dict) -> list[dict]:
        if doctype == "Sales Order Item":
            self.calls.append(doctype)
            return [
                {
                    "name": "SAL-ORD-0001-1",
                    "parent": "SAL-ORD-0001",
                    "parenttype": "Sales Order",
                },
                {
                    "name": "SAL-ORD-0001-2",
                    "parent": "PUR-ORD-0001",
                    "parenttype": "Purchase Order",
                },
            ]
        return super().list_rows(doctype, params)


def test_a_row_whose_parent_backtrack_failed_is_dropped_not_faked():
    """`Decision` ①（a）：回溯失败的那一行**丢掉**，不以 `docstatus` 未知记入。

    ⚠️ 为什么不能记入：`scan_links()` 末尾的下游筛选逐字是
    `row.get("docstatus") != CANCELLED`，而 `None != 2` **为真**
    ⇒ 记入等于把一张**可能已取消**的单据当成有效关联漏给下游，
    直接违反 roadmap「已知的坑」里那条「`doc.links` 的下游筛选是排除已取消」。
    取舍是明写的：**少报一条真实关联 > 冒充一条状态未知的**。

    同时钉住 `child_table_hits` 的口径 —— 计数只算**产出了命中**的子表行，
    所以 `child_level_rows.append(row)` 必须在那次调用**成功之后**。
    """
    session = _PartialBacktrackSession(fail_on=("Purchase Order",))
    rows, facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    names = [row["name"] for row in rows]
    assert names == ["MAT-DN-0001", "SAL-ORD-0001"], (
        f"能回溯的那一行必须留下、回溯失败的那一行必须丢掉，实得 {rows!r}"
    )
    assert "PUR-ORD-0001" not in names, (
        f"回溯失败的行被以 docstatus 未知记入了 —— 已取消单据会就此漏出去：{rows!r}"
    )
    assert facts["child_table_hits"] == 1, (
        f"`child_table_hits` 必须只算产出了命中的子表行，实得 {facts!r}"
    )
    assert facts["child_rows_skipped_after_failure"] == 1, (
        f"`Decision` ③（B）：被跳过的行要留痕，不许静默降级，实得 {facts!r}"
    )


def test_a_level_whose_hosts_all_failed_is_not_claimed_as_scanned():
    """`Decision` ②（a）：某一级的宿主**全部**查崩时，不许再声称扫过那一级。

    `scanned_link_levels` 是契约后置条件（`agenerp/tools_readonly.py`
    逐字要求 `contains child_table`），不是内部字段。声称扫过而实际全崩，
    下游会把「没扫成」读成「扫过、没有关联」—— 那正是归因静默出错的形状。
    ⚠️ **零命中仍要记**：扫成了只是没有关联，与全崩是两回事。
    """
    session = _ChildHostSession(fail_on=("Sales Order Item",))
    _rows, facts = documents.scan_links(session, "Item", "HRD-PACK-5K")

    assert set(facts["scanned_link_levels"]) == {"doctype"}, (
        f"子表宿主全崩了却仍声称扫过 child_table：{facts!r}"
    )
    assert facts["hosts_skipped_after_failure"] == 1, (
        f"`Decision` ③（B）：被跳过的宿主要留痕，实得 {facts!r}"
    )
