# 2026-08-22-2325-2 把种子装载与站点侧对账搬上 CI（`gates-l2-seed`）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: **工作项 7（种子数据 —— B 半的 CI 覆盖）**
>   ⚠️ **不挂工作项 9，理由必须写在这里**：工作项 9 的 `done` 判据逐字是「`gates.yml` 上存在一个 job，
>   在 live 判定环境下用 `tools/gates/check_expected_red.py` 对 `tests/gates` 全部 19 条判定并 `success`」，
>   它**已经在 `main` 上成立**（run `32572618933`，`1206-2`）。本 plan 一寸都推不动它。
>   本 plan 借的是工作项 9 的**机制**（CI 上跑活站点的那套 job 形态），交付的是**工作项 7 的覆盖面**。
>   **一个结果面**：「种子链在全新 runner 站点上跑得通且对得上账」，一条关闭判据，一组证据。
> Last Reviewed: 2026-08-22
> Source: `docs/masterplan/STATE.md` §2 2026-08-22T20:55Z 行逐字登记的缺口
>   —— 「**验证范围（scoped，照实写，不得读成 full green）**：本仓无全量套件。本行覆盖 11 条本机命令，
>   **不含 CI**；其中**五条活站点命令 `GATE_VERIFY` 复跑不到**。」
> Related: `2026-08-22-2325-1-acc-operating-constant-fix.md`（**必须先关闭**）·
>   `2026-08-22-0027-2` · `2026-08-22-1206-2`（两个已落地的 CI job 先例）
> Audit: required

## Current Baseline

**这一节全部来自 2026-08-22 对 `20f5679`（`main`，工作树干净）的实读。**

- `.github/workflows/gates.yml` 在 `main` 上 **308 行、9 个 job**
  （`gates-untouched` · `expected-red-ratchet` · `gates-l1` · `masterplan-links` · `roadmap-parseable` ·
  `loop-wiring` · `gates-l2` · `gates-l2-live` · `verdict-tool-untouched`）。
- 权威运行 `32572618933`（event `push`，head `3503f2c`）**九个 job 全 `success`**。
- **`gates-l2-live` 的形态可直接照抄**（job 键在 `:210`，末步 `拆栈（无条件）` 收在 `:257`；
  `:258`–`:272` 已经是 `verdict-tool-untouched`（`:273`）的注释块，**不属于它**）：起栈 →（判定）→ 三段取证（服务状态 / backend 日志 /
  引导服务日志）→ `拆栈（无条件）` `if: always()` 跑 `down -v`。
  该 `down -v` 已实测在**失败路径上**也执行（`docs/backlog/gate-fixtures-pollute-the-live-site.md` 2026-08-22 段：
  12 容器 + 5 卷 + 网络全部 `Removed`）。**这一条是本 plan 敢在 CI 上装种子数据的前提**。
- **种子链此刻在 CI 上零覆盖**：`grep -n seedsite .github/workflows/gates.yml` **零命中**；
  `--load-masters` / `--load-documents` / `--verify-site` 只在本机跑过。
- **这个缺口有前科，不是理论风险**：同一类「本机独证」在工作项 5/6 上被 CI 抓出过一条真红
  （run `32509351108`，`::test_no_orphan_column_left_behind` 两次 attempt 都红），
  而本机 6 跑只红 1 次、当时被记成「不可复现」。根因（`bench execute` 的 `if ret:`）后来由
  `2026-08-22-0228-2` 查实。**本机绿 ≠ 全新站点绿，这在本仓是实测事实。**
- **种子链尤其可疑**：`2107-1` / `2107-2` 的活站点证据全部取自**同一台本机**的站点循环；
  装载器没有 teardown，幂等靠业务字段过滤。全新 runner 站点是它**从未跑过**的输入。
- **点名最可能的那条分歧，不含糊**：9 项对账里 `_overdue_checks`（`agenerp/seedsite.py:802`–`:824`）
  判的是两张发票的 `status == "Overdue"`，而那个值是**站点拿真实时钟跟 `due_date` 比出来的**，
  且依赖 `scheduler` 服务（`docker-compose.yml:250`）真的跑过一轮。该函数自己的 docstring 就写着这条限定。
  **在一个刚起几分钟的 runner 站点上，这是最可能红的一项。**
  ⚠️ 缓解事实（已核）：`2107-2` 的本机证据也是从 `down -v` 冷起测的，所以本机那边不是「温站点」，
  但**冷起 ≠ 全新 runner**，这条仍是本 plan 要去证实或证伪的头号候选。
- **授权面（必须重新摆上台面，不得默认继承）**：`docs/context/ai-autonomy-policy.md` 给
  `.github/workflows/**` 定的是 `blocked`，与 `AGENTS.md` 红线 2「只禁**变松**」措辞不一致。
  该不一致由 `0027-2` 登记、`1206-1` / `1206-2` 各自重述，**至今未由人裁定**；
  `1206-2` 的 Deferred 逐字写死重开事件：「**下一个要动 `main` 上 `.github/workflows/**` 的 plan 开工前
  （必须重新摆上台面，不得默认继承）**」。**本 plan 就是那个 plan，事件已触发**，Phase 1 的 `Decision` 处置它。
- **两个 CI 守卫与本 plan 的关系（实读脚本体得出，不是推测）**：
  `gates-untouched` 只 diff `tests/gates/**`；`verdict-tool-untouched` 只 diff
  `tools/gates/check_expected_red.py` 与 `tools/gates/gate-verify.mjs`。
  **本 plan 这三个路径一个字节都不动**，因此两个守卫都会走「未触及」分支。
- **一条已知的、必须写在起草阶段的风险**：`verdict-tool-untouched` 的「触及 + 带 trailer → 放行」出口
  在同一 sha 上**不可复现**（`STATE.md` §3 的 `[open]` 行）。**它不影响本 plan**（本 plan 不触及判定器），
  但若执行期意外触及，处置是 `gh run rerun --failed` 原样复跑，**不是**改守卫脚本体。
- **前驱依赖**：`2026-08-22-2325-1` 修 `ACC_OPERATING` 之前，`--load-masters` 会打出一条 `⚠️` 告警行。
  在缺陷仍在时把这条链搬上 CI，等于把「带着已知缺陷也算绿」固化进 CI。**因此本 plan 排在它后面。**

## Goals

- `main` 上的 `.github/workflows/gates.yml` 存在一个新 job，在**全新 runner 站点**上跑完整种子链
  （`--load-masters` → `--load-documents` → 幂等复跑 → `--verify-site`）并 `success`，
  且该结论来自 `main` 的 `push` 权威运行、有 run id。
- 该 job **有牙齿**：一次变异实验证明它在种子链坏掉时会红，且红得指名道姓。
- 「工作项 7 的 B 半只在本机验证过」这句话在 `main` 上不再成立，改准落进 roadmap 与 `STATE.md`。
- ⚠️ **明确不追求的**：本 plan **不使**工作项 7 或 9 的状态值变动，**不使**种子链的三条站点侧断言成为门禁。

## Non-Goals

- **不动 `tests/gates/**` 一个字节**（红线 1），不新增门禁、不改判据。
  本 job 判的是 **CLI 退出码**，与 `tests/gates/**` 的 19 条互不重叠。
