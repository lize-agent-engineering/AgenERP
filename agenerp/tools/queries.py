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
    rows = session.list_rows(
        doctype, _list_params(fields, params.get("filters"), params.get("limit")), detail=ROWS
    )
    return Outcome(
        data=rows,
        facts={"rows_all_from_requested_doctype": session.row_sources() == (doctype,)},
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
    """行业包业务合理性规则。**本期没有行业包，因此它的完整正确行为就是指名报错。**

    前置条件「行业包必须已装载」不满足时，`runtime.execute` 在第 ① 步就中止，
    一个请求都不发。走到这里只有一种情形：调用方**声称**装载过。
    那就把缺的东西指名说出来——**不伪造一个空包**，返回空会被读成「查过了，没有规则」。
    重开事件是 P1.6 交付第一个行业包（P1.0a §9）。
    """
    scope = params.get("doctype") or params.get("scenario") or "<未指定场景>"
    raise ToolError(
        f"行业包未装载：本仓在 P1.6 之前没有任何行业包，{scope} 没有规则可查。"
        "缺的是 `docs/masterplan/02-WBS.md` P1.6 的行业包制品（pack_id + rule_id 的来源）；"
        "在它到位之前，rule.lookup 不返回空清单——空清单会被读成「查过了，没有规则」。"
    )
