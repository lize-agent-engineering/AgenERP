# P0 · 地基 — mission roadmap

> Last updated: 2026-08-21
> Sources: [`docs/backlog/implementation-roadmap.md`](./implementation-roadmap.md) 的 P0 节（判据的真相源）·
> [`tests/gates/`](../../tests/gates/README.md)（判据的可执行形式）

## Purpose

这是 **`p0-foundation` mission 自己的 roadmap**，由引擎在 closure 审计通过后回写。
全局阶段索引（P0–P5 谁做完了）在 [`implementation-roadmap.md`](./implementation-roadmap.md)，由人维护——**两者别搞混**。

P0 的目标一句话：**把「可验证」做出来。这一阶段不引入任何 LLM。**
每个工作项都绑定一条**先红着**的门禁测试；工作项关闭 = 那条测试转绿 + 从 `tools/gates/expected-red.txt` 划掉。

## Work Item Status

> **这是唯一的动态状态块。** 状态只在这里改。
> 顺序即执行顺序，引擎取第一个 `todo`。前三项是纯逻辑，不需要活站点或 docker，先做。

- 1. 定制包规范化器（剥易变字段 + 稳定排序）: `done`
- 2. 状态快照与结构化 diff: `done`
- 3. 零依赖启动（compose 语法 + 首页 AI 未配置降级）: `done`
- 4. 工具契约层 v0（先包 10 个只读工具）: `planned`
- 5. 差集 apply 引擎（读包 → 求差 → **对差集执行删除**）: `planned`
- 6. 定制包往返删除验证（活站点端到端）: `planned`
- 7. 种子数据（确定性生成，内置 1,010 米积压这个已知业务荒谬）: `planned`
- 8. 零依赖启动进 CI（L2 慢门禁）: `planned`

> **2026-08-21 新增一批 plan（三个，执行顺序 4 的 B 半 → 6 的导出 → 5 的删除）**：
> 三个 fixture 已由人在 `ede5440` 写完（STATE §2 11:20Z），工作项 4/5 两个前驱 plan 登记的 deferred 重开事件因此满足。
> 顺序与 roadmap 这张表的 4、5、6 不同，理由是判据自身的依赖：删除那条门禁的前四行代码要先能
> `export_customizations` 才走得到 `apply_pack`。三个 plan 都**不划 `expected-red.txt`**（默认判定环境下 L2 恒红），
> 因此工作项 4/5/6 均停在 `planned`，不置 `done`。
> · 工作项 4 的 B 半：[`2026-08-21-1922-1-site-snapshot-source-live.md`](../plans/p0-foundation/2026-08-21-1922-1-site-snapshot-source-live.md)
> · 工作项 6 的导出半：[`2026-08-21-1922-2-export-customizations-live.md`](../plans/p0-foundation/2026-08-21-1922-2-export-customizations-live.md)
> · 工作项 5 的 B 半：[`2026-08-21-1922-3-execute-plan-site-delete.md`](../plans/p0-foundation/2026-08-21-1922-3-execute-plan-site-delete.md)
> 工作项 6 剩下的 `test_no_orphan_column_left_behind`（`schema_drift`，要查物理表列，REST 面答不出）
> 归它的第二个 plan，本批不做。

## Status values

| Status | Meaning |
| --- | --- |
| `todo` | 未开始，没有 plan |
| `planned` | 已有执行 plan 且通过草案评审 |
| `done` | 完成，且通过 closure 审计（对应门禁测试已转绿并从预期红名单划掉） |

## 工作项 → 门禁测试对照

