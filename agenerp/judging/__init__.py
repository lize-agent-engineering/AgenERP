"""答案判定器 v0（P1.4 的第 2 个交付面）—— **判「这段答案对不对」，只判这一件事**。
落点节是 `docs/architecture/module-boundaries.md` §7.15。

`tests/unit/test_answer_judging_fixture.py` 模块头逐字要求：**动手写判定器之前，
先让它跑通那 24 条人工标注**。本包就是那句话的落地面，跑通与否的证据在
`docs/evidence/p1-answer-judge/`。

⚠️ **已验证的适用范围只有 P1.0 那一道题**（`rubric.QUESTION`）。
迁到别的题族（例如洞察 Agent 的归因文本）**属外推**，按 D-16 只能写「待复验」，
不能写成结论。

⚠️ **本包没有留出集评估**（plan D7：集子只有 5 条负例，留出 2 条剩 3 条，两边都失去判别力）。
「它在集子之外判得准」这句话**本仓没有任何实证支撑**，不得被任何下游当成已验证。

⚠️ **导出面刻意只有四个名字**：判一次（`judge_one`）、拿结果（`Verdict`）、
出事接住（`JudgingError`）、标签集合（`LABELS`）。
**读标注集与验收口径不在这里** —— 那两件事落 `tests/unit/answer_judge_fixture.py`（plan D7b）：
产品包依赖 `tests/fixtures/**` 是边界倒置，且会把"这次实验的验收口径"永久焊进产品导出面。
"""

from __future__ import annotations

from agenerp.judging.judge import Verdict, judge_one
from agenerp.judging.rubric import LABELS, JudgingError

__all__ = ("judge_one", "Verdict", "JudgingError", "LABELS")
