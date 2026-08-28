"""🔴 P2.3 · 视图 Agent 的判据本体。`02-WBS.md` §5 第 103 行那条验收命令打的就是本文件。

    python3 -m pytest tests/agents/test_view_agent.py -q

**零 token、零活栈、零凭据。** 模型是剧本假件，schema 是活站点导出的真快照
（`agenerp/schema/view-schema.json`），站点是 `tests/tools/conftest.py` 的假站点。

## 本文件验什么、不验什么

**验**：循环。校验绕不绕得过 · 错了顶不顶得回去 · 顶不动时交不交 · 没 schema 时算不算过。

⚠️ **不验**：工具层的真实性（那是 `tests/tools/**` 与 Phase 3 live 判据的活）·
模型到底聪不聪明（那是量化评测的活，Phase 4）。
**这句话写在这里，免得这一轮全绿被当成「视图 Agent 能用了」。**
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import view_fakes as fakes  # noqa: E402

from agenerp.dsl.blocks import (  # noqa: E402
    AGGREGATES,
    BLOCK_TYPES,
    CHART_KINDS,
    FILTER_OPERATORS,
)
from agenerp.dsl.validate import SchemaUnavailable  # noqa: E402
from agenerp.routing import RoutingError  # noqa: E402
from agenerp.views.wire import view_json_schema  # noqa: E402
from agenerp.views.loop import (  # noqa: E402
    STOP_PROPOSED,
    SYSTEM_PROMPT,
    propose_view,
    STOP_REPAIR_EXHAUSTED,
    ViewLoop,
)

WORKER_VIEW = {
    "name": "worker-today",
    "title": "今天的工单",
    "blocks": [
        {
            "type": "list",
            "title": "工单",
            "doctype": "Work Order",
            "fields": ["production_item", "qty", "status"],
            "sort": ["planned_start_date", "asc"],
            "limit": 50,
        }
    ],
}

REQUEST = "我想看今天要做的工单"


def _schema_enum(path: str) -> list:
    """从生成的 JSON Schema 里取一个枚举 —— **判据读的是产物，不是常量表**。"""
    block = view_json_schema()["properties"]["blocks"]["items"]["properties"]
    if path == "filters-operator":
        return block["filters"]["items"]["prefixItems"][1]["enum"]
    return block[path]["enum"]


def loop_for(transport, *, site=None, **kwargs) -> ViewLoop:
    return ViewLoop(
        adapter=fakes.adapter_for(transport),
        client=fakes.client_for(site if site is not None else fakes.site()),
        schema=fakes.schema(),
        **kwargs,
    )


def test_a_valid_dsl_becomes_a_proposal():
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.view is not None
    assert proposal.view.name == "worker-today"


def test_the_proposal_carries_the_validation_result():
    """产出**带着**校验结论走 —— 不是「循环内部验过了，相信我」。"""
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.validation is not None
    assert proposal.validation.ok
    assert proposal.validation.errors == ()


def test_the_proposal_carries_the_render_plan():
    """落回是**块粒度**的既有行为（P2.2）。视图 Agent 照样要把它交出来。"""
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.render_plan is not None
    assert len(proposal.render_plan.rendered) == 1
    assert proposal.render_plan.fallbacks == ()


# ── 拒绝路：交错了要顶回去 ──────────────────────────────────────────────────

BAD_FIELD_VIEW = {
    "name": "worker-today",
    "title": "今天的工单",
    "blocks": [
        {
            "type": "list",
            "doctype": "Work Order",
            # `qty` 真实存在，`qtyy` 不存在 —— 这是 L2「字段不存在」那条路径。
            # ⚠️ 刻意不用 `Sales Order.custmoer`：`Sales Order` 不在这份快照的 8 张表里，
            # 那条会退化成「DocType 不存在」，验的就不是同一件事了。
            "fields": ["production_item", "qtyy"],
        }
    ],
}

BAD_DOCTYPE_VIEW = {
    "name": "worker-today",
    "title": "今天的工单",
    "blocks": [{"type": "list", "doctype": "Werk Order", "fields": ["qty"]}],
}


def last_messages(model: fakes.ScriptedModel) -> str:
    """最后一次调用里，模型看到的全部文本。回注是不是**说清了**，就看它。"""
    return "\n".join(str(m.get("content") or "") for m in model.payloads[-1]["messages"])


def test_a_reply_that_is_not_dsl_is_pushed_back_and_the_second_try_lands():
    model = fakes.ScriptedModel(
        [fakes.submit_step("我建议你看一下工单列表。"), fakes.submit_step(WORKER_VIEW)]
    )

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.view is not None
    assert model.calls == 2, "第一次交的不是 DSL，循环必须把它顶回去再要一次"


def test_a_field_that_does_not_exist_is_pushed_back_and_the_second_try_lands():
    model = fakes.ScriptedModel(
        [fakes.submit_step(BAD_FIELD_VIEW), fakes.submit_step(WORKER_VIEW)]
    )

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.validation is not None and proposal.validation.ok
    assert model.calls == 2


def test_the_push_back_names_the_field_that_does_not_exist():
    """🔴 回注说不清是哪个字段，模型只能重猜 —— 而重猜要花掉一整轮修复预算。"""
    model = fakes.ScriptedModel(
        [fakes.submit_step(BAD_FIELD_VIEW), fakes.submit_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    message = last_messages(model)
    assert "qtyy" in message
    # 校验器逐条的原文要**穿过去**，不许被收敛成一句「校验没过」。
    assert "字段不存在" in message


def test_the_push_back_for_a_missing_doctype_is_not_the_same_message():
    """DocType 找错和字段找错是**两种错法**，回注话术不许混成一句。"""
    model = fakes.ScriptedModel(
        [fakes.submit_step(BAD_DOCTYPE_VIEW), fakes.submit_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    message = last_messages(model)
    assert "Werk Order" in message
    assert "DocType 不存在" in message


def test_a_broken_reply_says_the_format_is_wrong_not_the_fields():
    """`WireError` 与 `DslError` 分开的意义就在这一句回注上：
    模型要改的是**输出格式**，不是字段。"""
    model = fakes.ScriptedModel(
        [fakes.submit_step("我建议你看一下工单列表。"), fakes.submit_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    assert "JSON" in last_messages(model)


# ── 🔴 三条纪律：绕不过、顶不动就不交、没 schema 不算过 ──────────────────────


def test_a_model_that_never_fixes_it_never_gets_a_view():
    """🔴 **校验绕不过去。** 模型一再交同一份坏 DSL，循环一次都不许放它过。"""
    model = fakes.ScriptedModel([fakes.submit_step(BAD_FIELD_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.view is None
    assert proposal.stop_reason == STOP_REPAIR_EXHAUSTED


def test_running_out_of_repairs_does_not_downgrade_to_a_partial_view():
    """🔴 **顶不动就不交，不许把过不了的块删掉再交。**

    那正是 `agenerp/dsl/fallback.py` 模块头点名的坏选择：静默丢弃，
    用户以为那块内容本来就不存在。
    """
    model = fakes.ScriptedModel([fakes.submit_step(BAD_FIELD_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.view is None
    assert proposal.validation is None, "交不出来就没有「校验过了」这回事"
    assert proposal.render_plan is None, "交不出来就没有渲染计划 —— 有它就是降级交付"


def test_the_repair_budget_is_spent_before_giving_up():
    """放弃之前**真的把修复轮用完了** —— 否则「顶回去」是一句空话。"""
    model = fakes.ScriptedModel([fakes.submit_step(BAD_FIELD_VIEW)])

    loop = loop_for(model, repair_rounds=2)
    loop.run(REQUEST)

    assert model.calls == 3, "首次提交 + 2 次修复 = 3 次"


def test_without_a_schema_nothing_is_proposed_and_no_token_is_spent():
    """🔴 **没有 schema 就没有结论**，且**一次模型调用都不发生**。

    与 `validate(view, None)` 抛 `SchemaUnavailable` 同源。
    先跑一遍再抛等于白烧一次 token —— 而它抛不抛跟模型答什么无关。
    """
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])
    loop = ViewLoop(
        adapter=fakes.adapter_for(model),
        client=fakes.client_for(fakes.site()),
        schema=None,
    )

    with pytest.raises(SchemaUnavailable):
        loop.run(REQUEST)

    assert model.calls == 0


# ── 🔴 工具面：给它三个 schema 工具，不给校验、不给数据 ──────────────────────


def test_the_model_can_navigate_schema_before_submitting():
    """工具**真的被执行了** —— 断言站点收到了请求，不是「循环没炸」。

    ⚠️ 只断言 `model.calls == 2` 会**为错误的理由通过**：空 `content` 走
    `WireError` 那条路也是两次调用。判据必须能分开这两件事。
    """
    site = fakes.site()
    model = fakes.ScriptedModel(
        [
            fakes.tools_step(fakes.call("schema.search", keywords="工单")),
            fakes.submit_step(WORKER_VIEW),
        ]
    )

    proposal = loop_for(model, site=site).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert site.requests, "schema.search 没有打到站点 —— 工具压根没执行"
    assert any(turn["kind"] == "tools" for turn in proposal.trace.turns)


def test_a_tool_result_is_fed_back_to_the_model():
    """取回来的东西要**回注**给模型，否则它下一轮还是什么都不知道。"""
    site = fakes.site()
    model = fakes.ScriptedModel(
        [
            fakes.tools_step(fakes.call("meta.fields", doctype="Work Order")),
            fakes.submit_step(WORKER_VIEW),
        ]
    )

    loop_for(model, site=site).run(REQUEST)

    roles = [m.get("role") for m in model.payloads[-1]["messages"]]
    assert "tool" in roles


def test_dsl_validate_and_preview_are_not_on_the_tool_surface():
    """🔴 D2：校验与预览**不是模型可调的工具**，它们由循环无条件执行。

    工具面里有它们，模型就有了「不调就交」这条路 —— 而那正是本项要挡住的形态。
    """
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    offered = model.tools_offered()
    assert "dsl_validate" not in offered
    assert "dsl_preview" not in offered


def test_the_tool_surface_is_exactly_the_three_schema_tools():
    """视图 Agent 要的是 schema 不是数据行。给它 `query.read` / `doc.get`
    只会让它去查数据、烧 token，而答案不在那儿。"""
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    assert set(model.tools_offered()) == {
        "schema_search", "meta_fields", "system_overview", "view_submit",
    }


# ── 产品入口：走 route()，不静默降级 ────────────────────────────────────────


def test_the_product_entry_routes_through_the_view_task_class():
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    proposal = propose_view(
        REQUEST,
        client=fakes.client_for(fakes.site()),
        schema=fakes.schema(),
        models=fakes.models(),
        config=fakes.config(),
        transport=model,
    )

    assert proposal.stop_reason == STOP_PROPOSED


def test_a_model_that_cannot_call_tools_is_refused_not_downgraded():
    """§12.1 ③「绝不静默降级」—— 能力不满足就明确失败。

    视图 Agent 不调工具就无从知道字段存不存在，`view` 档的 `tool_calling` 挡的就是这个。
    """
    weak = [
        fakes.ModelProfile(
            name="fake-view-builder", capabilities=frozenset(), is_reasoning_model=False
        )
    ]

    with pytest.raises(RoutingError):
        propose_view(
            REQUEST,
            client=fakes.client_for(fakes.site()),
            schema=fakes.schema(),
            models=weak,
            config=fakes.config(),
            transport=fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)]),
        )


def test_the_repair_budget_is_not_reachable_from_the_product_entry():
    """🔴 修复预算**不许从产品入口被调**。

    形态照 `tests/unit/test_explain_runaway_guard.py` 的 H4 ⑤ ——
    那里逐字断言失控闸不在 `explain.__code__.co_varnames` 里。同一条理由：
    一个能从产品入口调的闸，等于一个可以被调用方一行关掉的闸。
    评测那类要拆闸的场合自己构造 `ViewLoop`。
    """
    assert "repair_rounds" not in propose_view.__code__.co_varnames


# ── 🔴 交付走「带 JSON Schema 的工具调用」，形状由端点挡 ─────────────────────
#
# 2026-08-28 活体实测抓到的两条，都出在**手搓结构化输出**这一段：
#   ② 模型把 filters 交成对象数组 → 解析崩
#   ③ 提示词里没说块长什么样 → 模型连查 8 轮不组装
# 这正是成熟框架（LangChain `with_structured_output`）替人做掉的那件事。
#
# 人 2026-08-28 裁定：**借思想不引依赖** —— 用 `blocks.py` 的封闭取值生成 JSON Schema，
# 当作工具参数交给模型，**端点替我们把形状挡住**。
# D-22 / D-22.1 不翻（Deep Agents 的 Filesystem middleware 删不掉，
# 会给一个零写工具面凭空开一条绕过 has_permission 的写通道）。


def test_the_schema_enumerates_every_block_type():
    """块类型是封闭表。加了一种而 schema 没跟着改，模型就永远不会用它。"""
    enum = _schema_enum("type")
    assert set(enum) == set(BLOCK_TYPES)


def test_the_schema_enumerates_every_filter_operator():
    assert set(_schema_enum("filters-operator")) == set(FILTER_OPERATORS)


def test_the_schema_enumerates_every_aggregate():
    assert set(_schema_enum("agg")) == set(AGGREGATES)


def test_the_schema_enumerates_every_chart_kind():
    assert set(_schema_enum("chart_kind")) == set(CHART_KINDS)


def test_the_schema_makes_filters_an_array_not_an_object():
    """🔴 活体实测那条 ②：模型交了对象数组。**schema 里写死它是数组**，端点先挡一道。"""
    block = view_json_schema()["properties"]["blocks"]["items"]["properties"]
    assert block["filters"]["type"] == "array"
    assert block["filters"]["items"]["type"] == "array"


def test_the_prompt_still_tells_the_model_to_copy_the_ref():
    """P2.0R 实测换来的：`meta.fields` 每行都给 `ref`，**可照抄**。
    这条是「怎么找字段」，不是「交什么形状」—— 留在提示词里。"""
    assert "ref" in SYSTEM_PROMPT


def test_the_submit_tool_is_on_the_surface():
    """交付通道**是**一个工具；校验器**不是**（D2）。两件事不许混。"""
    model = fakes.ScriptedModel([fakes.submit_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    assert "view_submit" in model.tools_offered()


def test_a_plain_text_reply_is_pushed_back_to_the_tool():
    """交付只有一条路。模型直接吐文本时，要明说「用工具交」，不是让它重猜格式。"""
    model = fakes.ScriptedModel(
        # 第一步刻意走**文本**：哪怕文本里就是一份合法 DSL，也不算交付。
        [fakes.dsl_step(WORKER_VIEW), fakes.submit_step(WORKER_VIEW)]
    )

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert "view_submit" in last_messages(model)


# ── 🔴 harness：重复调用自己挡，查够了催它交 ────────────────────────────────
#
# 2026-08-28 活体实测：40 轮那次**端点直接回 400**
# 「同名同参的工具调用连续重复」—— 由端点来杀，我们这边整轮跑飞、什么都留不下。
# ⇒ 这件事要**自己判、自己回注**，而判重复的口径只有一个：
#   `trajectory_full`（名字 + 参数）。按工具名数会把「同一工具不同参数」的探索
#   误判成打转 —— 那个信号在 P2.0R 骗过四次（handoff §3①）。

SEARCH = fakes.call("schema.search", "c0", keywords="工单")


def test_an_identical_repeat_is_pushed_back_instead_of_run_again():
    site = fakes.site()
    model = fakes.ScriptedModel(
        [fakes.tools_step(SEARCH), fakes.tools_step(SEARCH), fakes.submit_step(WORKER_VIEW)]
    )

    proposal = loop_for(model, site=site).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    tool_turns = [t for t in proposal.trace.turns if t["kind"] == "tools"]
    assert len(tool_turns) == 1, "一模一样的第二次不该再打站点"


def test_a_different_argument_is_not_treated_as_a_repeat():
    """🔴 §3①：**同一个工具、不同参数是探索，不是打转。**

    这一条是那个骗过四次的信号的反面判据 —— 少了它，重复保护会把正常探索掐死。
    """
    site = fakes.site()
    model = fakes.ScriptedModel(
        [
            fakes.tools_step(fakes.call("meta.fields", "c0", doctype="Work Order")),
            fakes.tools_step(fakes.call("meta.fields", "c1", doctype="Stock Entry")),
            fakes.submit_step(WORKER_VIEW),
        ]
    )

    proposal = loop_for(model, site=site).run(REQUEST)

    tool_turns = [t for t in proposal.trace.turns if t["kind"] == "tools"]
    assert len(tool_turns) == 2, "换了参数就是探索，不许当重复掐掉"


def test_the_repeat_push_back_tells_the_model_what_to_do():
    model = fakes.ScriptedModel(
        [fakes.tools_step(SEARCH), fakes.tools_step(SEARCH), fakes.submit_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    assert "一模一样" in last_messages(model)


def test_after_enough_tool_turns_the_model_is_told_to_deliver():
    """查够了要催它交。

    实测：真模型连查 8 轮 `meta.fields`（每轮关键词都不同，是探索不是打转），
    始终没进入组装，最后把轮次用光。**轮次是有限的，而模型看不见还剩几轮。**
    """
    steps = [
        fakes.tools_step(fakes.call("meta.fields", f"c{i}", doctype="Work Order", keywords=f"k{i}"))
        for i in range(4)
    ]
    model = fakes.ScriptedModel([*steps, fakes.submit_step(WORKER_VIEW)])

    loop_for(model, tool_turn_nudge=3).run(REQUEST)

    assert "现在就交" in last_messages(model)


def test_a_submit_mixed_with_another_tool_call_answers_every_call_id():
    """🔴 独立收口审计（2026-08-28）抓到的：**混在一轮里的其它工具调用没人应答。**

    OpenAI 兼容端点要求 assistant 消息里**每一个** `tool_call.id` 都有一条对应的
    `role="tool"` 回复。模型完全可能在同一轮里既调 `meta.fields` 又调 `view_submit`
    —— 此前只给 submit 那一条回了话，另一条的 id 无人应答 ⇒ **下一次请求会被端点拒**。

    这与 §3④ 同族：**一个本该被干净处理的形状，会变成整轮跑飞。**
    """
    mixed = {
        "choices": [
            {
                "message": {
                    "role": "assistant", "content": None,
                    "tool_calls": [
                        {"id": "call-a", "type": "function",
                         "function": {"name": "meta_fields",
                                      "arguments": '{"doctype": "Work Order"}'}},
                        {"id": "call-b", "type": "function",
                         "function": {"name": "view_submit",
                                      "arguments": json.dumps(BAD_FIELD_VIEW)}},
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": fakes.usage(),
    }
    model = fakes.ScriptedModel([mixed, fakes.submit_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    sent = model.payloads[-1]["messages"]
    declared = {
        call["id"]
        for m in sent if m.get("role") == "assistant"
        for call in (m.get("tool_calls") or [])
    }
    answered = {m["tool_call_id"] for m in sent if m.get("role") == "tool"}
    assert declared <= answered, f"这些 tool_call 没人应答：{sorted(declared - answered)}"


def test_the_loop_has_no_parameter_it_never_reads():
    """🔴 独立收口审计（2026-08-28）抓到的：**死参数看起来像做过了。**

    当时 `ViewLoop` 收 `doctypes` / `session_id` / `user` 三个参数，**一个都没被读过**，
    而 plan §6 的形状图第一行写着「开场注入（可见范围）」—— 读代码的人会以为
    可见范围被注进去了。判据侧还有三处在往里传，更像真的。

    ⇒ **要么实现它，要么删掉它。** 收口时按 YAGNI 删掉了声明：
    不在验收数字已经产出之后再改模型可见的行为（那会让那些数字不再描述这份代码）。

    本条守的是「不许再长出一个没人读的参数」，用签名比对，不靠人眼看。
    """
    import inspect

    for func in (ViewLoop.__init__, ViewLoop.run, propose_view):
        source = inspect.getsource(func)
        names = set(inspect.signature(func).parameters) - {"self", "request"}
        for name in names:
            # 参数名在函数体里至少要出现一次「被读」的形态。
            body = source.split(")", 1)[-1]
            assert name in body, f"{func.__qualname__} 的参数 {name!r} 从未被读过"
