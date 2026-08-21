# 2026-08-22-0228-2 孤儿列清除面在**全新站点**上不成立：先取证复现，再修 `agenerp`

> Plan Status: completed
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
3. **不迁就 runner**：修完之后本机**多轮累积站点**（非空表）上的 live 整目录判定必须仍绿——
   只在空站点绿说明修法可能只对空表成立。
4. **带上 `0027-2` 指名要的证据**：实跑前后**全量 `capture` 对照**，证明这次 apply 的影响面
   恰好只有探针，方向是「减少」不是「新增」。

## Non-Goals

- **不改 `tests/gates/**`**（红线 1）。门禁是裁判，红了改实现不改判据。
- **不划 `tools/gates/expected-red.txt`**：默认判定环境无 `AGENERP_LIVE`，L2 恒红，
  口径以人在 STATE §2（2026-08-21T11:20Z）的裁定为准。
- **不置任何 roadmap 工作项为 `done`**：`done` 要求「从预期红名单划掉」，该条件在此不可满足
  （与工作项 4/5/7/8/9 同一情形）。
- **不合并 PR #1**（人决定），不补 `0027-2` 欠的 `verdict-tool-untouched` 三次变异实证。
- **不动 `tools/gates/check_expected_red.py` 与 `tools/gates/explain_last_gate_failures.py`**：
  这两个文件归前驱 `0228-1`（本轮实测它是 `Plan Status: active`，**尚未执行**，
  `explain_last_gate_failures.py` 还不存在）。它落地了本 plan 就消费，没落地也**不代它改**。
- **不改 `.github/workflows/**` 一行**（`ai-autonomy-policy.md:84` 定级 `blocked | 人工批准`）。
  本 plan 只往既有分支推 `agenerp/**` 的提交，不新增/不修改任何 job、step、触发面。
- **不推 `main`**（本机 `main` 领先 `origin/main` 6 个提交，推不推由人决定）。
- 不顺手清理门禁 fixture 留下的孤儿列，也**不**把「站点被 `down -v` 清空」当成对它的修复——
  那条 backlog 要的是让 fixture 不再留残留，归
  `docs/backlog/gate-fixtures-pollute-the-live-site.md`（⚠️ Baseline 里那 5 条冷起前的历史孤儿列
  会随 Phase 1 的 `down -v` 一起消失，这是冷起的副作用，不是本 plan 交付的清理）。

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
- **冷起前先备份，并把备份拷出容器**：
  `docker compose -f docker-compose.yml exec -T backend bench --site frontend backup`，
  再 `docker compose -f docker-compose.yml cp backend:/home/frappe/frappe-bench/sites/frontend/private/backups ./.backups-<日期>`。
  **拷出这一步不能省**：备份落在 `sites` 卷里，而本 plan 要跑的 `down -v` 会**连卷一起删**，
  不拷出来等于没备份。
- `gh` 已认证；推 `ci/0027-2-l2-full-live-gate` 的权限。
- 回滚策略：`agenerp/**` 的改动是纯代码，回滚 = `git revert`。
  **⚠️ 站点侧不可回滚，照实写**：本仓的 compose 栈**就是**那个常驻站点（本轮实测 `Up 6 hours`），
  `docker compose down -v` 会把它连同 5 卷一起删掉，**Baseline 里那 5 条历史孤儿列随之永久消失**。
  这是本 plan 有意为之（全新站点是复现 runner 条件的唯一本机等价物），不是意外——
  但因此 Phase 1 必须**先**在冷起之前把常驻站点的证据取全（见 Phase 1 第 1 项），
  Phase 3 的「常驻站点」与「历史孤儿列」两条判据也按冷起后的实际情况定义，不写成拿不到的证据。

## Execution Plan

### Phase 1 - 复现与取证（**不猜根因**）

Status: completed
Targets: 无代码改动
Skill: `bug-diagnosis-prompt.md`

- Item Types: `Proof`（本阶段 6 项全部 `Proof`，按 Minimum Rule 7 在阶段层声明）
- Prereqs: 无硬前置。前驱 `0228-1` 若已落地，本机 `tools/gates/explain_last_gate_failures.py` 可直接打出红因原文，
  少走一次手工 `-vv` 复跑；未落地也不阻塞——本阶段的取证主路是本机冷起 + `pytest -vv`。

