"""P2.3 · 线格式：模型交出来的那段 JSON ↔ `View`。

🔴 **本文件只验形状，不验对错。** 纪律与 `agenerp/dsl/blocks.py` 同源：
解析器必须能造出**非法**的 `View`，否则校验器的拒绝路径根本没法测。
「这个视图对不对」是 `agenerp/dsl/validate.py` 的活，不是这里的。

`WireError` 与 `DslError` **分开**是刻意的：
「模型交的不是 DSL」和「模型交的是错的 DSL」回注给模型的话术不同，
混成一个，模型就分不清是格式没说清还是字段找错了。
"""

from __future__ import annotations

import pytest

from agenerp.views.wire import WireError, view_from_json, view_from_text

WORK_ORDER_PAYLOAD = {
    "name": "worker-today",
    "title": "今天的工单",
    "blocks": [
        {
            "type": "list",
            "title": "工单",
            "doctype": "Work Order",
            "fields": ["production_item", "qty", "status"],
            "sort": ["planned_start_date", "asc"],
            "limit": 50,
        }
    ],
}


def test_a_well_formed_payload_becomes_a_view():
    view = view_from_json(WORK_ORDER_PAYLOAD)

    assert view.name == "worker-today"
    assert view.title == "今天的工单"
    assert len(view.blocks) == 1

    block = view.blocks[0]
    assert block.type == "list"
    assert block.doctype == "Work Order"
    assert block.fields == ("production_item", "qty", "status")
    assert block.sort == ("planned_start_date", "asc")
    assert block.limit == 50


def test_field_refs_survives_the_round_trip():
    """`field_refs()` 是「这个视图用到了哪些字段」的唯一答案 —— 线格式不许把它弄丢。"""
    refs = view_from_json(WORK_ORDER_PAYLOAD).field_refs()

    assert ("Work Order", "production_item") in refs
    assert ("Work Order", "qty") in refs
    # sort 引用的字段也算用到了 —— 否则校验器会漏掉它。
    assert ("Work Order", "planned_start_date") in refs


def test_an_unknown_block_type_parses_and_is_left_for_the_validator():
    """🔴 解析器**不认识的块类型照样解析出来**，判它的是校验器。

    反过来做（在解析时就拒）会让「校验器拒绝了它」和「它压根构造不出来」分不清 ——
    那正是 `blocks.py` 模块头点名的那件事。
    """
    payload = {**WORK_ORDER_PAYLOAD, "blocks": [{"type": "gantt", "doctype": "Work Order"}]}

    view = view_from_json(payload)

    assert view.blocks[0].type == "gantt"


def test_a_payload_that_is_not_an_object_is_a_wire_error():
    with pytest.raises(WireError):
        view_from_json(["工单"])


def test_blocks_must_be_a_list():
    with pytest.raises(WireError):
        view_from_json({"name": "x", "title": "x", "blocks": {"type": "list"}})


def test_a_block_that_is_not_an_object_is_a_wire_error():
    with pytest.raises(WireError):
        view_from_json({"name": "x", "title": "x", "blocks": ["list"]})


def test_the_error_says_which_block_went_wrong():
    """回注给模型的消息要能让它改对 —— 说不清是哪一块，模型只能重猜。"""
    with pytest.raises(WireError) as excinfo:
        view_from_json({"name": "x", "title": "x", "blocks": [{"type": "list"}, "list"]})

    assert "blocks[1]" in str(excinfo.value)


def test_plain_json_text_parses():
    view = view_from_text('{"name":"x","title":"标题","blocks":[]}')

    assert view.name == "x"


def test_a_fenced_json_block_parses():
    """模型十有八九会套一个 ```json 围栏。**明确接受这一种**，其余一律拒。"""
    text = '前言\n```json\n{"name":"x","title":"标题","blocks":[]}\n```\n后记'

    assert view_from_text(text).name == "x"


def test_prose_without_any_json_is_a_wire_error():
    with pytest.raises(WireError):
        view_from_text("我建议你看一下工单列表。")


def test_broken_json_is_a_wire_error_not_a_crash():
    with pytest.raises(WireError):
        view_from_text('{"name":"x","title":"标题","blocks":[')


# ── 🔴 活体实测抓到的：模型会把 filters 写成对象数组 ─────────────────────────
#
# `qwen3.7-flash-2026-07-15` 2026-08-28 真跑时交的是
#   "filters": [{"field": "...", "operator": "=", "value": "..."}]
# 而 DSL 的形状是 `(字段, 算子, 值)` 三元组。
#
# 当时 `wire.py` 原样放过去 ⇒ `validate()` 的 `len(entry) != 3` 对一个三键的 dict
# **成立**（len 是 3），于是走到 `entry[1]` —— **KeyError 崩在循环里**。
# 一个本该被干净拒绝、回注给模型的格式错，变成了整轮跑飞。
#
# ⇒ 线格式必须保证交给校验器的每一段都是**校验器能求值的形状**。
#   这不违反「只解析形状不判对错」：判的正是形状本身。


def test_a_filter_written_as_an_object_is_a_wire_error():
    payload = {
        "name": "x",
        "title": "x",
        "blocks": [
            {
                "type": "list",
                "doctype": "Work Order",
                "fields": ["qty"],
                "filters": [{"field": "status", "operator": "=", "value": "In Process"}],
            }
        ],
    }

    with pytest.raises(WireError) as excinfo:
        view_from_json(payload)

    # 回注要能让模型改对：说清正确形状。
    assert "filters" in str(excinfo.value)


def test_a_filter_of_the_wrong_length_still_reaches_the_validator():
    """长度不对**不是**线格式的事 —— `validate()` 有一条「要形如 (字段, 算子, 值)」在等它。

    两者的界线：**形状能不能被求值**归线格式，**取值对不对**归校验器。
    """
    payload = {
        "name": "x",
        "title": "x",
        "blocks": [
            {"type": "list", "doctype": "Work Order", "fields": ["qty"],
             "filters": [["status", "="]]},
        ],
    }

    view = view_from_json(payload)

    assert view.blocks[0].filters == (("status", "="),)


def test_a_child_field_written_as_an_object_is_a_wire_error():
    payload = {
        "name": "x",
        "title": "x",
        "blocks": [
            {"type": "detail", "doctype": "Work Order", "fields": ["required_items"],
             "child_fields": [{"table": "required_items", "doctype": "Work Order Item"}]},
        ],
    }

    with pytest.raises(WireError):
        view_from_json(payload)


def test_a_sort_written_as_an_object_is_a_wire_error():
    payload = {
        "name": "x",
        "title": "x",
        "blocks": [
            {"type": "list", "doctype": "Work Order", "fields": ["qty"],
             "sort": {"field": "qty", "direction": "asc"}},
        ],
    }

    with pytest.raises(WireError):
        view_from_json(payload)
