# 2026-08-22-0027-2 CI 上把 L2 判定扩到全部 19 条门禁（live 判定模式进 `gates.yml`）

> Plan Status: deferred
> Deferred Reason: **CI 连续 2 轮红即停机**（`AGENTS.md` 裁判规则 4）。`gates-l2-live` 在 run `32509351108`
>   的 attempt 1 与 attempt 2（原样复跑）上**两次都红**，同一条 nodeid
>   `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`，
>   同一个计数 `门禁 19 项：红 1，绿 18，跳过 0`。**可复现，不是抖动。**
>   红因分流结果：**红在实现**（`apply_pack` 的物理列清除面在 runner 的全新站点上不成立），
>   而 `agenerp/**` 是本 plan 的 Non-Goal —— 按 Phase 2 末项写死的固定处置，本 plan 不修，交 successor。
>   **PR #1 未合并**，`.github/workflows/gates.yml` 的两个新 job 只在分支上，`main` 未受影响。
> Reopen When: successor plan 修好 `agenerp` 侧那条清除面（必须带 Protected Areas 末行要求的
>   「实跑前后全量 `capture` 对照」证据，并重新证明本机 live 整目录判定仍绿）之后，
>   从 Phase 2 的「守卫 job 的变异实证」那一项续跑。
> Mission: p0-foundation
> Work Item: 9. L2 门禁的判定与 CI 覆盖（把「只在本机验证过」补成 CI 可复跑）—— 第二个 plan：CI 侧（判定消费 + 判定器守卫）
> Last Reviewed: 2026-08-22
> Source: `docs/backlog/p0-foundation-roadmap.md`「5 现状」行逐字登记的「**验证范围**：live 只在本机做过，CI 未验证」；
>   `docs/context/project-context.md` 第 58 行逐字：「上面两条 L2（快照 / 定制包往返）**仍是本机独证**」；
>   plan `2026-08-21-2220-2` 的 Deferred「判定器没有「live 名单」这个概念」，重开事件逐字为
>   「当 CI 的 L2 覆盖面扩到 `test_zero_dep_boot.py` 之外时」
> Related: `2026-08-22-0027-1-live-mode-gate-verdict.md`（**前驱，本 plan 的唯一前置**，并把「判定器的 CI 侧守卫」指名交给本 plan）·
>   `2026-08-21-2220-2-homepage-ai-not-configured.md`（现有 `gates-l2` job 的交付者，也是本 plan 红线 2 纪律的先例）·
>   `docs/backlog/gate-fixtures-pollute-the-live-site.md`（本 plan 触发它的重开条件）
> Audit: required
> Closure Audit Log（只追加，不改上面任何一行）:
>   - 2026-08-22 · 独立关闭审计（fresh session）· 结论 **不可关闭，维持 `deferred`**。
>     实测复核：`main` 上 `.github/workflows/gates.yml` 的 job 键仍是 7 个
>     （`gates-untouched` / `expected-red-ratchet` / `gates-l1` / `masterplan-links` / `roadmap-parseable` /
>     `loop-wiring` / `gates-l2`），**没有 `gates-l2-live`、没有 `verdict-tool-untouched`** ——
>     两个新 job 确实只在分支 `ci/0027-2-l2-full-live-gate` 上，与 STATE §3 那条 `[open]` 行一致。
>     19 个未勾项**不是漏勾，是真没做**：Phase 2「守卫 job 的变异实证」三次实验从未跑过（无 run id），
>     Phase 3「前驱两条 Deferred 记为了结」未落地，`## Closure Gates` 十四框按本 plan
>     §「`Plan Status` 由谁写」的归属规则本就该保持未勾。审计**不代打勾**（打勾即伪造证据）。
>     阻塞方：**人 / successor plan** —— 重开条件（`agenerp` 侧清除面被修好）此刻未满足，
>     `docs/plans/p0-foundation/` 下无承接该面的 successor。
>   - 2026-08-22 · 第二次独立关闭审计（fresh session，收到同一份 `SCRIPT_CHECK_RESULT: FAIL`）·
>     结论**与上一条一致：不可关闭，维持 `deferred`**，且**本轮不改一个勾**。
>     复核命令与输出：`git log --oneline -1` → `c5c4538`；`git status --porcelain` → 空；
>     `git show main:.github/workflows/gates.yml | grep '^  [a-z0-9-]*:'` → 仍是 7 个 job 键，
>     `gates-l2-live` / `verdict-tool-untouched` **零命中**；`git branch -a` → 两个新 job 仍只在
>     `ci/0027-2-l2-full-live-gate` / `origin/ci/0027-2-l2-full-live-gate` 上，PR #1 未合。
>     即：自上一条审计以来**仓库状态一字未变**，19 个 `[ ]` 仍是真未做，重开条件仍未满足。
>     驱动脚本要求「把每个 `[ ]` 改成 `[x]` 才能关闭」——**本轮拒绝执行该要求**：
>     Phase 2 的守卫变异实证没有任何 run id、Phase 3 的「前驱两条 Deferred 记为了结」没有落地，
>     打勾即伪造证据（红线：测试过没过由退出码裁定，不得自报通过）。
>     阻塞方仍是**人 / successor plan**，本 plan 就地停机等待。

## 术语约定：本 plan 说的「判定方式节」在哪

起草时实测：`docs/architecture/system-baseline.md` 共 **393 行**，最后一个带编号的节是
`## 14.3 「AI 能力未配置」在本仓的表达口径`（第 286 行）；描述 CI L2 判定方式的那段是它下面
**一个不带编号的三级标题** `### L2 门禁在 CI 上的判定方式，与它换来的残余风险`（第 381 行）。
`grep "14\.4"` 在该文件上**零命中**——**本仓此刻没有 `§14.4`**。

**前驱 plan（`0027-1`）的 Phase 1 会把这一节提升为独立的 `## 14.4` 并改写。**
本 plan 因此按「前驱交付后的形态」称它为 `## 14.4`，**但 Phase 1 的前置检查会实测该标题是否真的存在**
（见 Phase 1 首项第 ④ 条）；不存在就说明前驱没做完，按前置未就绪停手。

## Current Baseline

**以下每条都在 2026-08-22 起草时读过活文件；被独立评审逐条复核过，复核指出的错处已就地改准。**

### CI 现状（`.github/workflows/gates.yml`，起草时 7 个 job）

`gates-untouched` · `expected-red-ratchet` · `gates-l1` · `masterplan-links` ·
`roadmap-parseable` · `loop-wiring` · `gates-l2`。触发 `on: push branches:[main]` / `pull_request` / `workflow_dispatch`；
`permissions: contents: read`。**`gates-l2` 是文件里的最后一个 job**（这一条是 Phase 2 自查方案成立的前提）。
**实测 `set -euo pipefail` 只出现 4 次、在 4 个 job 里**（`gates-untouched` / `expected-red-ratchet` /
`masterplan-links` / `roadmap-parseable`）；文件里共 5 个多行 `run: |` 块，第 5 个（`gates-l2` 打版本号那步）没有。
所以下文 Phase 2 检查 (d) 的「每个多行 `run:` 首行 `set -euo pipefail`」**比现状更严**——
它是本 plan 自己立的规矩，**不是**在援引一条已存在的惯例，别把它说成惯例。文件里**没有任何 `concurrency:` 键**（`grep` 全 `.github/` 零命中）。

`gates-l2` 的实际覆盖面**只有一个文件**：

```yaml
- name: L2 门禁 —— 零依赖启动
  env:
    AGENERP_LIVE: "1"
    AGENERP_ADMIN_PASSWORD: admin
  run: python3 -m pytest tests/gates/test_zero_dep_boot.py -q
```

起栈 `docker compose -f docker-compose.yml up -d --wait --wait-timeout 900`；收尾 `docker compose down -v`，`if: always()`。
它**不跑判定器**，直接对 pytest 退出码判定——理由与残余风险逐字写在判定方式节。

### 「只在本机验证过」此刻散落在四处（**这四处就是 Phase 3 要改的四处，不多不少**）

| # | 出处 | 逐字 |
|---|---|---|
| ① | roadmap「5 现状」行 | 「**验证范围**：live 只在本机做过，CI 未验证」 |
| ② | roadmap「6 现状」行 | 四条 live 全绿的证据全部来自本机命令 |
| ③ | `project-context.md` 第 56 / 57 / 58 行 | 第 58 行逐字「**本仓唯一一条在 CI 上真跑过的 L2**」「⋯**仍是本机独证**」 |
| ④ | 判定方式节（前驱提升后的 `## 14.4`） | CI 绕开判定器的口径与残余风险 |

⚠️ **plan `2026-08-21-2220-1` 的 Closure Gates 里那句「live 只在本机做过，CI 未验证」不在这四处之内，
本 plan 一个字都不改它。** 它是一个**已关闭 plan 的关闭证据**，在它关闭的那一刻为真；
改它等于篡改历史证据，与 Minimum Rule 14 说的「确认的 owner-doc 漂移」是两回事。

**P0 的目标一句话是「把「可验证」做出来」。** 一条只在某一台笔记本上绿过的判据不满足这个目标——
这是本 plan 存在的理由，不是「顺手优化」。

### runner 与本机的差异（按实测写，不按想象写）

- 已实证：runner 是 Docker **28.0.4** / Compose **v2.38.2**，本机 **29.2.1** / **v5.0.2**；
  在 `test_zero_dep_boot.py` 三条上两边表现一致（run `32499273158`，日志逐字 `3 passed in 2.68s`）。
- **真正的未知：runner 的站点是全新的，本机站点是长期存活的。**
  `docs/backlog/gate-fixtures-pollute-the-live-site.md` 实测记着本机 `tabItem` 上已积了 **6 条** `agenerp%` 孤儿列，
  所以 `schema_drift("Item")` 在两边返回的基线集合**不同**。
  `test_no_orphan_column_left_behind` 只断言 `PROBE_FIELD not in orphans`，**方向是安全的那一侧**，
  但「安全」是推理不是实测——这正是要让 CI 真跑一次的原因。
- **已排除的假风险（独立评审指出，照实更正）**：「`mariadb` 不在镜像里」**不可能**成立——
  `db` 用的是钉死的 `mariadb:10.6`，runner 与本机字节一致；`bench execute` 同理（`frappe/erpnext:v15.119.3`）。
  起草第一版把它列为风险是编造的，此处删除。
- `agenerp/oob.py` 的带外传输在 runner 上确实没跑过（`docker compose exec -T backend|db …`），
  这一条**保留为未知**，由 CI 实跑给答案。
- **不是风险**：`test_customization_roundtrip_delete.py` 走 `pack_repo` 要 `git init` + `git commit`。
  实测 `tests/gates/conftest.py:305/309/310-311`：`PackRepo.__init__` 自己设仓局部的
  `git config user.email` / `user.name`，**不依赖 runner 的全局 git 身份**。

### 端口与 env

- runner 上 8080 空闲，现有 `gates-l2` 不设 `AGENERP_HTTP_PORT`，走 compose 默认
  `127.0.0.1:${AGENERP_HTTP_PORT:-8080}:8080`，已实证可行。本 plan 沿用。
- `AGENERP_SITE_URL=http://127.0.0.1:8080` 是**冗余而非新耦合**：实测 `agenerp/site.py:130` 的
  `default_base_url()` 已经回落到 `AGENERP_HTTP_PORT` → `DEFAULT_HTTP_PORT = "8080"`（`site.py:49`），
  与 compose 默认一致。显式写出来更好读，但不要把它说成「引入了一处硬编码耦合」——那处耦合本来就在 `site.py` 里。
- **`AGENERP_SITE=frontend` 是 job 级的，它有一个必须点名的副作用**：
  它会把 `test_snapshot_diff_structured.py` 的 `test_two_snapshots_of_unchanged_site_diff_empty` 与
  `test_diff_is_structured_not_text` **从离线来源翻到活站点上**。实测影响面**恰好只有这两条**——
  `test_normalizer_idempotent.py` / `test_seed_dataset_absurdity.py` / `test_zero_dep_boot.py` 都不调 `capture()`。
  两条此刻是绿的 L1，进 CI 后会变成依赖活站点，这一点要写进 `## 14.4`。

