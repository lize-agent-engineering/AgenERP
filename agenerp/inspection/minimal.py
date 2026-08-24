"""巡检器自带的**最小规则集 v0** —— 一条规则，够命中固定测例，不多写一条。

⚠️ **这不是行业包。** 行业包 v0（每条带 `test_case` 的声明式规则清单，`pack_id` 的来源）
归 P1.6；本清单是**引擎自带的判据夹具**，用来证明「发现力来自规则清单」这件事本身。
读到 `agenerp/tools/queries.py` 的「本期没有行业包」时不要误判成过期漂移 —— 两者说的是两件事。

规则的口径来自 `docs/design/agents-and-roles.md` §5.0 ② 的实测结论逐字：
积压这种异常「不在任何字段上」，必须「汇总入库 − 出库，对照订单量判断
『多出来的有没有道理』」，前提是**先知道「产出远大于销出」是个问题**。

**措辞保持通用**：不出现任何单据号、任何物料号、任何具体数量。
判据 `tests/unit/test_inspection_rules.py` 直接对序列化后的声明断言这一条 ——
照答案写的规则会自证为真而毫无信息量（与 `EVIDENCE_GATE_L3` 的同一条纪律）。
"""

from __future__ import annotations

from typing import Any

from agenerp.inspection.rules import Rule, load_rules

RULE_OUTPUT_FAR_EXCEEDS_SOLD = "stock/output-far-exceeds-sold"

# 命中判据的比例阈值：剩下的存货**与订单量同一量级**才算「产出远大于销出」。
# 取半数是 v0 的保守口径（不是实测出来的），残余风险登记在 §7.9。
BACKLOG_FRACTION_OF_ORDERED = 0.5

DECLARATIONS: tuple[dict[str, Any], ...] = (
    {
        "rule_id": RULE_OUTPUT_FAR_EXCEEDS_SOLD,
        "statement": (
            "产出远大于销出：某物料在某仓库累计入库减去累计出库之后，"
            "剩下的存货仍与该物料的订单量同一量级 —— 多出来的这些没有道理"
        ),
        "doctype": "Stock Ledger Entry",
        "group_by": ["item_code", "warehouse"],
        "exclude": [{"field": "is_cancelled", "operator": "truthy"}],
        "measures": [
            {"name": "received", "operator": "sum_positive", "field": "actual_qty"},
            {"name": "issued", "operator": "sum_negative_abs", "field": "actual_qty"},
            {
                "name": "on_hand",
                "operator": "difference",
                "left": "received",
                "right": "issued",
            },
            {
                "name": "ordered",
                "operator": "related_sum",
                "doctype": "Sales Order Item",
                "parent": "Sales Order",
                "field": "qty",
                "match": [["item_code", "item_code"]],
            },
        ],
        "trigger": {
            "measure": "on_hand",
            "operator": "at_least_fraction_of",
            "reference": "ordered",
            "value": BACKLOG_FRACTION_OF_ORDERED,
        },
        "quantity": "on_hand",
        "test_case": {
            "name": "入库远多于出库、且剩余与订单量同量级 → 命中；卖光了 → 不命中",
            "rows": {
                "Stock Ledger Entry": [
                    {"item_code": "widget", "warehouse": "wh-main", "actual_qty": 120},
                    {"item_code": "widget", "warehouse": "wh-main", "actual_qty": -30},
                    {"item_code": "gasket", "warehouse": "wh-main", "actual_qty": 60},
                    {"item_code": "gasket", "warehouse": "wh-main", "actual_qty": -60},
                ],
                "Sales Order Item": [
                    {"item_code": "widget", "qty": 100},
                    {"item_code": "gasket", "qty": 60},
                ],
            },
            "expect_hit": True,
            "expect_quantity": 90,
        },
    },
)


def minimal_rules() -> tuple[Rule, ...]:
    """装载最小规则集。**每次都过一遍装载器** —— 声明改坏了在这里就红。"""
    return load_rules(DECLARATIONS)
