# 2026-08-23-0859-1 停机闸自己没有判据 —— 给 `check_budget.py` / `pass_usage.py` 补判据，并修「崩溃冒充超预算」

> Plan Status: active
> Mission: p0-foundation
> Work Item: 工作项 9 · L2 门禁的判定与 CI 覆盖（**判据设施**那一半 —— 本 plan 不改工作项 9 的 `done` 判据，也不改任何工作项的状态值）
> Last Reviewed: 2026-08-23
> Source: 实测覆盖率取证 —— `tools/gates/check_budget.py` 与 `tools/gates/pass_usage.py` 判据覆盖 **0%**，
> 且由此暴露出一条**确认的活缺陷**（台账里一行不带时区的时间戳会让停机闸崩溃，而崩溃的退出码 1 被监督器逐字翻译成「超预算」）
> Related: `2026-08-23-0120-1-ci-unit-and-contracts-coverage.md`（`unit-and-contracts` job —— 本 plan 新增的测试**靠它**自动获得 CI 覆盖，因此本 plan 不动 `.github/workflows/**`）·
> `2026-08-22-0027-1-live-mode-gate-verdict.md`（判定器本体的加严先例：判据设施本身也要有判据）·
> `2026-08-23-0859-2-ruff-force-exclude-guards-the-judges.md`（本批第二个 plan，**已按独立评审的结论大幅收窄**：
> 它只补 `pyproject.toml` 的 `force-exclude`，**不再**接手 `tools/**` 的 lint 扩面）·
> `2026-08-22-0228-1-gate-verdict-failure-forensics.md`（其评审记录 **M2 已裁定「明确不扩面」** —— 见 Baseline 13）
> Audit: required
> 执行顺序：**1 / 2**。两个 plan 的改动面在收窄之后**不再重叠**（`-2` 只动 `pyproject.toml`），
> 但顺序仍保留：`-2` 的 Baseline 要实读 `ruff check tools` 的命中数，而本 plan 会**改变**那个数
> —— 本 plan 新增的 `except … as exc:` 分支与提示语很可能**新增**若干 `F541` / `E501` 命中。
> ⚠️ **`-2` 开工时必须重新实读，不得照抄任何计数。**

## Current Baseline

全部为 2026-08-23 在 `main`（`6001ea0ae15cf3c84cc1bca19f138a738a50a7fc`）上的实读与实跑。
工作树在取证时干净（`git status --porcelain` 无输出）。

1. **停机闸的位置与它的退出码契约**。`tools/loop-supervisor.sh` 的模块头逐字写着五道闸，
   闸 2 是日预算；`cd "$ROOT"` 在文件开头（所以产品路径上 cwd 恒为仓库根）。闸 2 的调用逐字是：

   ```
   python3 tools/gates/check_budget.py
   case $? in
     1) halt_with "budget-exceeded" "24 小时内循环用量超出预算，停机等人复核"; exit 0 ;;
     2) log "预算：台账暂无记录（首趟），放行" ;;
   esac
   ```

   **退出码 1 是这条 7×24 循环唯一的成本停机入口**；退出码 2 是「放行」。
   闸 4 用 `pass_usage.py snapshot` / `measure` 把每一趟的用量写进台账 `_tmp/loop-usage.jsonl`，
   闸 2 读的就是它。**两个脚本是一条链：measure 写，check_budget 判。**

2. **这条链上零判据**。实测：

   ```
   python3 -m coverage run --source=agenerp,tools/gates -m pytest tests/unit tests/contracts -q   # 444 passed
   python3 -m coverage report --sort=miss
   ```

   → `tools/gates/check_budget.py` **59 stmts / 59 miss / 0%**、
   `tools/gates/pass_usage.py` **50 stmts / 50 miss / 0%**。
   **这两个是本仓仅有的两个 0%**，其余每一个被测模块都在 84%–100% 之间
   （`agenerp/oob.py` 87%、`check_expected_red.py` 84%、`agenerp/seedsite.py` 94%、`agenerp/tools_readonly.py` 100% …）。
   ⚠️ **覆盖率在本 plan 里只是发现问题的工具，不是判据**（判据是下面点名的那些行为各有一条断言）。

3. **确认的活缺陷（已复现，不是推理）**：台账里一行 `at` 不带时区，停机闸**崩溃**。
   在 `/tmp` 的干净沙箱里复现（只拷了脚本，没有动仓库）：

   ```
   printf '{"at": "2026-08-23T00:00:00", "label": "x", "sessions": 1, "input": 5, "output": 1, "msgs": 1}\n' > _tmp/loop-usage.jsonl
   python3 tools/gates/check_budget.py
   ```

   → 逐字 `TypeError: can't compare offset-naive and offset-aware datetimes`
   （抛在 `usage_since` 的 `if t < start:`），**未被捕获**，进程 **exit 1**。
   `usage_since` 的 `except (ValueError, KeyError): continue` 明写着「畸形行跳过」的意图，**这一类畸形逃出了它**。

4. **缺陷的后果是「说谎」，不是「多停一次」**。exit 1 在监督器里被逐字翻译成
   `halt_with "budget-exceeded" "24 小时内循环用量超出预算，停机等人复核"` ——
   **人第二天早上看到的停机记录会说「烧超了」，而真相是判定器自己崩了**。
   `AGENTS.md` 裁判规则 2 要求「宣称完成时必须有命令原文 + 退出码」，
   这条缺陷破坏的正是对称的那一半：**退出码不再唯一对应一件事**。

5. **已知触发面照实记，不夸大**：`pass_usage.py` 现在写的 `at` 是
   `datetime.datetime.now(datetime.UTC).isoformat()`，**带时区**，因此**产品路径上目前没有已知的活触发点**。
   触发面是：人手工编辑/拼接台账、别的产出方往台账里追加、或将来改写 `measure` 的时间戳写法。
   ⚠️ **「目前没触发」不等于「不是缺陷」**：这是一条判定器内部的未捕获异常，
   按 `docs/plans/00-plan-authoring-and-execution-guide.md` Minimum Rule 14，**确认的活缺陷不得降级为 follow-up**。

6. **阈值真相源在非仓根 cwd 下会给出第二个读数**。`check_budget.py` 的
   `CONFIG = pathlib.Path("tools/gates/budget.json")` 是 **cwd 相对**；
   `configured_budget()` 的 `except Exception: return DEFAULT_BUDGET` 是**静默兜底**。
   产品路径安全（监督器 `cd "$ROOT"`），**但人手工在别的目录下跑就读到内置默认 2 亿**，
   而 `tools/gates/budget.json` 现值是 **10 亿**。
   ⚠️ 这**逐字就是** `docs/masterplan/STATE.md:86` 记的那次事故
   （「同一个判定器给出两个答案 …… 人哪天手工查一眼看到「超预算」会以为循环该停了」），
   当时的修法只补了「配置文件作为唯一真相源」这一半，**路径解析那一半没补**。
   该文件自己的 docstring 与 `budget.json` 的 `_why_here` 都把「不能有两个读数」写成了它存在的理由。