### 受保护面自查

`docs/context/ai-autonomy-policy.md` 的 Protected Areas 表把 `.github/workflows/**` 标为 `blocked`，
Required Evidence 列写「人工批准（`AGENTS.md` 红线 2：不得让门禁变松）」。
而红线 2 原文只禁**变松**。**本 plan 不停下等人，理由写在文件里而不是靠先例**：

> `ai-autonomy-policy.md:72` 逐字：「下表前八条**全部照抄** `AGENTS.md` 的红线表——**此处不新增、不放宽任何一条**」

即该表自称是红线表的**转录**，不是更严的新规。转录不可能比被转录者更严，所以 `.github/workflows/**` 那行的
真实约束就是红线 2 的约束：**只禁变松**。本 plan 是纯新增、零删除、且逐条自查不变松，因此不落在禁止面内。
**但两处措辞确实不一致，这件事必须有落点**——本 plan 把它登记为 Deferred（人动作），不留在散文里。

**先例复核（不作为授权依据，只作为纪律来源）**：plan `2026-08-21-2220-2` 在同一张表下往 `gates.yml`
只增了一个 job，自查证据是 `git diff 3fed439..HEAD -- .github/workflows/` → **唯一 hunk**
`50 insertions / 0 deletions`，`on:` / `permissions:` 一行未动，无 trailer，通过了独立关闭审计。
⚠️ **本 plan 的自查比它更严**（见 Phase 2）——独立评审指出「deletions=0」本身**证明不了**
「现有 7 个 job 一行不改」：往既有 job 块里**插**一行也是纯新增。

### 本 plan 会触发/承接的三条已登记事项

1. `docs/backlog/gate-fixtures-pollute-the-live-site.md` 的新触发条件逐字：「当 CI 的 L2 覆盖面扩到
   `test_snapshot_diff_structured.py` 或 `test_customization_roundtrip_delete.py` 时⋯或当 CI 的 L2 站点不再是一次性的时」。
   **本 plan 正是前者**，必须在 Phase 3 给结论。
2. plan `2026-08-21-2220-2` 的 Deferred「判定器没有「live 名单」这个概念」——由前驱 plan 交付，本 plan 消费并记为了结。
3. **前驱 plan 指名交给本 plan 的「判定器 CI 侧守卫」**：判定器 `tools/gates/check_expected_red.py`
   此刻三层皆无保护（`gates-untouched` 只 diff `tests/gates/**`、`gate-verify.mjs:22` 的
   `PROTECTED = ["tests/gates/"]`、`expected-red-ratchet` 只数 txt 行数），而 `gates-l1` 跑的就是它本身。
   **边界（前驱定的硬约束）**：守卫**不得覆盖 `tools/gates/expected-red.txt`**。
   **出处（逐字，不用二手转述）**：`AGENTS.md` 红线 1 的「边界」句——「预期红名单
   `tools/gates/expected-red.txt` 不在此列——它是账本不是裁判，测试转绿时应当在同一提交里划掉对应行（只能变短）」；
   以及 `ai-autonomy-policy.md` Protected Areas 第 2 行——**allowed（只能变短）**，
   「名单**变长**仍需 `Gates-Change-Approved-By:`」，服务端控制是 `expected-red-ratchet` job。
   把账本圈进守卫会让**每一次合法的划短**在 CI 上失败，直接抵触红线 1 自己开的这个口子。
   ⚠️ **不要引 STATE §2 11:20Z**——那条逐字是「名单必须反映判定器实际看到的，不是我知道的」，
   讲的是**名单里该写什么**，不是**谁可以改它**（前驱起草时误引过，已改准）。

## Goals

- `.github/workflows/gates.yml` **新增两个 job，全部追加在文件末尾**：
  · 一个在 runner 上起栈后用 **live 判定模式**对**全部 19 条门禁**判定（本 plan 的主交付）；
  · 一个把 `tools/gates/check_expected_red.py` 纳入「未经批准不得改动」的服务端复核（前驱指名交办）。
- 让「live 只在本机做过，CI 未验证」第一次有资格被改写——**只在 CI 真跑出结果之后**，
  且按实跑结果改写 Current Baseline 那张表里的**四处**（①②③④），**不含**已关闭 plan 的关闭证据。
- 按 CI 实跑结果裁定站点污染那条 Deferred。
- roadmap 工作项 9 具备置 `done` 的条件（是否置由关闭审计判断）。

## Non-Goals

- **不删、不改现有 7 个 job**，包括覆盖面被新 job 完全包住的 `gates-l2`。退休它是删除动作，**由人决定**。
- **不动 `on:` / `permissions:`**，**不新增 `concurrency:`** —— 缩小触发范围与允许取消在途运行都是变松。
- **不改 `tests/gates/**`**（红线 1）。
- **不划 `tools/gates/expected-red.txt` 的任何一行。**
- **不改判定器 `tools/gates/check_expected_red.py`**（那是前驱的结果面）。发现缺陷回前驱改，不在这里打补丁。
  （**唯一例外**：Phase 2 守卫变异实验 ① 的临时空白提交，必须随即 revert、最终 diff 为零，
  判据见 Phase 3 自查。写在这里是因为 NB3 的教训——「显然可以调和」的事不写下来就会打架。）
- **不改 `agenerp/` 下任何产品代码。**（独立评审 B3，采纳）起草第一版允许「红在环境就修在 `agenerp/**`」，
  那与本 plan 的 Task Route（不改任何产品行为）直接冲突，会走进 Protected Areas 末行那个 `plan-first` 面
  而不带它要求的证据，且「改实现直到 CI 变绿」与「把实现调到迁就门禁」在操作上无法区分。
  runner 上的实现缺口一律**交出去**，处置写在 Phase 2。
- **不改任何已关闭 plan 的 Closure 段。**

## Task Route

- Type: `deployment change + verification or audit work`（改的是 CI 判定面，**不改任何产品行为**）
- Owner Docs: `docs/architecture/system-baseline.md` 判定方式节（前驱提升后的 `## 14.4`）·
  `docs/backlog/p0-foundation-roadmap.md` · `docs/context/project-context.md` 验证命令表 ·
  `docs/context/ai-autonomy-policy.md`（第 72 行的转录声明 + Protected Areas 表）·
  `docs/backlog/gate-fixtures-pollute-the-live-site.md` · `AGENTS.md` 红线 2 与裁判规则 2/3/4
- Skill Selection Basis: `docs/skills/README.md` 没有覆盖「改 CI 判定面」的条目；全程 `Skill: none`。

## Infrastructure And Config Prereqs

- **硬前置：前驱 plan `2026-08-22-0027-1` 已关闭，且它 Phase 3 的 live 整目录判定结论已知。**
  ⚠️ **前驱的 exit 0 是在本机（端口 18080、长期存活的站点）拿到的，不自动迁移到 runner 的全新站点上**；
  方向恰好是有利的那一侧（全新站点没有历史孤儿列），但这仍是推理不是实测——CI 那一跑就是来实测它的。
- runner：`ubuntu-latest`，自带 docker 与 compose。**无需新增 secret，不动 `permissions:`。**
- 新 job 的构建步骤按 `gates-l2` 同款：`actions/checkout@v4` · `actions/setup-python@v5`（3.11）· `pip install pytest`。
  **这一步不可省**：`check_expected_red.py:59` 用 `sys.executable, "-m", "pytest"` 拼命令、`:61` 起子进程，pytest 必须装在那个解释器里。
- **CI 实跑的落地路径由 Phase 1 的 `Decision` 决定（PR vs 直推 `main`）**，不预设。
- 无数据迁移。**回滚策略**：全部改动是文本；新 job 若稳定红且原因不可修，回滚 = revert 掉那个提交，
  其余 7 个 job 不受影响（一行都没改过它们）。若走 PR 路径，回滚 = 不合并，成本更低。

## Execution Plan

### Phase 1 — 前置核对与两个新 job 的形状

Status: completed
Targets: 本 plan 文件（`Decision` 落点）· `docs/architecture/system-baseline.md`（`## 14.4`）
Skill: `none`

- Item Types: `Proof | Decision`
- Prereqs: 无（本 plan 是本批第二顺位，前置核对就是第一项）

- [x] `Proof` **开工前置检查（第一步，不做完不许改 `gates.yml`）**，五条全部成立才继续：
      ① 记下开工 sha（`git rev-parse HEAD` + `git status --porcelain`，输出抄进本节）；
      ② 前驱 plan 的 `Plan Status` 是 `completed`；
      ③ `python3 tools/gates/check_expected_red.py` 在**默认环境**下 exit 0（判定器没被改坏）；
      ④ `grep -n '^## 14.4' docs/architecture/system-baseline.md` **有命中**（前驱确实把判定方式节提升了）；
      ⑤ 前驱 Phase 3 的 live 判定已被证明**能返回 exit 0**（整目录绿，或前驱记录的收窄正向对照绿）。
      **任一条不成立：立即停手**，不改 `gates.yml`、不提交，往 `docs/masterplan/STATE.md` §3 **追加**一行
      说明前置未就绪，并把本 plan 置为 `Plan Status: deferred`（**不要置回 `draft`**——`draft` 会被
      `draftPlans()` 重新捡起走 `REVIEW_PLANS` → `EXEC_PLANS` 来回弹）。
      - Skill: `none`
- [x] `Decision` **定新增的形态：两个 job，全部追加在文件末尾。**
      本 plan 要落两件事：主判定 job，以及前驱交办的判定器守卫。
      **候选 (a) 主判定新增一个 job + 守卫直接扩 `gates-untouched` 的 diff 范围**；
      **候选 (b) 两件事都做成新 job，全部 append 到文件末尾**；
      **候选 (c) 就地扩 `gates-l2` 的覆盖面**。
      **推荐 (b)。** 决定性理由是自查方案：(b) 让「新文件以旧文件为**行前缀**」这条**机械可核**的判据成立
      （`gates-l2` 实测是文件里最后一个 job，追加即可），它一次性覆盖了「7 个 job 一行不改」
      「`on:`/`permissions:` 不动」「零删除」三件事；(a) 要改 `gates-untouched` 的脚本体，
      (c) 要替换 `gates-l2` 的步骤——两者都会打掉前缀性质，于是每一轮都要重新论证「这次的改动不算变松」，
      把可机械核对的判据换成一场辩论。
      **代价照实记**：runner 会起两次栈（`gates-l2` 一次、新 job 一次），CI 墙钟约翻倍；
      `gates-l2` 的覆盖面被新 job 完全包住，**它变成冗余**；守卫 job 与 `gates-untouched` 逻辑近似重复。
      **残余风险**：冗余会让人误以为它们判的是不同东西。缓解是 `## 14.4` 写清楚 + 把「退休 `gates-l2`」
      登记为 Deferred（人动作，因为那是删除）。
      - Skill: `none`
