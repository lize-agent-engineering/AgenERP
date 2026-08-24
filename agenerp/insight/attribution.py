"""洞察 Agent 的归因面 —— **只做命中之后那一段**。

落点节是 `docs/architecture/module-boundaries.md` §7.9。

D-15 逐字：巡检（按清单逐条查、命中即报）是代码，模型真正不可替代的位置在**命中之后**
——「为什么会这样、要不要紧、该怎么办」。本模块就是那一段，而且**只有**那一段：
它不发现任何东西，发现力全在 `agenerp/inspection/` 的规则清单里。

**`Decision` D3：归因走 P1.4 的解释循环，不另起一条。** 消费的符号是
`agenerp.explain.explain`（`agenerp/explain/__init__.py` 的 `__all__` 两项之一，
返回 `ExplainResult`）。备选「洞察侧自己开一条轻循环、不带证据门禁」被否决：
那正是 `docs/design/agents-and-roles.md` §5.0 ① 要修的「停在第一层证据上」，
在洞察侧重新打开这个口子等于把 P1.4 白做。

⚠️ **残余风险照实登记（两条，都是 D3 选项 B 的代价）**：
① 命中记录里的数字会进答案文本，从而触发 L3 的取证要求 —— **这是想要的行为**
（覆盖判据由此生效），但会抬高单次归因的成本；
② 命中的 `subject` 里可能有**长得像单号**的取值（例如物料号 `HRD-PACK-5K` 三段全大写数字，
正好落进 `agenerp/explain/gate.py` 的 `DOC_NAME` 形状），于是 L1 会把它当成
「问题点名的单据」并要求 `doc.links`。判据实测确认了这一条。**不擅自绕开**：
门禁的措辞归 owner doc 与人的裁定面，而它误报的方向是**更严**（保守侧），不是更松。

**边界执行（不是靠自觉）**：巡检结论**不接受**模型输出改写。
命中记录 `Hit` 本身是 frozen dataclass、字段全是 tuple，模型没有任何路径能改它；
本模块另在归因返回前**再核一次**：命中的规范化形态与进循环之前逐字不同 → 抛
`InsightBoundaryError`。确定性不被随机性污染（D-15）这件事因此有一个可打红的落点。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agenerp.explain import ExplainResult, explain
from agenerp.inspection.engine import Hit, InspectionReport
from agenerp.tools.runtime import Executor

# 归因是「解释这条命中」，不是「顺链条追单据」，因此走 `explain` 档而不是 `lineage`。
TASK_CLASS = "explain"

QUESTION_PREFIX = "巡检器按规则"


class InsightBoundaryError(RuntimeError):
    """模型输出被用来改写巡检结论 —— 越界即抛，不静默采纳。"""


def _canonical(hit: Hit) -> str:
    return json.dumps(hit.as_dict(), ensure_ascii=False, sort_keys=True)


def ensure_unchanged(before: str, hit: Hit) -> None:
    """边界执行：归因交出去之前，命中记录必须与进循环之前**逐字相同**。

    `Hit` 是 frozen dataclass、字段全是 tuple，所以正常路径上这一条永远成立；
    它存在是为了给「模型输出被用来改写命中记录」这件事一个**可打红的落点** ——
    没有落点的边界只是一句话（D-15：确定性不被随机性污染）。
    """
    if _canonical(hit) != before:
        raise InsightBoundaryError(
            "巡检结论在归因过程中被改写了 —— 确定性不许被模型的随机性污染（D-15）。"
            f"进循环之前：{before}；出来之后：{_canonical(hit)}"
        )


def question_for(hit: Hit) -> str:
    """把一条命中变成一个问题。**命中记录逐字进问题**，包括那个算出来的数 ——
    归因要解释的正是它，含糊掉就没得解释了。"""
    subject = "、".join(f"{field} = {value}" for field, value in hit.subject)
    return (
        f"{QUESTION_PREFIX} {hit.rule_id} 报出一条命中：{hit.statement}。"
        f"落点是 {subject}，{hit.quantity_name} = {hit.quantity:g}。"
        "请解释：为什么会这样？要不要紧？作答前先把证据查全，不要猜。"
    )


@dataclass(frozen=True)
class Attribution:
    """一条命中的归因。**命中记录与归因文本一起落盘，取证轨迹可回放。**

    `hit` 是巡检器给的那一条，**逐字不变**；`answer` 是模型说的话。
    两者在同一个对象里但**不混**：`accepted` 为假时 `answer` 是空的（门禁没放行），
    而 `hit` 照样在 —— 巡检结论不因归因失败而消失。
    """

    hit: Hit
    question: str
    answer: str
    accepted: bool
    result: ExplainResult

    @property
    def trace(self) -> dict[str, Any]:
        return self.result.trace.as_dict()

    def as_dict(self) -> dict[str, Any]:
        return {
            "hit": self.hit.as_dict(),
            "question": self.question,
            "answer": self.answer,
            "accepted": self.accepted,
            "trace": self.trace,
        }


def attribute(
    hit: Hit,
    *,
    client,
    models,
    requested: str | None = None,
    config=None,
    transport=None,
    doctypes: Sequence[str] | None = None,
    session_id: str = "insight",
    user: str = "",
    max_turns: int | None = None,
    executors: Mapping[str, Executor] | None = None,
) -> Attribution:
    """给一条命中做归因。**取证与门禁全部沿用 P1.4 的循环，本模块不另起一条。**"""
    before = _canonical(hit)
    question = question_for(hit)
    kwargs: dict[str, Any] = {
        "task_class": TASK_CLASS,
        "client": client,
        "models": models,
        "requested": requested,
        "config": config,
        "transport": transport,
        "doctypes": None if doctypes is None else list(doctypes),
        "session_id": session_id,
        "user": user,
        "executors": executors,
    }
    if max_turns is not None:
        kwargs["max_turns"] = max_turns
    result = explain(question, **kwargs)

    attribution = Attribution(
        hit=hit,
        question=question,
        answer=result.answer,
        accepted=result.accepted,
        result=result,
    )
    ensure_unchanged(before, attribution.hit)
    return attribution


def attribute_all(
    report: InspectionReport, **kwargs: Any
) -> tuple[Attribution, ...]:
    """给一份巡检报告里的每条命中各做一次归因。**报告本身一个字不改。**"""
    return tuple(attribute(hit, **kwargs) for hit in report.hits)


def hits_unchanged(report: InspectionReport, attributions: Iterable[Attribution]) -> bool:
    """归因之后巡检报告是否逐字未变。判据侧与调用方都用它，不各写一遍比较。"""
    return [_canonical(hit) for hit in report.hits] == [
        _canonical(item.hit) for item in attributions
    ]