- **不改 `tools/gates/**`**（判定器与名单都不碰），因此不触发 `verdict-tool-untouched` 的 trailer 分支。
- **不删除、不禁用、不缩小任何既有 job 的触发范围**，不加 `continue-on-error`（红线 2）。
  新 job 是**纯追加**，`main` 上现有 308 行**逐字节不动**。
- **不退休 `gates-l2`**（`0027-2` / `1206-2` 已登记为人动作项，方向是变松）。
- 不修 `verdict-tool-untouched` 的 `|| true` 假阴入口与 trailer 出口不可复现（均为已登记的人裁定题）。
- 不给种子链补门禁形态（红线 1，人动作）。
- 不改 `docs/masterplan/DECISIONS.md`、不改 `missions/**`。

## Task Route

- Type: `verification or audit work`（交付的是**覆盖面**，不是新行为）+ `deployment`（改 CI）
- Owner Docs: `docs/architecture/system-baseline.md` **§14.5**（本 plan 新建；`§14` 本体是 Spike 10 的结论出处，`:180` 逐字「本节**只记落点，不改写 §14 任何一行**」，CI/判定口径历来写在 §14.x 子节，`0027-1` / `1206-1` / `1206-2` 都写在 §14.4）·
  `docs/context/ai-autonomy-policy.md`（Protected Areas）· `docs/backlog/p0-foundation-roadmap.md` 工作项 7 / 9
- Skill Selection Basis: `none`。落地形态（分支 → PR → 跑绿 → `--ff-only` 合 `main`）已由
  `2026-08-22-1206-2` 在本仓固化并实测过一次，照抄它的步骤即可，`docs/skills/README.md` 无更贴切的技能。

## Infrastructure And Config Prereqs

- GitHub Actions runner `ubuntu-latest`，docker + compose 由 runner 自带（`gates-l2-live` 已实测可用）。
- **站点名由 argv 给，不由环境变量给 —— 这一条起草时写错过，就地改准**：
  `agenerp/seedsite.py:856`–`:858` 实测「`--site` 为空即 `print(...)` 并 `return 2`」（`:855` 是**上一个**、
  管「需要且只需要一个动作」的守卫的 `return 2`，别引错），
  `client_from_env(args.site)` 取的是 **argv**。`AGENERP_SITE` 被 `snapshot.py` / `oob.py` / `pack.py` /
  `site.py:183` 消费，**`seedsite.py` 根本不读它**。实测 `python3 -m agenerp.seedsite --load-masters` → **exit 2**。
- 因此 job 里四条命令**每一条都必须带 `--site frontend`**，逐字写死：
  ① `python3 -m agenerp.seedsite --load-masters --site frontend`
  ② `python3 -m agenerp.seedsite --load-documents --site frontend`
  ③ 原样复跑 ②，**并对其输出施加幂等断言** `grep -qE '^合计：新建 0 '`（**断言归第 ③ 步，不归 ④**；
     ④ 是 9 项对账，与幂等无关。两处写法必须一致，否则实验③会打在一个没有断言的步骤上）
  ④ `python3 -m agenerp.seedsite --verify-site --site frontend`
- job 内环境变量只需两个（沿用 `gates-l2-live` 的值）：`AGENERP_SITE_URL=http://127.0.0.1:8080` /
  `AGENERP_ADMIN_PASSWORD=admin`（**注意端口是 8080，不是本机的 18080**）。
  `AGENERP_SITE` 一并带上无害，但**不得把它当成站点名的来源**。
- **无新 secret、无新外部服务。** 种子装载只打站点自己的 REST 面。
- **回滚策略**：新 job 是纯追加，回滚即 `git revert` 那一次提交；
  CI 站点由 `拆栈（无条件）` `if: always()` 的 `down -v` 负责，不留任何持久状态。
- **对活站点的非破坏性写 —— `ai-autonomy-policy.md` Protected Areas 末行要求「逐字写明本次改动之后
  站点侧回滚是否仍然只能手工做」，那一行明写「不许略过不谈」，这里当面交代**：
  本 plan 驱动的正是 `SiteClient.create_doc` / `ensure_doc` / `submit_doc` 与 `seedsite.py` 的装载路径，
  且把它开到一类**新站点**（CI runner）上。
  ① **CI 站点的回滚不是手工的** —— 是 `拆栈（无条件）` `if: always()` 里的 `down -v`，
  已实测在失败路径上照跑（12 容器 + 5 卷 + 网络全部 `Removed`）。
  ② **但装载器本身仍然零 teardown、零 cancel** —— 代码侧一行回滚都没加。
  **在任何非一次性站点上（含本机常驻站点），回滚仍然只能手工做**（`down -v` 冷起或 `bench restore`）。
  ③ 本 plan **不改变**这个事实，也不假装改变了它。
- **对外动作**：本 plan 要推分支、开 PR、合 `main`。这与 `1206-2` 同形态。
  **若执行期任何一条 CI 证据取不到，处置是把 plan 置 `deferred` 并写明重开条件，不是硬合。**

## Execution Plan

### Phase 1 - 授权面裁定 + 在分支上把 job 跑绿

Status: completed
Targets: `.github/workflows/gates.yml`（**只在分支上**）
Skill: `none`

- Item Types: `Decision | Add | Proof`（逐项标注；无任一类型占 80%）
- Prereqs: **`2026-08-22-2325-1` 已关闭并通过独立关闭审计**（措辞刻意避开字面 `Plan Status: completed`——
  Minimum Rule 12 的机械自查 `grep -B5 "\- \[ \]" <plan-file> | grep "Status: completed"` 要求结果为空，
  而这行 prose 就在 `- [ ]` 上方三行，写全会让自查假阳）

- [x] `Decision` **授权面重新摆上台面**（`1206-2` 写死的重开事件已触发，不得默认继承）。
      要回答的是：`ai-autonomy-policy.md` 的 `.github/workflows/** = blocked` 与红线 2「只禁变松」不一致时，
      本 plan 凭什么动它。候选与取舍逐字写进 plan 与 `docs/architecture/system-baseline.md` **§14.5**：
      **(a) 按字面 `blocked` 停手，把整件事交人** —— 代价：工作项 9 的交付面（CI 覆盖）此后完全不可推进，
      而它是 roadmap 上写着的工作项；
      **(b) 在「纯追加 = 加严」这条**未经追认的**先例上继续走**（`2021-2220-2` 加 `gates-l2`、
      `1206-2` 加两个 job，三个 job 都已在 `main` 上），并把**机械可核的加严判据**写进本 plan 的保命闸 —— 选它；
      ⚠️ **必须当面引用那条否掉本候选证据基础的规则，不许绕开**：
      `docs/context/ai-autonomy-policy.md:9` 逐字「AI **must not loosen** protected areas,
      change `ask-first`/`blocked`/`research-only` work to `implement`, or remove blockers
      **without explicit human confirmation or owner-doc evidence marked as human-approved**」。
      **那三个先例全是 AI 起草的，没有一条带人的批准标记**，因此它们**不构成授权**。
      本候选的诚实措辞是「**在未经追认的先例上继续走，欠一次追认**」，
      **不是**「沿用既有先例」（后者读起来像已定的授权，那是把 AI 自己的产物当成许可）；
      **(c) 先请人裁定再动** —— 代价：本 mission 无同步的人，等于 (a)。
      **残余风险照实记**：若人事后裁定严格 `blocked`，本次落地需要一次追认；这一条与
      `1206-2` 的同名 Deferred 是**同一条风险**，不因本 plan 重述而减轻，
      **也不因先例数量从 3 个变成 4 个而减轻** —— 四个未经追认的先例不等于一个授权。
      - Skill: `none`
