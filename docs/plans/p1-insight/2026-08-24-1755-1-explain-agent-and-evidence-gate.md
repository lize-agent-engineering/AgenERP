# P1.4 解释 Agent + 证据充分性门禁（控制循环本体）

> Plan Status: completed
> Mission: p1-insight
> Work Item: 6. 解释 Agent + 证据充分性门禁（P1.4）
> Execution Order: 1 / 2（本批第一个；同批第二个 `docs/plans/p1-insight/2026-08-24-1755-2-inspector-and-insight-agent.md` 以本 plan 为前置）
> Last Reviewed: 2026-08-24（起草基线 sha `9a7286a`；**执行期已按 §1.0 两次重取基线 → Phase 1 用 `b86244f`、Phase 2–4 用 `6b07889`**，红线自查各以对应 sha 为 diff 基线）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 6 · `docs/masterplan/02-WBS.md` §4 **P1.4 行**
> Related: 前置 P1.0a（`agenerp/tools/`）· P1.1（`agenerp/routing/`）· P1.2（`agenerp/context/`）· P1.3（`agenerp/orchestration/`）· 证据设施 `tools/experiments/p1_entry_gate/`
> Audit: required

## 1. Current Baseline

### 1.0 执行前必做：重取基线（**这不是形式**）

起草期实测：起草开始时 `git log -1` 是 `5ffb8fb`，写到一半已变成 `9a7286a`
（人在同一工作树上连提三笔：`b62db9f` RUNBOOK §5.5 · `3451462` / `9a7286a` 收 STATE §3）。
`docs/masterplan/04-RUNBOOK.md` §5.5 逐字：「**7×24 的默认状态是：loop 正在写这个工作树**」，
反过来也成立——**人也在写它**。

→ **开工第一件事**：`git log -1` + `git status --porcelain` 重取，把本节的基线 sha 就地改准，
并以**重取到的那个 sha** 作为 §10 红线自查的 diff 基线。
沿用起草期的 `9a7286a` 会把人的 `STATE.md` 追加行算成本 plan 的改动。

以下每条都是起草期实读，不是回忆；执行期逐条复核（行号可能已漂）。

**执行期实测（2026-08-24）**：`git log -1` → `b86244f`
（`docs(runbook): §5.6 的自查规矩写完第一次用就被违反 —— 补上虚警形态`）；
`git status --porcelain` → 只有本批两份 plan 未跟踪，工作树无其他改动。
→ **本 plan 的 diff 基线就此写死为 `b86244f`**，起草期的 `9a7286a` 作废。
基线数字复跑结果见 §1.8 的「执行期实测」行。

**Phase 2–4 执行期二次重取（2026-08-24，Phase 1 之后另一轮开工）**：`git log -1` → `6b07889`
（`ci: 补齐「L2 全量 live」前置的连接信息；站点名统一到 job 级 env`）；
`git status --porcelain` → 只有本批两份 plan 与 Phase 1 产出的 `agenerp/explain/` 未跟踪。
`b86244f..6b07889` 之间**人又提了五笔**（两笔 `ci:` 动 `.github/workflows/**`、三笔 `docs:`）。
→ **Phase 2–4 的红线自查以 `6b07889` 为 diff 基线**，沿用 `b86244f` 会把人那两笔
`.github/workflows/**` 的改动算成本 plan 触了红线 2 —— §1.0 这一节存在的理由就是这个，
不是形式。`b86244f` 仍是 Phase 1 的基线，两个都记着，不覆盖。

### 1.1 「控制循环本体」今天只存在于**实验设施**里，不在产品面

- `tools/experiments/p1_entry_gate/loop.py` 模块头逐字：「**这是实验设施，不是产品**
  （落在 `tools/experiments/`，不进 `agenerp/`）。它只为回答一个问题而存在：
  **确定性的循环门禁，能否补偿模型能力的不足？**」
- `agenerp/orchestration/__init__.py` 模块头逐字：「**不是控制循环本体**（模型选工具 → 回注 →
  作答 → 门禁 → 强制续跑）：**那归 P1.4**。」
- `ls agenerp/` → 无 `explain/`。**产品面上没有任何一行代码做过「解释 Agent」这件事。**

→ 本 plan 的第一个交付面就是把实验设施里已被实测过的那条循环，**换掉四个零件**
（模型侧、开场侧、会话侧、熔断侧）搬成产品件，而**不是重写一条新的**。

### 1.2 三条证据门禁规则已经是可执行件，且**已经挂在工具前置上**

- `agenerp/tools_readonly.py:58/66/74` → `EVIDENCE_GATE_L1 / L2 / L3`，`:90` 合成 `EVIDENCE_GATE`。
- `:95` → `ANSWERING_TOOLS = ("query.read", "snapshot.read")`；`:103`（`QUERY_READ`）与 `:155`（`SNAPSHOT_READ`）
  → 两条契约的 `preconditions` **都是** `EVIDENCE_GATE`。**① 那一面覆盖两条契约，不是一条。**
- owner doc 是 `docs/design/agents-and-roles.md` §5.0 ①，三条规则原文与代码 `text` 已由
  STATE §3 `[resolved] 2026-08-24T04:10Z` 机械核对为**逐字相等**。

→ **门禁规则本 plan 一个字不改。** 本 plan 交付的是「谁在什么时候拿这三条求值」。
⚠️ **两处求值不是一件事**（见 §5 的 `Decision` D2）：工具前置卡的是「取证工具能不能调」，
作答前卡的是「这个 answer 能不能被接受」。今天只有前者存在。

### 1.3 事实采集面已被实测过，但落在实验设施里

`tools/experiments/p1_entry_gate/gate.py` 模块头逐字：「**规则本身一个字都不在这里**……
本模块只做一件事：把一次对话的**事实**凑齐，交给它们求值。规则若在这里被复述一遍，
实验测的就成了这份复述而不是那三条规则。」它给出五条事实的来源表，其中：

| 事实 | 来源 |
|---|---|
| `documents_named_in_question` | 从问题文本按单号形状抽 |
| `doc_links_called_for` / `doc_get_called_for` | **轨迹**里的 `name` 参数（循环记，非模型自报） |
| `submitted_downstream_documents` | `doc.links` **返回值**中 `docstatus == 1` 的行 |
| `inbound_vouchers_of_quantities_in_answer` | **直接查站点**：答案里的数字若等于某个 `Bin.actual_qty`，取该 `(物料, 仓库)` 全部使数量增加的凭证 |

⚠️ 该模块**已登记一条残余风险**（逐字）：「只描述『积压』而不报数字的回答 **escape 得掉 L3**」。
本 plan **不擅自扩大 L3 的口径**（那要改规则措辞，属 owner doc 与人的裁定面），
只把这条残余风险原样带进产品面并在落点节复述。

### 1.4 四个可直接消费的前置件（P1.0a / P1.1 / P1.2 / P1.3 的交付物）

| 可用 | 出处（实读） | 本 plan 怎么用 |
|---|---|---|
| 十个只读工具的唯一执行入口 `execute(tool, params, *, client, context, executors)` | `agenerp/tools/runtime.py:316` | 循环的工具执行面，**不另起一条** |
| `route(task_class, *, models, requested, config, transport) -> ChatAdapter` · `ChatAdapter.chat(messages, tools, max_tokens) -> Reply` · `Reply.usage: Usage(prompt/completion/reasoning)` | `agenerp/routing/router.py:48` · `adapter.py:122` · `adapter.py:39` | 模型侧，**替掉实验设施自带的 `llm.py`**（见 D1） |
| `open_session(...) -> OpeningPack`（注入 `permission.scope`，`facts[PACK_FACT]` 由记录推导） | `agenerp/orchestration/opening.py:119` | 开场侧 |
| `DenialBreaker.record(result) / .tripped / .report()` | `agenerp/orchestration/circuit.py`（`DENIAL_THRESHOLD = 5`） | 熔断侧，**本 plan 负责接线** |
| `context.start(session_id, user=...) -> ConversationSession`（`Turn` / `ToolCall` / `ExecutedAction`） | `agenerp/context/session.py:170` | 会话侧 |
| `ImmediateContext` / `assemble` / `trim` | `agenerp/context/immediate.py` | ① 即时上下文，随开场包进循环 |

### 1.5 熔断的接线欠账，owner doc 已逐字点名归本 plan

`docs/architecture/module-boundaries.md` §7.4 末尾逐字：「⚠️ **接到真实控制循环上是 P1.4 的动作，
本期没做。** 本期能证明的是『喂 `DenialBreaker` N 次权限拒绝，它会刹车、会给出所需权限清单』，
**不是**『真实会话里它一定被调用到』——循环本体归 P1.4」；紧接一条：「⚠️ 本节的
『写入审计，标记为权限探测事件』那一行本期未落地：审计写入面属控制循环，与上一条同因。」

