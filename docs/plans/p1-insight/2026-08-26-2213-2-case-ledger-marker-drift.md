# 2026-08-26-2213-2 · 立案账本的标记与仓库真值对齐 —— 交接队列四组逐条改准 + `docs/bugs/03` 状态词改准，并立一条「引文存活」判据

> Plan Status: deferred
> Mission: p1-insight
> Work Item: **无合法归属 —— 这正是本 plan 停在 `deferred` 的原因**（起草期自称 P1.9 第 2 个 plan，独立评审第 1 轮 BL-4 推翻，见 `## 归属`）
> Last Reviewed: 2026-08-26
> Source: `docs/masterplan/STATE.md` §3 `[needs-human] 2026-08-26T20:48Z` 第 ⑥ 项（`docs/bugs/03` 标记与内容不一致，
> 逐字「交人：一行状态词，或**由人指派**任一后继 plan 顺手带上」——
> ⚠️ **起草稿在这里只抄了后半句、删掉了「由人指派」这个主语**，独立评审第 1 轮 BL-4 实读证伪，原引法留痕于此）·
> 起草步自查（本轮新查的来源：`docs/backlog/` 的**立案条目文件自身的引文**，前十轮只读过它们的**文件头状态词**，从没有一轮逐条核过正文里的引文）
> Related: `docs/plans/p1-insight/2026-08-26-2101-1-routing-guard-registration-drift.md` ·
> `docs/plans/p1-insight/2026-08-26-2213-1-ci-coverage-registration-drift.md`
> （**同一失败形态的第 1、2 例，本 plan 是第 3 例**：一段登记文字逐字与仓库相反，而没有任何判据拦得住）
> Audit: required

## Current Baseline

### B0 · 本 plan 起草时的实测基线（收尾要原样复跑）

| 命令 | 起草期实测 |
|---|---|
| `git rev-parse HEAD` | `bc7f13fbac0d3474f3fef5bc464041bdb31c147c` |
| `git status --porcelain \| wc -l` | **2** —— `docs/plans/p1-insight/2026-08-26-2213-1-…md` 与本文件，**两者都是起草步自己的产物**，仓内无其他未提交改动 |
| `python3 tools/gates/check_expected_red.py` | exit 0 · `门禁 29 项：预期红 0，绿 29，跳过 0` |
| `python3 -m pytest tests/unit tests/tools -q` | exit 0 · `920 passed, 29 skipped` |
| `python3 -m pytest tests/contracts tests/routing tests/context -q` | exit 0 · `386 passed, 1 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` | exit 0 · `All checks passed!` |

⚠️ **`386` 与 plan `2213-1` 的 B5 记的 `384` 不同值** —— 那份 plan 的基线取自 `1f5cb32`，此后 `2eb1559` 落了
`tests/routing/test_routing_guard_registration.py` 的两条。**本 plan 用自己实跑的数，不照抄。**

### B1 · 处置对象一：`docs/bugs/03-doc-links-dies-on-single-doctypes.md:3` 的状态词已被证伪

该文件 `:3` 今天逐字仍是：

> 状态：**已确认、可复现、未修**（归属不在本 plan 的交付面）

**四条实读反证**（起草期实跑，命令可复跑）：

- `grep -n 'issingle' agenerp/tools/documents.py` → `:55`（docstring）· **`:63`** `doctype_flags` 已把 `issingle` 一并查出 ·
  **`:128`** `if flags.get(holder, {}).get("issingle"):` ⇒ **Single 宿主一律跳过**。原文 §1 描述的第一个失败机制在代码里不成立。
- `git log --oneline -- tests/unit/test_doc_links_skips_singles.py` → **`7c64f9e`**（loop，子表支守卫）+ **`5396e68`**（人，跳 Single）。
- `python3 -m pytest tests/unit/test_doc_links_skips_singles.py -q` → **exit 0 · `8 passed`**。
- `grep -c '5396e68\|7c64f9e\|已修\|fixed' docs/bugs/03-doc-links-dies-on-single-doctypes.md` → **`0`**
  ⇒ **不是「修复注记写在别处」，是全文一个字都没写。**

**本仓的既有形态是有的，不需要现编**：`docs/bugs/01-…:3` 逐字 `> Status: **fixed（2026-08-23）** —— 由 plan …`，
且**原状态行的措辞保留在正文里**（追加式，不覆盖）。`02-…:3` 同形态（`> 状态：**已由人修复**（`484c123`，2026-08-25）`）。
⇒ **`03-…` 是三份里唯一没跟上的那份。**

### B2 · 处置对象二：`docs/backlog/needs-human-expected-red-handoff.md` 的**冲突 1 整组**已被人结清，四处引文全部与仓库相反

该文件 `:5` 今天逐字仍是 `> Status: `open` —— 每一组都**只有人能决**`。**冲突 1** 逐条实读结果：

