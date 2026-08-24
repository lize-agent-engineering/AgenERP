# P1.7 单次解释成本记账（记账但不拦截，D-18）+ 失控闸

> Plan Status: completed
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

### 0.1 执行期重取基线的**实读结果**（2026-08-24，执行基线 sha `f24e351`）

`git log -1` → `f24e351`（同批第一个 plan P1.6 已收口，起草基线 `928a888` 之后又落了两条 docs 提交）；
`git status --porcelain` **无输出**。§0 点名的五处逐条重读，结果如下：

| # | §0 / §1 要重读的事实 | 执行期实读 | 结论 |
|---|---|---|---|
| 1 | `ExplainLoop.run()` 里 `self.adapter.chat(...)` 的调用点个数 | `grep -n "adapter.chat" agenerp/explain/loop.py` → **只有 `:277` 一处** | **吻合**（H1 与 D1 的前提成立） |
| 2 | 四个 `STOP_*` 常量与四条返回路径 | `:60-63` 四个常量逐字仍在；`trace.stopped` 赋值在 `:279`(model-error) / `:299`(answered) / `:305`(max-turns) / `:468`(breaker)；`_run_tools()` 熔断早返回在 `:374-390` | **吻合** |
| 3 | `Usage`（`total = prompt + completion`，reasoning 是 completion 细分）与 `usage_of()`；`is_reasoning_model` | `adapter.py:41-77` 逐字仍在，`usage_of()` 在 `:204-211`（reasoning 缺失回 0）；`capabilities.py:52-70` 的 `is_reasoning_model` 逐字仍在 | **吻合** |
| 4 | `ConversationSession.usage_total` 逐轮 `Usage.plus()` | `agenerp/context/session.py:143-153`（`@property` 在 `:143`，`def` 在 `:144`） | **吻合**（§1.3 写的 `:144` 指的是 `def` 行） |
| 5 | `live-run-01.json` 的 `usage_total` 与 `per_call_ledger[]` | 七条；实算 `prompt 40,885` / `completion 4,310` / `reasoning 2,784` / `total 45,195`，与 `usage_total` 逐字相等；`trace.execute_calls = 8`；七条 `*_matches_endpoint` 全 `true` | **吻合** |

其余 §1 关键行逐条复核：`MAX_TURNS = 25`（`loop.py:52`）· `range(1, self.max_turns + 1)`（`:275`）·
未知/排除工具早返回 `:413-419` **先于** `trace.execute_calls += 1`（`:423`）·
`RoutingError` 是裸 `RuntimeError` 且 `errors.py` **不 import 本包任何模块** ·
`adapter.py:158-161` 的空回答分支把 `usage_of(...).as_dict()` 拼进报错字符串 ·
`grep -rn "成本上限"`（排除 `.git` 与本批两个 plan）= **19**，与 §1.6 的「7 逐行 + 12 逐类」对得上。

**两处就地改写（§1 与实际不符，照 §0 要求改准，并记进 §9 执行期续行）**：

1. **`tests/unit` 的既有条数不是 414，是 453。** §7 Phase 1/2 的 Exit 与 §8 风险⑥写的「414 条」
   是起草基线 `928a888` 的数；其后同批第一个 plan P1.6 落地（`6682b68`）新增 39 条。
   → 本 plan 自本节起，「既有条数一条未红」的基数读作 **453**。
2. **`module-boundaries.md` 的 §7.x 最大节号是 7.10**（P1.6 的落点节，同批第一个 plan 落的）。
   → 本 plan 的落点节顺延为 **§7.11**（§0 抬头要求的「开写前重读最大节号」已做，未撞号）。

**四条基线命令的开工前实测**（改一行代码之前跑，逐条抄命令原文与退出码）：

| # | 命令原文 | 退出码 | 结果 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | `0` | 门禁 11 项预期红 0 / 绿 11；`453 passed` |
| ② | `python3 -m pytest tests/contracts -q` | `0` | `151 passed` |
| ③ | `python3 -m pytest tests/tools -q` | `0` | `81 passed, 12 skipped` |
| ④ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | `0` | `All checks passed!` |
| ⑤ | `python3 -m pytest tests/routing -q`（D1 若选 (i) 则为必跑的第五条） | `0` | `163 passed, 1 skipped` |

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

