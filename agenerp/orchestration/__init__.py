"""编排层（P1.3）—— 「会话开场要做的事」与「循环出事时要刹的车」。

落点节是 `docs/architecture/module-boundaries.md` §7.4（熔断）与 §7.6a（本层各文件职责）。

**不是控制循环本体**（模型选工具 → 回注 → 作答 → 门禁 → 强制续跑）：那归 P1.4，
**已落地在 `agenerp/explain/loop.py`**（2026-08-24）。本层的定位一个字没变 ——
交付三个各自可独立构造的对象，由调用方驱动；今天的调用方就是那条循环：

- `opening.open_session` —— 开场装配器：注入 `permission.scope`，产物 + 代价 + 推导事实进开场包
- `navigation` —— 确定性导航策略与度量骨架（零模型，D-15：规则能覆盖的流程不 Agent 化）
- `circuit.DenialBreaker` —— §7.4 的权限拒绝熔断（连续 N 次 403 即刹车）

~~⚠️ **本层与真实控制循环之间的接缝只有单侧**：本层提供，P1.4 消费。
熔断**尚未接到任何真实循环上**……~~
**2026-08-24 已改准（P1.4）**：接缝**两侧都在**了。`agenerp/explain/loop.py` 的 `ExplainLoop`
在每次 `execute` 之后喂 `DenialBreaker.record(result, doctype=...)`，起步先调 `open_session()`；
「真实会话里它一定被调用到」由 `tests/unit/test_explain_loop.py` 判定
（熔断：`test_breaker_stops_the_loop_after_five_consecutive_denials`；
开场注入：`test_opening_injection_actually_hits_the_site_before_the_model_speaks`，
断言落在**假站点的请求记录**上而不是开场包的标志位上）。
⚠️ **`navigation` 这一件仍是单侧**：它的策略今天没有被那条循环消费
（循环里选工具的是模型，不是 `ScopeFirstStrategy`）—— 照实记，不含糊带过。
"""

from __future__ import annotations

from agenerp.orchestration.circuit import (
    DENIAL_THRESHOLD,
    BreakerReport,
    DenialBreaker,
    is_permission_denial,
    result_is_permission_denial,
)
from agenerp.orchestration.navigation import (
    STEP_ANSWER,
    STEP_EXECUTE,
    STEP_REFUSE,
    Hop,
    MetricRun,
    NavigationState,
    NavigationTask,
    ScopeFirstStrategy,
    Step,
    TaskMetric,
    run_metric,
)
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
    "STEP_ANSWER",
    "STEP_EXECUTE",
    "STEP_REFUSE",
    "Hop",
    "MetricRun",
    "NavigationState",
    "NavigationTask",
    "ScopeFirstStrategy",
    "Step",
    "TaskMetric",
    "run_metric",
    "DENIAL_THRESHOLD",
    "BreakerReport",
    "DenialBreaker",
    "is_permission_denial",
    "result_is_permission_denial",
)
