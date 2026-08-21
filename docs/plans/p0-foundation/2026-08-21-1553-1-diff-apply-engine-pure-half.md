# 2026-08-21-1553-1 差集 apply 引擎 · A 半（读包 → 求差 → **删除计划**，纯逻辑不接站点）

> Plan Status: active
> Mission: p0-foundation
> Work Item: 5. 差集 apply 引擎（读包 → 求差 → **对差集执行删除**）—— **只做 A 半（读包 + 求差 + 删除计划），不做 B 半（对站点执行）**
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 5 项（起草时 `todo`）·`docs/architecture/module-boundaries.md` §11.1「三个必须自建的部件」第二行 ·`docs/masterplan/02-WBS.md` P0.5
> Related: `2026-08-21-1022-2-tool-contract-layer-v0.md`（**先例**：同一工作项被红线 1 拦在活站点前时，如何只交付纯逻辑半边并把另一半登记给 successor）·`2026-08-20-2341-3-snapshot-structured-diff.md`（本 plan 复用它交付的 `Snapshot` / `diff`）·`2026-08-21-1553-2-seed-dataset-deterministic.md`（同批第 2 顺位，与本 plan 无依赖）
> Audit: required

## Current Baseline

起草时（2026-08-21，HEAD `494440d`）逐条读活代码得出，不靠记忆、不抄旧 plan。

### 工作项 5 的判据在哪里、够不够得着

- roadmap §「工作项 → 门禁测试对照」第 5 行把工作项 5 绑到
  `tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`（L2）。
- 那条测试的函数签名是 `def test_removing_from_pack_actually_deletes_on_site(live_site, pack_repo)`
  （`tests/gates/test_customization_roundtrip_delete.py:43`），两个 fixture 都定义在 `tests/gates/conftest.py`
  （`live_site` 在 `:15`、`pack_repo` 在 `:21`），**函数体是 `raise NotImplementedError`**（`:17` / `:23`）。
- `tests/gates/**` 是 `AGENTS.md` 红线 1，loop 一个字节都不许改。
  → **工作项 5 绑定的那条门禁，loop 无权让它转绿**。这不是本 plan 的疏忽，是已登记的人待办：
  `docs/masterplan/STATE.md` §3 有一行 `[open]`（2026-08-21），明写「挡的是 B 半与工作项 5/6/8」，
  并列出四个只有人能选的处置项 (a)/(b)/(c)/(d)。
- **本 plan 因此不承诺任何门禁转绿，`tools/gates/expected-red.txt` 一行都不动**（该文件当前 7 行，
  含上述四条 roundtrip 断言）。

### 已经在仓里的（本 plan 直接复用，不重造）

- `agenerp/snapshot.py`：`SnapshotEntry`（`doctype` / `fieldname` / `attributes`，`key` 为二元组）、
  `ChangedEntry`（带 `before` / `after`）、`Snapshot`（相等性只看 scope 与条目，`source` 不参与）、
  `diff(before, after) -> Diff`（纯函数，scope 不同即抛 `SnapshotScopeMismatch`）——**全部已实现**。
- `agenerp/snapshot.py:113` `OfflineSnapshotSource`（`.read` 在 `:132`）：从 `<root>/<scope>/*.json` 读，
  载荷经 `agenerp.pack.normalize` 剥易变字段后转成条目；目录不存在返回空元组而不抛。
  私有函数 `_entries_from_payload`（`:158`）承载「一个 JSON 载荷 → 条目列表」的解析口径，
  形状为 `{"doctype": ..., "custom_fields": [{"fieldname": ...}, ...]}`。
- `agenerp/pack.py:21` `normalize`：已实现，纯函数、幂等、剥 `modified`/`creation`/`owner`/`_comments`、稳定排序。

### 还不存在的（本 plan 的缺口清单）

