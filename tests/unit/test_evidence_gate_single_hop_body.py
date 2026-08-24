"""🔴 WBS §4 P1.4 那条验收（`tests/gates/test_evidence_gate_blocks_single_hop.py`）的**断言体**。

**这个文件是交接件。** 红线 1 禁止 loop 创建 `tests/gates/**` 下的任何文件，所以门禁那份
由**人**创建；人只需按路径加载本文件，`断言体不重写`（先例：P1.0a 的
`tests/gates/test_tool_execution_live.py`，commit `3b6d071`，`Gates-Change-Approved-By: lize`）。

⚠️ **两处与 P1.0a 那次不同，照实说，不照抄它的措辞**：

1. **basename 必须与门禁那份不同**（本文件叫 `..._single_hop_body.py`，门禁那份叫
   `test_evidence_gate_blocks_single_hop.py`）。`tests/` 没有 `__init__.py`，同名 basename
   会让 `pytest` 整轮 `import file mismatch` 收集失败 —— 起草期评审实测过。
2. **P1.0a 那次的「无站点时 skip → fail」在这里不适用**：本文件是**假 transport + 假站点**的，
   全程不依赖活站点、不依赖凭据，**根本没有 skip 可以收严**。门禁那份因此是**纯路径加载、
   无 live 语义**的严格模式：它保证的是「这条判据存在于 `tests/gates/` 下且与开发期同源」，
   不是「它必须打活站点」。⚠️ **这一句要人复核** —— WBS §4 P1.4 的 🔴 要的是
   「门禁拦得住单跳」这条判据在裁判目录下有一份，loop 不替人拍板它算不算数。

给人的加载片段（放进门禁那份文件即可，一行断言都不用重写）：

    _BODY = _load_sibling_module(
        "tests/unit/test_evidence_gate_single_hop_body.py", "_p1_4_single_hop_body"
    )
    test_single_hop_answer_is_rejected_on_the_product_path = (
        _BODY.test_single_hop_answer_is_rejected_on_the_product_path
    )
    ...

⚠️ 加载器必须**先把模块塞进 `sys.modules` 再 `exec_module`**（本文件 import 的
`explain_fakes` 里那个 `load_repo_module` 是同一形状，理由写在那里）。
"""

from __future__ import annotations

import inspect
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.explain import explain  # noqa: E402
from agenerp.explain.loop import ExplainLoop  # noqa: E402
from agenerp.routing import route  # noqa: E402

QUESTION = f"帮我看看 {fakes.ORDER_A} 现在什么情况？"

# Spike 02 实测到的失败形态：只调一次 `doc.get` 就下结论。
SINGLE_HOP = [
    fakes.tools_step(fakes.call("doc.get", doctype="Sales Order", name=fakes.ORDER_A)),
    fakes.answer_step(f"订单 {fakes.ORDER_A} 一切正常，已按计划推进。"),
]

# H2：**文字正确、数字对、结论对**，但取证轨迹与上面那条一模一样。
# 「答对」与「蒙对」的分界就在这里 —— 判据落在轨迹上，不落在答案文本上。
WELL_WORDED = [
    SINGLE_HOP[0],
    fakes.answer_step(
        f"订单 {fakes.ORDER_A} 的客户是北方新能源工程有限公司，"
        f"明细 1 行、物料 {fakes.ITEM}，单据已提交（docstatus=1）。"
    ),
]


def _run(script: list[dict], *, max_turns: int = 4):
    """产品默认路径：走导出面的 `explain()`，② 作答前门禁**没有参数可以关**。"""
    site = fakes.explain_site()
    result = explain(
        QUESTION,
        task_class="explain",
        client=fakes.client_for(site),
        models=fakes.models(),
        config=fakes.config(),
        transport=fakes.ScriptedModel(script),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        max_turns=max_turns,
    )
    return site, result


