# 2026-08-23-0337-1 把最后两条零 CI 覆盖的本机验证命令搬上 CI（`agenerp.seed --verify` + `ruff check`）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 工作项 9 · L2 门禁的判定与 CI 覆盖（**CI 覆盖面**那一半；不改工作项 9 的 `done` 判据，也不改工作项 7 的状态值）
> Last Reviewed: 2026-08-23
> Source: `docs/masterplan/STATE.md` §2（2026-08-23T01:00Z 行）逐字登记的
> 「`python3 -m agenerp.seed --seed 42 --verify` 与 `python3 -m pytest tests/unit -q` / `tests/contracts -q` /
> `ruff check …` **四条本机命令在 `gates.yml` 里零 job 覆盖**」——其中两条已由 `2026-08-23-0120-1` 补上，
> **本 plan 补剩下的两条**
> Related: `2026-08-23-0120-1-ci-unit-and-contracts-coverage.md`（同一形态的直接前驱，纯追加一个 job）·
> `2026-08-22-2325-2-ci-seed-site-verification.md`（写死了本 plan 必须重摆的授权面重开事件）·
> `2026-08-22-1206-2-gates-l2-live-lands-on-main.md`（同上）
> Audit: required
> 执行顺序：**1 / 2**。本批第二个 plan `2026-08-23-0337-2` 也往 `gates.yml` 追加 job，
> 两者都必须做「前 N 行逐字节未动」的前缀性 `diff` 自查，**串行执行可以让第二个 plan 的基线行数是确定的**。
> ⚠️ 队列里另有一个更早的 `active` plan `2026-08-23-0120-2`。**它与本 plan 在三个文档文件上「文件级重叠、行级不相交」**——
> `0120-2` 的 Targets 逐字含 `docs/architecture/system-baseline.md` §14.5 · `docs/context/project-context.md:57` ·
> `docs/backlog/p0-foundation-roadmap.md`，**与本 plan 的 Phase 1 / Phase 4 Targets 是同一批文件**。
> ⚠️ **初稿这里写的是「零交集」，那是错的**（评审第 1 轮抓出）：括号里只为 `agenerp/**` 辩护，结论却写到了全部改动面。
> 代码面确实零交集（本 plan 不碰 `agenerp/**`、不碰 `seedsite.py`），**文档面不是**。
> 处置：两者**串行执行**，后执行的一方开工时必须重读那三个文件的现时内容，**不得照抄本文件写下的行号**。

## Current Baseline

全部为 2026-08-23 在 `main`（`7a09ef7`）上的实跑/实读，不是回忆。
⚠️ **工作树此刻不干净，且这件事对本 plan 是有牙齿的**：`git status --porcelain` 有 4 个 `M`
（`docs/architecture/system-baseline.md` · `docs/backlog/p0-foundation-roadmap.md` ·
`docs/context/project-context.md` · `docs/plans/p0-foundation/2026-08-23-0120-1-…md`）与 1 个 `??`
与 3 个 `??`（plan `2026-08-23-0120-2` 与本批两个 plan 自己）。
⚠️ **四个 `M` 里有三个就是本 plan 自己的 Targets**（`system-baseline.md` 见 Phase 1 与 Phase 4；
`project-context.md` 与 `p0-foundation-roadmap.md` 见 Phase 4）——**初稿写的「与本 plan 的改动面零交集」是错的**
（评审第 1 轮抓出）。那些未入库的改动是 `0120-1` 的回填，**不是本 plan 的产物**。
**因此「`git add` 只列本 plan 自己动的路径」这条保命措施在这里恰好失效**：那些正是同一批路径，
照做就会把别人未入库的工作裹进本 plan 的提交。
**写死的硬前置（Phase 1 的第一个执行项，已落成 checkbox，不是散文）**：开工前先确认 `0120-1` 的未入库文档
**已入库**，`git status --porcelain -- docs/architecture/system-baseline.md docs/context/project-context.md
docs/backlog/p0-foundation-roadmap.md` **无输出**。
⚠️ **「已入库」是唯一出口，`stash` 不是等价出口**（评审第 2 轮抓出）：那些未入库的改动里就有本 plan Baseline 14
依赖的 §14.6，**stash 掉它们会当场改变本 plan 的写作前提**，而 Phase 4 又要求「§14.1–§14.6 逐字节未动」。
**做不到就停下来，把情况写进 `STATE.md` §3 等人**，不自行 stash 别人的工作。
**每次提交以 `git diff --cached --stat` 逐条核对实际入库路径**，**不以 `git add` 的参数列表为凭**。

1. **`ruff` 在 CI 上零覆盖。** `grep -rn "ruff" .github/` → **退 1，零命中**。
   本机 `ruff check agenerp tests/unit tests/contracts` → **exit 0**，逐字 `All checks passed!`；
   `ruff --version` → **`ruff 0.14.1`**。
2. **`ruff` 的版本在仓内哪里都没有钉住。** `pyproject.toml` 只有 `[tool.ruff]` 的**配置**
   （`line-length = 100` / `target-version = "py312"` / `exclude = ["tests/gates"]`），
   **没有任何一处写版本号**；仓内也没有 `requirements*.txt` / lock 文件。
   → 「CI 上装哪个 ruff」是本 plan 必须自己裁定的一件事（D2），不是照抄现成配置。
3. **`python3 -m agenerp.seed --seed 42 --verify` 在 CI 上零覆盖。**
   `grep -rn "agenerp\.seed \|agenerp/seed" .github/` 的**唯一**命中是
   `.github/workflows/gates.yml:320` 的一行注释，讲的是 `agenerp/seedsite.py`（**另一个模块**）。
   CI 上真跑的四条种子链命令（`gates.yml:356/359/365/369`）**全部是 `agenerp.seedsite`**，
   **一条都不是 `agenerp.seed`**。两者别混：`seedsite` 是站点装载器，`seed` 是确定性生成器。
   本机 `python3 -m agenerp.seed --seed 42 --verify` → **exit 0**，逐字 `✅ 种子 42：两次生成 diff 为空，场景断言全过`。
4. **这条命令是 WBS 写死的验收命令**：`docs/context/project-context.md` 的 `Seed dataset acceptance` 一行
   逐字标明它取自 `docs/masterplan/02-WBS.md` P0.6 的验收列，语义是「同种子两次生成 `diff` 为空**且**
   内置荒谬场景的断言全过 → 退 0」，并逐字登记着「⚠️ **它不在 `missions/p0-foundation.json` 的
   `commands.test` 里**，`GATE_VERIFY` 复跑不到它」。
5. **它不写仓库。** `agenerp/seed/__main__.py:26-27` 的 `--out` 帮助文逐字：
   「不给则：不带 `--verify` 时写进临时目录并打印路径，**带 `--verify` 时不落盘**。**仓库里不落生成物。**」
   → 在 CI 上跑它**不产生需要清理的产物**，也不会污染 `git status`。
6. **`gates.yml` 现状**：**404 行**，**11 个 job 键**
   （`gates-untouched` · `expected-red-ratchet` · `gates-l1` · `masterplan-links` · `roadmap-parseable` ·
   `loop-wiring` · `gates-l2` · `gates-l2-live` · `verdict-tool-untouched` · `gates-l2-seed` · `unit-and-contracts`）。
   末尾的 `unit-and-contracts`（`:389-404`）是 `0120-1` 纯追加的，其形态就是本 plan 要复用的模板：
   `actions/checkout@v4` + `actions/setup-python@v5`（`python-version: "3.11"`）+ `pip install pytest` + 两个判据 step。
7. **`unit-and-contracts` 不装 `agenerp`**：`pyproject.toml` 的
   `[tool.pytest.ini_options] pythonpath = ["."]` 让 `python3 -m pytest` 能 import `agenerp`。
   ⚠️ **这条对本 plan 不适用**：`python3 -m agenerp.seed` **不经过 pytest**，`pythonpath` 那行管不到它。
   本机之所以能跑，是因为 `-m` 形式会把 CWD 插进 `sys.path`（`pyproject.toml` 那两行注释自己写着这一点）。
   → CI 上 `working-directory` 是仓根，同一机制成立；**但这是本 plan 必须在 Phase 2 实测确认的一条，不是可以假设的**。
8. **本机与 CI 的解释器不同**：本机 `Python 3.12.9`，`gates.yml` 的既有 job 全钉 `3.11`。
   `pyproject.toml` 的 `requires-python = ">=3.11"`，两版都在支持面内。
   ⚠️ `[tool.ruff] target-version = "py312"` 是**给 ruff 看的语法目标**，与运行 ruff 的解释器版本无关，
   在 3.11 上装 ruff 去 lint「按 py312 语法」的代码是成立的 —— **但这句是推理，Phase 2 必须用实跑退出码证实它**。
9. **红线 2 的措辞只禁「变松」**：`AGENTS.md:11` 逐字「**不得修改 `.github/workflows/**`** 让门禁**变松**
   （禁用 job、加 `continue-on-error`、缩小触发范围）」；而
   `docs/context/ai-autonomy-policy.md` Protected Areas 给 `.github/workflows/**` 定的是 **`blocked`**。
   两者不一致，该不一致由 `0027-2` 登记、`1206-1` / `1206-2` / `2325-2` / `0120-1` 各自重述，**至今未由人裁定**。
   `0120-1` 的 Deferred 逐字写死了重开事件：「**下一个要动 `main` 上 `.github/workflows/**` 的 plan 开工前**
   （届时必须再摆一次）」。**本 plan 就是那个 plan**，因此 D1 必须重摆，**不得默认继承**。
10. **本仓已固化的红线 2 机械自查五条**（`2325-2` / `0120-1` 两次实测用的同一套）：
    ① 前缀性 `diff` 无输出（新增在文件末尾，既有行逐字节未动）；② job 键集合只增不减；
    ③ **禁用词自查（判据是「与改动前逐条相同」，不是「零命中」）** —— ⚠️ **「零命中」只对 `continue-on-error` / `if: false` / `paths-ignore` 三个成立**
    （实测 `grep` 退 1）；`\|\| true` **有两处既有命中**：`gates.yml:36` 与 `:293`
    （两处都是 `CHANGED=$(git diff --name-only … || true)`，在两个守卫 job 里）。
    **判据因此是「与改动前逐条相同」，不是「零命中」**——初稿只写「零命中」会让执行者看见这两处就停下、
    或更糟地「顺手清理」它们（那是改既有 job，本 plan 明令不做）；
    ④ `if:` 只出现在既有白名单位置（`gates.yml` 现有 10 处 `if: always()` **全在取证/拆栈步骤上，无一在判据步骤上**）；
    ⑤ 无失败吞噬（判据 step 不接 `|| true`、不接 `continue-on-error`）。
11. **`missions/p0-foundation.json:23` 的 `_notes.commands` 逐字写着**（⚠️ 行号是 `:23`，
    `:24` 是 `_notes.test`，两处引文不同，别混）：
    「本机 ruff / mypy / docker 都还没有，写进去等于每个 plan 一开局就 fail —— 它们是 P0 的交付物，
    **装上了再往这里加 lint / typecheck / build**。」
    ⚠️ **ruff 现在装上了**（Baseline 1），即这条注释自己预告的条件已满足；
    **但 `missions/*.json` 是角色 B 禁区（`ai-autonomy-policy.md` Protected Areas 第 9 行，`blocked`），loop 无权改。**
    → 这是一条**确认的、但 loop 动不了**的缺口，登记进 `## Deferred But Adjudicated`，**不假装它不存在**。

