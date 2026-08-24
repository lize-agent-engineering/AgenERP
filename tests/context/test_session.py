"""② 会话层的判据 —— 零网络。

四组：

① 轮次 / 动作 / 只读快照引用三项都真的记下来了；
② token 三项按 P1.1 的口径记：`reasoning` **单独可读**、`total = prompt + completion`、
   **reasoning 不参与求和**；
③ **`Usage.plus` 真的被调用过** —— monkeypatch 数次数。没有这一条，「必须调 `plus()`」
   只是一句注释：一份手写但算得对的三项加法能满足②组的全部算术断言；
④ **权限/风险红线的机械判据** —— AST 扫描，不是 code review。
"""

from __future__ import annotations

import pytest
from _scan import (
    EVALUATION_NAMES,
    SITE_WRITE_NAMES,
    contracts_imports,
    evaluation_surface_hits,
    execute_call_hits,
    facts_hits,
)

from agenerp.context.session import (
    ConversationSession,
    ExecutedAction,
    SnapshotRef,
    ToolCall,
    Turn,
    snapshot_ref,
    start,
)
from agenerp.routing.adapter import Usage
from agenerp.snapshot import Snapshot, SnapshotEntry

BEFORE = Snapshot(scope="doctypes", entries=(SnapshotEntry("Item", "agenerp_probe", {"a": 1}),))
AFTER = Snapshot(
    scope="doctypes",
    entries=(
        SnapshotEntry("Item", "agenerp_probe", {"a": 2}),
        SnapshotEntry("Item", "agenerp_probe_2", {}),
    ),
)


def _three_turn_session() -> ConversationSession:
    return (
        start("S-1", user="老板")
        .with_turn(Turn("user", "990 台去哪了", usage=Usage(11, 20, 7)))
        .with_turn(
            Turn(
                "assistant",
                "",
                tool_calls=(ToolCall("doc.get", {"zz_name": "SAL-ORD-1", "aa_doctype": "SO"}),),
                usage=Usage(100, 200, 150),
            )
        )
        .with_turn(Turn("assistant", "订单被人工关闭", usage=Usage(300, 40, 0)))
    )


# ── ① 三项都记下来 ──────────────────────────────────────────────────


def test_turns_are_appended_without_mutating_the_original():
    """不可变：`with_turn` 回新会话，原对象一轮都没多。审计面就地改写等于毁证。"""
    base = start("S-1")
    grown = base.with_turn(Turn("user", "hi"))
    assert len(base.turns) == 0
    assert [t.text for t in grown.turns] == ["hi"]


def test_a_readonly_probe_records_action_and_both_snapshot_refs():
    session = start("S-1").with_readonly_probe(
        tool="snapshot.read", params={"scope": "doctypes"}, before=BEFORE, after=AFTER, request_count=2
    )
    (action,) = session.actions
    assert action.tool == "snapshot.read"
    assert action.request_count == 2
    assert [ref.label for ref in session.snapshots] == [action.before, action.after]
    assert [ref.entry_count for ref in session.snapshots] == [1, 2]


def test_the_diff_summary_comes_from_agenerp_snapshot_not_a_second_comparison():
    from agenerp.snapshot import diff

    session = start("S-1").with_readonly_probe(
        tool="snapshot.read", params={}, before=BEFORE, after=AFTER
    )
    assert session.actions[0].diff_summary == diff(BEFORE, AFTER).summary()


def test_audit_records_are_listed_one_by_one_not_summarised():
    """§8.2 规则 ②：已执行动作的审计记录**不可压缩**。两条动作就是两条记录。"""
    session = (
        start("S-1")
        .with_readonly_probe(tool="doc.get", params={}, before=BEFORE, after=AFTER)
        .with_readonly_probe(tool="doc.links", params={}, before=BEFORE, after=BEFORE)
    )
    records = session.audit_records()
    assert len(records) == 2
    assert records[0].startswith("doc.get(")
    assert records[1].startswith("doc.links(")


