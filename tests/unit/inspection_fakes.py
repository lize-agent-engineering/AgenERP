"""P1.5 巡检判据的夹具 —— **数据一行都不手写，全部由 `agenerp/seed/` 派生**。

`Decision` D4：手写夹具可以被调到「怎么写规则都命中」，消融判据就测不出发现力。
所以固定测例这一侧的行**逐字取自 `agenerp.seed.generate()`**；
第二个数据集只做一件事：把 `agenerp/seed/model.py` 的 `INHOUSE_QTY` / `SUBCON_QTY` /
`DELIVERY_QTY` **换成别的参数**，其余构造原样不动。

⚠️ **两侧取数方向不许合并**（照抄 `agenerp/seed/checks.py:18-20` 那条纪律）：
夹具（数据）从**构造侧**取（`agenerp/seed/`）；期望值从 `agenerp/seed/checks.py` 取，
或者由判据自己写死一个字面量。从同一侧取会让断言变成同义反复 ——
改一个构造常量，数据与期望一起动，判据不会发红。

⚠️ **耦合照实登记**：本夹具与种子数据集是**耦合**的，种子改了夹具会跟着变。
这是想要的耦合（改了就该红），不是「夹具独立」。

假站点仍然只有一份（`tests/tools/conftest.py`），按 `explain_fakes.load_repo_module`
的同一招加载，不复制、不另写。
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as _explain  # noqa: E402

from agenerp.seed import generate  # noqa: E402
from agenerp.seed.model import (  # noqa: E402
    COMPANY,
    DELIVERY_QTY,
    FINISHED_ITEM,
    INHOUSE_QTY,
    SUBCON_QTY,
)

FakeSite = _explain.FakeSite
client_for = _explain.client_for
doctype = _explain.doctype

INHOUSE_VOUCHER_TYPE = "Stock Entry"
SUBCON_VOUCHER_TYPE = "Subcontracting Receipt"

# 巡检器实际会查的两张表；其余种子表照搬进假站点只是为了让站点自洽。
LEDGER = "Stock Ledger Entry"
ORDER_ITEM = "Sales Order Item"

# DocType **元数据**（不是数据行）。巡检器只查前四张；后面几张是给 Phase 2 的归因用的
# —— 取证要 `doc.get` 那两张入库凭证、`doc.links` 那个物料，缺元数据会红在站点自洽性上。
_DOCTYPES = {
    LEDGER: doctype(module="Stock", fields=[]),
    "Bin": doctype(module="Stock", fields=[]),
    "Sales Order": doctype(is_submittable=1, fields=[]),
    ORDER_ITEM: doctype(istable=1, fields=[]),
    "Item": doctype(module="Stock", fields=[]),
    "Warehouse": doctype(module="Stock", fields=[]),
    "Stock Entry": doctype(module="Stock", is_submittable=1, fields=[]),
    "Subcontracting Receipt": doctype(module="Subcontracting", is_submittable=1, fields=[]),
    "Delivery Note": doctype(is_submittable=1, fields=[]),
    "Work Order": doctype(module="Manufacturing", is_submittable=1, fields=[]),
    "Company": doctype(module="Setup", fields=[]),
}

# 假站点的模块表（`system.overview` / `permission.scope` 会读它）。
_MODULES = [
    {"name": "Stock", "app_name": "erpnext"},
    {"name": "Selling", "app_name": "erpnext"},
    {"name": "Manufacturing", "app_name": "erpnext"},
    {"name": "Subcontracting", "app_name": "erpnext"},
    {"name": "Setup", "app_name": "erpnext"},
]

# 归因取证时会被点名的两张入库凭证所属的 DocType（判据按这个顺序断言）。
ATTRIBUTION_DOCTYPES = ("Stock Ledger Entry", "Sales Order", "Item")


def _retimed(row: dict[str, Any], inhouse: float, subcon: float, delivery: float) -> dict:
    """把成品那三笔数量换成给定参数。**键是种子常量，不是单号** ——
    照单号改就等于把答案抄进夹具。"""
    if row.get("item_code") != FINISHED_ITEM:
        return row
    qty = float(row.get("actual_qty") or 0)
    voucher_type = row.get("voucher_type")
    if qty == float(INHOUSE_QTY) and voucher_type == INHOUSE_VOUCHER_TYPE:
        return {**row, "actual_qty": inhouse}
    if qty == float(SUBCON_QTY) and voucher_type == SUBCON_VOUCHER_TYPE:
        return {**row, "actual_qty": subcon}
    if qty == -float(DELIVERY_QTY):
        return {**row, "actual_qty": -delivery}
    return row


def _order_items(orders: tuple[dict, ...]) -> list[dict]:
    """`Sales Order Item` 由销售订单的子表派生 —— 种子把子表内嵌在父单里，
    而 Frappe 的 REST 面上子表是独立资源（v15 需点名 `parent`）。"""
    rows = []
    for order in orders:
        for index, item in enumerate(order.get("items") or (), start=1):
            rows.append(
                {
                    **item,
                    "name": f"{order['name']}-item-{index}",
                    "parent": order["name"],
                    "parenttype": "Sales Order",
                }
            )
    return rows


def _bins(ledger: list[dict], original: tuple[dict, ...]) -> list[dict]:
    """成品仓的 `Bin` 随流水一起走。巡检规则**不读 Bin**（它汇总的是流水），
    重算它只是为了让假站点自洽，不是判据来源。"""
    balance: dict[tuple[str, str], float] = {}
    for row in ledger:
        key = (str(row.get("item_code")), str(row.get("warehouse")))
        balance[key] = balance.get(key, 0.0) + float(row.get("actual_qty") or 0)
    out = []
    for row in original:
        key = (str(row.get("item_code")), str(row.get("warehouse")))
        out.append({**row, "actual_qty": balance.get(key, float(row.get("actual_qty") or 0))})
    return out


def seed_site(
    *,
    inhouse: float = INHOUSE_QTY,
    subcon: float = SUBCON_QTY,
    delivery: float = DELIVERY_QTY,
) -> FakeSite:
    """把种子数据集摆成一个假站点。默认参数 = 固定测例本身。"""
    dataset = generate()
    ledger = [
        _retimed(dict(row), inhouse, subcon, delivery) for row in dataset.of(LEDGER)
    ]
    rows: dict[str, list[dict]] = {
        name: [dict(row) for row in dataset.of(name)] for name in dataset.doctypes()
    }
    rows[LEDGER] = ledger
    rows["Bin"] = _bins(ledger, dataset.of("Bin"))
    rows[ORDER_ITEM] = _order_items(dataset.of("Sales Order"))
    # 种子的行里没有 `doctype` 键（它是站点回包的形状，不是数据集的一部分），
    # 而 `doc.get` 的契约把 `doctype` 列进了 `must_keep`。补上是**对齐站点形状**，
    # 不是补数据 —— 值由表名给出，没有任何一处是手抄的。
    rows = {
        name: [{**row, "doctype": name} for row in table] for name, table in rows.items()
    }
    rows["Module Def"] = [dict(row) for row in _MODULES]
    rows["Company"] = [{"name": COMPANY, "doctype": "Company"}]
    return FakeSite(doctypes=dict(_DOCTYPES), rows=rows)


def unrelated_site() -> FakeSite:
    """一条**与积压陷阱无关**的合成轨迹：两个物料都是产多少卖多少，订单也都交清了。

    它不是种子数据集的变形，就是要与那个陷阱**无关** —— H3 判的是
    「规则口径有没有被放宽到在正常数据上也叫」。
    """
    return FakeSite(
        doctypes=dict(_DOCTYPES),
        rows={
            LEDGER: [
                {"name": "sle-a", "item_code": "bolt", "warehouse": "wh-north",
                 "actual_qty": 400, "voucher_type": "Stock Entry", "is_cancelled": 0},
                {"name": "sle-b", "item_code": "bolt", "warehouse": "wh-north",
                 "actual_qty": -400, "voucher_type": "Delivery Note", "is_cancelled": 0},
                {"name": "sle-c", "item_code": "washer", "warehouse": "wh-north",
                 "actual_qty": 250, "voucher_type": "Stock Entry", "is_cancelled": 0},
                {"name": "sle-d", "item_code": "washer", "warehouse": "wh-north",
                 "actual_qty": -250, "voucher_type": "Delivery Note", "is_cancelled": 0},
            ],
            ORDER_ITEM: [
                {"name": "soi-a", "item_code": "bolt", "qty": 400, "parent": "so-a"},
                {"name": "soi-b", "item_code": "washer", "qty": 250, "parent": "so-b"},
            ],
        },
    )