- [x] `Proof`：**冷起之前，先把常驻站点的证据取全**（`down -v` 之后这些证据就不存在了）——
      ① `bench backup` 并按 Infra 那条把备份**拷出容器**；
      ② 记录常驻站点当前的孤儿列全集：`information_schema` 直查 `tabItem` 的列
      + `schema_drift("Item")` 各一份，逐字抄下（Baseline 说是 5–6 条，以本轮实测为准）；
      ③ 在常驻站点上跑一次 live 整目录判定，抄下退出码与输出，作为「冷起前的本机基线」。
      这一项做完再往下走；顺序颠倒就再也补不回来。
      - 实测（2026-08-22，`0cfd3bd`，常驻站点 `Up 6 hours`）：
        ① `docker compose -f docker-compose.yml exec -T backend bench --site frontend backup` → **exit 0**，
        `Database: ./frontend/private/backups/20260822_034532-frontend-database.sql.gz 797.9KiB`；
        `docker compose -f docker-compose.yml cp backend:/home/frappe/frappe-bench/sites/frontend/private/backups ./.backups-2026-08-22`
        → **exit 0**，落盘 `817012` 字节的 `.sql.gz` + `site_config_backup.json`（已加进 `.gitignore`，不进版本库）。
        ② `information_schema` 直查 `tabItem` → **81 列**，其中孤儿列 **1 条：`agenerp_gate_probe`**；
        `bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`
        → 逐字 `["agenerp_gate_probe"]`。**⚠️ 与 Baseline 的「5–6 条」不符，以本轮实测的 1 条为准**
        （冷起前的实际值，照实记）。
        ③ live 整目录判定 → **exit 0**，逐字 `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。
- [x] `Proof`：**本机冷起复现**——`docker compose -f docker-compose.yml down -v`
      （**破坏性：删 5 个卷，上一项那些历史孤儿列到此为止**）后
      `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300`，
      再单跑该文件：`… python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -vv`。
      全新站点是 runner 条件在本机最接近的等价物。抄下退出码与**完整** traceback。
      - 实测：`down -v` → exit 0（5 卷 `agenerp_sites` / `agenerp_db-data` / `agenerp_logs` /
        `agenerp_redis-cache-data` / `agenerp_redis-queue-data` 全部 `Removed`）；
        `up -d --wait --wait-timeout 300` → **exit 0**（61.7 秒，六服务 healthy）。
        `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -vv`
        → **exit 1**，`1 failed, 3 passed in 8.53s`，逐字
        `FAILED tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind - agenerp.oob.OobError: frappe.model.meta.trim_table 的输出不是 JSON：''`。
        **红在全新站点上首跑即复现**（后续第 2、3 跑同样红，共 3/3），与 runner 的 2/2 红方向一致。
        traceback 末端：`agenerp/snapshot.py:345` → `agenerp/oob.py:186` `raise OobError(f"{function} 的输出不是 JSON：{stdout[:300]!r}")`。
- [x] `Proof`：把 `agenerp.apply` 的 WARNING 打开（`-o log_cli=true --log-cli-level=WARNING` 或等价方式）
      再跑一次，记录 `narrow_deletes` / `drop_orphan_columns` 的跳过日志逐条原文。
      这直接回答「删除集是不是被收窄没了」与「哪几列被判为非孤儿」。
      - 实测（`… -o log_cli=true --log-cli-level=WARNING` 单跑该 nodeid → **exit 1**，`1 failed in 3.00s`）：
        **全程只有一条 WARNING**，来自 `narrow_deletes`（`apply.py:204`）：
        `apply 跳过 10 条**不在定制包管辖范围内**的删除（包覆盖的 DocType：['Item']）：('Address', 'is_your_company_address'), ('Address', 'tax_category'), ('Communication', 'company'), ('Contact', 'is_billing_contact'), ('Customer', 'crm_deal'), ('Email Account', 'company'), ('Print Settings', 'compact_item_print'), ('Print Settings', 'print_taxes_with_zero_amount'), ('Print Settings', 'print_uom_after_quantity'), ('Quotation', 'crm_deal')`。
        `drop_orphan_columns` 的两条 WARNING（`不是孤儿列` / `不碰…不是本次 apply 造成的孤儿列`）
        **一条都没打**——即 `fieldnames - orphans` 与 `orphans - fieldnames` 双双为空，
        `removable` 恰好是探针列，`drop_columns` 正常发了 DDL。
        **结论：删除集没有被收窄没了，清除面走到了且执行成功。**（排除 (c) 档。）
- [x] `Proof`：**实跑前后全量 `capture` 对照**（`0027-2` 指名要的证据）——
      apply 前后各做一次全量 `capture(PACK_SCOPE, source=SiteSnapshotSource(site))`，
      记录差集；同时用 `information_schema` 独立交叉验证 `tabItem` 上探针列的物理存在性
      （不经 `schema_drift`，避开已登记的假绿面）。
      - 实测（冷起后的全新站点，apply 前后各一次）：
        `before: entries=10 item_columns=80` → `after: entries=10 item_columns=80`；
        差集逐字 `entries added: []` / `entries removed: []` /
        `columns added: []` / `columns removed: []` / `probe col present after: False`。
        **影响面恰好只有探针**（加了又删干净），方向是「减少/归零」不是「新增」，
        且 `information_schema` 独立确认 `agenerp_gate_roundtrip` **不在** `tabItem` 上。
        **这条是本阶段最重的一条事实：物理清除面本身是好的，红不在清除面。**
- [x] `Proof`：**分流**——把红因归到下面三档之一并写明依据：
      (a) 断言失败且探针列确实还在表上；(b) `OobError`（带外命令没跑起来 / 非零退出 / 载荷不是 JSON）；
      (c) 走都没走到清除面（`plan.deletes` 为空，被 `narrow_deletes` 收窄掉）。
      **三档的修法完全不同**，不分流就动代码等于猜。
      - **分流结论：(b) 档**，且落点精确到 `agenerp/oob.py:186` `run_json` 的**空 stdout 分支**。依据：
        ① 排除 (a)：上一项的 `information_schema` 交叉验证证明探针列**不在**表上，断言本身不会失败；
        ② 排除 (c)：`drop_orphan_columns` 的 DDL 真发了（无跳过 WARNING，且列确实没了）；
        ③ (b) 的**具体形态不是「命令没跑起来」**——冷起后直接手跑
        `bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`
        → **exit 0、stdout 0 字节、stderr 0 字节**。即：清除做完之后全新站点上**一条孤儿列都没有了**，
        `trim_table` 返回 `[]`，而 `bench execute` 的打印是有条件的——
        `apps/frappe/frappe/commands/utils.py:285` 逐字 `if ret:`（v15.119.3 容器内实读），
        **假值返回不打印任何东西**。于是 `json.loads('')` 抛 `ValueError` → `OobError`。
      - **它逐字解释了「本机 6 跑红 1 次、runner 2 跑红 2 次」这个已实测差异**：
        本机常驻站点上一直躺着别的门禁留下的历史孤儿列（本轮冷起前实测 `["agenerp_gate_probe"]`），
        所以本次 apply 清完自己的探针列之后 `trim_table` 仍返回**非空**列表 → 打印 JSON → 绿；
        只有在残留恰好不在场的那一跑才会红（本机 1/6）。
        runner 的**全新**站点上没有任何历史残留 → 清完必然归零 → 必然红（runner 2/2、本机冷起 3/3）。
      - **安全前提已实证，不是推理**：`run_json` 若把「exit 0 且 stdout 全空」认成「callee 返回假值」，
        会不会把真故障吞掉？冷起站点上实跑三种故障形态，**全部非零退出**（故走不到该分支，
        仍由 `_run` 抛 `OobError`）：
        (A) 白名单外/不存在的函数 `frappe.model.meta.no_such_fn` → **exit 1**，
        `AttributeError: module 'frappe.model.meta' has no attribute 'no_such_fn'`；
        (B) 函数内部抛错 `trim_table(doctype='NoSuchDoctypeXYZ')` → **exit 1**，
        `pymysql.err.ProgrammingError: ('DocType', 'NoSuchDoctypeXYZ')`；
        (C) 站点不存在 `--site nosuchsite` → **exit 1**（stdout 32 字节，非 JSON，双重挡住）。
- [x] `Proof`：若本机冷起**复现不出来**（3 跑全绿）→ 逐字记「本机冷起不可复现」，**不猜根因**（裁判规则 3），
      并**不得**据此认为问题已消失（runner 上 2 跑红 2 次是已实测的事实）。
      此时唯一可走的取证路是 CI，而 CI 取证面归 `0228-1` 的 `## Human Handoff`（需要人解停机线 / 出 trailer）——
      本 plan 按 `## Deferred But Adjudicated` 的固定处置置 `deferred` 并把这一事实写进 STATE §3，
      **不自行推分支跑 CI 碰运气**。
      - **本条的前提不成立，故不适用**：本机冷起 **3 跑红 3 次**（非「3 跑全绿」），红因原文已到手。
        因此**不**走 `deferred` 分支，按 Phase 2 继续。