Status: completed
Targets: `agenerp/explain/ledger.py`（新增）· `agenerp/explain/loop.py`（接线）·
`agenerp/routing/errors.py` + `agenerp/routing/adapter.py`（D1 选定 (i)，只加结构化字段、`Usage` 口径不动）·
`tests/unit/test_explain_cost_ledger.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: 无（P1.4 已 `completed`）

- [x] **Decision D1 · 账本的落点与采集面。**
      **选定 (B)：挂在解释循环上，采集面只有一处。**
      `agenerp/explain/loop.py:277` 是 `self.adapter.chat(...)` 的**唯一**调用点（§0.1 实读复核），
      账本就记在它的**两条出口**上：`except RoutingError` 分支里 `record_error(...)`、
      正常返回后紧跟一行 `record_reply(...)`，**在分支判断之前** ——
      这样四条循环出口没有一条能绕过记账，而不是靠「每条出口都记得写一遍」。
      **被否决项的代价**：(A) 挂 `ChatAdapter` 覆盖面更大，但那是 P1.1 的导出面，
      改它会同时动 `tests/routing` 的既有判据，且「一次解释」这个聚合概念根本不在那一层；
      (C) 从 `ConversationSession` 反推 —— 异常那次**根本没有 turn**，反推必然漏，
      H1 ①a/①b 两条实测（`session_usage_records(result) == 0`）把这个代价量化了。
      **残余风险**：采集面与 `session.usage_total` 是**两个数**，权威面由 D2 与落点节 §7.11 钉住。
      ⚠️ **H1 ①b（空回答路径）的处置：选定 (i)** —— `RoutingError` 加一个可选属性
      `usage: dict | None = None`，由 `adapter.py` 抛出处注入。
      **实现形态与起草期写死的那条有一处偏离，理由在此**：起草期写「`as_dict()` 后注入」，
      执行期改为**注入端点自报的原始 usage 字典**。两者都满足「`errors.py` 不带类型依赖、
      不 import 本包任何模块」这条硬约束（循环 import 因此照样解得开），
      但原始 dict 多留住了 `total_tokens` 这个**端点自报的数**，
      而 `as_dict()` 里的 `total` 是 `prompt + completion` 那个**恒真式** ——
      注入 `as_dict()` 会让异常路径上的 `total_matches_endpoint` 判了等于没判。
      解析仍然只有 `usage_of()` 一处，本 plan 没有第二份解析。
      **顺带扩到三处抛出点**（原文只点名 `adapter.py:158-161` 的空回答）：
      「没有 choices」「choices[0] 里没有成形的 message」两条同样是**端点已经回包、
      token 已经真的花掉**，漏掉它们就是把同一个缺陷留下两份。三处共用同一个
      `endpoint_usage = body.get("usage") or None`。
      ⚠️ 该改动动到 P1.1 的导出面 → Task Route 的**条件性升格已触发**，
      `python3 -m pytest tests/routing -q` 进入本 plan 的验证命令清单（§0.1 表第 ⑤ 行）。
      ⚠️ **账本的导出面（交接断言体要写在稳定名字上）**：
      `agenerp.explain.ledger` 的 `CallLedger` / `CallEntry` / `CALL_TOOLS` / `CALL_ANSWER` / `CALL_ERROR`；
      `ExplainResult.cost_ledger`（`@property`，读 `trace.cost_ledger`）；
      `ExplainTrace.cost_ledger` 字段 + `ExplainTrace.as_dict()` 里的 `"cost_ledger"` 键。
      **带进 `as_dict()` 是必须的**：`agenerp/insight/attribution.py` 侧消费的正是序列化后的 trace 字典
      （`tests/unit/test_insight_attribution.py` 读 `attributed.trace["stopped"]`），
      不带就写不出「经由 insight 进来的那条路径也在账上」这条断言
      （判据见 `test_the_ledger_also_covers_the_path_that_comes_in_through_insight`）。
      ⚠️ `agenerp/explain/__init__.py` 的导出面**未动**（仍只有 `explain` 与 `ExplainResult`）——
      账本从子模块 import，与 P1.4 的 D7 同一口径。
      - Skill: `none`
- [x] **Decision D2 · `ExplainResult.usage` 是否改读账本。**
      **选定 (B)：保留现状 + 加同源判据。**
      理由：(A) 会改掉 P1.4 已声明的读法，`loop.py` 那句 docstring 连带失效，
      属 owner-doc 连带修改，而本 plan 的结果面是「把账记下来」，不是「改 P1.4 的导出面」；
      且 `tests/unit` 既有 453 条里有依赖该读法的判据，改它是拿既有判据换一个口径统一。
      **(B) 的代价照实记**：长期保留**两个数**，「哪个是权威」必须写进落点节，否则下游读错。
      **处置**：权威面写死 —— `ExplainResult.usage` 答「这次会话累计了多少」
      （口径：成为了一轮对话的那些调用）；`cost_ledger` 答「这次解释调了几次模型、各花多少」
      （口径：`adapter.chat` 发生过几次）。**要算钱就读账本**，这句逐字写进 `usage` 的 docstring 与落点节 §7.11。
      **同源判据（M7 的靶子）**：`test_d2_on_normal_paths_the_ledger_and_the_session_agree`
      在 `answered` / `max-turns` / `permission-breaker` 三条正常路径上判**逐项相等**
      （并先排掉「两个空 `Usage` 相等」那个恒真式）；
      `test_d2_on_the_error_path_the_ledger_is_strictly_larger_than_the_session`
      在异常路径上判**账本严格大于 session**，三项各判一次。
      `tests/unit` 既有 453 条**一条未因此变红**（实测 480 passed = 453 + 27）。
      - Skill: `none`
- [x] **Add** 账本：一次调用一条记录（三项 token + 模型名 + 第几轮 + 这次调用属于哪种出口），
      一次解释一份汇总。**汇总走 `Usage.plus()`，不自己写三项加法**（§7.7 的既有纪律逐字）。
      → `agenerp/explain/ledger.py`：`CallEntry(index, model, usage, outcome, endpoint_total,
      endpoint_reasoning, detail)`；`CallLedger.total` 是从空 `Usage()` 起折 N 条的 `plus()` 折叠。
      `outcome` 三取值 `tools` / `answer` / `model-error`，**由回包内容定，不由调用方声明**。
      每条**另留端点自报的原始数字**（`endpoint_total` / `endpoint_reasoning`）——
      `prompt + completion == total` 那种写法是恒真的，判它等于没判。
- [x] **Add** 异常出口的记账：模型调用抛错时，那次调用**照样在账上**。
      **口径选定**：记一条 `outcome = model-error` 的记录；端点确实回了包时
      （`RoutingError.usage` 非空）记**真数**，端点根本没回包时三项记 0 且
      `endpoint_*` 记 `None`（**「不知道」不写成「对得上」**，`total_matches_endpoint` 因此为 `False`）。
      理由与形态一并写进落点节 §7.11。
- [x] **Proof H1** 四条路径逐条实测，与 §6 的四条预测**逐条对照**：
      **①a 连不上端点 → 吻合**（`session` 上 0 条 usage 记录，账本 1 条，三项 0 是对的）；
      **①b 空回答 → 不吻合**：预测「账本对该路径系统性偏低」，实测**不偏低**
      —— 因为 D1 选定 (i) 之后 `RoutingError` 把端点自报的 usage 带出来了，
      实测 `Usage(15, 178, 173)` 一个 token 不丢。⚠️ **预测原文保留在 §6，不回头改**；
      该条判据自此转为**守护性回归**（`RoutingError.usage` 一旦被摘掉当场红）。
      ⚠️ 预测里「usage 只以字符串形式存在、拿不回来」这句**对改动前的实现属实**
      （`adapter.py:158-161` 的报错消息里确有 `usage_of(...).as_dict()`），
      不吻合的是「所以账本会偏低」这个结论 —— 本 plan 把前提改掉了；
      **② 熔断早返回 → 吻合**（`session` 记了 1 条、`trace.turns` 0 条，账本 1 条）；
      **③ `STOP_MAX_TURNS` → 吻合**（不漏，3 次调用 3 条）；
      **④ `STOP_ANSWERED` → 吻合**（不漏）。
      判据：`test_h1_1a_*` / `test_h1_1b_*` / `test_h1_2_*` / `test_h1_3_*` / `test_h1_4_*`。
- [x] **Proof（计数探针）** `CountingTransport` **自己数** `chat()` 被调了几次，
      与账本条数逐条比（`test_the_call_count_equals_the_ledger_length_on_every_exit`，
      **五个参数化用例**：`answered` / `max-turns` / `permission-breaker` /
      `model-error`（端点回了包）/ `model-error`（连不上端点）），
      并同时判序列化后的 `trace.as_dict()["cost_ledger"]["calls"]`。
      经由 `agenerp.insight` 进来的那条路径另有一例（§1.8）：
      `test_the_ledger_also_covers_the_path_that_comes_in_through_insight`
      —— 由巡检器真跑出命中、走 `attribute()`，判账本条数与 `attributed.trace["cost_ledger"]`。
- [x] **Proof H2a** 重放 `live-run-01.json` 的七条：**21 个字面期望值写死在判据里**
      （`LIVE_CALLS` 七元组 × 三项）+ 汇总逐字等于 `40,885 / 4,310 / 2,784 / 45,195`
      + 逐条 `usage.total == endpoint_total`（**端点自报的数**，不是恒真式）。
      另有一条判夹具本身未漂移（`test_h2a_the_evidence_file_still_reports_*`）。
      ⚠️ 该证据文件**只读，一个字未改**。
- [x] **Proof H2b** 假 transport 回**原始 OpenAI 形状 body**（含
      `completion_tokens_details.reasoning_tokens`，数值复用那七次里的四次实测数），
      经 `ExplainLoop` → 真 `adapter.chat` → `usage_of()` → 账本走完整条链路，
      断言对象是判据里写死的字面数字（`test_h2b_a_raw_endpoint_body_survives_the_whole_chain`）。
      另加一条非推理模型形态（`completion_tokens_details` 整个缺失）：
      reasoning 记 0，**不回退成算进 completion**。
- [x] **Proof H3** 两个数据集的假实现反测：
      ① 真实重放（七条，reasoning 全 > 0）② `reasoning == 0` 的合成用例（两条，汇总 197/53/0/250）。
      两个假实现各打一遍：`strip_reasoning`（M1，只记 completion 不记 reasoning）
      与 `ratio=0.7`（reasoning 恒等于 completion 的某个比例 —— **只有数据集①时可能蒙混过关**，
      加上②当场红）。另有 `test_h3_the_real_replay_is_green_without_the_fake`
      钉住「不加假实现时判定体是绿的」，否则 `pytest.raises` 只是在证明判定体永远红。
      ⚠️ **假实现摆在判据侧，产品代码一行未改**。
- [x] **Proof（D-18 的底线）** `test_the_ledger_never_blocks_anything`：
      喂一份 6,000 万 token 的账，跑完照样 `answered`、照样把答案交出去
      —— 账本里**没有阈值、没有任何「超了就……」的分支**。

Exit Criteria:

- [x] H1 / H2 / H3 与 §6 原文逐条对照，吻合与否照实记（H1 ①b **不吻合**，原文保留，理由见上）
- [x] D1 / D2 各有选定、备选、否决理由与残余风险
- [x] 四条基线命令全退 0（§0）+ 条件性升格的第五条 `tests/routing` 退 0，
      且 `tests/unit` 既有 **453** 条（§0.1 改准，起草期写的 414 是 `928a888` 的数）**一条未红**
- [x] owner-doc 落地**延至 Phase 3**；本阶段不改任何 owner doc

**Phase 1 收口实测**（命令原文 + 退出码）：

| 命令原文 | 退出码 | 结果 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | `0` | 预期红 0 / 绿 11；`480 passed`（453 + 27 新增） |
| `python3 -m pytest tests/contracts -q` | `0` | `151 passed` |
| `python3 -m pytest tests/tools -q` | `0` | `81 passed, 12 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | `0` | `All checks passed!` |
| `python3 -m pytest tests/routing -q`（D1 选 (i) 触发的第五条） | `0` | `164 passed, 1 skipped`（基线 163 + 1：`test_adapter.py:485` 按 `agenerp/**/*.py` 参数化，新模块 `ledger.py` 自动多一条） |
| `python3 -m pytest tests/context -q` | `0` | `53 passed` |

