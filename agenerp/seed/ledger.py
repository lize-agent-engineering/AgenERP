"""库存流水、结存与总账分录，全部由一张移动表推出。

两套口径会让「流水」与「结存」对不上，而这份数据集的全部意义正是「结存 1,010 米」这一个数。"""

from __future__ import annotations

from typing import Any

from agenerp.seed import names as N
from agenerp.seed.model import (
    ACC_COGS,
    ACC_FINISHED,
    ACC_GRNI,
    ACC_OPERATING,
    ACC_PAYABLE,
    ACC_RAW,
    ACC_RECEIVABLE,
    ACC_REVENUE,
    ACC_STOCK_ADJ,
    ACC_SUBCON_STOCK,
    ACC_WIP,
    BOM_RAW_QTY,
    COGS_VALUE,
    COMPANY,
    DELIVERY_QTY,
    FINISHED_ITEM,
    INHOUSE_QTY,
    INHOUSE_VALUE,
    OPENING_RAW_QTY,
    OPERATION_MINUTES,
    PAYABLE_OVERDUE,
    RAW_ITEM,
    RAW_RATE,
    RECEIVABLE_OVERDUE,
    SUBCONTRACT_FEE,
    SUBCON_QTY,
    SUBCON_VALUE,
    WH_FINISHED,
    WH_RAW,
    WH_SUBCON,
    WH_WIP,
    WORKSTATION_HOUR_RATE,
    day,
)

Row = dict[str, Any]

# 库存流水的唯一事实源：(单据类型, 单据号, 过账日, 物料, 仓库, 数量增减, 价值增减)。
# `Stock Ledger Entry` 与 `Bin` 都由它推出——两套口径会让「流水」与「结存」对不上，
# 而这个数据集的全部意义正是「结存 1,010 米」这一个数。
def movements() -> list[tuple[str, str, str, str, str, float, float]]:
    raw_batch = BOM_RAW_QTY * RAW_RATE
    return [
        ("Stock Entry", N.OPENING, day(0), RAW_ITEM, WH_RAW, OPENING_RAW_QTY, OPENING_RAW_QTY * RAW_RATE),
        ("Stock Entry", N.TRANSFER, day(1), RAW_ITEM, WH_RAW, -BOM_RAW_QTY, -raw_batch),
        ("Stock Entry", N.TRANSFER, day(1), RAW_ITEM, WH_WIP, BOM_RAW_QTY, raw_batch),
        ("Stock Entry", N.MANUFACTURE, day(3), RAW_ITEM, WH_WIP, -BOM_RAW_QTY, -raw_batch),
        ("Stock Entry", N.MANUFACTURE, day(3), FINISHED_ITEM, WH_FINISHED, INHOUSE_QTY, INHOUSE_VALUE),
        ("Stock Entry", N.RM_TO_SUBCON, day(4), RAW_ITEM, WH_RAW, -BOM_RAW_QTY, -raw_batch),
        ("Stock Entry", N.RM_TO_SUBCON, day(4), RAW_ITEM, WH_SUBCON, BOM_RAW_QTY, raw_batch),
        ("Subcontracting Receipt", N.RECEIPT, day(5), RAW_ITEM, WH_SUBCON, -BOM_RAW_QTY, -raw_batch),
        ("Subcontracting Receipt", N.RECEIPT, day(5), FINISHED_ITEM, WH_FINISHED, SUBCON_QTY, SUBCON_VALUE),
        # FIFO：990 台全部出自制批，因此出库价值是 990 × 自制单价，不是均价（§12.1）。
        ("Delivery Note", N.DELIVERY, day(6), FINISHED_ITEM, WH_FINISHED, -DELIVERY_QTY, -COGS_VALUE),
    ]