12. **`tests/unit` 已经在跑同一次调用了**（本条是评审第 1 轮抓出的、初稿整个漏掉的基线，Minimum Rule 1）：
    `tests/unit/test_seed_deterministic.py:18` 逐字 `from agenerp.seed.__main__ import main`
    （⚠️ `:17` 是另一条 import，评审第 2 轮改准）；
    `:205-208` 的 `test_cli_returns_one_and_names_the_failure`（monkeypatch `verify` → 断言 `main([...]) == 1`）
    与 `:211-213` 的 `test_cli_returns_zero_on_the_real_dataset`（`:212` 断言
    `main(["--seed","42","--verify"]) == 0`，`:213` 断言 `"两次生成 diff 为空" in capsys.readouterr().out`）——
    **同一个 `main()`、同一组 argv、同一个退出码、同一句 stdout，`tests/unit` 全都断言过了。**
    ⚠️ **这条直接倒置了实验 B 的搜索方向**（Phase 3）：初稿按「离单测最远」把
    `agenerp/seed/__main__.py` 的退出码映射排在**第一档**，而实读之后它是**离单测最近**的一档，
    逐条会被上面两条测例正面撞死。`checks.verify()` 由 `:194-202` 覆盖、`model.py` 常量由
    `tests/unit/test_seed_model_constants.py` 覆盖，**三档全被覆盖**。
13. **但 `tests/unit` 走不到 `__main__` 卫句**（本条是 Baseline 12 留下的唯一缝隙，也是 D4 的依据）：
    `agenerp/seed/__main__.py:69-70` 逐字
    `if __name__ == "__main__":` / `    raise SystemExit(main())`。
    测试是 `import main` 直接调，**从不经过这两行**；而 `python3 -m agenerp.seed` **只经过这两行**。

14. **§14.6 与它的 `### 它**不**覆盖什么` 小节此刻只在工作树里，不在 `main` 上**
    （评审第 2 轮抓出的、与本节开头「全部在 `main`（`7a09ef7`）上实读」冲突的一条）：
    `git show HEAD:docs/architecture/system-baseline.md | wc -l` → **785 行**，
    该小节在 HEAD 上**只有 `:715` 一处**（§14.5）；工作树版本有两处（`:715` / `:838`），
    第二处落在 `0120-1` 未入库的 +69 行里。
    → 本 plan 引用 `:838` 时**必须标明它取自未入库工作树**，且开工时重读（Baseline 顶部的硬前置一旦满足，它就在 `main` 上了）。

**⚠️ 全篇 job 计数口径（一次写死，后文所有「13 个 job」「其余 12 个」按此读）**：
起草时 `gates.yml` 为 **M = 11 个 job 键**（Baseline 6），本 plan 纯追加 2 个 → **M+2**。
后文为可读性写具体数字 **13 / 12**，那是**在 M = 11 成立时的值**；
⚠️ **开工时若实读到的 M 不是 11**（前驱或并行 plan 改过它），
**以 `M+2` / `M+1` 为准，并把实读值就地记进本 plan**，不得照抄 13。

## Goals

- `gates.yml` 上存在服务端复跑面，覆盖 `python3 -m agenerp.seed --seed 42 --verify`
  与 `ruff check agenerp tests/unit tests/contracts` 两条命令，**各自独立判退出码**。
- **（硬判据，必须过）** 两个新 job **各有至少一条变异实证**，证明「变异 → 该 job 红」。
- **（二态判据 A，只管 `lint`）** `lint` 的隐形性**已证**（变异 → `lint` 红、其余 12 个 job 全绿），
  **或者**本 plan / §14.7 / `docs/masterplan/STATE.md` **三处均载有那句逐字的
  「未能证明 `lint` 抓得到此前 CI 抓不到的东西」**。
- **（二态判据 B，只管 `seed-selfverify`）** 同上句式，主语换成 `seed-selfverify`。
  ⚠️ **初稿写的是「尽力证明……证不出就照实记」，那是一条两种结局都满足的 Goal，不可证伪**（评审第 1 轮抓出）；
  ⚠️ **第 1 轮的修法只改了一半**：它把两个 job 并成「两态**之一**」，
  于是「② 成立」就能打勾，**`lint` 未证且未记录也满足**（评审第 2 轮抓出）。
  现在是**每个 job 各一条**，必须**各自**落在二态之一。
- `main` 的 `push` 权威运行上全部 job `success`，落地 sha 与 PR 上跑绿的 head **逐字同一个**。

## Non-Goals

- **不改任何一条既有 job**（`gates.yml` 前 404 行逐字节不动），**不删 job**，**不改触发条件**。
- **不改 `missions/**`**（角色 B 禁区）——因此**本 plan 交付的不是 `GATE_VERIFY` 可复跑面**，
  ⚠️ **CI 覆盖 ≠ `GATE_VERIFY` 可复跑 ≠ 门禁形态，三者不得混为一谈。**
- **不改 `tests/gates/**`**（红线 1）、**不新增门禁**、**不改 `tools/gates/**`**、**不动 `tools/gates/expected-red.txt`**。
- **不改 `agenerp/**` 的任何产品代码**，**不改 `pyproject.toml`**，**不改 `tests/**`**
  （除变异实验中的临时改动，全部必须 revert 并实测复原）。
- **不改 `docs/masterplan/DECISIONS.md`**（红线 3）；`STATE.md` **只追加**（红线 5）。
- **不推动工作项 7 / 9 从 `planned` 变 `done`**（卡点都是「从 `expected-red.txt` 划掉」这条人裁定题）。
- **不修 ruff 报出的任何问题** —— 本机实测 `All checks passed!`，本 plan 押的就是这个前提；
  若 CI 上因版本差异报出问题，处置见 `## Deferred But Adjudicated` 的固定处置，**不放宽 lint 配置**。

## Task Route

- Type: `verification or audit work`（CI 判据面的覆盖扩展）
- Owner Docs: `docs/architecture/system-baseline.md`（新增 §14.7）·
  `docs/context/project-context.md` 的验证命令表两行 · `docs/backlog/p0-foundation-roadmap.md`（追加一行）
- Skill Selection Basis: `none`。方法是「往 `gates.yml` 纯追加 job + 变异实证」，
  `docs/skills/README.md` 的 Skill Registry 里没有对应条目（最近的 `code-quality-audit-prompt.md`
  是审代码质量，不是搭复跑面）。草案评审用 `plan-audit-prompt.md`，那是**评审者**的技能，不是本 plan 的执行技能。

## Infrastructure And Config Prereqs

- **不需要 docker、不需要活站点、零 env 变量**（两条命令都是纯本地进程）。
- 需要 `gh` CLI 已认证（取 run id 与 job 结论）。
- 需要网络（CI runner 上 `pip install ruff==<pin>`）。
- 回滚：本 plan 只往 `gates.yml` 末尾追加，回滚 = `git revert` 那一个提交。
- **无破坏性写入**：不调用 `apply_pack` / `execute_plan` / `drop_columns` 中的任何一个，
  也不对活站点做任何写 —— `ai-autonomy-policy.md` 那两行 `plan-first` 的 Required Evidence **不适用**。
  **这是排除，不是豁免。**

## Execution Plan

### Phase 1 - 授权面重摆 + 两个设计决策（一行 `gates.yml` 都不改）

Status: completed
Targets: `docs/architecture/system-baseline.md`（新建 §14.7 中承载 **D0–D3 四条决策**的那几段）
Skill: `none`

- Item Types: `Proof | Decision`
- Prereqs: 无

- [x] **Proof（本 Phase 的第一件事，先于任何 Decision）：工作树前置核对。**
      `git status --porcelain -- docs/architecture/system-baseline.md docs/context/project-context.md
      docs/backlog/p0-foundation-roadmap.md` → **必须无输出**（即 `0120-1` 的回填已入库）。
      ⚠️ **有输出就停**：把情况写进 `docs/masterplan/STATE.md` §3 等人，**不自行 stash 别人的工作**
      （理由见 `## Current Baseline` 顶部与 Baseline 14：stash 会当场改变本 plan 的写作前提）。
      同时重读 `docs/architecture/system-baseline.md` 的现时行数与 `### 它**不**覆盖什么` 两处的现时行号，
      **把实读值记进本 plan**（起草时工作树为 `:715` / `:838`，`main` 上只有 `:715`）。
      - Skill: `none`
- [x] **Decision D0：两条命令留在同一个 plan 里（Minimum Rule 4「One plan, one result surface」的当面裁定）。**
      ⚠️ **初稿全篇没有裁定这条规则，而 D3 自己的理由恰是反对它的最强论据**（评审第 1 轮抓出）：
      D3 逐字写「两条命令的**所有权与重开事件完全不同**」——「所有权不同、重开事件不同」几乎就是两个结果面的定义。
      **佐证还有三条**：D2 只为 ruff 半边存在；六条 Deferred 里三条只关 ruff；实验 A 与实验 B 的失败分支不对称。
      **裁定：保持一个 plan。** 唯一共享的关闭判据逐字是——
      **「`docs/masterplan/STATE.md` 2026-08-23T01:00Z 行记的那笔四条命令零 CI 覆盖的账，被一次 `main` `push`
      权威运行全绿一次性结清」**；两条命令是同一笔账的最后两项，分开关会让这笔账**永远差一半**。
      **被否候选**：拆成两个 plan —— 否掉，理由是 **D1 的授权面（本仓最高风险动作）要重摆两次**，
      而 `docs/plans/00-plan-authoring-and-execution-guide.md` Minimum Rule 4 自己写着
      「Multi-module extraction or migration that shares the same behavioral contract and closure criteria
      is still ONE result surface — **do not over-split**」。
      **残余风险照实记**：D3 的所有权论据**可以被反读成「这是两个结果面」**；
      本裁定押的是「共享关闭判据」这一侧，**押错的代价是关闭时两半状态不一致**——
      因此实验 A 与实验 B **必须各有一条对称的写死失败分支**（见 Phase 3），不许只给其中一条。
      - Skill: `none`
- [x] **Decision D1：动 `main` 上 `.github/workflows/**` 这一次凭什么（第五次重新摆上台面，不得默认继承）。**
      三个候选与代价必须逐条写进 §14.7：
      | 候选 | 内容 | 代价 / 后果 |
      |---|---|---|
      | (a) | 按 `ai-autonomy-policy.md` 的字面 `blocked` 停手，整件事交人 | 这两条命令此后永远零服务端复跑面；而「判定面漏一块，循环就不会自己发现」正是 `missions/p0-foundation.json:24` 已吃过一次的亏 |
      | (b) | 在「纯追加 = 加严」这条**未经追认**的先例上继续走，并把机械可核的加严判据（Baseline 10 那五条）写进保命闸 | 欠一次人的追认 |
      | (c) | 先请人裁定再动 | 本 mission 无同步的人，等价于 (a) |
      ⚠️ **必须当面引用那条否掉本候选证据基础的规则**：`ai-autonomy-policy.md:9` 逐字
      「AI must not loosen protected areas … **without explicit human confirmation or owner-doc evidence
      marked as human-approved**」。`2220-2` / `1206-2` / `2325-2` / `0120-1` **四个先例全是 AI 起草的、
      没有一条带人的批准标记**，因此**它们不构成授权**；**本 plan 的独立草案评审同样不构成授权**（评审者是子代理）。
      诚实措辞只能是「**在未经追认的先例上继续走，欠一次追认**」，**不是**「沿用既有先例」。
      **⚠️ 先例从 4 个变成 5 个不减轻这条风险，逐字写明。**
      **(a) 分支的写死处置**（免得它成为没有出口的候选）：一行 `gates.yml` 都不改，把 D1 的完整论证写进 §14.7 与
      `STATE.md` §3（**只追加**），plan 置 `Plan Status: deferred`，重开事件为「人对
      `.github/workflows/** = blocked` 给出裁定时」。
      - Skill: `none`
