# 架构文档索引

> **一句话定位**：基于 Frappe / ERPNext 的开源 Agent 驱动 ERP —— 让每家企业用自然语言长出自己的系统形态，而长出来的东西必须可版本化、可 diff、可回滚、可迁移。

| | |
|---|---|
| 文档状态 | 草案 v0.6（经建设前验证实测修订，见 [open-questions.md](./open-questions.md) 附录 B） |
| 许可 | **GPL-3.0**，不设 CLA，不双许可（见 [project-vision.md](./project-vision.md) §16） |
| 由来 | 原为 XM 探索项目的单文件 `ARCHITECTURE.md`（69KB/1159 行），2026-08-20 按语义拆分迁入本仓（WBS `W0.3`）。**原文件已冻结，本目录是唯一在演进的版本。** |

## 拆分后的归属

| 文件 | 装的是原文的哪几节 |
|---|---|
| [project-vision.md](./project-vision.md) | §1 定位与非目标（含**三条设计公理** §1.2）、§2 竞品与空缺、§16 许可与商业化 |
| [system-baseline.md](./system-baseline.md) | §3 分层架构、§4 三端模型、§14 数据与安全 |
| [module-boundaries.md](./module-boundaries.md) | §7 工具契约层、§11 定制包与 GitOps（**§11.2 防死亡螺旋**） |
| [model-management.md](./model-management.md) | §12 模型管理 |
| [open-questions.md](./open-questions.md) | §15 待定项、附录 A 实测问题清单、附录 B 建设前验证索引 |
| [../design/agents-and-roles.md](../design/agents-and-roles.md) | §5 Agent 清单、§6 角色×Agent 矩阵、§9 风险分级与审批 |
| [../design/context-and-memory.md](../design/context-and-memory.md) | §8 上下文、知识与记忆架构 |
| [../design/view-dsl-and-eval.md](../design/view-dsl-and-eval.md) | §10 视图 DSL 与渲染器、§13 状态快照与评测 |

**章节编号一律保持原样**（§1、§7、§11.2 …）：主计划的 `REF:` 表按标题原文定位，改标题等于断链。要改标题，先改 [REF 登记表](../masterplan/README.md)，再跑 `tools/check-masterplan-links.sh`。

## 边界

- `docs/design/` 管应用行为与功能语义；`docs/architecture/` 管技术结构与跨功能规则。
- 持久化与 schema 的真相以模型/schema 文件本身为准，不以本目录的描述为准。
- 被否掉的方案与探索笔记去 `docs/analysis/`，不留在 owner 文档里。
- `mission-driver-baseline.md`（引擎自身的公开契约）随 `W0.8` fork 引擎时落位。