- [x] `Add` 新建分支，在 `gates.yml` **末尾追加**一个 job `gates-l2-seed`（`name: L2 种子链（装载 + 站点侧对账）`），
      形态照抄 `gates-l2-live`：起栈 → 跑种子链 → 三段取证 → `拆栈（无条件）` `if: always()` `down -v`。
      **两处与先例的偏离必须明写，不许默默改**：① 取证步骤的条件 —— `gates-l2-live` 用的是
      `if: always()`（`:244` / `:248` / `:252`）。本 job **照抄 `always()`**：`failure()` 会在
      cancel / timeout 路径上丢掉日志，而那正是最需要证据的两种收场。② 必须设 `timeout-minutes`
      并在 plan 里写明预期墙钟（起整套 ERPNext 栈 + 四趟 CLI，含数百次 REST 与提交）。
      **理由**：一个长期慢或抖的必过 job，正是将来「不如加个 `continue-on-error`」的压力来源。
      job 内四步，**每一步独立判退出码，不许用 `||` 或 `continue-on-error` 吞掉失败**：
      四条命令逐字如 `## Infrastructure And Config Prereqs` 所列（**每条都带 `--site frontend`**）。
      ⚠️ **幂等断言必须锚在合计行上，不许裸 `grep 新建 0`**：`DocLoadReport.lines()`
      （`agenerp/seedsite.py:645`–`:655`）**每个 DocType 各打一行** `{doctype}：新建 N / …`，
      再打一行 `合计：新建 …`。裸 `grep -q '新建 0'` 会被任何一个「这轮没新建」的 DocType 命中，
      **哪怕 `合计：新建 7`** —— 那样整个 job 的承重判据在装载器不幂等时照样绿。
      判据逐字写死为 `grep -qE '^合计：新建 0 '`（模块 docstring `:16` 的口径就是合计）。
      - Skill: `none`
- [x] `Proof` **红线 2 机械自查五条**（照抄 `0027-2` / `1206-2` 的自查清单，逐条记退出码）：
      ① 前缀性 —— `diff <(git show main:.github/workflows/gates.yml) <(head -n 308 .github/workflows/gates.yml)`
      **必须无输出**；② job 键集合 = 原 9 个 + `gates-l2-seed`，一个不少；
      ③ 禁用词 `continue-on-error` / `if: false` 在新增段内 **0 命中**，
      且新增段**确实带 `timeout-minutes`**（obs-7 那条要求落在这里，否则它是第一个在执行压力下掉队的）；
      ④ 既有 job 的 `if:` 条件一字未改；⑤ 新增段内无失败吞噬（无 `|| true`、无 `set +e`）。
      - Skill: `none`
- [x] `Proof` 推分支、开 PR，取到 `gates-l2-seed` 在 **PR 上** `success` 的 run id 与逐字日志行
      （至少要抄到 `--verify-site` 的 `站点侧对账：9 项，通过 9，失败 0` 与两个承重数值行）。
      **若是红**：按裁判规则 3 先原样复跑一次；仍红则**不改判据、不放宽断言**，
      把红因原文写进 `STATE.md` §3 并把本 plan 置 `deferred`（见 `## Deferred But Adjudicated` 的固定处置）。
      - Skill: `none`

Exit Criteria:

- [x] `Decision` 的三个候选、选择、残余风险已写进 plan 与 `docs/architecture/system-baseline.md` **§14.5**
- [x] 五条机械自查全部为期望值，退出码逐条记录
- [x] `gates-l2-seed` 在 PR 上 `success`，run id / job id / 逐字日志行在案；
      **或**按固定处置置 `deferred` 并写明重开条件
- [x] `docs/logs/` 更新

#### Phase 1 实跑记录（2026-08-23，分支 `ci/2325-2-seed-chain-on-ci`，PR #4）

**开工前实读确认（Closure Gates 第一条）**：`2026-08-22-2325-1` 的 `> Plan Status:` 实读为 `completed`
（该文件 `:3`），其 `## Closure` 记着独立关闭审计证据（审计基线 `215e28d`，六条命令原文 + 退出码 + 独立重做的变异验证）。

**落地提交**：`da9d3af`（`ci(p0-foundation): plan-2026-08-22-2325-2 新增 gates-l2-seed job，把种子链搬上 CI`）。
`gates.yml` 由 **308 行 → 387 行**，job 键由 9 个 → **10 个**，新增段是 `:309`–`:387`。

**红线 2 机械自查五条（命令原文 + 退出码，逐条）**：

```
① 前缀性
$ diff <(git show main:.github/workflows/gates.yml) <(head -n 308 .github/workflows/gates.yml)
  → 无输出，exit 0                    （main 上原 308 行逐字节未动）
② job 键集合
$ grep -nE "^  [a-z0-9-]+:$" .github/workflows/gates.yml
  → exit 0；实得 gates-untouched / expected-red-ratchet / gates-l1 / masterplan-links /
    roadmap-parseable / loop-wiring / gates-l2 / gates-l2-live / verdict-tool-untouched
    + gates-l2-seed(:330)（原 9 个一个不少）
    ⚠️ 照实记：该正则同时命中 `:7  push:`（它在 `on:` 下，不是 job 键）。这是自查式本身的
       已知噪音，不是新增内容带来的；机械核对用的是 YAML 解析结果，见下一条。
$ python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/gates.yml')); print(list(d['jobs'])); print(len(d['jobs']))"
  → exit 0，10 个键，末位 gates-l2-seed（同时证明 YAML 可解析）
③ 禁用词 + timeout-minutes（作用域 = 新增段 :309 起）
$ sed -n '309,$p' .github/workflows/gates.yml | grep -nE "continue-on-error|if: false"
  → 无输出，exit 1（grep 零命中）
$ sed -n '309,$p' .github/workflows/gates.yml | grep -n "timeout-minutes:"
  → exit 0，`27:    timeout-minutes: 30`
  ⚠️ 照实记：首版新增段里有一处 `continue-on-error` **出现在解释性注释里**，
     使 ② 的裸 grep 变成「命中 1 处，但那是注释」。已把那句注释改写成不含字面名的说法
     （并在原处写明为什么这么改），复跑后零命中。**判据没有放宽，改的是注释措辞。**
④ 既有 job 的 if: 条件
$ diff <(git show main:.github/workflows/gates.yml | grep -n "if:") <(head -n 308 .github/workflows/gates.yml | grep -n "if:")
  → 无输出，exit 0
⑤ 失败吞噬
$ sed -n '309,$p' .github/workflows/gates.yml | grep -nE '\|\| true|set \+e'
  → 无输出，exit 1（grep 零命中）
```

**本机 scoped 验证（本 plan 不改 `agenerp/**` 与 `tests/**`，此处是基线未动的证明）**：

