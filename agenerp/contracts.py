"""工具契约层 v0 · 声明面。

形状逐条对齐 `docs/architecture/module-boundaries.md` §7.1（契约结构）与 §7.3.1
（只读工具也有契约；§7.1 须补 `returns` 段：裁剪规则 / 上限条数 / 必须保留什么），
外加 §7.5 的一个声明位：本工具是否会返回**用户可写自由文本**。

三件事在本模块里，其余都不在：

- `ToolContract` / `Returns` / `Condition`：契约的**声明格式**。§7.1 的 YAML 是文档呈现形式，
  不是运行时格式——运行时用纯 Python 声明，因为 CI 的 `gates-l1` 只 `pip install pytest`，
  `import yaml` 会红在缺依赖上。校验器接受的是**已解析的数据结构**，
  将来外挂一个 YAML → dict 加载器不改变本层任何签名。
- `validate` / `check`：**校验器**。每种拒绝都是独立可测的失败模式，且错误消息指名到
  「哪个工具的哪一段」——十条契约里错一个，不该靠人肉找。
- `Condition.evaluate`：前置条件与后置断言的**求值面**。条件对一个**注入进来的只读上下文**
  求值，本模块**不连任何站点**——这正是 `docs/masterplan/02-WBS.md` P0.2
  「前置条件/后置断言可独立测试」得以成立的机制。

不在本模块内（见 plan `2026-08-21-1022-2` 的 `## Deferred But Adjudicated`）：
§7.4 的权限拒绝熔断（N=5）与 §7.5 的数据边界**包裹动作**——二者是控制循环的运行时部件。
~~P0 阶段还没有控制循环去消费它们，现在实现只能得到「结构存在」的空断言。~~
**2026-08-24 这条前提不再成立**：控制循环已落地在 `agenerp/explain/loop.py`（P1.4），
熔断已由它消费（`agenerp/orchestration/circuit.py`，落点节 §7.4 / §7.8）。
**§7.5 的包裹动作仍未做**，它今天还只是 `Returns.user_writable_free_text` 这个声明位。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

# §5 的风险档位。不是标签，是执行路径，所以取值必须封闭。
RISK_LEVELS = ("L0", "L1", "L2", "L3")

# §7.1 的 `on_violation`。`abort_before_side_effect` 与 `rollback_and_report` 的分工见 §7.1
# 末段（有事务外副作用的只能选前者）；只读工具两个都够不着，它没有可回滚的东西。
ON_VIOLATION_VALUES = ("abort_and_report", "abort_before_side_effect", "rollback_and_report")

APPROVAL_NOT_REQUIRED = "not_required"

# `requires_permission` 里表示写动作的动词。只读工具出现任何一个都是声明与实现打架。
WRITE_VERBS = ("create", "write", "submit", "cancel", "delete", "amend")

# 条件的求值算子。刻意保持封闭且很小：契约要能被人读、被机器判，不是嵌一门语言进来。
OPERATORS = (
    "is_true",       # 事实为真
    "not_empty",     # 事实非空
    "is_empty",      # 事实为空
    "equals",        # 事实 == value
    "contains",      # value ∈ 事实
    "covers_fact",   # 集合意义上，事实 ⊇ 另一条事实（value 是**事实名**，不是字面值）
)


class ContractError(ValueError):
    """契约结构不合法。消息里必须能看出是哪个工具的哪一段。"""


@dataclass(frozen=True)
class ReadOnlyContext:
    """条件求值时注入进来的只读事实集。

    **它不做 I/O**：测试构造一个 `ReadOnlyContext` 即可求值，不需要 ERPNext。
    未登记的事实**不当成假**，而是让条件判为「不满足 + 上下文缺少该事实」——
    静默当假会把「没查」与「查了没有」混成一件事，那正是 §5.0 ① 要挡的错误。
    """

    facts: Mapping[str, Any] = field(default_factory=dict)

    def has(self, name: str) -> bool:
        return name in self.facts

    def get(self, name: str) -> Any:
        return self.facts[name]


@dataclass(frozen=True)
class Evaluation:
    """一次条件求值的结果：满足与否 + 原因。原因是给人看的，`satisfied` 才是判定面。"""

    condition: Condition
    satisfied: bool
    reason: str


@dataclass(frozen=True)
class Condition:
    """一条前置条件或后置断言。

    `text` 是 owner doc 的原文（人读），`fact` / `operator` / `value` 是它的可求值形式（机读）。
    两者并排放着是有意的：只写 `text` 就退回成注释，而注释不可测。
    `source` 记出处（文件 + 章节），使「这条约束是实测踩出来的」这件事本身可被断言。
    """

    text: str
    fact: str
    operator: str = "is_true"
    value: Any = None
    source: str = ""

    def evaluate(self, context: ReadOnlyContext) -> Evaluation:
        if self.operator not in OPERATORS:
            return Evaluation(self, False, f"未知算子 {self.operator!r}")
        if not context.has(self.fact):
            return Evaluation(self, False, f"上下文缺少事实 {self.fact!r}")
        actual = context.get(self.fact)
        satisfied, reason = _apply(self.operator, actual, self.value, context)
        return Evaluation(self, satisfied, reason)


def _apply(operator: str, actual: Any, value: Any, context: ReadOnlyContext) -> tuple[bool, str]:
    if operator == "is_true":
        return bool(actual), f"实际值 {actual!r}"
    if operator == "not_empty":
        return bool(_size(actual)), f"实际条目数 {_size(actual)}"
    if operator == "is_empty":
        return not _size(actual), f"实际条目数 {_size(actual)}"
    if operator == "equals":
        return actual == value, f"实际值 {actual!r}，期望 {value!r}"
    if operator == "contains":
        return value in actual, f"{value!r} {'在' if value in actual else '不在'} {actual!r} 中"
    if not context.has(value):
        return False, f"上下文缺少被比较的事实 {value!r}"
    missing = sorted(set(context.get(value)) - set(actual))
    return not missing, ("全部覆盖" if not missing else f"未覆盖 {missing!r}")


def _size(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 1 if value else 0


def evaluate_all(
    conditions: Iterable[Condition], context: ReadOnlyContext
) -> tuple[Evaluation, ...]:
    """对一组条件逐条求值。**不短路**——一次把所有不满足的原因都给出来。"""
    return tuple(condition.evaluate(context) for condition in conditions)


def unsatisfied(evaluations: Iterable[Evaluation]) -> tuple[Evaluation, ...]:
    return tuple(item for item in evaluations if not item.satisfied)


def check_preconditions(contract: ToolContract, context: ReadOnlyContext) -> tuple[Evaluation, ...]:
    """前置条件：调用之前是否允许调用（只读工具里，它约束的是「什么时候允许停下来」，见 §5.0 ①）。"""
    return evaluate_all(contract.preconditions, context)


def check_postconditions(
    contract: ToolContract, context: ReadOnlyContext
) -> tuple[Evaluation, ...]:
    """后置断言：执行之后必须成立的事。只读工具的后置断言约束的是**返回了什么**。"""
    return evaluate_all(contract.postconditions, context)


@dataclass(frozen=True)
class Returns:
    """§7.3.1 要求补进 §7.1 的 `returns` 段，三项缺一不可，外加 §7.5 的声明位。

    - `trim_rules`：裁剪规则。不裁剪的代价是实测过的——`permission.scope` 不过滤框架 DocType
      是老板 83 / 工人 61，过滤后 34 / 12。
    - `max_rows`：上限条数。
    - `must_keep`：**必须保留什么**。反例同样是实测的：`doc.links` 丢掉 `from_is_submittable`
      会让下游筛选整类丢掉不可提交的业务单据。
    - `user_writable_free_text`：§7.5 的声明位——本工具是否会返回**用户可写自由文本**。
      为真表示这条返回值是提示注入攻击面。**包裹动作不在 v0 内**，此处只留声明。
    """

    trim_rules: tuple[str, ...] = ()
    max_rows: int | None = None
    must_keep: tuple[str, ...] = ()
    user_writable_free_text: bool = False


@dataclass(frozen=True)
class ToolContract:
    """一个工具的契约。字段逐条对齐 §7.1，`returns` 与 `read_only` 来自 §7.3.1 / §7.5。

    `read_only` 为真时校验器会额外收紧：不得声明副作用、不得要写权限、
    `on_violation` 不得是 `rollback_and_report`（没有可回滚的东西）、`approval` 必须 `not_required`。
    """

    tool: str
    target: str
    risk: str
    requires_permission: tuple[str, ...] = ()
    preconditions: tuple[Condition, ...] = ()
    postconditions: tuple[Condition, ...] = ()
    returns: Returns | None = None
    on_violation: str = ""
    approval: str = ""
    read_only: bool = True
    side_effects: tuple[str, ...] = ()


def _label(contract: ToolContract) -> str:
    return contract.tool or "<未命名工具>"


def _problem(contract: ToolContract, segment: str, detail: str) -> str:
    return f"{_label(contract)} · {segment}: {detail}"


def _validate_conditions(
    contract: ToolContract, segment: str, conditions: Sequence[Condition]
) -> list[str]:
    problems: list[str] = []
    for index, condition in enumerate(conditions):
        where = f"{segment}[{index}]"
        if not isinstance(condition, Condition):
            got = type(condition).__name__
            problems.append(_problem(contract, where, f"必须是 Condition，读到 {got}"))
            continue
        if not condition.text.strip():
            problems.append(_problem(contract, where, "缺少人读原文 text"))
        if not condition.fact.strip():
            problems.append(_problem(contract, where, "缺少可求值的 fact"))
        if condition.operator not in OPERATORS:
            problems.append(
                _problem(contract, where, f"算子 {condition.operator!r} 不在 {list(OPERATORS)} 内")
            )
    return problems


def _validate_returns(contract: ToolContract) -> list[str]:
    returns = contract.returns
    if returns is None:
        return [_problem(contract, "returns", "缺少 returns 段（§7.3.1 要求只读工具也必须有）")]
    problems: list[str] = []
    if not returns.trim_rules:
        problems.append(_problem(contract, "returns", "缺少裁剪规则 trim_rules"))
    if not isinstance(returns.max_rows, int) or isinstance(returns.max_rows, bool):
        problems.append(_problem(contract, "returns", "缺少上限条数 max_rows"))
    elif returns.max_rows <= 0:
        problems.append(_problem(contract, "returns", f"上限条数 max_rows 必须为正，读到 {returns.max_rows}"))
    if not returns.must_keep:
        problems.append(_problem(contract, "returns", "缺少「必须保留什么」must_keep"))
    return problems


def _validate_read_only(contract: ToolContract) -> list[str]:
    problems: list[str] = []
    if contract.side_effects:
        problems.append(
            _problem(contract, "side_effects", f"只读工具不得声明写副作用：{list(contract.side_effects)}")
        )
    for permission in contract.requires_permission:
        verb = permission.rsplit(".", 1)[-1].strip().lower()
        if verb in WRITE_VERBS:
            problems.append(
                _problem(contract, "requires_permission", f"只读工具不得要求写权限：{permission!r}")
            )
    if contract.on_violation == "rollback_and_report":
        problems.append(
            _problem(contract, "on_violation", "只读工具没有可回滚的东西，不得用 rollback_and_report")
        )
    if contract.approval and contract.approval != APPROVAL_NOT_REQUIRED:
        problems.append(
            _problem(contract, "approval", f"只读工具不需要审批，应为 {APPROVAL_NOT_REQUIRED!r}")
        )
    return problems


def validate(contract: ToolContract) -> tuple[str, ...]:
    """返回该契约的全部结构问题。空元组 = 合法。**不抛异常**，好让调用方一次看全。"""
    problems: list[str] = []
    if not contract.tool.strip():
        problems.append(_problem(contract, "tool", "缺少工具名"))
    if not contract.target.strip():
        problems.append(_problem(contract, "target", "缺少 target"))
    if contract.risk not in RISK_LEVELS:
        problems.append(
            _problem(contract, "risk", f"取值 {contract.risk!r} 不在 {list(RISK_LEVELS)} 内")
        )
    if not contract.on_violation:
        problems.append(_problem(contract, "on_violation", "缺少 on_violation"))
    elif contract.on_violation not in ON_VIOLATION_VALUES:
        problems.append(
            _problem(
                contract,
                "on_violation",
                f"取值 {contract.on_violation!r} 不在 {list(ON_VIOLATION_VALUES)} 内",
            )
        )
    if not contract.approval:
        problems.append(_problem(contract, "approval", "缺少 approval"))
    problems.extend(_validate_conditions(contract, "preconditions", contract.preconditions))
    problems.extend(_validate_conditions(contract, "postconditions", contract.postconditions))
    problems.extend(_validate_returns(contract))
    if contract.read_only:
        problems.extend(_validate_read_only(contract))
    return tuple(problems)


def check(contract: ToolContract) -> None:
    """校验单个契约，不合法就抛 `ContractError`（消息含全部问题，指名到工具与段）。"""
    problems = validate(contract)
    if problems:
        raise ContractError("；".join(problems))


def validate_registry(contracts: Iterable[ToolContract]) -> tuple[str, ...]:
    """校验一组契约：逐个校验 + 工具名不得重复（重名会让「按名取契约」静默取错一条）。"""
    contracts = tuple(contracts)
    problems: list[str] = []
    for contract in contracts:
        problems.extend(validate(contract))
    seen: dict[str, int] = {}
    for contract in contracts:
        seen[contract.tool] = seen.get(contract.tool, 0) + 1
    for tool, count in seen.items():
        if count > 1:
            problems.append(f"{tool or '<未命名工具>'} · tool: 工具名重复 {count} 次")
    return tuple(problems)


def check_registry(contracts: Iterable[ToolContract]) -> None:
    problems = validate_registry(contracts)
    if problems:
        raise ContractError("；".join(problems))
