"""「未支持的一律落回 Desk」—— 规则面判定，**没有任何模型调用**。

D-15 / `p2-views-roadmap.md` 硬约束 ③ 逐字：**规则能覆盖的流程不 Agent 化。**
「这一块画得了画不了」是一张封闭表就能答的问题，交给模型判只会多一个不确定来源。
`tests/dsl/test_fallback_to_desk_is_fail_closed.py` 有一条**读本文件源码**的静态断言
守着这件事 —— 它读的是纸面上的字，比一句「我保证没调」硬。

## 为什么这里对不认识的块类型是「落回」，而 `validate.py` 里是「拒绝」

两者管的不是同一件事：

- `validate()` 管「**作者写对没有**」。不认识的块类型 = DSL 写错了，当场拒。
- `plan_render()` 管「**这一版渲染器画得了没有**」。它必须能读一个**比自己新**的 DSL：
  将来加了块类型、或者字段类型是这一版没见过的，此时**落回 Desk** ——
  不是炸掉（整个视图打不开），也不是静默丢弃（用户以为那块内容本来就不存在）。

两个方向都是 fail-closed，只是「关」的方式不同。

## 落回是**块粒度**的

一个块画不了，其余的照画。§10.3 只要求「未支持的落回 Desk」，
没有要求整个视图陪葬 —— 后者会把「有一列是富文本」变成「这个视图打不开」。

## 每一次落回都要说清为什么

§10.3：前端权限只做提示（「你看不到这个，因为…」）。同一条纪律：
**一个没有理由的落回，用户看到的是一块凭空消失的内容。**
"""

from __future__ import annotations

from dataclasses import dataclass

from agenerp.dsl.blocks import Block, View
from agenerp.dsl.schema import SchemaView

# 这一版渲染器画得了的块类型。**封闭**——「未支持的一律落回」只有在
# 「支持的是一张封闭表」时才有意义。
SUPPORTED_BLOCK_TYPES = ("list", "detail", "metric", "chart", "explain")

# 这一版渲染器画得了的字段类型。**封闭**，且刻意保守：
# 宁可多落回几块交给 Desk，不可画出一块「看起来对、其实不是那个意思」的内容。
# 富文本 / 附件 / 签名 / 二维码 / 代码 这些都不在里面 —— 它们要么需要专门的
# 渲染组件，要么本身就承载用户可写自由文本（`contracts.Returns.user_writable_free_text`
# 那个声明位防的是同一件事）。
RENDERABLE_FIELDTYPES = (
    "Data",
    "Link",
    "Dynamic Link",
    "Select",
    "Int",
    "Float",
    "Currency",
    "Percent",
    "Check",
    "Date",
    "Datetime",
    "Time",
    "Small Text",
    "Text",
    "Read Only",
)


@dataclass(frozen=True)
class Fallback:
    """一块落回 Desk 的记录。`index` 是它在 `view.blocks` 里的下标。"""

    index: int
    block_type: str
    reason: str


@dataclass(frozen=True)
class RenderPlan:
    rendered: tuple[Block, ...]
    fallbacks: tuple[Fallback, ...]


def plan_render(view: View, schema: SchemaView) -> RenderPlan:
    """给定一个视图，判断哪些块这一版画得了、哪些落回 Desk。"""
    rendered: list[Block] = []
    fallbacks: list[Fallback] = []

    for index, block in enumerate(view.blocks):
        reason = _why_it_cannot_be_drawn(block, schema)
        if reason:
            fallbacks.append(Fallback(index=index, block_type=block.type, reason=reason))
        else:
            rendered.append(block)

    return RenderPlan(rendered=tuple(rendered), fallbacks=tuple(fallbacks))


def _why_it_cannot_be_drawn(block: Block, schema: SchemaView) -> str:
    """画不了就回一句为什么；画得了回空串。"""
    if block.type not in SUPPORTED_BLOCK_TYPES:
        return (
            f"块类型 {block.type!r} 不在这一版渲染器的支持表里"
            f"（支持 {SUPPORTED_BLOCK_TYPES}），整块落回 Desk"
        )

    if block.type == "explain":
        return ""

    if not block.doctype or not schema.has_doctype(block.doctype):
        return f"DocType {block.doctype!r} 在当前 schema 里不存在，整块落回 Desk"

    for fieldname in block.fields:
        if not schema.has_field(block.doctype, fieldname):
            return (
                f"字段 {block.doctype}.{fieldname} 在当前 schema 里不存在，整块落回 Desk"
            )
        fieldtype = schema.fieldtype(block.doctype, fieldname)
        if fieldtype not in RENDERABLE_FIELDTYPES:
            # 不许「悄悄把这一列删掉再画」——那是画出来了，但画的不是用户要的东西。
            return (
                f"字段 {block.doctype}.{fieldname} 的类型 {fieldtype!r} "
                f"不在这一版渲染器画得了的类型表里，整块落回 Desk"
            )

    return ""
