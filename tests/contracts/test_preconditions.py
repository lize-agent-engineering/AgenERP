"""前置条件组 —— 对构造出来的只读上下文求值，满足与不满足各至少一例。

**失败意味着什么**：前置条件不可脱离活站点被独立测试，`docs/masterplan/02-WBS.md` P0.2
括号里那句「前置条件/后置断言可独立测试」的判据就不成立。

本文件**不 import 任何 Frappe / 站点相关的东西**——这正是「独立可测」的机制：
测试构造一个 `ReadOnlyContext` 即可求值。
"""

import pytest

from agenerp.contracts import (
    Condition,
    ReadOnlyContext,
    check_preconditions,
    evaluate_all,
    unsatisfied,
)
from agenerp.tools_readonly import (
    ANSWERING_TOOLS,
    EVIDENCE_GATE_L1,
    EVIDENCE_GATE_L2,
    RULE_LOOKUP,
    get,
)


def test_no_site_import_needed():
    """求值面不连任何站点：本模块跑得起来这件事本身就是判据。"""
    assert ReadOnlyContext().facts == {}


# --- 证据充分性门禁 L1（§5.0 ① Spike 02 实测产出）--------------------------------


def test_l1_satisfied_when_doc_links_was_called_for_the_named_document():
    context = ReadOnlyContext(
        {
            "documents_named_in_question": ["SAL-ORD-2026-00001"],
            "doc_links_called_for": ["SAL-ORD-2026-00001"],
        }
    )
    result = EVIDENCE_GATE_L1.evaluate(context)
    assert result.satisfied, result.reason


def test_l1_unsatisfied_reproduces_the_spike_02_premature_stop():
    """Spike 02：只调一次 doc.get 就下结论。每个数字都对，业务结论完全错。"""
    context = ReadOnlyContext(
        {
            "documents_named_in_question": ["SAL-ORD-2026-00001"],
            "doc_links_called_for": [],
        }
    )
    result = EVIDENCE_GATE_L1.evaluate(context)
    assert not result.satisfied
    assert "SAL-ORD-2026-00001" in result.reason


def test_l1_unsatisfied_when_the_context_never_recorded_the_fact():
    """没查 ≠ 查了没有。缺事实必须判为不满足，并且原因要说清是缺哪一条。"""
    result = EVIDENCE_GATE_L1.evaluate(ReadOnlyContext({}))
    assert not result.satisfied
    assert "doc_links_called_for" in result.reason


# --- 证据充分性门禁 L2（由 qwen3:14b 实测补出）-----------------------------------


def test_l2_satisfied_when_every_submitted_downstream_doc_was_opened():
    context = ReadOnlyContext(
        {
            "submitted_downstream_documents": ["MAT-SCR-2026-00001", "DN-2026-00007"],
            "doc_get_called_for": ["SAL-ORD-2026-00001", "MAT-SCR-2026-00001", "DN-2026-00007"],
        }
    )
    assert EVIDENCE_GATE_L2.evaluate(context).satisfied


def test_l2_unsatisfied_reproduces_seeing_loss_00003_without_opening_it():
    """qwen3:14b 照 L1 调了 doc.links、看到了那张下游单据，却没打开它。"""
    context = ReadOnlyContext(
        {
            "submitted_downstream_documents": ["MAT-SCR-2026-00001"],
            "doc_get_called_for": ["SAL-ORD-2026-00001"],
        }
    )
    result = EVIDENCE_GATE_L2.evaluate(context)
    assert not result.satisfied
    assert "MAT-SCR-2026-00001" in result.reason


def test_l2_reports_every_unopened_document_not_just_the_first():
    context = ReadOnlyContext(
        {
            "submitted_downstream_documents": ["MAT-SCR-2026-00001", "DN-2026-00007"],
            "doc_get_called_for": [],
        }
    )
    result = EVIDENCE_GATE_L2.evaluate(context)
    assert not result.satisfied
    assert "MAT-SCR-2026-00001" in result.reason and "DN-2026-00007" in result.reason


