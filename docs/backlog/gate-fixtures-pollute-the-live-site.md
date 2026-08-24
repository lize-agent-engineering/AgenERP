# 门禁自己在污染站点 —— 每轮跑完在活站点上留一条孤儿列

> Status: `deferred`（**登记，不处置**；处置需要人）
> Created: 2026-08-21
> 由 plan `docs/plans/p0-foundation/2026-08-21-2220-1-schema-drift-orphan-columns.md` 的 Phase 3 产出
> 处置者：**人**（改动落在 `tests/gates/conftest.py`，`AGENTS.md` 红线 1，loop 一个字节都不许改）

## 事实（2026-08-21 活站点实测）

`tests/gates/conftest.py` 的 `live_site` fixture 在 teardown 时删掉探针 Custom Field，
但 **Frappe 删 Custom Field 不删物理列**（Spike 06 的结论在 v15.119.3 上复验仍成立）。
所以门禁**每跑一轮就在站点上留一条孤儿列**。

开工时 `tabItem` 上已积了 6 条 `agenerp%` 列，来源分两类，**不含糊**：

| 列 | 来源 |
|---|---|
| `agenerp_gate_roundtrip` | `test_customization_roundtrip_delete.py` 的 `PROBE_FIELD`，**门禁自己留的** |
| `agenerp_gate_probe` | `test_snapshot_diff_structured.py` 的探针，**门禁自己留的** |
| `agenerp_explore_probe` / `agenerp_explore_probe2` / `agenerp_scope_probe_item` | 历轮人工探查留下的 |
| `agenerp_probe_orphan` | 本 plan 起草时做可行性实测留下的 |

**此前没有任何文档记过这件事。**

## 现状：已止血一半，另一半没有

plan `2026-08-21-2220-1` 的清除面让 `apply_pack` 在删完 Custom Field 之后清掉
**本次 apply 自己造成**的残列。所以走 `apply_pack` 这条路的探针（`agenerp_gate_roundtrip`）
现在会被清掉——实测门禁跑完那一轮它从 `schema_drift("Item")` 里消失了。

**没被覆盖的是另一类**：`test_snapshot_diff_structured.py` 的 `agenerp_gate_probe` 由
`live_site` fixture 直接建、直接删，**根本不经过 `apply_pack`**，因此它的列仍然每轮累积。
清除面管不到它——那不是 apply 的意图，让 apply 顺手清掉它正是本 plan 明文排除的作用域。

## 触发条件（按 Anti-Slacking Rule 必须写明，不是「以后有空再说」）

**当 CI 真的开始跑 L2 时** —— 即 plan `docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md`
的 CI 阶段（工作项 8）落地。届时残留会**随每次 CI 累积**，必须处置。

在那之前不处置的理由：本机站点上多几条孤儿列不影响任何判据（`schema_drift` 如实报它们，
清除面按交集收窄、不碰它们），而唯一的修法在红线 1 内。

### 2026-08-21 补记：触发**已经发生**，但上面那句「随每次 CI 累积」被实测证伪

plan `2026-08-21-2220-2` 的 CI 阶段已落地，`gates-l2` job 在 run `32499273158`（sha `ad42e91`）
上真跑过一次 L2，结论 `success`。所以「当 CI 真的开始跑 L2 时」这个触发条件**已满足**。

但它预告的那个后果**不成立**，本行照实更正（确认的文档漂移，不降级）：

1. **CI 站点是一次性的。** `gates-l2` job 的收尾步骤是 `docker compose down -v`（`if: always()`，
   无条件执行），实测把五个卷与网络全部 `Removed`。下一次 CI 是一个全新站点，**没有任何东西可累积**。
2. **CI 上的 L2 只跑 `tests/gates/test_zero_dep_boot.py` 三条。** 那三条只取 `compose_stack`，
   **不取 `live_site`**，一条 Custom Field 都不建——即使站点是常驻的，这条路径也不产生孤儿列。

