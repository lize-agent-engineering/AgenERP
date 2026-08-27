"""两层校验器。

    L1 结构      块类型在封闭集内 · 必填段齐 · 取值在枚举内
    L2 字段存在   每一个被引用的 `(DocType, fieldname)` 在 schema 视图里真的存在

🔴 **两层都跑，第二层不可跳过。** 理由逐字来自 `p2-views-roadmap.md` 硬约束 ①：

> **渲染出来 ≠ 渲染对了；DSL 校验过 ≠ 字段真的存在。**

以及硬约束 ④ 的理由：

> **P1 是只读解释，错了是一个错答案；P2 生成视图，错了是用户天天看到的错字段。**

🔴 **没有 schema 就没有结论。** `validate(view, None)` 抛 `SchemaUnavailable`，
**不返回 ok**。这是 P1 那次误放行的直接对策：当时
`assert payload["answer"] or payload["accepted"] is False` 里的一个 `or`
让空答案照过，一路绿了好几天。等价的错法在这里是「拿不到 schema 就跳过 L2 然后报 ok」
—— 那会让 `validate()` 的返回值在最需要它的时候变成一句空话。
"""

from __future__ import annotations

from dataclasses import dataclass

from agenerp.dsl.blocks import (
    AGGREGATES,
    BLOCK_TYPES,
    CHART_KINDS,
    FILTER_OPERATORS,
    SORT_DIRECTIONS,
    Block,
    View,
)
from agenerp.dsl.schema import SchemaView


class DslError(ValueError):
    """DSL 结构不合法。消息里必须能看出是哪个块的哪一段。"""


class SchemaUnavailable(DslError):
    """没有 schema 视图 ⇒ 字段存在性验不了 ⇒ **不许有结论**。"""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]


def validate(view: View, schema: SchemaView | None) -> ValidationResult:
    """校验一个视图。`schema` 是**必填**的位置参数，且不许是 `None`。"""
    if schema is None:
        raise SchemaUnavailable(
            "视图 " + repr(view.name) + " 无法校验：没有 schema 视图，"
            "字段存在性验不了。验不了的东西不许算过。"
        )

    errors: list[str] = []
    if not view.name:
        errors.append("view.name 不能为空")
    if not view.blocks:
        errors.append("view.blocks 至少要有一个块")

    for index, block in enumerate(view.blocks):
        where = f"blocks[{index}]"
        errors.extend(_check_structure(block, where))

    # L2 只在 L1 通过后才有意义 —— 结构都不对时，字段引用的位置本身就不可信。
    # ⚠️ 但这**不是**「L1 过了就不用跑 L2」，是「L1 没过时 L2 的输入是垃圾」。
    if not errors:
        errors.extend(_check_fields_exist(view, schema))

    return ValidationResult(ok=not errors, errors=tuple(errors))