| # | 工作项 | 关闭它的门禁测试 | 层 |
|---|---|---|---|
| 1 | 定制包规范化器 | `test_normalizer_idempotent.py`（3 条） | L1 |
| 2 | 状态快照与 diff | `test_snapshot_diff_structured.py::test_two_snapshots_of_unchanged_site_diff_empty` / `::test_diff_is_structured_not_text` | L1 |
| 3 | 零依赖启动 | `test_zero_dep_boot.py::test_compose_config_valid_with_empty_env` | L1 |
| 4 | 工具契约层 v0 | 提供 `live_site` fixture，解锁 L2 各项 | — |
| 4 现状 | **2026-08-21 补记，保持 `planned`**：A 半（声明面，`agenerp/contracts.py` + 十条契约）与 **B 半（站点只读传输 + `SiteSnapshotSource.read`，plan [`2026-08-21-1922-1`](../plans/p0-foundation/2026-08-21-1922-1-site-snapshot-source-live.md)，落点见 `docs/architecture/module-boundaries.md` §11.7）都已落地**；`test_field_addition_shows_up_as_structured_change` 在活站点上**实测转绿**（`… AGENERP_SITE=frontend … python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q` → exit 0，3 passed）。**但 `expected-red.txt` 一行未动**，理由是人在 STATE §2（11:20Z）已裁定「名单必须反映判定器实际看到的」，默认判定环境下该条仍红；新事实（harness 官方 L2 跑法缺 `AGENERP_SITE`、以及两条 L1 门禁的起栈顺序陷阱）已按 P0.7 先例追加进 STATE §3。**不置 `done` 的理由不是「名单没划」**：本行给工作项 4 绑的是「提供 `live_site` fixture」，它没有一条属于自己的门禁测试，`done` 的字面定义对它不可满足——与工作项 7 同一情形。**仍未做**：十条只读工具的**运行时执行器**（属 P1 控制循环） | — |
| 5 | 差集 apply 引擎 | `test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site` | L2 |
| 6 | 定制包往返验证 | `test_customization_roundtrip_delete.py::test_added_field_exports_into_pack` / `::test_export_produces_readable_diff_only`（导出两条）+ `::test_no_orphan_column_left_behind`（孤儿列） | L2 |
| 6 现状 | **2026-08-21 补记，保持 `planned`**（归属更正 + 实测结论）。**归属更正**：此前本行写「其余 3 条 + `test_field_addition_shows_up_as_structured_change`」，两处都不准——① `test_field_addition_shows_up_as_structured_change` 实际由**工作项 4** 的 plan [`2026-08-21-1922-1`](../plans/p0-foundation/2026-08-21-1922-1-site-snapshot-source-live.md) 承接并已在 live 转绿（见「4 现状」行）；② 「其余 3 条」把删除那条也算了进来，而它归工作项 5。本行现在只绑三条。**实测结论**：导出两条由 plan [`2026-08-21-1922-2`](../plans/p0-foundation/2026-08-21-1922-2-export-customizations-live.md) 交付的 `agenerp.pack.export_customizations` **在活站点上实测转绿**（`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q` → exit 1，`2 failed, 2 passed`；两条导出 PASSED，另两条 FAILED 且**逐字红在 `agenerp/apply.py` 的 `execute_plan` NotImplementedError**，不是红在导出上）。**`expected-red.txt` 一行未动**，沿用人在 STATE §2（11:20Z）的裁定：默认判定环境下 L2 恒红（`AGENERP_LIVE` 未设即 `pytest.fail`），划掉会让默认 `GATE_VERIFY` 立刻转红。因此**不置 `done`**——`done` 的定义要求「从预期红名单划掉」，该条件在此处不可满足，与工作项 4 / 7 同一情形。**仍未做**：`test_no_orphan_column_left_behind`（`schema_drift`，查物理表残留列，REST 面答不出），归工作项 6 的第二个 plan | — |
| 7 | 种子数据 | `test_seed_dataset_absurdity.py`（6 条：确定性 ×2、1,010 米/6,450 元精确值、积压对规则可见、不含图片、无第三方权利）—— **2026-08-21 由人补齐**，此前这一格是「仍然没有门禁」。实跑全绿：实现先于门禁存在，属特征化门禁而非 TDD | L1 |
| 8 | 零依赖启动进 CI | `test_zero_dep_boot.py` 其余 2 条（**两条都仍在 `expected-red.txt` 内，本次一条未划掉**）。2026-08-21 由 plan [`2026-08-21-1634-2-compose-healthcheck-app-services.md`](../plans/p0-foundation/2026-08-21-1634-2-compose-healthcheck-app-services.md) 交付了「healthy 可判定」这半：应用侧三个服务已落真实 healthcheck，`up -d --wait` 冷起实测 exit 0 且变异验证有牙齿，判定口径落在 `docs/architecture/system-baseline.md` §14.2。**剩下两半仍缺**：① `compose_stack` fixture 在 `tests/gates/conftest.py`（红线 1，等人处置，见 STATE §3）；② 首页「AI 能力未配置」文案 | L2 |