### Phase 2 — 失控闸：工具调用总数上限（与成本判据分开写）

Status: completed
Targets: `agenerp/explain/loop.py`（新增 `MAX_TOOL_CALLS` / `STOP_RUNAWAY` / 计量与停机）·
`tests/unit/test_explain_runaway_guard.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: Phase 1（**顺序理由**：失控闸触发时「账仍完整」是 H4 ③ 的一半，账本得先在）

- [x] **Decision D3 · 上限的计量单位。**
      **选定 (B)：单次解释的工具调用总数**，且**计量对象点名选 (B1)「模型发起的工具调用数」**。
      **被否决项的代价**：(A) 主循环轮数 —— `max_turns` 已经是它，D-18 要的是**工具调用**那一维；
      (C) 每轮工具调用数 —— 挡得住一轮暴涨，挡不住细水长流。
      **(B1) 而不是 (B2) 的取舍**：`loop.py` 里未知工具 / 被排除工具在
      `trace.execute_calls += 1` **之前**就早返回，选 (B2) 时一个**不断编造工具名**的跑飞模型
      会让计数**恒为 0**、闸门**永不触发**（起草期风险 ⑨）。选 (B1) 就把这条风险**关掉**，
      而不是登记成残余风险。**(B1) 的代价照实记**：把「没打到站点的调用」也算进来，
      闸门因此比「实际干了多少活」略严 —— **这是刻意的**，它管的是「停下来」，不是「花了多少」。
      判据：`test_the_guard_counts_calls_the_model_initiated_not_the_ones_that_reached_execute`
      （实测 `execute_calls == 0` 而 `model_tool_calls == 32`，闸门照样截住）。
      **默认值 `MAX_TOOL_CALLS = 32`，两段算术都写出来**：
      ① **对本项目实测留余量**：P1.4 那一次活端点解释实测 `trace.execute_calls == 8`
      （`docs/evidence/p1-explain/live-run-01.json`）—— 这是**唯一**可引用的本项目数字
      （D-16），`32 = 8 × 4`，四倍余量；
      ② **对 `MAX_TURNS` 严格大于**：`MAX_TURNS = 25`、主循环是 `range(1, max_turns + 1)`，
      「每轮发一次工具调用」的正常形态下第 25 轮恰好是第 25 次调用 —— 取 25 会让失控闸
      赶在 `STOP_MAX_TURNS` 之前触发、产品默认路径上 `max-turns` 永不可达。
      下界因此是 `MAX_TURNS + 1 = 26`（**等号处不算数**），`32 > 26`，余量 6。
      两段算术各有一条判据钉住（`test_d3_the_default_limit_leaves_headroom_over_the_measured_run`
      / `test_d3_the_default_limit_is_strictly_greater_than_max_turns`）。
      ⚠️ **对上位文件措辞的重读留痕**：D-18 与 `02-WBS.md:86` 都写「工具调用**轮数**上限」，
      本 plan 按 §1.5 的实读把它落成「**工具调用**那一维」（轮数已由 `max_turns` 占用）。
      `DECISIONS.md` 是 blocked 面，**本 plan 一个字未改**；重读只写在这里与落点节 §7.11。
      **收口不声称满足了 WBS 的字面措辞** —— 人若按字面读作「轮数」，须回到轮数口径重做。
      - Skill: `none`
- [x] **Add** 失控闸：达到上限即停机，**专属停止原因** `STOP_RUNAWAY = "tool-call-runaway"`
      （新增常量，不复用 `max-turns` / `permission-breaker`），轨迹里留痕
      `trace.runaway_events == [{"turn": ..., "tool_calls": ..., "limit": ...}]`
      （**第几次、上限是多少**）+ `trace.model_tool_calls`，两者都进 `as_dict()`。
      **不拦成本、不改模型、不降级** —— 它只做「停下来」这一件事。
      ⚠️ `_run_tools()` 的返回第二项由布尔改成**停止原因字符串**（三态）：熔断与失控闸是
      两个不同的闸，合成一个布尔就等于把停止原因混成一个。
- [x] **Add** 上限**可配置但有默认值**：`ExplainLoop(max_tool_calls=MAX_TOOL_CALLS)`，
      而**产品入口 `explain()` 的签名里根本没有这个参数**（照抄 P1.4 的 D7：
      安全闸不给产品面开关；判据侧要构造就直接构造 `ExplainLoop`）。
      判据 `test_h4_5_*` 里连 `"max_tool_calls" not in explain.__code__.co_varnames` 都判了。
- [x] **Proof H4** **五件事**逐条判，与 §6 原文对照 —— **五条全部吻合**：
      **① 不超上限**（`execute_calls <= 32`，`model_tool_calls == 32`）· **吻合**；
      **② 专属停止原因**（`STOP_RUNAWAY`，且 `!= STOP_MAX_TURNS`、`!= STOP_BREAKER`）· **吻合**；
      **③ 账仍完整**（`len(ledger) == 4`、三项均非 0、逐条对得上端点自报数、
      且 `ledger.total == result.usage`）· **吻合**；
      **④ 反向用例**（同一个假模型、上限调到 `10_000` → 跑到 `max-turns`，
      `model_tool_calls == 48` 却没被截）· **吻合**；
      **④ 的默认值形态**（每轮只发一次调用、**不传上限**、`max_turns = MAX_TURNS = 25`
      → 停在 `max-turns`，`model_tool_calls == 25`，`runaway_events == []`）· **吻合**
      —— 这正是 D3 ② 那条严格下界的可观测形态；
      **⑤ 经产品入口 `explain(...)`**（不传上限、`max_turns = 10_000`）
      → 仍被默认值截住，`trace.stopped == STOP_RUNAWAY`、`model_tool_calls == MAX_TOOL_CALLS` · **吻合**。
      ⚠️ 轮数远没到 `max_turns`：每轮 8 个调用，**第 4 轮**就撞 32，而 `max_turns` 给的是 6。
- [x] **Proof（两组判据分开）** 失控闸判据落 `tests/unit/test_explain_runaway_guard.py`，
      成本判据落 `tests/unit/test_explain_cost_ledger.py`，**互不 import 对方文件里的夹具**
      —— 由 `test_the_two_criteria_groups_do_not_import_each_other` 用 `ast` 解析
      两个文件的 `import` 语句判死（**判 import 语句本身，不按字符串搜正文**，
      模块头说明里写着对方文件名，按字符串搜会假红），
      并同时钉住「共用 `explain_fakes` 是允许的」。
- [x] **Proof** 变异自查 **M1–M8 逐个复跑，八个全部由绿转红**（变异摆在产品代码上、
      跑完即还原，工作树复核 `git status --porcelain` 干净）。**打不红的一个都没有，
      因此没有新增 M9…**。逐条对照如下（列出的是被打红的判据里最直接的那条）：

| 变异 | 形态 | 结果 | 由谁打红 |
|---|---|---|---|
| **M1** | 账本记录里 `reasoning` 置零 | **RED** | `test_h2a_the_seven_real_calls_replay_entry_by_entry`（per-entry `reasoning`）+ `test_h1_1b_*` + `test_h2b_*` 等 14 条 |
| **M2** | 只在成功路径记账（删掉 `record_error`） | **RED** | `test_the_call_count_equals_the_ledger_length_on_every_exit[model-error-*]` 两条 + `test_h1_1a_*` / `test_h1_1b_*` |
| **M3** | 汇总写死成常量 `Usage(40885, 4310, 2784)` | **RED** | `test_h3_the_synthetic_zero_reasoning_dataset_is_green`（**第二个数据集**，单一数据集挡不住写死）+ 11 条 |
| **M4** | `Usage.total` 把 `reasoning` 再加一遍 | **RED** | `test_h2a_*` / `test_h2b_*` 的逐条 `total == endpoint_total`（**端点自报的数**，不是恒真式） |
| **M5** | 失控闸被实现成「把 `max_turns` 改小」（返回 `STOP_MAX_TURNS`） | **RED** | `test_h4_1_and_2_*`（②停止原因）+ `test_h4_5_*` + `test_h4_the_guard_leaves_a_trace_*` |
| **M6** | 失控闸触发时把账清掉 | **RED** | `test_h4_3_the_cost_ledger_survives_the_runaway_stop`（H4 ③） |
| **M7** | 账本与 `session.usage_total` 漂移（汇总少折最后一条） | **RED** | `test_d2_on_normal_paths_the_ledger_and_the_session_agree` 三个参数化用例 + `test_d2_on_the_error_path_*` |
| **M8** | 记的是「打算调用」而非「实际回包」（发请求前记一条 0） | **RED** | `test_m8_every_entry_carries_the_usage_of_that_very_reply` + `test_h2b_*` + `test_d2_*` |

Exit Criteria:

- [x] H4 **五条**逐条对照 §6 原文，吻合与否照实记（**五条全部吻合**，含 ④ 的默认值形态）
- [x] M1–M8 逐个复跑**全部由绿转红**（无一条打不红，故未新增 M9…）
- [x] 两组判据在**两个文件**里，且互不 import **对方文件里**的夹具
      （共用 `explain_fakes.py` 不在禁止之列，并由 `ast` 判据同时钉住这两件事）
- [x] 四条基线命令全退 0，`tests/unit` 既有 **453** 条一条未红（实测 `491 passed` = 453 + 38）
- [x] owner-doc 落地**延至 Phase 3**（本阶段新增了产品可见的 `STOP_RUNAWAY`，文档在 Phase 3 一并落）

**Phase 2 收口实测**（命令原文 + 退出码）：

| 命令原文 | 退出码 | 结果 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | `0` | 预期红 0 / 绿 11；`491 passed` |
| `python3 -m pytest tests/contracts -q` | `0` | `151 passed` |
| `python3 -m pytest tests/tools -q` | `0` | `81 passed, 12 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | `0` | `All checks passed!` |
| `python3 -m pytest tests/routing -q` | `0` | `164 passed, 1 skipped` |
| `python3 -m pytest tests/context -q` | `0` | `53 passed` |