- `agenerp/pack.py:71` `apply_pack(path, site)` —— 函数体 `raise NotImplementedError(... 工作项 5 ...)`。
  **没有任何求差逻辑**：今天仓里不存在「读一个定制包目录」的代码，也不存在「删除集」这个概念的表达。
- `agenerp/snapshot.py:244` `schema_drift(doctype)` —— 同样只有签名。它要查的是**物理表残留列**，
  只有活站点答得出（`module-boundaries.md` §11.1 第三个部件），**不在本 plan 内**。
- `agenerp/snapshot.py:143` `SiteSnapshotSource.read` —— 仍 `raise`，归工作项 4 的 B 半。
- `agenerp/pack.py:64` `export_customizations` —— 仍 `raise`，归工作项 6（要活站点）。

### 判定面能看见什么

`missions/p0-foundation.json` 的 `commands.test` 逐字是
`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`。
→ **本 plan 的证明落在 `tests/unit/`，`GATE_VERIFY` 子进程复跑得到**，
不重蹈 plan `…-1022-2` 那个「主判据 `tests/contracts` 不在 `commands.test` 里」的缺口。

### 与 Frappe 的关系（为什么这半边值得单独做）

`module-boundaries.md` §11.1 的实测表：从定制包 JSON 里删掉字段再 `sync_customizations`，
**站点上字段纹丝不动**，因为 `sync_customizations_for_doctype` 是纯 upsert、**没有任何删除分支**。
「删除集」这个概念在 Frappe 那条路径上根本不存在——它正是本项目必须自建的东西，
而**算出删除集是纯逻辑，执行删除才需要站点**。本 plan 做前者。

## Goals

- 交付**读包**：把一个定制包目录读成 `Snapshot`，口径与 `OfflineSnapshotSource` 完全一致（同一套解析，不开第二口径）。
- 交付**求差**：`plan_apply(desired, current) -> ApplyPlan`，纯函数，产出 `creates` / `updates` / `deletes` 三个序列，
  **`deletes` 是一等公民**（这正是 Frappe 缺的那一半）。
- 交付**接缝**：`execute_plan(plan, site)` 与 `agenerp.pack.apply_pack` 的委派链就位，
  红在「执行未实现」而不是「求差不存在」——把 B 半的落点钉死一个位置。
- 交付**判据**：`tests/unit/` 下的行为覆盖，含一条**反 upsert 回归**断言（从包里删掉字段 → 该字段必须出现在 `plan.deletes` 里）。

## Non-Goals

- 不接活站点、不写 Frappe 运行时代码、**不生成运行时 Server Script**（红线 7）。
- 不实现 `execute_plan` 的真实执行、不实现 `export_customizations`、不实现 `schema_drift`、不实现 `SiteSnapshotSource.read`。
- **不改 `tests/gates/**` 任何文件**（红线 1），不用 `pytest_fixture_setup` 一类 hook 级绕道让门禁变绿
  （STATE §3 那行 `[open]` 的处置项 (d) 正在等人拍板，本 plan 不替人选）。
- **不改 `tools/gates/expected-red.txt`**：本 plan 不让任何门禁转绿，名单一行不动。
- 不改 `.github/workflows/**`、`missions/**`、`docs/masterplan/DECISIONS.md`、证据仓（`XM_PATH`）。
  `docs/masterplan/STATE.md` 仅在 Phase 3 的停手分支追加 §3 一行。
- **不把工作项 5 置为 `done`**：它绑定的门禁够不着（见 Current Baseline）。本 plan 只把它推进到 `planned`。
- 不改 `normalize` / `capture` / `diff` 的既有行为。

## Task Route

- Type: `app-layer design change`（新增公共模块 `agenerp.apply`，P2 的定制包 GitOps 会依赖它的形状）
- Owner Docs: `docs/architecture/module-boundaries.md` §11.1（差集 apply 引擎的真相源，读）、§11.5（快照与 diff 的结构边界，读）·
  `docs/masterplan/02-WBS.md` P0.5（判据，只读）·本 plan 要更新的 owner doc：`docs/architecture/module-boundaries.md`（**只追加一小节**）与 `docs/context/project-context.md`（若验证命令表需增行）
