"""主数据与订单：物料、仓库、BOM、销售订单、工单。

纯构造，无 RNG——这一层的每个数都参与断言。"""

from __future__ import annotations

from typing import Any

from agenerp.seed import names as N
from agenerp.seed.model import (
    BOM_RAW_QTY,
    COMPANY,
    CUSTOMER,
    DELIVERY_QTY,
    FINISHED_ITEM,
    INHOUSE_QTY,
    INHOUSE_VALUE,
    OPERATION_MINUTES,
    ORDER_QTY,
    RAW_ITEM,
    RAW_RATE,
    SALES_RATE,
    SERVICE_ITEM,
    WH_FINISHED,
    WH_RAW,
    WH_SUBCON,
    WH_WIP,
    WORKSTATION_HOUR_RATE,
    day,
)

Row = dict[str, Any]

def items() -> list[Row]:
    return [
        {
            "name": FINISHED_ITEM,
            "item_name": "XM 经编花边布",
            "item_group": "成品",
            "stock_uom": "Meter",
            "is_stock_item": 1,
        },
        {
            "name": RAW_ITEM,
            "item_name": "白色锦纶丝",
            "item_group": "原材料",
            "stock_uom": "Kg",
            "is_stock_item": 1,
        },
        {
            "name": SERVICE_ITEM,
            "item_name": "染整定型外协服务",
            "item_group": "服务",
            "stock_uom": "Nos",
            "is_stock_item": 0,
        },
    ]


def warehouses() -> list[Row]:
    return [
        {"name": WH_RAW, "company": COMPANY, "is_group": 0},
        {"name": WH_WIP, "company": COMPANY, "is_group": 0},
        {"name": WH_FINISHED, "company": COMPANY, "is_group": 0},
        {"name": WH_SUBCON, "company": COMPANY, "is_group": 0},
    ]


def bom() -> list[Row]:
    return [
        {
            "name": N.BOM,
            "item": FINISHED_ITEM,
            "company": COMPANY,
            "quantity": ORDER_QTY,
            "is_active": 1,
            "is_default": 1,
            "items": [
                {"item_code": RAW_ITEM, "qty": BOM_RAW_QTY, "rate": RAW_RATE},
            ],
            "operations": [
                {"operation": "织造", "time_in_mins": 300, "hour_rate": WORKSTATION_HOUR_RATE},
                {"operation": "定型", "time_in_mins": 180, "hour_rate": WORKSTATION_HOUR_RATE},
                {"operation": "成品检验", "time_in_mins": 120, "hour_rate": WORKSTATION_HOUR_RATE},
            ],
            "operating_cost": OPERATION_MINUTES / 60 * WORKSTATION_HOUR_RATE,
            "raw_material_cost": BOM_RAW_QTY * RAW_RATE,
            "total_cost": INHOUSE_VALUE,
        }
    ]


def sales_order() -> list[Row]:
    return [
        {
            "name": N.SALES_ORDER,
            "customer": CUSTOMER,
            "company": COMPANY,
            "transaction_date": day(0),
            "delivery_date": day(14),
            "docstatus": 1,
            "status": "Completed",
            "currency": "CNY",
            "items": [
                {
                    "item_code": FINISHED_ITEM,
                    "qty": ORDER_QTY,
                    "rate": SALES_RATE,
                    "uom": "Meter",
                    "warehouse": WH_FINISHED,
                    "delivered_qty": DELIVERY_QTY,
                }
            ],
            "total_qty": ORDER_QTY,
            "grand_total": ORDER_QTY * SALES_RATE,
        }
    ]


def work_order() -> list[Row]:
    return [
        {
            "name": N.WORK_ORDER,
            "production_item": FINISHED_ITEM,
            "bom_no": N.BOM,
            "company": COMPANY,
            "sales_order": N.SALES_ORDER,
            "qty": ORDER_QTY,
            "produced_qty": INHOUSE_QTY,
            "wip_warehouse": WH_WIP,
            "fg_warehouse": WH_FINISHED,
            "docstatus": 1,
            "status": "Completed",
            "required_items": [
                {
                    "item_code": RAW_ITEM,
                    "source_warehouse": WH_RAW,
                    "required_qty": BOM_RAW_QTY,
                    "transferred_qty": BOM_RAW_QTY,
                    "consumed_qty": BOM_RAW_QTY,
                }
            ],
        }
    ]
