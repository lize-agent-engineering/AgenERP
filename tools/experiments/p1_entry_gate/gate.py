"""把证据充分性门禁 L1/L2/L3 施加到一次对话上 —— **规则本身一个字都不在这里**。

三条 `Condition` 是 `agenerp/tools_readonly.py` 的 `EVIDENCE_GATE`（owner doc 是
`docs/design/agents-and-roles.md` §5.0 ①）。本模块只做一件事：把一次对话的**事实**
凑齐，交给它们求值。规则若在这里被复述一遍，实验测的就成了这份复述而不是那三条规则。

**五条事实各自怎么来**：

| 事实 | 来源 | 谁能伪造 |
|---|---|---|
| `documents_named_in_question` | 从问题文本里按单号形状抽 | 无（问题是四格逐字相同的常量） |
| `doc_links_called_for` | 轨迹里 `doc.links` 的 `name` 参数 | 无（轨迹由循环记，不由模型自报） |
| `doc_get_called_for` | 轨迹里 `doc.get` 的 `name` 参数 | 同上 |
| `submitted_downstream_documents` | 轨迹里 `doc.links` **返回值**中 `docstatus == 1` 的行 | 同上 |
| `inbound_vouchers_of_quantities_in_answer` | **直接查站点**：答案里出现的数字若等于某个 `Bin.actual_qty`，就取该 `(物料, 仓库)` 在库存流水里所有使数量**增加**的凭证 | 无（不看模型查过什么） |

**L3 的触发口径是「答案里的数字」，不是「模型查过 Bin」**：后者会让一个从不查
Bin、却照样报出 1,010 的回答绕过 L3。触发判据因此独立于模型的行为。
**残余风险照实登记**：只描述「积压」而不报数字的回答**escape 得掉 L3**——
规则原文写的就是「作答涉及某个仓库的库存**数量**」，本模块不擅自扩大它。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from agenerp.contracts import Evaluation, ReadOnlyContext, evaluate_all, unsatisfied
from agenerp.site import SiteClient
from agenerp.tools_readonly import EVIDENCE_GATE

# ERPNext 的单号形状：`SAL-ORD-2026-00001` / `MAT-SCR-2026-00001` / `MFG-WO-2026-00001`。
# 至少三段，全大写数字。**问题文本是四格逐字相同的常量**，抽取结果因此也是常量。
DOC_NAME = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}\b")

# 答案里的数字：允许千分位与小数。`1,010` 与 `1010` 必须都算命中。
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

SUBMITTED = 1


@dataclass
class Observations:
    """一次对话里**由循环记下来**的事实。模型说了什么不算数，调了什么才算数。"""

    doc_links_called_for: list[str] = field(default_factory=list)
    doc_get_called_for: list[str] = field(default_factory=list)
    submitted_downstream_documents: list[str] = field(default_factory=list)

    def record_call(self, tool: str, params: dict, data: Any) -> None:
        name = str(params.get("name") or "")
        if tool == "doc.get" and name:
            _add(self.doc_get_called_for, name)
        if tool == "doc.links" and name:
            _add(self.doc_links_called_for, name)
            for row in data if isinstance(data, list) else []:
                if isinstance(row, dict) and row.get("docstatus") == SUBMITTED:
                    _add(self.submitted_downstream_documents, str(row.get("name")))


def _add(bucket: list[str], value: str) -> None:
    if value and value not in bucket:
        bucket.append(value)


def documents_named_in(question: str) -> list[str]:
    return list(dict.fromkeys(DOC_NAME.findall(question)))


def _numbers_in(text: str) -> set[float]:
    found: set[float] = set()
    for token in NUMBER.findall(text):
        try:
            found.add(float(token.replace(",", "")))
        except ValueError:
            continue
    return found


def inbound_vouchers_for_answer(client: SiteClient, answer: str) -> list[str]:
    """答案里报了哪个仓库的库存量 → 该库存的全部入库凭证。

    **直接查站点**，不看模型查过什么：L3 判的是「答案里的数字有没有取全证」，
    模型从哪儿弄到那个数字不影响它该不该取证。
    """
    numbers = _numbers_in(answer)
    if not numbers:
        return []
    bins = _rows(client, "Bin", ("item_code", "warehouse", "actual_qty"))
    targets = [
        (row["item_code"], row["warehouse"])
        for row in bins
        if float(row.get("actual_qty") or 0) in numbers
    ]
    vouchers: list[str] = []
    for item_code, warehouse in targets:
        for row in _rows(
            client,
            "Stock Ledger Entry",
            ("item_code", "warehouse", "actual_qty", "voucher_no", "is_cancelled"),
            [["item_code", "=", item_code], ["warehouse", "=", warehouse]],
        ):
            if not row.get("is_cancelled") and float(row.get("actual_qty") or 0) > 0:
                _add(vouchers, str(row.get("voucher_no")))
    return sorted(vouchers)


def _rows(client: SiteClient, doctype: str, fields: tuple[str, ...], filters=None) -> list[dict]:
    params = {"fields": json.dumps(list(fields)), "limit_page_length": "0"}
    if filters:
        params["filters"] = json.dumps(filters)
    payload = client.get(f"/api/resource/{doctype}", params)
    rows = payload.get("data") if isinstance(payload, dict) else None
    return rows if isinstance(rows, list) else []


def facts(
    question: str, answer: str, observed: Observations, client: SiteClient
) -> dict[str, Any]:
    return {
        "documents_named_in_question": documents_named_in(question),
        "doc_links_called_for": list(observed.doc_links_called_for),
        "doc_get_called_for": list(observed.doc_get_called_for),
        "submitted_downstream_documents": list(observed.submitted_downstream_documents),
        "inbound_vouchers_of_quantities_in_answer": inbound_vouchers_for_answer(client, answer),
    }


def evaluate(
    question: str, answer: str, observed: Observations, client: SiteClient
) -> tuple[tuple[Evaluation, ...], dict[str, Any]]:
    """对三条规则求值，**不短路**——一次把所有不满足的原因都给出来。"""
    collected = facts(question, answer, observed, client)
    return evaluate_all(EVIDENCE_GATE, ReadOnlyContext(collected)), collected


def missing_count(evaluation: Evaluation, collected: dict[str, Any]) -> int | None:
    """这条规则还差几项证据 —— **只数个数，不取名字**（名字是答案的一部分）。"""
    condition = evaluation.condition
    if condition.operator != "covers_fact":
        return None
    required = collected.get(condition.value)
    actual = collected.get(condition.fact)
    if not isinstance(required, list) or not isinstance(actual, list):
        return None
    return len(set(required) - set(actual))


def forced_continue_message(failed: tuple[Evaluation, ...], collected: dict[str, Any]) -> str:
    """门禁发红时回注给模型的强制续跑消息。

    **只说规则和缺多少件，不说缺哪几件。** 说出单号等于把答案递过去 ——
    那样测到的是「告诉模型答案有没有用」，不是「门禁能不能补偿模型能力」。
    代价照实记（plan Phase 2 的 `Decision`）：这是**保守**的一侧，
    信息量更大的门禁可能表现更好，因此 H2 的结果是**下界**而不是上界。
    """
    lines = ["证据不足，还不能作答。以下规则没有满足："]
    for item in failed:
        lines.append(f"- {item.condition.text}")
        missing = missing_count(item, collected)
        if missing:
            lines.append(f"  还有 {missing} 项证据没有取到（用工具把它们查出来，不要猜）。")
    lines.append("请继续调工具补齐证据，补齐之后再给最终回答。")
    return "\n".join(lines)


def failures(evaluations: tuple[Evaluation, ...]) -> tuple[Evaluation, ...]:
    return unsatisfied(evaluations)
