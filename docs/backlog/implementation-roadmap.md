# AgenERP 实施路线图 — P0 → P5

> Last updated: 2026-08-20
> Sources: [`docs/architecture/`](../architecture/README.md)（架构，主）· [`docs/masterplan/02-WBS.md`](../masterplan/02-WBS.md)（工作分解）· 建设前验证证据见证据仓 `1c622c8` 的 `spike/`
> 前身：XM 仓 `docs/next/ROADMAP.md`（草案 v0.2 · 2026-08-19），2026-08-20 迁入本仓并改为引擎可解析格式（WBS `W0.4`）。**原文件已冻结。**

## Purpose

本文件是 P0–P5 的**全局阶段索引**：每个阶段的目标、交付物与**验收判据**都在这里，是「阶段算不算完成」的唯一真相源。
主计划（`docs/masterplan/`）只做编排（状态、次序、仪式），**不复制这里的判据**；它引用本文件的节标题。

**谁维护哪一块**（别搞混，搞混就会出现两个真相源）：

| 文件 | 粒度 | 谁写 |
|---|---|---|
| 本文件的 `## Work Item Status` | 阶段（P0–P5，各 = 一个 mission） | **人**手工维护 |
| `docs/backlog/p{n}-*-roadmap.md`（各 mission 自己的 roadmap） | 阶段内的工作项 | **引擎**在 closure 审计通过后回写 |

各 mission 的 `roadmapPath` 指向后者，**不指向本文件**。

## Work Item Status

> **本块是唯一的动态状态块。** 阶段状态只在这里改。

- 1. P0 · 地基（无 Agent）: `todo`
- 2. P1 · 解释与洞察（②端只读）: `todo`
- 3. P2 · 视图生成与新前端（②③端）: `todo`
- 4. P3 · 操作 Agent（③端写入）: `todo`
- 5. P4 · 形态 Agent（①端）: `todo`
- 6. P5 · 评测与编排: `todo`

## Status values

| Status | Meaning |
| --- | --- |
| `todo` | 未开始，没有 plan |
| `planned` | 已有执行 plan 且通过草案评审 |
| `done` | 完成，且通过 closure 审计 |

## 原则

1. **每个阶段独立交付、独立验证、独立放弃。** 任一阶段失败不拖垮前面已交付的价值。
2. **风险递增。** 只读 → 生成视图 → 写业务数据 → 改系统形态。绝不跳级。
3. **评测先于自动化。** 没有可验证的判定标准，就不允许 Agent 自动执行该类动作。
4. **每阶段一个 mission。** roadmap 的一个 work item = **1–2 个 plan**；plan 的关闭以 `GATE_VERIFY` 子进程的**退出码**为准，不以 AI 打勾为准。
   （原为「每阶段一个 change proposal：proposal → apply → archive」。裁决与理由见主计划 `REF:CUT-OPENSPEC`：两套状态机语义重叠而命名不同，同时跑会让模型在「该建哪个」上反复漂移。粒度感由 mission 承载，没有丢。）

---

## 待补 Spike（阻塞对应阶段）

2026-08-20 的能力勘察产出两个未验证假设，各自阻塞一个阶段的选型。详见 [design/view-dsl-and-eval.md](../design/view-dsl-and-eval.md) §10.4 与 [architecture/module-boundaries.md](../architecture/module-boundaries.md) §11.4。

| Spike | 假设 | 证伪判据（事先写死） | 阻塞 |
|---|---|---|---|
| **11 · Workspace 覆盖** | 改标准 Workspace 后，app 升级（fixture JSON 变更）会静默覆盖用户改动 | 改 Workspace → 手改 app 内该 JSON 使 md5 变化 → `bench migrate` → **改动仍在即证伪** | **P2**：视图产物落 Workspace 还是落 AgenERP 自有表 |
| **12 · custom DocType 全生命周期** | `custom:1` DocType 建 → 导出 → diff → 删 四步全程可治理 | 任一环节做不到即失败。已知风险：`developer_mode` 关闭时 `export_customizations` 不可用，即「能建、导不出」 | **P4**：形态 Agent 能否触及 DocType 层（而非仅 Custom Field） |

两个都是十几分钟量级，应在进入对应阶段前跑完。

---

## P0 · 地基（无 Agent）

**目标**：把「可验证」做出来。这一阶段不引入任何 LLM。

