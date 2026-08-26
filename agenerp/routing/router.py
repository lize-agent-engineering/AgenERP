"""路由器：**能力不满足就明确失败。**

`docs/architecture/model-management.md` §12.1 ③ 逐字要求「换模型时校验，
**不满足则明确失败，绝不静默降级**」。本模块是那句话的执行面，规矩只有三条：

1. **只在候选里挑「满足最低能力」的**。挑不到就抛，抛的时候逐条列出
   **缺哪几项能力、缺在哪个模型上** —— 只说"路由失败"等于让人去猜。
2. **点名指定的模型（`requested`）同样校验。** "我点名要它"不是豁免。
   静默降级最常见的形态就是"用户点名了，那就别拦"。
3. **绝不换、绝不放宽。** 强模型不在候选里时，`route('lineage', ...)` 抛，
   **不回**那个凑合的弱模型。判据是 `tests/routing/test_router.py` 的降级反测。
4. **配置里的模型名（`config.model` = `AGENERP_LLM_MODEL`）就是点名。**
   不传 `requested` 时它顶上，走**同一条**取档案 + 校验的路。配了 A 调 B 那条路
   在本模块里不存在（module-boundaries §7.25）。

候选顺序 = **调用方的偏好顺序**，第一个满足的胜出 —— **前提是 `config.model` 为空**。
`from_env()` 保证它非空，所以**环境驱动的路径上这条偏好顺序事实上失效**：那条路上
永远是「配的那个模型，或明确失败」（§7.25 的残余风险 D3，照实登记，不是遗漏）。
刻意不按"快"或"便宜"排序：速度与价格不是能力（见 owner doc §12.5 的否决理由），
把它们塞进排序会让本模块从"能力闸"退化成"价目表"。

**全是确定性规则，零模型参与**（D-15：规则能覆盖的流程不 Agent 化）。
这里没有任何"让模型决定用哪个模型"的路径。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from agenerp.routing.adapter import ChatAdapter
from agenerp.routing.capabilities import ModelProfile, minimum_capabilities
from agenerp.routing.config import LlmConfig
from agenerp.routing.config import from_env as config_from_env
from agenerp.routing.errors import RoutingError


def _as_sequence(models: Iterable[ModelProfile] | Mapping[str, ModelProfile]) -> tuple[ModelProfile, ...]:
    if isinstance(models, Mapping):
        return tuple(models.values())
    return tuple(models)


def _explain(task_class: str, candidates: tuple[ModelProfile, ...]) -> str:
    needed = sorted(minimum_capabilities(task_class))
    lines = [
        f"任务类目 {task_class!r} 的最低能力是 {needed}，"
        f"下列 {len(candidates)} 个候选模型没有一个满足（**不降级、不换、不放宽**）："
    ]
    lines += [f"  - {p.name}：缺 {list(p.missing_for(task_class))}" for p in candidates]
    return "\n".join(lines)


def route(
    task_class: str,
    *,
    models: Iterable[ModelProfile] | Mapping[str, ModelProfile],
    requested: str | None = None,
    config: LlmConfig | None = None,
    transport=None,
) -> ChatAdapter:
    """给一个任务类目挑模型，挑不到就抛。

    `requested` 走**同一条校验**：先按名字取出那份档案（取不到 → 抛），
    再拿它当唯一候选去过同一个集合包含判定。

    **`requested` 不给时，`config.model` 顶上**（去首尾空白后非空即算点名）——
    显式的 `requested` 压过它。配置里的模型名从此是真的默认模型名，
    不是一个被忽略的字段（`docs/architecture/model-management.md` §12.5）。
    """
    minimum_capabilities(task_class)  # 未知类目在这里就抛，不拖到挑完模型之后
    candidates = _as_sequence(models)
    if not candidates:
        raise RoutingError(f"任务类目 {task_class!r} 没有任何候选模型档案可挑")

    resolved_config = config if config is not None else config_from_env()
    if requested is None:
        requested = (resolved_config.model or "").strip() or None

    if requested is not None:
        named = [p for p in candidates if p.name == requested]
        if not named:
            raise RoutingError(
                f"点名的模型 {requested!r} 不在候选档案里；"
                f"候选是 {[p.name for p in candidates]}"
            )
        candidates = tuple(named)

    for profile in candidates:
        if profile.satisfies(task_class):
            return ChatAdapter(
                resolved_config, model=profile.name, profile=profile, transport=transport
            )

    raise RoutingError(_explain(task_class, candidates))