→ **这两条是本 plan 的欠账，不是别人的。** 处置分别见 Phase 2 与 `Decision` D4。

### 1.6 判据的落点被 CI 与红线**共同框死**，这决定 Phase 3 的形状

- `.github/workflows/gates.yml:517-530` 的步骤 ⑦「没有测试目录被漏在 CI 之外」逐字写死
  `COVERED="contracts context experiments fixtures gates routing tools unit"`，
  **`tests/` 下新增任何目录，这一步立刻红**；而 `.github/workflows/**` 在
  `docs/context/ai-autonomy-policy.md` Protected Areas 里是 `blocked`（红线 2）。
  → **本 plan 不得新建 `tests/<新目录>/`。**
- `missions/p1-insight.json` 的 `commands.test` 是
  `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`，
  `missions/*.json` 同为 `blocked`（红线；STATE §3 已有三条 `[open]` 记着
  `tests/tools` / `tests/routing` / `tests/context` 都进不了这条命令）。
  → **`tests/unit` 是今天唯一同时被 `GATE_VERIFY` 与 CI 复跑到的目录。**
  ⚠️ **一处不一致照实记，本 plan 不代改**：WBS §4 P1.4 行的「状态源」写的是 `MD:p1-explain`，
  而 `missions/` 下**只有** `p1-insight.json`（`ls missions/` 实读）。
  本 plan 的 Goal 4「`GATE_VERIFY` 复跑得到」依据的是 `missions/p1-insight.json` 的 `commands.test`；
  `missions/**` 是 blocked，这处不一致归人。
- `tests/gates/**` 是 blocked（红线 1）。WBS §4 P1.4 的验收原文
  🔴 `tests/gates/test_evidence_gate_blocks_single_hop.py` **本 plan 不得创建**
  ——创建即 `git diff` 触及该路径，CI 的 `gates-untouched` job 会拦下。
  **先例已有**：P1.0a 的 🔴 门禁那一半由人补齐（`tests/gates/test_tool_execution_live.py`，
  commit `3b6d071`，`Gates-Change-Approved-By: lize`），且那次的做法逐字是
  「**断言体不重写，按路径加载开发期那份**——判据只有一份，门禁是它的严格模式」。
  → 本 plan 按同一先例交付**断言体**，见 Phase 4。

### 1.7 已有的门禁求值判据（不重复覆盖）

`tests/unit/test_evidence_gate_l3.py` **已在**，它在**事实字典层**对 `EVIDENCE_GATE` 求值
（含 `agents-and-roles.md` §5.0 ① 点名的那条过拟合反测）。
→ **本 plan 的判据不与它重叠**：它判「给定事实，三条规则怎么判」；
本 plan 判「**循环怎么把事实凑出来、凑不齐时怎么办**」。收口时不得把它算成本 plan 的产出。

### 1.7a 「判自由文本前先跑通标注集」这条新规矩，本 plan 落在**例外**那一侧（照实说明理由）

起草期间人往 roadmap 追加了一节（`e08ca4b`）：**「⚠️ 判自由文本答案之前，先跑通标注集
（P1.4 / P1.5 动手前必读）」**，指向 `tests/fixtures/p1_entry_gate_labels.jsonl`（24 条人工标注）
与 `tests/unit/test_answer_judging_fixture.py`。理由逐字：人侧用关键词正则判那道题的答案
**判了四次、四次都判错**，结论是「**正则判自由文本这条路走不通**」。

同一节的末尾逐字给了例外：「若判的是**结构化事实**（例如「给定事实集，三条门禁规则怎么判」），
**本节不适用** —— 那是可枚举的，正则/条件求值没问题。」

→ **本 plan 的每一条判据都落在例外那一侧，逐条点清**：
H1/H2 判的是**门禁对一条给定轨迹的判定**（结构化事实）；H3 判的是 `execute` 次数与权限清单；
H4 判的是 token 账目。**没有一条判「答案对不对」**（§6 的 H4 已逐字写明「不预测答案对错」）。
→ **因此本 plan 不写自由文本判定器，也不需要先跑通那 24 条**。
⚠️ **反过来的约束照实立着**：执行期若有人想给本 plan 补一条「解释答得对不对」的判据，
**那条判据受该节约束**——必须先跑通标注集，跑不通就不许往下写。**本 plan 不开这个口子。**

### 1.8 基线数字（复跑对照用；**只记条数与退出码，不记墙钟**）

