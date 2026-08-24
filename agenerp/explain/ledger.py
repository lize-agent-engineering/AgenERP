"""单次解释的**成本账本** —— 一次模型调用一条记录，一次解释一份汇总（P1.7 / D-18）。

落点节是 `docs/architecture/module-boundaries.md` §7.11。

**记账，不拦截。** D-18 逐字把 P1.7 从「单次解释成本上限」改成「单次解释成本记账」，
所以本模块里**没有任何阈值、没有任何「超了就……」的分支**。将来要设限，先用这里记下的账
定阈值 —— 先有数据，再谈阈值。

**四项 token 的口径归 P1.1，本模块一个字不重定**（`agenerp/routing/adapter.py` 的 `Usage`）：
`reasoning` 是 `completion` 的细分、`cached` 是 `prompt` 的细分，两者都不是新的桶，
`total = prompt + completion`（`cached` **不进 `total`**）。
汇总走 `Usage.plus()`，**不自己写四项加法** —— 自己写就会与 P1.1 分家。

⚠️ **每条记录同时留两组数，不许合并**：

- `usage` 是**解析后的** `Usage`（由 `agenerp.routing.adapter.usage_of()` 产出，本模块不另写解析）；
- `endpoint_total` / `endpoint_reasoning` / `endpoint_cached` 是**端点自报的原始数字**
  （`total_tokens` · `completion_tokens_details.reasoning_tokens` ·
  `prompt_tokens_details.cached_tokens`）。

分开留的理由是**判据强度**：`prompt + completion == total` 这种写法是恒真的
（`docs/evidence/p1-explain/README.md` 逐字），判它等于没判。只有拿解析后的数去对
**端点自己报的那个数**，「只记 completion 不记 reasoning」「把 reasoning 再加一遍」
这两类假实现才打得红。形状照抄 `docs/evidence/p1-explain/live-run-01.json` 的
`per_call_ledger[]` —— 那是 P1.4 一次性脚本的产物，本模块把它变成产品制品。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agenerp.routing.adapter import Reply, Usage, usage_of
from agenerp.routing.errors import RoutingError

# 这次调用的出口形态。**四条循环出口映射到这三种**：`answered` 落 `CALL_ANSWER`，
# `max-turns` / `permission-breaker` / 失控闸落在最后一次 `CALL_TOOLS` 上，
# `model-error` 落 `CALL_ERROR`。
CALL_TOOLS = "tools"
CALL_ANSWER = "answer"
CALL_ERROR = "model-error"


def _endpoint_numbers(raw: dict | None) -> tuple[int | None, int | None, int | None]:
    """端点自报的 `total_tokens` / `reasoning_tokens` / `cached_tokens`。

    ⚠️ **缺失与 0 不是一回事**：整个 `usage` 都没有时这三个数全是 `None`（真的不知道）；
    `usage` 在而 `completion_tokens_details` 缺时 reasoning 记 **0**
    —— 那正是 `usage_of()` 的口径（缺失回 0，不回退成算进 completion），
    非推理模型的回包就是这个形状。

    `cached` **逐字沿用同一套口径**（D2）：`usage` 在而 `prompt_tokens_details` 缺时记 **0**
    —— 不做缓存的端点就是不报这个字段。两个对称字段用同一套缺失口径，
    读账的人不必记住哪个是哪个。
    ⚠️ 代价是 `0` 有两个含义（端点报了 0 命中 / 端点没报这个字段），
    **证据文件里必须把「端点是否报了 `prompt_tokens_details`」单独记一列**，
    不让它被 `0` 吃掉（落点节 §7.17 逐字登记）。
    """
    if not raw:
        return None, None, None
    details = raw.get("completion_tokens_details") or {}
    prompt_details = raw.get("prompt_tokens_details") or {}
    total = raw.get("total_tokens")
    reasoning = details.get("reasoning_tokens")
    cached = prompt_details.get("cached_tokens")
    return (
        int(total) if total is not None else None,
        int(reasoning) if reasoning is not None else 0,
        int(cached) if cached is not None else 0,
    )


@dataclass(frozen=True)
class CallEntry:
    """一次模型调用的账。**发生了就在账上** —— 包括抛错那一次。"""

    index: int
    model: str
    usage: Usage
    outcome: str
    endpoint_total: int | None = None
    endpoint_reasoning: int | None = None
    endpoint_cached: int | None = None
    detail: str = ""

    @property
    def total_matches_endpoint(self) -> bool:
        """解析后的 `total` 是否等于端点自报的 `total_tokens`。端点没报就是 `False`（不知道 ≠ 对得上）。"""
        return self.endpoint_total is not None and self.usage.total == self.endpoint_total

    @property
    def reasoning_matches_endpoint(self) -> bool:
        return (
            self.endpoint_reasoning is not None
            and self.usage.reasoning == self.endpoint_reasoning
        )

    @property
    def cached_matches_endpoint(self) -> bool:
        """形状**逐字对称**于上面那条：端点没报 ⇒ `False`（不知道 ≠ 对得上）。"""
        return (
            self.endpoint_cached is not None and self.usage.cached == self.endpoint_cached
        )

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "model": self.model,
            "outcome": self.outcome,
            "usage": self.usage.as_dict(),
            "endpoint_total_tokens": self.endpoint_total,
            "endpoint_reasoning_tokens": self.endpoint_reasoning,
            "endpoint_cached_tokens": self.endpoint_cached,
            "total_matches_endpoint": self.total_matches_endpoint,
            "reasoning_matches_endpoint": self.reasoning_matches_endpoint,
            "cached_matches_endpoint": self.cached_matches_endpoint,
            "detail": self.detail,
        }


@dataclass
class CallLedger:
    """一次解释的账本。**采集面只有一处**（`ExplainLoop.run()` 里那唯一一个
    `adapter.chat(...)` 调用点的紧后面），两份账必然漂移。"""

    entries: list[CallEntry] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def record_reply(self, index: int, reply: Reply) -> CallEntry:
        """回包成形的那一次。**四项事实全部从 `Reply` 上取**，一项都不由调用方声明
        —— 调用方能声明的东西就能声明错，而账本要的是「那次回包实际是什么」。"""
        return self._append(
            index=index,
            model=reply.model,
            usage=reply.usage,
            outcome=CALL_TOOLS if reply.tool_calls else CALL_ANSWER,
            raw_usage=(reply.raw or {}).get("usage"),
        )

    def record_error(self, index: int, model: str, error: RoutingError) -> CallEntry:
        """模型调用抛错的那一次。**照样在账上。**

        口径（落点节 §7.11 逐字登记）：**记一条 `outcome = model-error` 的记录**，
        端点确实回了包时（`RoutingError.usage` 非空，见 `agenerp/routing/errors.py`）
        记**真数**；连不上端点 / 配置不全那一类端点根本没回包，四项记 0、
        `endpoint_*` 记 `None`（**「不知道」不写成「对得上」**）。
        **不许悄悄不记** —— 不记就等于把一次真实花掉的 token 从账上抹掉，
        而 D-11 点名的推理模型「回两个字也烧约 195 reasoning token」正是走这条路径。
        """
        raw_usage = getattr(error, "usage", None)
        return self._append(
            index=index,
            model=model,
            usage=usage_of(raw_usage) if raw_usage else Usage(),
            outcome=CALL_ERROR,
            raw_usage=raw_usage,
            detail=str(error),
        )

    def _append(
        self,
        *,
        index: int,
        model: str,
        usage: Usage,
        outcome: str,
        raw_usage: dict | None,
        detail: str = "",
    ) -> CallEntry:
        endpoint_total, endpoint_reasoning, endpoint_cached = _endpoint_numbers(raw_usage)
        entry = CallEntry(
            index=index,
            model=model,
            usage=usage,
            outcome=outcome,
            endpoint_total=endpoint_total,
            endpoint_reasoning=endpoint_reasoning,
            endpoint_cached=endpoint_cached,
            detail=detail,
        )
        self.entries.append(entry)
        return entry

    @property
    def total(self) -> Usage:
        """本次解释的累计用量。**折叠形态**：从空 `Usage()` 起折 N 条 → 恰好 N 次 `plus()`。"""
        total = Usage()
        for entry in self.entries:
            total = total.plus(entry.usage)
        return total

    def as_dict(self) -> dict:
        return {
            "calls": len(self.entries),
            "total": self.total.as_dict(),
            "entries": [entry.as_dict() for entry in self.entries],
        }