```
$ python3 tools/gates/check_expected_red.py   → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）
$ python3 -m pytest tests/unit -q             → exit 0（288 passed）
$ python3 -m pytest tests/contracts -q        → exit 0（151 passed）
$ ruff check agenerp tests/unit tests/contracts → exit 0（All checks passed!）
```

**PR 上的运行（承重证据）**：PR **#4**（`ci/2325-2-seed-chain-on-ci` → `main`），head `da9d3af`，
run **`32584292331`**（event `pull_request`）→ **`success`，十个 job 全部 `success`**：
`roadmap 引擎可解析` `97058222429` · `循环联动冒烟` `97058222522` · `主计划引用不断链` `97058222525` ·
`L1 快门禁` `97058222530` · `判定器未被改动` `97058222557` · `L2 慢门禁（零依赖启动）` `97058222592` ·
`L2 全量 live 判定（19 条）` `97058222597` · `预期红名单只能变短` `97058222605` · `门禁未被改动` `97058222626` ·
**`L2 种子链（装载 + 站点侧对账）` `97058222671`**。

`gates-l2-seed`（job `97058222671`）**四步的逐字日志行**：

```
① 装载主数据段              → 合计：新建 40 / 已存在 0
   （⚠️ 全 job 日志 `grep "⚠️"` 零命中 —— 2325-1 修掉的那条告警行确实没再出现）
② 装载业务单据段并提交      → 合计：新建 17 / 已存在 0 / 提交 11
③ 原样复跑 ②（幂等断言）    → 合计：新建 0 / 已存在 17 / 提交 0
                              grep -qE '^合计：新建 0 ' /tmp/seed-idempotent.log → 通过
④ 站点侧对账（9 项）        → 站点侧对账：9 项，通过 9，失败 0
   承重两行逐字：
   ✅ Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00 / expected = 1010.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）
   ✅ Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = 6450.00 / expected = 6450.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_VALUE）
```

**三个数与 `2107-1` / `2107-2` / `2325-1` 的本机记录逐字相同**（`新建 40` / `新建 17 · 提交 11` /
`1010.00` 与 `6450.00`）。**全新 runner 站点这个从未跑过的输入没有推翻任何一个数。**

**墙钟**：job `97058222671` 用时 **3 分 06 秒**（`16:18:14Z` → `16:21:20Z`），
其中起栈 **2 分 23 秒**，四趟 CLI 合计 **17 秒**，拆栈 22 秒。
`timeout-minutes: 30` 因此是约 10 倍余量的上限，**不是贴身估计**——它挡的是「卡死」，不是「变慢」。

**⚠️ 起草时点名的头号候选被实测证伪，照实记**：plan `## Current Baseline` 逐字写着
`_overdue_checks`「在一个刚起几分钟的 runner 站点上，这是最可能红的一项」。**它绿了**——
在一个存活约 40 秒的全新 runner 站点上，两条 overdue 对账各命中 1 张发票：
`✅ Sales Invoice 中 status == 'Overdue' 的 outstanding_amount 合计（命中 1 张：ACC-SINV-2026-00001） = 18612.00`
与 `✅ Purchase Invoice 中 status == 'Overdue' 的 outstanding_amount 合计（命中 1 张：ACC-PINV-2026-00001） = 2200.00`。
**结论只能写到这么窄**：这一次、在这个日期上它绿。「`status` 到底是不是 `scheduler` 跑出来的」
本 plan **没有查证**，因此**不得读成「overdue 判定与时钟无关」**。它仍是这个 job 未来最可能先红的一项。
同一结论已写进 `docs/architecture/system-baseline.md` §14.5。

### Phase 2 - 变异实证：证明这个 job 有牙齿

Status: completed
Targets: 分支上的临时实验提交（**全部 revert，不进 `main`**）
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 1 拿到分支上的绿

- [x] `Proof` **实验①（正向必红）**：在分支上把 `agenerp/seed/checks.py` 的 `EXPECTED_BACKLOG_QTY`
      改成 `1000.0`（**只改期望值，不改装载逻辑**），推一次 → `gates-l2-seed` 必须 `failure`，
      且日志里 `--verify-site` 那一步逐字打出数量不符。
      **这个变异证明什么、不证明什么（照实写，不许拔高）**：它证明「与 `checks.EXPECTED_*` 的比对
      确实在执行」，**它证明不了左操作数来自站点**。
      「数是站点算出来的」由**日志行本身**证明 —— `CheckResult.line()`（`agenerp/seedsite.py:721`–`:723`）
      把 `actual` / `expected` 与出处并排打出来，取证时必须把那两行原样抄下来。
      **不得把这条变异写成「证明了数出自站点」。**
      ⚠️ **起草时这里写过一条「L1 门禁与 `--seed 42 --verify` 会一并转红」的连带红警告，那是编的，
      已被独立评审实测推翻，就地改准（Minimum Rule 1：从活基线出发，不靠记忆）**：
      评审把 `agenerp/seed/checks.py:23` 改成 `1000.0` 后实测
      `pytest tests/gates/test_seed_dataset_absurdity.py -q` → **`6 passed`，exit 0**、
      `python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 19 项：预期红 7，绿 12，跳过 0`）。
      原因就写在那个门禁文件自己的 docstring `:12`–`:14`：**它的数字是判据自带的，绝不从
      `agenerp.seed.checks` import**。另外 `--seed 42 --verify` **不在任何一个 CI job 里**（`grep` 实测），
      在 CI 上根本无从转红。
      **真实结论比原来那条强得多，必须写成期望的 job 矩阵**：`gates-l2-seed` = `failure`，
      **其余九个 job 全部 `success` —— 即这个变异对现有 19 条门禁**完全隐形**，
      **只有本 job 抓得到**。这正是本 plan 存在的理由，起草时把它当成噪音扔掉了。
      - Skill: `none`
- [x] `Proof` **实验②（revert 必绿）**：`git revert` 实验①，推一次 → `gates-l2-seed` 回到 `success`。
      拿不到这一条，实验①只证明「能红」，证不出「红是那个原因」。
      - Skill: `none`
- [x] `Proof` **实验③（幂等断言必有牙齿）**：把 job 第③步的幂等断言目标改成一个**不可能出现**的串
      （逐字 `^合计：新建 999 `），推一次 → `gates-l2-seed` 必须 **`failure`**；revert 后回 `success`。
      ⚠️ **起草时这一条写的是「改成恒成立的串 → 必须仍绿」，那是空转的实验，已按独立评审的指认整条替换**：
      未变异时本就是绿，变异后还是绿，**绿→绿没有差分信号**，分不出「断言被削弱」「断言是空操作」
      「这一步压根没跑」。**且那个方向是把 `gates.yml` 里的断言改松再推上 CI，形状正落在红线 2 上，
      换不回任何信息** —— 对照 `1206-1` 的四条实验，每一条的结果都与基线**不同**。
      现在这一条是**负向**变异：它证明该步骤确实在断言、且断得下来。
      ⚠️ **若三条实验中任何一条拿不到，就不算交付**（沿用 `1206-1` 立下的规矩），
      按固定处置登记，**不得把「跑绿了」写成「有牙齿」**。
      - Skill: `none`