- [x] **Decision D2：ruff 的版本怎么钉。**
      候选三条：
      (i) `pip install ruff`（不钉）—— **否掉**：ruff 的规则集随版本变，不钉等于让一次上游发布把 `main` 变红，
          而红因与本仓任何一次改动都无关；
      (ii) **`pip install ruff==0.14.1`（钉在本机实测的那一版）—— 选它**；
      (iii) 把版本钉进 `pyproject.toml` 的依赖组再由 CI 装 —— **否掉**：`pyproject.toml` 现在**没有**任何依赖声明，
          为一条 lint 命令新开一个依赖组是超出本 plan 结果面的结构改动，且它同时改了本机与 CI 两侧的口径。
      **残余风险照实记**：版本钉在 `.github/workflows/**` 这个 `blocked` 文件里，
      **将来升 ruff 必须再动一次这个文件**（又要重摆一次 D1）；且**本机侧仍然没有钉**，
      本机装了别的版本时两侧会不一致 —— 该不一致**本 plan 不消除**，登记进 Deferred。
      - Skill: `none`
- [x] **Decision D3：两条命令放一个 job 还是两个 job。**
      候选：
      (i) 追加成 `unit-and-contracts` 的第 ③④ 两个 step —— **否掉**：`steps` 默认 fail-fast，
          `tests/unit` 红时后面三步全不跑，一次运行只能报最靠前的那个问题；
          且它会把**四条归属线完全不同**的命令并进一个 job 名（现名逐字是「单测与契约测试（439 条）」，
          塞进 lint 与种子自验之后该名字当场变假）；
      (ii) 一个新 job 装两条命令（两个独立 step）—— 与 `0120-1` 的 D2 同形；代价是两条之间仍 fail-fast；
      (iii) **两个独立的新 job —— 选它**。
      **选 (iii) 的理由，逐条**：① 两条命令的**所有权与重开事件完全不同**
      （`agenerp.seed --verify` 归工作项 7 的生成器；`ruff check` 是全仓 lint，归任何改 Python 的 plan），
      合成一个 job 会把两条归属线并成一个退出码 —— 这正是 `0120-1` D2 写死的理由，本 plan 只是把它推到底；
      ② 两者并行跑，**互相看得见对方的红**，不受 fail-fast 遮蔽；
      ③ ruff 需要 `pip install ruff==…`，seed 自验**什么都不用装**，分开可以让后者的 job 更薄。
      **代价照实记**：job 键从 **11 → 13**，多一次 checkout/setup 开销（两个 job 各约十几秒，并行）。
      ⚠️ **不得把 (iii) 说成「消除了 fail-fast 风险」**——它只是把两条命令之间的 fail-fast 消除了，
      **每个 job 内部只有一条判据 step，本来就没有第二步可被遮蔽**。
      - Skill: `none`

**Phase 1 实测证据（2026-08-23 开工时实读，不是起草时的回忆）：**

- 工作树前置：`git status --porcelain -- docs/architecture/system-baseline.md docs/context/project-context.md docs/backlog/p0-foundation-roadmap.md`
  → **无输出**（`0120-1` 与 `0120-2` 的回填均已入库）。`git status --porcelain` 全仓亦**无输出**，工作树全干净。
  开工 HEAD = `d45163c73a0b35fda848cd810d9a9f1200d18a28`（**不是**起草时的 `7a09ef7`）。
- `docs/architecture/system-baseline.md` 现时 **887 行**（起草时 `main` 785 / 工作树 854，**两个数都已过期**）；
  `### 它**不**覆盖什么` 两处现时行号为 **`:748`（§14.5）** 与 **`:871`（§14.6）**
  （起草时写的 `:715` / `:838` 已过期，未照抄）。§14.5 起于 `:638`，§14.6 起于 `:760`。
- `.github/workflows/gates.yml` 实读 **404 行**、**M = 11 个 job 键**
  （`gates-untouched` · `expected-red-ratchet` · `gates-l1` · `masterplan-links` · `roadmap-parseable` ·
  `loop-wiring` · `gates-l2` · `gates-l2-live` · `verdict-tool-untouched` · `gates-l2-seed` · `unit-and-contracts`）
  —— 与 Baseline 6 一致，**因此全篇「13 个 job」「其余 12 个」的口径成立**（M+2 = 13）。
- D0–D3 已逐条写进 `docs/architecture/system-baseline.md` **§14.7**（新建，起于 `:889`，本 Phase 结束时文件 978 行）。
- 本 Phase 结束时 `git diff --stat .github/ agenerp/ tests/` → **无输出**（一行代码/工作流都没改）。

Exit Criteria:

- [x] **工作树前置已满足**：那条 `git status --porcelain` 的实测输出（无输出）记在本 plan 内；
      `system-baseline.md` 的现时行数与两处小节行号已实读并记下
- [x] §14.7 内已写下 **D0 的裁定**（Minimum Rule 4、唯一共享关闭判据原文、被否候选、残余风险）
- [x] §14.7 内已写下 D1 的三候选表、被引用的 `ai-autonomy-policy.md:9` 原文、
      「五个先例不等于一个授权」的逐字措辞，以及 (a) 分支的写死处置
- [x] §14.7 内已写下 D2 / D3 的候选、选择、理由与残余风险
- [x] 本 Phase 结束时 `git diff --stat .github/ agenerp/ tests/` **无输出**
- [x] No owner-doc update required beyond §14.7 (this phase)

### Phase 2 - 追加两个 job + 本机前置自查 + 把 CI 预测写死（推变异之前）

Status: completed
Targets: `.github/workflows/gates.yml`（**只在文件末尾追加**）
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1 全部 Exit Criteria（D1 若落 (a) 分支则本 Phase 不执行）

- [x] **Decision D4 | Add：追加 job `seed-selfverify`（种子生成器自验），判据是「退出码 **和** stdout 断言」两条，不是只判退出码。**
      形态钉死：`name: 种子生成器自验（agenerp.seed --verify）` · `runs-on: ubuntu-latest` ·
      `timeout-minutes: 10` · `actions/checkout@v4` · `actions/setup-python@v5` with
      `python-version: "3.11"`（与既有 job 逐字相同）· **不装任何 pip 包**（⚠️ 依据是 **Phase 2 实读确认**「`agenerp/**` 只 import 标准库」，
      **不是 Baseline 12** —— Baseline 12 只讲测试覆盖，初稿把出处安错了，评审第 2 轮抓出）· 一个判据 step，`set -euo pipefail` 开头，两行：
      `python3 -m agenerp.seed --seed 42 --verify | tee /tmp/seed-selfverify.log` 与
      `grep -qE '^✅ 种子 42：' /tmp/seed-selfverify.log`。
      ⚠️ **为什么必须加那条 `grep`（评审第 1 轮抓出的活假绿路径，不是洁癖）**：
      只判退出码时，把 `agenerp/seed/__main__.py:70` 的 `raise SystemExit(main())` 改成 `raise SystemExit(0)`
      → 本 job **静默退 0、绿**，而 `tests/unit` 直接 `import main`、**从不经过那两行**（Baseline 13）→ **也绿**。
      **该 job 会为一次它根本没跑过的生成器背书。** 加上 stdout 断言之后这条路径当场变红。
      ⚠️ **`| tee` 会让退出码变成 `tee` 的** —— 因此 `set -o pipefail` 不是装饰，**漏掉它就是把退出码判据丢了**；
      本 plan 的形态与 `gates.yml:363-366` 已固化的 `… | tee … && grep -qE …` 先例同形。
      **候选与取舍**：(i) 只判退出码（初稿写法）—— 否掉，上面那条假绿路径是活的；
      (ii) **退出码 + stdout 断言 —— 选它**，这是**加严**（红线 2 安全）；
      (iii) 改成 `python3 -c "from agenerp.seed.__main__ import main; ..."` —— 否掉：
      那样跑的就不再是 `project-context.md` 记的那条 WBS 验收命令，**判据形态与被判对象脱钩**。
      **残余风险**：`grep` 的模式写死了那句中文文案，将来改文案会让本 job 红 —— 那是**它该红**
      （文案是判据的一部分），但必须在 §14.7 写明这层耦合。
      - Skill: `none`
- [x] **Add：追加 job `lint`（ruff 静态检查）。** 形态钉死：
      `name: 静态检查（ruff）` · 同上的 `runs-on` / `timeout-minutes` / `checkout` / `setup-python@v5` `"3.11"` ·
      `pip install ruff==0.14.1`（D2）· 一个判据 step，命令**逐字**
      `ruff check agenerp tests/unit tests/contracts`。
      ⚠️ **作用域三个目录逐字照抄 `docs/context/project-context.md` 的 `Lint / static check` 一行，一个字不加不减**
      —— 尤其**不得**扩到 `tests/gates`（`pyproject.toml` 的 `[tool.ruff] exclude` 已把它排除，
      理由逐字是「免得 lint 逼着去改裁判」）。**扩作用域是另一个结果面，本 plan 不做。**
      - Skill: `none`
- [x] **Proof：红线 2 机械自查五条（Baseline 10），每条给命令原文与实测输出。**
      ① 前缀性 `diff` 无输出：`N=$(git show HEAD:.github/workflows/gates.yml | wc -l)` 取**开工时实读的基线行数**
      （起草时为 **404**，⚠️ **不得照抄这个数**——前驱/并行 plan 可能已经改过它），
      再 `git show HEAD:.github/workflows/gates.yml > /tmp/base.yml && head -"$N"
      .github/workflows/gates.yml | diff - /tmp/base.yml` → **无输出**；
      ② job 键 **`M → M+2`**，M = **开工时实读**的基线 job 键数（起草时为 11，**不得照抄**），
         集合只增不减（既有键逐字未动）；
      ③ 禁用词自查（判据同 Baseline 10 ③，是「与改动前逐条相同」）：`grep -nE "continue-on-error|if: false|paths-ignore|\|\| true" .github/workflows/gates.yml`
      → 退 1 或只命中既有行（**必须逐条比对与改动前完全相同**）；
      ④ `if:` 出现处与改动前**逐字相同**（本 plan 新增的两个 job **一个 `if:` 都不带**）；
      ⑤ 无失败吞噬：两个新判据 step 都不接 `|| true`、不接 `continue-on-error`。
      - Skill: `none`
- [x] **Proof：保命闸 —— 本机前置自查，四条各判退出码并原样记下。**
      ① `python3 -m agenerp.seed --seed 42 --verify` → 期望 **0**，输出逐字含 `✅ 种子 42：`；
      ② `ruff check agenerp tests/unit tests/contracts` → 期望 **0**，逐字 `All checks passed!`；
      ③ `python3 tools/gates/check_expected_red.py` → 期望 **0**，三行判定行逐字为
         `判定模式：default —— 按 tools/gates/expected-red.txt 判定` /
         `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`；
      ④ `python3 -m pytest tests/unit -q && python3 -m pytest tests/contracts -q` → 期望 **0**
         （证明本 plan 没有把既有 CI 面碰坏；⚠️ 计数以**实测**为准，
         本 plan **不预言** `288` / `151` 这两个数 —— 队列里的 `2026-08-23-0120-2` 会新增单测，
         执行顺序若在本 plan 之前，`tests/unit` 的数就已经变了。**照抄一个会过期的数是自造漂移。**）
      - Skill: `none`
