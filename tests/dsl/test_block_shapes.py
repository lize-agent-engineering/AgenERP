"""P2.1 · 五种块的声明格式：什么接受、什么拒绝。

判据来源：`docs/design/view-dsl-and-eval.md` §10.2（v0 只支持五种块，只读）。

⚠️ 本文件只管**结构**（L1）。「字段是不是真的存在」在
`test_field_refs_must_exist.py` —— 分两个文件不是为了整齐，是因为
`p2-views-roadmap.md` 硬约束 ① 逐字写着「**DSL 校验过 ≠ 字段真的存在**」：
两件事混在一个文件里，读判据的人会以为验了一件其实没验的事。
"""

from __future__ import annotations

import pytest

from agenerp.dsl.blocks import BLOCK_TYPES, Block, View
from agenerp.dsl.validate import DslError, validate

from tests.dsl.conftest import SALES_SCHEMA


def _view(*blocks: Block) -> View:
    return View(name="sales-overview", title="销售总览", blocks=blocks)


def test_the_five_block_types_are_exactly_the_ones_the_owner_doc_lists():
    # §10.2 的表就是这五行。多一种少一种都是 DSL 与 owner doc 打架。
    assert BLOCK_TYPES == ("list", "detail", "metric", "chart", "explain")


@pytest.mark.parametrize(
    "block",
    [
        Block(type="list", doctype="Sales Order", fields=("customer", "transaction_date")),
        Block(type="detail", doctype="Sales Order", fields=("customer", "grand_total")),
        Block(type="metric", doctype="Sales Order", fields=("grand_total",), agg="sum"),
        Block(type="chart", doctype="Sales Order", fields=("transaction_date", "grand_total"),
              chart_kind="line"),
        Block(type="explain", question="这单为什么还没发货？"),
    ],
    ids=list(BLOCK_TYPES),
)
def test_each_of_the_five_blocks_validates_when_it_is_well_formed(block):
    result = validate(_view(block), SALES_SCHEMA)
    assert result.ok
    assert result.errors == ()


def test_an_unknown_block_type_is_rejected_not_quietly_dropped():
    # 「宽容地忽略」等于 DSL 有一个没人看管的入口。
    result = validate(_view(Block(type="timeline", doctype="Sales Order", fields=("customer",))),
                      SALES_SCHEMA)
    assert not result.ok
    assert any("timeline" in e for e in result.errors)


def test_a_list_block_with_no_fields_is_rejected():
    result = validate(_view(Block(type="list", doctype="Sales Order", fields=())), SALES_SCHEMA)
    assert not result.ok
    assert any("fields" in e for e in result.errors)


def test_a_metric_block_without_an_aggregate_is_rejected():
    result = validate(_view(Block(type="metric", doctype="Sales Order", fields=("grand_total",))),
                      SALES_SCHEMA)
    assert not result.ok
    assert any("agg" in e for e in result.errors)


def test_a_metric_block_with_an_aggregate_outside_the_closed_set_is_rejected():
    result = validate(
        _view(Block(type="metric", doctype="Sales Order", fields=("grand_total",), agg="median")),
        SALES_SCHEMA,
    )
    assert not result.ok
    assert any("median" in e for e in result.errors)


def test_a_chart_block_needs_exactly_two_fields():
    # 一根轴画不出图，三根轴 v0 不支持 —— 两种都得当场说清楚，不是运行期才炸。
    result = validate(
        _view(Block(type="chart", doctype="Sales Order", fields=("grand_total",), chart_kind="bar")),
        SALES_SCHEMA,
    )
    assert not result.ok
    assert any("chart" in e for e in result.errors)


def test_an_explain_block_without_a_question_is_rejected():
    result = validate(_view(Block(type="explain", question="")), SALES_SCHEMA)
    assert not result.ok
    assert any("question" in e for e in result.errors)


def test_an_explain_block_must_not_carry_fields():
    # explain 是解释性文本块（§10.2），它不投影字段。
    # 允许它带 fields 会让「哪些字段被这个视图用到」这个问题有两个答案。
    result = validate(_view(Block(type="explain", question="为什么？", doctype="Sales Order",
                                  fields=("customer",))), SALES_SCHEMA)
    assert not result.ok
    assert any("explain" in e for e in result.errors)


def test_a_view_with_zero_blocks_is_rejected():
    result = validate(View(name="empty", title="空", blocks=()), SALES_SCHEMA)
    assert not result.ok
    assert any("blocks" in e for e in result.errors)


def test_errors_name_which_block_went_wrong():
    # 十个块里错一个，不该靠人肉找 —— 与 agenerp/contracts.py 的校验器同一条纪律。
    bad = Block(type="list", doctype="Sales Order", fields=())
    good = Block(type="detail", doctype="Sales Order", fields=("customer",))
    result = validate(_view(good, bad), SALES_SCHEMA)
    assert not result.ok
    assert any("blocks[1]" in e for e in result.errors)


def test_blocks_are_frozen_so_a_validated_view_cannot_be_mutated_afterwards():
    # 校验过的东西还能改，等于没校验。
    block = Block(type="list", doctype="Sales Order", fields=("customer",))
    with pytest.raises((AttributeError, DslError)):
        block.doctype = "Purchase Order"  # type: ignore[misc]