| 交付 | 说明 |
|---|---|
| 仓库与工程设施 | 新仓库、GPL-3.0、**不设 CLA**（见 [project-vision.md](../architecture/project-vision.md) §16）、CI、**AGE 骨架安装 + mission 配置**、AGENTS.md。**建仓库前必须定名**——已于 `W0.1` 复核完成，D-1 维持 AgenERP |
| 零依赖启动 | `git clone && docker compose up` 必须可跑，无需任何 API key |
| 工具契约层 v0 | 契约声明格式；先包 10 个只读工具 |
| 状态快照与 diff | 由 `runtime_snapshot()` 扩展为：任意时刻快照 + 两快照 diff + 断言 DSL |
| 种子数据 | **确定性程序化生成**的离散制造数据集（不含图片，无第三方权利），**必须内置一个已知业务荒谬**（如成品积压 1,010 米）作为洞察 Agent 与行业包规则的固定测例 |
| **定制包规范化器**（新增） | 剥离 `modified`/`creation`/`owner`/`_comments` 等易变字段并稳定排序。**不做则 git 历史无意义**——Spike 06 实测：什么都不改重新导出也会产生 diff |
| **差集 apply 引擎**（新增） | 读定制包 → 与站点现状求差 → **对差集执行删除**。Spike 06 实测 Frappe 的 `sync_customizations` 是纯 upsert，**`git revert` 撤不掉字段**。这是 P2 验收标准可达的前提 |
| **零依赖启动 CI**（新增） | 空环境变量下 `docker compose config && up -d` + 健康检查，断言全部服务 healthy 且首页显示「AI 能力未配置」 |

**验收**：
- 能对同一站点打两次快照并输出结构化 diff；契约的前置条件/后置断言可被独立测试
- **定制包往返：新增字段 → 导出 → `git diff` 干净可读 → 从包中删除 → apply → 字段真的消失**
- **空环境变量下 `docker compose up` 成功**

**为什么新增后三项**：Spike 06 表明定制包的规范化与差集 apply 是**定制包与视图 DSL 共用的地基**，
与 P0 已有的契约层、状态快照是同一批基础设施，一起做比分两次做便宜。Spike 10 表明零依赖启动
现状失败，而修法只是 compose 语法——是 P0 里最便宜、却守着第一转化率的一项。

**为什么先做这个**：没有客观判定标准，后面所有 Agent 的效果都只能靠感觉。

---

## P1 · 解释与洞察（②端只读）

**目标**：第一个可演示的东西，风险最低，痛点最大。

| 交付 | 说明 |
|---|---|
| 模型路由 v0 | OpenAI-compatible adapter；**能力声明按任务分档**（Spike 03：本地 14B 够做权限判断与单跳查询，不够做跨单据推理） |
| 上下文层 v0 | 即时上下文注入 + 会话落 DocType |
| **结构化导航工具** | `system.overview` / `permission.scope` / `meta.fields` / `doc.links`。**`permission.scope` 由循环在开场自动注入** |
| ~~Schema 元知识检索~~ | **降级为 P2 可选**。Spike 07：真实规模下最好 Top-5 仅 75%；而 Spike 02 全程未用向量检索即通过四道探针 |
| **解释 Agent** | text-to-query + 单据血缘追溯 + 规则查询 + **证据充分性门禁**（新增，见下） |
| **洞察 Agent** | **按行业包规则清单**巡检异常。Spike 08：自由巡检发现不了跨单据的业务荒谬 |
| 行业包 v0 | 离散制造。**首要内容是业务合理性规则**（不是术语表），每条规则须带 `test_case`；其次才是阈值与术语映射 |
| Agent 侧边栏（嵌入 Desk） | ⌘K 唤起，**保留当前单据上下文** |

**验收（用真实场景）**：
- 问「这单为什么还是待出货」→ 能答出「990 米已发，10 米为已审批合理损耗 LOSS-00003，业务已完结」
  - ⚠️ Spike 02 实测：**不加门禁时模型只调 1 次 `doc.get` 就建议「补发 10 米」**——复现了本项目要修的那个误读。因此门禁是交付项，不是优化项
- 行业包声明「成品库存无对应订单」规则后，无需指令即能报出「成品仓积压 1,010 米、价值 6,450 元」；
  **且移除该规则后能复现漏报**——以此证明是规则在起作用，不是模型碰巧猜到
- **单次解释的成本上限**（与正确率并列的验收项）。Spike 02 无缓存基线：$0.252/题

