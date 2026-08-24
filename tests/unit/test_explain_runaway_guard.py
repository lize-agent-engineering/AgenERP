"""P1.7 **失控闸**那一组判据（D-18）—— 判的是「**工具调用总数有上限，且它不是 `max_turns`**」。

⚠️ **成本记账的判据不在这里**，在 `tests/unit/test_explain_cost_ledger.py`。
D-18 逐字「**两者的判据分开写，不许合并**」，所以两组判据分两个文件，
**本文件不 import 那个文件里的任何夹具**（下面的假模型、`loop_for`、断言全部自备）。
两边共用的只有 P1.4 已交付的公共假件 `tests/unit/explain_fakes.py` —— 那不在禁止之列。

**失控闸只做「停下来」这一件事**：不拦成本、不改模型、不降级。
「贵」不归它管（D-18 取消了成本阈值），它管的是「**坏**」——
一个陷入循环的 Agent 会无限调工具。
"""

from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.explain import explain  # noqa: E402
from agenerp.explain.loop import (  # noqa: E402
    MAX_TOOL_CALLS,
    MAX_TURNS,
    STOP_ANSWERED,
    STOP_BREAKER,
    STOP_MAX_TURNS,
    STOP_MODEL_ERROR,
    STOP_RUNAWAY,
    ExplainLoop,
)
from agenerp.routing import route  # noqa: E402
from agenerp.routing.adapter import Usage  # noqa: E402


class LoopingModel:
    """**每轮回 K 个工具调用、永不作答**的假模型 —— 「调得通但陷入循环」那个形态。

    工具是**真存在**的只读工具（`doc.get`），所以每一次都真的走到 `execute` ——
    这样 H4 ① 的「`execute` 次数不超上限」才判得到实处。"""

    def __init__(self, calls_per_turn: int) -> None:
        self.calls_per_turn = calls_per_turn
        self.turns = 0

    def __call__(self, payload: dict) -> dict:
        self.turns += 1
        return fakes.tools_step(
            *[
                fakes.call(
                    "doc.get", f"r{self.turns}-{i}", doctype="Sales Order", name=fakes.ORDER_A
                )
                for i in range(self.calls_per_turn)
            ]
        )


def loop_for(transport, **kwargs) -> ExplainLoop:
    site = fakes.explain_site()
    adapter = route(
        "explain", models=fakes.models(), config=fakes.config(), transport=transport
    )
    return ExplainLoop(
        adapter=adapter,
        client=fakes.client_for(site),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        **kwargs,
    )


# ── D3 · 默认值的两条下界 ──────────────────────────────────────────────────


def test_d3_the_default_limit_is_strictly_greater_than_max_turns():
    """②「对 `MAX_TURNS` 留余量，**严格大于**」这条下界的可执行形态。

    取等号就会让失控闸赶在 `STOP_MAX_TURNS` 之前触发、产品默认路径上 `max-turns` 永不可达
    —— 那正是 D-18 禁止的合并，H4 ④ 的反向用例也就构造不出来了。"""
    assert MAX_TOOL_CALLS >= MAX_TURNS + 1
    assert MAX_TOOL_CALLS > MAX_TURNS


def test_d3_the_default_limit_leaves_headroom_over_the_measured_run():
    """①「对本项目实测留余量」：P1.4 那一次活端点解释实测 `execute_calls == 8`。

    ⚠️ 这是本项目**唯一**可引用的数字（D-16：以本项目实测为准），外部经验值一律不引。"""
    measured = 8
    assert MAX_TOOL_CALLS >= measured * 4


def test_the_runaway_stop_reason_is_its_own_value():
    """**专属停止原因**，不复用 `max-turns` / `permission-breaker` / `answered` / `model-error`。"""
    others = {STOP_ANSWERED, STOP_BREAKER, STOP_MAX_TURNS, STOP_MODEL_ERROR}
    assert STOP_RUNAWAY not in others
    assert len(others | {STOP_RUNAWAY}) == 5


# ── H4 · 五件事逐条判 ──────────────────────────────────────────────────────


def test_h4_1_and_2_the_guard_stops_before_the_limit_is_exceeded():
    """H4 ① `execute` 实际次数**不超过**上限；② 停止原因是失控闸专属的那个值。

    ⚠️ **轮数远没到 `max_turns`**：每轮 8 个调用，第 4 轮就撞上限 32，而 `max_turns` 是 6。"""
    model = LoopingModel(calls_per_turn=8)
    result = loop_for(model, max_turns=6, max_tool_calls=32).run("跑飞问题")

    assert result.trace.stopped == STOP_RUNAWAY
    assert result.trace.stopped != STOP_MAX_TURNS
    assert result.trace.stopped != STOP_BREAKER
    assert result.trace.model_tool_calls == 32
    assert result.trace.execute_calls <= 32
    assert model.turns == 4  # 6 轮的上限根本没跑到
    assert result.accepted is False


def test_h4_the_guard_leaves_a_trace_of_which_call_and_which_limit():
    """留痕：**第几次、上限是多少**。停机不留痕就没法事后判它到底该不该停。"""
    result = loop_for(LoopingModel(8), max_turns=6, max_tool_calls=32).run("跑飞问题")

    assert result.trace.runaway_events == [{"turn": 4, "tool_calls": 32, "limit": 32}]
    serialized = result.trace.as_dict()
    assert serialized["stopped"] == STOP_RUNAWAY
    assert serialized["runaway_events"] == result.trace.runaway_events
    assert serialized["model_tool_calls"] == 32


