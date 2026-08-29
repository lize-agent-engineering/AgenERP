"""被投毒的假站点 —— 形状与活站点实读一致，**数据不写进活站点**。

## 为什么是假站点，而不是往活站点的字段里真写载荷

被测的是「**模型会不会执行从工具返回值里读到的指令**」。那些字节是从 MariaDB 来的
还是从 fixture 来的，对模型完全没有区别；而真写进去要付一次站点污染 + 一次还原，
且 A2/A3 那两个字段实测是 `null`，写进去再抹掉未必字节级还原。

⚠️ **代价照实记**：这条选择让本实验测不到「活站点的字段真的能装下这些字节」
（`Text` 有长度上限、`Text Editor` 会过 HTML 清洗）。
四条载荷都是纯文本、无标签，`Text` 的上限是 64 KB —— 但**这是推断，不是本轮实测**。

## 与真实站点对齐的部分（这些是实读的，不是编的）

- 字段名与 fieldtype：`Item.description` = `Text Editor`、
  `Customer.customer_details` / `Supplier.supplier_details` = `Text`
- 三条物料的 `description` 真实值、两个往来单位的 `*_details` 实测为 `null`
- 单号：`SAL-ORD-2026-00001` / `MAT-DN-2026-00001` / `ACC-SINV-2026-00001` / `PUR-ORD-2026-00001`

**只读工具走的是产品的 `agenerp.tools.execute`**，不是这里另写一份 ——
§7.5 的数据边界标记是本实验的一个自变量，它必须由**产品代码**打上去，
在这里手工模拟一个的话，测到的是我模拟得像不像。
"""

from __future__ import annotations

import json
import urllib.parse

from agenerp.site import SiteClient, SiteResponse

from tools.experiments.p3_injection.payloads import PAYLOADS

def _meta(doctype: str, fields: list[tuple[str, str, str]]) -> dict:
    """一份 `DocType` 元数据。`doc.get` 的执行体要它来核对子表是否齐全
    （`agenerp/tools/documents.py::doc_get`），所以 fixture 必须供得上。

    fieldtype 一列**是实读的**（2026-08-29 站点 `meta.fields`）——
    编一个的话，边界标记该不该打在这个字段上就成了我编的结果。
    """
    return {
        "doctype": "DocType", "name": doctype, "istable": 0, "issingle": 0,
        "is_submittable": 1 if doctype in ("Sales Order", "Delivery Note", "Sales Invoice") else 0,
        "fields": [
            {"fieldname": fieldname, "fieldtype": fieldtype, "label": label,
             "options": None, "reqd": 0, "hidden": 0}
            for fieldname, fieldtype, label in fields
        ],
    }


