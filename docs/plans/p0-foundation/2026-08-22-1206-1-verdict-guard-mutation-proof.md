# 2026-08-22-1206-1 守卫 `verdict-tool-untouched` 的变异实证，与两个 job 在 **main 基线**上重跑绿

> Plan Status: active
> Mission: p0-foundation
> Work Item: 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）—— 承接 plan `2026-08-22-0027-2` 欠的**守卫实证**那一项
> Last Reviewed: 2026-08-22
> Execution Order: **1 / 2**（本批第一个；第二个是 `2026-08-22-1206-2-gates-l2-live-lands-on-main.md`，硬依赖本 plan 的四条实验证据）
> Source: plan [`2026-08-22-0027-2`](./2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md) 的
>   `> Reopen When:` 逐字：「successor plan 修好 `agenerp` 侧那条清除面（……）之后，**从 Phase 2 的「守卫 job 的变异实证」那一项续跑**」——
>   该重开条件已由 plan [`2026-08-22-0228-2`](./2026-08-22-0228-2-orphan-column-clearance-fresh-site.md) 逐字满足，
>   证据是 `docs/masterplan/STATE.md` §3 的 2026-08-22 `[resolved]` 行（run `32533449466`，`gates-l2-live` job `96929876654` `success`）。
> Related: `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（`deferred`，两个 job 的作者；本 plan **不改它的 `Plan Status`**，只在其 `Closure Audit Log` 追加事实行）·
>   `2026-08-22-0027-1-live-mode-gate-verdict.md`（判定器 live 模式与判定器守卫的提出者）·
>   `2026-08-22-0228-1-gate-verdict-failure-forensics.md`（判定器取证面；它使 `main` 的判定器与 PR #1 head 上的判定器**不再是同一份**，见 Current Baseline C4）
> Audit: required

## Current Baseline

⚠️ **本节在独立评审第 5 轮整体重测过一次：起草时的基线 `main` @ `aba9a5f` 已经过期。**
以下每一条都是 **2026-08-22 独立评审第 5 轮在 `main` @ `4d7b311` 上实跑得出的**，不是从旧 plan 抄的。
被改准的是 **A / A3 / C5.4** 与它们下游的判据锚点；**C1–C5.3 / D / E / F / G / G2 逐条复测仍为真**
（复测读数见 `## Draft Review Record` 的 iteration 5）。

**A. 仓库状态**

- `git log --oneline -1` → `4d7b311 fix(ops): plist 不再注入预算变量 —— 单一真相源留了个注入口就不单一`
- `git status --porcelain` → **空**（工作区干净）。⚠️ 起草时这里是两行 `??`（本批两个 draft plan 未跟踪）；
  它们已随 `6288666` 进入版本库，因此现在为空。
- **A3 · ⚠️ 起草时那条「本地 `main` 领先 `origin/main` 10 个提交，未推」已经不成立，本轮就地改准**：
  实测 `git rev-parse main origin/main` → **两值相等**，均为
  `4d7b311d0dd8e1e0da2d8a47329984d6d484eef4`；`git log --oneline origin/main..main | wc -l` → `0`。
  那 10 个提交（含 `57ad6d5 feat(gates): 门禁判定失败取证`）**已经推上去了**，其后 `main` 上又落了两个提交
  （`6288666` 预算阈值单一真相源 · `4d7b311` plist 不再注入预算变量），且都已推。
  **后果逐条说清，因为它改的是 Phase 1 的动作而不只是措辞**：
  · ① **Phase 1 第二个 `Decision` 要做的那一推已被现实满足**——`git push origin main` 现在是 no-op。
    它的**安全窗口论证仍必须留痕**（`main` 上此刻仍零 `verdict-tool-untouched`，见 B），
    但那一推不再消耗 CI 预算，也不再是「趁现在」的抢跑；该 `Decision` 因此降级为**核验 + 留痕**，见 Phase 1。
  · ② `$CUT`（切分支那一刻的 `main` sha）的期望值从 `aba9a5f…` 改为 **`4d7b311…`**，
    全 plan 所有以它为锚的判据同步改准。
  · ③ **Phase 4 红线自查原来写死的 `aba9a5f..HEAD` 锚点会误报，这是本轮抓到的唯一一条会直接卡住执行的硬伤**：
    实测 `git diff --stat aba9a5f..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates`
    → **非空**（`tools/gates/budget.json` +10 / `tools/gates/check_budget.py` +21 −1，来自 `6288666`）。
    那两个文件与本 plan 无关，锚点已全部改成 `$CUT`（= 开工那一刻的 `main` sha）。
  · ④ 起草时写的「GitHub 拿的基是 `origin/main` @ `508c75b`」本来就是错的（C5 已实测推翻），此处不再重复。

**B. `main` 上没有这两个 job（工作项 9 的关闭判据在 `main` 上不成立）**

- `git show main:.github/workflows/gates.yml | sed -n '/^jobs:/,$p' | grep -E '^  [a-z0-9-]+:'` → **7 个** job 键：
  `gates-untouched` / `expected-red-ratchet` / `gates-l1` / `masterplan-links` / `roadmap-parseable` / `loop-wiring` / `gates-l2`
- 同一文件 `grep -cE 'gates-l2-live|verdict-tool-untouched'` → `0`（退出码 1，零命中）
- 即：roadmap「工作项 9」那格逐字写的关闭判据（「`gates.yml` 上存在一个 job，在 live 判定环境下用
  `tools/gates/check_expected_red.py` 对 `tests/gates` **全部 19 条**判定并 `success`」）**此刻在 `main` 上不成立**。

**C. PR #1 与它的分支：真实状态（⚠️ 本节在独立评审中被推翻过一次，现按 merge-base 重写）**

- `gh pr view 1 --json number,state,headRefName,baseRefName,mergeable` → `{"baseRefName":"main","headRefName":"ci/0027-2-l2-full-live-gate","mergeable":"MERGEABLE","number":1,"state":"OPEN"}`
- **C1 · 合并 PR #1 不会删掉任何东西。** 判据是 merge-base，不是 tip-to-tip：
  `git merge-base main origin/ci/0027-2-l2-full-live-gate` → `77addbb`；
  `git diff --numstat 77addbb origin/ci/0027-2-l2-full-live-gate` → **三行**
  `118 0 .github/workflows/gates.yml` / `32 0 agenerp/oob.py` / `8 1 agenerp/snapshot.py`；
  `git log --oneline main..origin/ci/…` → **两个提交**（`c2c688b` / `9a8832f`），**都不删任何文件**。
  且 `agenerp/oob.py` 与 `agenerp/snapshot.py` 的内容**已经在 `main` 上**（`578eb8f` 那次 cherry-pick），
  `git diff --numstat main origin/ci/… -- agenerp/` → **零输出**。
  **结论：今天合并 PR #1，落到 `main` 上的净效果就是那 118 行 `gates.yml`，别的一个字节都不动。**
- **C2 · 一处必须记下来的读数陷阱（本 plan 起草时踩过）**：`git diff --stat main origin/ci/…` → `23 个文件，+384 / −3455`，
  看起来像「合并会回退 3455 行」——**那是 tip-to-tip 两点式，不是合并会应用的差集**。合并应用的是
  merge-base→分支，即上面那三行。同理 `gh pr view 1 --json changedFiles,additions,deletions` → `6 / 417 / 17`
  也不是本地口径。⚠️ **本句此前写的「GitHub 拿的基是 `origin/main` @ `508c75b`（见 A3），比本地 merge-base 旧」
  两处都错，已改准**：GitHub 拿的基是 **PR 创建时钉住的 `7b0f585`**，既不是 `origin/main` 也不是本地 merge-base；
  而 `508c75b` 比本地 merge-base `77addbb` **新**，不是旧（`77addbb` 出现在 `git log 7b0f585..508c75b` 里）。
  机械对照：`git diff --numstat 7b0f585 origin/ci/…` 汇总 → `files=6 +417 -17`，与 GitHub 读数**逐字相符**；
  `git diff --numstat $(git merge-base 508c75b origin/ci/…) origin/ci/…` → `files=3 +158 -1`，**对不上**。
  这条错误的完整后果见 **C5**——它不是一处措辞瑕疵，它推翻了本 plan 原来的整个实验载体设计。
  **本 plan 此后一律用 merge-base 形式写 diff 判据**，两点式 `git diff main <分支>` / `git diff main..<分支>` 一处不留
  （`git log` 的 `A..B` 区间形式不在此列——对 `git log` 而言 `main..分支` 与 `merge-base..分支` 本就等价）——它还有第二个毛病：
  `main` 一往前走（本 plan Phase 4 就会推 `main`），两点式的输出立刻变样，判据会因为与分支无关的原因失败。
- **C3 · 分支确实落后 `main`（第 5 轮实测 `git log --oneline origin/ci/0027-2-l2-full-live-gate..main | wc -l` → `21`；
  起草时是 `10`，`main` 此后又前进了），但「落后」的后果不是「合并会删东西」，而是「分支上的 CI 跑的不是 `main` 的代码」**——
  这条真实后果见 C4，也是本 plan Phase 1 存在的唯一理由。
- **C4 · 上一次绿证据的基线已过期（本 plan 存在的真正理由）**：run `32533449466`
  （`gates-l2-live` job `96929876654` `success`）跑在分支 head `c2c688b` 上，而
  `git diff --numstat main origin/ci/… -- tools/gates/check_expected_red.py` → `7	42` ——
  **判定器本身在 `main` 上已被 plan `2026-08-22-0228-1`（提交 `57ad6d5`，取证面）改过，那次绿没有覆盖当前这份判定器**。
  `agenerp/**`、`tests/gates/**`、`docker-compose.yml` 三处两边**逐字节相同**（`git diff --numstat` 对这些路径零输出），
  所以过期的只有判定器这一处——**但它恰好是 `gates-l2-live` 唯一执行的那条命令**。
  分支上再跑一百次 CI，跑的也不是 `main` 上那份判定器。

- **C5 · ⚠️ `pull_request` 的 `BASE` 不跟随 base 分支 tip，它在 PR 创建时就被钉死（独立评审第 4 轮实测推翻本 plan 原设计）**：
  本 plan 此前（以及 iteration 2/3 的评审结论）都写着「`pull_request` 事件的 `BASE` 取的是 base 分支的 tip（即 `origin/main`）」。
  **这句话是错的**，四条读数一致否掉它：
  · `gh pr view 1 --json baseRefOid` → `7b0f585f7c8082a64902da65e6e3314cb239dc9f`；
  · `gh api repos/:owner/:repo/pulls/1 --jq .base.sha` → 同一个 `7b0f585`，而彼时 `origin/main` 已是 `508c75b`；
  · `gh api repos/:owner/:repo/actions/runs/32533449466 --jq '[.pull_requests[].base.sha]'` → `["7b0f585…"]`——
    那次 `synchronize` 发生在 `origin/main` 移到 `508c75b` **之后 37 分钟**，`base.sha` **仍是** `7b0f585`；
  · 本仓自己的 `docs/masterplan/STATE.md:81` 早就记着 `gh pr view 1 --json state,baseRefOid` → `OPEN` / `7b0f585f7c…`，
    **本 plan 起草时没读它**。
  `7b0f585` 是 PR 创建时（2026-08-21T17:40:08Z）`main` 的 tip，实测 `git merge-base --is-ancestor 7b0f585 main` → 成立、
  `git merge-base --is-ancestor 7b0f585 origin/ci/…` → 成立。
- **C5.1 · 这条事实如何击穿原设计（必须写清，否则下一轮又会绕回去）**：守卫在 PR 上取 `BASE=github.event.pull_request.base.sha`，
  即 `7b0f585`，并跑**两点式** `git diff --name-only "$BASE" "$HEAD"`。原设计要把**同一个分支** force-push 成 `main`(`aba9a5f`) + 118 行追加，
  于是守卫会算：
  · `git diff --name-only 7b0f585 aba9a5f -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs` → **命中该文件**
    （`57ad6d5` 那次取证面改动落在这个区间里）；
  · `git log --format=%B 7b0f585..aba9a5f | grep -c '^Gates-Change-Approved-By:'` → `0`。
  → **守卫在刷新后的每一次运行上都 `failure`，与是否施加实验载荷无关**。后果逐条：Phase 2 的基线绿（含
  `verdict-tool-untouched` 日志逐字 `✅ 未触及判定器`）**拿不到**；实验 ② ③ 期望的 `success` **拿不到**；
  实验 ① 失去全部鉴别力（加不加那个空行它都红）。**「先推 `origin/main` 再刷新分支」消灭不了这一条**——
  `base.sha` 根本不看 `origin/main`。iteration 2/3 把那条时序约束称作「最硬的一条」「最有价值的一条」，
  **在这条实测面前它对 `pull_request` 路径是无效的**（它对 `push` 路径仍然有效，见 Phase 1 `Decision` 2 改准后的理由）。
- **C5.2 · 顺带纠正的第二个后果（原「硬判据」会必然失败）**：GitHub 的 PR 读数以 `base.sha` 为基。
  刷新后 `git diff --numstat 7b0f585 aba9a5f` → `files=24 +3752 -281`，加上 gates.yml 那一处后 PR 会读出约
  `25 / +3870 / −281`，**而不是**原 plan 钉死的 `1 / 118 / 0`。姊妹 plan 的 Phase 1 预检 ③ 拿的正是这个值当硬闸，
  两个 plan 会在同一处一起卡死。