- [x] `Proof` 收尾把分支 reset 回 Phase 1 的绿提交，`git diff` 对 `agenerp/**` 无输出。
      - Skill: `none`

Exit Criteria:

- [x] 三条实验各有 run id 与 `conclusion`，结论逐字记录；
      **实验①必须逐个抄下 job 矩阵** —— `gates-l2-seed` `failure`、**其余九个 `success`**
      （起草时这里写的是「含连带红的分辨说明」，而本 plan 已实测**没有连带红**，该要求不可满足，已替换）
- [x] 分支收尾后 `agenerp/**` 与 `tests/**` 相对 Phase 1 绿提交 `git diff` 无输出
- [x] `docs/logs/` 更新

#### Phase 2 实跑记录（2026-08-23，分支 `ci/2325-2-seed-chain-on-ci`，PR #4）

**三条实验的结果各不相同，没有一条是绿→绿的空转。**

| 实验 | 载荷 | 提交 | run id | `gates-l2-seed` job id | conclusion |
|---|---|---|---|---|---|
| ① 正向必红 | `agenerp/seed/checks.py:23` `EXPECTED_BACKLOG_QTY` `1010.0 → 1000.0`（只改期望值） | `24becbe` | **`32584645969`** | `97059088031` | **`failure`** |
| ② revert 必绿 | `git revert` 掉 ① | `bfd3a4b` | **`32584922052`** | `97059744724` | `success` |
| ③ 幂等断言负向变异 | job 第③步断言 `^合计：新建 0 ` → `^合计：新建 999 `（**收紧到不可能满足，不是放宽**） | `e1c0dc8` | **`32585177431`** | `97060355175` | **`failure`** |
| ③-revert | `git revert` 掉 ③ | `6980a1d` | **`32585384960`** | `97060854590` | `success` |

**实验① 的 job 矩阵逐个抄下（这是本 plan 存在的理由所在）**：`gates-l2-seed` **`failure`**，
**其余九个全部 `success`** —— `L2 全量 live 判定（19 条）` `97059087856` · `主计划引用不断链` `97059087934` ·
`L1 快门禁` `97059087954` · `循环联动冒烟` `97059087961` · `L2 慢门禁（零依赖启动）` `97059087975` ·
`roadmap 引擎可解析` `97059087984` · `预期红名单只能变短` `97059087997` · `判定器未被改动` `97059088023` ·
`门禁未被改动` `97059088040`。
**即：这个变异对现有 19 条门禁完全隐形，只有本 job 抓得到。**

实验① 的逐字红因（`--verify-site` 那一步，`##[error]Process completed with exit code 1.`）：

```
❌ Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00 / expected = 1000.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）
✅ Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = 6450.00 / expected = 6450.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_VALUE）
站点侧对账：9 项，通过 8，失败 1
```

**这条变异证明什么、不证明什么（照实写，不拔高）**：它证明「与 `checks.EXPECTED_*` 的比对确实在执行」，
**它证明不了左操作数来自站点**。「数是站点算出来的」由**日志行本身**证明 ——
`CheckResult.line()` 把 `actual` / `expected` 与出处并排打出来，而 `actual = 1010.00` 在期望值被改成
`1000.0` 之后**纹丝不动**：它显然不是从 `checks` 读来的。上面那两行原样在此。

**实验① 的本机侧连带影响，照实记（起草时 plan 对本机行为一个字未写，这里是新测出来的）**：
```
$ python3 -m pytest tests/gates/test_seed_dataset_absurdity.py -q  → exit 0（6 passed）   ← 与独立评审的实测一致
$ python3 tools/gates/check_expected_red.py                        → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）← 一致
$ python3 -m pytest tests/unit -q                                  → exit 1（3 failed, 285 passed）
$ python3 -m agenerp.seed --seed 42 --verify                       → exit 1（`成品仓结余应为 1000.0 米，实为 1010.0`）
```
**后两条不改变 CI 侧的结论**：`tests/unit` 与 `--seed 42 --verify` **不在 `gates.yml` 的任何一个 job 里**
（实读 `grep -n pytest .github/workflows/gates.yml`：只有 `test_zero_dep_boot.py` 与判定器两处），
所以它们在 CI 上无从转红，实验① 的九绿一红矩阵不受影响。**照实登记而不是省略。**

**实验③ 的红落点精确到步（这是它比「job 红了」强的地方）**：job `97060355175` 的步骤序列实读为
① `success` · ② `success` · **③ `failure`** · ④ **`skipped`** · 三段取证 `success` · `拆栈（无条件）` `success`。
逐字日志：`grep -qE '^合计：新建 999 ' /tmp/seed-idempotent.log` 上方紧跟着装载器真实打出的
`合计：新建 0 / 已存在 17 / 提交 0`，随后 `##[error]Process completed with exit code 1.`
**三件事同时被证实**：(i) 第③步确实在断言，断言目标改了它就红；(ii) 断言锚的确实是**合计行**；
(iii) **`always()` 取证与 `down -v` 在失败路径上照跑**（④ 被 skip，而取证三步与拆栈全部 `success`）——
后者是 plan `## Current Baseline` 里「敢在 CI 上装种子数据」那个前提的**本批直接实证**，
不再只是引用 backlog 里 2026-08-22 那次。

**⚠️ 实验③ 的方向必须写明**：它把断言**收紧到不可能满足**（`新建 999`），不是放宽。
红线 2 禁的是让门禁变松；该改动只活在分支上两次推送之间，**已 `git revert` 且未进 `main`**。

**收尾**：分支 `git reset --hard c603ec0`（Phase 1 的绿提交）+ `--force-with-lease` 推回。
reset 前先做过内容核对——`git diff c603ec0 HEAD --stat` **无输出**（两次 revert 已让内容归位，
reset 改的只是历史）。reset 后 `git diff c603ec0 HEAD -- agenerp/ tests/ .github/workflows/` **无输出，exit 0**。
四条实验提交按 sha 在 GitHub 上仍可访问（`24becbe` / `bfd3a4b` / `e1c0dc8` / `6980a1d`），**不是「抹掉」**。

### Phase 3 - 落 `main`，取权威运行

Status: completed
Targets: `main` 上的 `.github/workflows/gates.yml`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1 与 Phase 2 完成

- [x] `Add` 按 `1206-2` 的先例落地：**新开一个只含 `gates.yml` 追加的分支 → PR → `--ff-only` 合 `main`**，
      并核对「落进 `main` 的 sha 与 PR 上跑绿的 head **逐字同一个 sha**」。
      - Skill: `none`
- [x] `Proof` 取 `main` 的 `push` 权威运行：**十个 job 全部 `success`**，逐个抄 job id 与结论；
      `gates-l2-seed` 的日志逐字抄承重两行（`actual_qty = 1010.00` / `stock_value = 6450.00`）
      与 `站点侧对账：9 项，通过 9，失败 0`。
      - Skill: `none`
- [x] `Proof` 核对两个守卫走的是「未触及」分支（本 plan 不碰 `tests/gates/**` 与 `tools/gates/**`），
      日志逐字在案。**若 `verdict-tool-untouched` 意外红**，处置是 `gh run rerun --failed` 原样复跑
      并把结果记进 `STATE.md` §3 已有的那条 `[open]` 行下（**追加，不改写**），**不改守卫脚本体**。
      - Skill: `none`
