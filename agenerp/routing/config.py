"""模型端点配置 —— **三个变量，一个默认值都没有。**

`docs/architecture/model-management.md` §12.1 ① 是「默认不指向任何商业 API」。
落到代码上就是：**产品包里没有端点、没有厂商 SDK、没有厂商环境变量名**。
`DASHSCOPE_*` 那两个名字把厂商写进了产品配置面，本模块**不读它们**
（实验设施 `tools/experiments/p1_entry_gate/` 还在用，那是它的事）。

缺变量时**指名报错**，不猜、不兜底：一个默认端点会让"没配置"静默变成"连到了别人家"。

**凭据不进 `repr`、不进 `asdict` / `vars`、不进异常文本、不进本层任何日志。**
判据在 `tests/routing/test_adapter.py`（哨兵 key + 逐条断言），不是靠 code review 保证。
**边界照实说**：带栈帧局部变量的 traceback 打印器仍读得到 `_post` 里那个 `Request` 的请求头，
本层挡不住那种打印器 —— 判据判的是标准库 `traceback.format_exc()`。
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from agenerp.routing.errors import RoutingError

BASE_URL_ENV = "AGENERP_LLM_BASE_URL"
API_KEY_ENV = "AGENERP_LLM_API_KEY"
MODEL_ENV = "AGENERP_LLM_MODEL"

REQUIRED_ENV = (BASE_URL_ENV, API_KEY_ENV, MODEL_ENV)


class LlmConfig:
    """一个 OpenAI 兼容端点的最小配置。

    **刻意不是 dataclass。** 用 `__slots__` + 自己写的 `__repr__`，是为了把**批量序列化**
    这条泄漏路径整个拿掉：`dataclasses.asdict()` 会把 `repr=False` 的字段照样倒出来，
    `vars()` / `__dict__` 也一样 —— 那两条不是假想，任何一句"把配置打进日志看看"都会走上去。
    现在 `asdict` 不适用、`vars()` 直接 `TypeError`，key 只能**指名去取**。

    ⚠️ **能挡住什么、挡不住什么，说清楚**：挡得住 `repr` / `str` / `asdict` / `vars` /
    本层任何一条异常文本。**挡不住**带栈帧局部变量的 traceback 打印器（rich、cgitb 之类）——
    `_post` 的栈帧里有构造好的 `Request`，请求头里就是 `Authorization`。
    标准库 `traceback.format_exc()` 不打 locals，本层判据判的是它。
    """

    __slots__ = ("base_url", "model", "_api_key")

    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        object.__setattr__(self, "base_url", base_url.rstrip("/"))
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "_api_key", api_key)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("LlmConfig 是只读的")

    def __repr__(self) -> str:
        return f"LlmConfig(base_url={self.base_url!r}, model={self.model!r})"

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def authorization(self) -> str:
        """唯一一处该把 key 拿出来的地方 —— 拼请求头。别在别处调它。"""
        return f"Bearer {self._api_key}"


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
