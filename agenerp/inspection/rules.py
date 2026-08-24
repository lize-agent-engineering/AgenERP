"""巡检规则的**声明形状 v0** —— 规则是数据，不是代码。

落点节是 `docs/architecture/module-boundaries.md` §7.9。

`Decision` D1 选的是「**声明式数据 + 有限算子**」，否决了「自由 Python 谓词」：
谓词不可 diff、不可迁移，与北极星里「每一次生长都是可 diff、可回滚、可迁移的产物」
直接冲突。也没有照搬 `agenerp/contracts.py` 的 `Condition` —— 那套算子的语义是
「什么时候允许停下来」（工具契约的前置/后置），与「业务数据是否荒谬」不是一回事，
硬套会让两处语义互相污染。

⚠️ **本模块的规则不是行业包制品。** 行业包（`pack_id` + `rule_id` 的来源）归 P1.6；
`agenerp/tools/queries.py` 的 `rule.lookup` 因此仍然指名报错，本模块**不翻转它**。
另外，`agenerp/pack.py` 的「包」是**定制包**（Custom Field / Property Setter 的导出与 apply），
与行业规则包毫无关系 —— 目录命名消歧见 `Decision` D2。

**算子集是有限的，且刻意小**（v0 只装得下「够跑固定测例 + 形状可扩」）：

| 位置 | 算子 | 语义 |
|---|---|---|
| 行过滤 | `truthy` / `falsy` | 该字段为真 / 为假的行被排除 |
| 度量 | `sum_positive` | 组内该字段所有**正值**之和 |
| 度量 | `sum_negative_abs` | 组内该字段所有**负值**的绝对值之和 |
| 度量 | `difference` | 两个**已声明过的**度量相减 |
| 度量 | `related_sum` | 另一个 DocType 里按 `match` 对上的行的字段之和 |
| 触发 | `greater_than` | 度量 > 字面量 |
| 触发 | `at_least_fraction_of` | 参照量 > 0 **且** 度量 ≥ 比例 × 参照量 |

`at_least_fraction_of` 的「参照量 > 0」不是实现细节而是语义的一部分：参照量为 0 时
「多出来的有没有道理」这个问题问不出来（没卖过的东西谈不上「产出远大于销出」），
把它读成命中会让规则在每一个原料仓上误报。

**每条规则必须带 `test_case`，否则拒绝装载**（不是过滤掉、不是警告）：P1.6 的验收原文是
「无 `test_case` 的规则**即失败**」。静默过滤与正确拒载在退出码上一模一样，
所以这里只有抛错一条路。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# 行过滤算子
EXCLUDE_TRUTHY = "truthy"
EXCLUDE_FALSY = "falsy"
EXCLUDE_OPERATORS = (EXCLUDE_TRUTHY, EXCLUDE_FALSY)

# 度量算子
SUM_POSITIVE = "sum_positive"
SUM_NEGATIVE_ABS = "sum_negative_abs"
DIFFERENCE = "difference"
RELATED_SUM = "related_sum"
MEASURE_OPERATORS = (SUM_POSITIVE, SUM_NEGATIVE_ABS, DIFFERENCE, RELATED_SUM)

# 触发算子
GREATER_THAN = "greater_than"
AT_LEAST_FRACTION_OF = "at_least_fraction_of"
TRIGGER_OPERATORS = (GREATER_THAN, AT_LEAST_FRACTION_OF)


RULE_KEYS = frozenset(
    {
        "rule_id",
        "statement",
        "doctype",
        "group_by",
        "measures",
        "trigger",
        "quantity",
        "test_case",
        "exclude",
    }
)
MEASURE_KEYS = frozenset(
    {"name", "operator", "field", "left", "right", "doctype", "parent", "match"}
)
TRIGGER_KEYS = frozenset({"measure", "operator", "reference", "value"})
TEST_CASE_KEYS = frozenset({"name", "rows", "expect_hit", "expect_quantity"})
ROW_FILTER_KEYS = frozenset({"field", "operator"})


class RuleLoadError(ValueError):
    """规则清单装载失败。**拒载，不降级** —— 半份规则清单跑出来的零命中读起来
    与「一切正常」一模一样，那正是巡检器存在的理由要挡的东西。"""


@dataclass(frozen=True)
class RowFilter:
    """一条行过滤：`field` 上 `operator` 成立的行**被排除**在汇总之外。"""

    field: str
    operator: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "operator": self.operator}


@dataclass(frozen=True)
class Measure:
    """一条度量。`name` 在同一条规则内唯一，后面的度量可以引用前面的。"""

    name: str
    operator: str
    field: str = ""
    left: str = ""
    right: str = ""
    doctype: str = ""
    parent: str = ""
    match: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "operator": self.operator}
        for key in ("field", "left", "right", "doctype", "parent"):
            value = getattr(self, key)
            if value:
                payload[key] = value
        if self.match:
            payload["match"] = [list(pair) for pair in self.match]
        return payload


@dataclass(frozen=True)
class Trigger:
    """命中判据。`measure` 与 `reference` 都必须是本规则声明过的度量名。"""

    measure: str
    operator: str
    reference: str = ""
    value: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"measure": self.measure, "operator": self.operator}
        if self.reference:
            payload["reference"] = self.reference
        payload["value"] = self.value
        return payload


@dataclass(frozen=True)
class TestCase:
    """规则自带的测例。**不是装饰**：`agenerp.inspection.engine.check_test_cases`
    拿它在内存行集上真跑一遍，规则改坏了当场发红。"""

    name: str
    rows: tuple[tuple[str, tuple[dict[str, Any], ...]], ...]
    expect_hit: bool
    expect_quantity: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "rows": {doctype: [dict(row) for row in rows] for doctype, rows in self.rows},
            "expect_hit": self.expect_hit,
        }
        if self.expect_quantity is not None:
            payload["expect_quantity"] = self.expect_quantity
        return payload


@dataclass(frozen=True)
class Rule:
    """一条巡检规则。**人话陈述与判据表达分开**：前者进命中记录给人看，
    后者是引擎唯一读的东西 —— 两者对不上时红的是 `test_case`，不是注释。"""

    rule_id: str
    statement: str
    doctype: str
    group_by: tuple[str, ...]
    measures: tuple[Measure, ...]
    trigger: Trigger
    quantity: str
    test_case: TestCase
    exclude: tuple[RowFilter, ...] = ()

    def measure_names(self) -> tuple[str, ...]:
        return tuple(measure.name for measure in self.measures)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "rule_id": self.rule_id,
            "statement": self.statement,
            "doctype": self.doctype,
            "group_by": list(self.group_by),
            "measures": [measure.as_dict() for measure in self.measures],
            "trigger": self.trigger.as_dict(),
            "quantity": self.quantity,
            "test_case": self.test_case.as_dict(),
        }
        if self.exclude:
            payload["exclude"] = [item.as_dict() for item in self.exclude]
        return payload

    def serialized(self) -> str:
        """规则的**可 diff 形态**。判据直接对这个字符串断言（不含单号、不含答案里的数量）。"""
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, indent=2)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuleLoadError(message)


def _reject_unknown(declaration: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    """**未知键即拒载。** 装载器悄悄丢掉不认识的键有两个后果，两个都不能要：
    打错的键名会静默失效；而规则里夹带的具体单号 / 具体数量会因为「反正不参与求值」
    躲过序列化后的结构判据（这一条是执行期变异自查 **M7** 实测撞出来的，见 plan §9）。
    """
    unknown = sorted(set(declaration) - allowed)
    if unknown:
        raise RuleLoadError(f"{where}：不认识的键 {unknown}（有限形状，未知键一律拒载）")


def _text(declaration: Mapping[str, Any], key: str, where: str) -> str:
    value = declaration.get(key)
    _require(isinstance(value, str) and value.strip(), f"{where}：`{key}` 缺失或为空")
    return str(value)


def _row_filter(declaration: Mapping[str, Any], where: str) -> RowFilter:
    _reject_unknown(declaration, ROW_FILTER_KEYS, where)
    operator = _text(declaration, "operator", where)
    _require(
        operator in EXCLUDE_OPERATORS,
        f"{where}：行过滤算子 {operator!r} 不在有限算子集 {list(EXCLUDE_OPERATORS)} 里",
    )
    return RowFilter(field=_text(declaration, "field", where), operator=operator)


def _measure(declaration: Mapping[str, Any], seen: tuple[str, ...], where: str) -> Measure:
    _reject_unknown(declaration, MEASURE_KEYS, where)
    name = _text(declaration, "name", where)
    _require(name not in seen, f"{where}：度量名 {name!r} 重复")
    operator = _text(declaration, "operator", where)
    _require(
        operator in MEASURE_OPERATORS,
        f"{where}：度量算子 {operator!r} 不在有限算子集 {list(MEASURE_OPERATORS)} 里",
    )
    match = tuple(
        (str(pair[0]), str(pair[1])) for pair in declaration.get("match", ()) if len(pair) == 2
    )
    measure = Measure(
        name=name,
        operator=operator,
        field=str(declaration.get("field") or ""),
        left=str(declaration.get("left") or ""),
        right=str(declaration.get("right") or ""),
        doctype=str(declaration.get("doctype") or ""),
        parent=str(declaration.get("parent") or ""),
        match=match,
    )
    if operator in (SUM_POSITIVE, SUM_NEGATIVE_ABS):
        _require(bool(measure.field), f"{where}：{operator} 需要 `field`")
    if operator == DIFFERENCE:
        for side in ("left", "right"):
            referenced = getattr(measure, side)
            _require(bool(referenced), f"{where}：difference 需要 `{side}`")
            _require(
                referenced in seen,
                f"{where}：difference 的 `{side}` 引用了未声明的度量 {referenced!r}",
            )
    if operator == RELATED_SUM:
        _require(bool(measure.doctype), f"{where}：related_sum 需要 `doctype`")
        _require(bool(measure.field), f"{where}：related_sum 需要 `field`")
        _require(bool(measure.match), f"{where}：related_sum 需要非空的 `match`")
    return measure


def _trigger(declaration: Mapping[str, Any], names: tuple[str, ...], where: str) -> Trigger:
    _reject_unknown(declaration, TRIGGER_KEYS, where)
    operator = _text(declaration, "operator", where)
    _require(
        operator in TRIGGER_OPERATORS,
        f"{where}：触发算子 {operator!r} 不在有限算子集 {list(TRIGGER_OPERATORS)} 里",
    )
    measure = _text(declaration, "measure", where)
    _require(measure in names, f"{where}：触发引用了未声明的度量 {measure!r}")
    reference = str(declaration.get("reference") or "")
    if operator == AT_LEAST_FRACTION_OF:
        _require(bool(reference), f"{where}：at_least_fraction_of 需要 `reference`")
        _require(
            reference in names,
            f"{where}：触发的 `reference` 引用了未声明的度量 {reference!r}",
        )
    value = declaration.get("value")
    _require(isinstance(value, (int, float)), f"{where}：触发的 `value` 必须是数字")
    return Trigger(measure=measure, operator=operator, reference=reference, value=float(value))


def _test_case(declaration: Any, where: str) -> TestCase:
    """**缺 `test_case` 即拒载。** P1.6 的验收原文是「无 `test_case` 的规则即失败」，
    静默过滤掉它与正确拒载在退出码上一模一样，所以这里只抛错。"""
    _require(
        isinstance(declaration, Mapping) and declaration,
        f"{where}：规则必须带 `test_case`（P1.6 验收原文：无 test_case 的规则即失败）；"
        "拒绝装载，不静默过滤",
    )
    _reject_unknown(declaration, TEST_CASE_KEYS, where)
    rows = declaration.get("rows")
    _require(isinstance(rows, Mapping) and rows, f"{where}：`test_case.rows` 缺失或为空")
    expect_hit = declaration.get("expect_hit")
    _require(isinstance(expect_hit, bool), f"{where}：`test_case.expect_hit` 必须是布尔值")
    quantity = declaration.get("expect_quantity")
    _require(
        quantity is None or isinstance(quantity, (int, float)),
        f"{where}：`test_case.expect_quantity` 必须是数字或缺省",
    )
    return TestCase(
        name=_text(declaration, "name", where),
        rows=tuple(
            (str(doctype), tuple(dict(row) for row in table))
            for doctype, table in sorted(rows.items())
        ),
        expect_hit=bool(expect_hit),
        expect_quantity=None if quantity is None else float(quantity),
    )


def load_rule(declaration: Mapping[str, Any]) -> Rule:
    """把一份声明装载成 `Rule`。**任何一处不合形状都抛 `RuleLoadError`。**"""
    _require(isinstance(declaration, Mapping), "规则声明必须是映射")
    rule_id = _text(declaration, "rule_id", "规则声明")
    where = f"规则 {rule_id!r}"
    _reject_unknown(declaration, RULE_KEYS, where)
    group_by = tuple(str(field) for field in declaration.get("group_by", ()))
    _require(bool(group_by), f"{where}：`group_by` 不能为空")

    measures: list[Measure] = []
    for index, raw in enumerate(declaration.get("measures", ())):
        measures.append(_measure(raw, tuple(m.name for m in measures), f"{where} 的度量 #{index}"))
    _require(bool(measures), f"{where}：`measures` 不能为空")
    names = tuple(measure.name for measure in measures)

    quantity = _text(declaration, "quantity", where)
    _require(quantity in names, f"{where}：`quantity` 引用了未声明的度量 {quantity!r}")

    return Rule(
        rule_id=rule_id,
        statement=_text(declaration, "statement", where),
        doctype=_text(declaration, "doctype", where),
        group_by=group_by,
        measures=tuple(measures),
        trigger=_trigger(declaration.get("trigger") or {}, names, f"{where} 的触发"),
        quantity=quantity,
        test_case=_test_case(declaration.get("test_case"), where),
        exclude=tuple(
            _row_filter(raw, f"{where} 的行过滤 #{index}")
            for index, raw in enumerate(declaration.get("exclude", ()))
        ),
    )


def load_rules(declarations: Sequence[Mapping[str, Any]]) -> tuple[Rule, ...]:
    """装载一份规则清单。`rule_id` 重复也拒载 —— 命中记录靠它指回规则。"""
    rules: list[Rule] = []
    for declaration in declarations:
        rule = load_rule(declaration)
        _require(
            rule.rule_id not in {existing.rule_id for existing in rules},
            f"规则 {rule.rule_id!r} 重复出现在同一份清单里",
        )
        rules.append(rule)
    return tuple(rules)