- Skill Selection Basis: `docs/skills/README.md` 的技能表里没有「设计纯函数差集引擎」对应的**工作方法**技能；
  形状被 §11.5 已定稿的 `Snapshot` / `Diff` 直接约束，属受限选择。各执行阶段 `Skill: none`；
  草案评审用 `docs/skills/plan-audit-prompt.md`，关闭审计用 `docs/skills/closure-audit-prompt.md`。

## Infrastructure And Config Prereqs

- 无新增依赖、无端口、无环境变量、无外部服务。**`agenerp.apply` 只用标准库 + 仓内既有模块。**
- 零依赖硬约束：CI 的 `gates-l1` 只 `pip install pytest`，因此**不得 `import yaml` 一类第三方库**。
- 回滚策略：一个新文件 + 两处委派改动 + 文档追加，`git revert` 即回到今天的状态；无迁移、无外部副作用、无数据改动。

## 结构边界（本 plan 定稿的接口契约）

按计划指南规则 6 的例外：这是**模块边界定义**，不是实现伪代码。

| 落点 | 契约 | 谁实现 |
|---|---|---|
| `agenerp/apply.py` · `read_pack(path) -> Snapshot` | 把定制包目录读成快照。**解析口径必须与 `OfflineSnapshotSource` 同源**（同一个载荷解析函数），不得另起一套 | 本 plan |
| `agenerp/apply.py` · `ApplyPlan` | 不可变值对象：`scope` / `creates: tuple[SnapshotEntry, ...]` / `updates: tuple[ChangedEntry, ...]` / `deletes: tuple[SnapshotEntry, ...]`，含 `is_empty()` 与人读的 `summary()`。**三个序列是判定面，`summary()` 不是** | 本 plan |
| `agenerp/apply.py` · `plan_apply(desired, current) -> ApplyPlan` | 纯函数，不做 I/O、不改入参。`desired` = 包，`current` = 站点现状。scope 不同时沿用 `SnapshotScopeMismatch` 拒绝。**参数序陷阱（起草时读活代码确认）**：`snapshot.diff(before, after)` 的 `added` = 只在 `after`、`removed` = 只在 `before`（`agenerp/snapshot.py:234-235`），因此正确调用是 `diff(before=current, after=desired)`——**与 `plan_apply` 自己的形参顺序相反**。映射：`added→creates` / `removed→deletes` / `changed→updates` | 本 plan |
| `agenerp/apply.py` · `execute_plan(plan, site) -> None` | **B 半的唯一落点**，本 plan 内 `raise NotImplementedError` 并在消息里指名工作项 6 与 STATE §3 那行 `[open]` | successor |
| `agenerp/pack.py` · `apply_pack(path, site)` | 保持签名与导入路径不变（门禁逐字 `from agenerp.pack import apply_pack`），改为委派：`read_pack` → `plan_apply` → `execute_plan`。**红因随之从「求差不存在」变成「执行未实现」** | 本 plan |
| `agenerp/snapshot.py` · `schema_drift` | 不动，仍 `raise`。它查物理表残留列，只有活站点答得出。⚠️ 代码里的 `NotImplementedError` 消息逐字写的是「工作项 5」（`agenerp/snapshot.py:246`），与本表归属不一致；**本 plan 不改那条消息**（改它会让红因文本漂移），归属以 roadmap 为准 | 工作项 6（与 B 半同一 successor） |

**导入方向**：`apply` → `snapshot` → `pack`。`pack.apply_pack` 反向用到 `apply` 时**在函数体内导入**，
避免 `pack` ↔ `apply` 顶层循环导入。这一条要有判据（Phase 2）。

## Execution Plan

