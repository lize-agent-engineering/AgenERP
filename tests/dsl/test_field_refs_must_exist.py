"""🔴 P2.1 · 「DSL 校验过 ≠ 字段真的存在」—— 这一层单独立文件。

判据来源：`docs/backlog/p2-views-roadmap.md` 硬约束 ④，理由逐字：

> **P1 是只读解释，错了是一个错答案；P2 生成视图，错了是用户天天看到的错字段。**

以及硬约束 ①（CP9 继承项）：**判据不许只验「调得通」。**

## 这一层防的是什么

一个结构完全合法的 DSL——块类型对、必填段齐、取值都在枚举内——
里面写着 `Sales Order.custmoer`（拼错了）。**L1 结构校验器对此一无所知。**
如果 `validate()` 到此为止，那么「校验通过」这句话在
「字段是不是真的存在」这一维上**是空的**。

⚠️ 这正是 P1 那次误放行的同形：判据绿着，但它什么都没验
（`docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2）。
"""

from __future__ import annotations

import pytest

from agenerp.dsl.blocks import Block, View
from agenerp.dsl.validate import SchemaUnavailable, validate

from tests.dsl.conftest import SALES_SCHEMA


def _view(block: Block) -> View:
    return View(name="v", title="t", blocks=(block,))


def test_a_structurally_perfect_block_is_still_rejected_when_the_field_does_not_exist():
    # 块本身挑不出毛病：类型对、doctype 对、fields 非空。错的只有一个字母。
    block = Block(type="list", doctype="Sales Order", fields=("customer", "custmoer"))
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("custmoer" in e for e in result.errors)


def test_a_block_pointing_at_a_doctype_that_does_not_exist_is_rejected():
    block = Block(type="list", doctype="Sales Ordr", fields=("customer",))
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("Sales Ordr" in e for e in result.errors)


def test_the_field_check_looks_at_the_blocks_own_doctype_not_any_doctype():
    # `qty` 在 `Sales Order Item` 上真实存在，但**不在 `Sales Order` 上**。
    # 一个只问「这个字段名在整个 schema 里出现过吗」的实现会放它过去 ——
    # 而那正是 P2.0R 实测出的头号错法：**语义对了，单据错了**。
    block = Block(type="list", doctype="Sales Order", fields=("qty",))
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("qty" in e for e in result.errors)


def test_a_metric_aggregate_field_goes_through_the_same_existence_check():
    # 每一处字段引用都要过这一层，不是只有 list 的 fields 过。
    block = Block(type="metric", doctype="Sales Order", fields=("gross_total",), agg="sum")
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("gross_total" in e for e in result.errors)


def test_a_chart_axis_field_goes_through_the_same_existence_check():
    block = Block(type="chart", doctype="Sales Order",
                  fields=("transaction_date", "grnd_total"), chart_kind="line")
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("grnd_total" in e for e in result.errors)


def test_a_filter_field_goes_through_the_same_existence_check():
    # 筛选条件里的字段同样是「自然语言 → 字段」的产物，同样要指回真实字段。
    block = Block(type="list", doctype="Sales Order", fields=("customer",),
                  filters=(("statuz", "=", "To Deliver"),))
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("statuz" in e for e in result.errors)


def test_a_sort_field_goes_through_the_same_existence_check():
    block = Block(type="list", doctype="Sales Order", fields=("customer",),
                  sort=("transation_date", "desc"))
    result = validate(_view(block), SALES_SCHEMA)
    assert not result.ok
    assert any("transation_date" in e for e in result.errors)


def test_every_field_ref_the_view_uses_can_be_enumerated():
    # 「这个视图用到了哪些字段」必须有唯一答案 —— 否则 P2.5 的 schema.drift
    # 巡检没法知道该盯哪些列。
    block = Block(type="list", doctype="Sales Order", fields=("customer", "grand_total"),
                  filters=(("status", "=", "To Deliver"),), sort=("transaction_date", "desc"))
    refs = _view(block).field_refs()
    assert refs == (
        ("Sales Order", "customer"),
        ("Sales Order", "grand_total"),
        ("Sales Order", "status"),
        ("Sales Order", "transaction_date"),
    )


def test_validating_without_a_schema_raises_instead_of_reporting_success():
    """🔴 验不了的东西不许算过。

    这是 P1 那个 `or` 的教训的直接执行：当时
    `assert payload["answer"] or payload["accepted"] is False` 让空答案照过，
    **一路绿了好几天**。这里的等价形态是「拿不到 schema 就跳过字段检查、
    然后报 ok」—— 那样 `validate()` 的返回值会在最需要它的时候变成一句空话。

    所以：**没有 schema 就不许有结论**，抛异常，不返回 ok。
    """
    block = Block(type="list", doctype="Sales Order", fields=("customer",))
    with pytest.raises(SchemaUnavailable):
        validate(_view(block), None)


def test_an_empty_schema_is_not_treated_as_permission_to_skip_the_check():
    # 空的 schema 视图是「这个站点什么都没有」，不是「别查了」。
    from agenerp.dsl.schema import SchemaView

    block = Block(type="list", doctype="Sales Order", fields=("customer",))
    result = validate(_view(block), SchemaView({}))
    assert not result.ok
    assert any("Sales Order" in e for e in result.errors)