- [x] `Proof` 把 `main` 上 `gates.yml` 的行数与 job 键集合实读一次，写进 plan
      （下一个动它的 plan 要拿这个数做前缀自查）。
      - Skill: `none`

Exit Criteria:

- [x] `main` 上存在 `gates-l2-seed`，落地 sha 与 PR 跑绿 head 逐字相同
- [x] `main` `push` 权威运行的 run id 与十个 job 的结论在案
- [x] `main` 上 `gates.yml` 的新行数与 job 键集合已记录
- [x] `docs/logs/` 更新

#### Phase 3 实跑记录（2026-08-23）

**落地形态照抄 `1206-2`**：从 `main` @ `2505970` 新切分支 **`ci/2325-2-seed-land`**，
其上**只有一个提交、只含 `.github/workflows/gates.yml` 的纯追加**（`79	0`，`git diff --numstat main HEAD` 实读）。
⚠️ **照实记一处偏离处置**：首次是用 `git cherry-pick da9d3af` 做的，但那个提交里同时带着
`docs/architecture/system-baseline.md` §14.5（`2 files changed`），**不满足「只含 `gates.yml`」**。
已 `git reset --hard main` 后改用 `git checkout da9d3af -- .github/workflows/gates.yml` 重做，
并逐字节核对 `diff <(git show da9d3af:.github/workflows/gates.yml) .github/workflows/gates.yml` → **无输出**。
§14.5 与本 plan、日志随**后一个**提交直接落 `main`。

**PR #5**（`ci/2325-2-seed-land` → `main`），head **`29726696f7ceb4a6a17cb5cf9dda8902607e11ff`**，
run **`32585758762`**（event `pull_request`）→ **`success`，十个 job 全 `success`**。

**落地**：`git checkout main && git merge --ff-only ci/2325-2-seed-land` →
`Updating 2505970..2972669  Fast-forward  1 file changed, 79 insertions(+)`；
**`main` 的 tip 与 PR #5 上跑绿的 head 逐字同一个 sha**：
`29726696f7ceb4a6a17cb5cf9dda8902607e11ff`（机械比对 `[ "$(git rev-parse HEAD)" = "2972669…" ]` → `IDENTICAL`）。
PR #5 状态实读 `MERGED`。

**权威运行（`main` 的 `push`）：run `32585965892`，event `push`，head `2972669…` → `success`，十个 job 全部 `success`**：

| job | job id | conclusion |
|---|---|---|
| 预期红名单只能变短 | `97062260964` | `success` |
| L2 慢门禁（零依赖启动） | `97062261053` | `success` |
| 门禁未被改动 | `97062261064` | `success` |
| 循环联动冒烟 | `97062261065` | `success` |
| L1 快门禁 | `97062261066` | `success` |
| 主计划引用不断链 | `97062261074` | `success` |
| roadmap 引擎可解析 | `97062261090` | `success` |
| **L2 种子链（装载 + 站点侧对账）** | **`97062261110`** | **`success`** |
| 判定器未被改动 | `97062261119` | `success` |
| L2 全量 live 判定（19 条） | `97062261128` | `success` |

`gates-l2-seed`（`97062261110`）的逐字日志，**承重两行与 PR #4 首跑、与本机 `2107-2` / `2325-1` 全部相同**：

```
① 合计：新建 40 / 已存在 0
② 合计：新建 17 / 已存在 0 / 提交 11
③ 合计：新建 0 / 已存在 17 / 提交 0        （grep -qE '^合计：新建 0 ' 通过）
④ ✅ Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00 / expected = 1010.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）
   ✅ Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = 6450.00 / expected = 6450.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_VALUE）
   站点侧对账：9 项，通过 9，失败 0
```

墙钟 **3 分 33 秒**（`16:51:26Z` → `16:54:59Z`），与 PR #4 首跑的 3 分 06 秒同量级。

**两个守卫都走「未触及」分支，日志逐字在案**：
`门禁未被改动`（`97062261064`）→ `✅ 未触及 tests/gates/**`；
`判定器未被改动`（`97062261119`）→ `✅ 未触及判定器`。
**两者都没红，因此 `verdict-tool-untouched` 的 trailer 出口不可复现那条 `[open]` 风险本轮未被触发**，
`STATE.md` §3 那条行**无需追加**（追加只在它真的红过时才有内容）。
同轮 `gates-l2-live`（`97062261128`）逐字 `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。

**`main` 上 `gates.yml` 的实读事实（下一个动它的 plan 拿这个做前缀自查）**：

- **行数 `387`**（原 308 + 新增 79）。
- **job 键 10 个，顺序逐字**：`gates-untouched` · `expected-red-ratchet` · `gates-l1` ·
  `masterplan-links` · `roadmap-parseable` · `loop-wiring` · `gates-l2` · `gates-l2-live` ·
  `verdict-tool-untouched` · **`gates-l2-seed`**（YAML 解析实证，不是 grep 猜的）。
- **`gates-l2-seed` 的段落是 `:309`–`:387`**，前 308 行逐字节未动。

### Phase 4 - 把「只在本机验证过」这句话改准

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md` · `docs/architecture/system-baseline.md`（新建 §14.5）· `docs/context/project-context.md` · `docs/logs/`
Skill: `none`

- Item Types: `Fix`（确认的 owner-doc 漂移，Minimum Rule 14 不降级）
- Prereqs: Phase 3 完成

- [x] `Fix` roadmap 工作项 7 那段**追加**一行：B 半的 CI 覆盖已落地、run id、以及
      **工作项 7 的状态值一个字不改**（卡点仍是「那条 L1 门禁从未进过 `expected-red.txt`」）。
      `git diff --numstat` 删除列必须为 `0`。
      - Skill: `none`
- [x] `Fix` roadmap 工作项 9「9 现状」那段**追加**一行：本 plan 把 CI 覆盖面从「19 条门禁」扩到
      「门禁 + 种子链 CLI」，并**逐字写明这不改变工作项 9 的 `done` 判据**
      （它的判据是「对 19 条 live 判定并 `success`」，`1206-2` 已使其成立；本 plan 是覆盖面的扩展，不是判据的替换）。
      **不得把本 plan 写成「工作项 9 因此可以 `done`」** —— 它另有一条独立障碍：没有属于自己的门禁测试。
      - Skill: `none`
- [x] `Fix` `docs/masterplan/STATE.md` §2 **追加**一条证据行（红线 5：只追加）。
      其中必须逐字承接 2026-08-22T20:55Z 行那句「**不含 CI；其中五条活站点命令 `GATE_VERIFY` 复跑不到**」
      并说明**哪几条现在被 CI 覆盖了、哪几条仍然没有**（`GATE_VERIFY` 复跑不到这一点**不因 CI 覆盖而改变**）。
      - Skill: `none`
- [x] `Fix` 在 `docs/architecture/system-baseline.md` **新建 §14.5** 记录新 job 的判定口径与它**不覆盖**的部分。
      ⚠️ **`§14` 本体（`:131`–`:177`）一行不改** —— `:180` 逐字禁止，且它是 Spike 10 的结论出处。
      - Skill: `none`