### Phase 1 — 开工前置、包布局裁定、`agenerp/apply.py` 落盘

Status: completed
Targets: `agenerp/apply.py`、`agenerp/snapshot.py`（**仅**把载荷解析改为可复用的公开入口，不改其行为）
Skill: `none`

- Item Types: `Proof | Decision | Add | Fix`
- Prereqs: 无硬前置。工作项 4 的 B 半、工作项 6 都**不是**本 plan 的前置（本 plan 全程无活站点）

- [x] `Proof` **开工前置检查（第一步，不做完不许写代码）**：实跑并把命令原文 + 退出码记进 `docs/logs/2026/08-21.md`：
      `python3 tools/gates/check_expected_red.py`、`python3 -m pytest tests/unit -q`、`ruff check agenerp tests/unit tests/contracts`。
      三条**不写死期望数字**（名单会随别的 plan 变短）。若 `check_expected_red.py` 因 `PATH` 缺 `/usr/local/bin` 而报
      `docker` 找不到，按 `docs/logs/2026/08-21.md` 已记录的现象处理：加 `PATH="/usr/local/bin:$PATH"` 复跑一次并记下两次退出码，
      **不得改任何 `tests/gates/**` 文件去迁就它**。
      **同时记下开工基线 sha**：`git rev-parse HEAD` 的输出写进同一条日志，逐字标注「本 plan 开工基线」——
      Phase 3 的红线自查 `<base>` 取的就是它，不记就没有可复算的区间。
      - Skill: `none`
- [x] `Proof` 复核 `agenerp/apply.py` 确不存在。**若已存在**：读它的 git 来源（`git log --diff-filter=A -- agenerp/apply.py`），
      若是本 plan 自己的在途产物则续做并记明理由；若来自别的会话，**停手**并往 `docs/masterplan/STATE.md` §3 追加一行等人。
      - Skill: `none`
- [x] `Decision` **定制包的目录布局**。三个候选与取舍写进本项或 `module-boundaries.md` 追加小节：
      (a) `<root>/custom/<DocType>.json`（贴 Frappe `export_customizations` 的 `<app>/<module>/custom/` 惯例）；
      (b) `<root>/<scope>/<DocType>.json`（贴仓内既有 `OfflineSnapshotSource` 的 `<root>/<scope>/*.json`）；
      (c) 单文件 `<root>/pack.json`。
      **必须记录残余风险**：`export_customizations` 尚未实现（工作项 6），布局最终要与它产出的形状对齐；
      本 plan 选的布局若被工作项 6 推翻，代价是改 `read_pack` 一处 + 其单测，**不影响 `plan_apply` 的形状**。
      - Skill: `none`
- [x] `Add` 实现 `read_pack`：目录不存在 → 返回零条目快照（**不抛**，与 `OfflineSnapshotSource` 同口径）；
      载荷不是 JSON 对象 / 条目缺 `fieldname` → 显式报错（沿用既有错误口径，不静默跳过）。
      - Skill: `none`
- [x] `Add` 实现 `ApplyPlan` 与 `plan_apply`：由 `agenerp.snapshot.diff` 推导，
      **方向必须写死并有断言把守**——`current` 有而 `desired` 无 → `deletes`；`desired` 有而 `current` 无 → `creates`；两边都有但属性不同 → `updates`。
      - Skill: `none`
- [x] `Add` 落 `execute_plan` 的 `raise NotImplementedError`，消息里指名工作项 6 与 STATE §3 的 `[open]` 行。
      - Skill: `none`
- [x] `Fix` 把 `agenerp/snapshot.py` 的载荷解析暴露成可复用入口（**行为一字不改**），供 `read_pack` 调用。
      判据：改动前后 `python3 -m pytest tests/unit -q` 的既有 50 条一条不少、一条不红。
      - Skill: `none`

Exit Criteria:

