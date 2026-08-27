"""OpenAI 兼容的 chat 适配面。

形状继承 `tools/experiments/p1_entry_gate/llm.py` 已解决掉的四件事（**继承形状，不复制文件**
—— 那个文件是 P1.0 的判定证据，一行不动）：

1. OpenAI 兼容 `/chat/completions`，`model` / `messages` / `tools` / `max_tokens` 四件套；
2. **transport 可注入** —— 单测喂假模型，不打网络；
3. **token 四项分开记**（`prompt` / `completion` / `reasoning` / `cached`）——
   推理模型回两个字也烧 reasoning token（D-11：`qwen3.6-plus` 约 195），
   混进 `completion` 里成本模型（P1.7）就没法算；`cached` 是**对称的另一半**
   （端点自报的 prompt 侧细分），一次多轮解释里 prompt 能占九成，
   折掉它就分辨不出那九成里哪些是命中缓存的便宜 token；
4. **失败不降级成空回答** —— 一切失败抛 `RoutingError`。空回答与"模型选择不作答"
   长得一样，降级会把一次 API 故障记成一次真实结果。

**certifi 是惰性 import。** CI 的 `unit-and-contracts` job 只 `pip install pytest`
（`.github/workflows/gates.yml`），模块级 `import certifi` 会让 CI 当场 ImportError；
而 D-11 的环境注记又要求产品代码显式给 CA 根证书。两条同时成立的唯一摆法就是：
`import certifi` 只出现在真正构造 SSL 上下文的函数体内。判据见
`tests/routing/test_adapter.py` 的 CI 依赖面反测（AST + 全新解释器两道）。
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field

from agenerp.routing.capabilities import ModelProfile
from agenerp.routing.config import LlmConfig
from agenerp.routing.errors import RoutingError

DEFAULT_TIMEOUT = 300
DEFAULT_MAX_TOKENS = 2048


@dataclass(frozen=True)
class Usage:
    """一次调用的 token 账。

    **`reasoning` 是 `completion` 的一个细分，不是第四个桶** —— 2026-08-24 对活端点
    实读的回包逐字如此：`{"prompt_tokens": 15, "completion_tokens": 178,
    "total_tokens": 193, "completion_tokens_details": {"reasoning_tokens": 173}}`，
    `15 + 178 = 193` 对得上，`reasoning` 落在 `completion` 里面。
    所以 `total` 是 `prompt + completion`（与端点自报的 `total_tokens` 一致），
    **绝不再把 reasoning 加一遍**。

    分开记的理由不是"加总",是**留住这个细分**：推理模型回两个字也能烧掉九成的
    completion（上面那次 178 里有 173 是 reasoning），reasoning 与可见输出常常不同价，
    折掉这一位，P1.7 的**成本账**就只能按"输出 178 token"去算，差一个量级
    （D-18：P1.7 是**记账**不是设上限；账记错了将来连阈值都没法定）。

    **`cached` 是 `prompt` 的一个细分，不是第五个桶** —— 与上面那句 `reasoning` 的话
    形状完全对称，只是发生在 prompt 侧：端点回包里
    `prompt_tokens_details.cached_tokens` 与 `completion_tokens_details.reasoning_tokens`
    是同一形状的两个细分。所以 `total` 仍是 `prompt + completion`，
    **`cached` 绝不进 `total`** —— 它是 `prompt` 的子集，加进去当场与端点自报的
    `total_tokens` 对不上。分开记的理由同样不是"加总"，是**留住这个细分**：
    命中前缀缓存的 prompt token 与未命中的在多数计费口径下不同价，
    折掉这一位，占一次解释九成的那一栏就分辨不出贵与便宜。"""

    prompt: int = 0
    completion: int = 0
    reasoning: int = 0
    cached: int = 0

    @property
    def total(self) -> int:
        return self.prompt + self.completion

    def plus(self, other: Usage) -> Usage:
        return Usage(
            self.prompt + other.prompt,
            self.completion + other.completion,
            self.reasoning + other.reasoning,
            self.cached + other.cached,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt": self.prompt,
            "completion": self.completion,
            "reasoning": self.reasoning,
            "cached": self.cached,
            "total": self.total,
        }


@dataclass(frozen=True)
class Reply:
    """模型的一次回复：要么是若干次工具调用，要么是最终答案文本。"""

    text: str = ""
    tool_calls: tuple[dict, ...] = ()
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    raw: dict = field(default_factory=dict, compare=False)


def _ssl_context() -> ssl.SSLContext:
    """**唯一** import certifi 的地方，且在函数体内（见模块头）。"""
    import certifi

    return ssl.create_default_context(cafile=certifi.where())


# 🔴 **产品默认：关掉思考。** 人 2026-08-27 裁定「关思考 + 保持 4096」。
#
# 依据是实测，两条缺一不可：
#   (a) 不关时 `glm-5.2` 做难题会把**整个输出预算**烧在 reasoning 上 ——
#       实测 `completion=16385 / reasoning=16384`（上限已从 4096 提到 16384），
#       回包 `finish_reason='length'`、**一个字都没吐**。
#       把上限调大不解决：它只是想得更多。
#   (b) 关掉之后同一条题实测 reasoning **每次调用都是 0**，截断消失。
# ⇒ 「关思考」与「保持 `PER_CALL_OUTPUT_TOKENS = 4096`」是**绑在一起的一个决定**：
#    关了，4096 够用；不关，4096 必须提高。**只做一半都不行。**
#
# ⚠️ **它不在 OpenAI 兼容的四件套里**（`model`/`messages`/`tools`/`max_tokens`），
#    是百炼一侧的扩展。§12.1 ① 要求「默认不指向任何商业 API」，而本常量确实
#    把一个厂商扩展写进了默认路径 —— **这是那条要求上的一处让步，照实记。**
#    逃生口是构造参数：**换到不认这个键的端点时，`ChatAdapter(..., enable_thinking=None)`
#    就一个字节都不发**，行为回到本常量出现之前。
#    不加第四个环境变量：`config.py` 的抬头逐字是「三个变量，一个默认值都没有」。
DEFAULT_ENABLE_THINKING: bool | None = False


class ChatAdapter:
    """绑定到一个具体模型的调用面。`route()` 返回的就是它。

    `profile` 是这个模型的能力档案。adapter **自己不做能力校验** ——
    校验是 `router.route()` 的职责，放两处会出现"一处松一处紧"。
    档案带在身上是为了让调用方（P1.7 的成本面）能读到 `is_reasoning_model`。

    ⚠️ **`enable_thinking` 2026-08-27 加入，同日由人裁定默认改成 `False`（关思考）。**
    这**改变了产品行为**：从「不发送、随模型默认」变成「显式关」。理由是实测：`glm-5.2` 的思考默认开着，
    做难题时会把整个输出预算烧在 reasoning 上 ——
    实测 `completion=16385 / reasoning=16384`（上限已放到 16384），
    回包 `finish_reason='length'`、**一个字都没吐**。把上限从 4096 提到 16384 没解决，
    它只是想得更多 ⇒ **要试的是关掉思考，不是继续加预算。**

    ⚠️ 它**不在 OpenAI 兼容的四件套里**（`model`/`messages`/`tools`/`max_tokens`），
    是百炼一侧的扩展。不是所有端点都认 ⇒ 默认不发，
    由调用方在**知道自己在跟谁说话**的时候显式给。
    """

    def __init__(
        self,
        config: LlmConfig,
        *,
        model: str | None = None,
        profile: ModelProfile | None = None,
        enable_thinking: bool | None = DEFAULT_ENABLE_THINKING,
        transport=None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = config
        self.model = model or config.model
        self.profile = profile
        self._enable_thinking = enable_thinking
        self._transport = transport
        self._timeout = timeout

    def __repr__(self) -> str:
        """**不含凭据。** `LlmConfig.api_key` 是 `repr=False`，这里也不另插值它。"""
        return f"ChatAdapter(model={self.model!r}, base_url={self._config.base_url!r})"

    def chat(
        self,
        messages: Sequence[dict],
        tools: Sequence[dict] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Reply:
        payload: dict = {
            "model": self.model,
            "messages": list(messages),
            "max_tokens": max_tokens,
        }
        # `tools` 只在给了的时候才进载荷。**这是取舍，不是实测**：空数组在各家兼容端点上的
        # 行为本仓没有逐一验证过，不发送是那个两边都成立的选择。
        if tools:
            payload["tools"] = list(tools)
        # `enable_thinking` 同理：**`None` 就一个字节都不发**，行为与本参数出现之前逐字相同。
        # 它不在 OpenAI 兼容的四件套里，是百炼一侧的扩展 —— 不是所有端点都认，
        # 所以默认不发，由调用方在**知道自己在跟谁说话**的时候显式给。
        if self._enable_thinking is not None:
            payload["enable_thinking"] = self._enable_thinking

        body = self._send(payload)
        # **端点已经回包 = token 已经真的花掉**，哪怕这个包不成形。下面三条失败路径
        # 因此都把端点自报的 usage 原样挂在异常上（P1.7 / D-18：一次调用都不许漏账）。
        # 不挂就等于把这次的 token 从账上抹掉 —— 详见 `agenerp/routing/errors.py`。
        endpoint_usage = body.get("usage") or None
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RoutingError(
                f"模型回包里没有 choices：{json.dumps(body, ensure_ascii=False)[:300]}",
                usage=endpoint_usage,
            )
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        if not isinstance(message, dict):
            raise RoutingError(
                f"模型回包的 choices[0] 里没有成形的 message："
                f"{json.dumps(body, ensure_ascii=False)[:300]}",
                usage=endpoint_usage,
            )

        text = (message.get("content") or "").strip()
        tool_calls = tuple(message.get("tool_calls") or ())
        if not text and not tool_calls:
            # **既没有文本也没有工具调用 = 一次空回答**，与"模型选择不作答"长得一模一样。
            # 回它出去就是本模块开头拒绝的那种降级，所以带上 finish_reason 抛出去
            # （`length` 说明是 max_tokens 截断，那是调用方该知道的事，不是一次"回答"）。
            raise RoutingError(
                f"模型既没回文本也没回工具调用（finish_reason="
                f"{first.get('finish_reason')!r}，usage={usage_of(body.get('usage') or {}).as_dict()}）"
                "——**不降级成空回答**",
                usage=endpoint_usage,
            )

        return Reply(
            text=text,
            tool_calls=tool_calls,
            usage=usage_of(body.get("usage") or {}),
            model=self.model,
            raw=body,
        )

    def _send(self, payload: dict) -> dict:
        """注入的 transport 与真网络**走同一段失败映射** ——
        分成两段写，假 transport 就测不到真网络那段的映射了。"""
        try:
            body = self._transport(payload) if self._transport is not None else self._post(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RoutingError(f"模型端点返回 HTTP {exc.code}：{detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RoutingError(f"调模型失败（连不上端点 {self._config.base_url}）：{exc}") from exc
        except ValueError as exc:
            raise RoutingError(f"模型回包不是 JSON：{exc}") from exc
        if not isinstance(body, dict):
            raise RoutingError(f"模型回包不是 JSON 对象，拿到 {type(body).__name__}")
        return body

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self._config.chat_completions_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self._config.authorization(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request, timeout=self._timeout, context=_ssl_context()
        ) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))


def usage_of(usage: dict) -> Usage:
    """两个细分各自缺失时都回 0，**不回退成把它算进所属的那个桶**。

    `completion_tokens_details.reasoning_tokens` 缺失 → `reasoning = 0`（不算进 completion）；
    `prompt_tokens_details.cached_tokens` 缺失 → `cached = 0`（不算进 prompt，也不算进别处）。
    ⚠️ 解析侧的 `0` 因此有两个含义（端点报了 0 命中 / 端点根本没报这个字段），
    要分辨得看账本的 `endpoint_cached`（`agenerp/explain/ledger.py`）。
    """
    details = usage.get("completion_tokens_details") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    return Usage(
        prompt=int(usage.get("prompt_tokens") or 0),
        completion=int(usage.get("completion_tokens") or 0),
        reasoning=int(details.get("reasoning_tokens") or 0),
        cached=int(prompt_details.get("cached_tokens") or 0),
    )
