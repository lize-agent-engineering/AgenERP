# 2026-08-22-1206-2 两个 job 落到 `main`：工作项 9 的关闭判据第一次在 `main` 上成立

> Plan Status: active
> Mission: p0-foundation
> Work Item: 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）—— 落地面（含 plan `2026-08-22-0027-2` 欠的 Phase 3 那一项）
> Last Reviewed: 2026-08-22
> Execution Order: **2 / 2**（本批第二个；**硬依赖**第一个 plan `2026-08-22-1206-1-verdict-guard-mutation-proof.md` 的**四条**实验证据与刷新后的分支形态）
> Source: `docs/backlog/p0-foundation-roadmap.md`「工作项 9」那格写死的关闭判据，**原文逐字**为
>   「`gates.yml` 上存在一个 job，在 live 判定环境下用 `tools/gates/check_expected_red.py` 对 `tests/gates`
>   **全部 19 条**判定并 `success`」（本行照抄，未改写）；实测该判据**此刻在 `main` 上不成立**（见 Current Baseline B）。
> Related: `2026-08-22-1206-1-verdict-guard-mutation-proof.md`（**唯一前置**，交付守卫实证与安全的 PR 形态）·
>   `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（`deferred`，两个 job 的作者；本 plan 承接它 Phase 3 欠的「把前驱两条 Deferred 记为了结」）·
>   `2026-08-21-2220-2-homepage-ai-not-configured.md`（`gates-l2` job 的交付者，也是「纯追加进 `main` 的 `gates.yml`」这条先例的来源，且是那两条待了结 Deferred 的所在）
> Audit: required

## Current Baseline

以下每一条都是 2026-08-22 实跑得出的。⚠️ **第 4 轮评审刷新基线（Minimum Rule 1）**：起草时锚在 `main` @ `aba9a5f`，
评审当日 `main` 已前进到 `4d7b311`（两个提交：`6288666` 预算阈值单一真相源、`4d7b311` plist 不再注入预算变量），
且 `origin/main` 已追平。**关键：`.github/workflows/gates.yml` 在 `aba9a5f..4d7b311` 之间逐字节未变**
（`git diff --numstat aba9a5f 4d7b311 -- .github/workflows/gates.yml` → 无输出），
因此 B / C / D / F 各条结论**不受影响**；下面凡涉及 `main` sha 的读数一律以 `4d7b311` 为准。

**A. 前置状态**

- 起草时（2026-08-22 12:06）：`git log --oneline -1` → `aba9a5f`；`git status --porcelain` → **两行**，
  均为本批两个 draft plan 文件（未跟踪）。**第 4 轮评审当日复测**：`git log --oneline -1` → `4d7b311`；
  `git status --porcelain` → **一行**（前驱 plan 文件正在被改写），本批两个 plan 文件均已入库。
- **A3 · 本地 `main` 与 `origin/main` 必须分开说**：起草时 `git rev-parse main origin/main`
  → `aba9a5f` / `508c75b`，本地领先 **10** 个提交。**第 4 轮评审当日复测：两者已相等（均为 `4d7b311`，
  `git rev-list --left-right --count origin/main...main` → `0` / `0`）**——前驱那两次 `main` push 里的第一次已经发生。
  本 plan 的结果面是**远程 push 运行**，因此凡说「`main`」的地方都要指明是本地还是远程。
  前驱的收尾判据**不是**「两者相等」而是「`origin/main` 是 `main` 的祖先，且差集只含文档路径」
  （前驱第 5 轮改准，见前置核对 ⑥）；**本 plan 开工时必须实测复核这一点**。
- 本 plan 开工时，第一个 plan 必须已 `completed`。**它没完成之前本 plan 不得开工**——理由在 D。

**B. 工作项 9 的关闭判据在 `main` 上不成立（本 plan 存在的全部理由）**

- `git show main:.github/workflows/gates.yml | sed -n '/^jobs:/,$p' | grep -E '^  [a-z0-9-]+:'` → 7 个 job 键，
  `gates-untouched` / `expected-red-ratchet` / `gates-l1` / `masterplan-links` / `roadmap-parseable` / `loop-wiring` / `gates-l2`
- 同一文件 `grep -cE 'gates-l2-live|verdict-tool-untouched'` → `0`
- 两个新 job 此刻只存在于分支 `ci/0027-2-l2-full-live-gate` / PR #1 上，**`main` 未受影响**
  （⚠️ 本 plan 开工时它们**还会**存在于前驱新建的 `ci/1206-1-verdict-guard-proof` 上，内容逐字相同）。
  这一事实已被 plan `2026-08-22-0027-2` 的**三次独立关闭审计**各自实测复核过一遍，结论一致。

**C. 已有的绿证据与它的限定**

- run `32533449466`（PR #1，head `c2c688b`）：`gates-l2-live` job `96929876654` **`success`**，
  日志逐字 `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`；
  `verdict-tool-untouched` job `96929876658` `success`。
- **限定一**：那次跑在 `pull_request` 事件上，不是 `main` 的 `push` 上。
- **限定二**：那次的判定器与 `main` 上的**不是同一份**（`git diff --numstat main origin/ci/… -- tools/gates/check_expected_red.py` → `7 42`，
  差异来自 plan `2026-08-22-0228-1` 的取证面）。这一处由第一个 plan 的 Phase 2 补齐。
- **限定三（本 plan 要消灭的那条）**：plan `2026-08-22-0027-2` 自己写死的 **NB2** 把
  「合并后 `main` 上那次 `push` 运行」定为**权威运行**。在拿到它之前，工作项 9 的判据只能算「在 PR 上成立」。

**D. 为什么必须排在第一个 plan 之后（不是可调整的偏好）**

- D1 · plan `2026-08-22-0027-2` 逐字写着「**拿不到这三条，守卫不算交付**——绿的 CI 证明不了一个从不触发的守卫」。
  在守卫没有实证之前把它落进 `main`，落进去的就是一条**没有证据的安全声明**——那正是本仓反复批评的毛病。
- D2 · **⚠️ 本条在独立评审中被推翻并重写**。起草时写的「按现状合并会删掉 4 个 plan 文件……」**是错的**：
  `git diff --stat main origin/ci/…`（23 文件，−3455）是**两点式对比，不是合并预演**。
  合并走三方，实测 `git merge-tree --write-tree main origin/ci/0027-2-l2-full-live-gate` → 一棵树，
  `git diff --numstat main <该树>` → **只有一行** `118	0	.github/workflows/gates.yml`。**合并删不掉任何东西。**
  **真正需要第一个 plan 先跑的理由是另外两条，都成立**：
  · ① **`--ff-only` 要求 `main` 是分支的祖先**，而现在不是：
    `git merge-base --is-ancestor main ci/0027-2-l2-full-live-gate` → **否**（merge-base 停在 `77addbb`）；
  · ② **限定二**：PR 上那次绿跑的判定器与 `main` 上的不是同一份
    （`git diff --numstat main origin/ci/… -- tools/gates/check_expected_red.py` → `7	42`）。
  · ③ **⚠️ 第 3 轮评审新增，且它把「必须走前驱」从两条加强到三条**：`pull_request` 的 `BASE`
    在 **PR 创建时钉死**（前驱 Baseline C5，实测 `gh pr view 1 --json baseRefOid` → `7b0f585`，
    而彼时 `origin/main` 已是 `508c75b`；`STATE.md:81` 早有此记录）。
    **后果对本 plan 是直接的**：PR #1 **不能**用作落地载体——在它上面守卫恒红（`7b0f585..main` 命中判定器且无 trailer——起草时锚 `aba9a5f`，第 4 轮当日锚 `4d7b311`，两者同解），
    且它的 `changedFiles/additions/deletions` 恒为 `6 / 417 / 17` 而非 `1 / 118 / 0`。
    因此本 plan 落地的是**前驱新建的分支与 PR**，PR #1 改为在 Phase 1 的专门 `Decision` 里关闭并留证。
- D3 · 本 plan Phase 3 要写的「把前驱两条 Deferred 记为了结」，在守卫未交付时写就是
  「比证据更强的说法」（0027-2 的 `[open]` 停机行逐字给出过这个判断）。

**E. 本 plan 承接的那项欠账（来自 plan `2026-08-22-0027-2` Phase 3）**

- 逐字：「`Fix` **把前驱那两条 Deferred 记为了结**：在 plan `2026-08-21-2220-2` 的
  `Deferred But Adjudicated` 相应条目下**追加**一行指向本批两个 plan（**不改写已有行**——那是别人的关闭证据）。
  同时在 `## 14.4` 里写清：新 job 走判定器，**live 模式的契约是全绿零 skip，比预期红名单棘轮更紧**，
  因此「L2 在 CI 上不受棘轮保护」这条残余风险已被覆盖。」
- 其中 §14.4 那半**已经做了**（0027-2 Phase 3 的 Exit Criteria 里那一框是 `[x]`）；
  欠的是**在 `2026-08-21-2220-2` 里追加那一行**。本 plan 开工时必须先实测确认这一点，不得凭本行断定。

**F. 授权面（与第一个 plan 同一处，本 plan 不得默认继承，必须重新摆上台面）**

- `AGENTS.md` 红线 2 只禁**变松**；本 plan 是纯追加，方向是**加严**。
- `docs/context/ai-autonomy-policy.md` Protected Areas 表 `.github/workflows/** | blocked | 人工批准`。
- **先例**：plan `2026-08-21-2220-2` 用同一读法把 `gates-l2` job 追加进了 `main` 的 `gates.yml`，
  该 job 此刻就在 `main` 的 7 个 job 键里。
- **但本 plan 与第一个 plan 有实质区别**：第一个 plan 对 `main` 的 workflow **零改动**，本 plan **要真的改 `main`**。
  因此这条不一致对本 plan 的约束更强，Phase 1 有一个专门的 `Decision` 项处置它。

## Goals

1. **`main` 的 `.github/workflows/gates.yml` 末尾追加 `gates-l2-live` 与 `verdict-tool-untouched` 两个 job**，
   与已实测那 118 行逐字一致，且 `main` 的旧 190 行**逐字节不动**（前缀性判据）。
2. **拿到 NB2 定义的权威运行**：`main` 上那次 `push` 触发的运行里 `gates-l2-live` 为 `success`，
   即工作项 9 的关闭判据第一次在 `main` 上成立。**这次运行同时是守卫 `push` BASE/HEAD 推导路径的首次实测。**
3. **处置 PR #1（关闭并留证，不删分支）与落地用的那个 PR（`MERGED`）**，
   并把 plan `2026-08-22-0027-2` Phase 3 欠的那一项（E）落地。
4. **把 owner doc 里那一族「`main` 上没有这个 job / 仍是本机独证」的陈述逐条裁定并处置**——
   **不是「三处」，也不是「三个文件」，是 Phase 3 那条 grep 在三个目录里命中的每一处**
   （起草时按 Phase 3 的完整 pattern 实测 **10 行 / 4 个文件**：`system-baseline.md:448,457,461,521` ·
   `project-context.md:58,59` · `p0-foundation-roadmap.md:62,64,69` · `module-boundaries.md:305`）。
   ⚠️ **义务的形状是「逐条裁定」，不是「逐条照改」（第 3 轮评审改准）**：
   **裁定为确认漂移的 → 就地改准**，按 Minimum Rule 14 **不得降级成 follow-up**；
   **裁定为非漂移的 → 逐字记明命中位置与不改的理由，不得静默略过、更不得照改**。
   此前本条写成「命中的每一处**就地改准**……**它们**在落地之后成为确认的 owner-doc 漂移」，
   与 Phase 3 那一项逐字冲突，且照它执行会**改坏一条正确的架构原则**——
   `module-boundaries.md:305` 讲的是「无活站点不等于错误……让它抛异常，门禁就会永远红在环境而不是红在实现上」，
   与两个 job 在不在 `main` 上毫无关系。**该行起草时即预判为非漂移，最终裁定在 Phase 3。**
   ⚠️ **10 行 / 4 个文件这个数怎么来的**：起草时先写的是「8 行 / 3 个文件」，把 pattern 补上 `红在实现` 之后
   **多出两行、多出一个文件**（`system-baseline.md:461` 与 `module-boundaries.md:305`）——
   前者正是「红在实现，不是红在判据」那一行、是**今天就已确认**的漂移，后者是上面说的那条非漂移。
   靠挑一条更窄的 pattern 把 `:461` 排除在外，就是用 Goal 自己绕开 Minimum Rule 14；
   代价是同一条更宽的 pattern 会顺带捞进 `:305`，所以才需要「逐条裁定」而不是「逐条照改」。
   ⚠️ 其中 `system-baseline.md:457`（「原因：`gates-l2-live` 在 CI 上第一次跑就红，且原样复跑复现」）
   **今天就已经是确认漂移**——它被 `0228-2` 与 run `32533449466` 推翻了，**与本 plan 是否落地无关**。

## Non-Goals

- **不把 roadmap 的工作项 9 置 `done`**。roadmap 逐字：状态「由引擎在 closure 审计通过后回写」；
  plan 只写「9 现状」行的事实与判据是否成立，**置状态不是 plan 的事**。
- **不动 `tools/gates/expected-red.txt`**。工作项 4/5/6/7/8/9 卡在「从预期红名单划掉」上是**另一个已登记的人裁定题**
  （`docs/backlog/needs-human-expected-red-handoff.md`），本 plan 不替人解。
- **不改 `tests/gates/**`**（红线 1）、**不改 `agenerp/**`**、**不改判定器 `tools/gates/check_expected_red.py`**。
- **不退休 / 不合并既有的 `gates-l2` job**（它与 `gates-l2-live` 覆盖面重复，但删除是变松方向，
  且会打掉前缀性自查这条机械判据；已由 0027-2 登记为人动作 Deferred，本 plan 继续挂着）。
- **不改 plan `2026-08-22-0027-2` 的 `Plan Status`**，**不勾它任何一个 `[ ]`**（见 Phase 3 的红线纪律）。
- **不改 `docs/context/ai-autonomy-policy.md` 的 Rule 列**。

## Task Route

- Type: `verification or audit work`（主体是把一段已实证的 CI 配置落到 `main` 并取权威运行；附带 owner-doc 漂移改准）
- Owner Docs: `docs/architecture/system-baseline.md` §14.2 / §14.4 · `docs/backlog/p0-foundation-roadmap.md`（「9 现状」行）·
  `docs/context/project-context.md`（L2 那几行的验证范围表述）· `docs/context/ai-autonomy-policy.md`（只读）
