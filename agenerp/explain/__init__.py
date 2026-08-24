"""解释 Agent（P1.4）—— 控制循环本体。落点节是
`docs/architecture/module-boundaries.md` §7.8。

**导出面刻意只有两样东西**：一个入口（`explain`）与它的返回类型（`ExplainResult`）。
其余（循环类、事实采集面、工具 schema、熔断接线）是内部件，从子模块 import 即可，
但不进这一层 —— 导出面一旦泄开就收不回来（`agenerp/routing/__init__.py` 同一口径）。

⚠️ **`ExplainLoop` 不在导出面上是有意的**（`Decision` D7）：② 作答前那道门禁的消融开关
只在判据侧构造得出来，产品调用方拿不到它。① 工具前置那一面**全程开着、根本没有开关**。
"""

from __future__ import annotations

from agenerp.explain.loop import ExplainResult, explain

__all__ = ("explain", "ExplainResult")
