"""P3.0 用的模型客户端 —— 在 P1.0 那份之上**只加一件事**：透传 `extra_body`。

**不去改 `tools/experiments/p1_entry_gate/llm.py`**：那份是另一个实验的判据面
（`tests/experiments/test_entry_gate_loop.py` 在断它），为跑本实验去动它，
等于让一次新实验的方便改掉一份已交付实验的行为。子类是更便宜的形态。

## 为什么要 `enable_thinking: false`

人 2026-08-24 的记账口径：**它是预算前提，差约 450 倍**。
本实验一次要跑 2 模型 × 4 格 × 3 次 = 24 轮多轮对话，
放任 reasoning token 的话这笔账的量级完全不同。

⚠️ **它不一定被每个模型接受**：`enable_thinking` 是通义系的参数，
`glm-5.2` / `kimi-k3` 是百炼上的第三方模型。所以这里做的是**试探 + 照实降级**：
被 4xx 拒了就去掉该参数重发一次，**并把「这一轮没能关掉 thinking」记进轨迹** ——
静默降级会让「关掉了」与「关不掉」在账本上长得一样。
"""

from __future__ import annotations

from tools.experiments.p1_entry_gate.llm import DashScopeClient, LlmError, Reply


# 只有**这一类**错误才说明「这个模型不认 enable_thinking」。
# 认证 / 配额 / 限流一律不属于它 —— 那些是「没跑成」，不是「参数不对」。
_PARAMETER_REJECTION_MARKERS = (
    "enable_thinking",
    "unsupported parameter",
    "invalid_parameter",
    "InvalidParameter",
)
_NOT_PARAMETER_MARKERS = ("HTTP 401", "HTTP 403", "HTTP 429", "Quota", "quota")


def _looks_like_parameter_rejection(exc: Exception) -> bool:
    text = str(exc)
    if any(marker in text for marker in _NOT_PARAMETER_MARKERS):
        return False
    return "HTTP 400" in text or any(m in text for m in _PARAMETER_REJECTION_MARKERS)


class ThinkingOffClient(DashScopeClient):
    """带 `enable_thinking: false` 的客户端，被拒即照实降级并留痕。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.thinking_disabled: bool | None = None
        self.downgrade_reason: str = ""

    def chat(self, messages: list[dict], tools: list[dict], max_tokens: int) -> Reply:
        if self.thinking_disabled is False:
            return super().chat(messages, tools, max_tokens)
        try:
            reply = self._chat_with_extra(messages, tools, max_tokens)
        except LlmError as exc:
            if self.thinking_disabled is True or not _looks_like_parameter_rejection(exc):
                # 🔴 **只对「这个参数不认」降级。** 2026-08-29 实测踩到的：
                # 配额耗尽回的是 HTTP 403 `AllocationQuota.FreeTierOnly`，
                # 原实现把它一并当成「参数被拒」⇒ 每次调用白白重发一次、
                # 并把 `thinking_disabled` 记成 `False`，而真相是**它压根没跑**。
                # 那正是「不伪装成功」要挡的形状：把 A 类故障记成 B 类事实。
                raise
            self.thinking_disabled = False
            self.downgrade_reason = str(exc)[:300]
            return super().chat(messages, tools, max_tokens)
        self.thinking_disabled = True
        return reply

    def _chat_with_extra(self, messages, tools, max_tokens) -> Reply:
        import json

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
            "enable_thinking": False,
        }
        body = self._send(payload)  # noqa: SLF001 —— 子类用父类的传输，不另开一条
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmError(f"回包里没有 choices：{json.dumps(body, ensure_ascii=False)[:300]}")
        message = choices[0].get("message") or {}
        from tools.experiments.p1_entry_gate.llm import _usage_of

        return Reply(
            text=(message.get("content") or "").strip(),
            tool_calls=tuple(message.get("tool_calls") or ()),
            usage=_usage_of(body.get("usage") or {}),
            raw=body,
        )
