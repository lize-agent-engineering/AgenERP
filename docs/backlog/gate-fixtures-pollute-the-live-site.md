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