### Phase 3 — 活端点一跑 · 🔴 门禁交接 · owner doc 改准 · 日志

Status: completed
Targets: `tests/unit/test_explain_cost_accounting_body.py`（🔴 的断言体，**两节**）·
`docs/architecture/model-management.md` §12.2/§12.5 · `docs/architecture/module-boundaries.md` **§7.11** ·
`agenerp/routing/capabilities.py` + `agenerp/routing/adapter.py` + `agenerp/explain/loop.py`（**仅注释**）·
`docs/masterplan/STATE.md`（**只追加**）· `docs/evidence/p1-cost/` · `docs/logs/2026/08-24.md`
Skill: `none`

- Item Types: `Fix | Add | Proof | Follow-up`
- Prereqs: Phase 1, Phase 2

- [x] **Proof H5（活端点跑一次）** **已跑，凭据齐备**（`~/.config/agenerp/secrets.env` +
      本地 compose 站点 `frontend@http://127.0.0.1:18080`）。轨迹与账本落
      `docs/evidence/p1-cost/`（照 `docs/evidence/p1-explain/` 的形制，含「证明了什么 /
      没证明什么」两节）。**只跑一次**。
      **与 §6 H5 原文逐条对照 —— 三条全部吻合**：
      ① 账本每条与端点自报的 `raw["usage"]` **逐次相等** → `total_matches_endpoint` **8/8**、
      `reasoning_matches_endpoint` **8/8** · **吻合**；
      ② 三项均 > 0（D-11） → **8 条全部三项 > 0**，逐条 reasoning
      142 / 255 / 288 / 41 / 1,008 / 922 / 181 / 261 · **吻合**；
      ③ **不预测总量落在哪个区间** → 实测 **53,041 / 5,538 / 3,098 / 58,579**，8 次模型调用 ·
      **照实记，不与 P1.4 的 45,195、不与 roadmap 的 9.7 万–12.8 万作优劣比较**（§8 风险 ⑦）。
      ⚠️ **那一跑没证明什么，逐条写在证据 README 里**：没走到异常出口（`stopped == "answered"`）、
      没触发失控闸（`model_tool_calls == 9`，远在 32 之下）、一跑不是成本分布。
      ⚠️ **执行期实测两处与 P1.4 那一跑不同，照实记**（均非本 plan 改出来的）：
      ② 作答前门禁这次**被走到了拒绝路径**（`forced_continues` 1 条、`gate_checks` 2 条），
      故 `execute_calls` 从 8 变 9、模型调用从 7 次变 8 次；`opening_request_count` 是 8 不是 10
      （本跑给的 `doctypes` 清单是 8 个）。
      ⚠️ **第一次尝试没跑完**：在 10 分钟执行超时上被掐断、无产物；**原样复跑**一次即成功
      （102.0 秒）。**两次的差异未定位，不猜根因**（裁判规则 3）。
      ⚠️ 落盘 JSON 已复核**无任何凭据字样**。