- [x] **Proof：把四条 CI 预测写死在本 plan 里（推之前写，不许事后补）。**
      预测 ①：PR 首跑 **13 个 job 全 `success`**，`seed-selfverify` 日志逐字含 `✅ 种子 42：两次生成 diff 为空，场景断言全过`；
      预测 ②：`lint` 日志逐字含 `All checks passed!`；
      预测 ③：Phase 3 的 ruff 变异（往 `agenerp/` 某个模块加一个未使用的 import）→ **`lint` 红，其余 12 个 job 全绿**；
      预测 ④：Phase 3 的 seed 变异 → **`seed-selfverify` 红**，且**尽力**让其余 12 个 job 全绿。
      ⚠️ **预测 ④ 是四条里最可能落空的一条，理由写在这里**：种子生成器被 `tests/unit` 覆盖得很密，
      大多数变异会**同时**让 `unit-and-contracts` 红 —— 那样只能证明「新 job 有牙齿」，
      **证不出「该变异对此前的 CI 隐形」**。找不到隐形变异时的处置写死在 Phase 3，**不临场发明**。
      - Skill: `none`

**Phase 2 实测证据（2026-08-23，全部为实跑，不是回忆）：**

**红线 2 机械自查五条**（基线为开工 HEAD `d45163c`）：

| # | 命令原文 | 实测输出 | 判定 |
|---|---|---|---|
| ① | `N=$(git show HEAD:.github/workflows/gates.yml \| wc -l)` → **N=404**；`git show HEAD:.github/workflows/gates.yml > /tmp/base.yml && head -"$N" .github/workflows/gates.yml \| diff - /tmp/base.yml` | **无输出**，退 **0** | 前 404 行逐字节未动 ✅ |
| ② | `diff <(grep -oE "^  [a-z0-9-]+:$" /tmp/base.yml) <(grep -oE "^  [a-z0-9-]+:$" .github/workflows/gates.yml)` | 唯一差异逐字为 `12a13,14` / `>   seed-selfverify:` / `>   lint:`；锚定计数 **12 → 14**（`push:` + M 个 job 键，M **11 → 13**） | 只增不减、既有键逐字未动 ✅ |
| ③ | `grep -nE "continue-on-error\|if: false\|paths-ignore\|\\\|\\\| true" .github/workflows/gates.yml` | 退 **0**，命中两行：`36:          CHANGED=$(git diff --name-only "$BASE" "$HEAD" -- 'tests/gates/**' \|\| true)` 与 `293:          CHANGED=$(… 'tools/gates/gate-verify.mjs' \|\| true)` | **与改动前逐条相同**（判据不是「零命中」）；`continue-on-error` / `if: false` / `paths-ignore` 三词零命中 ✅ |
| ④ | `diff <(grep -nE "^\s*if:" /tmp/base.yml) <(grep -nE "^\s*if:" .github/workflows/gates.yml)` | **无输出**，退 **0**（10 处 `if: always()` 的行号与内容逐字相同：`185/189/244/248/252/256/374/378/382/386`） | 两个新 job **一个 `if:` 都不带** ✅ |
| ⑤ | 人工复核两个新判据 step | `种子 42 自验（退出码 + stdout 断言）` 与 `ruff check（agenerp / tests/unit / tests/contracts）` 都**不接 `\|\| true`、不接 `continue-on-error`** | 无失败吞噬 ✅ |

`git diff --numstat -- .github/workflows/gates.yml` → **`37	0`**（**删除列为 `0`**，纯追加）。
`git status --porcelain -- tests/gates tools/gates missions agenerp pyproject.toml` → **无输出**（五处零改动）。
`yaml.safe_load` 实跑确认 job 键 13 个、两个新 job 的 `name:` 逐字为
`种子生成器自验（agenerp.seed --verify）` 与 `静态检查（ruff）`。

**D4 的「不装任何 pip 包」实读依据**（Phase 2 实读，**不是** Baseline 12）：
`grep -rhE "^\s*(import|from) " --include='*.py' agenerp/ | awk '{print $2}' | cut -d. -f1 | sort -u`
→ `__future__ agenerp argparse collections dataclasses datetime json logging os pathlib random re
subprocess sys tempfile typing urllib` —— **全部是标准库 + `agenerp` 自身**，零第三方依赖。

**保命闸 —— 本机前置自查四条，各判退出码**：

| # | 命令原文 | 退出码 | 输出 |
|---|---|---|---|
| ① | `python3 -m agenerp.seed --seed 42 --verify` | **0** | 逐字 `✅ 种子 42：两次生成 diff 为空，场景断言全过` |
| ② | `ruff check agenerp tests/unit tests/contracts` | **0** | 逐字 `All checks passed!`（`ruff --version` → `ruff 0.14.1`） |
| ③ | `python3 tools/gates/check_expected_red.py` | **0** | 三行逐字 `判定模式：default —— 按 tools/gates/expected-red.txt 判定` / `门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` |
| ④ | `python3 -m pytest tests/unit -q` / `python3 -m pytest tests/contracts -q` | **0** / **0** | 实测 `293 passed in 0.62s` / `151 passed in 0.06s`（⚠️ **不是**起草时的 `288`——`0120-2` 已新增 5 条单测，此处按实测记，不照抄会过期的数） |

**四条 CI 预测（写死在推任何一次 CI 之前）**：

- **预测 ①**：PR 首跑 **13 个 job 全 `success`**，`seed-selfverify` 日志逐字含
  `✅ 种子 42：两次生成 diff 为空，场景断言全过`。
- **预测 ②**：`lint` 日志逐字含 `All checks passed!`。
- **预测 ③**：变异实验 A（往 `agenerp/` 与 `tests/unit` 各加一处 `F401` 未使用 import）
  → **`lint` `failure`，其余 12 个 job 全 `success`**。
- **预测 ④**：变异实验 B（`agenerp/seed/__main__.py:70` 的 `raise SystemExit(main())` → `raise SystemExit(0)`）
  → **`seed-selfverify` `failure`**，且**尽力**让其余 12 个 job 全 `success`。
  ⚠️ **预测 ④ 是四条里最可能落空的一条**：种子生成器被 `tests/unit` 覆盖得很密，
  大多数变异会**同时**让 `unit-and-contracts` 红，那样只能证明「新 job 有牙齿」，
  **证不出「该变异对此前的 CI 隐形」**。找不到隐形变异时的处置写死在 Phase 3，**不临场发明**。

Exit Criteria:

- [x] `gates.yml` 为纯追加：`git diff --numstat -- .github/workflows/gates.yml` 的**删除列为 `0`**
- [x] 红线 2 五条自查的命令原文与输出全部记在本 plan 内，且全为期望值
- [x] 保命闸四条的退出码记在本 plan 内，全为 **0**
- [x] 四条 CI 预测已逐字写死在本 plan 内（时间上先于 Phase 3 的任何一次 push）
- [x] `tests/gates/**` / `tools/gates/**` / `missions/**` / `agenerp/**` / `pyproject.toml` **零改动**
- [x] `docs/logs/` 更新

### Phase 3 - 变异实证（PR 分支上跑 CI，证明两个新 job 有牙齿）

Status: completed
Targets: 临时变异提交（**全部必须 revert 并实测复原**）· 本 plan 的取证记录
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 2 全部 Exit Criteria

**⚠️ 裁判规则 4（「CI 连续 2 轮红即停机」）在本 Phase 内生效，口径照抄先例 `0120-1`**：
实验 A 与实验 B 的红是本 plan **事先逐字写死的预测**，且**两者之间隔着各自的 revert 全绿跑**
（顺序为 首跑绿 → A 红 → A-revert 绿 → B 红 → B-revert 绿），**因此不构成「连续 2 轮红」**。
⚠️ **若出现一次未被预测的红，它就是真的红**：立即按 `## Deferred But Adjudicated` 的固定处置停下。
**CI 预算**：本 Phase 预计消耗 5 次 run，实际次数在关闭时按实填，并对照裁判规则 4 的累计成本条款。

- [x] **Proof：开分支 `ci/0337-1-seed-lint-coverage`，推首跑。** 记 run id + 13 个 job 的结论 +
      两个新 job 的日志逐字行。与预测 ①② 逐条对照。
      ⚠️ **Baseline 7 那条推理的真正判据在这一跑，不在 Phase 2**（初稿把它写在 Phase 2 而 Phase 3 又以
      Phase 2 为前置，形成循环，评审第 1 轮抓出）：`python3 -m agenerp.seed` 不经过 pytest，
      `pyproject.toml` 的 `pythonpath = ["."]` 管不到它，能 import `agenerp` 靠的是 `-m` 把 CWD 插进 `sys.path`。
      **本 Phase 的首跑退出码就是它的判据。**
      若 runner 上 import 失败，处置是**在 job 里加 `pip install -e .`**（那是**加**，不是放宽），
      **不得**改成 `PYTHONPATH=. python3 …` 这种把成立条件藏进 env 的写法。
      - Skill: `none`
- [x] **Proof：变异实验 A（ruff）。** 往 `agenerp/` 下某个模块加一处 ruff 必报的违例
      （**首选未使用的 import，规则 `F401`**，因为它与运行时行为无关，不会连带弄红别的 job）。
      ⚠️ **同一个变异提交里必须在 `tests/unit` 或 `tests/contracts` 下也放一处违例**
      （评审第 1 轮：只动 `agenerp/` 的话，三个作用域目录只证了三分之一）。
      期望：`lint` **`failure`** 且日志点名两处的规则码与文件行号，**其余 12 个 job 全 `success`**。
      随后 revert，期望回到 13 绿。**两次 run id 都记下。**
      **写死的失败分支（与实验 B 对称，D0 要求，不许只给 B）**：
      若 `lint` 没红 → 先原样 `gh run rerun --failed` 一次；仍不红则**停**，
      把「本 job 对一个 ruff 本机确实会报的违例视而不见」原样记进本 plan 与 `STATE.md` §3，
      **不放宽、不猜根因**（裁判规则 3），plan 置 `deferred`。
      若 `lint` 红了但**别的 job 也红** → 照实记「未能证明隐形」，与实验 B 的 ③ 分支同口径处理，
      **不得把它写成「隐形已证」**。
      - Skill: `none`
- [x] **Proof：变异实验 B（seed 自验）。首选变异已由 Baseline 12/13 定出来，不再「按序试」。**
      ⚠️ **初稿把 `agenerp/seed/__main__.py` 的退出码映射排在「离单测最远」的第一档 —— 那是反的**
      （评审第 1 轮抓出）：`tests/unit/test_seed_deterministic.py:205-212` 正面断言了同一个 `main()`、
      同一组 argv、同一个退出码、同一句 stdout，逐条会被撞死；`checks.verify()` 与 `model.py` 常量
      也各自被覆盖。**三档全被覆盖，所以初稿的搜索按构造找不到隐形变异。**
      **写死的首选变异（Baseline 13 留下的唯一缝隙）**：把 `agenerp/seed/__main__.py:70` 的
      `raise SystemExit(main())` 改成 `raise SystemExit(0)`。
      `tests/unit` **直接 `import main`，从不经过 `__main__` 卫句** → 它看不见这个变异；
      而 D4 给 `seed-selfverify` 加的 `grep -qE '^✅ 种子 42：'` 会当场红（stdout 变空）。
      **期望：`seed-selfverify` 红，其余 12 个 job 全绿 —— 这正是「此前的 CI 对它完全隐形」。**
      **本机预筛（推 CI 之前必须先跑，两条同时满足才推）**：
      `python3 -m agenerp.seed --seed 42 --verify | tee /tmp/x.log; grep -qE '^✅ 种子 42：' /tmp/x.log`
      → 期望**非 0**；`python3 -m pytest tests/unit tests/contracts -q` → 期望 **0**。
      **写死的失败分支（不粉饰、不放弃取证）**：若上述变异未能拿到「其余 12 绿」，
      改用一个 `--verify` 与 `tests/unit` **都**抓得到的变异推一次 CI，期望
      **`seed-selfverify` 与 `unit-and-contracts` 同时红**；并在本 plan、§14.7、`STATE.md` §3 三处**逐字**记下
      「**未能证明该 job 抓得到此前 CI 抓不到的东西；它此刻是一层冗余复跑面，不是新增覆盖面**」。
      ⚠️ **这一条不许写成「牙齿已证」**，也不许因此就删掉这个 job —— 冗余复跑面本身仍有价值
      （WBS 验收命令进服务端复跑），但**价值的名字必须叫对**。
      - Skill: `none`