7. **环境变量的静默兜底同向**。`configured_budget()` 只在 `env.isdigit()` 为真时采信环境变量；
   `AGENERP_DAILY_TOKEN_BUDGET="200,000,000"` 这类写法 `isdigit()` 为假 → **静默落到文件的 10 亿**，
   即**比操作者意图更松**，且没有任何输出提示它被忽略了。

8. **`pass_usage.py measure` 在快照文件缺失时会把全部历史会话记成「本趟」**。
   `before = set(snap.read_text().split("\n")) if snap.exists() else set()` ——
   快照不在 → `before` 空 → `current_files() - before` = 全部会话文件 → 台账被写进一个巨大的假数字，
   下一次 `check_budget` 就会据此停机。监督器里 snapshot 恒先于 measure，
   但 `tools/ab-run.sh:42` 的 snapshot 带 `2>/dev/null`，**失败是静默的**。

9. **授权面：本 plan 要动的文件都不在任何禁区内**（逐条实读，不推断）：
   - `docs/context/ai-autonomy-policy.md` 的 Protected Areas 表里**没有** `tools/gates/check_budget.py`、
     **没有** `tools/gates/pass_usage.py`、**没有** `tools/loop-supervisor.sh`；
     表里点名的 `tools/gates/**` 只有两项：`expected-red.txt`（`allowed（只能变短）`）与
     `check_expected_red.py`（`plan-first`）。**本 plan 一个字节都不动这两项。**
   - 服务端守卫 `verdict-tool-untouched` 的 pathspec 逐字只有
     `tools/gates/check_expected_red.py` 与 `tools/gates/gate-verify.mjs`，**不含**本 plan 要动的文件。
   - `tests/unit/**` **不是**红线 1 的裁判面（红线 1 只圈 `tests/gates/**`）；本 plan 新增测试落在 `tests/unit/`。
   - **红线 1 / 2 / 3 / 4 / 5 / 6 / 7 全部不触及**：不动 `tests/gates/**`、不动 `.github/workflows/**`、
     不动 `docs/masterplan/**`（`STATE.md` 只按既有惯例**追加**一行证据）、不动 `missions/**`、不动证据仓。