- [x] `Decision` **定 CI 实跑的落地路径：PR vs 直推 `main`**（独立评审 B7，本项为新增）。
      **候选 (a) 直推 `main`** —— 先例是 plan `2026-08-21-2220-2`（run `32499273158`，sha `6ac1005`）。
      **候选 (b) 开 PR**，`gates.yml` 的 `on:` **已经含 `pull_request`**，且 `gates-untouched` /
      `expected-red-ratchet` 两个 job 都显式处理了 PR 路径（用 `base.sha` / `head.sha`）。
      **推荐 (b)**：覆盖面完全相同（八个 job 全跑），但把工作流改动**挡在 `main` 之外**直到证据到手；
      回滚从「在 `main` 上 revert」降级成「不合并」，严格更可逆。
      本 plan 起草第一版按先例选了 (a)，那是**只凭先例、没有权衡**——先例证明 (a) 可行，不证明 (a) 更好。
      **代价**：多一次开 PR 与合并的动作；PR 与 push 两次触发会跑两遍（可接受，都是绿才合）。
      **⚠️ 开 PR 与合并都是对外动作**，必须显式执行、显式留痕，不得默默发生。
      **⚠️ 照实记（独立评审 nit 3）**：本仓 91 个提交里 **0 个 merge commit**，
      **PR 路径从未真正跑过**。「八个 job 全跑、`gates-untouched` / `expected-red-ratchet` 用
      `base.sha`/`head.sha` 处理 PR」是**读代码读出来的**，不是观测到的——
      正是本 plan 要消灭的那种「本机独证」的同类。因此**第一个 PR 同时也是 PR 路径自己的首次实测**：
      若 `gates-untouched` / `expected-red-ratchet` 在 PR 上红，**先排除「这是 PR 路径自身的缺陷」**，
      再谈是不是真违规。这条分流写进 Phase 2 的取证要求。
      - Skill: `none`
- [x] `Decision` **定主判定 job 的命令与 env**（runner 取值与本机不同，不许照抄本机那串）：
      · **先起栈**：单独一步 `docker compose -f docker-compose.yml up -d --wait --wait-timeout 900`
        （沿用 `gates-l2` 已实证的 900）；
      · `AGENERP_LIVE: "1"` · `AGENERP_ADMIN_PASSWORD: admin` · `AGENERP_SITE: frontend` ·
        `AGENERP_SITE_URL: http://127.0.0.1:8080`（冗余但更好读，见 Current Baseline）·
        **`AGENERP_HTTP_PORT` 不设**；
      · 判定命令是 **`python3 tools/gates/check_expected_red.py`**（整目录 19 条），**不是**逐文件 pytest；
      · **必须在 `## 14.4` 里点名 `AGENERP_SITE` 的副作用**：它把
        `test_two_snapshots_of_unchanged_site_diff_empty` 与 `test_diff_is_structured_not_text`
        从离线来源翻到活站点上（实测影响面恰好这两条），两条绿 L1 因此变成依赖活站点。
      - Skill: `none`
- [x] `Decision` **定失败取证与 job 的"不许变松"写法**（`if: always()`，不影响判定）：
      · 取证三条：`docker compose -f docker-compose.yml ps` ·
        `docker compose -f docker-compose.yml logs backend --tail 200` ·
        `docker compose -f docker-compose.yml logs bootstrap-homepage --no-log-prefix`
        （**一律带 `-f`**，与文件里其余步骤同一约定）；收尾 `docker compose -f docker-compose.yml down -v`，`if: always()`。
      · **判定步骤的 `run:` 必须是单条命令**，不含 `||`、不含 `;`、不含尾随 `exit`；
        任何多行 `run:` 一律以 `set -euo pipefail` 开头（**这是本 plan 自己立的规矩，比现状更严**——
        实测该指令只在 4 个 job 里出现过，见 Current Baseline，别把它说成已有惯例）。
      · **不加 `continue-on-error`**；`if:` 只允许出现在取证与拆栈两类步骤上、且只能是 `if: always()`。
      - Skill: `none`
- [x] `Proof` **把上述结论落进 `## 14.4`**（补上「CI 怎么用这个判定模式」那半，前驱只写了判定契约）。
      - Skill: `none`

Exit Criteria:

- [x] 五条前置核对各有实测结论写进 plan（命令原文 + 退出码）
- [x] 四个 `Decision` 各自写下选择、备选与残余风险；其中「PR vs 直推」是显式权衡而非援引先例
- [x] `## 14.4` 已补上 CI 用法那半，且点名了 `AGENERP_SITE` 的副作用
- [x] `docs/logs/` 更新

#### Phase 1 实测与决定记录（2026-08-22）

##### 开工前置检查 —— 五条全部成立

**① 开工 sha 与工作区状态**

```
$ git rev-parse HEAD
7b0f585f7c8082a64902da65e6e3314cb239dc9f
$ git status --porcelain
（无输出）
```

**开工 sha 逐字：`7b0f585f7c8082a64902da65e6e3314cb239dc9f`**，工作区干净。
本 plan 后文所有「用开工 sha 作基线」的自查都指这一条。

**② 前驱 plan 的 `Plan Status`**

```
$ grep -n '^> Plan Status:' docs/plans/p0-foundation/2026-08-22-0027-1-live-mode-gate-verdict.md
3:> Plan Status: completed
```

**③ 默认环境下判定器 exit 0**

```
$ python3 tools/gates/check_expected_red.py ; echo "exit=$?"
判定模式：default —— 按 tools/gates/expected-red.txt 判定
门禁 19 项：预期红 7，绿 12，跳过 0
✅ 与预期红名单完全一致
exit=0
```

**④ `## 14.4` 确实存在**

```
$ grep -n '^## 14.4' docs/architecture/system-baseline.md ; echo "exit=$?"
383:## 14.4 门禁判定器的两种判定模式，与判定器自身的保护现状（2026-08-22 追加）
exit=0
```

前驱确实把判定方式节提升成了独立的 `## 14.4`（起草时该文件 393 行，现为 453 行）。

**⑤ 前驱 Phase 3 的 live 判定已被证明能返回 exit 0**

前驱 plan 逐字记录：整目录 live 判定跑了 6 次，**第 1 跑 exit 1**
（`门禁 19 项：红 1，绿 18，跳过 0`，红因是 `::test_no_orphan_column_left_behind`），
**第 2/3/4/5 跑均 exit 0**（`门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`）。
前驱按裁判规则 3 记为「不可复现」，并登记成一条 `watch-only residual` Deferred。

⚠️ **这一条对本 plan 的直接后果，先写在这里**：本机上已经观测到
`::test_no_orphan_column_left_behind` 在整目录 live 判定下**是间歇性的**。
runner 的站点是全新的（没有本机那 6 条 `agenerp%` 历史孤儿列），方向上更有利，
但**间歇性本身不因站点新旧而消失**。因此 Phase 2 的判定算术里那条
「首轮红、复跑绿 → 结论是『首轮红、复跑绿、不可复现』而不是 `success`」
**不是假想分支，是一个已知有先例的分支**。

**结论：五条全部成立，Phase 1 继续。**

##### `Decision` 一 —— 新增的形态：取 (b)，两个新 job 全部追加在文件末尾

**选 (b)。** 决定性理由是自查方案的可机械核对性：`gates-l2` 实测是 `gates.yml` 里的最后一个 job
（实测该文件 190 行，`gates-l2:` 在第 153 行，其后没有别的 job 键），
所以纯追加会让「新文件以旧文件为**行前缀**」这条判据成立，一次性覆盖
「7 个 job 一行不改」「`on:` / `permissions:` 不动」「零删除」三件事。

**备选未选**：
- **(a) 主判定新增 job + 守卫直接扩 `gates-untouched` 的 diff 范围** —— 要改 `gates-untouched` 的脚本体，
  打掉行前缀性质，此后每一轮都要重新论证「这次的改动不算变松」。
- **(c) 就地扩 `gates-l2` 的覆盖面** —— 要替换 `gates-l2` 的步骤，同样打掉行前缀性质，
  且属于「改现有 job」，落在 Non-Goals 里。

**代价照实记**：runner 会起两次栈（`gates-l2` 一次、`gates-l2-live` 一次），CI 墙钟约翻倍；
`gates-l2` 的覆盖面被 `gates-l2-live` **完全包住**，它变成冗余；
`verdict-tool-untouched` 与 `gates-untouched` 逻辑近似重复。

**残余风险**：冗余会让人误以为两者判的是不同东西。缓解是 `## 14.4` 写清包含关系，
并把「退休 `gates-l2`」与「两个守卫 job 逻辑重复」各登记成一条人动作 Deferred（本 plan 已有）。

##### `Decision` 二 —— CI 落地路径：取 (b) 开 PR

**选 (b) 开 PR**，不是援引先例，是权衡后的选择：

| | (a) 直推 `main` | (b) 开 PR |
|---|---|---|
| 覆盖面 | 9 个 job 全跑 | 9 个 job 全跑（`on:` 里本来就有 `pull_request`） |
| 工作流改动进 `main` 的时机 | **在证据到手之前** | 在证据到手之后 |
| 回滚 | 在 `main` 上 revert | **不合并** |
| 守卫变异实验能不能做 | 只能在 `main` 上推三个实验提交再清理 | 在分支上做，`main` 全程干净 |

**决定性理由**：守卫的三次变异实验必须真的推上去才拿得到 run id，其中 experiment ① **必须红**。
在 (a) 下这意味着往 `main` 推一个已知会红的提交；在 (b) 下它被挡在分支上。
回滚从「在 `main` 上 revert」降级成「不合并」，严格更可逆。

**代价**：多一次开 PR 与合并的动作；PR 与 push 两次触发会跑两遍。

**⚠️ 照实记**：本仓 91 个提交里 **0 个 merge commit**，**PR 路径此前从未真正跑过**。
「八个 job 全跑、`gates-untouched` / `expected-red-ratchet` 用 `base.sha`/`head.sha` 处理 PR」
是读代码读出来的，不是观测到的——正是本 plan 要消灭的那种「本机独证」的同类。
**因此第一个 PR 同时也是 PR 路径自己的首次实测**：若 `gates-untouched` / `expected-red-ratchet`
在 PR 上红，先排除「这是 PR 路径自身的缺陷」，再谈是不是真违规。

**⚠️ 落地路径带出的一个必须先做的动作（起草时没预见到，实测发现，照实记）**：
开工时 `origin/main` 停在 `8b1e95c`，本地 `main` 领先 **6 个提交**（前驱 `0027-1` 的全部交付，已关闭），
而那 6 个提交**改过 `tools/gates/check_expected_red.py`**（判定器的 live 模式就在里面）。
若不先把 `main` 推上去，PR 的 base 就是陈旧的 `8b1e95c`，
`verdict-tool-untouched` 在 `base.sha..head.sha` 上会看见前驱对判定器的改动而报红——
**那是 base 陈旧造成的假阳，不是路径清单写错**。
处置：**先 `git push origin main` 把已关闭的前驱工作推上去**，再从 `7b0f585` 开分支。

```
$ git push origin main
   8b1e95c..7b0f585  main -> main
```

##### `Decision` 三 —— 主判定 job 的命令与 env

job 名 **`gates-l2-live`**，`runs-on: ubuntu-latest`，步骤序列：

1. `actions/checkout@v4` · `actions/setup-python@v5`（3.11）· `pip install pytest`
   —— **不可省**：`check_expected_red.py:67` 用 `sys.executable, "-m", "pytest"` 拼命令、`:69` 起子进程，
   pytest 必须装在那个解释器里。
   ⚠️ **行号照实更正**：Current Baseline 与 Infrastructure 两处写的是 `:59`/`:61`，那是**起草时**的行号；
   前驱 `0027-1` 改过这个文件（加了 live 模式与纯函数接缝），实测现在是 `:67`/`:69`。
   引用的事实没变，行号变了，此处按活文件写。
2. 打 docker / compose 版本（沿用 `gates-l2` 的做法，版本差是 `1022-1` 登记的 watch-only residual）。
3. **起栈单独一步**：`docker compose -f docker-compose.yml up -d --wait --wait-timeout 900`
   （沿用 `gates-l2` 已实证的 900）。
4. **判定步骤**：`python3 tools/gates/check_expected_red.py`（整目录 19 条，**不是**逐文件 pytest），env 为
   `AGENERP_LIVE: "1"` · `AGENERP_ADMIN_PASSWORD: admin` · `AGENERP_SITE: frontend` ·
   `AGENERP_SITE_URL: http://127.0.0.1:8080`；**`AGENERP_HTTP_PORT` 不设**（走 compose 默认 8080，runner 上已实证空闲）。

`AGENERP_SITE_URL` 是**冗余而非新耦合**：`agenerp/site.py:130` 的 `default_base_url()` 已经回落到
`AGENERP_HTTP_PORT` → `DEFAULT_HTTP_PORT = "8080"`（`site.py:49`），与 compose 默认一致；显式写出来只是更好读。