- Skill Selection Basis: Skill Routing Rule 第 5 条——工作方法是「纯追加改 CI + 取权威运行 + owner-doc 漂移就地改准」，
  Skill Registry 无匹配的工作方法条目，全程 `Skill: none`。

## Infrastructure And Config Prereqs

- `gh` CLI 已认证（认证失败是裁判规则 4 的停机条件，触发即停）。
- 向 `main` 推送的权限。
- 无新增 secret、无新增 runner 需求。
- **回滚**：见 Phase 1 的 `Decision`「落地失败怎么办」。**此处不给授权**——起草时把回滚写在这里，
  与「停机纪律」里那句「是否 revert 由人选」自相矛盾，执行器可能读成自授权（独立评审 B7）。
  一条实测事实先摆在这里：`gh api repos/:owner/:repo/branches/main/protection` → **403**，
  报文逐字 `Upgrade to GitHub Pro or make this repository public to enable this feature.`
  —— **要读准：这是「私有仓在当前套餐下用不了分支保护」，不是「配了保护但为空」**。
  推论一样成立：`main` 上没有任何东西会因为 CI 红而挡住后续推送，
  「`main` 红了就再也推不动」这个死锁**不存在**，回滚不是唯一出路。

## 停机纪律（本 plan 特有）

本 plan 改的是 `main`，红了会挡住之后每一轮 loop。因此判据比第一个 plan 更硬：

- 落地后 `main` 上那次 push 运行**任何** job 红 → 先 `gh run rerun --failed` **原样复跑一次**（裁判规则 3）。
- 两次都红（**可复现**）→ **立刻停机**：写 `STATE.md` §3 needs-human 队列，plan 置 `deferred` 并写死 `Reopen When`，
  **不猜根因**。**revert 是人的选项，loop 不得自行执行**——授权口径只在 Phase 1 那条 `Decision` 里，别处不得再授权。
- **NB2 的计数锚点**：`0027-2` 定的「`CI 已验证` 的充要条件是执行期间主判定 job 从未出现非预期红（含 PR 上的每一次）」
  锚在**它自己**身上。本 plan 起新计数器，但**合并前 PR 上的每一次运行都要记，不得只留绿的那次**；
  run `32509351108` 那次可复现的红是永久证据，任何改准后的表述都不得抹掉它。
- 一红一绿 → 记「**不可复现**」，`main` 保持现状，**不得写成「CI 已验证」**，并把它作为已知风险登记进 `## Deferred But Adjudicated`。
- **先例摆在这里，不是假设**：同一批门禁在本机 6 跑红过 1 次（不可复现）、在 runner 上 2 跑红过 2 次（可复现，真红，
  最后查出是 `agenerp/oob.py` 的 `run_json` 把「exit 0 且 stdout 全空」判成载荷不是 JSON）。两种走向都发生过。

**CI 运行预算（裁判规则 4 的「单 mission 累计成本超阈值」也是停机条件）**

- 本 plan 声明的预算：**上限 7 次运行**（⚠️ **第 4 轮评审从 6 改为 7**，补上此前根本没有的第 0 步）——
  Phase 2 **第 0 步「先把 `main` 推到 `origin`」** 1（理由见该项：不先推平就拿不到 `baseRefOid == $RECUT`）·
  新分支的 PR 1 · 落地 push 1 · Phase 3 收尾**第一推** 1 · 收尾**第二推** 1（终止规则那一步）· 机动 2。
  `gates.yml` 的 `on: push: branches: [main]` **没有路径过滤**，因此每一次推 `main` 都会跑满全部 job
  （落地**前** 7 个、落地**后** 9 个），落地后每一次都含起一整套 ERPNext/MariaDB 栈的 `gates-l2-live`。
- **超出即停**：跑满 7 次仍未拿到 `main` 上的权威绿 → 停机，写 `STATE.md` §3 needs-human，**不得**继续加跑。

## Execution Plan

### Phase 1 — 前置核对与落地方式决策（一个字节都还没改）

Status: completed
Targets: 本 plan 文件
Skill: `none`

- Item Types: `Proof | Decision`
- Prereqs: 第一个 plan `2026-08-22-1206-1` 已 `completed`

- [x] `Proof` **前置八条实测核对，输出逐字抄进本 plan。任何一条不成立就停在这里，不往下走**：
      · ① 第一个 plan 的 `Plan Status` 逐字为 `completed`，且它的**四条**实验证据（run id + job id + conclusion）都在文件里
        （四条 = 正向必红 / revert 必绿 / 只动账本必不触发 / **触及且带 trailer 必放行**；缺第四条就停在这里——
        那条出口决定「人将来还能不能合法地改判定器」）；
      · ② **判据锚在前驱记下的 `$CUT`（它切分支那一刻的 `main` sha），不用两点式、也不用 `git merge-base main …`**
        （两点式在此处必然失败：前驱的 Phase 4 把 §14.4、`0027-2` 的审计行、日志与 `STATE.md` 提到了 `main` 而不是分支上，
        两点式会把它们全读成倒退；而 `git merge-base main <分支>` 会随本 plan 自己往 `main` 提交而漂）：
        `git diff --numstat "$CUT" ci/1206-1-verdict-guard-proof` → **恰好一行** `118	0	.github/workflows/gates.yml`；
      · ③ `gh pr view <前驱新建的 PR 号> --json state,changedFiles,additions,deletions` → `OPEN / 1 / 118 / 0`；
      · ④ 该 PR head 上最近一次运行**全绿**，其中 `gates-l2-live` `success`（run id 逐字）；
      · ⑤ Baseline E 那半的现状实测：`grep -n '2026-08-22-1206' docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md`
        → 期望零命中（确认那一行**确实还欠着**，不是凭 Baseline E 断定）；
      · ⑥ **收敛判据两条同时成立**（⚠️ 第 3 轮评审改准：此处原写的是「`git rev-parse main origin/main` 两值相等」，
        **那条在本 plan 开工那一刻必然为假**——前驱置 `completed` 需要一次独立关闭审计回填提交，
        它必然发生在前驱收尾推送**之后**，于是两个 plan 在这里**死锁**。前驱的收尾判据已同步改成下面这两条）：
        `git merge-base --is-ancestor origin/main main` → **成立**；且
        `git diff --name-only origin/main main` → 输出**只含** `docs/logs/**` 与 `docs/plans/p0-foundation/**`。
        任何一条不成立就停在这里——本 plan 的 `--ff-only` 与守卫时序都建立在这上面。
      · ⑦ **`baseRefOid` 那颗钉子仍在**：`gh pr view <前驱新建的 PR 号> --json baseRefOid` → 逐字等于 `$CUT`。
        **这一条不能省**（前驱 Baseline C5）：`pull_request` 的 `BASE` 在 PR 创建时钉死，
        它一旦不是 `$CUT`，前驱那四条实验证明的就不是「这 118 行」，本 plan 的 go/no-go 闸就建立在错的东西上。
      · ⑧ **PR #1 仍原封未动**：`gh pr view 1 --json state,headRefOid,baseRefOid` → `OPEN` / `c2c688b…` / `7b0f585…`
        （前驱的 Non-Goals 承诺不碰它；本 plan 的 Phase 3 才处置它）。
      - Skill: `none`
