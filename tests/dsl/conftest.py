"""P2.1 · 测试用的 schema 视图。

🔴 **这份 schema 不是我编的，是从活站点实读导出的。**

`fixtures/site-schema-subset.json` 由
`tools/experiments/p2_schema_retrieval/dump_schema.py` 在站点 `frontend`
（frappe 15.118.0 / erpnext 15.119.3）上导出后按 DocType 取的子集，
文件里带 `provenance` 段。

理由：`p2-views-roadmap.md` 硬约束 ④ 要求产出指回真实字段，而
**拿一份手写的 schema 去测「字段存在性」，测的是我编得对不对，不是校验器对不对。**
`test_fixture_schema_is_real.py` 守着这份文件的真实性与自洽。

复跑（要有活站点）：

    docker cp tools/experiments/p2_schema_retrieval/dump_schema.py agenerp-backend-1:/tmp/
    docker exec -w /home/frappe/frappe-bench/sites agenerp-backend-1 \\
        ../env/bin/python /tmp/dump_schema.py frontend > /tmp/schema.json
"""

from __future__ import annotations

import json
import pathlib

import pytest

from agenerp.dsl.schema import SchemaView

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "site-schema-subset.json"
CHILD_TABLES_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "child-tables.json"

_RAW = json.loads(FIXTURE.read_text(encoding="utf-8"))
SALES_FIELDS: dict[str, dict[str, str]] = _RAW["fields"]
PROVENANCE: dict[str, str] = _RAW["provenance"]

# `"父.字段" -> 子表 DocType`，同样由 `dump_schema.py` 从活站点导出，**不手写**。
_CHILD_RAW: dict[str, str] = json.loads(CHILD_TABLES_FIXTURE.read_text(encoding="utf-8"))
CHILD_TABLES: dict[tuple[str, str], str] = {
    (key.split(".", 1)[0], key.split(".", 1)[1]): child for key, child in _CHILD_RAW.items()
}


@pytest.fixture
def schema() -> SchemaView:
    return SchemaView(SALES_FIELDS, CHILD_TABLES)
