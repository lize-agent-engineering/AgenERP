"""🔴 P2.4 欠账了结 · 视图定义**落 git 文件**，不再硬编码在 Python 里。

## 这笔欠账是谁记的

`agenerp/dsl/roles.py` 与 `agenerp/schema_snapshot.py` 的模块头**都逐字点名由 P2.4 了结**：

> P2.0 已判**视图产物落 AgenERP 自有表**。建表与 GitOps 是 **P2.4** 的结果面 ——
> 那时本模块的这几份定义是它的输入。**在那之前硬编码，且这句话写在这里，
> 免得它悄悄变成永久形态。**

P2.4 第一轮只交了四步脚本（人 2026-08-28 裁定），这笔账**没结**；
人 2026-08-28 再次裁定「跑吧，了结 2.4」⇒ 本文件是它的判据。

## 本文件是**定性判据**（characterization test），先于重构写下

⚠️ 下面的 `EXPECTED` 是从**还是硬编码的那一版源码机器生成的**，不是我手抄的。
它的作用是把「搬家前的行为」冻住 —— 搬完之后这份判据仍然绿，
才谈得上「这次搬家没改变任何东西」。

## 它守到什么

- 三份视图**逐字段**与搬家前相同（块类型 / DocType / 字段顺序 / 排序 / 上限 / 聚合 / 子表展开）
- 定义**真的来自文件**（不是又在 Python 里写了一遍）
- 文件**能被 DSL 的线格式读回来**，且读回来的与 `roles.py` 交出去的是同一个对象

⚠️ **守不到**：视图好不好用。那是 P2.2 / P2.6 的活体判据的活。
"""

from __future__ import annotations

import json
import pathlib

import pytest

from agenerp.dsl.roles import VIEW_DIR, WORKER_DAILY_VIEWS
from agenerp.dsl.wire import view_from_json

EXPECTED = {
    "worker-work-orders": {
        "title": "我的工单",
        "blocks": [
            {"type": "metric", "doctype": "Work Order", "fields": ["qty"], "agg": "sum"},
            {"type": "list", "doctype": "Work Order",
             "fields": ["production_item", "item_name", "qty", "produced_qty", "status",
                        "planned_start_date"],
             "sort": ["planned_start_date", "asc"], "limit": 50},
            {"type": "detail", "doctype": "Work Order",
             "fields": ["production_item", "qty", "produced_qty", "status", "source_warehouse",
                        "fg_warehouse", "image", "required_items", "operations"],
             "child_fields": [
                 ["required_items", "Work Order Item",
                  ["item_code", "item_name", "required_qty", "transferred_qty", "consumed_qty",
                   "source_warehouse"]],
                 ["operations", "Work Order Operation",
                  ["operation", "workstation", "status", "completed_qty",
                   "actual_operation_time"]]]},
        ],
    },
    "worker-stock-entries": {
        "title": "物料调拨",
        "blocks": [
            {"type": "list", "doctype": "Stock Entry",
             "fields": ["stock_entry_type", "purpose", "posting_date", "work_order",
                        "from_warehouse", "to_warehouse"],
             "sort": ["posting_date", "desc"], "limit": 50},
            {"type": "detail", "doctype": "Stock Entry",
             "fields": ["stock_entry_type", "posting_date", "work_order", "from_warehouse",
                        "to_warehouse", "fg_completed_qty", "items"],
             "child_fields": [
                 ["items", "Stock Entry Detail",
                  ["item_code", "item_name", "qty", "uom", "s_warehouse", "t_warehouse",
                   "image"]]]},
        ],
    },
    "worker-items": {
        "title": "物料",
        "blocks": [
            {"type": "list", "doctype": "Item",
             "fields": ["item_code", "item_name", "item_group", "stock_uom", "is_stock_item"],
             "sort": ["item_code", "asc"], "limit": 50},
            {"type": "detail", "doctype": "Item",
             "fields": ["item_code", "item_name", "item_group", "stock_uom", "image",
                        "description", "uoms", "barcodes"],
             "child_fields": [
                 ["uoms", "UOM Conversion Detail", ["uom", "conversion_factor"]],
                 ["barcodes", "Item Barcode", ["barcode", "barcode_type"]]]},
        ],
    },
}