- [x] `agenerp/apply.py` 存在，`read_pack` / `ApplyPlan` / `plan_apply` **有实体行为**（非占位 `return None`、非空函数体）；
      `execute_plan` 明确 `raise` 且消息指名后继
- [x] `python3 -c "import agenerp.apply"` 退 0，且零第三方依赖（Phase 2 有判据）
- [x] 既有 `tests/unit` 全部仍绿，`tools/gates/expected-red.txt` 一行未动
- [x] 相关 owner doc 更新推迟到 Phase 3（本阶段 `No owner-doc update required`）
- [x] `docs/logs/` 记录前置检查三条命令的原文与退出码，**且含 `git rev-parse HEAD` 的开工基线 sha**（Phase 3 的 `<base>` 依赖它）

### Phase 2 — 把行为固化成判据（`tests/unit/`）

Status: planned
Targets: `tests/unit/test_apply_plan.py`
Skill: `none`

- Item Types: `Proof`（5/5 全为 Proof）
- Prereqs: Phase 1

- [ ] `Proof` **反 upsert 回归（承重条款）**：构造「包里没有、站点上有」的字段 → 断言它出现在 `plan.deletes` 中。
      这条断言的失败信息必须点名 §11.1 的实测结论（`sync_customizations` 纯 upsert、revert 无效），
      让将来读到红的人一眼知道它守的是什么。
      - Skill: `none`
- [ ] `Proof` 方向不可颠倒：同一对快照互换 `desired` / `current`，`creates` 与 `deletes` 必须互换而不是同时为空。
      - Skill: `none`
- [ ] `Proof` 幂等与空计划：`plan_apply(s, s).is_empty()` 为真；scope 不同抛 `SnapshotScopeMismatch`；
      `plan_apply` 不改入参（调用前后两个 `Snapshot` 仍相等）。
      - Skill: `none`
- [ ] `Proof` `read_pack` 的三条边界：目录不存在 → 零条目；易变字段（`modified` / `creation` / `owner` / `_comments`）
      **不进条目**（与 `normalize` 同口径）；条目缺 `fieldname` → 显式报错。
      - Skill: `none`
- [ ] `Proof` 零依赖与导入方向。⚠️ **必须在全新子进程里测，不许在当前 pytest 进程里做模块集合求差**——
      同一进程里 `agenerp.apply` 可能已被别的测试模块导入，`sys.modules` 前后求差会恒为空，
      断言就成了本仓反复禁止的**假判据**（永远绿、什么也没测）。落法：
      `subprocess.run([sys.executable, "-c", ...], capture_output=True)`，子进程里 import 后
      打印 `sys.modules` 的顶层名集合，父进程断言「不属于 `sys.stdlib_module_names`、不是 `agenerp`、
      不是解释器自带的启动模块」的残余为空。
      同一手法再跑两个子进程覆盖导入顺序：先 `agenerp.pack` 后 `agenerp.apply`、以及反序，
      **两个子进程都必须 returncode 0**（挡住 `pack` ↔ `apply` 循环导入回归）。
      三个子进程的 `returncode` 都要进断言，不许只看 stdout。
      - Skill: `none`

Exit Criteria:

- [ ] `python3 -m pytest tests/unit -q` 退 0，且新文件的断言数 > 0（把实际条数记进日志，不写死在本行）
- [ ] `ruff check agenerp tests/unit tests/contracts` 退 0
- [ ] **变异实测**：至少对 `plan_apply` 的删除分支做一次真改文件的反向变异（如把 `deletes` 恒置空），
      确认新判据**真的转红**，再 `git checkout` 还原并用 `git diff --quiet` 证明还原干净。命令原文与退出码进日志
- [ ] `No owner-doc update required`（文档在 Phase 3）
- [ ] `docs/logs/` 更新

### Phase 3 — 委派链、文档、roadmap 写入、日志