**`AGENERP_SITE: frontend` 是 job 级的，它有一个必须点名的副作用**：
它把 `tests/gates/test_snapshot_diff_structured.py` 的
`::test_two_snapshots_of_unchanged_site_diff_empty` 与 `::test_diff_is_structured_not_text`
**从离线来源翻到活站点上**（这两条不取任何 fixture、直接调 `capture()`）。
实测影响面**恰好只有这两条**——`test_normalizer_idempotent.py` / `test_seed_dataset_absurdity.py` /
`test_zero_dep_boot.py` 都不调 `capture()`。两条此刻是绿的 L1，进 CI 后变成依赖活站点。
**这一条已写进 `## 14.4`。**

##### `Decision` 四 —— 失败取证与「不许变松」的写法

- **取证三条**，全部 `if: always()`、全部带 `-f docker-compose.yml`：
  `ps` · `logs backend --tail 200` · `logs bootstrap-homepage --no-log-prefix`；
  收尾 `down -v`，同样 `if: always()`。
- **判定步骤的 `run:` 是单条命令**：`python3 tools/gates/check_expected_red.py`，
  不含 `||`、不含 `;`、不含尾随 `exit`。
- **任何多行 `run:` 一律以 `set -euo pipefail` 开头**（本 plan 自己立的规矩，比现状更严——
  实测该指令此前只在 4 个 job 里出现过）。新增块里只有两处多行 `run:`：
  `gates-l2-live` 的版本打印步骤、`verdict-tool-untouched` 的脚本体，两处都写了。
- **不加 `continue-on-error`**；`if:` 只出现在取证与拆栈两类步骤上、且只能是 `if: always()`；
  **不新增 `concurrency:`**。

**残余风险**：`set -euo pipefail` 只在新增块里立规矩，现存 5 个多行 `run:` 里的第 5 个
（`gates-l2` 打版本号那步）仍然没有——本 plan **不去补它**，补它就是改现有 job，打掉行前缀自查。
这条不一致照实记在这里，不假装它不存在。

### Phase 2 — 落地两个新 job，并让 CI 真跑一次

Status: **停机中断，未完成**（`Add` / 红线 2 自查 / 静态自检 / CI 实跑 / 红因分流五项已完成；
  **守卫变异实证未做**——做它要再跑三轮 CI，而停机线已触发。reopen 后从那一项续跑）
Targets: `.github/workflows/gates.yml`（**只在文件末尾追加两个 job**）· `docs/logs/2026/08-22.md`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1 完成

- [x] `Add` 按 Phase 1 的 `Decision` 在 `gates.yml` **末尾追加主判定 job**（形如 `gates-l2-live`）。
      注释写清：它跑整目录 live 判定（19 条）、它与 `gates-l2` 的覆盖面包含关系、以及为什么没有就地合并。
      - Skill: `none`
- [x] `Add` 在 `gates.yml` **末尾追加判定器守卫 job**（形如 `verdict-tool-untouched`），
      逻辑照 `gates-untouched` 但 diff 路径为 **`tools/gates/check_expected_red.py`**
      （可一并含 `tools/gates/gate-verify.mjs`），放行方式同样是提交信息里的 `Gates-Change-Approved-By:` trailer。
      **硬边界（前驱定的）：路径清单里不得出现 `tools/gates/expected-red.txt`**——
      账本允许 loop 在同一提交里划短（`AGENTS.md` 红线 1 的「边界」句 +
      `ai-autonomy-policy.md` Protected Areas 第 2 行 `allowed（只能变短）`，
      服务端控制是既有的 `expected-red-ratchet` job）。圈进去会让每一次合法的划短在 CI 上失败。
      ⚠️ **本 plan 自己的提交会触发这个新 job 吗？** 不会——本 plan 不改判定器。若实测触发了（**假阳**），
      说明路径清单写错了，回来改清单，**不得**给本 plan 的提交加 trailer 绕过。
      **⚠️ 更危险的是反方向（独立评审 NB1）**：守卫**永远不触发**（假阴）时，CI 照样绿，
      与一个真正管用的守卫**长得一模一样**。`gates-untouched` 有三个提前 `exit 0` 分支
      （`未触及` / `首次推送，跳过 diff 比对` / `找到人工批准 trailer，放行`），
      抄错 `BASE` 推导、或让全零 sha 那条分支恒命中，守卫就永久绿而毫无作用。
      **因此本项必须把三处逐字钉死、不许「照抄大意」**：
      ① `BASE` / `HEAD` 的推导（`pull_request` 走 `base.sha` / `head.sha`，`push` 走 `github.event.before` / `github.sha`）；
      ② 全零 sha（首次推送）分支的处置；③ trailer 的匹配式 `^Gates-Change-Approved-By:`。
      三处与 `gates-untouched` 的差异（若有）要逐条写进 plan。
      - Skill: `none`
- [ ] `Proof` **守卫 job 的变异实证（NB1，本项为新增；没有它，守卫就是一条没证据的安全声明）**。
      本仓的既有标准就是这样：plan `2026-08-21-2220-2` 的关闭审计跑了 4 次变异 + 2 次绕过实验，
      **正是靠变异发现了一个真洞**；`project-context.md` 给每条门禁都记了变异结论。守卫不能例外。
      三次实验，全部在 PR 分支上做，**每次的 run id 与 job 结论逐字抄进 plan**：
      · **正向（必须红）**：往 `tools/gates/check_expected_red.py` 推一个**只改空白**的提交，
        提交信息**不带** trailer → `verdict-tool-untouched` 必须 `failure`。
        **⚠️ 空白改动必须落在语义无关处**（例如文件末尾加一个空行）——`gates-l1` 跑的就是这个脚本，
        改动若碰巧有语义，`gates-l1` 会跟着红，把实验污染成两个 job 同时红，说明不了守卫有没有牙齿。
        （与 experiment ③ 的污染防护同一条理由。）
      · **复原（必须绿）**：revert 掉它 → 必须回到 `success`。
      · **边界（必须不触发）**：推一个**只动 `tools/gates/expected-red.txt`** 的提交，
        → 守卫必须**不报错**。这条是本 plan 反复声明的那个硬边界（账本只能变短、划短不需 trailer）
        **第一次拿到实证**，此前它只是一句话。
        **⚠️ 这一改必须是加一行 `#` 注释，不能加一条真的 nodeid**（独立评审 nit 4）：
        `expected-red-ratchet` 的 `count()` 是 `grep -vE '^\s*(#|$)' | wc -l`，注释不计数、行数持平；
        加真 nodeid 会让名单变长、当场触发棘轮，把这次实验**污染**成两个 job 同时红，说明不了任何事。
      **做完把这几个实验提交清理掉，不留进最终 diff。**
      **拿不到这三条，守卫不算交付**——绿的 CI 证明不了一个从不触发的守卫。
      **⚠️ 覆盖面限定，照实记（独立评审 nit 3）**：三次实验全在 PR 分支上做，
      因此**只证明了 `pull_request` 那条 BASE/HEAD 推导路径**。`gates.yml` 的 `on: push` 限定
      `branches: [main]`，所以 `push` 那条分支**在合并前无法实测**——而 NB2 恰好又把合并后 `main` 上
      那次 `push` 运行定为权威运行。这句限定必须逐字写进 plan 与 `## 14.4`，
      **不得让它读成「守卫已全面实证」**。
      - Skill: `none`
- [x] `Proof` **红线 2 自查（机械可核，五条，全部输出逐字抄进 plan）**：
      · **(a) 前缀性**：`git show <开工 sha>:.github/workflows/gates.yml` 必须是新文件的**行前缀**。
        实测写法：`diff <(git show <开工 sha>:.github/workflows/gates.yml) <(head -n $(git show <开工 sha>:.github/workflows/gates.yml | wc -l) .github/workflows/gates.yml)`
        → 期望**无输出**。这一条**同时**证明了「7 个 job 一行不改」「`on:` / `permissions:` 不动」「零删除」，
        比「deletions=0」严得多——往既有 job 里**插**一行也是纯新增，`deletions=0` 抓不到它。
      · **(a2) job 键集合**：`python3 -c "import yaml;print(sorted(yaml.safe_load(open('.github/workflows/gates.yml'))['jobs']))"`
        → 必须**恰好**是原有 7 个 job 名加上本次新增的 2 个。
        理由（独立评审 nit 2）：(a) 只证明旧**文本**没变，不证明旧 **job** 没被架空——
        纯追加也能**重新声明一个已有的 job 键**，`yaml.safe_load` 静默地后者胜出，(a) 与 yaml 静态检查都会放行。
        不是会误犯的错，但一行就堵上。
      · **(b) 禁用词**：对新增块 `grep -nE 'continue-on-error|concurrency|cancel-in-progress'` → **0 命中**。
      · **(c) `if:` 白名单**：新增块里的 `if:` 只允许是取证步骤与拆栈步骤上的 `if: always()`；
        逐条列出实际出现的位置与取值，**任何其它 `if:`（含 step 级）都算不合格**。
      · **(d) 失败吞噬**：新增块里每个多行 `run:` 首行是 `set -euo pipefail`；
        **`||` / `;` / 尾随 `exit` 的零次要求只针对主判定 job 的那一条判定步骤**——
        守卫 job 的脚本体照 `gates-untouched` 抄，**天生带三个提前 `exit 0` 分支**
        （未触及 / 首次推送 / 找到 trailer），把 (d) 套到它身上会得到一条必然失败的自查（独立评审 nit 4）。
        **守卫 job 的正确判据不是「没有 `exit`」，而是下面那条变异实证。**
      **任一条不成立就回退重做**，不许在 plan 里解释「虽然如此但没变松」。
      - Skill: `none`
- [x] `Proof` **落地前的本地静态自检**：
      `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))"` → exit 0；
      `docker compose -f docker-compose.yml config -q` → exit 0。
      理由：yaml 语法错在 runner 上表现为「job 根本没跑」，会被误读成「加了但没生效」。
      - Skill: `none`
- [x] `Proof` **让 CI 真跑（按 Phase 1 `Decision` 选定的路径）**。取 run id，
      **把两个新 job 的结论、墙钟、以及判定器输出的模式行与判定行逐字抄进 plan 与 log。**
      **结局的判定算术事先钉死（独立评审 B4 + NB2，防止「复跑成绿」或「改一版重来」被洗成「CI 已验证」）**：
      · **⚠️ 本条计数只针对主判定 job（`gates-l2-live`）的「非预期红」**（独立评审 NB3）。
        **必须先划清这条界线，否则本 Phase 的两个 `Proof` 项互相打架、无法同时满足**：
        守卫变异实证的 **experiment ①**（无 trailer 改判定器 → `verdict-tool-untouched` 必须 `failure`）
        是一次**预期红、且是必需证据**——它证明守卫有牙齿。它**单独成段记录**，
        **不计入**裁判规则 4 的连续红计数，**不影响**「CI 已验证」的判定。
        守卫 job 的**任何其它**红（非实验期间的、或实验之外的）仍按非预期红计。
        起草时把两条规则各写各的，结果是「跑了必需的实验就永远写不了『CI 已验证』」——
        那会逼执行者临场发明例外，正是本条算术要防的行为。
      · **计数锚在 plan 上，不锚在 sha 上。** 主判定 job 的**任何一次非预期红**——不管发生在哪个 sha 上、
        中间是否 amend / rebase / force-push、是 PR 事件还是 push 事件——都是**本 plan 的永久证据**。
        改写提交**不清零**计数；裁判规则 4 的「连续 2 轮红」同此口径。
        ⚠️ 这一条是 NB2 补的：B4 原来把结论锚在 sha 上，而 B7 又把落地路径改成 PR，
        PR 分支上 force-push 换 head sha 是家常便饭——「落地 sha 上的第一次运行绿」于是**字面为真而实质为假**。
      · **权威运行**：以**合并后 `main` 上那次 `push` 事件的运行**为交付证据；
        合并前 PR 上的每一次运行**一并记录**，不得只留绿的那次。
      · **「CI 已验证」的充要条件**：本 plan 执行期间主判定 job **从未出现过非预期红**（含 PR 上的每一次）。
      · **出现过红、后来绿了** → 结论**不是** `success`，而是**「首轮红、复跑绿、不可复现」**，
        这七个字必须逐字写进 Phase 3 改的每一处。**红的运行是永久证据，不因后来的绿而消失。**
      · **红且复跑仍红** → 按红因分流（下一项）。
      · 上述一切只约束**主判定 job**；守卫 job 的判定见它自己那条变异实证项。
      · 任何情形都不许把某条门禁从覆盖面里摘出来——摘出来就是缩小覆盖面，等于变松。
      - Skill: `none`