10. **新增测试自动获得 CI 覆盖，因此本 plan 零 CI 改动**。`gates.yml:389` 的 `unit-and-contracts` job
    分两步跑 `python3 -m pytest tests/unit -q` 与 `python3 -m pytest tests/contracts -q`。
    实测当前 `tests/unit` **293 passed**、`tests/contracts` **151 passed**。
    ⚠️ **CI 覆盖 ≠ 门禁形态 ≠ `GATE_VERIFY` 可复跑** —— 但这一条对本 plan 例外的那一半要写清：
    `missions/p0-foundation.json` 的 `commands.test` 逐字是
    `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，
    **`tests/unit` 在判定面内**，所以本 plan 新增的断言**每轮 `GATE_VERIFY` 都会复跑到**。
    这是本仓少见的「不用动 `missions/**` 就能进判定面」的位置，照实记，别推广到 `tests/contracts`（它仍不在）。

11. **lint 面刻意留给后继 plan**。`pyproject.toml` 的 `[tool.ruff] exclude = ["tests/gates"]`；
    实测 `python3 -m ruff check tools --output-format=concise` → **exit 1，9 条**，
    其中 `check_budget.py` 2 条（`:97` `:98` `F541`）、`pass_usage.py` 1 条（`:14` `E401`）、
    `tools/rotate-state.py` 6 条（`E741`）。**本 plan 一条都不修**（见 `## Non-Goals`）。

12. **既有的 CI 与本机判据现状**（开工基线，用于收尾对照）：
    `python3 tools/gates/check_expected_red.py` → **exit 0**，stdout **三行**，逐字：

    ```
    判定模式：default —— 按 tools/gates/expected-red.txt 判定
    门禁 19 项：预期红 7，绿 12，跳过 0
    ✅ 与预期红名单完全一致
    ```

    ⚠️ **三行都要引全** —— Phase 2 的 Exit Criteria 要求「逐字节相同（`diff` 无输出）」，
    只引两行会让那条判据在收尾时对不上。
    `gates.yml` **485 行 / 14 个 job 键**。**本 plan 对 `gates.yml` 的期望改动量是零。**

13. **`tools/**` 的 lint 扩面此前已被裁定「不做」，本 plan 不重开它**（Minimum Rule 1 要求盘点会被本工作
    抵触的既有裁定）。`docs/plans/p0-foundation/2026-08-22-0228-1-gate-verdict-failure-forensics.md`
    的评审记录 **M2** 逐字：

    > **M2** 新增的 `tools/gates/explain_last_gate_failures.py` 无 lint 覆盖 ——
    > 本仓惯用 lint 面 `agenerp tests/unit tests/contracts` 不含 `tools/`；已加**文件级** ruff 判据，
    > 并实测 `tools/gates` 整目录另有 3 条既存告警（`check_budget.py` / `pass_usage.py`），
    > 故明确不扩面，避免把顺手优化拖进来。

    **本 plan 与它不冲突**：本 plan 买的是**行为判据**（`pytest` 真调 `main()`），不是静态检查面；
    ⚠️ 但 `## Deferred But Adjudicated` 里那条「`tools/**` 仍不在 lint 作用域内」**必须按这条裁定改写**，
    不得再写成「交给后继 plan」。

14. **`docs/context/project-context.md` 会被本 plan 改旧**（确认将发生的 owner-doc 漂移，
    按 Minimum Rule 14 不得降级）：该文件 `:53`（Unit tests 一行）与 `:57` 都把
    `tests/unit` 的活计数写成 **293**。本 plan 的 Phase 1 一落地这个数就不对了。
    ⚠️ 该文件**已因同一处漂移被就地改准过两次**（`:57` 自述「此前写 `288`……再往前写的 `283`」），
    **这是复发性漂移，不是新鲜事** —— 因此它必须是本 plan 的一个 `Fix` 项，不是收尾时的顺手动作。

15. **`tests/unit` 在判定面内这件事，对「判据先行」有一个直接后果**（Baseline 10 的下半句，
    本条把它接上）：Phase 1 若单独提交一个**红着的**断言，那么在 Phase 2 落地之前，
    每一轮 `GATE_VERIFY` 都会红，而 `AGENTS.md` 裁判规则 4 的停机条件之一是
    「同一 plan 连续 3 轮 `GATE_VERIFY` fail」。**处置写死在 Phase 1，不临场决定。**

## Goals

- **停机闸这条链有判据**：`check_budget.py` 的各个退出口径、阈值优先级三档、台账聚合口径，
  与 `pass_usage.py` 的 snapshot/measure 差分语义，各有一条钉住的断言，
  且它们**每轮 `GATE_VERIFY` 与每次 CI 都复跑得到**。
- **退出码 1 只对应一件事**：超预算。判定器自身的任何失败都不得再冒充它。
- **判定器自身失败时，闸仍然往「停」的方向倒**。⚠️ 这一条是独立评审第 1 轮加的，
  它约束着上一条的实现方式：把崩溃改判成一个**放行**的码，等于用「不再说谎」换来「不再拦」，
  那不是修复。
- **阈值只有一个读数**：在任何 cwd 下、以及环境变量被写坏时，`configured_budget()` 要么给出同一个值，
  要么让闸停下来，**不再静默降到内置默认**。

## Non-Goals

- **不动 `.github/workflows/**` 一个字节**（红线 2）。新增断言靠既有 `unit-and-contracts` job 自动覆盖。
- **不修 `tools/**` 的 ruff 告警、不扩 lint 作用域** —— 那是本批第二个 plan `2026-08-23-0859-2` 的结果面。
- **不改阈值本身**：`tools/gates/budget.json` 的 `daily_token_budget`（10 亿）是**人的决策**，本 plan 一个数字不改。
- **不改监督器的闸序、不新增闸、不改退出码 0 / 1 / 2 三者既有的「停 / 放行」走向。**
  ⚠️ **本条已按独立评审第 1 轮收窄措辞**：初稿写的是「不改任何一道闸的走向」，
  而那条 Non-Goal 恰好把 D1 唯一正确的候选（新增一个此前未被使用的退出码 **3**）挡在了门外 ——
  用 Non-Goal 关掉一个还没论证过的候选，是把结论写在前面。
  本 plan 对 `tools/loop-supervisor.sh` 的改动是：闸 2 的 `case` **新增一个 `3)` 分支**，
  并改准 `2)` 分支的一行日志措辞。**`0` / `1` / `2` 三者的走向一个字不动，闸序不动，闸数不动。**
- **不给 `tests/gates/**` 加任何东西**，不新增门禁形态（红线 1）。
- **不动 `missions/**`**（角色 B 禁区）。
- **不追覆盖率数字**：不以「`check_budget.py` 达到 N%」作为任何一条 Exit Criteria。
- **不动 `tools/gates/check_expected_red.py` / `gate-verify.mjs` / `expected-red.txt`**。

## Task Route

- Type: `implementation-only change`（含一条**确认活缺陷的 `Fix`**）+ 一处 owner-doc 新增
- Owner Docs: `docs/architecture/system-baseline.md`（新增 **§14.9**）· `docs/context/project-context.md`（验证命令表）
- Skill Selection Basis: 本仓 `docs/skills/README.md` 下没有与「给既有 CLI 补 pytest 判据」对应的技能；
  工作方法由 `docs/plans/00-plan-authoring-and-execution-guide.md` 与 `AGENTS.md` 裁判规则直接给定。
  各 Phase 逐字记 `Skill: none`。

## Infrastructure And Config Prereqs

- **零新增基础设施**：不起 docker、不连活站点、不需要任何 env、不联网。全部断言在 `tmp_path` 里跑。
- **测试必须与真实环境隔离**，这是硬约束不是建议：
  - 不得读真实的 `~/.claude/projects/**`（`pass_usage.sessions_dir()` 的默认落点）；
  - 不得写真实的 `_tmp/loop-usage.jsonl`（`LEDGER` 的默认落点）；
  - 不得读真实的 `tools/gates/budget.json` 作为断言输入。
  三者一律 `monkeypatch` 到 `tmp_path`。**验收方式是机械的**：整套测试跑完
  `git status --porcelain` 必须无输出（见 Phase 1 Exit Criteria）。
- 回滚策略：本 plan 无数据迁移、无站点写、无不可逆动作。回滚 = `git revert` 对应提交。

## Execution Plan

### Phase 1 — 判据先行：把现状钉成断言（含两条现在就红的）

Status: completed
Targets: `tests/unit/test_budget_gate.py`（新建）· `tests/unit/test_pass_usage.py`（新建）
Skill: `none`

- Item Types: `Proof`-heavy（8/9 项为 `Proof`；余一项为 `Decision`）
- Prereqs: 无

- [x] `Decision` **D0：红着的断言怎么落地，才不会把 `GATE_VERIFY` 拖红。**（Baseline 15 的写死处置）
      - (i) Phase 1 与 Phase 2 合成一个提交：判据先行在**文件历史**里就看不见了，红从未存在过。否决。
      - (ii) 用 `@pytest.mark.xfail(strict=True, reason="Baseline 3/…确认的活缺陷，Phase 2 修")`：
        红是**声明出来的**，`pytest` 退 0，`GATE_VERIFY` 不被拖红；
        `strict=True` 保证 Phase 2 之前它**不可能假绿**（真绿会被判成 `XPASS` 失败）。**取此。**
      - (iii) 先提交 Phase 1 让它红着：会在 Phase 2 落地前撞上 `AGENTS.md` 裁判规则 4
        「同一 plan 连续 3 轮 `GATE_VERIFY` fail」的停机条件。否决。
      - **残余风险**：`xfail` 让「红」变成一个不那么刺眼的状态。代偿是 `strict=True`
        与 Phase 2 的 Exit Criteria 逐字要求「删掉 `xfail` 标记后转绿」——**标记必须被删掉，不许留着**。
      - Skill: `none`
- [x] `Proof` 建 `tests/unit/test_budget_gate.py`，钉住 `check_budget.py` 的**现状**（此刻应全绿）：
      `configured_budget()` 三档优先级各一条（环境变量 / 配置文件 / 内置默认）；
      `usage_since()` 的窗口边界（24 小时外的记录不计）、畸形 JSON 行跳过、缺 `at` 键跳过、
      `passes` / `sessions` / `input` / `output` / `msgs` 五个累加口径；
      `main()` 的三个退出码（台账无记录 → 2、在预算内 → 0、超预算 → 1），
      超预算那条**必须逐字断言 stderr 里出现「超预算」与「停机等人」**，
      因为监督器是靠退出码判的、人是靠这句话读的，两者都得钉。
      - Skill: `none`
- [x] `Proof | xfail` **红判据 A（具体输入）**：台账含一行 `at` 不带时区时，`main()` **不得**返回 1。
      此刻它以 `TypeError` 崩掉（Baseline 3 已复现）。按 D0 标 `xfail(strict=True)`。
      - Skill: `none`
- [x] `Proof | xfail` **红判据 B（通用契约，不依赖 A 的那个输入）**：
      ⚠️ **这一条是独立评审第 1 轮加的，缺了它 Phase 3 的变异 ① 会「绿→绿」空转** ——
      因为 D1(c) 单独就能让 A 转绿，撤掉顶层兜底 A 也不会红。
      本条注入一个 (c) **覆盖不到**的异常（例如把 `LEDGER` 指到一个**目录**，让 `.open()` 抛
      `IsADirectoryError`），断言两件事：① `main()` 的返回值**不是 1**；
      ② 异常原文出现在 stderr 上。按 D0 标 `xfail(strict=True)`。
      - Skill: `none`
- [x] `Proof` 建 `tests/unit/test_pass_usage.py`，钉住 `pass_usage.py` 的**现状**：
      `sessions_dir()` 由 cwd 派生的拼法；`current_files()` 在目录不存在时回空集；
      `sum_usage()` 只计 `type == "assistant"`、`input` 等于
      `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`、
      无 `usage` 的消息不计、畸形行跳过；
      `snapshot` → `measure` 的差分只把**新出现**的会话记进台账，且台账是**追加**（第二趟不覆盖第一趟）。
      ⚠️ **三个 token 字段的 fixture 必须取三个互不相同的非零值** ——
      取 0 或取相等值会让 Phase 3 的变异 ③（删掉 `cache_read` 项）算出同一个和，判据当场空转。
      - Skill: `none`
- [x] `Proof` 加一条钉住 Baseline 8 的断言：`measure` 在**快照文件缺失**时的行为。
      ⚠️ **本 phase 只钉现状、不改行为**；若现状确为「全部历史会话被记成本趟」，
      按 Baseline 8 逐字断言它。**要不要改它，见 `## Deferred But Adjudicated` 里那条同名条目**
      —— ⚠️ 初稿这里写「在 D3 里裁定」是**错的指向**（D3 裁的是环境变量，Baseline 7），
      按独立评审第 3 轮改准；那处裁定此前悬空，现已补上。
      - Skill: `none`
- [x] `Proof` 隔离性自查：`monkeypatch` 覆盖 `LEDGER` / 阈值配置路径 / `sessions_dir`，
      并实跑 `git status --porcelain` 确认测试没有在仓里落任何文件。
      - Skill: `none`
- [x] `Proof` 实跑并记录：`python3 -m pytest tests/unit -q`（**期望 exit 0**，因为两条红判据由 D0 标了
      `xfail`；输出里应出现 `2 xfailed`）· `python3 -m pytest tests/unit/test_budget_gate.py
      tests/unit/test_pass_usage.py -q`（点名两条 `xfail`）·
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`（**GATE_VERIFY 原文命令，期望 exit 0**）。
      - Skill: `none`
- [x] `Proof` 实跑 `python3 -m ruff check agenerp tests/unit tests/contracts` —— 新文件落在既有 `lint` job
      的作用域内，**必须 exit 0**，否则会在 CI 上把一个与本 plan 无关的 job 弄红。
      - Skill: `none`

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` → **exit 0**，且输出里 **`xfailed` 计数为 2**
      （⚠️ 不是「没有红」，是「红被声明了两条」）
      —— **实测**：`317 passed, 2 xfailed in 0.74s`，exit **0**
- [x] `tests/unit` 的 **passed 计数**从 **293** 上升到 N，**N 写进 plan**（不写「若干」；
      `xfail` 的两条不计进 passed，这一点在记数时写明）
      —— **N = 317**（+24：`test_budget_gate.py` 15 条中的 13 条 passed + 2 条 `xfailed`、
      `test_pass_usage.py` 11 条 passed；**两条 `xfail` 不计进 passed**，
      故 `24 passed, 2 xfailed` 对应新增 26 个测试函数）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0（实测）
- [x] 整套测试跑完 `git status --porcelain` 只含本 plan 的交付物
      （实测四行：两个 plan 文件 + `tests/unit/test_budget_gate.py` + `tests/unit/test_pass_usage.py`）
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0（实测 `All checks passed!`）
- [x] No owner-doc update required（本 phase 只加测试，不改任何对外行为；
      `project-context.md` 的计数改准归 Phase 2，理由是那两个数要等 Phase 2 定稿后才是终值）
- [x] `docs/logs/` 更新

### Phase 2 — Fix：崩溃既不许冒充超预算，也不许换成放行

Status: completed
Targets: `tools/gates/check_budget.py` · `tools/loop-supervisor.sh` ·
**`tests/unit/test_budget_gate.py`** · `docs/context/project-context.md` · `docs/architecture/system-baseline.md`
Skill: `none`
Prereqs: Phase 1（两条 `xfail` 必须先存在，否则本 phase 的绿证明不了任何东西）

- Item Types: `Fix | Add | Decision`
- ⚠️ **本 phase 必须动测试文件，这不是可选的**（独立评审第 2 轮 N1）：
  Phase 1 把 `configured_budget()` 的**现状**钉成了绿断言（含 `isdigit()` 的静默兜底与
  `except Exception: return DEFAULT_BUDGET`），而 D2 / D3 **刻意把这两处现状改掉** ——
  那两条 Phase 1 的绿断言会在本 phase 变红。**这是预期内的判据更新，不是回归**，
  但它必须以显式执行项落地，否则 Phase 3 的变异 ② / ④ 会点名**根本不存在的断言**。

- [x] `Decision` **D1：判定器自身失败时该退什么码、监督器该怎么接。**
      候选与取舍必须写进 `docs/architecture/system-baseline.md` §14.9。
      - **(a) 在 `usage_since` 的行循环里把 `TypeError` 一并 `except` 掉（跳过该行）** ——
        **静默少算用量**，让一条设计取向逐字为「宁可停着等人」（`loop-supervisor.sh` 模块头）的闸
        向「放行」倾斜。否决。
      - **(b) 台账不可解析即整体退 2** —— 一行坏数据让整份台账作废，同样向放行倾斜。否决。
      - **(c) 把不带时区的 `at` 按 UTC 归一，并在 stderr 上出声** —— 见 D1b，与 (e) 并取。
      - **(d) 顶层兜底后返回 2** —— ⚠️ **初稿取的就是它，独立评审第 1 轮实测证伪，此处照实记不粉饰**：
        监督器的 `case` 只有 `1)` 与 `2)` 两个分支，`2)` 是**放行**。
        今天一次崩溃 exit 1 → 停机（理由说谎但**停住了**）；改成 2 之后 → **接着烧，零成本约束**。
        那不是「登记而不消除的既有残余」，是**本 plan 亲手引入的回退**，
        与 `AGENTS.md` 裁判规则 4 的停机条件「单 mission 累计成本超阈值」直接冲突。**否决。**
      - **(e) 判定器自身失败 → 退一个此前未被使用的码 `3`；监督器新增 `3)` 分支落停机记录。** **取此。**
        它同时满足两条 Goal：`1` 只对应超预算（不再说谎），且崩溃仍然**停**（不再放行）。
        授权面已核：`tools/loop-supervisor.sh` **不在** Protected Areas 表内，
        也**不在** `verdict-tool-untouched` 的 pathspec 内（`gates.yml:293` 逐字只有
        `tools/gates/check_expected_red.py` 与 `tools/gates/gate-verify.mjs`）。
      - **考虑过并否决「让 `2` 改成停机」**：台账在全新检出上必然为空（`_tmp/` 已 `.gitignore`），
        首趟恒退 2，改成停机等于让循环永远起不来 —— 这是可判定的，不是顾虑。
        ⚠️ **它与 (e) 是两个不同的提案**，不得用否决前者来顺带否决后者（初稿犯的就是这个错）。
      - **残余风险**：`3` 是本仓新造的一个码，任何**不经监督器**直接调 `check_budget.py` 的调用方
        看到 3 时没有约定动作。⚠️ **调用方清单已实测改准**（独立评审第 3 轮）：
        `check_budget.py` 在本仓的**唯一**调用方是 `tools/loop-supervisor.sh:70`；
        `tools/ab-run.sh:42,64` 调的是 `pass_usage.py`，**不调它** ——
        初稿把 `ab-run.sh` 写成调用方是错的，**残余因此比初稿写的小**：
        实际暴露面只有「人手工跑」与「将来新增的调用方」。处置：`--help` 与 docstring 里写明三码语义。
      - Skill: `none`
- [x] `Decision` **D1b：不带时区的 `at` 怎么处理。**（独立评审第 1 轮指出初稿的理由是空的，此处重写）
      - ⚠️ **初稿写「写入方一直用 `datetime.now(datetime.UTC)`，所以「它本来就是 UTC」是有据的」——
        这条理由对它要处理的那些行是空的**：`pass_usage.py` **从不产出**不带时区的行（Baseline 5），
        所以它的行为对「手写行是什么时区」一个字都没说。
      - **(i) 按 UTC 归一 + 每次归一都在 stderr 出声。** **取此。**
        理由不是「有据」，而是「**最小意外，且与仓内唯一写入方的口径一致**」；
        出声是为了让这个假设**不静默**。
      - (ii) 不带时区的行**无条件计入窗口**（不猜时区，宁可多算）：更贴合「往停的方向倒」，
        但会让 24 小时窗口对这类行失效，一条三个月前的手写记录也会被算进今天。**否决，理由是可判定的**：
        它把一个时间窗判据变成了非时间窗判据。
      - **残余风险（必须写，初稿漏了）**：负时区手写的本地时间被读成 UTC 会**更早**，
        更可能落到 24h 窗口外而被**少算** —— 方向不安全。代偿只有 (i) 那条 stderr 告警，
        且它只在有人看日志时起作用。**照实登记，不粉饰。**
      - Skill: `none`
- [x] `Fix` 按 D1b(i) 处理不带时区的 `at`；按 D1(e) 给 `main()` 加顶层兜底并**返回 3**，
      把异常原文打到 stderr。⚠️ **不得吞掉异常原文** —— 那会把「说谎」换成「沉默」。
- [x] `Fix` `tools/loop-supervisor.sh` 闸 2：新增
      `3) halt_with "budget-gate-broken" "预算闸自身失败，停机等人"; exit 0 ;;`，
      并改准 `2)` 分支那行日志（现状逐字 `预算：台账暂无记录（首趟），放行` 把 2 的原因写死成「首趟」）。
      ⚠️ **`case` 的 `1)` / `2)` 两个分支的走向与 `exit` 语义一个字不改**；
      改完实跑 `bash -n tools/loop-supervisor.sh` 与 `git diff --numstat -- tools/loop-supervisor.sh`，
      **期望首两列为 `2` `1`**（新增 `3)` 一行 + 改写日志一行）。
- [x] `Decision` **D2：阈值配置的路径解析，以及它怎么被测到。**
      - **(i) 抽一个调用时求值的助手** `config_path() -> pathlib.Path`，
        返回 `pathlib.Path(__file__).resolve().parent / "budget.json"`，由 `configured_budget()` 调它。**取此。**
        ⚠️ **「调用时求值」是硬要求，不是风格偏好**（独立评审第 1 轮）：
        若仍是模块级常量，测试只能二选一 —— 要么 `monkeypatch` 掉它（**锚定逻辑被绕过，
        Phase 3 变异 ② 会绿→绿空转**），要么真去读仓里的 `budget.json`（**违反本 plan 自己的隔离硬约束**）。
        有了助手，断言可以是 `monkeypatch.chdir(tmp_path); assert check_budget.config_path() == 期望值`，
        既不读真文件也不绕过逻辑。
      - (ii) 向上找仓库根：多一层「什么算仓库根」的约定，本仓此刻没有这个约定。否决。
      - (iii) 维持 cwd 相对、只在文档里写「必须在仓根跑」：文档级约束对拿着 shell 的人没有强制力。否决。
      - **并取：配置文件存在但读不出/解析不出 → 退 `3`（判定器自身失败）并打印原文**；
        **文件不存在** → 仍用内置默认（那是全新检出的正常状态，不是错误）。
        ⚠️ 初稿这里写的是「退 2」，按 D1(e) 统一改成 3 —— **坏配置必须停机，不是放行。**
      - **残余风险**：脚本被单独拷走而 `budget.json` 没跟着 → 落到内置默认 2 亿，
        比现值 10 亿**更紧**，方向安全；照实登记。
      - Skill: `none`
- [x] `Fix` 按 D2 落地 `config_path()` 与「坏配置退 3」。
- [x] `Decision | Fix` **D3：环境变量被写坏时的静默兜底**（Baseline 7）。
      取「**非空且非纯数字 → 退 `3` 并打印原文**」；空/未设仍按优先级往下走。
      理由：现状是**静默向更松的一侧**倒（忽略操作者写的 2 亿、改用文件的 10 亿）。
      **否决**「静默采信 `int()` 能解析的写法」—— 会让 `1e9` 这类写法悄悄生效，把一个决策变成一次手滑。
      ⚠️ **独立评审第 1 轮的定性照收**：D3 **没有活触发点、没有事故背书**
      （`tools/install-loop-agent.sh` 装 plist 时**刻意不注入** `AGENERP_DAILY_TOKEN_BUDGET`），
      是本 plan 里最接近顺手优化的一项；它被留在 scope 内的唯一理由是它与 D2 属同一个结果面
      （「阈值只有一个读数」）且共用同一个退出码语义。
      - **残余风险（独立评审第 3 轮补，Rule 9）**：D3 之后，一个**写坏的环境变量会直接停机**。
        操作者本想放宽一天的预算、结果把循环停了 —— 这是**新增的停机入口**。
        取此仍属可接受的方向（往「停」倒），但**不得写成「无代价」**；
        代偿是 stderr 会打出被拒绝的原值。
      - Skill: `none`
- [x] `Add` **删掉 Phase 1 那两条 `xfail` 标记**（只删标记，不动断言正文）。
- [x] `Add` **重写 D2 / D3 刻意作废的那两条断言**：`configured_budget()` 的
      「配置文件读不出 → 静默用内置默认」与「非纯数字环境变量 → 静默落到文件」两条现状断言，
      改成断言退出码 `3`。⚠️ **必须在提交信息或断言注释里引上旧期望的原文**，
      让「判据被改过」这件事在 diff 上看得见，而不是悄悄换掉。
- [x] `Add` **cwd 无关性断言**（B4 的落点，Phase 3 变异 ② 点名的就是它）：
      `monkeypatch.chdir(tmp_path)` 之后断言 `check_budget.config_path()` 仍指向脚本同目录的
      `budget.json`。⚠️ **不得 `monkeypatch` 掉 `config_path` 本身**，那会把要测的逻辑绕过去。
- [x] `Add` **退出码 `3` 的三条断言**（Phase 3 变异 ④ 点名的在其中）：
      判定器内部异常 → `3` · 配置文件存在但解析不出 → `3` · 环境变量非空且非纯数字 → `3`。
- [x] `Fix` **就地改准 `check_budget.py` 的 docstring**：`:8` 的用法行写着
      `[--exclude-session ID]`，而 `argparse` **从未定义过这个参数**（实测只有 `--budget-tokens` 与 `--json`）——
      确认的文档漂移。本 plan 反正要重写这段 docstring（加三码语义表），**顺路改准，不是另开一件事**。
- [x] `Fix` 把三个退出码的语义写进 `--help`（`argparse` 的 `description` / `epilog`）与 docstring，
      让不经监督器的调用方看得到（D1 残余风险段写死的那条处置）。
- [x] `Fix` **`docs/context/project-context.md` 的 `:53` 与 `:57` 两处 `293` 就地改准**为 Phase 1 定下的新计数
      （Baseline 14 的确认漂移，Minimum Rule 14 不降级）。
      ⚠️ 照该文件既有惯例标注改准来源与本 plan id；**不新增任何一行验证命令**，只改数字与出处。
- [x] `Fix` 新增 `docs/architecture/system-baseline.md` **§14.9**，落纸 D0 / D1 / D1b / D2 / D3
      五处取舍、各自代价与残余风险，以及三个退出码的语义表。
      ⚠️ 开工时实读确认 §14.9 未被占用（现有最大编号为 §14.8）。

Exit Criteria:

- [x] Phase 1 的两条 `xfail` 标记**被删掉**，且删掉后两条**转绿**；绿因是行为改对，不是断言被放宽。
      ⚠️ **判据是机械的，且作用域是那两个测试函数、不是整个文件**（独立评审第 2 / 3 轮连续改准：
      初稿写「断言正文前后 `git diff` 为空」字面为假；二稿改成「整个文件的删除行只许是那两行装饰器」，
      **仍然不可满足** —— 同一文件里还有两条断言要被 D2 / D3 有意改写）：
      判据是 **`git diff -U0` 中属于这两个 `xfail` 函数的 hunk，其删除行只有那两行
      `@pytest.mark.xfail(...)`**，函数体一行未删。
- [x] `python3 -m pytest tests/unit -q` → exit 0，`xfailed` 计数 **归 0**
- [x] `python3 -m pytest tests/contracts -q` → exit 0
- [x] `python3 tools/gates/check_expected_red.py` → exit 0，输出与 Baseline 12 引的**三行**逐字节相同（`diff` 无输出）
- [x] `bash -n tools/loop-supervisor.sh` → exit 0；`git diff --numstat -- tools/loop-supervisor.sh` 首两列为 `2` `1`
- [x] 三个退出码各有一条断言：`1` 仅超预算、`3` 仅判定器自身失败、`2` 仅台账无记录
- [x] `python3 tools/gates/check_budget.py --help` 的输出里**同时**出现 `1` / `2` / `3` 三个码的语义
      （grep 可核；D1 与 Deferred 都承诺了这一条，此前没有任何判据看着它）
- [x] `grep -n "exclude-session" tools/gates/check_budget.py` **零命中**（NB3 那处文档漂移已改准）
- [x] **被 D2 / D3 有意作废的那两条断言另有一条独立判据**（与上一条互不混用）：
      两条都已重写为断言退出码 `3`，且**旧期望的原文出现在断言注释或提交信息里**（grep 可核）
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `docs/architecture/system-baseline.md` §14.9 落地；`docs/context/project-context.md` 两处计数改准
- [x] `docs/logs/` 更新

### Phase 3 — 变异验证：证明这些断言有牙齿

Status: planned
Targets: `tools/gates/check_budget.py` · `tools/gates/pass_usage.py`（实验后一律复原）·
`docs/masterplan/STATE.md`（**只追加**一行证据）
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 2

- [ ] `Proof` 变异 ①：撤掉 D1(e) 的顶层兜底 → 期望 `pytest tests/unit` **exit 1** 且**逐字点名
      红判据 B**（Phase 1 那条注入 `IsADirectoryError` 的通用契约断言）。
      ⚠️ **点名的必须是 B 不是 A** —— A 由 D1b(i) 单独就能绿，用 A 做这条变异会绿→绿空转。
      复原后回 exit 0。
- [ ] `Proof` 变异 ②：把 D2 的 `config_path()` 体改回 `pathlib.Path("tools/gates/budget.json")` →
      期望那条 cwd 无关性断言红。⚠️ 若它在仓根 cwd 下也绿，说明断言没真测到路径 ——
      **那是判据无牙齿，必须当场改断言**。复原后回 exit 0。
- [ ] `Proof` 变异 ③：把 `sum_usage` 的 `cache_read_input_tokens` 一项删掉 →
      期望 `test_pass_usage.py` 的聚合口径断言红并点名（fixture 的三个字段已按 Phase 1 取三个互不相同的非零值）。
      复原后回 exit 0。
- [ ] `Proof` 变异 ④：把 D3 的「非纯数字环境变量 → 退 3」改回静默兜底 → 期望对应断言红并点名。
      复原后回 exit 0。
- [ ] `Proof` 四次变异的八个退出码（红→绿 ×4）与**点名集合逐字**记进本 plan。
      ⚠️ 只写「红了」不算证据；**任何一条出现「绿→绿」即判为该断言空转，必须当场补强而不是记成通过**。
- [ ] `Proof` 收尾复跑 `GATE_VERIFY` 的原文命令
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，记退出码与输出原文。
- [ ] `Proof` 往 `docs/masterplan/STATE.md` **追加**一行证据（红线 5：只追加，不改写既有行）。
- [ ] `Proof` 收尾实跑 `git status --porcelain`，确认四次变异全部复原、工作树只剩本 plan 的交付物。

Exit Criteria:

- [ ] 四条变异各自的红/绿八个退出码与点名集合已落纸；**没有任何一条是「绿→绿」**
- [ ] 收尾 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，原文入档
- [ ] `docs/masterplan/STATE.md` 的 `git diff` **只显示新增行**
- [ ] `git status --porcelain` 只含本 plan 的交付物
- [ ] No owner-doc update required（本 phase 只取证；owner doc 已在 Phase 2 对齐）
- [ ] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-23）——
  六条阻断项，全部已在本稿改掉，逐条对照：
  **B1** D1(d)「崩溃退 2」把停机闸从 fail-stop 改成 fail-open，
  且本 plan 否决 (a)/(b) 的理由恰好也否决它自己 → 新增并取用候选 **(e)**（退 `3` + 监督器 `3)` 分支），
  Non-Goal 相应收窄（初稿用 Non-Goal 把唯一正确的候选挡在了门外）。
  **B2** Phase 1 会把一条红断言落进 `missions/p0-foundation.json` 的判定面，
  单独提交将连续拖红 `GATE_VERIFY` 并撞裁判规则 4 → 新增 **D0**，取 `xfail(strict=True)`；
  Exit Criteria 改为 **passed 计数**并写明期望退出码与 `xfailed` 计数。
  **B3** 原 Phase 1 只有「具体输入」那一条红判据，D1(c) 单独就能让它绿 →
  变异 ① 会绿→绿空转；新增**红判据 B**（注入 `IsADirectoryError` 的通用契约），变异 ① 改为点名 B。
  **B4** `CONFIG` 是模块级常量，测试要么绕过锚定逻辑要么读真文件 →
  D2 写死「调用时求值的 `config_path()` 助手」这一接口契约。
  **B5** `docs/context/project-context.md:53` / `:57` 的 `293` 会被 Phase 1 改旧（复发性漂移）→
  新增 Baseline 14 与 Phase 2 的 `Fix` 项 + Exit Criterion。
  **B6** D1(c)「有据的，不是猜」对它要处理的那些行是空的 →
  拆出 **D1b**，改成「最小意外」+ 强制 stderr 出声，并补上初稿漏掉的残余风险（负时区手写时间会被少算）。
  非阻断建议 1/2/3/4/5/6 亦已采纳（Baseline 12 引全三行 · `STATE.md` 追加项排进 Phase 3 ·
  变异 ③ 的 fixture 取三个互不相同的非零值 · Deferred 首条补 `Why Not Blocking Closure` ·
  `numstat` 判据改为「首两列」· 头部对后继 plan 的提醒改成「计数可能**变大**」）。
  建议 7（D3 最接近顺手优化）以**就地记明定性**的方式采纳，未移出 scope，理由写在 D3 项内。
- Independent draft review iteration 2: **needs revision**（独立子代理，fresh session，2026-08-23）——
  **B1–B6 全部判 CLOSED**，评审并复跑了本稿新增的每一条事实（三行判定输出、`0228-1` M2 原文、
  `project-context.md` 的两处 `293` 与两次历史改准、`loop-supervisor.sh` 的授权面、
  `numstat` 的 `2` `1` 算术、`xfail(strict=True)` 的实际行为）逐项 ✔。
  **一条新阻断项 N1 已在本稿改掉**：Phase 2 的 D2 / D3 会**有意作废** Phase 1 钉下的两条现状断言，
  而 Phase 2 既没把测试文件列进 `Targets`、`Item Types` 也没有 `Add`，
  于是 Phase 3 的变异 ② / ④ 点名的是**没有任何执行项创建过的断言**（B4 的目的因此仍未达成）→
  Phase 2 补 `Targets` / `Item Types` 与四条 `Add` 执行项。
  非阻断 1（xfail 判据字面为假）、3（`--exclude-session` 文档漂移）、4（三码语义缺判据）亦已采纳。
- Independent draft review iteration 3: **needs revision**（独立子代理，fresh session，2026-08-23）——
  **N1 判 CLOSED**，红线 1–7 全部未触及，Rule 11 / 12 一致性通过。四条待改已在本稿改掉：
  ① xfail 判据二稿仍不可满足（同一文件里还有两条断言要被有意改写）→ 收窄到「那两个 `xfail` 函数的
  `-U0` hunk」，并给 D2 / D3 的重写**另立一条独立判据**；
  ② **Baseline 8 的裁定此前悬空**（Phase 1 指向 D3，而 D3 裁的是别的事）→ 补 `Deferred` 条目并改准指向；
  ③ **`tools/ab-run.sh` 调 `check_budget.py` 是假陈述**（实测唯一调用方是 `loop-supervisor.sh:70`）→
  两处就地改准，并写明「残余比初稿写的小」；
  ④ 评审记录未回填 → 即本条。
  非阻断（D3 缺残余风险行、`gates.yml:390` 的 job 名过期）亦已采纳，后者已立 `Deferred` 条目。
- Independent draft review iteration 4: **acceptable as-is**（独立子代理，fresh session，2026-08-23）——
  第 3 轮的四条阻断项与两条非阻断项**逐条判 CLOSED**（xfail 判据已收窄到那两个函数的 `-U0` hunk 且
  D2/D3 重写另立判据 · Baseline 8 的悬空裁定已补成带两条重开事件的 `Deferred` 条目 ·
  `ab-run.sh` 假陈述两处均已改准且写明「残余比初稿小」· 评审记录已回填）。
  整体一致性通过：红线 1–7 未触及、§14.9 确为空号、Rule 7 / 9 / 10 / 11 / 12 全部满足、
  九条 `Deferred` 各有重开事件、Exit Criteria 全部是「命令 + 退出码」形态、
  `numstat` 的 `2` `1` 与两行监督器改动对得上。评审逐字：「**I would set `Plan Status: active`**」。
  两处**刻意不阻断**的观感项照实记：Infra 段那句 `git status --porcelain` 必须无输出比
  Phase 1 Exit Criteria 的「只含本 plan 的交付物」更严（后者才对，新测试文件是 untracked）；
  Phase 2「重写那两条断言」与「退出码 3 三条断言」两项有重叠，属无害冗余。
- **共识达成（四轮）**：第 1 轮 `needs revision`（B1–B6）→ 第 2 轮 `needs revision`（B1–B6 全 CLOSED，
  新增 N1）→ 第 3 轮 `needs revision`（N1 CLOSED，四条待改）→ **第 4 轮 `acceptable as-is`**。
  据此把 `Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（`system-baseline.md` **§14.9** 新增 · `project-context.md` `:53` / `:57`
      两处计数就地改准 · `docs/masterplan/STATE.md` 追加一行证据）
- [ ] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts -q` · `python3 -m ruff check agenerp tests/unit tests/contracts` ·
      `bash -n tools/loop-supervisor.sh` · 四次变异的八个退出码
- [ ] scoped verification is not conflated with full verification —— ⚠️ **本 plan 的验证范围限于本机**；
      CI 侧由既有 `unit-and-contracts` job 在合并后自然复跑，**本 plan 不烧 CI 轮次、也不宣称 CI 已验证**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### 退出码 `2`（台账无记录）仍然是放行，本 plan 不改它

- Classification: `watch-only residual`
- Why Not Blocking Closure: ⚠️ **本条已按独立评审第 1 轮整条重写，初稿那条是错的** ——
  初稿把「崩溃在无人值守时不会停机」登记成残余，而那个后果是**初稿自己 D1(d) 引入的**，
  不是既有状态。D1(e) 取用退出码 `3` 之后，**崩溃是停机**，该残余不存在了。
  本条现在登记的是**真正剩下的那一块**：`2` 的语义仍是「24 小时内台账没有循环趟次记录」，
  监督器对它仍是放行。这是**既有行为，本 plan 一个字未改**，
  且 D1 已实测论证改成停机会让全新检出的首趟永远起不来（`_tmp/` 在 `.gitignore` 里，台账必然为空）。
- Successor Required: `no`
- 重开事件：**第一次出现「台账因非首趟原因为空、循环却一路放行」时**，
  或**人裁定给监督器加一道「连续 N 次退 2 即停」的闸时**。

### 新造的退出码 `3` 对不经监督器的调用方没有约定动作

- Classification: `watch-only residual`（**本 plan 自己造出来的，登记而不消除**）
- Why Not Blocking Closure: ⚠️ **本条的事实面已按独立评审第 3 轮改准**：初稿写「`tools/ab-run.sh`
  与人手工查读都直接调 `check_budget.py`」，**`ab-run.sh` 那半句是错的**（它只调 `pass_usage.py`，
  见 `:42` `:64`）。实测 `check_budget.py` 在本仓**只有一个调用方**：`tools/loop-supervisor.sh:70`，
  而本 plan 正是给它加了 `3)` 分支。**因此这条残余现在只覆盖「人手工跑」与「将来新增的调用方」。**
  处置是把三码语义写进 `--help` 与 docstring（D1 的残余风险段写死的那条），
  **但那是文档级约束，对将来的调用方没有强制力**。⚠️ 不得写成「已覆盖所有调用方」。
- Successor Required: `no`
- 重开事件：**第一次出现某个调用方吞掉 `3` 时**，或**人裁定给这三个码定一份跨调用方的约定时**。

### `tools/**` 仍不在 lint 作用域内

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: ⚠️ **本条已按独立评审的结论改写** —— 初稿写「交给本批第二个 plan」，
  而 `-2` 已按其独立评审的结论**放弃扩面**。真正的处置依据是 Baseline 13：
  `2026-08-22-0228-1` 的评审记录 **M2 已就同一处裁定「明确不扩面，避免把顺手优化拖进来」**，
  本 plan 不重开别人的裁定。
  ⚠️ **本 plan 不因此宣称 `tools/**` 已被覆盖**：它买的是 `check_budget.py` / `pass_usage.py`
  两个文件的**行为判据**，`tools/` 下另外四个 Python 文件与全部 shell 仍然零静态检查、零判据。
- Successor Required: `no` —— 已登记进 `docs/backlog/`（由 plan `-2` 落纸），交人裁定
- 重开事件：**人裁定推翻 `0228-1` M2 时**，或**第一次出现「`tools/**` 被改坏、当轮 `GATE_VERIFY` 绿、
  无人值守时才炸」时**（届时这条残余就有了活例证）。

### `tools/loop-supervisor.sh` 整体没有判据

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 给的是**闸 2 那一格**的判据。五道闸里的
  停机记录闸 / LoopX 配额闸 / 退 2 即停闸仍是纯 shell、无任何自动判据。
  给 shell 加判据需要一套本仓此刻没有的 bats/shunit 类设施，那是独立的结果面，
  且会把「新增一类测试运行器」这个决策夹带进一个 `Fix` plan 里。
- Successor Required: `no`
- 重开事件：**监督器第一次因自身逻辑错误误停或误放行时**，
  或**人裁定给本仓引入 shell 测试运行器时**。

### `tests/unit` 与 `tests/contracts` 不受任何棘轮保护

- Classification: `watch-only residual`（`0120-1` 已登记，本 plan 继续挂着并**说明它对本 plan 的具体后果**）
- Why Not Blocking Closure: 红线 1 只圈 `tests/gates/**`，loop 可以合法地删本 plan 新加的断言。
  ⚠️ **对本 plan 尤其要紧**：本 plan 交付的正是「停机闸的判据」，
  删掉它们等于把停机闸退回今天的 0% 状态，而 CI 只会看到 `passed` 计数变小、不会红。
- Successor Required: `no`
- 重开事件：**第一次出现「单测被删/放宽而 CI 仍绿」时**，或**人裁定给这两个目录加计数棘轮时**。

### `pass_usage.py measure` 在快照文件缺失时把全部历史会话记成一趟（Baseline 8）

- Classification: `watch-only residual`（**此前悬空的一处裁定，独立评审第 3 轮补上**）
- Why Not Blocking Closure: ⚠️ **先说清它为什么此前是悬空的**：Phase 1 原写「在 D3 里裁定要不要改」，
  而 D3 裁的是环境变量，**根本不是这件事** —— 那是一处指向错误，不是裁过了。
  **本条现在正式裁定：钉住现状，不改行为。** 理由两条：
  ① 产品路径上 `tools/loop-supervisor.sh:86` 的 `snapshot` 恒先于 `:90` 的 `measure`，无已知活触发点；
  ② 改它要决定「快照缺失时该记 0 趟还是该报错」，那是一个**新的判定语义**，
  与本 plan 的结果面（停机闸的判据 + 退出码契约）不是一件事。
  ⚠️ **代价照实记**：`tools/ab-run.sh:42` 的 snapshot 带 `2>/dev/null`，**它失败是静默的**；
  真撞上这条，台账会被写进一个巨大的假数字，下一趟 `check_budget` 就会据此停机
  ——**方向是「停」，不是「放行」**，这是它可以只钉不改的另一半理由。
- Successor Required: `no`
- 重开事件：**第一次出现「台账里某一趟的数字大得离谱」时**（届时 Phase 1 钉下的那条断言就是解释它的现成依据），
  或**有人给 `measure` 新增一个不经 `snapshot` 的调用路径时**。

### `gates.yml:390` 的 job 名 `单测与契约测试（439 条）` 已经过期，本 plan 不改

- Classification: `watch-only residual`（**红线 2 内，只有人能做**；独立评审第 2 轮点名）
- Why Not Blocking Closure: 该 job 名把测试条数写死在 CI 里，实测当前是 **444 条**（`tests/unit` 293 + `tests/contracts` 151），
  已经对不上；**本 plan 的 Phase 1 还会把它推得更远**。但 `.github/workflows/**` 是红线 2 的 `blocked` 面，
  为一个 job 名去重摆授权面并烧一轮 CI 不划算。
  ⚠️ **它不影响判定**（job 判的是 pytest 退出码，不是那个数字），但它是一处**会持续变旧的字面陈述**，
  照实登记，不粉饰成「无害」。
- Successor Required: `no`（**人动作**，可与将来任何一次动 `gates.yml` 的 plan 搭车）
- 重开事件：**下一个因任何理由要动 `gates.yml` 的 plan 开工时**（届时必须把这处 job 名一并纳入 scope）。

### 覆盖率没有被做成判据

- Classification: `watch-only residual`（**刻意的选择，不是遗漏**）
- Why Not Blocking Closure: 覆盖率阈值会奖励「跑到过这一行」而不是「判对了这个行为」，
  且会把 `coverage` 引成一条新的 CI 依赖。本 plan 的判据是点名的**行为**各有断言。
  ⚠️ 代价照实记：**`check_budget.py` 里没被本 plan 点名的分支仍然无判据**，
  且没有任何机械手段会提醒后来者这一点。
- Successor Required: `no`
- 重开事件：**人裁定给本仓引入覆盖率门槛时**。

### 取不到预期证据 / 结果与预测不符时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- Why Not Blocking Closure: 本条不是一件待办，而是**失败分支的固定处置**——
  把它写在这里是为了不临场发明处置方式；它不占用任何 Exit Criterion。
- 处置逐字：原样复跑一次（裁判规则 3：复跑优先于分析）→ 仍不符则记录所有已跑命令与输出原文 →
  追加进 `docs/masterplan/STATE.md` §3（**不改写既有行**）→ **不放宽任何断言**、
  **不改 `tests/gates/**` 与 `tools/gates/check_expected_red.py`** → **不猜根因** →
  本 plan 置 `deferred` 并在文件头写明重开条件。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或不符之因被一个独立 plan 查清之后。

## Closure

Status Note: <待关闭时填写>

Closure Audit Evidence:

- Auditor / Agent: <独立子代理>
- Evidence: <task id / 命令原文 + 退出码 + commit sha>

Follow-up:

- <仅非阻塞项；确认的活缺陷不得出现在这里>
