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


def _view(*blocks: Block) -> View:
    return View(name="v", title="t", blocks=blocks)


def test_a_fully_supported_view_renders_with_nothing_falling_back(schema):
    plan = plan_render(_view(Block(type="list", doctype="Sales Order",
                                   fields=("customer", "transaction_date"))), schema)
    assert len(plan.rendered) == 1
    assert plan.fallbacks == ()


def test_this_version_of_the_renderer_supports_all_five_block_types(schema):
    """这一版五种块全支持 —— 这件事要写死，因为它决定了下一条判据在测什么。

    ⚠️ 原本这里想写「渲染器不支持的块类型落回 Desk」，但这一版没有
    「认识但画不了」的块类型 —— 那样的判据会**恒真而无判别力**，
    也就是本仓说的「半条判据」。所以改成把当前支持面钉死；
    「不认识的类型落回」由下一条（未来块类型）判据实测。
    """
    from agenerp.dsl.blocks import BLOCK_TYPES

    assert SUPPORTED_BLOCK_TYPES == BLOCK_TYPES


def test_a_block_type_from_the_future_falls_back_instead_of_raising(schema):
    # 渲染器读到一个它这一版根本不认识的类型时，**必须落回 Desk**。
    # 炸掉会让整个视图打不开；静默丢弃会让用户以为那块内容本来就不存在。
    plan = plan_render(_view(Block(type="kanban", doctype="Sales Order",
                                   fields=("status",))), schema)
    assert plan.rendered == ()
    assert len(plan.fallbacks) == 1
    assert "kanban" in plan.fallbacks[0].reason


def test_a_field_whose_type_this_renderer_cannot_draw_makes_its_block_fall_back(schema):
    """渲染器画不了就整块落回，**不许悄悄把这一列删掉再画**。

    ⚠️ **本条 2026-08-27 换过例子，照实记**：原来用的是 `Sales Order.terms`
    （`Text Editor`）。P2.2 把富文本改成了**降级渲染**（剥标签只显纯文本），
    于是它不再落回 —— **那一刻这条判据变成了恒真的空壳**。
    换成 `Sales Order Item.item_tax_rate`（`Code`），它今天仍在
    `RENDERABLE_FIELDTYPES` 之外。`test_..._is_actually_unrenderable` 钉住这个前提。
    """
    assert "Code" not in RENDERABLE_FIELDTYPES
    plan = plan_render(_view(Block(type="list", doctype="Sales Order Item",
                                   fields=("item_code", "item_tax_rate"))), schema)
    assert plan.rendered == ()
    assert len(plan.fallbacks) == 1
    assert "item_tax_rate" in plan.fallbacks[0].reason


def test_rich_text_is_degraded_not_dropped_and_not_silently_rendered(schema):
    """富文本：画出来，但明说少了什么。**第三种状态，不是「画得了」也不是「落回」。**

    `module-boundaries.md` §7.23 第 1 条硬约束逐字：建 DOM 只走 `textContent`。
    ⇒ 富文本剥标签只显纯文本。**代价是用户看不到格式** —— 这件事必须出现在
    `degraded` 里并说清原因，否则用户看到的是一段莫名其妙变了样的文字。
    """
    plan = plan_render(_view(Block(type="list", doctype="Sales Order",
                                   fields=("customer", "terms"))), schema)
    assert len(plan.rendered) == 1          # 画得了
    assert plan.fallbacks == ()             # 没落回
    assert len(plan.degraded) == 1          # 但画不全，且说了
    assert "Sales Order.terms" == plan.degraded[0].fieldname
    assert "Desk" in plan.degraded[0].reason


def test_a_supported_block_still_renders_when_a_sibling_block_falls_back(schema):
    # 落回是**块粒度**的，不是整个视图一起陪葬。
    good = Block(type="list", doctype="Sales Order", fields=("customer",))
    bad = Block(type="kanban", doctype="Sales Order", fields=("status",))
    plan = plan_render(_view(good, bad), schema)
    assert len(plan.rendered) == 1
    assert len(plan.fallbacks) == 1
    assert plan.fallbacks[0].index == 1


def test_every_fallback_says_why(schema):
    # §10.3：前端只做提示（「你看不到这个，因为…」）。
    # 一个没有理由的落回，用户看到的是一块凭空消失的内容。
    plan = plan_render(_view(Block(type="kanban", doctype="Sales Order", fields=("status",))),
                       schema)
    assert plan.fallbacks[0].reason.strip() != ""


def test_a_field_that_does_not_exist_falls_back_rather_than_being_drawn(schema):
    # 渲染器不是校验器的替代品，但它**也不能**把一个不存在的字段画出来。
    # 两层各自 fail-closed，谁也不依赖对方跑过。
    plan = plan_render(_view(Block(type="list", doctype="Sales Order", fields=("custmoer",))),
                       schema)
    assert plan.rendered == ()
    assert "custmoer" in plan.fallbacks[0].reason


def test_the_supported_sets_are_closed_tuples_not_open_containers(schema):
    # 「未支持的一律落回」只有在「支持的是一张封闭表」时才有意义（D-15）。
    assert isinstance(SUPPORTED_BLOCK_TYPES, tuple)
    assert isinstance(RENDERABLE_FIELDTYPES, tuple)


def test_deciding_what_falls_back_involves_no_model_call(schema):
    """D-15 / 硬约束 ③：这一步是规则面，不许交给模型判。

    判法：`agenerp/dsl/fallback.py` 的源码里不许出现任何模型/路由/LLM 的入口。
    这条断言比「我保证没调」硬 —— 它读的是纸面上的字。
    """
    import pathlib

    import agenerp.dsl.fallback as mod

    src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("route(", "llm", "LLM", "complete(", "chat(", "openai", "dashscope"):
        assert forbidden not in src, f"落回判定里出现了模型入口：{forbidden}"
