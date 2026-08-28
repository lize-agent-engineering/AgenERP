"""能力声明：任务类目 → 最低能力 · 模型 → 具备能力。

`docs/architecture/model-management.md` §12.1 ③ 的逐字要求是「每个 Agent 声明所需最低模型能力
……换模型时校验，**不满足则明确失败，绝不静默降级**」。本模块是那句话第一次变成
**可断言**的东西：声明放在这里，校验器也放在这里，判据在 `tests/routing/test_capabilities.py`。

三条摆放上的硬规矩：

- **未观测的能力不声明。** 模型档案里没写的能力一律按"不具备"处理。反过来（默认具备、
  没观测到问题就放行）会让"不满足则失败"退化成"没人拦就过"。
- **能力必须是"能被一次真实调用证伪"的东西。** 速度与价格不是能力，它们是选型偏好；
  混进来会让"能力不满足则失败"退化成"按价格排序"。备选与否决理由见 owner doc §12.5。
- **`multi_hop` 今天没有低成本的自动判定法**，它的取值来自人写的模型档案而非探测。
  这一条在 owner doc §12.5 里逐字写着，**不许读成"已校验"**。

本模块与 `docs/architecture/model-management.md` §12.5 的三张 `machine-read` 表**逐行同构**，
同构由 `tests/routing/test_capabilities.py` 判定：文档改了、代码没改，测试就红。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from agenerp.routing.errors import DeclarationError

# 能力维度。取值封闭：不在这个元组里的名字，出现在任何一张声明表里都是声明错误。
# 每一项都必须能被一次真实调用证伪 —— 否决 `vision` / `embedding`（本期无消费者，
# 声明了也无人校验），否决"速度"/"价格"（那是选型偏好，不是能力）。
CAPABILITIES = (
    "tool_calling",   # 能按 JSON 动作协议发起工具调用（§12.3 结论 1）
    "long_context",   # 能吃下系统指令 + 工具定义 + DocType schema 的稳定前缀（§12.1 ③）
    "reasoning",      # 能做需要多步演绎的归因/诊断（§12.1 ③"推理强度"）
    "multi_hop",      # 能跨单据追溯血缘并把追到的东西用上（§12.3 结论 3）
)

# 任务类目。**不发明新类目**：四档全部来自 owner doc §12.1 ② 与 §12.3 两张表，
# 对齐结果逐行写在 §12.5。⚠️ 四档的边界未经真实提问分布验证，P1.4 解释 Agent 落地后
# 很可能要重划 —— 这一条在 §12.5 里逐字写着，不得读成已定型。
TASK_CLASSES = ("permission", "explain", "lineage", "shape")

# 任务类目 → 最低能力集。空集不是合法取值：一个"谁都能接"的类目等于没有分档。
TASK_MINIMUM_CAPABILITIES: Mapping[str, frozenset[str]] = {
    "permission": frozenset({"tool_calling"}),
    "explain": frozenset({"tool_calling"}),
    "lineage": frozenset({"tool_calling", "reasoning", "multi_hop"}),
    "shape": frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
}


@dataclass(frozen=True)
class ModelProfile:
    """一个模型的能力档案。

    `is_reasoning_model` **不是** `reasoning` 能力的同义词，两者刻意分开：

    - `reasoning`（能力）：它推得动多步演绎。
    - `is_reasoning_model`（计费形态）：它的回包会计 reasoning token，
      成本必须按 reasoning 计（D-11：`qwen3.6-plus` 回两个字也烧约 195 reasoning token）。
      P1.7 的**成本记账**读的是这一位（D-18：记账但不拦截，**没有阈值**）。

    一个模型可以推理很强却不计 reasoning token，反之亦然，所以不能合成一位。
    """

    name: str
    capabilities: frozenset[str]
    is_reasoning_model: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))

    def missing_for(self, task_class: str) -> tuple[str, ...]:
        """该模型相对某任务类目**缺哪几项能力**，排序输出以便断言与人读。"""
        return tuple(sorted(minimum_capabilities(task_class) - self.capabilities))

    def satisfies(self, task_class: str) -> bool:
        return not self.missing_for(task_class)


# 本仓**实测过**的模型档案。这是一份配置种子，不是厂商绑定：
# 端点、凭据、默认模型名全部从 `AGENERP_LLM_*` 环境变量来（见 `config.py`），
# 产品包里没有任何厂商端点或厂商 SDK。人可以增删这张表而不改任何代码路径。
# 出处逐行写在 owner doc §12.5 的 `model-profiles` 表里。
KNOWN_MODEL_PROFILES: Mapping[str, ModelProfile] = {
    # P1.0 第二轮实测过的两个（2026-08-24）。`multi_hop` 的取值**首次有本项目
    # 实测支撑**，不再只靠人填 —— 见 §12.5 出处列与 `docs/evidence/p1-entry-gate-round2/`。
    "qwen3.8-max": ModelProfile(
        name="qwen3.8-max",
        capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
        is_reasoning_model=True,
    ),
    "qwen3.7-plus-2026-05-26": ModelProfile(
        name="qwen3.7-plus-2026-05-26",
        capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
        is_reasoning_model=True,
    ),
    "qwen3.6-plus": ModelProfile(
        name="qwen3.6-plus",
        capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
        is_reasoning_model=True,
    ),
    "qwen-plus": ModelProfile(
        name="qwen-plus",
        capabilities=frozenset({"tool_calling", "long_context"}),
        is_reasoning_model=False,
    ),
    # 2026-08-27 实测加入（P2.0R 评测要用）。**只声明探到的那两项** ——
    # 探针给了工具定义，它真发起了 `meta_fields({"doctype": "Sales Order"})` ⇒ `tool_calling`；
    # 回包 `completion_tokens_details.reasoning_tokens = 33` ⇒ 计 reasoning token。
    # ⚠️ `long_context` / `reasoning` / `multi_hop` **那次探针判不了，因此一律不声明** ——
    # 「未观测的能力不声明」是本模块第一条摆放规矩。这意味着 glm-5.2 今天只够
    # `permission` 与 `explain` 两档；要接 `lineage` / `shape` 得先有两跳题的实测。
    # 2026-08-27 实测加入（独立评测集 60 条要用，本模型免费额度满格）。
    # 同样**只声明探到的两项**：探针给了工具定义，它真发起了
    # `meta_fields({"doctype": "Sales Order"})` ⇒ `tool_calling`；
    # 回包 `reasoning_tokens = 71` ⇒ 计 reasoning token。
    # ⚠️ `long_context` / `reasoning` / `multi_hop` 那次探针判不了 ⇒ **不声明**。
    "kimi-k3": ModelProfile(
        name="kimi-k3",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    "glm-5.2": ModelProfile(
        name="glm-5.2",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    # 2026-08-27 实测加入（人指定的备选：glm-5.2 额度不够时用）。
    # **只声明探到的那两项** —— 探针给了工具定义，两个都真发起了
    # `meta_fields({"doctype": "Sales Order"})`；回包都计 reasoning
    # （`qwen3.8-flash` 52 · `qwen3.7-flash` 436）。
    # ⚠️ `long_context` / `reasoning` / `multi_hop` 那次探针**判不了 ⇒ 一律不声明**
    # ⇒ 两个今天都只够 `permission` / `explain` 两档，接不了 `lineage` / `shape`。
    "qwen3.8-flash": ModelProfile(
        name="qwen3.8-flash",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    "qwen3.7-flash": ModelProfile(
        name="qwen3.7-flash",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    # 2026-08-28 实测加入（人授权的第三批：前四个免费额度全部用尽）。
    # **只声明探到的那两项** —— 三个都真发起了 `meta_fields(...)`；回包都计 reasoning
    # （`deepseek-v4-pro-0813` 41 · `qwen3.8-2.4t-a95b` 85 · `qwen3.7-flash-2026-07-15` 356）。
    # ⚠️ `long_context` / `reasoning` / `multi_hop` **判不了 ⇒ 一律不声明**
    # ⇒ 三个今天都只够 `permission` / `explain` 两档。
    # ⚠️ 探针里记一笔：`qwen3.8-2.4t-a95b` 把 doctype 写成了**中文「销售订单」**
    #    （另两个写英文名）—— 站点上不存在那个名字。这不是能力声明，是观察。
    "deepseek-v4-pro-0813": ModelProfile(
        name="deepseek-v4-pro-0813",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    "qwen3.8-2.4t-a95b": ModelProfile(
        name="qwen3.8-2.4t-a95b",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    "qwen3.7-flash-2026-07-15": ModelProfile(
        name="qwen3.7-flash-2026-07-15",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=True,
    ),
    "qwen3:14b": ModelProfile(
        name="qwen3:14b",
        capabilities=frozenset({"tool_calling"}),
        is_reasoning_model=False,
    ),
}


def minimum_capabilities(task_class: str) -> frozenset[str]:
    """某任务类目的最低能力集。类目不认识时**指名报错**，不回空集。

    回空集会让"未知类目"静默变成"谁都能接"，那正是本模块存在的理由的反面。
    """
    try:
        return TASK_MINIMUM_CAPABILITIES[task_class]
    except KeyError:
        raise DeclarationError(
            f"未知任务类目 {task_class!r}；已声明的是 {list(TASK_CLASSES)}"
        ) from None


def validate_task_requirements(table: Mapping[str, Iterable[str]]) -> None:
    """校验「任务类目 → 最低能力」声明表。四类畸形各有独立的失败消息。"""
    declared = set(table)
    missing = [t for t in TASK_CLASSES if t not in declared]
    if missing:
        raise DeclarationError(f"任务类目缺条目：{missing}")
    unknown = sorted(declared - set(TASK_CLASSES))
    if unknown:
        raise DeclarationError(f"声明表里出现枚举外的任务类目：{unknown}")
    for task, caps in table.items():
        caps = frozenset(caps)
        if not caps:
            raise DeclarationError(
                f"任务类目 {task!r} 的最低能力是空集：空集等于不分档，"
                "而分档正是 §12.1 ③ 要求的东西"
            )
        outside = sorted(caps - set(CAPABILITIES))
        if outside:
            raise DeclarationError(f"任务类目 {task!r} 声明了枚举外的能力：{outside}")


def validate_model_profile(profile: ModelProfile) -> None:
    """校验一份模型档案。名字为空、或声明了枚举外的能力，都是声明错误。"""
    if not profile.name or not profile.name.strip():
        raise DeclarationError("模型档案缺名字")
    outside = sorted(profile.capabilities - set(CAPABILITIES))
    if outside:
        raise DeclarationError(
            f"模型 {profile.name!r} 声明了枚举外的能力：{outside}；"
            f"已声明的能力是 {list(CAPABILITIES)}"
        )


def validate_declarations() -> None:
    """把本模块自己带的三份声明全过一遍。导入期不自动跑 —— 由判据显式调用，
    免得一处笔误让整个包 import 不动（那会把一个声明错误放大成产品事故）。"""
    validate_task_requirements(TASK_MINIMUM_CAPABILITIES)
    for profile in KNOWN_MODEL_PROFILES.values():
        validate_model_profile(profile)
