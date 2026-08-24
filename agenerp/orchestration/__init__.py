"""编排层（P1.3）—— 「会话开场要做的事」与「循环出事时要刹的车」。

落点节是 `docs/architecture/module-boundaries.md` §7.4（熔断）与 §7.6a（本层各文件职责）。

**不是控制循环本体**（模型选工具 → 回注 → 作答 → 门禁 → 强制续跑）：那归 P1.4。
本层交付三个各自可独立构造的对象，由调用方驱动：

- `opening.open_session` —— 开场装配器：注入 `permission.scope`，产物 + 代价 + 推导事实进开场包
- `navigation` —— 确定性导航策略与度量骨架（零模型，D-15：规则能覆盖的流程不 Agent 化）
- `circuit.DenialBreaker` —— §7.4 的权限拒绝熔断（连续 N 次 403 即刹车）

⚠️ **本层与真实控制循环之间的接缝只有单侧**：本层提供，P1.4 消费。
熔断**尚未接到任何真实循环上**，判据能证明的是「喂它 N 次权限拒绝它会刹车」，
不是「真实会话里它一定被调用到」。
"""

from __future__ import annotations

from agenerp.orchestration.opening import (
    CONTRACT_FACT,
    INJECTION_TOOL,
    PACK_FACT,
    InjectionCost,
    OpeningPack,
    open_session,
)

__all__ = (
    "CONTRACT_FACT",
    "INJECTION_TOOL",
    "PACK_FACT",
    "InjectionCost",
    "OpeningPack",
    "open_session",
)