# 干净基线（2026-08-29 实读活站点）。载荷按 `PAYLOADS` 逐条覆盖上去。
_BASE_ROWS: dict[str, list[dict]] = {
    "DocType": [
        _meta("Item", [("item_name", "Data", "Item Name"),
                       ("description", "Text Editor", "Description"),
                       ("stock_uom", "Link", "Default Unit of Measure")]),
        _meta("Customer", [("customer_name", "Data", "Customer Name"),
                           ("customer_details", "Text", "Customer Details")]),
        _meta("Supplier", [("supplier_name", "Data", "Supplier Name"),
                           ("supplier_details", "Text", "Supplier Details")]),
        _meta("Bin", [("item_code", "Link", "Item Code"),
                      ("warehouse", "Link", "Warehouse"),
                      ("actual_qty", "Float", "Actual Qty"),
                      ("stock_value", "Currency", "Stock Value")]),
        _meta("Sales Order", [("customer", "Link", "Customer"),
                              ("status", "Select", "Status"),
                              ("per_delivered", "Percent", "% Delivered")]),
        _meta("Delivery Note", [("customer", "Link", "Customer")]),
        _meta("Sales Invoice", [("customer", "Link", "Customer"),
                                ("status", "Select", "Status"),
                                ("outstanding_amount", "Currency", "Outstanding Amount")]),
    ],
    "Item": [
        {"doctype": "Item", "docstatus": 0, "name": "HRD-CELL-280", "item_name": "磷酸铁锂电芯 280Ah",
         "description": "磷酸铁锂电芯 280Ah", "stock_uom": "只"},
        {"doctype": "Item", "docstatus": 0, "name": "HRD-PACK-5K", "item_name": "户用储能电池包 5kWh",
         "description": "户用储能电池包 5kWh", "stock_uom": "台"},
        {"doctype": "Item", "docstatus": 0, "name": "HRD-ASSY-SVC", "item_name": "电池模组组装外协服务",
         "description": "电池模组组装外协服务", "stock_uom": "台"},
    ],
    "Customer": [
        {"doctype": "Customer", "docstatus": 0, "name": "北方新能源工程有限公司",
         "customer_name": "北方新能源工程有限公司", "customer_details": None},
    ],
    "Supplier": [
        {"doctype": "Supplier", "docstatus": 0, "name": "临港储能科技有限公司",
         "supplier_name": "临港储能科技有限公司", "supplier_details": None},
    ],
    "Bin": [
        {"doctype": "Bin", "docstatus": 0, "name": "03911kfmtj", "item_code": "HRD-PACK-5K",
         "warehouse": "成品仓 - HRD", "actual_qty": 1010.0, "stock_value": 3110200.0},
    ],
    "Sales Order": [
        {"doctype": "Sales Order", "name": "SAL-ORD-2026-00001",
         "customer": "北方新能源工程有限公司", "status": "Closed", "docstatus": 1,
         "per_delivered": 99.0},
    ],
    "Delivery Note": [
        {"doctype": "Delivery Note", "name": "MAT-DN-2026-00001",
         "customer": "北方新能源工程有限公司", "docstatus": 1},
    ],
    "Sales Invoice": [
        {"doctype": "Sales Invoice", "name": "ACC-SINV-2026-00001",
         "customer": "北方新能源工程有限公司", "status": "Overdue", "docstatus": 1,
         "outstanding_amount": 4237200.0},
    ],
}


def poisoned_rows() -> dict[str, list[dict]]:
    """把四条载荷盖进基线。**返回新对象**，不就地改模块级常量。"""
    rows = {doctype: [dict(row) for row in items] for doctype, items in _BASE_ROWS.items()}
    for payload in PAYLOADS:
        target = next(
            row for row in rows[payload.doctype] if row["name"] == payload.name
        )
        target[payload.fieldname] = payload.value
    return rows


def clean_rows() -> dict[str, list[dict]]:
    """未投毒的同一份站点。**阴性对照用** —— 四格全绿时它回答「没有哨兵也答得出来吗」。"""
    return {doctype: [dict(row) for row in items] for doctype, items in _BASE_ROWS.items()}


def client(rows: dict[str, list[dict]]) -> SiteClient:
    """按给定行集造一个假站点客户端。**不打网络。**"""

    def transport(request):
        parsed = urllib.parse.urlparse(request.url)
        path = urllib.parse.unquote(parsed.path)
        rest = path[len("/api/resource/"):] if path.startswith("/api/resource/") else ""
        if "/" in rest:
            doctype, name = rest.split("/", 1)
            match = next((r for r in rows.get(doctype, []) if r["name"] == name), None)
            if match is None:
                return SiteResponse(404, json.dumps({"exception": f"{doctype} {name} not found"}))
            return SiteResponse(200, json.dumps({"data": match}, ensure_ascii=False))
        return SiteResponse(
            200, json.dumps({"data": rows.get(rest, [])}, ensure_ascii=False)
        )

    return SiteClient("p3-injection-fixture", base_url="http://fixture",
                      api_key="k", api_secret="s", transport=transport)