- [x] **Proof：全部变异 revert 后复跑一次，13 个 job 全 `success`。** 记 run id。
      **实验提交必须从分支历史上收尾干净**（`git log --oneline` 记下最终分支形态），
      落 `main` 的必须是「跑绿的那一个 sha」。
      - Skill: `none`

**Phase 3 实测证据（2026-08-23，分支 `ci/0337-1-seed-lint-coverage`，PR **#8**，共 5 次 run）：**

**开工实读的 job 计数**：`gates.yml` 基线 **M = 11**（Baseline 6 逐字吻合），
纯追加 2 个 → **13**。**因此全篇「13 个 job」「其余 12 个」的口径原样成立，无需按 `M+2` 改写。**

| # | run id | head sha | 内容 | 结论 |
|---|---|---|---|---|
| 1 | `32601490564` | `1debf1a` | 首跑（无变异） | **13 个 job 全 `success`** —— 与**预测 ①②** 逐条吻合 |
| 2 | `32601754671` | `eeaac53` | 变异 A：`agenerp/snapshot.py` 与 `tests/unit/test_seed_deterministic.py` 各加一处 `F401` | **`lint` `failure`（job `97100973890`），其余 12 个 job 全 `success`** —— 与**预测 ③** 逐条吻合 |
| 3 | `32601993786` | `17a9532` | `git revert` A | **13 个 job 全 `success`** |
| 4 | `32602225121` | `a4c2cbf` | 变异 B：`agenerp/seed/__main__.py:70` `raise SystemExit(main())` → `raise SystemExit(0)` | **`seed-selfverify` `failure`（job `97102151649`），其余 12 个 job 全 `success`**（含 `unit-and-contracts` `97102151664` `success`） —— 与**预测 ④** 逐条吻合 |
| 5 | `32602435912` | `9835019` | `git revert` B | **13 个 job 全 `success`** |

**首跑两个新 job 的日志逐字行**（run `32601490564`）：

- `seed-selfverify`（job `97100318957`，`名称：种子生成器自验（agenerp.seed --verify）`，墙钟 `22:06:07Z`→`22:06:13Z`，**6 秒**）：
  stdout 逐字 **`✅ 种子 42：两次生成 diff 为空，场景断言全过`**；判据 step 逐字三行
  `set -euo pipefail` / `python3 -m agenerp.seed --seed 42 --verify | tee /tmp/seed-selfverify.log` /
  `grep -qE '^✅ 种子 42：' /tmp/seed-selfverify.log`。
- `lint`（job `97100318919`，`名称：静态检查（ruff）`，墙钟 `22:06:06Z`→`22:06:14Z`，**8 秒**）：
  `Successfully installed ruff-0.14.1`，判据 step 输出逐字 **`All checks passed!`**。

**Baseline 7 那条推理的判据落在这一跑，已实测成立**：runner 上 `python3 -m agenerp.seed`
**不经过 pytest、不装 `agenerp`**（job 里连 `pip install` 都没有），仍能 import
——`-m` 把 CWD 插进 `sys.path` 这一机制在 `ubuntu-latest` / Python `3.11.16` 上成立。
**没有走「加 `pip install -e .`」那条处置分支。**

**实验 A 的红日志逐字**（job `97100973890`）：

```
F401 [*] `uuid` imported but unused
  --> agenerp/snapshot.py:16:8
F401 [*] `uuid` imported but unused
  --> tests/unit/test_seed_deterministic.py:10:8
Found 2 errors.
##[error]Process completed with exit code 1.
```

**两处规则码与文件行号都被点名，三个作用域目录里的两个各证一处**（`tests/contracts` 未放违例，
本 plan **不声称**该目录已被实证，只声称它在命令的作用域里）。
**其余 12 个 job 全 `success` —— 即这两处 `F401` 对 `main` 上原有的 11 个 job 完全隐形。**

**实验 B 的结论逐字（落在「找到隐形变异」这一支，不含糊）**：

> **`seed-selfverify` 的隐形性已证。** 把 `agenerp/seed/__main__.py:70` 的 `raise SystemExit(main())`
> 改成 `raise SystemExit(0)` 之后，run `32602225121` 上 **`seed-selfverify` `failure`，其余 12 个 job 全 `success`**
> ——**包括 `unit-and-contracts`（job `97102151664`，`success`）**。
> 该变异对此前 CI 上的全部 11 个 job 完全隐形，只有这个新 job 抓到了它。
> 红因是 stdout 断言：`tee` 到的日志为空 → `grep -qE '^✅ 种子 42：'` 退 1 → step `##[error]Process completed with exit code 1.`
> ——**这正是 D4 加那条 `grep` 所堵住的那条假绿路径，被一次真实的 CI 运行当场坐实。**
> **因此本 plan 不需要写「未能证明 `seed-selfverify` 抓得到此前 CI 抓不到的东西」那句话。**

**同理，`lint` 的隐形性亦已证**（实验 A：`lint` 红、其余 12 绿），
**本 plan 也不需要写「未能证明 `lint` 抓得到此前 CI 抓不到的东西」那句话。**

**本机预筛（推实验 B 之前实跑，两条同时满足才推）**：
`set -euo pipefail; python3 -m agenerp.seed --seed 42 --verify | tee /tmp/x.log; grep -qE '^✅ 种子 42：' /tmp/x.log`
→ **exit 1**（期望非 0 ✅）；`python3 -m pytest tests/unit tests/contracts -q` → **exit 0**，`444 passed in 0.73s`（期望 0 ✅）。
变异 B 期间 `ruff check agenerp tests/unit tests/contracts` → **exit 0**（确认没有污染实验 B 的归因）。

**变异全部复原的机械证据**：`git diff main..HEAD -- agenerp/ tests/ pyproject.toml` → **无输出**。
分支最终形态（`git log --oneline main..HEAD`）：

```
9835019 Revert "MUTATION-B: __main__ 卫句改成 raise SystemExit(0) …"
a4c2cbf MUTATION-B: __main__ 卫句改成 raise SystemExit(0) …
17a9532 Revert "MUTATION-A: 故意的 F401（两处，agenerp/ 与 tests/unit/ 各一）…"
eeaac53 MUTATION-A: 故意的 F401（两处，agenerp/ 与 tests/unit/ 各一）…
1debf1a feat(ci): plan-2026-08-23-0337-1 Phase 1-2 —— gates.yml 纯追加 seed-selfverify / lint 两个 job
```

⚠️ **实验提交要从落 `main` 的历史上收尾干净**：本分支带 4 个实验/revert 提交，
**因此它不用来落地**（PR #8 只用于实证，不合并）；落地走另一个从 `main` 新切、只含一个干净提交的分支（Phase 4）。

**CI 预算与裁判规则 4 的对照**：本 Phase 实耗 **5 次 run**（与预算逐字相同）。
两次红（run 2 / run 4）**都是本 plan 事先逐字写死的预测**，且两者之间隔着 run 3 的全绿跑，
顺序为 **首跑绿 → A 红 → A-revert 绿 → B 红 → B-revert 绿**，
**不构成「CI 连续 2 轮红」**。**本 Phase 未出现任何一次未被预测的红**，固定处置分支未触发。

Exit Criteria:

- [x] 首跑 run id + 13 个 job 结论 + 两个新 job 的日志逐字行记在本 plan 内
- [x] 实验 A 的红/绿两个 run id 与「其余 12 个 job 全绿」的实测结论记在本 plan 内
- [x] 实验 B 落在「找到隐形变异」或「未能证明隐形」二者之一，**结论逐字记下，不含糊**
- [x] 最终 revert 后的全绿 run id 记在本 plan 内
- [x] `git diff main..HEAD -- agenerp/ tests/ pyproject.toml` **无输出**（变异全部复原）
- [x] `docs/logs/` 更新

### Phase 4 - 落 `main` + owner doc 回填

Status: completed
Targets: `.github/workflows/gates.yml`（经 PR `--ff-only` 落 `main`）·
`docs/architecture/system-baseline.md` §14.7 · `docs/context/project-context.md` 的
`Lint / static check` 与 `Seed dataset acceptance` 两行 · `docs/backlog/p0-foundation-roadmap.md` ·
`docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-23.md`
Skill: `none`

- Item Types: `Add | Fix | Proof`
- Prereqs: Phase 3 全部 Exit Criteria

- [x] **Proof：开 PR、`--ff-only` 合进 `main`，取 `main` 的 `push` 权威运行。**
      **落地 sha 必须与 PR 上跑绿的 head 逐字同一个**（本仓已固化的判据，`1206-2` / `2325-2` / `0120-1` 三次先例）。
      记：PR 号 · 落地 sha（全长）· `main` `push` run id · 13 个 job 各自的 job id 与结论。
      **若权威运行不是全绿，走 `## Deferred But Adjudicated` 的固定处置，不得就地放宽。**
      - Skill: `none`
- [x] **Add：回填 `docs/architecture/system-baseline.md` §14.7**（该节由 Phase 1 建立并已写入 D0–D3，
      本项补全其余各段），与 §14.5 / §14.6 同规矩：
      **只记落点，不改写 §14 本体（`:131`–`:177`）任何一行**，也不改写 §14.1–§14.6 任何一行。
      内容：D0 / D1 三候选表与授权面诚实措辞（Phase 1 已写）· D2 / D3 / D4 ·
      两个 job 判什么（命令逐字 + 期望退出码 + `seed-selfverify` 的 stdout 断言）·
      变异实证结论（含实验 B 的两分支结论）· 残余风险。
      ⚠️ **必须带一个 `### 它**不**覆盖什么（这一段不许省，也不许读成更强的说法）` 小节**
      —— §14.5（`system-baseline.md:715`）与 §14.6（`:838`）都有同名小节，是本仓已固化的写法。
      该小节**至少**要写死这三条：
      ① **`lint` 只跑 ruff 的默认规则集**（实读 `pyproject.toml` 的 `[tool.ruff]` **没有 `select` /
         `extend-select`**，因此生效的只有 `E4,E7,E9,F`）——**不得**把「ruff 进 CI 了」读成「全仓静态检查到位」；
      ② `tests/gates` **不在 lint 作用域内**（`[tool.ruff] exclude`，理由是不让 lint 逼着改裁判）；
      ③ **CI 覆盖 ≠ 门禁形态 ≠ `GATE_VERIFY` 可复跑**，`missions/**` 一个字节未动。
      - Skill: `none`