- **C5.3 · 已有那次绿证据对本条**不构成**反证，照实记**：run `32533449466` 的守卫绿，是因为
  `git diff --name-only 7b0f585 c2c688b -- …` 与 `git diff --name-only 508c75b c2c688b -- …` **两者都为空**——
  它对「`BASE` 到底是哪一个」**不作鉴别**。本条结论靠的是上面 C5 那四条直接读数，不是靠它。
- **C5.4 · 因此本 plan 换实验载体：不 force-push PR #1，另开一条新分支与一个新 PR。**
  新 PR 的 `base.sha` 在创建那一刻等于当时的 `origin/main`，因此只要**建 PR 那一刻 `origin/main == main`**，
  就有 `BASE = $CUT`，四条实验各自回到它们本来要证明的那条出口。
  ⚠️ **第 5 轮改准**：这个前提**此刻已经成立**（A3：两值相等，均为 `4d7b311`），
  不再需要原文那句「先把 `origin/main` 推到 `aba9a5f`」的抢跑；
  但**建 PR 前必须现场重新核验一次两值相等**——Phase 4 会推 `main`，执行若跨过那一步再复跑，前提会重新变得不平凡。
  做法与备选见 Phase 1 第一个 `Decision`。
  **额外的好处照实记**：`base.sha` 一旦钉死就不再漂移，Phase 4 往 `main` 推文档**不会**动摇实验区间——
  原设计里那种「`main` 一动判据就变样」的脆弱性在新载体上消失。

**D. `gates.yml` 的前缀关系（红线 2 自查的机械判据，已成立）**

- `diff <(git show main:.github/workflows/gates.yml) <(git show origin/ci/…:.github/workflows/gates.yml | head -n 190)` → **无输出**
- `main` 190 行 / 分支 308 行，差 **118 行，且是纯末尾追加**。两个新 job 一行都没碰既有 7 个 job、`on:`、`permissions:`。

**E. plan `2026-08-22-0027-2` 欠的两项（本 plan 只承接第一项）**

- E1 · Phase 2 的 `Proof` **守卫 job 的变异实证**（三次实验：正向必红 / revert 必绿 / 只动账本必不触发）——
  **没有任何 run id**。0027-2 自己逐字写着「**拿不到这三条，守卫不算交付**——绿的 CI 证明不了一个从不触发的守卫」。
  它三次独立关闭审计都拒绝给这一项打勾，理由是「打勾即伪造证据」。**本 plan 就是来还这一项的。**
- E2 · Phase 3 的 `Fix`「把前驱两条 Deferred 记为了结」—— 被 E1 卡死，**归本批第二个 plan**（守卫交付之后才写得出「了结」）。

**G2. 判定器本体是 `plan-first` 受保护面——实验 ①④ 会碰它，此处逐条对齐 Required Evidence**

- `docs/context/ai-autonomy-policy.md` Protected Areas 末行逐字：
  `tools/gates/check_expected_red.py`（**门禁判定器本体**）| `plan-first` |
  「独立草案评审 + 独立关闭审计 + **「默认判定环境输出逐字节不变」的前后两次实跑** +
  **判定器自身的变异验证**（**改坏它必须让 `tests/unit` 红**）」——
  括号里那半是该项真正的验收判据，此前本节把它截掉了，现补全逐字引用。
- 本 plan 的对齐结论，**四条逐条给，不含糊**：
  · **独立草案评审**：本 plan `## Draft Review Record` 已记录多轮 —— **满足**；
  · **独立关闭审计**：`> Audit: required`，关闭时由独立子代理做 —— **满足**；
  · **「默认判定环境输出逐字节不变」的前后两次实跑**：本 plan 对该文件的**净改动为零**
    （实验 ①④ 的空行改动在清理步骤被 `reset` 抹掉，机械判据在 Phase 3 清理项里），
    但仍按该行要求补齐两次实跑——**Phase 2 开跑前记一次「前」的基线输出**，
    Phase 4 的 `python3 tools/gates/check_expected_red.py` 复跑就是「后」，两次输出逐字节对照；
  · **判定器自身的变异验证**：**不适用，理由逐字写明**——本 plan 的变异对象是**守卫 job**，
    不是判定器；判定器的变异验证（其验收判据逐字是「改坏它必须让 `tests/unit` 红」）
    由 plan `2026-08-22-0027-1` 与 `2026-08-22-0228-1` 各做过一次，本 plan 不重复，也不假装做过。
    本 plan 对判定器的净改动为零，因此不存在「需要让 `tests/unit` 红」的对象。

**F. 覆盖面的天然缺口（0027-2 已逐字登记，本 plan 不消灭它，只如实继承）**

- `gates.yml` 的 `on: push` 限定 `branches: [main]`，因此守卫的 **`push` 那条 BASE/HEAD 推导路径在合并前无法实测**。
  本 plan 的四条实验全在 PR 分支上做，**只证明 `pull_request` 那条路径**。这句限定必须原样带进结论，
  **不得让它读成「守卫已全面实证」**。`push` 那条路径的首次实测归本批第二个 plan（`main` 落地后的那次 push 运行）。

**G. 授权面（动 `.github/workflows/**` 这件事的口径，照实记，本 plan 不替人改）**

- `AGENTS.md` 红线 2 只禁**变松**（禁用 job / `continue-on-error` / 缩小触发范围）；本 plan 是纯追加，方向是**加严**。
- 但 `docs/context/ai-autonomy-policy.md` Protected Areas 表第 3 行写的是 `.github/workflows/** | blocked | 人工批准`，
  **两处措辞不一致**。这处不一致已由 plan `2026-08-22-0027-2` 登记成一条**人动作** Deferred，**至今未裁**。
- **该表自己的前言逐字写着**「下表前八条全部照抄 `AGENTS.md` 的红线表——**此处不新增、不放宽任何一条**」，
  而它那一行的 Required Evidence 列引的正是红线 2「不得让门禁变松」。把 `blocked` 读成「一律禁止」会让该表**自相矛盾**；
  `AGENTS.md` 第 3 行又把红线置于一切之上。**因此本 plan 不停下等人。**
- **本 plan 的处置**：沿用**已在 `main` 上落地的先例**——plan `2026-08-21-2220-2` 用同一条「纯追加 = 加严」的读法
  把 `gates-l2` job 加进了 `main` 的 `gates.yml`（`main` 上 7 个 job 键里就有它；
  **先例的机械出处**：`git log -S 'gates-l2:' -- .github/workflows/gates.yml` → `6ac1005`，至今未被推翻）。本 plan 不替人改那一行 Rule，
  只在 `## Deferred But Adjudicated` 里把这条人动作项**继续挂着**并指向已有登记。

## Goals

1. **守卫 `verdict-tool-untouched` 拿到四条变异实证**（正向必红 / revert 必绿 / 只动账本必不触发 / 带 trailer 必放行），
   每条带 run id 与 job 结论逐字。没有它，守卫只是一条没有证据的安全声明。
2. **另起一条从当前 `main` 切出的新分支 `ci/1206-1-verdict-guard-proof` 与一个新 PR**：
   分支 = `main` + **唯一一个纯追加提交**（118 行，与已实测那份逐字一致），
   使 `git diff --numstat $(git merge-base main <新分支>) <新分支>` 只剩 `.github/workflows/gates.yml` 一个文件、`+118 / −0`，
   且新 PR 的 `baseRefOid` **恰好等于**切分支时那个 `main` sha。
   **三条理由，缺一条这个 Goal 都不成立**：① 让 CI 在 `main` 的代码上跑（C4）；
   ② 让本批第二个 plan 的 `--ff-only` 落地成为可能（分支不含 `main` 就 ff 不动）；
   ③ **最硬的一条**：`pull_request` 的 `BASE` 在 PR 创建时钉死（C5），沿用 PR #1 会让 `BASE` 永远停在 `7b0f585`，
   守卫恒红、四条实验全部失去鉴别力。**这不是「消除合并风险」**——C1 已实测合并 PR #1 删不掉任何东西。
3. **在当前 `main` 基线（含 `2026-08-22-0228-1` 改过的判定器）上重新取得 `gates-l2-live` 的 `success`**，
   把 C4 那处过期的绿证据补成有效的。

## Non-Goals

- **不把两个 job 落进 `main` 的 `gates.yml`**。合并/落地、`main` 的 push 权威运行、roadmap「9 现状」改准、
  工作项 9 的判据裁定，全部归本批第二个 plan `2026-08-22-1206-2`。
  ⚠️ **说清楚一件事**：本 plan 的 Phase 4 **会**往 `main` 提交文档（§14.4、log、STATE §2），
  因而会触发一次 `main` 的 push 运行——但那时 `main` 上**还没有**这两个 job，
  所以那次运行**不构成**守卫 `push` BASE/HEAD 路径的实测，也不构成工作项 9 判据的成立。
- **不改 `tests/gates/**`**（红线 1）、**不改 `agenerp/**`**、**不改 `docker-compose.yml`**。
- **不改 `tools/gates/check_expected_red.py` 的最终形态**：实验 ① 会临时改它一个空行，
  收尾时必须 revert 干净，机械判据见 Phase 4。
- **不让 `tools/gates/expected-red.txt` 变长**：实验 ③ 只加一行 `#` 注释，收尾必须清掉。
- **不改 plan `2026-08-22-0027-2` 的 `Plan Status`，不勾它任何一个 `[ ]`**。它是否 Reopen 由人裁定
  （STATE §3 逐字：「它是否 Reopen 续跑由人决定」）；本 plan 只在其 `Closure Audit Log` **追加**事实行。
- **不改 `docs/context/ai-autonomy-policy.md` 的 Rule 列**（见 Baseline G）。
- **不动 PR #1 与它的分支 `ci/0027-2-l2-full-live-gate`**：不 force-push、不改 base、不关闭、不合并。
  本 plan 全程在新分支 `ci/1206-1-verdict-guard-proof` 与新 PR 上做（C5.4）。PR #1 的终局处置归本批第二个 plan。

## Task Route

- Type: `verification or audit work`（主体是给一个已存在的 CI 守卫补实证；附带一次分支形态修复）
- Owner Docs: `docs/architecture/system-baseline.md` §14.4（判定器与 CI 判定口径的真相源）·
  `docs/context/ai-autonomy-policy.md`（Protected Areas，只读不改）· `AGENTS.md` 红线 1/2 与裁判规则 1/2/3/4
- Skill Selection Basis: `docs/skills/README.md` 的 Skill Routing Rule 第 5 条——本 plan 的工作方法是
  「对一条已存在的 CI 守卫做变异实验并逐字留痕」，Skill Registry 里没有匹配的工作方法条目，
  因此全程 `Skill: none`，走常规 docs-driven 流程。

## Infrastructure And Config Prereqs

- 需要 `gh` CLI 已认证（PR #1 由同一条链路创建过，认证链路已实证可用）。
  **认证失败是 `AGENTS.md` 裁判规则 4 的停机条件之一**，触发即停，不重试绕过。
- 需要**新建远程分支 `ci/1206-1-verdict-guard-proof`** 并向它推送（含实验期间的 `--force-with-lease`）的权限，
  以及向 `origin/main` 推送的权限（两者的论证都在 **Phase 1** 的两个 `Decision` 里）。
  ⚠️ **不需要**向 `origin/ci/0027-2-l2-full-live-gate` force-push 的权限——本 plan 不碰那条分支（见 Non-Goals）。
- CI 侧无新增 secret / 无新增 runner 需求：两个 job 都只用 `ubuntu-latest` 自带的 docker + `pip install pytest`。
- 本机侧无需起 docker 栈——本 plan 的证据全部来自 CI runner。
- **回滚策略（分两面说，别混）**：
  · **分支面**：可回滚——`git reset --hard <Phase 2 sha>` + `--force-with-lease`，作用对象是**本 plan 自己新建的**
    `ci/1206-1-verdict-guard-proof`。四条实验的清理走的就是它。**PR #1 的分支不在此列，本 plan 不碰它。**
  · **`main` 面**：**不可回滚**。⚠️ **第 5 轮改准**：此前写的是「推两次（Phase 1 追平那 10 个既有提交、Phase 4 收尾的文档提交）」；
    A3 实测 `origin/main` 已等于 `main`，**Phase 1 那一推已成为 no-op**，因此正常路径下本 plan 只往 `origin/main` 推
    **一次**（Phase 4 收尾的文档提交）。已推历史不改写。
    **补偿是「推前预检」而不是「推后回滚」**：每一次推（含 Phase 1 万一需要的补推）都有写死的四条预检，
    预检不为期望值就不推。
  · 本 plan 对 `main` 的 **workflow 零改动**（Non-Goals 第一条只说这一件事，不是说 `main` 零改动）。

## 停机纪律（本 plan 特有，必须先读）

本 plan 会**故意**让 CI 红一次（实验 ①）。`AGENTS.md` 裁判规则 4 的停机条件之一是「CI 连续 2 轮红」，
因此必须先把「预期红」与「真红」分开，否则要么误停机、要么把真红当实验红放过去。**判据钉死如下**：

**两个定义必须互补穷尽，不留未定义区**（独立评审第 2 轮：原写法在「只有守卫红、但 head sha 不是实验 ① 的」
那一格里两边都落不进去，而那一格恰恰是本 plan 自己预判会发生的情形）：

