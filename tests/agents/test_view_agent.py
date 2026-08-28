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

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import view_fakes as fakes  # noqa: E402

from agenerp.dsl.validate import SchemaUnavailable  # noqa: E402
from agenerp.views.loop import (  # noqa: E402
    STOP_PROPOSED,
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


def loop_for(transport, *, site=None, **kwargs) -> ViewLoop:
    return ViewLoop(
        adapter=fakes.adapter_for(transport),
        client=fakes.client_for(site if site is not None else fakes.site()),
        schema=fakes.schema(),
        doctypes=list(fakes.SNAPSHOT_DOCTYPES),
        **kwargs,
    )


def test_a_valid_dsl_becomes_a_proposal():
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.view is not None
    assert proposal.view.name == "worker-today"


def test_the_proposal_carries_the_validation_result():
    """产出**带着**校验结论走 —— 不是「循环内部验过了，相信我」。"""
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.validation is not None
    assert proposal.validation.ok
    assert proposal.validation.errors == ()


def test_the_proposal_carries_the_render_plan():
    """落回是**块粒度**的既有行为（P2.2）。视图 Agent 照样要把它交出来。"""
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])

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
        [fakes.dsl_step("我建议你看一下工单列表。"), fakes.dsl_step(WORKER_VIEW)]
    )

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.view is not None
    assert model.calls == 2, "第一次交的不是 DSL，循环必须把它顶回去再要一次"


def test_a_field_that_does_not_exist_is_pushed_back_and_the_second_try_lands():
    model = fakes.ScriptedModel(
        [fakes.dsl_step(BAD_FIELD_VIEW), fakes.dsl_step(WORKER_VIEW)]
    )

    proposal = loop_for(model).run(REQUEST)

    assert proposal.stop_reason == STOP_PROPOSED
    assert proposal.validation is not None and proposal.validation.ok
    assert model.calls == 2


def test_the_push_back_names_the_field_that_does_not_exist():
    """🔴 回注说不清是哪个字段，模型只能重猜 —— 而重猜要花掉一整轮修复预算。"""
    model = fakes.ScriptedModel(
        [fakes.dsl_step(BAD_FIELD_VIEW), fakes.dsl_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    message = last_messages(model)
    assert "qtyy" in message
    # 校验器逐条的原文要**穿过去**，不许被收敛成一句「校验没过」。
    assert "字段不存在" in message


def test_the_push_back_for_a_missing_doctype_is_not_the_same_message():
    """DocType 找错和字段找错是**两种错法**，回注话术不许混成一句。"""
    model = fakes.ScriptedModel(
        [fakes.dsl_step(BAD_DOCTYPE_VIEW), fakes.dsl_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    message = last_messages(model)
    assert "Werk Order" in message
    assert "DocType 不存在" in message


def test_a_broken_reply_says_the_format_is_wrong_not_the_fields():
    """`WireError` 与 `DslError` 分开的意义就在这一句回注上：
    模型要改的是**输出格式**，不是字段。"""
    model = fakes.ScriptedModel(
        [fakes.dsl_step("我建议你看一下工单列表。"), fakes.dsl_step(WORKER_VIEW)]
    )

    loop_for(model).run(REQUEST)

    assert "JSON" in last_messages(model)


# ── 🔴 三条纪律：绕不过、顶不动就不交、没 schema 不算过 ──────────────────────


def test_a_model_that_never_fixes_it_never_gets_a_view():
    """🔴 **校验绕不过去。** 模型一再交同一份坏 DSL，循环一次都不许放它过。"""
    model = fakes.ScriptedModel([fakes.dsl_step(BAD_FIELD_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.view is None
    assert proposal.stop_reason == STOP_REPAIR_EXHAUSTED


def test_running_out_of_repairs_does_not_downgrade_to_a_partial_view():
    """🔴 **顶不动就不交，不许把过不了的块删掉再交。**

    那正是 `agenerp/dsl/fallback.py` 模块头点名的坏选择：静默丢弃，
    用户以为那块内容本来就不存在。
    """
    model = fakes.ScriptedModel([fakes.dsl_step(BAD_FIELD_VIEW)])

    proposal = loop_for(model).run(REQUEST)

    assert proposal.view is None
    assert proposal.validation is None, "交不出来就没有「校验过了」这回事"
    assert proposal.render_plan is None, "交不出来就没有渲染计划 —— 有它就是降级交付"


def test_the_repair_budget_is_spent_before_giving_up():
    """放弃之前**真的把修复轮用完了** —— 否则「顶回去」是一句空话。"""
    model = fakes.ScriptedModel([fakes.dsl_step(BAD_FIELD_VIEW)])

    loop = loop_for(model, repair_rounds=2)
    loop.run(REQUEST)

    assert model.calls == 3, "首次提交 + 2 次修复 = 3 次"


def test_without_a_schema_nothing_is_proposed_and_no_token_is_spent():
    """🔴 **没有 schema 就没有结论**，且**一次模型调用都不发生**。

    与 `validate(view, None)` 抛 `SchemaUnavailable` 同源。
    先跑一遍再抛等于白烧一次 token —— 而它抛不抛跟模型答什么无关。
    """
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])
    loop = ViewLoop(
        adapter=fakes.adapter_for(model),
        client=fakes.client_for(fakes.site()),
        schema=None,
        doctypes=list(fakes.SNAPSHOT_DOCTYPES),
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
            fakes.dsl_step(WORKER_VIEW),
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
            fakes.dsl_step(WORKER_VIEW),
        ]
    )

    loop_for(model, site=site).run(REQUEST)

    roles = [m.get("role") for m in model.payloads[-1]["messages"]]
    assert "tool" in roles


def test_dsl_validate_and_preview_are_not_on_the_tool_surface():
    """🔴 D2：校验与预览**不是模型可调的工具**，它们由循环无条件执行。

    工具面里有它们，模型就有了「不调就交」这条路 —— 而那正是本项要挡住的形态。
    """
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    offered = model.tools_offered()
    assert "dsl_validate" not in offered
    assert "dsl_preview" not in offered


def test_the_tool_surface_is_exactly_the_three_schema_tools():
    """视图 Agent 要的是 schema 不是数据行。给它 `query.read` / `doc.get`
    只会让它去查数据、烧 token，而答案不在那儿。"""
    model = fakes.ScriptedModel([fakes.dsl_step(WORKER_VIEW)])

    loop_for(model).run(REQUEST)

    assert set(model.tools_offered()) == {"schema_search", "meta_fields", "system_overview"}