- [x] `Proof` **红因分流与停机线**：
      · 红在**判据**（某条门禁在 runner 上真的不成立）→ **这是 CI 抓到的真问题**，逐字记进 plan / log / STATE §2。
      · 红在**环境或实现**（例如 `agenerp/oob.py` 的带外命令在 runner 上够不到 db）→
        **本 plan 不修**（`agenerp/**` 是 Non-Goal）。处置固定为：逐字记录 → 往 STATE §3 **追加** needs-human →
        置 `Plan Status: deferred` 并写明重开条件 → 由 successor plan 承接，
        且 successor 必须带上 Protected Areas 末行对 `agenerp/apply.py` 删除路径要求的
        「实跑前后全量 `capture` 对照」证据。
      · **CI 连续 2 轮红即停机**（`AGENTS.md` 裁判规则 4 逐字）。**非预期红的计数只增不减**，
        复跑变绿不清零——清零就等于给「重试到绿」开了门。**守卫变异实验 ① 的那次预期红不入这个计数。**
      - Skill: `none`

Exit Criteria:

- [x] `gates.yml` 末尾多出两个 job，红线 2 自查五条全部为期望值且输出逐字在 plan 里
- [x] 静态自检两条 exit 0
- [x] CI 至少跑过一次，run id / 两个 job 的结论 / 判定器模式行与判定行逐字在 plan 与 log 里
- [ ] **守卫三次变异实验各有 run id 与 job 结论逐字在 plan 里**，结果为
      ① `failure` / ② `success` / ③ 未触发；三条实验提交已清理，最终 diff 为零
- [x] `## 14.4` 已写入守卫的「只覆盖 `pull_request` 路径、`push` 分支合并前无法实测」这条限定
- [x] 结论已按钉死的算术归入 `success` / 「首轮红、复跑绿、不可复现」/ 红因分流三者之一
- [x] 若红在环境或实现：`agenerp/**` 一行未改，STATE §3 有追加行，本 plan 置 `deferred`
- [x] `docs/logs/2026/08-22.md` 更新

#### Phase 2 实测记录（2026-08-22）—— **落地成功，CI 判定连续两轮红，按裁判规则 4 停机**

##### 两个新 job 已落地

`.github/workflows/gates.yml` 末尾追加 **`gates-l2-live`**（19 条全量 live 判定）与
**`verdict-tool-untouched`**（判定器守卫），提交 **`9a8832f`**。文件 190 行 → 308 行，新增块 118 行。

守卫的三处易错点与 `gates-untouched` **逐字同构，无差异**：
① `BASE`/`HEAD` 推导 —— `pull_request` 走 `base.sha`/`head.sha`，`push` 走 `github.event.before`/`github.sha`；
② 全零 sha（首次推送）分支 —— `echo "首次推送，跳过 diff 比对"; exit 0`；
③ trailer 匹配式 —— `grep -q '^Gates-Change-Approved-By:'`。
**唯一差别是 diff 路径**：`'tools/gates/check_expected_red.py' 'tools/gates/gate-verify.mjs'`，
**清单里没有 `tools/gates/expected-red.txt`**（硬边界）。

##### 红线 2 自查五条 —— 全部为期望值（开工 sha `7b0f585`）

**(a) 行前缀**

```
$ diff <(git show 7b0f585:.github/workflows/gates.yml) \
       <(head -n $(git show 7b0f585:.github/workflows/gates.yml | wc -l) .github/workflows/gates.yml)
（无输出）
diff-exit=0
```

**(a2) job 键集合**

```
$ python3 -c "import yaml;print(sorted(yaml.safe_load(open('.github/workflows/gates.yml'))['jobs']))"
['expected-red-ratchet', 'gates-l1', 'gates-l2', 'gates-l2-live', 'gates-untouched', 'loop-wiring', 'masterplan-links', 'roadmap-parseable', 'verdict-tool-untouched']

$ git show 7b0f585:.github/workflows/gates.yml > /tmp/old-gates.yml && python3 -c "import yaml;print(sorted(yaml.safe_load(open('/tmp/old-gates.yml'))['jobs']))"
['expected-red-ratchet', 'gates-l1', 'gates-l2', 'gates-untouched', 'loop-wiring', 'masterplan-links', 'roadmap-parseable']
```

**恰好**是原有 7 个加上新增的 2 个，没有任何已有 job 键被重新声明。

**(b) 禁用词 —— 0 命中**

```
$ tail -n +191 .github/workflows/gates.yml > /tmp/new-block.yml   # 旧文件 190 行
$ grep -nE 'continue-on-error|concurrency|cancel-in-progress' /tmp/new-block.yml
grep-exit=1（无输出 = 0 命中）
```

**(c) `if:` 白名单 —— 4 处，全部合格**

```
$ grep -nE '^\s*if:' /tmp/new-block.yml
54:        if: always()     ← 取证 —— 服务状态
58:        if: always()     ← 取证 —— backend 日志
62:        if: always()     ← 取证 —— 引导服务日志
66:        if: always()     ← 拆栈（无条件）
```

四处**全部**落在取证与拆栈两类步骤上，取值**全部**是 `if: always()`；无 job 级 `if:`，无其它 step 级 `if:`。

**(d) 失败吞噬**

```
$ grep -nE '^\s*run: \|' /tmp/new-block.yml
33:        run: |          ← gates-l2-live 的版本打印步骤
92:        run: |          ← verdict-tool-untouched 的脚本体
$ grep -nE 'set -euo pipefail' /tmp/new-block.yml
34:          set -euo pipefail
93:          set -euo pipefail
```

两处多行 `run:` 首行**都是** `set -euo pipefail`。
主判定步骤：`run: python3 tools/gates/check_expected_red.py` ——
`grep -nE '\|\||;|exit'` 对该行 **0 命中**。
守卫 job 的三个提前 `exit 0` 分支按 plan 的规定**不套用这条**，它的判据是变异实证（未做，见下）。

##### 静态自检两条 —— exit 0

```
$ python3 -c "import yaml; yaml.safe_load(open('.github/workflows/gates.yml'))" ; echo $?
0
$ docker compose -f docker-compose.yml config -q ; echo $?
0
```

##### CI 实跑 —— **`gates-l2-live` 连续两轮红，同一条 nodeid，可复现**

落地路径按 `Decision` 二走 PR：**PR #1**（`https://github.com/lize-agent-engineering/AgenERP/pull/1`），
base `main`（`7b0f585`），head `9a8832f`。

**⚠️ 先记一条 PR 路径自己的首测结果**：往 `ci/0027-2-l2-full-live-gate` 分支推送
**没有触发任何运行**——`on: push` 限定 `branches: [main]`，只有开 PR 时的 `pull_request` 事件触发。
这与读代码读出来的一致，但此前从未观测过（本仓 0 个 merge commit），现在有实测了。

**run `32509351108`**（`pull_request`，head `9a8832f`），两次 attempt：

| attempt | `gates-l2-live` | 其余 8 个 job |
|---|---|---|
| 1 | **`failure`**（job `96856597161`，17:40:13Z→17:43:27Z） | 全部 `success` |
| 2（`gh run rerun --failed`，原样复跑） | **`failure`**（17:44:31Z→17:47:30Z） | 全部 `success` |

**两次 attempt 的判定器输出逐字完全相同**：

```
判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单
门禁 19 项：红 1，绿 18，跳过 0

❌ live 判定契约是全部门禁绿，下列门禁红了：
   tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind
##[error]Process completed with exit code 1.
```

**判定模式行确认判定器走的是 live 模式**，19 条一条不少，零 skip。
`verdict-tool-untouched` 两次 attempt 都是 `success`（本 plan 不改判定器，符合预期，尚未证明它有牙齿）。

##### 按钉死的判定算术归类

- **不是 `success`**：主判定 job 出现过非预期红。
- **不是「首轮红、复跑绿、不可复现」**：**原样复跑复现了**，同一条 nodeid、同一个计数
  （`红 1，绿 18，跳过 0`）。裁判规则 3 的「不可复现」分支在此**不适用**。
- **归入「红因分流」**，且**同时触发 `AGENTS.md` 裁判规则 4 的停机条件**：CI 连续 2 轮红。

##### 红因分流 —— 红在**实现**，本 plan 不修