因此本条**回到 watch-only**，不再由「CI 开始跑 L2」触发。**新的触发条件**：
**当 CI 的 L2 覆盖面扩到 `test_snapshot_diff_structured.py` 或 `test_customization_roundtrip_delete.py` 时**
（那两个文件才取 `live_site`），或**当 CI 的 L2 站点不再是一次性的**（收尾从 `down -v` 改成保留卷）时。
在此之前，唯一受影响的仍然只有本机常驻站点，处置手段见文末那条 `trim-tables`。

### 2026-08-22 补记：新触发条件**已满足**，裁定结果是**维持 watch-only**，触发条件再改绑一次

2026-08-21 那次补记写下的新触发条件逐字是「**当 CI 的 L2 覆盖面扩到
`test_snapshot_diff_structured.py` 或 `test_customization_roundtrip_delete.py` 时**⋯
或**当 CI 的 L2 站点不再是一次性的**时」。

**前者已经发生**：plan `docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`
的新 job `gates-l2-live` 在 CI 上跑**整目录 19 条**，两个文件都在覆盖面里
（run `32509351108`，PR #1，head `2ef7cdc`）。**必须给结论，本节就是结论。**

**待核的两个事实，按 CI 实跑日志核对过，不是推理**：

1. **新 job 的收尾仍是 `down -v`，且 `if: always()`。** 实测 attempt 2 的「拆栈（无条件）」步骤逐字打出
   12 个容器 `Removed`、**5 个卷全部 `Removed`**（`agenerp_sites` / `agenerp_db-data` / `agenerp_logs` /
   `agenerp_redis-queue-data` / `agenerp_redis-cache-data`）、`Network agenerp_default Removed`。
   ⚠️ 这一跑的判定步骤是**红**的，拆栈仍然执行了——`if: always()` 在失败路径上实测生效。
2. **CI 站点仍是一次性的。** 卷被删干净，下一次 CI 是全新站点。

**因此裁定：维持 `watch-only`。** 残留仍**不累积**——即使门禁在 CI 上每轮都建探针 Custom Field，
那些物理列随卷一起消失。唯一受影响的仍然只有**本机常驻站点**，处置手段见文末那条 `trim-tables`。

**触发条件按新事实就地再改绑一次**（照 2026-08-21 那次的写法，不新开条目）：
**当 CI 的 L2 站点不再是一次性的时**（收尾从 `down -v` 改成保留卷，或改用常驻 runner / 外部站点）。
「覆盖面扩到那两个文件」这一条**已经用掉了，不再是触发条件**。

**⚠️ 一条必须点名的相邻事实，别把它和本条混为一谈**：那次 CI 实跑里
`test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind` **两次 attempt 都红**
（可复现）。**那不是站点污染问题**——CI 站点是全新的，没有任何历史孤儿列可污染。
它是 `apply_pack` 物理列清除面的**实现问题**，归 `docs/masterplan/STATE.md` §3 的 2026-08-22 `[open]` 行
与它指名的 successor plan。本条**不承接它**，也不因它改变裁定。

## 可选处置（loop 不替人选）

- **(a)** 人带 `Gates-Change-Approved-By:` trailer 改 `tests/gates/conftest.py` 的 `live_site` teardown，
  让它在删完 Custom Field 之后也清掉物理列（可复用 `agenerp.oob.drop_columns`）。
  **代价**：门禁开始依赖 `agenerp/` 的实现来做自己的清理——裁判用了被裁判者的代码。
- **(b)** 在 CI 的 L2 job 收尾处跑一次 `bench --site frontend trim-tables`，
  把清理放在 harness 之外。**代价**：`.github/workflows/**` 是红线 2 的关注面，且它一次删光
  该站点上**所有**孤儿列——在一次性 CI 站点上这没问题，在本机常驻站点上会删掉观测对象。
- **(c)** 维持现状，接受 CI 站点上的累积。**代价**：CI 站点若不是一次性的，`tabItem` 会越来越宽。

## 现在就能做的（不需要人，也不碰红线）

本机站点随时可由人自行清理：`docker compose exec -T backend bench --site frontend trim-tables`。