- **预期红** = **下面三条同时成立**（只看 job 集合不够——守卫因 `set -euo pipefail`、`BASE` 取不到、
  checkout `fetch-depth` 回归等**无关原因**失败时，job 集合长得一模一样）：
  · (a) `verdict-tool-untouched` 为 `failure`，**且** `gates-l1` / `gates-untouched` / `expected-red-ratchet` /
    `masterplan-links` / `roadmap-parseable` / `loop-wiring` / **`gates-l2`** **全部 `success`**
    （**`gates-l2` 必须点名**——它也起 docker 栈、也会抖，漏掉它会让一次真红满足 (a)(b)(c) 而被吞成「预期红」）；
  · (b) 该 job 日志**逐字**同时含 `本次改动触及判定器：` **和** `❌ 改动了门禁判定器却没有人工批准。`；
  · (c) 该 run 的 head sha **恰好**是实验 ① 那个提交的 sha。
- **真红** = **凡不满足上面三条的任何一次红，一律按真红计**。没有第三种归类。
  真红**照常计入**停机计数：**连续 2 轮真红即停机**，写进 `STATE.md` §3 的 needs-human 队列，等人。
- **`gates-l2-live` 单独开一格，理由是它有实测在案的间歇性**（本机 6 跑红 1 次、runner 2 跑红 2 次，见本节末的先例行）：
  它在实验轮里红时，按裁判规则 3 **原样复跑一次**；它的结论**不参与实验 ① 的判定**（(a) 的清单里没有它），
  但**照常计入真红计数**。这样一次抖动不会把一条正确触发的守卫判决作废，也不会让抖动隐形。
- 实验 ① 的空白改动**必须落在语义无关处**（文件末尾加一个空行）。若 `gates-l1` 跟着红，
  说明这一改有语义 → 按「真红」处置，**不得**辩解成「实验污染」了事。
- 实验 ③ 只允许给 `expected-red.txt` 加一行 `#` 注释。若 `expected-red-ratchet` 红了，
  说明账本行数被改变 → 按「真红」处置。

**CI 运行预算（裁判规则 4 的「单 mission 累计成本超阈值」也是停机条件）**

- 本 plan 声明的预算：**上限 12 次运行**，逐项算得出来：
  Phase 4 `main` 收尾 1 · 新 PR 建立后的基线 1 · 实验 ①②③④ 各 1（= 4）·
  隔离纪律要求的 reset 推送最多 3（③ 前、④ 前、最终清理）· 机动 3。
  ⚠️ **第 5 轮改准**：原枚举里的「`origin/main` 追平 1」已不存在（A3：`origin/main` 已等于 `main`，那一推是 no-op）。
  **总额仍保持 12 不变**，腾出的那一格并进机动——本轮新增了「建 PR 前重新核验两值相等」这类可能引发复跑的核验点。
  **不做「reset 到已跑过的 sha 不另计」这种假设**——force-push 会不会触发 `synchronize` 事件本仓没实测过，
  按最坏情形算预算，实际少跑就少跑。
  每次运行都会起一整套 ERPNext/MariaDB 栈（`gates-l2-live`，`--wait-timeout 900`）。
- **超出即停**：跑满 12 次仍未拿齐四条实验证据 → 停机，写 `STATE.md` §3 needs-human，**不得**继续加跑。
- 先例：前驱 plan `2026-08-22-0027-2` 自设过「CI 实跑 1 次（硬上限 2）」（STATE §2）。本 plan 的预算更高，
  是因为四条实验各自必须独立成跑（隔离纪律），**这一点在 Phase 3 有机械判据兜底，不是放宽**。
- **NB2 的计数锚点说清楚**：`0027-2` 定的「`CI 已验证` 的充要条件是执行期间主判定 job 从未出现非预期红」
  锚在**它自己**身上；本 plan 起一个**新计数器**。run `32509351108` 那次可复现的红是永久证据，
  在任何改准后的表述里都不得抹掉。

## Execution Plan

### 全程硬规矩：文档改动只提到 `main`，分支上只许有那一个追加提交

**这条不是风格偏好，是防一次静默数据丢失**（独立评审第 3 轮实测）：`docs/logs/2026/08-22.md` 是**已跟踪文件**，
而 Phase 3 要做三次 `git reset --hard <Phase 2 sha>`（③ 前 / ④ 前 / 最终清理）。两条路都是坏的——
把日志提交到分支上，区间提交数当场破坏 Phase 1 的「恰好一个提交」与隔离纪律的 ①=2/②=3/③=2/④=2；
不提交就留在工作树里，`reset --hard` 会**把它连同前三个阶段的日志记录一起丢掉，且不报错**。

- **`docs/logs/**`、本 plan 文件、`STATE.md`、`docs/architecture/system-baseline.md` 的编辑，一律只在 `main` 上提交**
  （临时 `git switch main` → 提交 → 切回分支）。
- 新分支 `ci/1206-1-verdict-guard-proof` 上**只允许**存在：Phase 1 那一个 118 行追加提交，以及实验期间的临时提交。
- **每次 `git reset --hard` 之前先跑 `git status --porcelain` → 期望输出为空**；不为空就先切回 `main` 提交，再回来 reset。
- **`<Phase 2 sha>` 的定义在此处钉死**：**就是 Phase 1 那个 118 行追加提交的 sha**
  （Phase 2 不在分支上产生任何提交——它只跑 CI 与留痕，而留痕按上面第一条提到 `main`）。

### Phase 1 — 新建实验载体分支与新 PR（PR #1 全程不动）

Status: completed
Targets: **新建**分支 `ci/1206-1-verdict-guard-proof`（远程与本地）· 新建 PR · 本 plan 文件 ·
  `docs/logs/2026/08-22.md`
  （**不含** PR #1 与 `ci/0027-2-l2-full-live-gate`——本 plan 不碰它们）
Skill: `none`

- Item Types: `Decision | Fix | Proof`
- Prereqs: 无

- [x] `Decision` **实验载体定死为「从 `main` 新切一条分支 + 单提交 append + 新建 PR」，并写清备选与残余风险**。
      ⚠️ **本项标题在第 5 轮就地改准**：原标题写的是「刷新方式定死为『reset 到 `main` 再单提交 append』」，
      那是第 4 轮改写**之前**的残留——它描述的正是本项自己已经否掉的**备选 (d)**（force-push PR #1 的分支）。
      照原标题执行会直接踩中 C5.1 那个陷阱，与下面的「选定方案」自相矛盾。
      **⚠️ 本项的理由在独立评审第 1 轮被推翻过一次，下面是改准后的版本**：起草时写的
      「PR #1 按现状合并会回退 3455 行」是**两点式误读**，C1 已实测**合并删不掉任何东西**。
      真实理由只剩两条，都成立且都够硬：
      · **理由一（C4）**：分支落后 `main` 21 个提交（C3），其中 `57ad6d5` 改的正是 `gates-l2-live` 唯一执行的那条命令
        （判定器）。不追平，分支上的 CI 就永远证明不了 `main` 的代码。
      · **理由二**：本批第二个 plan 选的是 `--ff-only` 落地，**分支不包含 `main` 就 ff 不动**。
      · **理由三（独立评审第 4 轮新增，是三条里最硬的一条）**：`pull_request` 的 `BASE` 在 **PR 创建时**钉死（C5），
        PR #1 的 `baseRefOid` 永远是 `7b0f585`。**沿用 PR #1 的分支做实验，守卫恒红且与实验载荷无关**（C5.1），
        四条实验一条也证明不了。所以载体必须换，而不只是把分支追平。
      - **选定方案（⚠️ 本项在独立评审第 4 轮被整条改写）**：**不动 PR #1，另开新分支与新 PR**——
        `git switch -c ci/1206-1-verdict-guard-proof main` → 把已实测那 118 行原样追加到
        `.github/workflows/gates.yml` 末尾 → **一个**提交 → `git push -u origin ci/1206-1-verdict-guard-proof`
        → `gh pr create --base main --head ci/1206-1-verdict-guard-proof`。
        **顺序硬约束**：`git push origin main`（第二个 `Decision`）**必须在 `gh pr create` 之前**完成——
        新 PR 的 `base.sha` 等于**创建那一刻 `origin/main` 的 tip**，`origin/main` 还停在 `508c75b` 时建 PR，
        `BASE` 就是 `508c75b`，区间里含无 trailer 的 `57ad6d5`，守卫照样恒红。
      - **⚠️ 提交信息硬约束**：该提交的 message **不得包含 `Gates-Change-Approved-By:`**。
        守卫扫的是整个 `BASE..HEAD` 区间的 message（`git log --format=%B "$BASE..$HEAD" | grep -q '^Gates-Change-Approved-By:'`），
        区间里任何一个提交带了 trailer，实验 ① 就会**放行成 `success`**，整组实验当场作废。
      - **备选 (a) `git merge main` 进分支**：**不选**。会产生 merge commit，PR diff 里混进 `main` 那 21 个提交的内容，
        「PR 上评审的就是这 118 行」这句话不再成立。
      - **备选 (b) `git rebase main`**：**不选**。分支上的 `c2c688b`（`agenerp/oob.py` 的 `FALSY_RESULT` 修复）
        内容**已经在 `main` 上**（`578eb8f`，实测 `git diff --numstat main origin/… -- agenerp/` 零输出），
        rebase 会产出空提交或冲突，换来一段没有信息量的历史。
      - **备选 (c) 什么都不做，直接让第二个 plan 合并 PR #1**：**不选**，理由是 C4——
        那样落到 `main` 的 118 行**从未在 `main` 的判定器上跑过**。
      - **备选 (d) force-push PR #1 的分支（本项改写前的选定方案）**：**不选**，理由是 C5.1——
        `base.sha` 钉死在 `7b0f585` 不随之更新，守卫恒红，四条实验全部作废；且 C5.2 那条 `1 / 118 / 0` 硬判据也会必然失败。
      - **备选 (e) `gh pr edit 1 --base <临时分支>` 再改回 `main`，逼 GitHub 重算 `base.sha`**：**不选**。
        **本仓从未实测过这个行为**，把一组实验的成立前提押在一个未验证的 GitHub 行为上，正是本 plan 反复批评的毛病。
        建新 PR 是同样成本、且语义确定的路。
      - **残余风险（照实记，共两条）**：
        · ① 仓库里会同时挂着两个 open PR（#1 与新 PR），内容是同一份 118 行。**这是有意为之**：PR #1 连同它的
          run `32509351108`（红）与 `32533449466`（绿）保持原样不动，是一条完整的历史证据链；新 PR 只承载本 plan 的实验。
          **消歧办法**：`gh pr create` 的正文首行逐字写明「本 PR 取代 PR #1 作为 plan 2026-08-22-1206-1 的实验载体，
          PR #1 保持不动，终局处置归 plan 2026-08-22-1206-2」。两个 PR 的终局处置归本批第二个 plan，本 plan 不替它决定。
        · ② 新 PR 上不存在 PR #1 那两次历史运行。补偿与原方案相同：run id 与结论已逐字存在 `STATE.md` §3 和
          roadmap「9 现状」里，`gh run view <id>` 仍可查；**证据不依赖任何一条分支或 PR 存活**。
      - **前置保命闸**：建分支前先把已实测那 118 行**存成一个文件**
        （`git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml | tail -n 118 > /tmp/two-jobs.yml`），
        **不手打、不凭记忆重写**；后续所有「逐字一致」判据都对着这个文件比。
        ⚠️ 这是本 plan **唯一**一次读 `ci/0027-2-l2-full-live-gate`，且是只读，不违反 Non-Goals 的「不动 PR #1」。
      - Skill: `none`
