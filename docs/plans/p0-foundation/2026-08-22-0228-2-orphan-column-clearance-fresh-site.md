# 2026-08-22-0228-2 孤儿列清除面在**全新站点**上不成立：先取证复现，再修 `agenerp`

> Plan Status: draft
> Mission: p0-foundation
> Work Item: 6. 定制包往返删除验证（活站点端到端）—— 承接 `::test_no_orphan_column_left_behind`
> Last Reviewed: 2026-08-22
> Source: plan `2026-08-22-0027-2` 的 `## Deferred But Adjudicated` 第一条逐字要求的
>   **blocking successor**；`docs/masterplan/STATE.md` §3 的 2026-08-22 `[open]` 停机行。
> Related: `2026-08-22-0228-1-gate-verdict-failure-forensics.md`（前驱，提供本机取证出口；**不是硬前置**——
>   本 plan 的取证主路是本机冷起复现，见 Phase 1）·
>   `2026-08-21-2220-1-schema-drift-orphan-columns.md`（巡检 + 清除两半的交付者，本 plan 修的就是它的清除面）·
>   `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（`deferred`，本 plan 落地即满足它的 Reopen When）
> Execution Order: **2 / 2** —— 排在 `0228-1` 之后是因为那个 plan 便宜、零 CI，且能让本机取证少走一步；
>   **但本 plan 不阻塞于它**：`0027-2` 与 Protected Areas 要的「实跑前后全量 `capture` 对照」
>   本来就是**站点侧的本机证据**，不需要 CI 日志。
> Audit: required

## Current Baseline

以下每一条都是 2026-08-22 在 `10c737c` 上实测或从 CI 日志逐字抄来的。

- **红是可复现的，不是抖动。** CI run `32509351108`（PR #1，head `9a8832f`，分支
  `ci/0027-2-l2-full-live-gate`）两次 attempt（第二次是 `gh run rerun --failed` 原样复跑）
  **都**打出 `门禁 19 项：红 1，绿 18，跳过 0`，都逐字点名
  `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`。
  裁判规则 3 的「不可复现」分支**不适用**。
- **本机与 runner 表现不同，且方向与起草时的推理相反。** 本机常驻站点（本轮实测已 `Up 3 hours`，
  历史孤儿列 5–6 条）6 跑红 1 次；runner 的**全新**站点 2 跑红 2 次。
  `0027-2` 起草时写的「runner 没有历史孤儿列，方向恰好有利」**被实测证伪**。
- **红因当前是未知的，不许猜。** CI 日志里只有判定器的三行输出加一条 nodeid：判定器
  `tools/gates/check_expected_red.py:66-76` 以 `--tb=no` 起 pytest、`capture_output=True` 吃掉输出、
  解析完 `JUNIT.unlink()` 删报告。所以**连「是断言失败还是 `OobError`」都答不出**。
  这正是前驱 plan `0228-1` 要补的面。
- **被指控的实现面在哪（三段，任何一段都可能是红因，本 plan 开工前不预设）**：
  ① `agenerp/pack.py:153-186` `apply_pack` → `read_pack` → `capture` → `plan_apply` →
  `narrow_deletes(plan, pack_doctypes(path))` → `execute_plan`；
  ② `agenerp/apply.py` `execute_plan` 末尾调 `drop_orphan_columns(deleted, site, runner=runner)`，
  **且只在 `plan.deletes` 非空时才走到**（`if not plan.deletes: return` 在它之前）；
  ③ `agenerp/apply.py` `drop_orphan_columns` 把清除面收窄到
  「本次删掉的 fieldname ∩ `schema_drift(doctype)`」，再交 `agenerp/oob.py` `drop_columns` 发 DDL。
- **`schema_drift` 的口径是带外调的 Frappe 自己的函数。** `agenerp/snapshot.py:325-353` 走
  `agenerp/oob.py` 的 `run_json(TRIM_TABLE, …)`，`ALLOWED_CALLS` 把 `dry_run` 钉死为 `True`。
  站点答不上话时抛 `OobError`，不返回空元组。
- **这条门禁对「巡检坏掉」零覆盖（已登记的假绿面）。** `2026-08-21-2220-1` 的变异验证结论：
  把 `schema_drift` 改成返回空 → 门禁**绿**而物理列一列没删。所以**「让门禁变绿」不等于「修好了」**，
  本 plan 的证明必须包含独立于门禁的物理列证据。
- **DDL 不可逆。** `agenerp/oob.py` `drop_columns` 直发 `ALTER TABLE … DROP COLUMN`，
  `docs/context/project-context.md` 的「带外容器命令」行逐字要求动它之前先
  `docker compose exec -T backend bench --site frontend backup`。
- **停机线现状**：`AGENTS.md` 裁判规则 4 的「CI 连续 2 轮红」已触发，`0027-2` 已 `deferred`；
  其 Closure Audit Log 第四条另记了「停机后空转 4 轮」的成本停机线风险。本 plan 因此对 CI 实跑设硬上限。
- **⚠️ 推分支的唯一合法形态：只把 `agenerp/**` 的修复 cherry-pick 上去，绝不把 `main` 合进分支。**
  分支上的 `verdict-tool-untouched` 比的是 `git diff --name-only $BASE $HEAD -- tools/gates/check_expected_red.py …`，
  `$BASE` 取 `github.event.pull_request.base.sha`，而 PR #1 的 `baseRefOid` **钉在 `7b0f585`**
  （`gh pr view 1 --json baseRefOid,headRefOid` 实测），不随 `origin/main` 走。
  `git diff` 比的是两棵树，所以「main 有而分支没有」同样算命中——
  **把 `main`（含前驱 plan 的判定器改动）合进分支会必然点亮该 job**，而放行只能靠人工
  `^Gates-Change-Approved-By:` trailer，AI 自加即伪造。`7b0f585` 与分支都不含判定器改动，
  只 cherry-pick `agenerp/**` 时该 diff 为空，job 保持 `success`（前两次 attempt 实测均 `success`）。
- 本机 `main`（`10c737c`）比 `origin/main`（`3425dae`）**领先 6 个提交**，未推。本 plan 不推 `main`。

## Goals

1. **先证明红因，再动代码。** 拿到 `::test_no_orphan_column_left_behind` 在**全新站点**上的红因原文
   （断言原文 / 异常类型 / `agenerp.apply` 的 WARNING），写成可复述的事实，**不猜**。
2. **修 `agenerp` 侧那一处**，让该门禁在**全新站点**上稳定绿。
3. **不迁就 runner**：修完之后本机**常驻站点**上的 live 整目录判定必须仍绿。
4. **带上 `0027-2` 指名要的证据**：实跑前后**全量 `capture` 对照**，证明这次 apply 的影响面
   恰好只有探针，方向是「减少」不是「新增」。

## Non-Goals

- **不改 `tests/gates/**`**（红线 1）。门禁是裁判，红了改实现不改判据。
- **不划 `tools/gates/expected-red.txt`**：默认判定环境无 `AGENERP_LIVE`，L2 恒红，
  口径以人在 STATE §2（2026-08-21T11:20Z）的裁定为准。
- **不置任何 roadmap 工作项为 `done`**：`done` 要求「从预期红名单划掉」，该条件在此不可满足
  （与工作项 4/5/7/8/9 同一情形）。
- **不合并 PR #1**（人决定），不补 `0027-2` 欠的 `verdict-tool-untouched` 三次变异实证。
- **不动 `tools/gates/check_expected_red.py`**（前驱已改完，本 plan 只消费）。
- **不改 `.github/workflows/**` 一行**（`ai-autonomy-policy.md:84` 定级 `blocked | 人工批准`）。
  本 plan 只往既有分支推 `agenerp/**` 的提交，不新增/不修改任何 job、step、触发面。
- **不推 `main`**（本机 `main` 领先 `origin/main` 6 个提交，推不推由人决定）。
- 不顺手清理本机站点上那 5 条历史孤儿列——它们归
  `docs/backlog/gate-fixtures-pollute-the-live-site.md`。

## Task Route

- Type: `bug investigation` → `implementation-only change`
- Owner Docs: `docs/architecture/module-boundaries.md` §11.6（差集 apply 的落点与收窄裁定）·
  §11.8（带外容器命令传输）· `docs/context/project-context.md` Verification Commands
  「L2 live 门禁（定制包往返）」与「L2 live 门禁（**整目录判定**）」两行
- Skill Selection Basis: `docs/skills/README.md` 的 `bug-diagnosis-prompt.md` 逐字适用于
  「bug 是真的但根因尚未证明」，正是 Phase 1；Phase 3 的证明面用
  `verification-before-completion` 纪律（证据先于断言），无对口 prompt 文件时记 `none`。

## Infrastructure And Config Prereqs

- 本机 docker 栈（`docker-compose.yml`）；端口 **18080**（8080 被本机另一套常驻 ERPNext 栈占着，
  `compose_stack` 有端口预检会直接 fail）。
- live 门禁 env 四件套：`AGENERP_LIVE=1` / `AGENERP_SITE=frontend` /
  `AGENERP_SITE_URL=http://127.0.0.1:18080` / `AGENERP_ADMIN_PASSWORD=admin`。
- **冷起前先备份**：`docker compose -f docker-compose.yml exec -T backend bench --site frontend backup`
  （DDL 不可逆）。
- `gh` 已认证；推 `ci/0027-2-l2-full-live-gate` 的权限。
- 回滚策略：`agenerp/**` 的改动是纯代码，回滚 = `git revert`。站点侧只做 `down -v` 冷起，
  不对**常驻**站点做破坏性操作；若必须动，先跑上面那条 `bench backup`。

## Execution Plan

### Phase 1 - 复现与取证（**不猜根因**）

Status: planned
Targets: 无代码改动
Skill: `bug-diagnosis-prompt.md`

- Item Types: `Proof`（本阶段 5 项全部 `Proof`，按 Minimum Rule 7 在阶段层声明）
- Prereqs: 无硬前置。前驱 `0228-1` 若已落地，本机 `tools/gates/explain_last_gate_failures.py` 可直接打出红因原文，
  少走一次手工 `-vv` 复跑；未落地也不阻塞——本阶段的取证主路是本机冷起 + `pytest -vv`。

- [ ] `Proof`：**本机冷起复现**——`docker compose -f docker-compose.yml down -v` 后
      `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`，
      再单跑该文件：`… python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -vv`。
      全新站点是 runner 条件在本机最接近的等价物。抄下退出码与**完整** traceback。
- [ ] `Proof`：把 `agenerp.apply` 的 WARNING 打开（`-o log_cli=true --log-cli-level=WARNING` 或等价方式）
      再跑一次，记录 `narrow_deletes` / `drop_orphan_columns` 的跳过日志逐条原文。
      这直接回答「删除集是不是被收窄没了」与「哪几列被判为非孤儿」。
- [ ] `Proof`：**实跑前后全量 `capture` 对照**（`0027-2` 指名要的证据）——
      apply 前后各做一次全量 `capture(PACK_SCOPE, source=SiteSnapshotSource(site))`，
      记录差集；同时用 `information_schema` 独立交叉验证 `tabItem` 上探针列的物理存在性
      （不经 `schema_drift`，避开已登记的假绿面）。
- [ ] `Proof`：**分流**——把红因归到下面三档之一并写明依据：
      (a) 断言失败且探针列确实还在表上；(b) `OobError`（带外命令没跑起来 / 非零退出 / 载荷不是 JSON）；
      (c) 走都没走到清除面（`plan.deletes` 为空，被 `narrow_deletes` 收窄掉）。
      **三档的修法完全不同**，不分流就动代码等于猜。
- [ ] `Proof`：若本机冷起**复现不出来**（3 跑全绿）→ 逐字记「本机冷起不可复现」，**不猜根因**（裁判规则 3），
      并**不得**据此认为问题已消失（runner 上 2 跑红 2 次是已实测的事实）。
      此时唯一可走的取证路是 CI，而 CI 取证面归 `0228-1` 的 `## Human Handoff`（需要人解停机线 / 出 trailer）——
      本 plan 按 `## Deferred But Adjudicated` 的固定处置置 `deferred` 并把这一事实写进 STATE §3，
      **不自行推分支跑 CI 碰运气**。

Exit Criteria:

- [ ] 红因被归入 (a)/(b)/(c) 之一，依据是命令原文 + 退出码 + 输出，不是推断
- [ ] 前后全量 `capture` 对照 + `information_schema` 交叉验证两份证据在案
- [ ] No owner-doc update required（本阶段不改行为）
- [ ] `docs/logs/2026/08-22.md` 更新

### Phase 2 - 按证据修实现

Status: planned
Targets: `agenerp/apply.py` · `agenerp/oob.py` · `agenerp/snapshot.py`（**只改 Phase 1 分流指到的那一处**）· `tests/unit/`
Skill: `none`

- Item Types: `Fix | Proof`
- Prereqs: Phase 1 完成且分流结论明确

- [ ] `Fix`：只改分流指到的那一处。**不做与红因无关的顺手优化**（北极星条款）。
      改动前在本项下写明：改哪个函数、为什么这一处、以及它如何解释「本机 6 跑红 1 次、runner 2 跑红 2 次」
      这个已实测的差异——解释不了就说明分流没做完，回 Phase 1。
- [ ] `Fix`：若红因落在 (b)/(c) 档，**不得**用「吞掉异常」或「放宽收窄」的方式让门禁变绿——
      两者都会重新制造 `2026-08-21-2220-1` 已登记的假绿面。收窄若确需放宽，
      必须在 `module-boundaries.md` §11.6 追加裁定并写清作用域上界。
- [ ] `Proof`：`tests/unit/` 补一条**对着红因**的判据（不是对着门禁），
      命令 `python3 -m pytest tests/unit -q` → exit 0。
- [ ] `Proof`：`ruff check agenerp tests/unit tests/contracts` → exit 0；
      `python3 -m pytest tests/contracts -q` → exit 0。

Exit Criteria:

- [ ] 改动面 ≤ Phase 1 分流指到的一处，且能解释本机/runner 的差异
- [ ] 单测与契约测试全绿，lint 干净
- [ ] `docs/architecture/module-boundaries.md` §11.6 或 §11.8 追加实测结论（**追加，不改写**）
- [ ] `docs/logs/2026/08-22.md` 更新

### Phase 3 - 三面证明（全新站点 / 常驻站点 / 变异）

Status: planned
Targets: 无代码改动
Skill: `none`

- Item Types: `Proof`（全部）
- Prereqs: Phase 2 完成

- [ ] `Proof`：**全新站点**——`down -v` 冷起后跑 live 整目录判定
      `… python3 tools/gates/check_expected_red.py` → 期望 `门禁 19 项：红 0，绿 19，跳过 0` / exit 0，
      **连跑 3 次全绿**（前驱 `0027-1` 实测过这条门禁有间歇性，1 跑不算数）。
- [ ] `Proof`：**常驻站点**——不 `down -v`，在已跑过多轮的站点上跑同一条命令 → exit 0。
      这一条是「不迁就 runner」的判据：只在全新站点绿说明修法可能只对空表成立。
- [ ] `Proof`：**变异验证**——把 Phase 2 的修复点改回改动前的形态 → 该门禁必须**逐字转红**
      且点名集合恰好多出 `::test_no_orphan_column_left_behind` 一条；复原后复跑回 exit 0。
      牙齿在这里；变异不红就说明修的不是红因。
- [ ] `Proof`：**物理列的独立证据**——修复后再做一次 `information_schema` 查询，
      确认探针列确实不在 `tabItem` 上，且**本机那 5 条历史孤儿列一条不少**（作用域方向是「减少」不是「扩大」）。

Exit Criteria:

- [ ] 全新站点 3 跑全绿、常驻站点 1 跑绿，命令原文与退出码在案
- [ ] 变异验证有牙齿，点名集合精确
- [ ] 历史孤儿列未被误删（列表前后对照在案）
- [ ] `docs/logs/2026/08-22.md` 更新

### Phase 4 - CI 实跑与回写（**硬上限 2 次实跑**）

Status: planned
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`（§2/§3 追加行）· `docs/context/project-context.md`
Skill: `none`

- Item Types: 共 6 项 —— `Decision` 1、`Fix` 3、`Proof` 2
- Prereqs: **Phase 3 三面证明全绿**（硬前置，未全绿不得推分支）

- [ ] `Decision`（**草案评审阶段已裁定，执行时照做**）：本阶段跑 CI 是**合法**的，理由是它逐字满足
      STATE §3 那条 `[open]` 停机行自己写死的重开条件（「successor 修好 `agenerp` 侧清除面后，
      往分支推一次，`gates-l2-live` 在 PR 上 `success`」）。**Phase 3 三面证明全绿是硬前置**——
      没跑绿就推分支，等于在停机状态下碰运气，本 plan 明令禁止。
      备选（推迟到人显式解停机线再推）被排除：那会让停机永远等不到它自己写的重开事件。
      残余风险：仍可能红，缓解是硬上限 2 次实跑 + 红即停机不重试第三次。
      - Skill: `none`
- [ ] `Fix`：推分支的形态**只能是把 `agenerp/**` 的修复 cherry-pick 到 `ci/0027-2-l2-full-live-gate`**，
      **不得 merge / rebase `main` 进分支**（会点亮 `verdict-tool-untouched`，见 Baseline）。
      推之前实跑 `git diff --name-only 7b0f585 <branch-head> -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
      确认**无输出**，把命令与输出抄进本 plan。
- [ ] `Proof`：推分支触发 CI，读 `gates-l2-live` 的结论。**上限 2 次实跑**（首跑 + 必要时 1 次原样复跑）。
      绿：记 run id / job id / sha。红：**先原样复跑一次**（裁判规则 3），仍红则按固定处置停机，
      **不猜根因**，把前驱取证步骤打出的红因原文追加进 STATE §3。
- [ ] `Fix`：绿之后**就地改准**两处已确认的 owner-doc 漂移（Minimum Rule 14，不降级）——
      `docs/context/project-context.md` 与 roadmap「5 现状」/「6 现状」/「9 现状」三行里
      「红因是 `::test_no_orphan_column_left_behind`、CI 上不成立」的表述已被本 plan 推翻，
      须就地改准并注明改准日期与依据 run id。
- [ ] `Fix`：在 `2026-08-22-0027-2-…md` 的 `Closure Audit Log` **追加**一行
      （只追加，不改写任何既有行）说明其 `Reopen When` 已满足；**不替它改 `Plan Status`**——
      那是它自己 Reopen 之后续跑的事。
- [ ] `Proof`：在 `docs/masterplan/STATE.md` §2 追加一条证据行
      （时间 · WBS 行 ID · 命令→退出码 · sha · 下一项），§3 那条 `[open]` 行下方追加处置事实行。

Exit Criteria:

- [ ] `gates-l2-live` 在 CI 上 `success`，或红且已按固定处置停机并留痕（run id / job id / sha 三件套在案）
- [ ] `verdict-tool-untouched` 仍 `success`；`git diff --name-only 7b0f585 <branch-head> -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs` 无输出
- [ ] CI 实跑次数 ≤ 2（`gh run list --branch ci/0027-2-l2-full-live-gate` 前后条数差在案）
- [ ] roadmap 三行 + `project-context.md` 的确认漂移已就地改准
- [ ] `0027-2` 的 Closure Audit Log 有追加行，其既有行一字未改
- [ ] STATE §2/§3 有追加行；`docs/masterplan/DECISIONS.md` 一行未动
- [ ] `docs/logs/2026/08-22.md` 更新

## Draft Review Record

- Independent draft review iteration 1: <pending>

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（roadmap 三行 · `project-context.md` · `module-boundaries.md` · STATE · `0027-2` 追加行）
- [ ] verification has run：本机冷起 3 跑 live 整目录判定 · 常驻站点 1 跑 · 变异验证 · `pytest tests/unit` · `pytest tests/contracts` · `ruff` · CI `gates-l2-live`
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件，须显式写明「verification scope limited」
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **`0027-2` 指名的证据在案**：实跑前后全量 `capture` 对照 + 修完后本机 live 整目录判定仍绿
- [ ] `git diff` 未触及 `tests/gates/**`、`tools/gates/expected-red.txt`、`docs/masterplan/DECISIONS.md`、`missions/**`

## Deferred But Adjudicated

### 取证拿不到可分流证据时的固定处置

- Classification: `watch-only residual`
- Why Not Blocking Closure: 失败分支的写死处置，不是被推迟的工作项。
- 处置逐字：记录所有已跑命令与输出 → 追加进 STATE §3（不改写既有行）→ 本 plan 置 `deferred`
  并在文件头写明重开条件 → **不改一行 `agenerp/`**、**不猜根因**。
- Successor Required: `no`

### 本机站点上那 5 条历史孤儿列

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它们由门禁 fixture 每轮留下，修法在 `tests/gates/conftest.py`（红线 1），只有人能做。
- Successor Required: `no`（归 `docs/backlog/gate-fixtures-pollute-the-live-site.md`）
- 重开事件：见该文档自身的触发条件。

### 门禁对「巡检坏掉」零覆盖（已登记的假绿面）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 补它要改 `tests/gates/**`（红线 1）或新增门禁（要人批，走 `Gates-Change-Approved-By:`）。
  本 plan 的代偿是 Phase 1/3 两次独立于 `schema_drift` 的 `information_schema` 交叉验证。
- Successor Required: `no`
- 重开事件：人批准新增一条针对巡检面的门禁时。

### PR #1 未合并

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 合不合由人决定；本 plan 只负责把 `gates-l2-live` 在分支上跑绿。
- Successor Required: `no`
- 重开事件：人决定合并 PR #1 时。

## Closure

Status Note: <待关闭审计填写>

Closure Audit Evidence:

- Auditor / Agent: <待填>
- Evidence: <待填>

Follow-up:

- <待填；确认的缺陷不得写在这里>