- `python3 -m pytest tests/unit -q` → **exit 0，`373 passed`**
- `python3 tools/gates/check_expected_red.py` → **exit 0，`门禁 11 项：预期红 0，绿 11，跳过 0`**
- `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
  → 这是 CI `lint` job 第 569 行的原文作用域，**新增的 `agenerp/explain/**` 与 `tests/unit/**` 都在里面**，
  开工时先跑一次留基线
- `tools/gates/expected-red.txt` 已清空到 0 条条目（棘轮方向只能变短）。**本 plan 不往里加行。**

**执行期实测（基线 `b86244f`，开工前复跑，逐条与上面对照）**：

| 命令 | 退出码 | 输出 | 与起草期基线 |
|---|---|---|---|
| `python3 tools/gates/check_expected_red.py` | 0 | `门禁 11 项：预期红 0，绿 11，跳过 0` | 吻合 |
| `python3 -m pytest tests/unit -q` | 0 | `373 passed` | 吻合 |
| `python3 -m pytest tests/tools -q` | 0 | `81 passed, 12 skipped` | 起草期未记，此处补记为对照基线 |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | 0 | `All checks passed!` | 吻合 |

## 2. Goals

1. `agenerp/explain/` 落地**解释 Agent 的控制循环本体**：开场注入 → 模型选工具 → `execute` →
   结果回注 → 作答 → **证据充分性门禁判定** → 不满足则强制续跑；满足才把答案交出去。
2. **证据充分性门禁在作答面真的拦得住单跳答案**，且拦得住这件事由**轨迹**证明，不由答案文本证明。
3. P1.3 的 `DenialBreaker` **真的被接到这条循环上**，§7.4 那条「本期没做」的失效归属就此改准。
4. 判据落在 `tests/unit/`，**`GATE_VERIFY` 与 CI 两侧都复跑得到**（这是本批相对前四个工作项的加严项）。
5. 交付 🔴 `tests/gates/test_evidence_gate_blocks_single_hop.py` 的**断言体**
   （`tests/unit/test_evidence_gate_single_hop_body.py`，**basename 必须与门禁那份不同**）**与交接说明**，人只需按路径加载。

## 3. Non-Goals

1. **不做成本记账的判据**（P1.7）。循环内会有 `Usage` 汇总的**载体**（否则无处可记），
   但「三项分开记 / 能按一次解释汇总 / 缺一项即红」这套判据归 P1.7，本 plan 不写、不声称。
2. **不做工具调用轮数上限的判据**（P1.7 的「失控闸另算」）。本 plan 给循环一个 `max_turns`
   参数与默认值**只为防跑飞**，不把它当作交付面，收口时不得说成「失控闸已做」。
3. **不做巡检器与洞察 Agent**（P1.5，同批第二个 plan）。
4. **不做 Desk 侧边栏**（P1.8）。本 plan 的交付面是库，不是 UI。
5. **不改 `EVIDENCE_GATE` 三条规则的措辞**，不改 `ANSWERING_TOOLS`，不改十个契约的任何一条。
6. **不写任何业务数据**（②端只读，mission `goal` 逐字）。循环只调只读工具。
7. **不动 `tools/experiments/p1_entry_gate/`**（含删除、改名、"合并进产品面"）。
   它是 P1.0 的证据设施，14 份轨迹的可复跑性挂在它上面；退役与否由人定。
8. **不收窄 `agenerp/routing` 的导出面**。STATE §3 `[open] 2026-08-24T08:12Z` 的 F8
   （`ChatAdapter` 可被直接构造绕过能力校验）逐字写着处置「届时**由人决定**是收窄导出面
   还是加一条静态判据」——本 plan 把「唯一调用入口」这个前提做出来，**不替人做那个决定**。
9. **不动 `missions/**` / `.github/workflows/**` / `tests/gates/**` / `docs/masterplan/` 已有行**（红线 1/2/3/5）。

## 4. Task Route

- Type: `implementation-only change`（产品面新增模块；owner doc 只补落点节与失效归属改准，不改设计结论）
- Owner Docs: `docs/design/agents-and-roles.md` §5.0 ① / §5.1 · `docs/architecture/module-boundaries.md` §7.4 / §7.6a / **新增 §7.8**
- Skill Selection Basis: `docs/skills/README.md` 里没有与「把实验设施搬成产品件 + 循环门禁判据」对应的方法件；
  评审与收口审计走独立子代理（`ai-autonomy-policy.md` Reviewer availability = `subagent`）。各 Phase 记 `Skill: none`。

## 5. Infrastructure And Config Prereqs

- **Phase 1–3 零外部依赖**：假 transport（`ChatAdapter(transport=...)`）+ 假站点，
  零网络、零凭据、零 docker。这是判据能进 `tests/unit` 的前提。
- **Phase 4 的一次实跑需要**：活站点四个 `AGENERP_*` 环境变量（P1.0 已跑通同一套）+
  `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL`。**凭据绝不进 git、不打印到日志**
  （`missions/p1-insight.json` `_notes.p1_specific` 逐字）。
- **无 DDL、无写操作、无回滚脚本需求**：本 plan 不对活站点发任何写请求，
  `agenerp/site.py` 的 `create_doc` / `ensure_doc` / `delete_custom_field` 一次都不调
  （Protected Areas 里「对活站点的破坏性写 / 非破坏性写」两行**都不触发**）。

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下列四条在写任何实现代码之前逐字写死，事后逐条对照，不许事后改写。**
它们判的是**本仓夹具与本站点上的行为**，不外推。

- **H1（门禁在作答面拦得住单跳）**：给循环一条只调过一次 `doc.get`、随后直接作答的轨迹，
  门禁开时该 answer **被拒**且回注强制续跑消息；门禁关时**同一条轨迹的同一个答案被接受**。
  → 两侧都成立才算 H1 吻合；只验前者等于没验（那不能区分「门禁拦住了」与「循环本来就不作答」）。
  ⚠️ **判据侧比本假设多一条**：Phase 3 的 D7 选定「门禁关」只在判据侧构造，
  因此 Proof H1 是**三条**断言（多一条「产品默认路径下 ② 门禁确实是开的」）。
  **这是判据集加强，不是假设改写** —— H1 本身一个字未动。
- **H2（判据落在轨迹上，不落在答案文本上）**：把上述答案文本换成一段
  **文字正确但取证不足**的答案（数字对、结论对），门禁**仍然拒**。
  → 这是「答对」与「蒙对」的分界，也是硬约束①在本 plan 上的具体形式。
- **H3（熔断真的在循环里被调用到）**：让假站点对连续 5 次**工具调用**回 HTTP 403，
  循环**在第 5 次之后不再发起第 6 次 `execute`**，并返回固定文案「你的权限不足以回答这个问题」
  \+ **点名了那几个被拒 DocType 的**所需权限清单（形如 `read:GL Entry`）。
  → **计数单位写死**：判据数的是**循环发起的 `execute` 次数**，
  不是假站点收到的 HTTP 请求数（一次 `execute` 可能发多个请求，例如权限探测）。
  → 清单那一半**不许是空的**：`DenialBreaker.report()` 的 `denied` 由 `record(..., doctype=...)` 填，
  循环不传 `doctype` 就会得到一句裸的「所需权限：」——那等于 H3 只验了一半（见 Phase 2 的 D6）。
- **H4（活端点上跑得起来且账目对得上）**：Phase 4 的一次真实运行里，
  `usage` 的 `prompt > 0`、`completion > 0`、`reasoning > 0`（D-11：`qwen3.6-plus` 回两个字
  也烧约 195 reasoning token），**且账目对得上端点自报的数**：
  `usage.prompt + usage.completion == raw["usage"]["total_tokens"]` 且
  `usage.reasoning == raw["usage"]["completion_tokens_details"]["reasoning_tokens"]`（`raw` 是 `Reply.raw`）。
  ⚠️ **不许写成 `prompt + completion == total`** —— `Usage.total` 就是 `prompt + completion`
  这个计算属性（`agenerp/routing/adapter.py:57-59`），那条断言对任何实例恒真，**证不了任何事**。
  → **H4 不预测答案对错**。这道题的正确率归 P1.0，本 plan 不重跑那个实验、不引用它的数字作结论。

⚠️ **H1–H4 全部是机制性断言，没有一条是「模型答得更好」。** 本 plan 不产出任何正确率数字；
若执行期有人想加，那是另一个实验，须另起 plan（D-16）。

## 7. Execution Plan

### Phase 1 — 解释 Agent 的循环本体

Status: completed
Targets: `agenerp/explain/__init__.py` · `agenerp/explain/gate.py` · `agenerp/explain/loop.py`
Skill: `none`

- Item Types: `Add | Decision`
- Prereqs: 无（§1.4 的四个前置件均已在仓）

- [x] **Add** `agenerp/explain/gate.py` —— 证据充分性门禁的**事实采集面**。
      五条事实的来源与 `tools/experiments/p1_entry_gate/gate.py` 的来源表**逐条相同**；
      **规则一个字不复述**，一律 `from agenerp.tools_readonly import EVIDENCE_GATE` 求值。
      §1.3 那条残余风险（只描述积压不报数字可 escape L3）**原样带过来并写在模块头**。
- [x] **Add** `agenerp/explain/loop.py` —— 控制循环：开场 → 模型 → `execute` → 回注 → 作答 →
      门禁判定 → 强制续跑。工具声明**由契约生成**（契约表变了自动跟着变），
      `permission.scope` 由开场包注入而**不进模型的工具面**（理由见 D3）。
- [x] **Add** `agenerp/explain/__init__.py` —— 导出面**只有**一个入口与它的返回类型。
      导出面一旦泄开就收不回来（`routing/__init__.py` 模块头同一口径）。
- [x] **Decision D1 · 模型侧走 `agenerp.routing`，不用实验设施的 `llm.py`。**
      备选：(A) 直接复用 `tools/experiments/p1_entry_gate/llm.py` —— **否决**：它自己的模块头
      （`llm.py:1`）逐字写着「**实验设施，不是产品代码**」，产品面依赖它等于把实验设施变成产品依赖，
      P1.0 的轨迹设施从此不能动；
      且它绕过 P1.1 的能力分档校验。(B) **走 `route(task_class, ...)` 取 `ChatAdapter`**（选定）：
      任务类目取 `TASK_MINIMUM_CAPABILITIES` 里已声明的 `explain` / `lineage`，由调用方指定，
      循环不替调用方选类目。**残余风险照实登记**：`lineage` 档今天会放行 `qwen3.6-plus`，
      而它在本项目两跳题上是 1/6（STATE §3 `[open] 2026-08-24T07:50Z` 第二条）——
      **那条 `[open]` 本 plan 不代人处置，也不因本 plan 落地而消失。**
      ⚠️ **一处前向引用就地关掉**：`agenerp/routing/capabilities.py:38` 逐字预告四个任务类目
      「P1.4 解释 Agent 落地后很可能要重划」。**本 plan 不重划**——重划要动 P1.1 已收口的声明表与
      `tests/routing` 的回归面，属另一个交付面；本 plan 只**消费**现有的 `explain` / `lineage` 两档。
- [x] **Decision D2 · 门禁在两处求值，分工写死，不许各自漂移。**
      **两处不是重复**：① **工具前置**（`QUERY_READ.preconditions`，P1.0a 已在）卡的是
      「作答类工具能不能被调用」；② **作答前**（本 plan 新增）卡的是「这个 answer 能不能被接受」。
      只有 ② 能拦住「模型不调作答类工具、直接凭 `doc.get` 的返回值报数字」这条路
      ——而那正是 Spike 02 实测到的失败形态（`agents-and-roles.md` §5.0 ①：只调一次 `doc.get` 就下结论）。
      备选：(A) 只保留 ① —— **否决**，理由同上；(B) 只保留 ② —— **否决**：那要改 P1.0a 已收口的契约（Non-Goals 5）；
      (C) **两处并存，事实采集面只有一份**（选定）：`explain/gate.py` 既喂 `execute` 的 `context`，
      也喂作答前那一次求值，**两处求的是同一个事实字典**。
      **残余风险**：两处口径靠「同一份事实采集面」绑定，有人另写一份事实就会漂移 ——
      判据用一条断言钉住（Phase 3）。
- [x] **Decision D3 · `permission.scope` 不进模型可见的工具面。**
      沿用 `tools/experiments/p1_entry_gate/loop.py:50` 的 `EXCLUDED_TOOLS` 口径（`:17` 是它的理由段），
      但**理由已经变了**：实验期是「本设施没实现开场注入」，本期是「开场注入**已由 P1.3 实现**，
      再让模型自己调一次等于把已经确定性化的一步交回给模型（D-15）」。
      **残余风险**：模型若在开场包之外还需要更新可见范围（例如换身份），本期没有这条路径；
      本期不发生换身份，登记为 watch-only。

Exit Criteria:

- [x] `agenerp/explain/` 三个模块可 import，导出面只含一个入口与其返回类型
- [x] D1 / D2 / D3 的选定与备选、残余风险已写进本 plan 或模块头
- [x] 无 owner-doc 更新（落点节统一在 Phase 4 写）—— 本阶段 `No owner-doc update required`

### Phase 2 — 接线：开场注入 · 会话落盘 · 权限拒绝熔断

Status: completed
Targets: `agenerp/explain/loop.py` · `agenerp/explain/__init__.py`
Skill: `none`

- Item Types: `Add | Fix | Decision`
- Prereqs: Phase 1

- [x] **Add** 开场侧：循环起步先调 `orchestration.open_session(...)`，把 `OpeningPack`
      （注入产物 + `facts[PACK_FACT]` + 注入代价）摆进第一条消息之前。
      **注入代价照记**（`InjectionCost.request_count`），不记就是把「自动注入」变成隐性成本。
      落点：`ExplainLoop._open()` / `_opening_message()`，代价进 `ExplainTrace.opening_request_count`。
- [x] **Add** 会话侧：每一轮落 `context.session` 的 `Turn` / `ToolCall`，
      用量聚合走 `Usage.plus()`（`module-boundaries.md` §7.7 逐字「不许自己写加法」）。
      落点：`ExplainLoop.run()` / `_run_tools()` 的 `with_turn(...)`；
      `ExplainResult.usage` 直接回 `ConversationSession.usage_total`，**本模块一行加法都没写**。
- [x] **Fix** 熔断接线：每次 `execute` 之后喂 `DenialBreaker.record(result, doctype=...)`；
      `tripped` 为真即**停止再发工具调用**，返回 `report()` 的固定文案 + 所需权限清单。
      这是 §1.5 里 owner doc 逐字点名归本 plan 的欠账，**属 `Fix` 不属 `Follow-up`**。
      落点：`ExplainLoop._execute_one()` 的 `self.breaker.record(...)` 与 `_run_tools()` 里
      `if self.breaker.tripped:` 那一段（**同一批里剩下的调用也不发**）。
- [x] **Decision D6 · 熔断的 `doctype` 从哪来。**
      `DenialBreaker.record()` 的 `doctype` 参数**不传就是空**，`report()` 的 `denied` 随之为空，
      「所需权限清单」会退化成一句裸的「所需权限：」——**那等于 §7.4 表里第二行没落地**
      （现有调用方 `tests/tools/test_navigation.py` 每次都传，本 plan 不得比它弱）。
      备选：(A) 从工具参数里取 `params["doctype"]` —— 覆盖不到 `system.overview` / `permission.scope`
      这类没有 `doctype` 参数的工具；(B) 让 `execute` 回填 —— **否决**：要改 P1.0a 已收口的执行面（Non-Goals 5）；
      (C) **(A) + 一条兜底口径**（选定）：有 `doctype` 参数的按参数取，没有的按**工具名**记，
      两类在清单里可区分。**残余风险**：按工具名记的那类，清单里给出的不是 `read:<DocType>` 形状，
      §7.4 表第二行的「指名 DocType」对它只成立一半 —— 照实登记，不粉饰。
- [x] **Decision D4 · §7.4 的「写入审计，标记为权限探测事件」这一行，本期落成什么。**
      备选：(A) 写进 ERPNext 站点的审计表 —— **否决**：那是**写操作**，违反 ②端只读（Non-Goals 6），
      且触发 Protected Areas 的「对活站点的非破坏性写」一行；
      (B) **落进会话轨迹**（选定）：熔断事件作为一条结构化记录进 `ConversationSession`，
      与工具调用轨迹同一份载体，可 diff、可回放；
      (C) 不做，继续留白 —— **否决**：owner doc 已把它归到本 plan，留白第二次就是欠账转移。
      **残余风险照实登记**：(B) **不是**站点侧审计。会话轨迹的落盘实现今天是
      `JsonFileSessionStore`（P1.2 的「端口 + 零依赖内置实现」），**会话 DocType 在活站点上尚未建表**
      （STATE §3 `[open] 2026-08-24T09:20Z`）。因此「写入审计」在本期的含义是
      **本地可回放的轨迹**，收口时不得写成「审计已入站点」。

Exit Criteria:

- [x] 开场注入、会话落盘、熔断三条接线在循环里各有一个真实调用点
      （`_open()` → `open_session` · `run()`/`_run_tools()` → `with_turn` ·
      `_execute_one()` → `breaker.record`；三条各由 Phase 3 的一条判据钉住）
- [x] D4 的选定与残余风险已写进本 plan（并复述在 `ExplainLoop._record_breaker` 的 docstring 里）
- [x] `No owner-doc update required`（落点节统一在 Phase 4）

### Phase 3 — 判据：单跳被拒、补齐放行、消融、熔断、变异自查

Status: completed
Targets: `tests/unit/test_explain_loop.py` · `tests/unit/test_evidence_gate_single_hop_body.py`
Skill: `none`

- Item Types: `Proof | Decision`
- Prereqs: Phase 1, Phase 2

- [x] **Decision D5 · 判据落 `tests/unit/`，不新建 `tests/` 子目录。**
      依据是 §1.6 实读的两条硬约束：新建目录会让 CI 步骤 ⑦ 直接红，而改 workflow 是红线 2；
      `tests/unit` 是今天**唯一**同时进 `commands.test`（`GATE_VERIFY` 复跑得到）与 CI 的目录。
      备选：(A) `tests/explain/` 新目录 —— **否决**：CI 步骤 ⑦ 必红且需人改 workflow；
      (B) `tests/tools/` —— **否决**：进 CI 但**不进 `commands.test`**，
      会第五次复制 `tests/routing` / `tests/context` / `tests/tools` 那个已被登记三次的老问题；
      (C) **`tests/unit/`**（选定）。
      **代价照实记**：`tests/tools/conftest.py:31` 的 `FakeSite` 在 `tests/unit` 里**不可直接 import**。
      ⚠️ **起草期已实测，别再试一遍那条死路**：`from tests.tools.conftest import FakeSite` **不成立**
      （`tests/` 没有 `__init__.py`，不是包；`tests/gates/test_tool_execution_live.py:56` 逐字记着同一件事）。
      **两条可行形状**，由本 Phase 第一项实测选定：
      (i) 把 `FakeSite` 放到 `tests/` 根下的一个 helper 模块，并加 `tests/conftest.py`
      （conftest 所在目录会进 `sys.path`）——**只加文件不加目录，CI 步骤 ⑦ 不受影响**；
      (ii) 按路径加载（`importlib.util.spec_from_file_location`），这正是人做 `3b6d071` 时用的招
      （`tests/gates/test_tool_execution_live.py` 的 `_load_sibling_module`）。
- [x] **Proof（前置动作）** 把假站点做成**一份**：先实测 `tests/unit` 能否 import 到
      `tests/tools/conftest.py` 的 `FakeSite`。**实测决定形态，不许拍脑袋**：
      **起草期已实测过 `from tests.tools.conftest import ...` 那条死路，不许再试**（见 D5）：
      按 D5 的 (i) 或 (ii) 选一条，并由 `tests/tools/conftest.py` 再导出，
      使**工具执行层那份 `FakeSite` 全仓只有一份**（`tests/unit` 里既有的另两份 `FakeSite`
      与三份 `FakeSiteClient` 服务的是种子与定制包，**本 plan 一个字不动**）。
      **禁止的处置**：在 `tests/unit` 里另写一个假站点 —— 两份假站点会各自漂移，
      而它们正是本 plan 全部判据的地基。**改动 `tests/tools/**` 不触红线**（红线 1 只覆盖 `tests/gates/**`），
      但会动到 P1.0a/P1.3 已收口的判据面，因此**必须复跑 `pytest tests/tools -q` 证明零回归**。
- [x] **Decision D7 · H1 的「门禁关」那一侧靠什么实现。**
      **① 那一面全程开着，不许动**：`tools_readonly.py:103`（`QUERY_READ`）与 `:155`（`SNAPSHOT_READ`）
      的 `preconditions` 是 P1.0a 已收口的契约声明，Non-Goals 5 禁止改。
      因此消融**只作用于 ② 作答前那一次求值**。
      备选：(A) 产品入口上加一个 `gate=on|off` 参数 —— **否决**：在一道安全闸上给产品面开关，
      调用方一行就能关掉，且它会进导出面，与 Phase 1 的「导出面只含一个入口与其返回类型」冲突；
      (B) **判据侧直接构造一个不带 ② 门禁的循环对象**（选定）：开关不进产品导出面。
      **残余风险**：(B) 测的是**判据侧构造出来的对象**，不是产品默认路径 ——
      因此 H1 必须多一条断言：**产品默认路径下 ② 门禁确实是开的**，
      否则 (B) 可能变成「在两个不同对象上比较」。
- [x] **Proof H1** 三条都要：① 单跳答案在**产品默认路径**下被拒；
      ② 同一答案在 D7 的 (B) 构造下被接受；③ **产品默认路径下 ② 门禁确实是开的**
- [x] **Proof H2** 文字正确但取证不足的答案**仍然被拒**（判据落在轨迹上）
- [x] **Proof** 补齐证据后**放行**：同一条会话继续取证到三条规则全满足，answer 被接受
- [x] **Proof H3** 连续 5 次 403 → 循环**不再发起第 6 次 `execute`** + 固定文案 +
      **非空且点名 DocType 的** `read:<DocType>` 清单（D6）。
      **计数单位按 §6 写死的那条**：数的是**循环发起的 `execute` 次数**，
      **不是**假站点收到的 HTTP 请求数（一次 `execute` 可能发多个请求）
- [x] **Proof** 非 403 失败（超时 / 5xx）**既不计数也不清零**，循环不因站点故障误刹
      （§7.4 表里那一行的循环侧对照）
- [x] **Proof** D2 的绑定断言：作答前那次求值与工具前置那次求值**取自同一份事实采集面**。
      **一条轨迹不够** —— 另写一份"碰巧在这条轨迹上答案相同"的采集面也能骗过它。
      判据取 **≥2 条会让错误实现分叉的轨迹**（例如：一条有已提交下游单、一条只有草稿下游单），
      **并加一条同一性断言**（两处拿到的是同一个采集面对象，不是两个值相等的对象）
- [x] **Proof** 开场注入在真实循环里**真的发生**：断言落在假站点的请求记录上，
      不落在 `OpeningPack` 的标志位上（P1.3 的 M6 教训：相等断言挡不住装配路径上写死成正确值）
- [x] **Proof** 变异自查 **M1–M8 —— 八个变异在此逐字写死**，不许执行期看着自己的实现现编
      （那正是硬约束② 要挡的「事后写假设」）。逐个把实现改坏，确认对应判据**转红**：
      **M1** ② 作答前门禁的判定写死为「通过」；
      **M2** ② 处换用另写的一份事实采集面（D2 的绑定断言必须打红）；
      **M3** 一次 `execute` 都不发就直接作答（取证轨迹为空仍被接受）；
      **M4** `DenialBreaker` 建了但从不喂 `record()`；
      **M5** 把非 403 失败也计进熔断计数；
      **M6** 开场包的 `opening_injection_verified` 写死为 `True`、站点上不发那次注入请求
      （P1.3 的 M6 第一轮是绿的，本 plan 照它的教训要同一性断言）；
      **M7** `record()` 不传 `doctype`（所需权限清单退化成空，H3 的清单那一半必须打红）；
      **M8** 门禁发红时不回注强制续跑消息、直接把答案交出去。
      任一变异打不红即说明判据有缺口，**就地补断言并把新判据登记为 M9…**，不许略过
- [x] **Proof** 复跑基线命令，与 §1.8 对照，**三条都要**：
      ① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 退 0；
      ② `python3 -m pytest tests/tools -q` 退 0；
      ③ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` 退 0
      （CI `lint` job 第 569 行的原文作用域，新增代码全在里面）

**执行记录（2026-08-24，基线 `6b07889`）**

**D5 实测选定 (ii)「按路径加载」，理由照实记**：(i) 要把 `FakeSite` 搬到 `tests/` 根下再由
`tests/tools/conftest.py` 再导出 —— 那要改动 P1.0a / P1.3 已收口判据面的地基（§8 风险 ④）；
(ii) **一个字都不动 `tests/tools/**`**，代价只是判据侧多一个加载器。落点是
`tests/unit/explain_fakes.py` 的 `load_repo_module()`。
⚠️ **实测补出先例里没有的一行**：`tests/gates/test_tool_execution_live.py` 的
`_load_sibling_module` **没有**把模块塞进 `sys.modules`，而 `tests/tools/conftest.py` 的模块级
`@dataclass` 在那种加载方式下当场炸（`dataclasses._is_type` 反查 `sys.modules[cls.__module__]`
拿到 `None`，`AttributeError`）。所以本 plan 的加载器**必须先注册再 `exec_module`**。
起草期记的那条死路（`from tests.tools.conftest import ...`）执行期未再试，按 D5 的禁令执行。

**判据落点**：`tests/unit/test_evidence_gate_single_hop_body.py`（H1 三条 + H2 两条，5 条）·
`tests/unit/test_explain_loop.py`（11 条）· `tests/unit/explain_fakes.py`（共用假件，非判据）。
`tests/unit` 由 373 → **389 passed**（+16）。

**H1 / H2 / H3 与 §6 原文逐条对照**：

| 假设 | §6 写死的预测 | 实测 | 吻合 |
|---|---|---|---|
| H1 | 门禁开 → 单跳答案被拒 + 回注强制续跑 | `accepted is False`、`answer == ""`、`forced_continues[0]` 含「证据不足」与 `doc.links` | 吻合 |
| H1 | 门禁关 → **同一条轨迹的同一个答案**被接受 | `accepted is True`、`answer` 与剧本逐字相等、两侧 `execute_calls` 同为 1 | 吻合 |
| H1（判据加强项） | 产品默认路径下 ② 门禁确实是开的 | `__kwdefaults__["answer_gate_enabled"] is True`；`explain()` 签名里**没有**这个参数；默认路径下 `gate_checks` 非空且 `enforced` 全真 | 吻合 |
| H2 | 文字正确但取证不足 → **仍然拒** | 同一条轨迹、两段不同答案文本，`gate_checks[0]["facts"]` **逐字相等**，判定同为拒 | 吻合 |
| H3 | 连续 5 次 403 → 不发起第 6 次 `execute` | `trace.execute_calls == 5`（剧本一批给了 6 个调用），`stopped == "permission-breaker"` | 吻合 |
| H3 | 固定文案 + **非空且点名 DocType** 的清单 | `answer` 以「你的权限不足以回答这个问题」开头且含 `read:GL Entry`；`breaker.denied == ("GL Entry",)` | 吻合 |

**M1–M8 变异自查（逐个改坏实现，跑 `pytest <两份判据> -q`，全部打红后立即还原）**：

| 变异 | 改坏了什么 | 结果 | 打红的判据（首要） |
|---|---|---|---|
| M1 | ② 门禁判定写死为「通过」 | **RED** | `test_single_hop_answer_is_rejected_on_the_product_path` 等 9 条 |
| M2 | ② 处换用另写的一份事实采集面 | **RED** | `test_both_evaluations_share_one_evidence_surface_object`（D2 绑定断言）等 7 条 |
| M3 | 取证轨迹为空时直接接受 | **RED** | `test_l3_requires_every_inbound_voucher_of_a_quantity_in_the_answer` |
| M4 | `DenialBreaker` 建了但从不喂 `record()` | **RED** | `test_breaker_stops_the_loop_after_five_consecutive_denials` 等 3 条 |
| M5 | 非 403 失败也计进熔断计数 | **RED** | `test_non_permission_failures_neither_count_nor_clear_the_streak` |
| M6 | 开场包标志位写死为 `True`、站点上不发注入请求 | **RED** | `test_opening_injection_actually_hits_the_site_before_the_model_speaks` |
| M7 | `record()` 不传 `doctype` | **RED** | `test_breaker_stops_...`（`read:GL Entry` 那一半）· `test_breaker_event_is_recorded_into_the_conversation_session` |
| M8 | 门禁发红时不回注、直接交出答案 | **RED** | `test_single_hop_answer_is_rejected_on_the_product_path` 等 9 条 |

→ **八个全部打红，没有一个需要补断言，因此没有 M9**。变异脚本是一次性的（写在
scratchpad，不进仓），每次变异跑完立即 `shutil.copy` 还原；跑完 `git status --porcelain`
确认 `agenerp/` 与 `agenerp/orchestration/` 无残留改动。

**复跑基线（三条，退出码与输出照抄）**：

| 命令 | 退出码 | 输出 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | 0 | `门禁 11 项：预期红 0，绿 11，跳过 0` |
| `python3 -m pytest tests/unit -q` | 0 | `389 passed`（基线 373 → +16） |
| `python3 -m pytest tests/tools -q` | 0 | `81 passed, 12 skipped`（与 §1.8 基线**逐字相同**，零回归） |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | 0 | `All checks passed!` |
| `python3 -m pytest tests -q -m "not live"`（全工作树，额外跑的） | 0 | `849 passed, 12 skipped, 21 deselected` |

Exit Criteria:

- [x] H1 / H2 / H3 三条与 §6 写死的原文**逐条对照**，吻合与否照实记（见上表，**六行全部吻合**）
- [x] **工具执行层那份 `FakeSite` 只有一份**（`tests/tools` 与本 plan 判据共用），且 `pytest tests/tools -q` 零回归。
      本 plan **一个字都没改 `tests/tools/**`**（D5 选 (ii) 的直接后果），`81 passed, 12 skipped` 与基线逐字相同。
      ⚠️ **不是「全仓只有一份假站点」**：`tests/unit/test_seedusers.py` / `test_seedsite_loader.py` 另有自己的 `FakeSite`，
      `test_snapshot_capture.py` / `test_pack_export.py` / `test_apply_execute.py` 另有 `FakeSiteClient`——
      它们服务的是种子与定制包，**本 plan 一个字不动**（复核过：三份 `FakeSiteClient` 与两份 `FakeSite` 均未被触碰）
- [x] M1–M8（及补出的 M9…）逐个记录「打红 / 未打红 → 如何补」（见上表，八个全红，无 M9）
- [x] `No owner-doc update required`（落点节统一在 Phase 4）

### Phase 4 — 活端点实跑一次 · 门禁文件交接 · owner doc 落点 · 日志

Status: completed
Targets: `docs/architecture/module-boundaries.md` · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/`
Skill: `none`

- Item Types: `Proof | Fix | Follow-up`
- Prereqs: Phase 3

- [x] **Proof H4** 活站点 + 活端点跑**一次**完整解释，落一份轨迹到 `docs/evidence/p1-explain/`。
      逐条对照 §6 的 H4 原文。⚠️ **单次实跑的成本量级已知**：P1.0 实测单次解释
      9.7 万–12.8 万 token（roadmap P1.7 节），**跑一次即可，不做多次采样**
      ——多次采样是实验，属另一个 plan（D-16）。
      ⚠️ 若活站点或凭据不可得：**照实记「未跑」并把 H4 判为未验证**，
      **不得**用假 transport 的结果冒充活端点结果，也**不得**因此声称 Phase 4 完成。
- [x] **Fix** owner doc 落点：`docs/architecture/module-boundaries.md` **新增 §7.8**
      「解释 Agent 控制循环在本仓的落点（P1.4）」——各文件职责、**D1–D7 七个 `Decision`**、
      两处门禁求值的分工、以及**判据缺口与验证范围**（照 §7.6a / §7.7 的既有体例）。
      ⚠️ **D6（熔断 `doctype` 兜底口径只满足一半「指名 DocType」）与 D7（消融开关只在判据侧）
      两条残余风险必须出现在「判据缺口与验证范围」小节里**，不许只写在 plan 里。
- [x] **Fix** 失效归属一起改准，**五处，逐条点名**（漏一处就是 owner-doc 漂移，属非降级项）：
      ① `module-boundaries.md` **§7.4 末尾那条 ⚠️**「接到真实控制循环上是 P1.4 的动作，本期没做」；
      ② `module-boundaries.md` **§7.4 末尾第二条 ⚠️**「『写入审计，标记为权限探测事件』那一行本期未落地」
      —— 按 D4 的口径写成**本地可回放轨迹**，**不写成站点侧审计**；
      ③ `module-boundaries.md` **`:205`（§7.6 之内，不是 §7.6a）** 那句
      「**但它尚未接到任何真实控制循环上**，接线归 P1.4」——起草期 `grep` 实测：
      全文**只有这一处**含该句，§7.6a 里没有；`:204` 是已被 `~~划掉~~` 的旧行，**不动它**；
      ④ `agenerp/orchestration/__init__.py` 模块头「**不是控制循环本体**……那归 P1.4」与
      「**本层与真实控制循环之间的接缝只有单侧**」两句（§7.6a 正文里对应的
      「接缝只有单侧」那条残余风险一并改准）；
      ⑤ `agenerp/contracts.py:20-21`「P0 阶段还没有控制循环去消费它们，现在实现只能得到
      『结构存在』的空断言」—— 本 plan 落地后这条前提不再成立。
      ⚠️ **只改这五处失效归属**，§7.4 表里的六行落地形态与「35 次」那条 D-16 警示**一个字不动**。
- [x] **Follow-up → 交接** 🔴 `tests/gates/test_evidence_gate_blocks_single_hop.py` 由**人**创建
      （红线 1；触发条件：本 plan 落地且 Phase 3 全绿）。本 plan 交付的是它的**断言体**
      `tests/unit/test_evidence_gate_single_hop_body.py`，按 P1.0a 先例
      （`tests/gates/test_tool_execution_live.py`：「断言体不重写，按路径加载开发期那份」），
      人只需按路径加载它。
      ⚠️ **两处照实说，不许照抄 P1.0a 的措辞**：
      ① **文件名必须与门禁那份不同**（起草期实测：同名 basename 在 `tests/` 无 `__init__.py` 的布局下
      会让 `pytest` 整轮 `import file mismatch` 收集失败）；
      ② P1.0a 那次的「无站点时 skip → fail」**在本 plan 不适用** —— 本 plan 的断言体是
      **假 transport + 假站点**的，全程不依赖活站点，根本没有 skip 可收严。
      交接说明里必须写清：该门禁是**纯路径加载**、无 live 语义，以及**为什么这仍然满足**
      WBS §4 P1.4 那一行的 🔴（它要的是「门禁拦得住单跳」这条判据存在于 `tests/gates/` 下，
      不是「它必须打活站点」）。**这一句由人复核，loop 不替人拍板。**
      交接说明写进 §7.8 的「判据缺口」小节，**并在 `docs/masterplan/STATE.md` §3 追加一条
      needs-human**（只追加、不改写任何已有行，红线 5），含：命令原文 + 退出码 + sha +
      「本 plan 未创建该文件、也未声称 WBS §4 P1.4 的 🔴 验收已满足」。
- [x] **Fix** 日志：`docs/logs/2026/08-24.md`（若执行日不同则按执行日）按
      `docs/logs/00-log-writing-guide.md` 的格式写一条，含命令原文 + 退出码 + sha。

**执行记录（2026-08-24）**

**H4 逐条对照**（轨迹 `docs/evidence/p1-explain/live-run-01.json`，README 里有同一张表）：

| §6 的预测 | 实测 | 吻合 |
|---|---|---|
| `usage.prompt > 0` | 40,885 | 吻合 |
| `usage.completion > 0` | 4,310 | 吻合 |
| `usage.reasoning > 0` | 2,784 | 吻合 |
| `usage.prompt + usage.completion == raw["usage"]["total_tokens"]` | 七次调用**逐次**成立 | 吻合 |
| `usage.reasoning == raw["usage"]["completion_tokens_details"]["reasoning_tokens"]` | 七次调用**逐次**成立 | 吻合 |

**那一跑证明了什么、没证明什么（照实写）**：证明了循环在活站点 + 活端点上跑得通
（开场注入 10 次 `has_permission` → 七轮 → **8 次 `execute`** → ② 门禁放行），
且 **L3 在真实数据上抓到了它被设计来抓的那件事** —— 答案报成品仓 1,010 台，门禁从库存流水
反查出 `MAT-SCR-2026-00001`（外协入库，正是 P1.0 记录的「沿订单查得再深也看不见」的那张）
与 `MAT-STE-2026-00003`，模型对两张都调过 `doc.get` 因此放行。
**没证明**：② 门禁的**拒绝路径那一跑没走到**（`forced_continues` 为空），熔断**没被触发**
（Administrator 不撞 403）—— 那两件由 Phase 3 的 `tests/unit` 判据证明，不由这一跑证明。
**H4 不预测答案对错**，本 plan 不产出任何正确率数字。

⚠️ **一处与 plan 预期不同的数，照实记**：§8 风险 ⑤ 引 roadmap 写着单次解释
9.7 万–12.8 万 token，本跑是 **45,195 token**，**低于该区间**。**不修饰成「优化了」**——
本 plan 没做任何成本工作（Non-Goals 1），差异成因未测量，成本记账归 P1.7。

⚠️ **实跑的两处形状照实说明**（README 里同样写着）：① 走的是 `ExplainLoop` 而不是导出面的
`explain()` —— 两者装配完全相同（`explain()` 内部就是 `route()` + `ExplainLoop(...).run(...)`），
分开只为在 `adapter.chat` 外包一层留住每个 `Reply`，因为 **`Reply.raw` 不进 `ExplainResult`**
而 H4 的账目核对要的正是它；产品行为一个字没改（② 门禁走默认值 `True`）。
② 开场注入给了 10 个候选 DocType 而不是走发现式路径，这是**调用方的选择**，不是循环的默认。

**五处失效归属逐条点名（改准位置可核对）**：
① `module-boundaries.md` §7.4 末尾第一条 ⚠️（「接到真实控制循环上是 P1.4 的动作，本期没做」）→ 划掉 + ✅ 已接线；
② §7.4 末尾第二条 ⚠️（「写入审计……本期未落地」）→ 划掉 + ✅ 已落地，**并逐字写明这不是站点侧审计**（D4）；
③ `module-boundaries.md` §7.6 内那句「但它尚未接到任何真实控制循环上」（`grep` 复核：全文**仍只有这一处**）→ 划掉 + 指向 §7.8；
④ `agenerp/orchestration/__init__.py` 模块头两句 + §7.6a D1 的「接缝只有单侧」残余风险 → 两处均改准，
   **并新增一句照实记**：`navigation` 那一件**仍是单侧**（循环里选工具的是模型，不是 `ScopeFirstStrategy`）；
⑤ `agenerp/contracts.py` 模块头「P0 阶段还没有控制循环去消费它们」→ 划掉 + 前提不再成立，
   **并保留 §7.5 包裹动作仍未做**这一半。
**§7.4 表里的六行落地形态与「35 次」那条 D-16 警示一个字未动**（`git diff` 可核）。

**门禁文件交接**：断言体 `tests/unit/test_evidence_gate_single_hop_body.py` 已交付，
交接说明写在它的模块头（含给人的加载片段）与 §7.8 的「判据缺口」小节；
STATE §3 已追加 needs-human 一条（`git diff --numstat docs/masterplan/STATE.md` → `7	0`，删除列为 0）。

Exit Criteria:

- [x] H4 逐条对照并记录（**跑了**，五行逐条吻合；「没证明什么」同样逐条记在上面）
- [x] §7.8 落点节存在（含 D1–D7；D6/D7 的残余风险在「判据缺口与验证范围」小节里，
      与 L3 逃逸口、`lineage` 档那两条并列为四条）；上列**五处**失效归属逐条改准，无一遗漏
- [x] STATE §3 needs-human 已追加（只追加）；`git diff docs/masterplan/` 除追加行外无改动
- [x] `docs/logs/2026/08-24.md` 已更新（含命令原文 + 退出码 + sha）

## 8. 风险

| # | 风险 | 处置 |
|---|---|---|
| ① | **「门禁拦住了」与「循环本来就不作答」长得一样** | H1 强制两侧都验（门禁开拒、门禁关收）。只验一侧的判据一律不算数（硬约束①） |
| ② | **判据落在答案文本上就等于测蒙对** | H2 用「文字正确但取证不足」的答案反测；全部断言落在轨迹与假站点请求记录上 |
| ③ | **工具执行层的假站点被复制成两份后各自漂移** | Phase 3 第一项强制「**工具执行层那份**只有一份」（不是「全仓只有一份」——种子与定制包另有自己的假件，不动），并复跑 `tests/tools` 证明零回归 |
| ④ | **动 `tests/tools/conftest.py` 会碰到 P1.0a / P1.3 已收口的判据面** | 该路径不在红线内，但改动后必须复跑 `pytest tests/tools -q`；若出现任何回归，**回退该处置、改用不动 conftest 的方案**，不许顺手改别人的断言 |
| ⑤ | **活端点单次实跑成本 9.7 万–12.8 万 token** | 只跑一次；跑不了就照实记「未验证」，不补跑、不采样 |
| ⑥ | **L3 的已知逃逸口（只描述积压不报数字）** | §1.3 原样带进产品面并在 §7.8 复述；**不擅自扩大 L3 口径**（改规则措辞属人的裁定面） |
| ⑦ | **`lineage` 档放行的模型在本项目两跳题上是 1/6** | D1 的残余风险已登记；**不代人处置** STATE §3 那条 `[open]` |
| ⑧ | **WBS §4 P1.4 的 🔴 验收本 plan 交付不了** | Phase 4 按 P1.0a 先例交接给人；收口时**不得**声称该验收已满足 |

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-24）
  —— 12 条 blocking。**逐条处置**：
  ① H4 的 `prompt + completion == total` **恒真**（`Usage.total` 就是这个计算属性）→ 改判端点自报的 `raw["usage"]`；
  ② 断言体与门禁文件**同名 basename 会让 `pytest` 整轮收集失败**（评审实测 `import file mismatch`）
  → 改名 `test_evidence_gate_single_hop_body.py`；
  ③「skip → fail」在本 plan 不适用（断言体是假 transport，没有 live skip）→ 交接说明改写并点名需人复核；
  ④ D5 的兜底路径 `from tests.tools.conftest import ...` **不成立**（`tests/` 不是包）
  → 换成 `tests/conftest.py` + 根下 helper，或按路径加载（`3b6d071` 先例）；
  ⑤「全仓只有一份 `FakeSite`」在基线上就是假的（`tests/unit` 另有两份 `FakeSite` + 三份 `FakeSiteClient`）
  → 收窄为「工具执行层那份只有一份」并把既有的列进来标明不动；
  ⑥ `DenialBreaker.record()` 不传 `doctype` → 所需权限清单是空的，H3 只验了一半 → 新增 `Decision` D6 + H3 加严；
  ⑦ H1 的「门禁关」没有机制、且与「导出面只有一个入口」冲突 → 应新增 `Decision` D7；
  ⑧ M1–M8 只被引用未被定义（等于允许执行期看着自己的实现现编）→ 应把八个变异逐字写死；
  **⚠️ ⑦ 与 ⑧ 在第一轮修订里因脚本中途失败而实际未落地**，由第二轮评审当场查出（见下）；
  ⑨ 失效归属漏了 §7.6 / `orchestration/__init__.py` / `contracts.py:20-21` → Phase 4 改为**四处**一起改准；
  ⑩ 验证集漏了 `ruff`（新增代码在 CI `lint` 作用域内）→ 三条命令写进 Phase 3 与 Closure Gates；
  ⑪ 第二条 Deferred 缺重开事件 → 补；
  ⑫ 基线 sha 已过期（起草期间人连提三笔）→ 新增 §1.0「执行前必做：重取基线」。
  另采纳 8 条非阻断项（`llm.py:1` / `loop.py:50` 的引用改准、`SNAPSHOT_READ:155` 补进 ① 面、
  D2 绑定断言加「≥2 条分叉轨迹 + 同一性断言」、H3 的计数单位写死为 `execute` 次数、
  §1.7 新增「已有判据不重复覆盖」、`capabilities.py:38` 的前向引用就地关掉、
  WBS 状态源 `MD:p1-explain` 与 `missions/` 不一致照实记、墙钟数从基线里去掉）。
- Independent draft review iteration 2: **needs revision**（同一独立子代理，2026-08-24）
  —— 判定 12 条中 **9 条已关闭**（1/2/3/4/5/6/10/11/12），并当场查出 8 条仍开或新引入的问题。
  **逐条处置**：
  ① **D7 根本不在文件里**（第一轮脚本在一处 anchor 上断言失败、整批未写入，而 §9 已把它记成做了）
  → 已补上真正的 D7（Phase 3），并把 H1 改成三条断言（含「产品默认路径下 ② 门禁确实是开的」）；
  ② **M1–M8 同因未落地** → 已在 Phase 3 逐字写死八个变异；
  ③ **五处失效归属里有两处指错、一处不存在**：「熔断尚未接到任何真实控制循环上」全文只在
  `module-boundaries.md:205`（**§7.6 之内**，不是 §7.6a），`:204` 是已划掉的旧行
  → 已按 `grep` 实测逐条点名重写；
  ④ Phase 4 自相矛盾（新旧两条并存、「四处」却列了五条、Closure Gates 还写着两处）→ 已合并成一条五处清单，三处计数对齐；
  ⑤ H3 的计数单位在 §6 与 Phase 3 里打架（`execute` 次数 vs 站点请求数）→ Phase 3 改成 §6 写死的那条；
  ⑥ `FakeSite` 的收窄只改了 Exit Criteria，Proof 项与 §8 风险 ③ 仍写「全仓只有一份」→ 两处一并改准；
  ⑦ §7.8 落点节仍写「D1–D5 五个 `Decision`」→ 改为 D1–D7，并要求 D6/D7 的残余风险进「判据缺口」小节；
  ⑧ **§9 记了没做的事** —— 这条是本轮最该记的一条：草案评审记录夸大已落地内容，
  与收口规则要防的是同一种失败。已把 ⑦⑧ 两条改写成「应做但未落地」，并以本行记录真正的落地。
  另新增 §1.7a：起草期间人追加的「判自由文本前先跑通标注集」一节，逐条说明本 plan 全部判据
  落在该节自己写的**结构化事实**例外一侧，且不为「判答案对不对」开口子。
- Independent draft review iteration 3: **acceptable as-is** —— **共识达成**（同一独立子代理，2026-08-24）
  —— 逐条在文件里核实而非采信声明：D7 真实存在且 H1 的第三条断言正好堵住 (B) 的洞；
  M1–M8 八个各自映射到已有的 Proof 项，**没有一个是孤儿**；**五处失效归属逐处对着仓库验过**
  （「尚未接到任何真实控制循环上」全文只在 `module-boundaries.md:205`；
  §7.6a 里「接缝只有单侧」在 `:270` 确实存在；幻影站点已消失）；Phase 4 两条已合并、三处计数一致；
  H3 计数单位、`FakeSite` 三处措辞、§7.8 的 D1–D7 均已对齐；§9 不再声称没做的事。
  §1.7a 的例外主张**被判为诚实**：本 plan 没有任何一条判据在判「答得对不对」。
  红线自查：无一执行项触及 `tests/gates/**` / `.github/workflows/**` / `missions/**` / `DECISIONS.md`，
  `STATE.md` 仅追加。**结论：可作为执行契约 → `Plan Status: active`。**
  另收两条非阻断记录（不再起一轮）：① L3 的触发确实对答案文本做数字抽取，但那是
  「抽取 → 结构化求值」，不是判对错，其已知漏口在 §1.3 与风险 ⑥ 已登记两次；
  ② §6 H1 写两侧而 Phase 3 要三条 —— 已就地在 H1 下加一句「判据集加强，假设未改写」。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.8 新增；§7.4 两条 ⚠️ · `module-boundaries.md` §7.6 那句 · `orchestration/__init__.py` 模块头（+ §7.6a 的「接缝只有单侧」）· `contracts.py` 模块头 **五处**失效归属改准）
- [x] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **0**（`预期红 0，绿 11` · `389 passed`）· `python3 -m pytest tests/tools -q` → **0**（`81 passed, 12 skipped`）· `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **0** · `python3 -m pytest tests -q -m "not live"` → **0**（`849 passed, 12 skipped, 21 deselected`）· Phase 4 的一次活端点实跑**已做**（`docs/evidence/p1-explain/`）
- [x] scoped verification is not conflated with full verification —— 活端点实跑**做了**，因此 H4 不判为未验证；但**验证范围仍有界，逐字记在这里**：那一跑**没有走到 ② 门禁的拒绝路径**（`forced_continues` 为空）、**没有触发熔断**（Administrator 不撞 403），那两件由 `tests/unit` 判据证明；且**只跑一次，不做多次采样**，不得读成「活端点上的稳定行为」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§9 三轮，第三轮 `acceptable as-is`）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— ⚠️ **未做，留白照实记**。本轮执行环境不具备独立子代理（执行器被明确约束不得自行派生代理），沿用 P1.3 首次收口的做法：**不由执行者自审冒充独立审计**。补做条件与记录位置见 §12
- [x] closure evidence exists in files（`docs/evidence/p1-explain/` · `docs/architecture/module-boundaries.md` §7.8 · `docs/masterplan/STATE.md` §3 · `docs/logs/2026/08-24.md`）
- [x] **红线自查**（基线 `6b07889`，`git diff --name-only 6b07889 -- <pathspec>` + `git status --porcelain -- <pathspec>` 两条都跑）：`tests/gates/**` · `.github/workflows/**` · `missions/**` · `docs/masterplan/DECISIONS.md` **四个 pathspec 均无输出**；`git diff --numstat -- docs/masterplan/STATE.md` → `7	0`（**删除列为 0**，只有追加行）。⚠️ 执行期间人又提了两笔（`dc7077c` → `tools/loop-supervisor.sh`；`548cca6` → `docs/masterplan/04-RUNBOOK.md`），**两笔都不属本 plan，loop 一个字未动它们**

## 11. Deferred But Adjudicated

### WBS §4 P1.4 的 🔴 `tests/gates/test_evidence_gate_blocks_single_hop.py`

- Classification: `out-of-scope improvement`（红线 1 禁止 loop 创建，非能力问题）
- Why Not Blocking Closure: 本 plan 交付其断言体与交接说明；P1.0a 已有同形态先例（人补齐 + `Gates-Change-Approved-By:`）
- Successor Required: `yes` —— 由**人**创建该文件
- 重开条件：人补齐该门禁文件之后，本 plan 的 §7.8「判据缺口」小节与 STATE §3 对应行须由人或后继 plan 收口

### `tests/unit` 之外的判据覆盖面（`tests/tools` / `tests/routing` / `tests/context` 进不了 `commands.test`）

- Classification: `watch-only residual`
- Why Not Blocking Closure: `missions/*.json` 是 blocked，loop 无权改；STATE §3 已有三条 `[open]` 覆盖，本 plan **不重复登记**，且本 plan 自己的判据**已选进 `tests/unit`** 从而不新增这类欠账
- Successor Required: `no`（由人处置既有的三条 `[open]`）
- 重开条件：**人把 `tests/tools` / `tests/routing` / `tests/context` 接进 `missions/*.json` 的
  `commands.test` 之后** —— 届时 D5 可以重估是否仍需绑死 `tests/unit`

## 12. Closure

Status Note: **收口（2026-08-24，基线 `6b07889`）。四个 Phase 全部执行完，判据全绿。**

- **交付面**：`agenerp/explain/`（`gate.py` 事实采集面 · `loop.py` 控制循环本体 ·
  `__init__.py` 只导出 `explain` 与 `ExplainResult`）+ `tests/unit/` 三个文件（16 条判据 + 共用假件）。
- **命令原文 + 退出码 + sha**：见 §10 第三条与 Phase 3/4 的执行记录，逐条抄自终端，不复述。
- **§6 的 H1–H4 全部吻合，假设一个字未改**；**M1–M8 八个全部被打红，无一需要补断言（没有 M9）**。
- **Non-Goals 逐条守住**：没做成本记账判据（Non-Goals 1，`max_turns` 与 `Usage` 只是载体，
  收口不声称做过失控闸或成本上限）· 没做巡检器/洞察 Agent · 没做 Desk 侧边栏 ·
  **没改 `EVIDENCE_GATE` 三条规则的措辞、没改 `ANSWERING_TOOLS`、没改十个契约的任何一条** ·
  **一条业务数据都没写**（活端点实跑只调只读工具，`create_doc` / `ensure_doc` /
  `delete_custom_field` 一次都没调）· **`tools/experiments/p1_entry_gate/` 一个字未动** ·
  **没收窄 `agenerp/routing` 的导出面**（F8 那条 `[open]` 不代人处置）·
  **`missions/**` / `.github/workflows/**` / `tests/gates/**` / `docs/masterplan/` 已有行一律未动**。
- ⚠️ **两件明确不声称的事**：① WBS §4 P1.4 那条 🔴 **未满足**（本 plan 未创建门禁文件，见 §11）；
  ② 活端点那一跑**没有**证明「门禁拦得住单跳」与「熔断会被触发」。

Closure Audit Evidence:

- Auditor / Agent: **未做 —— 照实留白，不由执行者自审冒充独立审计。**
  本轮执行环境明确约束执行器不得自行派生子代理，`docs/context/ai-autonomy-policy.md` 的
  Reviewer availability = `subagent` 因此在本轮不可得。**沿用 P1.3 首次收口的做法**
  （那次同样留白，后由独立会话补做并记进 plan 的另一节，旧记录保留不改写）。
- Evidence: 无。**补做条件**：具备独立子代理（fresh session、不带实现上下文）时，
  由它在本 plan 的基线上复跑 §10 第三条那四条命令、自出独立探针（不复用 M1–M8），
  记录另起一节追加，**本节一个字不改写**。
- **代偿控制（照实记，不当作等价物）**：三轮独立草案评审（§9，第三轮 `acceptable as-is`）+
  M1–M8 全红 + 判据落在 `tests/unit`（**同时进 `GATE_VERIFY` 与 CI**，这是本批相对前四个工作项的加严项）+
  STATE §3 的 needs-human 行。

Follow-up:

- **由人创建** `tests/gates/test_evidence_gate_blocks_single_hop.py`（红线 1）——
  断言体与加载片段已交付，见 §11 与 `tests/unit/test_evidence_gate_single_hop_body.py` 的模块头。
  ⚠️ 其中「纯路径加载、无 live 语义是否仍满足那个 🔴」**由人裁定**，loop 不替人拍板。
- **补做独立关闭审计**（见上）。
- 以上两条**都不是本 plan 确认的缺陷** —— 一条是红线禁止 loop 做的，一条是环境不具备。
