"""工具执行层判据的假站点 —— 一个够小、但**行为与 Frappe REST 面同形**的替身。

为什么不连真站点：`agenerp/site.py` 的 `Transport` 协议就是为这个接缝准备的。
单测在无凭据、无 docker 的环境里必须全绿，否则判据会红在环境上而不是红在实现上。

假站点只实现执行体真正用到的四条路径，**不多实现一条**：

- `GET /api/resource/<DocType>` —— 列表，支持 `filters` / `fields` / `parent`
- `GET /api/resource/<DocType>/<name>` —— 单文档（含子表）
- `POST /api/resource/<DocType>` —— 建档（受限身份装载器的幂等判据要用）
- `POST /api/method/frappe.client.get_count`
- `POST /api/method/frappe.client.has_permission`

**它不做权限判定**：`has_permission` 的答案由夹具直接给定。判据要验的是
「执行体逐个探了没有」，不是「Frappe 的权限引擎算得对不对」——后者不是本仓的东西。
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import pytest

from agenerp.site import SiteClient, SiteRequest, SiteResponse


@dataclass
class FakeSite:
    """一个假站点：DocType 元数据 + 行数据 + 权限答案。请求逐条留痕。"""

    doctypes: dict[str, dict] = field(default_factory=dict)
    rows: dict[str, list[dict]] = field(default_factory=dict)
    permissions: dict[str, bool] = field(default_factory=dict)
    forbidden: set[str] = field(default_factory=set)
    requests: list[SiteRequest] = field(default_factory=list)

    def __call__(self, request: SiteRequest) -> SiteResponse:
        self.requests.append(request)
        parsed = urllib.parse.urlparse(request.url)
        path = urllib.parse.unquote(parsed.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        if path.startswith("/api/method/"):
            return self._method(path.rsplit("/", 1)[-1], json.loads(request.body or b"{}"))
        if path.startswith("/api/resource/"):
            tail = path[len("/api/resource/") :]
            if request.method == "POST":
                return self._create(tail, json.loads(request.body or b"{}"))
            return self._resource(tail, params)
        return SiteResponse(404, json.dumps({"exception": f"未实现的路径 {path}"}))

    # ── 路径实现 ────────────────────────────────────────────────────────────
    def _method(self, name: str, body: dict) -> SiteResponse:
        doctype = body.get("doctype", "")
        if name == "frappe.client.get_count":
            if doctype in self.forbidden:
                return self._denied(doctype)
            return SiteResponse(200, json.dumps({"message": len(self.rows.get(doctype, []))}))
        if name == "frappe.client.has_permission":
            allowed = self.permissions.get(doctype, doctype not in self.forbidden)
            return SiteResponse(200, json.dumps({"message": {"has_permission": allowed}}))
        return SiteResponse(404, json.dumps({"exception": f"未实现的方法 {name}"}))

    def _resource(self, tail: str, params: dict[str, str]) -> SiteResponse:
        parts = tail.split("/", 1)
        doctype = parts[0]
        if doctype in self.forbidden:
            return self._denied(doctype)
        if len(parts) == 2:
            for row in self.rows.get(doctype, []):
                if row.get("name") == parts[1]:
                    return SiteResponse(200, json.dumps({"data": row}, ensure_ascii=False))
            if doctype == "DocType" and parts[1] in self.doctypes:
                return SiteResponse(
                    200, json.dumps({"data": self._doctype_doc(parts[1])}, ensure_ascii=False)
                )
            return SiteResponse(404, json.dumps({"exception": f"{doctype} {parts[1]} 不存在"}))
        rows = self._rows_of(doctype)
        rows = [row for row in rows if _matches(row, json.loads(params.get("filters", "[]")))]
        fields = json.loads(params.get("fields", '["*"]'))
        if fields != ["*"]:
            rows = [{key: row.get(key) for key in fields} for row in rows]
        return SiteResponse(200, json.dumps({"data": rows}, ensure_ascii=False))

    def _create(self, doctype: str, payload: dict) -> SiteResponse:
        """建档。名字**由站点说了算**：载荷没给 `name` 时按序号派生，与真站点同形。"""
        rows = self.rows.setdefault(doctype, [])
        name = payload.get("name") or payload.get("email") or f"{doctype}-{len(rows) + 1:04d}"
        row = {**payload, "name": name, "doctype": doctype}
        rows.append(row)
        return SiteResponse(200, json.dumps({"data": row}, ensure_ascii=False))

    def _rows_of(self, doctype: str) -> list[dict]:
        if doctype == "DocType":
            return [{"name": name, **meta} for name, meta in self.doctypes.items()]
        if doctype == "DocField":
            return self._docfields()
        return self.rows.get(doctype, [])

    def _docfields(self) -> list[dict]:
        return [
            {"parent": owner, **{k: v for k, v in dict(field).items() if k != "parent"}}
            for owner, meta in self.doctypes.items()
            for field in meta.get("fields", [])
        ]

    def _doctype_doc(self, name: str) -> dict:
        meta = self.doctypes[name]
        return {"name": name, "doctype": "DocType", **meta}

    def _denied(self, doctype: str) -> SiteResponse:
        return SiteResponse(
            403, json.dumps({"exception": f"frappe.exceptions.PermissionError: {doctype}"})
        )


def _matches(row: dict, filters: list) -> bool:
    for entry in filters:
        if len(entry) != 3:
            return False
        fieldname, operator, value = entry
        actual = row.get(fieldname)
        if operator == "=" and actual != value:
            return False
        if operator == "in" and actual not in value:
            return False
    return True


def client_for(site: FakeSite) -> SiteClient:
    """假站点的客户端。给 token 是为了跳过登录那一跳——它不是被测对象。"""
    return SiteClient(
        "fake", base_url="http://fake", api_key="k", api_secret="s", transport=site
    )


def doctype(**kwargs: Any) -> dict:
    """一份 DocType 元数据，默认值取 Frappe 的默认值（实体表、不可提交、非虚拟）。"""
    meta = {
        "module": "Selling",
        "istable": 0,
        "issingle": 0,
        "is_virtual": 0,
        "is_submittable": 0,
        "fields": [],
    }
    meta.update(kwargs)
    return meta


@pytest.fixture
def fake_client(fake_site: FakeSite) -> SiteClient:
    """跟 `fake_site` 同一实例的客户端。判据用它，避免测试文件之间互相 import。"""
    return client_for(fake_site)


@pytest.fixture
def fake_site() -> FakeSite:
    """一张销售订单 + 一张发货单（子表指回订单）+ 一张已取消的下游，够验完血缘三条硬约束。"""
    return FakeSite(
        doctypes={
            "Sales Order": doctype(
                is_submittable=1,
                fields=[
                    {"fieldname": "customer", "fieldtype": "Link", "options": "Customer",
                     "label": "客户", "in_list_view": 1},
                    {"fieldname": "notes", "fieldtype": "Small Text", "label": "备注"},
                    {"fieldname": "layout", "fieldtype": "Section Break", "label": None},
                    {"fieldname": "items", "fieldtype": "Table",
                     "options": "Sales Order Item", "label": "明细"},
                ],
            ),
            "Sales Order Item": doctype(istable=1, fields=[
                {"fieldname": "item_code", "fieldtype": "Data", "label": "物料"},
            ]),
            "Delivery Note": doctype(is_submittable=1, fields=[
                {"fieldname": "items", "fieldtype": "Table",
                 "options": "Delivery Note Item", "label": "明细"},
            ]),
            "Delivery Note Item": doctype(istable=1, fields=[
                {"fieldname": "against_sales_order", "fieldtype": "Link",
                 "options": "Sales Order", "label": "对应订单"},
            ]),
            "Work Order": doctype(module="Manufacturing", is_submittable=1, fields=[
                {"fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order",
                 "label": "销售订单"},
            ]),
            "Customer": doctype(fields=[]),
            "Company": doctype(module="Setup", fields=[]),
            "GL Entry": doctype(module="Accounts", fields=[]),
            "Token Cache": doctype(module="Core", fields=[]),
            "Bulk Transaction Log": doctype(module="Bulk Transaction", is_virtual=1, fields=[]),
        },
        rows={
            "Module Def": [
                {"name": "Selling", "app_name": "erpnext"},
                {"name": "Manufacturing", "app_name": "erpnext"},
                {"name": "Setup", "app_name": "erpnext"},
                {"name": "Accounts", "app_name": "erpnext"},
                {"name": "Bulk Transaction", "app_name": "erpnext"},
                {"name": "Core", "app_name": "frappe"},
            ],
            "Company": [{"name": "恒锐动力科技有限公司", "doctype": "Company"}],
            "GL Entry": [
                {"name": "GL-1", "posting_date": "2026-02-02", "docstatus": 1},
                {"name": "GL-2", "posting_date": "2026-02-08", "docstatus": 1},
            ],
            "Sales Order": [
                {
                    "name": "SAL-ORD-2026-00001",
                    "doctype": "Sales Order",
                    "docstatus": 1,
                    "customer": "北方新能源工程有限公司",
                    "notes": "客户要求分批发货",
                    "modified": "2026-02-08 10:00:00",
                    "creation": "2026-02-01 09:00:00",
                    "owner": "Administrator",
                    "_comments": "[]",
                    "idx": 0,
                    "items": [
                        {"name": "soi-1", "item_code": "HRD-PACK-5K", "qty": 1000,
                         "modified": "2026-02-08 10:00:00"}
                    ],
                }
            ],
            "Delivery Note": [
                {"name": "MAT-DN-2026-00001", "doctype": "Delivery Note", "docstatus": 1},
                {"name": "MAT-DN-2026-00002", "doctype": "Delivery Note", "docstatus": 2},
            ],
            "Delivery Note Item": [
                {"name": "dni-1", "parent": "MAT-DN-2026-00001", "parenttype": "Delivery Note",
                 "against_sales_order": "SAL-ORD-2026-00001"},
                {"name": "dni-2", "parent": "MAT-DN-2026-00002", "parenttype": "Delivery Note",
                 "against_sales_order": "SAL-ORD-2026-00001"},
            ],
            "Work Order": [
                {"name": "MFG-WO-2026-00001", "doctype": "Work Order", "docstatus": 0,
                 "sales_order": "SAL-ORD-2026-00001"},
            ],
            "Custom Field": [
                {"name": "Item-hrd_line", "dt": "Item", "fieldname": "hrd_line",
                 "fieldtype": "Data", "modified": "2026-02-08 10:00:00"},
            ],
        },
    )
