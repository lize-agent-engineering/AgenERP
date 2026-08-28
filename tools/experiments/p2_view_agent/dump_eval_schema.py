"""P2.3 Phase 4 · 导出评测用的 schema。**实验设施，不是产品代码。**

与 `agenerp/schema_snapshot.py` 的区别只有一个：**覆盖面**。
产品快照只收车间工人那 8 张表（P2.2 路线 C 的分母），
而评测集有一个**域外子集**，问的正是快照之外的单据 ——
拿产品快照去评域外，每一条都会被 L2 判成「DocType 不存在」，
量出来的是快照的覆盖面，不是视图 Agent 的能力。

标准字段照 `schema_snapshot.STANDARD_FIELDS` 补 —— 口径必须与产品一致，
否则评测里 `count(name)` 过得了、生产上过不了。

    set -a; . ~/.config/agenerp/secrets.env; set +a
    export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
           AGENERP_ADMIN_PASSWORD=admin
    python3 tools/experiments/p2_view_agent/dump_eval_schema.py
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from agenerp.schema_snapshot import STANDARD_FIELDS  # noqa: E402
from agenerp.site import client_from_env  # noqa: E402

# 主集：车间工人真实可读的三张表（`agenerp/seedusers.py` 建的受限身份）+ 它们的子表。
IN_DOMAIN = ("Work Order", "Work Order Item", "Work Order Operation",
             "Stock Entry", "Stock Entry Detail", "Item")
# 域外：销售/采购侧，工人看不到，也不在产品快照里。
OUT_OF_DOMAIN = ("Sales Order", "Sales Order Item", "Quotation", "Purchase Order",
                 "Purchase Order Item", "Customer", "Supplier", "Delivery Note")

OUT = pathlib.Path(__file__).parent / "eval-schema.json"


def main() -> None:
    client = client_from_env("frontend")
    rows: list[dict] = []
    covered: list[str] = []
    for doctype in IN_DOMAIN + OUT_OF_DOMAIN:
        meta = client.get(f"/api/resource/DocType/{doctype}")
        fields = (meta.get("data") or {}).get("fields") or []
        if not fields:
            print(f"⚠️ {doctype} 一个字段都没取到，跳过")
            continue
        covered.append(doctype)
        for row in fields:
            if not row.get("fieldname"):
                continue
            rows.append({
                "doctype": doctype,
                "fieldname": row.get("fieldname"),
                "fieldtype": row.get("fieldtype"),
                "options": row.get("options"),
            })
    present = {(r["doctype"], r["fieldname"]) for r in rows}
    rows += [
        {"doctype": d, "fieldname": f, "fieldtype": ft, "options": None}
        for d in covered for f, ft in STANDARD_FIELDS.items() if (d, f) not in present
    ]
    OUT.write_text(json.dumps({
        "provenance": {
            "site": "frontend",
            "generated_by": "tools/experiments/p2_view_agent/dump_eval_schema.py",
            "generated_on": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d"),
        },
        "in_domain": [d for d in IN_DOMAIN if d in covered],
        "out_of_domain": [d for d in OUT_OF_DOMAIN if d in covered],
        "fields": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {OUT}（{len(covered)} 个 DocType，{len(rows)} 个字段）")


if __name__ == "__main__":
    main()