- [x] `Decision` **建 PR 之前 `origin/main` 必须已等于 `main`——⚠️ 第 5 轮整条改准：这个前提此刻已经成立，
      本项因此从「执行一次抢跑推送」降级为「核验 + 留痕」，但一条也不许略过**。
      **改准的事实（A3）**：起草时本地 `main` 领先 `origin/main` 10 个提交、未推；
      实测此刻 `git rev-parse main origin/main` → **两值相等**（均为 `4d7b311…`），
      `git log --oneline origin/main..main | wc -l` → `0`。那 10 个提交（含无 trailer 的判定器改动 `57ad6d5`）**早已推上去**。
      **为什么这个前提仍然承重（论据保留，因为它解释了「为什么现在是安全的」而不只是「现在没事」）**：
      新 PR 的 `base.sha` **等于 `gh pr create` 那一刻 `origin/main` 的 tip**（C5）。
      若 `origin/main` 落后于 `main`，`BASE` 就会落在一个**含无 trailer 判定器改动**的区间起点上
      （起草时那个具体形态：`git diff --name-only 508c75b aba9a5f -- tools/gates/check_expected_red.py tools/gates/gate-verify.mjs`
      → 命中；`git log --format=%B 508c75b..aba9a5f | grep -c '^Gates-Change-Approved-By:'` → `0`）
      → **守卫在新 PR 上恒红**，Phase 2 的基线绿拿不到，四条实验全部失去鉴别力。
      **`push` 路径那半的风险已经过去，照实记**：起草时担心的「守卫落进 `main` 之后再推这 10 个提交必然红」
      （`BASE=github.event.before`，区间含无 trailer 的判定器改动）**已经不会发生**——那些提交在守卫落地**之前**就推完了。
      安全窗口**被用掉了，而且用对了**；`main` 上此刻仍零守卫（`git show origin/main:.github/workflows/gates.yml | grep -c 'verdict-tool-untouched'` → `0`），
      窗口在本批第二个 plan 落地那一刻才永久关闭。
      - **选定**：Phase 1 开工第一步**核验** `git rev-parse main origin/main` 两值相等并抄进 plan；
        **不等**（例如执行跨过了 Phase 4 的推送后又复跑）才补一次 `git push origin main`，
        补推前必须跑下面那四条预检。顺序硬约束不变：**`origin/main == main` 成立在前 → 切新分支 → `gh pr create`**。
      - **备选 (a) 不核验，直接建 PR**：**不选**——`base.sha` 一旦钉在一个落后的 sha 上就不可挽回，
        只能弃掉这个 PR 重建（C5：`base.sha` 不随 base 分支 tip 更新）。核验成本是一条命令。
      - **备选 (b) 给 `57ad6d5` 补 trailer**：**不选**（此刻已无必要，且原理由仍成立）——
        改写已推历史，且 trailer 是给人用的批准语义，loop 不得自签。
      - **四条推前预检**（只在真需要补推时跑；Phase 4 那次收尾推送**无条件**跑同一组），
        任何一条不为期望值就不推：
        · `git diff --stat origin/main main -- .github/workflows/` → 期望**无输出**（红线 2）；
        · `git diff --name-only origin/main main -- tests/gates tools/gates/expected-red.txt` → 期望**无输出**（红线 1 与账本）；
        · `git diff --name-only origin/main main -- docs/masterplan/DECISIONS.md` → 期望**无输出**（红线 3）；
        · `git diff origin/main main -- docs/masterplan/STATE.md | grep '^-' | grep -v '^---'` → 期望**无输出**（红线 5，只追加）。
      - **残余风险**：核验为「相等」时本阶段**不产生** `main` push 运行，CI 预算相应少用一格（见「CI 运行预算」的第 5 轮改准）。
        若确需补推，那一推会在 `main` 上触发一次完整 CI 运行（此刻 `main` 上的 7 个 job），按下面 `Fix` 项的红处置分支走。
      - Skill: `none`
- [x] `Fix` 按上面两个 `Decision` **依次**执行（**顺序是硬约束，见 `Decision` 2 的选定项**）：
      ① **核验** `git rev-parse main origin/main` 两值相等（期望均为 `$CUT` = `4d7b311…`），抄进 plan；
      不等则跑四条预检后 `git push origin main`，并记录那次 `main` push 运行的 run id 与全部 job 结论；
      ② `git switch -c ci/1206-1-verdict-guard-proof main` + 追加 118 行 + 单提交 +
      `git push -u origin ci/1206-1-verdict-guard-proof`；③ `gh pr create --base main --head ci/1206-1-verdict-guard-proof`。
      记录新 PR 的编号。
      **红了怎么办，此处写死（与 Phase 2 同一套，不许临场发挥）**：按裁判规则 3 先 `gh run rerun --failed` 原样复跑一次；
      两次都红 → **停机**，写 `STATE.md` §3 needs-human，**不猜根因**，且**不得**继续建分支建 PR
      （载体建立在 `origin/main == main` 这个前提上）；一红一绿 → 记「不可复现」，
      **不得写成「CI 已验证」**，并按「停机纪律」计入真红计数。
      - Skill: `none`
- [x] `Proof` **形态判据五条，输出逐字抄进本 plan。一律用 merge-base 形式，不用两点式**
      （两点式在 `main` 前进后会因与分支无关的原因失败，见 C2）。
      **先把切分支那一刻的 `main` sha 记成 `$CUT` 并写进 plan**（`CUT=$(git rev-parse main)`，期望 `4d7b311…`）——
      后面每一条判据都以它为锚，**不用 `git rev-parse main`**：Phase 4 会往 `main` 提文档，`main` 之后必然前进：
      · `MB=$(git merge-base main ci/1206-1-verdict-guard-proof); git diff --numstat "$MB" ci/1206-1-verdict-guard-proof`
        → 期望**恰好一行** `118	0	.github/workflows/gates.yml`；且此时 `$MB` 应逐字等于 `$CUT`（切分支的直接推论）；
      · `git log --oneline "$MB"..ci/1206-1-verdict-guard-proof | wc -l` → 期望 `1`（唯一一个追加提交）；
      · `diff <(git show "$MB":.github/workflows/gates.yml) <(head -n 190 .github/workflows/gates.yml)` → 期望**无输出**
        （前缀性：这一条同时证明「既有 7 个 job 一行未改」「`on:` / `permissions:` 未动」「零删除」，
        比 `deletions=0` 严——往既有 job 里**插**一行也是纯新增，`deletions=0` 抓不到）；
      · `diff /tmp/two-jobs.yml <(tail -n 118 .github/workflows/gates.yml)` → 期望**无输出**，
        证明追加的 118 行与已实测那份**逐字一致**，不是重写的相似版本
        （**对着保命闸存下的文件比，不用 `origin/…@{1}` 这种 reflog 形式**——任何一次 `git fetch` 都会把它挪走）；
      · **⚠️ 第五条，本轮新增，是全批最承重的一条判据**：`gh pr view <新 PR 号> --json baseRefOid`
        → 期望**逐字等于 `$CUT`**。这一条直接钉住 C5 那个陷阱：`base.sha` 一旦不是 `$CUT`，
        守卫算的就不是「本分支的 118 行」，四条实验全部作废。
        **不为期望值就停在这里**，按 `Decision` 1 的备选 (e) 处置（不自行去 `gh pr edit --base` 试探未验证行为，写 needs-human）。
      - Skill: `none`
- [x] `Proof` **trailer 洁净度预检（实验 ① 的成立前提）**：
      `git log --format=%B "$CUT"..ci/1206-1-verdict-guard-proof | grep -c '^Gates-Change-Approved-By:'`
      → 期望 `0`。**用 `$CUT` 而不是 `git merge-base main <分支>`**：守卫扫的区间起点是 `base.sha`（= `$CUT`），
      判据必须与守卫算的是同一个区间。
      **不为期望值就不许进 Phase 3**：区间里有 trailer，守卫会一路放行，四条实验全部作废。
      - Skill: `none`
- [x] `Proof` `gh pr view <新 PR 号> --json state,mergeable,changedFiles,additions,deletions` → 期望
      `state: OPEN`、`changedFiles: 1`、`additions: 118`、`deletions: 0`。
      **这一条的意义是「PR 上评审的就是这 118 行」，不是「回退风险已消除」**——C1 已实测那个风险不存在。
      ⚠️ **这条是硬判据，没有豁免，但它成立有前提，前提就是上一项的第五条**：
      GitHub 按 `base.sha` 算 PR 读数（C5.2），`baseRefOid == $CUT` 成立时读数才**必须**是 `1 / 118 / 0`。
      两条要一起看：`baseRefOid` 对不上时，`1 / 118 / 0` 对不上是**推论而不是新问题**，去修前者。
      ⚠️ **这条问的是新 PR，不是 PR #1**：PR #1 的读数仍是 `6 / 417 / 17`（基 `7b0f585`），
      本 plan 不动它，也不拿它当判据。本批第二个 plan 的 Phase 1 预检 ③ 拿的是**新 PR** 的这个值。
      - Skill: `none`

Exit Criteria:

⚠️ **本组判据在独立评审第 4 轮整体改写过一次，原因必须写下来**：原写法把三条并列成
「merge-base == `git rev-parse main`」+「`git rev-parse main origin/main` 两值相等」+「本阶段日志已追加」，
而「全程硬规矩」要求日志只提到 `main` 上——**日志一提交，`main` 就前进，前两条当场同时为假**，
三条**互相不可同时满足**。改准后一律锚在 `$CUT`（切分支那一刻的 `main` sha）与「祖先 + 只含文档」上，
不锚在浮动的 `git rev-parse main` 上。

- [x] **`$CUT` 已记进 plan**（切分支那一刻的 `git rev-parse main`，期望 `4d7b311…`），此后各判据一律以它为锚
- [x] 新分支形态：`git merge-base main ci/1206-1-verdict-guard-proof` == `$CUT`，区间内**恰好一个**提交，
      净 diff 为 `118	0	.github/workflows/gates.yml`
- [x] 追加的 118 行与 run `32533449466` 上跑过的那份**逐字一致**（对着保命闸文件比，有输出为证）
- [x] 前缀性判据无输出
- [x] trailer 洁净度预检（`$CUT`..分支）为 `0`
- [x] **`origin/main == main` 在 `gh pr create` 之前已成立且已留痕**（⚠️ 第 5 轮改准：此前写成「已追平且顺序正确 +
      推完那一刻…… + 那次 `main` push 运行的结论」，而 A3 实测那一推已成为 no-op，原判据要求一次不会发生的推送）：
      建 PR **之前**实测 `git rev-parse main origin/main` 两值相等（均为 `$CUT`）并抄进 plan，
      记下该核验与 `gh pr create` 的先后；
      **仅当**核验不等而补推时，四条推前预检的输出与那次 `main` push 运行的 run id + 全部 job 结论才逐字入 plan
      （核验相等时此处逐字写「核验相等，本阶段无 `main` push 运行」，**不得留空**）
- [x] **本阶段日志提交之后的收敛判据（取代原来那条会自相矛盾的「两值相等」）**：
      `git merge-base --is-ancestor origin/main main` **成立**，且
      `git diff --name-only origin/main main` 的输出**只含** `docs/logs/**` 与本 plan 文件
      —— 即本地 `main` 只比 `origin/main` 多出本阶段的文档提交，没有别的东西
- [x] **新 PR 的 `baseRefOid` 逐字等于 `$CUT`**（全批最承重的一条，直接钉住 C5 那个陷阱）
- [x] `gh pr view <新 PR 号>` 读数逐字为 `state: OPEN` / `changedFiles: 1` / `additions: 118` / `deletions: 0`
      （**硬判据，无豁免**；它成立以上一条为前提）
- [x] PR #1 一个字节未动：`gh pr view 1 --json state,headRefOid,baseRefOid` 与开工时逐字相同
      （`OPEN` / `c2c688b…` / `7b0f585…`）
- [x] `docs/logs/2026/08-22.md` 已追加本阶段记录

#### Phase 1 执行记录（2026-08-22 实跑回填）

**⚠️ 开工第一件事就是一处基线改准，必须写在最前面**：本 plan `## Current Baseline` A / A3 记的
`main` @ `4d7b311` 在执行当日**又已过期**——实测 `main` 已前进到 `f689d0e docs(decisions): D-8 —— OAuth
过期照旧由人处理，不换认证不加通知`（一个提交，改的是 `docs/masterplan/DECISIONS.md`，与本 plan 无关）。
因此 **`$CUT` 的实测值是 `f689d0e7cde3f2733b044b004f7a314f14958973`，不是 plan 里写的 `4d7b311…`**。
plan 全篇的判据锚点写的是 `$CUT` 这个符号而不是那个字面值（第 5 轮评审改准的正是这件事），
所以**没有一条判据因此失效**；下面全部读数一律以实测 `$CUT` 为准。
`4d7b311` 那个期望值就此作废，**不去追认它**。

**① `origin/main == main` 核验（`gh pr create` 之前，顺序留痕）**

| 命令 | 输出 | 时序 |
|---|---|---|
| `git fetch origin --prune` | （无关输出） | 建 PR 前 |
| `git rev-parse main origin/main` | `f689d0e7cde3f2733b044b004f7a314f14958973` / `f689d0e7cde3f2733b044b004f7a314f14958973` —— **两值相等** | 建 PR 前 |
| `git rev-list --left-right --count origin/main...main` | `0	0` | 建 PR 前 |
| `git log --oneline origin/main..main \| wc -l` | `0` | 建 PR 前 |
| `git fetch origin main; git rev-parse main origin/main`（**紧贴 `gh pr create` 之前再核一次**） | 两值仍为 `f689d0e…` | `gh pr create` 前一条命令 |

**核验相等，本阶段无 `main` push 运行**（Exit Criteria 逐字要求此处不得留空）。四条推前预检因此**未跑**——
它们的触发条件是「核验不等而补推」，本阶段不成立；Phase 4 那次收尾推送会无条件跑同一组。

**② 保命闸与前缀性（建分支之前）**

| 命令 | 输出 |
|---|---|
| `git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml \| tail -n 118 > /tmp/two-jobs.yml` | 存下 **118** 行（本 plan 唯一一次读该分支，只读） |
| `git show main:.github/workflows/gates.yml \| sed -n '/^jobs:/,$p' \| grep -E '^  [a-z0-9-]+:'` | **7** 个 job 键，与 Baseline B 逐字一致 |
| `git show main:.github/workflows/gates.yml \| grep -cE 'gates-l2-live\|verdict-tool-untouched'` | `0`（退出码 1）—— 安全窗口此刻仍开着 |
| `git show main:… \| wc -l` / 分支版 `wc -l` | `190` / `308` |
| `diff <(git show main:.github/workflows/gates.yml) <(git show origin/ci/…:.github/workflows/gates.yml \| head -n 190)` | **无输出** |

**③ 建分支 + 单提交 + 推 + 建 PR（顺序即执行顺序）**

- `git switch -c ci/1206-1-verdict-guard-proof main` → `Switched to a new branch 'ci/1206-1-verdict-guard-proof'`
- `cat /tmp/two-jobs.yml >> .github/workflows/gates.yml` → `wc -l` = `308`；
  `diff .github/workflows/gates.yml <(git show origin/ci/0027-2-l2-full-live-gate:.github/workflows/gates.yml)` → **无输出**
