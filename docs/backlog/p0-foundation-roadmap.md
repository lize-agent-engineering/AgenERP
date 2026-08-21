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
- 5. 差集 apply 引擎（读包 → 求差 → **对差集执行删除**）: `todo`
- 6. 定制包往返删除验证（活站点端到端）: `todo`
- 7. 种子数据（确定性生成，内置 1,010 米积压这个已知业务荒谬）: `todo`
- 8. 零依赖启动进 CI（L2 慢门禁）: `todo`

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
| 5 | 差集 apply 引擎 | `test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site` | L2 |
| 6 | 定制包往返验证 | `test_customization_roundtrip_delete.py` 其余 3 条 + `test_snapshot_diff_structured.py::test_field_addition_shows_up_as_structured_change` | L2 |
| 7 | 种子数据 | 尚无门禁——**开工前先补一条**，否则这一项没有判据（见下方规则） |
| 8 | 零依赖启动进 CI | `test_zero_dep_boot.py` 其余 2 条 | L2 |

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
- 工作项 7（种子数据）**没有门禁测试**

## 本 mission 的规则

- **判据先行**：任何工作项开工前，先确认它有绑定的门禁测试。没有就先补一条红的（补测试要人批，走 `Gates-Change-Approved-By:`）。
- **一个工作项 = 1–2 个 plan。** 超过两个说明工作项拆得不够细，回来改这张表。
- **关闭工作项的同一个提交里**，必须把对应测试从 `tools/gates/expected-red.txt` 划掉——名单只能变短，CI 的棘轮会盯着。
  （2026-08-21 `920ce0e` 起名单已迁出 `tests/gates/`：测试代码是裁判受红线 1 保护，名单只是账本，允许在同一提交里划短。）
- 不许为了让测试变绿去改测试。改判据走 needs-human 五步。