Status: planned
Targets: `agenerp/pack.py`（仅 `apply_pack` 函数体）、`docs/architecture/module-boundaries.md`（**只在 §11 末尾追加一小节**）、`docs/backlog/p0-foundation-roadmap.md`、`docs/logs/2026/08-21.md`、`docs/masterplan/STATE.md`（**仅停手分支追加 §3 一行**）
Skill: `none`

- Item Types: `Add | Proof | Decision`
- Prereqs: Phase 1、Phase 2

- [ ] `Add` 把 `agenerp/pack.py` 的 `apply_pack` 改成委派（函数体内导入 `agenerp.apply`），
      **签名与导入路径一字不改**。判据：`python3 -c "from agenerp.pack import apply_pack"` 退 0；
      且门禁 `test_removing_from_pack_actually_deletes_on_site` 的红因仍在 fixture 层
      （`live_site` 的 `NotImplementedError`），**不是**被本改动改成了别的红。
      - Skill: `none`
- [ ] `Proof` 红线自查（区间 diff，基线取本 plan 开工前的 sha）：
      `git diff --name-only <base>..HEAD -- tests/gates/ .github/workflows/ missions/ tools/gates/ docs/masterplan/DECISIONS.md` → **必须为空**；
      `git diff --numstat <base>..HEAD -- docs/masterplan/` → 若非空则只允许 `STATE.md` 且删除行数为 0。
      命令原文与退出码进日志。
      - Skill: `none`
- [ ] `Add` `docs/architecture/module-boundaries.md` §11 末尾**追加**一小节「差集 apply 引擎在本仓的落点（A 半）」：
      落点表、包布局裁定与备选、方向约定、`execute_plan` 接缝归属、**以及「本 plan 未让任何门禁转绿」这一事实**。
      只追加，不改已有行。
      - Skill: `none`
- [ ] `Decision | Add` **自带 roadmap 写入落点**：把 `docs/backlog/p0-foundation-roadmap.md:24` 的工作项 5
      置 **`planned`**（若起草步已置则为空操作，**幂等**）。**不得置 `done`**：其绑定门禁被红线 1 挡着。
      起草评审时逐字复核过两处引擎产物，结论要写准，不许含糊：
      `docs/skills/closure-audit-prompt.md` 里 `roadmap` 出现 **0 次**（`grep -c` 实测），关闭审计**不**被指示写 roadmap；
      而 `tools/mission-driver/prompts/execute.md` 第 4.b 条**确实**指示写 roadmap，但它逐字要求
      「change the work item from ❌ to ✅」——**那一条本 plan 不执行**，理由与下节 `Plan Status` 同源（见「`Plan Status` 由谁写」）。
      本项落的是 `planned`，不是 ✅。
      - Skill: `none`
- [ ] `Proof` 判据可达性如实复核：跑 `python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q --tb=line`，
      把「四条仍红、红在 fixture 的 `NotImplementedError`」的原文与退出码记进日志。
      **起草评审时实跑过一次，基线形态是 `4 errors`（`ERROR at setup`，逐字 `NotImplementedError: live_site 尚未实现 …`），
      不是 `4 failed`**；若执行时看到的形态与此不同，那是漂移，按红因变化处理而不是照抄本行——
      这是「本 plan 没有偷偷让判据变绿、也没有伪装成关闭了工作项」的证据。
      - Skill: `none`
- [ ] `Add` `docs/logs/2026/08-21.md` 追加条目：命令原文 + 退出码 + commit sha，写明**只交付 A 半、工作项 5 停在 `planned`**。
      - Skill: `none`
- [ ] `Proof` **停手分支（条件触发，不触发就明确写「未触发」）**：若执行中发现 A 半也需要碰 `tests/gates/**` 才能自证，
      **立刻停手**，往 `docs/masterplan/STATE.md` §3 **追加**一行（不改已有行），置 `Plan Status: deferred` 并写明重开条件。
      - Skill: `none`