- [x] **Add：`docs/context/project-context.md` 的 `Lint / static check` 一行**
      （⚠️ **标签是 `Add` 不是 `Fix`**：该行现在没有任何一处说它有没有复跑面，**这不是缺陷、不是漂移**，
      本 plan 是给它补一条此前不存在的事实。误标 `Fix` 会暗示一处并不存在的漂移。）
      —— 该行现在只写命令，**没有任何一处说它有没有复跑面**；本 plan 让它有了，
      **在既有句末追加**一句「⚠️ 2026-08-23 追加：它已由 `gates.yml` 的 job `lint` 覆盖（run `<id>`，
      ruff 钉 `0.14.1`）。**CI 覆盖 ≠ 门禁形态 ≠ `GATE_VERIFY` 可复跑**」。
      ⚠️ **该表「整体臃肿」是 `1041-1` 登记、`2107-1` 就地裁定过的条目**，重开事件逐字是
      「下一个需要往该表新增一行或改写既有行的 plan 开工时」——**本 plan 触发它**，
      处置**在该裁定内进一步收紧**：`2107-1` 的裁定逐字是「只**新增一行**、不动既有行结构」，
      **它是允许新增行的**；本 plan 自我限制为**只在既有句末补记、连新增行也不做**。
      ⚠️ **因此措辞不是「沿用同一裁定」而是「在该裁定内进一步收紧」**（评审第 1 轮抓出的引文不准）。
      - Skill: `none`
- [x] **Add：同文件 `Seed dataset acceptance` 一行**（⚠️ 同上，标签是 `Add`：
      该行那句「`GATE_VERIFY` 复跑不到它」**仍然为真、本 plan 一个字不改**，因此不存在要修的缺陷）。 该行逐字写着
      「⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它」——
      ⚠️ **那句话本 plan 一个字不改，它仍然为真**（`missions/**` 一个字节未动）。
      只在句末**追加**「⚠️ 2026-08-23 追加：它已由 `gates.yml` 的 job `seed-selfverify` 覆盖（run `<id>`）。
      **这是 CI 覆盖，不是对上面那句的否定**——两条通道互相独立，上面那句仍然成立、本次一个字未改」。
      **这段措辞照抄 `2325-2` 已固化的写法，不发明新说法。**
      - Skill: `none`
- [x] **Add：`docs/backlog/p0-foundation-roadmap.md` 追加一行
      `| 9 现状 · 生成器自验与 lint 的 CI 覆盖 |`**，**纯追加，既有行一个字不改**。
      ⚠️ **列形态必须与既有行一致**：开工时**先实读一条既有的 `| N 现状 · … |` 行照着写**
      （该表带「层」列，现状行形态为 `| N 现状 · … | <正文> | <L1 / L2> |`），免得把表格写坏
      —— `roadmap-parseable` job 校验的是 `Work Item Status` 块，**它不会替你挡这个错**。
      必须逐字写明：**工作项 9 的 `done` 判据（「用判定器对 `tests/gates` 全部 19 条 live 判定并 `success`」）
      与本 job 的两条命令互不重叠，本行是覆盖面的扩展、不是判据的替换**，
      **不得**被读成「工作项 9 因此可以 `done`」；**工作项 7 / 9 的状态值本行一个字不改。**
      - Skill: `none`
- [x] **Add：`docs/masterplan/STATE.md` §2 追加一条证据行**（红线 5：**只追加，不改写已有行**）。
      必须承接并改准 2026-08-23T01:00Z 行那句「四条本机命令在 `gates.yml` 里零 job 覆盖」——
      **上一行一个字不改**，本行写明：那四条**此刻全部有 CI 覆盖**（`tests/unit` / `tests/contracts` 由
      `0120-1` 的 `unit-and-contracts`；`agenerp.seed --verify` / `ruff check` 由本 plan 的两个新 job），
      并逐字重申「**`GATE_VERIFY` 复跑不到**这一点不因 CI 覆盖而改变，`missions/**` 一个字节未动」。
      - Skill: `none`
- [x] **Proof：陈旧陈述复核（两条 grep，逐条给结论）。**
      ① `grep -rn "零 job 覆盖\|零 CI 覆盖" docs/ | grep -v "^docs/logs/\|^docs/plans/\|^docs/masterplan/STATE"`
         —— 逐条确认每一处**要么仍为真、要么已按上一项改准**；
      ② `grep -rn "gates.yml.*个 job\|11 个 job 键\|10 个 job 键" docs/`
         —— 逐条确认 job 计数类陈述**要么已按实测改准，要么属于「带日期的历史证据行」**。
      ⚠️ **必须事先钉死的口径（评审第 1 轮抓出的自相矛盾）**：roadmap 的 `| N 现状 · … |` 行、
      `docs/logs/`、`docs/masterplan/`、`docs/plans/` 里的既有行**全部是带日期的历史证据，一律不改写**
      —— 它们在写下的当天为真，红线 5 与本仓的追加式惯例禁止改写。
      **「改准」只适用于不带日期的活陈述。** 初稿这条 grep 要求「改准」，
      与同 Phase 的「roadmap 既有行一个字不改」直接打架，本条即是那处矛盾的消解。
      **两份清单与逐条结论都记在本 plan 内。**
      - Skill: `none`

**Phase 4 实测证据（2026-08-23）：**

**落地（PR #9，与实证用的 PR #8 是两个分支）**：
从 `main` 新切 `ci/0337-1-seed-lint-coverage-land`，**只含一个提交、只含 `gates.yml`**
（实验/revert 四个提交全部留在 PR #8，**不进 `main` 历史**）。

| 项 | 值 |
|---|---|
| PR 号 | **#9**（实证用的是 **#8**，未合并） |
| PR #9 上跑绿的 run | `32602725539`（event `pull_request`，head `4476c470fb65e53d81faa1ee0cd84ea674330689`），**13 个 job 全 `success`** |
| 落地 sha（全长） | **`4476c470fb65e53d81faa1ee0cd84ea674330689`** |
| 落地方式 | `git merge --ff-only ci/0337-1-seed-lint-coverage-land` → `Updating d45163c..4476c47 / Fast-forward` |
| `main` `push` 权威运行 | **`32602915798`**（event `push`，head `4476c470f…`）→ **`success`** |

⚠️ **落地 sha 与 PR #9 上跑绿的 head 逐字同一个**：
`4476c470fb65e53d81faa1ee0cd84ea674330689` **=** `4476c470fb65e53d81faa1ee0cd84ea674330689`。
（`--ff-only` 快进，没有产生 merge commit，因此两者按构造相等，并已实测核对。）

**`main` `push` 权威运行 `32602915798` 的 13 个 job（job id + `name:` + 结论，逐条）**：

| job id | `name:` | 结论 |
|---|---|---|
| `97103765688` | 门禁未被改动 | `success` |
| `97103765736` | L2 慢门禁（零依赖启动） | `success` |
| **`97103765753`** | **静态检查（ruff）** | **`success`** |
| **`97103765758`** | **种子生成器自验（agenerp.seed --verify）** | **`success`** |
| `97103765790` | roadmap 引擎可解析 | `success` |
| `97103765805` | 单测与契约测试（439 条） | `success` |
| `97103765820` | 判定器未被改动 | `success` |
| `97103765823` | 循环联动冒烟 | `success` |
| `97103765826` | L1 快门禁 | `success` |
| `97103765837` | 预期红名单只能变短 | `success` |
| `97103765838` | 主计划引用不断链 | `success` |
| `97103765869` | L2 种子链（装载 + 站点侧对账） | `success` |
| `97103765893` | L2 全量 live 判定（19 条） | `success` |

**两个新 job 各有 `name:`，且上表按该 `name:` 逐条对上**：
`种子生成器自验（agenerp.seed --verify）` / `静态检查（ruff）`（`yaml.safe_load` 实证）。

**owner doc 回填的机械证据**：

| 文件 | `git diff --numstat` | 判定 |
|---|---|---|
| `docs/architecture/system-baseline.md` | `113	0` | **删除列 `0`**；`head -887 … \| diff - <(git show d45163c:…)` → **无输出**，即 **§14 本体（`:131`–`:177`）与 §14.1–§14.6 逐字节未动**；§14.7 起于 `:889` |
| `docs/context/project-context.md` | `2	2` | **两行都是句末追加**（同一行改写，`2` 增 `2` 删）；**文件行数 108 → 108 未变**，即**未新增行、未重构表结构** |
| `docs/backlog/p0-foundation-roadmap.md` | `1	0` | **纯追加**（删除列 `0`）；新行 `\| 9 现状 · 生成器自验与 lint 的 CI 覆盖 \| … \| L2 \|`，**3 个单元格 + 「层」列 `L2`**，与既有 `\| 9 现状 · … \|` 行（`:89` / `:90`）形态一致 |
| `docs/masterplan/STATE.md` | `7	0` | **纯追加**（删除列 `0`，红线 5）；§2 末尾一条证据行 + 6 条 `  · ` 子项，**既有行一个字未改** |

**工作项 7 / 9 的状态值一个字未改**：roadmap `:82`（工作项 7）与 `:88`（工作项 9）两行**未被触碰**
（`git diff` 只有 `:92` 一行新增）；新行内逐字写明「**工作项 7 / 9 的状态值本行一个字未改，仍 `planned`**」，
且逐字写明「工作项 9 的 `done` 判据与本行的两条命令**互不重叠**，本行是**覆盖面的扩展、不是判据的替换**，
**不得被读成「工作项 9 因此可以 `done`」**」。

**陈旧陈述复核（两条 grep，逐条给结论）**

⚠️ **事先钉死的口径**：roadmap 的 `\| N 现状 · … \|` 行、`docs/logs/`、`docs/masterplan/`、`docs/plans/`
里的既有行**全部是带日期的历史证据，一律不改写**（红线 5 与本仓的追加式惯例）。
**「改准」只适用于不带日期的活陈述。**

**grep ①** `grep -rn "零 job 覆盖\|零 CI 覆盖" docs/ | grep -v "^docs/logs/\|^docs/plans/\|^docs/masterplan/STATE"`
→ **2 条命中，逐条结论**：

| 行 | 内容 | 结论 |
|---|---|---|
| `docs/architecture/system-baseline.md:776` | §14.6 D1 候选表 (a) 格里的「439 条测试的零 CI 覆盖正是 `missions/p0-foundation.json:24` 已吃过一次的亏」 | **仍为真，不改**。它是 `0120-1` 落节时的**带日期历史证据**，讲的是**那之前**的状态；且 §14.1–§14.6 本 Phase 要求逐字节未动 |
| `docs/architecture/system-baseline.md:903` | §14.7 D0 里对 `STATE.md` 2026-08-23T01:00Z 行的**逐字引用** | **仍为真，不改**。它是引文，引的是一条带日期的账本行；那笔账**本轮已由 `STATE.md` §2 的追加行明写结清**，引文本身不因此变假 |

**结论：grep ① 零处需要改准。**

**grep ②** `grep -rn "gates.yml.*个 job\|11 个 job 键\|10 个 job 键" docs/`
→ 命中覆盖 `docs/plans/`（14 个文件）· `docs/logs/`（`08-21` / `08-22` / `08-23`）·
`docs/masterplan/STATE.md` 与 `archive/` · `docs/backlog/p0-foundation-roadmap.md`（`:84` / `:88`–`:92`）·
`docs/context/project-context.md`（`:52` / `:53` / `:55` / `:57` / `:61`）·
`docs/architecture/system-baseline.md`（`:471` / `:866`）。**按上面钉死的口径逐条分类**：

| 类别 | 命中 | 结论 |
|---|---|---|
| 带日期的历史证据（`docs/plans/` · `docs/logs/` · `docs/masterplan/**` · roadmap 的 `\| N 现状 · … \|` 行） | 除下面两类外的**全部**命中 | **一律不改写**。它们在写下的当天为真（`6` / `7` / `9` / `10` / `11` 个 job 键都是各自当时的实读值） |
| `system-baseline.md:471`（`main` 上 9 个 job 键，`1206-2` 的落地证据）· `:866`（锚定 `grep` → `12`，`0120-1` 的落地证据） | 2 处 | **不改**：同属带日期的落地证据；且 §14.1–§14.6 本 Phase 要求**逐字节未动** |
| `project-context.md` 的活陈述 | `:53` 逐字「`gates.yml` 上的第 **11** 个 CI job `unit-and-contracts`」 | **仍为真，不改**：本 plan 追加的两个 job 是**第 12 / 13 个**，`unit-and-contracts` **仍然是第 11 个 job 键**（实读顺序未变） |
| 同上 | `:55` / `:57` / `:61`（`gates-l2-seed` 是「第十个 job」· run `32572618933` 的「九个 job 全绿」等） | **仍为真，不改**：前者是**序数**（仍是第 10 个 job 键），后者是**某次具体运行的历史结论** |
| 同上 | `:52` | **本 plan 本轮新写的**，逐字含权威运行 `32602915798` 与 job `97103765753`，与实测一致 |