红的那条判据是 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`
（逐字：`assert PROBE_FIELD not in orphans`）。它断言的是 `agenerp` 的行为——
`apply_pack` 删掉 Custom Field 之后**必须连物理列一起清掉**（清除面由 plan `2026-08-21-2220-1` 交付）。
断言在 runner 上不成立，**判据本身没有问题，不成立的是被判的那个实现**。
因此归入「红在环境或实现」这一支：**`agenerp/**` 是本 plan 的 Non-Goal，本 plan 一行不改。**

**新事实，照实记，不猜根因（裁判规则 3）**：

| | 本机（前驱 `0027-1` Phase 3） | runner（本次） |
|---|---|---|
| 整目录 live 判定跑数 | 6 | 2 |
| 该条门禁红的次数 | **1 / 6**，原样复跑 4 次全绿 | **2 / 2**，原样复跑仍红 |
| 站点 | 长期存活，`tabItem` 上有 6 条历史 `agenerp%` 孤儿列 | 全新（每次 `down -v`） |

起草时 Current Baseline 写的推理是「runner 的全新站点没有历史孤儿列，方向恰好是**有利**的那一侧」。
**这条推理被实测证伪**：全新站点上它不是偶发，而是稳定红。
**为什么，本 plan 不给答案**——那需要动 `agenerp/**` 才查得清，落在 Non-Goal 内，
且 `agenerp/apply.py` 的删除路径是 Protected Areas 的 `plan-first` 面，
Required Evidence 含「实跑前后全量 `capture` 对照」，在一个 CI 判定面的 plan 里顺手查它等于绕过那条证据要求。
交给 successor plan，**它必须带上那条 `capture` 对照证据**。

**这正是本 plan 存在的理由兑现了一次**：一条「只在某一台笔记本上绿过」的判据，
在 CI 上第一次跑就被抓出来是稳定红的。**CI 抓到了一个本机独证掩盖着的真问题。**

##### 停机处置（按 Phase 2 末项写死的固定处置执行）

- **PR #1 不合并**（`Decision` 二选 PR 路径换来的可逆性在这里兑现：回滚成本 = 不合并，`main` 全程干净）。
- **守卫 `verdict-tool-untouched` 的三次变异实验没有做**——做它们要再推三次、再跑三轮 CI，
  而停机线已经触发。**因此守卫此刻仍是一条没有牙齿证据的安全声明**，
  按本 plan 自己的规定「拿不到这三条，守卫不算交付」，**守卫未交付**。
  这一项**保持未打勾**，reopen 后从这里续跑。
- **`agenerp/**` 一行未改**，实测（基线用开工 sha）：

```
$ git diff --stat 7b0f585..HEAD -- agenerp tests/gates docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py tools/gates/expected-red.txt
（无输出）
$ git status --porcelain -- agenerp tests/gates docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py tools/gates/expected-red.txt
（无输出）
```

- **往 `docs/masterplan/STATE.md` §3 追加 needs-human 一行**（已做）。
- **`Plan Status` 由 `active` 置为 `deferred`**，重开条件写在文件头。
- **Phase 3 未执行**：它的第一项要「按实跑结果改准四处表述」，而结论是「红在实现、已停机」——
  在停机状态下把四处 owner doc 改成任何一种说法都为时过早，
  且 Phase 3 的 Prereq 逐字是「Phase 2 完成」，Phase 2 没完成。

### Phase 3 — 按实跑结果改准四处表述，裁定 Deferred，收尾

Status: **部分完成，随 Phase 2 一起停机**（4 个 `Fix` 已做：四处漂移就地改准 / 站点污染 Deferred 裁定 / `ai-autonomy-policy.md` 措辞已落成人动作 Deferred / roadmap「9 现状」；
  **未做**：把前驱两条 Deferred 记为「了结」——守卫尚未交付，写「了结」就是比证据更强的说法）
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/context/project-context.md` ·
  `docs/architecture/system-baseline.md`（`## 14.4`）· `docs/context/ai-autonomy-policy.md` ·
  `docs/backlog/gate-fixtures-pollute-the-live-site.md` · `docs/plans/p0-foundation/2026-08-21-2220-2-…`（**只追加**）·
  `docs/logs/2026/08-22.md` · `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Fix | Proof`
- Prereqs: Phase 2 完成且 CI 结论已知

- [x] `Fix` **改准 Current Baseline 那张表里的四处**（①②③④，**不多不少**）。确认的 owner-doc 漂移，
      按 Minimum Rule 14 不得降级成 follow-up。
      **写什么由 Phase 2 的结论决定，三种写法各自对应一种结论**（`success` / 「首轮红、复跑绿、不可复现」/
      「CI 上实跑过，结论是红，红因是 X」），**绝不能写成比证据更强的说法**。
      ⚠️ **`2026-08-21-2220-1` 的 Closure Gates 那行不在四处之内，一个字不改**——
      它是已关闭 plan 的历史证据，在关闭时为真。
      - Skill: `none`
- [x] `Fix` **裁定站点污染那条 Deferred**（`gate-fixtures-pollute-the-live-site.md`）。
      它的触发条件已被本 plan 满足，必须给结论，不许再往后推。
      **待核事实（看 Phase 2 的实跑日志，不要凭推理写）**：新 job 收尾是否仍 `down -v`、CI 站点是否仍一次性。
      若是 → 残留仍不累积，该条**维持 watch-only**，并把触发条件按新事实**就地**再改绑一次
      （照该文档 2026-08-21 那次补记的写法，不新开条目）。
      若不是 → 按该文档的 (a)/(b)/(c) 三个候选**登记给人**，loop 不替人选。
      - Skill: `none`
- [x] `Fix` **登记 `ai-autonomy-policy.md` 的措辞不一致**（独立评审 B5，本项为新增）。
      该表 `.github/workflows/**` 行写 `blocked`，而它自称是红线表的转录（第 72 行），红线 2 只禁变松。
      **本 plan 不替人改那一行**（改 Protected Areas 的 Rule 列等于替人定授权口径），
      而是在 `## Deferred But Adjudicated` 里落一条明确的人动作项。
      **本项要做的是**：确认那条 Deferred 已写进本 plan，并在 `## 14.4` 里留一句指向它，
      免得下一个要动 `gates.yml` 的 plan 从零再论证一遍。
      - Skill: `none`
- [ ] `Fix` **把前驱那两条 Deferred 记为了结**：在 plan `2026-08-21-2220-2` 的
      `Deferred But Adjudicated` 相应条目下**追加**一行指向本批两个 plan（**不改写已有行**——那是别人的关闭证据）。
      同时在 `## 14.4` 里写清：新 job 走判定器，**live 模式的契约是全绿零 skip，比预期红名单棘轮更紧**，
      因此「L2 在 CI 上不受棘轮保护」这条残余风险已被覆盖。
      - Skill: `none`
- [x] `Fix` **roadmap「9 现状」行**：写明两个 plan 各交付了什么、CI run id 与结论、两个新 job 的名字、
      以及工作项 9 的判据与工作项 8 判据的**包含关系**。
      **本 plan 不自行把工作项 9 置 `done`**——置状态是关闭审计的事。
      - Skill: `none`
- [x] `Proof` **收尾复跑与红线自查（用开工 sha 作基线，不用裸 `git diff`）**：
      · `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → 期望 exit 0；
      · `python3 -m pytest tests/contracts -q` → 期望 exit 0；
      · `ruff check agenerp tests/unit tests/contracts` → 期望 exit 0；
      · `git diff --stat <开工 sha>..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py`
        → 期望**输出为空**；
      · `git status --porcelain -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py`
        → 期望**输出为空**（两条一起才覆盖「已提交」与「未提交」两种情形）。
        **判定器被加进这份清单，是为了给「实验提交已清理干净」这句话配一条机械判据**
        （第 4 轮评审 nit 2）——此前它只是 Phase 2 里的一句叮嘱，与本 plan 反复批评的
        「没有判据的安全声明」是同一个毛病；
      · `git diff --numstat <开工 sha>..HEAD -- tools/gates/expected-red.txt` → 期望**输出为空**。
      全部命令原文 + 退出码 + commit sha 写进 log 与 STATE §2（**只追加**）。
      - Skill: `none`

Exit Criteria:

- [x] 四处表述已按实跑结果改准，且没有被改成比证据更强的说法
- [x] `2026-08-21-2220-1` 的 Closure Gates **未被改动**（`git diff` 对该文件为空）
- [x] 站点污染那条 Deferred 有明确结论
- [x] `ai-autonomy-policy.md` 措辞不一致已落成一条人动作 Deferred，且 `## 14.4` 有指向它的一句
- [x] `## 14.4` 已写入「live 模式的契约是全绿零 skip，比预期红名单棘轮更紧」这句棘轮覆盖说明
- [ ] 前驱两条 Deferred 已记为了结（**追加**，不改写他人已有行）
- [x] roadmap 有「9 现状」行，含与工作项 8 的包含关系
- [x] 红线自查六条命令输出为期望值
- [x] `docs/logs/2026/08-22.md` 与 STATE §2 各有对应记录（STATE 只追加）


#### Phase 3 实测记录（2026-08-22）—— **部分执行**：确认漂移就地改准 + Deferred 裁定；「了结」那条不写

##### 为什么在停机状态下仍然做了 Phase 3 的四个 `Fix`

Phase 3 的 Prereq 逐字是「Phase 2 完成且 CI 结论已知」，**Phase 2 没完成**（守卫变异实证未做）。
但**CI 结论已知且是终局**，而五处 owner doc 此刻正**逐字断言一件已经不成立的事**——
「**验证范围**：live 只在本机做过，CI 未验证」。
`Minimum Rule 14` 逐字要求「确认的 owner-doc 漂移不得降级成 follow-up」，
把这五处留到 reopen 之后再改，就是把一条**已确认**的漂移降级成 follow-up。
因此：**做**四个证据已完全确定的 `Fix`，**不做**那个依赖守卫交付的 `Fix`（见下）。
Phase 3 的 `Status` 如实写成「部分完成，随 Phase 2 一起停机」，不写 `completed`。

##### 改准的五处（四处 + 「9 现状」），三种写法里选的是**第三种**

plan 事先钉死三种写法：`success` / 「首轮红、复跑绿、不可复现」/「CI 上实跑过，结论是红，红因是 X」。
**实测归入第三种**，五处**全部**按第三种写，一处都没被写成比证据更强的说法：

| # | 出处 | 改成了什么 |
|---|---|---|
| ① | roadmap「5 现状」行 | 「CI 上真跑了整目录 live 判定⋯**结论是红，不是绿**，红因是 `::test_no_orphan_column_left_behind`，两次 attempt 都红、**可复现**，因此不是「不可复现」，更不是「CI 已验证」」 |
| ② | roadmap「6 现状」行 | 「该文件四条在 live 环境下全绿」**只在本机成立**；CI 上四条里的 `::test_no_orphan_column_left_behind` 两次都红 |
| ③ | `project-context.md` 第 58 / 59 行 | 「本仓唯一一条在 CI 上真跑过的 L2」已不成立；但**PR 未合并，`main` 上没有这个 job**，所以「定制包往返」那条**在 `main` 上仍是本机独证，而它在 CI 上已被证明不成立** |
| ④ | `## 14.4` | 两个新小节开头加**上线状态段**：这两个 job **不在 `main` 上**，只在分支与 PR #1 上，PR 未合并；并把「空窗期终点」「残余风险已收口」两句改准（终点未到达，收口方案未生效） |
| ＋ | roadmap「9 现状」行 | 二次补记：两个 plan 各交付了什么、两个新 job 的名字、红线 2 自查五条结果、**与工作项 8 判据的包含关系**、以及「job 有了、`success` 没有」所以工作项 9 保持 `planned` |

**⚠️ `2026-08-21-2220-1` 的 Closure Gates 一个字未改**，实测：

```
$ git diff --stat 7b0f585..HEAD -- 'docs/plans/p0-foundation/2026-08-21-2220-1*'
（无输出）
$ git status --porcelain -- 'docs/plans/p0-foundation/2026-08-21-2220-1*'
（无输出）
```

##### 站点污染那条 Deferred —— 裁定：**维持 watch-only**，触发条件再改绑一次

触发条件（「覆盖面扩到 `test_snapshot_diff_structured.py` 或 `test_customization_roundtrip_delete.py`」）
**已被本 plan 满足**，必须给结论，已在 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 就地补记
（照 2026-08-21 那次的写法，未新开条目）。

**待核的两个事实按 CI 日志核对，不是推理**：

```
拆栈（无条件）步骤（attempt 2，判定步骤是红的那一次）：
 Volume agenerp_sites          Removed
 Volume agenerp_db-data        Removed
 Volume agenerp_logs           Removed
 Volume agenerp_redis-queue-data  Removed
 Volume agenerp_redis-cache-data  Removed
 Network agenerp_default       Removed
```

12 个容器 + **5 个卷全部 `Removed`** + 网络 `Removed`。
⚠️ 这一跑的**判定步骤是红的，拆栈仍然执行了**——`if: always()` 在失败路径上实测生效。
→ CI 站点仍是一次性的，残留**不累积** → **维持 watch-only**。
新触发条件改绑为「**当 CI 的 L2 站点不再是一次性的时**」，旧那条已用掉。

**一条必须分清的相邻事实**：那次 CI 红的 `::test_no_orphan_column_left_behind`
**不是站点污染问题**——CI 站点是全新的，没有历史孤儿列可污染。它是实现问题，归 STATE §3 的 `[open]` 行。

##### 前驱两条 Deferred —— **不写「了结」**，理由写在这里

plan 要求在 `2026-08-21-2220-2` 的 `Deferred But Adjudicated` 下追加一行把两条记为「了结」。
**本 plan 不写这一行**，因为其中一条（「判定器的 CI 侧守卫」）**尚未了结**：
`verdict-tool-untouched` 只存在于未合并的 PR 上，且**没有变异实证**——
按本 plan 自己的规定「拿不到这三条，守卫不算交付」。
在别人的 plan 里追加一行说它「了结」，正是本 plan 反复批评的「比证据更强的说法」。
**该项保持未打勾，reopen 后与守卫变异实证一起做。**

##### 收尾复跑与红线自查（基线用开工 sha `7b0f585`）

| 命令 | 结果 |
|---|---|
| `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **exit 0**（`门禁 19 项：预期红 7，绿 12，跳过 0` / `✅ 与预期红名单完全一致` / `205 passed in 0.51s`） |
| `python3 -m pytest tests/contracts -q` | **exit 0**（`151 passed in 0.08s`） |
| `ruff check agenerp tests/unit tests/contracts` | **exit 0**（`All checks passed!`） |
| `git diff --stat 7b0f585..HEAD -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py` | **无输出** |
| `git status --porcelain -- tests/gates agenerp docs/masterplan/DECISIONS.md missions tools/gates/check_expected_red.py` | **无输出** |
| `git diff --numstat 7b0f585..HEAD -- tools/gates/expected-red.txt` | **无输出** |
| `git diff --numstat -- docs/masterplan/STATE.md` | **`8	0`** —— 8 增 0 删，**只追加**成立 |

判定器那条被放进前两条 pathspec，是给「实验提交已清理干净」配的机械判据。
⚠️ **本次守卫变异实验根本没做**，所以那三个实验提交从不存在——
这条判据在此处证明的是「本 plan 一次都没碰过判定器」，比「清理干净了」更强。

**scoped verification is not conflated with full verification**：本仓无全量套件
（`project-context.md` 第 61–62 行逐字：「本仓此刻没有全量套件（无 build、无 typecheck，L2 门禁未解锁）」），
上面这些绿是 **scoped verification**，不是「全量验证通过」。
**而本 plan 真正要交付的那条 CI 判定是红的**，绿的只是本机默认环境那几条。

## One Result Surface 复核（scope 在评审中扩过，按 Minimum Rule 4 复核一次）

本 plan 现在有两个交付物：主判定 job 与守卫 job。**它们仍是一个结果面**——
「`gates.yml` 上的服务端判定在 live 环境下对本仓的判据设施做出正确判定」，
两者共用同一份关闭证据（**同一条 PR / 同一批 CI 运行**、同一套红线 2 自查、同一批 owner-doc 更正）。
⚠️ 措辞在第 4 轮评审后改准：守卫的证据来自 PR 上的三次实验运行，主判定的交付证据来自合并后
`main` 上那次 `push` 运行——**不是同一次运行**，但同属一条 PR 的同一批。
**成立的前提是守卫带着自己的变异实证**（Phase 2 那一项）：没有它，守卫就是一个
「绿了但可能什么都没做」的第二交付物，那时才该拆成两个 plan。这一条写在这里，
免得关闭审计看到 scope 扩过却找不到复核记录。

## `Plan Status` 由谁写（写死，免得烧循环）

与本批第一个 plan 同一套归属，不再论证：

- `REVIEW_PLANS`：评审收敛后 `draft` → `active`。
- `EXECUTE`（Phase 1–3）：只打勾执行项与 Exit Criteria，`Plan Status` **保持 `active`**，
  `## Closure Gates` 十四框**保持未勾**。例外只有三条自置 `deferred` 的路径：
  Phase 1 首项前置未就绪、Phase 2 末项红在环境或实现、Phase 2 末项 CI 连续两轮红。
- `CLOSURE_AUDIT`：通过 → 勾框 + 置 `completed` + 补 `## Closure`；需改代码 → 保持 `active`；
  阻塞于人 → 置 `deferred`。

⚠️ `tools/mission-driver/prompts/execute.md` 第 4.a 条要求执行会话自置 `completed`，
与 `AGENTS.md` 裁判规则 1/2 冲突，按优先级次序**不执行**。该冲突已由 plan `2026-08-21-1553-1` 登记，不重复登记。

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-22）。
  逐条复核了 `Current Baseline`，确认多数、**证伪 3 条**，给出 **7 条 blocking**：
  · **B1** 引用的 `§14.4` **不存在**（该文件 393 行，最后一个编号节是 `## 14.3`，目标文本是其下一个不带编号的
    `###`，第 381 行）；七个勾选项指向一个不存在的节，且前驱 plan 有同样的错。
  · **B2** 红线 2 自查**比它自称抄的先例更弱**，漏掉四条**纯新增**的变松路径：
    ① `deletions=0` 证明不了「7 个 job 一行不改」（往既有 job 里插一行也是纯新增；先例的证据是**唯一 hunk**）；
    ② 新 job 的 `run:` 里 `|| true` / `; true` / `set +e` / 尾随 `exit 0` 都能让它静默变绿；
    ③ 只查了 **job 级** `if:`，**step 级** `if:` 同样能缩覆盖面；
    ④ 新增 `concurrency: cancel-in-progress: true` 能让在途门禁运行被取消（本仓 `.github/` 现无此键）。
  · **B3** Phase 2 的失败分支授权「修在 `agenerp/**`」，与本 plan Task Route（不改任何产品行为）直接冲突，
    且会走进 Protected Areas 末行那个 `plan-first` 面而不带其 Required Evidence；
    「改实现直到 CI 变绿」与「把实现调到迁就门禁」操作上无法区分。
  · **B4** 「首轮红、复跑绿」没有定性，执行者会把它当成 `success` 写进四处 owner doc，
    正是本 plan 自称要堵的「重试到绿」；且与裁判规则 4「连续 2 轮红即停机」的计数冲突。
  · **B5** Protected Areas 与红线 2 的措辞冲突被提出却**没有落地状态**（Anti-Slacking 四态之外）；
    并指出本 plan 手上最强的在文证据没被用上——`ai-autonomy-policy.md:72` 逐字
    「下表前八条**全部照抄** `AGENTS.md` 的红线表——此处不新增、不放宽任何一条」。
  · **B6** 两个「四处」清单不一致，其中一处指向**已关闭 plan `2026-08-21-2220-1` 的 Closure Gates**，
    按 Minimum Rule 14 会把执行者推去改别人的关闭证据。
  · **B7** 落地路径只凭先例选了直推 `main`，而 `on:` 里**本来就有 `pull_request`**，
    PR 路径覆盖面相同却严格更可逆，plan 从未权衡。
  另有 9 条 nit（`conftest.py` 行号应为 305/309/310-311；`AGENERP_SITE_URL` 是冗余不是新耦合，
  `site.py:130/49` 已有同样回落；`AGENERP_SITE` 的真实影响面是**恰好两条** L1 被翻到活站点上，未点名；
  新 job 缺 checkout/setup-python/pip 步骤而 `check_expected_red.py:61` 用 `sys.executable -m pytest`；
  取证步骤漏 `-f docker-compose.yml`；「`mariadb` 不在镜像里」是**编造的风险**（镜像钉死 `mariadb:10.6`，
  真正的 delta 是 runner 站点全新、本机站点有 6 条历史孤儿列）；两个 Phase 达到 80% 同类型阈值应声明；
  前置 ③ 用本机退出码给 runner 全新站点背书需点明；one result surface 成立）。
- Revision after iteration 1（本次修订，逐条对应）：
  新增 `## 术语约定` 写死「判定方式节 = 第 381 行的 `###`」，并把它改为「前驱提升为 `## 14.4`」+
  Phase 1 前置检查第 ④ 条**实测该标题存在**（B1）；红线 2 自查全部重写为四条机械判据，
  核心换成**行前缀比对**（一次覆盖三件事），并新增禁用词、`if:` 白名单、`set -euo pipefail` 与
  「判定步骤 `run:` 不含 `||`/`;`/尾随 `exit`」（B2）；`agenerp/**` 写进 Non-Goals，
  失败分支改为「记录 → STATE §3 → `deferred` → successor 带 `capture` 对照证据」（B3）；
  新增**判定算术**：落地 sha 首跑绿才算 `success`，首轮红复跑绿一律写「首轮红、复跑绿、不可复现」，
  红的计数只增不减（B4）；引用 `ai-autonomy-policy.md:72` 的转录声明作为在文依据，
  并新增一条人动作 Deferred 承接措辞冲突（B5）；两个「四处」清单统一为 Current Baseline 那张表，
  并明写 `2026-08-21-2220-1` 的 Closure Gates **不改**，Exit Criteria 加一条 `git diff` 为空的验收（B6）；
  新增 `Decision`「PR vs 直推 `main`」并推荐 PR（B7）。
  九条 nit 全部就地采纳（行号、冗余不是耦合、点名两条被翻到活站点的 L1、补 setup 步骤、
  取证带 `-f`、删掉编造的 `mariadb` 风险并换成真正的 delta、两个 Phase 声明主类型、前置 ⑤ 点明不可迁移性）。
  **另有一处因 B2 的修法而必须改的设计**：前驱把「判定器 CI 侧守卫」交办给本 plan，
  若按原设想去扩 `gates-untouched` 的 diff 范围，就会打掉行前缀性质——因此改为
  **追加一个独立的守卫 job**（`verdict-tool-untouched`），两个新 job 都 append 在文件末尾。
- Independent draft review iteration 2: **needs revision**（同一独立评审者，2026-08-22）。
  **B1–B7 逐条复核：B1 / B2 / B3 / B5 / B6 / B7 判定为已解决，B4 部分解决。** 评审并做了几处独立实证：
  ① `diff <(git show …) <(head -n $(… | wc -l) file)` 这个写法**可执行**，且因为 `gates.yml` 以 `\n` 结尾，
  `wc -l` 给出真实行数、`head -n N` 精确——它是**行**前缀不是字节前缀，但偏差方向是安全的那侧；
  ② 「守卫做成第二个 job 而不是扩 `gates-untouched` 的 pathspec」在**可被绕过性**上找不到不对称
  （两者同处一文件、都不自保、都被同一个 trailer 放行），真实代价只是重复漂移，plan 已登记为 Deferred；
  ③ `if:` 白名单**可被人执行**，`run:` 里的 shell `if [ … ]` 不会误命中 `grep 'if:'`。
  新增 2 条 blocking：
  · **NB1**：`verdict-tool-untouched` 是一条**没有任何牙齿证据**的安全守卫——
    它抄自的 `gates-untouched` 有三个提前 `exit 0` 分支（未触及 / 首次推送 / 找到 trailer），
    抄错 `BASE` 推导或让全零 sha 分支恒命中，守卫就**永久绿而毫无作用**，
    与一个真正管用的守卫**长得一模一样**。plan 只防了假阳（「若实测触发了说明清单写错了」），
    没防假阴。而本仓的既有标准恰恰相反：`2220-2` 的关闭审计跑了 4 次变异 + 2 次绕过实验，**靠变异发现了真洞**。
  · **NB2**：B4 把结论锚在 sha 上，B7 又把落地路径改成 PR——PR 分支上 amend / rebase / force-push
    换 head sha 是家常便饭，「落地 sha 上的第一次运行绿」于是**字面为真而实质为假**；
    且 PR 路径会产生多达三次「第一次运行」，plan 没说哪次权威。两个修法各自独立做出、从未对账。
  另有 9 条 nit（`set -euo pipefail` 实测是 **4** 次在 4 个 job 里而非六个、
  行前缀只证明旧**文本**没变而纯追加可**重新声明**已有 job 键（`yaml.safe_load` 后者胜出）、
  本仓 91 个提交 **0 个 merge commit** 故 PR 路径从未真跑过、
  检查 (d) 的「无 `exit`」套到守卫 job 上必然失败（它天生带三个 `exit 0`）、
  Closure Gates 实为 14 框而文中写十二、`:61` 应为 `:59`、Phase 2 的类型声明 67% 未过阈值、
  Work Item 标签「CI 消费半」不含守卫、scope 扩过后应补 one-result-surface 复核）。
- Revision after iteration 2（逐条对应）：
  `Add` 项钉死守卫的三处易错点（`BASE`/`HEAD` 按事件类型推导、全零 sha 分支、trailer 匹配式），
  并新增一条 `Proof` 做**三次变异实验**（无 trailer 改判定器必须红 / revert 必须绿 /
  只动 `expected-red.txt` 必须不触发），明写「拿不到这三条守卫不算交付」（NB1）；
  红计数**改锚到 plan 上**、权威运行定为合并后 `main` 的 `push`、合并前每次一并记录、
  「CI 已验证」要求从未出现过红（NB2）；9 条 nit 全部就地采纳，并顺手修掉一条
  与前驱 plan 同类的裸 `git diff` 判据（`agenerp/**` 一行未改）。
- Independent draft review iteration 3: **needs revision**（同一独立评审者，2026-08-22）。
  确认 **NB1 / NB2 实质关闭**，并逐条验证了三次实验**真的能失败**：
  `gates-untouched` 用的是 `git diff --name-only "$BASE" "$HEAD"`（树比较），
  所以 ① 在空白提交上会红、② revert 后树与 BASE 一致故转绿、③ 因 pathspec 排除账本而保持安静；
  而「`BASE` 推导抄错 / 全零 sha 分支恒命中」这类空转会表现为 ① 返回 `success` 而不是必需的 `failure`——
  **正是这条实验要抓的那个失效模式**。9 条 nit 逐条确认落地。
  新增 1 条 blocking：
  · **NB3**：**NB1 的修法与 NB2 的修法互相矛盾，plan 无法执行**。
    NB1 的 experiment ① **要求**守卫 job 红；而 NB2 写的是「新 job 的**任何一次红**都是永久证据」
    「「CI 已验证」的充要条件是新 job **从未出现过红**」，且 `新 job` 涵盖两个 job。
    于是跑了那条必需实验的执行者**永远写不出「CI 已验证」**，还白烧掉裁判规则 4 两次红里的一次。
    三条出路全是坏的：不跑实验（守卫未交付）、跑了却把结论降级成「不可复现」（证据其实是干净的）、
    临场发明例外——**最后这条正是这套算术要防的行为**。评审指出这是第 2 轮 B4/B7 冲突的同型复发：
    两个修法各自独立写出、从未对账。
  另有 6 条 nit（Phase 1 `Decision` 里「与文件里六个脚本 job 同一约定」是上一轮已改准事实的残留、
  自查项标题与 Exit Criteria 仍写「四条」而列表已有五条、
  三次实验只覆盖 `pull_request` 分支的 BASE/HEAD 推导而 `push` 分支合并前无法实测、
  experiment ③ 必须加 `#` 注释而不能加真 nodeid（否则触发棘轮、污染实验）、
  「字节前缀」应统一改为「行前缀」、`Draft Review Record` 落后一轮）。
- Revision after iteration 3（逐条对应）：
  判定算术首条改为**只针对主判定 job 的「非预期红」**，并把 experiment ① 那次红**显式定性为
  「预期红、必需证据」**，单独成段记录、不入连续红计数、不影响「CI 已验证」；
  「充要条件」与停机线两处同步收窄口径，并补一句「上述一切只约束主判定 job」（NB3）；
  6 条 nit 全部就地采纳（删掉「六个脚本 job」残留并改写为「本 plan 自己立的更严规矩」、
  两处「四条」改「五条」、补上「三次实验只证明了 `pull_request` 路径，`push` 分支合并前无法实测，
  不得读成守卫已全面实证」、experiment ③ 补上「必须加 `#` 注释」及其理由（`count()` 的
  `grep -vE '^\s*(#|$)'` 语义）、全文「字节前缀」统一改为「行前缀」、本记录补齐第 2/3 轮）。
- Independent draft review iteration 4: **acceptable as-is** —— **共识达成**（同一独立评审者，2026-08-22）。
  判定 **NB3 已真正调和**：两个 `Proof` 项现在可以同时满足；豁免口被**三重围栏**框住
  （限定 job 名 `verdict-tool-untouched`、限定 experiment ①、限定必需结论 `failure`），
  且「守卫 job 的任何其它红仍按非预期红计」堵掉了最明显的那条延伸读法，
  豁免口**够不到** `gates-l2-live` 一根手指头——评审逐字：「I could not construct a reading where a real red gets excused.」
  评审另做了一次**矛盾对扫**（这个模式已经咬了两次）：Non-Goals × 实验、
  Phase 1 `Decision` (d) × Phase 2 检查 (d)、守卫的 `set -euo pipefail` 要求 × 它抄的 `gates-untouched` 脚本体、
  清理要求 × 行前缀检查、experiment ③ × `expected-red-ratchet`、停机线 × 实验次数——**未再发现互斥规则**。
  六条 nit 逐条确认落地。评审给出 6 条新 nit，**全部就地采纳**：
  ① 守卫变异实证没有对应的 Exit Criteria / Closure Gate（**已各补一条**）；
  ② 「实验提交已清理」这句话没有机械判据——Phase 3 自查的 pathspec 里没有判定器
  （**已把 `tools/gates/check_expected_red.py` 加进那两条命令**，这正是本 plan 反复批评的
  「没有判据的安全声明」，出现在自己身上）；
  ③ Non-Goals 第 153 行字面禁止 experiment ①（**已补例外条款**，理由写明是 NB3 的教训）；
  ④ experiment ① 缺污染防护而 ③ 有（**已补「空白改动必须落在语义无关处」**，
  否则 `gates-l1` 会跟着红、两个 job 同时红说明不了问题）；
  ⑤ `## One Result Surface 复核` 里「同一次 CI 运行」在第 3/4 轮后已不准
  （**改为「同一条 PR / 同一批 CI 运行」**并写明守卫证据来自 PR、主判定证据来自合并后 `push`）；
  ⑥ `## 14.4` 有五处必写内容而只有三处有 Exit Criteria（**已补齐另外两条**）。
- **共识达成**：四轮独立评审，第四轮 `acceptable as-is`，`Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（roadmap「5 现状」「6 现状」「9 现状」/ `project-context.md` 第 56–58 行 /
      `## 14.4` / `ai-autonomy-policy.md` 相关登记 / `gate-fixtures-pollute-the-live-site.md` / STATE §2）
- [ ] 四处确认漂移已就地改准，**没有被降级成 follow-up**（Minimum Rule 14）
- [ ] **已关闭 plan 的 Closure 段一个字未改**（`2026-08-21-2220-1` 的 `git diff` 为空）
- [ ] verification has run：CI 新 job（run id 逐字）· 默认环境 `check_expected_red.py` ·
      `pytest tests/unit` · `pytest tests/contracts` · `ruff check` · 本地 yaml/compose 静态自检
- [ ] 红线 2 自查五条（行前缀 / job 键集合 / 禁用词 0 命中 / `if:` 白名单 / 无失败吞噬）有实测输出
- [ ] **守卫 job 带着自己的变异实证**：三次实验的 run id 与结论（① `failure` / ② `success` / ③ 未触发）
      逐字在 plan 里，且 `## 14.4` 记着「只证明了 `pull_request` 路径」这条限定。
      **没有这条，守卫只是一条没有证据的安全声明，`## One Result Surface 复核` 的前提也不成立**
- [ ] CI 结论已按钉死的算术归类，**「首轮红、复跑绿」未被写成「CI 已验证」**
- [ ] `agenerp/**` 一行未改 —— **用开工 sha，不用裸 `git diff`**：
      `git diff --stat <开工 sha>..HEAD -- agenerp` **与** `git status --porcelain -- agenerp` 两条都为空
- [ ] scoped verification is not conflated with full verification —— 本仓无全量套件
      （`project-context.md` 第 61–62 行），本 plan 的绿是 scoped，这句必须逐字出现在 `## Closure` 里
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

### `ai-autonomy-policy.md` 的 `.github/workflows/**` 行与红线 2 措辞不一致，需人就地改准

- Classification: `out-of-scope improvement`（out-of-authority：改 Protected Areas 的 Rule 列等于替人定授权口径）
- Why Not Blocking Closure: 该表第 72 行自称是红线表的**转录**（「全部照抄⋯此处不新增、不放宽任何一条」），
  而红线 2 只禁变松。本 plan 是纯新增、零删除、逐条自查不变松，因此不落在禁止面内——
  冲突不影响本 plan 能否执行，只影响**下一个人要不要再论证一遍**。
- Successor Required: `no`（**人动作**：把该行 Rule 列改成与红线 2 一致的措辞，或在 Required Evidence 里
  写明「纯新增不需批准」）
- 重开事件：下一个需要动 `gates.yml` 的 plan 起草时；或人复核受保护面表时。

### 退休被新 job 完全包住的 `gates-l2`

- Classification: `out-of-scope improvement`（out-of-authority）
- Why Not Blocking Closure: 删 job 是删除动作，且本仓对红线 2 的自查已固化成「新文件以旧文件为行前缀」，
  删除会直接打掉它。留着的代价只是 CI 分钟与一处需要文档解释的冗余，不影响任何判定。
- Successor Required: `no`（**人动作**）
- 重开事件：人确认新 job 已连续绿过若干轮、愿意承担「只剩一条 L2 判定路径」时。

### 两个守卫 job 逻辑近似重复（`gates-untouched` 与 `verdict-tool-untouched`）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 合并它们要改 `gates-untouched` 的脚本体，会打掉行前缀自查。
  重复的代价是两处脚本将来可能漂移；缓解是两个 job 的 diff 逻辑完全同构，且都由同一个 trailer 放行。
- Successor Required: `no`（**人动作**，与「退休 `gates-l2`」同一时机做最省）
- 重开事件：人决定重排 `gates.yml` 时。

### runner 上的实现缺口 —— **已触发，2026-08-22 实测坐实，本 plan 因它停机**

**这一条不再是「若」。** Phase 2 的 CI 实跑（run `32509351108`，两次 attempt）把它变成了事实。

- Classification: `out-of-scope improvement` → **升级为 blocking successor**（阻的是本 plan 自己）
- 事实（逐字，两次 attempt 完全相同）：
  `门禁 19 项：红 1，绿 18，跳过 0` /
  `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`
- **可复现**：`gh run rerun --failed` 原样复跑，同一条 nodeid 再红一次。
  **不是抖动，裁判规则 3 的「不可复现」分支不适用。**
- **与本机的差异是本条最有价值的一句**：本机 6 跑红 1 次（前驱 `0027-1`），runner **2 跑红 2 次**。
  起草时写的推理「runner 的全新站点没有历史孤儿列，方向恰好有利」**被实测证伪**。
  **不猜为什么**（裁判规则 3）——查清它要动 `agenerp/**`，落在 Non-Goal 内。
- Why Not Blocking Closure: **它现在就是 blocking**。本 plan 按 Phase 2 末项写死的处置置 `deferred`。
- Successor Required: `yes` —— 一个专门的 plan，**必须带上 Protected Areas 末行要求的
  「实跑前后全量 `capture` 对照」证据**，并在修完后**重新证明本机 live 整目录判定仍绿**
  （防止把实现调到只迁就 runner）。
  successor 手上已有的现成复现路径：**PR #1 的分支 `ci/0027-2-l2-full-live-gate` 上那两个 job 是现成的**，
  改完 `agenerp` 推上去就能在同一条 PR 上复跑，不用重新搭。
- 重开事件：**已发生**（2026-08-22，run `32509351108`）。

### CI 上的 L2 仍只在 `ubuntu-latest` 一种 runner 上验证

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本仓没有多平台承诺，`project-context.md` 也没声称过跨平台。
  runner 与本机的 docker/compose 版本差已在 `2026-08-21-1022-1` 登记，本 plan 不加剧。
- Successor Required: `no`
- 重开事件：本仓第一次对「在别的平台上也能起栈」作出承诺时。

### 门禁每跑一轮留孤儿列（本机常驻站点那半）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 修法在 `tests/gates/conftest.py`（红线 1），只有人能做。
  本 plan 只按实跑结果**重新裁定 CI 那半**（Phase 3 第二项），本机那半照旧由
  `docs/backlog/gate-fixtures-pollute-the-live-site.md` 承接，清理手段见该文档文末的 `trim-tables`。
- Successor Required: `no`
- 重开事件：见该文档届时被本 plan 改绑后的触发条件。

### 并发起栈时的 8080 端口争用

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 明确不新增 `concurrency:`；`gates-l2` 与新 job 在同一次 workflow run 里
  是两个独立 runner（各自一台机器），不共享端口。真正会撞的是同一台机器上跑两份栈，本仓不这么做。
- Successor Required: `no`
- 重开事件：有人给 job 加 matrix 或在同一 runner 上并发起栈时。

## Closure

Status Note: <待关闭审计填写>

Closure Audit Evidence:

- Auditor / Agent: <待填>
- Evidence: <待填>
