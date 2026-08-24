"""巡检执行体：按规则清单逐条查、命中即报。**整条路径上没有模型接缝。**

落点节是 `docs/architecture/module-boundaries.md` §7.9。

D-15 逐字：「按清单逐条查、命中即报**是代码，不是 Agent**」，
模型不可替代的位置在**命中之后**（那一段是 `agenerp/insight/`）。
所以本模块**没有** adapter、没有 transport、没有「可注入模型」的口子 ——
留一个口子再往里塞替身，等于先假设接缝存在再证明它没被用过。
判据（`tests/unit/test_inspection_rules.py`）除了进程级探针之外，
还在**全新解释器**里断言 `import agenerp.inspection` 之后 `agenerp.routing` 不在 `sys.modules` 里。

取数只走站点的只读列表端点（`agenerp/site.py` 的 `SiteClient.get`），
形状与 `agenerp/explain/gate.py` 的 `_rows` 相同：**只取规则声明用得到的字段**，
不 `*`，不整行倒出来。行源是可换的（`RowSource`），因此规则自带的 `test_case`
可以在纯内存行集上跑，一个请求都不发。
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from agenerp.inspection.rules import (
    AT_LEAST_FRACTION_OF,
    DIFFERENCE,
    EXCLUDE_EQUALS,
    EXCLUDE_FALSY,
    EXCLUDE_NOT_EQUALS,
    EXCLUDE_TRUTHY,
    GREATER_THAN,
    RELATED_SUM,
    SUM_NEGATIVE_ABS,
    SUM_POSITIVE,
    Measure,
    Rule,
)
from agenerp.site import SiteClient


class RowSource(Protocol):
    """行源。巡检器只要「给我某个 DocType 的这几个字段」这一个能力。"""

    def rows(
        self, doctype: str, fields: Sequence[str], parent: str = ""
    ) -> list[dict[str, Any]]: ...


@dataclass
class SiteRows:
    """活站点/假站点的行源。**只读**：一条写路径都没有。"""

    client: SiteClient
    request_count: int = 0

    def rows(
        self, doctype: str, fields: Sequence[str], parent: str = ""
    ) -> list[dict[str, Any]]:
        params = {
            "fields": json.dumps(list(fields)),
            "limit_page_length": "0",
        }
        if parent:
            # 子表在 Frappe 的 REST 面上必须点名 `parent`，否则 v15 直接拒。
            params["parent"] = parent
        self.request_count += 1
        payload = self.client.get(f"/api/resource/{doctype}", params)
        found = payload.get("data") if isinstance(payload, Mapping) else None
        return [dict(row) for row in found] if isinstance(found, list) else []


@dataclass
class MappingRows:
    """内存行源：规则自带的 `test_case` 用它跑，零请求、零站点。"""

    tables: Mapping[str, Sequence[Mapping[str, Any]]]
    request_count: int = 0

    def rows(
        self, doctype: str, fields: Sequence[str], parent: str = ""
    ) -> list[dict[str, Any]]:
        self.request_count += 1
        return [
            {key: row.get(key) for key in fields} for row in self.tables.get(doctype, ())
        ]


@dataclass(frozen=True)
class Hit:
    """一条命中记录。**结构化、可 diff、可回放**，且带一个**算出来的数**。

    `subject` 是分组键的取值（例如物料 + 仓库），不是单据号：规则不照单号写，
    命中也不按单号报。

    `pack_id` 是**出处**（P1.6 的 `Decision` D5）：命中要回答得了「这是哪个包的哪条规则报的」。
    它**不来自 `rule_id`、也不在 `Rule` 里** —— 同一条 `rule_id` 可以挂在两个包下，
    出处必须跟着包走，所以来源那一层是包（`agenerp.packs.Pack.pack_id`）
    经 `run()` / `inspect_site()` 的 `pack_id` 形参传进来。默认空串 =「不属于任何包」
    （引擎自带的最小规则集就是这一类，它**不是**行业包制品）。
    """

    rule_id: str
    statement: str
    subject: tuple[tuple[str, str], ...]
    quantity_name: str
    quantity: float
    measures: tuple[tuple[str, float], ...]
    pack_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "rule_id": self.rule_id,
            "statement": self.statement,
            "subject": dict(self.subject),
            "quantity_name": self.quantity_name,
            "quantity": self.quantity,
            "measures": dict(self.measures),
        }


@dataclass(frozen=True)
class InspectionReport:
    """一次巡检的产物。**零命中也是产物** —— 空报告与「没跑」必须分得开，
    所以 `rule_ids` 逐条记下这次到底查了哪些规则。"""

    rule_ids: tuple[str, ...]
    hits: tuple[Hit, ...] = ()
    request_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_ids": list(self.rule_ids),
            "request_count": self.request_count,
            "hits": [hit.as_dict() for hit in self.hits],
        }


def _num(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _same(value: Any, literal: Any) -> bool:
    """`equals` / `not_equals` 的比较口径。**两侧都是数字时按数字比，否则按字符串比** ——
    站点 REST 面回来的 `docstatus` 可能是 `1` 也可能是 `"1"`，按字符串硬比会静默失效。"""
    numeric = (int, float)
    if (
        isinstance(value, numeric)
        and not isinstance(value, bool)
        and isinstance(literal, numeric)
        and not isinstance(literal, bool)
    ):
        return float(value) == float(literal)
    return str("" if value is None else value) == str("" if literal is None else literal)


def _excluded(row: Mapping[str, Any], rule: Rule) -> bool:
    for item in rule.exclude:
        value = row.get(item.field)
        if item.operator == EXCLUDE_TRUTHY and value:
            return True
        if item.operator == EXCLUDE_FALSY and not value:
            return True
        if item.operator == EXCLUDE_EQUALS and _same(value, item.value):
            return True
        if item.operator == EXCLUDE_NOT_EQUALS and not _same(value, item.value):
            return True
    return False


def _primary_fields(rule: Rule) -> tuple[str, ...]:
    wanted = [*rule.group_by, *(item.field for item in rule.exclude)]
    wanted += [
        measure.field
        for measure in rule.measures
        if measure.operator in (SUM_POSITIVE, SUM_NEGATIVE_ABS) and measure.field
    ]
    return tuple(dict.fromkeys(field for field in wanted if field))


def _related_fields(measure: Measure) -> tuple[str, ...]:
    wanted = [measure.field, *(target for _, target in measure.match)]
    return tuple(dict.fromkeys(field for field in wanted if field))


def _related_sum(
    measure: Measure, subject: Mapping[str, str], source: RowSource
) -> float:
    rows = source.rows(measure.doctype, _related_fields(measure), parent=measure.parent)
    total = 0.0
    for row in rows:
        if all(str(row.get(target) or "") == subject.get(key, "") for key, target in measure.match):
            total += _num(row.get(measure.field))
    return total


def _fires(rule: Rule, values: Mapping[str, float]) -> bool:
    trigger = rule.trigger
    measured = values.get(trigger.measure, 0.0)
    if trigger.operator == GREATER_THAN:
        return measured > trigger.value
    if trigger.operator == AT_LEAST_FRACTION_OF:
        reference = values.get(trigger.reference, 0.0)
        # 参照量为 0 时问题问不出来 —— 没卖过的东西谈不上「产出远大于销出」。
        return reference > 0 and measured >= trigger.value * reference
    return False


def _evaluate(rule: Rule, source: RowSource, pack_id: str = "") -> list[Hit]:
    rows = source.rows(rule.doctype, _primary_fields(rule))
    groups: dict[tuple[tuple[str, str], ...], list[Mapping[str, Any]]] = {}
    for row in rows:
        if _excluded(row, rule):
            continue
        if any(row.get(key) in (None, "") for key in rule.group_by):
            continue
        key = tuple((field, str(row.get(field))) for field in rule.group_by)
        groups.setdefault(key, []).append(row)

    hits: list[Hit] = []
    for key, grouped in sorted(groups.items()):
        subject = dict(key)
        values: dict[str, float] = {}
        for measure in rule.measures:
            if measure.operator == SUM_POSITIVE:
                values[measure.name] = sum(
                    _num(row.get(measure.field))
                    for row in grouped
                    if _num(row.get(measure.field)) > 0
                )
            elif measure.operator == SUM_NEGATIVE_ABS:
                values[measure.name] = sum(
                    -_num(row.get(measure.field))
                    for row in grouped
                    if _num(row.get(measure.field)) < 0
                )
            elif measure.operator == DIFFERENCE:
                values[measure.name] = values[measure.left] - values[measure.right]
            elif measure.operator == RELATED_SUM:
                values[measure.name] = _related_sum(measure, subject, source)
        if not _fires(rule, values):
            continue
        hits.append(
            Hit(
                pack_id=pack_id,
                rule_id=rule.rule_id,
                statement=rule.statement,
                subject=key,
                quantity_name=rule.quantity,
                quantity=values[rule.quantity],
                measures=tuple(sorted(values.items())),
            )
        )
    return hits


def run(rules: Iterable[Rule], source: RowSource, pack_id: str = "") -> InspectionReport:
    """在给定行源上跑一遍清单。**清单是唯一的发现力来源** ——
    抽掉一条规则，它能发现的东西就跟着消失（消融判据）。

    `pack_id` 只做一件事：把出处**原样**盖进每条命中（D5）。它不参与求值，
    也不校验规则属不属于那个包 —— 出处是调用方（包的装载面）声明的事实，
    引擎不猜。
    """
    listed = tuple(rules)
    hits: list[Hit] = []
    for rule in listed:
        hits.extend(_evaluate(rule, source, pack_id))
    return InspectionReport(
        rule_ids=tuple(rule.rule_id for rule in listed),
        hits=tuple(hits),
        request_count=getattr(source, "request_count", 0),
    )


def inspect_site(
    rules: Iterable[Rule], client: SiteClient, pack_id: str = ""
) -> InspectionReport:
    """产品入口：在一个站点上跑一遍巡检。**零 LLM、零写操作。**"""
    return run(rules, SiteRows(client), pack_id)


@dataclass(frozen=True)
class TestCaseFailure:
    rule_id: str
    case: str
    reason: str


def check_test_cases(rules: Iterable[Rule]) -> tuple[TestCaseFailure, ...]:
    """把每条规则自带的 `test_case` 真跑一遍。返回失败清单，空 = 全过。

    这让 `test_case` 不是装饰：规则的判据表达改坏了，它自己的测例先红。
    """
    failures: list[TestCaseFailure] = []
    for rule in rules:
        case = rule.test_case
        report = run([rule], MappingRows(dict(case.rows)))
        hit = report.hits[0] if report.hits else None
        if case.expect_hit and hit is None:
            failures.append(TestCaseFailure(rule.rule_id, case.name, "期望命中，实际零命中"))
            continue
        if not case.expect_hit and hit is not None:
            failures.append(
                TestCaseFailure(rule.rule_id, case.name, f"期望不命中，实际命中 {hit.quantity}")
            )
            continue
        if hit is not None and case.expect_quantity is not None:
            if abs(hit.quantity - case.expect_quantity) > 1e-6:
                failures.append(
                    TestCaseFailure(
                        rule.rule_id,
                        case.name,
                        f"命中数量 {hit.quantity} ≠ 期望 {case.expect_quantity}",
                    )
                )
    return tuple(failures)


def without(rules: Iterable[Rule], rule_id: str) -> tuple[Rule, ...]:
    """消融用：把一条规则从清单里抽掉。**判据侧的工具，产品路径不用它。**"""
    return tuple(rule for rule in rules if rule.rule_id != rule_id)
