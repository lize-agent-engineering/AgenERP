"""巡检器（P1.5）—— **纯规则引擎，零 LLM**。落点节是
`docs/architecture/module-boundaries.md` §7.9。

D-15 把 P1.5 拆成两件东西：**巡检**（按清单逐条查、命中即报）是代码，
**归因**（为什么会这样、要不要紧、该怎么办）才是模型。本包只做前一半，
后一半在 `agenerp/insight/`。两者**不许合并成一个模块** —— 混在一个「Agent」里
会让规则的确定性被模型的随机性污染（`Decision` D2）。

⚠️ **目录命名消歧**：`agenerp/pack.py` 的「包」是**定制包**（Custom Field /
Property Setter 的导出与 apply），与行业规则包无关；`inspect` 是标准库名。
故取 `agenerp/inspection/`，且本包**不复用 `pack.py` 的任何结构**。

⚠️ **本包自带的最小规则集不是行业包制品**（P1.6 才交付行业包）。

导出面只有四样：跑一次巡检（`inspect_site`）、它的产物（`InspectionReport` / `Hit`）、
规则的声明形状与装载器（`Rule` / `load_rules` / `RuleLoadError`）、自带的最小规则集
（`minimal_rules`）。其余是内部件，从子模块 import 即可。
"""

from __future__ import annotations

from agenerp.inspection.engine import (
    Hit,
    InspectionReport,
    check_test_cases,
    inspect_site,
    run,
)
from agenerp.inspection.minimal import minimal_rules
from agenerp.inspection.rules import Rule, RuleLoadError, load_rules

__all__ = (
    "Hit",
    "InspectionReport",
    "Rule",
    "RuleLoadError",
    "check_test_cases",
    "inspect_site",
    "load_rules",
    "minimal_rules",
    "run",
)