def test_h4_3_the_cost_ledger_survives_the_runaway_stop():
    """H4 ③ **成本账仍然完整**（停机不清账；不拦截 ≠ 不丢账）。

    每轮一次模型调用 → 4 轮 4 条；每条都带着那次回包自报的三项。"""
    model = LoopingModel(8)
    result = loop_for(model, max_turns=6, max_tool_calls=32).run("跑飞问题")

    ledger = result.cost_ledger
    assert len(ledger) == model.turns == 4
    assert all(entry.usage != Usage() for entry in ledger.entries)
    assert all(entry.total_matches_endpoint for entry in ledger.entries)
    # `explain_fakes.usage()` 的默认账是 31 / 17 / 11。
    assert ledger.total == Usage(prompt=4 * 31, completion=4 * 17, reasoning=4 * 11)
    # 停机的这一轮照样进了会话 —— 两处账不许各算各的。
    assert ledger.total == result.usage


def test_h4_4_a_generous_limit_lets_the_same_model_run_into_max_turns():
    """H4 ④ 反向用例：把上限调大到够用，**同一个假模型**跑到 `max-turns` 停。

    → 两个闸**各判各的**，失控闸不是「把 `max_turns` 改小」。"""
    model = LoopingModel(8)
    result = loop_for(model, max_turns=6, max_tool_calls=10_000).run("跑飞问题")

    assert result.trace.stopped == STOP_MAX_TURNS
    assert result.trace.stopped != STOP_RUNAWAY
    assert model.turns == 6
    assert result.trace.model_tool_calls == 48  # 超过了刚才那个 32，但这次没被截
    assert result.trace.runaway_events == []


def test_h4_4_the_reverse_case_also_holds_under_the_default_limit():
    """H4 ④ 的严格下界形态：**每轮只发一次工具调用**的假模型，**不传上限**时
    应当停在 `max-turns` 而不是失控闸。

    ⚠️ 这一条是 D3 ② 那条「严格大于 `MAX_TURNS`」的可观测形态：
    默认值若取 25，`max_turns` 跑满 25 轮时第 25 次调用恰好撞闸，本条当场红。"""
    model = LoopingModel(calls_per_turn=1)
    result = loop_for(model, max_turns=MAX_TURNS).run("细水长流问题")

    assert result.trace.stopped == STOP_MAX_TURNS
    assert result.trace.model_tool_calls == MAX_TURNS == 25
    assert result.trace.runaway_events == []


def test_h4_5_the_product_entry_is_cut_by_the_default_limit():
    """H4 ⑤ 经产品入口 `explain(...)` 跑一次，**不显式传上限**、`max_turns` 给 `10_000`。

    ⚠️ 不可省的理由：H4 ①–④ 全都显式构造 `ExplainLoop` 并传上限，
    一个「默认值 = 无限」的实现能通过那四条的全部。
    ⚠️ 上限**不给产品面开关**（照抄 P1.4 的 D7：安全闸不给产品面开关）——
    `explain()` 的签名里根本没有这个参数，判据侧要构造就直接构造 `ExplainLoop`。"""
    model = LoopingModel(calls_per_turn=8)
    result = explain(
        "产品入口跑飞问题",
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
    assert result.trace.execute_calls <= MAX_TOOL_CALLS
    assert model.turns * 8 >= MAX_TOOL_CALLS
    assert "max_tool_calls" not in explain.__code__.co_varnames


def test_the_guard_counts_calls_the_model_initiated_not_the_ones_that_reached_execute():
    """D3 的计量对象是 **(B1)「模型发起的工具调用数」**，不是 (B2)`trace.execute_calls`。

    ⚠️ 选 (B2) 的代价（起草期风险 ⑨）：未知工具在 `_execute_one()` 的计数之前就早返回，
    一个**不断编造工具名**的跑飞模型会让 (B2) 恒为 0、闸门**永不触发**。
    本条构造的正是那个形态：`execute_calls == 0`，而闸门照样把它截住。"""

    class BabblingModel:
        def __init__(self) -> None:
            self.turns = 0

        def __call__(self, payload: dict) -> dict:
            self.turns += 1
            return fakes.tools_step(
                *[
                    fakes.call("no.such.tool", f"b{self.turns}-{i}", doctype="X")
                    for i in range(8)
                ]
            )

    model = BabblingModel()
    result = loop_for(model, max_turns=1000, max_tool_calls=32).run("编造工具名问题")

    assert result.trace.stopped == STOP_RUNAWAY
    assert result.trace.execute_calls == 0  # (B2) 恒为 0 —— 选它闸门就废了
    assert result.trace.model_tool_calls == 32  # (B1) 照样数得到
    assert model.turns == 4


def imported_modules(path: pathlib.Path) -> set[str]:
    """这个判据文件 import 了哪些模块。**判 `import` 语句本身**，不判正文里出现过谁 ——
    模块头那段说明里就写着对方的文件名，按字符串搜会假红。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_the_two_criteria_groups_do_not_import_each_other():
    """D-18 逐字「判据分开写，不许合并」的**可观测形态**：两组判据在两个文件里，
    且**互不 import 对方文件里的夹具**。

    ⚠️ 共用 P1.4 已交付的 `tests/unit/explain_fakes.py` **不算违反** ——
    禁的是两组判据互相依赖，不是禁止复用既有公共假件（下面第三条断言把这一点钉住）。"""
    here = pathlib.Path(__file__)
    cost = here.with_name("test_explain_cost_ledger.py")
    assert cost.is_file(), "成本记账那一组判据不在了 —— 失控闸这一组不该独自变绿"

    assert "test_explain_cost_ledger" not in imported_modules(here)
    assert "test_explain_runaway_guard" not in imported_modules(cost)
    assert "explain_fakes" in imported_modules(here) & imported_modules(cost)
