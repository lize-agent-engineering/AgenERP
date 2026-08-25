"""🔴 P1.4 门禁 · 证据充分性门禁拦得住单跳答案

判据来源：`docs/masterplan/02-WBS.md` §4 第 P1.4 行。

**本文件不重写断言体**，按路径加载 `tests/unit/test_evidence_gate_single_hop_body.py`。
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


_BODY = _load("tests/unit/test_evidence_gate_single_hop_body.py", "_gate_body_single_hop")

test_single_hop_answer_is_rejected_on_the_product_path = _BODY.test_single_hop_answer_is_rejected_on_the_product_path
test_same_trace_and_answer_is_accepted_when_the_answering_gate_is_ablated = _BODY.test_same_trace_and_answer_is_accepted_when_the_answering_gate_is_ablated
test_the_answering_gate_is_on_by_default_on_the_product_path = _BODY.test_the_answering_gate_is_on_by_default_on_the_product_path
test_well_worded_but_under_evidenced_answer_is_still_rejected = _BODY.test_well_worded_but_under_evidenced_answer_is_still_rejected
test_the_two_answers_differ_in_text_but_not_in_trace = _BODY.test_the_two_answers_differ_in_text_but_not_in_trace
