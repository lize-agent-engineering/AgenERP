"""🔴 WBS §4 P1.7 那**两条**验收的**断言体**（P1.7 / D-18）。

**这个文件是交接件。** 红线 1 禁止 loop 创建 `tests/gates/**` 下的任何文件，所以门禁那两份
由**人**创建；人只需按路径加载本文件，**断言体不重写**（先例：P1.0a 的
`tests/gates/test_tool_execution_live.py`，commit `3b6d071`，`Gates-Change-Approved-By: lize`；
P1.4 的 `tests/unit/test_evidence_gate_single_hop_body.py`；P1.5 同形态）。

⚠️ **两条 🔴 的措辞照实，不许含糊**（`docs/masterplan/02-WBS.md` §4 P1.7 行实读）：

| # | 🔴 | 文件路径 | 本文件里的节 |
|---|---|---|---|
| 一 | 断言**成本可观测**：三项都记了、能按解释汇总、缺任一项即红 | `tests/gates/test_explain_cost_accounting.py`（**有名**） | §A |
| 二 | **失控闸另算**：单次解释的工具调用轮数上限仍要有 | **没有给文件路径**（**未命名**） | §B |

→ 收口措辞因此是「**一条有名、一条未命名，两条的断言体都已交付**」，
**不是**「一个不存在的文件未创建」。

⚠️ **两节分开写，不合并**（D-18 逐字「两者的判据分开写，不许合并」）。
人若要建两个门禁文件，各加载各的那一节即可。

⚠️ **关于第二条 🔴 的字面措辞**：WBS 与 D-18 都写「工具调用**轮数**上限」，
而本 plan 按实读把它落成「**工具调用**那一维」（轮数已由 `max_turns` 占用，
一次回复可携带 K 个 `tool_call`，轮数根本不设限于此）。
**loop 不声称满足了 WBS 的字面措辞** —— 人若按字面读作「轮数」，须回到轮数口径重做。
重读留痕见 plan `2026-08-24-2109-2` 的 D3 与 `docs/architecture/module-boundaries.md` §7.11。

给人的加载片段（放进门禁那份文件即可，一行断言都不用重写）：

    _BODY = _load_sibling_module(
        "tests/unit/test_explain_cost_accounting_body.py", "_p1_7_cost_accounting_body"
    )
    test_all_three_token_buckets_are_recorded_per_call = (
        _BODY.test_all_three_token_buckets_are_recorded_per_call
    )
    test_the_ledger_rolls_up_per_explanation = _BODY.test_the_ledger_rolls_up_per_explanation
    test_dropping_any_one_bucket_turns_the_criteria_red = (
        _BODY.test_dropping_any_one_bucket_turns_the_criteria_red
    )
    ...

⚠️ 加载器必须**先把模块塞进 `sys.modules` 再 `exec_module`**（本文件 import 的
`explain_fakes` 里那个 `load_repo_module` 是同一形状，理由写在那里）。

⚠️ **basename 必须与门禁那两份不同**（本文件叫 `..._body.py`）。`tests/` 没有 `__init__.py`，
同名 basename 会让 `pytest` 整轮 `import file mismatch` 收集失败 —— P1.4 起草期评审实测过。

⚠️ **「纯路径加载、无 live 语义是否仍满足那两个 🔴」由人裁定，loop 不替人拍板。**
本文件全程假 transport + 假站点，不依赖活站点、不依赖凭据，**根本没有 skip 可以收严**。
活端点那一跑的证据另落 `docs/evidence/p1-cost/`。
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.explain import explain  # noqa: E402
from agenerp.explain.ledger import CALL_ANSWER, CALL_TOOLS  # noqa: E402
from agenerp.explain.loop import (  # noqa: E402
    MAX_TOOL_CALLS,
    MAX_TURNS,
    STOP_ANSWERED,
    STOP_MAX_TURNS,
    STOP_RUNAWAY,
    ExplainLoop,
)
from agenerp.routing import route  # noqa: E402
from agenerp.routing.adapter import Usage  # noqa: E402

QUESTION = f"帮我看看 {fakes.ORDER_A} 现在什么情况？"


def endpoint_usage(prompt: int, completion: int, reasoning: int) -> dict:
    """端点自报的 `usage`，**原始形状** —— 判据要判的是解析这一段，不是我们自己造的 `Usage`。"""
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "completion_tokens_details": {"reasoning_tokens": reasoning},
    }


def tools_reply(*calls: dict, usage: dict) -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": None, "tool_calls": list(calls)},
                "finish_reason": "tool_calls",
            }
        ],
        "usage": usage,
    }


def answer_reply(text: str, *, usage: dict) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": usage,
    }


# **每次调用的账各不相同** —— 三条一模一样的话，「汇总写死成常量」的假实现照样全绿。
CALL_1 = (1067, 207, 150)
CALL_2 = (3291, 180, 123)
CALL_3 = (3472, 225, 116)
CALL_4 = (6458, 513, 393)
EXPECTED_TOTAL = Usage(
    prompt=1067 + 3291 + 3472 + 6458,
    completion=207 + 180 + 225 + 513,
    reasoning=150 + 123 + 116 + 393,
)

SCRIPT = [
    tools_reply(
        fakes.call("doc.get", "b0", doctype="Sales Order", name=fakes.ORDER_A),
        usage=endpoint_usage(*CALL_1),
    ),
    tools_reply(
        fakes.call("doc.links", "b1", doctype="Sales Order", name=fakes.ORDER_A),
        usage=endpoint_usage(*CALL_2),
    ),
    tools_reply(
        fakes.call("doc.get", "b2", doctype="Delivery Note", name=fakes.SUBMITTED_DN),
        usage=endpoint_usage(*CALL_3),
    ),
    answer_reply(
        f"订单已由发货单 {fakes.SUBMITTED_DN} 发出，工单还是草稿。",
        usage=endpoint_usage(*CALL_4),
    ),
]


def run_product_path(script: list[dict], *, max_turns: int = 6):
    """产品默认路径：走导出面的 `explain()`，**账本没有参数可以关**。"""
    return explain(
        QUESTION,
        task_class="explain",
        client=fakes.client_for(fakes.explain_site()),
        models=fakes.models(),
        config=fakes.config(),
        transport=fakes.ScriptedModel(script),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        max_turns=max_turns,
    )


# ═══════════════════════════════════════════════════════════════════════════
# §A · 第一条 🔴（**有名**：`tests/gates/test_explain_cost_accounting.py`）
#      「断言**成本可观测**：三项都记了、能按解释汇总、缺任一项即红」
# ═══════════════════════════════════════════════════════════════════════════


def test_all_three_token_buckets_are_recorded_per_call():
    """**三项都记了**，而且是**每次调用一条**、逐条对得上端点自报的数。

    ⚠️ D-18 逐字「不许退化成『跑通就算』」：这里判的是 `prompt` / `completion` /
    **`reasoning`** 三项**各自**的数字，不是「账本非空」。
    ⚠️ 逐条 `total` 判的是**端点自报的 `total_tokens`**，不是 `Usage.total` 那个恒真式
    （`prompt + completion == total` 那种写法判了等于没判）。
    """
    result = run_product_path(SCRIPT)

    assert result.trace.stopped == STOP_ANSWERED
    ledger = result.cost_ledger
    assert len(ledger) == 4, "四次模型调用应当有四条账"

    assert [
        (e.usage.prompt, e.usage.completion, e.usage.reasoning) for e in ledger.entries
    ] == [CALL_1, CALL_2, CALL_3, CALL_4]

    for entry in ledger.entries:
        assert entry.usage.prompt > 0
        assert entry.usage.completion > 0
        assert entry.usage.reasoning > 0, "reasoning 漏记 —— D-11：回两个字也烧约 195 reasoning token"
        assert entry.usage.total == entry.endpoint_total
        assert entry.usage.reasoning == entry.endpoint_reasoning
        assert entry.total_matches_endpoint and entry.reasoning_matches_endpoint

    assert [e.outcome for e in ledger.entries] == [
        CALL_TOOLS, CALL_TOOLS, CALL_TOOLS, CALL_ANSWER,
    ]
    assert [e.index for e in ledger.entries] == [1, 2, 3, 4]


def test_the_ledger_rolls_up_per_explanation():
    """**能按一次解释汇总**，且汇总不是写死的常量。

    ⚠️ 每次调用的账刻意各不相同 —— 都一样的话，「汇总写死成常量」的假实现全绿。"""
    result = run_product_path(SCRIPT)

    assert result.cost_ledger.total == EXPECTED_TOTAL
    assert result.cost_ledger.total.total == EXPECTED_TOTAL.prompt + EXPECTED_TOTAL.completion
    # 汇总 == 逐条相加，且逐条各不相同。
    assert len({e.usage for e in result.cost_ledger.entries}) == 4
    assert result.cost_ledger.as_dict()["calls"] == 4
    assert result.trace.as_dict()["cost_ledger"]["total"] == EXPECTED_TOTAL.as_dict()


@pytest.mark.parametrize("bucket", ["prompt", "completion", "reasoning"])
def test_dropping_any_one_bucket_turns_the_criteria_red(bucket):
    """**缺任一项即红** —— 三项各反测一次，`reasoning` 是 D-18 点名的那一项。

    ⚠️ 假实现摆在判据侧（把某一位置零后重跑同一套断言），**产品代码一行不改**。"""
    result = run_product_path(SCRIPT)
    crippled = [
        Usage(
            prompt=0 if bucket == "prompt" else e.usage.prompt,
            completion=0 if bucket == "completion" else e.usage.completion,
            reasoning=0 if bucket == "reasoning" else e.usage.reasoning,
        )
        for e in result.cost_ledger.entries
    ]

    with pytest.raises(AssertionError):
        assert all(u.prompt > 0 and u.completion > 0 and u.reasoning > 0 for u in crippled)

    folded = Usage()
    for usage in crippled:
        folded = folded.plus(usage)
    with pytest.raises(AssertionError):
        assert folded == EXPECTED_TOTAL


def test_the_ledger_is_on_the_product_path_and_has_no_switch():
    """账本在**产品默认路径**上，且**没有开关可以关掉它**。

    判据形态：`explain()` 的签名里没有任何跟账本有关的参数，账本照样在。"""
    result = run_product_path(SCRIPT)

    assert len(result.cost_ledger) == 4
    forbidden = {"ledger", "cost_ledger", "cost", "usage_ledger"}
    assert forbidden.isdisjoint(set(explain.__code__.co_varnames))


def test_the_accounting_never_blocks_anything():
    """**D-18 的底线：记账，不拦截。** 账本里没有阈值、没有任何「超了就……」的分支。

    ⚠️ 这一条防的是「将来有人顺手在账本里加一条拦截」—— 那是 D-18 明令取消的东西。"""
    huge = endpoint_usage(10_000_000, 5_000_000, 4_000_000)
    script = [
        tools_reply(
            fakes.call("doc.get", "h0", doctype="Sales Order", name=fakes.ORDER_A), usage=huge
        ),
        tools_reply(
            fakes.call("doc.links", "h1", doctype="Sales Order", name=fakes.ORDER_A), usage=huge
        ),
        tools_reply(
            fakes.call("doc.get", "h2", doctype="Delivery Note", name=fakes.SUBMITTED_DN),
            usage=huge,
        ),
        answer_reply(f"订单已由发货单 {fakes.SUBMITTED_DN} 发出。", usage=huge),
    ]
    result = run_product_path(script)

    assert result.trace.stopped == STOP_ANSWERED
    assert result.accepted is True
    assert result.cost_ledger.total.total == 4 * 15_000_000


# ═══════════════════════════════════════════════════════════════════════════
# §B · 第二条 🔴（**未命名**：`02-WBS.md` §4 P1.7 行的第二个 🔴 **没有给文件路径**）
#      「**失控闸另算**：单次解释的工具调用轮数上限仍要有 —— 不拦成本 ≠ 不拦失控」
#
# ⚠️ **本节与 §A 分开，不合并**（D-18 逐字）。人若只建一个门禁文件，
#    也请把两节的断言分成两组、分开陈述结果。
# ⚠️ **本节不声称满足了 WBS「轮数」那个字面措辞**（见模块头）。
# ═══════════════════════════════════════════════════════════════════════════


class RunawayModel:
    """**每轮回 K 个工具调用、永不作答**的假模型 —— 「调得通但陷入循环」那个形态。"""

    def __init__(self, calls_per_turn: int) -> None:
        self.calls_per_turn = calls_per_turn
        self.turns = 0

    def __call__(self, payload: dict) -> dict:
        self.turns += 1
        return tools_reply(
            *[
                fakes.call(
                    "doc.get", f"w{self.turns}-{i}", doctype="Sales Order", name=fakes.ORDER_A
                )
                for i in range(self.calls_per_turn)
            ],
            usage=endpoint_usage(*CALL_1),
        )


def loop_with(transport, **kwargs) -> ExplainLoop:
    adapter = route(
        "explain", models=fakes.models(), config=fakes.config(), transport=transport
    )
    return ExplainLoop(
        adapter=adapter,
        client=fakes.client_for(fakes.explain_site()),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        **kwargs,
    )


def test_a_runaway_explanation_is_stopped_by_the_tool_call_limit():
    """**上限确实存在，且轮数远没到 `max_turns` 时就生效。**

    每轮 8 个调用、上限 32 → 第 4 轮撞闸，而 `max_turns` 给的是 6。"""
    model = RunawayModel(calls_per_turn=8)
    result = loop_with(model, max_turns=6, max_tool_calls=32).run(QUESTION)

    assert result.trace.stopped == STOP_RUNAWAY
    assert result.trace.model_tool_calls == 32
    assert result.trace.execute_calls <= 32
    assert model.turns == 4
    assert result.accepted is False
    # 留痕：第几次、上限是多少。
    assert result.trace.runaway_events == [{"turn": 4, "tool_calls": 32, "limit": 32}]


def test_the_runaway_stop_reason_is_not_max_turns_and_not_the_breaker():
    """**失控闸「另算」的可观测形态**：它有**专属**停止原因，不复用任何既有的那个。

    ⚠️ 这一条挡的是「把失控闸实现成把 `max_turns` 改小」—— 那等于两个闸合并，D-18 禁止。"""
    from agenerp.explain.loop import STOP_BREAKER, STOP_MODEL_ERROR

    assert STOP_RUNAWAY not in {STOP_ANSWERED, STOP_BREAKER, STOP_MAX_TURNS, STOP_MODEL_ERROR}

    result = loop_with(RunawayModel(8), max_turns=6, max_tool_calls=32).run(QUESTION)
    assert result.trace.stopped == STOP_RUNAWAY
    assert result.trace.stopped != STOP_MAX_TURNS
    assert result.trace.stopped != STOP_BREAKER


def test_the_two_gates_fire_independently():
    """**两个闸各判各的**：同一个假模型，上限调大就跑到 `max-turns`；
    每轮只发一次调用的模型，**在默认上限下**也停在 `max-turns`。

    ⚠️ 后半条是「默认上限严格大于 `MAX_TURNS`」这条下界的可观测形态：
    默认值若取 25，`max_turns` 跑满 25 轮时第 25 次调用恰好撞闸，本条当场红。"""
    loose = RunawayModel(8)
    result = loop_with(loose, max_turns=6, max_tool_calls=10_000).run(QUESTION)
    assert result.trace.stopped == STOP_MAX_TURNS
    assert result.trace.model_tool_calls == 48
    assert result.trace.runaway_events == []

    steady = RunawayModel(calls_per_turn=1)
    default_run = loop_with(steady, max_turns=MAX_TURNS).run(QUESTION)
    assert default_run.trace.stopped == STOP_MAX_TURNS
    assert default_run.trace.model_tool_calls == MAX_TURNS
    assert MAX_TOOL_CALLS > MAX_TURNS


def test_the_default_limit_applies_on_the_product_path_without_any_switch():
    """**产品入口走默认值，且不给产品面开关**（照抄 P1.4 的 D7：安全闸不给开关）。

    ⚠️ 不可省的理由：上面几条全都显式构造 `ExplainLoop` 并传上限，
    一个「默认值 = 无限」的实现能通过它们的全部。这里 `max_turns` 给 `10_000`，
    截住它的只可能是**默认上限**。"""
    model = RunawayModel(calls_per_turn=8)
    result = explain(
        QUESTION,
        task_class="explain",
        client=fakes.client_for(fakes.explain_site()),
        models=fakes.models(),
        config=fakes.config(),
        transport=model,
        doctypes=list(fakes.SCOPE_CANDIDATES),
        max_turns=10_000,
    )

    assert result.trace.stopped == STOP_RUNAWAY
    assert result.trace.model_tool_calls == MAX_TOOL_CALLS
    assert "max_tool_calls" not in explain.__code__.co_varnames


def test_the_cost_ledger_is_still_complete_when_the_runaway_gate_fires():
    """**停机不清账** —— 「不拦成本」不等于「不记账」，也不等于「不停失控」。

    ⚠️ 这一条是把 §A 与 §B 的行为契约耦合在一起的那条：拆成两个 plan 就没人证明它。
    但**判据仍在两组里各自陈述**，本条属 §B。"""
    model = RunawayModel(8)
    result = loop_with(model, max_turns=6, max_tool_calls=32).run(QUESTION)

    assert result.trace.stopped == STOP_RUNAWAY
    ledger = result.cost_ledger
    assert len(ledger) == model.turns == 4
    assert all(e.usage.reasoning > 0 for e in ledger.entries)
    assert all(e.total_matches_endpoint for e in ledger.entries)
    assert ledger.total == Usage(
        prompt=4 * CALL_1[0], completion=4 * CALL_1[1], reasoning=4 * CALL_1[2]
    )
