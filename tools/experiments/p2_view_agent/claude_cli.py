"""把 `claude -p` 包成一个 OpenAI 兼容的 transport。**实验设施，不是产品代码。**

模块头这句话与 `tools/experiments/p1_entry_gate/llm.py` 同源，且这里更要紧：

🔴 **产品的 `agenerp/routing/config.py` 按 `model-management.md` §12.1 ①
不许出现厂商名、厂商端点、厂商 SDK。** 本文件走的是订阅制 CLI，
它**只能**住在实验设施里 —— 产品路径一行都不引它。

用它的理由是人 2026-08-28 定的：**开发期的量化评测走 Claude 订阅额度，不烧百炼。**
⚠️ **代价照实记**：这样拿到的数字与 P2.0R 那 57/60 = 95.0%（`deepseek-v4-pro-0813`）
**不可比**，也不代表百炼上任何模型的表现。引用本文件产出的数字时必须点名模型。

## 怎么骗过 `ChatAdapter`

`ChatAdapter._send` 把注入的 transport 与真网络**走同一段失败映射**，
所以这里只要接受一个 OpenAI 形状的 payload、回一个 OpenAI 形状的 body 就行。
`claude -p` 不吃 `tools` 参数 ⇒ 工具面在提示词里描述，并要求模型
**回一个严格的 JSON 信封**，本文件再把它翻译回 `tool_calls` / `content`。
"""

from __future__ import annotations

import json
import re
import subprocess

FENCE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)

ENVELOPE = """
你在扮演一个 OpenAI 兼容的 chat completions 端点。**只输出一个 JSON 对象，不要任何解释。**

两种形状二选一：
  调工具   {"tool_calls": [{"name": "<工具名>", "arguments": {<参数>}}]}
  出文本   {"content": "<文本>"}

可用工具（`parameters` 是 JSON Schema，照它的形状填 `arguments`）：
%s

以下是对话历史，最后一条之后轮到你：
%s
""".strip()


class ClaudeCliTransport:
    """一次调用 = 一次 `claude -p` 子进程。**每次调用逐条留痕。**"""

    def __init__(self, model: str = "sonnet", timeout: int = 300) -> None:
        self.model = model
        self.timeout = timeout
        self.calls: list[dict] = []

    def __call__(self, payload: dict) -> dict:
        prompt = ENVELOPE % (
            json.dumps(payload.get("tools") or [], ensure_ascii=False, indent=1),
            _render(payload.get("messages") or []),
        )
        raw = self._run(prompt)
        envelope = _parse(raw["result"])
        usage = raw.get("usage") or {}
        self.calls.append({"cost_usd": raw.get("total_cost_usd"), "usage": usage})
        return _openai_body(envelope, usage)

    def _run(self, prompt: str) -> dict:
        proc = subprocess.run(
            ["claude", "-p", "--model", self.model, "--output-format", "json",
             "--allowed-tools", ""],
            input=prompt, capture_output=True, text=True, timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p 退 {proc.returncode}：{proc.stderr[:300]}")
        return json.loads(proc.stdout)


def _render(messages: list[dict]) -> str:
    lines = []
    for message in messages:
        role = message.get("role")
        if role == "assistant" and message.get("tool_calls"):
            body = json.dumps(
                [
                    {"name": c["function"]["name"], "arguments": c["function"]["arguments"]}
                    for c in message["tool_calls"]
                ],
                ensure_ascii=False,
            )
            lines.append(f"[assistant 调了工具] {body}")
            continue
        lines.append(f"[{role}] {message.get('content') or ''}")
    return "\n\n".join(lines)


def _parse(text: str) -> dict:
    """把回来的东西读成信封。**读不成就明确报错，不静默当成空回答** ——
    静默会让「模型没按格式答」在结果里长得像「模型答不出来」。"""
    candidate = (text or "").strip()
    fenced = FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        envelope = json.loads(candidate)
    except ValueError as exc:
        raise RuntimeError(f"信封不是 JSON：{exc}；原文前 200 字：{text[:200]!r}") from exc
    if not isinstance(envelope, dict):
        raise RuntimeError(f"信封不是对象：{type(envelope).__name__}")
    return envelope


def _openai_body(envelope: dict, usage: dict) -> dict:
    calls = envelope.get("tool_calls") or []
    message: dict = {"role": "assistant", "content": envelope.get("content")}
    if calls:
        message["content"] = None
        message["tool_calls"] = [
            {
                "id": f"call-{index}",
                "type": "function",
                "function": {
                    "name": call.get("name", ""),
                    "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
                },
            }
            for index, call in enumerate(calls)
        ]
    return {
        "choices": [
            {
                "message": message,
                "finish_reason": "tool_calls" if calls else "stop",
            }
        ],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "completion_tokens_details": {
                "reasoning_tokens": (usage.get("output_tokens_details") or {}).get(
                    "thinking_tokens", 0
                )
            },
        },
    }