- [x] **Add（交接，红线 1）** `tests/gates/test_explain_cost_accounting.py` **未创建**。
      断言体交付在 `tests/unit/test_explain_cost_accounting_body.py` 的 **§A**，
      照抄 P1.4 的 `test_evidence_gate_single_hop_body.py` 形制，模块头带**加载片段与交接说明**。
      **覆盖 D-18 逐字要的那两件事**：三项都记了（`test_all_three_token_buckets_are_recorded_per_call`，
      逐条判 `prompt` / `completion` / **`reasoning`** 各自的数字 + 逐条对端点自报的 total）
      + 能按解释汇总（`test_the_ledger_rolls_up_per_explanation`，四次调用的账**刻意各不相同**，
      挡住「汇总写死成常量」）+ **缺任一项即红**
      （`test_dropping_any_one_bucket_turns_the_criteria_red`，三项各反测一次）。
      另有两条：账本在产品默认路径上且**没有开关**、**记账不拦截**。
      ⚠️ 「纯路径加载、无 live 语义是否仍满足那个 🔴」**由人裁定**，loop 不替人拍板 ——
      这句逐字写在模块头与 STATE §3 的 needs-human 里。
- [x] **Add（交接）** 第二个 🔴「失控闸另算」同样交接，断言体在**同文件的 §B 单独一节**，
      **不与成本那条合并**（D-18 逐字）。五条：上限确实生效且轮数远没到 `max_turns` ·
      停止原因**不是** `max-turns`/`permission-breaker` · 两个闸**独立触发**（含默认值下的反向用例）·
      产品入口走默认值且无开关 · 失控闸触发时**账仍完整**。
      ⚠️ **措辞照实**：`02-WBS.md` P1.7 行的第二个 🔴 **没有给文件路径**（只有第一个 🔴 有），
      故收口写作「**一条有名、一条未命名，两条的断言体都已交付**」，
      **不得**说成「一个不存在的文件未创建」。
