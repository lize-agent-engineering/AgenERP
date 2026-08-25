"""🔴 P1.5 门禁 · 洞察消融：抽掉规则就查不出

判据来源：`docs/masterplan/02-WBS.md` §4 第 P1.5 行。

**本文件不重写断言体**，按路径加载 `tests/unit/test_inspection_rules.py`。
与 `tests/gates/test_tool_execution_live.py` 同一取舍，理由逐字照搬：

> 判据只有一份，门禁是它的严格模式；两边各写一套会漂移成
> 「门禁版」与「开发版」两个标准。

**loop 交付断言体、人创建门禁**：`tests/gates/**` 在红线 1 内，loop 不得修改。
它把判据写足强度放在红线外并登记 needs-human，这一半由人做（带
`Gates-Change-Approved-By:` trailer）。

⚠️ **断言强度不因为换了路径而改变。** 若开发期那份被改弱，这边同步变弱且
立刻可见 —— 这是有意的。
"""
from __future__ import annotations

import importlib.util
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(relative_path: str, module_name: str):
    """按路径加载仓内另一个测试模块。找不到就**抛**，不静默降级。

    静默降级会让「判据源文件被删/改名」表现为「门禁少跑几条」——
    那正是判定器不许有的形状。
    """
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"{relative_path} 不存在。判据的断言体只有一份，源文件没了就是红，"
            "不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BODY = _load("tests/unit/test_inspection_rules.py", "_gate_body_ablation")

# WBS §4 P1.5 的 🔴 判据是**消融**：抽掉规则则查不出。
test_h1_ablation_removing_that_rule_yields_zero_hits = _BODY.test_h1_ablation_removing_that_rule_yields_zero_hits

# ⚠️ **「零 LLM 调用」那两条不在这里导出**，理由照实写：它们依赖
# `no_model_calls` fixture（monkeypatch 六个模型入口），跨文件加载时 fixture
# 不随函数走。**硬导出会得到 2 个 error，那是「判据跑不起来」而不是
# 「判据发红」—— 两者在退出码上一样，但含义完全不同。**
#
# 它们仍由 `tests/unit/test_inspection_rules.py` 跑到，而 tests/unit 已在
# CI 的「单测与契约测试」job 里（2026-08-24 接入）。**不是没人管，是管在别处。**