## 框架/平台复用

| 能力 | 由谁提供 | 说明 |
|---|---|---|
| DocType / 权限 / 事务 | Frappe / ERPNext | **不重造会计与制造内核**（D-7）。我们长在它上面 |
| 定制导出 | Frappe `export_customizations` | 只用它导出；**不用 `sync_customizations` 做 apply**——Spike 06 实测它是纯 upsert，删不掉 |
| 测试运行 | pytest 9.x | 已在本机；`markers` 定义在 `pyproject.toml` |
| 门禁判定 | `tools/gates/check_expected_red.py` | 已就绪，别再写第二个判定器 |

## 当前基线

**已就位：**
- Day 0 的工程设施：AGE 骨架、AGENTS.md 红线、CI 五个 job 全绿、mission-driver fork（P1–P4 四个补丁）
- 四个红测试 13 条断言，全红且红得有据（实现不存在，非测试缺陷）

**主要缺口：**
- ~~`agenerp` 这个 Python 包**还不存在**~~ —— 2026-08-20 已由前置基线 plan
  [`2026-08-20-2341-1-agenerp-package-skeleton.md`](../plans/p0-foundation/2026-08-20-2341-1-agenerp-package-skeleton.md) 交付：
  `agenerp.pack` / `agenerp.snapshot` 六个契约面**签名已定稿、行为未实现**，调用即 `NotImplementedError`。
  门禁的红因因此从 `ModuleNotFoundError` 变成 `NotImplementedError`——**没有任何一条门禁因此转绿**，
  下面 8 个工作项的状态一项未动。
- 没有 `docker-compose.yml`，没有活站点，`live_site` / `pack_repo` / `compose_stack` 三个 fixture 都还抛 `NotImplementedError`
- 工作项 7（种子数据）**仍然没有门禁测试**。2026-08-21 由 plan [`2026-08-21-1634-1-seed-dataset-deterministic.md`](../plans/p0-foundation/2026-08-21-1634-1-seed-dataset-deterministic.md) 交付了 A 半（`agenerp.seed` 确定性生成器 + 自验 CLI + 31 条单测），**A/B 切分的责任在那个 plan 自己**：B 半要 `live_site`，该 fixture 在 `tests/gates/conftest.py`（红线 1）。
  因此工作项 7 置 `planned` 而非 `done`——roadmap 对 `done` 的定义是「对应门禁测试已转绿并从预期红名单划掉」，而它压根没有门禁测试，这个定义在字面上不可满足。门禁提案已写在红线外（[`gate-proposal-seed-dataset.md`](./gate-proposal-seed-dataset.md)），判据缺口已登记进 `docs/masterplan/STATE.md` 的 needs-human 队列，等人从三个处置项里选。

## 本 mission 的规则

- **判据先行**：任何工作项开工前，先确认它有绑定的门禁测试。没有就先补一条红的（补测试要人批，走 `Gates-Change-Approved-By:`）。
- **一个工作项 = 1–2 个 plan。** 超过两个说明工作项拆得不够细，回来改这张表。
- **关闭工作项的同一个提交里**，必须把对应测试从 `tools/gates/expected-red.txt` 划掉——名单只能变短，CI 的棘轮会盯着。
  （2026-08-21 `920ce0e` 起名单已迁出 `tests/gates/`：测试代码是裁判受红线 1 保护，名单只是账本，允许在同一提交里划短。）
- 不许为了让测试变绿去改测试。改判据走 needs-human 五步。
