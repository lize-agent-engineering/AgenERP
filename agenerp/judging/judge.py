"""判一段答案：**一次调用、一个标签、一条账**。落点节 `docs/architecture/module-boundaries.md` §7.15。

## 三条不许绕的规矩

1. **一律走 `route()`。** 本模块不 import、不构造 `ChatAdapter` ——
   `STATE.md` §3 `[open] 2026-08-24T08:12Z`（F8：`ChatAdapter` 可被直接构造绕过能力校验）
   那条路不在本包重现。判据是对本包做 AST 扫描（plan 变异 M6）。
2. **标签必须是模型回包的函数。** `judge_one()` 自己**不看答案文本的内容**去凑标签 ——
   它只把文本包进 `messages`、把回包交给 `rubric.parse_label()`。
   判据是「同一段答案配两份不同的假回包 ⇒ 两个不同的标签」（plan §6 H7 ③，变异 M9 / M9b）。
3. **一次 `chat()` 一条账。** 成功记 `record_reply`，抛错记 `record_error` **再抛出去** ——
   端点回过包就等于 token 已经真的花掉（P1.7 / D-18：记账不拦截，**本模块没有任何阈值**）。

## 签名为什么长这样

`judge_one(answer: str, *, ...)` 的第一个形参**只收一段文本**，其余全是关键字形参，
且**没有任何一个能承载被判那一行的 `label` / `reason`**（plan §6 H7 ①）。
这比"扫一遍实现里有没有读 label"强：AST 的作用域是实现者自己选的，签名不是。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agenerp.explain.ledger import CallLedger
from agenerp.judging.rubric import build_messages, parse_label
from agenerp.routing import route
from agenerp.routing.adapter import Usage
from agenerp.routing.errors import RoutingError

# 判定是一次**无工具的单轮**调用，输出只有一个 JSON 对象。给的额度足够推理模型
# 把 reasoning 烧完还剩下那几十个字 —— 太小会把一次正常判定截成 `length` 空回答。
DEFAULT_JUDGE_MAX_TOKENS = 2048

JUDGE_TASK_CLASS = "explain"


@dataclass(frozen=True)
class Verdict:
    """一次判定的结果。**四项事实全部来自那次回包**，一项都不由调用方声明。"""

    label: str
    raw_text: str
    usage: Usage
    model: str
    endpoint_usage: dict = field(default_factory=dict, compare=False)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "model": self.model,
            "usage": self.usage.as_dict(),
            "endpoint_usage": self.endpoint_usage,
            "raw_text": self.raw_text,
        }


def judge_one(
    answer: str,
    *,
    models,
    requested: str | None = None,
    config=None,
    transport=None,
    ledger: CallLedger | None = None,
    index: int = 0,
    max_tokens: int = DEFAULT_JUDGE_MAX_TOKENS,
) -> Verdict:
    """判一段答案文本，回一个 `Verdict`。

    ⚠️ 形参里**没有** `label` / `reason` / 行对象 —— 见模块头「签名为什么长这样」。
    """
    adapter = route(
        JUDGE_TASK_CLASS,
        models=models,
        requested=requested,
        config=config,
        transport=transport,
    )
    messages = build_messages(answer)
    try:
        reply = adapter.chat(messages, max_tokens=max_tokens)
    except RoutingError as exc:
        if ledger is not None:
            ledger.record_error(index, adapter.model, exc)
        raise
    if ledger is not None:
        ledger.record_reply(index, reply)
    return Verdict(
        label=parse_label(reply.text),
        raw_text=reply.text,
        usage=reply.usage,
        model=reply.model,
        endpoint_usage=dict((reply.raw or {}).get("usage") or {}),
    )