Exit Criteria:

- [ ] `apply_pack` 已委派且导入路径不变；roundtrip 门禁四条仍红且红在 fixture 层（有命令原文与退出码为证）
- [ ] 红线自查三条命令输出如实记录，`tests/gates/**` 与 `tools/gates/expected-red.txt` 零改动
- [ ] `docs/architecture/module-boundaries.md` 只追加（`git diff --numstat` 的删除列为 0）
- [ ] roadmap 工作项 5 = `planned`（不是 `done`）
- [ ] `docs/logs/` 更新，含命令原文 + 退出码 + sha

## `Plan Status` 由谁写（写死，免得烧循环）

沿用 plan `2026-08-21-1022-1` 已查实的步序（`flows/plan-execution.json`：`EXECUTE → CLOSURE_SCRIPT_CHECK →（fail）CLOSURE_AUDIT → BUILD_VERIFY → GATE_VERIFY`）：

- `EXECUTE`（Phase 1–3）：只打勾执行项与 Exit Criteria，`Plan Status` **保持 `active`**，`## Closure Gates` 九框**保持未勾**。
- `CLOSURE_AUDIT`（独立审计会话）：通过 → 勾九框 + 置 `completed` + 补 `## Closure` 证据 + 确认 roadmap 工作项 5 为 `planned`；
  不通过且需改代码 → 保持 `active`；不通过且阻塞于人 → 置 `deferred` 并写明重开条件。
- ⚠️ 不得为了让 `CLOSURE_SCRIPT_CHECK` 变绿而在 `EXECUTE` 阶段勾九框——其中两框在那一步为假，勾上即自证关闭
  （违反 `AGENTS.md` 裁判规则 1/2 与计划指南规则 13）。
- ⚠️ `tools/mission-driver/prompts/execute.md` 第 4.a 条逐字要求「Update the plan's `Plan Status` to `completed`」——
  那是上游模板默认，按 `AGENTS.md` 开头声明的次序低于裁判规则 1/2，**不执行**。矛盾原文记在此处，不擅自消解。
- ⚠️ 同一文件第 4.b 条逐字要求「change the work item from ❌ to ✅」——**同样不执行**。
  工作项 5 绑定的门禁 `test_removing_from_pack_actually_deletes_on_site` 被红线 1 挡着，loop 无权让它转绿；
  把它标成 ✅ 就是裁判规则 1 明禁的「自报通过」。本 plan 只把它写到 `planned`。
  这两条与 4.c（无 `> Source Audits:` 行，整步略过）一并如实记在此处，由人裁定要不要改上游模板。

## Draft Review Record

- Independent draft review iteration 1: `accept`（`MISSION_DRIVER:2026-08-21-155943-mission-driver` 的独立评审步，与起草会话分离）
  after 逐条对**评审时的 HEAD `d6672cc`**（起草时为 `494440d`，其间循环另有提交推进；
  本 plan 涉及的 `agenerp/**` / `tests/gates/**` / `tools/gates/expected-red.txt` 在两个 sha 之间无差异，
  故 Current Baseline 的结论仍然成立）的活代码复核基线并就地修掉以下问题：
  (1) Phase 1 的 `Item Types` 漏了实际存在的 `Fix` 项（指南规则 7）；
  (2) Phase 3 红线自查的 `<base>` 没有任何执行项负责记录 → 在 Phase 1 首个 `Proof` 加 `git rev-parse HEAD` 并写进该阶段 Exit Criteria；
  (3) Phase 2 的零依赖断言原写法在同一 pytest 进程里对 `sys.modules` 求差，会恒为空 → 改判为**子进程实测**，避免落成假判据；
  (4) 「没有任何引擎产物被指示写 roadmap」是过头论断——`prompts/execute.md` 第 4.b 条确实指示写，且要求写 ✅ →
  改成如实陈述，并把该条与 4.a 一并登记为「已知矛盾、不执行」；
  (5) 补上 `snapshot.diff` 的**参数序陷阱**（`diff(before=current, after=desired)`，与 `plan_apply` 形参顺序相反），
  这是本 plan 最容易写反且单测能抓到的一处；
  (6) 校正三处行号漂移与 `schema_drift` 归属不一致（代码消息写「工作项 5」、本表写「工作项 6」）。
  基线核实项：`agenerp/apply.py` 确不存在 · `tests/unit` 现为 50 条且全绿 · `expected-red.txt` 现 7 行 ·
  roadmap `:24` 工作项 5 = `todo` · STATE `:182` 的 `[open]` 行在位 · `flows/plan-execution.json` 的步序与本 plan 所述一致 ·
  `missions/p0-foundation.json` 的 `commands.test` 逐字包含 `python3 -m pytest tests/unit -q`（本 plan 判据落在复跑面内）。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned
