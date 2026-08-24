"""业务单据：库存分录、外协四步链、发货、两张逾期发票。

「990 台之谜」的解释在**销售订单自己身上**：订单 1,000 台、发货 990 台，
差额 10 台既没发也没记欠货——有人把 `status` 置成 `Closed`，ERPNext 据此
按完成计，达成率显示 100%，账面没有一个字段是红的。

D-9 之前这里挂的是 XM 自建的 `Loss Review`（`LOSS-00003`，一笔"已审批合理
损耗"）。原生 ERPNext 无此表，已弃用。换成原生字段后荒谬**更锋利**：
从前尚有"损耗审批过了"这个解释，现在没有任何解释，只是有人关了单。"""

from __future__ import annotations

import random
from typing import Any

from agenerp.seed import names as N
from agenerp.seed.model import (
    ACC_OPERATING,
    BOM_RAW_QTY,
    COMPANY,
    CUSTOMER,
    DELIVERY_QTY,
    FINISHED_ITEM,
    INHOUSE_QTY,
    INHOUSE_RATE,
    INHOUSE_VALUE,
    INVOICE_TERM_DAYS,
    OPENING_RAW_QTY,
    OPERATION_MINUTES,
    RAW_ITEM,
    RAW_RATE,
    SALES_RATE,
    SERVICE_ITEM,
    SUBCONTRACT_FEE,
    SUBCON_QTY,
    SUBCON_RATE,
    SUBCON_VALUE,
    SUPPLIER,
    WH_FINISHED,
    WH_RAW,
    WH_SUBCON,
    WH_WIP,
    WORKSTATION_HOUR_RATE,
    day,
)

Row = dict[str, Any]

def _lot(rng: random.Random) -> str:
    """装饰性字段：批号后缀。**不参与任何断言**，存在只为让 `--seed` 是真参数。"""
    return f"HRD-LOT-{rng.randrange(100000, 1000000)}"


