"""prompt 侧细分 `cached` 的记账判据（plan `2026-08-25-0554-1-prompt-cache-accounting.md`）。

**为什么落在 `tests/unit` 而不是 `tests/routing` / `tests/context`**：
`missions/p1-insight.json` 的 `commands.test` 只含
`tools/gates/check_expected_red.py` 与 `pytest tests/unit`，
判据落在别处进不了 `GATE_VERIFY` 复跑（plan §1.1 / D3 残余风险）。

**这里的断言一律写死字面数字、整字典比较，不写 `total == prompt + completion` 那种恒真式**
—— `agenerp/explain/ledger.py` 模块头逐字批评过：判它等于没判。
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.context.session import Turn, start  # noqa: E402
from agenerp.context.store import from_payload, to_payload  # noqa: E402
from agenerp.explain import explain  # noqa: E402
from agenerp.explain.ledger import CallLedger  # noqa: E402
from agenerp.explain.loop import STOP_ANSWERED  # noqa: E402
from agenerp.routing.adapter import Reply, Usage, usage_of  # noqa: E402


def _body(
    *,
    prompt: int,
    completion: int,
    reasoning: int | None = None,
    cached: int | None = None,
) -> dict:
    """端点回包里 `usage` 那一段，形状照抄 `docs/evidence/p1-answer-judge/all.json` 的实读原文。"""
    usage: dict = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
    if reasoning is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning}
    if cached is not None:
        usage["prompt_tokens_details"] = {"cached_tokens": cached, "text_tokens": prompt}
    return usage


# ── ① 端点报了 `prompt_tokens_details.cached_tokens` ⇒ 解析得到 ───────────────


def test_cached_tokens_are_parsed_from_prompt_tokens_details():
    """M1 / M3 的红灯：不读 `prompt_tokens_details`（或读错成 completion 侧）这里就红。"""
    usage = usage_of(_body(prompt=1334, completion=457, reasoning=446, cached=1024))

    assert usage.cached == 1024
    assert usage.prompt == 1334
    assert usage.reasoning == 446


# ── ② `prompt_tokens_details` 整个缺 ⇒ `cached == 0` 且不影响 `prompt` ─────────


def test_missing_prompt_tokens_details_yields_zero_cached_and_untouched_prompt():
    """缺失回 0（D2），**不回退成算进 `prompt` 之外的任何地方**。"""
    usage = usage_of(_body(prompt=1334, completion=457, reasoning=446))

    assert usage.cached == 0
    assert usage.prompt == 1334
    assert usage.completion == 457


# ── ③ `as_dict()` 整字典比较，写死字面数字 ────────────────────────────────────


def test_as_dict_is_exactly_this_dictionary_cached_never_enters_total():
    """M2 / M9 的红灯：`cached` 进了 `total`、或 `as_dict()` 不出 `cached` 键，这里就红。

    ⚠️ 写死 `"total": 120` 而不是 `prompt + completion` —— 后者是恒真式。
    """
    usage = Usage(prompt=100, completion=20, cached=999)

    assert usage.as_dict() == {
        "prompt": 100,
        "completion": 20,
        "reasoning": 0,
        "cached": 999,
        "total": 120,
    }


# ── ④ `plus()` 四项各自相加 ──────────────────────────────────────────────────


def test_plus_adds_all_four_buckets_including_cached():
    """M10 的红灯：`plus()` 漏加 `cached`（折叠后恒等于第一条）这里就红。"""
    folded = Usage(prompt=10, completion=2, reasoning=1, cached=7).plus(
        Usage(prompt=300, completion=40, reasoning=5, cached=60)
    )

    assert (folded.prompt, folded.completion, folded.reasoning, folded.cached) == (
        310,
        42,
        6,
        67,
    )


# ── ⑤ `as_dict()` 键集恰等于五键（写死字面量，不用变量算） ─────────────────────


def test_as_dict_key_set_is_exactly_five_literal_keys():
    """M9 的第二道：解析对了但导不出来，这里就红。"""
    assert set(Usage().as_dict()) == {"prompt", "completion", "reasoning", "cached", "total"}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 · 账本面与落盘面（⑥–⑪）
# ═══════════════════════════════════════════════════════════════════════════


def _reply(usage_body: dict | None) -> Reply:
    """`raw` 里放端点回包，`usage` 走 `usage_of()` 解析 —— **两组数各走各的路**。

    账本若实现成「记的就是 `reply.usage`」，`cached_matches_endpoint` 就成了恒真式；
    这里让原始 body 从 `raw` 出发、解析侧从 `usage_of()` 出发，才判得到解析这一段。
    """
    return Reply(
        text="答案",
        usage=usage_of(usage_body) if usage_body else Usage(),
        model="qwen3.6-plus",
        raw={"usage": usage_body} if usage_body else {},
    )


# ── ⑥ 账本记一条带 `cached` 的回包 ⇒ 两组数都对，比对属性为真 ────────────────


def test_the_ledger_records_both_the_parsed_and_the_endpoint_reported_cached():
    """M1 的红灯：产品侧 `usage_of()` 不读 `prompt_tokens_details` 时，解析值 0 对不上端点自报的 1024。"""
    ledger = CallLedger()
    entry = ledger.record_reply(1, _reply(_body(prompt=1334, completion=457, reasoning=446, cached=1024)))

    assert entry.usage.cached == 1024
    assert entry.endpoint_cached == 1024
    assert entry.cached_matches_endpoint is True
    assert entry.as_dict()["endpoint_cached_tokens"] == 1024
    assert entry.as_dict()["cached_matches_endpoint"] is True


# ── ⑦ 回包根本没有 `usage` ⇒ `endpoint_cached is None` 且比对属性为 False ─────


def test_a_reply_without_any_usage_reports_none_not_zero():
    """M4 的红灯：**「不知道」不写成「对得上」**（D2）。

    ⚠️ 与「端点报了 `usage` 但没报 `prompt_tokens_details`」是两件事 —— 后者记 `0`，见下。
    """
    entry = CallLedger().record_reply(1, _reply(None))

    assert entry.endpoint_cached is None
    assert entry.cached_matches_endpoint is False

    reported = CallLedger().record_reply(1, _reply(_body(prompt=7, completion=3)))
    assert reported.endpoint_cached == 0, "`usage` 在而 `prompt_tokens_details` 缺 ⇒ 记 0，不是 None"
    assert reported.cached_matches_endpoint is True


# ── ⑧ 端点报 100 而解析值是 0 ⇒ 比对属性为 False（打红假实现的那条） ──────────


def test_a_parser_that_drops_cached_is_caught_by_the_endpoint_comparison():
    """**这条是恒真式的反面**：拿解析后的数去对端点自己报的那个数。

    M5 的红灯：`cached_matches_endpoint` 若写成拿端点的数跟自己比，这里会变绿。
    """
    entry = CallLedger().record_reply(
        1,
        Reply(
            text="答案",
            usage=Usage(prompt=1334, completion=457, reasoning=446, cached=0),  # 坏实现丢了 cached
            model="qwen3.6-plus",
            raw={"usage": _body(prompt=1334, completion=457, reasoning=446, cached=100)},
        ),
    )

    assert entry.endpoint_cached == 100
    assert entry.usage.cached == 0
    assert entry.cached_matches_endpoint is False
    assert entry.total_matches_endpoint is True, "`total` 口径不受牵连（H6 的回归面）"


# ── ⑨ `CallLedger.total` 折两条 ⇒ 整字典比较，写死字面数字 ────────────────────


def test_the_ledger_rollup_is_exactly_this_dictionary():
    """M2 / M10 的红灯：`cached` 进了 `total`、或 `plus()` 漏加 `cached`，这里就红。

    ⚠️ 两条的数字刻意各不相同 —— 都一样的话「汇总写死成常量」的假实现照样全绿。
    """
    ledger = CallLedger()
    ledger.record_reply(1, _reply(_body(prompt=1067, completion=207, reasoning=150, cached=1024)))
    ledger.record_reply(2, _reply(_body(prompt=3291, completion=180, reasoning=123, cached=2048)))

    assert ledger.total.as_dict() == {
        "prompt": 4358,
        "completion": 387,
        "reasoning": 273,
        "cached": 3072,
        "total": 4745,
    }


# ── ⑩ 账本仍然不拦截（D-18 回归） ────────────────────────────────────────────


def test_a_huge_cached_count_still_does_not_block_the_answer():
    """M8 的红灯：账本里若加了「`cached` 超过 X 就拒答」的分支，这里就红。

    D-18 逐字把 P1.7 从「单次解释成本上限」改成「单次解释成本记账」——
    **记账，不拦截**：账本里没有任何阈值、没有任何「超了就……」的分支。
    """
    huge = 10**9
    body = _body(prompt=huge, completion=huge, reasoning=huge, cached=huge)
    script = [
        fakes.tools_step(fakes.call("doc.get", "b0", doctype="Sales Order", name=fakes.ORDER_A)),
        fakes.tools_step(fakes.call("doc.links", "b1", doctype="Sales Order", name=fakes.ORDER_A)),
        fakes.tools_step(
            fakes.call("doc.get", "b2", doctype="Delivery Note", name=fakes.SUBMITTED_DN)
        ),
        fakes.answer_step(f"订单已由发货单 {fakes.SUBMITTED_DN} 发出，工单还是草稿。"),
    ]
    for step in script:
        step["usage"] = body

    result = explain(
        f"帮我看看 {fakes.ORDER_A} 现在什么情况？",
        task_class="explain",
        client=fakes.client_for(fakes.explain_site()),
        models=fakes.models(),
        config=fakes.config(),
        transport=fakes.ScriptedModel(script),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        max_turns=6,
    )

    assert result.cost_ledger.total.cached == 4 * huge
    assert result.trace.stopped == STOP_ANSWERED
    assert result.answer, "答案照样交出去了 —— 记账不拦截"


# ── ⑪ D3 的承重判据：落盘/读回同时钉在 `tests/unit`（进得了 `GATE_VERIFY`） ────
#
# ⚠️ **刻意不 import `tests/context` 的夹具、不用它的 `_session()`**：
# `tests/context` 不在 `missions/p1-insight.json` 的 `commands.test` 里，
# 只钉在那边的判据 `GATE_VERIFY` 复跑不到（plan D3 残余风险）。


def test_the_persisted_usage_payload_has_exactly_these_four_keys():
    """⑪(a) —— M6 的红灯：`store.py` 落盘仍写三键，这里就红。"""
    session = start("S-cache").with_turn(
        Turn("assistant", "答案", usage=Usage(prompt=1334, completion=457, reasoning=446, cached=1024))
    )

    assert set(to_payload(session)["turns"][0]["usage"]) == {
        "prompt",
        "completion",
        "reasoning",
        "cached",
    }


def test_a_cached_hit_survives_the_round_trip_through_the_store():
    """⑪(b) —— M7 的红灯：落四键但**读回只读三键**（静默丢数），这里就红。

    ⚠️ `cached` 必须 **> 0** —— 恒 0 的会话上，一个把 `cached` 丢掉的实现 round-trip 照样相等。
    """
    session = start("S-cache").with_turn(
        Turn("assistant", "答案", usage=Usage(prompt=1334, completion=457, reasoning=446, cached=1024))
    )

    assert from_payload(to_payload(session)) == session
    assert from_payload(to_payload(session)).turns[0].usage.cached == 1024
