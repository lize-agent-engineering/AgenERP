"""P2.1 · 测试用的 schema 视图。

⚠️ 这里的字段**取自真实站点上真实存在的字段**（`Sales Order` / `Sales Order Item`），
不是编的。理由：`p2-views-roadmap.md` 硬约束 ④ 要求产出指回真实字段，而
**拿一份编造的 schema 去测「字段存在性」，测的是我编得对不对，不是校验器对不对。**

真实性由 `tests/dsl/test_fixture_schema_is_real.py` 在活站点上守着（live 层）。
"""

from __future__ import annotations

from agenerp.dsl.schema import SchemaView

# `Sales Order` / `Sales Order Item` 上真实存在的字段（子集，够本层用）。
SALES_SCHEMA = SchemaView(
    {
        "Sales Order": {
            "customer": "Link",
            "customer_name": "Data",
            "transaction_date": "Date",
            "delivery_date": "Date",
            "grand_total": "Currency",
            "status": "Select",
            "items": "Table",
            "terms": "Text Editor",
        },
        "Sales Order Item": {
            "item_code": "Link",
            "qty": "Float",
            "rate": "Currency",
            "delivered_qty": "Float",
        },
    }
)