def stock_entries(rng: random.Random) -> list[Row]:
    """四张库存分录。批号是装饰性字段，其余每个数都参与断言。"""
    return [
        {
            "name": N.OPENING,
            "stock_entry_type": "Material Receipt",
            "company": COMPANY,
            "posting_date": day(0),
            "docstatus": 1,
            "remarks": "HRD-OPENING-2026Q1",
            "items": [
                {
                    "item_code": RAW_ITEM,
                    "t_warehouse": WH_RAW,
                    "qty": OPENING_RAW_QTY,
                    "basic_rate": RAW_RATE,
                    "amount": OPENING_RAW_QTY * RAW_RATE,
                    "lot_no": _lot(rng),
                }
            ],
        },
        {
            "name": N.TRANSFER,
            "stock_entry_type": "Material Transfer for Manufacture",
            "company": COMPANY,
            "posting_date": day(1),
            "docstatus": 1,
            "work_order": N.WORK_ORDER,
            "items": [
                {
                    "item_code": RAW_ITEM,
                    "s_warehouse": WH_RAW,
                    "t_warehouse": WH_WIP,
                    "qty": BOM_RAW_QTY,
                    "basic_rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                }
            ],
        },
        {
            "name": N.MANUFACTURE,
            "stock_entry_type": "Manufacture",
            "company": COMPANY,
            "posting_date": day(3),
            "docstatus": 1,
            "work_order": N.WORK_ORDER,
            "additional_costs": [
                {
                    "expense_account": ACC_OPERATING,
                    "description": "工序费用（模组装配/BMS 调试老化/成品检验）",
                    "amount": OPERATION_MINUTES / 60 * WORKSTATION_HOUR_RATE,
                }
            ],
            "items": [
                {
                    "item_code": RAW_ITEM,
                    "s_warehouse": WH_WIP,
                    "qty": BOM_RAW_QTY,
                    "basic_rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                },
                {
                    "item_code": FINISHED_ITEM,
                    "t_warehouse": WH_FINISHED,
                    "qty": INHOUSE_QTY,
                    "basic_rate": INHOUSE_RATE,
                    "amount": INHOUSE_VALUE,
                    "is_finished_item": 1,
                    "lot_no": _lot(rng),
                },
            ],
        },
        {
            "name": N.RM_TO_SUBCON,
            "stock_entry_type": "Send to Subcontractor",
            "company": COMPANY,
            "posting_date": day(4),
            "docstatus": 1,
            "subcontracting_order": N.SUBCON_ORDER,
            "items": [
                {
                    "item_code": RAW_ITEM,
                    "s_warehouse": WH_RAW,
                    "t_warehouse": WH_SUBCON,
                    "qty": BOM_RAW_QTY,
                    "basic_rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                }
            ],
        },
    ]


def subcontracting() -> tuple[list[Row], list[Row]]:
    """外协批：**ERPNext v15 原生结构**（D-12）。

    结构照站点实测形状写，不自造：
    - `items` 装的是**成品**（HRD-PACK-5K，带 BOM 与收货仓），不是服务件
    - `service_items` 才装服务件，带 `fg_item` / `fg_item_qty` 指回成品
    - `supplied_items` 是发给供应商的原料，`reserve_warehouse` 是**原料仓**

    D-12 之前这里把服务件塞进 `items`，与站点对不上；而站点侧当时压根没有这两张单
    （装载器把外协批伪造成第二张工单）。两边现已统一到真实语义。
    """
    order = [
        {
            "name": N.SUBCON_ORDER,
            "purchase_order": N.SUBCON_PO,
            "supplier": SUPPLIER,
            "company": COMPANY,
            "transaction_date": day(3),
            "docstatus": 1,
            "status": "Completed",
            "supplier_warehouse": WH_SUBCON,
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    "qty": SUBCON_QTY,
                    "warehouse": WH_FINISHED,
                    "bom": N.BOM,
                    "rate": SUBCONTRACT_FEE / SUBCON_QTY,
                    "service_cost_per_qty": SUBCONTRACT_FEE / SUBCON_QTY,
                    "amount": SUBCONTRACT_FEE,
                }
            ],
            "service_items": [
                {
                    "item_code": SERVICE_ITEM,
                    "qty": SUBCON_QTY,
                    "rate": SUBCONTRACT_FEE / SUBCON_QTY,
                    "amount": SUBCONTRACT_FEE,
                    "fg_item": FINISHED_ITEM,
                    "fg_item_qty": SUBCON_QTY,
                }
            ],
            "supplied_items": [
                {
                    "rm_item_code": RAW_ITEM,
                    "required_qty": BOM_RAW_QTY,
                    "reserve_warehouse": WH_RAW,
                    "rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                }
            ],
        }
    ]
    receipt = [
        {
            "name": N.RECEIPT,
            "supplier": SUPPLIER,
            "company": COMPANY,
            "posting_date": day(5),
            "docstatus": 1,
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    # **挂在行上，不是表头。** ERPNext v15 的 `Subcontracting Receipt`
                    # 表头没有 `subcontracting_order` 列，它在 `Subcontracting Receipt
                    # Item` 上（站点实读确认）。此前离线放在表头，层级错了 ——
                    # 由 `_link_field_checks` 抓出（2026-08-24，它上线第一次跑就抓到两条）。
                    "subcontracting_order": N.SUBCON_ORDER,
                    "warehouse": WH_FINISHED,
                    "qty": SUBCON_QTY,
                    "received_qty": SUBCON_QTY,
                    "rate": SUBCON_RATE,
                    "amount": SUBCON_VALUE,
                    # 站点实算的两段分解（实测：2,960 + 120 = 3,080）。
                    "rm_cost_per_qty": BOM_RAW_QTY * RAW_RATE / SUBCON_QTY,
                    "service_cost_per_qty": SUBCONTRACT_FEE / SUBCON_QTY,
                }
            ],
            "supplied_items": [
                {
                    "rm_item_code": RAW_ITEM,
                    "reserve_warehouse": WH_RAW,
                    "consumed_qty": BOM_RAW_QTY,
                    "rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                }
            ],
            "total_service_cost": SUBCONTRACT_FEE,
        }
    ]
    return order, receipt


def subcontract_purchase_order() -> list[Row]:
    """外协采购订单 —— ERPNext v15 外协链的起点（D-12）。

    `Subcontracting Order` 的 `purchase_order` 是**必填**（实测 `DocField.reqd = 1`），
    外协订单只能由它派生（`make_subcontracting_order`）。缺这一张，离线数据集与
    站点的文档图就对不上 —— 那正是 D-12 要治理的分歧。
    """
    return [
        {
            "name": N.SUBCON_PO,
            "supplier": SUPPLIER,
            "company": COMPANY,
            "transaction_date": day(3),
            "schedule_date": day(4),
            "docstatus": 1,
            "status": "Completed",
            "is_subcontracted": 1,
            "supplier_warehouse": WH_SUBCON,
            # 发料仓。不设则 ERPNext 把 `reserve_warehouse` 推成采购行的收货仓
            # （成品仓），发料时查不到电芯估值（实测 417）。
            "set_reserve_warehouse": WH_RAW,
            "items": [
                {
                    "item_code": SERVICE_ITEM,
                    "qty": SUBCON_QTY,
                    "rate": SUBCONTRACT_FEE / SUBCON_QTY,
                    "amount": SUBCONTRACT_FEE,
                    "warehouse": WH_FINISHED,
                    "fg_item": FINISHED_ITEM,
                    "fg_item_qty": SUBCON_QTY,
                }
            ],
            "grand_total": SUBCONTRACT_FEE,
        }
    ]


def delivery() -> list[Row]:
    return [
        {
            "name": N.DELIVERY,
            "customer": CUSTOMER,
            "company": COMPANY,
            "posting_date": day(6),
            "docstatus": 1,
            "status": "Completed",
            "po_no": "NNE-PO-2026-0117",
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    "warehouse": WH_FINISHED,
                    "qty": DELIVERY_QTY,
                    "rate": SALES_RATE,
                    "amount": DELIVERY_QTY * SALES_RATE,
                    "against_sales_order": N.SALES_ORDER,
                    "incoming_rate": INHOUSE_RATE,
                }
            ],
            "grand_total": DELIVERY_QTY * SALES_RATE,
        }
    ]