- [x] **Follow-up → STATE §3 追加 needs-human**（只追加，`--numstat` 实测 `8	0`，删除列为 0）。
      一行里四个 bullet，**各自的触发条件已逐条点名**：
      ① 两条 🔴（一条有名、一条未命名）待人按路径加载 —— 触发条件：**人创建该门禁文件时**；
      ② `docs/backlog/implementation-roadmap.md:117` 的「单次解释的成本上限」由**人**改准
      （该文件由人维护，§1.6 ⑥）—— 触发条件：**人编辑该文件时**；
      ③ `docs/backlog/p1-insight-roadmap.md:64` 的同一措辞与同文件下方 D-18 那一节并存、会误导
      （§1.6 ⑦）—— 触发条件：**人或引擎回写该文件时**；
      ④ `STATE.md` 那条 `[open] 2026-08-24T08:56Z` 的第 ③ 项仍逐字挂着
      「P1.7 的成本上限按哪个档位定」，已由 D-18 与本 plan 实质取代 ——
      **只追加一行指明，那条 `[open]` 一个字未改**（红线 5）—— 触发条件：**人处置那条 `[open]` 时**。
      另附两项照实记（不属上面四条）：失控闸的计量口径与 WBS 字面措辞不同 · 活端点只跑了一次且
      那一跑没走到异常出口 / 没触发失控闸。
- [x] **Fix** §1.6 表里 ①–⑤ **五处**「成本上限」drift 全部改准，指名 D-18：
      ① `model-management.md:55` → 「成本**记账**」+ 三句补注（判据是成本可观测 / 不设阈值不拦截 /
      **不拦成本 ≠ 不拦失控**）；② `model-management.md:213` → 「P1.7 的**成本记账**读后者」；
      ③ `agenerp/routing/capabilities.py` 的 `is_reasoning_model` docstring（**仅注释**，
      `is_reasoning_model` 的行为与声明**一个字未动**）；
      ④ `agenerp/routing/adapter.py` 的 `Usage` docstring（**仅注释**，`Usage` 口径**一个字未动**，Non-Goal 2）；
      ⑤ `agenerp/explain/loop.py` 模块头那两句「归 P1.7 / 本模块不声称做过它」——
      **落地即失效**，改写成「失控闸是 `MAX_TOOL_CALLS`、账本是 `ledger.py`、两者已在本模块落地」。
      ⚠️ **§12.2 的 Spike 02 成本表与「没有前缀缓存，解释 Agent 在经济上不成立」的结论一个字未动**
      （`git diff` 实测该文件只有 6 增 2 删，全在上述两处）。
      ⚠️ ⑥⑦ 未改（归属交人，已进 STATE §3）；⑧ 未改（判据行为正确，只是措辞引旧口径，
      改它要动 P1.2 的判据文件而无行为收益，理由已在 §1.6 留痕）；
      其余十二处按类处置、一处未动。
- [x] **Add** 落点节 `docs/architecture/module-boundaries.md` **§7.11**
      （开写前重读当时最大节号 **7.10**（P1.6，同批第一个 plan 落的）后顺延，**未撞号**）。
      内容含：账本的采集面在哪、为什么只有一份、**导出面叫什么**（D1 裁定）、
      异常出口的记账口径（含 ①b 空回答那条的处置与「只挂 dict 不挂 Usage」的循环 import 理由）、
      失控闸的计量对象（**B1**）与默认值的**两段算术**（8 × 4 = 32 · `MAX_TURNS + 1 = 26` 严格下界）、
      对上位文件「轮数」措辞的重读留痕、判据缺口小节，
      **以及三句边界**：「记账 ≠ 拦截」「失控闸 ≠ 成本闸」
      「本账本 ≠ `tools/gates/check_budget.py` 那个循环日预算停机闸（两者不互读、不互写）」。
- [x] **Add** `docs/logs/2026/08-24.md` 追加一条聚合日志（含命令原文 + 退出码 + 红线复核 +
      「本轮不扩大任何声称」四条）。

Exit Criteria:

