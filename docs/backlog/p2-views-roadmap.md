# P2 · 视图生成与新前端 — mission roadmap

> Last updated: 2026-08-26
> Sources: [`docs/masterplan/02-WBS.md`](../masterplan/02-WBS.md) §5（判据的真相源）·
> [`tests/gates/`](../../tests/gates/README.md)（判据的可执行形式）

## Purpose

这是 **`p2-views` mission 自己的 roadmap**，由引擎在 closure 审计通过后回写。
全局阶段索引在 [`implementation-roadmap.md`](./implementation-roadmap.md)，由人维护。

P2 的目标一句话：**让 Agent 能按自然语言生成用户看得懂的视图，并且能证明生成的视图指向真实字段。**

**②③端仍只读**——本阶段 Agent 不写任何业务数据。

## 本阶段的四条硬约束（违反即停机，不是风格建议）

**① 判据不许只验「调得通」。**（CP9 继承项，P1 原样带过来）
**渲染出来 ≠ 渲染对了；DSL 校验过 ≠ 字段真的存在。**

⚠️ P1 用一次真实事故证明了这条不是空话：答案面判据里一个 `or` 让空答案照过，
**「54 项全绿」在「Agent 到底能不能答」这一维上是空的，挂了数日无人发现**
（见 `docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2）。
P2 的等价风险是：**视图渲染出来了，但字段名是编的。**

**② 预测在前，结果在后，逐条吻合。**（CP9 继承项）

**③ 规则能覆盖的流程不 Agent 化。**（D-15）
视图 DSL 的校验、「未支持一律落回 Desk」的判定 —— **都是规则面，不许交给模型判**。

**④ P2 专属：任何「自然语言 → 字段」的产出，必须能指回一个真实存在的 DocType 字段。**

> **P1 是只读解释，错了是一个错答案；P2 生成视图，错了是用户天天看到的错字段。**

---

## 🔴 头号技术风险：schema 检索（P2.0R）

`open-questions.md` **U6「schema 向量检索能找对字段」实测结论是「不成立」——
最好 Top-5 = 75%**（Spike 07）。本站点一千多个 DocType、上万个字段。

**为什么它是头号**：**P2.3（视图 Agent）与整个 P3（操作 Agent）都建立在它之上。**
检索不准，视图会画错字段，写入 Agent 会改错单据 —— **后者是脏账，不是错答案。**

⚠️ **这个风险与 agent harness 无关**（D-22.4）：换任何框架都不会让 Top-5 从 75%
变成 90%，它们不知道 `Stock Entry` 和 `Stock Reconciliation` 的区别。
**这是本项目自己的 ERP 领域问题。**

**候选方向（均未在本仓实测，不是候选清单）**：结构化召回（按 DocType 关系图 +
Link 字段收敛）· 术语层反向索引（P2.7 的产物）· 行业包约束（P1.6 的声明式规则缩小搜索域）。

⚠️ **不得在没有实测的情况下选路**（D-16）。

---

## 工作项

> 编号与 `02-WBS.md` §5 一一对应。**判据以 WBS 为准，本文不重定。**

- 1. **入口关口实验：Spike 11 · Workspace 升级覆盖**（P2.0 🚪）: **`done`** —— **人 2026-08-26 裁定「以 Arm B 判过」**。
  假设**成立**：改标准 `Workspace` 会被升级静默覆盖（Arm B 实测：`icon` 被 JSON 覆盖、shortcuts 7→6、
  canary 子表**物理删行**，只有 `is_hidden` 幸存；且该次 migrate 的输出与「什么都没发生」那次**逐字节相同**）。
  ⇒ 🔴 **载体结论：视图产物落 AgenERP 自有表，不落标准 `Workspace`。**
  证据：[`docs/plans/p2-views/2026-08-26-P2.0-…-workspace-upgrade-overwrite.md`](../plans/p2-views/2026-08-26-P2.0-entry-gate-spike11-workspace-upgrade-overwrite.md)（`f7cc4bd` 预测 → `7ca312a` 结果）·
  [`module-boundaries.md` §11.4](../architecture/module-boundaries.md)（机制陈述已按实测订正）
- 2. **schema 检索可用性**（P2.0R 🔴，头号风险）: `todo` —— 验收：真实 DocType 上自然语言问句 → 目标字段 **Top-5 命中率 ≥ 90%**（今日基线 75%）
- 3. **视图 DSL v0**（P2.1，五种块）: **`done`** —— 前置 P2.0（已过）。
  `agenerp/dsl/`（声明格式 + 两层校验器 + 落回 Desk 的规则面判定）·
  `pytest tests/dsl -q` → **退出码 0，42 passed**。
  🔴 **L2「字段真的存在吗」是独立一层且不可跳过**，`validate(view, None)` 抛异常不返回 ok；
  **四条变异逐条见血**（把 L2 改恒真 → 6 条红），复原后实现文件 `sha256` 逐字节相同。
  证据：[plan](../plans/p2-views/2026-08-26-P2.1-view-dsl-v0.md)（`0bcf546` 先红 → 实现）
- 4. **渲染器：未支持的一律落回 Desk**（P2.2）: **`done`** —— 前置 P2.1（已过）。
  `pytest -m live tests/render -q` → **退出码 0，14 passed**（真站点 · 真权限 · 真浏览器）。
  🔴 **人 2026-08-27 选定路线 C（按角色做到 100%）**：车间工人的三个日常视图
  **落回 Desk = 0**（从 `957ac06` 实测的 3 降下来）。覆盖面 15 张表 / 317 个字段。
  安全代价事先定死并各有判据：富文本剥标签（`javascript:`/`data:`/`vbscript:`/`//host`
  四种载荷全部不产出可点击元素；`<img onerror>` 不执行）。
  ⚠️ **与 WBS 字面「frappe-ui」偏离**：用零构建 vanilla JS，理由与可逆性见 plan §3，**供人推翻**。
  ⚠️ **只对车间工人这一个角色成立**，推广要另量。
  证据：[plan](../plans/p2-views/2026-08-27-P2.2-renderer-role-complete.md)