Exit Criteria:

- [x] 红因被归入 (a)/(b)/(c) 之一，依据是命令原文 + 退出码 + 输出，不是推断 —— **(b) 档**，见分流项
- [x] 前后全量 `capture` 对照 + `information_schema` 交叉验证两份证据在案
- [x] **冷起前**的常驻站点证据三件（备份已拷出 · 孤儿列全集 · live 整目录判定退出码）在案
- [x] No owner-doc update required（本阶段不改行为）
- [x] `docs/logs/2026/08-22.md` 更新

### Phase 2 - 按证据修实现

Status: completed
Targets: `agenerp/apply.py` · `agenerp/oob.py` · `agenerp/snapshot.py`（**只改 Phase 1 分流指到的那一处**）· `tests/unit/`
Skill: `none`

- Item Types: `Fix | Proof`
- Prereqs: Phase 1 完成且分流结论明确

- [x] `Fix`：只改分流指到的那一处。**不做与红因无关的顺手优化**（北极星条款）。
      改动前在本项下写明：改哪个函数、为什么这一处、以及它如何解释「本机 6 跑红 1 次、runner 2 跑红 2 次」
      这个已实测的差异——解释不了就说明分流没做完，回 Phase 1。
      - **改哪个函数**：`agenerp/oob.py` `run_json` 的**空 stdout 分支**（原 `agenerp/oob.py:186`）。
        新增哨兵 `FALSY_RESULT`；`run_json` 对「退出码 0 且 `stdout.strip()` 为空」返回该哨兵，
        其余路径一字未动。连带一处**必须同时改的消费端**：`agenerp/snapshot.py` `schema_drift`
        把 `FALSY_RESULT` 翻译成 `()`。
      - **为什么是这一处**：Phase 1 已用两条独立证据排掉另外两档——`information_schema` 证明探针列
        物理上不在表上（排 (a)），`drop_orphan_columns` 无任何跳过 WARNING 且 DDL 真发了（排 (c)）。
        剩下的唯一未证伪面就是 `run_json` 把「零字节 stdout」判成「载荷不是 JSON」。
        冷起站点上手跑 `trim_table` → **exit 0 / stdout 0 字节**，而
        `apps/frappe/frappe/commands/utils.py:285` 逐字 `if ret:` —— 假值返回不打印。
      - **`agenerp/apply.py` 一字未改**：Targets 允许它，但分流没指到它，按本项自己的约束不动。
      - **它如何解释已实测的差异**：本机常驻站点长期躺着别的门禁留下的历史孤儿列
        （冷起前实测 `schema_drift("Item")` → `["agenerp_gate_probe"]`），apply 清完自己的探针列后
        集合**仍非空** → `bench execute` 打印 JSON → 绿；只有残留恰好不在场的那一跑才红（本机 1/6）。
        runner 的**全新**站点没有任何残留 → 清完必然**归零** → `[]` → 零字节 → 必然红
        （runner 2/2、本机冷起 3/3）。**方向、频次、站点形态三者全部对得上。**
