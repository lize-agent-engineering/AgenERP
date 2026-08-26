# `doc.links` 子表分支补守卫 —— 活站点回归证据

plan：`docs/plans/p1-insight/2026-08-26-1618-1-doc-links-child-host-guard.md`
落点节：`docs/architecture/module-boundaries.md` §7.24

## 这里的证据证的是什么，不证什么

⚠️ 本目录的两跑证的是「**没弄坏正常路径**」，**不是**「守卫生效」。
守卫生效由 `tests/unit/test_doc_links_skips_singles.py` 的五条判据
与 plan Phase 2 的变异表 M1–M6 证明，**两者不得互相冒充**。

## 改动前 / 改动后各一跑（逐字节相同的脚本与 env）

- 改动前：基线 sha `8dcc9ac`，`git status --porcelain` **空输出**（干净树），`agenerp/**` 一个字节未改
- 改动后：本 plan Phase 1–2 的改动已在树上

脚本（`/tmp/doclinks_probe.py`，仓内零施加，跑完即删）：

```python
import json
from agenerp.site import client_from_env
from agenerp.tools.runtime import execute
from agenerp.contracts import ReadOnlyContext
ctx = ReadOnlyContext({"doc_links_called_for": [], "documents_named_in_question": [], "doc_get_called_for": []})
out = execute("doc.links", {"doctype": "Item", "name": "HRD-PACK-5K"},
              client=client_from_env("frontend"), context=ctx)
rows = out.data or []
print("ok=", out.ok, "rows=", len(rows))
print(json.dumps(rows, ensure_ascii=False, sort_keys=True))
```

命令原文：

```sh
AGENERP_HTTP_PORT=18080 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin PYTHONPATH=. python3 /tmp/doclinks_probe.py | tail -1 | shasum -a 256
```

| 跑次 | 树状态 | 第一行 | 规范化 JSON 的 `sha256` |
|---|---|---|---|
| 改动前 | `8dcc9ac` 干净树 | `ok= True rows= 14` | `203db3f89a095aa19b6c684f4a808137c63cf9ef33cc74f575a766970e668bd1` |
| 改动后 | Phase 1–2 已落树 | `ok= True rows= 14` | `203db3f89a095aa19b6c684f4a808137c63cf9ef33cc74f575a766970e668bd1` |

**逐字对照结果：行数相同（14 = 14）、`sha256` 逐字节相同** ⇒ 正常路径一个字未变，
与 plan 的 Non-Goal 4 与 H6 一致。起草期在 `7302ebe` 上取得的那个值也是同一个 `sha256`
（`203db3f8…e668bd1`），三跑同值。

## 活体门禁 `tests/gates/test_tool_execution_live.py` 改动前后各一跑

命令原文（**只读复跑，`tests/gates/**` 一个字节未动**，红线 1）：

```sh
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \
  AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \
  python3 -m pytest tests/gates/test_tool_execution_live.py -q
```

| 跑次 | 退出码 | 汇总 | 唯一的红 |
|---|---|---|---|
| 改动前（`8dcc9ac` 干净树） | **1** | `1 failed, 11 passed in 5.68s` | `test_permission_scope_produces_at_least_one_real_negative` |
| 改动后 | **1** | `1 failed, 11 passed in 5.59s` | 同上，逐字同一条 |

**两跑的红完全一致**，红因逐字是：

```
E   Failed: 受限身份口令未设（AGENERP_WORKER_PASSWORD），本条判据无法执行。
E       装载受限身份：python3 -m agenerp.seedusers --site frontend
```

⇒ 这是**环境缺一个受限身份口令**，与 `doc.links` 无关；它在改动**之前就红**。
本 plan 真正要看的那条参数化断言，两跑逐字都是 **PASSED**：

```
tests/gates/test_tool_execution_live.py::test_every_tool_returns_a_shape_its_contract_allows[doc.links] PASSED
tests/gates/test_tool_execution_live.py::test_every_tool_returns_a_shape_its_contract_allows[lineage.trace] PASSED
```

改动前该行 PASSED，改动后仍 PASSED ⇒ **`doc.links` / `lineage.trace` 的活体裁判没有回归**。

⚠️ **H8 未命中，照实记**：H8 预测「改动前后都是 exit 0」，实测**两跑都是 exit 1**。
这是一条与本 plan 无关的既有事实（受限身份未装载），**不因此认定本 plan 无责** ——
本 plan 的无责由「同一条红、改动前后逐字相同」与「`[doc.links]` 两跑都 PASSED」证明，
不由退出码本身证明。**未为让它转绿而动 `tests/gates/**` 任何一个字节**（红线 1）。
装载受限身份不在本 plan 的范围内，已登记交人（见 plan 的 `Deferred But Adjudicated`）。
