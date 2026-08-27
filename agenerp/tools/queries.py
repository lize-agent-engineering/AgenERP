"""查询面的三个执行体：`query.read` · `snapshot.read` · `rule.lookup`。

前两个是**作答类工具**（`ANSWERING_TOOLS`）——证据充分性门禁 L1/L2/L3 挂在它们身上，
因为它们的返回值就是答案里的数字。门禁判定在 `runtime.execute` 的第 ① 步，
本模块**一行都不参与**：让被考的人参与判卷正是门禁要挡的形状。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from agenerp.site import SiteError
from agenerp.snapshot import SITE_SCOPE_DOCTYPES, entries_from_site_rows
from agenerp.tools.runtime import Outcome, Session, ToolError

# `query.read` 必回的两个字段（契约 `must_keep`）。调用方点名字段时也要并进去：
# 少了 `name` 下游没法再取证，少了 `docstatus` 分不清草稿与已提交。
REQUIRED_FIELDS: tuple[str, ...] = ("name", "docstatus")

ROWS = "rows"


def _list_params(fields: tuple[str, ...], filters: Any, limit: Any) -> dict[str, str]:
    params = {"fields": json.dumps(list(fields)), "limit_page_length": "0"}
    if filters:
        params["filters"] = json.dumps(filters)
    if limit:
        params["limit_page_length"] = str(int(limit))
    return params


def _list_view_fields(session: Session, doctype: str) -> tuple[str, ...]:
    """调用方没点名字段时的默认字段集：DocType 自己的 `in_list_view`。

    **不回 `*`**：整行倒给模型正是 §7.3.1 那条裁剪规则要挡的东西。
    """
    meta = session.get_doc("DocType", doctype)
    chosen = [
        field["fieldname"]
        for field in meta.get("fields", [])
        if field.get("in_list_view") and field.get("fieldname")
    ]
    return tuple(dict.fromkeys([*REQUIRED_FIELDS, *chosen]))


def query_read(session: Session, params: Mapping[str, Any]) -> Outcome:
    """读一个 DocType 的若干行。**返回的每一行都来自调用方声明的 DocType，不得跨表拼装。**

    `rows_all_from_requested_doctype` 由**本次实际取过行的资源端点**推出来
    （`Session.row_sources()`）：拼两张表的实现必然取过两个端点，这条后置断言就红。
    残余弱点照实记（P1.0a §8 风险②）：它验得了「取自哪几个端点」，
    验不了「每个筛选条件的语义都对」。
    """
    doctype = str(params.get("doctype") or "")
    if not doctype:
        raise ToolError("需要 doctype 参数：不猜 DocType，缺参即停")
    requested = params.get("fields")
    fields = (
        tuple(dict.fromkeys([*REQUIRED_FIELDS, *[str(f) for f in requested]]))
        if requested
        else _list_view_fields(session, doctype)
    )
    try:
        rows = session.list_rows(
            doctype, _list_params(fields, params.get("filters"), params.get("limit")), detail=ROWS
        )
    except SiteError as exc:
        raise _child_table_error(session, doctype, exc) from exc
    return Outcome(
        data=rows,
        facts={"rows_all_from_requested_doctype": session.row_sources() == (doctype,)},
    )


def _child_table_error(session: Session, doctype: str, exc: SiteError) -> Exception:
    """站点拒了这次列表读 —— 判一下**是不是因为它压根是张子表**。

    🔴 实测根因（2026-08-27，站点 `frontend`）：`Purchase Order Item` / `Sales Order Item`
    这类子表 `GET /api/resource/<子表>` **恒回 HTTP 403 PermissionError**，
    连 Administrator 也一样 —— 那是 Frappe 的结构约束，不是权限配错。
    而同一行数据从父单据读得到：`Purchase Order/PUR-ORD-2026-00001` → `items[0].received_qty`。

    ⚠️ **代价是实测过的**：解释循环里模型已经找对了 `Purchase Order Item.received_qty`，
    想验证一下，被这个 403 顶回来，于是以为**单据选错了**，退回去重搜 —— 再验、再 403，
    **八轮烧光、返回空答案**。回给它的原文是一坨 Python traceback，
    里面没有任何一句说得清「子表要从父单据读」。评测集 40 条里有 8 条踩这条路。

    ⚠️ **只在站点已经拒了之后才判**，成功路径一个额外请求都不发 ——
    `Session` 的注释写死了「这次执行发了几个请求」是判据，不许平白变胖。

    判不出来就**原样抛回去**：把「真的没权限」改写成「这是子表」会是更坏的错误。
    """
    try:
        meta = session.get_doc("DocType", doctype)
    except SiteError:
        return exc  # 连 meta 都读不到 —— 说不出更多，别编
    if not meta.get("istable"):
        return exc
    return ToolError(
        f"{doctype} 是子表（istable=1）—— Frappe **不允许**直接列读子 DocType，"
        f"这不是权限没配好，换个身份也一样。子表的行随父单据一起返回："
        f"改用 `doc.get` 读**父单据**，要的字段就在父单据的子表里。"
        f"（站点原文：{str(exc).splitlines()[0][:120]}）"
    )


def _canonical(entries: list[dict]) -> str:
    return json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def snapshot_read(session: Session, params: Mapping[str, Any]) -> Outcome:
    """打一次站点状态快照。**口径与 `agenerp.snapshot` 同源**，不开第二套。

    规范化（剥 modified / creation / owner / `_comments`、键稳定排序）由
    `agenerp.snapshot.entries_from_site_rows` 做；本执行体只负责把它摆成工具返回值的形状，
    并把 `snapshot_normalized` 这条事实**从产出上核对出来**——
    执行体自报一句 `True` 的话，一个不规范化的实现照样绿。

    `snapshot_id` 是内容哈希：同一状态两次读出同一个 id。采集时刻**不进 id**，
    否则「同一站点两次快照相等」永远不成立（§11.5 的同一条要求）。
    """
    scope = str(params.get("scope") or "doctypes")
    doctype = SITE_SCOPE_DOCTYPES.get(scope)
    if doctype is None:
        raise ToolError(
            f"站点来源不认识 scope {scope!r}；已知：{sorted(SITE_SCOPE_DOCTYPES)}"
            "（返回空会让「scope 拼错了」和「这个 scope 下没有定制」长得一模一样）"
        )
    rows = session.list_rows(doctype, {"fields": json.dumps(["*"]), "limit_page_length": "0"},
                             detail=ROWS)
    entries = [
        {"doctype": entry.doctype, "fieldname": entry.fieldname, "attributes": entry.attributes}
        for entry in sorted(entries_from_site_rows(rows), key=lambda e: e.key)
    ]
    canonical = _canonical(entries)
    keys = {key for entry in entries for key in entry["attributes"]}
    return Outcome(
        data={
            "snapshot_id": hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16],
            "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "scope": scope,
            "entries": entries,
        },
        facts={
            "snapshot_normalized": not (keys & _VOLATILE_KEYS)
            and canonical == _canonical(sorted(entries, key=lambda e: (e["doctype"], e["fieldname"]))),
        },
        rows_key="entries",
    )


# 规范化要剥掉的易变键。带着它们的话，什么都没改重新读一次也会 diff 出差异。
_VOLATILE_KEYS = {"modified", "creation", "owner", "modified_by", "_comments", "_liked_by"}


def rule_lookup(session: Session, params: Mapping[str, Any]) -> Outcome:
    """行业包业务合理性规则。**它的完整正确行为仍然是指名报错**，但理由变了。

    前置条件「行业包必须已装载」不满足时，`runtime.execute` 在第 ① 步就中止，
    一个请求都不发。走到这里只有一种情形：调用方**声称**装载过。
    那就把缺的东西指名说出来——**不伪造一个空包**，返回空会被读成「查过了，没有规则」。

    ⚠️ **P1.6 已经交付第一个行业包，原先那个重开事件已经发生，但翻转被裁判挡住了。**
    今天的三件事逐条说清：
    ① **包在盘上**：`industry-packs/discrete/pack.json`（三条规则各带 `test_case`），
       装载面与校验器在 `agenerp/packs/`，落点节 `docs/architecture/module-boundaries.md` §7.10；
    ② **未接线**：本函数**没有**去读那个包，工具面上「行业包已装载」依然不成立；
    ③ **接线为什么要人裁定**：三处判据钉着本函数的现行报错行为 ——
       `tests/gates/test_tool_execution_live.py:119`（裁判）· 它委派进去的
       `tests/tools/test_live_conformance.py:157` · `tests/tools/test_executors.py:290`。
       接线会让那条 L2 门禁由绿转红，复绿只能改裁判或改它委派的断言体，两者都在红线内。
       两条出路与各自代价见 `docs/masterplan/STATE.md` §3 的 needs-human。

    **本 docstring 只改说法，报错消息的行为一个字没改**（上面三处判据都钉着它）。
    """
    scope = params.get("doctype") or params.get("scenario") or "<未指定场景>"
    raise ToolError(
        f"行业包未装载：本仓在 P1.6 之前没有任何行业包，{scope} 没有规则可查。"
        "缺的是 `docs/masterplan/02-WBS.md` P1.6 的行业包制品（pack_id + rule_id 的来源）；"
        "在它到位之前，rule.lookup 不返回空清单——空清单会被读成「查过了，没有规则」。"
    )
