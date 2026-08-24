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
    """


class DeclarationError(RoutingError):
    """能力声明自身不成立 —— 与运行时环境无关，是声明写错了。"""