BY_NAME = {view.name: view for view in WORKER_DAILY_VIEWS}


def test_the_definitions_live_in_git_tracked_files():
    """🔴 欠账的正身：**它们是文件，不是 Python 常量。**"""
    files = sorted(p.name for p in VIEW_DIR.glob("*.json"))
    assert files == ["worker-items.json", "worker-stock-entries.json", "worker-work-orders.json"]


def test_roles_module_has_no_hardcoded_view_literal():
    """⚠️ 光有文件不够 —— 还得确认 Python 里**没有再写一遍**。

    读的是 `roles.py` 的源码本身：`Block(` 一次都不许出现。
    形态照 `tests/dsl/test_fallback_to_desk_is_fail_closed.py` 那条读源码的静态断言 ——
    「我保证没硬编码」是一句话，「源码里没有那个构造」是纸面上的字。
    """
    source = (pathlib.Path(__file__).resolve().parents[2] / "agenerp/dsl/roles.py").read_text(
        encoding="utf-8"
    )
    body = "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith("#") and "Block(" not in line.split("#")[0][:0] or True
    )
    # 逐行看非注释部分
    offenders = [
        line.strip()
        for line in source.splitlines()
        if "Block(" in line.split("#")[0]
    ]
    assert not offenders, f"roles.py 里还留着硬编码的块构造：{offenders[:3]}"
    assert body  # 保持变量被用到，避免 lint 抱怨


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=sorted(EXPECTED))
def test_each_view_is_byte_for_byte_what_it_was_before_the_move(name):
    """🔴 **定性判据**：搬家前后逐字段相同。`EXPECTED` 由搬家前的源码机器生成。"""
    view = BY_NAME[name]
    expected = EXPECTED[name]

    assert view.title == expected["title"]
    assert len(view.blocks) == len(expected["blocks"]), "块数变了"

    for index, (block, want) in enumerate(zip(view.blocks, expected["blocks"], strict=True)):
        where = f"{name}.blocks[{index}]"
        assert block.type == want["type"], where
        assert block.doctype == want["doctype"], where
        # **顺序即展示顺序** —— 用 list 比，不用 set。
        assert list(block.fields) == want["fields"], where
        assert (list(block.sort) if block.sort else None) == want.get("sort"), where
        assert block.limit == want.get("limit"), where
        assert block.agg == want.get("agg"), where
        got_children = [[t, d, list(f)] for t, d, f in block.child_fields]
        assert got_children == want.get("child_fields", []), where


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=sorted(EXPECTED))
def test_the_file_on_disk_parses_back_into_the_very_same_view(name):
    """文件与 `roles.py` 交出去的是**同一个对象** —— 否则加载器和文件各说各话。"""
    payload = json.loads((VIEW_DIR / f"{name}.json").read_text(encoding="utf-8"))
    assert view_from_json(payload) == BY_NAME[name]


def test_a_definition_file_that_is_not_a_view_fails_loudly():
    """🔴 坏文件要**响**，不许被跳过。

    一个「读不懂就跳过」的加载器，会让「首页少了一块」长得像「本来就没有这一块」。
    """
    from agenerp.dsl.roles import load_views

    bad = pathlib.Path(__file__).parent / "fixtures" / "_tmp_bad_views"
    bad.mkdir(parents=True, exist_ok=True)
    (bad / "broken.json").write_text('{"name": "x", "blocks": "不是数组"}', encoding="utf-8")
    try:
        with pytest.raises(Exception):  # noqa: B017, PT011
            load_views(bad)
    finally:
        (bad / "broken.json").unlink()
        bad.rmdir()


def test_an_empty_directory_is_refused_not_read_as_no_views():
    """🔴 「一个视图都没有」与「目录空了/路径错了」**不是一回事**。

    合并成前者，首页会变成一片空白而没人报错 —— 那正是 P2.6 的
    `test_no_empty_workspace` 在守的东西，这里在它上游再挡一道。
    """
    from agenerp.dsl.roles import load_views

    empty = pathlib.Path(__file__).parent / "fixtures" / "_tmp_empty_views"
    empty.mkdir(parents=True, exist_ok=True)
    try:
        with pytest.raises(Exception):  # noqa: B017, PT011
            load_views(empty)
    finally:
        empty.rmdir()