- `git commit`（**message 不含 `Gates-Change-Approved-By:`**）→ `[ci/1206-1-verdict-guard-proof b7348bf] 1 file changed, 118 insertions(+)`，
  提交 sha **`b7348bf3a1eb1eccbe1c032af8bd73ed808ed4af`**
- `git push -u origin ci/1206-1-verdict-guard-proof` → `* [new branch]`，exit 0
- `gh pr create --base main --head ci/1206-1-verdict-guard-proof …` → **PR #2**
  （`https://github.com/lize-agent-engineering/AgenERP/pull/2`）。正文首行逐字写明「本 PR 取代 PR #1 作为
  plan 2026-08-22-1206-1 的实验载体，PR #1 保持不动，终局处置归 plan 2026-08-22-1206-2」

**④ 形态判据五条（一律 merge-base / `$CUT` 形式，无两点式 `git diff main <分支>`）**

| # | 命令 | 输出 | 期望 |
|---|---|---|---|
| 1 | `MB=$(git merge-base main ci/1206-1-verdict-guard-proof); git diff --numstat "$MB" ci/1206-1-verdict-guard-proof` | `MB=f689d0e7cde…`（**逐字等于 `$CUT`**）；`118	0	.github/workflows/gates.yml` **恰好一行** | ✅ |
| 2 | `git log --oneline "$MB"..ci/1206-1-verdict-guard-proof \| wc -l` | `1` | ✅ |
| 3 | `diff <(git show "$MB":.github/workflows/gates.yml) <(head -n 190 .github/workflows/gates.yml)` | **无输出** | ✅ |
| 4 | `diff /tmp/two-jobs.yml <(tail -n 118 .github/workflows/gates.yml)` | **无输出** | ✅ |
| 5 | `gh pr view 2 --json baseRefOid` | `{"baseRefOid":"f689d0e7cde3f2733b044b004f7a314f14958973"}` —— **逐字等于 `$CUT`** | ✅ **全批最承重的一条，C5 那颗钉子钉住了** |

**⑤ trailer 洁净度预检**

`git log --format=%B "$CUT"..ci/1206-1-verdict-guard-proof | grep -c '^Gates-Change-Approved-By:'` → **`0`** ✅

**⑥ PR 读数与 PR #1 未被触碰**

- `gh pr view 2 --json state,mergeable,changedFiles,additions,deletions` →
  `{"additions":118,"changedFiles":1,"deletions":0,"mergeable":"MERGEABLE","state":"OPEN"}` ——
  逐字为 `OPEN` / `1` / `118` / `0` ✅（它成立的前提是判据 5，两条一起读）
- `gh pr view 1 --json state,headRefOid,baseRefOid` →
  `{"baseRefOid":"7b0f585f7c8082a64902da65e6e3314cb239dc9f","headRefOid":"c2c688b7f6bc49a96d1e89a3582014334ba8fb71","state":"OPEN"}`
  —— 与开工时逐字相同，**PR #1 一个字节未动** ✅

**⑦ 一处必须照实记的偏差：工作树带进来一个前序会话的未提交改动**

开工时 `git status --porcelain` **不为空**，有一行
`M docs/plans/p0-foundation/2026-08-22-1206-2-gates-l2-live-lands-on-main.md`——
那是姊妹 plan 第 4 轮草案评审的改写，前序会话未提交就结束了。
按「全程硬规矩」第三条（`reset --hard` 前工作树必须干净，否则会**静默吞掉**已跟踪文件的改动），
它必须在进 Phase 3 之前落进版本库。**处置：随本阶段的文档提交一起提到 `main` 上，内容一字未改。**
**后果照实写**：Phase 1 的收敛判据原文要求 `git diff --name-only origin/main main` **只含**
`docs/logs/**` 与**本** plan 文件，而实际还多一个**姊妹 plan 文件**。
这一条偏差**不隐藏、不改判据去迁就**：多出来的那个文件仍在 `docs/plans/p0-foundation/**` 之内，
与 Phase 4 收尾那条更宽的收敛判据逐字相容；**丢弃它才是真正的损失**（销毁一次独立评审的产物）。

**⑧ 本阶段 CI 消耗**：`gh pr create` 触发 `pull_request` 事件一次 → run **`32569935835`**（head `b7348bf`）。
**这一次运行同时就是 Phase 2 的基线运行**，不另起。滚动计数：**1 / 12**。
（`git push -u origin <分支>` 本身**不触发**：`gates.yml` 的 `on: push` 限定 `branches: [main]`。）

### Phase 2 — 在当前 `main` 基线上重新取得 `gates-l2-live` 的绿

Status: planned
Targets: 无**代码 / 配置**改动（本阶段只跑 CI 并留痕）· 本 plan 文件 · `docs/logs/2026/08-22.md`
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 1 完成

- [ ] `Proof` **先记一次「前」的本机判定基线**（G2 第三条要求的那半）：
      `python3 tools/gates/check_expected_red.py` → 期望 exit 0，输出逐字存进 plan
      （期望 `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`）。
      Phase 4 收尾那次复跑是「后」，两次**逐字节对照**。
      - Skill: `none`
- [ ] `Proof` **取得新 PR（`ci/1206-1-verdict-guard-proof`）上的一次完整运行**，逐字记录：run id、每个 job 的 id 与 conclusion。
      ⚠️ **第 5 轮改准**：此处此前写的是「刷新后 PR #1 上的一次完整运行」，那是第 4 轮换载体**之前**的残留。
      **PR #1 不是本 plan 的载体**（Non-Goals 与 C5.4：它全程不动），在它上面取运行既拿不到 `BASE = $CUT`，
      也违反本 plan 自己的 Non-Goals。
      判据：**`gates-l2-live` 为 `success`**，且它的日志里逐字出现
      `门禁 19 项：红 0，绿 19，跳过 0` 与 `✅ live 判定：全部门禁绿，零 red、零 skip`。
      **这一条不是重复劳动**：Baseline C4 已实测判定器在 `main` 上被 `2026-08-22-0228-1` 改过（`7 42`），
      run `32533449466` 的绿**没有覆盖当前这份判定器**，而 `gates-l2-live` 唯一执行的命令就是它。
      - Skill: `none`
- [ ] `Proof` **同一轮里其余 job 全部 `success`**（含 `verdict-tool-untouched`——此刻它应当**未触及判定器**而提前 `exit 0`，
      日志逐字 `✅ 未触及判定器`）。**注意这一条证明不了守卫有牙齿**，它只是基线；牙齿归 Phase 3。
      - Skill: `none`
- [ ] `Proof` **若 `gates-l2-live` 红**：按裁判规则 3，先 `gh run rerun --failed` **原样复跑一次**，
      两次都红 → 记「可复现」并**立刻停机**写进 `STATE.md` §3（不猜根因，不在本 plan 里修 `agenerp/**`）；
      一红一绿 → 记「不可复现」，**照实写，不得写成「CI 已验证」**，并把它作为已知风险带进本批第二个 plan。
      （先例：同一条门禁在本机 6 跑红过 1 次、在 runner 上 2 跑红过 2 次，两种情形都发生过。）
      - Skill: `none`

Exit Criteria:

- [ ] **新 PR** 上有一次运行，`gates-l2-live` 结论逐字入 plan（run id + job id + conclusion）
- [ ] 该轮其余 job 的结论逐字入 plan
- [ ] **`check_expected_red.py` 的「前」基线输出已逐字入 plan**（G2 第三条要求的那半；Phase 4 复跑是「后」）
- [ ] 红/绿两种走向的处置已按上面写死的分支执行，没有把红写成绿
- [ ] `docs/logs/2026/08-22.md` 已追加本阶段记录

### Phase 3 — 守卫的四次变异实证（本 plan 的主交付）

Status: planned
Targets: 新分支 `ci/1206-1-verdict-guard-proof` 上的**临时实验提交**（最终全部清理）· 本 plan 文件
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 2 完成（先有一次干净的基线运行，才分辨得出实验引起的变化）

- [ ] `Proof` **实验隔离纪律（先立规矩，四条实验都受它约束）**。守卫比的是**累积** `BASE..HEAD`
      （`git diff --name-only "$BASE" "$HEAD" -- 'tools/gates/check_expected_red.py' 'tools/gates/gate-verify.mjs'`，
      `BASE` 取 `pull_request.base.sha`），trailer 也是**整区间**扫。因此**实验不许叠罗汉**：
      · **动手前先跑 `git status --porcelain` → 期望输出为空**（见「全程硬规矩」：`reset --hard` 会静默吞掉
        工作树里未提交的已跟踪文件改动，而日志是已跟踪文件）；
      · **①→② 是唯一允许叠加的一对**：② 的动作就是 `git revert` 掉 ①，先 reset 就没有 revert 对象了。
        **③ 与 ④ 各自开跑前必须 `git reset --hard <Phase 2 sha>` + `git push --force-with-lease`**，回到干净起点；
      · 每次推送前的机械预检两条，**期望值逐条写死，不是「该实验声明的数」这种空话**
        （区间起点是 Phase 2 sha，它上面已经有 Phase 1 那个 118 行追加提交，所以基数是 1）：
        `git log --oneline "$CUT"..HEAD | wc -l`
        → **① 期望 `2` · ② 期望 `3` · ③ 期望 `2` · ④ 期望 `2`**；
        `git log --format=%B "$CUT"..HEAD | grep -c '^Gates-Change-Approved-By:'`
        → **①②③ 期望 `0`，④ 期望 `1`**。
        （**一律锚 `$CUT`，即守卫真正用的 `base.sha`**——`git merge-base main HEAD` 在 Phase 4 推 `main` 之后会漂，
        而守卫算的区间从头到尾都是 `$CUT..HEAD`。）
      **不这么做的后果是实测可复现的**：实验 ③ 若堆在 ①+② 之上，它绿只是因为 ② 把净 diff 抹平了，
      证明不了「账本不在守卫路径清单内」；实验 ④ 一旦留在区间里，其后每条实验都会被 trailer 一路放行。
      - Skill: `none`
- [ ] `Proof` **实验 ①（正向，必须红）**：往 `tools/gates/check_expected_red.py`
      **文件末尾加一个空行**，提交信息**不带** `Gates-Change-Approved-By:` trailer，推到分支。
      判据：`verdict-tool-untouched` 结论为 **`failure`**，日志逐字出现
      `本次改动触及判定器：` 与 `❌ 改动了门禁判定器却没有人工批准。`。
      **判定一律按「停机纪律」的「预期红」三条走，此处不另立标准**：
      (a) 七个点名 job（`gates-l1` / `gates-untouched` / `expected-red-ratchet` / `masterplan-links` /
      `roadmap-parseable` / `loop-wiring` / `gates-l2`）全部 `success` 且 `verdict-tool-untouched` 为 `failure`；
      (b) 两条日志原文；(c) head sha 对得上。`gates-l2-live` 按停机纪律里给它单开的那一格处置，**不参与本实验判定**。
      尤其 `gates-l1` 必须仍 `success`——它跑的就是这个脚本，跟着红说明这一改有语义、实验作废。
      逐字记录：run id、job id、conclusion、红 job 集合。
      - Skill: `none`
- [ ] `Proof` **实验 ②（复原，必须绿）**：`git revert` 掉实验 ① 那个提交（同样不带 trailer），推到分支。
      判据：`verdict-tool-untouched` 回到 **`success`**，日志逐字 `✅ 未触及判定器`。
      ⚠️ **这一条有一个必须当场验的坑**：守卫比的是 `BASE..HEAD` 的**累积 diff**（`git diff --name-only "$BASE" "$HEAD"`），
      PR 的 `BASE` 是**创建 PR 那一刻钉死的 `base.sha`**（= `$CUT`，见 C5——**不是** base 分支的当前 tip，
      本 plan 此前写成后者，已在第 4 轮评审整条改准）。
      revert 之后 `git diff --name-only <BASE> <HEAD> -- tools/gates/check_expected_red.py` 为空 → 应当绿。
      ⚠️ **顺带把守卫的真实语义写准**：`git diff A B` 是**两点式 tip-to-tip 树比较**，不是 merge-base（`A...B` 才是）。
      本 plan 期间两者恰好相等（`main` 是分支祖先），**但这个等式是有前提的**，别当成 `git diff` 的普遍语义。
      **若它仍红**，说明守卫比的其实是逐提交而非累积，那是守卫的真实行为，**照实记，不许改判据去迁就期望**。
      **并且此时必须走这条写死的分支**：② 红 → **先 `git reset --hard <Phase 2 sha>` + force-push 回干净起点，再跑 ③**；
      **不得**把 ③ 堆在一个净 diff 非空的区间上（那样 ③ 无论红绿都解释不了任何事，作废）。
      逐字记录：run id、job id、conclusion。
      - Skill: `none`
