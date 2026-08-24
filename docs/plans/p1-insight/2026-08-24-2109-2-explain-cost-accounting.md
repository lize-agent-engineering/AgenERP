# P1.7 单次解释成本记账（记账但不拦截，D-18）+ 失控闸

> Plan Status: active
> Mission: p1-insight
> Work Item: 9. **单次解释成本记账**（记账但不拦截，D-18）（P1.7）
> Execution Order: 2 / 2（本批第二个；与同批第一个 `2026-08-24-2109-1-industry-pack-v0-discrete.md` **无相互依赖**。⚠️ **代码文件集合不相交，但三处文档落点重合**：`docs/architecture/module-boundaries.md`（两个 plan 都要新增落点节）· `docs/masterplan/STATE.md`（只追加）· `docs/logs/2026/08-24.md`。→ **串行执行**，且开写前**重读当时的最大节号**再顺延，避免撞号）
> Last Reviewed: 2026-08-24（起草基线 sha `928a888`，`git status --porcelain` 无输出）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 9 与「P1.7 已按 D-18 改为『记账但不拦截』」一节 · `docs/masterplan/02-WBS.md` §4 **P1.7 行** · `docs/masterplan/DECISIONS.md` **D-18 / D-11**
> Related: 前置 P1.4（已 `completed`，交付 `agenerp/explain/`）· 同批第一个 P1.6（无依赖）
> Audit: required

## 0. 执行前必做：重取基线

起草基线是 sha `928a888`。**开工第一件事是重读仓库**，把 §1 每一条与当时的实际代码逐条核对，
不吻合的就地改写 §1 并把改动记进 `## Draft Review Record` 的续行（照 P1.5 §0.1 列一张对照表）。

**必须重新实读、不许凭本文件转述的五处**：

1. `agenerp/explain/loop.py` 的 `ExplainLoop.run()` —— **`self.adapter.chat(...)` 的调用点有几个**
   （起草期实读：**一个**，在 `run()` 的主循环里）。§6 的 H1 与 D1 全建立在这个数上。
2. 同文件的四个 `STOP_*` 常量与四条返回路径（`answered` / `permission-breaker` / `max-turns` / `model-error`），
   以及 `_run_tools()` 里熔断早返回那一段 —— H1 预测的漏记点在那里。
3. `agenerp/routing/adapter.py` 的 `Usage`（`total = prompt + completion`，**reasoning 是 completion 的细分**）
   与 `usage_of()`；`capabilities.py` 的 `is_reasoning_model`。
4. `agenerp/context/session.py` 的 `usage_total`（逐轮 `Usage.plus()`）。
5. `docs/evidence/p1-explain/live-run-01.json` 的 `usage_total` 与 `per_call_ledger[]`
   —— H2 的重放夹具就是它。

