"""🔴 P1.7 门禁 · 单次解释成本记账（记账但不拦截，D-18）+ 失控闸

判据来源：`docs/masterplan/02-WBS.md` §4 第 P1.7 行。

**本文件不重写断言体**，按路径加载 `tests/unit/test_explain_cost_accounting_body.py`。
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


_BODY = _load("tests/unit/test_explain_cost_accounting_body.py", "_gate_body_cost")

test_all_three_token_buckets_are_recorded_per_call = _BODY.test_all_three_token_buckets_are_recorded_per_call
test_the_ledger_rolls_up_per_explanation = _BODY.test_the_ledger_rolls_up_per_explanation
test_the_ledger_is_on_the_product_path_and_has_no_switch = _BODY.test_the_ledger_is_on_the_product_path_and_has_no_switch
test_the_accounting_never_blocks_anything = _BODY.test_the_accounting_never_blocks_anything
test_a_runaway_explanation_is_stopped_by_the_tool_call_limit = _BODY.test_a_runaway_explanation_is_stopped_by_the_tool_call_limit
test_the_runaway_stop_reason_is_not_max_turns_and_not_the_breaker = _BODY.test_the_runaway_stop_reason_is_not_max_turns_and_not_the_breaker
test_the_two_gates_fire_independently = _BODY.test_the_two_gates_fire_independently
test_the_default_limit_applies_on_the_product_path_without_any_switch = _BODY.test_the_default_limit_applies_on_the_product_path_without_any_switch
test_the_cost_ledger_is_still_complete_when_the_runaway_gate_fires = _BODY.test_the_cost_ledger_is_still_complete_when_the_runaway_gate_fires