- [x] `Fix`：若红因落在 (b)/(c) 档，**不得**用「吞掉异常」或「放宽收窄」的方式让门禁变绿——
      两者都会重新制造 `2026-08-21-2220-1` 已登记的假绿面。收窄若确需放宽，
      必须在 `module-boundaries.md` §11.6 追加裁定并写清作用域上界。
      - **没有吞任何异常，也没有放宽任何收窄**：`narrow_deletes` 与 `drop_orphan_columns` 的交集口径
        一字未改；`_run` 的非零退出仍抛；非空的非 JSON 载荷仍抛；非 list、非 str 列名仍抛。
        新增的只有「exit 0 且 stdout 全空」这一条，而它在 `bench execute` 的协议里**等价于**
        「被调函数返回了假值」，不是「命令没跑起来」。
      - **该等价性是实证的，不是推理**（冷起站点逐条实跑，三种真故障**全部非零退出**，
        走不到新分支）：(A) 函数不存在 → exit 1 `AttributeError: module 'frappe.model.meta' has no attribute 'no_such_fn'`；
        (B) 函数内部抛错 → exit 1 `pymysql.err.ProgrammingError: ('DocType', 'NoSuchDoctypeXYZ')`；
        (C) 站点不存在 → exit 1。
      - **哨兵而不是 `[]`/`None` 的理由**：`json.loads("null")` 就是 `None`，用 `None` 兼表两件事会
        重新制造本模块要挡的歧义；直接回 `[]` 等于替调用方猜「这个函数返回列表」，
        `ALLOWED_CALLS` 以后多一条返回 dict 的函数那个猜就会静默错掉。哨兵逼调用方显式翻译。
- [x] `Proof`：`tests/unit/` 补一条**对着红因**的判据（不是对着门禁），
      命令 `python3 -m pytest tests/unit -q` → exit 0。
      - 补在 `tests/unit/test_schema_drift.py`（该文件的模块 docstring 自称就是
        「钉死孤儿列巡检的行为（`agenerp/oob.py` + `agenerp.snapshot.schema_drift`）」，是这条面的既有 owner），
        共 **4 条**，全部喂假 `Runner`、不连站点：
        `test_empty_stdout_means_the_callee_returned_a_falsy_value` ·
        `test_a_site_with_zero_orphan_columns_is_expressible`（承重条款：零孤儿列必须表达得出来） ·
        `test_blank_stdout_is_not_confused_with_a_broken_command`（例外只覆盖 exit 0） ·
        `test_the_falsy_sentinel_is_not_a_result_any_caller_can_use_by_accident`（含 `null` 与空输出必须分得开）。
      - `python3 -m pytest tests/unit -q` → **exit 0**，`221 passed in 0.59s`。
- [x] `Proof`：`ruff check agenerp tests/unit tests/contracts` → exit 0；
      `python3 -m pytest tests/contracts -q` → exit 0。
      - `ruff check agenerp tests/unit tests/contracts` → **exit 0**，`All checks passed!`
      - `python3 -m pytest tests/contracts -q` → **exit 0**，`151 passed in 0.06s`
      - 附带：`python3 tools/gates/check_expected_red.py`（默认判定环境，L1）→ **exit 0**，
        `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`（名单一行未动）。

Exit Criteria:

- [x] 改动面 ≤ Phase 1 分流指到的一处，且能解释本机/runner 的差异 —— `run_json` 空 stdout 分支 + 其消费端翻译
- [x] 单测与契约测试全绿，lint 干净
- [x] `docs/architecture/module-boundaries.md` §11.8 追加实测结论（**追加，不改写**；§11.6 无需改，收窄口径一字未动）
- [x] `docs/logs/2026/08-22.md` 更新

### Phase 3 - 三面证明（全新站点 / 多轮累积站点 / 变异）

Status: completed
Targets: 无代码改动
Skill: `none`

- Item Types: `Proof`（全部）
- Prereqs: Phase 2 完成

