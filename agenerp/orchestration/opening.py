"""会话开场装配器 —— 在模型看到第一条消息之前，**先把可见范围摆出来**。

owner doc 是 `docs/design/agents-and-roles.md` §5.1：`permission.scope`「由控制循环在
会话开场自动注入，不依赖模型想起来调用」。落点节在
`docs/architecture/module-boundaries.md` §7.6a。

**两段机制，语义不同，不许混为一谈**（plan `2026-08-24-1601-2` §1.1a）：

| | 事实的含义 | 谁给 | 可验性 |
|---|---|---|---|
| 契约面 `injected_at_session_start` | 「本次调用是编排面在会话开场发起的」 | **调用方自证** | 弱 |
| 开场包面 `opening_injection_verified` | 「注入这件事真的发生过」 | 从 `ToolResult` **推导** | 强 |

契约面那条是 `agenerp/tools_readonly.py` 的 `PERMISSION_SCOPE` 第二条后置断言。
`agenerp/tools/runtime.py` 的事实合并是 `{**caller_facts, **outcome.facts}`，而
`agenerp/contracts.py` 的 `Condition.evaluate` 在事实缺席时直接判否 —— 因此装配器
**必须**把它交进 `ReadOnlyContext`，否则 `execute` 必然在 `postconditions` 上 abort。
**这一段本模块不宣称被加强**：绕过本模块直接调 `execute` 的人照样能把它填成 `True`。

强度放在开场包面：`opening_injection_verified` 由 `_verified()` 从注入记录推出来，
**调用方传进来的任何同名值一律不进开场包**。判据（含「只写标志不真注入」的反测）在
`tests/tools/test_navigation.py`。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from agenerp.context.immediate import ImmediateContext
from agenerp.context.session import ConversationSession, ExecutedAction
from agenerp.contracts import ReadOnlyContext
from agenerp.site import SiteClient
from agenerp.tools.runtime import Executor, ToolResult, execute

INJECTION_TOOL = "permission.scope"

# 契约面那条：调用方自证，**必须**交进 `ReadOnlyContext`，否则契约在后置上 abort。
CONTRACT_FACT = "injected_at_session_start"

# 开场包面那条：从注入记录推导，**与契约那条不同名**，防止两者被读成同一件事。
PACK_FACT = "opening_injection_verified"

# 执行体推出来的事实里，开场包原样带走的那些。**白名单而不是黑名单**：
# `ToolResult.facts` 是 `{**caller_facts, **outcome.facts}`，黑名单会把调用方
# 塞进来的任意事实一起放行，开场包就又变成了「调用方说了算」。
EXECUTOR_FACTS: tuple[str, ...] = ("permission_probe_method",)


@dataclass(frozen=True)
class InjectionCost:
    """开场注入烧掉的代价。**记下来是为了让它可被断言** —— 「自动注入」若不记账，
    就会变成一个每次会话烧几百次站点请求的隐性成本。

    `candidate_count` 为 `None` 表示走的是**发现式路径**：候选集由执行体在站点上
    枚举出来，装配器数不出它有多少个（受限身份枚举不出 DocType 清单，见
    `module-boundaries.md` §7.6 限制 1，因此候选集通常由调用方给）。
    """

    request_count: int
    candidate_count: int | None


@dataclass(frozen=True)
class OpeningPack:
    """摆到模型面前的开场包：注入产物 + 由记录推导的事实 + 注入代价（+ ① 即时上下文）。

    `facts[PACK_FACT]` 是本层的判定面。**它不是调用方交进来的** —— 见模块头两段机制。
    """

    result: ToolResult | None = None
    scope: tuple[Mapping[str, Any], ...] = ()
    cost: InjectionCost = InjectionCost(0, None)
    facts: Mapping[str, Any] = field(default_factory=dict)
    immediate: ImmediateContext | None = None
    session: ConversationSession | None = None
    execute_calls: int = 0

    @property
    def injection_verified(self) -> bool:
        return bool(self.facts.get(PACK_FACT))

    def readable(self, doctype: str) -> bool | None:
        """该 DocType 读得到读不到。**`None` 表示开场包答不上来**，与「读不到」分开。

        混成一件事正是 §5.0 ① 要挡的错误：「没查」与「查了没有」在下游长得一样时，
        导航策略会把「我不知道」当成「不可读」而提前拒答。
        """
        for row in self.scope:
            if row.get("doctype") == doctype:
                return bool(row.get("can_read"))
        return None


def _rows(result: ToolResult | None) -> tuple[Mapping[str, Any], ...]:
    if result is None or not isinstance(result.data, list):
        return ()
    return tuple(row for row in result.data if isinstance(row, Mapping))


def _verified(result: ToolResult | None, rows: Sequence[Mapping[str, Any]]) -> bool:
    """开场包面那条事实的**推导判据，写死在代码里**。

    五条缺一不可：注入产物存在 · 是 `permission.scope` 的产物 · `ok is True` ·
    真的发过站点请求 · 产物里含 `can_read` 行。
    去掉其中任何一条，「只写标志不真注入」就能蒙混过去（反测 A / 变异 M1）。
    """
    return (
        result is not None
        and result.tool == INJECTION_TOOL
        and result.ok is True
        and result.request_count > 0
        and bool(rows)
        and all("can_read" in row for row in rows)
    )


def open_session(
    *,
    client: SiteClient,
    doctypes: Sequence[str] | None = None,
    facts: Mapping[str, Any] | None = None,
    immediate: ImmediateContext | None = None,
    session: ConversationSession | None = None,
    executors: Mapping[str, Executor] | None = None,
) -> OpeningPack:
    """会话开场：**在任何模型消息之前**执行一次 `permission.scope`，产物摆进开场包。

    `doctypes` 是候选集，**允许由调用方给**：stock Frappe 只把 `DocType` 的读权限给
    System Manager / Administrator，受限身份因此枚举不出 DocType 清单
    （`module-boundaries.md` §7.6 限制 1）。**不靠给身份提权走发现式路径** ——
    那等于把「受限」这件事取消掉。给了候选集就**只探候选集**，一个元数据枚举请求都不发。
    """
    params: dict[str, Any] = {}
    candidate_count: int | None = None
    if doctypes is not None:
        candidates = [str(name) for name in doctypes]
        params["doctypes"] = candidates
        candidate_count = len(candidates)

    caller_facts = {k: v for k, v in dict(facts or {}).items() if k != PACK_FACT}
    result = execute(
        INJECTION_TOOL,
        params,
        client=client,
        context=ReadOnlyContext({**caller_facts, CONTRACT_FACT: True}),
        executors=executors,
    )

    rows = _rows(result)
    pack_facts: dict[str, Any] = {PACK_FACT: _verified(result, rows)}
    for name in EXECUTOR_FACTS:
        if name in result.facts:
            pack_facts[name] = result.facts[name]

    return OpeningPack(
        result=result,
        scope=rows,
        cost=InjectionCost(result.request_count, candidate_count),
        facts=pack_facts,
        immediate=immediate,
        session=_record(session, params, result),
        execute_calls=1,
    )


def _record(
    session: ConversationSession | None, params: Mapping[str, Any], result: ToolResult
) -> ConversationSession | None:
    """把注入记进 ② 对话会话的**已执行动作**档（§8.2 规则 ②：审计记录不可压缩）。

    走 `ConversationSession.with_action`，不自己拼一条记录 —— 第二套记法会与 P1.2 漂移。
    """
    if session is None:
        return None
    return session.with_action(
        ExecutedAction(
            tool=INJECTION_TOOL,
            params=dict(params),
            request_count=result.request_count,
            diff_summary=f"开场注入 · ok={result.ok}",
        )
    )
