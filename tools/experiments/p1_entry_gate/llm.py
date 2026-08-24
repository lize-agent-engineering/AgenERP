"""DashScope（OpenAI 兼容面）的最小客户端 —— **实验设施，不是产品代码**。

放在 `tools/experiments/` 而不是 `agenerp/`：本目录下的东西为了跑一次实验而存在，
不承担产品的向后兼容义务。模型路由的产品形态是 P1.1，不是这里。

两条环境上的硬约束（不是猜的）：

- **必须显式给 CA 根证书**：本机 python.org 版 Python 3.12 没装系统 CA，
  依赖默认必报 `CERTIFICATE_VERIFY_FAILED`（D-11 的环境注记）。
- **key 只从环境读，绝不进 git、不进轨迹文件、不进日志**。
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import certifi

API_KEY_ENV = "DASHSCOPE_API_KEY"
BASE_URL_ENV = "DASHSCOPE_BASE_URL"

DEFAULT_TIMEOUT = 300


class LlmError(RuntimeError):
    """模型侧的一切失败：连不上、非 2xx、载荷不是 JSON、回包缺 choices。

    **不降级成空回答**：空回答与「模型选择不作答」长得一样，那会让一次 API 故障
    被记成一次真实的实验结果。
    """


@dataclass(frozen=True)
class Usage:
    """一次调用的 token 账。**三项分开记**——`qwen3.6-plus` 是推理模型，
    reasoning token 混进 completion 里的话，成本模型（P1.7）就没法算。"""

    prompt: int = 0
    completion: int = 0
    reasoning: int = 0

    @property
    def total(self) -> int:
        return self.prompt + self.completion

    def plus(self, other: Usage) -> Usage:
        return Usage(
            self.prompt + other.prompt,
            self.completion + other.completion,
            self.reasoning + other.reasoning,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "reasoning": self.reasoning,
            "total": self.total,
        }


@dataclass(frozen=True)
class Reply:
    """模型的一次回复：要么是若干次工具调用，要么是最终答案文本。"""

    text: str = ""
    tool_calls: tuple[dict, ...] = ()
    usage: Usage = field(default_factory=Usage)
    raw: dict = field(default_factory=dict, compare=False)


def _context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


class DashScopeClient:
    """OpenAI 兼容的 `/chat/completions`。传输可注入 —— 单测喂假模型，不打网络。"""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        transport=None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.model = model
        self._api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV, "").strip()
        self._base_url = (
            base_url or os.environ.get(BASE_URL_ENV, "").strip()
        ).rstrip("/")
        self._transport = transport
        self._timeout = timeout
        if self._transport is None and not self._api_key:
            raise LlmError(f"缺少模型凭据：设置 {API_KEY_ENV}（实验设施不内置 key 默认值）")
        if self._transport is None and not self._base_url:
            raise LlmError(f"缺少端点：设置 {BASE_URL_ENV}")

    def chat(self, messages: list[dict], tools: list[dict], max_tokens: int) -> Reply:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
        }
        body = self._send(payload)
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmError(f"回包里没有 choices：{json.dumps(body, ensure_ascii=False)[:300]}")
        message = choices[0].get("message") or {}
        return Reply(
            text=(message.get("content") or "").strip(),
            tool_calls=tuple(message.get("tool_calls") or ()),
            usage=_usage_of(body.get("usage") or {}),
            raw=body,
        )

    def _send(self, payload: dict) -> dict:
        if self._transport is not None:
            return self._transport(payload)
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout, context=_context()) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:  # 4xx/5xx：把站点原文带出来，不改写
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise LlmError(f"HTTP {exc.code}：{detail}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise LlmError(f"调模型失败：{exc}") from exc


def _usage_of(usage: dict) -> Usage:
    details = usage.get("completion_tokens_details") or {}
    return Usage(
        prompt=int(usage.get("prompt_tokens") or 0),
        completion=int(usage.get("completion_tokens") or 0),
        reasoning=int(details.get("reasoning_tokens") or 0),
    )
