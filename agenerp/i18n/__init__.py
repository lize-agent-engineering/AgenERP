"""术语层（P2.7）· 字段 → 中文名。

## 为什么需要它

活站点导出实读（2026-08-27）：**业务 app 全量 6,350 个字段，label 含中文的 = 0**。
不是「少」，是零。而 `Item Reorder.warehouse` 的 label 逐字是「**Request for**」——
字段名说的是仓库，标签说的是「请求给」。一个中国工人看着那张表，
既读不懂英文，也猜不出这一列到底是什么。

Spike 07 §6.3 给它加了第二个理由：**术语层同时是检索质量的前置条件** ——
用户用中文问、schema 是英文的，这是跨语言检索。
⚠️ 那是 Spike 07 的**建议**，不是实测结论。

## ⚠️ 这一层的质量上限，写在这里

判据（`tests/i18n/`）能守住的全是**规则面**：覆盖率、指回真实字段、含中文、
不抄英文、不抄 fieldname、不空不过长，外加 15 条「不该错」的清单。

**它们验的是「有没有离谱地错」，不是「翻译得好不好」。**
后者没有规则面的判法，而硬约束 ③（D-15）反过来也成立 —— **不许让模型判自己的产物**。
⇒ **上限由那 15 条决定，且这个上限低。用它之前先知道这一点。**

## ⚠️ v0 是仓内的 JSON，这是暂时的

P2.0 已判**产物落 AgenERP 自有表**（Workspace 会被升级整条删了重插）。
建表与 GitOps 是 **P2.4** 的结果面 —— 那时本模块这份 JSON 是它的输入。
**在那之前落在仓里，且这句话写在这里，免得它悄悄变成永久形态。**（形态同 `agenerp/dsl/roles.py`。）
"""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache

TERMS_PATH = pathlib.Path(__file__).resolve().parent / "terms.zh.json"


@lru_cache(maxsize=1)
def load_terms() -> dict:
    """读整份术语层（含 `provenance`）。

    ⚠️ **读不到就抛，不回一个空 dict。** 空 dict 会让调用方安静地退回英文，
    而「术语层没装上」与「术语层说这个字段没有中文名」在界面上长得一模一样。
    这与 `agenerp/dsl/validate.py` 那条「验不了的东西不许算过」同源。
    """
    if not TERMS_PATH.exists():
        raise FileNotFoundError(
            f"术语层产物不在 {TERMS_PATH} —— "
            "生成方式见 tools/experiments/p2_terminology/generate_terms.py"
        )
    raw = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
    if set(raw) != {"provenance", "terms"}:
        raise ValueError(f"术语层的结构不对：期望 provenance + terms，实际 {sorted(raw)}")
    return raw


def label_for(doctype: str, fieldname: str) -> str | None:
    """一个字段的中文名。**没有就回 `None`，不回 fieldname 兜底。**

    兜底成 fieldname 会让「有中文名」与「没有中文名」在调用方那里分不出来 ——
    而分不出来时，覆盖率这个数就没法验了。
    """
    return load_terms()["terms"].get(f"{doctype}.{fieldname}")
