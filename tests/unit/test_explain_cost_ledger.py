"""P1.7 **成本记账**那一组判据（D-18）—— 判的是「**每次模型调用的账都在，且对得上端点自报的数**」。

⚠️ **失控闸的判据不在这里**，在 `tests/unit/test_explain_runaway_guard.py`。
D-18 逐字「两者的判据分开写，不许合并」，所以两组判据分两个文件、**互不 import 对方文件里的夹具**。
两边共用的只有 P1.4 已交付的公共假件 `tests/unit/explain_fakes.py` —— 那不在禁止之列
（禁的是两组判据互相依赖，不是禁止复用既有公共假件）。

**本文件不判任何阈值**：D-18 取消的就是阈值，账本里连一个「超了就……」的分支都不该有。
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.explain import explain  # noqa: E402
from agenerp.explain.ledger import (  # noqa: E402
    CALL_ANSWER,
    CALL_ERROR,
    CALL_TOOLS,
    CallLedger,
)
from agenerp.explain.loop import (  # noqa: E402
    STOP_ANSWERED,
    STOP_BREAKER,
    STOP_MAX_TURNS,
    STOP_MODEL_ERROR,
    ExplainLoop,
)
from agenerp.orchestration.circuit import DENIAL_THRESHOLD  # noqa: E402
from agenerp.routing import route  # noqa: E402
from agenerp.routing.adapter import Reply, Usage, usage_of  # noqa: E402
from agenerp.routing.errors import RoutingError  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE_RUN = REPO_ROOT / "docs/evidence/p1-explain/live-run-01.json"


# ── 端点回包的原始形状（**不是** 解析后的 `Usage`）────────────────────────────


def body_usage(prompt: int, completion: int, reasoning: int | None) -> dict:
    """端点自报的 `usage`。`reasoning is None` → 整个 `completion_tokens_details` 都不回
    （非推理模型的形状），`usage_of()` 对它的口径是「缺失回 0」。"""
    raw: dict = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
    if reasoning is not None:
        raw["completion_tokens_details"] = {"reasoning_tokens": reasoning}
    return raw


def tools_body(*calls: dict, usage: dict) -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": None, "tool_calls": list(calls)},
                "finish_reason": "tool_calls",
            }
        ],
        "usage": usage,
    }


def answer_body(text: str, *, usage: dict) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": usage,
    }


def empty_body(*, usage: dict) -> dict:
    """「空回答」：端点**已经回包、token 已经真的花掉**，但既没文本也没工具调用。
    `ChatAdapter` 对它的处置是抛 `RoutingError`（不降级成空回答）—— H1 ①b 就是这条路径。"""
    return {
        "choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "length"}],
        "usage": usage,
    }


class CountingTransport:
    """**自己计数**的假 transport。计数探针判的是可观测量：
    `chat()` 实际被调了几次 vs. 账本上有几条 —— 不是「读代码确认都写了」。"""

    def __init__(self, bodies: list[dict], *, raise_urlerror_at: int | None = None) -> None:
        self.bodies = list(bodies)
        self.raise_urlerror_at = raise_urlerror_at
        self.calls = 0

    def __call__(self, payload: dict) -> dict:
        self.calls += 1
        if self.raise_urlerror_at is not None and self.calls >= self.raise_urlerror_at:
            raise urllib.error.URLError("假端点：连不上")
        return self.bodies[min(self.calls - 1, len(self.bodies) - 1)]


def loop_for(transport, *, site=None, max_turns=8, breaker=None) -> ExplainLoop:
    """直接构造 `ExplainLoop` —— 判据侧要摆四条出口就得摆得出来。
    产品入口那一条**另有一例**（见 `test_the_product_entry_keeps_the_same_ledger`）。"""
    site = site if site is not None else fakes.explain_site()
    adapter = route(
        "explain", models=fakes.models(), config=fakes.config(), transport=transport
    )
    return ExplainLoop(
        adapter=adapter,
        client=fakes.client_for(site),
        max_turns=max_turns,
        doctypes=list(fakes.SCOPE_CANDIDATES),
        breaker=breaker,
    )


U = body_usage(31, 17, 11)

GET_ORDER = fakes.call("doc.get", "c0", doctype="Sales Order", name=fakes.ORDER_A)
GET_LINKS = fakes.call("doc.links", "c1", doctype="Sales Order", name=fakes.ORDER_A)
GET_DN = fakes.call("doc.get", "c2", doctype="Delivery Note", name=fakes.SUBMITTED_DN)

ANSWER_TEXT = f"订单已由发货单 {fakes.SUBMITTED_DN} 发出，工单还是草稿。"

DENIED_DOCTYPE = "GL Entry"


def denial_batch(count: int) -> dict:
    return tools_body(
        *[
            fakes.call("doc.get", f"d{i}", doctype=DENIED_DOCTYPE, name=f"GL-{i}")
            for i in range(1, count + 1)
        ],
        usage=U,
    )

ANSWERED_SCRIPT = [
    tools_body(GET_ORDER, usage=U),
    tools_body(GET_LINKS, usage=U),
    tools_body(GET_DN, usage=U),
    answer_body(ANSWER_TEXT, usage=U),
]


def session_usage_records(result) -> int:
    """`ConversationSession` 上**带 usage 的轮次**有几条 —— 那是 P1.4 留下的「载体」，
    不是账本。H1 判的就是这个载体在哪条出口上漏。"""
    return sum(1 for turn in result.session.turns if turn.usage != Usage())


def trace_usage_records(result) -> int:
    return sum(1 for turn in result.trace.turns if "usage" in turn)


# ── H1 · 四条出口逐条实测「漏账与否」，与 §6 的四条预测对照 ─────────────────
#
# ⚠️ 判的对象是 **P1.4 留下的两个载体**（`session.usage_total` / `trace.turns`），
# 不是本 plan 新增的账本 —— H1 问的正是「新账本非做不可吗」。


def test_h1_1a_model_error_without_a_reply_leaks_from_the_session_carrier():
    """H1 ①a：连不上端点 —— 那次**真的没有 usage**，记 0 是对的，但**调用发生过**。

    预测「漏账」→ **吻合**：`session` 上一条 usage 记录都没有（那次调用没成为一轮对话），
    而账本上有一条。"""
    transport = CountingTransport([answer_body("不会用到", usage=U)], raise_urlerror_at=1)
    result = loop_for(transport).run("空账问题")

    assert result.trace.stopped == STOP_MODEL_ERROR
    assert transport.calls == 1
    assert session_usage_records(result) == 0  # 载体漏了
    assert len(result.cost_ledger) == 1  # 账本没漏

    entry = result.cost_ledger.entries[0]
    assert entry.outcome == CALL_ERROR
    assert entry.usage == Usage()  # 端点没回包 → 三项 0
    assert entry.endpoint_total is None  # 「不知道」不写成「对得上」
    assert entry.total_matches_endpoint is False


def test_h1_1b_the_empty_answer_path_keeps_the_real_tokens():
    """H1 ①b：端点**已经回包、usage 真实存在**，但 `ChatAdapter` 抛 `RoutingError`。

    预测「账本在这条路径上会系统性偏低」→ **不吻合了**：D1 选定 (i) 之后不再偏低。
    ⚠️ 预测原文保留在 §6，不回头改；这一条自此转为**守护性回归** ——
    `RoutingError.usage` 一旦被摘掉，本条立刻红。"""
    transport = CountingTransport([empty_body(usage=body_usage(15, 178, 173))])
    result = loop_for(transport).run("空回答问题")

    assert result.trace.stopped == STOP_MODEL_ERROR
    assert transport.calls == 1
    assert session_usage_records(result) == 0  # 载体照旧漏

    entry = result.cost_ledger.entries[0]
    assert entry.outcome == CALL_ERROR
    # D-11 实读的那个回包：回两个字也烧 173 reasoning token。**一个都不许丢。**
    assert entry.usage == Usage(prompt=15, completion=178, reasoning=173)
    assert entry.endpoint_total == 193
    assert entry.endpoint_reasoning == 173
    assert entry.total_matches_endpoint and entry.reasoning_matches_endpoint


def test_h1_2_breaker_stop_leaks_from_the_trace_carrier():
    """H1 ②：熔断早返回 —— 预测「`session` 记了、`trace.turns` 没记」→ **吻合**。

    熔断在**一次回复的批内**早返回，`_run_tools()` 那一段只 `with_turn` 不 `trace.turns.append`。"""
    site = fakes.explain_site()
    site.forbidden = {DENIED_DOCTYPE}
    transport = CountingTransport([denial_batch(DENIAL_THRESHOLD + 1)])
    result = loop_for(transport, site=site, max_turns=4).run("熔断问题")

    assert result.trace.stopped == STOP_BREAKER
    assert transport.calls == 1
    assert session_usage_records(result) == 1  # 载体①记了
    assert trace_usage_records(result) == 0  # 载体②漏了
    assert len(result.cost_ledger) == 1  # 账本没漏
    assert result.cost_ledger.entries[0].outcome == CALL_TOOLS


def test_h1_3_max_turns_does_not_leak():
    """H1 ③：`STOP_MAX_TURNS` —— 预测「不漏」→ **吻合**（每轮都走 `with_turn`）。"""
    transport = CountingTransport([tools_body(GET_ORDER, usage=U)])
    result = loop_for(transport, max_turns=3).run("跑飞问题")

    assert result.trace.stopped == STOP_MAX_TURNS
    assert transport.calls == 3
    assert session_usage_records(result) == 3  # 载体没漏
    assert len(result.cost_ledger) == 3


def test_h1_4_answered_does_not_leak():
    """H1 ④：`STOP_ANSWERED` —— 预测「不漏」→ **吻合**。"""
    transport = CountingTransport(ANSWERED_SCRIPT)
    result = loop_for(transport).run("正常问题")

    assert result.trace.stopped == STOP_ANSWERED
    assert session_usage_records(result) == transport.calls
    assert len(result.cost_ledger) == transport.calls


# ── 计数探针：`chat()` 被调了几次 == 账本上有几条 ───────────────────────────
#
# ⚠️ 判在**可观测量**上，不是「读代码确认四条出口都写了记账」。
# 假 transport **自己计数**，账本条数由产品代码产出，两个数字来自两个不同的地方。


@pytest.mark.parametrize(
    ("label", "bodies", "raise_at", "max_turns", "forbidden", "stopped", "expected_calls"),
    [
        ("answered", ANSWERED_SCRIPT, None, 8, None, STOP_ANSWERED, 4),
        ("max-turns", [tools_body(GET_ORDER, usage=U)], None, 3, None, STOP_MAX_TURNS, 3),
        (
            "permission-breaker",
            [denial_batch(DENIAL_THRESHOLD + 1)],
            None,
            4,
            DENIED_DOCTYPE,
            STOP_BREAKER,
            1,
        ),
        ("model-error", [empty_body(usage=body_usage(15, 178, 173))], None, 5, None,
         STOP_MODEL_ERROR, 1),
        ("model-error-no-reply", [answer_body("不会用到", usage=U)], 1, 5, None,
         STOP_MODEL_ERROR, 1),
    ],
)
def test_the_call_count_equals_the_ledger_length_on_every_exit(
    label, bodies, raise_at, max_turns, forbidden, stopped, expected_calls
):
    site = fakes.explain_site()
    if forbidden:
        site.forbidden = {forbidden}
    transport = CountingTransport(bodies, raise_urlerror_at=raise_at)
    result = loop_for(transport, site=site, max_turns=max_turns).run(f"{label} 问题")

    assert result.trace.stopped == stopped
    assert transport.calls == expected_calls
    assert len(result.cost_ledger) == transport.calls
    assert result.trace.as_dict()["cost_ledger"]["calls"] == transport.calls


def test_the_ledger_also_covers_the_path_that_comes_in_through_insight():
    """§1.8：洞察 Agent 的归因**走同一条解释循环**，所以账本自动覆盖它。

    ⚠️ 不加这一条就只证明了「直接调解释循环时账在」，而记账口径改错会**同时**影响两个 Agent。"""
    import inspection_fakes as insight_fakes

    from agenerp.inspection import inspect_site, minimal_rules
    from agenerp.insight import attribute

    site = insight_fakes.seed_site()
    report = inspect_site(minimal_rules(), insight_fakes.client_for(site))
    assert len(report.hits) == 1

    transport = CountingTransport([answer_body("成品仓积压 1,010 台。", usage=U)])
    attributed = attribute(
        report.hits[0],
        client=insight_fakes.client_for(site),
        models=fakes.models(),
        config=fakes.config(),
        transport=transport,
        doctypes=list(insight_fakes.ATTRIBUTION_DOCTYPES),
        max_turns=3,
    )

    ledger = attributed.result.cost_ledger
    assert transport.calls >= 1
    assert len(ledger) == transport.calls
    assert ledger.total.reasoning == 11 * transport.calls
    # 序列化后的 trace 也带着账 —— `agenerp/insight/attribution.py` 侧消费的正是这个字典。
    assert attributed.trace["cost_ledger"]["calls"] == transport.calls


# ── H2a · 重放 P1.4 那一跑的七次调用（**本项目实测**，D-16）──────────────────
#
# ⚠️ 下面 21 个数字与四个汇总数**逐字写死在判据里**，不是从夹具文件读出来再自比 ——
# 从文件读出来再和文件比是恒真的。夹具只提供**原始回包形状**，期望值在这里。
# ⚠️ 逐条 `total` 判的是**端点自报的 `endpoint_total_tokens`**，不是 `Usage.total`
# 那个恒真式（`prompt + completion == total` 那种写法判了等于没判）。
# ⚠️ **本节不算「与端点独立核对」**：期望值与夹具同源于同一份落盘文件。
# 独立核对那份功劳归 H2b（原始 body 走完整解析链路）与 H5（活端点）。

LIVE_CALLS = (
    # (prompt, completion, reasoning)  —— 七条 × 三项 = 21 个字面期望值
    (1067, 207, 150),
    (3291, 180, 123),
    (3472, 225, 116),
    (6458, 513, 393),
    (6989, 516, 458),
    (8624, 994, 787),
    (10984, 1675, 757),
)
LIVE_TOTALS = (40885, 4310, 2784, 45195)


def live_run_bodies() -> list[dict]:
    """从 P1.4 的证据文件重建**端点原始回包形状**的 usage。

    ⚠️ `docs/evidence/p1-explain/live-run-01.json` 是 P1.4 的证据，**只读，一个字不改**。"""
    payload = json.loads(LIVE_RUN.read_text(encoding="utf-8"))
    bodies = []
    for row in payload["per_call_ledger"]:
        parsed = row["usage"]
        bodies.append(
            {
                "prompt_tokens": parsed["prompt"],
                "completion_tokens": parsed["completion"],
                "total_tokens": row["endpoint_total_tokens"],
                "completion_tokens_details": {
                    "reasoning_tokens": row["endpoint_reasoning_tokens"]
                },
            }
        )
    return bodies


def replay(bodies, *, strip_reasoning: bool = False, ratio: float | None = None) -> CallLedger:
    """把一批**端点原始 usage** 喂进账本。

    `strip_reasoning` / `ratio` 是 H3 的两个假实现开关：前者把 reasoning 那一位置零
    （D-18 点名的「只记 completion 不记 reasoning」），后者让 reasoning 恒等于 completion
    的某个比例（只有一个数据集时能蒙混过关的那种）。**产品代码一行不改**，
    假实现摆在判据侧 —— 改产品代码去反测，反测完就得记得改回来。"""
    ledger = CallLedger()
    for index, raw in enumerate(bodies, start=1):
        parsed = usage_of(raw)
        if strip_reasoning:
            parsed = Usage(parsed.prompt, parsed.completion, 0)
        elif ratio is not None:
            parsed = Usage(parsed.prompt, parsed.completion, int(parsed.completion * ratio))
        ledger.record_reply(
            index,
            Reply(text="", usage=parsed, model="qwen3.6-plus", raw={"usage": raw}),
        )
    return ledger


def assert_matches_live_run(ledger: CallLedger) -> None:
    """H2a 的判定体。**H3 的两个假实现要打红的就是它。**"""
    assert len(ledger) == 7
    for entry, (prompt, completion, reasoning) in zip(ledger.entries, LIVE_CALLS, strict=True):
        assert entry.usage.prompt == prompt
        assert entry.usage.completion == completion
        assert entry.usage.reasoning == reasoning
        # 逐条对**端点自报的 total**，不是恒真式。
        assert entry.usage.total == entry.endpoint_total
        assert entry.usage.reasoning == entry.endpoint_reasoning
    total = ledger.total
    assert (total.prompt, total.completion, total.reasoning, total.total) == LIVE_TOTALS


def test_h2a_the_seven_real_calls_replay_entry_by_entry():
    assert_matches_live_run(replay(live_run_bodies()))


def test_h2a_the_evidence_file_still_reports_the_numbers_the_criteria_expect():
    """夹具漂移就是红。**这一条判的是文件，上一条判的是账本**，两件事。"""
    payload = json.loads(LIVE_RUN.read_text(encoding="utf-8"))
    assert payload["usage_total"] == {
        "prompt": LIVE_TOTALS[0],
        "completion": LIVE_TOTALS[1],
        "reasoning": LIVE_TOTALS[2],
        "total": LIVE_TOTALS[3],
    }
    assert len(payload["per_call_ledger"]) == len(LIVE_CALLS)


# ── H2b · 原始 OpenAI 形状 body 走完整 `adapter.chat → 账本` 链路 ────────────
#
# ⚠️ **不可省的理由**：`live-run-01.json` 存的是**解析后的 `Usage`**、没有原始回包，
# 而账本若实现成「记的就是 `reply.usage`」，H2a 那条「与端点自报相等」就是恒真的。
# 只有让原始 body 从假 transport 出发、走完 `usage_of()` 这段解析再进账本，
# 才判得到解析这一段。断言对象是**这里写死的字面数字**。


def test_h2b_a_raw_endpoint_body_survives_the_whole_chain():
    bodies = [
        tools_body(GET_ORDER, usage=body_usage(1067, 207, 150)),
        tools_body(GET_LINKS, usage=body_usage(3291, 180, 123)),
        tools_body(GET_DN, usage=body_usage(3472, 225, 116)),
        answer_body(ANSWER_TEXT, usage=body_usage(6458, 513, 393)),
    ]
    transport = CountingTransport(bodies)
    result = loop_for(transport).run("完整链路问题")

    assert result.trace.stopped == STOP_ANSWERED
    assert transport.calls == 4
    ledger = result.cost_ledger
    assert [(e.usage.prompt, e.usage.completion, e.usage.reasoning) for e in ledger.entries] == [
        (1067, 207, 150),
        (3291, 180, 123),
        (3472, 225, 116),
        (6458, 513, 393),
    ]
    assert [e.endpoint_total for e in ledger.entries] == [1274, 3471, 3697, 6971]
    assert [e.endpoint_reasoning for e in ledger.entries] == [150, 123, 116, 393]
    assert all(e.total_matches_endpoint and e.reasoning_matches_endpoint for e in ledger.entries)
    assert [e.outcome for e in ledger.entries] == [
        CALL_TOOLS, CALL_TOOLS, CALL_TOOLS, CALL_ANSWER,
    ]
    total = ledger.total
    assert (total.prompt, total.completion, total.reasoning, total.total) == (
        14288, 1125, 782, 15413,
    )


def test_h2b_a_reply_without_reasoning_details_is_not_folded_into_completion():
    """非推理模型的回包形状（没有 `completion_tokens_details`）——
    `usage_of()` 的口径是「缺失回 0，**不回退成把它算进 completion**」。"""
    transport = CountingTransport([answer_body(ANSWER_TEXT, usage=body_usage(120, 40, None))])
    result = loop_for(transport).run("非推理模型问题")

    entry = result.cost_ledger.entries[0]
    assert entry.usage == Usage(prompt=120, completion=40, reasoning=0)
    assert entry.endpoint_total == 160
    assert entry.endpoint_reasoning == 0
    assert entry.total_matches_endpoint and entry.reasoning_matches_endpoint


# ── H3 · 假实现反测（**两个数据集**）──────────────────────────────────────
#
# 数据集①：H2a 的真实重放（七条、reasoning 全 > 0）；
# 数据集②：一份 `reasoning == 0` 的合成用例（非推理模型形态）。
# ⚠️ 只有①时，「reasoning 恒等于 completion 的某个比例」的假实现可能蒙混过关。

SYNTHETIC = [body_usage(120, 40, None), body_usage(77, 13, None)]


def assert_synthetic_reasoning_is_zero(ledger: CallLedger) -> None:
    assert [e.usage.reasoning for e in ledger.entries] == [0, 0]
    assert [e.endpoint_reasoning for e in ledger.entries] == [0, 0]
    assert all(e.reasoning_matches_endpoint for e in ledger.entries)
    # **第二个数据集的汇总与第一个不同** —— 汇总写死成常量（M3）在这里当场红。
    total = ledger.total
    assert (total.prompt, total.completion, total.reasoning, total.total) == (197, 53, 0, 250)


def test_h3_the_synthetic_zero_reasoning_dataset_is_green():
    assert_synthetic_reasoning_is_zero(replay(SYNTHETIC))


def test_h3_dropping_reasoning_turns_the_real_replay_red():
    """M1：只记 `completion` 不记 `reasoning`（D-18 逐字点名的假实现）。"""
    with pytest.raises(AssertionError):
        assert_matches_live_run(replay(live_run_bodies(), strip_reasoning=True))


def test_h3_a_proportional_reasoning_fake_also_turns_both_datasets_red():
    """「reasoning = completion × 比例」这种假实现 —— **两个数据集都要打红**。

    ⚠️ 真实重放里 reasoning/completion 的比值七条各不相同（150/207 … 757/1675），
    所以①打得红；②是 `reasoning == 0` 的形态，比例法在那里也不成立。"""
    with pytest.raises(AssertionError):
        assert_matches_live_run(replay(live_run_bodies(), ratio=0.7))
    with pytest.raises(AssertionError):
        assert_synthetic_reasoning_is_zero(replay(SYNTHETIC, ratio=0.7))


def test_h3_the_real_replay_is_green_without_the_fake():
    """反测的另一半：**不加假实现时这两条判定体是绿的** —— 否则 `pytest.raises`
    只是在证明「判定体永远红」。"""
    assert_matches_live_run(replay(live_run_bodies()))
    assert_synthetic_reasoning_is_zero(replay(SYNTHETIC))


# ── D2 · 账本与 `session.usage_total` 不许各算各的（M7 的靶子）──────────────
#
# 选定 (B)：`ExplainResult.usage` **保留现状**（读 `session.usage_total`，P1.4 的既有导出面），
# 账本另立一份，并由下面这两条钉住两者的关系：
#   · 正常路径（每次调用都成为了一轮对话）→ **逐项相等**；
#   · 异常路径（抛错那次没有 turn）→ **账本 ≥ session**，且端点回过包时**严格大于**。
# 权威面写死在落点节 §7.11：**要算钱就读账本。**


@pytest.mark.parametrize(
    ("label", "bodies", "max_turns", "forbidden"),
    [
        ("answered", ANSWERED_SCRIPT, 8, None),
        ("max-turns", [tools_body(GET_ORDER, usage=U)], 3, None),
        ("permission-breaker", [denial_batch(DENIAL_THRESHOLD + 1)], 4, DENIED_DOCTYPE),
    ],
)
def test_d2_on_normal_paths_the_ledger_and_the_session_agree(
    label, bodies, max_turns, forbidden
):
    site = fakes.explain_site()
    if forbidden:
        site.forbidden = {forbidden}
    result = loop_for(CountingTransport(bodies), site=site, max_turns=max_turns).run(label)

    assert result.cost_ledger.total == result.usage
    assert result.usage != Usage()  # 两个空 `Usage` 相等是恒真的，先排掉


def test_d2_on_the_error_path_the_ledger_is_strictly_larger_than_the_session():
    """抛错那一次**没有 turn**，所以 `session.usage_total` 必然少算 —— 这正是账本存在的理由。"""
    bodies = [
        tools_body(GET_ORDER, usage=body_usage(1000, 100, 60)),
        empty_body(usage=body_usage(15, 178, 173)),
    ]
    result = loop_for(CountingTransport(bodies)).run("先取证再空回答")

    assert result.trace.stopped == STOP_MODEL_ERROR
    assert result.usage == Usage(prompt=1000, completion=100, reasoning=60)
    assert result.cost_ledger.total == Usage(prompt=1015, completion=278, reasoning=233)
    ledger, session = result.cost_ledger.total, result.usage
    assert ledger.prompt > session.prompt
    assert ledger.completion > session.completion
    assert ledger.reasoning > session.reasoning


# ── M8 · 账本记的是「实际回包」，不是「打算调用」 ───────────────────────────


def test_m8_every_entry_carries_the_usage_of_that_very_reply():
    """发请求前先记一条 0、事后不回填的实现 —— 在这里当场红。

    每条记录的三项**逐条**等于该次回包自报的数，且**没有一条是全 0 的**。"""
    per_call = [(1067, 207, 150), (3291, 180, 123), (3472, 225, 116), (6458, 513, 393)]
    bodies = [
        tools_body(GET_ORDER, usage=body_usage(*per_call[0])),
        tools_body(GET_LINKS, usage=body_usage(*per_call[1])),
        tools_body(GET_DN, usage=body_usage(*per_call[2])),
        answer_body(ANSWER_TEXT, usage=body_usage(*per_call[3])),
    ]
    result = loop_for(CountingTransport(bodies)).run("逐条对账问题")

    entries = result.cost_ledger.entries
    assert len(entries) == len(per_call)
    for entry, (prompt, completion, reasoning) in zip(entries, per_call, strict=True):
        assert (entry.usage.prompt, entry.usage.completion, entry.usage.reasoning) == (
            prompt, completion, reasoning,
        )
        assert entry.usage != Usage()
    assert [e.index for e in entries] == [1, 2, 3, 4]
    assert {e.model for e in entries} == {"fake-explainer"}


def test_the_product_entry_keeps_the_same_ledger():
    """产品入口 `explain(...)` 上账本照样在 —— 判据不许只在自己构造的 `ExplainLoop` 上成立。"""
    site = fakes.explain_site()
    transport = CountingTransport(ANSWERED_SCRIPT)
    result = explain(
        "产品入口问题",
        task_class="explain",
        client=fakes.client_for(site),
        models=fakes.models(),
        config=fakes.config(),
        transport=transport,
        doctypes=list(fakes.SCOPE_CANDIDATES),
        max_turns=8,
    )

    assert result.trace.stopped == STOP_ANSWERED
    assert len(result.cost_ledger) == transport.calls == 4
    assert result.cost_ledger.total == result.usage


# ── D-18 的底线：**记账，不拦截** ───────────────────────────────────────────


def test_the_ledger_never_blocks_anything():
    """账本里**没有阈值、没有任何「超了就……」的分支**（D-18 逐字）。

    判据形态：喂一份大到离谱的账，跑完照样 `answered`、照样把答案交出去。
    ⚠️ 这一条防的是「将来有人顺手在账本里加一条拦截」——那是 D-18 明令取消的东西。"""
    huge = body_usage(10_000_000, 5_000_000, 4_000_000)
    transport = CountingTransport(
        [tools_body(GET_ORDER, usage=huge), tools_body(GET_LINKS, usage=huge),
         tools_body(GET_DN, usage=huge), answer_body(ANSWER_TEXT, usage=huge)]
    )
    result = loop_for(transport).run("巨额账问题")

    assert result.trace.stopped == STOP_ANSWERED
    assert result.accepted is True
    assert result.cost_ledger.total.total == 4 * 15_000_000


# ── D1 (i) · `RoutingError` 上那一位结构化 `usage` 的契约 ───────────────────


def test_d1_a_routing_error_carrying_usage_lands_on_the_ledger_as_real_numbers():
    """账本对 `RoutingError.usage` 的读法：**有就记真数，没有就记 0 且 `endpoint_*` 为 `None`**。

    ⚠️ `errors.py` **不 import 本包任何模块**（那会造成 adapter ↔ errors 循环 import），
    所以挂上来的是**端点自报的原始 dict**，解析仍归 `usage_of()` 那一处。"""
    ledger = CallLedger()
    carried = ledger.record_error(
        1, "qwen3.6-plus", RoutingError("空回答", usage=body_usage(15, 178, 173))
    )
    assert carried.usage == Usage(prompt=15, completion=178, reasoning=173)
    assert carried.endpoint_total == 193 and carried.endpoint_reasoning == 173

    blind = ledger.record_error(2, "qwen3.6-plus", RoutingError("连不上端点"))
    assert blind.usage == Usage()
    assert blind.endpoint_total is None and blind.endpoint_reasoning is None
    assert blind.total_matches_endpoint is False

    assert len(ledger) == 2
    assert ledger.total == Usage(prompt=15, completion=178, reasoning=173)
    assert [e.outcome for e in ledger.entries] == [CALL_ERROR, CALL_ERROR]
