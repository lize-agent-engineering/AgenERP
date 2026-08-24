"""P1.4 控制循环本体的判据 —— 判的是「**循环怎么把事实凑出来、凑不齐时怎么办**」。

**不与 `tests/unit/test_evidence_gate_l3.py` 重叠**：那一份在事实字典层判
「给定事实，三条规则怎么判」；本文件判的是循环侧。收口时不得把它算成本 plan 的产出。

**H1 / H2 不在这里**，在 `tests/unit/test_evidence_gate_single_hop_body.py`
（那份同时是 🔴 门禁的断言体，见它的模块头）。

判据全部落在**轨迹**与**假站点的请求记录**上，一条都不落在答案文本上。
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.explain import explain  # noqa: E402
from agenerp.explain.gate import USE_ANSWERING, USE_TOOL_PRECONDITION  # noqa: E402
from agenerp.explain.loop import (  # noqa: E402
    BREAKER_ACTION,
    EXCLUDED_TOOLS,
    STOP_ANSWERED,
    STOP_BREAKER,
    tool_schemas,
)
from agenerp.orchestration.circuit import BREAKER_MESSAGE, DENIAL_THRESHOLD  # noqa: E402
from agenerp.tools_readonly import READONLY_TOOL_NAMES  # noqa: E402


def run(question, script, *, site=None, max_turns=8, doctypes=None):
    site = site if site is not None else fakes.explain_site()
    result = explain(
        question,
        task_class="explain",
        client=fakes.client_for(site),
        models=fakes.models(),
        config=fakes.config(),
        transport=fakes.ScriptedModel(script),
        doctypes=list(fakes.SCOPE_CANDIDATES if doctypes is None else doctypes),
        max_turns=max_turns,
    )
    return site, result


# ── 补齐证据后放行 ──────────────────────────────────────────────────────────

TRACE_A = [
    fakes.tools_step(fakes.call("doc.get", doctype="Sales Order", name=fakes.ORDER_A)),
    fakes.answer_step(f"订单 {fakes.ORDER_A} 一切正常。"),
    fakes.tools_step(fakes.call("doc.links", doctype="Sales Order", name=fakes.ORDER_A)),
    fakes.tools_step(
        fakes.call("doc.get", doctype="Delivery Note", name=fakes.SUBMITTED_DN)
    ),
    fakes.answer_step(f"订单已由发货单 {fakes.SUBMITTED_DN} 发出，工单还是草稿。"),
]


def test_answer_is_released_once_the_evidence_is_complete():
    """同一条会话继续取证到三条规则全满足，answer 被接受 —— 门禁不是「永远拒」。"""
    _, result = run(f"帮我看看 {fakes.ORDER_A} 现在什么情况？", TRACE_A)

    assert result.accepted is True
    assert result.trace.stopped == STOP_ANSWERED
    assert result.answer.startswith("订单已由发货单")
    assert len(result.trace.forced_continues) == 1, "补齐之前恰好被拦过一次"
    assert result.trace.gate_checks[-1]["failed"] == []


def test_l3_requires_every_inbound_voucher_of_a_quantity_in_the_answer():
    """L3 在循环里真的起作用：答案报了 `Bin` 上的数量 → 全部入库凭证逐张 `doc.get` 之前不放行。

    出库那张与已取消那张**都不在要求集里** —— 规则要的是「使数量增加的凭证」。
    """
    _, blocked = run(
        "成品仓里那个主力型号现在有多少台？",
        [fakes.answer_step(f"成品仓现在有 {fakes.BIN_QTY:,} 台。")],
        max_turns=2,
    )
    assert blocked.accepted is False
    required = blocked.trace.gate_checks[0]["facts"][
        "inbound_vouchers_of_quantities_in_answer"
    ]
    assert required == [fakes.INBOUND_A, fakes.INBOUND_B]
    assert fakes.SUBMITTED_DN not in required

    _, released = run(
        "成品仓里那个主力型号现在有多少台？",
        [
            fakes.tools_step(
                fakes.call("doc.get", "c1", doctype="Stock Entry", name=fakes.INBOUND_A),
                fakes.call("doc.get", "c2", doctype="Stock Entry", name=fakes.INBOUND_B),
            ),
            fakes.answer_step(f"成品仓现在有 {fakes.BIN_QTY:,} 台。"),
        ],
    )
    assert released.accepted is True
    assert released.trace.gate_checks[-1]["failed"] == []


# ── D2：两处求值取自同一份事实采集面 ────────────────────────────────────────

TRACE_B = [
    fakes.tools_step(fakes.call("doc.links", doctype="Sales Order", name=fakes.ORDER_B)),
    fakes.answer_step(f"订单 {fakes.ORDER_B} 的下游只有一张草稿工单，没有已提交的发货单。"),
]


def test_both_evaluations_share_one_evidence_surface_object():
    """D2 的绑定断言。**一条轨迹不够** —— 另写一份「碰巧在这条轨迹上答案相同」的
    采集面也骗得过它，所以取两条会让错误实现分叉的轨迹，再加一条**同一性**断言。

    分叉点：轨迹 A 的下游有一张**已提交**发货单（L2 因此要求 `doc.get`），
    轨迹 B 的下游只有**草稿**工单（L2 因此空过）。
    """
    _, a = run(f"帮我看看 {fakes.ORDER_A} 现在什么情况？", TRACE_A)
    _, b = run(f"帮我看看 {fakes.ORDER_B} 现在什么情况？", TRACE_B)

    assert a.trace.gate_checks[-1]["facts"]["submitted_downstream_documents"] == [
        fakes.SUBMITTED_DN
    ]
    assert b.trace.gate_checks[-1]["facts"]["submitted_downstream_documents"] == []
    assert b.accepted is True
    assert [c["tool"] for c in b.trace.tool_calls] == ["doc.links"]

    for result in (a, b):
        surface = result.surface
        # 同一性：两处的用途留痕落在**同一个对象**上，不是两个值相等的对象。
        assert surface.used_for(USE_TOOL_PRECONDITION) == result.trace.execute_calls
        assert surface.used_for(USE_ANSWERING) == len(result.trace.gate_checks)
        assert surface.uses[0] == USE_TOOL_PRECONDITION
        assert USE_ANSWERING in surface.uses
        ids = {row["surface_id"] for row in result.trace.tool_calls}
        ids |= {row["surface_id"] for row in result.trace.gate_checks}
        assert ids == {surface.surface_id}


def test_the_two_trajectories_would_diverge_for_a_second_surface():
    """分叉本身要可见：两条轨迹的 ② 事实字典在 L2 那一项上**必须不同**。"""
    _, a = run(f"帮我看看 {fakes.ORDER_A} 现在什么情况？", TRACE_A)
    _, b = run(f"帮我看看 {fakes.ORDER_B} 现在什么情况？", TRACE_B)

    key = "submitted_downstream_documents"
    assert a.trace.gate_checks[-1]["facts"][key] != b.trace.gate_checks[-1]["facts"][key]


# ── 开场注入：断言落在假站点的请求记录上 ────────────────────────────────────


def test_opening_injection_actually_hits_the_site_before_the_model_speaks():
    """P1.3 的 M6 教训：**相等断言挡不住装配路径上把标志位写死成正确值**。

    所以这条判据不看 `OpeningPack` 的标志位，只看假站点收到了什么、什么时候收到的。
    """
    site, result = run(f"帮我看看 {fakes.ORDER_A} 现在什么情况？", TRACE_A)

    probes = [i for i, r in enumerate(site.requests) if "has_permission" in r.url]
    assert len(probes) == len(fakes.SCOPE_CANDIDATES)
    others = [i for i, r in enumerate(site.requests) if "has_permission" not in r.url]
    assert max(probes) < min(others), "注入必须发生在任何取证请求之前"

    # 注入代价照记 —— 不记就是把「自动注入」变成一笔隐性成本。
    assert result.trace.opening_request_count == len(fakes.SCOPE_CANDIDATES)
    assert [row["doctype"] for row in result.opening.scope] == sorted(
        fakes.SCOPE_CANDIDATES
    )
    assert result.trace.execute_calls == 3, "注入那一次不计进循环发起的 execute 次数"


def test_permission_scope_is_not_in_the_model_facing_tool_surface():
    """D3：`permission.scope` 不进模型可见的工具面（开场注入已确定性化那一步）。"""
    names = {schema["function"]["name"] for schema in tool_schemas()}
    assert "permission_scope" not in names
    assert EXCLUDED_TOOLS == ("permission.scope",)
    # 其余契约**逐个**都在：工具声明由契约生成，契约表变了这里自动跟着变。
    assert names == {
        name.replace(".", "_") for name in READONLY_TOOL_NAMES if name not in EXCLUDED_TOOLS
    }


# ── H3：熔断真的在循环里被调用到 ────────────────────────────────────────────

DENIED_DOCTYPE = "GL Entry"


def _denial_batch(count):
    return fakes.tools_step(
        *[
            fakes.call("doc.get", f"c{i}", doctype=DENIED_DOCTYPE, name=f"GL-{i}")
            for i in range(1, count + 1)
        ]
    )


def test_breaker_stops_the_loop_after_five_consecutive_denials():
    """H3。**计数单位是循环发起的 `execute` 次数**，不是假站点收到的 HTTP 请求数
    （一次 `execute` 可能发多个请求）。"""
    site = fakes.explain_site()
    site.forbidden = {DENIED_DOCTYPE}
    _, result = run("这个月的毛利怎么样？", [_denial_batch(DENIAL_THRESHOLD + 1)], site=site)

    assert result.trace.execute_calls == DENIAL_THRESHOLD
    assert result.breaker.tripped is True
    assert result.trace.stopped == STOP_BREAKER
    assert result.accepted is False
    assert result.answer.startswith(BREAKER_MESSAGE)
    # 清单那一半不许是空的，且要**点名 DocType**（D6）。
    assert result.breaker.denied == (DENIED_DOCTYPE,)
    assert f"read:{DENIED_DOCTYPE}" in result.answer


def test_breaker_event_is_recorded_into_the_conversation_session():
    """D4：熔断事件落进会话轨迹（**本地可回放的轨迹，不是站点侧审计**）。"""
    site = fakes.explain_site()
    site.forbidden = {DENIED_DOCTYPE}
    _, result = run("这个月的毛利怎么样？", [_denial_batch(DENIAL_THRESHOLD + 1)], site=site)

    events = [a for a in result.session.actions if a.tool == BREAKER_ACTION]
    assert len(events) == 1
    assert events[0].params["streak"] == DENIAL_THRESHOLD
    assert "权限探测事件" in events[0].diff_summary
    assert f"read:{DENIED_DOCTYPE}" in events[0].diff_summary
    assert result.trace.breaker_events[0]["denied"] == [DENIED_DOCTYPE]


def test_non_permission_failures_neither_count_nor_clear_the_streak():
    """站点故障不是越权证据，也不是「这次访问合法」的证据（§7.4 表那一行的循环侧对照）。

    剧本：403 · 403 · **404** · 403 · 403 · 403 —— 若 404 被计进去，循环会在第 5 次
    就刹车；若 404 清零，循环到第 6 次也刹不住。两种坏实现都会让本条转红。
    """
    site = fakes.explain_site()
    site.forbidden = {DENIED_DOCTYPE}
    script = [
        fakes.tools_step(
            fakes.call("doc.get", "c1", doctype=DENIED_DOCTYPE, name="GL-1"),
            fakes.call("doc.get", "c2", doctype=DENIED_DOCTYPE, name="GL-2"),
            fakes.call("doc.get", "c3", doctype="Sales Order", name="SAL-ORD-9999-99999"),
            fakes.call("doc.get", "c4", doctype=DENIED_DOCTYPE, name="GL-4"),
            fakes.call("doc.get", "c5", doctype=DENIED_DOCTYPE, name="GL-5"),
            fakes.call("doc.get", "c6", doctype=DENIED_DOCTYPE, name="GL-6"),
            fakes.call("doc.get", "c7", doctype=DENIED_DOCTYPE, name="GL-7"),
        )
    ]
    _, result = run("这个月的毛利怎么样？", script, site=site)

    missing = [c for c in result.trace.tool_calls if c["params"].get("name", "").endswith("99999")]
    assert missing and "HTTP 404" in missing[0]["reasons"][0]
    assert result.trace.execute_calls == 6, "404 既没被计数、也没有把连击清零"
    assert result.breaker.tripped is True


def test_a_successful_call_clears_the_streak():
    """「连续」不是「累计」：中间成功一次即清零，否则正常会话会被误刹。"""
    site = fakes.explain_site()
    site.forbidden = {DENIED_DOCTYPE}
    script = [
        fakes.tools_step(
            *[
                fakes.call("doc.get", f"d{i}", doctype=DENIED_DOCTYPE, name=f"GL-{i}")
                for i in range(1, DENIAL_THRESHOLD)
            ],
            fakes.call("doc.get", "ok", doctype="Sales Order", name=fakes.ORDER_A),
            *[
                fakes.call("doc.get", f"e{i}", doctype=DENIED_DOCTYPE, name=f"GL-2{i}")
                for i in range(1, DENIAL_THRESHOLD)
            ],
        ),
        fakes.answer_step("查不动。"),
    ]
    _, result = run("这个月的毛利怎么样？", script, site=site)

    assert result.breaker.tripped is False
    assert result.trace.execute_calls == DENIAL_THRESHOLD * 2 - 1
    assert result.trace.stopped != STOP_BREAKER


# ── 会话落盘与用量聚合 ──────────────────────────────────────────────────────


def test_every_turn_lands_in_the_conversation_session():
    """会话侧：每一轮都落 `Turn` / `ToolCall`，用量走 `Usage.plus()`（不自己写加法）。"""
    _, result = run(f"帮我看看 {fakes.ORDER_A} 现在什么情况？", TRACE_A)

    tool_calls = [call for turn in result.session.turns for call in turn.tool_calls]
    assert [c.tool for c in tool_calls] == [c["tool"] for c in result.trace.tool_calls]
    assert all(c.ok for c in tool_calls)

    model_turns = [t for t in result.session.turns if t.usage.total]
    assert len(model_turns) == 5, "剧本里的每一次模型回复都留了一轮"
    assert result.usage == result.session.usage_total
    assert result.usage.prompt == 31 * 5
    assert result.usage.completion == 17 * 5
    assert result.usage.reasoning == 11 * 5