- [x] `Proof`：**全新站点**——`down -v` 冷起后跑 live 整目录判定
      `… python3 tools/gates/check_expected_red.py` → 期望 `门禁 19 项：红 0，绿 19，跳过 0` / exit 0，
      **连跑 3 次全绿**（前驱 `0027-1` 实测过这条门禁有间歇性，1 跑不算数）。
      - 实测：`down -v` → exit 0（18 项 `Removed`）；`up -d --wait --wait-timeout 300` → exit 0（61.1 秒）。
        `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`
        连跑 3 次：**RUN1 exit 0 · RUN2 exit 0 · RUN3 exit 0**，三次均逐字
        `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。
        对照 Phase 1 同一形态站点上的 **3 跑红 3 次**——方向逆转，且首跑即绿。
- [x] `Proof`：**多轮累积站点**（Baseline 里说的「常驻站点」在 Phase 1 冷起时已被 `down -v` 删掉，
      因此这一条按冷起后的实际情况定义，不写成拿不到的证据）——
      在**上一项连跑 3 次之后、不再 `down -v`** 的那个站点上跑同一条命令 → exit 0。
      此时站点已积累了至少 3 轮门禁 fixture 的残留，正是「非空表」条件。
      这一条是「不迁就 runner」的判据：只在**空**站点绿说明修法可能只对空表成立。
      - 实测：同一站点第 4 跑（未 `down -v`）→ **exit 0**，`门禁 19 项：红 0，绿 19，跳过 0`。
        此时 `tabItem` 已由 80 列涨到 **81 列**、孤儿列集合由**空**变成 `["agenerp_gate_probe"]`
        （非空表条件成立）。
      - **补一条更强的隔离证据**（同一累积站点上单跑该门禁文件，前后各一次全量 `capture`）：
        `acc_before: entries=10 item_columns=81` → 门禁 **exit 0，4 passed in 7.29s** → `acc_after: entries=10 item_columns=81`；
        差集 `entries added/removed: []`、`columns added/removed: []`；
        `agenerp_gate_probe still there: True`、`agenerp_gate_roundtrip present: False`。
        即：在**非空**表上，apply 只清掉自己的探针列，**一列都没多删**——收窄口径仍然成立。
- [x] `Proof`：**变异验证**（**必须在 `down -v` 冷起后的全新站点上做**——红只在全新站点稳定复现，
      在多轮累积站点上做变异，不红也说明不了问题）——把 Phase 2 的修复点改回改动前的形态 → 该门禁必须**逐字转红**
      且点名集合恰好多出 `::test_no_orphan_column_left_behind` 一条；复原后复跑回 exit 0。
      牙齿在这里；变异不红就说明修的不是红因。
      - **A/B 两跑都在各自 `down -v` 冷起后的全新站点上做**（控制变量，不拿累积站点凑数）：
      - **变异**（删掉 `run_json` 里 `if not stdout.strip(): return FALSY_RESULT` 两行，其余一字不动）
        → `python3 tools/gates/check_expected_red.py` **exit 1**，逐字：
        `门禁 19 项：红 1，绿 18，跳过 0` / `❌ live 判定契约是全部门禁绿，下列门禁红了：` /
        `   tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`。
        **点名集合恰好一条，且与 CI run `32509351108` 两次 attempt 的输出逐字一致。**
      - 变异同时也把单测打红（牙齿不只在门禁上）：`python3 -m pytest tests/unit -q` → **exit 1**，
        `2 failed, 219 passed`，红的恰好是 `::test_empty_stdout_means_the_callee_returned_a_falsy_value`
        与 `::test_a_site_with_zero_orphan_columns_is_expressible`。
      - **复原**（`cp /tmp/oob.py.good agenerp/oob.py`）→ `python3 -m pytest tests/unit -q` **exit 0**（`221 passed`）；
        再 `down -v` 冷起同形态全新站点 → `python3 tools/gates/check_expected_red.py` **exit 0**，
        `门禁 19 项：红 0，绿 19，跳过 0`。
- [x] `Proof`：**物理列的独立证据**——修复后再做一次 `information_schema` 查询，
      确认探针列确实不在 `tabItem` 上；**作用域方向判据按冷起后的集合算**：
      拿本阶段第 1 项冷起**之后**首跑前记录的孤儿列集合作基准，
      修复后该集合**只许减少本次探针列、不许多删一条、不许新增**。
      （Baseline 里那 5 条冷起前的历史孤儿列已随 `down -v` 消失，**不得**把它们写进本条判据——
      写了就是拿不到的证据。）
      - **基准（冷起后、首跑前）**：`trim_table(dry_run=True)` → exit 0 / **0 字节**（孤儿列集合为**空集**）；
        `information_schema` → `tabItem` **80 列**，零个 `agenerp*` 列。
      - **4 跑之后**：孤儿列集合 = `["agenerp_gate_probe"]`，`tabItem` **81 列**，
        `diff` 基准→现状**只有一行**：`> agenerp_gate_probe`。
        本次探针列 `agenerp_gate_roundtrip` **不在** `tabItem` 上（`grep` 命中 0 次），
        不经 `schema_drift`、直查 `information_schema` 得出，避开已登记的假绿面。
      - **方向照实说明，不粉饰**：集合从空集变成 1 条，看上去是「新增」，但那一条**不是 apply 造成的**——
        `agenerp_gate_probe` 由**另一条门禁**创建，`grep` 实证落点
        `tests/gates/test_snapshot_diff_structured.py:39` `live_site.add_custom_field(doctype="Item", fieldname="agenerp_gate_probe", …)`，
        属本 plan Non-Goals 明列、归 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 的门禁 fixture 残留。
      - **apply 自身的方向判据由前后 `capture` 对照单独给出，两侧站点各一次，均为「减少/归零」**：
        全新站点 `columns added: []` / `columns removed: []`（探针列加了又清干净）；
        非空累积站点同样 `columns added: []` / `columns removed: []`，且 `agenerp_gate_probe` **原样保留**——
        **一列都没多删**，收窄面完好。

Exit Criteria:

- [x] 全新站点 3 跑全绿、多轮累积站点 1 跑绿，命令原文与退出码在案
- [x] 变异验证有牙齿（在全新站点上做），点名集合精确（恰好 1 条，与 CI 红因逐字一致）
- [x] 作用域方向是「减少」：冷起后孤儿列集合的前后对照在案，只少了本次探针列；
      唯一的「新增」已实证归因于另一条门禁的 fixture 残留（既有 backlog 项），不是本次 apply
- [x] `docs/logs/2026/08-22.md` 更新

### Phase 4 - CI 实跑与回写（**硬上限 2 次实跑**）

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`（§2/§3 追加行）· `docs/context/project-context.md`
Skill: `none`

