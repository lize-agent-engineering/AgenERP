"""数据集的装配：把各层的构造函数拼成一份 `Dataset`。

纯函数，无 IO、无时钟、无环境读取。`random.Random(seed)` 只驱动不参与任何断言的
装饰性字段（批号后缀），且只用 `randrange`——`shuffle` / `sample` 的实现细节
在 CPython 历史上变过，把确定性押在它们上面等于押在实现细节上（`docs/architecture/module-boundaries.md` §12.4）。

排序在**生成期**做死（DocType 名与单据号两级），不留给落盘或比较环节：
确定性的落点只该有一个。
"""

from __future__ import annotations

import random
from typing import Any

from agenerp.seed import documents, ledger, masters
from agenerp.seed.model import INVOICE_TERM_DAYS, OVERDUE_DAYS, Dataset, day

Row = dict[str, Any]


def generate(seed: int = 42) -> Dataset:
    """确定性生成整份数据集。同 `seed` 两次调用结果相等。"""
    rng = random.Random(seed)
    sales_invoice, purchase_invoice = documents.invoices()
    subcon_order, subcon_receipt = documents.subcontracting()
    stock_ledger, bins = ledger.stock_ledger_and_bins()
    grouped: dict[str, list[Row]] = {
        "Item": masters.items(),
        "Warehouse": masters.warehouses(),
        "BOM": masters.bom(),
        "Sales Order": masters.sales_order(),
        "Work Order": masters.work_order(),
        "Stock Entry": documents.stock_entries(rng),
        "Purchase Order": documents.subcontract_purchase_order(),
        "Subcontracting Order": subcon_order,
        "Subcontracting Receipt": subcon_receipt,
        "Delivery Note": documents.delivery(),
        "Sales Invoice": sales_invoice,
        "Purchase Invoice": purchase_invoice,
        "Stock Ledger Entry": stock_ledger,
        "Bin": bins,
        "GL Entry": ledger.gl_entries(),
    }
    records = {
        doctype: tuple(sorted(rows, key=lambda row: str(row["name"])))
        for doctype, rows in sorted(grouped.items())
    }
    return Dataset(
        seed=seed,
        as_of=day(6 + INVOICE_TERM_DAYS + OVERDUE_DAYS),
        records=records,
    )
