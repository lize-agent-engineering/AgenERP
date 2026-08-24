"""证据充分性门禁 L3：入库来源的**覆盖**（P1.0 入口关口实验产出）。

L1/L2 管的是**深度**——顺着一张单据的链条查得够不够深。
L3 管的是**覆盖**——答案里出现库存数量时，那些库存的入库来源查全了没有。

两者不能互相替代。本文件的第二条测试用一条**与恒锐动力那个陷阱完全无关**的
合成轨迹反测：L3 若只对那个陷阱有效，就是照答案写的规则，实验会自证为真而
毫无信息量（方案 §6 风险③）。
"""
from __future__ import annotations

from agenerp.contracts import ReadOnlyContext, evaluate_all, unsatisfied
from agenerp.tools_readonly import (
    EVIDENCE_GATE,
    EVIDENCE_GATE_L1,
    EVIDENCE_GATE_L2,
    EVIDENCE_GATE_L3,
)


def _verdict(facts: dict) -> tuple:
    return unsatisfied(evaluate_all(EVIDENCE_GATE, ReadOnlyContext(facts=facts)))


# ── ① L3 必须挡住「错法 A」：顺着订单查到底，仍漏掉一整批入库 ──────────────


def test_l3_blocks_an_answer_that_missed_an_inbound_source():
    """**这是 L3 存在的理由。**

    轨迹取自 P1.0 的实验前提（活站点实读）：从销售订单出发，`doc.links` 能看到
    工单与发货单，但**看不到外协那一批** —— ERPNext v15 的 `Subcontracting Order`
    结构上没有 `sales_order` 字段，沿订单查得再深也够不着。

    于是一个 L1/L2 **全部满足**的 Agent 仍会漏掉一整批入库。L3 必须判它违规。
    """
    facts = {
        "documents_named_in_question": {"SO-1"},
        "doc_links_called_for": {"SO-1"},                    # L1 满足
        "submitted_downstream_documents": {"WO-1", "DN-1"},
        "doc_get_called_for": {"WO-1", "DN-1"},              # L2 满足
        # 库存流水里有两张使数量增加的凭证，Agent 只看了其中一张
        "inbound_vouchers_of_quantities_in_answer": {"STE-MFG-1", "SCR-1"},
    }
    facts["doc_get_called_for"] |= {"STE-MFG-1"}             # 只补了自制批那张

    reds = _verdict(facts)

    assert len(reds) == 1, f"应恰好红 L3 一条，实为 {[r.condition.text[:20] for r in reds]}"
    assert reds[0].condition is EVIDENCE_GATE_L3
    # L1/L2 必须是绿的 —— 证明这个缺口确实是它们看不见的
    assert all(e.satisfied for e in evaluate_all((EVIDENCE_GATE_L1, EVIDENCE_GATE_L2),
                                                 ReadOnlyContext(facts=facts)))


def test_l3_passes_once_every_inbound_source_was_opened():
    """把漏掉的那张补上，L3 即放行。判据要能开也要能关。"""
    facts = {
        "documents_named_in_question": {"SO-1"},
        "doc_links_called_for": {"SO-1"},
        "submitted_downstream_documents": {"WO-1", "DN-1"},
        "inbound_vouchers_of_quantities_in_answer": {"STE-MFG-1", "SCR-1"},
        "doc_get_called_for": {"WO-1", "DN-1", "STE-MFG-1", "SCR-1"},
    }

    assert _verdict(facts) == ()


# ── ② 反测：L3 不得是照着那个陷阱写的 ──────────────────────────────────


def test_l3_fires_on_an_unrelated_domain_it_was_not_designed_against():
    """**过拟合反测**（方案 §6 风险③）。

    这条轨迹与恒锐动力的储能电池包、外协、销售订单**毫无关系**：一个图书馆的
    书库盘点，入库来源是采购入库与捐赠入库两张凭证，Agent 只看了采购那张。

    形状相同（库存数量 + 多个入库来源 + 只看了一部分），L3 就必须发红。
    若它只对原陷阱有效，说明规则里藏着对那个场景的依赖，实验将自证为真。
    """
    facts = {
        "documents_named_in_question": set(),
        "doc_links_called_for": set(),
        "submitted_downstream_documents": set(),
        "inbound_vouchers_of_quantities_in_answer": {"采购入库-2024-0031", "捐赠入库-2024-0007"},
        "doc_get_called_for": {"采购入库-2024-0031"},
    }

    reds = _verdict(facts)

    assert [r.condition for r in reds] == [EVIDENCE_GATE_L3]


def test_l3_stays_silent_when_the_answer_involves_no_stock_quantity():
    """答案不涉及库存数量时 L3 不该发言 —— 否则它会把纯问答也卡住。

    形态上就是「应覆盖集合为空」：空集被任何集合覆盖，条件自然满足。
    """
    facts = {
        "documents_named_in_question": set(),
        "doc_links_called_for": set(),
        "submitted_downstream_documents": set(),
        "inbound_vouchers_of_quantities_in_answer": set(),
        "doc_get_called_for": set(),
    }

    assert _verdict(facts) == ()


# ── ③ 措辞纪律：规则不许写进具体单号 ────────────────────────────────


def test_l3_wording_carries_no_case_specific_identifiers():
    """规则措辞必须通用。写进具体单号就是照答案写规则（方案 §6 风险③）。

    判据故意用**字面量列表**而不是 import 常量：从 `model.py` import 会让这条
    断言随样板公司改名而自动"通过"，而它要挡的恰恰是「规则被绑到某个具体案例」。
    """
    forbidden = (
        "SAL-ORD", "MFG-WO", "SC-ORD", "PUR-ORD", "MAT-", "ACC-",
        "HRD", "恒锐", "电池", "1010", "1,010", "2000", "2,000", "990",
    )
    blob = f"{EVIDENCE_GATE_L3.text} {EVIDENCE_GATE_L3.fact} {EVIDENCE_GATE_L3.value}"

    hits = [token for token in forbidden if token in blob]

    assert hits == [], f"L3 措辞里出现了案例专属标识：{hits}"