def stock_ledger_and_bins() -> tuple[list[Row], list[Row]]:
    qty: dict[tuple[str, str], float] = {}
    value: dict[tuple[str, str], float] = {}
    ledger: list[Row] = []
    for index, (vtype, vno, posting, item, warehouse, dq, dv) in enumerate(movements(), start=1):
        key = (item, warehouse)
        qty[key] = round(qty.get(key, 0.0) + dq, 6)
        value[key] = round(value.get(key, 0.0) + dv, 6)
        ledger.append(
            {
                "name": f"SLE-2026-{index:05d}",
                "voucher_type": vtype,
                "voucher_no": vno,
                "posting_date": posting,
                "item_code": item,
                "warehouse": warehouse,
                "actual_qty": dq,
                "stock_value_difference": dv,
                "qty_after_transaction": qty[key],
                "stock_value": value[key],
            }
        )
    bins = [
        {
            "name": f"BIN-{item}-{warehouse}",
            "item_code": item,
            "warehouse": warehouse,
            "actual_qty": qty[(item, warehouse)],
            "stock_value": value[(item, warehouse)],
            "valuation_rate": (
                round(value[(item, warehouse)] / qty[(item, warehouse)], 6)
                if qty[(item, warehouse)]
                else 0.0
            ),
        }
        for item, warehouse in sorted(qty)
    ]
    return ledger, bins


def gl_entries() -> list[Row]:
    raw_batch = BOM_RAW_QTY * RAW_RATE
    operating = OPERATION_MINUTES / 60 * WORKSTATION_HOUR_RATE
    vouchers: list[tuple[str, str, str, list[tuple[str, float, float]]]] = [
        ("Stock Entry", N.OPENING, day(0), [
            (ACC_RAW, OPENING_RAW_QTY * RAW_RATE, 0.0),
            (ACC_STOCK_ADJ, 0.0, OPENING_RAW_QTY * RAW_RATE),
        ]),
        ("Stock Entry", N.TRANSFER, day(1), [
            (ACC_WIP, raw_batch, 0.0),
            (ACC_RAW, 0.0, raw_batch),
        ]),
        ("Stock Entry", N.MANUFACTURE, day(3), [
            (ACC_FINISHED, INHOUSE_VALUE, 0.0),
            (ACC_WIP, 0.0, raw_batch),
            (ACC_OPERATING, 0.0, operating),
        ]),
        ("Stock Entry", N.RM_TO_SUBCON, day(4), [
            (ACC_SUBCON_STOCK, raw_batch, 0.0),
            (ACC_RAW, 0.0, raw_batch),
        ]),
        ("Subcontracting Receipt", N.RECEIPT, day(5), [
            (ACC_FINISHED, SUBCON_VALUE, 0.0),
            (ACC_SUBCON_STOCK, 0.0, raw_batch),
            (ACC_GRNI, 0.0, SUBCONTRACT_FEE),
        ]),
        ("Delivery Note", N.DELIVERY, day(6), [
            (ACC_COGS, COGS_VALUE, 0.0),
            (ACC_FINISHED, 0.0, COGS_VALUE),
        ]),
        ("Sales Invoice", N.SALES_INVOICE, day(6), [
            (ACC_RECEIVABLE, RECEIVABLE_OVERDUE, 0.0),
            (ACC_REVENUE, 0.0, RECEIVABLE_OVERDUE),
        ]),
        ("Purchase Invoice", N.PURCHASE_INVOICE, day(5), [
            (ACC_GRNI, PAYABLE_OVERDUE, 0.0),
            (ACC_PAYABLE, 0.0, PAYABLE_OVERDUE),
        ]),
    ]
    rows: list[Row] = []
    index = 0
    for vtype, vno, posting, legs in vouchers:
        for account, debit, credit in legs:
            index += 1
            rows.append(
                {
                    "name": f"GL-2026-{index:05d}",
                    "posting_date": posting,
                    "company": COMPANY,
                    "account": account,
                    "debit": round(debit, 2),
                    "credit": round(credit, 2),
                    "voucher_type": vtype,
                    "voucher_no": vno,
                }
            )
    return rows