- [x] `Fix` `docs/context/project-context.md:57`（种子站点侧对账那一行）**核对两处、只改一处**：
      ① 它逐字写着「⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它」——
      **这一句在本 plan 之后仍然成立，不得改**（CI 覆盖 ≠ `GATE_VERIFY` 可复跑）；
      ② 但它列举的代偿控制清单里要**补上**「CI job `gates-l2-seed`」。
      `1206-2` 在 CI 覆盖面变化时更新过这张表，本 plan 沿用同一处置。**只改这一行，不动表结构。**
      - Skill: `none`

Exit Criteria:

- [x] roadmap 与 STATE 均为**纯追加**（`git diff --numstat` 删除列为 `0`）
- [x] 工作项 7 与工作项 9 的状态值**均未被本 plan 改动**
- [x] **§14.5** 写明新 job 的覆盖面**与**它不覆盖的部分；**`§14` 本体一行未改**（`diff` 实证）
- [x] `project-context.md:57` 的代偿控制清单已补上新 job，且「`GATE_VERIFY` 复跑不到」那句**未被改动**
- [x] `docs/logs/` 更新

## Draft Review Record

- 独立评审第 1 轮：**needs revision**（独立子代理，fresh session）—— 八条阻塞项 B1–B8。
  承重的四条：① 变异实验③是绿→绿的**空转实验**，且方向是把 `gates.yml` 的断言改松再推 CI，**形状落在红线 2 上**；
  ② 起草时那条「变异会让 L1 门禁与 `--seed 42 --verify` 一并转红」的连带红警告**是编的**，
  评审实测推翻（`6 passed` / 判定器 exit 0），而真实结论**比它强**——该变异对现有 19 条门禁完全隐形；
  ③ `--site` 由 argv 给而非 `AGENERP_SITE`，按原稿写的 job **会 exit 2**；
  ④ 幂等断言裸 `grep 新建 0` 会被任一 DocType 的行命中，**装载器不幂等时照样绿**。
  另有 B5（工作项归属应为 7 而非 9）、B6（`§14` 本体禁改，应新建 §14.5）、
  B7（Protected Areas 非破坏性写那条「不许略过不谈」未交代）、B8（`Decision` 未面对
  `ai-autonomy-policy.md:9` 那条否掉其证据基础的规则）。十条非阻塞观察一并采纳。
- 独立评审第 2 轮：**needs revision** —— 八条全部落地且未引入新的假陈述；
  剩余三条机械问题：R1（第 ③ 步的断言归属在两处写法里自相矛盾，会让实验③打在没有断言的步骤上）、
  R2（三处行号 off-by-one，其中 `:855` 指向的是**上一个**守卫）、
  R3（Phase 2 退出判据仍要求「连带红的分辨说明」，而本 plan 已实测**没有连带红**，该判据不可满足）。
  评审同时确认了两条我特意送检的自查：§14.x 的落点属实；「`--seed 42 --verify` 在 CI 上无从转红」**没有过度声称**
  （本机退出码未测，故本 plan 对本机行为**一个字都不写**）。
- 独立评审第 3 轮：**accept** —— 五条改动全部落地并逐一复核行号；禁用词扫描干净；
  无任何路径写入 `§14` 本体。仅剩一条 cosmetic 提示（`Prereqs` 里的字面 `Plan Status: completed`
  会让 Minimum Rule 12 的机械自查假阳），**已按提示改掉**。

## Closure Gates

- [x] **开工前实读确认**：`2026-08-22-2325-1` 的 `> Plan Status:` 为 `completed` 且其 `## Closure`
      记着独立关闭审计证据（**此刻两个 plan 都还是未入库的 draft，没有任何机制在强制这个顺序**）
- [x] in-scope behavior is complete（`main` 上有 `gates-l2-seed` 且权威运行 `success`）
- [x] 三条变异实验齐全，**三条各自的结果都与基线不同**（无绿→绿的空转实验），
      且**「跑绿了」没有被写成「有牙齿」**
- [x] relevant docs are aligned（roadmap 两处追加 · STATE 追加 · 新建 §14.5 · `project-context.md:57` · `docs/logs/`）
- [x] verification has run：五条红线 2 机械自查 + PR 上的 run + 三条变异 run + `main` 权威 run，
      每一条都有 run id / 退出码
- [x] **scoped verification is not conflated with full verification**：本仓无全量套件；
      本 plan 的结论**只覆盖 CI 上跑到的那几条命令**，必须逐字写明哪些仍未被覆盖
- [x] `tests/gates/**` · `tools/gates/**` · `docs/masterplan/DECISIONS.md` · `missions/**` 均 `git diff` 无输出
- [x] `docs/architecture/system-baseline.md` 的 `§14` 本体（`:131`–`:177`）`git diff` 无输出
- [x] `main` 上 `gates.yml` 原 308 行**逐字节未动**（前缀性 `diff` 无输出）
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [x] closure evidence exists in files

## Deferred But Adjudicated

### 取不到 CI 证据时的固定处置（写死，不临场决定）

- Classification: `watch-only residual`（失败分支的写死处置，不是被推迟的工作项）
- 处置逐字：原样复跑一次 → 仍红则记录所有已跑命令与输出原文 → 追加进 `STATE.md` §3（不改写既有行）→
  本 plan 置 `deferred` 并在文件头写明重开条件 → **不放宽任何断言**、**不改 `tests/gates/**` 与 `tools/gates/**`**、
  **不猜根因**（裁判规则 3）→ **不把分支合进 `main`**。
- **落 `main` 之后再红，处置相同，写在这里免得临场发明**：原样复跑一次 → 仍红则把红因原文追加进
  `STATE.md` §3 并停下来交人。**明确不做**：不禁用该 job、不加 `continue-on-error`、不缩小它的触发范围、
  不放宽它的断言 —— 那些全在红线 2 内。**这是本条与「合并前红」唯一不同的场景，不得因为「已经在 `main` 上了」就改口径。**
- ⚠️ **停机线**：`AGENTS.md` 裁判规则 4「CI 连续 2 轮红即停机」在本 plan 内同样生效。
  触发后立即停止推送，走上面的处置，**不得靠继续烧 CI 轮次去碰运气**。
- Successor Required: `no`
- 重开事件：**人裁定继续**，或红因被一个独立 plan 修好之后。

### `ai-autonomy-policy.md` 的 `.github/workflows/** = blocked` 与红线 2「只禁变松」措辞不一致

- Classification: `out-of-scope improvement`（**人动作项**）
- Why Not Blocking Closure: 本 plan 的 Phase 1 `Decision` 已按 `1206-2` 写死的重开事件把它**重新摆上台面**，
  给出候选、选择与残余风险，**没有默认继承**。但**改 Protected Areas 的 Rule 列等于替人定授权口径，loop 不做**。
- Successor Required: `no`
- 重开事件：**人给出裁定**，或**下一个要动 `main` 上 `.github/workflows/**` 的 plan 开工前**
  （届时必须再摆一次，同样不得默认继承）。

### `verdict-tool-untouched` 的 trailer 出口不可复现 / `|| true` 假阴入口