# --- 门禁挂在哪些工具上 -----------------------------------------------------------


@pytest.mark.parametrize("tool", ANSWERING_TOOLS)
def test_answering_tools_carry_both_gates(tool):
    preconditions = get(tool).preconditions
    assert EVIDENCE_GATE_L1 in preconditions, tool
    assert EVIDENCE_GATE_L2 in preconditions, tool


@pytest.mark.parametrize("tool", ["doc.get", "doc.links"])
def test_evidence_gathering_tools_are_not_gated_on_themselves(tool):
    """L1 卡住第一次 doc.links 就再也调不出 doc.links——循环依赖，必须不挂。"""
    preconditions = get(tool).preconditions
    assert EVIDENCE_GATE_L1 not in preconditions
    assert EVIDENCE_GATE_L2 not in preconditions


def test_check_preconditions_evaluates_a_whole_contract():
    contract = get("query.read")
    satisfied_context = ReadOnlyContext(
        {
            "documents_named_in_question": ["SAL-ORD-2026-00001"],
            "doc_links_called_for": ["SAL-ORD-2026-00001"],
            # 下游用一张原生单据。此处原本写 `LOSS-00003` —— 那是 XM 自建的
            # custom DocType，已按 D-9 退役。
            "submitted_downstream_documents": ["MAT-DN-2026-00001"],
            # L3 要求的入库来源覆盖（P1.0）。这里给成空集：本测试验的是
            # 「三条前置**都满足**时不报违规」，答案不涉及库存数量即为空集。
            "inbound_vouchers_of_quantities_in_answer": [],
            "doc_get_called_for": ["MAT-DN-2026-00001"],
        }
    )
    assert unsatisfied(check_preconditions(contract, satisfied_context)) == ()

    blocked = check_preconditions(contract, ReadOnlyContext({}))
    assert len(unsatisfied(blocked)) == len(contract.preconditions)


def test_rule_lookup_blocks_when_the_industry_pack_is_not_loaded():
    """「无需指令」成立，「无需规则」不成立（§5.0 ②）。"""
    loaded = ReadOnlyContext({"industry_pack_loaded": True})
    absent = ReadOnlyContext({"industry_pack_loaded": False})
    assert unsatisfied(check_preconditions(RULE_LOOKUP, loaded)) == ()
    assert len(unsatisfied(check_preconditions(RULE_LOOKUP, absent))) == 1


# --- 求值面本身 -------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator,fact_value,value,expected",
    [
        ("is_true", True, None, True),
        ("is_true", False, None, False),
        ("not_empty", ["a"], None, True),
        ("not_empty", [], None, False),
        ("is_empty", [], None, True),
        ("is_empty", ["a"], None, False),
        ("equals", "has_permission", "has_permission", True),
        ("equals", "docperm", "has_permission", False),
        ("contains", ["a", "b"], "a", True),
        ("contains", ["a", "b"], "z", False),
    ],
)
def test_every_operator_has_a_true_and_a_false_case(operator, fact_value, value, expected):
    condition = Condition(text="t", fact="f", operator=operator, value=value)
    assert condition.evaluate(ReadOnlyContext({"f": fact_value})).satisfied is expected


def test_unknown_operator_is_unsatisfied_rather_than_crashing():
    result = Condition(text="t", fact="f", operator="sudo").evaluate(ReadOnlyContext({"f": 1}))
    assert not result.satisfied
    assert "sudo" in result.reason


def test_covers_fact_needs_the_compared_fact_to_be_present():
    condition = Condition(text="t", fact="a", operator="covers_fact", value="b")
    result = condition.evaluate(ReadOnlyContext({"a": ["x"]}))
    assert not result.satisfied
    assert "'b'" in result.reason


def test_evaluate_all_does_not_short_circuit():
    conditions = (
        Condition(text="1", fact="missing_one"),
        Condition(text="2", fact="missing_two"),
    )
    assert len(unsatisfied(evaluate_all(conditions, ReadOnlyContext({})))) == 2