- [x] H5 逐条对照 §6 原文，**三条全部吻合**，实测数字照实记（已跑，非「未跑 · 未验证」）
- [x] 两个 🔴 的断言体 + 交接说明已交付，且**分成两节**（§A / §B，不合并）
- [x] §1.6 表里 **①–⑤ 五处** drift 改准（含 `capabilities.py` / `adapter.py` / `loop.py` 三处代码孪生句），
      且**未动那张实测表**
- [x] STATE §3 needs-human 已追加（只追加，`8	0`）· `docs/logs/` 已更新
- [x] 四条基线命令全退 0

**Phase 3 收口实测**（命令原文 + 退出码）：

| 命令原文 | 退出码 | 结果 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | `0` | 预期红 0 / 绿 11；`503 passed`（453 + 50） |
| `python3 -m pytest tests/contracts -q` | `0` | `151 passed` |
| `python3 -m pytest tests/tools -q` | `0` | `81 passed, 12 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | `0` | `All checks passed!` |
| `python3 -m pytest tests/routing -q` | `0` | `164 passed, 1 skipped` |
| `python3 -m pytest tests/context -q` | `0` | `53 passed` |
| 活端点解释一次（脚本不进仓，照 P1.4 先例） | `0` | 8 次调用；`total_matches_endpoint` 8/8 · `reasoning_matches_endpoint` 8/8 · 三项均 > 0 |

**红线复核**（执行期实跑，不采信转述）：
`git diff --name-only f24e351 HEAD -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md`
→ **无输出**；`git diff --numstat f24e351 HEAD -- docs/masterplan/STATE.md` → **`8	0`**（删除列为 0，只追加）。
红线 1–7 无一触碰。`tools/gates/expected-red.txt` **本轮无需划行**（名单已为 0 条，无名单内转绿项）。

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

- **执行期续行（2026-08-24，执行基线 `f24e351`）** —— §0 要求「不吻合的就地改写 §1 并把改动记进本节」。
  对照表在 **§0.1**，**§1 的事实条目逐条吻合，无一条需要改写**；就地改准的只有**两处计数**：
  ① `tests/unit` 的既有条数 **414 → 453**（起草基线 `928a888` 之后同批第一个 plan P1.6 落地 `6682b68`，
  新增 39 条）—— §7 两个 Phase 的 Exit 与 §8 风险⑥里的「414」自 §0.1 起读作 **453**；
  ② `module-boundaries.md` 的 §7.x **最大节号是 7.10**（P1.6 的落点节），本 plan 顺延为 **§7.11**，
  未与同批第一个 plan 撞号（§0 抬头要求的「开写前重读最大节号」已做）。
- **执行期的一处实现形态偏离，理由记在 D1，此处只索引**：D1 分支 (i) 起草期写「`as_dict()` 后注入」，
  执行期改为**注入端点自报的原始 usage 字典**。两者都满足「`errors.py` 不带类型依赖」这条硬约束
  （循环 import 照样解得开），但 `as_dict()` 里的 `total` 是恒真式，注入它会让异常路径上的
  「对得上端点」判了等于没判。**并顺带把注入面从一处扩到三处**（空回答 / 没有 choices /
  choices[0] 没有成形的 message —— 三条都是「端点已回包、token 已真的花掉」）。
- **执行期未新增任何 blocking 评审项**：三轮独立起草评审已于起草期收敛（上文三条），
  执行期没有回头改动 §6 的任何一条假设、也没有改动 §2/§3 的任何一条。

## 10. Closure Gates

- [x] in-scope behavior is complete（账本 + 异常出口记账 + 失控闸 + 两组判据）
- [x] relevant docs are aligned（落点节 **§7.11** + §1.6 表里 **①–⑤ 五处** drift，含三处代码孪生句）
- [x] verification has run：§0 四条 + 条件性升格的第五条，**逐条命令原文与退出码见下方 `## Closure`**
- [x] scoped verification is not conflated with full verification —— **活端点那一跑已做**
      （`docs/evidence/p1-cost/`），故**不写** `verification scope limited`；
      但那一跑的边界逐条写清：**没走到异常出口、没触发失控闸、一跑不是成本分布**
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§9，三轮，第三轮零 blocking）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— ⚠️ **留白，照实记**：本轮执行环境不具备独立子代理
      （执行者自审不算独立），先例 P1.3 / P1.4 / P1.5 / P1.6 同形态。**不勾**。
- [x] closure evidence exists in files（`docs/evidence/p1-cost/` · `docs/logs/2026/08-24.md` ·
      `docs/masterplan/STATE.md` §3 · `docs/architecture/module-boundaries.md` §7.11）
- [x] **收口时逐字声明五件事**（见下方 `## Closure` 的「五件事」一节，逐条写死）

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

Status Note: **三个 Phase 全部执行完毕，四条基线命令 + 条件性升格的第五条全绿，活端点跑过一次。**
唯一未勾的 gate 是 `closure audit was independent`（本轮环境不具备独立子代理，照实留白）。

### 验证命令原文与退出码（裁判规则 2）

执行基线 sha `f24e351`（开工前 `git status --porcelain` 无输出）。

