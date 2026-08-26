"""P2.1 · 「未支持的一律落回 Desk」是规则面判定，且 fail-closed。

判据来源：`docs/design/view-dsl-and-eval.md` §10.3「未支持的块/字段类型 → 落回 Desk」
与 D-15 / `p2-views-roadmap.md` 硬约束 ③：**规则能覆盖的流程不 Agent 化。**

## 为什么 `validate` 严格、`plan_render` 兜底 —— 两者管的不是同一件事

- `validate()` 管「**作者写对没有**」：不认识的块类型是 DSL 写错了，当场拒。
- `plan_render()` 管「**这一版渲染器画得了没有**」：它必须能处理一个**比自己新**的 DSL
  （将来加了块类型、或者字段类型是这一版没见过的），此时**落回 Desk**，
  不是炸掉、也不是假装画出来了。

两个方向都是 fail-closed，只是「关」的方式不同。
"""

from __future__ import annotations

from agenerp.dsl.blocks import Block, View
from agenerp.dsl.fallback import RENDERABLE_FIELDTYPES, SUPPORTED_BLOCK_TYPES, plan_render

from tests.dsl.conftest import SALES_SCHEMA


def _view(*blocks: Block) -> View:
    return View(name="v", title="t", blocks=blocks)


def test_a_fully_supported_view_renders_with_nothing_falling_back():
    plan = plan_render(_view(Block(type="list", doctype="Sales Order",
                                   fields=("customer", "transaction_date"))), SALES_SCHEMA)
    assert len(plan.rendered) == 1
    assert plan.fallbacks == ()


def test_a_block_type_this_renderer_does_not_support_falls_back_to_desk():
    unsupported = next((t for t in ("chart", "metric", "explain")
                        if t not in SUPPORTED_BLOCK_TYPES), None)
    if unsupported is None:
        # 这一版全支持 —— 用一个**未来的**块类型走同一条路，见下一条判据。
        return
    plan = plan_render(_view(Block(type=unsupported, doctype="Sales Order",
                                   fields=("grand_total",), agg="sum")), SALES_SCHEMA)
    assert plan.rendered == ()
    assert len(plan.fallbacks) == 1


def test_a_block_type_from_the_future_falls_back_instead_of_raising():
    # 渲染器读到一个它这一版根本不认识的类型时，**必须落回 Desk**。
    # 炸掉会让整个视图打不开；静默丢弃会让用户以为那块内容本来就不存在。
    plan = plan_render(_view(Block(type="kanban", doctype="Sales Order",
                                   fields=("status",))), SALES_SCHEMA)
    assert plan.rendered == ()
    assert len(plan.fallbacks) == 1
    assert "kanban" in plan.fallbacks[0].reason


def test_a_field_whose_type_this_renderer_cannot_draw_makes_its_block_fall_back():
    # `terms` 是 `Text Editor`（富文本）。渲染器画不了就整块落回，
    # **不许悄悄把这一列删掉再画** —— 那是「画出来了但画的不是用户要的东西」。
    assert "Text Editor" not in RENDERABLE_FIELDTYPES
    plan = plan_render(_view(Block(type="list", doctype="Sales Order",
                                   fields=("customer", "terms"))), SALES_SCHEMA)
    assert plan.rendered == ()
    assert len(plan.fallbacks) == 1
    assert "terms" in plan.fallbacks[0].reason


def test_a_supported_block_still_renders_when_a_sibling_block_falls_back():
    # 落回是**块粒度**的，不是整个视图一起陪葬。
    good = Block(type="list", doctype="Sales Order", fields=("customer",))
    bad = Block(type="kanban", doctype="Sales Order", fields=("status",))
    plan = plan_render(_view(good, bad), SALES_SCHEMA)
    assert len(plan.rendered) == 1
    assert len(plan.fallbacks) == 1
    assert plan.fallbacks[0].index == 1


def test_every_fallback_says_why():
    # §10.3：前端只做提示（「你看不到这个，因为…」）。
    # 一个没有理由的落回，用户看到的是一块凭空消失的内容。
    plan = plan_render(_view(Block(type="kanban", doctype="Sales Order", fields=("status",))),
                       SALES_SCHEMA)
    assert plan.fallbacks[0].reason.strip() != ""


def test_a_field_that_does_not_exist_falls_back_rather_than_being_drawn():
    # 渲染器不是校验器的替代品，但它**也不能**把一个不存在的字段画出来。
    # 两层各自 fail-closed，谁也不依赖对方跑过。
    plan = plan_render(_view(Block(type="list", doctype="Sales Order", fields=("custmoer",))),
                       SALES_SCHEMA)
    assert plan.rendered == ()
    assert "custmoer" in plan.fallbacks[0].reason


def test_the_supported_sets_are_closed_tuples_not_open_containers():
    # 「未支持的一律落回」只有在「支持的是一张封闭表」时才有意义（D-15）。
    assert isinstance(SUPPORTED_BLOCK_TYPES, tuple)
    assert isinstance(RENDERABLE_FIELDTYPES, tuple)


def test_deciding_what_falls_back_involves_no_model_call():
    """D-15 / 硬约束 ③：这一步是规则面，不许交给模型判。

    判法：`agenerp/dsl/fallback.py` 的源码里不许出现任何模型/路由/LLM 的入口。
    这条断言比「我保证没调」硬 —— 它读的是纸面上的字。
    """
    import pathlib

    import agenerp.dsl.fallback as mod

    src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("route(", "llm", "LLM", "complete(", "chat(", "openai", "dashscope"):
        assert forbidden not in src, f"落回判定里出现了模型入口：{forbidden}"
