"""单据面的四个执行体：`doc.get` · `doc.links` · `lineage.trace` · `meta.fields`。

血缘扫描（`doc.links` / `lineage.trace` 共用）的三条实测硬约束逐条落在代码里：

- **必须扫子表级 Link 字段**——实测 21 个指向 `Sales Order` 的 Link 里 14 个在子表，
  只扫主表会返回空结果（本站点同一口径实读为 18 个里 14 个在子表）。
- **子表命中必须回溯到父单据**，否则返回的是明细行而不是单据。
- **下游筛选规则是「排除已取消（`docstatus == 2`）」**，不是「只要已提交」——
  草稿下游同样是证据，滤掉它会把 L2 门禁架空。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from agenerp.tools.runtime import Outcome, Session, ToolError

CANCELLED = 2

# 纯排版 fieldtype：`meta.fields` 的裁剪规则点名要剔的就是这些。
LAYOUT_FIELDTYPES = ("Section Break", "Column Break", "Tab Break", "HTML", "Fold")

TABLE_FIELDTYPES = ("Table", "Table MultiSelect")

LEVEL_DOCTYPE = "doctype"
LEVEL_CHILD_TABLE = "child_table"

# `doc.links` 每条关联的投影形状。**声明在这里**，因为后置断言要判的
# `fields_returned` 就是它：零条关联时也判得动——从返回的行上推的话，
# 「没有下游」会被读成「少返回了 from_is_submittable」。
LINK_ROW_FIELDS: tuple[str, ...] = (
    "name",
    "doctype",
    "docstatus",
    "from_is_submittable",
    "linked_via",
)


def _fields(names: tuple[str, ...], **extra: str) -> dict[str, str]:
    return {"fields": json.dumps(list(names)), "limit_page_length": "0", **extra}


def _filtered(names: tuple[str, ...], filters: list, **extra: str) -> dict[str, str]:
    return {**_fields(names, **extra), "filters": json.dumps(filters)}


def doctype_flags(session: Session) -> dict[str, dict]:
    """全站 DocType 的结构标志。

    `istable` 决定扫子表还是主表，`is_submittable` 是必须回的一列。

    ⚠️ **`issingle` 必须一起查出来。** 2026-08-26 之前这里只取三列，
    `scan_links()` 因此**无从知道哪个宿主是 Single** —— 而 Single 没有实体表，
    `GET /api/resource/<它>` 直接 HTTP 500，整个 `doc.links` 随之失败，
    模型拿到失败**原样重试同一个调用**，实测一次解释里同一调用被逐字节相同地
    调了六次、烧掉 13.6 万 token 后撞熔断。**只在下面加跳过判断而不查这一列，
    跳过会静默失效** —— 判据绿着，事故照旧。
    """
    rows = session.list_rows(
        "DocType", _fields(("name", "istable", "is_submittable", "issingle"))
    )
    return {row["name"]: row for row in rows}


def child_table_hosts(session: Session) -> dict[str, str]:
    """子表 DocType → 宿主 DocType。查子表行时 Frappe 要求带 `parent=<宿主>`，缺它查不动。"""
    rows = session.list_rows(
        "DocField",
        _filtered(("parent", "options"), [["fieldtype", "in", list(TABLE_FIELDTYPES)]],
                  parent="DocType"),
    )
    return {row["options"]: row["parent"] for row in rows if row.get("options")}


def link_fields_to(session: Session, doctype: str) -> list[dict]:
    """全站指向 `doctype` 的 Link 字段（含子表级）。一次查询拿全，不逐个 DocType 试。"""
    return session.list_rows(
        "DocField",
        _filtered(
            ("parent", "fieldname"),
            [["fieldtype", "=", "Link"], ["options", "=", doctype]],
            parent="DocType",
        ),
    )


def _link_row(name: str, doctype: str, docstatus: Any, flags: dict, via: str) -> dict:
    return {
        "name": name,
        "doctype": doctype,
        "docstatus": docstatus,
        "from_is_submittable": bool(flags.get(doctype, {}).get("is_submittable")),
        "linked_via": via,
    }


def scan_links(session: Session, doctype: str, name: str) -> tuple[list[dict], dict]:
    """一跳血缘：所有指向 `(doctype, name)` 的单据。返回 `(关联行, 扫描事实)`。

    主表级与子表级**两级都扫**，子表命中一律回溯到父单据。已取消（`docstatus == 2`）
    排除，草稿保留。
    """
    flags = doctype_flags(session)
    hosts = child_table_hosts(session)
    levels: list[str] = []
    hits: dict[tuple[str, str], dict] = {}
    child_level_rows: list[dict] = []
    for candidate in link_fields_to(session, doctype):
        holder, fieldname = candidate.get("parent"), candidate.get("fieldname")
        if not holder or not fieldname:
            continue
        # **Single 宿主一律跳过**（人 2026-08-25 对 C1 的裁定，逐字「排除 Single
        # 宿主，不留痕」）。Single 是单例设置/工具页，它那一格的值是「上一个用户
        # 刚输入的那个」，**不是业务关联**；而它没有实体表，查它必 HTTP 500。
        if flags.get(holder, {}).get("issingle"):
            continue
        is_child = bool(flags.get(holder, {}).get("istable"))
        level = LEVEL_CHILD_TABLE if is_child else LEVEL_DOCTYPE
        if level not in levels:
            levels.append(level)
        via = f"{holder}.{fieldname}"
        if is_child:
            host = hosts.get(holder)
            if host is None:
                continue
            rows = session.list_rows(
                holder,
                _filtered(("name", "parent", "parenttype"), [[fieldname, "=", name]], parent=host),
            )
            for row in rows:
                parent_type = row.get("parenttype") or host
                parent_name = row.get("parent")
                if not parent_name:
                    continue
                child_level_rows.append(row)
                parent_doc = session.list_rows(
                    parent_type,
                    _filtered(("name", "docstatus"), [["name", "=", parent_name]]),
                )
                docstatus = parent_doc[0].get("docstatus") if parent_doc else None
                hits[(parent_type, parent_name)] = _link_row(
                    parent_name, parent_type, docstatus, flags, via
                )
        else:
            # **单个宿主查失败不整次作废**（C1 裁定第 ② 条）。Single 只是「宿主
            # 会失败」的一种成因，权限、软删、上游 bug 都能让某一个宿主查崩。
            # 整次作废 = 一个坏宿主瘫痪整条归因链，而模型看到失败就重试 ⇒ 熔断。
            try:
                holder_rows = session.list_rows(
                    holder, _filtered(("name", "docstatus"), [[fieldname, "=", name]])
                )
            except Exception:  # noqa: BLE001 —— 宿主千奇百怪，这里只负责「别带走整次」
                continue
            for row in holder_rows:
                hits[(holder, row["name"])] = _link_row(
                    row["name"], holder, row.get("docstatus"), flags, via
                )
    rows = [row for row in hits.values() if row.get("docstatus") != CANCELLED]
    rows.sort(key=lambda row: (row["doctype"], row["name"]))
    child_doctypes = {name for name, flag in flags.items() if flag.get("istable")}
    facts = {
        # 扫过的层级：两级的候选都被走过一遍才两个都在。只扫主表的实现推不出 child_table。
        "scanned_link_levels": tuple(levels),
        # 回溯到位与否**从返回的行上推**：有任何一行的 doctype 是子表，就说明没回溯。
        "child_hits_resolved_to_parent": all(
            row["doctype"] not in child_doctypes for row in rows
        ),
        "child_table_hits": len(child_level_rows),
    }
    return rows, facts


def doc_links(session: Session, params: Mapping[str, Any]) -> Outcome:
    """一张单据的上下游关联。`from_is_submittable` 必回——缺它下游筛选会整类丢掉不可提交的业务单据。"""
    doctype, name = _target(params)
    rows, _ = scan_links(session, doctype, name)
    return Outcome(data=rows, facts={"fields_returned": LINK_ROW_FIELDS})


def lineage_trace(session: Session, params: Mapping[str, Any]) -> Outcome:
    """单据血缘：从 `(doctype, name)` 出发按跳数展开，逐跳都走 `scan_links` 的两级扫描。

    `depth` 默认 1；`max_rows` 由 runtime 按契约截断，本执行体不自行收窄。
    """
    doctype, name = _target(params)
    depth = int(params.get("depth", 1) or 1)
    seen: dict[tuple[str, str], dict] = {}
    frontier = [(doctype, name)]
    levels: list[str] = []
    resolved = True
    child_hits = 0
    for hop in range(1, max(depth, 1) + 1):
        nxt: list[tuple[str, str]] = []
        for node_type, node_name in frontier:
            rows, facts = scan_links(session, node_type, node_name)
            for level in facts["scanned_link_levels"]:
                if level not in levels:
                    levels.append(level)
            resolved = resolved and bool(facts["child_hits_resolved_to_parent"])
            child_hits += int(facts["child_table_hits"])
            for row in rows:
                key = (row["doctype"], row["name"])
                if key in seen or key == (doctype, name):
                    continue
                seen[key] = {**row, "hops": hop}
                nxt.append(key)
        frontier = nxt
        if not frontier:
            break
    rows = sorted(seen.values(), key=lambda row: (row["hops"], row["doctype"], row["name"]))
    return Outcome(
        data=rows,
        facts={
            "scanned_link_levels": tuple(levels),
            "child_hits_resolved_to_parent": resolved,
            "child_table_hits": child_hits,
        },
    )


def _target(params: Mapping[str, Any]) -> tuple[str, str]:
    doctype, name = params.get("doctype"), params.get("name")
    if not doctype or not name:
        raise ToolError("需要 doctype 与 name 两个参数：不猜单据，缺一即停")
    return str(doctype), str(name)


def meta_field_rows(session: Session, doctype: str, level: str) -> tuple[list[dict], list[str]]:
    """一个 DocType 的字段行（已剔排版与隐藏字段），外加它的子表 DocType 清单。"""
    meta = session.get_doc("DocType", doctype)
    rows: list[dict] = []
    children: list[str] = []
    for field in meta.get("fields", []):
        fieldtype = field.get("fieldtype")
        if fieldtype in TABLE_FIELDTYPES and field.get("options"):
            children.append(field["options"])
        if fieldtype in LAYOUT_FIELDTYPES or field.get("hidden"):
            continue
        rows.append(
            {
                "fieldname": field.get("fieldname"),
                "fieldtype": fieldtype,
                "label": field.get("label"),
                "options": field.get("options"),
                "reqd": bool(field.get("reqd")),
                "level": level,
                "parent_doctype": doctype,
            }
        )
    return rows, children


def meta_fields(session: Session, params: Mapping[str, Any]) -> Outcome:
    """一个 DocType 的字段表。**主表字段与子表字段分标**，否则结构化导航会在子表上失明。"""
    doctype = str(params.get("doctype") or "")
    if not doctype:
        raise ToolError("需要 doctype 参数：不猜 DocType，缺参即停")
    rows, children = meta_field_rows(session, doctype, LEVEL_DOCTYPE)
    for child in dict.fromkeys(children):
        child_rows, _ = meta_field_rows(session, child, LEVEL_CHILD_TABLE)
        rows.extend(child_rows)
    return Outcome(
        data=rows,
        facts={"fields_tagged_by_level": all(
            row.get("level") in (LEVEL_DOCTYPE, LEVEL_CHILD_TABLE) for row in rows
        ) and bool(rows)},
    )


def doc_get(session: Session, params: Mapping[str, Any]) -> Outcome:
    """取一张完整单据，**子表明细一并返回**——否则拿不到 warehouse / against_sales_order 这类事实。

    `child_tables_included` 由**站点的元数据**核对出来：单据的 meta 里声明了哪些子表字段，
    返回值里就必须有哪些。执行体自报一句 `True` 是验不出漏子表的。
    """
    doctype, name = _target(params)
    doc = session.get_doc(doctype, name)
    meta = session.get_doc("DocType", doctype)
    declared = [
        field["fieldname"]
        for field in meta.get("fields", [])
        if field.get("fieldtype") in TABLE_FIELDTYPES and field.get("fieldname")
    ]
    included = all(isinstance(doc.get(fieldname), list) for fieldname in declared)
    return Outcome(data=doc, facts={"child_tables_included": included})