| # | 命令原文 | 退出码 | 结果 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0** | `判定模式：default` · `门禁 11 项：预期红 0，绿 11，跳过 0` · `✅ 与预期红名单完全一致` · **`503 passed`**（基线 453 → +50，**既有 453 条一条未红**） |
| ② | `python3 -m pytest tests/contracts -q` | **0** | `151 passed`（与基线逐字相同） |
| ③ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped`（与基线逐字相同，`tests/tools/**` 一个字未改） |
| ④ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` |
| ⑤ | `python3 -m pytest tests/routing -q` | **0** | `164 passed, 1 skipped`（基线 163；+1 是 `tests/routing/test_adapter.py` 按 `agenerp/**/*.py` 参数化，新模块 `ledger.py` 自动多一条）。**本条因 D1 选定 (i) 动到 P1.1 导出面而进入验证清单** |
| ⑥ | `python3 -m pytest tests/context -q` | **0** | `53 passed` |
| ⑦ | 活端点解释一次（一次性脚本不进仓，照 P1.4 先例） | **0** | 8 次调用；`total_matches_endpoint` **8/8** · `reasoning_matches_endpoint` **8/8** · 三项均 > 0；轨迹与账本 `docs/evidence/p1-cost/` |

**红线复核**（执行期实跑，不采信转述）：
`git diff --name-only f24e351 HEAD -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md`
→ **无输出**；`git diff --numstat f24e351 HEAD -- docs/masterplan/STATE.md` → **`8	0`**（删除列为 0，只追加）。
红线 1–7 无一触碰。`tools/gates/expected-red.txt` **本轮无需划行**（名单已为 0 条）。

### 收口逐字声明的五件事（§10 要求）

1. **WBS §4 P1.7 的两条 🔴 未创建**（红线 1）：**一条有名**
   （`tests/gates/test_explain_cost_accounting.py`）、**一条未命名**
   （`docs/masterplan/02-WBS.md` P1.7 行的第二个 🔴 **没有给文件路径**）。
   交付的是**断言体与交接说明** —— `tests/unit/test_explain_cost_accounting_body.py` 的
   **§A / §B 两节**，带加载片段。**本 plan 未声称那两个 🔴 已满足**；
   「纯路径加载、无 live 语义是否仍满足它们」**由人裁定**。
2. **没有设任何成本阈值、没有任何拦截分支**（D-18）。账本里连一个「超了就……」的分支都没有，
   判据 `test_the_ledger_never_blocks_anything` / `test_the_accounting_never_blocks_anything`
   各钉一遍（喂 6,000 万 token 的账，跑完照样 `answered`、照样把答案交出去）。
3. **失控闸与成本记账的判据在两个文件里**（`test_explain_runaway_guard.py` /
   `test_explain_cost_ledger.py`），互不 import 对方文件里的夹具（由 `ast` 判据钉死），
   🔴 断言体也分成 §A / §B 两节 —— **收口陈述同样分开**：
   · **成本面**：一次调用一条记录、三项分开记、逐条对得上端点自报的数、能按解释汇总、不拦截。
   · **失控面**：单次解释的工具调用总数上限 32，专属停止原因 `tool-call-runaway`，
     与 `max_turns` 可独立触发，产品入口走默认值且无开关，触发时账仍完整。
4. **H1 的四条预测与实测的逐条对照**（不吻合的原文保留在 §6，未回头改）：
   **①a 连不上端点 → 吻合**（session 载体漏、账本不漏，三项记 0 是对的）；
   **①b 空回答 → 不吻合**：预测「账本对该路径系统性偏低」，实测**不偏低**。
   预测里「usage 只以字符串形式存在、拿不回来」这句**对改动前的实现属实**，
   不吻合的是「所以账本会偏低」这个结论 —— D1 选定 (i) 把前提改掉了。
   该条判据自此转为**守护性回归**（`RoutingError.usage` 一旦被摘掉当场红）；
   **② 熔断早返回 → 吻合**（session 记了、`trace.turns` 没记）；
   **③ `STOP_MAX_TURNS` → 吻合**（不漏）；**④ `STOP_ANSWERED` → 吻合**（不漏）。
5. **未声称满足 WBS「工具调用轮数上限」的字面措辞。** 本 plan 按「**工具调用**」那一维实现
   （轮数已由 `max_turns` 占用，一次回复可携带 K 个 `tool_call`）。
   `DECISIONS.md` 是 blocked 面，**一个字未改**；重读留痕在 D3 与 `module-boundaries.md` §7.11。
   **人若按字面读作「轮数」，须回到轮数口径重做。**

### 另外照实记的三件事（不属上面五条）

- **活端点只跑了一次**，且那一跑**没走到异常出口、没触发失控闸**
  （`stopped == "answered"` · `model_tool_calls == 9`，远在 32 之下）——
  那两件由 `tests/unit` 的判据证明，**不由那一跑证明**。**一跑不是成本分布。**
- **不与任何数字作优劣比较**（§8 风险 ⑦）：本跑 58,579、P1.4 那跑 45,195、
  roadmap 记的 9.7 万–12.8 万，是**三次不同的解释**，本 plan 没做任何成本工作。
- **活端点第一次尝试没跑完**：在 10 分钟执行超时上被掐断、无产物；原样复跑一次即成功
  （102.0 秒）。**两次的差异未定位，不猜根因**（裁判规则 3）。

Closure Audit Evidence:

- Auditor / Agent: **未做（留白）** —— 本轮执行环境不具备独立子代理，执行者自审不算独立。
  先例：P1.3 / P1.4 / P1.5 / P1.6 首次收口均为同一形态（其中 P1.4 / P1.6 后由独立会话补做）。
- Evidence: 上表七条命令的退出码 · `docs/evidence/p1-cost/`（活端点轨迹与账本）·
  `docs/architecture/module-boundaries.md` §7.11（落点节）· `docs/masterplan/STATE.md` §3
  的 `[open] 2026-08-24T22:05Z`（needs-human，只追加）· `docs/logs/2026/08-24.md`（当日聚合日志）·
  M1–M8 变异自查逐条打红的对照表（Phase 2）。

Follow-up:

- **两条 🔴 门禁文件由人创建**（§11 已裁定，`out-of-scope improvement`，红线 1 禁止 loop 创建）。
- **`docs/backlog/implementation-roadmap.md:117` 与 `docs/backlog/p1-insight-roadmap.md:64`
  的旧措辞由人改准**（归属交人，§1.6 ⑥⑦）。
- **`STATE.md` 那条 `[open] 2026-08-24T08:56Z` 的第 ③ 项由人处置**（已被 D-18 与本 plan 实质取代；
  本 plan 只追加一行指明，未改写那条 open）。
- **独立关闭审计待补**（本轮留白）。

⚠️ **确认的缺陷一条都不在这里** —— 上面四条都是「红线禁止 loop 做」或「归属在人手上」，
不是「查出来了但不修」。
