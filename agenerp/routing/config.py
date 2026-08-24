"""模型端点配置 —— **三个变量，一个默认值都没有。**

`docs/architecture/model-management.md` §12.1 ① 是「默认不指向任何商业 API」。
落到代码上就是：**产品包里没有端点、没有厂商 SDK、没有厂商环境变量名**。
`DASHSCOPE_*` 那两个名字把厂商写进了产品配置面，本模块**不读它们**
（实验设施 `tools/experiments/p1_entry_gate/` 还在用，那是它的事）。

缺变量时**指名报错**，不猜、不兜底：一个默认端点会让"没配置"静默变成"连到了别人家"。

**凭据不进 `repr`、不进异常文本、不进任何日志。** `api_key` 是 `repr=False` 的字段，
本模块任何一条异常消息里都不插值它。判据在 `tests/routing/test_adapter.py`
（哨兵 key + 断言它不出现在 `repr` 与异常文本里），不是靠 code review 保证。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from agenerp.routing.errors import RoutingError

BASE_URL_ENV = "AGENERP_LLM_BASE_URL"
API_KEY_ENV = "AGENERP_LLM_API_KEY"
MODEL_ENV = "AGENERP_LLM_MODEL"

REQUIRED_ENV = (BASE_URL_ENV, API_KEY_ENV, MODEL_ENV)


@dataclass(frozen=True)
class LlmConfig:
    """一个 OpenAI 兼容端点的最小配置。`api_key` 不参与 `repr`。"""

    base_url: str
    model: str
    api_key: str = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def authorization(self) -> str:
        """唯一一处该把 key 拿出来的地方 —— 拼请求头。别在别处调它。"""
        return f"Bearer {self.api_key}"


def from_env(env: Mapping[str, str] | None = None) -> LlmConfig:
    """从环境读配置。**任何一个缺失都明确失败，并指名缺的是哪个。**"""
    env = os.environ if env is None else env
    values = {name: (env.get(name) or "").strip() for name in REQUIRED_ENV}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RoutingError(
            f"模型端点配置不全，缺：{missing}。"
            f"三个变量都没有默认值（{list(REQUIRED_ENV)}）—— "
            "默认端点会让「没配置」静默变成「连到了别人家」"
        )
    return LlmConfig(
        base_url=values[BASE_URL_ENV],
        model=values[MODEL_ENV],
        api_key=values[API_KEY_ENV],
    )