- Item Types: 共 6 项 —— `Decision` 1、`Fix` 3、`Proof` 2
- Prereqs: **Phase 3 三面证明全绿**（硬前置，未全绿不得推分支）;
  **PR #1 必须仍是 `OPEN`**（硬前置）——Baseline 实测：往该分支 `push` **不触发任何运行**
  （`on: push` 限定 `branches: [main]`），CI 只由开着的 PR 的 `pull_request` 事件触发。
  推之前先 `gh pr view 1 --json state,baseRefOid` 确认 `state=OPEN` 且 `baseRefOid` 仍是 `7b0f585`；
  任一条不成立则**不推**，按 `## Deferred But Adjudicated` 的固定处置停机等人
  （PR 被关掉或 base 被移动都属于人的动作，loop 不替人重开 PR）。
  - **两条硬前置推前实测均成立**：Phase 3 三面证明全绿（见上）；
    `gh pr view 1 --json state,baseRefOid,headRefOid,headRefName` →
    `{"baseRefOid":"7b0f585f7c8082a64902da65e6e3314cb239dc9f","headRefName":"ci/0027-2-l2-full-live-gate","headRefOid":"9a8832f…","state":"OPEN"}`。

- [x] `Decision`（**草案评审阶段已裁定，执行时照做**）：本阶段跑 CI 是**合法**的，理由是它逐字满足
      STATE §3 那条 `[open]` 停机行自己写死的重开条件（「successor 修好 `agenerp` 侧清除面后，
      往分支推一次，`gates-l2-live` 在 PR 上 `success`」）。**Phase 3 三面证明全绿是硬前置**——
      没跑绿就推分支，等于在停机状态下碰运气，本 plan 明令禁止。
      备选（推迟到人显式解停机线再推）被排除：那会让停机永远等不到它自己写的重开事件。
      残余风险：仍可能红，缓解是硬上限 2 次实跑 + 红即停机不重试第三次。
      - Skill: `none`
      - **照做**：Phase 3 全绿后才推，实跑 1 次即绿，未用到第 2 次配额。
- [x] `Fix`：推分支的形态**只能是把 `agenerp/**` 的修复 cherry-pick 到 `ci/0027-2-l2-full-live-gate`**，
      **不得 merge / rebase `main` 进分支**（会点亮 `verdict-tool-untouched`，见 Baseline）。
      推之前实跑 `git diff --name-only 7b0f585 <branch-head> -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
      确认**无输出**，把命令与输出抄进本 plan。
      - 形态：`git checkout -B ci/0027-2-l2-full-live-gate origin/ci/0027-2-l2-full-live-gate`（基线 `9a8832f`）
        → `git checkout 578eb8f -- agenerp/oob.py agenerp/snapshot.py` → 提交 `c2c688b`。
        **只取两个文件，未 merge / rebase `main`。**
      - `git diff --name-only 9a8832f c2c688b` → 逐字只有两行：`agenerp/oob.py` · `agenerp/snapshot.py`。
      - `git diff --name-only 7b0f585 c2c688b -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
        → **无输出**（exit 0）。
      - `git push origin ci/0027-2-l2-full-live-gate` → **exit 0**，`9a8832f..c2c688b`。