**开工前四条基线命令**（改一行代码之前先跑，把退出码与数字抄进 §0.1）：
① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
② `python3 -m pytest tests/contracts -q`
③ `python3 -m pytest tests/tools -q`
④ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`

## 1. Current Baseline

以下每条本轮实读（起草基线 `928a888`）。

### 1.1 D-18 把 P1.7 从「上限」改成「记账」，并**另外钉死了两件事**

`DECISIONS.md` D-18 逐字：判据从「成本 ≤ X」变成「**成本可观测**」；
⚠️「**不许退化成『跑通就算』**：判据必须能挡住『只记 `completion` 不记 `reasoning`』这类假实现
—— D-11 实测 `qwen3.6-plus` 回两个字也烧约 195 reasoning token」；
⚠️「**不拦成本 ≠ 不拦失控**……单次解释的**工具调用轮数上限**仍须存在……
**两者的判据分开写，不许合并**」。
`STATE.md` §3 的 `[resolved] 2026-08-24T09:08Z` 一行把同样两条又钉了一遍。
→ 本 plan 因此是**两个交付面共一条结果面**：记账（可观测）与失控闸（有上限），
**判据分两组写、分两组跑，收口时分开陈述**。
⚠️ **guide Minimum Rule 4（一个 plan 一个结果面）的裁定写在这里**：两者**不拆**。
依据：同一条 WBS 行、同一个 roadmap 工作项 9、都落在 `agenerp/explain/loop.py` 这一个模块，
且 §6 H4 ③「失控闸停机时账仍完整」把两者的行为契约**耦合在一起** —— 拆开就没人证明这一条。
D-18 逐字要求的是**判据分开写**，不是 plan 分开写。
⚠️ **拆分触发条件写死**：若 Phase 2 的默认值需人裁定而阻塞，**不许**把 Phase 1 拖成 deferred，
按 guide Minimum Rule 10 走**记录在案的范围变更**，把 Phase 2 整体移交具名后继 plan。

### 1.2 三项 token 的**口径**已经由 P1.1 定死，本 plan 不许再定一次

`agenerp/routing/adapter.py` 的 `Usage` docstring 逐字：`reasoning` 是 `completion` 的**细分**，
不是第四个桶；`total = prompt + completion`（与端点自报的 `total_tokens` 一致），
**绝不再把 reasoning 加一遍**；实读回包样例 `{"prompt_tokens": 15, "completion_tokens": 178,
"total_tokens": 193, "completion_tokens_details": {"reasoning_tokens": 173}}`。
`usage_of()` 逐字：`reasoning_tokens` 缺失时回 0，**不回退成把它算进 completion**。
→ 本 plan **不改 `Usage`**（改它会让 `tests/routing` 的既有判据与本 plan 的账目同时漂移）。

### 1.3 今天有「载体」，没有「账本」

- `ConversationSession.usage_total`（`agenerp/context/session.py:144`）逐轮 `Usage.plus()` 求和；
- `ExplainResult.usage` 读它，docstring 逐字「**不自己写三项加法**」；
- `ExplainTrace.turns[]` 里每条带 `usage`（`answer` 与 `tools` 两种 kind）；
- `agenerp/explain/loop.py` 模块头逐字：「`usage` 同理 —— 这里只有**载体**……
  **成本记账判据归 P1.7**」，且「**`max_turns` 只为防跑飞，不是失控闸**……那套判据归 P1.7，
  本模块不声称做过它」。

→ **P1.4 已经把这两件事显式记成欠账并指名归 P1.7。** 本 plan 是它的收口方。

### 1.4 「每次调用的账」这件事**目前只存在于一次性脚本里**，不是产品行为

`docs/evidence/p1-explain/live-run-01.json` 有 `per_call_ledger[]`（七条，每条带
`usage` / `endpoint_total_tokens` / `endpoint_reasoning_tokens` / 两个 `*_matches_endpoint` 布尔），
`README.md` 把它记作 H4 的「账目核对面」。但 `grep -rln "per_call_ledger"` 全仓只命中
**那两个文档文件**，产品代码里**没有**这个结构 —— 它是 P1.4 那一跑的临时脚本产物，
脚本本身没有进仓。
→ **本 plan 的第一件事就是把它变成产品制品**：同样的账，由 `agenerp/` 里的代码产出，
可复算、可判据、可在任何一次解释上拿到。
→ **顺带的好处（H2 靠它）**：那七条是**本项目实测**（D-16）的真实端点数字，
可以当成一份**离线重放夹具**，让账本在没有凭据的环境里也能被真实数据判一次。

### 1.5 失控闸今天**不存在**，`max_turns` 挡不住它要挡的东西

实读 `agenerp/explain/loop.py`：`MAX_TURNS = 25` 限的是**主循环轮数**；
`_run_tools()` 对**一次回复里的每个 `tool_call`** 逐个执行，
`trace.execute_calls`（`_execute_one` 里 `+= 1`）**只计数，不设限**。
→ 一次回复携带 K 个工具调用时，单次解释的 `execute` 次数上界是 `max_turns × K`，
而 K 由模型决定 —— **没有任何一处对「工具调用总数」设限**。
熔断（`DenialBreaker`）只在**连续权限拒绝**上触发，不覆盖「调得通但陷入循环」。
→ D-18 要的「工具调用轮数上限」**确实缺失**，不是「已有但没判据」。

### 1.6 「成本上限」这个措辞：**owner doc 与产品代码面逐行处置，其余按类处置**

`grep -rn "成本上限"`（排除 `.git` 与本批两个 plan）实读**十九处**。
**逐行处置的是 owner doc 与产品代码那七处**（下表 ①–④⑥⑦⑧）+ **一处非字面命中**
（表里的 ⑤：`loop.py:26-28` 写的是「工具调用轮数上限」「成本记账判据归 P1.7」，
不含「成本上限」四个字，但**落地即失效**，故一并逐行处置）。
**其余十二处按类处置，逐类点名，不沉默**（见表后一段）。
Minimum Rule 1 的 inventory 要求由「八行逐行（其中七行是字面命中）+ 十二处逐类」两段共同满足：**7 + 12 = 19**，对得上。

| # | 位置 | 现文（逐字要点） | 处置 |
|---|---|---|---|
| ① | `docs/architecture/model-management.md:55` | 「**P1 的验收标准必须包含单次解释的成本上限**，与正确率并列」 | **改准**（Phase 3 `Fix`），指名 D-18 |
| ② | `docs/architecture/model-management.md:213` | 「前者是能力，后者是计费形态（**P1.7 的成本上限**读后者）」 | **改准**（Phase 3 `Fix`） |
| ③ | `agenerp/routing/capabilities.py:60` | 「P1.7 的成本上限读的是这一位」（②的**代码孪生句**） | **改准**（Phase 3 `Fix`；只改注释，不动 `is_reasoning_model` 的行为与声明） |
| ④ | `agenerp/routing/adapter.py:51` | 「折掉这一位，P1.7 的成本上限就只能按『输出 178 token』去算」 | **改准**（Phase 3 `Fix`；只改注释，**不动 `Usage` 口径**，见 Non-Goal 2） |
| ⑤ | `agenerp/explain/loop.py:26-28` | 「`max_turns` 只为防跑飞，不是失控闸……那套判据归 P1.7，本模块不声称做过它」「成本记账判据归 P1.7」 | **落地即失效**（P1.7 就落在这个文件里）→ **改准**（Phase 3 `Fix`） |
| ⑥ | `docs/backlog/implementation-roadmap.md:117` | 「**单次解释的成本上限**（与正确率并列的验收项）」 | **不改，归属交人**：该文件是全局阶段索引，roadmap 自己写着「由人维护」；本 plan 在 STATE §3 的 needs-human 里点名它 |
| ⑦ | `docs/backlog/p1-insight-roadmap.md:64` | 「成本上限须按 reasoning token 计」 | **不改，归属交引擎/人**：这是 mission roadmap 的静态说明段，同文件下方已有 D-18 的「记账但不拦截」一节；两处并存会误导，故在 needs-human 里一并点名 |
| ⑧ | `tests/context/test_session.py:117` | 测试 docstring：「折掉它，P1.7 的成本上限只能按可见输出去算」 | **不改**：判据行为正确，只是措辞引旧口径；改它要动 P1.2 的判据文件而无行为收益。**理由在此留痕，不沉默** |

**其余十二处的类级处置（逐类点名，一处不动）**：
- **实验设施**：`tools/experiments/p1_entry_gate/loop.py:14` —— **一行不动**（P1.4 已立的纪律：
  实验设施是历史证据，不随产品演进改写）。
- **历史记录，改了就是篡改**：`docs/analysis/2026-08-19-pre-build-validation.md:206` ·
  `docs/audits/p1-insight/2026-08-24-P1.0-entry-gate.md`（两处）·
  `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`（两处）·
  `2026-08-24-1755-1-explain-agent-and-evidence-gate.md`（一处）·
  `2026-08-24-P1.0-entry-gate-experiment.md`（一处）—— **一律不动**。
- **blocked / 只追加面**：`docs/masterplan/DECISIONS.md`（两处，其中一处就是 D-18 自己在陈述被它取代的旧设计）·
  `docs/masterplan/STATE.md`（两处）—— **红线 3 / 红线 5**，一个字不改；`STATE.md` 只追加。

→ Minimum Rule 14：**确认的 owner-doc drift 不许降级成 follow-up** —— 表里 ①–⑤ 五处进 Phase 3 的 `Fix`。
⚠️ **只改「上限」那半句**：§12.2 那张 Spike 02 的成本表与「没有前缀缓存，解释 Agent 在经济上不成立」
的结论**一个字不动** —— 那是实测，没有被 D-18 推翻。

### 1.7 判据落点的硬约束（与 P1.4 / P1.5 同一条，不重复推导）

`missions/p1-insight.json` 的 `commands.test` 只跑
`tools/gates/check_expected_red.py` + `tests/unit`；`.github/workflows/**` / `missions/*.json` /
`tests/gates/**` 均为 `blocked`。
→ **判据一律落 `tests/unit/`**；WBS §4 P1.7 的 🔴 `tests/gates/test_explain_cost_accounting.py`
**本 plan 不得创建**，按 P1.0a / P1.4 / P1.5 的先例交付**断言体 + 交接说明**（Phase 3）。

### 1.8 洞察 Agent 走同一条循环，因此**自动**被记账覆盖

`agenerp/insight/attribution.py` 实读：归因走 `agenerp.explain.explain`（P1.5 的 D3，
「不另起循环」）。→ 账本挂在解释循环上，洞察侧不需要第二套。
⚠️ 但这也意味着：**记账口径改错会同时影响两个 Agent**，判据必须覆盖「经由 `insight` 进来的那条路径也在账上」。

## 2. Goals

1. 落地**单次解释的成本账本**：每次模型调用一条记录，`prompt` / `completion` / `reasoning`
   **三项分开记**，可按**一次解释**汇总。**不设阈值、不拦截**（D-18）。
2. **一次模型调用都不许漏账**：包括模型报错那一次、熔断停机那一次、轮数用尽那一次。
   判据形态写死为**计数探针**（模型调用次数 == 账本条目数），不是「看代码里都写了」。
3. **账目对得上端点自报的数**：每条记录与该次回包的 `raw["usage"]` 逐次相等
   （`prompt` / `completion` / `reasoning` 三项都判），并能重放 P1.4 那一跑的七次调用。
4. **失控闸**：单次解释的**工具调用总数上限**，触发时以**专属停止原因**停机、留痕，
   **且成本账照记**（不拦截 ≠ 不记账，也 ≠ 不停失控）。
5. **两组判据分开写、分开跑、分开陈述**（D-18 逐字：「不许合并」）。
6. 判据落 `tests/unit/`；WBS §4 P1.7 的 🔴 门禁交付**断言体 + 交接**（红线 1）。
7. owner doc 的两处「成本上限」drift 改准（§1.6）。

## 3. Non-Goals

1. **不设成本阈值、不拦截、不降级模型**（D-18 逐字）。账本里**不许出现**任何
   「超了就……」的分支 —— 那是将来用已记的账定阈值时的事。
2. **不改 `Usage` 的口径**（`reasoning` 是 `completion` 的细分；`total = prompt + completion`）。
   改它会同时动 `tests/routing` 的既有判据（§1.2）。
3. **不做按租户/角色的配额**（`model-management.md` §12.2 列的那条属更后面的阶段，
   没有 DocType 承载，也没有验收命令）。
4. **不做成本采样实验**（多次跑、算分布）。那是实验，属另一个 plan（D-16 与 P1.4 §8 风险⑤同一条纪律）。
5. **不改 `max_turns` 的语义**。它是「防一次跑飞」的既有物；失控闸是**另一个**上限，
   两者必须能**独立触发**（H4），不许把失控闸实现成「把 `max_turns` 改小」。
6. **不动** `agenerp/explain/gate.py` 的三条证据规则、`ANSWERING_TOOLS`、十个契约的任何一条。
7. **不写任何业务数据**（②端只读）。
8. **不动** `missions/**` / `.github/workflows/**` / `tests/gates/**` / `docs/masterplan/` 已有行
   （`STATE.md` 只追加）· **不动** `tools/experiments/p1_entry_gate/`。
9. **不判自由文本**（答案对不对不在本 plan 的判定面上）。

## 4. Task Route

- Type: `implementation-only change`（D-18 已把设计裁定完，本 plan 落成代码与判据）+ owner-doc `Fix`
  ⚠️ **条件性升格**：若 D1 选定 (i)（给 `RoutingError` 加结构化属性），则动到 **P1.1 的导出面**，
  该 Phase 按 `app-layer design change` 对待 —— 落点节须记这次导出面变更，且验证命令加 `tests/routing`。
- Owner Docs: `docs/architecture/model-management.md` §12.2 / §12.5 ·
  `docs/architecture/module-boundaries.md`（**新增落点节，编号执行期顺延**）· `docs/masterplan/DECISIONS.md`（**只读**）
- 额外触及的代码面（§1.6 的③④⑤与 D1 的 B1 分支）：`agenerp/routing/capabilities.py`（**仅注释**）·
  `agenerp/routing/adapter.py`（**仅注释**；`Usage` 口径不动）· `agenerp/routing/errors.py`
  （**仅在 D1 选定「给 `RoutingError` 挂结构化 `usage`」时**）· `agenerp/explain/loop.py`
- Skill Selection Basis: `docs/skills/README.md` 无对应方法件；草案评审与关闭审计走独立子代理。各 Phase 记 `Skill: none`。

## 5. Infrastructure And Config Prereqs

- Phase 1 / Phase 2 全部在假 transport 上跑：零网络、零凭据、零 docker。
- **H2 的重放夹具是仓内已有的 `docs/evidence/p1-explain/live-run-01.json`**，无需凭据。
  ⚠️ 该文件是 P1.4 的**证据**，本 plan **只读它，一个字不改**。
- Phase 3 的活端点跑一次需要 `.env` 的 `DASHSCOPE_API_KEY` 与 `AGENERP_*` 四个变量。
  **凭据齐备时必做**（D-16：以本项目实测为准）；不齐备时照实记「未跑 · 未验证」
  并在 §10 逐字写 `verification scope limited`。**没有第三种处置。**
- 凭据**绝不进 git、绝不打印进日志或轨迹**（`missions/p1-insight.json` 的 `p1_specific` 逐字）。

## 6. 开工前写死的假设（硬约束②）

**逐字写死在跑之前，事后逐条对照，不许事后改写。**

- **H1（漏账点的预测）**：现行实现里存在**至少一条**「模型调用发生了、但账上没有」的路径。
  逐条预测写死：
  ① `STOP_MODEL_ERROR`（`adapter.chat` 抛 `RoutingError`）—— **预测漏账，且分成两个子形态**
  （起草期实读 `adapter.py:154-162` 与 `routing/errors.py` 确认）：
  **①a 连不上端点 / 配置不全** —— 那次**真的没有 usage**，记 0 是对的；
  **①b「空回答」** —— 端点**已经回包、usage 真实存在**（`adapter.py:158-161` 甚至把
  `usage_of(...).as_dict()` 拼进了报错消息里），但 `RoutingError` 是个裸 `RuntimeError`
  （`errors.py` 无任何结构化字段），token 数**只以字符串形式存在**、拿不回来 ——
  账本在这条路径上会**系统性偏低**，而 D-11 点名的推理模型正是「回两个字也烧 195 reasoning token」；
  ② 熔断早返回（`_run_tools` 里 `breaker.tripped` 那一段）—— **预测：`session` 记了、`trace.turns` 没记**；
  ③ `STOP_MAX_TURNS` —— **预测不漏**（每轮都走 `with_turn`）；
  ④ `STOP_ANSWERED` —— **预测不漏**。
  执行期逐条实测对照，**吻合与否照实记**；**预测错了（其实都不漏）就照实写「不吻合」**，
  并把该条判据留作守护性回归，不许回头改这四条预测。
- **H2（两个形态，缺一不可）**：
  **H2a（真实数据重放，判到 per-entry）**：把 `docs/evidence/p1-explain/live-run-01.json` 的
  `per_call_ledger[]` 七条喂进账本，**逐条三项各自相等**（七条 × `prompt`/`completion`/`reasoning`
  = **21 个字面期望值写进判据**），汇总再**逐字等于** `40,885` / `4,310` / `2,784` / `45,195`。
  ⚠️ **只判汇总不够**：「每条都记 `reasoning = 0`、汇总另从 `session.usage_total` 取」的假实现
  在只判汇总的判据下是**全绿**的。
  ⚠️ 逐条 `total` 判的是**端点自报的 `endpoint_total_tokens`**，不是 `Usage.total` 那个恒真式
  （照抄 `docs/evidence/p1-explain/README.md` 那句「⚠️ `prompt + completion == total` 那种写法是恒真的」）。
  **H2b（走完整 `adapter.chat → 账本` 链路）**：用假 transport 回**OpenAI 线上形状的原始 body**
  （含 `completion_tokens_details.reasoning_tokens`，数值复用那七次的实测数），
  断言对象是**测试里写死的字面数字**。
  ⚠️ **H2b 不可省的理由**：`live-run-01.json` 存的是**解析后的 `Usage`**、没有原始回包，
  而账本若实现成 `entry.usage == usage_of(reply.raw["usage"])`、记的又正是 `reply.usage`
  （`adapter.py:167`），那条断言**恒真**。只有让原始 body 走完整条链路才判得到解析这一段。
  ⚠️ **H2 证明了什么 / 没证明什么**（照 P1.4 README 的形制，收口时逐字写）：
  那七次**全是成功路径**，**没有异常路径、没有熔断路径、没有原始回包** ——
  这三件由 H1 与 Phase 1 的计数探针证明，**不由 H2 证明**。
  ⚠️ **H2a 的「逐条 `total == endpoint_total_tokens`」在重放夹具内部仍是近似同源的**
  （两个数都来自同一份落盘文件）—— 收口陈述**不许把它算成「与端点独立核对」**，
  那份功劳归 **H2b**（原始 body 走完整解析链路）与 **H5**（活端点）。
- **H3（假实现反测：只记 completion 不记 reasoning）**：把账本里 reasoning 那一位去掉/置零后，
  判据**必须由绿转红**。⚠️ **两个数据集**：① H2 的真实重放；
  ② 一个 `reasoning == 0` 的合成用例（非推理模型形态）——
  只有前者时，一个「reasoning 恒等于 completion 的某个比例」的假实现可能蒙混过关。
- **H4（失控闸与 `max_turns` 可独立触发）**：构造一个**每轮回 K 个工具调用、永不作答**的假模型，
  使得**轮数远没到 `max_turns`**（例如 K 大、轮数小）时工具调用总数就超过上限。
  预测四件事同时成立：① `execute` 的实际次数**不超过**上限；
  ② 停止原因是**失控闸专属的那个值**，不是 `max-turns`、不是 `permission-breaker`；
  ③ **成本账仍然完整**（停机不清账，不拦截也不丢账）；
  ④ 反向用例：把上限调大到够用时，同一个假模型跑到 `max-turns` 停 —— 证明两个闸**各判各的**。
  ⚠️ **反向用例必须也在「默认值」下成立**：每轮只发一次工具调用的假模型，
  在**不传上限**时应当停在 `max-turns` 而不是失控闸 —— 这是 D3 那条严格下界的可观测形态；
  ⑤ **经产品入口 `explain(...)` 跑一次**（**不显式传上限**，`max_turns` 给一个大值如 `10_000`）：
  同一个假模型仍被**默认上限**截住，`trace.stopped` 等于那个新常量。
  ⚠️ ⑤ 不可省的理由：①–④ 全都显式构造 `ExplainLoop` 并传上限，
  一个「默认值 = 无限」的实现能通过①–④的全部四条。
- **H5（活端点，凭据齐备时必做）**：真跑一次解释，账本每条与端点自报的 `raw["usage"]`
  逐次相等，三项均 > 0（D-11：推理模型 reasoning 必 > 0）。
  ⚠️ **不预测总量落在哪个区间**：roadmap 记的 9.7 万–12.8 万与 P1.4 实测的 45,195
  相差一倍以上，本 plan **不拿任何一个当预期**，实测多少记多少（D-16）。

## 7. Execution Plan

### Phase 1 — 账本：每次调用一条记录，一次解释一份汇总

Status: planned
Targets: `agenerp/explain/`（账本模块，落点执行期按 D1 定）· `agenerp/routing/errors.py` + `agenerp/routing/adapter.py`（**仅在 D1 选定 (i) 时**，且只加结构化字段、不动 `Usage` 口径）· `tests/unit/test_explain_cost_ledger.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: 无（P1.4 已 `completed`）

- [ ] **Decision D1 · 账本的落点与采集面。**
      备选：(A) 挂在 `ChatAdapter` 上（每次 `chat()` 自动记）—— 覆盖面最大，
      但那是 P1.1 的导出面，改它会同时动 `tests/routing`，且「一次解释」这个聚合概念不在那一层；
      (B) **挂在解释循环上、采集面只有一处**（选定倾向）：`ExplainLoop.run()` 里
      `self.adapter.chat(...)` 是**唯一调用点**（§0 要求重新实读确认），
      在它的**成功与异常两条出口**各记一次；
      (C) 从 `ConversationSession` 反推 —— **否决**：session 只记「成为了一轮对话」的调用，
      异常那次根本没有 turn，反推必然漏（H1 ① 预测的正是这个）。
      **选定与理由、被否决项的代价、残余风险执行期写进本条。**
      ⚠️ **不管选哪个，「事实采集面只有一份」是硬要求**（照抄 P1.4 的 D2：
      两处求值、一份事实面），两份账会漂移。
      ⚠️ **本条必须一并裁定 H1 ①b（空回答路径）的处置，二选一、不许留白**：
      (i) 给 `RoutingError` 挂一个**结构化可选属性**，账本据此记真数（**`Usage` 的口径一个字不动**）。
      ⚠️ **实现形态写死，照字面做会当场循环 import**：`agenerp/routing/errors.py` 实读
      **不 import 本包任何模块**，而 `Usage` 定义在 `adapter.py`、`adapter.py` 又
      `from agenerp.routing.errors import RoutingError` —— 在 `errors.py` 里 import `Usage`
      即成 adapter ↔ errors 循环（`routing/__init__.py` 先 import adapter，会当场 `ImportError`）。
      → 形态定为：**`errors.py` 只加一个不带类型依赖的可选属性**（`usage: dict | None = None`，
      或 `TYPE_CHECKING` 下的前向注解），值由 `adapter.py:158-161` 抛出处 `as_dict()` 后注入。
      ⚠️ `errors.py` 是 P1.1 的导出面 —— **改后必须复跑 `python3 -m pytest tests/routing -q`**，
      并把它加进本 plan 的验证命令清单（§0 四条之外的第五条）；
      或 (ii) 明确**不做**，则在 §11 加一条 `watch-only residual`，
      **逐字写「空回答路径 token 恒记 0，账本对该路径系统性偏低」** + 重开条件。
      **不许出现第三种处置（沉默）。**
      ⚠️ **本条还必须裁定账本的导出面**（交接给人的断言体要写在一个稳定名字上）：
      `ExplainResult` 上叫什么、`ExplainTrace.as_dict()`（`loop.py:167-180`）里带不带它。
      理由：`agenerp/insight/attribution.py` 侧消费的是序列化后的 trace 字典
      （`tests/unit/test_insight_attribution.py` 读 `attributed.trace["stopped"]`），
      带不带账本直接决定断言体怎么写。
      - Skill: `none`
- [ ] **Decision D2 · `ExplainResult.usage` 是否改读账本。**
      现状读 `session.usage_total`（P1.4 的导出面，有既有判据）。
      备选：(A) 改读账本 —— 口径归一，但改了 P1.4 的既有行为；
      (B) 保留现状 + **加一条同源判据**断言两者在正常路径上相等，异常路径上账本 ≥ session。
      **两条分支的代价起草期即写死**（Rule 9 不许整条推到执行期）：
      **(A) 的代价** —— 改了 P1.4 已声明的读法，`loop.py:196-199` 的 docstring
      （「走 `ConversationSession.usage_total`……不自己写三项加法」）连带失效，属 owner-doc 连带修改；
      **(B) 的代价** —— 长期保留**两个数**，异常路径上两者必然不等，
      「哪个是权威」这件事要写进落点节，否则下游读错。
      **选定执行期定**，但**硬要求写死**：无论选哪条，都必须有一条判据钉住
      「两处数不许各算各的」（M7 的靶子），且 `tests/unit` 既有 414 条**一条都不许因此变红**。
      - Skill: `none`
- [ ] **Add** 账本：一次调用一条记录（三项 token + 模型名 + 第几轮 + 这次调用属于哪种出口），
      一次解释一份汇总。**汇总走 `Usage.plus()`，不自己写三项加法**（§7.7 的既有纪律逐字）。
- [ ] **Add** 异常出口的记账：模型调用抛错时，那次调用**照样在账上**（口径执行期定：
      记为「无 usage 的一次调用」还是「usage 未知」——**但不许悄悄不记**；
      选定口径与理由写进落点节）。
- [ ] **Proof H1** 四条路径逐条实测漏账与否，与 §6 的四条预测**逐条对照**，吻合与否照实记。
- [ ] **Proof（计数探针）** 用一个**自己计数**的假 transport / 假 adapter：
      `chat()` 被调用的次数 **== 账本条目数**。⚠️ 判在**可观测量**上，不是「读代码确认都写了」。
      覆盖四条出口各一例（含经由 `agenerp.insight` 进来的那条路径，§1.8）。
- [ ] **Proof H2a** 重放 `live-run-01.json` 的七条：**逐条三项各自相等（21 个字面期望值）**
      + 汇总逐字等于那四个数 + 逐条 `total == endpoint_total_tokens`。
- [ ] **Proof H2b** 假 transport 回**原始 OpenAI 形状 body**，走完整 `adapter.chat → 账本` 链路，
      断言对象是判据里写死的字面数字（挡住「记的就是 `reply.usage`」那条恒真断言）。
- [ ] **Proof H3** 两个数据集的假实现反测（真实重放 + `reasoning == 0` 的合成用例）。

Exit Criteria:

- [ ] H1 / H2 / H3 与 §6 原文逐条对照，吻合与否照实记
- [ ] D1 / D2 各有选定、备选、否决理由与残余风险
- [ ] 四条基线命令全退 0（§0），且 `tests/unit` 既有条数**一条未红**
- [ ] owner-doc 落地**延至 Phase 3**；本阶段不改任何 owner doc

### Phase 2 — 失控闸：工具调用总数上限（与成本判据分开写）

Status: planned
Targets: `agenerp/explain/loop.py`（新增上限与专属停止原因）· `tests/unit/test_explain_runaway_guard.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: Phase 1（**顺序理由**：失控闸触发时「账仍完整」是 H4 ③ 的一半，账本得先在）

- [ ] **Decision D3 · 上限的计量单位。**
      备选：(A) 主循环轮数 —— **否决**：`max_turns` 已经是它，D-18 要的是**工具调用**那一维
      （§1.5：一次回复可携带 K 个调用，轮数不设限于此）；
      (B) **单次解释的工具调用总数**（选定倾向）。⚠️ **计量对象必须在 (B1)「模型发起的工具调用数」
      与 (B2)「实际进入 `execute()` 的次数」之间点名选一个，并写明取舍**：
      起草期实读 `loop.py:413-419` —— **未知工具 / 被排除工具在 `trace.execute_calls += 1`
      （`:423`）之前就早返回**，因此选 (B2) 时，一个不断编造工具名的跑飞模型会让计数**恒为 0**、
      失控闸**永不触发**。选 (B2) 就必须补一条「未知工具刷屏」形态的判据，
      或在落点节**逐字登记**这条残余风险；
      (C) 每轮工具调用数 —— 否决：挡得住一轮暴涨，挡不住细水长流。
      ⚠️ **对上位文件措辞的重读必须留痕**：D-18（`DECISIONS.md`）与 WBS §4 P1.7 行都写
      「工具调用**轮数**上限」，而本 plan 按 §1.5 的实读把它读成「**工具调用**那一维」
      （轮数已由 `max_turns` 占用）。`DECISIONS.md` 是 blocked 面、**本 plan 一个字不改**，
      重读只写在这里与落点节；**收口时不得声称满足了 WBS 的字面措辞**，
      若人按字面读作「轮数」，须回到轮数口径重做。
      **默认值取多少、依据是什么，执行期写死并说明。依据只能是本项目实测**：
      P1.4 那一跑是 **8 次 `execute`** —— 这是**唯一**可引用的本项目数字，不许引用任何外部经验值。
      ⚠️ **取值必须同时满足两条下界，两段算术都要写出来**：
      (i) 对实测 8 次留出余量；
      (ii) **默认值 ≥ `MAX_TURNS + 1`**（`loop.py:52` 实读 `MAX_TURNS = 25` → 默认值 **≥ 26**）。
      ⚠️ **等号处不算数，必须严格大于 `MAX_TURNS`**：`loop.py:275` 是 `range(1, max_turns + 1)`，
      「每轮发一次工具调用」的正常形态下第 25 轮恰好是第 25 次调用 ——
      默认值取 25 且「达到上限即停」时，失控闸会**赶在 `STOP_MAX_TURNS` 之前**触发，
      产品默认路径上 `max-turns` **永不可达**，失控闸就地退化成一个更严的 `max_turns`，
      **那正是 D-18 禁止的合并**，H4 ④ 的反向用例也构造不出来。
      - Skill: `none`
- [ ] **Add** 失控闸：达到上限即停机，**专属停止原因**（新增一个 `STOP_*` 常量，
      不复用 `max-turns` / `permission-breaker`），并在轨迹里留痕（第几次、上限是多少）。
      **不拦成本、不改模型、不降级** —— 它只做「停下来」这一件事。
- [ ] **Add** 上限**可配置但有默认值**，且**产品入口 `explain()` 走默认值**
      （照抄 P1.4 的 D7：安全闸不给产品面开关；判据侧要构造就直接构造 `ExplainLoop`）。
- [ ] **Proof H4** **五件事**逐条判（不超上限 / 专属停止原因 / 账仍完整 / 反向用例走到 `max-turns` /
      **经产品入口 `explain(...)` 不传上限也被默认值截住**）。
- [ ] **Proof（两组判据分开）** 失控闸的判据落**单独一个测试文件**，成本判据落另一个，
      **互不 import 对方文件里的夹具**（D-18 逐字「判据分开写，不许合并」的可观测形态）。
      ⚠️ 共用 P1.4 交付的 `tests/unit/explain_fakes.py` **不算违反** —— 禁的是两组判据互相依赖，
      不是禁止复用既有公共假件。
- [ ] **Proof** 变异自查 **M1–M8，八个变异在此逐字写死**，不许执行期看着自己的实现现编：
      **M1** 只记 `completion` 不记 `reasoning`（D-18 点名的假实现）→ **由 H2a 的 per-entry
      `reasoning` 断言与 H3 一起打红**（⚠️ 只判汇总的判据对它可能是绿的，见 H2a 的告警）；
      **M2** 只在成功路径记账（异常/熔断出口漏记）→ 计数探针打红；
      **M3** 汇总写死成常量 → **必须用第二个数据集打红**（H2 的真实重放 + 一份数不同的合成账，
      单一数据集挡不住写死 —— P1.3 的 M6 与 P1.5 的 H1 都栽在这上面）；
      **M4** 把 `reasoning` 再加进 `total` 一遍（口径漂移）→ 逐条 `total == endpoint_total_tokens` 打红；
      **M5** 失控闸被实现成「把 `max_turns` 改小」→ H4 ② + ④ 打红（停止原因与反向用例）；
      **M6** 失控闸触发时把账清掉或不记 → H4 ③ 打红；
      **M7** 账在两处各算各的（账本与 `session.usage_total` 漂移）→ D2 那条同源判据打红；
      **M8** 账本记的是「打算调用」而非「实际回包」（发请求前记一条 0）→
      「每条记录等于该次回包的 usage」打红。
      任一变异打不红即说明判据有缺口，**就地补断言并登记为 M9…**，不许略过。

Exit Criteria:

- [ ] H4 **五条**逐条对照 §6 原文，吻合与否照实记
- [ ] M1–M8 逐个复跑**全部由绿转红**（打不红的就地补断言并登记）
- [ ] 两组判据在**两个文件**里，且互不 import **对方文件里**的夹具
      （共用 P1.4 已有的 `tests/unit/explain_fakes.py` **不在禁止之列**）
- [ ] 四条基线命令全退 0，`tests/unit` 既有条数一条未红
- [ ] owner-doc 落地**延至 Phase 3**（本阶段新增了一个产品可见的停止原因常量，文档在 Phase 3 一并落）

### Phase 3 — 活端点一跑 · 🔴 门禁交接 · owner doc 改准 · 日志

Status: planned
Targets: `tests/unit/test_explain_cost_accounting_body.py`（🔴 的断言体）· `docs/architecture/model-management.md` §12.2/§12.5 · `docs/architecture/module-boundaries.md`（新增落点节）· `docs/masterplan/STATE.md`（**只追加**）· `docs/evidence/p1-cost/`（活端点跑成时）· `docs/logs/2026/08-24.md`
Skill: `none`

- Item Types: `Fix | Add | Proof | Follow-up`
- Prereqs: Phase 1, Phase 2

- [ ] **Proof H5（活端点跑一次）** 真跑一次解释，账目逐次对上端点自报的 `raw["usage"]`，
      三项均 > 0；轨迹与账本落 `docs/evidence/p1-cost/`（照 `docs/evidence/p1-explain/` 的形制，
      含「证明了什么 / 没证明什么」两节）。**只跑一次**（成本量级已知，多跑是采样实验，Non-Goal 4）。
      凭据不齐备时照实记「未跑 · 未验证」+ §10 逐字写 `verification scope limited`，
      **且不创建 `docs/evidence/p1-cost/` 空目录或占位 README** —— 空壳读起来像证据。
- [ ] **Add（交接，红线 1）** WBS §4 P1.7 的 🔴 `tests/gates/test_explain_cost_accounting.py`
      **本 plan 不创建**。交付其**断言体**（放 `tests/unit/test_explain_cost_accounting_body.py`，
      照抄 P1.4 的 `test_evidence_gate_single_hop_body.py` 形制）+ 模块头里的**加载片段与交接说明**。
      ⚠️ 断言体必须覆盖 D-18 逐字要的那两件事：**三项都记了 + 能按解释汇总 + 缺任一项即红**。
      ⚠️ **「纯路径加载、无 live 语义是否仍满足那个 🔴」由人裁定**，loop 不替人拍板。
- [ ] **Add（交接）** 🔴「失控闸另算」那一条同样交接（WBS §4 P1.7 行第二个 🔴）：
      断言体与说明**单独一节**，不与成本那条合并（D-18 逐字）。
      ⚠️ **措辞照实**：`02-WBS.md:86` 的第二个 🔴 **没有给文件路径**（只有第一个 🔴 有
      `tests/gates/test_explain_cost_accounting.py`）。收口不得声称「一个不存在的文件未创建」——
      写作「一条有名、一条未命名，两条的断言体都已交付」。
- [ ] **Follow-up → STATE §3 追加 needs-human**（只追加），一条行里四个 bullet：
      ① 两条 🔴（一条有名、一条未命名）待人按路径加载（P1.0a / P1.4 / P1.5 三个先例）——
      触发条件：**人创建该门禁文件时**本条进入范围；
      ② `docs/backlog/implementation-roadmap.md:117` 的「单次解释的成本上限」由**人**改准
      （该文件由人维护，见 §1.6 ⑥）；
      ③ `docs/backlog/p1-insight-roadmap.md:64` 的同一措辞与同文件下方 D-18 那一节并存、会误导（§1.6 ⑦）；
      ④ `STATE.md` 那条 `[open] 2026-08-24T08:56Z` 的第 **③** 项仍逐字挂着
      「P1.7 的成本上限按哪个档位定」，已由 D-18 与本 plan 实质取代 ——
      **只追加一行指明，不改写那条 open**（红线 5）。
      **四个 bullet 各自的触发条件（Anti-Slacking 要求逐条点名）**：
      ① 人创建那两个门禁文件时 · ② 人编辑 `implementation-roadmap.md` 时 ·
      ③ 人或引擎回写 `p1-insight-roadmap.md` 时 · ④ 人处置那条 `[open]` 时。
- [ ] **Fix** §1.6 表里 ①–⑤ **五处**「成本上限」drift 全部改准，指名 D-18：
      ① `model-management.md:55` · ② `model-management.md:213` ·
      ③ `agenerp/routing/capabilities.py:60`（**仅注释**）· ④ `agenerp/routing/adapter.py:51`（**仅注释**）·
      ⑤ `agenerp/explain/loop.py:26-28`（落地即失效的那两句「归 P1.7 / 本模块不声称做过它」）。
      ⚠️ **只改文档不改代码孪生句 = 把本 plan 声称关掉的 drift 原地复制一份**，③④⑤ 不许略。
      ⚠️ **§12.2 的 Spike 02 成本表与「没有前缀缓存，解释 Agent 在经济上不成立」的结论一个字不动**；
      ⚠️ `Usage` 的口径、`is_reasoning_model` 的声明与行为**一个字不动**（Non-Goal 2）。
- [ ] **Add** 落点节（`module-boundaries.md` 新增一节，编号按当时最大编号顺延、收口时逐字记）：
      账本的采集面在哪、为什么只有一份、**导出面叫什么**（D1 裁定）、异常出口的记账口径
      （含 ①b 空回答那条的处置）、失控闸的计量对象（B1/B2 之选）与默认值的**两段算术**
      （对实测 8 次的余量 + 对 `MAX_TURNS + 1 = 26` 这条严格下界的余量）、
      **以及三句边界**：「记账 ≠ 拦截」「失控闸 ≠ 成本闸」
      「**本账本 ≠ `tools/gates/check_budget.py` 那个循环日预算停机闸**
      —— 后者是 7×24 循环自己的成本闸（会真停机），两者**不互读、不互写**；
      把两者接起来会同时造出 D-18 禁止的拦截路径并触及 `tools/gates/`」。
- [ ] **Add** `docs/logs/2026/08-24.md` 追加一条聚合日志。

Exit Criteria:

- [ ] H5 逐条对照 §6 原文，吻合与否照实记（未跑时逐字写「未跑 · 未验证」）
- [ ] 两个 🔴 的断言体 + 交接说明已交付，且**分成两节**
- [ ] §1.6 表里 **①–⑤ 五处** drift 改准（含 `capabilities.py:60` / `adapter.py:51` / `loop.py:26-28`），且不动那张实测表
- [ ] STATE §3 needs-human 已追加（只追加）· `docs/logs/` 已更新
- [ ] 四条基线命令全退 0

## 8. 风险

| # | 风险 | 处置（写死，不留「到时候再看」） |
|---|---|---|
| ① | **记账退化成「跑通就算」** | H3 两个数据集的假实现反测 + M1/M4；判据判**端点自报的数**，不判恒真式 |
| ② | **漏账**（异常出口最容易漏） | 计数探针（调用次数 == 条目数），覆盖四条出口 + `insight` 那条路径 |
| ③ | **两处账漂移** | D2 的同源判据 + M7 |
| ④ | **失控闸与 `max_turns` 被合并** | H4 ② ④ + M5 + 两组判据分文件（D-18 逐字） |
| ⑤ | **上限默认值拍脑袋** | D3 要求给出算术与本项目实测出处（P1.4 那一跑 8 次 `execute`），外部经验值一律不许引 |
| ⑥ | **改动打破 P1.4 的既有导出面** | D2 硬要求：`tests/unit` 既有 414 条一条不许因此变红 |
| ⑦ | **活端点一跑被读成「成本已优化」** | 本 plan 不做任何成本优化；实测多少记多少，**不与 roadmap 的 9.7 万–12.8 万作优劣比较**（P1.4 收口已有同一条教训） |
| ⑧ | **「空回答」路径的 token 拿不回来**（`RoutingError` 无结构化字段） | D1 二选一并留痕：给它挂结构化 `usage`，或在 §11 逐字登记「该路径系统性偏低」 |
| ⑨ | **失控闸计不到「未知工具刷屏」**（早返回在计数之前） | D3 点名计量对象；选 (B2) 就补该形态判据或逐字登记残余风险 |
| ⑩ | **默认上限取得比 `max_turns` 还严**（两闸事实上合并） | D3 写死下界：默认值 **≥ `MAX_TURNS + 1` = 26**（等号不算数，理由见 D3），两段余量算术都要写出来 |
| ⑫ | **D1 选 (i) 时改出循环 import**（`errors.py` ↔ `adapter.py`） | D1 已写死形态：`errors.py` 只加不带类型依赖的可选属性；改后必跑 `tests/routing` |
| ⑪ | **文档落点与同批第一个 plan 撞号** | 串行执行；开写前重读 `module-boundaries.md` 当时最大节号再顺延 |

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，不带起草上下文；
  2026-08-24）。七条 blocking，**逐条已改，无一条被驳回**（每条均由起草侧复核过原始出处）：
  **B1** `adapter.py:154-162` 的「空回答」路径上 usage **确实存在**却随 `RoutingError` 丢弃
  （`errors.py` 无结构化字段，token 数只以字符串形式活在报错消息里）→ H1 ① 拆成 ①a/①b 两个子形态，
  D1 增一条「二选一、不许沉默」的裁定，Targets 与 Task Route 条件性纳入 `routing/errors.py` + `adapter.py`；
  **B2** H2 只判汇总，per-entry 的 `reasoning` 从未单独断言 →「每条记 0、汇总另取」的假实现能全绿 →
  H2a 改为**七条 × 三项 = 21 个字面期望值**逐条判，M1 的打红面随之改准；
  **B3** `live-run-01.json` 只有解析后的 `Usage`、无原始回包且七次全是成功路径，
  账本若记的就是 `reply.usage` 则「与端点自报相等」是**恒真**（`adapter.py:167`）→
  新增 **H2b**（假 transport 回原始 OpenAI 形状 body，走完整链路，断言写死的字面数字）
  + H2 下补「证明了什么 / 没证明什么」；
  **B4** H4 四条全部显式构造 `ExplainLoop` 传上限 →「默认值 = 无限」的实现能全过 →
  新增 **H4 ⑤**（经产品入口 `explain(...)` 不传上限、`max_turns` 给 `10_000`，仍被默认值截住）；
  **B5** 只按「实测 8 次 + 余量」推默认值会取出 < `MAX_TURNS = 25` 的数，
  使失控闸退化成更严的 `max_turns`（正是 D-18 禁止的合并，且 H4 ④ 无从构造）→
  D3 写死**两条下界与两段算术**；
  **B6** `loop.py:413-419` 的未知/排除工具早返回发生在 `execute_calls += 1`（`:423`）**之前**，
  编造工具名的跑飞模型会让计数恒为 0 → D3 必须点名计量对象 (B1)/(B2) 并写取舍，选 (B2) 要补判据或登记残余风险；
  **B7** 「成本上限」措辞全仓**七处**，草案只列了两处 → §1.6 扩成**八行完整清单**，
  ①–⑤ 进 Phase 3 的 `Fix`（含 `capabilities.py:60` / `adapter.py:51` / `loop.py:26-28` 三处代码孪生句），
  ⑥⑦ 归属交人并写进 STATE §3，⑧ 明确不改并留下理由（不沉默）。
  另处理六条 non-blocking：抬头「文件集合不相交」更正为「代码不相交、三处文档落点重合 → 串行 + 重读节号」·
  Phase 3 `Item Types` 补 `Add` · Phase 2 Exit 补 owner-doc 行 ·
  「互不 import 对方夹具」澄清为「不 import 对方**文件里**的夹具，共用 `explain_fakes.py` 不禁」·
  D1 增裁定账本的**导出面** · D2 补两条分支各自的代价 ·
  第二个 🔴 **没有文件名**（`02-WBS.md:86`）故收口措辞改为「一条有名、一条未命名」·
  D3 对 WBS/D-18「**轮数**」措辞的重读留痕 · `STATE.md` 那条 open 的第 ③ 项并入 needs-human ·
  落点节补「本账本 ≠ `tools/gates/check_budget.py` 的循环日预算停机闸」这条边界 ·
  §1.1 补 Minimum Rule 4「不拆」的裁定与拆分触发条件。
- Independent draft review iteration 2: **needs revision**（第二个独立子代理，fresh session；2026-08-24）。
  该轮**逐条复核并确认第 1 轮的事实前提全部属实**（`adapter.chat` 在 `loop.py:277` 是唯一调用点 ·
  `MAX_TURNS = 25` 在 `:52` · 未知工具早返回在 `:413-419` 而计数在 `:423` ·
  `RoutingError` 是裸 `RuntimeError` · `live-run-01.json` 七条实算 = 40,885/4,310/2,784/45,195 ·
  `trace.execute_calls = 8` · `tests/unit` 现为 414 passed · 红线面均未触及），
  并判定第 1 轮七条 blocking 已被实质改掉。新出三条 blocking，**逐条已改**：
  ① §1.6 自称「实读全仓逐行列清」，但 `grep` 实为**十九处**、表里只处置七处 →
  表头改成「七处逐行 + 一处非字面 + 十一处**逐类点名**」，并补一段类级处置
  （实验设施不动 / audits・analysis・历史 plan 是历史记录不改 / `DECISIONS.md`・`STATE.md` 是 blocked 或只追加面）；
  ② D3 的下界写成「≥ `MAX_TURNS`」，**等号处仍是 D-18 禁止的合并** ——
  `loop.py:275` 是 `range(1, max_turns + 1)`，每轮一次调用时第 25 轮恰为第 25 次调用，
  取 25 会让失控闸赶在 `max-turns` 之前触发、产品默认路径上 `max-turns` 永不可达 →
  下界改为**严格大于**（**≥ 26**），H4 ④ 补「反向用例在默认值下也须成立」；
  ③ D1 分支 (i) 照字面实现会造成 `errors.py` ↔ `adapter.py` **循环 import**
  （`errors.py` 不 import 本包任何模块，而 `Usage` 在 `adapter.py`，后者又 import `errors`）→
  形态写死为「`errors.py` 只加不带类型依赖的可选属性，值由抛出处 `as_dict()` 注入」，
  并要求改后复跑 `tests/routing`、Task Route 条件性升格。
  五条 non-blocking 一并处理：§1.6 表头「七处」与八行表的口径对齐 ·
  Follow-up 四个 bullet 各自点名触发条件 · Task Route 的条件性升格 ·
  H2a 不许被算成「与端点独立核对」（功劳归 H2b / H5）· 活端点未跑时**不创建空壳证据目录**。
- Independent draft review iteration 3: **acceptable as-is**（第三个独立子代理，fresh session；2026-08-24）。
  **零 blocking**。该轮实跑复核：`grep -rn "成本上限"`（排除 `.git` 与本批两个 plan）= **19**，
  与 §1.6 的口径吻合、无一处被静默丢掉；`loop.py:52` `MAX_TURNS = 25` 与 `:275`
  `range(1, self.max_turns + 1)` 证实 D3 的严格下界（≥ 26）自洽，并交叉验了 H4 ④/⑤ 两侧可构造；
  `errors.py` 不 import 本包任何模块、`adapter.py:32` 反向 import，D1 (i) 的循环 import 风险属实
  且写死的形态解得开；另核实 `adapter.chat` 唯一调用点（`:277`）、未知工具早返回（`:413-419`）
  先于计数（`:423`）、`live-run-01.json` 七条汇总实算吻合、`tests/unit` = 414 passed、
  红线面均未触及。判据强度一项逐个试构造假实现，**未能构造出通过全部判据的假实现**。
  三条 non-blocking 已就地改掉：「其余十一处」→**十二处**（7 + 12 = 19 的算术对上）·
  Phase 2 Exit 的「H4 四条」→**五条** · Phase 3 Exit 与 Closure Gate 的 drift 计数
  由「`model-management.md` 两处」改为「§1.6 表里 **①–⑤ 五处**，含三处代码孪生句」。
  → **三轮评审收敛，本 plan 转 `active`。**

## 10. Closure Gates

- [ ] in-scope behavior is complete（账本 + 异常出口记账 + 失控闸 + 两组判据）
- [ ] relevant docs are aligned（落点节 + §1.6 表里 **①–⑤ 五处** drift，含三处代码孪生句）
- [ ] verification has run：§0 四条，**逐条抄命令原文与退出码**
- [ ] scoped verification is not conflated with full verification —— 活端点那一跑若未做，逐字写 `verification scope limited`
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded（§9）
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **收口时逐字声明五件事**：① 两条 🔴（**一条有名、一条未命名**）**未创建**（交付的是断言体与交接）；
      ② **没有设任何成本阈值、没有任何拦截分支**（D-18）；
      ③ 失控闸与成本记账的判据**在两个文件里**，收口陈述也分开；
      ④ H1 的四条预测（含 ①a/①b）与实测的**逐条对照结果**（不吻合的原文保留）；
      ⑤ **未声称满足 WBS「工具调用轮数上限」的字面措辞** —— 本 plan 按「工具调用」那一维实现，重读见 D3

## 11. Deferred But Adjudicated

### WBS §4 P1.7 的两条 🔴 门禁文件

- Classification: `out-of-scope improvement`（红线 1 禁止 loop 创建，非能力问题）
- Why Not Blocking Closure: 交付断言体 + 交接说明；P1.0a / P1.4 / P1.5 三个同形态先例
- Successor Required: `yes` —— 由**人**创建
- 重开条件：人补齐后，落点节的「判据缺口」小节与 STATE §3 对应行须由人或后继 plan 收口

### 成本阈值与配额

- Classification: `watch-only residual`
- Why Not Blocking Closure: D-18 逐字「不设阈值、不拦截」；**先有数据，再谈阈值**
- Successor Required: `no`
- 重开条件：**出现实际成本压力（账单 / 配额），或某类任务被观测到成本分布长尾严重**（D-18 的翻案条件逐字）

### 成本的多次采样与分布

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 一跑是验证账本可用，不是测成本分布；多次采样是实验（D-16）
- Successor Required: `no`
- 重开条件：**要用已记的账定阈值时**（届时须先有采样计划与假设，属另一个 plan）

## Closure

Status Note: <收口时填>

Closure Audit Evidence:

- Auditor / Agent: <收口时填>
- Evidence: <收口时填>

Follow-up:

- <收口时填；确认的缺陷不许出现在这里>
