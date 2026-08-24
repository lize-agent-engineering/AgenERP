"""① 即时上下文的确定性装配：当前单据 / 角色 / 视图 → 一份**可断言的结构**。

三条规矩，每条都有判据（`tests/context/test_immediate.py`）：

1. **装配面不自己去猜。** 当前单据、角色、视图全由调用方给。这一层不打站点、
   不查权限、不问模型 —— 它只把给进来的东西按 §8.2 的优先级摆好。
2. **产物是结构，不是拼好的字符串。** 字符串没法断言「哪个字段被裁掉了」，
   而「① 当前单据的完整字段永远优先、不可裁剪」这条规则要能被机械判定。
3. **自由文本走 `agenerp.tools.runtime.wrap_free_text`，不抄一套。**
   前端注入的单据字段**不经过工具执行入口**，是 §7.5 此前没有覆盖到的第二条注入面，
   但包法必须与那条咽喉逐字同源 —— 抄一份就会漂移。

**裁剪的方向是从低优先级往高**：③ 记忆、④ schema 先走，① 与 ② 永不裁。
裁到只剩 ① 与 ② 仍超预算时**抛**，不静默截断 —— 静默截断之后，
「上下文里没有那个字段」与「模型没看见那个字段」在事后无从分辨。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from agenerp.tools.runtime import STRUCTURAL_KEYS, wrap_free_text

# 本层包裹自由文本时的 keep 集合 —— **恰好是 `STRUCTURAL_KEYS`，`name` 不在里面**。
# 取舍与残余风险见 `module-boundaries.md` §7.7 的 `Decision`：单据身份由
# `CurrentDocument.doctype` / `.name` 两个专用字段承载，下游不必从字段表里读身份，
# 因此 `name` 没有「不包就会失效的判定面」；而 prompt 命名的 DocType 上 `name` 是人写的自由文本。
# 保守口径（`runtime.py:220` 逐字「漏套比噪声危险」）之下，它该被包。
BOUNDARY_KEEP: frozenset[str] = frozenset(STRUCTURAL_KEYS)

# §8.2 的四条上下文窗口工程规则表达成四个**优先级档**。数字小 = 先保。
TIER_DOCUMENT = 0  # ① 当前单据的完整字段 —— 不可裁剪
TIER_ACTIONS = 1  # ② 已执行动作的审计记录 —— 不可压缩
TIER_MEMORY = 2  # ③ 记忆 —— **本层只留档位，不实现**（Non-Goals 1）
TIER_SCHEMA = 3  # ④ schema 元知识 —— **本层只留档位，不实现**（Non-Goals 2）

TIER_LABELS: dict[int, str] = {
    TIER_DOCUMENT: "① 当前单据",
    TIER_ACTIONS: "② 已执行动作",
    TIER_MEMORY: "③ 记忆",
    TIER_SCHEMA: "④ schema",
}

# 这两档**永不参与裁剪**。规则出处是 §8.2 的「① 当前单据的完整字段永远优先，①不可裁剪」
# 与「② 已执行动作的审计记录不可压缩」。写成常量而不是散在 if 里，是为了让判据能直接引它。
UNTRIMMABLE_TIERS: frozenset[int] = frozenset({TIER_DOCUMENT, TIER_ACTIONS})


class ContextBudgetExceeded(RuntimeError):
    """③ / ④ 全裁光之后 ① 与 ② 仍装不下预算。

    **不降级成截断。** 截断之后模型少看了哪个字段，事后没有任何地方说得出来。
    """


@dataclass(frozen=True)
class CurrentDocument:
    """当前单据：身份两项 + 完整字段表。

    身份（`doctype` / `name`）**单独摆在结构上**，不要求调用方从 `fields` 里再读一遍 ——
    `fields` 里的自由文本是被包裹过的，拿它当身份会把标记串拼进单号。
    """

    doctype: str
    name: str
    fields: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextBlock:
    """摆进上下文窗口的一块内容，带优先级档。`payload` 必须是 JSON 可序列化的。"""

    tier: int
    key: str
    payload: Any

    def size(self) -> int:
        """确定性的体量度量：JSON 化后的字符数。**不用 token 数** —— 那要 tokenizer，
        而本层的判据必须零依赖、零网络，且不同模型的 tokenizer 各不相同。"""
        return len(json.dumps(self.payload, ensure_ascii=False, sort_keys=True))


@dataclass(frozen=True)
class ImmediateContext:
    """① 层的装配产物。`document.fields` 里的自由文本已按 §7.5 包过边界标记。"""

    document: CurrentDocument
    role: str
    view: str
    actions: tuple[str, ...] = ()

    def blocks(self) -> tuple[ContextBlock, ...]:
        """摊成带优先级档的块序列，交给 `trim`。③ / ④ 两档由调用方另外补进来。"""
        return (
            ContextBlock(
                TIER_DOCUMENT,
                "document",
                {
                    "doctype": self.document.doctype,
                    "name": self.document.name,
                    "role": self.role,
                    "view": self.view,
                    "fields": dict(self.document.fields),
                },
            ),
            ContextBlock(TIER_ACTIONS, "actions", list(self.actions)),
        )


def assemble(
    *,
    doctype: str,
    name: str,
    fields: Mapping[str, Any],
    role: str,
    view: str,
    actions: Sequence[str] = (),
) -> ImmediateContext:
    """装配 ① 层。**字段一个不裁、一个不改名**，只按 §7.5 给自由文本套边界标记。"""
    wrapped = wrap_free_text(dict(fields), BOUNDARY_KEEP)
    return ImmediateContext(
        document=CurrentDocument(doctype=doctype, name=name, fields=wrapped),
        role=role,
        view=view,
        actions=tuple(actions),
    )


def trim(blocks: Iterable[ContextBlock], *, budget: int) -> tuple[ContextBlock, ...]:
    """按 §8.2 的优先级裁到预算内，保持调用方给的次序。

    **档内次序是调用方的事**：③ 的「按是否已验证排序」与 ④ 的「按检索相关度排序」
    分属记忆层与检索层（Non-Goals 1/2），本层不替它们排，只保证**先裁 ④ 再裁 ③**、
    且档内从**尾部**开始丢 —— 调用方把最该留的排在前面即可。
    """
    kept = list(blocks)
    droppable = [i for i, b in enumerate(kept) if b.tier not in UNTRIMMABLE_TIERS]
    droppable.sort(key=lambda i: (-kept[i].tier, -i))
    for index in droppable:
        if sum(b.size() for b in kept if b is not None) <= budget:
            break
        kept[index] = None  # type: ignore[call-overload]
    remaining = tuple(b for b in kept if b is not None)
    total = sum(b.size() for b in remaining)
    if total > budget:
        locked = ", ".join(f"{TIER_LABELS[b.tier]}/{b.key}" for b in remaining)
        raise ContextBudgetExceeded(
            f"③ / ④ 已全部裁光，剩下的 {total} 字符仍超预算 {budget}：{locked}。"
            "① 与 ② 不可裁剪（§8.2），**不做静默截断**"
        )
    return remaining