def test_snapshot_ref_does_not_copy_the_snapshot_body():
    ref = snapshot_ref("取证前", AFTER)
    assert ref == SnapshotRef(label="取证前", scope="doctypes", entry_count=2)
    assert not hasattr(ref, "entries")


# ── ② token 三项的口径（沿用 P1.1，不另立一套）──────────────────────


def test_reasoning_is_readable_on_its_own():
    """`reasoning` 不得被折掉 —— 折掉它，P1.7 的成本上限只能按可见输出去算，差一个量级。"""
    assert _three_turn_session().usage_total.reasoning == 7 + 150 + 0


def test_the_session_total_is_prompt_plus_completion_and_reasoning_is_not_added_again():
    """**反测位**：把 reasoning 再加一遍（`prompt + completion + reasoning`）必须红。"""
    total = _three_turn_session().usage_total
    assert (total.prompt, total.completion) == (411, 260)
    assert total.total == 411 + 260 == 671
    assert total.total != 411 + 260 + total.reasoning


def test_an_empty_session_costs_nothing():
    assert start("S-1").usage_total == Usage(0, 0, 0)


# ── ③ `Usage.plus` 真的被调用过 ─────────────────────────────────────


def test_the_aggregate_actually_goes_through_usage_plus_exactly_once_per_turn(monkeypatch):
    """折叠形态**定死**：从空 `Usage()` 起折 N 轮 → **恰好 N 次**。不写「至少一次」。

    自己写三项加法的实现算得出同样的数，但一次 `plus` 都不会调 —— 这一条是唯一能把它打红的。
    """
    calls: list[tuple[Usage, Usage]] = []
    original = Usage.plus

    def counting_plus(self: Usage, other: Usage) -> Usage:
        calls.append((self, other))
        return original(self, other)

    monkeypatch.setattr(Usage, "plus", counting_plus)

    session = _three_turn_session()
    total = session.usage_total

    assert len(calls) == len(session.turns) == 3
    assert calls[0][0] == Usage(), "折叠必须从空 `Usage()` 起——形态变了，次数断言就失去意义"
    assert [other for _, other in calls] == [turn.usage for turn in session.turns]
    assert total == Usage(411, 260, 157)


# ── ④ 权限 / 风险红线的机械判据 ─────────────────────────────────────


def test_the_context_layer_never_imports_the_contracts_module():
    assert contracts_imports() == []


def test_the_context_layer_never_touches_the_contract_evaluation_surface():
    """黑名单是**这几个具体名字**，不是「禁 import `agenerp.tools.runtime`」。

    过宽的模块级禁令会把 ① 层当场打红 —— 它正要 import 那个模块的 `wrap_free_text`，
    而那与权限判定毫无关系。
    """
    assert "ReadOnlyContext" in EVALUATION_NAMES
    assert evaluation_surface_hits() == []


def test_the_context_layer_never_builds_a_facts_dict_or_calls_execute():
    assert facts_hits() == []
    assert execute_call_hits() == []


def test_the_scanner_is_not_vacuous():
    """扫描器自己要能抓到东西 —— 否则四条红线判据全是空转的绿。"""
    from _scan import EVALUATION_NAMES as names

    assert names and SITE_WRITE_NAMES
    assert "create_doc" in SITE_WRITE_NAMES


@pytest.mark.parametrize("bad_id", ["", ".", "..", "a/b"])
def test_session_id_that_cannot_be_a_filename_is_refused(bad_id, tmp_path):
    from agenerp.context.store import JsonFileSessionStore

    with pytest.raises(ValueError):
        JsonFileSessionStore(tmp_path).path_of(bad_id)


def test_executed_action_defaults_are_empty_not_none():
    action = ExecutedAction(tool="doc.get")
    assert action.params == {} and action.before == "" and action.after == ""