**结论：grep ② 零处需要改准**；job 计数类陈述**要么是带日期的历史证据、要么是仍然成立的序数**。

Exit Criteria:

- [x] PR 号 / 落地 sha（全长）/ `main` `push` 权威运行 run id / 13 个 job 的 job id 与结论全部记在本 plan 内
- [x] 落地 sha 与 PR 上跑绿的 head **逐字同一个**，该等式在本 plan 内被明写
- [x] §14.7 已建，且 §14 本体与 §14.1–§14.6 **逐字节未动**（`git diff` 该段无输出）
- [x] `project-context.md` 两行为**句末追加**，**未新增行、未重构表结构**
- [x] roadmap 与 `STATE.md` 均为**纯追加**（`git diff --numstat` 删除列为 `0`）
- [x] 工作项 7 / 9 的状态值**一个字未改**（仍 `planned`）
- [x] 两条 grep 的清单与逐条结论记在本 plan 内
- [x] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: **`needs revision`**（独立子代理，fresh session，task `a8fdde2b`）—— **6 条阻塞项 + 10 条 should-fix**。
  评审逐条实读复核了 Baseline 1–10 并**全部核准**（含 `grep -rn ruff .github/` 退 1、
  `ruff 0.14.1`、`gates.yml` 404 行 11 键、`agenerp/seed/__main__.py:26-27` 的落盘行为、
  `AGENTS.md:11` 与 `ai-autonomy-policy.md:81` 的原文、10 处 `if: always()` 全在取证/拆栈步骤上），
  并确认**无红线问题**。**6 条阻塞项逐条照实记，不粉饰**：
  ① **Baseline 里「工作树四个 `M` 与本 plan 改动面零交集」是假的** —— 其中**三个就是本 plan 自己的 Targets**
  （`system-baseline.md` / `project-context.md` / `p0-foundation-roadmap.md`），
  因此初稿写的保命措施「`git add` 只列本 plan 自己动的路径」**恰好会把 `0120-1` 未入库的工作裹进来**；
  同一缺陷也出现在对 `0120-2` 的判断上（那三个文件同样重叠，括号却只为 `agenerp/**` 辩护）。
  已改准两处，并新增「开工前 `0120-1` 文档必须先入库或 stash」的硬前置与
  「以 `git diff --cached --stat` 核对、不以 `git add` 参数为凭」。
  ② **Baseline 整个漏掉 `tests/unit/test_seed_deterministic.py`**（Minimum Rule 1），
  而 `:205-212` 已经断言了新 job 要判的**同一个 `main()`、同一组 argv、同一个退出码、同一句 stdout**
  —— 初稿把 `__main__.py` 的退出码映射排为「离单测最远」的第一档，**方向是反的**，
  按初稿的搜索按构造找不到隐形变异。已补进 Baseline 12/13 并重写实验 B。
  ③ **`seed-selfverify` 按初稿形态有一条活的假绿路径**：只判退出码时，把 `__main__.py:70` 的
  `raise SystemExit(main())` 改成 `raise SystemExit(0)` → 本 job 静默退 0 **绿**，
  而 `tests/unit` 直接 `import main`、从不经过卫句 → **也绿**，**该 job 会为一次它根本没跑过的生成器背书**。
  已新增 **D4**：判据改为「退出码 + `grep -qE '^✅ 种子 42：'` stdout 断言」（与 `gates.yml:363-366` 先例同形），
  并顺带把它变成实验 B 的首选隐形变异。
  ④ **`missions/p0-foundation.json:24` 错行号**（`_notes.commands` 在 `:23`，`:24` 是 `_notes.test`），
  两处不同引文被指向同一行号；`missions/**` 的 Protected Areas 位置也改准为「`missions/*.json`，第 9 行」。
  ⑤ **Minimum Rule 4 全篇未裁定**，而 D3 自己的「所有权与重开事件完全不同」几乎就是两个结果面的定义。
  已新增 **D0** 当面裁定（保持一个 plan；唯一共享关闭判据是「四条命令那笔账被一次权威运行结清」；
  被否候选与残余风险照实写），并给实验 A 补上与实验 B 对称的写死失败分支。
  ⑥ **Goal 2「尽力证明隐形，证不出就照实记」两种结局都满足，不可证伪**，无法被 Closure Gate 检验。
  已拆成一条硬判据 +一条二态判据。
  **10 条 should-fix 亦已全部吸收**：`|| true` 在 `gates.yml:36` / `:293` 有两处既有命中，
  「零命中」的说法改准为「与改动前逐条相同」· §14.7 必须带 `### 它**不**覆盖什么` 小节并写明
  **ruff 只跑默认规则集**（`pyproject.toml` 无 `select`）· runner 退出码的判据从 Phase 2 挪进 Phase 3（消除循环前置）·
  两个新 job 各钉 `name:` · 实验 A 的违例必须同时落在 `tests/unit` 或 `tests/contracts`（否则只证了三分之一作用域）·
  roadmap 带日期的历史行**一律不改写**（消解「改准」与「既有行一个字不改」的矛盾）·
  `project-context.md` 两项由 `Fix` 改标 `Add`（不存在要修的缺陷，误标会暗示一处并不存在的漂移）·
  固定处置那条 Deferred 补上 `Why Not Blocking Closure` · `2107-1` 的裁定引文改准为「在该裁定内进一步收紧」·
  「前 404 行」改为「前 N 行，N 为开工时实读」（与姊妹 plan `0337-2` 的约定对齐）。