- 5. **视图 Agent：自然语言 → DSL**（P2.3）: `todo` —— 前置 P2.2 **且 P2.0R**
- 6. **定制包 GitOps v0**（P2.4）: `todo` —— 前置 P2.3
- 7. **`schema.drift` 巡检**（P2.5）: `todo` —— 前置 P2.4
- 8. **角色首页**（P2.6）: **功能面完成，`todo`（判据未落地）** —— 前置 P2.2（已过）。
  `/agenerp/home` 用**浏览器自己的 sid** 问站点角色 → 封闭表映射到首页视图。
  `pytest -m live tests/render -q` → **退 0，18 passed**；端点判据用
  `build_server(port=0)` 本地起真服务发真 HTTP（22 passed）。
  🔴 「不空」按**内容**判，不是按 DOM：≥1 个块 · **≥1 行真数据** · 无落回卡片。
  fail-closed：认不出人 → 401、角色没配页 → 403，**都带 `fallback: desk`，都不给别人的首页**。
  🚫 **WBS 的验收判据 `tests/gates/test_no_empty_workspace.py` 仍不存在**（红线 1 我不能建），
  草稿在 `tools/experiments/p2_role_home/` ⇒ **本项不由 loop 判过，状态留 `todo`**。
  证据：[plan](../plans/p2-views/2026-08-27-P2.6-role-home.md)
- 9. **术语层**（P2.7）: **`done`** —— 前置 P2.2（已过）。
  `pytest tests/i18n -q` → **退出码 0，12 passed**。基线是**零**：整站 6,350 个业务字段
  label 含中文的 = 0。现在车间工人覆盖面 **317/317 = 100%** 有中文名，且渲染器表头已是中文
  （`pytest -m live tests/render -q` 仍退 0，16 passed）。**API 成本 = 0**（本地 Ollama）。
  ⚠️ **判据验的是「有没有离谱地错」，不是「翻译得好不好」** —— plan §12.3 用一次真实的
  模型更换证明了这个上限有多低：**T3 全中的同时 `has_batch_no` 是错的**（「批次号」）。
  ⚠️ 只覆盖 317 个字段，整站 6,350 个未做。
  证据：[plan](../plans/p2-views/2026-08-27-P2.7-terminology-layer.md)
- 10. **CP9 · P2 阶段复盘**（P2.8）: `todo` —— **状态源 `人`**，loop 不动它

### 🔴 P2.8 复盘的既定入账项（人 2026-08-26 裁定时指定，不许丢）

**`REF:ROADMAP-SPIKE1112` 的证伪判据名不副实。** 它写的是「手改 app 内该 JSON **使 md5 变化**
→ 改动仍在即证伪」，但 `import_file.py` 的 md5 比较**只对 `DocType` 生效**（`migration_hash`
是 DocType 的字段，`Workspace` 没有，实测 `has_column` → `False`）。**照字面跑得到「证伪」，
而实测事实是「成立」—— 判据与它要测的事方向相反。**

⇒ 按 `04-RUNBOOK.md` §7.2.1，这是**「它测的不是它名字说的那件事」的一个实例**，
P2.8 必须把它记进抽查制那一节。**人已裁定判据原样保留、不改**（判据是裁判）。
⚠️ 区别于 P1 那次：**这次是在跑之前发现的**，没有变成误放行。

---

## 从 P1 带过来的、必须照做的四条

**① 门禁的抽查制**（`04-RUNBOOK.md` §7.2.1，P1 复盘产物）
每阶段从**新增或改动过的绿判据**里随机抽 3 条，逐条答
「**它测的，是不是它名字说的那件事？**」⚠️ **抽查者不得是这些判据的作者。**

**② 人侧改动也走独立复核**（§7.2.2）
人侧对 `tests/gates/**`、断言体、`agenerp/**` 的改动，提交后登记 `STATE` §3，
由 loop 下一轮独立复核。**不阻塞提交 —— 要的是有人看过。**

**③ 断言里不许有失败逃逸**
`tests/gates/test_assertions_have_no_escape_hatch.py` 已在守。
口径：「一条会 skip 的门禁等于一条不存在的门禁」→「**一条带失败逃逸的断言等于半条判据**」。

**④ 状态回退必须同时写「什么条件成立就可以改回来」**
P1 期间人侧把 P1.8a 回退成 `todo` 却没写复原条件，
结果**理由消失后没人负责改回，还把下游依赖搞成倒挂**。

---

## 已知会咬人的（P1 实测，P2 直接继承）

| 事项 | 实测 | 对 P2 的含义 |
|---|---|---|
| `AGENERP_LLM_MODEL` 曾是死配置 | `route()` 忽略它，走到没额度的模型，**每次解释都 403** | 工作项 3b 修 `route()` 本体；P2 起任何新配置项都要有「配了就该生效」判据 |
| 归因类问题会打爆预算 | 修 `doc.links` + 放开上限后 **0/3 → 3/3** | 视图生成是同一类多跳任务，**上限要先量再定** |
| 免费额度会被单次问答吃掉 | 一次 runaway 烧掉 13.6 万，占某模型月度额度 **60%** | P2 有真跑判据时，**先看 D-17 的取用顺序** |
| 停机标记会残留 | `auth-expired` 解除后不自动复跑，**白停 12 小时** | 守卫每次拉起须**复验条件**，不是无条件停在标记上 |