def _ablated(script: list[dict], *, max_turns: int = 4):
    """D7 的 (B)：**判据侧直接构造**一个不带 ② 门禁的循环，开关不进产品导出面。

    ① 工具前置那一面**全程开着、无开关** —— 那是 P1.0a 已收口的契约声明。
    """
    site = fakes.explain_site()
    adapter = route(
        "explain",
        models=fakes.models(),
        config=fakes.config(),
        transport=fakes.ScriptedModel(script),
    )
    loop = ExplainLoop(
        adapter=adapter,
        client=fakes.client_for(site),
        answer_gate_enabled=False,
        max_turns=max_turns,
        doctypes=list(fakes.SCOPE_CANDIDATES),
    )
    return site, loop.run(QUESTION)


# ── H1 · 三条断言 ───────────────────────────────────────────────────────────


def test_single_hop_answer_is_rejected_on_the_product_path():
    """H1 ①：单跳答案在**产品默认路径**下被拒，且回注了强制续跑消息。"""
    _, result = _run(SINGLE_HOP)

    assert result.accepted is False
    assert result.answer == ""
    assert result.trace.forced_continues, "门禁发红却没有回注强制续跑消息"
    assert "证据不足" in result.trace.forced_continues[0]
    assert "doc.links" in result.trace.forced_continues[0]

    failed = [row for check in result.trace.gate_checks for row in check["failed"]]
    assert any(row["fact"] == "doc_links_called_for" for row in failed)


def test_same_trace_and_answer_is_accepted_when_the_answering_gate_is_ablated():
    """H1 ②：**同一条轨迹的同一个答案**在门禁关的一侧被接受。

    只验 ① 等于没验 —— 那分不清「门禁拦住了」与「循环本来就不作答」。
    """
    _, result = _ablated(SINGLE_HOP)

    assert result.accepted is True
    assert result.answer == SINGLE_HOP[1]["choices"][0]["message"]["content"]
    assert result.trace.gate_checks == [], "门禁关的一侧不该留下任何 ② 求值记录"
    assert result.trace.execute_calls == 1, "两侧必须是同一条轨迹：都只发过一次 execute"


def test_the_answering_gate_is_on_by_default_on_the_product_path():
    """H1 ③：**产品默认路径下 ② 门禁确实是开的**。

    没有这一条，H1 ② 可能退化成「在两个不同对象上比较」（D7 的残余风险）。
    """
    assert ExplainLoop.__init__.__kwdefaults__["answer_gate_enabled"] is True
    assert ExplainLoop(adapter=None, client=None).answer_gate_enabled is True
    # 产品入口上**根本没有这个参数** —— 调用方一行关不掉它（D7 的 (A) 被否决的理由）。
    assert "answer_gate_enabled" not in inspect.signature(explain).parameters

    _, result = _run(SINGLE_HOP)
    assert result.trace.gate_checks, "产品默认路径下一次 ② 求值都没发生"
    assert all(check["enforced"] is True for check in result.trace.gate_checks)
    assert result.surface.used_for("answering") >= 1


# ── H2 · 判据落在轨迹上，不落在答案文本上 ───────────────────────────────────


def test_well_worded_but_under_evidenced_answer_is_still_rejected():
    """H2：把答案换成一段**文字正确但取证不足**的（数字对、结论对），门禁**仍然拒**。"""
    _, result = _run(WELL_WORDED)

    assert result.accepted is False
    assert result.answer == ""
    assert result.trace.forced_continues

    facts = result.trace.gate_checks[0]["facts"]
    assert facts["doc_get_called_for"] == [fakes.ORDER_A]
    assert facts["doc_links_called_for"] == []


def test_the_two_answers_differ_in_text_but_not_in_trace():
    """H2 的另一半：两条答案文本不同、**取证轨迹完全相同**，判定也就必须相同。"""
    _, plain = _run(SINGLE_HOP)
    _, worded = _run(WELL_WORDED)

    assert plain.accepted is worded.accepted is False
    assert [c["tool"] for c in plain.trace.tool_calls] == [
        c["tool"] for c in worded.trace.tool_calls
    ]
    assert plain.trace.gate_checks[0]["facts"] == worded.trace.gate_checks[0]["facts"]
