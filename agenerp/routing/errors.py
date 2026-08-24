"""路由层的失败面。**一个也不许降级成"能跑"。**

两条独立的失败模式，分成两个类型，因为它们该由不同的人在不同的时刻修：

- `DeclarationError`：**声明本身有毛病**（任务类目缺条目、能力名不在枚举里、模型档案
  声明了枚举外的能力）。这是写声明的人当场就该修的，跟运行时环境无关。
- `RoutingError`：**运行时不满足**（配置缺环境变量、目标模型不具备任务所需能力、
  模型侧调用失败）。

`DeclarationError` 是 `RoutingError` 的子类：调用方只想"路由层出事了就别继续"时，
接一个基类即可；要分开处置时再分开接。
"""

from __future__ import annotations


class RoutingError(RuntimeError):
    """路由层的一切失败：配置不全、能力不满足、模型侧调不通、回包不成形。

    **绝不降级**：既不静默换一个模型，也不把失败写成一个空回答。
    空回答与"模型选择不作答"长得一样（`tools/experiments/p1_entry_gate/llm.py`
    的 `LlmError` 已经吃过这个亏），一次故障会被记成一次真实结果。

    `usage` 是**端点自报的原始 usage 字典**（`{"prompt_tokens": ..., "completion_tokens": ...,
    "total_tokens": ..., "completion_tokens_details": {...}}`），**端点确实回了包时才有**
    （P1.7 / D-18）。「空回答」那条路径上端点已经回包、token 已经真的花掉，
    但失败是靠异常传出去的 —— 不把这一位挂上来，那次调用的 token 就只以报错字符串的形态存在，
    账本对该路径会**系统性偏低**，而 D-11 点名的推理模型「回两个字也烧约 195 reasoning token」
    正走这条路径。

    ⚠️ **刻意只挂 `dict`，不挂 `Usage`**：`Usage` 定义在 `agenerp/routing/adapter.py`，
    而 `adapter.py` 自己 `from agenerp.routing.errors import RoutingError` ——
    在本模块 import 它即成 adapter ↔ errors 循环，`routing/__init__.py` 会当场 `ImportError`。
    本模块**不 import 本包任何模块**这一条因此是硬约束，别顺手"改成有类型的"。
    解析归 `agenerp.routing.adapter.usage_of()` 那一处，本模块只搬运。
    """

    def __init__(self, *args: object, usage: dict | None = None) -> None:
        super().__init__(*args)
        self.usage = usage


class DeclarationError(RoutingError):
    """能力声明自身不成立 —— 与运行时环境无关，是声明写错了。"""
