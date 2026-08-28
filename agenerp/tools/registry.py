"""契约 ↔ 执行体的注册表。**双向**：每条契约都要有执行体，每个执行体都要有契约。

少一边就是一个静默缺口：加了工具忘了契约 → 它绕过前置/裁剪/后置整层；
加了契约忘了执行体 → 控制循环调它时才在运行期炸。
判据是 `tests/tools/test_registry_pairing.py`，人为删一条就红。
"""

from __future__ import annotations

from agenerp.tools.documents import doc_get, doc_links, lineage_trace, meta_fields
from agenerp.tools.drift import schema_drift_scan
from agenerp.tools.queries import query_read, rule_lookup, snapshot_read
from agenerp.tools.runtime import Executor
from agenerp.tools.site_scope import permission_scope, schema_search, system_overview

EXECUTORS: dict[str, Executor] = {
    "query.read": query_read,
    "schema.search": schema_search,
    "snapshot.read": snapshot_read,
    "lineage.trace": lineage_trace,
    "rule.lookup": rule_lookup,
    "system.overview": system_overview,
    "permission.scope": permission_scope,
    "doc.get": doc_get,
    "doc.links": doc_links,
    "meta.fields": meta_fields,
    # 巡检族（P2.5）。**不在模型工具面上** —— `tool_schemas()` 按 `READONLY_CONTRACTS`
    # 生成，而它的契约在 `INSPECTION_CONTRACTS` 里。见 `tools_readonly.py` 那一段。
    "schema.drift": schema_drift_scan,
}