- [ ] verification has run（`python3 tools/gates/check_expected_red.py`、`python3 -m pytest tests/unit -q`、`ruff check agenerp tests/unit tests/contracts`、`python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q --tb=line`，逐条记退出码）
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件（无 build、无 typecheck、L2 门禁未解锁），关闭记录必须逐字写明「verification scope limited」
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### B 半：`execute_plan` 对站点执行删除（工作项 5 的绑定门禁）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它要的 `live_site` / `pack_repo` 两个 fixture 全在 `tests/gates/conftest.py`（红线 1），
  loop 无权实现；已由 `docs/masterplan/STATE.md` §3 一行 `[open]` 登记，四个处置项 (a)/(b)/(c)/(d) 只有人能选。
  本 plan 关闭时工作项 5 置 **`planned`（不是 `done`）**，因此不存在「把没做完的活报成 done」。
- Successor Required: `yes` —— 工作项 5 的第二个 plan（roadmap 规则允许一个工作项 1–2 个 plan），
  它要自带 `planned → done` 的 roadmap 写入落点。
- 重开事件：人对 STATE §3 那行 `[open]` 的 (a)/(b)/(c)/(d) 作出选择之后。

### `schema_drift` 孤儿列巡检（§11.1 第三个部件）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它查的是**物理表残留列**，无活站点即无答案；roadmap 把它归在工作项 5/6 的 L2 断言
  `test_no_orphan_column_left_behind`，与 B 半同一把锁。现在实现只能得到「结构存在」的空断言，那正是本仓反复禁止的假判据。
- Successor Required: `yes` —— 与 B 半同一个 successor
- 重开事件：同上。

### 定制包目录布局可能被 `export_customizations` 推翻

- Classification: `watch-only residual`
- Why Not Blocking Closure: `export_customizations`（工作项 6）尚未实现，包的真实产出形状还没有活证据。
  Phase 1 的 `Decision` 已把三个候选、选择理由与残余风险写进 `module-boundaries.md`；
  **可逆成本低**：改 `read_pack` 一处 + 其单测，`plan_apply` 的形状不受影响。
- Successor Required: `no`
- 重开事件：工作项 6 实现 `export_customizations` 并拿到 Frappe 的真实产出形状时。

### `02-WBS.md` 与 roadmap 的顺序/前置冲突（冲突 4.2）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已由 `docs/backlog/needs-human-expected-red-handoff.md` 冲突 4.2 登记为 `open`，明写需人对齐。
  本 plan 只采信 P0.5 的交付描述并如实记下其前置列，不替人消解。
- Successor Required: `no`（人动作）
- 重开事件：人对齐 WBS 与 roadmap 顺序时。

## Closure

Status Note: 待独立关闭审计填写。

Closure Audit Evidence:

- Auditor / Agent: 待填（必须与 `EXECUTE` 会话分离）
- Evidence: 待填（命令原文 + 退出码 + commit sha）

Follow-up:

- 待填（确认缺陷不得出现在此处）