| # | 文件里的引文（逐字） | 今天的真值（起草期实读） |
|---|---|---|
| 1 | `:19` 引 `missions/prompts/build-verify.md:63-64`「把它从 `tests/gates/EXPECTED_RED.txt` 删掉」 | **`build-verify.md:63` 逐字是 `tools/gates/expected-red.txt`**，且 `:64` 另起一句「该文件**不在** `tests/gates/**` 红线内」 |
| 2 | `:22-24` 引同文件 `:9-11`「名单内**绿** = 名单过期…」 | 该段今天在 `:9-11`，**逐字是 `tools/gates/expected-red.txt`** |
| 3 | `:26-28` 引 `tools/gates/check_expected_red.py:78` 的 print 含 `EXPECTED_RED.txt` | 该 print 今天在 **`:165-166`**，逐字是 `请在同一个提交里把它从 tools/gates/expected-red.txt 划掉：` |
| 4 | `:41` 引 `tests/gates/EXPECTED_RED.txt:12`「本文件在 tests/gates/** 红线内，loop 不得修改」 | **该文件不存在** —— `find . -iname '*expected*red*' -not -path './.git/*'` 的命中里没有它；实际文件是 `tools/gates/expected-red.txt` |
| 5 | `:34-39`「禁止 loop 去改的（三处）」以 `AGENTS.md` 红线 1 为首 | `AGENTS.md:10` 今天带**明写的边界**：逐字「**边界**：预期红名单 `tools/gates/expected-red.txt` 不在此列——它是账本不是裁判」 |

**是谁结清的、什么时候**（不是「还没来得及」）：`tools/gates/expected-red.txt:12-15` 的文件头逐字写着
「⚠️ **2026-08-21 从 tests/gates/ 挪到这里**，原因是循环实测撞出的一个真矛盾：build-verify prompt、判定器输出、
gate-verify 的失败回灌 —— 三处都命令 loop『测试转绿就把它从名单里划掉』，而 AGENTS.md 红线 1 又禁止碰 tests/gates/** 下的
任何文件。循环没有自己找理由绕过，而是停下来写了交接文档等人（做得对）。」
⇒ **那份「交接文档」就是本 plan 处置的这一份，人当天就按它做了处置，而它自己没被改准。**

### B3 · 冲突 2 / 3 / 4 逐条判词 —— **不是整份都过期**，四组各不相同，逐组说清

| 组 | 今天的判词 | 依据（起草期实读） |
|---|---|---|
| **冲突 1** | **已失效（整组）** | B2 五行 |
| **冲突 2** | **成立（结论）· 引文行号已漂移** | `AGENTS.md` 裁判规则 4 今天仍逐字含「同一 plan 连续 3 轮 `GATE_VERIFY` fail」；`tools/mission-driver/flows/plan-execution.json` 的 `maxRetries: 3` / `onMaxRetries` 今天在 `:105` / `:111`。⚠️ 而 `:68` 引的 `check_expected_red.py:61,82-83` 今天落在 `run_pytest()` 上，**不是** `unexpected_green` 判定处（今天在 `:155-156` / `:166`） |
| **冲突 3** | **前提已变（(a) 的必要性消失）** | (a) 的原话是「由**人**补一次带 `Gates-Change-Approved-By:` trailer 的划名单提交」，而 `AGENTS.md:10` 的边界 + `build-verify.md:63-64` 今天逐字要求 **loop 自己**在同一提交里划。⚠️ **(c) / (d) 仍是活的人侧选项，本 plan 不代选** |
| **冲突 4.1** | **已失效（它报的漂移不存在了）** | 它报「`STATE.md` §1 写 P0.1 · 定制包规范化器，而 WBS 的 P0.1 是零依赖启动」。今天 `STATE.md` §1 那一格逐字是 **`P0.2 · 工具契约层 v0`**，而 `02-WBS.md:64` 的 P0.2 逐字是 **`工具契约层 v0`** ⇒ **ID 与名字相符**。⚠️ **它同一段指出的判定缺口仍然成立**：`tools/check-state-consistency.sh:21-26` 今天逐字仍只校验「ID 在 WBS 表里存在」，**不校验 ID 与名字相符** |
| **冲突 4.2** | **成立但已无实际后果** | `02-WBS.md:65-66` 的前置链与 `p0-foundation-roadmap.md:20-22` 的顺序今天**仍然相反**；但 roadmap 三项今天逐字全是 `done` ⇒ 顺序分歧不再影响任何调度 |
| **冲突 4.3** | **完全成立，一个字不用改** | `missions/p0-foundation.json` 的 `_notes.commands` 今天逐字仍是「本机 ruff / mypy / docker 都还没有」，而 `ruff` / `docker` 都在。**`missions/**` 是 Protected Area（`ai-autonomy-policy.md`），loop 不改它，只如实登记** |

### B4 · 这份文件的过期**有可观测的代价**，不是洁癖

`docs/masterplan/STATE.md:1026` 那一轮盘点逐字把本文件读成
「`Status: open`，逐字『每一组都**只有人能决**。loop 不得自行处置』」，并据此把它计入「五份全部归人」。
⇒ **一个只按标记读文档的人（和已经这么读过的每一轮盘点），会得出「这四组都还敞着、都得等人」的结论。
其中至少冲突 1 整组早在 2026-08-21 就被同一个人处置完了。**

同一形态在 `docs/bugs/03` 上也已发生过一次，且被逐字记下来了（`STATE.md` §3 `20:48Z` 第 ⑥ 项：
「**一个只按标记读文档的人，会得出「还有一条 `doc.links` 的活缺陷敞着」的结论。它已经修好了。**」）。

### B5 · 今天没有任何判据拦得住这一形态

- `grep -rn 'needs-human-expected-red-handoff\|docs/bugs' tests/` → **2 命中，但两条都不是判据**（起草期首稿把它记成「零命中」，
  独立评审第 1 轮实跑证伪，按实测改准，原值留痕于此）：`tests/unit/test_seed_model_constants.py:43` 与
  `tests/unit/test_insight_live_harness.py:96` —— **两处都是 docstring 里对 `docs/bugs/01` / `02` 的出处引用**，
  不读那两个文件、不对它们做任何断言。⇒ **「没有任何判据以这两份立案文件为对象」这个结论仍然成立，
  但它的举证不是「grep 零命中」，而是「两条命中逐条读过、都不是断言」。**
- 前两例（`2101-1` / `2213-1`）立的两条判据，纳管面分别是 `model-management.md` 的 routing-guards 表与
  `gates.yml` 的 job/步骤表，**都不覆盖 `docs/backlog/**` 与 `docs/bugs/**` 的引文**。
⇒ **改准之后若无判据，它会以同样的方式再漂一次。** 这正是前两例各自 `D4` 里写的重开事件。

## 归属 —— 起草稿的论证已被独立评审推翻，本节记的是推翻过程

**起草稿主张**：本 plan 记在 P1.9（CP9 · P1 阶段复盘）名下，该格 `1/2`，用掉最后一格即可，不需要人加预算。
**独立评审第 1 轮 BL-3 / BL-4 逐条推翻，起草者复核后接受推翻。逐条记，不修饰：**

- 🔴 **BL-3 · 承重引文是编的。** 起草稿逐字写「`04-RUNBOOK.md` §7.2 把阶段关口定义为**对本阶段留下的账逐项复评**」，
  而 §7.2（`:426-435`）全节只有「走 `03-SKILL-GATE-MAP.md` §A9 模板。**阶段关口必答第 6 项：方法论续用复评**」+
  AGE/LoopX 续用-停用判据表 + 「结论只有『续用』『停用』两种」；`03-SKILL-GATE-MAP.md:82-90` 的 §A9 七项
  （目标对照 / 停机次数 / 门禁误判 / 成本 / 措辞审计 / 方法论续用 / 下一期一件事）**同样没有「账」「逐项复评」任何一词**。
  ⇒ **那句「定义」是起草者自己写的，却被装成引文。**
  **这正是本 plan 要治的病，在本 plan 自己的归属论证里犯了一次 ——** 起草稿全文都在数别人「引文与仓库相反」，
  自己写下了一句仓库里根本不存在的引文。**照实记在最显眼处，不移到脚注。**
- 🔴 **BL-4 · P1.9 不是一个「有空预算的格」，它是一行状态源为 `人` 的工作项。**
  `02-WBS.md:91` 实读：状态源列逐字 **`人`**；交给 loop 的面逐字**只有**「**§7.2.1 的判据抽查整项交 loop**」，
  而那一项已由 `2026-08-26-1835-1-gate-spotcheck-p1-9.md` 交付并独立收口 ⇒ **该委派已用尽**。
  **起草稿全文从未引用过 `02-WBS.md:91` 这一行** —— 论证绕开了唯一能定归属的那行字。
- **另两条同向的实读**：① `STATE.md:1621` 逐字「交人：一行状态词，或**由人指派**任一后继 plan 顺手带上」，
  且该行标 `[needs-human]`（`:1602`）⇒ `docs/bugs/03` 那一半是**明写要人指派的**，不是敞着等人捡；
  ② 被改的 `needs-human-expected-red-handoff.md:5` 逐字「**loop 不得自行处置**」，
  而 Phase 3 要把它的 `Status:` 由 `open` 改成 `partially-open` 并宣告哪一组已闭 —— **那正是「处置」**。
- **与 `2026-08-26-2213-1` 的决定性差别**（不许把两者混为一谈）：那份 plan 的**主交付面就在它记账的那一格里**
  （工作项 4 的落点节 §7.7），越出的只是几条指针；**本 plan 100% 的交付内容都归别的格**。
  ⇒ 表规 3 的「计 plan 数不计文档小节」那条读法**救不了本 plan**，因为本 plan 的问题不是计数，是**权属**。

**结论（起草者自判，不等评审替我说）**：本 plan **没有合法归属**。
按 `DECISIONS.md` D-24 逐字「**loop 仍然不得自行加行。它判『无 plan 可派』并停下来是正确行为**」，
本 plan 停在 `deferred`，**不转 `active`、不执行**。`deferred` 是本仓唯一能让 plan 停下来等人的状态
（`flow-loader.js` 的 `ACTIVE_STATUSES` / `DRAFT_STATUSES` 均不含它），先例 `2026-08-25-0119-1`。

**留着这份文件而不是删掉它，理由只有一条**：B1–B5 里那两处漂移是**实测出来的、今天仍然成立的**，
删掉文件等于把证据一起丢掉。**下面的 Goals / Phases 一律不得当作已批准的作业读** —— 它们是起草稿原状，
其中若干条已被独立评审实测证伪（见 `## Draft Review Record`），**执行前必须先修**。

## Goals

- **G1** `docs/bugs/03-doc-links-dies-on-single-doctypes.md` 的状态词与仓库真值一致，形态与 `01-…` / `02-…` 两份先例相同。
- **G2** `docs/backlog/needs-human-expected-red-handoff.md` 的**四组逐组给出今日判词**，被证伪的从句删掉、
  仍成立的结论一个字不改；文件头 `Status:` 与四组的实际判词一致。
- **G3** 新增**一张引文登记表**（成对 `machine-read` 标记包围）作为该文件引文状态的**单一真相源**，
  并由一条判据判定它与被引文件**双向同构**：引用的文件不存在、引文原文改过、组增删而表没跟上、表被删空 —— 四种都当场红。
- **G4** 变异自查 N1–N10 逐条先写死预测再施加，**全部落在 `/tmp` 的整仓副本上，活仓零变异**。

## Non-Goals

1. **不改 `tools/gates/expected-red.txt` 的任何一行**（名单是账本，但本 plan 没让任何门禁转绿，无行可划）。
2. **不改 `tests/gates/**` 一个字节**（红线 1）。
3. **不改 `.github/workflows/**` 一个字节**（红线 2）；本 plan 不新增门禁，`门禁 29 项` 不变。
4. **不改 `missions/**` 一个字节** —— 但**两份文件的出处不同，不许混为一谈**（独立评审第 1 轮 BL-5 实读改准）：
   · `missions/p0-foundation.json`（冲突 4.3 点名）—— 出处是 `docs/context/ai-autonomy-policy.md:87`
     逐字 `| missions/*.json | blocked | 角色 B 禁区（…§1 禁止项 ③），由人编辑 |` 与 `01-EXECUTION-MODEL.md:14` 禁止项 ③（逐字「改 `missions/*.json`」）。
   · `missions/prompts/build-verify.md` —— **不在**上述两条的字面范围内。
     ⚠️ **这一点正是本 plan 要改准的那份文件自己裁定过的**：`needs-human-expected-red-handoff.md:54-56` 逐字
     「`missions/prompts/build-verify.md` **不是** `missions/*.json`，**不在**…禁止项 ③ 的字面范围内」。
     不改它是**本 plan 自设的围栏**，理由是「改执行器每轮读的行为指令属于改控制面」。
   ⚠️ **三者都不是 `AGENTS.md` 的七条红线**（红线里没有 `missions/**` 任何形态）。
5. **不代人做冲突 2 的 (A)/(B)、冲突 3 的 (c)/(d) 任何一个选择** —— 那四个是人侧选项，本 plan 只把
   「哪些前提已经变了」写实，**不替人选，也不删掉那些选项**。
6. **不改 `docs/masterplan/**` 已有的任何一行**（红线 5）；只往 `STATE.md` §3 追加一条证据行。
7. **不补 `tools/check-state-consistency.sh` 的「ID 与名字相符」校验**（冲突 4.1 指出的真缺口）——
   那是给状态账本加一条新校验，与本 plan 的结果面（**立案账本说真话**）不是同一个面；
   本 plan 只把它从「已过期的漂移报告」改准成「仍然成立的判定缺口」并留在队列里等人。**不是忘了，是划出去的**，见 `D2`。
8. **判据不纳管 `docs/bugs/**` 的引文** —— 只纳管交接队列那一份文件的引文。理由与残余风险见 `D3`，
   并**逐字写进判据文件头**，不默默省掉。

## Task Route

- Type: `verification or audit work`（主）+ `implementation-only change`（判据那一半）
- Owner Docs: `docs/backlog/needs-human-expected-red-handoff.md`（自身即登记面）·
  `docs/bugs/03-doc-links-dies-on-single-doctypes.md` · `docs/masterplan/STATE.md` §3（只追加）
- Skill Selection Basis: `docs/skills/README.md` 实读后**未选任何 skill** —— 本 plan 的两半
  （逐条实读核对 + 写一条纯文本解析判据）都不匹配任何既有 skill 的输入/输出约定；
  收口侧的独立审计口径沿用 `docs/skills/closure-audit-prompt.md`（不采信自报，逐条对活仓取证），**那是审计者的输入，不是本 plan 的执行 skill**。

## Infrastructure And Config Prereqs

No infra prereqs beyond existing baseline —— 本 plan 全程离线：不起 docker 栈、不打任何活站点、
不调任何模型端点、零新增依赖（`pyproject.toml` 不动）。`/tmp` 上的整仓副本用 `cp -r` 建，用完删。

## Execution Plan

### Phase 1 — 把四组的今日真值逐条实测出来，落成唯一一张引文登记表

Status: planned
Targets: `docs/backlog/needs-human-expected-red-handoff.md`（新增登记表段）· `docs/evidence/p1-case-ledger-citations/`
Skill: `none`

- Item Types: `Proof | Decision | Add`
- Prereqs: 无

- [ ] **Proof** · **逐条实测 B2/B3 两张表里的每一格**，命令原文与输出**逐条落进**
      `docs/evidence/p1-case-ledger-citations/README.md`：
      ① `find . -iname '*expected*red*' -not -path './.git/*'` ② `sed -n '9,11p;63,65p' missions/prompts/build-verify.md`
      ③ `grep -n 'expected-red.txt' tools/gates/check_expected_red.py` ④ `sed -n '10p' AGENTS.md`
      ⑤ `sed -n '12,15p' tools/gates/expected-red.txt` ⑥ `grep -n '下一个未阻塞工作项' docs/masterplan/STATE.md` + `grep -n '^| P0\.2 ' docs/masterplan/02-WBS.md`
      ⑦ `sed -n '21,26p' tools/check-state-consistency.sh` ⑧ `grep -n 'maxRetries\|onMaxRetries' tools/mission-driver/flows/plan-execution.json`
      ⑨ `python3 -c "import json;print(json.load(open('missions/p0-foundation.json'))['_notes']['commands'])"`
      ⑩ B1 的四条。**被引段落的原文一并抄进证据文件**（改准之前的原状留痕）。
      - Skill: `none`
- [ ] **Decision** · **纳管口径 = 这一份文件里「点名了另一个文件的路径」的引文，粒度到「组」。**
      备选：(A) 纳管全仓所有 `docs/backlog/*.md` 的引文 —— **否决**：六份立案文件形态各异，
      解析口径要为每份现编一套，判据会变成一堆特例，**判别力不随覆盖面增长**；
      (B) 纳管到「每一条引文一行」—— **否决**：本文件同一组内一条引文常跨 3–5 行块引用，
      「一条」在文本上不可稳定切分，行数会随排版变动而变，**判据会因排版红**。
      **选 (C)：一组一行，组内引文以「路径 + 逐字片段」列出**（可多值，用 ` · ` 分隔）。
      残余风险：组内新增一条引文而不进表，判据看不见 —— 由 `D3` 登记并逐字写进判据文件头。
      - Skill: `none`
- [ ] **Add** · 在该文件**文末新增一节** `## 引文登记表（machine-read）`，正文由成对标记包围：
      `<!-- machine-read: handoff-citations -->` … `<!-- /machine-read: handoff-citations -->`。
      表头七列，逐字：`组 | 引文指向的文件 | 引文逐字片段 | 今日判词 | 失效依据 | 实测日期 | 证据路径`。
      「今日判词」列**取值只有两个**：`成立` / `已失效`（自由文本一律当红，见断言⑤）。
      - Skill: `none`
- [ ] **Add** · 表下逐字写清**这张表不管什么**：不管引文所指内容的**语义**是否正确（只管路径在不在、片段还在不在）·
      不管四组各自的**处置选项**该选哪个（那是人的）· 不管 `docs/bugs/**` 的引文（Non-Goals 8 / `D3`）·
      不管「实测日期是否新鲜」（只管可解析 + 证据路径存在，同 `2101-1` 第 ⑤ 条口径）。
      - Skill: `none`
- [ ] **Add** · 表内逐字声明它是**这件事的单一真相源**，并点名今天在别处重复登记同一事实的位置
      （`STATE.md:1026` 的那一轮盘点行 —— **只点名、不重述、不改写**，红线 5）。
      ⚠️ **正文四组的改准（Phase 3）一律写成指向本表的指针，不重述表里的事实** ——
      这是 `2213-1` 第 1 轮评审 BL-4 的教训（同一事实写进三处即自我推翻「单一真相源」）。
      - Skill: `none`

Exit Criteria:

- [ ] 登记表存在，成对标记齐全，**数据行数 == 该文件 `^## 冲突 ` 标题实测条数**，逐行与 Phase 1 ① 的实测一致
- [ ] `git diff --numstat bc7f13f -- docs/backlog/needs-human-expected-red-handoff.md` 的**删除列为 0**（本 Phase 只新增；删从句在 Phase 3）
- [ ] `docs/evidence/p1-case-ledger-citations/README.md` 落盘，十组实测命令原文 + 输出 + 被引段落原状俱全
- [ ] No owner-doc update required（被改的文件自身即登记面；架构面无新增契约）
- [ ] `docs/logs/2026/08-26.md` 更新

### Phase 2 — 判据：登记表与被引文件双向同构

Status: planned
Targets: `tests/unit/test_handoff_citation_registration.py`（新增）
Skill: `none`

- Item Types: `Decision | Add | Proof`
- Prereqs: Phase 1（表要先存在）

- [ ] **Decision** · **判据落 `tests/unit/`。** 备选：(A) `tests/gates/` —— **否决，红线 1**；
      (B) `tests/contracts/` —— **否决**：那是工具契约的面，本条与契约无关；
      **选 (C) `tests/unit/`** —— 它同时在 `missions/p1-insight.json:16` 的 `commands.test` 与
      `gates.yml` 的 `unit-and-contracts` / `lint` 两个 job 里（`2213-1` Phase 1 已实测该事实）
      ⇒ `GATE_VERIFY` 与 CI **两侧都复跑得到**。
      **已知代价**（不粉饰）：人正当改动被引文件时本条会红并拖红 `GATE_VERIFY`。缓解见下一条，残余登记为 `D4`。
      - Skill: `none`
- [ ] **Add** · **失败文案硬要求**：任何一条断言失败都必须逐字打印 **① 是哪一组 ② 是表的哪一列 ③ 该改哪个文件**。
      「改准这张表」与「改准被引文件」是两种不同的处置，文案不许让人猜。
      - Skill: `none`
- [ ] **Add** · **八条断言，逐条对应一种漂移**：
      **①** 成对标记存在且**成对**（只有起标记 / 只有止标记 / 顺序颠倒 → 红）
      **②** 表的**数据行数 ≥ 1**（**存活守卫** —— 挡「整表删空 ⇒ A = B = ∅ ⇒ 恒绿」，这是 `2101-1` 评审在原型上实测出来的坑）
      **③** 表的「组」列取值集合 **==** 文件里 `^## 冲突 \d+` 解析出的组集合（**双向**：删组不删行 → 红；加组不加行 → 红）
      **④** 每行「引文指向的文件」列里的**每一个**路径都必须 `Path(...).exists()`（多值逐个查，不许只查第一个 —— 这是 `2101-1` 评审 SF「读全部参数」那条的同一形态）
      **⑤** 「今日判词」列取值 ∈ {`成立`, `已失效`}，否则红
      **⑥** 判词为 `成立` 的行：「引文逐字片段」列的**每一个**片段必须仍能在对应文件里**逐字** `in` 到
      **⑦** 判词为 `已失效` 的行：「失效依据」列非空，且其中出现的**每一个**仓内路径都必须存在
      **⑧** 「实测日期」可被 `datetime.date.fromisoformat` 解析，且「证据路径」列指向的路径存在
      **每条断言各自对空表短路**（先判②再判其余；否则表被删空时会一次冒出七条红，掩盖真正的那条 —— 同 `2213-1` 评审 SF-1 的教训）
      - Skill: `none`
- [ ] **Add** · **解析器写死为纯文本行扫描**（不 import `yaml`、不 import `markdown`，零新增依赖）：
      取两标记之间的行、丢掉表头与分隔行、按 `|` 切列、`strip()` 每格；
      多值列按 ` · ` 切分。**表列数不足七列的行当红**（挡「少写一列让后面的列错位」）。
      - Skill: `none`
- [ ] **Add** · **判据文件头逐字写清四件事**：① 本条只验**存在性同构**、不验语义（沿用 `2101-1` 措辞）·
      ② **它不纳管 `docs/bugs/**`**，为什么不纳管（`D3`）· ③ 它**不需要**先例那种 `_REGISTERED_FILES` 纳管常量，
      为什么不需要（`2101-1` 的 `B` 由表自己导出才需要钉死；本条的 `B` 三路来源分别是**被引文件的内容**、
      **文件自己的 `## 冲突` 标题**、**文件系统**，无一由表导出 ⇒ 表清空会被②当场打红，不会 `A = B = ∅`）·
      ④ 它钉不住「实测日期是否新鲜」。
      - Skill: `none`
- [ ] **Proof** · `python3 -m pytest tests/unit/test_handoff_citation_registration.py -q` → exit 0，
      并逐条记录八条断言各自的名字与它挡的那种漂移。
      - Skill: `none`

Exit Criteria:

- [ ] 八条断言全部落地且默认全绿
- [ ] `python3 tools/gates/check_expected_red.py` → exit 0，**`门禁 29 项` 不变**（本 plan 不新增门禁）
- [ ] `python3 -m pytest tests/unit tests/tools -q` → exit 0，`passed` **只增不减**（基线 `920`）
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0
- [ ] `git diff -- pyproject.toml` → **0 行**（零新增依赖）
- [ ] No owner-doc update required（判据说明已随 Phase 1 落在表下与判据文件头）
- [ ] `docs/logs/2026/08-26.md` 更新

### Phase 3 — 变异自查（活仓零变异）+ 两份立案文件就地改准 + 收口落盘

Status: planned
Targets: `docs/backlog/needs-human-expected-red-handoff.md` · `docs/bugs/03-doc-links-dies-on-single-doctypes.md` ·
`docs/masterplan/STATE.md`（§3 **只追加**）· `docs/logs/2026/08-26.md` · `docs/evidence/p1-case-ledger-citations/`
Skill: `none`

- Item Types: `Proof | Fix | Decision`
- Prereqs: Phase 1、Phase 2 **均已提交**（先提交再变异，避免变异期的工作树污染 `git diff` 自证）

- [ ] **Proof** · 🔴 **硬约束：N1–N10 十条全部在 `/tmp` 的整仓副本上施加**（`cp -r` 到 `/tmp`），
      **活仓一个字节都不许被变异触及**。每条：施加 → 复跑 → 记退出码与红在哪条断言 → 复原 → `sha256` 比对 `RESTORED OK`。
      - Skill: `none`
- [ ] **Proof** · **变异表，逐条先写死预测再施加**：

      | # | 变异 | 预测 |
      |---|---|---|
      | N1 | 删登记表里的一行数据行 | **红 · ③**（组集合少一个） |
      | N2 | 把登记表整体删空（只留成对标记） | **红 · ②**（存活守卫；⚠️ 只红这一条，其余七条短路） |
      | N3 | 删掉止标记 `<!-- /machine-read: handoff-citations -->` | **红 · ①** |
      | N4 | 文件里新增一节 `## 冲突 5 · <任意>` 而表不动 | **红 · ③** |
      | N5 | 把某行「引文指向的文件」改成 `tests/gates/EXPECTED_RED.txt`（判词仍 `成立`） | **红 · ④**（该路径今天不存在 —— 这正是本 plan 要治的那个病的原样重演） |
      | N6 | 把某判词 `成立` 行的「引文逐字片段」改一个字符 | **红 · ⑥** |
      | N7 | 把某行判词由 `成立` 改成 `大概还成立` | **红 · ⑤** |
      | N8 | 把某行判词由 `成立` 改成 `已失效`，「失效依据」留空 | **红 · ⑦** |
      | N9 | 把「证据路径」列改成一个不存在的目录 | **红 · ⑧** |
      | N10 | **must-stay-green**：把表的数据行**顺序整体打乱**（内容一字不改） | **绿**（证明③是集合比较不是列表比较、其余各条不依赖行序） |

      ⚠️ **N10 是唯一一条 must-stay-green，它承担的举证责任是「基线不是靠恒红蒙的」** —— 没有它，
      N1–N9 全红也可能只是因为判据永远红。**它若红了，说明判据把排版当成了事实。**
      ⚠️ **N5 的红因必须是断言④（路径不存在），不是断言⑥** —— 若实测红在⑥，说明④漏判，**当场改准判据并复跑，不许改预测**。
      - Skill: `none`
- [ ] **Fix** · `docs/bugs/03-doc-links-dies-on-single-doctypes.md:3` **就地改准**：状态词改成
      `> 状态：**已修复（2026-08-26 复核）**` + 点名两个修复 commit（`5396e68` 人 / `7c64f9e` loop）+ 判据路径
      + 一句逐字「**修法横跨人侧与 loop 各一个提交，两侧都没回头改这份记录**」。
      **形态照抄 `01-…:3` 与 `02-…:3`**（不现编），**原状态行的措辞保留在正文里**（追加式，不覆盖）。
      ⚠️ **本条只声称「代码 + 离线判据这一层已修好」** —— 起草期未起 compose 栈复跑该文件 `## Reproduction` 那段，
      **「活站点上今天也不再复现」本 plan 不声称**，并把这句限制逐字写进那份记录里。
      - Skill: `none`
- [ ] **Fix** · `needs-human-expected-red-handoff.md` **冲突 1 整组就地改准**：
      **只删被证伪的从句、只改被证伪的路径，四方结构与「谁说的 + 原文出处」的写法一个字不动**：
      ① 标题里的 `tests/gates/EXPECTED_RED.txt` 改成 `tools/gates/expected-red.txt`
      ② `:19` / `:22-24` / `:26-28` 三处引文换成今天的逐字原文与今天的行号
      ③ `:41` 那一整条（引一个**不存在的文件**）删掉，代之以 `AGENTS.md:10` 边界的逐字原文
      ④ `### 当前处置与仍待人决的部分` 追加一段：**这一组已于 2026-08-21 由人处置完毕**，
      指名 `tools/gates/expected-red.txt:12-15` 的文件头自述，**并指向登记表**（不重述表里的事实）。
      - Skill: `none`
- [ ] **Fix** · **冲突 2 / 3 / 4 逐从句处置，逐条列明，不含糊**：
      · 冲突 2 `:68` 的 `check_expected_red.py:61,82-83` → 改成今天的 `:155-156` / `:166`；**结论与 (A)/(B) 两个选项一个字不动**
      · 冲突 3 (a) 追加一句：**它的前提已由 `AGENTS.md:10` 的边界改变**（loop 今天有权划名单）；**(b)/(c)/(d) 一个字不动**
      · 冲突 4.1 → 把「ID 错」那半**删掉**（今天 `STATE.md` §1 与 `02-WBS.md:64` 相符），
        **保留并加粗它指出的判定缺口**（`check-state-consistency.sh:21-26` 不校验名字），
        ⚠️ **补一句「本 plan 不补这条校验」并指向 `D2`**
      · 冲突 4.2 → 追加一句「三项今天全 `done` ⇒ 顺序分歧不再影响调度」；**原文一个字不删**
      · 冲突 4.3 → **一个字不改**（今天完全成立）
      · 文件头 `:5` 的 `Status:` → 由 `open` 改成 `partially-open`，并逐字写明**哪一组已闭、哪几组还敞着**（指向登记表）
      - Skill: `none`
- [ ] **Decision** · **不删任何一个人侧选项**（冲突 2 的 (A)/(B)、冲突 3 的 (b)/(c)/(d)）。
      备选：把已被前提变化架空的选项删掉 —— **否决**：判断「前提变了所以这个选项不必要了」是**替人做决定**，
      而这四组的处置权逐字归人。**选：只加「前提已变」的事实注记，选项原样留着。**
      残余风险：人读到的选项列表里会有已经过时的项 —— 由注记本身缓解，且注记就在选项旁边。
      - Skill: `none`
- [ ] **Proof** · **同形态补扫一遍**：`grep -rn 'EXPECTED_RED\|tests/gates/EXPECTED' docs/ --include='*.md' | grep -v '^docs/plans/\|^docs/logs/'`
      → 逐条读原文判定，**命中且仍指向不存在路径的一律当场改准或点名交人**；结果落进证据文件。
      ⚠️ **这是关键词扫描 + 逐条读原文，不是全文逐行复核** —— 边界逐字写进证据文件，见 `D5`。
      - Skill: `none`
- [ ] **Proof** · `STATE.md` §3 追加**一条** `[open]` 证据行：命令原文 + 退出码 + commit sha + 红线自证 +
      归属取舍（含 `D1` 的推翻方式）+ **本 plan 未声称的两件事**（活站点复现 · 全文逐行复核）。
      **只追加，不改写本节任何已有行。**
      - Skill: `none`

Exit Criteria:

- [ ] N1–N10 **十条全部与预测吻合**（含 N10 保持绿），逐条落进证据文件；十次复原后 `sha256` 均 `RESTORED OK`
- [ ] `git diff --name-only bc7f13f -- .github/ missions/ tests/gates/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md tools/` → **无输出**
- [ ] `docs/bugs/03-…` 状态词改准，且**原状态行措辞在正文里留痕**（`git diff` 逐 hunk 复核）
- [ ] `needs-human-expected-red-handoff.md` 的改动**只有：删被证伪的从句 + 改被证伪的行号/路径 + 加注记 + 加表**；
      `git diff` 逐 hunk 复核，**四组的结论与全部人侧选项零删除**
- [ ] 正文四组的改准**不含任何被重述的表内事实**（逐 hunk 复核，只许有指针）
- [ ] B0 六条命令**收尾原样复跑**，退出码与输出记进 `STATE.md` 追加行
- [ ] `STATE.md` §3 的 `[open]` 行已落地；`git diff --numstat bc7f13f -- docs/masterplan/STATE.md` **删除列为 0**
- [ ] `docs/logs/2026/08-26.md` 更新

## Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，全新会话，2026-08-26，task `a5d396c`）——
  **在 `/tmp` 整仓副本上把登记表与八条断言做成原型并实跑全部变异**（活仓零字节改动），
  开出 **9 条 blocking + 11 条 should-fix**。**九条全部成立，起草者逐条复核后接受。**
  🔴 **其中两条是「本 plan 自己犯了它要治的病」，逐条留在最显眼处，不移到脚注**：
  - **BL-3 编引文**（见 `## 归属`）· **BL-4 归属不合法**（见 `## 归属`）⇒ **本 plan 因此停在 `deferred`。**
  **其余七条是技术缺陷，已逐条记下，执行前必须先修（现在**不**修，因为本 plan 不该被执行）**：
  - **BL-1 B5 的「零命中」为假** —— 实为 2 命中（`test_seed_model_constants.py:43` / `test_insight_live_harness.py:96`，
    两处均为 docstring 提及、非断言）。**已改准，原值留痕。**
  - **BL-2 `expected-red.txt` 文件头行号错** —— 所引四行实为 `:12-15`，非 `:13-18`。**已改准（三处）。**
  - **BL-5 `missions/prompts/build-verify.md` 的禁令出处认错** —— 它**不在** `missions/*.json` 的字面范围内，
    且这一点正是被改准的那份文件 `:54-56` 自己裁定过的。**已改准。**
  - 🔴 **BL-6 断言⑦ 对本 plan 的旗舰行不可满足** —— 原型 baseline 实测 `1 failed, 7 passed`，
    红的是 `test_07_dead_rows_have_reason`：冲突 1 判 `已失效` 的**依据就是** `tests/gates/EXPECTED_RED.txt` 不存在，
    而⑦要求失效依据里的路径必须存在 ⇒ **二者互斥**。评审为让 baseline 转绿，**不得不把那个死路径从依据里删掉** ——
    即「⑦ 逼执行者回避写出死路径，而写出死路径正是『已失效』这个判词的全部依据」。**未修。**
  - 🔴 **BL-7 N3 / N5 的预测经实测不成立** —— 各 2 条红（N3 `['01','02']`：删止标记 ⇒ 数据行 = 0 ⇒ ② 一并炸；
    N5 `['04','06']`：④ 并未漏判，是⑥ 也去那个不存在的文件里找片段）。
    ⚠️ **起草稿 `:293` 那句「若实测红在⑥，说明④漏判」诊断方向是错的。** 补两处短路后十条逐条吻合
    （`N1['03'] N2['02'] N3['01'] N4['03'] N5['04'] N6['06'] N7['05'] N8['07'] N9['08'] N10 exit 0`，`RESTORED OK`），
    且评审另测：③ 改成保序列表比较后 **N10 转红 `['03']`** ⇒ **N10 是活控制，不是摆设**。**未修。**
  - 🔴 **BL-9 多值分隔符 ` · ` 与语料冲突，已实测出静默绿** —— 本仓真实语料大量含 ` · `
    （最直接的例子就是本 plan 自己要登记的 `STATE.md:17` 逐字 `**P0.2 · 工具契约层 v0**`）。
    实测：登记该片段 → `8 passed`；**把 `STATE.md` 的 `P0.2` 改成 `P0.9`（引文真的失效了）→ 仍 `8 passed`** ——
    碎片 `工具契约层 v0` 照样匹配得上。**一条在自己引文被证伪时保持绿的判据，正是本 plan 要治的那种「绿着坏掉」。**
    另：多值「文件」列与多值「片段」列之间的**配对规则全文未定义**。**未修。**
  - **BL-8 冲突 2 / 3 的引文行号与一处事实已漂** —— `check_expected_red.py:60` → `:155`、`:72-75` → `:160`；
    `:81-82` 的 `maxTotalSteps: 120` 与「160 万 token」今天分别是 `60` 与 note 自述的「1,500 万」。**未修。**
  - **SF 1–11 全部成立**（含：B1 漏掉 `docs/bugs/03` 的**第二个**失败机制 `documents.py:171`；
    `check_expected_red.py:61` 不在 `run_pytest()` 里；红线 5 的自证只盖了两个文件、应改成整目录减 `STATE.md`；
    `tools/**` 的三分归属；规则 4「一个结果面」可疑；`D3` 的重开事件含「无人发现」不可观测；
    Phase 1 Exit 的「行数 == `^## 冲突 ` 条数」实测为 4 而 B3 给了 6 条判词，且「今日判词」一列被塞了两种语义）。**未修。**
- ⚠️ **不再起第 2 轮评审** —— 评审收敛的目的是把 plan 修成可执行契约，而本 plan 已判**不该被执行**（`## 归属`）。
  继续评审技术细节是把力气花在一份没有归属的作业上。

## Closure Gates

- [ ] in-scope behavior is complete（`docs/bugs/03` 状态词 + 交接队列四组逐组判词 + 登记表 + 八条断言 + N1–N10）
- [ ] relevant docs are aligned（`docs/bugs/03-…` · `needs-human-expected-red-handoff.md` · `STATE.md` §3 追加行 · `docs/logs/2026/08-26.md`）
- [ ] verification has run：`python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit tests/tools -q` · `python3 -m pytest tests/contracts tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui`
- [ ] scoped verification is not conflated with full verification —— 未跑整仓 `pytest tests -q -m "not live"`
      （**已知基线即红**，见 `docs/backlog/gates-and-tools-leak-env-across-directories.md`）、未起 docker 栈、
      未跑任何 `-m live`、**未经 CI 服务端复跑** ⇒ 收口逐字写 `verification scope limited`
- [ ] no in-scope item downgraded to deferred/follow-up（Non-Goals 7 的 `check-state-consistency.sh` 校验是
      **起草期就划出去的范围**，不是执行期降级；`D2` 记它的重开事件）
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **红线自证（`AGENTS.md` 的七条，逐条）**：`git diff --name-only bc7f13f -- tests/gates/ .github/workflows/
      docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → 无输出（红线 1/2/3/5，项目名/包名未改 = 红线 4）；
      `git diff --numstat bc7f13f -- docs/masterplan/STATE.md` 删除列为 0（红线 5 的追加口径）；
      全程未读写 `${XM_PATH}`（红线 6）；未生成运行时 Server Script（红线 7）
- [ ] **本 plan 自设的围栏（不是红线，分开列，不许与上一条混为一谈）**：
      `git diff --name-only bc7f13f -- missions/ agenerp/ tools/ tests/routing/ tests/context/ tests/tools/
      tests/contracts/ docker-compose.yml industry-packs/ pyproject.toml tools/gates/expected-red.txt` → 无输出。
      ⚠️ **`missions/**` 与 `tools/**` 列在这里而不是上一条**：`AGENTS.md` 的七条红线里没有它们，
      `missions/**` 的禁令出处是 `docs/context/ai-autonomy-policy.md` 的 Protected Areas（标 `blocked`）与
      `01-EXECUTION-MODEL.md` §1 禁止项 ③；`tools/**` 是本 plan 自设的（Non-Goals 7）—— **三者不许混为一谈**

## Deferred But Adjudicated

### D1 · 「本 plan 该不该记在 P1.9 名下」这条读法本身

- Classification: `watch-only residual`
- Why Not Blocking Closure: **不是漂移、不是缺陷，是一条归属读法的取舍**。`## 归属` 节逐字写死了规则原文
  （表规 3 计 plan 数）、仓内先例（`STATE.md:840`）与反对读法。**它可被人一次 `git revert` 推翻**
  —— 本 plan 的产物按文件分得开（两份立案文件 + 一个判据文件 + 一个证据目录），revert 后其余交付物不受影响。
- Successor Required: `no`（若人不认同，人 revert 即可；无需后继 plan）
- 重开事件：**人明确裁定「改别的工作项名下的立案文件要占那一格预算」**，或**人在 `02-WBS.md` 就此加一条表规**。

### D2 · `tools/check-state-consistency.sh` 不校验「ID 与名字相符」

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它是**给状态账本加一条新校验**，结果面是「状态账本的自检更严」，
  与本 plan 的结果面（**立案账本说真话**）不共享收口判据（指南规则 4）。
  且本 plan 已把它从「一条已过期的漂移报告的附注」改准成「**仍然成立的判定缺口**」并留在队列里
  ⇒ 它比今天**更**显眼，不是被埋掉。
- Successor Required: `yes`（人指派；`tools/**` 今天既不在 `ruff` 作用域也不在任何 CI job 里，见
  `docs/backlog/tools-dir-has-no-static-check-coverage.md`，该条 `Status: deferred`、处置者是人）
- 重开事件：**再出现一次「STATE §1 的 ID 与名字对不上而无人发现」的实例**，或人把 `tools/**` 接进任一 job。

### D3 · 判据不纳管 `docs/bugs/**`，也不纳管「组内新增一条引文而不进表」

- Classification: `watch-only residual`
- Why Not Blocking Closure: 两处都是**先写死的纳管边界，不是遗漏**：前者因 `docs/bugs/**` 三份形态各异
  （`Status:` / `状态：` 两种写法并存，实读确认），为它现编解析口径会让判据变成一堆特例；
  后者是 Phase 1 `Decision` 选 (C) 的已知代价。**两条都逐字写进判据文件头与表下的「这张表不管什么」**，
  不默默省掉 —— 同 `2101-1` 第 ⑤ 条与 `2213-1` `D3` 的措辞。
- Successor Required: `no`
- 重开事件：**出现一次「`docs/bugs/**` 的状态词又漂了一次而无人发现」**，或
  **出现一次「组内新增引文指向不存在的文件而八条断言全绿」的实例**。

### D4 · 本条判据可能因人正当改动被引文件而红在 `GATE_VERIFY` 上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 Phase 2 `Decision` 选 (C)（判据落 `tests/unit/`）的**已知代价**，不是遗漏；
  缓解（失败文案逐字指出是哪一组、哪一列、该改哪个文件）已是执行项。
  **不接受「把判据挪出 `commands.test` 的作用域以免拖红」这种缓解** —— 那是用降低判别力换绿。
- Successor Required: `no`
- 重开事件：**本仓实际发生一次「人改被引文件 → 本条红 → 循环停机」**（有轨迹为证），届时由人裁定是否换落点。

### D5 · `docs/` 其余各处的同形态引文未逐行复核

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: Phase 3 已加一条关键词补扫（`EXPECTED_RED` / `tests/gates/EXPECTED`），
  但那仍是**关键词扫描 + 逐条读原文**，不是全文逐行复核。**边界逐字写进证据文件。**
- Successor Required: `no`
- 重开事件：**再发现一处指向不存在路径的引文**，届时并进登记表或另起 plan。

## Closure

Status Note: **`deferred` —— 不是「做完了」，也不是「做不动」，是「本 plan 没有合法归属，loop 不该动它」。**
按 D-24 逐字「loop 仍然不得自行加行。它判『无 plan 可派』并停下来是正确行为」。

**留给人的三件事，逐条可判、不含糊**：

1. 🔴 **`docs/backlog/needs-human-expected-red-handoff.md` 的冲突 1 整组早已被人自己结清，文件仍标 `Status: open`。**
   实测四条：`tests/gates/EXPECTED_RED.txt` **不存在**（`find . -iname '*expected*red*' -not -path './.git/*'`）·
   `missions/prompts/build-verify.md:63` 逐字已是 `tools/gates/expected-red.txt` ·
   `tools/gates/check_expected_red.py:165-166` 同 · `AGENTS.md:10` 已带明写边界。
   结清动作是 `4bbe3f5`（`lize`，2026-08-21）。**代价是实测过的**：`STATE.md:1026` 那一轮盘点就是按 `Status: open`
   把它计入「五份全部归人」的。
2. 🔴 **`docs/bugs/03-doc-links-dies-on-single-doctypes.md:3` 仍写「已确认、可复现、未修」，而两个失败机制都已修好并有绿判据守着。**
   `pytest tests/unit/test_doc_links_skips_singles.py -q` → exit 0 · `8 passed`；修法横跨 `5396e68`（人）与 `7c64f9e`（loop）；
   `grep -c '5396e68\|7c64f9e\|已修\|fixed'` → `0`。**这一条 `STATE.md:1621` 已逐字写明「由人指派」。**
3. **若人决定派人做，本文件的 Goals / Phases 不可直接执行** —— BL-6 / BL-7 / BL-9 三条设计缺陷经 `/tmp` 实测坐实且**尚未修**
   （断言⑦ 自相矛盾 · N3/N5 短路口径错 · 分隔符 ` · ` 与语料冲突导致静默绿）。**先修这三条，再谈执行。**

Closure Audit Evidence:

- Auditor / Agent: **不适用** —— 本 plan 未执行、未交付任何产物，`git status --porcelain -- docs/bugs/ docs/backlog/ tests/` 应为空。
  独立**起草**评审 1 轮已做并记在 `## Draft Review Record`（task `a5d396c`）。

Follow-up:

- <非阻塞项；确认的缺陷不得出现在这里>