- [x] `Proof`：推分支（PR #1 的 `pull_request` synchronize 事件）触发 CI，读 `gates-l2-live` 的结论。**上限 2 次实跑**（首跑 + 必要时 1 次原样复跑）。
      绿：记 run id / job id / sha。红：**先原样复跑一次**（裁判规则 3），仍红则按固定处置停机，
      **不猜根因**，把前驱取证步骤打出的红因原文追加进 STATE §3。
      - **绿，首跑即绿，用了 1 次实跑（上限 2）**。三件套：
        **run id `32533449466`** · **job id `96929876654`**（`L2 全量 live 判定（19 条）` = `gates-l2-live`）·
        **sha `c2c688b7f6bc49a96d1e89a3582014334ba8fb71`**。
      - `gh run view 32533449466 --json status,conclusion,headSha` → `"conclusion":"success"` / `"status":"completed"`。
      - 该 job 日志逐字：`判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单` /
        `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。
      - **九个 job 全部 `success`**，其中 `判定器未被改动`（`verdict-tool-untouched`，job `96929876658`）`success`。
      - 实跑次数核对：`gh run list --branch ci/0027-2-l2-full-live-gate` 推前 **1 条**、推后 **2 条**，差 **1**（≤ 2）。
- [x] `Fix`：绿之后**就地改准**两处已确认的 owner-doc 漂移（Minimum Rule 14，不降级）——
      `docs/context/project-context.md` 与 roadmap「5 现状」/「6 现状」/「9 现状」三行里
      「红因是 `::test_no_orphan_column_left_behind`、CI 上不成立」的表述已被本 plan 推翻，
      须就地改准并注明改准日期与依据 run id。
      - roadmap 三行各追加一段「2026-08-22 三次补记，就地改准」，逐字推翻
        「红在**实现**（`apply_pack` 的物理列清除面在 runner 的全新站点上不成立）」，
        改准为「清除面从来没坏过，真红因在巡检的表达能力」，并注明依据 run `32533449466`
        与 job `96929876654` / `96929876658`。`grep -c 32533449466` → **3**。
      - `docs/context/project-context.md` 两行（「L2 live 门禁（定制包往返）」与「L2 live 门禁（**整目录判定**）」）
        同样就地改准，含「本机 6 跑红 1 次 / runner 2 跑红 2 次……**不猜根因**」那处——本轮已给出实测答案。
        `grep -c 32533449466` → **2**。
      - **三张表的结构未破**：三条 roadmap 行仍以 `| — |` / `| L2 |` 收尾（脚本实测断言通过）。
      - **仍不置 `done`**（Non-Goals）：`done` 要求「从 `expected-red.txt` 划掉」，默认判定环境无
        `AGENERP_LIVE`、L2 恒红，条件不可满足（人在 STATE §2 11:20Z 的裁定），与工作项 4/5/7/8/9 同一情形。
        因此 driver 步骤 4.b 的「把工作项由 ❌ 改 ✅」在本 plan 上以**就地改准现状行**的方式落实，不改状态值。
- [x] `Fix`：在 `2026-08-22-0027-2-…md` 的 `Closure Audit Log` **追加**一行
      （只追加，不改写任何既有行）说明其 `Reopen When` 已满足；**不替它改 `Plan Status`**——
      那是它自己 Reopen 之后续跑的事。
      - 已追加第五条。**为什么追加不违反它上一条自己写的「不再往本 Log 追加第五条」**：那句限定在
        「人给出裁定之前、每轮产出都是同一份拒绝执行」的空转情形，本条记的是**那个条件本身发生了变化**
        （重开条件被满足），是新事实不是空转。
      - 该条同时写明：**重开条件满足 ≠ 可以关闭**——它自己欠的守卫三次变异实证仍无 run id，
        19 个 `[ ]` 仍是真未做。**本轮一个勾未改、`Plan Status` 未动。**
- [x] `Proof`：在 `docs/masterplan/STATE.md` §2 追加一条证据行
      （时间 · WBS 行 ID · 命令→退出码 · sha · 下一项），§3 那条 `[open]` 行下方追加处置事实行。
      - §2 追加 `2026-08-22T14:40Z · P0/工作项 6 · …` 一条（含五条子事实：红因 · 本机/runner 差异的解释 ·
        清除面证据 · 修法与「不是放宽」的实证 · 变异 · CI 三件套 · 未做且明确不做 · 验证范围）。
      - §3 在那条 `[open]` 行之后追加一条 `[resolved]` **处置事实行**，
        逐字记「重开条件已被满足 / 停机就此解除 / 红因不再是未知 / 重开条件满足 ≠ `0027-2` 可关闭 /
        (a) 项仍未做」。**未改写 §3 任何既有行**（`[open]` 那行一字未动）。
      - **红线 5 自查实跑**：`git diff -U0 docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**
        （`17 insertions(+), 0 deletions`），纯追加属实。
      - `docs/masterplan/DECISIONS.md` **一行未动**（`git status` 无该文件）。

Exit Criteria:

- [x] 推之前 `gh pr view 1 --json state,baseRefOid` 实测为 `OPEN` / `7b0f585`，命令与输出在案
- [x] `gates-l2-live` 在 CI 上 `success`（run `32533449466` / job `96929876654` / sha `c2c688b`）
- [x] `verdict-tool-untouched` 仍 `success`（job `96929876658`）；
      `git diff --name-only 7b0f585 c2c688b -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs` 无输出
- [x] CI 实跑次数 ≤ 2 —— `gh run list --branch ci/0027-2-l2-full-live-gate` 推前 1 条、推后 2 条，**差 1**
- [x] roadmap 三行 + `project-context.md` 的确认漂移已就地改准
- [x] `0027-2` 的 Closure Audit Log 有追加行，其既有行一字未改
- [x] STATE §2/§3 有追加行（纯追加实测 0 删除）；`docs/masterplan/DECISIONS.md` 一行未动
- [x] `docs/logs/2026/08-22.md` 更新

## Draft Review Record