def _check_structure(block: Block, where: str) -> list[str]:
    if block.type not in BLOCK_TYPES:
        # 不认识的块类型是**作者写错了**，当场拒。
        # （渲染器遇到不认识的类型是另一回事 —— 那里落回 Desk，见 fallback.py 的模块 docstring。）
        return [f"{where}.type 不是受支持的块类型：{block.type!r}；只支持 {BLOCK_TYPES}"]

    errors: list[str] = []
    if block.type == "explain":
        if not block.question.strip():
            errors.append(f"{where}.question 不能为空：explain 块的正文就是那个问题")
        if block.fields:
            errors.append(
                f"{where}：explain 块不投影字段，不许带 fields —— "
                "否则「这个视图用到了哪些字段」会有两个答案"
            )
        return errors

    if not block.doctype:
        errors.append(f"{where}.doctype 不能为空")
    if not block.fields:
        errors.append(f"{where}.fields 不能为空")

    if block.type == "metric":
        if not block.agg:
            errors.append(f"{where}.agg 不能为空：metric 必须说清算的是什么口径")
        elif block.agg not in AGGREGATES:
            errors.append(f"{where}.agg 不在封闭取值里：{block.agg!r}；只支持 {AGGREGATES}")
        if len(block.fields) != 1:
            errors.append(f"{where}：metric 恰好聚合一个字段，收到 {len(block.fields)} 个")

    if block.type == "chart":
        if len(block.fields) != 2:
            errors.append(
                f"{where}：chart 恰好要两个字段 (x 轴, y 轴)，收到 {len(block.fields)} 个"
            )
        if not block.chart_kind:
            errors.append(f"{where}.chart_kind 不能为空")
        elif block.chart_kind not in CHART_KINDS:
            errors.append(
                f"{where}.chart_kind 不在封闭取值里：{block.chart_kind!r}；只支持 {CHART_KINDS}"
            )

    for n, entry in enumerate(block.filters):
        if len(entry) != 3:
            errors.append(f"{where}.filters[{n}] 要形如 (字段, 算子, 值)")
            continue
        if entry[1] not in FILTER_OPERATORS:
            errors.append(
                f"{where}.filters[{n}] 算子不在封闭取值里：{entry[1]!r}；只支持 {FILTER_OPERATORS}"
            )

    if block.sort is not None:
        if len(block.sort) != 2:
            errors.append(f"{where}.sort 要形如 (字段, asc|desc)")
        elif block.sort[1] not in SORT_DIRECTIONS:
            errors.append(f"{where}.sort 方向不在封闭取值里：{block.sort[1]!r}")

    if block.limit is not None and block.limit <= 0:
        errors.append(f"{where}.limit 要是正整数，收到 {block.limit!r}")

    if block.child_fields and block.type != "detail":
        errors.append(f"{where}：只有 detail 块能展开子表，{block.type} 块不许带 child_fields")

    seen_tables: set[str] = set()
    for n, entry in enumerate(block.child_fields):
        if len(entry) != 3:
            errors.append(f"{where}.child_fields[{n}] 要形如 (Table 字段, 子表 DocType, (字段…))")
            continue
        table_field, child_doctype, child_fieldnames = entry
        if table_field not in block.fields:
            # 展开一个本块没有投影的子表，等于视图里凭空多出一段内容。
            errors.append(
                f"{where}.child_fields[{n}]：{table_field!r} 不在本块的 fields 里"
            )
        if not child_doctype:
            errors.append(f"{where}.child_fields[{n}] 的子表 DocType 不能为空")
        if not child_fieldnames:
            errors.append(
                f"{where}.child_fields[{n}]：展开 {table_field!r} 却没说要展示哪些字段"
            )
        if table_field in seen_tables:
            errors.append(f"{where}.child_fields 里 {table_field!r} 声明了不止一次")
        seen_tables.add(table_field)

    return errors


def _check_fields_exist(view: View, schema: SchemaView) -> list[str]:
    """🔴 硬约束 ④ 的执行体：每一处字段引用都要指回一个真实存在的字段。

    ⚠️ **按块自己的 DocType 查，不是「这个字段名在整个 schema 里出现过吗」。**
    P2.0R 实测出的头号错法就是「语义对了，单据错了」：`qty` 在
    `Sales Order Item` 上真实存在，但不在 `Sales Order` 上。一个只问字段名的
    实现会把它放过去，而用户看到的是一列永远为空的数据。
    """
    errors: list[str] = []
    missing_doctypes: set[str] = set()

    for doctype, fieldname in view.field_refs():
        if not schema.has_doctype(doctype):
            if doctype not in missing_doctypes:
                missing_doctypes.add(doctype)
                errors.append(f"DocType 不存在：{doctype!r}")
            continue
        if not schema.has_field(doctype, fieldname):
            errors.append(f"字段不存在：{doctype}.{fieldname}")

    for index, block in enumerate(view.blocks):
        for n, (table_field, child_doctype, _names) in enumerate(block.child_fields):
            where = f"blocks[{index}].child_fields[{n}]"
            if not block.doctype:
                continue
            if schema.fieldtype(block.doctype, table_field) != "Table":
                errors.append(
                    f"{where}：{block.doctype}.{table_field} 不是 Table 字段，展不开"
                )
                continue
            actual = schema.child_doctype(block.doctype, table_field)
            if actual is None:
                # 🔴 查不到 ≠ 放行。与 `SchemaUnavailable` 同源：验不了的东西不许算过。
                errors.append(
                    f"{where}：schema 里没有 {block.doctype}.{table_field} 指向哪张子表，"
                    "无法核对声明的子表对不对 —— 验不了的不算过"
                )
            elif actual != child_doctype:
                errors.append(
                    f"{where}：声明的子表是 {child_doctype!r}，"
                    f"但 {block.doctype}.{table_field} 实际指向 {actual!r}"
                )

        if block.type == "explain" and block.subject:
            subject = block.subject.split(".", 1)[0]
            if not schema.has_doctype(subject):
                errors.append(f"blocks[{index}].subject 指向的 DocType 不存在：{subject!r}")

    return errors