**为什么侧边栏先嵌 Desk**：此时还没有新前端。先证明 Agent 有用，再投入渲染器。

---

## P2 · 视图生成与新前端（②③端）

**目标**：解决「太不直观」+「每家公司不一样」——同一个解。

| 交付 | 说明 |
|---|---|
| 视图 DSL v0 | 五种块：`list` / `detail` / `metric` / `chart` / `explain` |
| 渲染器 | frappe-ui（Vue 3 + Tailwind）；**未支持的一律落回 Desk** |
| **视图 Agent** | 自然语言 → DSL；含 `dsl.validate` / `dsl.preview` |
| 定制包 GitOps v0 | DSL 落 git，可 diff、可 revert、可迁移到另一站点（**依赖 P0 的规范化器与差集 apply 引擎**） |
| `schema.drift` 巡检（新增） | 检出「数据库有列但无对应 Custom Field」的孤儿列。Spike 06：删 Custom Field 不删列，反复增删会静默累积 |
| 角色首页 | ②③ 端按角色渲染不同默认视图 |
| 术语层 | LLM 生成 label，绕开社区翻译（修「大师」「进行中」类事故）。**Spike 07 追加理由：用户用中文问、schema 是英文的，术语层同时是检索质量的前置条件** |

**验收**：
- 一句话改出老板首页 → `git diff` 看得到改了什么 → `git revert` 撤得回来 → 同步到另一个站点生效
- 老板首页首屏有结论和基准，不再是 12 个链接 0 个数字
- **可机器判定的基线（Spike 09 实测现状）**：老板 `Home` 工作台当前渲染 **0** 个链接，
  20 个可见工作台里 8 个是完全空壳。验收标准：**每个角色的默认首页渲染元素 > 0，空壳工作台数为 0**，可进 CI

**这是项目最具说服力的演示**：现有 7 个同类项目一个都做不到。

---

## P3 · 操作 Agent（③端写入）

**目标**：开始产生生产力。风险升到 L2。

| 交付 | 说明 |
|---|---|
| 工具契约层 v1 | 写操作契约：前置条件 + 后置断言 + 回滚语义。**回滚 = savepoint 回滚**（Spike 05 已确定语义），非 cancel/amend |
| **回滚前提回归测试**（新增） | 对每个写契约覆盖的 DocType 断言「提交路径不调用 `db.commit`、不 `enqueue`」。**该测试失败即意味着该 DocType 的 `rollback_and_report` 失效**，契约须降级为「仅前置校验」 |
| **操作 Agent** | 建单、提交、报工、走流程 |
| 风险分级与审批 harness | 审批 gate **长在控制循环里**，不是外挂 |
| 补偿事务 | 后置断言不成立时的回滚与留痕。**契约须声明是否产生事务外副作用**；产生的只能 `abort_before_side_effect` |
| Memory v0 | 三层粒度 DocType + 分级 + 安全红线 |
| **写权限下的注入重测**（新增） | Spike 04 的抗注入结论是在 **L0 只读** Agent 上得到的。操作 Agent 拿到写工具后，同样载荷的后果完全不同。**必须在操作 Agent 上线前重跑并扩测 Memory 投毒** |
| **Harness 采用决策** | 依据稳定性 + 实测 worker 资源开销 + 镜像体积，决定是否提升为推荐配置。**Spike 02 已证明内置纯 Python 循环够用 → Harness 降为纯增强** |

**验收**：
- Agent 在**不绕过 4 道 `before_submit` 门禁**的前提下推完一笔订单
- 每一步 state-diff 可判定
- 越权/超阈值动作被正确拦截并要求人批
- **后置断言失败时回滚干净**：单据、SLE、GL、单号计数器全部回退，不留作废单与反向分录
- **写权限下的四类注入 0 执行**

---

## P4 · 形态 Agent（①端）

**目标**：最难，也最值钱——系统形态由企业自己长出来。

| 交付 | 说明 |
|---|---|
| **形态 Agent** | Custom Field / DocType / Property Setter / 权限 |
| 冗余判断 | 原生字段冲突检查（防 Job Card 那类重复定制） |
| 权限多层联动 | 一条指令同时处理**五层**：DocType / **Report.Has Role（主导）** / Workspace 可见性 / Workspace 内容 / 渲染 API 检查。Spike 09：老板打不开的 186 张报表中 184 张是被 `Report.Has Role` 挡住，与 DocType 权限无关 |
| 定制包 GitOps v1 | 元数据变更的 diff、迁移计划、回滚 |
| L3 审批链 | 强制人批 + 落 git；**Server Script 永不运行时注入** |

