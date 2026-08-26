#!/usr/bin/env python3
"""P2.0R · 把活站点的 schema 导成 JSON（只读）。

在 frappe 容器里跑：
    docker cp dump_schema.py agenerp-backend-1:/tmp/
    docker exec -w /home/frappe/frappe-bench/sites agenerp-backend-1 \
        ../env/bin/python /tmp/dump_schema.py > schema.json

口径**逐条对齐 Spike 07**（`${XM}/spike/07-schema-retrieval/`），否则新旧数不可比：
  - 业务 app = 非 frappe 的 app（本站点即 erpnext + agenerp）
  - 剔除 Single（没有表，谈不上「有没有数据」）
  - 剔除布局类 fieldtype（分节符、分栏符等，不是可检索的元知识）
  - rowcount 直接 count(*)，「有数据」= rowcount > 0
"""

import json
import sys

import frappe

LAYOUT = {
    "Section Break",
    "Column Break",
    "Tab Break",
    "HTML",
    "Heading",
    "Fold",
    "Button",
    "Image",
}


def main(site: str) -> None:
    frappe.init(site=site)
    frappe.connect()

    # module → app，用来判「是不是业务 app」。比硬编码模块名单可靠：
    # 站点装了什么 app 是活事实，而模块名单会随 Frappe 版本漂。
    module_app = {
        row.name: row.app_name
        for row in frappe.get_all("Module Def", fields=["name", "app_name"], limit_page_length=0)
    }

    out = []
    doctypes = frappe.get_all(
        "DocType",
        fields=["name", "module", "istable", "issingle"],
        limit_page_length=0,
    )

    for dt in doctypes:
        if dt.issingle:
            continue
        app = module_app.get(dt.module, "")
        if app == "frappe" or not app:
            continue
        try:
            rowcount = frappe.db.count(dt.name)
        except Exception:
            continue
        meta = frappe.get_meta(dt.name)
        for f in meta.fields:
            if f.fieldtype in LAYOUT:
                continue
            out.append(
                {
                    "doctype": dt.name,
                    "module": dt.module,
                    "app": app,
                    "istable": int(dt.istable or 0),
                    "rowcount": rowcount,
                    "fieldname": f.fieldname,
                    "label": f.label or "",
                    "fieldtype": f.fieldtype,
                    "options": (f.options or "").strip(),
                }
            )

    json.dump({"site": site, "fields": out}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "frontend")
