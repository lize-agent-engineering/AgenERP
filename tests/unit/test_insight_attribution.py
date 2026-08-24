"""P1.5 洞察 Agent（归因）的判据 —— 判的是「**归因走 P1.4 的循环、且改不动巡检结论**」。

判据全部落在**结构化事实**上：取证轨迹、门禁判定、命中记录逐字不变。
**归因文本的质量不在这里，也不在本 plan 的任何 Exit Criteria 里**（plan Non-Goal 8）：
判自由文本要先跑通 `tests/unit/test_answer_judging_fixture.py` 的 24 条人工标注，
那属另一个交付面，本 plan 不开这个口子。
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as model_fakes  # noqa: E402
import inspection_fakes as fakes  # noqa: E402

from agenerp.context import session as conversation  # noqa: E402
from agenerp.explain import ExplainResult  # noqa: E402
from agenerp.explain.gate import (  # noqa: E402
    USE_ANSWERING,
    USE_TOOL_PRECONDITION,
    EvidenceSurface,
)
from agenerp.explain.loop import STOP_ANSWERED, ExplainTrace  # noqa: E402
from agenerp.insight import (  # noqa: E402
    InsightBoundaryError,
    attribute,
    attribute_all,
    ensure_unchanged,
    hits_unchanged,
    question_for,
)
from agenerp.insight import attribution as insight  # noqa: E402
from agenerp.inspection import inspect_site, minimal_rules  # noqa: E402
from agenerp.inspection.engine import Hit  # noqa: E402
from agenerp.orchestration import DenialBreaker  # noqa: E402
from agenerp.seed.checks import EXPECTED_BACKLOG_QTY  # noqa: E402

ITEM_LINK_STEP = model_fakes.tools_step(
    model_fakes.call("doc.links", "c0", doctype="Item", name="HRD-PACK-5K")
)
INBOUND_STEP = model_fakes.tools_step(
    model_fakes.call(
        "doc.get", "c1", doctype="Subcontracting Receipt", name="MAT-SCR-2026-00001"
    ),
    model_fakes.call("doc.get", "c2", doctype="Stock Entry", name="MAT-STE-2026-00003"),
)
GROUNDED_ANSWER = model_fakes.answer_step(
    "成品仓积压 1,010 台：自制与外协各入库 1,000 台，只发出 990 台，"
    "订单被人工关闭所以账面达成率还是 100%。"
)


def backlog_hit(site) -> Hit:
    """命中**由巡检器真跑出来**，不是判据手捏的 —— 归因解释的必须是那一条。"""
    report = inspect_site(minimal_rules(), fakes.client_for(site))
    assert len(report.hits) == 1
    return report.hits[0]


def run(script, *, site=None, max_turns=6):
    site = site if site is not None else fakes.seed_site()
    hit = backlog_hit(site)
    result = attribute(
        hit,
        client=fakes.client_for(site),
        models=model_fakes.models(),
        config=model_fakes.config(),
        transport=model_fakes.ScriptedModel(script),
        doctypes=list(fakes.ATTRIBUTION_DOCTYPES),
        max_turns=max_turns,
    )
    return hit, result


# ── D3：归因走 P1.4 的解释循环，不另起一条 ──────────────────────────────────


def test_d3_the_attribution_goes_through_the_p1_4_loop():
    """消费的符号是 `agenerp.explain.explain`（P1.4 导出面两项之一）。

    **判据不是「代码里 import 了它」**，而是回来的东西带着那条循环独有的痕迹：
    开场注入的代价、证据充分性门禁的求值记录、以及**同一份**事实采集面被两处用过。
    """
    _, attributed = run([ITEM_LINK_STEP, INBOUND_STEP, GROUNDED_ANSWER])

    assert isinstance(attributed.result, ExplainResult)
    assert attributed.trace["task_class"] == "explain"
    assert attributed.trace["opening_request_count"] > 0, "开场注入没跑 = 不是那条循环"
    assert attributed.trace["gate_checks"], "没有门禁求值记录 = 绕开了 P1.4"
    assert all(check["enforced"] for check in attributed.trace["gate_checks"])
    surface = attributed.result.surface
    assert surface.used_for(USE_TOOL_PRECONDITION) > 0
    assert surface.used_for(USE_ANSWERING) > 0


def test_d3_insight_never_reaches_the_model_except_through_that_entry(monkeypatch):
    """M9 的杀手：把 `explain` 换成记账替身。洞察侧若自己直连模型，它一次都不会被调到。"""
    calls: list[dict] = []

    def recorder(question, **kwargs):
        calls.append({"question": question, **kwargs})
        return _stub_result()

    monkeypatch.setattr(insight, "explain", recorder)
    site = fakes.seed_site()
    hit = backlog_hit(site)
    attribute(hit, client=fakes.client_for(site), models=model_fakes.models())

    assert len(calls) == 1
    assert calls[0]["task_class"] == "explain"
    assert calls[0]["question"] == question_for(hit)


def _stub_result() -> ExplainResult:
    """`explain` 的记账替身要回一个成形的 `ExplainResult` —— 这条判据判的是
    「那条入口被调到了没有」，不是循环内部怎么跑。"""
    client = fakes.client_for(fakes.seed_site())
    return ExplainResult(
        answer="（替身）",
        accepted=True,
        trace=ExplainTrace(question="stub"),
        session=conversation.start("stub"),
        surface=EvidenceSurface("stub", client),
        breaker=DenialBreaker(),
    )


# ── 命中 → 归因的接线 ───────────────────────────────────────────────────────


def test_the_hit_record_goes_into_the_question_verbatim():
    """命中记录逐字进问题，**包括那个算出来的数** —— 含糊掉就没得解释了。"""
    site = fakes.seed_site()
    hit = backlog_hit(site)
    question = question_for(hit)

    assert hit.rule_id in question
    assert str(int(EXPECTED_BACKLOG_QTY)) in question
    assert "HRD-PACK-5K" in question and "成品仓 - HRD" in question


def test_the_attribution_and_its_evidence_trace_land_together():
    """归因文本与取证轨迹一起落盘、可回放。"""
    hit, attributed = run([ITEM_LINK_STEP, INBOUND_STEP, GROUNDED_ANSWER])

    assert attributed.accepted is True
    assert attributed.trace["stopped"] == STOP_ANSWERED
    payload = attributed.as_dict()
    assert payload["hit"] == hit.as_dict()
    assert payload["answer"] == attributed.answer
    assert [call["tool"] for call in payload["trace"]["tool_calls"]] == [
        "doc.links",
        "doc.get",
        "doc.get",
    ]
    assert json.dumps(payload, ensure_ascii=False, sort_keys=True)


# ── H4：取证不足时归因被证据充分性门禁拒绝 ─────────────────────────────────


def test_h4_an_ungrounded_attribution_is_refused_by_the_evidence_gate():
    """判据落在**轨迹**上，不落在归因文本上。

    两条规则同时发红，**两条都照实断言**：
    L3 —— 答案报了成品仓的库存量，两张入库凭证一张都没查；
    L1 —— 命中的 `item_code` 恰好长得像单号（`HRD-PACK-5K` 三段全大写数字），
    于是门禁把它当成「问题点名的单据」。后者是 D3 选项 B 的残余风险之一，
    **照实记，不擅自绕开**：它误报的方向是更严，不是更松。
    """
    _, refused = run(
        [model_fakes.answer_step("成品仓积压了 1,010 台，因为订单被人工关闭。")],
        max_turns=2,
    )

    assert refused.accepted is False
    assert refused.answer == "", "门禁没放行 → 答案不许交出去"
    facts = refused.trace["gate_checks"][0]["facts"]
    assert facts["inbound_vouchers_of_quantities_in_answer"] == [
        "MAT-SCR-2026-00001",
        "MAT-STE-2026-00003",
    ]
    assert facts["doc_get_called_for"] == []
    failed = {item["fact"]: item for item in refused.trace["gate_checks"][0]["failed"]}
    assert failed["doc_get_called_for"]["missing_count"] == 2
    assert facts["documents_named_in_question"] == ["HRD-PACK-5K"]
    assert "doc_links_called_for" in failed


def test_h4_the_same_attribution_is_released_once_the_evidence_is_complete():
    """门禁不是「永远拒」—— 补齐取证之后同一条归因被放行。"""
    _, released = run([ITEM_LINK_STEP, INBOUND_STEP, GROUNDED_ANSWER])

    assert released.accepted is True
    assert released.trace["gate_checks"][-1]["failed"] == []
    assert released.trace["forced_continues"] == []


# ── 巡检结论不可被模型改写 ──────────────────────────────────────────────────

CONTRADICTING_ANSWER = model_fakes.answer_step(
    "巡检器算错了：成品仓其实一台都没有积压，on_hand 是 0 台，这条命中应当撤销。"
)


def test_the_model_cannot_rewrite_the_inspection_verdict():
    """给替身模型一个与命中**相反**的输出，最终命中记录**一个字不变**（M11 的杀手）。"""
    site = fakes.seed_site()
    report = inspect_site(minimal_rules(), fakes.client_for(site))
    hit = report.hits[0]
    before = hit.as_dict()

    attributed = attribute(
        hit,
        client=fakes.client_for(site),
        models=model_fakes.models(),
        config=model_fakes.config(),
        transport=model_fakes.ScriptedModel([ITEM_LINK_STEP, INBOUND_STEP, CONTRADICTING_ANSWER]),
        doctypes=list(fakes.ATTRIBUTION_DOCTYPES),
        max_turns=6,
    )

    assert attributed.hit is hit
    assert attributed.hit.as_dict() == before
    assert attributed.hit.quantity == EXPECTED_BACKLOG_QTY
    assert report.hits[0].as_dict() == before
    assert hits_unchanged(report, [attributed])


def test_the_boundary_guard_actually_fires_when_the_verdict_moves():
    """边界执行本身有判据 —— 没有落点的边界只是一句话。"""
    site = fakes.seed_site()
    hit = backlog_hit(site)
    before = json.dumps(hit.as_dict(), ensure_ascii=False, sort_keys=True)

    ensure_unchanged(before, hit)
    rewritten = Hit(
        rule_id=hit.rule_id,
        statement=hit.statement,
        subject=hit.subject,
        quantity_name=hit.quantity_name,
        quantity=0.0,
        measures=hit.measures,
    )
    with pytest.raises(InsightBoundaryError):
        ensure_unchanged(before, rewritten)


def test_attribute_all_leaves_the_report_untouched():
    site = fakes.seed_site()
    report = inspect_site(minimal_rules(), fakes.client_for(site))
    before = report.as_dict()

    attributions = attribute_all(
        report,
        client=fakes.client_for(site),
        models=model_fakes.models(),
        config=model_fakes.config(),
        transport=model_fakes.ScriptedModel([ITEM_LINK_STEP, INBOUND_STEP, GROUNDED_ANSWER]),
        doctypes=list(fakes.ATTRIBUTION_DOCTYPES),
        max_turns=6,
    )

    assert len(attributions) == len(report.hits) == 1
    assert report.as_dict() == before
    assert hits_unchanged(report, attributions)