def invoices() -> tuple[list[Row], list[Row]]:
    """两笔逾期：合计由单据自然加总，**不硬写**（§12.5）。

    逾期与否由 `as_of` 与 `due_date` 相比得出，不读时钟。
    """
    sales = [
        {
            "name": N.SALES_INVOICE,
            "customer": CUSTOMER,
            "company": COMPANY,
            "posting_date": day(6),
            "due_date": day(6 + INVOICE_TERM_DAYS),
            "docstatus": 1,
            "status": "Overdue",
            "po_no": "NNE-PO-2026-0117",
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    "qty": DELIVERY_QTY,
                    "rate": SALES_RATE,
                    "amount": DELIVERY_QTY * SALES_RATE,
                    "delivery_note": N.DELIVERY,
                }
            ],
            "grand_total": DELIVERY_QTY * SALES_RATE,
            "outstanding_amount": DELIVERY_QTY * SALES_RATE,
        }
    ]
    purchase = [
        {
            "name": N.PURCHASE_INVOICE,
            "supplier": SUPPLIER,
            "company": COMPANY,
            "posting_date": day(5),
            "due_date": day(5 + INVOICE_TERM_DAYS),
            "docstatus": 1,
            "status": "Overdue",
            "bill_no": "LGCN-2026-0043",
            "items": [
                {
                    "item_code": SERVICE_ITEM,
                    "qty": 1,
                    "rate": SUBCONTRACT_FEE,
                    "amount": SUBCONTRACT_FEE,
                    "subcontracting_receipt": N.RECEIPT,
                }
            ],
            "grand_total": SUBCONTRACT_FEE,
            "outstanding_amount": SUBCONTRACT_FEE,
        }
    ]
    return sales, purchase