- Classification: `watch-only residual`
- Why Not Blocking Closure: 两条都是已登记的人裁定题（`STATE.md` §3 的 `[open]` 行 + `1206-1` / `1206-2` 的同名 Deferred）。
  **本 plan 不触及判定器**，因此不会走到那个 trailer 分支；修它要改既有 job 的脚本体并重取全套 CI 证据。
- Successor Required: `no`
- 重开事件：**人裁定修守卫脚本体时**，或**守卫出现一次已知的假阴时**。

### `gates-l2` 与 `gates-l2-live` 覆盖面重复，前者未退休

- Classification: `out-of-scope improvement`（**人动作项**，`0027-2` / `1206-2` 已登记，本 plan 继续挂着）
- Why Not Blocking Closure: 退休它是**删除**动作，方向是变松；且会打掉「新文件以旧文件为行前缀」
  这条本仓已固化的红线 2 机械判据。本 plan 只增不减。
- Successor Required: `no`
- 重开事件：**人裁定退休它**，或 CI 时长成为实际瓶颈。

### 种子链的三条站点侧断言仍无门禁形态

- Classification: `watch-only residual`
- Why Not Blocking Closure: 新建 `tests/gates/**` 在红线 1 内。**本 plan 交付的是 CI 覆盖，不是门禁形态**——
  ⚠️ 两者不得混为一谈：CI 上跑 CLI 退出码**不使**这三条断言成为门禁，
  `GATE_VERIFY` 与 `tools/gates/check_expected_red.py` 仍然复跑不到它们。
- Successor Required: `no`（**人动作**）
- 重开事件：**人出具 `Gates-Change-Approved-By:` trailer 采纳
  `docs/backlog/gate-proposal-seed-dataset.md` 时**。

### CI 站点若不再是一次性的，门禁探针会开始累积

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 的新 job 沿用 `拆栈（无条件）` `if: always()` + `down -v`，
  站点仍是一次性的，`docs/backlog/gate-fixtures-pollute-the-live-site.md` 的裁定（维持 watch-only）不变。
- Successor Required: `no`
- 重开事件：**该 backlog 条目自己写死的触发条件** —— CI 的 L2 站点不再是一次性的时。

## Closure

Status Note: 四个 Phase 全部执行完毕。逐条自陈，**不粉饰**：

1. **结果面成立**：`main` 上存在 job `gates-l2-seed`，`main` `push` 权威运行 **`32585965892`
   十个 job 全部 `success`**；它在**全新 runner 站点**上跑通整条种子链并对上了账
   （`站点侧对账：9 项，通过 9，失败 0`，`actual_qty = 1010.00` / `stock_value = 6450.00`，
   与本机 `2107-2` / `2325-1` 的记录逐字相同）。**落地 sha `29726696f7ceb4a6a17cb5cf9dda8902607e11ff`
   与 PR #5 上跑绿的 head 逐字同一个。**
2. **它有牙齿，且三条实验的结果各不相同**（无绿→绿的空转）：`32584645969` `failure`（其余九个
   `success`——该变异对现有 19 条门禁**完全隐形**）· `32584922052` `success` ·
   `32585177431` `failure`（红精确落在第③步）· `32585384960` `success`。
   **「跑绿了」没有被写成「有牙齿」**：前者由首跑与权威运行给，后者由这四条 run 给，两组证据分开列。
3. **授权面重新摆上台面，未默认继承**，三个候选 / 选择 (b) / 「**欠一次人的追认**」的残余风险
   写进 `system-baseline.md` **新建 §14.5**；`ai-autonomy-policy.md:9` 那条否掉本候选证据基础的规则
   **被当面引用**，先例被明写为「**不构成授权**」。
4. **工作项 7 与工作项 9 的状态值本 plan 一个字未改**，两者仍 `planned`；roadmap 与 STATE 均为
   **纯追加**（删除列均为 `0`）。
5. **两处执行期偏离照实记，不是事后美化**：① Phase 3 首次用 `git cherry-pick` 做落地分支时
   带进了 §14.5，不满足「只含 `gates.yml`」，已 `reset --hard` 重做并逐字节核对；
   ② Phase 1 首版新增段有一处 `continue-on-error` **落在注释里**让红线 2 自查 ③ 从「0 命中」
   退化成「命中 1 处，但那是注释」，已改写注释措辞（**判据没放宽**）后复跑零命中。两处都写在对应 Phase 的实跑记录里。
6. **起草时点名的头号红候选 `_overdue_checks` 被实测证伪**，结论只写到「这一次、在这个日期上它绿」，
   **没有拔高成「与时钟无关」**；它仍被登记为这个 job 未来最可能先红的一项。
7. **⚠️ scoped verification，不是 full green。** 本仓无全量套件。本 plan 的结论**只覆盖 CI 上跑到的那几条命令**：
   种子链三条活站点 CLI（含幂等复跑）此刻在 `main` 的每次 `push` 与每个 PR 上被服务端复跑。
   **仍未被 CI 覆盖的，逐条写明**：`python3 -m agenerp.seed --seed 42 --verify` ·
   `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` ·
   `ruff check agenerp tests/unit tests/contracts` —— 这四条在 `gates.yml` 里**零 job 覆盖**；
   两条单独形态的活站点 pytest 命令行本身也没有独立 job（其**断言**被 `gates-l2-live` 覆盖）。
8. **⚠️ CI 覆盖 ≠ 门禁形态 ≠ `GATE_VERIFY` 可复跑。** 新 job 判的是**四条 CLI 的退出码**，
   **不使**种子链的三条站点侧断言成为门禁；`missions/p0-foundation.json` 一个字节未动，
   `GATE_VERIFY` 仍然复跑不到它们。`project-context.md:57` 里那句「`GATE_VERIFY` 复跑不到它」
   **本次一个字未改**（md5 前后一致，实证在 Phase 4 记录里）。

**本 plan 执行期的机械自查（命令原文 + 退出码，基线 `2505970`）**：

```
$ git diff --numstat 2505970 -- tests/gates tools/gates docs/masterplan/DECISIONS.md missions
  → 无输出，exit 0
$ diff <(git show 2505970:docs/architecture/system-baseline.md | sed -n '131,177p') <(sed -n '131,177p' docs/architecture/system-baseline.md)
  → 无输出，exit 0                     （§14 本体一行未改）
$ diff <(git show 2505970:.github/workflows/gates.yml) <(head -n 308 .github/workflows/gates.yml)
  → 无输出，exit 0                     （main 上原 308 行逐字节未动）
$ python3 tools/gates/check_expected_red.py        → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）
$ python3 -m pytest tests/unit -q                  → exit 0（288 passed）
$ python3 -m pytest tests/contracts -q             → exit 0（151 passed）
$ ruff check agenerp tests/unit tests/contracts    → exit 0（All checks passed!）
$ python3 -m agenerp.seed --seed 42 --verify       → exit 0
$ git diff --numstat docs/backlog/p0-foundation-roadmap.md docs/masterplan/STATE.md
  → `2	0` / `8	0`（删除列均为 0，纯追加）
```

Closure Audit Evidence:

- Auditor / Agent: 待独立审计（**执行者不自证**）。`closure audit was independent` 是唯一未勾的 Closure Gate。
- Evidence: 待回填