- [ ] `Proof` **实验 ③（边界，必须不触发）**：推一个**只动 `tools/gates/expected-red.txt`** 的提交，
      改动内容**只能是加一行 `#` 开头的注释**。判据两条：
      · `verdict-tool-untouched` **`success`** 且日志逐字 `✅ 未触及判定器`（账本不在守卫的路径清单内）；
      · `expected-red-ratchet` **`success`**（`count()` 是 `grep -vE '^\s*(#|$)' | wc -l`，注释不计数、行数持平）。
      **这是本仓反复声明的那条硬边界（账本只能变短、划短不需 trailer）第一次拿到实证**，此前它只是一句话。
      ⚠️ **一句去混淆的话，别让读者自己去凑**：`✅ 未触及判定器` 这行**既**是本实验期望的正确出口，
      **也**是已登记的 `|| true` 假阴路径会打印的同一行。本实验仍成立，是因为实验 ① 在**同一套配置**下
      证明了 `git diff` 那一步确实工作（它红得出来）；两条一起读才排除得掉假阴。
      ⚠️ **不得加一条真的 nodeid**：那会让名单变长、当场触发棘轮，把实验污染成两个 job 同时红，什么也证明不了。
      逐字记录：run id、job id ×2、conclusion ×2。
      - Skill: `none`
- [ ] `Proof` **实验 ④（放行路径，必须绿且必须是「放行」而不是「未触及」）**。
      **加它的理由（独立评审 B6）**：守卫有四条出口，其中「触及 + 带 trailer → 放行」这一条
      **在 ①②③ 里一次都走不到**，而它恰恰决定「人将来还能不能合法地改判定器」。
      若 `grep -q '^Gates-Change-Approved-By:'` 的匹配式在实践中不成立（trailer 位置、`%B` 的换行、
      squash 合并重写 message），**每一次合法的判定器改动都会被一个从未被证明能打开的守卫挡住**。
      做法：先按隔离纪律 reset 回 Phase 2 sha，再推一个改 `tools/gates/check_expected_red.py`
      （同样是**文件末尾加一个空行**，语义无关）且提交信息**带** trailer 的提交。
      ⚠️ **与「loop 不得自签批准」那句的界线，此处逐字划清**（独立评审第 2 轮）：
      Phase 1 备选 (b) 拒绝给 `57ad6d5` 补 trailer，是因为那会**追认一次真实的判定器改动**。
      本条不同：它是**一次性实验载荷，不批准任何真实改动**，且会在清理步骤被 `reset` 移出分支，
      **永不进入 `main`、也不留在 PR 的最终形态里**。
      ⚠️ **措辞准确性（第 4 轮评审 nit）**：`reset` + force-push **不等于「抹掉」**——
      被 force-push 掉的提交在 GitHub 上按 sha 仍可长期访问。成立的说法只有「不进 `main`、不留在 PR 最终形态」这两句。为了让这一点在 git 历史里也读得出来，
      姓名字段**逐字**用 `Gates-Change-Approved-By: EXPERIMENT-ONLY-NOT-AN-APPROVAL`，不填任何真人姓名。
      判据三条：`verdict-tool-untouched` → **`success`**；日志逐字含 `本次改动触及判定器：`
      **和** `✅ 找到人工批准 trailer，放行`；**且不得**出现 `✅ 未触及判定器`
      （出现它说明走的是另一条出口，这条实验作废）。同时核对 `gates-l1` 仍 `success`。
      逐字记录：run id、job id、conclusion、命中的日志行。
      - Skill: `none`
- [ ] `Proof` **清理实验提交，并给「清理干净」配机械判据**（不是一句叮嘱）：
      · `git reset --hard <Phase 2 结束时的 sha>` 后 `git push --force-with-lease`；
      · `git rev-parse ci/1206-1-verdict-guard-proof` → 期望**逐字等于** Phase 2 结束时那个 sha；
      · `git diff --numstat "$CUT" ci/1206-1-verdict-guard-proof`
        → 期望**仍恰好一行** `118	0	.github/workflows/gates.yml`
        （**锚 `$CUT`，不用 `git merge-base main …`**：Phase 4 会推 `main`，浮动锚会让这条判据因与实验无关的原因失败）；
      · `git diff --numstat "$CUT" ci/1206-1-verdict-guard-proof -- tools/gates/check_expected_red.py tools/gates/expected-red.txt`
        → 期望**输出为空**；
      · `git log --format=%B "$CUT"..ci/1206-1-verdict-guard-proof | grep -c '^Gates-Change-Approved-By:'` → 期望 `0`
        （实验 ④ 的 trailer 已随 reset 消失）。
      · `gh pr view <新 PR 号> --json changedFiles,additions,deletions` → 期望**仍是** `1 / 118 / 0`
        （`baseRefOid` 钉死在 `$CUT` 不漂移，这是硬判据，无豁免）；
      · `gh pr view <新 PR 号> --json baseRefOid` → 期望**仍逐字等于 `$CUT`**（复核 C5 那颗钉子没松）。
      - Skill: `none`
- [ ] `Proof` **确认「清理后的 head 上有一次全绿」**。
      **先看清一件事，别白等**：`git reset --hard <Phase 2 sha>` + force-push 之后，PR head sha
      与 Phase 2 那次运行的 head sha **完全相同**，因此 **Phase 2 那次运行本身就是「清理后 head 上的绿」**，
      force-push 到一个已跑过的 sha **可能不产生新的 run id**。
      判据因此写成：`gh pr view <新 PR 号> --json headRefOid` 的值 == Phase 2 那次 run 的 head sha，
      （⚠️ 第 5 轮改准：此处此前写的是 `gh pr view 1`，是换载体前的残留——问的必须是**新 PR**，不是 PR #1）
      且该 sha 上存在一次全绿运行（**引用 Phase 2 的 run id 即可，不必制造新的**）。
      只有在 head sha 与 Phase 2 不一致时才需要重新跑一次并记新 run id。
      - Skill: `none`
- [ ] `Proof` **覆盖面限定，逐字写死（不得被读成「守卫已全面实证」）**：四条实验全在 PR 分支上做，
      因此**只证明了 `pull_request` 那条 `BASE`/`HEAD` 推导路径**（`base.sha` / `head.sha`）。
      `gates.yml` 的 `on: push` 限定 `branches: [main]`，所以 `push` 那条路径
      （`github.event.before` / `github.sha`，以及全零 sha 那个「首次推送」提前 `exit 0` 分支）
      **在合并前无法实测**——它归本批第二个 plan 的 `main` push 运行，而全零 sha 那个分支
      **在 `main` 上永远不会命中**，属于本 plan 与后继 plan 都覆盖不到的残余面，登记进 `## Deferred But Adjudicated`。
      - Skill: `none`

Exit Criteria:

- [ ] **四次**实验各有 run id、job id、conclusion 逐字在 plan 里，结果分别为
      `failure` / `success` / `success` / `success`（③ 附 `expected-red-ratchet` 的 `success`；
      ④ 附日志逐字 `✅ 找到人工批准 trailer，放行` 且**不含** `✅ 未触及判定器`）
- [ ] 实验 ① 按「预期红」三条判据全中（**七个点名 job 全绿 + 守卫 `failure`** + 两条日志原文 + head sha 对得上）
- [ ] 每条实验开跑前的两条隔离预检（提交数 / trailer 计数）均为期望值
- [ ] 实验提交已清理，清理项那五条机械判据全部为期望值
- [ ] 清理后的 head 上存在一次全绿运行（引用 Phase 2 的 run id 即可，head sha 已核对一致）
- [ ] **截至本阶段结束**，CI 运行次数未超过声明的 **12 次**预算（**这是一个滚动计数，不是终值**——
      Phase 4 那次 `main` 收尾推送也计入同一份预算，终值判据在 Phase 4 的 Exit Criteria）
- [ ] 覆盖面限定已逐字写进**本 plan**（写进 `system-baseline.md` §14.4 归 Phase 4，不在本阶段 Targets 里）
- [ ] `docs/logs/2026/08-22.md` 已追加本阶段记录

### Phase 4 — 留痕与收尾自查

Status: planned
Targets: `docs/architecture/system-baseline.md`（§14.4，**追加**）·
  `docs/plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md`（**只在 `Closure Audit Log` 追加一行**）·
  `docs/logs/2026/08-22.md` · `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Fix | Proof`
- Prereqs: Phase 3 完成

- [ ] `Fix` **本阶段第一件事：`git switch main`**。Phase 3 结束时工作树在 `ci/1206-1-verdict-guard-proof` 上，
      不切回去的话本阶段那条 `git diff <开工 sha>..HEAD -- .github/workflows/` 会读出 `+118` 而误判成红线 2 违规。
      - Skill: `none`
- [ ] `Fix` **§14.4 补上守卫的实证结论**：**四条**实验的 run id 与结论、以及 Phase 3 末项那句**覆盖面限定**。
      写法约束：**绝不能写成比证据更强的说法**——**四句分开写，与 `## Closure Gates` 那一框逐条对齐**：
      ① `pull_request` 路径的四条出口里三条已实证（未触及 / 触及无 trailer 必红 / 触及带 trailer 放行）；
      ② `push` 路径未实证；③ 全零 sha 分支永不可测；④ 守卫体内 `|| true` 的假阴入口已登记且**本批新引入**。
      - Skill: `none`
- [ ] `Fix` **在 plan `2026-08-22-0027-2` 的 `Closure Audit Log` 末尾追加一行**：
      本 plan 已还上它 Phase 2 那一项欠账（**四条**实验的 run id —— `0027-2` 原文只要求三条，本 plan 多补了「触及 + 带 trailer 放行」那条出口，**多给不算少给**），**其 Phase 3「把前驱两条 Deferred 记为了结」仍欠着，归本批第二个 plan**。
      ⚠️ **红线纪律**：只追加，**不改写它任何已有行**，**不改它的 `Plan Status`**，**不勾它任何一个 `[ ]`**——
      它欠的 19 个 `[ ]` 里，本 plan 只让其中「守卫实证」那一项在**本 plan 里**成立，
      代它打勾等于伪造它的关闭证据（它自己三次关闭审计都拒绝过这件事）。
      - Skill: `none`
- [ ] `Proof` **收尾复跑（本机，用开工 sha `$CUT` 作基线，不用裸 `git diff`）**：
      · `python3 tools/gates/check_expected_red.py` → 期望 exit 0（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`），
        **且与 Phase 2 记下的「前」输出逐字节相同**（存两份文件 `diff` 一次，期望无输出——G2 第三条的「后」那半）；
      · `python3 -m pytest tests/unit -q` → 期望 exit 0；
      · `python3 -m pytest tests/contracts -q` → 期望 exit 0；
      · `ruff check agenerp tests/unit tests/contracts` → 期望 exit 0。
      - Skill: `none`
- [ ] `Proof` **红线自查（机械可核，输出逐字抄进 plan）**：
      ⚠️ **第 5 轮改准，锚点从写死的 `aba9a5f` 换成 `$CUT`（= 开工那一刻的 `main` sha，实测 `4d7b311…`）**。
      原因不是措辞：`aba9a5f` 已被 `main` 甩在身后两个提交，实测
      `git diff --stat aba9a5f..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates`
      → **非空**（`tools/gates/budget.json` / `tools/gates/check_budget.py`，来自与本 plan 无关的 `6288666`）。
      照原文执行，这条红线自查会**因为别人的提交**而失败，把一次干净的收尾误判成红线违规。
      · `git diff --stat "$CUT"..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` → 期望**输出为空**；
      · `git status --porcelain -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates` → 期望**输出为空**
        （两条一起才覆盖「已提交」与「未提交」两种情形）；
      · `git diff "$CUT"..HEAD -- .github/workflows/` → 期望**输出为空**（本 plan 对 `main` 的 workflow **零改动**，改动只在分支上）；
      · `git diff "$CUT"..HEAD -- docs/masterplan/STATE.md | grep '^-' | grep -v '^---'` → 期望**输出为空**（STATE 只追加）。
      - Skill: `none`
- [ ] `Proof` 全部命令原文 + 退出码 + commit sha 写进 `docs/logs/2026/08-22.md` 与 `STATE.md` §2（**只追加**）。
      - Skill: `none`
- [ ] `Fix` **本阶段的文档提交推到 `origin/main`，让 `origin/main == main` 收尾**。
      **理由**：安全窗口（`main` 上还没有守卫）在本 plan 期间一直开着，此刻推是安全的；
      留到本批第二个 plan 再推，就要和守卫落地那一推抢时序。
      推前跑 Phase 1 那**同一组四条预检**（workflow / 裁判与账本 / `DECISIONS.md` / `STATE.md` 只追加）。
      记录那次 `main` push 运行的 run id 与全部 job 结论。
      ⚠️ **收尾判据不是「`git rev-parse main origin/main` 两值相等」，第 4 轮评审已改准，原因必须写下来**：
      本 plan 置 `completed` 还需要一次**独立关闭审计的回填提交**（`## Closure` 段 + `Closure Gates` 打勾，
      本仓每个 plan 都这么收尾，最近一例是 `aba9a5f docs(p0-foundation): plan-1041-1 独立关闭审计回填`）。
      那次回填**必然发生在本次推送之后**，于是「两值相等」在**姊妹 plan 开工那一刻必然为假**——
      而姊妹 plan 的 Phase 1 预检 ⑥ 原本拿它当停机闸，**两个 plan 会在这里死锁**。
      **改准后的收尾判据（与姊妹 plan 预检 ⑥ 逐字一致，两边必须同时改）**：
      · `git merge-base --is-ancestor origin/main main` → **成立**；
      · `git diff --name-only origin/main main` → 输出**只含** `docs/logs/**` 与 `docs/plans/p0-foundation/**`
        （即只剩文档提交，没有 workflow、判定器、账本、`tests/gates`、`agenerp` 的任何改动）。
      **这两条在「回填提交已落地」与「尚未落地」两种状态下都成立**，因此不会死锁；
      而它对姊妹 plan 真正需要的东西（`main` 是分支的祖先、`main` 上没有意外改动）保护力**不低于**原判据。
      - Skill: `none`

