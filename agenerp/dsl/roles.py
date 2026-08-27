"""角色的日常视图 —— P2.2 路线 C 的分母。

人 2026-08-27 选定路线 **C · 按角色做到 100%**：不重写 Desk（`system-baseline.md`
§3.2 已判那条走不通），而是把「100% 完备」的**分母**从「全部 1000+ DocType」
换成「**这个角色每天碰的那几个**」。

本模块就是那个分母的定义。**它先于渲染器实现提交**（plan §2.1 的 R1 靠这个顺序成立）：
若允许事后调整视图定义，「落回 = 0」这条验收就退化成「我挑了一组不会落回的字段」。

## 车间工人

`agenerp/seedusers.py:30-39` 在站点上建的真实受限身份：
`worker@hrd.example.com`，**仅可读 `Work Order` / `Stock Entry` / `Item`**，
权限由 `Custom DocPerm` 强制。⚠️ **不得为了让渲染器好做而放宽它。**

## ⚠️ v0 硬编码在代码里，这是暂时的

P2.0 已判**视图产物落 AgenERP 自有表**（Workspace 会被升级整条删了重插）。
建表与 GitOps 是 **P2.4** 的结果面 —— 那时本模块的这几份定义是它的输入。
**在那之前硬编码，且这句话写在这里，免得它悄悄变成永久形态。**
"""

from __future__ import annotations

from agenerp.dsl.blocks import Block, View

WORKER_ROLE = "车间工人"
WORKER_DOCTYPES: tuple[str, ...] = ("Work Order", "Stock Entry", "Item")


# ① 今天要做哪些工单 —— 工人开工第一眼看的东西
WORKER_WORK_ORDERS = View(
    name="worker-work-orders",
    title="我的工单",
    blocks=(
        Block(
            type="metric",
            title="计划产量合计",
            doctype="Work Order",
            fields=("qty",),
            agg="sum",
        ),
        Block(
            type="list",
            title="工单",
            doctype="Work Order",
            fields=("production_item", "item_name", "qty", "produced_qty",
                    "status", "planned_start_date"),
            sort=("planned_start_date", "asc"),
            limit=50,
        ),
        Block(
            type="detail",
            title="工单明细",
            doctype="Work Order",
            # `image` 是 Attach Image、`required_items` / `operations` 是 Table
            # —— 工人确实要看图和用料表，**不是为了凑落回才放进来的**。
            fields=("production_item", "qty", "produced_qty", "status",
                    "source_warehouse", "fg_warehouse",
                    "image", "required_items", "operations"),
            child_fields=(
                ("required_items", "Work Order Item",
                 ("item_code", "item_name", "required_qty", "transferred_qty",
                  "consumed_qty", "source_warehouse")),
                ("operations", "Work Order Operation",
                 ("operation", "workstation", "status", "completed_qty",
                  "actual_operation_time")),
            ),
        ),
    ),
)


# ② 物料调拨 —— 领料、报工、入库都走这张单
WORKER_STOCK_ENTRIES = View(
    name="worker-stock-entries",
    title="物料调拨",
    blocks=(
        Block(
            type="list",
            title="调拨单",
            doctype="Stock Entry",
            fields=("stock_entry_type", "purpose", "posting_date",
                    "work_order", "from_warehouse", "to_warehouse"),
            sort=("posting_date", "desc"),
            limit=50,
        ),
        Block(
            type="detail",
            title="调拨明细",
            doctype="Stock Entry",
            # `items` 是 Table，展开后其行上的 `image` 是 Attach。
            fields=("stock_entry_type", "posting_date", "work_order",
                    "from_warehouse", "to_warehouse", "fg_completed_qty", "items"),
            child_fields=(
                # `image` 是 `Attach` —— 工人扫码领料时看的就是这张图。
                ("items", "Stock Entry Detail",
                 ("item_code", "item_name", "qty", "uom",
                  "s_warehouse", "t_warehouse", "image")),
            ),
        ),
    ),
)


# ③ 物料查询 —— 「这个料是什么、用什么单位、条码是多少」
WORKER_ITEMS = View(
    name="worker-items",
    title="物料",
    blocks=(
        Block(
            type="list",
            title="物料",
            doctype="Item",
            fields=("item_code", "item_name", "item_group", "stock_uom", "is_stock_item"),
            sort=("item_code", "asc"),
            limit=50,
        ),
        Block(
            type="detail",
            title="物料明细",
            doctype="Item",
            # `image` Attach Image · `description` Text Editor · `uoms` / `barcodes` Table
            fields=("item_code", "item_name", "item_group", "stock_uom",
                    "image", "description", "uoms", "barcodes"),
            child_fields=(
                ("uoms", "UOM Conversion Detail", ("uom", "conversion_factor")),
                ("barcodes", "Item Barcode", ("barcode", "barcode_type")),
            ),
        ),
    ),
)


WORKER_DAILY_VIEWS: tuple[View, ...] = (
    WORKER_WORK_ORDERS,
    WORKER_STOCK_ENTRIES,
    WORKER_ITEMS,
)
