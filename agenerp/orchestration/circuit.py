"""§7.4 的权限拒绝熔断 —— 连续 N 次权限拒绝即终止工具调用循环。

owner doc 是 `docs/architecture/module-boundaries.md` §7.4（Spike 01 探针 3 实测：
受限身份问毛利，工具调用从约 7 次放大到 **35 次**，模型在系统性寻找绕过路径）。
它是**确定性规则**（连续计数 + 阈值 + 固定文案），按 D-15 不许 Agent 化。

**拒绝的识别口径沿用已实测的那一条**：`agenerp/tools/site_scope.py` 的
`doctypes_with_data` 逐字「**只有 HTTP 403 被判成『这个身份读不到』**」，
其余任何失败照旧抛出去。**站点宕机 / 超时 / 5xx 不计进熔断计数** ——
那会把「站点坏了」读成「你没权限」。

⚠️ 那段判定**内联在 `doctypes_with_data` 里**，今天不是一个可复用件，而
`permission_scope` 自己根本不分类 403。因此本模块**独立实现一次**，并由
`tests/tools/test_navigation.py` 拿 `FakeSite` 驱动 `doctypes_with_data` 取**行为**作基准，
断言两处对同样两种输入给出相同的分类。**残余风险**：两处口径靠一条断言绑定，
有人只改一处且顺手改断言就会漂移 —— 靠人复核兜。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agenerp.site import SiteError
from agenerp.tools.runtime import ToolResult

# §7.4 表里的建议值。**连续**，不是累计。
DENIAL_THRESHOLD = 5

# 判定用的那一串。`agenerp/site.py` 把非 2xx 收敛成 `... → HTTP {status} ...`，
# `site_scope.py` 判的就是这同一串（`"HTTP 403" not in str(exc)`）。
FORBIDDEN_MARKER = "HTTP 403"

BREAKER_MESSAGE = "你的权限不足以回答这个问题"


def is_permission_denial(failure: Any) -> bool:
    """这次失败是不是「这个身份读不到」。**只有 HTTP 403 算**。

    站点宕机、超时、5xx 一律**不算** —— 把它们计进熔断计数，等于让一次站点故障
    看起来像一次越权探测。
    """
    if isinstance(failure, SiteError):
        return FORBIDDEN_MARKER in str(failure)
    return False


def result_is_permission_denial(result: ToolResult) -> bool:
    """`execute` 把 `SiteError` 收敛成了 `ok=False` + 原文进 `reasons`（不改写），
    所以从 `ToolResult` 这一侧同样判得出来 —— 判的是同一串。"""
    if result.ok:
        return False
    return any(FORBIDDEN_MARKER in reason for reason in result.reasons)


@dataclass(frozen=True)
class BreakerReport:
    """刹车时给用户的东西：固定文案 + **所需权限清单**（§7.4 第二行）。"""

    message: str
    required_permissions: tuple[str, ...]

    def text(self) -> str:
        return f"{self.message}。所需权限：" + "、".join(self.required_permissions)


@dataclass
class DenialBreaker:
    """单次会话内**连续** N 次权限拒绝即刹车。

    **「连续」不是「累计」**：中间成功一次即清零。累计版会把正常会话误刹 ——
    一个跑了两小时、零星撞过 5 次权限边界的会话与一次越权探测长得完全不一样。

    **非 403 的失败既不计数、也不清零**：站点宕机不是越权证据，也不是「这次访问合法」
    的证据。把它当清零处理，等于给「每两次 403 之间制造一次超时」留了一条绕过路径。
    """

    threshold: int = DENIAL_THRESHOLD
    streak: int = 0
    denied: tuple[str, ...] = ()
    _order: list[str] = field(default_factory=list, repr=False)

    @property
    def tripped(self) -> bool:
        return self.streak >= self.threshold

    def record(self, result: ToolResult, *, doctype: str = "") -> bool:
        """记一次工具执行结果，回「是否已刹车」。"""
        if result_is_permission_denial(result):
            return self._deny(doctype)
        if result.ok:
            self.streak = 0
            return self.tripped
        return self.tripped  # 非 403 的失败：不计数、不清零

    def record_failure(self, failure: Any, *, doctype: str = "") -> bool:
        """同上，但收的是异常（`SiteError`）而不是 `ToolResult`。"""
        if is_permission_denial(failure):
            return self._deny(doctype)
        return self.tripped

    def record_success(self) -> bool:
        self.streak = 0
        return self.tripped

    def _deny(self, doctype: str) -> bool:
        self.streak += 1
        if doctype and doctype not in self._order:
            self._order.append(doctype)
            self.denied = tuple(self._order)
        return self.tripped

    def report(self) -> BreakerReport:
        """刹车文案 + 所需权限清单。**清单指名 DocType**，不是一句「权限不足」了事。"""
        return BreakerReport(
            message=BREAKER_MESSAGE,
            required_permissions=tuple(f"read:{doctype}" for doctype in self.denied),
        )