Exit Criteria:

- [ ] §14.4 有守卫的**四条**实证结论与覆盖面限定，且没有写成比证据更强的说法
- [ ] `2026-08-22-0027-2` 只被追加了一行，`git diff` 对它的 `Plan Status` 与 `[ ]` 计数为零变化
      （判据：`grep -c '^\s*-\s\[ \]' <该文件>` 仍为 `19`）
- [ ] 四条本机验证命令均 exit 0，输出逐字入 plan
- [ ] 判定器默认环境输出的「前 / 后」两次实跑已逐字入 plan 且**逐字节相同**（Protected Areas Required Evidence，G2 第三条）
- [ ] 红线自查四条输出均为期望值
- [ ] `docs/logs/2026/08-22.md` 与 `STATE.md` §2 各有对应记录（STATE 只追加）
- [ ] 收尾推送已执行，推前四条预检输出为期望值，那次 `main` push 运行的 run id 与全部 job 结论逐字入 plan
- [ ] **收尾收敛判据成立（取代原来那条会与姊妹 plan 死锁的「两值相等」）**：
      `git merge-base --is-ancestor origin/main main` 成立，且 `git diff --name-only origin/main main`
      只含 `docs/logs/**` 与 `docs/plans/p0-foundation/**`
- [ ] **CI 运行次数终值未超过声明的 12 次预算**（全 plan 累计，含本阶段两次 `main` push 运行）

## Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理，fresh session，2026-08-22）。
  **推翻了本 plan 的一条中心事实**：起草时写的「PR #1 按现状合并会回退 3455 行」是**两点式误读**——
  合并用的是 merge-base，实测 `git merge-base main origin/ci/…` → `77addbb`，
  `git diff --numstat 77addbb origin/ci/…` 只有三行且**零删除**，`agenerp/` 两处内容已在 `main` 上，
  **合并 PR #1 删不掉任何东西**。据此改准的有：Baseline C 全节重写、Goals 2 重新定性
  （从「消除合并风险」改成「追平 `main` 以让 CI 跑对代码 + 让 ff-only 成为可能」）、Phase 1 `Decision` 的理由与备选重写。
  其余 blocking 逐条落地：`git status` 实测是 2 行不是 0；所有两点式 `main..分支` 判据改成 merge-base 形式；
  Phase 1 增加「追加提交不得带 `Gates-Change-Approved-By:`」硬约束与 trailer 洁净度预检；
  新增**实验 ④**（守卫「触及 + 带 trailer 放行」这条出口原本四条实验一次都走不到）；
  新增**实验隔离纪律**（守卫比累积区间，实验叠罗汉会让 ③④ 失去解释力）与 ② 红时的写死分支；
  「预期红」定义从「job 集合」加严成三条并列（集合 + 两条日志原文 + head sha）。
  nit 也已落地：清理后不必制造新 run（head sha 与 Phase 2 相同）、CI 运行预算 7 次并写明超出即停、
  逐字比对改为对着保命闸存下的文件而非 `origin/…@{1}` reflog、Non-Goals 的「不落 `main`」改成
  「不把两个 job 落进 `main` 的 `gates.yml`」并写明 Phase 4 那次 `main` push 不构成守卫 `push` 路径实测。
- **Independent draft review iteration 2（针对姊妹 plan，结论回灌本 plan）：`needs revision`**（另一独立子代理，fresh session，2026-08-22）。
  它实测发现一条**时序约束**，直接改变了本 plan Phase 1 的动作序列：本地 `main` 领先 `origin/main` **10 个提交**
  （`git rev-parse main origin/main` → `aba9a5f` / `508c75b`），其中 `57ad6d5` 改了判定器且**不带 trailer**
  （`git log --format=%B 508c75b..aba9a5f | grep -c '^Gates-Change-Approved-By:'` → `0`）。
  **守卫一旦落进 `main`，再推这 10 个提交就必然红。** 因此本 plan 新增「趁 `main` 上还没有守卫，先把 `origin/main` 追平」
  这个 `Decision`（带两条推前预检与安全窗口论证），并在 Phase 4 收尾时再推一次，使 `git rev-parse main origin/main` 相等。
  同一轮还回灌了：守卫体内 `|| true` 的假阴入口登记为 Deferred（继承自既有 `gates-untouched`，非本批引入）；
  Protected Areas 那处措辞不一致补上该表**前言**的逐字反证与先例的机械出处（`git log -S 'gates-l2:'` → `6ac1005`）。
- **Independent draft review iteration 3: `needs revision`**（第三个独立子代理，fresh session，2026-08-22）。
  它复核确认 Baseline A/A3/B/C1–C4/D/E/F/G **逐条实测为真**、round-1 的修订确实落地，
  但抓出修订自己引入的新矛盾与残留，12 条 blocking 全部落地：
  ① **隔离纪律对实验 ② 逻辑上不可能** —— ② 的动作就是 revert ①，先 reset 就没有 revert 对象。
  已改成「①→② 是唯一允许叠加的一对，③④ 各自 reset 回 Phase 2 sha」，并把每条实验的期望提交数
  逐字写死（①=2 / ②=3 / ③=2 / ④=2），此前那句「该实验声明的提交数」根本没处可查。
  ② Baseline A3 ② 把 Phase 1 明确否掉的备选当成事实在陈述，已改准。
  ③ 回滚策略仍写着「本 plan 对 `main` 零改动」，而修订后本 plan 要推两次 `main`。
  已拆成分支面（可回滚）与 `main` 面（**不可回滚，靠推前预检**）两条。
  ④ 7 次 CI 预算漏算 Phase 4 那次 `main` 推与隔离纪律的三次 reset 推送，已重新逐项枚举为**上限 12 次**，
  并拒绝「reset 到已跑过的 sha 不另计」这种没实测过的假设。
  ⑤ **最有价值的一条**：守卫**已经活在 PR 分支上**，而 `pull_request` 的 `BASE` 取的是 base 分支 tip。
  若先刷分支后推 `main`，`BASE=508c75b`，区间含无 trailer 的 `57ad6d5` → **守卫当场红，Phase 2 的基线绿根本拿不到**。
  已把「先推 `main`、再刷分支」写成 Phase 1 `Decision` 的**理由三**与硬约束。
  ⑥ 预期红 / 真红 两个定义不互补，「只有守卫红但 head sha 不是实验 ① 的」那一格两边都落不进去——
  而那正是 plan 自己预判会发生的情形。已改成「凡不满足预期红三条的任何一次红，一律按真红计」。
  ⑦ 预期红条件 (a) 让实验 ① 被 `gates-l2-live` 的已知间歇性绑架。已把 (a) 改成点名**七个**稳定 job 全绿
  （`gates-l1` / `gates-untouched` / `expected-red-ratchet` / `masterplan-links` / `roadmap-parseable` / `loop-wiring` / `gates-l2`；
  此处第 3 轮记的「六个」是笔误，第 4 轮改准，plan 正文一直是七个），
  `gates-l2-live` 单开一格：复跑一次、不参与实验判定、但照常计入真红。
  ⑧ 实验 ④ 要 loop 自签批准 trailer，与 Phase 1 备选 (b)「loop 不得自签」直接冲突。
  已划清界线并把姓名字段逐字定为 `EXPERIMENT-ONLY-NOT-AN-APPROVAL`。
  ⑨ Protected Areas 有一条 `plan-first` 专门管判定器本体，而实验 ①④ 正好碰它，原 plan 只字未提。
  已新增 Baseline **G2** 逐条对齐四项 Required Evidence（含在 Phase 2 补一次「前」的判定基线实跑，
  以及「判定器自身的变异验证」按不适用**写明理由**而不是略过）。
  ⑩ Phase 1 那次 `main` push 没有红处置分支，已补上与 Phase 2 同一套。
  ⑪ 加了实验 ④ 之后「三次实验」在九处残留，其中两处正是写 owner doc 的那一项，照抄会把 ④ 漏记进 §14.4。已全部改准。
  ⑫ 两处 ⚠️ 豁免（「`gh pr view` 读数更大也不算失败」）在 Phase 1 推 `main` 之后变成假的，
  且会架空姊妹 plan 的硬闸。已删除并改写成硬判据。
  nit 也已落地：`main..HEAD` 那处两点式 diff 记法改准并写清 `git diff A B` 是 tip-to-tip、`A...B` 才是 merge-base；
  两点式禁令收窄为只针对 `git diff`（`git log` 的区间形式本就等价）；重复的 `Skill: none`、
  force-push 的 `Decision` 交叉引用（Phase 2 → Phase 1）、Phase 2 的 Targets 自相矛盾、
  机械判据条数不一致、Phase 4 缺 `git switch main`、实验 ③ 与 `|| true` 假阴同打一行日志的去混淆说明。
- **Independent draft review iteration 4: `needs revision`**（第四个独立子代理，fresh session，2026-08-22）。
  它复核确认 Baseline A/A3/B/C1/C3/C4/D/E1/F/G/G2 **逐条实测仍为真**、Rule 12 grep 干净、
  Anti-Slacking 禁用词零命中、四个 Deferred 各有重开事件、无一步触碰红线 1/2/3/5/6/7。
  但**推翻了本 plan 的实验载体设计**，7 条 blocking 全部落地：
  ① **中心事实被证伪**：`pull_request` 的 `BASE` **不**取 base 分支 tip，它在 **PR 创建时钉死**。
  实测 `gh pr view 1 --json baseRefOid` → `7b0f585`，而彼时 `origin/main` 已是 `508c75b`；
  run `32533449466` 那次 `synchronize` 发生在 `origin/main` 前进 **37 分钟之后**，`base.sha` 仍是 `7b0f585`；
  本仓 `STATE.md:81` 早就记着这个值，起草时没读。**后果**：原设计（force-push PR #1 的分支到 `main`+append）
  会让守卫算 `git diff 7b0f585 aba9a5f` → 命中判定器、trailer `0` → **守卫恒红且与实验载荷无关**，
  Phase 2 基线绿拿不到、实验 ②③ 拿不到、实验 ① 失去全部鉴别力。
  已新增 Baseline **C5 / C5.1 / C5.2 / C5.3 / C5.4** 五节，并把实验载体整体改成
  **新分支 `ci/1206-1-verdict-guard-proof` + 新 PR**（`base.sha` 在创建时等于当时的 `origin/main`，
  故「先推 `main` 再建 PR」的顺序约束**保留但换了论据**）；PR #1 全程不动，新增备选 (d)(e) 与两条残余风险。
  ② Baseline C2 一句话里两处事实错误（基不是 `508c75b` 而是 `7b0f585`；`508c75b` 比本地 merge-base **新**不是旧）。已改准。
  ③ `1 / 118 / 0` 那条「硬判据」在原设计下必然读出约 `25 / +3870 / −281`（GitHub 按 `base.sha` 算），
  而姊妹 plan 的预检 ③ 拿它当硬闸 → 两个 plan 一起卡死。已随载体改换修复，并补上**最承重的新判据 `baseRefOid == $CUT`**。
  ④ Phase 1 三条 Exit Criteria **互相不可同时满足**（日志按「全程硬规矩」提到 `main` 上 → `main` 前进 → 前两条同时为假）。
  已整组改锚到 `$CUT` 与「祖先 + 只含文档」。
  ⑤ Closure Gate 的「实验 ① 红 job 集合**恰好是** `{verdict-tool-untouched}`」与停机纪律给 `gates-l2-live` 开的豁免格直接打架。已改成二选一形式。
  ⑥ `|| true` 那条 Deferred 的**理由是假的**：这处 `|| true` 在**新**守卫体内（属那 118 行），**本批新引入**，
  不是继承；且前缀自查只覆盖前 190 行，改它**不可能**打掉它。已换成唯一成立的理由（改它会让那 118 行与已实测那份不再逐字一致）。
  ⑦ **跨 plan 死锁**：本 plan 收尾判据「`git rev-parse main origin/main` 两值相等」与姊妹 plan 预检 ⑥ 同形，
  而本 plan 置 `completed` 还需一次关闭审计回填提交，必然发生在推送之后 → 姊妹 plan 开工即停机。
  已在两个 plan 里同步改成「`is-ancestor` + `git diff --name-only` 只含文档」。
  nit 也已落地：Draft Review Record 的「六个稳定 job」改准为七个；§14.4 的「三句」改成与 Closure Gate 对齐的四句；
  12 次预算判据说明是滚动计数、终值判据移到 Phase 4；G2 补全 Protected Areas 那行被截掉的
  「（改坏它必须让 `tests/unit` 红）」；推前预检从两条补到四条（补红线 3/5，此前只在两次推**之后**才自查）；
  实验 ④ 的「被 `reset` 抹掉」改准为「移出分支」（force-push 掉的提交按 sha 仍可访问）。