- [x] `Proof` **落地那一推的守卫预测（必须在推之前算出来，不能等 CI 告诉你）**。守卫在 `push` 上取
      `BASE=github.event.before` / `HEAD=github.sha`。因此推之前先在本地把同一个谓词算一遍：
      ⚠️ **先 `git fetch origin main`**（第 3 轮评审 nit）：本条自称硬闸，却读的是本地远程跟踪 ref `origin/main`；
      不 fetch 就可能拿一份陈旧的值当闸门。
      ⚠️ **Phase 1 时「落地 head」还不存在**（本 plan 的落地分支 `ci/1206-2-l2-live-land` 要到 Phase 2 第一步才建）。
      此刻拿前驱那条分支当代理先算一遍（两者的 118 行逐字相同）：
      · `git diff --name-only origin/main ci/1206-1-verdict-guard-proof -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
        → **期望无输出**；
      · `git log --format=%B origin/main..ci/1206-1-verdict-guard-proof | grep -c '^Gates-Change-Approved-By:'` → 记录实际值。
      **有约束力的那一次是 Phase 2 落地推之前的重算**，本条是提前暴露问题，不是替代它。
      ⚠️ **本条只写了 `push` 那一路，`pull_request` 那一路要一并写死（第 3 轮评审 nit）**：
      Phase 2 第二步那次 PR 运行也会跑守卫，且它的「全绿」是落地的硬闸，因此它走哪条出口同样必须**事先算定**。
      **它算的是 `BASE = 本 plan 新 PR 的 `baseRefOid`（= 第 0 步推平之后的 `main` sha，即 `$RECUT`）`、`HEAD = 分支 tip`**——
      新分支是从当时的 `main` 切出来的，所以两式退化成「`main` vs `main`+118 行追加」，与上面 `push` 那一路**数值上同解**，
      期望同样是情形 ①（`✅ 未触及判定器`）。**同解是推论不是巧合，这里写明，免得下一轮又去重新推导。**
      **三种结果各自对应守卫的哪条出口，先写死，别事后解释**：
      ① 上式无输出 → 期望 `✅ 未触及判定器`、`success`；
      ② 有输出且 trailer 计数 ≥1 → 期望 `✅ 找到人工批准 trailer，放行`、`success`；
      ③ 有输出且 trailer 计数 `0` → 期望**红**，且这是**真红**（说明落地区间里混进了判定器改动），
        按停机纪律处置，**不得**推。
      ⚠️ **这条预检是硬闸**：`origin/main` 若未追平（A3），区间里会混进 `57ad6d5`
      （改了判定器、无 trailer）→ 落到情形 ③，守卫必然红。第一个 plan 的两次 `main` push 就是为了消灭这个情形。
      ⚠️ **前置核对 ⑥ 只保证 Phase 1 开工那一刻的收敛，本阶段自己的日志/plan 提交会立刻让本地 `main` 领先 `origin/main`。
      ⚠️ 第 4 轮评审改准：这件事对守卫谓词无害（本阶段只碰文档），但对 Phase 2 的 PR 判据有害**——
      `baseRefOid` 钉的是建 PR 那一刻 `origin/main` 的 tip，本地领先就拿不到 `baseRefOid == $RECUT`，
      PR 读数也不会是 `1 / 118 / 0`。**所以 Phase 2 有一个第 0 步：先 `git push origin main` 推平，再切分支建 PR。**
      **落地推之前那次重算仍是唯一有约束力的守卫预检。**
      - Skill: `none`
- [x] `Decision` **落地失败怎么办（回滚 / 前滚 / 停机三选一，此处定死，别处不得再授权）**。
      - **选定**：**停机等人**。`main` 权威运行两次真红 → 写 `STATE.md` §3 needs-human 队列并置本 plan `deferred`，
        **loop 不自行 revert**。理由：`main` 无分支保护（Infra 那条 403 实测），红的 `main` 并不阻塞后续推送，
        没有「必须立刻回滚」的技术压力；而 revert 一个刚落地的判定 job 会把「工作项 9 的判据在 `main` 上成立」
        这件事**退回原点**，属于人该拍板的事。
      - **备选 (a) `git revert <落地 sha>`**：**不选（且不授权给执行器）**。方向上它是删一个门禁 job，
        与红线 2 的精神相抵；只有**人**可以选它。
      - **备选 (b) 前滚修 `agenerp/**`**：**不选**——那是本 plan 的 Non-Goal，且需要 Protected Areas
        末行要求的「实跑前后全量 `capture` 对照」证据，属另一个 plan。
      - **残余风险**：停机期间 `main` 上挂着一次红的权威运行，后续每轮 loop 都会看到它。
        **这正是想要的效果**——它是给人的可见信号，不是要被抹掉的噪声。
      - Skill: `none`
- [x] `Decision` **落地方式：`--ff-only` 合并本 plan 新开的那条分支，不用 squash，也不在 `main` 上另起提交**。
      ⚠️ **本项在第 3 轮评审随载体改换重写，第 4 轮再随分支改名改准**：落地对象**不是 PR #1**
      （前驱 Baseline C5：`pull_request` 的 `BASE` 在 PR 创建时钉死，PR #1 的 `baseRefOid` 永远停在 `7b0f585`，
      守卫在它上面恒红，前驱那四条实验根本做不成），**也不是前驱那条分支**
      （force-push 它会打漂前驱已关闭的证据判据，理由见下面那条前置），
      而是本 plan 在 Phase 2 新建的 `ci/1206-2-l2-live-land` 与它的新 PR。
      **PR #1 与前驱 PR 的终局处置都由本 plan 承担**，见本 Phase 的最后一个 `Decision`。
      - **选定**：`git switch main && git merge --ff-only ci/1206-2-l2-live-land && git push origin main`
        （分支是 `main` + 单提交，天然可 ff）。之后本 plan 那个新 PR 应自动变 `MERGED`。
      - **备选 (a) `gh pr merge --squash`**：等价产物，但会产生一个新 sha，PR head 的绿证据与 `main` 上的 sha 对不上，
        「哪个 sha 上跑绿的」这句话要多绕一层。**不选**。
      - **备选 (b) 直接在 `main` 上手工再 append 一遍、把两个 PR 都关掉**：**不选**。手工重写 118 行有逐字漂移风险，
        且会让这段配置**没有任何一条 PR 承载它的 CI 证据链**。
      - **约束（框架强制，不需要备选分析）**：ff-only 保证 `main` 上落地的 sha **就是** PR 上跑绿的那个 sha。
      - **⚠️ 前置：落地分支必须由本 plan 自己新切一条，这不是残余风险而是确定会发生的事**（独立评审 B2）。
        本仓 loop **每个 phase 往 `main` 提一次**（`git log --oneline` 可见 `plan-1041-1 Phase 1/2/3/4` 四连），
        因此第一个 plan 的 Phase 4 与本 plan 的 Phase 1 都会让 `main` 前进，
        `git merge-base --is-ancestor main <前驱分支>` 必然**不成立**。
        **本 plan 的 Phase 2 因此有第 0 步与第一步**（⚠️ **第 4 轮评审 blocking，两处都改了**）：
        · **第 0 步：`git push origin main`**，把 Phase 1 的文档提交推平，实测 `git rev-parse main origin/main` 两值相等。
          **不先推平，下一步的 `baseRefOid == $RECUT` 与 `1 / 118 / 0` 两条判据必然为假**——
          `baseRefOid` 钉的是**建 PR 那一刻 `origin/main` 的 tip**，本地领先时它拿不到本地 `main` 的 sha，
          且 PR 读数会把 Phase 1 的文档提交一并算进去。该次推送**已计入预算**。
        · **第一步：`RECUT=$(git rev-parse main)` → `git switch -c ci/1206-2-l2-live-land main`**
          → 追加同一份 118 行（对着保命闸存下的文件逐字比，见 Phase 2 那一项写的再生路径）
          → 单提交（**message 不得带 trailer**）→ `git push -u origin ci/1206-2-l2-live-land`（新分支，**不需要 force**）
          → `gh pr create --base main` → **取一次 PR 全绿**（已计入预算）。
          ⚠️ **不再用 `switch -C` 覆盖前驱的 `ci/1206-1-verdict-guard-proof`**：force-push 它会把前驱 Phase 4
          已关闭的那条判据 `git rev-parse ci/1206-1-verdict-guard-proof` 当场打漂，而前驱四条实验证据与它的 PR
          都挂在那条分支上。**本 plan 一个字节不碰前驱的分支与 PR**，它的终局处置见本 Phase 最后一个 `Decision`。
        ⚠️ **必须是新 PR，不能沿用前驱那个 PR（第 3 轮评审，直接推论自前驱 C5）**：
        `base.sha` 在 PR 创建时钉死，沿用旧 PR 会让 `BASE` 停在前驱的 `$CUT`，
        而新分支是从**更新的** `main` 切的，区间里会混进前驱 Phase 4 的文档提交——
        守卫虽仍会绿（那些提交不碰判定器），但 `changedFiles / additions / deletions` **不再是 `1 / 118 / 0`**，
        本 plan 自己的判据会因一个非理由失败。**规则一句话：每切一次分支就开一个新 PR，
        并先把 `origin/main` 推平，使 `baseRefOid == 切分支时的 `main` sha（记作 `$RECUT`）`。** 切完立刻实测并抄进 plan。
      - **硬约束**：从切分支到 ff-merge 之间，**不得**有任何提交落到 `main`。
        **这条不只约束 Phase 3**：**Phase 2 自己的收尾提交也必须排在 ff-merge 之后，phase 中途不得提交**——
        真正的威胁是本阶段自己，不是后面那个阶段。违反即回到第 0 步重来，**不得**用 merge commit 绕过。
        （第 0 步那次 `git push origin main` **不违反本条**：它发生在切分支**之前**。）
      - **残余风险**：`main` 若在切分支与 ff-merge 之间被别的东西推进（他人、另一轮 loop），
        新分支即不再可 ff，必须回到第 0 步重来；判据是落地时 `git rev-parse main` 仍等于 `$RECUT`。
      - Skill: `none`
- [x] `Decision` **PR #1 与前驱 PR 的终局处置（本 plan 独有，第 3 轮评审新增；第 4 轮随分支改名改准）**。
      落地之后仓库里会同时存在**三个** PR：PR #1（`OPEN`，`baseRefOid=7b0f585`，承载 run `32509351108` 红与 `32533449466` 绿）、
      前驱那个 PR（`ci/1206-1-verdict-guard-proof`，`OPEN`，承载四条实验证据，**本次不合并它**）、
      以及本 plan 新开的那个 PR（`ci/1206-2-l2-live-land`，被 ff-merge → `MERGED`）。
      - **选定**：**把 PR #1 与前驱那个 PR 都 `gh pr close`，各留一条说明评论**，评论逐字点名两件事：
        ① 它承载的那 118 行**已由 `<落地 sha>` 落进 `main`**；② 它的历史运行 id 与结论**保持可查**
        （PR #1：`gh run view 32509351108` / `32533449466`；前驱 PR：四条实验各自的 run id），不因关闭而消失。
      - **备选 (a) 让它们一直 `OPEN` 挂着**：**不选**。它们的 118 行与 `main` 上已落地的那份内容相同，
        留着会让「这段配置还没落地」这个错误印象长期存在，正是本 plan Goal 4 要消灭的那一族陈述。
      - **备选 (b) 把 PR #1 也 ff-merge 一次**：**不选**，且**做不到**——落地后它的 118 行与 `main` 上的重复，
        合并只会产生一个空变更或冲突；且它的分支落后 `main` 十几个提交，不满足 ff 的祖先要求。
      - **备选 (c) 改用前驱那个 PR 作落地载体**：**不选**（第 4 轮评审）——那要 force-push 前驱的证据分支，
        会打漂前驱 Phase 4 已关闭的判据 `git rev-parse ci/1206-1-verdict-guard-proof`。
        **改一条已关闭 plan 的证据锚，代价远高于多开一个 PR。**
      - **备选 (d) 删掉分支 `ci/0027-2-l2-full-live-gate` 或 `ci/1206-1-verdict-guard-proof`**：**不选**。
        删远程分支是不可逆动作，收益只有「少一条分支」，而它们是那些历史运行与四条实验证据的挂靠点。
        **本 plan 不删任何远程分支。**
      - **残余风险**：`gh pr close` 是可逆的（`gh pr reopen`），且不改任何 git 历史。**风险面接近零，照实记。**
      - Skill: `none`
- [x] `Decision` **授权面重新摆上台面（Baseline F，不得默认继承）**：记录本 plan **要真的改 `main` 的 workflow**，
      与第一个 plan（零改动 `main`）不同；选定处置是**沿用 `2026-08-21-2220-2` 的先例**（纯追加 = 加严，红线 2 允许），
      并在 `## Deferred But Adjudicated` 里把「`ai-autonomy-policy.md` 的 `blocked` 措辞待人裁定」这条**继续挂着**。
      **备选**：停下来等人裁定后再落地——**不选**，理由是先例已在 `main` 上落地过一次且未被推翻，
      而工作项 9 的关闭判据被这条未裁的措辞无限期挂起，代价大于风险。**残余风险**：若人事后裁定
      `.github/workflows/**` 严格 `blocked`，本次落地需要补一次追认；**该风险逐字登记，不掩盖**。
      - Skill: `none`

Exit Criteria:

- [x] **八条**前置核对输出逐字入 plan，全部成立（含 ⑥ 的两条收敛判据、⑦ 的 `baseRefOid == $CUT`、⑧ 的 PR #1 原封未动）
- [x] 守卫预测预检已**在推之前**算出，三种情形（①未触及 / ②带 trailer 放行 / ③无 trailer 必红）对应的出口已写死并逐字入 plan
- [x] 回滚 `Decision` 已选定「停机等人」，备选 (a)(b) 各有不选理由，残余风险已写明
- [x] 落地方式与授权面两个 `Decision` 各有选定、备选、约束、残余风险
- [x] **PR 终局处置 `Decision` 已选定并记录**：PR #1 与前驱 PR 各自的终局动作、四类备选的不选理由、残余风险
      （⚠️ 第 4 轮评审补：该 `Decision` 此前在 Phase 1 的 Exit Criteria 里没有任何一框对应，
      正是第 2 轮 blocking ⑤ 抓过的同一种毛病——`Decision` 没有 gate 就等于没有约束力）
- [x] `docs/logs/2026/08-22.md` 已追加本阶段记录

#### Phase 1 执行记录（2026-08-22 实跑回填）

**开工基线（本 plan 自己的锚）**

- `git log --oneline -1` → `79184e5`（= 本 plan 的**开工 sha**，Phase 3 红线自查一律锚它）；
  `git status --porcelain` → **无输出**（工作区干净）。
- `git rev-parse main origin/main` → `79184e56024c786f717b43e983752b39fcf9c342` / `10da9e7506ead7d1121130343649dc7728613bf5`
  —— 本地领先 **2** 个提交（`d1d30c5` 收尾推送结果回填、`79184e5` 文档/日志/roadmap 更新），
  **正是前置核对 ⑥ 预料的形态**，不是「两值相等」。
- `$CUT`（前驱切分支那一刻的 `main` sha，取自前驱 plan 第 5 轮实测行）
  = **`f689d0e7cde3f2733b044b004f7a314f14958973`**。前驱新建的 PR 号 = **#2**。

**① 前驱 plan 已 `completed`，四条实验证据在文件里**

- `grep -n '^> Plan Status:' docs/plans/p0-foundation/2026-08-22-1206-1-verdict-guard-mutation-proof.md`
  → `3:> Plan Status: completed` ✅
- 四条实验的 run id / head / 结论逐字在前驱 plan 的实验矩阵里：
  实验 ①（正向必红）`32570222139` head `47e0069` → `failure`（**预期红**）·
  实验 ②（revert 必绿）`32570426423` head `4516e7f` → `success` ·
  实验 ③（只动账本必不触发）`32570691388` head `a8e8305` → `success` ·
  实验 ④（触及且带 trailer 必放行）`32570942284` head `cf73d90` → attempt 1 `failure`（真红 #1）、
  attempt 2 **`success`**，守卫 job `97026657710` 输出逐字 `✅ 找到人工批准 trailer，放行`。
  **第四条在**（缺它就要停在这里），且前驱自己把它记成「同一 sha 上不可复现」，本 plan **不改写这个限定**。

**② 判据锚 `$CUT`，非两点式**

- `git diff --numstat f689d0e7cde3f2733b044b004f7a314f14958973 ci/1206-1-verdict-guard-proof`
  → **恰好一行** `118	0	.github/workflows/gates.yml` ✅
- 附带核对本地与远程该分支同 sha：`git rev-parse ci/1206-1-verdict-guard-proof origin/ci/1206-1-verdict-guard-proof`
  → 两值均 `b7348bf3a1eb1eccbe1c032af8bd73ed808ed4af` ✅

**③ 前驱 PR #2 的读数**

- `gh pr view 2 --json state,changedFiles,additions,deletions`
  → `{"additions":118,"changedFiles":1,"deletions":0,"state":"OPEN"}` —— 即 `OPEN / 1 / 118 / 0` ✅

**④ 该 PR head 上最近一次运行全绿**

- `gh run view 32571266013` → run **`32571266013`**（event `pull_request`，head `b7348bf`）→ **`success`**，
  **九个 job 全部 `success`**：`L1 快门禁` `97026942644` · `roadmap 引擎可解析` `97026942696` ·
  `预期红名单只能变短` `97026942704` · `L2 慢门禁（零依赖启动）` `97026942716` · `循环联动冒烟` `97026942728` ·
  **`L2 全量 live 判定（19 条）` `97026942737`** · `主计划引用不断链` `97026942741` ·
  `判定器未被改动` `97026942746` · `门禁未被改动` `97026942760` ✅

**⑤ Baseline E 那半确实还欠着**

- `grep -n '2026-08-22-1206' docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md`
  → **零命中**（退出码 `1`）✅ —— 欠账是实测确认的，不是凭 Baseline E 断定。

**⑥ 两条收敛判据同时成立**

- `git merge-base --is-ancestor origin/main main` → 退出码 **`0`**（成立）✅
- `git diff --name-only origin/main main` → 两行，**只含**
  `docs/logs/2026/08-22.md` 与 `docs/plans/p0-foundation/2026-08-22-1206-1-verdict-guard-mutation-proof.md` ✅
  （即只有 `docs/logs/**` 与 `docs/plans/p0-foundation/**`）

**⑦ `baseRefOid` 那颗钉子仍在**

- `gh pr view 2 --json baseRefOid` → `{"baseRefOid":"f689d0e7cde3f2733b044b004f7a314f14958973"}`
  —— **逐字等于 `$CUT`** ✅

**⑧ PR #1 仍原封未动**

- `gh pr view 1 --json state,headRefOid,baseRefOid` →
  `{"baseRefOid":"7b0f585f7c8082a64902da65e6e3314cb239dc9f","headRefOid":"c2c688b7f6bc49a96d1e89a3582014334ba8fb71","state":"OPEN"}`
  —— `OPEN` / `c2c688b…` / `7b0f585…`，与 Baseline 逐字一致 ✅

**八条全部成立，闸门放行。**

**守卫预测预检（在推之前算出，代理操作数 = 前驱分支）**

- `git fetch origin main` → exit 0（先刷新远程跟踪 ref，再读它当闸门）。
- `git diff --name-only origin/main ci/1206-1-verdict-guard-proof -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
  → **无输出** ⇒ 落在**情形 ①**：期望守卫走 `✅ 未触及判定器`、`success`。
- `git log --format=%B origin/main..ci/1206-1-verdict-guard-proof | grep -c '^Gates-Change-Approved-By:'` → **`0`**
  （与情形 ① 自洽：无触及则不需要 trailer）。
- **三种情形的出口在 plan 正文里已写死**：① 未触及 → 绿 · ② 触及 + trailer ≥1 → 放行绿 · ③ 触及 + trailer `0` → **真红，不推**。
- `pull_request` 那一路同解：新 PR 的 `BASE = baseRefOid = $RECUT`（第 0 步推平后的 `main` sha），
  `HEAD =` 分支 tip，两式退化成「`main` vs `main`+118 行追加」，期望同为情形 ①。
- ⚠️ **有约束力的那一次是 Phase 2 落地推之前的重算**，本条只提前暴露问题。

**四个 `Decision` 的选定**

- **落地失败怎么办** → 选定**停机等人**（备选 (a) `git revert` 不选且不授权给执行器、(b) 前滚修 `agenerp/**` 不选）。
  残余风险：停机期间 `main` 上挂着一次红的权威运行——**这正是要的可见信号**。
- **落地方式** → 选定 `git switch main && git merge --ff-only ci/1206-2-l2-live-land && git push origin main`；
  备选 (a) squash / (b) 手工再 append 各有不选理由；硬约束「切分支到 ff-merge 之间 `main` 零新提交」照 plan 正文。
- **PR 终局处置** → 选定：PR #1 与前驱 PR #2 **均 `gh pr close` 并各留说明评论**，**不删任何远程分支**；
  本 plan 新开的 PR 被 ff-merge → `MERGED`。四类备选 (a)(b)(c)(d) 的不选理由见正文。
- **授权面重新摆上台面** → 选定**沿用 `2026-08-21-2220-2` 的先例**（纯追加 = 加严，红线 2 只禁变松）；
  `ai-autonomy-policy.md` 的 `blocked` 措辞待人裁定这条**继续挂在 `## Deferred But Adjudicated` 里**。
  残余风险：人若事后裁定严格 `blocked`，本次落地需补一次追认——**逐字记着，不掩盖**。

### Phase 2 — 落地到 `main`，并取得权威运行

Status: completed
Targets: `.github/workflows/gates.yml`（**只在文件末尾追加**；追加动作发生在新分支 `ci/1206-2-l2-live-land` 上，
  经 `--ff-only` 到达 `main`，**不是直接在 `main` 上编辑**）· 本 plan 文件 · `docs/logs/2026/08-22.md`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1 完成

- [x] `Add` **第 0 步：先把 `main` 推到 `origin`（⚠️ 第 4 轮评审 blocking 新增，不得跳过）**。
      **为什么必须有这一步**：`baseRefOid` 钉的是**建 PR 那一刻 `origin/main` 的 tip**（前驱 C5 实测的正是这个含义），
      而 Phase 1 的日志/plan 提交只落在**本地** `main` 上。不先推平，下一步那两条判据
      （`baseRefOid == $RECUT`、读数 `1 / 118 / 0`）**必然为假**——失败模式与本 plan 自己诊断过的「沿用旧 PR」一模一样，
      判据会因一个非理由失败。
      · `git fetch origin main`；
      · **推之前先跑一次 Phase 1 那条守卫预测预检**（此刻 `main` 上还没有守卫，但 `origin/main..main` 里若混进判定器改动，
        落地那一推的区间同样会含它）：
        `git diff --name-only origin/main main -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs` → 期望**无输出**；
        有输出且 `git log --format=%B origin/main..main | grep -c '^Gates-Change-Approved-By:'` 为 `0` → 落到情形 ③，
        **不推**，按停机纪律处置；
      · `git push origin main`；
      · 实测 `git rev-parse main origin/main` **两值相等**，逐字抄进 plan；
      · 记录该次 `main` push 运行的 run id 与结论（此刻 `gates.yml` 仍是 **7** 个 job）。**已计入预算的第 1 次。**
      - Skill: `none`
- [x] `Add` **第一步：另起新分支 `ci/1206-2-l2-live-land` 并开一个新 PR**
      （⚠️ **第 4 轮评审 blocking：不再用 `switch -C` 覆盖前驱的 `ci/1206-1-verdict-guard-proof`**——
      force-push 会把前驱 Phase 4 已关闭的那条判据 `git rev-parse ci/1206-1-verdict-guard-proof` 当场打漂，
      而前驱的四条实验证据与它的 PR 都挂在那条分支上。**本 plan 一个字节不碰前驱的分支与 PR。**）。
      `RECUT=$(git rev-parse main)` → `git switch -c ci/1206-2-l2-live-land main` → 在 `.github/workflows/gates.yml`
      末尾追加那 118 行 → **单**提交（**message 不得含 `Gates-Change-Approved-By:`**）
      → `git push -u origin ci/1206-2-l2-live-land`（新分支，**不需要 force**）
      → `gh pr create --base main --head ci/1206-2-l2-live-land`。
      ⚠️ **那 118 行从哪来（⚠️ 第 4 轮评审补：原写法只认一个跨会话易失的临时文件，没有再生路径）**：
      优先对着第一个 plan 保命闸存下的 `/tmp/two-jobs.yml` 逐字比
      （`diff /tmp/two-jobs.yml <(tail -n 118 .github/workflows/gates.yml)` → 无输出）；
      **`/tmp` 跨会话易失**，文件不在就**原地再生**，两条路等价（同一个远程 ref 的同一段字节）：
      `git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml | tail -n 118 > /tmp/two-jobs.yml`，
      再生后先自检 `grep -E '^  [a-z0-9-]+:' /tmp/two-jobs.yml` → 恰为 `gates-l2-live:` 与 `verdict-tool-untouched:` **两行**。
      判据六条（缺一条都可能把别的文件顺手扫进那个提交而没人发现）：
      · `git merge-base --is-ancestor main ci/1206-2-l2-live-land` → **成立**（退出码 0）；
      · `git diff --numstat "$RECUT" ci/1206-2-l2-live-land` → **恰好一行** `118	0	.github/workflows/gates.yml`；
      · `git log --oneline "$RECUT"..ci/1206-2-l2-live-land | wc -l` → `1`（唯一那个追加提交）；
      · `gh pr view <新 PR 号> --json baseRefOid` → **逐字等于 `$RECUT`**
        （前驱 C5 那颗钉子，本阶段自己也要钉一次；它成立的前提就是第 0 步已把 `origin/main` 推到 `$RECUT`）；
      · `gh pr view <新 PR 号> --json changedFiles,additions,deletions` → `1 / 118 / 0`；
      · **`$RECUT` 的值当场抄进 plan**（Exit Criteria 里那条「落地时 `git rev-parse main` 仍等于 `$RECUT`」要拿它比对，
        不记下来那条判据就没法跑）。
      - Skill: `none`
- [x] `Proof` **新 PR 上取一次全绿**（`gates-l2-live` `success`，run id 与全部 job 结论逐字）。
      **不能省**：ff-merge 落到 `main` 的就是这个 sha，「落地的 sha 就是跑绿的 sha」这句话靠它成立。
      - Skill: `none`
- [x] `Add` 按 Phase 1 的 `Decision` 执行 `--ff-only` 合并并推 `main`。记录落地 sha。
      **推之前重跑一次 Phase 1 那条守卫预测预检**（`main` 可能在这期间被别的东西推进过），三种情形的处置照 Phase 1 写死的走。
      - Skill: `none`
- [x] `Proof` **红线 2 自查五条（机械可核，输出逐字抄进 plan）**：
      · **(a) 前缀性**：`diff <(git show "$RECUT":.github/workflows/gates.yml) <(head -n 190 .github/workflows/gates.yml)`
        （⚠️ **第 4 轮评审：锚点从写死的 `aba9a5f` 换成 `$RECUT`**——与前驱第 5 轮「一律锚开工 sha」同口径。
        实测 `gates.yml` 在 `aba9a5f..4d7b311` 之间**逐字节未变**，两个锚今天同解，但浮动锚才不会随 `main` 前进而失效）
        → 期望**无输出**。这一条同时证明「既有 7 个 job 一行未改」「`on:` / `permissions:` 未动」「零删除」，
        比 `deletions=0` 严——往既有 job 里**插**一行也是纯新增，`deletions=0` 抓不到它；
      · **(b) job 键集合**：落地后 `sed -n '/^jobs:/,$p' .github/workflows/gates.yml | grep -E '^  [a-z0-9-]+:'`
        → 期望**9 个**，即原 7 个**原序原名**加末尾两个新的；
      · **(c) 禁用词**：`grep -nE 'continue-on-error|if: *false|\bdisabled\b' .github/workflows/gates.yml` → 期望**零命中**；
      · **(d) 触发范围**：`on:` 块逐字与 `$RECUT` 上的那份相同（已被 (a) 覆盖，单独再记一次因为红线 2 逐字点名了「缩小触发范围」）；
      · **(e) 无失败吞噬（⚠️ 起草时这条写错了，已按实测改准）**：`if: always()` 只出现在**取证步骤与拆栈步骤**上，
        判定步骤**没有** `continue-on-error` —— 这两句成立。**但「没有 `|| true` 兜底」不成立**：
        `grep -n '|| true' .github/workflows/gates.yml` 实测命中两处，其中**一处就在新守卫体内**
        （`CHANGED=$(git diff --name-only "$BASE" "$HEAD" -- 'tools/gates/check_expected_red.py' 'tools/gates/gate-verify.mjs' || true)`），
        另一处是既有 `gates-untouched` 的同款写法。它是一个**真实的假阴入口**（`git diff` 出错 → `CHANGED` 空 →
        `✅ 未触及判定器` → `exit 0`），**继承自既有 job，非本批引入**。
        因此本条的正确说法收窄为：**判定与守卫的 `exit 1` 路径没有被吞掉**；假阴入口已登记进 `## Deferred But Adjudicated`。
      - Skill: `none`
- [x] `Proof` **`main` 的 push 运行 = NB2 的权威运行**。逐字记录 run id、全部 job 的 id 与 conclusion。
      判据两条：
      · `gates-l2-live` **`success`**，日志逐字 `门禁 19 项：红 0，绿 19，跳过 0` 与 `✅ live 判定：全部门禁绿，零 red、零 skip`；
      · 其余 8 个 job 全部 `success`。
      **这次运行同时是守卫 `verdict-tool-untouched` 的 `push` BASE/HEAD 推导路径（`github.event.before` / `github.sha`）
      的首次实测** —— 第一个 plan 的四条实验只覆盖 `pull_request`。
      **守卫走哪条出口由 Phase 1 的预检在推之前算定**（情形 ①/②/③），此处只做核对，**不做预测式断言**：
      实测出口必须与预检算出的那一条一致；不一致本身就是发现，照实记并按停机纪律分流。
      **照实记的边界**：即便走到 ①，它也只证明 `push` 路径能跑通并走到「未触及」分支，
      **不证明它在 `push` 上有牙齿**——`push` 上的正向变异实验要在 `main` 上故意改判定器，代价过高，登记为残余。
      - Skill: `none`
- [x] `Proof` **红了怎么办，按「停机纪律」执行**，三条走向（复跑绿 / 可复现红 / 不可复现）各自的处置已写死，
      执行时照做并逐字留痕，**不得**临场放宽。
      - Skill: `none`
- [x] `Proof` **三个 PR 的终局状态（⚠️ 第 4 轮评审随分支改名重写：被合并的是本 plan 新开的那个 PR）**：
      · **本 plan 新开的那个 PR**（`ci/1206-2-l2-live-land`）→ `gh pr view <号> --json state,mergeCommit` 期望 `state: MERGED`。
        ⚠️ **`mergeCommit` 允许是 `null`**：PR 由一次 push（而非合并按钮）关闭时 GitHub 常报 `null`，
        拿它当判据会让一个正确的结果判失败。**真正的不变式用这条钉**：
        `git merge-base --is-ancestor <该 PR head sha> origin/main` → 退出码 `0`；
      · **前驱那个 PR**（`ci/1206-1-verdict-guard-proof`）→ 它**不参与本次 ff-merge**，因此终局是**确定的、不是待观察的**：
        按 Phase 1 那条 `Decision` 执行 `gh pr close` 并留说明评论，期望 `state: CLOSED`；
        **分支不删**，前驱四条实验的挂靠点原样保留
        （⚠️ 第 4 轮评审改准：旧写法「同一条分支名，GitHub 自动关闭行为本仓未实测过，不强求某个值」
        的不确定性来自「复用前驱分支名」这个已被推翻的设计，改用新分支后它不再存在）；
      · **PR #1** → 同样按 Phase 1 那条 `Decision` 执行 `gh pr close` 并留说明评论，
        终局期望 `state: CLOSED`，且两条历史 run 仍 `gh run view` 可查（各跑一次，输出抄进 plan）。
      - Skill: `none`

Exit Criteria:

- [x] **第 0 步已执行**：`git push origin main` 之后实测 `git rev-parse main origin/main` **两值相等**（逐字入 plan），
      该次 push 运行的 run id 与结论已记录
- [x] 新分支 `ci/1206-2-l2-live-land` 已建，`git merge-base --is-ancestor main ci/1206-2-l2-live-land` 成立，
      新 PR 的 `baseRefOid == $RECUT` 且读数为 `1 / 118 / 0`；该 PR 上有一次全绿（run id 逐字）
- [x] **前驱分支 `ci/1206-1-verdict-guard-proof` 与它的 PR 一个字节未动**：
      `git rev-parse origin/ci/1206-1-verdict-guard-proof` 与前驱 Phase 4 记下的 sha 逐字相同
- [x] 从切分支到 ff-merge 之间 `main` 零新提交（判据：落地时 `git rev-parse main` == `$RECUT`）
- [x] `main` 上 `gates.yml` 有 9 个 job 键，新增两个在末尾，前 190 行逐字节未动
- [x] 红线 2 自查五条输出均为期望值，其中 (e) 已按 `|| true` 的实测收窄，未写成「零吞噬」
- [x] `main` push 权威运行的 run id 与全部 job 结论逐字入 plan，`gates-l2-live` `success`
- [x] 守卫实测出口与 Phase 1 预检算定的那一条**一致**；结论**没有被写成「守卫在 push 上已有牙齿」**
- [x] **落地的那个 PR** 状态为 `MERGED`；不变式用 `git merge-base --is-ancestor <该 PR head> origin/main` 钉住
      （不拿 `mergeCommit` 当判据）
- [x] **PR #1 与前驱 PR 均已 `CLOSED` 并各留有说明评论**；PR #1 的两条历史 run（`32509351108` / `32533449466`）
      与前驱四条实验的 run 实测仍可 `gh run view`；**未删除任何远程分支**
- [x] `docs/logs/2026/08-22.md` 已追加本阶段记录

#### Phase 2 执行记录（2026-08-22 实跑回填）

**第 0 步：先把 `main` 推到 `origin`**

- `git fetch origin main` → exit 0。
- **推前守卫预检**：`git diff --name-only origin/main main -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
  → **无输出** ⇒ 情形 ①；`git log --format=%B origin/main..main | grep -c '^Gates-Change-Approved-By:'` → `0`。
  区间三个提交（`d1d30c5` / `79184e5` / `bb83b20`）改动的文件只有 `docs/logs/**` 与 `docs/plans/p0-foundation/**`。
- `git push origin main` → exit 0，`10da9e7..bb83b20`。
- **实测两值相等**：`git rev-parse main origin/main` →
  `bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf` / `bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf` ✅
- **该次 `main` push 运行**：run **`32572388207`**（event `push`，head `bb83b20`）→ **`success`**，
  **七个 job**（此刻 `gates.yml` 仍是 7 个 job，这本身是一条证据）全部 `success`：
  `L1 快门禁` `97029653922` · `循环联动冒烟` `97029654056` · `roadmap 引擎可解析` `97029654071` ·
  `L2 慢门禁（零依赖启动）` `97029654077` · `预期红名单只能变短` `97029654115` ·
  `主计划引用不断链` `97029654118` · `门禁未被改动` `97029654171`。**预算第 1 次。**

**第一步：新分支 `ci/1206-2-l2-live-land` 与新 PR #3**

- **`$RECUT` = `bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf`**（切分支那一刻的 `main` sha，当场记下）。
- **那 118 行的来源**：`/tmp/two-jobs.yml` 跨会话已失，走**再生路径**
  `git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml | tail -n 118 > /tmp/two-jobs.yml`；
  再生自检 `grep -E '^  [a-z0-9-]+:' /tmp/two-jobs.yml` → **恰为两行** `gates-l2-live:` / `verdict-tool-untouched:` ✅；
  额外冗余核对 `diff <(git show ci/1206-1-verdict-guard-proof:.github/workflows/gates.yml | tail -n 118) /tmp/two-jobs.yml`
  → **无输出**（两条路确是同一段字节）。
- `git switch -c ci/1206-2-l2-live-land main` → 追加后 `.github/workflows/gates.yml` 由 **190 → 308** 行；
  `diff <(tail -n 118 .github/workflows/gates.yml) /tmp/two-jobs.yml` → **无输出**；
  `python3 -c "import yaml; yaml.safe_load(...)"` → exit 0。
- 单提交 **`3503f2c`**（message **不含** `Gates-Change-Approved-By:`）→ `git push -u origin ci/1206-2-l2-live-land`
  （**新分支，普通 push，无 force**）→ `gh pr create --base main --head ci/1206-2-l2-live-land` → **PR #3**。
- **六条判据全部为期望值**：
  · `git merge-base --is-ancestor main ci/1206-2-l2-live-land` → 退出码 **`0`** ✅
  · `git diff --numstat "$RECUT" ci/1206-2-l2-live-land` → **恰好一行** `118	0	.github/workflows/gates.yml` ✅
  · `git log --oneline "$RECUT"..ci/1206-2-l2-live-land | wc -l` → **`1`** ✅
  · `gh pr view 3 --json baseRefOid` → `bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf`，**逐字等于 `$RECUT`** ✅
    （第 0 步推平的直接收益：这条判据在没有第 0 步时必然为假）
  · `gh pr view 3 --json changedFiles,additions,deletions` → `1 / 118 / 0` ✅
  · trailer 洁净度 `git log --format=%B "$RECUT"..ci/1206-2-l2-live-land | grep -c '^Gates-Change-Approved-By:'` → `0` ✅
- **前驱分支与 PR 一个字节未动**：本步用的是 `switch -c` + 新分支名，全程未碰 `ci/1206-1-verdict-guard-proof`。

**新 PR 上的一次全绿（预算第 2 次）**

- run **`32572416547`**（event `pull_request`，head `3503f2c`）→ **`success`**，**九个 job 全部 `success`**：
  `预期红名单只能变短` `97029725274` · `门禁未被改动` `97029725416` · `roadmap 引擎可解析` `97029725419` ·
  `主计划引用不断链` `97029725439` · `循环联动冒烟` `97029725444` · `L1 快门禁` `97029725454` ·
  **`判定器未被改动` `97029725459`** · **`L2 全量 live 判定（19 条）` `97029725467`** ·
  `L2 慢门禁（零依赖启动）` `97029725572`。
- `gates-l2-live` 日志逐字：`门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。
- 守卫日志逐字：`BASE="bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf"; HEAD="3503f2c89d78f44f94e0e0ff9f6061ca72e90b89"`
  → **`✅ 未触及判定器`** —— 与 Phase 1 预检算定的**情形 ①** **一致** ✅
  （同时实测确认 `BASE` 就是 `baseRefOid` = `$RECUT`，`pull_request` 与 `push` 两路同解那条推导成立）。
- **「落地的 sha 就是跑绿的 sha」**：这次跑的 head `3503f2c` 就是下一步 ff 到 `main` 的那个 sha。

**`--ff-only` 落地（预算第 3 次）**

- **推之前重跑守卫预检**（`main` 可能被别的东西推进过）：`git fetch origin main` → exit 0；
  `git diff --name-only origin/main ci/1206-2-l2-live-land -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
  → **无输出** ⇒ 仍是**情形 ①**；trailer 计数 `0`。
- **切分支到 ff-merge 之间 `main` 零新提交**：落地前 `git rev-parse main` → `bb83b20…`，**逐字等于 `$RECUT`** ✅
  （Phase 2 自己的收尾提交排在 ff-merge 之后，phase 中途未提交）。
- `git switch main && git merge --ff-only ci/1206-2-l2-live-land` → `Updating bb83b20..3503f2c` / `Fast-forward` /
  `1 file changed, 118 insertions(+)`；`git push origin main` → exit 0，`bb83b20..3503f2c`。
- **落地 sha = `3503f2c89d78f44f94e0e0ff9f6061ca72e90b89`**，与 PR #3 的 head **逐字相同**。

**红线 2 自查五条（落地后实跑）**

| # | 命令 | 输出 | 判定 |
|---|---|---|---|
| (a) 前缀性 | `diff <(git show "$RECUT":.github/workflows/gates.yml) <(head -n 190 .github/workflows/gates.yml)` | **无输出**，退出码 `0` | ✅ 既有 7 个 job 一行未改、`on:`/`permissions:` 未动、零删除，且「往既有 job 里插一行」也被挡住 |
| (b) job 键集合 | `sed -n '/^jobs:/,$p' .github/workflows/gates.yml \| grep -E '^  [a-z0-9-]+:'` | **9 个**：`gates-untouched` · `expected-red-ratchet` · `gates-l1` · `masterplan-links` · `roadmap-parseable` · `loop-wiring` · `gates-l2` · **`gates-l2-live`** · **`verdict-tool-untouched`** —— 原 7 个**原序原名**，新增两个在**末尾** | ✅ |
| (c) 禁用词 | `grep -nE 'continue-on-error\|if: *false\|\bdisabled\b' .github/workflows/gates.yml` | **零命中**（退出码 `1`） | ✅ |
| (d) 触发范围 | `diff <(git show "$RECUT":….yml \| sed -n '1,/^jobs:/p') <(sed -n '1,/^jobs:/p' ….yml)` | **无输出** | ✅ `on:` 块逐字未动（已被 (a) 覆盖，因红线 2 逐字点名「缩小触发范围」而单记一次） |
| (e) 失败吞噬 | `grep -n '\|\| true' .github/workflows/gates.yml` → **两处**：`36`（既有 `gates-untouched`）、`293`（新守卫体内，同款写法）；`grep -n 'if: always()'` → 六处，全部在**取证步骤与拆栈步骤**上，判定步骤**没有** `continue-on-error` | —— | ⚠️ **正确说法收窄为「判定与守卫的 `exit 1` 路径没有被吞掉」**。`\|\| true` 那个**假阴入口真实存在**（`git diff` 出错 → `CHANGED` 空 → `✅ 未触及判定器` → `exit 0`），已登记进 `## Deferred But Adjudicated`。**不写成「零吞噬」。** |

**NB2 的权威运行（`main` push，预算第 4 次）**

- run **`32572618933`**（event **`push`**，head **`3503f2c`**）→ **`success`**，**九个 job 全部 `success`**：
  `门禁未被改动` `97030229573` · `循环联动冒烟` `97030229628` · `L1 快门禁` `97030229662` ·
  **`L2 全量 live 判定（19 条）` `97030229667`** · `roadmap 引擎可解析` `97030229671` ·
  `主计划引用不断链` `97030229672` · `L2 慢门禁（零依赖启动）` `97030229696` ·
  **`判定器未被改动` `97030229697`** · `预期红名单只能变短` `97030229729`。
- `gates-l2-live` 日志**逐字**：`门禁 19 项：红 0，绿 19，跳过 0` /
  `✅ live 判定：全部门禁绿，零 red、零 skip` ✅
- **⇒ 工作项 9 的关闭判据第一次在 `main` 上成立**（「`gates.yml` 上存在一个 job，在 live 判定环境下用
  `tools/gates/check_expected_red.py` 对 `tests/gates` 全部 19 条判定并 `success`」）。
- **守卫 `push` 路径首次实测**：日志逐字
  `BASE="bb83b2039efd9c733ff9c9aa0bba85b4bbb11edf"; HEAD="3503f2c89d78f44f94e0e0ff9f6061ca72e90b89"`
  （即 `github.event.before` / `github.sha`）→ **`✅ 未触及判定器`**，
  **与 Phase 1 预检在推之前算定的情形 ① 一致** ✅
  ⚠️ **照实记的边界**：它只证明 `push` 路径**能跑通并走到「未触及」分支**，
  **不证明守卫在 `push` 上已有牙齿**——正向变异要在 `main` 上故意改判定器，代价过高，已登记为残余。
- **停机纪律未被触发**：本 plan 期间**没有任何一次红**（第 0 步 7/7 · PR #3 9/9 · 权威运行 9/9），
  因此「复跑绿 / 可复现红 / 不可复现」三条走向**一条都没走到**，无临场放宽可言。
- **CI 运行次数 4 / 7**（`32572388207` · `32572416547` · `32572618933`，外加 Phase 3 收尾两推待记）。

**三个 PR 的终局状态**

- **PR #3**（`ci/1206-2-l2-live-land`，本 plan 新开）→ `gh pr view 3 --json state,mergeCommit,headRefOid`
  → `state: **MERGED**`，`mergeCommit.oid` = `3503f2c…`（本次它非 `null`，但**判据不靠它**）。
  **不变式**：`git merge-base --is-ancestor 3503f2c89d78f44f94e0e0ff9f6061ca72e90b89 origin/main`
  → 退出码 **`0`** ✅
- **PR #2**（前驱 `ci/1206-1-verdict-guard-proof`）→ 已 `gh pr comment` 留说明评论
  （`#issuecomment-5380403008`，逐字点名落地 sha 与四条实验各自的 run id）+ `gh pr close`
  → `state: **CLOSED**`；`headRefOid` 仍为 `b7348bf3a1eb1eccbe1c032af8bd73ed808ed4af`，
  与前驱 Phase 4 记下的 sha **逐字相同**（**一个字节未动**）✅
- **PR #1** → 已 `gh pr comment` 留说明评论（`#issuecomment-5380401581`）+ `gh pr close`
  → `state: **CLOSED**`；两条历史 run 实测仍可查：
  `gh run view 32509351108` → `failure`（那次**可复现的红是永久证据**，未被抹掉）·
  `gh run view 32533449466` → `success`。
- **前驱四条实验的 run 实测仍可查**：`32570222139` → `failure` · `32570426423` → `success` ·
  `32570691388` → `success` · `32570942284` → `success`。
- **未删除任何远程分支**：`git ls-remote --heads origin` → `ab/codex-sol` · `ci/0027-2-l2-full-live-gate` ·
  `ci/1206-1-verdict-guard-proof` · `ci/1206-2-l2-live-land` · `main` —— **五条都在** ✅

### Phase 3 — owner-doc 漂移就地改准 + 还清 `0027-2` 的最后一项欠账

Status: planned
Targets: `docs/backlog/p0-foundation-roadmap.md`（「9 现状」「5 现状」「6 现状」三行）·
  `docs/context/project-context.md`（L2 那几行的验证范围表述）· `docs/architecture/system-baseline.md`（§14.4）·
  `docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md`（**只追加**）·
  `docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（**只在 `Closure Audit Log` 追加**）·
  `docs/logs/2026/08-22.md` · `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Fix | Proof`
- Prereqs: Phase 2 完成且权威运行结论已知

- [ ] `Fix` **改准「`main` 上没有这个 job」这一族陈述**。落地之后它们成为**确认的 owner-doc 漂移**，
      按 Minimum Rule 14 **不得降级成 follow-up**。**先实测定位再改，不凭本行列举的位置动手**：
      `grep -rn 'main.*上.*没有这个 job\|本机独证\|PR #1 仍未合并\|未合并\|红在实现' docs/context/ docs/backlog/ docs/architecture/`
      —— 命中的每一处**逐条裁定，不是逐条照改**：是确认漂移的**就地改准**；
      判定为**非漂移**的（与本议题无关的用词命中——本条这个 grep 的作用域内起草时实测有**一条**：
      `docs/architecture/module-boundaries.md:305` 讲的是「无活站点不等于错误……红在环境而不是红在实现」这条设计原则）
      **逐字记明命中位置与不改的理由**，**不得静默略过**。
      ⚠️ **`docs/masterplan/archive/STATE-2026-08-22.md:177`（冻结的历史记录）不是本条的命中**——
      本条 grep 的作用域是 `docs/context/ docs/backlog/ docs/architecture/`，够不着它；
      它只会被**下一项**那个 `docs/masterplan/` 的 grep 捞到，处置也归下一项（第 3 轮评审改准，
      此前把它列在这里，会让执行者拿本条的 grep 输出去对，发现只有一条非漂移而误以为基线漂了）。**两处补正，别用起草时那条更窄的 grep**：
      · 加上 `红在实现` 这个词——`docs/architecture/system-baseline.md` 里那句
        「**红在实现，不是红在判据**：`apply_pack` 的物理列清除面在 runner 的全新站点上不成立」
        **今天就已经是确认漂移**（被 `0228-2` 的「清除面从来没坏过」推翻，且 `d27c9a2` 那次回写没碰过这个文件），
        而起草时那条 grep **匹配不到它**——靠挑 pattern 把一条确认漂移挡在外面，就是 Minimum Rule 14 的绕行；
      · 目录范围放宽到三个目录，别只点三个文件。
      **写法约束**：写成什么由 Phase 2 的实测结论决定（`success` / 「首轮红、复跑绿、不可复现」/ 「可复现红」三选一），
      **绝不能写成比证据更强的说法**。
      - Skill: `none`
- [ ] `Fix` **`docs/masterplan/` 只读边界（这是一条常设禁令，不是上面那条 grep 的结论）**：
      上面的 `grep` 作用域**不含** `docs/masterplan/`，所以它永远不会替你发现这里的问题。
      本项要求**另跑一次，且用与上一项完全相同的 pattern**（第 3 轮评审：两处 pattern 无理由不同；
      实测今天两者在 `docs/masterplan/` 上返回相同的 7 条，但那是巧合不是保证）：
      `grep -rn 'main.*上.*没有这个 job\|本机独证\|PR #1 仍未合并\|未合并\|红在实现' docs/masterplan/` ——
      命中 `STATE.md` 以外的任何文件都**不得就地改**（红线 5），改用
      「在 `STATE.md` §2/§3 追加一条改准事实行」的既有先例处置；`STATE.md` 自身也只许追加。
      这是本仓已经用过两次的手法（0228-2 的「红线 5 不允许改写本文件已有行，故此处只追加」）。
      - Skill: `none`
- [ ] `Fix` **还清 `0027-2` Phase 3 的那一项（Baseline E）**：在 plan `2026-08-21-2220-2` 的
      `## Deferred But Adjudicated` 相应两条**下方追加**一行，**点名两个 plan 的完整 id**
      （`2026-08-22-1206-1-verdict-guard-mutation-proof` 与 `2026-08-22-1206-2-gates-l2-live-lands-on-main`——
      不要写「本批两个 plan」，`0027-2` 里那句「本批两个 plan」指的是 `0027-1`/`0027-2`，会读混）与 `main` 上的权威运行 run id，
      记为**了结**。⚠️ **不改写它任何已有行**——那是别人的关闭证据。
      **这一项现在才写得出来**：0027-2 逐字规定「拿不到这三条，守卫不算交付」，
      **四条**已由第一个 plan 交付（原文只要求三条），因此「了结」不再是比证据更强的说法。
      - Skill: `none`
- [ ] `Fix` **`0027-2` 的 `Closure Audit Log` 追加一行，只写本 plan 还的那一项**：Phase 3 的「把前驱两条 Deferred 记为了结」。
      Phase 2 那项（守卫实证）**由第一个 plan 自己追加过一行，本 plan 只引用它、不复述**（避免同一事实在同一文件里出现两次，
      读的人分不清是两次事件还是一次）。同时写明**它自身的 `Plan Status` 与 19 个 `[ ]` 由人裁定**。
      ⚠️ **不改它的 `Plan Status`、不勾它任何一个 `[ ]`**：它欠的 19 框里还有整个 `## Closure Gates`
      与它自己的 Exit Criteria，代打勾即伪造它的关闭证据——它三次独立关闭审计都拒绝过这件事。
      判据**四条**（第 3 轮评审改准：第 2 轮补了 `[x]` 那一条却没改这个数，正是它自己在 Phase 1 抓过的同一种毛病），
      改动前后都要跑（**路径写全，别用省略号；只钉 `19` 不够**——该文件 `[ ]` 的**总**出现次数是 `24`，
      追加的 `Closure Audit Log` 行里若带方括号对，锚定式的 `19` 看不见它）：
      · `grep -c '^\s*-\s\[ \]' docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md` → `19`；
      · `grep -c '\[ \]' docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`
        → **不写死数字，记实测值，要求落地前后两次相同**（起草时是 `24`，但第一个 plan 的 Phase 4 也会往同一个
        `Closure Audit Log` 追加，追加行里若含一对方括号这个数就变；写死会让本 plan 因一个非理由停下）；
      · `grep -c '^\s*-\s\[x\]' docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`
        → 同样记实测值并要求前后相同（**只钉未勾数挡不住「新增一条已勾行」**）；
      · `grep -c '^> Plan Status: deferred' docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md` → `1`。
      - Skill: `none`
- [ ] `Fix` **roadmap「9 现状」行改准**：写明两个新 job 已在 `main` 上、`main` push 权威运行的 run id 与结论、
      守卫**四条**实验的 run id、以及**工作项 9 的关闭判据是否成立的事实陈述**。
      ⚠️ **不自行把工作项 9 置 `done`**（Non-Goals 第一条：状态由引擎在 closure 审计通过后回写）。
      同时写清与**工作项 8** 的包含关系：9 的判据（CI 上判 19 条）覆盖 8 的判据（`gates-l2` 直接判 3 条），
      但 **9 绿不代表 8 可置 `done`**——8 的 `done` 仍卡在「从预期红名单划掉」上，那是
      `docs/backlog/needs-human-expected-red-handoff.md` 里的人裁定题。
      - Skill: `none`
- [ ] `Proof` **收尾复跑（本机，用开工 sha 作基线，不用裸 `git diff`）**：
      · `python3 tools/gates/check_expected_red.py` → 期望 exit 0（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`）；
      · `python3 -m pytest tests/unit -q` → 期望 exit 0；
      · `python3 -m pytest tests/contracts -q` → 期望 exit 0；
      · `ruff check agenerp tests/unit tests/contracts` → 期望 exit 0；
      · `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))"` → 期望 exit 0。
      - Skill: `none`
- [ ] `Proof` **红线自查（机械可核，输出逐字抄进 plan）**：
      · `git diff --stat <开工 sha>..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` → 期望**输出为空**；
      · `git status --porcelain -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` → 期望**输出为空**；
      · `git diff --numstat <开工 sha>..HEAD -- tools/gates/expected-red.txt` → 期望**输出为空**；
      · `git diff <开工 sha>..HEAD -- docs/masterplan/STATE.md | grep '^-' | grep -v '^---'` → 期望**输出为空**（只追加）；
      · `git diff --numstat <开工 sha>..HEAD -- docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md`
        → 期望**删除列为 `0`**（只追加，不改写他人关闭证据）。
      - Skill: `none`
- [ ] `Proof` 全部命令原文 + 退出码 + commit sha 写进 `docs/logs/2026/08-22.md` 与 `STATE.md` §2（**只追加**）；
      并在 `STATE.md` §3 追加一条处置事实行，记 `0027-2` 两项欠账的了结与它 `Plan Status` 仍待人裁定。
      - Skill: `none`
- [ ] `Fix` **收尾把 `main` 推到 `origin`，让 `git rev-parse main origin/main` 重新相等**。
      **为什么必须有这一项**：落地之后 Phase 2 的收尾提交与 Phase 3 的全部文档提交都只落在**本地** `main` 上，
      不推的话闭幕时 `origin/main` 会落后 2 个以上提交，而 `## Closure Gates` 里那条「落地后同样相等」当场为假。
      ⚠️ **这一推与之前所有推都不同：守卫此刻已经活在 `main` 上**。因此**推之前必须重跑 Phase 1 那条守卫预测预检**：
      · `git diff --name-only origin/main main -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
        → 期望**无输出**（Phase 3 只改文档）；
      · `git log --format=%B origin/main..main | grep -c '^Gates-Change-Approved-By:'` → 记录实际值。
      落到情形 ③（有判定器改动且无 trailer）就**不推**，按停机纪律处置。
      推后记录那次 `main` push 运行的 run id 与**全部 9 个 job** 的结论；红了按停机纪律走。
      ⚠️ **回归的终点在此写死（第 3 轮评审 blocking：原写法不可满足）**。
      问题的形状：「推完 → 记 run id」这个记录动作本身是一次 `main` 提交，它当场打破同一条判据里的
      「`git rev-parse main origin/main` 两值相等」；把它推上去又产生一次新 run，其 id 又要记……**没有终点**。
      **终止规则，三步，照做不得增删**：
      · **第一推**：推 Phase 2 收尾 + Phase 3 的全部文档提交。**当场实测并抄进 plan**：
        `git rev-parse main origin/main` 两值相等（这一刻它是真的），以及该次 run 的 id 与 9 个 job 结论；
      · **第二推**：把上面那条记录本身（log + 本 plan 文件）提交并推出去。**这一推只记 run id 与 `conclusion` 一行，
        不再回写 9 个 job 的明细**——它跑的是与第一推逐字相同的 workflow，明细无新信息量。**计入机动预算。**
      · **终点判据（此后不再推、不再记）**：`git merge-base --is-ancestor origin/main main` 成立，
        且 `git rev-list --count origin/main..main` **≤ 1**，且那至多一个提交**只含** `docs/logs/**`
        与 `docs/plans/p0-foundation/**`。**闭幕判据用这一条，不用「两值相等」。**
        （与前驱 plan 收尾判据同形，两个 plan 的收敛口径因此一致。）
      - Skill: `none`

Exit Criteria:

- [ ] 「`main` 上没有这个 job / 仍是本机独证」一族陈述已按实测结论就地改准，且未被写成比证据更强的说法
- [ ] `docs/masterplan/` 下的命中（若有）走的是「STATE 追加」而非就地改
- [ ] `2026-08-21-2220-2` 只被追加，删除行数为 `0`
- [ ] `2026-08-22-0027-2` 的**四条**计数判据改动前后均为期望值：锚定 `[ ]` 为 `19`、
      `[ ]` 总计数与锚定 `[x]` 计数**前后两次实测相同**（起草日实测值：总 `[ ]` = `24`、锚定 `[x]` = `36`，
      **以执行当日实测为准，不写死**）、`Plan Status: deferred` 计数为 `1`
      （⚠️ 此前本框只写了锚定 `[ ]` 一条，比它对应的执行项弱——**打勾的是 gate**，弱写法能让代打勾溜过去）
- [ ] roadmap 有改准后的「9 现状」行，含与工作项 8 的包含关系，且**未自行置 `done`**
- [ ] 本机五条验证命令均 exit 0，红线自查五条输出均为期望值
- [ ] `docs/logs/2026/08-22.md`、`STATE.md` §2 与 §3 各有对应记录（STATE 只追加）
- [ ] 收尾推送已按写死的**三步终止规则**执行：推前守卫预检落在情形 ①（无输出）；
      **第一推**推后当场实测 `git rev-parse main origin/main` 两值相等并抄进 plan，
      该次 run 的 id 与 **9 个 job** 结论逐字入 plan；**第二推**只记 run id 与 `conclusion`
- [ ] **终点判据成立**：`git merge-base --is-ancestor origin/main main` 成立，
      `git rev-list --count origin/main..main` ≤ 1，且那至多一个提交只含 `docs/logs/**` 与 `docs/plans/p0-foundation/**`

#### Phase 3 执行记录（2026-08-22 实跑回填）

**一、那条 grep 命中的每一处，逐条裁定（10 行 / 4 个文件，与起草时实测一致）**

`grep -rn 'main.*上.*没有这个 job\|本机独证\|PR #1 仍未合并\|未合并\|红在实现' docs/context/ docs/backlog/ docs/architecture/`
→ **10 行 / 4 个文件**：`project-context.md:58,59` · `system-baseline.md:448,457,461,521` ·
`p0-foundation-roadmap.md:62,64,69` · `module-boundaries.md:305`。

| # | 命中位置 | 裁定 | 处置 |
|---|---|---|---|
| 1 | `docs/context/project-context.md:58` | **确认漂移**（「PR 未合并，`main` 上没有这个 job」「在 `main` 上仍是本机独证」） | **就地改准**：追加「四次补记」，写明落地 sha `3503f2c`、权威运行 `32572618933` 九个 job 全绿、`gates-l2-live` job `97030229667` 日志逐字；并写明 run `32509351108` 那次可复现的红是**永久证据、未被抹掉**，只是不再是当前状态 |
| 2 | `docs/context/project-context.md:59` | **确认漂移**（「PR #1 仍未合并，`main` 上仍没有这个 job……仍是本机独证」） | **就地改准**：整句改准为「此刻在 `main` 上由 CI 服务端复跑，不再是本机独证」，并保留两条照实读的限定（不在 `commands.test` 里、`GATE_VERIFY` 复跑不到；PR #1/#2 已 `CLOSED` 但历史 run 仍可查） |
| 3 | `docs/architecture/system-baseline.md:448` | **确认漂移**（「空窗期终点尚未到达（PR #1 未合并）」「空窗期此刻仍开着」） | **就地改准**：改成「该终点已于 2026-08-22 到达」+ 落地 sha + 权威运行 + 守卫 job id，并写明**闭合不等于守卫在 `push` 上已有牙齿** |
| 4 | `docs/architecture/system-baseline.md:457` | **确认漂移，且落地之前就已确认**（「原因：`gates-l2-live` 在 CI 上第一次跑就红，且原样复跑复现」——被 run `32533449466` 推翻） | **就地改准**：在「上线状态」段末追加「四次补记」整块，逐条改准；⚠️ **那条可复现的红（`32509351108`）逐字保留，不得抹掉** |
| 5 | `docs/architecture/system-baseline.md:461` | **确认漂移，与本次落地无关**（「红在实现，不是红在判据：`apply_pack` 的物理列清除面在 runner 的全新站点上不成立」——被 plan `2026-08-22-0228-2` 推翻：清除面从来没坏过，真红因在 `bench execute` 的 `if ret:`） | **就地改准**：同一块「四次补记」里单列一条，写明它是**独立的**确认漂移，不是本次落地的副产物 |
| 6 | `docs/architecture/system-baseline.md:521` | **确认漂移**（「收口方案……但它尚未在 `main` 上生效（PR #1 未合并）」） | **就地改准**：改成「已于 2026-08-22 在 `main` 上生效」+ 落地 sha + job id |
| 7 | `docs/architecture/module-boundaries.md:305` | **非漂移** | **不改，逐字记明理由**：该行是「**无活站点不等于错误**：无站点配置时走离线来源……让它抛异常，门禁就会永远红在环境而不是红在实现上」——它是一条**关于来源解析设计的正确架构原则**，命中只因为共用了「红在实现」这个词组，**与两个 job 在不在 `main` 上毫无关系**。改它会**改坏一条正确的原则**（第 3 轮评审 blocking ① 预判过这一点）。**记明命中位置与不改的理由，未静默略过、更未照改。** |
| 8 | `docs/backlog/p0-foundation-roadmap.md:62`（「5 现状」） | **确认漂移**（「PR #1 未合并，`main` 上仍没有这两个 job」） | **就地改准**：行内追加「四次补记」，并写明**本行状态不因此变动**（`done` 仍卡在划名单那条人裁定题上） |
| 9 | `docs/backlog/p0-foundation-roadmap.md:64`（「6 现状」） | **确认漂移**（同上）；另含一处**保留的历史陈述**「这是一个 CI 抓到、本机独证掩盖着的真问题」 | **就地改准**：同 #8；对那处历史陈述**指明其现时效力已由本行随后那条「三次补记，就地改准」接管，此处不重复改准** |
| 10 | `docs/backlog/p0-foundation-roadmap.md:69`（「9 现状」） | **确认漂移** | **由本 Phase 的专门 `Fix` 项处置**（见下面第四节） |

**没有一处被降级成 follow-up（Minimum Rule 14）；非漂移的那一处也没有被静默略过。**

**二、`docs/masterplan/` 只读边界（另跑一次，同一 pattern）**

`grep -rn '<同一 pattern>' docs/masterplan/` → **7 条**（与起草时实测一致）：
`STATE.md:50,54,112,113,115,127` 与 `archive/STATE-2026-08-22.md:177`。

- **一处都没有就地改**（红线 5）。处置走既有先例：**在 `STATE.md` §2 与 §3 各追加一条事实行**，
  改准的内容写在追加行里。
- `docs/masterplan/archive/STATE-2026-08-22.md:177` 是**冻结的历史记录**，
  **连追加都不做**——它是已归档的证据，改它等于伪造历史。
- 机械判据：`git diff --numstat <开工 sha>..HEAD -- docs/masterplan/STATE.md` → **删除列为 `0`**；
  `git diff … | grep '^-' | grep -v '^---'` → **无输出**（**只追加**）。

**三、`0027-2` 两项欠账的了结**

- **在 `2026-08-21-2220-2` 的 `## Deferred But Adjudicated` 下追加两行**（分别挂在
  「L2 门禁在 CI 上不受 `expected-red.txt` 棘轮保护」与「判定器没有「live 名单」这个概念」两条下方），
  **逐字点名两个 plan 的完整 id**（`2026-08-22-1206-1-verdict-guard-mutation-proof` 与
  `2026-08-22-1206-2-gates-l2-live-lands-on-main`，**不写「本批两个 plan」**）与 `main` 上的权威运行 `32572618933`。
  机械判据：`git diff --numstat` → **`2	0`**，**删除列为 `0`**（一个字未改写他人的关闭证据）✅
- **`0027-2` 的 `Closure Audit Log` 追加一行**，**只写本 plan 还的那一项**（Phase 3 的「把前驱两条 Deferred 记为了结」）；
  Phase 2 那项（守卫实证）由第一个 plan 自己追加过一行，**本 plan 只引用、不复述**。
  同时写明它自身的 `Plan Status` 与那 19 个未勾框**由人裁定**。
  机械判据：`git diff --numstat` → **`11	0`**（纯追加）。
- **四条计数判据，改动前后两次实测**（**以执行当日为准，未写死起草日的数**）：

| 判据 | 改动前 | 改动后 | 期望 | 结论 |
|---|---|---|---|---|
| `grep -c '^\s*-\s\[ \]' …0027-2….md`（锚定未勾） | `19` | `19` | `19` | ✅ |
| `grep -c '\[ \]' …0027-2….md`（未勾总计数） | `26` | `26` | 前后相同 | ✅（起草日是 `24`，本 plan 未写死它） |
| `grep -c '^\s*-\s\[x\]' …0027-2….md`（锚定已勾） | `36` | `36` | 前后相同 | ✅ |
| `grep -c '^> Plan Status: deferred' …0027-2….md` | `1` | `1` | `1` | ✅ |

⚠️ 追加时曾一度让「未勾总计数」由 `26` 变 `27`——原因是追加文本里写了一对字面方括号；
**当场按该判据收回改成「未勾框」三字**，这正是那条判据存在的理由（只钉锚定式的 `19` 看不见它）。

**四、roadmap「9 现状」行改准**

- 行内追加「四次补记」，写明：① 两个新 job 已在 `main` 上，落地 sha `3503f2c89d78f44f94e0e0ff9f6061ca72e90b89`，
  `main` 上 `gates.yml` 有 **9 个 job 键**、前 190 行逐字节未动；② **权威运行 `32572618933` 九个 job 的 id 与结论逐字**，
  `gates-l2-live` 日志逐字；③ 守卫**四条**变异实验的 run id 与结论，**含第四条「同一 sha 上不可复现」的限定**，
  以及 `push` 路径「只证明能跑通、不证明有牙齿」的收窄说法；
  ④ **事实陈述**：那格写死的关闭判据**此刻成立**；⑤ 与**工作项 8** 的包含关系：9 的判据完全包住 8 的判据，
  **但 9 绿不代表 8 可置 `done`**；⑥ **不自行把工作项 9 置 `done`**，并写明它除「划名单」外还有
  **第二条独立障碍**（没有属于自己的门禁测试）。
- ⚠️ **`## Work Item Status` 块一个字未动**：工作项 9 仍是 `planned`。
  该块逐字写着「状态只在这里改」，而 roadmap 的 `Status values` 表把 `done` 定义为
  「完成，且通过 closure 审计」——**置状态不是 plan 的事**（本 plan 的 Non-Goals 第一条）。
  该 roadmap **不使用 `❌ / ✅` 标记**，因此没有可翻转的标记；本 plan 改的是「9 现状」这一格的事实陈述。

**五、收尾复跑（本机，五条全部 exit 0）**

| # | 命令 | 退出码 | 输出 |
|---|---|---|---|
| 1 | `python3 tools/gates/check_expected_red.py` | **0** | `判定模式：default —— 按 tools/gates/expected-red.txt 判定` / `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` |
| 2 | `python3 -m pytest tests/unit -q` | **0** | `221 passed` |
| 3 | `python3 -m pytest tests/contracts -q` | **0** | `151 passed` |
| 4 | `ruff check agenerp tests/unit tests/contracts` | **0** | `All checks passed!` |
| 5 | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))"` | **0** | 无输出 |

⚠️ **验证范围照实说**：本仓无全量套件（无 build、无 typecheck）。本 plan 的证据面是
**「CI 上九个 job 的结论 + 本机这五条命令」**，**不得报成「全量验证通过」**。

**六、红线自查（锚开工 sha `79184e5`，不用裸 `git diff`）**

| # | 命令 | 输出 | 期望 | 结论 |
|---|---|---|---|---|
| 1 | `git diff --stat 79184e5..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` | **无输出** | 空 | ✅ 红线 1/3 与 `agenerp/**` 零触碰 |
| 2 | `git status --porcelain -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` | **无输出** | 空 | ✅ 工作区亦无未提交触碰 |
| 3 | `git diff --numstat 79184e5..HEAD -- tools/gates/expected-red.txt` | **无输出** | 空 | ✅ **账本一行未动** |
| 4 | `git diff 79184e5..HEAD -- docs/masterplan/STATE.md \| grep '^-' \| grep -v '^---'` | **无输出** | 空 | ✅ **只追加**（`--numstat` 为 `19	0`） |
| 5 | `git diff --numstat 79184e5..HEAD -- docs/plans/p0-foundation/2026-08-21-2220-2-homepage-ai-not-configured.md` | `2	0` | **删除列为 `0`** | ✅ 未改写他人关闭证据 |

**另记两条常设禁令的实测**：`git diff --numstat 79184e5..HEAD -- .github/workflows/gates.yml` → **`118	0`**
（纯追加、零删除）；**证据仓 `${XM_PATH}` 全程未写入**（本 plan 无任何写它的命令）。

## Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理，fresh session，2026-08-22）。
  七条 blocking 全部落地：
  ① **落地那一推在原设计下必然红** —— 本地 `main` 领先 `origin/main` 10 个提交，`57ad6d5` 改了判定器且无 trailer，
  守卫在 `push` 上取 `BASE=github.event.before=508c75b` → 必然 `exit 1`。**已改成分两次推**：
  第一个 plan 趁 `main` 上还没有守卫先把 `origin/main` 追平，本 plan 只推落地那一个提交；
  并新增「推之前本地把守卫谓词算一遍」的硬闸（三种情形的处置写死）。
  ② **`--ff-only` 在原设计下跑不动** —— `git merge-base --is-ancestor main <分支>` 实测**不成立**，
  且本仓 loop 每个 phase 都往 `main` 提一次，`main` 必然在中间前进。**已把「重刷分支 + 重取一次 PR 绿」
  写成本 plan Phase 2 的第一步**，并加「重刷到 ff-merge 之间 `main` 零新提交」的硬约束与机械判据。
  ③ **Baseline D2 是假陈述** —— 「合并会删掉 4 个 plan 文件」由两点式误读而来；
  `git merge-tree --write-tree` 实测合并只产生 `118 0 .github/workflows/gates.yml`，**删不掉任何东西**。已整条重写，
  并把真实理由换成 ff-only 的祖先要求与「PR 那次绿跑的是另一份判定器」。
  ④ Baseline A 的 `git status` 实测是 2 行不是 0；本地/远程 `main` 全文分开表述。
  ⑤ 红线 2 自查 (e)「没有 `|| true` 兜底」被实测推翻（守卫体内就有一处），已收窄成「`exit 1` 路径没被吞掉」，
  假阴入口登记为 Deferred。
  ⑥ 守卫结论由「断言」改成「Phase 1 预检算定 + Phase 2 核对」的三态矩阵。
  ⑦ 回滚从 Infra 条目提升为 Phase 1 的 `Decision`，**明确 revert 只有人能选**，
  并记入实测事实 `gh api …/branches/main/protection` → 403（`main` 无保护，不存在「红了推不动」的死锁）。
  nit 也已落地：Goal 4 的「三处」改成 grep 实测的 8 行并点名 `system-baseline.md:457` 是**今天就已确认**的漂移；
  `0027-2` 的 `[ ]` 判据补上总计数 `24` 与 `Plan Status` 两条、路径写全；
  `0027-2` 的 `Closure Audit Log` 追加内容收窄到只写本 plan 还的那一项；
  `mergeCommit == 落地 sha` 放宽为 `state: MERGED` + `git merge-base --is-ancestor` 不变式；
  NB2 的计数锚点写明。
- **Independent draft review iteration 2: `needs revision`**（另一个独立子代理，fresh session，2026-08-22）。
  它复核确认 round-1 七条 blocking **全部实质落地**、且**没能证伪任何一条重写后的技术论断**
  （逐条实跑过：`merge-tree` 只产生 118 行、`is-ancestor` 退出 1、守卫 `BASE`/`HEAD` 与本地预检式逐字对应、
  红线 2 五条自查、`0027-2` 的 `19` / `24` / `deferred` 三个锚、403 报文原文、Goal 4 那 8 行 grep、
  以及回滚 `Decision` 与停机纪律**不矛盾**）。但抓出 7 条 blocking，均为修订留下的陈旧计数与缺失步骤：
  ① `Closure Gates` 仍写「三处 owner-doc 改准」，而 Goal 4 已改成「grep 命中的每一处（8 行）」——
  **打勾的是 gate**，照旧写法改 3 行也能如实打勾，等于用 gate 本身绕开 Minimum Rule 14。已改准。
  ② `Closure Gates` 仍写「无失败吞噬」，正是 round-1 已推翻的说法（守卫体内就有一处 `|| true`）。已收窄。
  ③ 「三条实验」与「四条实验」在同一文件里打架，且**前置核对 ① 是本 plan 对前驱的 go/no-go 闸**——
  照旧写法拿 3 条就能放行，而缺的第 4 条恰是「人将来还能不能合法改判定器」那条出口。已全部改成四条并点名。
  ④ Phase 1 写「前置五条」却列了六条，Exit Criteria 也钉在「五条」，
  而第 6 条（`origin/main == main`）正是 round-1 新加的、最承重的那条。已改成六条。
  ⑤ Phase 1 的守卫预测预检（自称「硬闸」）与回滚 `Decision` **在 Exit Criteria 里没有任何一条对应**；
  且 Exit Criteria 要求落地方式 `Decision` 有「残余风险」而它原本没写。两者都已补。
  ⑥ **没有任何一步把 `main` 推回 `origin`**，而 `Closure Gates` 却断言「落地后同样相等」——
  Phase 2 收尾与 Phase 3 全部文档提交都只在本地。已在 Phase 3 补一条收尾推送项，
  且**因为守卫此刻已活在 `main` 上，推之前必须重跑守卫预测预检**。
  ⑦ 「预算里已计这一次」指向一份本 plan 根本没有的预算。已按前驱格式补上**上限 6 次**的预算块与超出即停。
  nit 也已落地：Phase 1 预检的操作数改成当时真实存在的 ref 并写明「有约束力的是 Phase 2 那次重算」；
  `docs/masterplan/` 只读那条从「grep 的结论」（作用域根本不含它，永远不会触发）改成一条**另跑一次**的常设检查；
  Phase 3 的 grep 加上 `红在实现` 并把作用域放宽到三个目录（`system-baseline.md` 里那句
  「红在实现，不是红在判据」**今天就已是确认漂移**，旧 pattern 匹配不到它——挑 pattern 挡掉确认漂移就是绕行）；
  重刷后补一条净 diff 判据并要求当场记下 `git rev-parse main`；`[ ]` 总数不再写死 `24` 而是「记实测值、前后相同」
  并补一条 `[x]` 计数（只钉未勾数挡不住「新增一条已勾行」）；`mergeCommit`、`Source` 的逐字框定、
  「本批两个 plan」的指代歧义、以及「Phase 2 自己的收尾提交也必须排在 ff-merge 之后」这条真正的威胁。
- **Independent draft review iteration 3: `needs revision`**（第三个独立子代理，fresh session，2026-08-22）。
  它把 `Current Baseline` **A / A3 / B / C / D1 / D2 / E / F / Infra** 逐条重跑，**零 mismatch**
  （含 `merge-tree --write-tree` 只产生 `118 0 gates.yml`、`is-ancestor` 退 1、403 报文逐字、
  roadmap 工作项 9 的关闭判据引用**逐字准确**、`0027-2` 的 `19` 锚、`|| true` 恰好两处、
  守卫 BASE/HEAD 推导与 plan 描述一致），并确认无一步触碰红线 1/2/3/5，未代翻 `0027-2` 的 `Plan Status`。
  2 条 blocking 与 10 条 nit 全部落地：
  ① **Goal 4 与 Phase 3 对 `module-boundaries.md:305` 的处置直接冲突**：Goal 4 要「命中的每一处就地改准……
  它们都是确认漂移」，Phase 3 要「逐条裁定，非漂移的记明理由不改」。照 Goal 4 执行会**改坏一条正确的架构原则**
  （该行讲的是「无活站点不等于错误……红在环境而不是红在实现」）。已把 Goal 4 的义务形状整条重写成「逐条裁定」，
  并把 `8 行/3 文件 → 10 行/4 文件` 的算术解释清楚（补 `红在实现` 这个词同时捞进了 `:461` 这条真漂移与 `:305` 这条非漂移）。
  ② **收尾「记录 → 推送 → 再记录」无穷回归**：记 run id 本身是一次 `main` 提交，当场打破同一条判据里的
  「两值相等」；推上去又生成新 run，其 id 又要记。已写死**三步终止规则**（第一推记全量、第二推只记 run id 与
  conclusion、终点判据改为 `is-ancestor` + `rev-list --count ≤ 1` + 只含文档路径），
  并把 `Closure Gates` 里那条「开工前相等、落地后同样」一并改准、预算补上漏算的第二推。
  nit 逐条：判据「三条」实列四条已改准；Phase 3 Exit Criterion 从只钉锚定 `[ ]` 补到四条计数
  （起草日实测 总 `[ ]`=24 / 锚定 `[x]`=36，写明以执行当日为准）；`archive/STATE-2026-08-22.md:177`
  从第一项的 grep 例子挪到第二项（第一项作用域根本够不着它）；Goal 4 的 8→10 算术说明；
  Phase 1 守卫预检补上 `pull_request` 那一路的预测出口并写明与 `push` 路那一路同解的**推导理由**；
  预检前补 `git fetch origin main`；两个 grep 统一成同一 pattern；Phase 2 Targets 改掉「在 `main` 上编辑」的暗示；
  `scoped verification` 补上「不得报成全量验证通过」的逐字说法；
  「工作项 9 卡在名单」那条 Deferred 补上 roadmap 给的**第二条独立理由**（它没有属于自己的门禁测试）。
- **姊妹 plan 第 4 轮评审的回灌（同日，结构性）**：前驱 `2026-08-22-1206-1` 的第 4 轮独立评审证伪了
  「`pull_request` 的 `BASE` 取 base 分支 tip」这条**两个 plan 共用的中心事实**——它在 **PR 创建时钉死**
  （实测 `baseRefOid` → `7b0f585`）。本 plan 因此同步改动四处：
  Baseline D 新增第 ③ 条限定；前置核对 ②③ 改锚 `$CUT` 与前驱新建的 PR、新增 ⑦（`baseRefOid == $CUT`）与 ⑧（PR #1 原封未动）、
  ⑥ 改成两条收敛判据以解开与前驱的**跨 plan 死锁**；落地方式 `Decision` 整条重写（落地对象是前驱新建的分支与 PR，
  不是 PR #1），并加硬约束「每重刷一次分支就开一个新 PR，使 `baseRefOid == 重刷时的 `main` sha`」；
  新增一条 `Decision` 处置 PR #1 的终局（关闭 + 留证，不删远程分支，带四个备选与残余风险）。
- **Independent draft review iteration 4: `needs revision` → 已就地改准，可执行**（第四个独立评审代理，fresh session，2026-08-22）。
  它把 `Current Baseline` A / B / C / D / E / F 与 Infra 逐条重跑，**未证伪任何一条技术论断**：
  `git merge-tree --write-tree main origin/ci/0027-2-l2-full-live-gate` 得到的树对 `main` 做 `git diff --numstat`
  → **只有一行** `118	0	.github/workflows/gates.yml`；`git merge-base --is-ancestor main origin/ci/0027-2-l2-full-live-gate`
  → 退出码 `1`，merge-base 停在 `77addbb`；分支上 `gates.yml` 共 **308** 行，**前 190 行与 `main` 逐字节相同**（`diff` 无输出），
  `tail -n 118` 的 job 键恰为 `gates-l2-live:` / `verdict-tool-untouched:`；`main` 上 7 个 job 键、
  `grep -cE 'gates-l2-live|verdict-tool-untouched'` → `0`；Goal 4 那条 grep 在三个目录上 **10 行 / 4 个文件**，
  行号 `system-baseline.md:448,457,461,521` · `project-context.md:58,59` · `p0-foundation-roadmap.md:62,64,69` ·
  `module-boundaries.md:305` **与 plan 逐字一致**；同一 pattern 在 `docs/masterplan/` 上 **7 条**；
  `0027-2` 的四个计数 **19 / 24 / 36 / 1** 全中；`2026-08-21-2220-2` 里 `2026-08-22-1206` 命中 **0**（欠账确实还欠着）；
  `gh pr list --state all` → 只有 PR #1，`OPEN` / `baseRefOid=7b0f585` / `headRefOid=c2c688b` / `6 / 417 / 17`；
  `gh api …/branches/main/protection` → `403`，报文逐字与 plan 一致。
  抓出 **2 条 blocking + 4 条 major**，全部就地改准：
  ① **blocking：Phase 2 那组「`baseRefOid == $RECUT` + 读数 `1 / 118 / 0`」判据在本 plan 自己的节奏下不可满足。**
  `baseRefOid` 钉的是**建 PR 那一刻 `origin/main` 的 tip**（前驱 C5 的实测正是这个含义：PR #1 的 `baseRefOid` = `7b0f585`
  = 建 PR 时 `origin/main` 的值），而 Phase 1 的日志/plan 提交按本 plan 自己的说法「只落在本地 `main` 上」
  （旧 Phase 1 预检里那句「让 `main` 再次领先——这是无害的」）。于是建 PR 时 `origin/main` ≠ 本地 `main` = `$RECUT`，
  两条判据**必然为假**，且 PR 读数会把 Phase 1 的文档提交一并算进去——**与本 plan 自己诊断「不能沿用旧 PR」的失败模式一模一样**。
  已补 **Phase 2 第 0 步：先 `git push origin main` 并实测两值相等，再取 `$RECUT` 切分支建 PR**；
  「这是无害的」那句改准；预算从 **6 次改为 7 次**。
  ② **blocking：`git switch -C ci/1206-1-verdict-guard-proof main` 会 force-push 覆盖前驱的证据分支。**
  前驱 Phase 4 的关闭判据里有 `git rev-parse ci/1206-1-verdict-guard-proof` → 等于它 Phase 2 结束时那个 sha，
  且它的四条实验证据与新 PR 都挂在那条分支上；本 plan 一旦 `-C` 重写它，前驱一条**已关闭的证据判据当场变假**。
  已改成**另起新分支 `ci/1206-2-l2-live-land`（`switch -c`，普通 push，无 force）**，**前驱分支与 PR 一个字节不碰**；
  前驱 PR 的终局因此从「待观察」变成**确定的**——它不参与 ff-merge，由本 plan 一并 `gh pr close` 并留证，
  旧写法里「同一条分支名，GitHub 自动关闭行为本仓未实测过，不强求某个值」那段不确定性随之消失。
  ③ **major：`Current Baseline` 陈旧**（锚在 `main` @ `aba9a5f`、本地领先 10 个提交），而评审当日 `main` 已是 `4d7b311`
  且 `origin/main` 已追平——违反 Minimum Rule 1。已刷新，并实测记明 `gates.yml` 在 `aba9a5f..4d7b311` 之间**逐字节未变**，
  B / C / D / F 各条结论不受影响。
  ④ **major：Phase 2 红线 2 自查 (a)(d) 锚死 `aba9a5f`**，与前驱第 5 轮「锚点一律改成开工 sha」不同口径。已改锚 `$RECUT`。
  ⑤ **major：`/tmp/two-jobs.yml` 是跨 plan、跨会话的临时文件，本 plan 没有给再生路径**——`/tmp` 被清一次，
  Phase 2 第一步那条逐字比对判据就跑不了。已写明再生命令
  （`git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml | tail -n 118 > /tmp/two-jobs.yml`）、
  再生后的自检，以及「两条路等价（同一个远程 ref 的同一段字节）」的理由。
  ⑥ **major：Phase 1 的「PR 终局处置 `Decision`」在 Phase 1 的 Exit Criteria 里没有任何一框对应**——
  正是第 2 轮 blocking ⑤ 抓过的同一种毛病（`Decision` 没有 gate 就没有约束力）。已补一框。
  另有一处措辞改准：落地方式 `Decision` 的残余风险原写「PR #1 若在重刷与 ff-merge 之间被别的东西推进」，
  主语应是 `main` 而不是 PR #1（PR #1 全程不动）。
- **评审结论：无剩余 Blocker，`Plan Status` 由 `draft` 置 `active`。**
  尚存 Minor 交由执行期与独立关闭审计承接：Phase 3 的 `Targets` 列了 roadmap「5 现状」「6 现状」两行，
  而执行项里只有「9 现状」有专门的 `Fix`——那两行（`p0-foundation-roadmap.md:62,64`）落在 Goal 4 那条 grep 的
  「逐条裁定」义务里，覆盖面不缺，只是入口不在同一项上。

## Closure Gates

- [ ] in-scope behavior is complete（两个 job 在 `main` 上 + 权威运行绿 + **Phase 3 那条 grep 命中的每一处已逐条裁定并处置** + `0027-2` 欠账还清）
- [ ] relevant docs are aligned（roadmap「5/6/9 现状」· `project-context.md` · `system-baseline.md` §14.4 ·
      `2026-08-21-2220-2`（追加）· `2026-08-22-0027-2`（追加）· log · STATE §2/§3）
- [ ] verification has run：`main` push 权威运行的 run id 与九个 job 结论逐字 · 本机五条命令 exit 0
- [ ] 红线 2 自查五条（前缀性 / job 键集合 / 禁用词零命中 / 触发范围 / **判定与守卫的 `exit 1` 路径未被吞掉**——`|| true` 假阴入口已登记为 Deferred，**不得写成「零吞噬」**）有实测输出
- [ ] **确认的 owner-doc 漂移已就地改准，没有被降级成 follow-up**（Minimum Rule 14）
- [ ] **已关闭 plan 的证据段一个字未改**：`2026-08-21-2220-2` 的删除行数为 `0`
- [ ] **`2026-08-22-0027-2` 未被代关闭**：`Plan Status` 仍 `deferred`，锚定 `[ ]` 计数仍 `19`，
      `[ ]` 总计数与 `[x]` 计数**落地前后两次实测相同**（值以实测为准，**不写死数字**——理由见 Phase 3 那一项）
- [ ] **落地那一推的守卫预测是「推之前算出来的」**，不是事后解释；实测出口与预测一致
- [ ] **`origin/main` 与本地 `main` 的区分已贯彻**：开工前按 Phase 1 前置核对 ⑥ 的**两条收敛判据**有实测输出；
      收尾按 Phase 3 的**三步终止规则**执行并满足终点判据
      （⚠️ **不写成「开工前两者相等、落地后同样」**——那个形式在本仓的 loop 节奏下**不可满足**，
      理由见 Phase 1 前置核对 ⑥ 与 Phase 3 收尾项，第 3 轮评审改准）
- [ ] CI 结论已按「停机纪律」归类，**「首轮红、复跑绿」未被写成「CI 已验证」**
- [ ] 守卫 `push` 路径的结论**未被写成「守卫在 push 上已有牙齿」**
- [ ] `tools/gates/expected-red.txt` 一行未动；工作项 9 **未被 plan 自行置 `done`**
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件，本 plan 的证据面是
      「CI 上九个 job 的结论 + 本机五条命令」，**不得报成「全量验证通过」**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### 守卫 `verdict-tool-untouched` 在 `push` 事件上没有正向变异实证

- Classification: `watch-only residual`
- Why Not Blocking Closure: 正向实验要在 `main` 上故意推一个改判定器且不带 trailer 的提交，
  代价是让 `main` 红一次并留在历史里。`push` 路径的**连通性**已由本 plan 的权威运行实测（走到「未触及」分支并 `exit 0`），
  `pull_request` 路径的**牙齿**已由第一个 plan 的**四条**实验实测；两者合起来是可负担的最大覆盖面。
- Successor Required: `no` —— 重开事件：**下一次有人合法改判定器时**（提交信息带 `Gates-Change-Approved-By:`），
  那次 `main` push 运行天然会走到守卫的「触及 + 找到 trailer 放行」分支，届时把结论补记进 §14.4 即可。

### 守卫脚本用 `|| true` 吞掉 `git diff` 的错误，存在假阴入口

- Classification: `watch-only residual`
- Why Not Blocking Closure: 实测 `grep -n '|| true' .github/workflows/gates.yml` 两处命中，
  一处在新守卫体内、一处在既有 `gates-untouched` 里，**同款写法、继承而来，非本批引入**。
  `git diff` 出错时 `CHANGED` 为空 → 走 `✅ 未触及判定器` 并 `exit 0`，是真实的假阴入口。
  修它要改既有 job 的脚本体，会打掉本仓已固化的「行前缀」自查判据，且改既有 job 需人批。
- Successor Required: `no` —— 重开事件：**人裁定统一修这两处**，或**守卫出现一次已知的假阴**
  （表现为判定器被改了而守卫仍绿）。

### `gates-l2` 与 `gates-l2-live` 覆盖面重复，前者未退休

- Classification: `out-of-scope improvement`（**人动作项**，0027-2 已登记，本 plan 继续挂着）
- Why Not Blocking Closure: 退休 `gates-l2` 是**删除**动作，方向是变松；且会打掉「新文件以旧文件为行前缀」
  这条本仓已固化的红线 2 机械判据，此后每一轮动 `gates.yml` 都要重新论证一遍。冗余的代价只是多一次 runner 时间。
- Successor Required: `no` —— 重开事件：**人裁定退休它**，或 CI 时长成为实际瓶颈。

### `ai-autonomy-policy.md` 的 `.github/workflows/** = blocked` 与红线 2「只禁变松」措辞不一致

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: 见 Phase 1 的授权面 `Decision`——沿用 `2026-08-21-2220-2` 已在 `main` 落地的先例。
  **残余风险照实记**：若人事后裁定严格 `blocked`，本次落地需要一次追认。
- Successor Required: `no`（改 Protected Areas 的 Rule 列等于替人定授权口径，loop 不做）——
  重开事件：**人给出裁定**，或**下一个要动 `main` 上 `.github/workflows/**` 的 plan 开工前**（必须重新摆上台面，不得默认继承）。

### 工作项 4/5/6/7/8/9 仍卡在「从预期红名单划掉」这条 `done` 定义上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是一个**已登记的人裁定题**（`docs/backlog/needs-human-expected-red-handoff.md`），
  根因是「默认判定环境没有 `AGENERP_LIVE`，L2 在那里恒红」，而人已裁定「名单必须反映判定器实际看到的」（STATE §2 11:20Z）。
  本 plan 交付的是工作项 9 的**关闭判据本身**（CI 上判 19 条并 `success`），与名单是两件事。
  ⚠️ **对工作项 9 而言这还不是唯一障碍（第 3 轮评审补）**：roadmap 行 `| 9 |` 另给了一条独立理由——
  它**没有属于自己的门禁测试**，`done` 的字面定义对它「在字面上不可满足」，与工作项 4 同一情形。
  **只写名单那一条，会让工作项 9 看起来离 `done` 只差一步。**
- Successor Required: `no` —— 重开事件：**人从那份 handoff 文档的候选处置里选定一个**。

## Closure

Status Note: <待关闭时填写>

Closure Audit Evidence:

- Auditor / Agent: <independent auditor or independent subagent>
- Evidence: <task id / log link / walkthrough record>