- Independent draft review iteration 1: `needs revision → 已就地修复，accept`（MISSION_DRIVER 评审步骤，2026-08-22）。
  逐条复核了 Baseline 的每一条事实，**全部实测对得上**：`gh pr view 1` → PR #1 `state=OPEN`、
  `baseRefOid=7b0f585f7c…`（与 plan 写的 `7b0f585` 一致）；`agenerp/pack.py` 的 `apply_pack` 委派链、
  `agenerp/apply.py:245` 的 `if not plan.deletes: return` 与 `:251` 的 `drop_orphan_columns`、
  `agenerp/snapshot.py` `schema_drift` 的「答不上话抛 `OobError` 不返回空元组」、
  `tools/gates/check_expected_red.py` 的 `capture_output=True` + `JUNIT.unlink()`，逐一核对无误；
  STATE §3 第 88 行的重开条件与 roadmap「5/6 现状」两行的漂移表述也与 plan 的引用一致；
  禁用词扫描零命中，`Status: completed` + 未勾框扫描为空。
  **修掉 1 个 Blocker**：本仓 compose 栈**就是**那个常驻站点（本轮 `docker compose ps` 实测 `Up 6 hours`），
  而原 Phase 1 第一项直接 `down -v`——它会连 5 卷一起删掉，于是原 Phase 3 的「常驻站点 1 跑绿」
  和「本机那 5 条历史孤儿列一条不少」**两条退出判据在自己的 Phase 1 执行后即不可满足**，
  Infra 那句「不对常驻站点做破坏性操作」也与之直接矛盾。已改为：Phase 1 新增冷起**前**的取证首项
  （备份并拷出卷 · 孤儿列全集 · 冷起前基线判定），Phase 3 两条判据改按冷起后的实际集合定义，
  Infra 的回滚段照实改写为「站点侧不可回滚」。
  **修掉 4 个 Major**：① 备份落在 `sites` 卷里而 `down -v` 删卷，补上 `docker compose cp` 拷出步骤；
  ② Phase 3 变异验证未钉死站点形态，补上「必须在冷起后的全新站点上做」；
  ③ Phase 4 漏了硬前置「PR #1 仍 `OPEN`」——Baseline 自己写着 `push` 不触发任何运行、只有 `pull_request` 触发，
  PR 一旦被关掉推上去就是静默无事件，已补前置检查与对应退出判据；
  ④ Non-Goals 写「前驱已改完」比证据强——`0228-1` 实测是 `active` 未执行、`explain_last_gate_failures.py` 尚不存在，
  已改准并与 Phase 1 Prereqs 的「若已落地」口径统一。
  **修掉 1 个 Minor**：`## Deferred But Adjudicated` 第一条缺 `重开事件`（Anti-Slacking Rule 要求），已补。
  Phase 4 那条 `Decision` 自称「草案评审阶段已裁定」——**本次评审确认该裁定成立**：
  它逐字满足 STATE §3 第 88 行自己写死的重开条件，且 Phase 3 三面证明为硬前置、CI 实跑硬上限 2 次，
  备选（等人显式解停机线）会让那条停机行永远等不到它自己写的重开事件，予以排除。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（roadmap 三行 · `project-context.md` · `module-boundaries.md` · STATE · `0027-2` 追加行）
- [ ] verification has run：本机冷起 3 跑 live 整目录判定 · 多轮累积站点 1 跑 · 变异验证（冷起站点）· `pytest tests/unit` · `pytest tests/contracts` · `ruff` · CI `gates-l2-live`
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件，须显式写明「verification scope limited」
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **`0027-2` 指名的证据在案**：实跑前后全量 `capture` 对照 + 修完后本机 live 整目录判定仍绿
- [ ] 冷起**前**的常驻站点证据三件在案（备份已拷出卷 · 孤儿列全集 · 冷起前基线判定退出码）
- [ ] `git diff` 未触及 `tests/gates/**`、`tools/gates/expected-red.txt`、`docs/masterplan/DECISIONS.md`、`missions/**`

## Deferred But Adjudicated

### 取证拿不到可分流证据时的固定处置

- Classification: `watch-only residual`
- Why Not Blocking Closure: 失败分支的写死处置，不是被推迟的工作项。
- 处置逐字：记录所有已跑命令与输出 → 追加进 STATE §3（不改写既有行）→ 本 plan 置 `deferred`
  并在文件头写明重开条件 → **不改一行 `agenerp/`**、**不猜根因**。
- Successor Required: `no`
- 重开事件：**人解开 `0228-1` 的 `## Human Handoff`（出 `Gates-Change-Approved-By:` trailer 或直接授权跑 CI 取证）**，
  使 CI 侧的红因原文可得；或本机冷起在后续任一轮里复现出该红。二者任一发生即重开本 plan。

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

Status Note: 四个 Phase 全部执行完毕，逐项证据写在各 Phase 项下（命令原文 + 退出码 + sha）。**verification scope limited**：本仓无全量套件（无 build、无 typecheck），本 plan 覆盖的是 `ruff` · `pytest tests/unit`（221 passed）· `pytest tests/contracts`（151 passed）· 默认判定环境判定器 · 本机 live 整目录判定（冷起全新站点 3 跑 + 多轮累积站点 1 跑，均 exit 0）· 变异验证（冷起全新站点，A/B 各一次）· CI run `32533449466`（九个 job 全绿）。交付 sha：`main` 上 `578eb8f`（**未推**）、分支 `ci/0027-2-l2-full-live-gate` 上 `c2c688b`（已推）。**`## Closure Gates` 十二框本轮一个未勾，`Closure Audit Evidence` 亦留空——本 plan 头 `Audit: required`，且它触及 `ai-autonomy-policy.md` Protected Areas 的 `agenerp/apply.py` 删除路径一族，关闭审计须由执行器之外的独立 `CLOSURE_VERIFY` 步做；执行器自勾即自审，等于伪造独立性。**（与 `2026-08-22-0228-1` 的处置一致：那份的十四框也是由独立审计回填的。）

Closure Audit Evidence:

- Auditor / Agent: <待填>
- Evidence: <待填>

Follow-up:

- <待填；确认的缺陷不得写在这里>