- **Independent draft review iteration 5: `accept`（改准后可执行）**（第五个独立子代理，fresh session，2026-08-22）。
  它按 `docs/plans/00-plan-authoring-and-execution-guide.md` 逐条核了格式、完整性、边界与关闭证据，
  并**在 `main` @ `4d7b311` 上重跑了 Current Baseline 的每一条**。
  **复测仍为真（读数逐字）**：
  · B —— `git show main:.github/workflows/gates.yml | sed -n '/^jobs:/,$p' | grep -E '^  [a-z0-9-]+:'` → 7 个 job 键，
    与 plan 所列一致；`grep -cE 'gates-l2-live|verdict-tool-untouched'` → `0`（退出码 1）；文件 190 行。
  · C1 —— `git merge-base main origin/ci/0027-2-l2-full-live-gate` → `77addbb`；
    该区间 `git diff --numstat` → 三行 `118 0 .github/workflows/gates.yml` / `32 0 agenerp/oob.py` / `8 1 agenerp/snapshot.py`；
    `git diff --numstat main origin/ci/… -- agenerp/` → 零输出。
  · C4 —— `git diff --numstat main origin/ci/… -- tools/gates/check_expected_red.py` → `7 42`（判定器仍已过期）；
    `-- tests/gates docker-compose.yml` → 零输出。
  · C5 —— `gh pr view 1 --json baseRefOid,headRefOid,state,changedFiles,additions,deletions`
    → `7b0f585f7c…` / `c2c688b7f6…` / `OPEN` / `6` / `417` / `17`，与 plan 逐字相符。
  · D —— `diff <(git show main:.github/workflows/gates.yml) <(git show origin/ci/…:.github/workflows/gates.yml | head -n 190)`
    → **无输出**；分支侧 308 行，差 118 行纯末尾追加。
  · E1 / Phase 4 判据 —— `grep -c '^\s*-\s\[ \]' 0027-2` → `19`，`Plan Status: deferred`，`Closure Audit Log` 段存在。
  · 守卫体 —— 把那 118 行取出来实读，plan 逐字引用的四条日志串
    （`✅ 未触及判定器` / `本次改动触及判定器：` / `✅ 找到人工批准 trailer，放行` / `❌ 改动了门禁判定器却没有人工批准。`）
    **全部存在**；`|| true` 确在**新** job 体内（证实第 4 轮对 Deferred 三的改准）；
    `expected-red-ratchet` 的 `count()` 为 `grep -vE '^\s*(#|$)' | wc -l`，**确认实验 ③ 加一行 `#` 注释不改变计数**；
    `gates-l1` 只跑 `python3 tools/gates/check_expected_red.py`，**确认实验 ①④ 的末尾空行语义无关**。
  · 判定器默认输出 —— `python3 tools/gates/check_expected_red.py` → exit 0，
    逐字 `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`（= Phase 2「前」基线的期望值，已核准）。
  · 规则自查 —— Rule 12 的 `grep -B5 "\- \[ \]" <plan> | grep "Status: completed"` **无输出**；
    Anti-Slacking 禁用词零命中；四个 Deferred 各有分类与重开事件。
  **本轮改准的 5 条 blocking（起因是同一件事：起草基线 `aba9a5f` 已过期）**：
  ① **Current Baseline A / A3 整节失效** —— 实测 `git rev-parse main origin/main` **两值相等**（均 `4d7b311`），
  `origin/main..main` → `0`，`git status --porcelain` → 空。那 10 个提交早已推上去，`main` 其后又落了
  `6288666` / `4d7b311` 两个提交。A / A3 已按实测重写并逐条列出后果。
  ② **Phase 4 红线自查会因别人的提交而误报**（本轮唯一一条会直接卡住执行的硬伤）：
  实测 `git diff --stat aba9a5f..HEAD -- … tools/gates` → **非空**（`budget.json` / `check_budget.py`，来自 `6288666`）。
  四条命令的锚点已全部从写死的 `aba9a5f` 换成 `$CUT`。
  ③ **Phase 1 第二个 `Decision` 要执行一次已经不存在的推送**。已降级为「核验 + 留痕」，
  保留 `base.sha` 的顺序硬约束与四条推前预检（只在真需要补推时跑），并把「安全窗口已被用掉且用对了」照实记下来。
  ④ **换载体后的三处残留会把执行带回被否掉的老设计**：Phase 1 标题「（PR #1 就地刷新）」、
  `Decision` 1 标题「刷新方式定死为『reset 到 `main` 再单提交 append』」、Phase 2 的「取得刷新后 **PR #1** 上的一次完整运行」
  与 Phase 3 清理项的 `gh pr view 1 --json headRefOid`。照它们执行就是备选 (d)，正是 C5.1 判死的那条路。四处已全部改准。
  ⑤ **两处判据/闸门会永远勾不上**：Phase 1 Exit Criteria 的「`origin/main` 已追平…… 那次 `main` push 运行的结论」
  与同形的 Closure Gate，都以一次 no-op 推送为前提。已改成「核验相等 → 逐字写明无 push 运行；不等才补推并记 run」。
  同批改准的还有：回滚策略「推两次」→「正常路径只推一次」、CI 预算枚举去掉「追平 1」（**总额 12 不变**，那一格并进机动）、
  C5.4 的「先把 `origin/main` 推到 `aba9a5f`」、C3 与 `Decision` 1 理由一的「落后 10 个提交」→ 实测 `21`、
  Phase 1 `Targets` 补上 `docs/logs/2026/08-22.md`（Exit Criteria 要求它但 Targets 漏列）。
  **结论**：载体设计（新分支 + 新 PR + 四条实验 + 隔离纪律）经复测**成立且未被本轮任何读数动摇**，
  Baseline 过期属锚点问题而非结构问题，已就地改准 → **`Plan Status` 置 `active`**。

## Closure Gates

- [ ] in-scope behavior is complete（**四条**实验证据齐 + 建 PR 前 `origin/main == main` 已核验 +
      新分支从 `main` 切出且新 PR 就绪 + `main` 基线上的 `gates-l2-live` 绿）
- [ ] relevant docs are aligned（`docs/architecture/system-baseline.md` §14.4 · `docs/logs/2026/08-22.md` · `STATE.md` §2）
- [ ] verification has run：**四条**实验的 run id 与 job 结论逐字 · Phase 2 的全绿运行 run id 逐字
      （Phase 3 清理后 head sha 与之相同，**同一个 run id 即可**；head sha 不同时才另记一条）·
      本机四条命令 exit 0
- [ ] **守卫的覆盖面限定已逐字落地**：`pull_request` 路径的**四条出口里三条**（未触及 / 触及无 trailer 必红 / 触及带 trailer 放行）已实证 /
      `push` 路径未实证 / 全零 sha 分支永不可测 / `|| true` 假阴入口已登记**且写明是本批新引入而非继承**，四句分开
- [ ] **安全窗口论证与两条 `main` 面留痕已落地**（⚠️ 第 5 轮改准：此前这一框要求「`origin/main` 追平那一推」的
      预检与 run 结论，而 A3 实测那一推已是 no-op，该框原样保留会永远勾不上）：
      · 建 PR 前 `git rev-parse main origin/main` 两值相等（= `$CUT`）已逐字入 plan；
        若核验不等而补推，则那一推的**四条**预检输出与 run id + 全部 job 结论也逐字入 plan；
      · `main` 上此刻零 `verdict-tool-untouched`（安全窗口仍开着）已逐字入 plan；
      · Phase 4 收尾那一推的**四条**预检（workflow / 裁判与账本 / `DECISIONS.md` / `STATE.md` 只追加）
        输出为期望值，且那次 `main` push 运行的 run id 与全部 job 结论逐字入 plan
- [ ] **实验载体是本 plan 新建的分支与新 PR，PR #1 一个字节未动**：新 PR 的 `baseRefOid` 逐字等于 `$CUT`，
      PR #1 的 `state` / `headRefOid` / `baseRefOid` 与开工时相同
- [ ] **预期红与真红的区分已按「停机纪律」执行**：实验 ① 的红 job 集合是 `{verdict-tool-untouched}`，
      **或** `{verdict-tool-untouched, gates-l2-live}` 且后者已按停机纪律**原样复跑一次**并**照常计入真红计数**
      （**这两种都算实验 ① 成立**——停机纪律给 `gates-l2-live` 单开了一格，本 gate 此前写「恰好是」与它直接打架，
      第 4 轮评审改准）；且没有把任何真红计成实验红
- [ ] 实验提交已清理，清理项那五条机械判据为期望值；`tools/gates/check_expected_red.py` 与 `expected-red.txt` 的净 diff 为空
- [ ] `main` 上 `.github/workflows/**` 一行未改（本 plan 的 workflow 改动只在分支上；`main` 只收到文档提交）
- [ ] `2026-08-22-0027-2` 未被改写：`Plan Status` 仍 `deferred`，`[ ]` 计数仍为 `19`，只多了一行 `Closure Audit Log`
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件，本 plan 的证据面是
      「CI 上两个 job 的结论 + 本机四条命令」，**不得报成「全量验证通过」**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] 判定器默认环境输出的「前 / 后」两次实跑已逐字入 plan 且逐字节相同（Protected Areas Required Evidence）
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### 守卫的 `push` BASE/HEAD 路径未实证

- Classification: `watch-only residual`
- Why Not Blocking Closure: `gates.yml` 的 `on: push` 限定 `branches: [main]`，在 PR 分支上**物理上跑不到**这条路径。
  本 plan 的四条实验只覆盖 `pull_request`，这已是分支上能取到的最大覆盖面。
- Successor Required: `yes` —— 本批第二个 plan `2026-08-22-1206-2` 把守卫落地到 `main` 之后，
  那次 push 运行**就是** `push` 路径的第一次实测，由它承接。
  ⚠️ **本 plan Phase 1/Phase 4 那两次 `main` push 不算**：那时 `main` 上还没有这个 job。

### 守卫的「首次推送（全零 sha）」提前 `exit 0` 分支永远不可实测

- Classification: `watch-only residual`
- Why Not Blocking Closure: 该分支只在**新分支首次 push** 时命中，而守卫的 `push` 触发被限定在 `branches: [main]`，
  `main` 不会有「首次推送」。它是从 `gates-untouched` 同构抄来的死代码路径，**不是本 plan 引入的**。
- Successor Required: `no` —— 但它是「守卫假阴」的理论入口，已在 §14.4 记名。
  重开事件：**若将来有人把 `on: push` 的 `branches` 放宽到 `main` 以外**，这条分支立刻变成可命中且不可见，
  届时必须补一条实证。

### 守卫脚本吞掉 `git diff` 的错误（`|| true`），存在假阴入口

- Classification: `watch-only residual`
- Why Not Blocking Closure: 守卫体内逐字为
  `CHANGED=$(git diff --name-only "$BASE" "$HEAD" -- 'tools/gates/check_expected_red.py' 'tools/gates/gate-verify.mjs' || true)`。
  `git diff` 出错（`BASE` 取不到、`fetch-depth` 回归）时 `CHANGED` 为空 → 走 `✅ 未触及判定器` 并 `exit 0`，
  **是一个真实的假阴入口**。
  ⚠️ **本条的理由在独立评审第 4 轮被推翻并重写，旧理由是假的**：此前写的是
  「它是继承来的，不是本批引入的……改它等于改一个已在 `main` 上运行的既有 job 的脚本体，会打掉本仓已固化的「行前缀」自查判据」。
  **两句都不成立**：① 这一处 `|| true` 在**新** `verdict-tool-untouched` job 体内，属于那 118 行追加内容
  （分支文件第 191–308 行），**是本批新引入的**，不是继承的——同款写法确实也存在于既有 `gates-untouched`（第 36 行），
  但那是**另一处**，本条说的不是它；② 前缀性自查是
  `diff <(git show main:.github/workflows/gates.yml) <(head -n 190 …)`，**只覆盖前 190 行**，
  改第 190 行之后的任何内容**都不可能**打掉它（实测 `git show main:…| wc -l` → `190`）。
  **真正的、成立的理由只有一条**：修它会让那 118 行与 run `32533449466` 上跑过的那一份**不再逐字一致**，
  而「落地的就是已实测那一份」是本批两个 plan 共同的承重判据（Goals 2 / Phase 1 保命闸 / 姊妹 plan 的 ff-only 论证）。
  **本批因此选择「带着这个已知假阴入口落地」，并把这个选择明写出来，而不是假装它是继承来的。**
- Successor Required: `no`（**修它要重新取一次全套 CI 证据，且改既有 job 的脚本体需要人批**）——
  重开事件：**人裁定统一修这两处**，或**守卫出现一次已知的假阴**（表现为：判定器被改了而守卫仍绿）。

### `ai-autonomy-policy.md` 里 `.github/workflows/** = blocked` 与红线 2「只禁变松」的措辞不一致

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: 这条不一致已由 plan `2026-08-22-0027-2` 登记为人动作 Deferred，至今未裁。
  本 plan 沿用**已在 `main` 上落地的先例**（plan `2026-08-21-2220-2` 以「纯追加 = 加严」的读法把 `gates-l2` 加进了 `main`），
  且本 plan 对 `main` 的 workflow **零改动**（只动分支），受这处不一致影响的面比先例更小。
- Successor Required: `no`（**改 Protected Areas 的 Rule 列等于替人定授权口径，loop 不做**）——
  重开事件：**人给出裁定**，或**下一个要动 `main` 上 `gates.yml` 的 plan 开工前**（即本批第二个 plan，
  它必须在 Phase 1 里把这条重新摆到台面上，不得默认继承）。

## Closure

Status Note: <待关闭时填写>

Closure Audit Evidence:

- Auditor / Agent: <independent auditor or independent subagent>
- Evidence: <task id / log link / walkthrough record>
