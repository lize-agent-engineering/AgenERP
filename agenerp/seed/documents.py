"""业务单据：库存分录、外协、已审批损耗、发货、两张逾期发票。

`LOSS-00003` 那 10 米是「990 米之谜」的解释：销售单 1,000 米、发货 990 米，
差额是一笔审批过的合理损耗，因此达成率 100%——账面没有一个字段是红的。"""

from __future__ import annotations

import random
from typing import Any

from agenerp.seed import names as N
from agenerp.seed.model import (
    ACC_OPERATING,
    APPROVED_LOSS_QTY,
    BOM_RAW_QTY,
    COMPANY,
    CUSTOMER,
    DELIVERY_QTY,
    FINISHED_ITEM,
    INHOUSE_QTY,
    INHOUSE_RATE,
    INHOUSE_VALUE,
    INVOICE_TERM_DAYS,
    LOSS_REVIEW_NAME,
    LOSS_REVIEW_STATUS,
    OPENING_RAW_QTY,
    OPERATION_MINUTES,
    ORDER_QTY,
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
    return f"XM-LOT-{rng.randrange(100000, 1000000)}"


def stock_entries(rng: random.Random) -> list[Row]:
    """四张库存分录。批号是装饰性字段，其余每个数都参与断言。"""
    return [
        {
            "name": N.OPENING,
            "stock_entry_type": "Material Receipt",
            "company": COMPANY,
            "posting_date": day(0),
            "docstatus": 1,
            "remarks": "XM-DEMO-OPENING",
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
                    "description": "工序费用（织造/定型/成品检验）",
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
    order = [
        {
            "name": N.SUBCON_ORDER,
            "supplier": SUPPLIER,
            "company": COMPANY,
            "transaction_date": day(3),
            "docstatus": 1,
            "status": "Completed",
            "items": [
                {
                    "item_code": SERVICE_ITEM,
                    "qty": 1,
                    "rate": SUBCONTRACT_FEE,
                    "fg_item": FINISHED_ITEM,
                    "fg_item_qty": SUBCON_QTY,
                    "bom": N.BOM,
                    "warehouse": WH_FINISHED,
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
            "subcontracting_order": N.SUBCON_ORDER,
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    "warehouse": WH_FINISHED,
                    "qty": SUBCON_QTY,
                    "rate": SUBCON_RATE,
                    "amount": SUBCON_VALUE,
                    "service_cost_per_qty": SUBCONTRACT_FEE / SUBCON_QTY,
                }
            ],
            "supplied_items": [
                {
                    "rm_item_code": RAW_ITEM,
                    "reserve_warehouse": WH_SUBCON,
                    "consumed_qty": BOM_RAW_QTY,
                    "rate": RAW_RATE,
                    "amount": BOM_RAW_QTY * RAW_RATE,
                }
            ],
            "total_service_cost": SUBCONTRACT_FEE,
        }
    ]
    return order, receipt


def loss_review() -> list[Row]:
    """`LOSS-00003`：10 米**已审批**合理损耗。

    「990 米之谜」靠它成立——销售单 1,000 米、发货 990 米，剩下的 10 米不是欠货，
    是一笔审批过的损耗，因此达成率是 100% 而不是 99%。
    """
    return [
        {
            "name": LOSS_REVIEW_NAME,
            "work_order": N.WORK_ORDER,
            "sales_order": N.SALES_ORDER,
            "input_quantity": ORDER_QTY,
            "off_machine_quantity": ORDER_QTY,
            "available_finished_quantity": ORDER_QTY,
            "approved_loss_quantity": APPROVED_LOSS_QTY,
            "actual_delivery_quantity": DELIVERY_QTY,
            "status": LOSS_REVIEW_STATUS,
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
            "po_no": "XM-DEMO-1000M",
            "xm_loss_review": LOSS_REVIEW_NAME,
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
            "po_no": "XM-DEMO-1000M",
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
            "bill_no": "XM-DEMO-SUBCONTRACT",
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