- Independent draft review iteration 2: **`needs revision`**（独立子代理，fresh session，task `ad3bb503`）—— **5 条阻塞项 + 6 条 should-fix**。
  评审**独立复跑验证了第 1 轮 B3 的修法真的堵住了假绿**：把 `agenerp/seed/__main__.py:70` 改成
  `raise SystemExit(0)` 后，`set -euo pipefail; python3 -m agenerp.seed --seed 42 --verify | tee /tmp/x.log;
  grep -qE '^✅ 种子 42：' /tmp/x.log` → **exit 1**，而同一变异下 `pytest tests/unit -q` → **288 passed**
  ——**实验 B 的首选变异确为「对旧 CI 隐形」**，且未发现新的结构性假绿路径。
  Baseline 1/2/3/5/6/10/13 与 B4/B5/D1 的引文全部实读核准，**无红线问题**。**5 条阻塞项逐条照实记**：
  ① **「硬前置」只落在散文里，没有任何 checkbox 或 Exit Criteria 检查它** —— 第 1 轮 B1 认定的风险因此不可核。
  已把它落成 Phase 1 的第一个 `Proof` 项并补进 Exit Criteria。
  ② **`system-baseline.md:838` 不在 `main` 上**（HEAD 版共 785 行，该小节只有 `:715` 一处；
  `:838` 在 `0120-1` 未入库的 +69 行里），与 Baseline 顶部「全部在 `main` 上实读」直接冲突；
  且硬前置里「**或已 stash**」这一支会让 §14.6 当场消失，而 Phase 4 又要求「§14.1–§14.6 逐字节未动」。
  已新增 Baseline 14 并**删掉 `stash` 这个出口**。
  ③ **第 1 轮 B6 的修法只改了一半**：两个 job 被并成「两态**之一**」，于是 ② 成立就能打勾、
  **`lint` 未证且未记录也满足**；且 Phase 3 里「`lint` 红了但别的 job 也红 → 照实记」正是它宣称不存在的第三态。
  已拆成**每个 job 各一条**二态判据，Closure Gate 同步改。
  ④ **Baseline 12 两处行号错**：import 在 `:18` 不是 `:17`；`test_cli_returns_zero_on_the_real_dataset`
  在 `:211-213`，而被引用的 stdout 断言在 `:213`、**落在初稿所写区间之外**。已改准。
  ⑤ **Deferred 段与 Phase 4 逐字互斥**：一处写「沿用同一裁定」、另一处写「不是『沿用同一裁定』而是
  『在该裁定内进一步收紧』」；且 `2107-1` 的原文被引成「只新增行/**补记**」（原文无「补记」二字）。已统一。
  **6 条 should-fix 亦已吸收**：「`agenerp` 只 import 标准库」的出处由伪造的 Baseline 12 改为 Phase 2 实读 ·
  机械自查 ③ 的标题改成与其判据一致 · Phase 1 Targets 由「前三段」改准为「D0–D3 四条」并把 D0 补进 Exit Criteria ·
  工作树现状改准为 4 个 `M` + 3 个 `??` · job 键 `11 → 13` 改为「以开工实读为准」·
  Draft Review Record 补上 task id。
- Independent draft review iteration 3: **`acceptable as-is`**（独立子代理，fresh session，task `a05853c9`）
  —— **零阻塞项，达成共识。**
  评审对第 2 轮 5 条修法逐条独立复核并**全部确认成立**：① 硬前置已落成 Phase 1 第一个 `Proof` checkbox
  并进 Exit Criteria；② Baseline 14 **实测吻合**（HEAD 版 **785 行**、该小节只有 `:715`；工作树 **854 行**、
  `:715` / `:838` 两处，差值 **+69**），且全文 `stash` 只剩「**不自行** stash」，出口确已删除；
  ③ Goals 已拆成每 job 各一条二态判据、Closure Gate 明写「必须各自成立，不是二者之一」；
  ④ Baseline 12 的 `:18` / `:205-208` / `:211-213`（`:212` 判退出码、`:213` 判 stdout）**全对**；
  ⑤ Deferred 与 Phase 4 均已统一为「在该裁定内进一步收紧」，`2107-1:437` 引文逐字准确。
  **本轮另行实读核准**：`gates.yml` 404 行 / 11 个 job 键（键名与顺序逐字一致）·
  `grep -rn ruff .github/` 退 1 · seed 的唯一命中在 `:320` 注释、四条 seedsite 命令在 `:356/359/365/369`、
  `tee`+`grep` 先例在 `:363-366` · `|| true` 只有 `:36` / `:293` 两处 · `if: always()` 10 处全在取证/拆栈步骤 ·
  `.github/workflows/` 只有 `gates.yml` 一个文件（「13 个 job」口径成立）· `missions/p0-foundation.json:23`/`:24`
  分属 `_notes.commands`/`_notes.test` · `pyproject.toml [tool.ruff]` 无 `select`（默认规则集的说法成立）·
  四条本机命令实跑结论与本 plan 记录逐字一致 · **红线 1–7 无触及**、模板字段齐全、
  Anti-Slacking 禁用词零命中、六条 Deferred 均带重开事件 ·
  `roadmap-parseable` job 校验的是 `Work Item Status` 块，Phase 4 的追加行不会踩它。
  **5 条 should-fix（不阻塞）已吸收 4 条**：Deferred 里 `missions/…:24` 改准为 `:23`（与 Baseline 11 一致）·
  新增「全篇 job 计数口径」段，写明 13/12 是 **M = 11 时的值**、开工实读不符时以 `M+2`/`M+1` 为准 ·
  Phase 4 的 §14.7 由「新建」改为「回填」（该节由 Phase 1 建立）·
  roadmap 追加行补上「先实读一条既有现状行照着写」的列形态要求。
  **第 5 条不改，理由照实写**：评审指出 `2107-1` 回填后的现行重开事件其实是「人明确裁定要重构该表时」，
  本 plan 说「触发它写死的重开事件」略偏 —— 但本 plan 的处置（**只在既有句末补记、连新增行也不做**）
  比两版裁定**都更紧**，无实际影响；改它会引入一处与 `1041-1` / `2107-1` 两份记录都对不上的第三种表述。
  **共识达成，`Plan Status` 由 `draft` 改为 `active`。**

## Closure Gates

- [x] in-scope behavior is complete（两个新 job 落 `main` 且在权威运行上 `success`）
- [x] relevant docs are aligned（§14.7 · `project-context.md` 两行 · roadmap 追加行 · `STATE.md` 追加行）
- [x] verification has run：`python3 -m agenerp.seed --seed 42 --verify` ·
      `ruff check agenerp tests/unit tests/contracts` · `python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` ·
      CI：PR 首跑 + 变异实验 A（红/绿两跑）+ 实验 B + revert 全绿 + `main` `push` 权威运行
- [x] scoped verification is not conflated with full verification —— **本仓无全量套件**（无 build、无 typecheck）；
      本 plan 的覆盖面**不含**任何活站点命令，逐字记「verification scope limited：本 plan 只覆盖两条纯本地命令」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（轮次以 `## Draft Review Record` 的实际记录为准，本行不写死数）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— ⚠️ **执行者不自证，本行由 loop 的独立关闭审计打勾**
- [x] closure evidence exists in files
- [x] **红线自查五条**：① `tests/gates/**` 零改动 ② `.github/workflows/**` **纯追加**（删除列为 `0`，
      **前 N 行逐字节未动**，N = **开工时实读**的基线行数（起草时为 404，**不得照抄**），
      Baseline 10 五条全为期望值）③ `docs/masterplan/DECISIONS.md` 零改动、无新增 `R-x`
      ④ `missions/**` 零改动 ⑤ `docs/masterplan/STATE.md` 只追加不改写
- [x] **三条 Goal 分别打勾**：（a）两个新 job 各有 ≥1 条「变异 → 该 job 红」的实证（硬判据）；
      （b）**`lint` 的**隐形性已证，**或**三处均逐字写着「未能证明 `lint` 抓得到此前 CI 抓不到的东西」；
      （c）**`seed-selfverify` 的**隐形性已证，**或**三处均逐字写着同句式（主语换成 `seed-selfverify`）。
      ⚠️ **(b) 与 (c) 必须各自成立，不是「二者之一」**（评审第 2 轮抓出的漏洞）
- [x] **Minimum Rule 4 已被当面裁定**（D0），且共享关闭判据原文写在 §14.7 内
- [x] **两个新 job 各有 `name:`**，且 Phase 4 记录的 job 结论按该 `name:` 逐条对上

## Deferred But Adjudicated

### `missions/p0-foundation.json` 的 `commands.test` 仍然没有 `ruff` / `tests/contracts` / `agenerp.seed --verify`

- Classification: `watch-only residual`
- Why Not Blocking Closure: `missions/**` 是角色 B 禁区（`ai-autonomy-policy.md` Protected Areas，`blocked`），
  **loop 无权改**。⚠️ 本 plan 交付的是 **CI 侧**覆盖，**不得读成「这两条已进判定面」**——
  每轮 `GATE_VERIFY` 仍然看不见它们，loop 仍可能改坏而当轮不自知，**只是不再能合进 `main` 而不被发现**。
  ⚠️ 特别照实记：`missions/p0-foundation.json:23` 的 `_notes.commands` 自己写着「装上了再往这里加 lint」，
  **ruff 现在装上了，即该注释预告的条件已满足**，但动作在人手里。
- Successor Required: `no`（**人动作**）
- 重开事件：**人裁定改 `missions/**` 时**，或**第一次出现「lint / 生成器被改坏、当轮 `GATE_VERIFY` 绿、CI 上才红」时**
  （届时这条残余就有了活例证，应升级进 `STATE.md` §3）。

### ruff 版本只钉在 CI，本机侧没有钉

- Classification: `watch-only residual`
- Why Not Blocking Closure: D2 选 (ii) 之后 CI 侧是确定的（`ruff==0.14.1`），
  但本机装的是什么版本仍由环境决定；两侧不一致时表现为「本机绿 CI 红」或反之。
  本 plan **不消除**这条不一致——消除它要动 `pyproject.toml` 的依赖声明（D2 的候选 (iii)，已否掉）。
- Successor Required: `no`
- 重开事件：**第一次出现本机与 CI 的 ruff 结论不一致时**，或**人裁定给本仓引入依赖锁文件时**。

### 升 ruff 版本必须再动一次 `.github/workflows/**`

- Classification: `watch-only residual`
- Why Not Blocking Closure: 版本号写在一个 `blocked` 文件里，升级时又要重摆一次 D1 的授权面。
  **照实登记，不粉饰成「无成本」。**
- Successor Required: `no`
- 重开事件：**下一个要升 ruff 的 plan 开工时**（届时必须把 D1 再摆一遍）。

### `.github/workflows/** = blocked` 与红线 2「只禁变松」措辞不一致

- Classification: `out-of-scope improvement`（**人动作项**，`0027-2` / `1206-1` / `1206-2` / `2325-2` / `0120-1` 已连续登记）
- Why Not Blocking Closure: Phase 1 的 D1 已按写死的重开事件把它**重新摆上台面**，
  给出候选、选择与残余风险，**没有默认继承**。但改 Protected Areas 的 Rule 列等于替人定授权口径，loop 不做。
- Successor Required: `no`
- 重开事件：**人给出裁定**，或**下一个要动 `main` 上 `.github/workflows/**` 的 plan 开工前**（届时必须再摆一次）。

### `gates.yml` 的 job 数持续增长，且 `gates-l2` 与 `gates-l2-live` 覆盖面重复、前者未退休

- Classification: `out-of-scope improvement`（**人动作项**，`0027-2` / `1206-2` / `2325-2` / `0120-1` 已连续登记，本 plan 继续挂着）
- Why Not Blocking Closure: 退休任何 job 是**删除**动作，方向是变松；且会打掉「前缀性」这条本仓已固化的
  红线 2 机械判据。本 plan 只增不减，并把 job 数从 11 推到 13 —— **这条增长本身就是代价，照实记。**
- Successor Required: `no`
- 重开事件：**人裁定退休它**，或 CI 时长/并发额度成为实际瓶颈。

### `docs/context/project-context.md` 验证命令表整体臃肿

- Classification: `optimization candidate`
- Why Not Blocking Closure: 该条由 `1041-1` 登记、`2107-1` 就地裁定 —— `2107-1:437` 原文逐字是
  「本 plan 只**新增一行**、不动既有行结构」。
  **本 plan 的 Phase 4 再次触发它写死的重开事件**，处置是**在该裁定内进一步收紧**
  （本 plan 连新增行也不做，只在既有句末补记），**不重复裁**。
  ⚠️ **措辞与 Phase 4 那一项逐字一致**：**不是**「沿用同一裁定」（评审第 2 轮抓出的自相矛盾）。
- Successor Required: `no`
- 重开事件：**人明确裁定要重构该表时**。

### 取不到 CI 证据 / 结果与预测不符时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- Why Not Blocking Closure: 它不是一件被推迟的工作，而是**本 plan 失败时该怎么办**的事先写死。
  它在关闭时要么从未被触发（本 plan 走到底），要么已被执行（本 plan 置 `deferred`、根本不会走到关闭）
  —— 两种情形下它都不构成一个未完成的 in-scope 项。
- 处置逐字：原样复跑一次（`gh run rerun --failed`）→ 仍与预测不符则记录所有已跑命令与输出原文 →
  追加进 `docs/masterplan/STATE.md` §3（**只追加，不改写既有行**）→ 本 plan 置 `Plan Status: deferred`
  并在文件头写明重开条件 → **不放宽任何断言**、**不放宽 `[tool.ruff]` 配置**、**不缩小 lint 作用域**、
  **不禁用 job**、**不加 `continue-on-error`**、**不缩小触发范围**、**不改 `tests/gates/**` 与 `tools/gates/**`**、
  **不猜根因**（裁判规则 3）→ **不把分支合进 `main`**。
- **落 `main` 之后再红，处置相同**：原样复跑一次 → 仍红则把红因原文追加进 §3 并停下来交人。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或红因被一个独立 plan 修好之后。

## Closure

Status Note: **四个 Phase 全部执行完毕，两个新 job 已落 `main` 并在权威运行上 `success`。**
两条二态判据**都落在「已证」那一支**：`lint` 与 `seed-selfverify` 各有一条「变异 → 该 job 红、其余 12 个 job 全绿」
的实证，即两者各自抓到了此前 11 个 job 一个都抓不到的东西——**因此本 plan 三处都不需要写那句
「未能证明 … 抓得到此前 CI 抓不到的东西」**。四条 CI 预测在推之前逐字写死、事后**逐条吻合、无一落空**。
⚠️ **仍要照实读的三条**：① **CI 覆盖 ≠ 门禁形态 ≠ `GATE_VERIFY` 可复跑**，`missions/**` 一个字节未动，
每轮 `GATE_VERIFY` 仍然看不见这两条命令；② **`lint` 只跑 ruff 的默认规则集**（`E4,E7,E9,F`），
`tests/gates` 不在作用域内，`tests/contracts` 在作用域里但**未被变异实证**；
③ **授权面欠着一次人的追认**——五个先例全是 AI 自产的，落地跑绿**不等于已获授权**。
⚠️ **verification scope limited：本 plan 只覆盖两条纯本地命令**（`python3 -m agenerp.seed --seed 42 --verify`
与 `ruff check agenerp tests/unit tests/contracts`），**不含任何活站点命令**；
**本仓无全量套件**（无 build、无 typecheck），**scoped verification 不得读成全量绿**。

Closure Audit Evidence:

- Auditor / Agent: <independent subagent —— **执行者不自证**，由 loop 的 `CLOSURE_VERIFY` 步骤填写>
- Evidence（执行者侧已落盘的可复核证据）：
  - **本机命令原文 + 退出码**（落地后在 `main` `4476c47` 上复跑）：
    `python3 -m agenerp.seed --seed 42 --verify` → **0**（`✅ 种子 42：两次生成 diff 为空，场景断言全过`）·
    `ruff check agenerp tests/unit tests/contracts` → **0**（`All checks passed!`）·
    `python3 tools/gates/check_expected_red.py` → **0**（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致`）·
    `python3 -m pytest tests/unit -q` → **0**（`293 passed`）· `python3 -m pytest tests/contracts -q` → **0**（`151 passed`）
  - **commit sha**：落地 sha **`4476c470fb65e53d81faa1ee0cd84ea674330689`**（= PR #9 跑绿 head，逐字同一个）
  - **CI run id**：PR #8 实证五跑 `32601490564` / `32601754671` / `32601993786` / `32602225121` / `32602435912` ·
    PR #9 落地跑 `32602725539` · **`main` `push` 权威运行 `32602915798`（13 个 job 全 `success`）**
  - **红线自查五条**：① `tests/gates/**` 零改动 ② `.github/workflows/**` 纯追加（`37	0`，前 **404** 行逐字节未动）
    ③ `DECISIONS.md` 零改动、无新增 `R-x` ④ `missions/**` 零改动 ⑤ `STATE.md` 只追加（`7	0`）

Follow-up:

- 无。六条 Deferred 均带重开事件，**确认的缺陷一条都没往这里放**。