**验收**：
- 「给外协收货加个水洗牢度字段」→ 检出原生无冲突 → 生成变更 → 人批 → 应用 → 落 git → 可 revert
- 「让老板能看所有报表」→ 五层权限同时正确处理，用户不再撞墙
- **后置断言以「用户能看到什么」判定**，不以「写了几条 DocPerm」判定：直接调 `get_desktop_page` 断言渲染元素 > 0

---

## P5 · 评测与编排

| 交付 | 说明 |
|---|---|
| 评测集 | ERPNext 上的 agent benchmark，state-diff 判定 + 业务合理性规则。**种子数据内置的已知业务荒谬（1,010 米积压）即 test case #1**。补齐本轮 spike 缺失的**重复实验与统计显著性**——所有探针目前每题各跑 1 次 |
| 持续基准生成 | 随 DocType 演进自动更新 |
| **编排 Agent** | 意图路由、任务分解、跨 Agent 调度 |
| 行业包机制 v1 | 声明格式与分发，使社区可贡献行业知识 |

**验收**：前四阶段的能力可回归；新增行业包无需改内核。

---

## 关键依赖与风险

| 依赖 | 风险 | 缓解 |
|---|---|---|
| DeepSeek Harness | 有官方 Python SDK，但 runtime 为打包子进程：**不支持 Windows**、worker 资源开销未测、镜像体积增大、preview 期会破坏兼容 | 内置纯 Python runtime 零依赖且支持 Windows；Harness 作可选依赖 `agenerp[harness]`；P3 依实测决策 |
| MyContext | 发布约一周，数据源与粒度需适配 | 作为 adapter；内置 Memory 实现独立可用 |
| DeepSeek V4 | 商业 API，数据出境 | model adapter；默认 OpenAI-compatible；首版即支持本地模型 |
| ERPNext 升级 | 上游变更影响契约 | 不改 ERPNext 核心；契约以 DocType meta 为准而非硬编码 |
| **Frappe 事务语义** | `rollback_and_report` 依赖「提交路径不 commit、不 enqueue」这一**实现细节而非承诺**，上游一次改动即可失效 | P3 的回归测试；失效时契约自动降级 |
| **Frappe `sync_customizations` 语义** | 纯 upsert，不删除。若指望它做 revert 会静默失败 | **不使用它**，改用自建差集 apply 引擎（P0） |
| **模型能力落差** | 本地 14B 在跨单据推理上不足；仅靠提示词无法弥补 | 能力声明按任务分档；**用确定性循环门禁补偿**而非换更强提示词 |

## 不做的事（避免踩已知的坑）

- ❌ **不重写 Desk** —— Frappe 核心开发者的尝试（frappe-deskv3）已于 2022 年停止
- ❌ **不把 ERP 数据写进向量库** —— 精度、时效、权限三重问题
- ❌ **不做独立 AI 聊天页** —— 丢上下文，是现有 AI 插件普遍无用的原因
- ❌ **不让 Agent 生成运行时 Server Script** —— 等同 RCE
- ❌ **不做通用行业** —— 内核通用，行业深度靠行业包
- ❌ **不指望洞察 Agent 自由发挥** —— Spike 08：无规则驱动的巡检漏掉了积压 1,010 米并判其「正常」
- ❌ **不用「只看已提交单据」筛选下游** —— Loss Review / Production Issue 这类承载业务判断的 DocType 不可提交，docstatus 恒为草稿，会被整类丢掉
- ❌ **不从权限表反推权限** —— 必须逐个调 `frappe.has_permission`；反推会漏报，而漏报会让 Agent 错误地拒绝回答

---

## 本文件的维护规则

- 阶段状态**只在 `## Work Item Status` 改**；阶段详情里若要提状态，写「见上方 Work Item Status」。
- `## Work Item Status` 这个标题是**硬契约**（引擎的 `roadmap-check.mjs` 只认这个字串与旧称 `## 阶段状态`）。改标题 = 监控面板拿不到数据 + 终局判定失效。
- 验收判据**只增不改**：判据被实测推翻时，追加一行写清是什么实测推翻了它，不要静悄悄改掉原判据。
- 阶段详情里的「为什么」段落不要删——它们记的是当初为什么这么定，删了以后没人知道能不能改。
- 本文件不放实现细节。实现细节进 plan（`docs/plans/`）。
