# 2026-08-26-2101-1 F8 的登记面与它的处置对不上 —— §12.5 仍写「没有任何判据拦得住」，而判据 2026-08-25 就已落地

> Plan Status: active
> Mission: p1-insight
> Work Item: 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，本 plan 用掉最后一格）
> Last Reviewed: 2026-08-26
> Source: 起草步 2026-08-26T20:55Z 实测 —— `2026-08-24-1457-1-model-routing-v0.md` 独立收口审计的 **F8** 把「`ChatAdapter` 可直接构造、绕过全部能力校验」逐字登记进 `docs/architecture/model-management.md` §12.5 与 `STATE.md` §3；人 2026-08-25T09:33Z 裁定「加静态判据，不收窄导出面」，判据已由人 `d18c05c` 落地并至今绿着 —— **而 §12.5 的那段登记文字一个字没改，今天仍逐字写着「没有任何判据拦得住这条路」。**
> ⚠️ **不是本轮第一次被看见**：`docs/masterplan/STATE.md:1543`（同日更早一轮起草）已实读出「F8 的活已经干完，`[open]` 行是过期描述」——
> 那一轮**只判它「不可派」并停下**（判据落点在 `tests/gates/**`，红线 1）。本 plan 派得出来是因为**结果面不同**：不是去补判据，是去修**登记面**（owner doc），那一面不在任何红线内。
> Related: `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`（F8 的出处）· `docs/plans/p1-insight/2026-08-26-1728-1-routing-honors-configured-model.md`（同一 owner doc 的上一次改准）· `docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2（「绿着的判据未必测它名字说的那件事」）
> Audit: required

## Current Baseline

**全部由本 plan 起草期实跑取证，命令与退出码逐条附在 Phase 1 之前的表里，不引任何转述。**

- **漂移的那段文字**：`docs/architecture/model-management.md:293-297`（§12.5「落地形态」小节末），逐字：
  - `:295` 「本该按 `lineage` 分档的调用，而今天**没有任何判据拦得住这条路**。」
  - `:297` 「真正的闸要等 P1.4 解释 Agent 落地、有了唯一的调用入口才谈得上。」
- **判据早已存在且绿着**：`tests/gates/test_agent_seam_stays_swappable.py:87` 的
  `test_chat_adapter_is_only_constructed_inside_routing`，失败文案逐字引「独立收口审计 F8」。
  `git log --format='%h %ad %an' --date=short -- tests/gates/test_agent_seam_stays_swappable.py`
  → **`d18c05c` 2026-08-25 `lize`**（人落，带门禁审批）。
  `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` → **exit 0 · `2 passed`**。
- **不是「注记写在别处」**：`grep -rn 'test_agent_seam_stays_swappable\|only_constructed_inside_routing' docs/architecture/`
  → **零命中**。整个 `docs/architecture/` 没有任何一处提到这条判据。
- **不是「文档还没来得及动」**：`git log --date=short --format='%h %ad' -1 -- docs/architecture/model-management.md`
  → **`38969b1` 2026-08-26** —— 该文件在判据落地**之后**又被动过一次，那段话仍未被改准。
- **第二句的预期本身没兑现，也没人回头说明**：P1.4（工作项 6）已 `done`（2026-08-24），
  而「唯一的调用入口」**没有出现** —— `grep -rn 'route(' --include='*.py' agenerp/` 实点产品调用点**两处**：
  `agenerp/explain/loop.py:664` 与 `agenerp/judging/judge.py:73`。
- **判据的扫描域与匹配形状（读源码得到的形状，牙口留给 Phase 1 实测）**：
  `_PKG = <repo>/agenerp`（只扫 `agenerp/**`）· 匹配条件是 `ast.Call` 且 `node.func` 为 `ast.Name` 且 `id == "ChatAdapter"`
  ⇒ **属性式构造（`r.ChatAdapter(...)`）与别名导入（`as _CA`）在形状上落在匹配条件之外**，
  `agenerp/` 之外的调用方落在扫描域之外。**这三条是假设，不是结论**，Phase 1 用变异实测逐条判定。
- **第四条不是假设，是已实测**：判据 `:100` **没有 `:74` 那样的存活守卫** ⇒ `ChatAdapter` 这个名字一旦消失，`offenders` 恒空、判据永久静默绿。
  第 2 轮独立评审已在 `/tmp` 隔离副本上实测（门禁 `2 passed` 绿 / `pytest tests/routing -q` `2 errors` 红），**执行期仍须在活仓复现一次**（M6）。
- **预算**：`docs/plans/p1-insight/*.md` 起草时实点 **25 份**（**本 plan 落盘后为 26 份**，独立评审复点确认），按 `> Work Item:` 首行归组，
  工作项 3 名下**只有 1 份**（`2026-08-24-1457-1-model-routing-v0.md`）⇒ 该格 **1/2**，本 plan 是最后一格。
- **CI 面无需改动**：`.github/workflows/gates.yml:617-618` 已有步骤 ④ `python3 -m pytest tests/routing -q`，
  `:631` 的 `COVERED` 已含 `routing` ⇒ **新判据落在 `tests/routing/` 即自动进 CI，一行 workflow 都不用改**（红线 2 不触碰）。
- **域外逃逸今天就有一个真实实例（不必为它造临时文件）**：`tools/experiments/p1_insight_live/run.py:159`
  逐字 `self._poster = None if inner is not None else ChatAdapter(config)`，该文件 `:151` 逐字写明「打真端点」
  ⇒ **它在 `agenerp/` 之外，门禁扫不到，而它是会真发请求的实验设施。**
- **同一句话有第二处登记，也漂移了**：`docs/masterplan/STATE.md:751`（`[open] 2026-08-24T08:12Z`）逐字同样写着
  「今天没有任何判据拦得住这条路」。⚠️ **红线 5 只许追加** ⇒ 本 plan 只能**追加一条更正行**，不改写它。
  **这处漂移有实际代价**：起草步已多轮把这条 `[open]` 当成活缺口反复读（`STATE.md:940` / `:952` / `:1543` / `:1551`）。
- **CI 覆盖了，`GATE_VERIFY` 判定面没覆盖**：`missions/p1-insight.json:16` 的 `commands.test` 逐字只有
  `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
  ⇒ **新判据落在 `tests/routing/` 会进 CI（`gates.yml:617`），但不进 `GATE_VERIFY`。** `missions/**` 是红线，登记不改（见 `D3`）。
- **`docs/backlog/p1-insight-roadmap.md:43` 有一句今天已假**：逐字「`tests/routing` 既不在 `commands.test` 也不在任何 CI job 里」——
  `commands.test` 那一半今天仍真，**「任何 CI job」那一半已假**（`gates.yml:617-618` 步骤 ④）。roadmap 不在红线内，可改准。
- **仓库基线（本轮实跑）**：`python3 tools/gates/check_expected_red.py` → exit 0（`门禁 29 项：预期红 0，绿 29，跳过 0`）·
  `python3 -m pytest tests/unit tests/tools -q` → exit 0（`920 passed, 29 skipped`）·
  `python3 -m pytest tests/contracts tests/routing tests/context -q` → exit 0（`384 passed, 1 skipped`）·
  `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0。

**剩下的缺口一句话**：F8 这条链子上，**处置做完了、登记没跟上**。
一个只读 owner doc 的人，今天会得出「这个接缝完全没人守」的结论 —— 而它有人守，只是守得有边界。

## Goals

1. §12.5 那段登记文字说的是**今天的真话**：判据是谁、什么时候落的、**盖住什么形态**、**盖不住什么形态**。
2. 「盖住什么」**不是读代码读出来的，是变异实测出来的** —— CP9 §1.2 的教训逐字是「核了门禁绿不绿，没核绿的门禁在测什么」。
3. 该登记面**被钉住**：文档里的判据登记表与仓里真实存在的判据同构，由一条可复跑的 `tests/routing/` 判据保证，
   下一次「判据变了而文档没跟上」会**红**，而不是再挂一年。

## Non-Goals

1. **不改 `tests/gates/**` 一个字节（红线 1）。** 变异只施加在**产品源码 / owner doc（`docs/architecture/model-management.md`）/ 本 plan 自己新增的文件**上，逐次复原并 `sha256` 比对（`T4`：Phase 3 的 N1–N5 打在 owner doc 上，原措辞漏了这一类）。
2. **不收窄 `agenerp/routing/__init__.py` 的导出面** —— 人 2026-08-25 逐字裁定「加静态判据，**不收窄导出面**」，本 plan 不重开该裁定。
3. **不去堵门禁盖不住的那些形态**（别名导入 / 属性式构造 / `agenerp/` 之外的调用方 / **判据自身无存活守卫**，共**四**种，见 `D1`）。
   堵它要么改 `tests/gates/**`（红线 1），要么在 `tests/routing/` 造一条同义判据 ——
   后者正是 `agenerp/routing/adapter.py:114` 逐字反对的「放两处会出现一处松一处紧」。**照实登记为残余风险，交人。**
   ⚠️ **与另一条同族缺口划清界限，免得被读成「凡缺口都不修」**：`tests/unit/test_answer_judge.py:275-279` 那条缺口
   **不在红线内**、且 `STATE.md:1560` 已判它是指南规则 14 的不可降级项 —— 它归**工作项 6 / 9**（两格预算已满），
   不归本 plan。本条与它的差别是**红线**，不是**要不要修**。
4. **不动 §12.5 三张既有 `machine-read` 表的任何一格**（`capability-enum` / 任务类目矩阵 / `model-profiles`），
   它们由 `tests/routing/test_capabilities.py` 钉着，改它们是另一个结果面。
5. **不改 `DECISIONS.md` / `02-WBS.md` / `STATE.md` 的任何已有行**（红线 3/5），只在 `STATE.md` §3 **追加**证据行。
6. **不翻工作项 3 的 roadmap 状态词** —— 指 `docs/backlog/p1-insight-roadmap.md:43` 行首那个 `` `done` ``。
   本 plan 是交付后发现的登记漂移，只在**该行下追加**结清记录（同 `1618-1` / `1728-1` 先例），**状态词一个字不动**。
7. **不修 P1.9 plan `D2` 那条 `MAX_TOOL_CALLS` owner-doc 漂移** —— 它的面在工作项 6/9，两格预算已满，与本 plan 不共享收口判据（指南规则 4）。

## Task Route

- Type: `verification or audit work`（Phase 1）+ `implementation-only change`（Phase 2/3）
- Owner Docs: `docs/architecture/model-management.md` §12.5
- Skill Selection Basis: 无适用技能 —— 交付面是「一段登记文字 + 一条同构判据」，
  变异自查是本仓既有惯例（`docs/skills/README.md` 无对应条目）。全程 `Skill: none`。

## Infrastructure And Config Prereqs

No infra prereqs beyond existing baseline —— **全程离线**：不起 docker 栈、不调模型、不读任何 `AGENERP_LLM_*`。

## Execution Plan

### Phase 1 - 先测牙口，再改字

Status: completed
Targets: `agenerp/explain/loop.py`（临时变异，复原）· `agenerp/routing/adapter.py` + `agenerp/routing/__init__.py`（M5/M6 临时变异，复原）· `docs/evidence/p1-routing-guard-registration/`
⚠️ **`tools/experiments/p1_insight_live/run.py` 只读观测，零施加**（M4）；**`agenerp/routing/router.py` 已从 Targets 移除** —— 原 M6 打在那里是错的（`F1`）。
Skill: `none`

- Item Types: `Proof`
- Prereqs: 无

**预测在前、结果在后（本阶段硬约束②）：下表六行必须在第一次施加变异之前逐字写死进证据文件，事后逐条对照，不许改预测。**

| 变异 | 施加处（全部是产品源码，不碰 `tests/gates/**`） | 预测 |
|---|---|---|
| M1 | `agenerp/explain/loop.py` 内直接写 `ChatAdapter(cfg, model="qwen3:14b")` | 门禁 **红** |
| M2 | 同处改成 `from agenerp.routing import ChatAdapter as _CA` + `_CA(...)` | 门禁 **绿**（别名逃逸） |
| M3 | 同处改成 `import agenerp.routing as _r` + `_r.ChatAdapter(...)` | 门禁 **绿**（属性式逃逸） |
| M4 | **零施加** —— 直接跑门禁，观测它对**今天已经存在**的域外构造 `tools/experiments/p1_insight_live/run.py:159` 的反应 | 门禁 **绿**（扫描域只有 `agenerp/`）|
| M5 | 在 `agenerp/routing/` **之内**新增一处直接构造 | 门禁 **绿**（允许面成立，确认它不是空话） |
| M6 | **把类名整体改掉**：`agenerp/routing/adapter.py` 的 `class ChatAdapter` 与 `agenerp/routing/` 内的引用一并改名 | 门禁 **绿**（⚠️ 见下）、`pytest tests/routing -q` **红** |

⚠️ **M6 是本阶段最重要的一条，它测的是「判据会不会静默失效」**：
循环那条判据 `:74` 有一句存活守卫（`assert found, "一处 agent 循环都没找到 —— 判据本身可能已失效"`），
**adapter 那条判据 `:100` 没有** —— 它只有 `assert not offenders`。
⇒ **`ChatAdapter` 这个名字一旦不再存在，`offenders` 恒为空，判据永久静默绿。**
这正是 CP9 §1.2 罚的那件事。**「判据无存活守卫」就是第四种不覆盖形态**，须与另外三种一并写进 `routing-guards` 表与 `D1`。
⚠️ **它已经不是条件句 —— 第 2 轮独立评审在 `/tmp/m6replica` 隔离副本上实测过**（`R6`，**未碰活仓一个字节**）：
把 `agenerp/routing/` 内的 `ChatAdapter` 整体改名后，门禁 **`2 passed`（绿）**、`pytest tests/routing -q` **`2 errors`（红）**。
**执行期仍须在活仓上按变异协议复现一次并复原** —— 采信隔离副本的结论而不自己复跑，正是本仓禁止的「自报」。
⚠️ **预测里就写明红的形态**：`tests/routing` 那一半红在 **collection 阶段的 ImportError**（`test_adapter.py` / `test_router.py`），
**不是断言失败**；且 M6 会连带打断 `agenerp/explain/loop.py:53` 的 `from agenerp.routing...` 导入 —— 两点都照实记进证据文件。
⚠️ **原起草版把 M6 打在 `router.py:90` 上是错的**（独立评审 `F1` 指出，起草者复跑确认）：
判据 `:92` 逐字 `if rel.startswith(_ALLOWED_ADAPTER_PREFIX): continue` ⇒ `agenerp/routing/**` 整份跳过，
在那里改名「门禁仍绿」是**定义上必然**，证明不了任何事。**照实记这次更正，不抹掉。**

- [x] `Proof` — 把上表六行原样落进 `docs/evidence/p1-routing-guard-registration/README.md`，**先落盘再施加第一条变异**（`git log` 可验先后）
      - Skill: `none`
- [x] `Proof` — 逐条施加、跑 `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q`、记退出码与失败文案首行、复原、`sha256` 逐字节比对
      - Skill: `none`
- [x] `Proof` — **预测与实测不吻合的，照实记在证据文件里，并且以实测为准写进 Phase 2 的文档措辞**；不回头改预测
      - Skill: `none`

Exit Criteria:

- [x] **M1 / M2 / M3 / M5 / M6 五条**各有：命令原文 + 退出码 + 复原后的 `sha256` 比对结果（`RESTORED OK`）；
      **M4 是零施加**（只观测今天已存在的 `tools/experiments/p1_insight_live/run.py:159`）⇒ 它只有命令原文与退出码，**没有也不该有 `RESTORED OK`**
- [x] 施加完毕后 `git status --porcelain -- agenerp/ tools/ tests/` → **零行**（产品源码与实验设施零残留）
      ⚠️ **不许用 `git checkout -- .` 兜底复原** —— 那会把本 plan 自己未入库的文件一并抹掉；复原必须逐文件按施加前的 `sha256` 比对（同 `1835-1` 口径）
- [x] 判据的真实覆盖边界有一句可引用的结论（「盖住 X 形态；不盖 Y/Z 形态」），**由实测支撑，不由读源码支撑**
- [x] `docs/evidence/p1-routing-guard-registration/README.md` 落盘
- [x] **把这条打法写进证据文件**（四轮评审的共同结论）：本 plan 两次栽在同一个病上
      （`F1` 门禁无存活守卫 · `S1` 新判据无存活守卫），**两次都是靠「按判据源码/正文口径做原型实跑」发现的，不是靠读文字发现的**
      —— 记为 CP9 §1.2 的一条可复用打法
- [x] `docs/logs/` 更新

### Phase 2 - 把 §12.5 那段登记改成今天的真话

Status: planned
Targets: `docs/architecture/model-management.md` · `docs/masterplan/STATE.md`（**只许追加，红线 5**）· `docs/backlog/p1-insight-roadmap.md`（**行下追加，状态词不动**）
Skill: `none`
Prereqs: Phase 1

- Item Types: `Fix | Decision | Add`（6 项中 `Fix`×4 = **67%**，**够不上规则 7 逐字的 80% 门槛** ⇒ 不在 phase 级声明统一类型，逐项标注为准）
- [ ] `Fix` — 改准 `:295` 「今天没有任何判据拦得住这条路」：写明判据文件、判据函数名、落地 commit `d18c05c` 与日期，
      并**逐字列出 Phase 1 实测出的不覆盖形态**（不写成「已被拦住」）
      - Skill: `none`
- [ ] `Fix` — 改准 `:297` 「真正的闸要等 P1.4 落地、有了唯一的调用入口」：P1.4 已落地，
      **而「唯一入口」没有出现**（两个产品调用点，逐条点名）⇒ 照实写「这条预期没兑现」，不假装兑现
      - Skill: `none`
- [ ] `Decision | Add` — 新增 `<!-- machine-read: routing-guards -->` 表，每行**五**列：判据文件 · 判据函数名 · 盖住的形态 · **明确不盖的形态** · **实测日期 + 证据路径**。
      第 5 列（`R7`）指向 `docs/evidence/p1-routing-guard-registration/`，让读者一眼看出**这条覆盖断言有多老** —— 本 plan 修的就是一条没人知道它有多老的断言。
      **成员规则起草期写死，不留给执行期（`R1`）：选 (a) 文件级纳管** —— **一个文件进表，它里面的每一个顶层 `def test_*` 都必须各占一行**。
      ⇒ `tests/gates/test_agent_seam_stays_swappable.py` 实点 **2 条**（`:58` `test_agent_loop_lives_in_exactly_one_module` · `:87` `test_chat_adapter_is_only_constructed_inside_routing`），
      **两条都要登记**；循环那条照实写它盖的是「第二处 agent 循环」，**不硬塞成 routing 语义**（表名 `routing-guards` 指的是「本节登记的接缝判据」，不是「只登记 routing 语义的判据」，这句要写进表的前言）。
      **备选 (b) 正则纳管**（`B` 只取匹配写死正则的函数）：**否决** —— 正则本身会变成第二个可以被悄悄放松的旋钮。
      ⚠️ **「(a) 更难骗」不是感觉，是实测**（第 4 轮独立评审）：有人会问 `_REGISTERED_FILES` 自己是不是同一个旋钮 ——
      **把该常量清空后跑 baseline → `RED ④`**（表里出现未纳管文件）⇒ **③ 与 ④ 互相咬住，它无法被悄悄放松成空。**
      **残余风险**：(a) 使这张表**只能纳管「整份都是接缝判据」的文件** —— 若将来要登记 `tests/routing/test_capabilities.py`（实点 14 条 `def test_`）
      或 `tests/unit/test_configured_model_is_the_one_used.py`（实点 4 条），这张表会退化成全量测试清单，第 3/4 列没法逐行写实。
      ⇒ **本期表里只纳管那一个文件**；要纳管第二个文件时**必须先重开这条 `Decision`**，这句写进表的前言与判据模块头。
      - Skill: `none`
- [ ] `Fix` — **第二处登记也要改准**：往 `docs/masterplan/STATE.md` §3 **追加**一条更正行（**只追加，零删除，红线 5**），
      点名 `[open] 2026-08-24T08:12Z`（`:751`）那两句「今天没有任何判据拦得住这条路」/「真正的闸要等 P1.4」，
      声明它们已被 `d18c05c` 与工作项 6 的 `done` 证伪，并给出本 plan 的证据文件路径。
      ⚠️ **先堵一条会被收口审计误判的引证（`S5`）**：`D3` 引的 `docs/masterplan/01-EXECUTION-MODEL.md:14` 紧挨着的 `:15`
      逐字写着角色 B「**不得手写 STATE**」—— 顺着读下去会以为本条撞红线。**优先级要写进追加行本身**：
      `AGENTS.md:14`（红线 5）逐字「**`STATE.md` 只允许追加证据行**，不得改写已有行」是**更具体的限定**，
      且 `AGENTS.md:3-4` 逐字规定红线**优先于** `docs/masterplan/` 的执行协议；仓内先例 `STATE.md:758` / `:773` / `:781` / `:789`
      - Skill: `none`
- [ ] `Fix` — **`docs/backlog/p1-insight-roadmap.md:43` 那句已假的一半改准**：逐字「`tests/routing` 既不在 `commands.test`
      也不在任何 CI job 里」—— **`commands.test` 那一半仍真，「任何 CI job」那一半已假**（`gates.yml:617-618` 步骤 ④ + `:631` `COVERED` 含 `routing`）。
      按本仓惯例**在该行下追加结清记录**，不改写原句
      - Skill: `none`
- [ ] `Decision` — 「保留原句 + 追加改准」还是「就地改写」：选**就地改写**。
      ⚠️ **本裁定只管 §12.5 那一段（`R8`）** —— 同 Phase 另两条 `Fix`（`STATE.md` / roadmap）用的是**追加**，
      那是**红线 5 与仓内惯例决定的，不是本裁定的选择结果**，两者不矛盾。
      备选是 `docs/bugs/01-…` 那种「原状态行保留 + 追加」的写法；否决理由是本段不是状态行而是**事实陈述**，
      留着一句已不成立的事实陈述正是本 plan 要修的病（§7.25.4 逐字先例：「这句已在 `router.py` 模块头就地改准，**不留在那里当一句已不成立的话**」）。
      残余风险：就地改写会让 `git diff` 之外看不到原句 ⇒ **原句逐字抄进证据文件**留痕
      - Skill: `none`

Exit Criteria:

- [ ] 该段无一句与今天的仓库不符（逐句附一条可复跑命令）
- [ ] **`STATE.md` §3 的更正行已追加**：`git diff --numstat <BASE> -- docs/masterplan/STATE.md` **删除列为 0**，
      且新行逐字点名 `[open] 2026-08-24T08:12Z` 与 `d18c05c`
- [ ] **`docs/backlog/p1-insight-roadmap.md:43` 的结清记录已追加**：追加文字**分开说** `commands.test` 那一半仍真、「任何 CI job」那一半已假
      ⚠️ **不用 `git diff --numstat` 判它**（`R3`）—— 那一行是**一整行**，行内追加必然让整行进 diff（`1 1`），numstat 判不出「有没有改写原句」。
      ⚠️ **也不用「`grep` 原句片段」**（`S2`）—— 该行实测长 **1066 字节 / 701 字符**
      （⚠️ `T3(d)`：第 3 轮记的「1066 字符」是 `awk length()` 按字节数读出来的，那行满是 CJK；**论点不变，数字照实更正**），只守被点名的那个片段，
      **而片段由谁来挑没写死**：独立评审实跑演示过，挑中被改那句能捕获、挑成别处（如 `` sha `5a0f87a` ``）**同一次改写照样绿**。
      **改用子串不变式**，三处加固逐字写死（`T3`）：
      **(a) `old` 从 git 取，不靠执行者手工存**：`git show <BASE>:docs/backlog/p1-insight-roadmap.md` 里按工作项前缀 `- 3. 模型路由 v0` 定位那一行
      （独立评审实跑验证：`HEAD` 里恰好命中 **1** 行、以 `）` 结尾、其 `core` 是工作树全文的子串）——
      手工存会把判据的有效性绑在「当时记得先存」这个人工动作上，**收口审计无法独立复跑**。
      **(b) 砍行尾那个字符之前先断言它就是 `）`**：`assert old.rstrip().endswith("）")`，再取 `core = old.rstrip()[:-1]`
      —— 无条件 `[:-1]` 在行尾不是 `）` 时会**静默砍掉一个真字符**而 `core in ...` 仍可能成立，判据静默放松。
      **(c) 判全文子串而不是判那一行**：断言 `core in new_text`（整份文件）
      —— 合法的行内追加照样过、任何把 `core` 从中间劈开的写法照样红，且不再把「追加必须在行内、不得换行」这条**没写出来的**格式约束塞进判据。
      独立评审实测三格：`行内追加(合法)` → **PASS** · `改写原句` → **FAIL** · `翻状态词` → **FAIL**
      ⇒ **一条不变式同时覆盖「原句任意处被改写」与「状态词被翻」**，并**天然容纳** `1618-1` 先例里那个「行尾 `）` 右移一个字符」的合法位移
      （那条口头提醒因此变成判据自身的定义，不再靠收口审计记得）。
      ⚠️ **定位不写死行号** —— 用工作项前缀（`- 3. 模型路由 v0`）定位，roadmap 上方一旦插行，写死的 `:43` 会指错行
- [ ] `git diff docs/architecture/model-management.md` 的改动**全部落在 `:293-297` 那一段与新增表内**；
      三张既有 `machine-read` 表零改动（`python3 -m pytest tests/routing/test_capabilities.py -q` → exit 0 自证）
- [ ] owner doc 已更新（本 plan 的结果面就是它）
- [ ] `docs/logs/` 更新

### Phase 3 - 钉住登记面，让下一次漂移变红

Status: planned
Targets: `tests/routing/test_routing_guard_registration.py`（新增）· `docs/architecture/model-management.md`（N1–N5 的变异施加面，逐条复原）
Skill: `none`
Prereqs: Phase 2

- Item Types: `Add | Proof`
- [ ] `Add` — 新判据读 `routing-guards` 表（复用 `tests/routing/test_capabilities.py` 的 `_table_after()` 口径），
      断言的是**双向同构 + 一句存活守卫**，起草期就写死，不留给执行期补：
      **① 纳管文件集合写死进判据模块常量**：`_REGISTERED_FILES = {"tests/gates/test_agent_seam_stays_swappable.py"}`
      **② 令 `A` = 表里 (判据文件, 判据函数名) 的集合；`B` = `_REGISTERED_FILES` 内各文件的全部**顶层** `def test_*` 的集合。断言 `A == B`。**
      **③ 存活守卫**：`assert A, "routing-guards 表为空 —— 判据静默失效"`
      **④ 纳管边界**：`assert {f for f, _ in A} <= _REGISTERED_FILES`（表里出现未纳管文件即红）
      **⑤ 第 5 列可判定的那一半也要钉**：断言每行第 5 列里的**证据路径存在**（`Path(...).exists()`），
      且日期字段**逐字为 `YYYY-MM-DD` 并能过 `datetime.date.fromisoformat`**（`T2(b)`：不写死格式的话，
      执行者写成 `2026-08-26T20:55Z` 或 `08-26` 都会让判据**在自己落地那天就红**）。
      ⚠️ **路径以 Phase 1 Exit 落盘的那个路径为准，逐字节一致**（`T2(c)`），今天两处已一致：`docs/evidence/p1-routing-guard-registration/`
      ⇒ 删表一行 → `B` 多一个 → **红**；写不存在的函数名 → `A` 多一个 → **红**；
      写错文件路径 → 该文件不在 `_REGISTERED_FILES` 里 → **红（④）**；**整表删空 → 红（③ 捕获，不是 `A == B` 捕获）**；
      证据目录被删/改名 → **红（⑤）**。
      ⚠️ **`B` 绝不能由表自己导出**（`S1`，独立评审按上一版正文做出原型并实测：
      上一版 `B` 取「**表中出现的**每个文件」⇒ 表清空则 `A = B = ∅` ⇒ **`A == B` 成立 ⇒ 绿**，
      实测四格 `baseline GREEN / N1 RED / N2 RED / N3 RED / **N4 GREEN ❌**`）。
      **那正是本 plan 在 `D1` 里登记的第四种形态（判据无存活守卫）在新判据上的重演** —— 照实记，不抹掉。
      ⚠️ **不写成单向存在性检查**（第 1 版就是单向的，独立评审 `F2` 判它同义反复）。
      ⚠️ **`_REGISTERED_FILES` 同时把 `Decision`（本 Phase 2 那条）从散文变成机器约束**：
      想纳管第二个文件必须改那行常量，改常量就必须回来重开那条 `Decision`。
      - Skill: `none`
- [ ] `Add` — **判据自己声明它验的是什么**：模块头逐字写明「本条只验**存在性同构**，不验语义。
      『那条判据到底盖住什么』由 `docs/evidence/p1-routing-guard-registration/` 的变异实测负责」——
      这是 CP9 §1.2「判据名不副实」的直接对冲
      - Skill: `none`
- [ ] `Proof` — 变异自查**五条**，全部施加在**本 plan 自己新增的文件与 owner doc** 上：
      N1 删表里一行 → 预测**红** · N2 把表里的函数名改一个字 → 预测**红** ·
      N3 把表里的文件路径改一个字 → 预测**红（由 ④ 纳管边界捕获）** · N4 把整张表删空 → 预测**红（由 ③ 存活守卫捕获，不是由 `A == B` 捕获）** ·
      **N5 把第 5 列的证据路径改成不存在的目录 → 预测红（由 ⑤ 捕获）**。逐条复原并 `sha256` 比对
      ⚠️ **每条都要写明「预测由哪一句断言捕获」** —— 只写「红」会让一条其实是被别的断言顺带打红的变异冒充成守卫有效
      - Skill: `none`

Exit Criteria:

- [ ] `python3 -m pytest tests/routing -q` → exit 0，且条数比基线 `179 passed, 1 skipped` **只增不减**
- [ ] **五条**变异逐条有：预测 · **预测的捕获者** · 实测 · 退出码 · `RESTORED OK`；不吻合的照实记，并说明实测与预测差在哪 —— **不在执行期改判据设计**
- [ ] **N1–N5 复原自证**：`git status --porcelain -- docs/architecture/` → **零行**（与 Phase 1 同口径，`T4`）
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0
- [ ] `python3 tools/gates/check_expected_red.py` → exit 0
      ⚠️ **不把「仍是 29 项」写成本 plan 的判据** —— 该脚本只跑 `tests/gates/`，而本 plan 一个字都不碰那里，
      「项数不变」是**恒真**的，证明力为零（独立评审 `Q6` 指出）。它在这里只作基线不回归的旁证。
- [ ] No owner-doc update required（Phase 2 已交付 owner doc 那一半）
- [ ] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: needs revision (fresh subagent, 2026-08-26) because 逐条对活仓复跑后，`Current Baseline` 的**数字与引文几乎全部核实无误**（判据落地 commit `d18c05c` 2026-08-25 · `pytest tests/gates/test_agent_seam_stays_swappable.py -q` → exit 0 `2 passed` · `grep -rn 'test_agent_seam_stays_swappable\|only_constructed_inside_routing' docs/architecture/` → exit 1 零命中 · `:293-297` 行号与逐字引文精确 · `git log -1 -- docs/architecture/model-management.md` → `38969b1 2026-08-26` · `pytest tests/routing -q` → `179 passed, 1 skipped` · `check_expected_red.py` → exit 0 `门禁 29 项：预期红 0，绿 29，跳过 0` · `route()` 产品调用点确为两处 · `gates.yml:617-618` 确已跑 `tests/routing`、`:631` `COVERED` 确含 `routing` · 工作项 3 名下确只 1 份 plan ⇒ `1/2` 属实），**这份 plan 也确实该存在**（判词见 F8：它落在决策表第 3 行 `stale-doc conflict → Full plan`，不是 trivial edit）；但有**两条 blocking**：Phase 1 的 M6 施加在一份**门禁根本不扫描的文件**上，因而证明不了它声称要证明的事，同时漏掉了这条判据真正的空转风险（F1）；Phase 3 的 N1 把一个**设计上必然的洞**写成「预测绿 → 当场补断言」，而它给出的补法（`表条数 ≥ 仓里真实判据条数`）方向错且不可计算，照此执行会再造一条 CP9 §1.2 罚的「名不副实的绿判据」（F2）。另有 5 条 should-fix，其中一条是**起草期漏点了今天就真实存在的一处域外构造**，它同时使 D1 的重开事件在起草当天即已成立（F3）。

**Findings**（编号 · 严重度 · 位置 · 实测事实 · 建议改法）

- **F1 · `blocking` · Phase 1 变异表 M6（plan `:98`）** —— **M6 证明不了它声称要证明的事，且真正的空转风险被漏掉。**
  - 实测：判据 `tests/gates/test_agent_seam_stays_swappable.py:91-93` 是 `rel = _rel(path)` / `if rel.startswith(_ALLOWED_ADAPTER_PREFIX): continue`，而 `_ALLOWED_ADAPTER_PREFIX = "agenerp/routing/"`（`:47`）⇒ **`agenerp/routing/router.py` 整份文件根本不进 AST 扫描**。把 `:90` 那处构造改名，门禁绿是**定义上必然**，与「门禁是不是靠『某处存在构造』在工作」毫无关系。
  - 实测：真正的空转风险在别处 —— 同文件的循环判据 `:74` 有 `assert found, "一处 agent 循环都没找到 —— 判据本身可能已失效…门禁静默地什么都不再检查"`，而 **adapter 判据 `:100` 只有 `assert not offenders`，没有任何对应的非空/存活守卫**。⇒ 只要 `ChatAdapter` 这个类名被整体改掉（`agenerp/routing/adapter.py:110` + 全部引用），这条判据将**永久静默绿、永远不再检查任何东西**。这正是 CP9 §1.2「绿着的判据未必测它名字说的那件事」，也正是本 plan Goals 2 立誓要对冲的东西。
  - 建议：M6 改成「把 `agenerp/routing/adapter.py:110` 的类名 `ChatAdapter` 连同全部引用一起改掉」，预测 **门禁绿 / `pytest tests/routing -q` 红**；并把「**本判据无存活守卫：类名一改即永久空转**」作为**第四种不覆盖形态**写进 Phase 2 的 `routing-guards` 表与 `D1`。若要保留原 M6，须把它的说明词改成「确认 `agenerp/routing/**` 的允许面是**按路径前缀整份跳过**，不是按构造点豁免」——那才是它实际测到的事。

- **F2 · `blocking` · Phase 3 `Proof` 项 N1（plan `:161`）** —— **「预测绿 ⇒ 当场补断言」是把设计缺陷排进执行期，而给出的补法方向错且不可计算。**
  - 实测判词：N1「删表里一行 → 预测绿」**不是变异实验**，是对「只做存在性单向检查」这一设计的**同义反复**——单向检查在定义上不可能发现少一行。把一个必然结论写成预测、再靠「若为绿则当场补一条断言」兜底，等于**承认判据在起草时就有洞**，却把设计决定推给执行者临场做。指南规则 9（Decision 要写选项与残余风险）与规则 5（proof before closure）都要求它在起草期就定死。
  - 实测判词：补法「表条数 ≥ 仓里真实判据条数」**方向错**——`≥` 允许「删一条真行、加一条假行」照样绿；且「仓里真实判据条数」**没有可计算的定义**（哪些 test 算 "routing guard"？靠人手维护那个数，就是本 plan 正在治的那个病）。
  - 建议：把 Phase 3 第一个 `Add` 项直接写成**双向同构**，并写死可计算的反向源，例如：表里逐行的「判据文件 + 判据函数名」构成集合 `A`；对表中**出现过的每一个判据文件**，用 `ast` 取出其全部 `def test_*` 顶层函数名构成集合 `B`；断言 `A == B`（不是 `A ⊆ B`）。这样「仓里新增一条同文件判据而没登记」会**红**，「表里删掉一行」也会**红**。然后把 N1 的预测改成 **红**，让它真正成为一次变异实测而不是补丁触发器。若起草者认为 `A == B` 过严（例如同文件里有与 routing 无关的判据），则必须在 Phase 3 写一条 `Decision`，写明取哪种可计算的子集口径、备选、残余风险 —— 但**不能留「预测绿再说」**。

- **F3 · `should-fix`（逼近 blocking）· `Current Baseline` 全节 + Phase 1 表 M4（plan `:96`）+ `D1` 重开事件（plan `:202`）** —— **起草期漏点了一处今天就真实存在的域外构造。**
  - 实测：`grep -rn 'ChatAdapter' --include='*.py' .` 排除 `agenerp/` 与 `tests/` 后，命中 **`tools/experiments/p1_insight_live/run.py:44` `from agenerp.routing.adapter import ChatAdapter` 与 `:159` `self._poster = None if inner is not None else ChatAdapter(config)`**。该文件模块头逐字「**它是实验设施，不是产品代码**」，但 `:151` 逐字「`inner` 为空时**打真端点**：借 `ChatAdapter` 自己的 `_post`」⇒ 这是一条**会真的发出调用**的域外构造，`_PKG = <repo>/agenerp` 的 rglob 扫不到它。STATE.md `:1543` 也已点过这一处。
  - 后果一：M4 **不需要造临时文件**。仓里现成有真实样本，用它取证既更强也不脏工作树；照现写法新建 `tools/` 下临时文件反而会污染 `git status`（见 F6），且「逐次复原并 `sha256` 比对」对一个「新建再删除」的文件**没有定义**。
  - 后果二：`D1` 的重开事件逐字「**实测出现一次真实的逃逸构造**」在**起草当天就已经成立** ⇒ 这条 deferral 自我否定。
  - 建议：`Current Baseline` 增一条实点行写明 `tools/experiments/p1_insight_live/run.py:159`；M4 改为「**实点**该处已存在的域外构造并跑门禁确认绿」（零变异、零新建文件）；`D1` 重开事件改准为「**在 `agenerp/**` 产品代码内**出现一次逃逸构造，或实验设施里的那处被产品代码 import」。Phase 2 的 `routing-guards` 表在「不盖的形态」一列里应**点名**这处真实实例，而不是只写一个抽象形态。

- **F4 · `should-fix` · Non-Goals 5（plan `:62`）** —— **同一句谎话的第二处登记（`STATE.md:751`）无人认领。**
  - 实测：`grep -rn '没有任何判据拦得住' --include='*.md' .` 全仓命中**两处**：`docs/architecture/model-management.md:295` 与 **`docs/masterplan/STATE.md:751`**（`[open] 2026-08-24T08:12Z` F8 行，逐字「**今天没有任何判据拦得住这条路**」+ 处置逐字「真正的闸要等 P1.4 … 届时由人决定」）。两处都已被 `d18c05c` 证伪。
  - 实测代价：STATE.md `:940` / `:952` / `:1543` / `:1551` 显示起草步已**连续多轮**把 F8 当候选重读，`:1543` 那轮实读后自己写下「**F8 的活已经干完，`[open]` 行是过期描述，不是活缺口**」——过期登记正在持续消耗判断轮次。
  - 判词：按规则 14，这是**确认的 owner-doc 漂移**，不可降级。红线 4 使它**只能追加**——但「只能追加」不等于「不必处置」。
  - 建议：Non-Goals 5 保持不变（不改已有行），但在 Phase 2 增一条 `Fix` 执行项 + 对应 Exit Criteria：**向 `STATE.md` §3 追加一行，逐字点名 `[open] 2026-08-24T08:12Z`，声明其「没有任何判据拦得住」与「等 P1.4 才谈得上」两句均已被 `d18c05c`（2026-08-25）证伪，指向新的 `routing-guards` 登记表**。

- **F5 · `should-fix` · Non-Goals 5/6（plan `:62-64`）** —— **两处承诺的追加动作没有任何 Phase 认领。**
  - 实测：Non-Goals 5 承诺「在 `STATE.md` §3 追加证据行」、Non-Goals 6 承诺「在 roadmap 该行下追加结清记录」，但三个 Phase 的 `Targets`、执行项、`Exit Criteria` **一处都没提这两个文件**。Anti-Slacking Rule 要求每个在范围项落在四态之一；「写在 Non-Goals 里的一句承诺」不是其中任何一态。
  - 先例：`2026-08-26-1618-1` 的收口审计已就**完全同形**的问题点过名（其 `Closure` 逐字：`docs/backlog/p1-insight-roadmap.md` 有改动而「**该文件不在 Phase 3 的 `Targets` 列表里**」）。同一个坑不该踩第二次。
  - 建议：把两条追加动作写成 Phase 3（或新增收尾 Phase）的显式执行项，并把两个文件路径写进该 Phase 的 `Targets`。

- **F6 · `should-fix` · Phase 1 Exit Criteria（plan `:110`）** —— **`git status --porcelain` → 零行 今天就不成立。**
  - 实测：此刻 `git status --porcelain` 已输出 `?? docs/plans/p1-insight/2026-08-26-2101-1-routing-guard-registration-drift.md`（plan 自己未入库）。Phase 1 还要新建 `docs/evidence/p1-routing-guard-registration/README.md`，M4 按现写法还要新建 `tools/` 下临时文件 ⇒ 该判据**必然红**，执行者只能靠「先提交再跑」或干脆略过它，两条都不好。
  - 建议：照 `2026-08-26-1835-1` 的 `P2-0` 先例改成 **`git status --porcelain -- agenerp/ tools/ tests/` → 无输出**（括号里的「产品源码零残留」本意即此）。该 plan 同时逐字写明「**不许用 `git checkout -- .` 兜底复原**」（会抹掉人侧在飞改动），本 plan 也该抄上这一句。

- **F7 · `should-fix` · `Current Baseline` 的「CI 面无需改动」条（plan `:36-37`）+ Phase 3 Exit** —— **CI 那一半对了，`commands.test` 那一半没说。**
  - 实测（对了的那一半）：`.github/workflows/gates.yml:617-618` 确为 `- name: ④ 模型路由（tests/routing）` / `run: python3 -m pytest tests/routing -q`，`:631` `COVERED="contracts context experiments fixtures gates routing tools ui unit"` 确含 `routing` ⇒ **Phase 3 的判据在 CI 上不是零覆盖，一行 workflow 都不用改，红线 2 不被触碰。这条不构成 blocking finding。**
  - 实测（没说的那一半）：`missions/p1-insight.json` 的 `commands.test` 逐字只有 `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` ⇒ **新判据不在 mission GATE_VERIFY 的判定面上**。同一份 json `:24` 逐字警告过这个坑：「commands.test 里没有单测，GATE_VERIFY 看不见 —— **判定面漏了一块，循环就不会自己发现**」。`missions/` 在红线内 ⇒ 只能照实登记，不能不写。
  - 顺带（同一事实的第三处过期登记）：`docs/backlog/p1-insight-roadmap.md:43` 工作项 3 行逐字仍写「`tests/routing` **既不在 `commands.test` 也不在任何 CI job 里**」——后半句今天已假。本 plan 既然要在该行追加结清记录，顺手在追加段里点名（**不改原文**）。
  - 建议：`Current Baseline` 那条补一句「CI 覆盖成立，`commands.test` 不覆盖」；`Closure Gates` 的 "verification scope limited" 那条把它写进去；`D1`/`D2` 之外可新增一条 `watch-only residual` 或并入 `D1`。

- **F8 · `nit`（判词，非 finding）· 重点拷问 1：这份 plan 值不值得存在** —— **值得。它落在决策表第 3 行 `stale-doc conflict → Full plan`，不是 `Trivial local edit`。不构成 blocking finding。**
  - 理由 a：`:295` 不是「typo / copy change / single style tweak / test-only cleanup」中的任何一种，它是一句**与仓库相反的事实陈述**——实测判据 `d18c05c`（2026-08-25，`lize`，唯一一条 commit）今天 `pytest tests/gates/test_agent_seam_stays_swappable.py -q` → exit 0 `2 passed`，而 `:295` 逐字仍写「今天**没有任何判据拦得住这条路**」。这正是规则 14 的「确认的 owner-doc 漂移」，也正是决策表第 3 行逐字列出的 `stale-doc conflict`。
  - 理由 b：交付面不止改字 —— 新增 `<!-- machine-read: routing-guards -->` 表 + **净新增判据代码** `tests/routing/test_routing_guard_registration.py` + 证据目录 + 两处台账追加，跨 4–6 个文件，且「加一条判据」本身就是决策表第 3 行的高风险面（判据写错=把缺陷钉成规范）。
  - 预算面独立复核（不采信 plan 自报）：逐份点 `docs/plans/p1-insight/*.md` 的 `> Work Item:` 首行，工作项 3 名下**确实只有** `2026-08-24-1457-1-model-routing-v0.md` 一份；`2026-08-26-1728-1` 的首行是「**3b**」，且 `docs/backlog/p1-insight-roadmap.md:44` 逐字「**plan 预算独立计，不占工作项 3 的额度**」、`02-WBS.md:81` 是独立的 `P1.1-fix` 行 ⇒ **`1/2` 属实，本 plan 是最后一格，占得合规。**
  - ⚠️ 唯一 nit：`> Source:` 只记「起草步 2026-08-26T20:55Z 实测」，未点名 **`STATE.md:1543`** —— 同日更早一轮已实读得出「**F8 的活已经干完，`[open]` 行是过期描述，不是活缺口**」。那是本 plan 的直接前身，该引；不引会让读者以为这是首次发现。

- **F9 · `nit`（判词）· 重点拷问 4：Non-Goals 3 是不是把在范围的事降级了** —— **不是降级，它确实是另一个结果面。判词成立，但措辞要补一句。**
  - 理由 a（不是在线缺陷，是覆盖缺口）：实点 `agenerp/` 内的 `ChatAdapter(` 只有 `routing/router.py:90`（真实构造）与 `adapter.py:135`（`__repr__` 的 f-string 文本）⇒ **三种逃逸形态今天在产品代码内零实例**。规则 14 管的是「确认的**活缺陷**」，这里没有活缺陷。
  - 理由 b（堵它必须越界）：匹配形状写死在 `tests/gates/test_agent_seam_stays_swappable.py:96-98`（红线 1），而第二处同义判据被 `agenerp/routing/adapter.py:114` 逐字反对（「校验是 `router.route()` 的职责，**放两处会出现"一处松一处紧"**」）。且人 2026-08-25T09:33Z 已就该接缝下过裁定（`STATE.md:752`）⇒ 处置者是人。
  - 理由 c（Anti-Slacking 合规）：`D1` 有 `Classification` + `Why Not Blocking Closure` + `Successor Required: yes（人）` + 具名重开事件（但重开事件写错了，见 F3），且 plan 把它**登记进 owner doc**而不是藏起来 —— 这正是「照实登记为残余风险」的正确形态。
  - ⚠️ 措辞补正：Non-Goals 3 逐字「堵它要么改 `tests/gates/**`（红线 1），要么在 `tests/routing/` 造一条同义判据」**不完全准确**。同族缺口的另一实例 **`tests/unit/test_answer_judge.py:275-279`**（同样只认 `ast.Call` + `ast.Name`，属性式构造照样绿）**不在红线内**，且 `STATE.md:1560` 已逐字判它「**这是一条确认在线的缺口，按起草指南规则 14 属不可降级项**」。它归工作项 6/9（另一结果面，两格预算已满，`2026-08-26-1835-1` 的审计已登记）⇒ **不归本 plan**，但 Non-Goals 3 应点名它，免得读起来像「所有同族缺口都被红线挡住了」。

- **F10 · `nit`（判词）· 重点拷问 5：一个 plan 一个结果面（规则 4）** —— **成立，是一个结果面，不该拆。**
  - Phase 1 是 Phase 2 措辞的**取证**（「盖住什么」必须是实测出来的），Phase 3 是给 Phase 2 的产物**上锁**。三者共享**同一条收口判据**：「§12.5 的判据登记说的是今天的真话，且下一次漂移会红」。规则 4 逐字「shares the same behavioral contract and closure criteria is still ONE result surface — do not over-split」，此处正合。
  - 反向检查也过：三个 Phase 里没有任何一个能**独立收口**（Phase 1 的证据文件本身不是交付物、Phase 3 的判据离了 Phase 2 的表无物可读）⇒ 不存在「多个独立收口判据」。

- **F11 · `nit`（判词）· 重点拷问 6：红线复核** —— **未发现撞红线，但有一处路径写得不明确、一处 Exit Criteria 是恒真的。**
  - 逐条实点：三个 Phase 的 `Targets` 无一落在 `tests/gates/**` / `.github/workflows/**` / `docs/masterplan/DECISIONS.md` / `docs/masterplan/02-WBS.md` / `missions/`；Phase 3 只往 `tests/routing/` 新增文件，`gates.yml` 的 `COVERED` 守卫（`:631`）只管**目录**、`routing` 已在列 ⇒ 不触发。
  - ⚠️ 路径不明确：Non-Goals 6 逐字「只在该行下**追加**结清记录」——「该行」实为 **`docs/backlog/p1-insight-roadmap.md:43`**，**不是** `02-WBS.md:80` 那一行、也不在 `missions/`。plan 没写出这个路径，读者/执行者容易误读成要动 `02-WBS.md`，那会直接撞它自己 `:189` 的红线自证清单。建议 Non-Goals 6 补上完整路径。
  - ⚠️ 恒真判据：Phase 3 Exit「`check_expected_red.py` → exit 0 且**仍是 29 项**（本 plan 一条门禁都没加没减）」——实测 `tools/gates/check_expected_red.py:74` 的命令是 `[sys.executable, "-m", "pytest", "tests/gates", ...]`，**只跑 `tests/gates`** ⇒ 往 `tests/routing/` 加文件在原理上不可能改变 29 这个数。留着无害（它确实证明「没偷偷动门禁」），但**证明力接近零**，别把它当成 Phase 3 的主要保险。

- **F12 · `nit`（复核结论）· Phase 1 变异表 M1–M5（plan `:93-97`）** —— **六条预测的"结果"全部正确；只有 M6 的"理由"是错的（已在 F1 单列）。**
  - 我的独立取证（不采信 plan 自报，离线用判据同一套 AST 条件 `ast.Call` + `func` 为 `ast.Name` + `id == "ChatAdapter"` 逐形态跑）：**M1** 直接构造 → offenders 非空 ⇒ **红** ✓ · **M2** `from … import ChatAdapter as _CA` + `_CA(...)` → offenders 空 ⇒ **绿** ✓ · **M3** `import agenerp.routing as _r` + `_r.ChatAdapter(...)`（`func` 是 `ast.Attribute`）→ offenders 空 ⇒ **绿** ✓。
  - **M4** 读源码 `:41` `_PKG = _REPO_ROOT / "agenerp"`、`:51` `_PKG.rglob("*.py")` ⇒ `tools/` 落在扫描域之外 ⇒ **绿** ✓（但见 F3：不必造这个文件）。
  - **M5** 读源码 `:92` 前缀 `continue` ⇒ `agenerp/routing/` 内新增构造被整份跳过 ⇒ **绿** ✓，「允许面不是空话」的说法成立。
  - **M6** 结果预测（门禁绿 / `pytest tests/routing` 红）**也对**——改名后 `route()` 抛 `NameError`，`tests/routing` 必红；门禁绿。**但绿的原因不是 plan 写的那个**（见 F1）。

- **F13 · `nit` · `Current Baseline` 的 plan 份数（plan `:34`）** —— **唯一一处对不上的数字。**
  - 实测：`ls docs/plans/p1-insight/*.md | wc -l` → **26**，不是 25。差的正是本 plan 自己（起草时尚未落盘）。**不影响**工作项 3 的 `1/2` 结论（已在 F8 独立复核确认）。
  - 建议：改成「**26 份（含本 plan）**」或「25 份（不含本 plan）」，把口径写死 —— 本 plan 的主题就是「登记要说今天的真话」，自己的 baseline 更不能留一个会过期的裸数字。
  - 顺带（**不可修，只登记**）：`.github/workflows/gates.yml:610` 的注释逐字「`tests/tools`（61）· **`tests/routing`（148）** · `tests/context`（51）」，而今天实测 `tests/routing` 是 **179 passed, 1 skipped** ⇒ 那三个数已过期。该文件是红线 2，本 plan **不许碰**；但既然 Phase 3 会让这个数再涨，值得在证据文件里点一句，免得下一个人读注释当真。

**总判：`needs revision`** —— 2 条 blocking（F1 · F2）+ 5 条 should-fix（F3 · F4 · F5 · F6 · F7）处置后可复审。plan 的事实底座扎实、方向正确、红线意识到位；卡住它的是「变异测了个扫不到的文件」和「判据自己留了个洞还打算临场补」这两件事。

---

- Independent draft review iteration 2: needs revision (fresh subagent, 2026-08-26) after 起草者处置了第 1 轮全部 13 条。**逐条复读正文核对（不采信处置说明）：F1/F2/F3/F4/F6/F7/Q1/Q4/Q6/份数 十处已改准；F5 只改好了一半。** 新增取证两项：① **M6 的新预测两半都对，且我把 F1 的推演升级成了实测** —— 在 `/tmp` 隔离副本上把 `agenerp/routing/` 内的 `ChatAdapter` 整体改名后，门禁 `2 passed`（绿）、`pytest tests/routing -q` `2 errors`（红），**判据在类名消失后完全静默**（R6）；② `tests/gates/test_agent_seam_stays_swappable.py` 实点**只有 2 个顶层 `def test_`**，而新的 `A == B` 以**文件**为单位取 `B` ⇒ **表里必须同时登记那条与 routing 无关的循环判据，否则 Phase 3 的判据一落地就红**（R1，`blocking`）。另有 R2–R5 四条 should-fix（`Targets` 没跟上、两条新 `Fix` 无 Exit Criteria、`D1` 仍写「三种形态」、三处计数与新表对不上），R6–R10 为判词与复核结论。

**Iteration 2 Findings**

- **R1 · `blocking` · Phase 2 `Add` 表（`:156`）× Phase 3 `A == B`（`:188-192`）** —— **表的成员规则没定，两处规格互相矛盾，Phase 3 的判据可能一落地就红。**
  - 实测：`grep -c '^def test_' tests/gates/test_agent_seam_stays_swappable.py` → **2**（`:58` `test_agent_loop_lives_in_exactly_one_module` 与 `:87` `test_chat_adapter_is_only_constructed_inside_routing`）。新判据的 `B` 取法逐字是「**表中出现的每一个判据文件里实际存在的全部 `def test_*`**」⇒ **只要该文件出现在表里，那条与 routing 无关的「agent 循环只许一处」判据也必须登记**，否则 `B` 比 `A` 多一个 ⇒ **红**。
  - 而 Phase 2 `:156` 只写「每行四列：判据文件 · 判据函数名 · 盖住的形态 · 明确不盖的形态」，**从没说哪些判据进表**；表名又叫 `routing-guards`。执行者按表名只登记 adapter 那一条，Phase 3 Exit `:208`（`pytest tests/routing -q` → exit 0）**不可达**。
  - 放大风险实点：若表里再纳入 `tests/routing/test_capabilities.py`（**14** 条顶层 `def test_`）或 `tests/unit/test_configured_model_is_the_one_used.py`（**4** 条），`B` 立刻膨胀，这张「判据登记表」会退化成一份**全量测试清单**，第 3/4 列（盖住/不盖的形态）也就没法逐行写实。
  - 判词：**这正是 F2 罚过的那件事的翻版** —— 一个必须在起草期定死的口径被留给执行者临场决定。F2 修好了「断言方向」，没修「集合边界」。
  - 建议（二选一，写进 Phase 2 并在 Phase 3 加一条 `Decision` 记备选与残余风险）：**(a) 文件级纳管** —— 表以文件为单位，「纳管一个文件即纳管其全部 `def test_*`」，并**明确 `tests/gates/test_agent_seam_stays_swappable.py` 的两条都要登记**（循环判据那行照实写它盖的是「第二处 agent 循环」，不硬塞成 routing 语义）；**(b) 前缀/正则纳管** —— `B` 改成「文件内函数名匹配写死正则的 test」，把正则逐字写进判据模块头。**(a) 更简单也更难骗，我倾向 (a)**，但无论选哪个，**必须在 Phase 2 就写死，不能留到执行期。**

- **R2 · `should-fix` · Phase 1 `Targets`（`:99`）与 Phase 2 `Targets`（`:145`）** —— **F5 只修好了一半：动作认领了，`Targets` 没跟上（规则 11）。**
  - 实测：M6 改后要动 `agenerp/routing/adapter.py`（`class ChatAdapter` 在 `:110`）、`agenerp/routing/__init__.py:10,21`、`agenerp/routing/router.py:30,60,90`；M5 还要在 `agenerp/routing/` 内新增一处构造。而 Phase 1 `Targets` 只列 `agenerp/explain/loop.py` 与 `agenerp/routing/router.py`。
  - 实测：Phase 2 新增的两条 `Fix`（`:158` / `:162`）分别动 `docs/masterplan/STATE.md` 与 `docs/backlog/p1-insight-roadmap.md`，而 Phase 2 `Targets` 只列 `docs/architecture/model-management.md`。
  - 这正是 F5 引的先例（`1618-1` 收口审计逐字「该文件**不在 Phase 3 的 `Targets` 列表里**」）罚的形态 —— 同一个坑不该踩第二次。
  - 建议：Phase 1 `Targets` 补 `agenerp/routing/adapter.py` · `agenerp/routing/__init__.py`；Phase 2 `Targets` 补 `docs/masterplan/STATE.md`（**append-only**）· `docs/backlog/p1-insight-roadmap.md`。

- **R3 · `should-fix` · Phase 2 Exit Criteria（`:174-178`）** —— **两条新 `Fix` 没有任何判据。**
  - 实测：Phase 2 的四条 Exit 全部只谈 `model-management.md`；**STATE 追加与 roadmap 追加零 Exit Criteria** ⇒ 收口时判不出这两件事做没做、做对没做对（规则 3 + Anti-Slacking）。
  - 建议补两条，并把红线自证写成**可跑命令**：
    - STATE：`git diff --numstat -- docs/masterplan/STATE.md` **删除列为 0**（`Closure Gates:305` 已有同款，Phase 2 直接引用即可），外加 `grep -c '2026-08-24T08:12Z' docs/masterplan/STATE.md` 只增不减。
    - roadmap：⚠️ **numstat 判不出来** —— `:43` 是**一整行**且以 `）` 结尾，行内追加必然让整行进 diff（`1 1`）。须换**语义判据**，例如改动后 `sed -n '43p' docs/backlog/p1-insight-roadmap.md | grep -c '（P1.1）: `done`'` 仍为 **1**（状态词没被翻），且 `grep -c '既不在 `commands.test`' ` 仍为 1（原句没被改写）。
  - ⚠️ 一并提醒执行者与收口审计：`1618-1` 的收口记录逐字记过「唯一的字符级改动是行尾那个 `）` 被右移」—— 行内追加**必然**产生这一个字符的位移，**那不算改写原句**，不该按它判红。

- **R4 · `should-fix` · `D1` 标题与正文（`:309` / `:313-315`）** —— **仍写「三种形态」，与 Phase 1 `:120-121` 的强制要求矛盾。**
  - 实测矛盾：Phase 1 逐字「M6 若如预测为绿，『判据无存活守卫』就是**第四种不覆盖形态**，须与另外三种一并写进 `routing-guards` 表与 `D1`」；而 `D1` 的 heading 与 `Why Not Blocking Closure` 都只讲三种。重开事件 `:317` 已补「/ 补存活守卫」⇒ **起草者改了一半。**
  - 且那个「若」现在已经不成立 —— **我实测确认 M6 必为绿**（R6），第四种形态**一定**会成立，不是条件句。
  - 建议：`D1` 标题改成「四种形态（别名导入 / 属性式构造 / `agenerp/` 之外的调用方 / **判据无存活守卫**）」，正文点名「类名一改即永久静默绿」，并注明这一条由 Phase 1 M6 实测坐实。
  - **附判词（重点拷问 4）：存活守卫缺失不是被降级的在线缺陷。** (a) `ChatAdapter` 今天存在、判据今天确实在检查东西 ⇒ 是**潜伏空转风险**，不是规则 14 说的「confirmed live defect」；(b) 补守卫必须改 `tests/gates/**` —— `docs/masterplan/01-EXECUTION-MODEL.md:14` 逐字「① 改 `tests/gates/**`（**触碰即停机**）」。⇒ `watch-only residual` + `Successor Required: yes（人）` 是正确处置。

- **R5 · `should-fix` · 三处计数/措辞与新表对不上（规则 11 文本一致性）。**
  - `:201` 逐字「变异自查**三条**」，后面列的是 **N1 · N2 · N3 · N4 四条**。
  - `:209` Exit 逐字「**三条**变异逐条有：预测 · 实测 · 退出码 · `RESTORED OK`」同错；且尾句「不吻合的照实记**并说明补了什么**」是旧 N1「预测绿 → 当场补断言」的**残留措辞** —— 新设计里已经没有「补」这一步，留着会诱导执行者把设计决定重新推回执行期，**正是 F2 判过的病**。
  - `:135` Phase 1 Exit 逐字「**六条**变异各有：命令原文 + 退出码 + **复原后的 `sha256` 比对结果（`RESTORED OK`）**」—— 但 **M4 已改成零施加**（`:112`），没有施加也就没有复原，凑不出 `RESTORED OK`。
  - 建议：`:201`/`:209` 改「四条」，`:209` 尾句改成「不吻合的照实记，并说明实测与预测差在哪 —— **不在执行期改判据设计**」；`:135` 改成「M1/M2/M3/M5/M6 五条各有 … `RESTORED OK`；**M4 为零施加**，只记命令原文 + 退出码 + 被观测文件 `tools/experiments/p1_insight_live/run.py` 的 `sha256` 前后未变」。

- **R6 · `nit`（复核结论，非 finding）· 重点拷问 1：M6 的新预测两半都对，且我把 F1 的推演升级成了实测。**
  - 方法（**未碰活仓一个字节**）：把 `agenerp/` 与该门禁文件复制到 `/tmp/m6replica`（门禁 `_REPO_ROOT = parents[2]` 使副本自洽），`sed` 把 `agenerp/routing/` 内出现的 `ChatAdapter` 整体改名为 `ChatSeamXX` —— 实点全中 `adapter.py:110` 的 `class`、`__init__.py:10,21`、`router.py:30,60,90`。
  - 结果 ①：`python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` → **`2 passed`（绿）**。⇒ **`offenders` 恒空，判据在类名消失后完全静默** —— F1 指出的空转风险**由推演变成实测**，Phase 1 `:116-121` 的说法成立。
  - 结果 ②：`python3 -m pytest tests/routing -q` → **`2 errors in 0.14s`（红）**，红在 `tests/routing/test_adapter.py` 与 `test_router.py` 的 **collection 阶段** ImportError。
  - ⚠️ 给执行者两点预先提醒（写进预测更诚实）：**① 红的形态是 collection error，不是断言失败** —— 证据文件里照实记这个形态；**② M6 会连带打断 `agenerp/explain/loop.py:53` 的 `from agenerp.routing.adapter import ChatAdapter`**（该行在 `agenerp/routing/` 之外，不在改名范围内）⇒ `tests/unit` 同样会红。这不是意外，预测里写上。

- **R7 · `nit` · 重点拷问 2：`A == B` 的剩余洞 —— 第 3、4 列没有任何判据钉着。**
  - `A == B` 钉的是「文件 + 函数名」，而**本 plan 真正在修的漂移恰恰发生在「盖住什么 / 不盖什么」这种散文断言上**。判据模块头的自我声明（`:197-199`「本条只验存在性同构，不验语义」）**正确且必要**，但它是免责不是防线：今天这场漂移若发生在第 3/4 列，新判据照样全绿。
  - 建议：`routing-guards` 表加一列「**实测日期 + 证据路径**」（指向 `docs/evidence/p1-routing-guard-registration/`），让读者一眼看出这条覆盖断言有多老；并在 `D1` 里把「第 3/4 列不被任何判据钉住」登记为已知残余。
  - 另两个够不上改设计、写进判据模块头即可的小口子：**(i)** `def test_*` 的取法要写死是**顶层函数**（实测 `tests/routing/**` 与该门禁文件今天**零 class-based、零嵌套 test**，现状安全，但口径要写死，否则将来有人用 `class TestX` 就会静默漏掉）；**(ii)** `A == B` 钉的是**一致性不是相关性** —— 表里换成一个不相干的文件，只要两边对得上仍绿。

- **R8 · `nit` · Phase 2 的 `Decision`（`:166-170`）现在需要限定作用域。**
  - 它逐字「选**就地改写**」，而同一个 Phase 的另两条 `Fix` 用的是**追加**（STATE 因红线 5、roadmap 因本仓惯例）。收口审计读到「选就地改写」再看到两处追加，会判自相矛盾。
  - 建议补一句：「本裁定**只管 §12.5 那一段**；`STATE.md` 与 `docs/backlog/p1-insight-roadmap.md` 两处用追加，**那不是本裁定的选择结果，是红线与惯例决定的**。」

- **R9 · `nit`（判词）· 重点拷问 4：`D1` / `D2` / `D3` 三条都不是把在范围的东西降级。**
  - `D3` 的两处引证我逐条复核**属实**：`missions/p1-insight.json:16` 逐字 `"test": "python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q"` ✓；`docs/masterplan/01-EXECUTION-MODEL.md:14` 逐字「**禁止** … ③ 改 `missions/*.json`」✓。三要素齐（分类 / 不阻塞理由 / 具名重开事件），且诚实自标「**本条是登记，不是发现了一个新坑**」。
  - 判词：**D1** 与 **D3** 的处置面都**在红线内**（`tests/gates/**` / `missions/**`，`01-EXECUTION-MODEL.md:14` 禁止项 ①③），**D2** 是一次新的产品裁定（归人，D-22 接缝面）⇒ 三条都属「不在本 plan 结果面上」，不是降级。规则 14 与 Anti-Slacking 均满足（每条都有具名重开事件，无 `optional`/`consider`/`if time permits` 类措辞 —— 我全文扫过，零命中）。
  - ⚠️ 唯一遗留：`Closure Gates:299` 的 `scoped verification` 那条仍只提整仓 `-m "not live"` 基线红，**没把 `D3` 那件事（新判据进 CI 不进 `GATE_VERIFY`）写进去**。收口时那一格要勾，建议在括号里一并点名。

- **R10 · `nit`（判词）· 重点拷问 3：处置没有引入新的红线风险。**
  - 逐条实点：Phase 2 新增两条 `Fix` 分别动 **`docs/masterplan/STATE.md`**（红线 4，只许追加 —— 执行项 `:158` 逐字「**只追加，零删除，红线 5**」，且 `Closure Gates:305` 已有 `git diff --numstat -- docs/masterplan/STATE.md` 删除列为 0 的自证 ✓）与 **`docs/backlog/p1-insight-roadmap.md`**（实测**不在**任何红线清单里：既不属 `docs/masterplan/**`，也不在 `:305` 的自证路径列中 ✓）。
  - Non-Goals 6 `:79-80` 现已写明完整路径与「行首那个 `` `done` ``」；实测 `sed -n '43p' docs/backlog/p1-insight-roadmap.md` 首段逐字 `- 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）: `done`（2026-08-24，sha `5a0f87a`；…` ⇒ 指向准确 ✓。
  - M4 已改零施加 ⇒ `tools/` 下不再新建文件 ✓；Phase 1 Exit `:136-137` 的 `git status --porcelain -- agenerp/ tools/ tests/` 与「不许 `git checkout -- .` 兜底」已按 F6 落实 ✓。
  - M6 的施加面全部在 `agenerp/routing/**` 与 `agenerp/`，**不碰 `tests/gates/**`** ✓（我自己做实测时也是在 `/tmp` 副本上做的，活仓 `git status` 除本 plan 文件外零改动）。

- **R11 · `nit`（复核结论）· 第 1 轮十处处置逐条核对属实。**
  - `F1`→M6 改成整体改类名 + `:116-124` 写明存活守卫缺失且**照实留下原起草版的错法与更正** ✓ · `F2`→`:188-195` 双向同构 `A == B` 起草期写死、N1 预测改红、加了 N4 ✓ · `F3`→M4 零施加 + Baseline `:40-42` 点名 `tools/experiments/p1_insight_live/run.py:159` + `D1` 重开事件 `:318-321` 已删掉「实测出现一次真实的逃逸构造」并改成「在 `agenerp/**` 产品代码内」✓ · `F4`→Phase 2 `:158-161` 新增 STATE 追加 `Fix` ✓ · `F5`→**只好一半**（见 R2/R3）· `F6`→`:136-137` ✓ · `F7`→Baseline `:46-48` + `D3` ✓ · `Q1`→表头 `:8-9` 补 `STATE.md:1543` 的前身说明且判词准确 ✓ · `Q4`→Non-Goals 3 `:73-75` 点名 `test_answer_judge.py:275-279` 并写明「差别是**红线**，不是**要不要修**」✓ · `Q6`→Non-Goals 6 `:79` 写明路径、Phase 3 Exit `:211-213` 把「仍是 29 项」改成明标恒真的旁证 ✓ · 份数→Baseline `:36` 改成「起草时 25 份，本 plan 落盘后 26 份」✓。

**iteration 2 总判：`needs revision`** —— 1 条 `blocking`（R1：表的成员规则未定，按表名只登记 adapter 一条会让 Phase 3 判据**一落地就红**，且逼执行者临场做一次设计决定 —— 与 F2 同病）+ 4 条 `should-fix`（R2 `Targets` 没跟上 · R3 两条新 `Fix` 无 Exit Criteria · R4 `D1` 仍写「三种形态」· R5 三处计数与措辞残留）。**方向与事实底座这一轮更硬了**：M6 从「测了个扫不到的文件」变成一条**我实测坐实的、真能揭示判据静默失效的变异**，双向同构也把 F2 那个洞堵上了。剩下的全是**边界与记账**问题，改完即可执行。

---

- Independent draft review iteration 3: needs revision (fresh subagent, 2026-08-26) after 起草者处置了第 2 轮全部 11 条。**逐条复读正文核对（不采信处置说明）：R1–R7 七条全部落到正文且落得准确**（见 `S10`）。**`R1` 那条 blocking 已解除** —— 我把 `A == B` 按正文 `:210` 的逐字口径做成原型跑过：两条都登记 → **GREEN**，只登记 adapter 一条 → **RED**，确认口径已定死、Phase 3 落地后 `pytest tests/routing -q` 会绿（`S7` 给确定判词）。**但同一次原型跑出一条新的 `blocking`**：`N4`「整表删空」按正文写死的 `B` 取法**实测是 GREEN，不是红**，而 `:212` 逐字预测「红」—— 这条判据在表被清空时**静默通过**，正是它自己在 `D1` 里登记的「无存活守卫」那个病，且**第 1 轮草案原本有的「空表不许绿」在 `F2` 处置中被丢掉了**，属回归（`S1`）。另有 `S2`–`S4` 三条 should-fix 与 `S5`–`S6` 两条遗留 nit。

**Iteration 3 Findings**

- **S1 · `blocking` · Phase 3 `:210-212` 的 `B` 取法 × N4（`:223`）** —— **「表为空 → 红」是错的，实测为绿；新判据在表被清空时静默通过。**
  - 实测（按正文 `:210` 逐字口径做原型，读活仓真文件）：
    | 变异 | 正文 `:210` 逐字口径实测 | 正文 `:211-212` 的预测 |
    |---|---|---|
    | baseline（两条都登记） | **GREEN** | 绿 ✓ |
    | N1 删一行 | **RED**（`B-A = {test_chat_adapter_is_only_constructed_inside_routing}`） | 红 ✓ |
    | N2 函数名改一个字 | **RED** | 红 ✓ |
    | N3 文件路径改一个字 | **RED**（文件读不到） | 红 ✓ |
    | **N4 整表删空** | **GREEN** ❌ | 红 ✗ **对不上** |
  - 根因（正文自相矛盾）：`:210` 逐字「`B` = **表中出现的每一个判据文件**里实际存在的全部 `def test_*`」⇒ **`B` 由 `A` 的文件集合导出**。表清空 ⇒ 没有文件 ⇒ `B = ∅ = A` ⇒ `A == B` 成立 ⇒ **绿**。而 `:212` 逐字写「表为空 → `A` 为空而 **`B` 非空**」—— `B` 只有在文件集合**独立于表**被钉住时才可能非空，正文没有这么钉。
  - 严重性：**这正是本 plan 在 `D1` 里登记的第四种形态（判据无存活守卫）在新判据上的重演** —— 一条「登记表被整个删掉也不报警」的判据，恰恰守不住本 plan 的 Goal 3。而且这是**回归**：第 1 轮草案原文逐字有「并断言表**非空**（空表不许绿）」，`F2` 处置换成 `A == B` 时把它丢了。
  - 建议（我已把改法原型跑通，四条变异全部如预期）：把**纳管文件集合写死进判据模块**，`B` 不再由表导出 ——
    `_REGISTERED_FILES = {"tests/gates/test_agent_seam_stays_swappable.py"}`；`B` = 该常量集合内各文件的全部顶层 `def test_*`；
    再加两句：**① 存活守卫 `assert A, "routing-guards 表为空 —— 判据静默失效"`；② `assert {f for f,_ in A} <= _REGISTERED_FILES`（表里出现未纳管文件即红）。**
    实测结果：`N4 整表删空 → RED（表为空 —— 存活守卫）`、`N3 → RED（表里出现未纳管文件）`，其余三条与现口径完全一致。
    **额外好处**：`Decision`（`:170`）逐字写的「本期表里只纳管那一个文件，要纳管第二个必须先重开这条 `Decision`」目前**只是散文**；写成 `_REGISTERED_FILES` 常量后它变成**机器执行的约束** —— 想加第二个文件必须改那行常量，而改常量会逼人正面回答「为什么」，与 `tests/gates/` 里 `_ALLOWED_LOOP` 的执法套路同构（该文件 `:43-45` 逐字就是这个理由）。
  - 顺带把 N4 的预测改准，或直接把 N4 改成「整表删空 → 红（**由存活守卫捕获**，不是由 `A == B` 捕获）」，把捕获者写清楚。

- **S2 · `should-fix` · Phase 2 Exit（`:191-194`）的 roadmap 语义判据** —— **方向对了，但守得不够，且「原句片段」没点名。**（重点拷问 2 的判词）
  - 实测：`docs/backlog/p1-insight-roadmap.md:43` 长 **1066 字符**。现写法「改动后该行仍逐字包含原句（`grep -c` 原句片段 == 1）且状态词仍是 `` `done` ``」**只守住被点名的那个片段**；这 1066 字符里的其余任何一处被悄悄改写，两条 `grep` 都照样过。
  - 而且**片段没点名** —— 正文只写「原句片段」，执行者自己挑。我实跑演示过两种挑法的差别：挑中被改的那句（`既不在 `commands.test` 也不在任何 CI job 里`）时能捕获「改写原句」；挑成别处（如 `sha `5a0f87a``）时，同一次改写**照样绿**。
  - 建议（我已实跑验证，三种形态全部判对）：改成**子串不变式** —— 编辑前先存下该行 `old`，取 `core = old.rstrip()[:-1]`（**去掉行尾那个 `）`**），编辑后断言 `core in new_line`。实测：
    `行内追加(合法)` → **PASS** · `改写原句` → **FAIL（红）** · `翻状态词` → **FAIL（红）**。
    一条不变式同时覆盖「原句任意处被改写」与「状态词被翻」两个失败形态，且**天然容纳** `1618-1` 先例里那个「行尾 `）` 右移一个字符」的合法位移 —— 现写法里那句给收口审计的提醒（`:194`）也就不再是口头约定，而是判据本身的定义。
  - 若坚持用 `grep` 版，**至少把片段逐字写死在 Exit 里**，别留给执行期挑。另建议 Exit 别把行号 `:43` 写死（改用工作项前缀定位），否则 roadmap 上方一旦插行，判据就指错行。

- **S3 · `should-fix` · Phase 2 `:162-163` 第 5 列 × Phase 3 `A == B`** —— **第 5 列的证据路径「存不存在」是本 plan 范围内、零成本就能钉住的，现在一点没钉。**（重点拷问 3 的一半）
  - 实测：`A` 只取第 1、2 列，第 3/4/5 列**全部不进任何断言**。`D1` 自陈「第 5 列是**缓解，不是判据**」——**这句话只对了一半**：第 3/4 列（散文）确实钉不住，但第 5 列里的**证据路径是一个可判定的对象**，`Path(...).exists()` 一行就能钉。
  - 后果：今天写 `docs/evidence/p1-routing-guard-registration/`，将来目录被删/改名，表里那条「实测日期 + 证据路径」变成一条**指向虚空的可信度背书**，而判据全绿。这与本 plan 要修的病同形。
  - 建议：新判据加一条断言「第 5 列里的证据路径必须存在」（并可顺带断言日期字段能被 `date` 解析）。**这不是扩范围** —— 它就在 Phase 3 已经要写的那个文件里，是同一条 `Add` 项的一句话。
  - ⚠️ 但 `D1` 里「要真钉住第 3/4 列只能靠**周期性重跑变异表** ⇒ 一格新预算（归人）」这条判词我**认可，不判 blocking**：那是一个**反复执行的机制**（每次重跑都要人重新看结论、判断覆盖有没有变），不是一次性交付物；规则 14 管的是「确认的活缺陷 / 契约漂移 / owner-doc 漂移 / 已修的 CI-lint 规则」，第 3/4 列**在 Phase 1 实测当天是真的**，不属其中任何一类。`watch-only residual` + `Successor Required: yes（人）` 是正确处置。**只有 S3 那一句是被误划出去的，那一句必须收回范围内。**

- **S4 · `should-fix` · Phase 2 `- Item Types:`（`:155`）** —— **仍逐字写 `Fix`，与本 Phase 现在的实际构成不符（规则 7 + 规则 11）。**
  - 实测：Phase 2 现有 **6 个执行项** —— `Fix`×4、`Decision | Add`×1（`:162`）、`Decision`×1（`:180`）⇒ `Fix` 占 **4/6 = 67%**，**够不上规则 7 逐字的「80%+ 才可在 phase 级声明统一类型」**。
  - 建议：把 `:155` 改成 `- Item Types: `Fix | Decision | Add`（4/6 为 `Fix`）`，或删掉 phase 级声明只留逐项标注（逐项标注今天已经齐全）。

- **S5 · `nit` · Phase 2 `Targets`（`:151`）把 `docs/masterplan/STATE.md` 列进来 —— 合规，但要先堵住一条会被收口审计误判的引证。**（重点拷问 5）
  - 实测：**合规**。`AGENTS.md:14`（红线 5）逐字「**不得改动 `docs/masterplan/` 下的其余文件**（loop 侧只读；**`STATE.md` 只允许追加证据行**，不得改写已有行）」⇒ 追加被明文许可；`AGENTS.md:3-4` 逐字「本文件前两节是红线与裁判规则，**优先于** … `docs/masterplan/` 的执行协议」⇒ 优先级也写死了；仓里先例满地（`STATE.md:758` / `:773` / `:781` / `:789` 逐字「**本行只追加，不改写本节任何已有行（红线 5）**」）。
  - ⚠️ 但 `D3` 引的是 `docs/masterplan/01-EXECUTION-MODEL.md:14`（禁止项 ③ `改 missions/*.json`），而**紧挨着的 `:15`「状态写权」那一行逐字写着角色 B「不得手写 STATE」** —— 一个照着 `D3` 的引证顺藤读下去的收口审计者，会在同一张表里读到一句看似禁止 Phase 2 那条 `Fix` 的话。
  - 建议：在 Phase 2 那条 `Fix`（`:172`）或 `D3` 里补一句，把优先级点明：「`01-EXECUTION-MODEL.md:15` 的『不得手写 STATE』被 `AGENTS.md:14` 红线 5 的括号（`STATE.md` 只允许追加证据行）**更具体地限定**，且 `AGENTS.md:3-4` 逐字规定红线优先于 `docs/masterplan/` 的执行协议；仓内先例见 `STATE.md:758/773/781/789`。」**一句话，省掉收口时的一次争议。**

- **S6 · `nit` · 两条第 2 轮遗留项本轮未处置（不阻塞，但记在这里免得掉）。**
  - `R8`：Phase 2 的 `Decision`（`:180`）仍逐字「选**就地改写**」，而同 Phase 另两条 `Fix` 用的是**追加**。建议补一句「本裁定**只管 §12.5 那一段**；`STATE.md` 与 roadmap 两处用追加，是红线与惯例决定的，不是本裁定的选择结果」。
  - `R9` 遗留半条：`Closure Gates` 的 `scoped verification` 那条（现 `:388`）仍只提整仓 `-m "not live"` 基线红，**没点名 `D3`**（新判据进 CI 不进 `GATE_VERIFY`）。建议在括号里一并写上。

- **S7 · `nit`（判词）· 重点拷问 1：`R1` 的处置**已经把口径定死，Phase 3 落地后 `pytest tests/routing -q` **会绿。**
  - 实测（按正文 `:164-166` 的 (a) 文件级纳管 + `:210` 的 `A == B` 做原型，读活仓真文件）：**两条都登记 → GREEN**；**只登记 adapter 一条 → RED**（`B-A = {test_agent_loop_lives_in_exactly_one_module}`）。⇒ `R1` 指出的「按表名只登记一条会一落地就红」确实成立，而正文 `:165-166` 逐字点名两条函数名 + 「循环那条照实写它盖的是『第二处 agent 循环』，不硬塞成 routing 语义」+ 表名含义写进前言，**三处一起把口径钉死了**。备选 (b) 正则纳管的否决理由（「正则会变成第二个可以被悄悄放松的旋钮」）写得准确，符合规则 9。
  - ⚠️ 唯一前提：`S1` 必须先修 —— 现口径在「表被清空」这一格上是绿的。

- **S8 · `nit`（判词）· 重点拷问 4：文本一致性再扫（规则 11/12）。**
  - 已核对一致：Phase 1「下表**六行**」= M1–M6 六行 ✓ · Phase 1 Exit「M1/M2/M3/M5/M6 **五条** + M4 零施加无 `RESTORED OK`」✓ · Phase 3「**四条**」两处（`:221` / `:229`）✓ · `D1` 标题与正文「**四种**形态」✓ · Non-Goals 3 枚举同步为四种（`:70`）✓ · Phase 1 `Targets` 已去 `router.py`、补 `adapter.py` + `__init__.py`、标注 `tools/experiments/...` 只读零施加 ✓ · Phase 2 `Targets` 已补两份台账并各自标注约束 ✓ · Phase 2 Exit 已补两条 ✓ · Phase 3 Exit 尾句旧残留措辞已改 ✓ · 表列数「**五**列」在 `:162` 与 `D1` 的自陈里一致 ✓。
  - 仍对不上的两处：**① `:212` 的 N4 预测（`S1`，blocking）**；**② `:155` 的 `Item Types`（`S4`）**。
  - 规则 12 机检：`grep -B5 "\- \[ \]" <plan> | grep "Status: completed"` → **空** ✓（三个 Phase 均 `planned`，与 `Plan Status: draft` 一致）。
  - Anti-Slacking 禁用词全文扫描：`optional` / `if time permits` / `consider` / `maybe` / `nice to have` / `as needed` 在**执行项与 Deferred 条目中零命中** ✓。

- **S9 · `nit`（判词）· 重点拷问 5：处置未引入新的红线风险。**
  - Phase 1 `Targets` 新增的两份都在 `agenerp/routing/`（产品源码，不在任何红线内）✓；`router.py` 移出 Targets 与 M6 的新施加面一致 ✓；M4 明标只读零施加 ⇒ `tools/` 不新建也不改文件 ✓。
  - Phase 2 新增的两份台账：`docs/masterplan/STATE.md` 见 `S5`（合规，建议补一句引证）；`docs/backlog/p1-insight-roadmap.md` **实测不在任何红线清单内**（既非 `docs/masterplan/**`，也不在 `Closure Gates` 红线自证的路径列里）✓。
  - `Closure Gates` 的红线自证（`:394`）仍覆盖 `tests/gates/ .github/workflows/ DECISIONS.md 02-WBS.md missions/ …` 且对 `STATE.md` 要求删除列为 0 ✓ —— 与 Phase 2 新增的两条 `Fix` 不冲突。
  - 我本轮的全部实测都在 `/tmp` 上做（原型脚本 + 子串不变式演示），**活仓 `git status` 除本 plan 文件外零改动** ✓。

- **S10 · `nit`（复核结论）· 第 2 轮 R1–R7 逐条核对属实。**
  - `R1`→`:162-170` 改成 `Decision | Add`、(a) 文件级纳管写死、逐字点名两条函数名与「不硬塞 routing 语义」、(b) 正则纳管逐字否决、残余风险点名 14 条 / 4 条实点数并写死「纳管第二个文件必须先重开这条 `Decision`」✓ · `R2`→Phase 1/2 `Targets` 均已改准 ✓ · `R3`→Phase 2 Exit 补两条，roadmap 那条确已改成语义判据并写进「行尾 `）` 右移不算改写」的提醒 ✓（强度不足见 `S2`）· `R4`→`D1` 标题正文四种形态 + 点名「类名一改即永久静默绿」+ 注明由 M6 实测坐实，Non-Goals 3 同步 ✓ · `R5`→三处计数与措辞全部改准 ✓ · `R6`→`:122-126` 条件句已删，改成「第 2 轮评审已在隔离副本实测…**执行期仍须在活仓复现并复原**，采信隔离副本而不自己复跑正是本仓禁止的自报」，并写进 collection ImportError 与 `loop.py:53` 导入被打断两点 ✓ · `R7`→第 5 列已加，`D1` 自陈第 3/4 列无判据、第 5 列是缓解不是判据 ✓（那句自陈只对了一半，见 `S3`）。

**iteration 3 总判：`needs revision`** —— 1 条 `blocking`（`S1`：`N4 整表删空` 实测**绿**而正文预测**红**，新判据在表被清空时静默通过；且这是第 1 轮草案本来有过的「空表不许绿」在 `F2` 处置中的**回归**）+ 3 条 `should-fix`（`S2` roadmap 判据守不住任意改写且片段未点名 · `S3` 第 5 列的证据路径本可零成本钉住却被划成残余 · `S4` `Item Types` 与实际构成不符）+ 2 条遗留 nit。**上一轮的 blocking（`R1`）已由原型实跑确认解除**，本轮的 blocking 是把同一套双向同构口径**再往下推一格**才暴露出来的 —— 修法我已原型跑通（写死 `_REGISTERED_FILES` + 两句守卫，四条变异全部如预期），**改动量约五行，改完即可执行。**

---

- Independent draft review iteration 4: accept as-is (fresh subagent, 2026-08-26) after 起草者处置了第 3 轮全部 10 条。**本轮唯一的验收点（`S1` 有没有真堵住 N4）通过：我按今天正文 `:222-234` 的五句断言重做原型、跑活仓真文件，N1–N5 五条与正文预测逐条吻合，捕获者也逐条对上**（`T1` 附实测表）。`S2`–`S6` 五条处置逐条复读属实（`T5`）。**无 blocking，无新引入的红线风险**（`T5`）。余下 `T2`–`T4` 共 4 条是**执行前的一次性打磨**（日期格式未写死 · 子串不变式的三处写歪风险 · Non-Goals 1 与 owner-doc 施加面对不上 · 我自己第 3 轮给错的一个数字），**都不改变交付形状，也不影响任何一条已写死的判据设计** —— 起草者顺手改掉即可，不需要第 5 轮评审来放行。

**Iteration 4 Findings**

- **T1 · `nit`（判词，本轮唯一验收点）· 重点拷问 1：`S1` 已堵住，五条逐条吻合。**
  - 方法：按正文 `:222-234` 的五句断言（① `_REGISTERED_FILES` 常量 · ② `B` 由常量导出的顶层 `def test_*` 且 `A == B` · ③ `assert A` 存活守卫 · ④ `{f for f,_ in A} <= _REGISTERED_FILES` · ⑤ 第 5 列证据路径存在 + 日期可解析）重做原型，读活仓真文件，**未碰活仓一个字节**。

    | 变异 | 正文预测（含捕获者） | 我的实测 | 吻合 |
    |---|---|---|---|
    | baseline 两行都登记 | 绿 | GREEN（见下 `T2`(a) 的时序说明） | ✓ |
    | N1 删表里一行 | 红 ② | `RED ② B-A={test_chat_adapter_is_only_constructed_inside_routing}` | ✓ |
    | N2 函数名改一个字 | 红 ② | `RED ② A-B={…routinX} B-A={…routing}` | ✓ |
    | N3 文件路径改一个字 | 红 ④ | `RED ④ 表里出现未纳管文件 [tests/gates/…swappableX.py]` | ✓ |
    | **N4 整表删空** | **红 ③** | **`RED ③ 表为空 —— 判据静默失效`** | ✓ **（上一版此格为 GREEN）** |
    | N5 证据路径改成不存在的目录 | 红 ⑤ | `RED ⑤ 证据路径不存在：…/NOPE-does-not-exist/` | ✓ |

  - ⇒ **`S1` 那条 blocking 解除**：`B` 已与表解耦，表被清空时由 ③ 打红，不再静默通过。**「每条写明由哪一句断言捕获」这个要求也验证过是有意义的** —— N3 若不点名捕获者，会被误读成「`A == B` 抓到了」，实际抓它的是 ④。
  - **额外验证一条起草者没写、但我预判会被质疑的事**：正文用「正则会变成第二个可以被悄悄放松的旋钮」否决了备选 (b)，那么 `_REGISTERED_FILES` 自己是不是同一个旋钮？**实测不是** —— 把该常量清空后跑 baseline → `RED ④ 表里出现未纳管文件`。**③ 与 ④ 互相咬住，使这个常量无法被悄悄放松成空**（只能被显式换成另一个文件，而那要同时改常量与表两处，diff 上藏不住）。这条值得补进 `Decision` 的否决理由里，把 (b) 的否决从「感觉更难骗」升级成「实测更难骗」。

- **T2 · `should-fix`（执行前打磨，不阻塞）· 断言 ⑤（`:227`）· 重点拷问 2 的答案。**
  - **(a) Phase 顺序成立，⑤ 不会因时序假红 —— 已实测确认。** `docs/evidence/` 今天已存在且**被 git 跟踪**（`git ls-files docs/evidence` 非空）、**未被 `.gitignore` 忽略**（`git check-ignore` 无命中）⇒ CI checkout 后目录会在。Phase 1 Exit（`:147`）已要求 `docs/evidence/p1-routing-guard-registration/README.md` 落盘，Phase 2 写表，Phase 3 才加判据 ⇒ ⑤ 跑时目录必已存在。**我的原型今天（Phase 1 尚未跑）对 baseline 得到 `RED ⑤ 证据路径不存在` —— 那正是这条时序依赖的证据，不是缺陷。**
  - **(b) 会真写歪的一处：⑤ 的「日期字段可被解析」没写格式。** 建议逐字写死 `YYYY-MM-DD` + `datetime.date.fromisoformat`（我的原型即用此，`2026-08-26` 通过）。不写死的话，执行者写成 `2026-08-26T20:55Z` 或 `08-26` 都可能让判据在自己落地那天就红，或者反过来把解析写得极宽等于没验。
  - **(c) 第 5 列的路径字符串必须与 Phase 1 的落盘路径逐字节一致。** 今天正文两处（`:147` 的 `docs/evidence/p1-routing-guard-registration/README.md` 与 `:165` 的 `docs/evidence/p1-routing-guard-registration/`）**已经一致 ✓**，但建议在 ⑤ 里点明「以 Phase 1 Exit 那个路径为准」，免得执行期两处各写各的。
  - **(d) `D1` 里「第 5 列已被钉住」是一处轻微 over-claim。** ⑤ 钉住的是**路径存在性 + 日期可解析性**，**没有也无法钉住「日期是否新鲜」**。建议改成这个精确说法 —— 本 plan 通篇在反 over-claim，自己这句不该留半分。

- **T3 · `should-fix`（执行前打磨，不阻塞）· Phase 2 Exit 的子串不变式（`:200-206`）· 重点拷问 3 的答案：会写歪，有三处。**
  - **(a) `old.rstrip()[:-1]` 无条件砍掉最后一个字符。** 今天那行确实以 `）` 结尾（实测 ✓），但判据里没有任何一句保证这一点。若将来行尾不是 `）`，`[:-1]` 会**静默砍掉一个真字符**，而 `core in new_line` 仍可能成立 ⇒ 判据静默放松。**必须先 `assert old.rstrip().endswith("）")`。**
  - **(b) `old` 的来源建议从「执行者手工存」改成「从 git 取」。** 正文逐字写的是「编辑前存下该行 `old`」——**语义是对的**，但它把判据的有效性绑在「执行者当时记得先存」这一个人工动作上，**收口审计无法独立复跑**。建议改成 `git show HEAD:docs/backlog/p1-insight-roadmap.md`，按工作项前缀 `- 3. 模型路由 v0` 定位。**我实跑验证过可行**：HEAD 里按该前缀**恰好命中 1 行**、以 `）` 结尾、其 `core` 是今天工作树全文的子串 ⇒ 改完之后**任何人任何时候都能独立复跑这条判据**，不依赖执行者当时存没存对。
  - **(c) `core in new_line` 隐含一条没写出来的约束：「追加必须在行内、不得换行」。** 建议改成 `core in new_text`（对**全文**判子串）：合法的行内追加照样过；任何把 `core` 从中间劈开的写法照样红；但不再把一条未言明的格式约束塞进判据。
  - **(d) 更正一个我自己第 3 轮给错的数字（照实记，不抹）**：正文 `:201` 与我第 3 轮的 `S2` 都写「该行实测长 **1066 字符**」。**实际是 1066 字节 / 701 字符** —— `awk length()` 在本机按字节数、Python `len()` 按字符数，那行满是 CJK。**论点完全不受影响**（那仍是一行很长的文本，片段式 `grep` 仍然守不住它），但本 plan 的主题就是「登记要说今天的真话」，自己引的数字更该写准。建议两处都改成「**1066 字节 ≈ 701 字符**」。

- **T4 · `nit` · Non-Goals 1（`:69`）与 Phase 3 的变异施加面对不上（规则 11）。**
  - 实测：Non-Goals 1 逐字「变异只施加在**产品源码**与本 plan 自己新增的文件上」，而 Phase 3 的 `Proof`（`:243`）逐字「全部施加在本 plan 自己新增的文件**与 owner doc** 上」，N1–N5 全部落在 `docs/architecture/model-management.md` —— 它**既不是产品源码，也不是本 plan 新增的文件**。
  - Phase 3 `Targets`（`:216`）已经把 owner doc 补进去了 ✓，**只差 Non-Goals 这一处措辞**。建议补成「产品源码 / owner doc / 本 plan 自己新增的文件」。
  - 顺带（更小）：Phase 1 有 `git status --porcelain -- agenerp/ tools/ tests/` → 零行 的复原自证（`:144`），**Phase 3 没有对称的一条**。N1–N5 改的是 owner doc，建议补一条 `git status --porcelain -- docs/architecture/` → 零行，与 Phase 1 同口径。

- **T5 · `nit`（复核结论）· 重点拷问 4 与 5：第 3 轮处置逐条属实；一致性、Anti-Slacking、红线三扫全过；无新引入的问题。**
  - **`S2`–`S6` 逐条核对**：`S2`→Phase 2 Exit 已换成子串不变式，且把旧 `grep` 写法**为什么不够**（长度 / 片段没点名 / 挑成 `` sha `5a0f87a` `` 照样绿）连同三格实测一并留在正文 ✓（强度问题见 `T3`）· `S3`→断言 ⑤ 已收回范围内，`D1` 改成「留在本条里的只有第 3/4 列」并逐字采纳「周期性重跑是反复执行的机制、不落规则 14 四类」的判词 ✓（精度见 `T2`(d)）· `S4`→`:157` 已改 `Fix | Decision | Add` 并注明 `4/6 = 67%` 够不上 80% 门槛、以逐项标注为准 ✓ · `S5`→`:180-185` 已把优先级写进那条 `Fix` 本身（`AGENTS.md:14` 红线 5 的括号是更具体的限定 · `AGENTS.md:3-4` 红线优先 · 先例 `STATE.md:758/773/781/789`）✓ · `S6/R8`→`:187-189` 已限定「本裁定只管 §12.5 那一段」✓ · `S6/R9`→`Closure Gates` 的 scoped-verification 已点名 `D3` 并写明「**`GATE_VERIFY` 退 0 不等于这条判据被跑过**」✓ · 顺带那条→`Current Baseline:36` 已补第四条并标「不是假设，是已实测」，与 Phase 1 / Non-Goals 3 / `D1` 的「四种形态」三处对齐 ✓。
  - **计数一致性（规则 11）全过**：Phase 1「下表**六行**」= M1–M6 ✓ · Phase 1 Exit「M1/M2/M3/M5/M6 **五条** + M4 零施加无 `RESTORED OK`」✓ · Phase 3「**五条**」两处（`:243` / `:253`）✓ · 表「**五**列」与断言 ⑤ 的「第 5 列」一致 ✓ · 「**四种**形态」在 Non-Goals 3 / Phase 1 `:123` / `D1` 标题三处一致 ✓。
  - **规则 12 机检**：`grep -B5 "\- \[ \]" <plan> | grep "Status: completed"` → **空** ✓；三个 Phase 均 `Status: planned`，与 `> Plan Status: draft` 一致 ✓（本轮判 accept 后即可改 `active`）。
  - **Anti-Slacking**：在执行项与 `Deferred But Adjudicated` 范围内扫 `optional` / `if time permits` / `consider` / `maybe` / `nice to have` / `as needed` → **零命中** ✓；`D1`/`D2`/`D3` 三条各有 `Classification` + `Why Not Blocking Closure` + `Successor Required` + **具名重开事件** ✓。
  - **红线三扫**：① 三个 Phase 的 `Targets` 无一落在 `tests/gates/**` / `.github/workflows/**` / `DECISIONS.md` / `02-WBS.md` / `missions/` ✓ —— Phase 3 新增的 `docs/architecture/model-management.md` 是 owner doc，不在任何红线内；② `docs/masterplan/STATE.md` 只追加，`Closure Gates` 有 numstat 删除列为 0 的自证，且 `T5` 引的优先级说明已写进正文 ✓；③ `docs/backlog/p1-insight-roadmap.md` 实测不在任何红线清单内 ✓。
  - **一条我特意查过的交叉污染风险，结论是安全**：N1–N5 变异的是 owner doc，而 `tests/routing/test_capabilities.py` 也读同一份文件。实测其 `_table_after(marker)` 按**标记名**取表（`:45`），N4「整表删空」只动 `routing-guards` 那一张 ⇒ `capability-enum` / `task-capability-matrix` / `model-profiles` 三张表不受影响，Phase 3 变异期间**只有新判据会红，既有 14 条不会连坐** ✓。
  - **我本轮的全部实测都在 `/tmp` 上做**（原型脚本 + git 取 `old` 的可行性验证），活仓 `git status --porcelain` 除本 plan 文件外**零改动** ✓。

**iteration 4 总判：`accept`，本 plan 可转 `active`。** —— 0 条 blocking，0 条会改变交付形状的问题。上一轮的 blocking（`S1`：`N4 整表删空` 静默绿）已由我按今天正文重做原型、五条变异逐条实测确认堵住，且捕获者逐条对得上。余下 `T2`–`T4` 共 4 条是执行前的一次性打磨（日期格式写死 · 子串不变式补 `endswith` 断言 / 改从 git 取 `old` / 改判全文子串 · Non-Goals 1 补 owner doc · 把「1066 字符」改成「1066 字节 ≈ 701 字符」），**建议起草者顺手改掉再开工，但不需要再走一轮独立评审来放行**。
**四轮下来这份 plan 的形状值得记一句**：它两次在同一个病上栽跟头（`F1` 的门禁无存活守卫、`S1` 的新判据无存活守卫），**两次都是靠「按判据源码/正文口径做原型实跑」而不是靠读文字发现的** —— 这条方法本身建议由起草者写进证据文件，作为 CP9 §1.2 的一条可复用打法。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned
- [ ] verification has run（`pytest tests/routing -q` · `pytest tests/unit tests/tools -q` · `pytest tests/contracts tests/routing tests/context -q` · `tools/gates/check_expected_red.py` · `ruff check …`，逐条附退出码）
- [ ] scoped verification is not conflated with full verification —— 整仓 `pytest tests -q -m "not live"` **基线即红**（`gates`×`tools` 环境泄漏已单列 `docs/backlog/gates-and-tools-leak-env-across-directories.md`），本 plan 不声称跑绿它，写明 "verification scope limited"；
      **并一并点名 `D3`（`R9`）**：本 plan 新增的判据**进 CI（`gates.yml` 步骤 ④）但不进 `GATE_VERIFY`**（`missions/p1-insight.json:16` 的 `commands.test` 不含 `tests/routing`）⇒ **`GATE_VERIFY` 退 0 不等于这条判据被跑过**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **红线自证**：`git diff --name-only <BASE> -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md missions/ docker-compose.yml industry-packs/ pyproject.toml` → **无输出**；`git diff --numstat <BASE> -- docs/masterplan/STATE.md` 删除列为 **0**

## Deferred But Adjudicated

### D1 · 门禁盖不住的**四种**形态（别名导入 / 属性式构造 / `agenerp/` 之外的调用方 / **判据自身无存活守卫**）

- Classification: `watch-only residual`
  ⚠️ **照实说：它是一条覆盖缺口，不是「改进建议」。** 本 plan 把它**登记准确**，不假装它被堵上了。
  ⚠️ **第四种是评审期实测出来的，不是推演**（`R6`）：独立评审者在 `/tmp` 隔离副本上把 `agenerp/routing/` 内的
  `ChatAdapter` 整体改名后，门禁 **`2 passed`（绿）**、`pytest tests/routing -q` **`2 errors`（红）**
  ⇒ **判据在类名消失后完全静默**。`:100` 缺一句 `:74` 那样的存活守卫。
  ⚠️ **补那句守卫要改 `tests/gates/**`（红线 1），loop 无权** —— 这正是它只能被登记、不能被修的原因。
  ⚠️ **本 plan 自己也留了一个洞，写在这里不藏（`R7`）**：`A == B` 钉住的是「文件 + 函数名」，
  **表的第 3/4 列（盖住什么 / 不盖什么）是散文，没有任何判据钉着** —— 而本 plan 修的那条漂移恰恰就是一句散文断言。
  ⚠️ **第 5 列不同，它已被收回范围内（`S3`）**：Phase 3 的断言 ⑤ 钉住的是**路径存在性 + 日期可解析性**
  —— ⚠️ **不是「日期是否新鲜」，那一项钉不住，本 plan 也不声称钉住了**（`T2(d)`：通篇在反 over-claim，自己这句不留半分）。
  它要挡的失败形态是 ——
  「今天写下、将来目录被删/改名而判据全绿」那种**指向虚空的可信度背书**与本 plan 要修的病同形，**不能也登记成残余风险**。
  ⇒ 留在本条里的只有**第 3/4 列**。**要真钉住它们，只能靠周期性重跑 Phase 1 那张变异表** ——
  那是一个**反复执行的机制**（每次重跑都要人重新判断覆盖有没有变），不是一次性交付物，需要一格新预算（归人）。
  ⚠️ **它不落规则 14 四类中的任何一类**：第 3/4 列在 Phase 1 实测当天为真，**不是确认的漂移，也不是确认的活缺陷**（独立评审 `S3` 判词，起草者采纳）。
- Why Not Blocking Closure: 本 plan 的结果面是「登记面说真话且被钉住」，不是「把口子堵上」。
  堵它必须改 `tests/gates/**`（红线 1，loop 无权），或在 `tests/routing/` 造一条同义判据 ——
  后者被 `agenerp/routing/adapter.py:114` 逐字反对（「放两处会出现一处松一处紧」）。
- Successor Required: `yes`（人）
- 重开事件：**人批准改 `tests/gates/test_agent_seam_stays_swappable.py` 收严匹配形状 / 补存活守卫**，
  或**人为工作项 3 之外另开一格预算**，或**在 `agenerp/**` 产品代码内出现一次逃逸构造**。
  ⚠️ **重开事件里不写「实测出现一次真实的逃逸构造」** —— 独立评审 `F3` 指出它**起草当天就已成立**
  （`tools/experiments/p1_insight_live/run.py:159`），写成重开事件等于自我否定。
  域外那一处**今天就存在**，它由本 plan 逐字登记进 owner doc，**不由重开事件承接**。

### D2 · 「唯一调用入口」这条预期没兑现

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 只负责把「没兑现」这件事写准，
  要不要把入口收敛成一处是一次新的 `Decision`，归人（D-22 接缝面）。
- Successor Required: `yes`（人）
- 重开事件：**出现第三个 `route()` 产品调用点**，或**人裁定收敛调用入口**。

### D3 · 新判据不在 `GATE_VERIFY` 的判定面上

- Classification: `watch-only residual`
- Why Not Blocking Closure: `missions/p1-insight.json:16` 的 `commands.test` 逐字只有
  `check_expected_red.py && pytest tests/unit -q` ⇒ 本 plan 落在 `tests/routing/` 的判据**进 CI（`gates.yml` 步骤 ④）
  但不进 `GATE_VERIFY`**。`missions/**` 在红线内（`01-EXECUTION-MODEL.md:14` 禁止项 ③），loop 无权改。
  ⚠️ 该 json `:24` 自己就警告过这类坑 —— **本条是登记，不是发现了一个新坑**。
- Successor Required: `yes`（人）
- 重开事件：**人扩 `missions/p1-insight.json` 的 `commands.test`**，或人裁定 CI 覆盖已足够。

## Closure

Status Note: 未收口。

Closure Audit Evidence:

- Auditor / Agent: 待独立收口审计
- Evidence: 待填

Follow-up:

- 待填
