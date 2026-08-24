"""洞察 Agent（P1.5）—— **只负责命中之后的归因**。落点节是
`docs/architecture/module-boundaries.md` §7.9。

与 `agenerp/inspection/`（巡检器）**分开**是 D-15 的直接后果，不许合并成一个模块：
巡检是确定性的规则执行，归因是模糊的、枚举不完的叙述；混在一个「Agent」里
会让规则的确定性被模型的随机性污染，且成本白花。

⚠️ **本模块不实现 `anomaly.scan` / `benchmark.compare`**（它们不在十个只读契约里）。
⚠️ **归因文本的质量本期没有任何判据**：判自由文本要先跑通 24 条人工标注
（`tests/unit/test_answer_judging_fixture.py`），那属另一个交付面。
本模块的判据只落在**结构化事实**上：取证轨迹、门禁判定、命中记录逐字不变。
"""

from __future__ import annotations

from agenerp.insight.attribution import (
    Attribution,
    InsightBoundaryError,
    attribute,
    attribute_all,
    ensure_unchanged,
    hits_unchanged,
    question_for,
)

__all__ = (
    "Attribution",
    "InsightBoundaryError",
    "attribute",
    "attribute_all",
    "ensure_unchanged",
    "hits_unchanged",
    "question_for",
)
