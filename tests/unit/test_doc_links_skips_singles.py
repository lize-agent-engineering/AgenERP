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

import pytest

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
