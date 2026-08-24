# P1.5 巡检器（纯规则引擎）+ 洞察 Agent（归因）

> Plan Status: completed
> Mission: p1-insight
> Work Item: 7. 巡检器（纯规则引擎）+ 洞察 Agent（归因）（P1.5，见 D-15）
> Execution Order: 2 / 2（本批第二个；**前置是同批第一个** `docs/plans/p1-insight/2026-08-24-1755-1-explain-agent-and-evidence-gate.md`）
> Last Reviewed: 2026-08-24（起草基线 sha `5ffb8fb`；**执行期已按 §0 重取基线 → 执行基线 `04aa9ea`**，红线自查以它为 diff 基线）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 7 · `docs/masterplan/02-WBS.md` §4 **P1.5 行** · `docs/masterplan/DECISIONS.md` **D-15**
> Related: 前置 P1.4（同批第一个）· 后继 P1.6（行业包 v0）
> Audit: required

## 0. 执行前必做：重取基线

**本 plan 起草时，它的前置（P1.4，同批第一个 plan）尚未执行**，`agenerp/explain/` 在起草基线
sha `5ffb8fb` 上**不存在**（`ls agenerp/` 实读）。因此：

- **开工第一件事是重读仓库**，把 §1 的每一条与当时的实际代码逐条核对，
  不吻合的就地改写 §1 并把改动记进 `## Draft Review Record` 的续行。
- **D3 必须在 Phase 2 开工前重新绑定到真实符号**：起草期 P1.4 的入口只是「`agenerp/explain/__init__.py`
  的唯一入口」这个**承诺**，`agenerp/explain/` 当时并不存在，因此 D3 里没有符号名。
  开工时把 D3 的「复用 P1.4 的入口」**改写成那个真实导出符号**，并把改写记进 §9。
- **若 P1.4 尚未 `completed`**：Phase 2（洞察 Agent）**不得开工**——它消费 P1.4 的入口。
  Phase 1（巡检器）**不依赖 P1.4**，可以先做（见 §1.5）。
- **停滞分支（写死，免得执行期临时发明）**：若 Phase 1 已收口而 P1.4 仍未 `completed`，
  **不许**把 Phase 2 降级成 follow-up（§10 禁止），也**不许**空等把本 plan 挂着 ——
  按 authoring guide **Minimum Rule 10** 走**记录在案的 scope change**：
  把 Phase 2 整体移交给一个**具名后继 plan**（`docs/plans/p1-insight/<日期>-N-insight-agent-attribution.md`），
  在本 plan §11 写明移交理由与重开条件，本 plan 只以 Phase 1 + Phase 3 的巡检器那一半收口，
  且**收口时逐字写明 WBS §4 P1.5 只满足了两条 🔴 里的哪一条**。
- 本节存在的理由是硬约束②的同一条精神：**起草期的假设要写死，执行期要逐条对照**，
  不许把起草期的推测当成实测基线。

### 0.1 执行期重取基线的**实读结果**（2026-08-24，执行基线 sha `33c65b4`）

`git log -1` → `33c65b4`；`git status --porcelain` 非空（`tools/loop-supervisor.sh`、
`tools/loopx-writeback.sh` 两处**开工前既有的**未提交改动，与本 plan 无关，本 plan 不碰它们）。
逐条对照 §1：

| §1 的条目 | 执行期实读 | 结论 |
|---|---|---|
| §1.3 `agenerp/pack.py` 是定制包 | 仍然如此 | **吻合** |
| §1.3 `queries.py` 的 `rule_lookup` 指名报错 | 逐字仍在（`agenerp/tools/queries.py`） | **吻合** |
| §1.3 `anomaly.scan` / `benchmark.compare` 不在十个只读契约里 | 逐字仍在（`agenerp/tools_readonly.py:9`） | **吻合** |
| §1.4 `ORDER_QTY/INHOUSE_QTY/SUBCON_QTY/DELIVERY_QTY/SHORTFALL_QTY` | `agenerp/seed/model.py:38-42` 逐字仍在 | **吻合** |
| §1.4 `EXPECTED_BACKLOG_QTY = 1010.0` | `agenerp/seed/checks.py:23` 逐字仍在 | **吻合** |
| §1.6 CI `lint` 作用域七个目录 | `.github/workflows/gates.yml:584` 逐字相同 | **吻合** |
| §0 「`agenerp/explain/` 不存在」 | **已过时**：P1.4 已执行完（`a39070f` / `33c65b4`），`agenerp/explain/` 在仓 | **就地改写，见下** |

**§0 的过时条目就地改写**：`agenerp/explain/` 现在存在，`__init__.py` 的导出面**只有两样**
—— `explain`（入口）与 `ExplainResult`（返回类型）。同批第一个 plan 的
`Plan Status: completed`（实读该文件第 3 行），**四个 Phase 全 `completed`、`[ ]` 项为 0**。
→ **Phase 2 的开工前置成立**，§0 的停滞分支（把 Phase 2 移交后继 plan）**未被触发**，
§11 因此不记移交。

**D3 的符号重绑**（§0 要求的那一条）：D3 里的「复用 P1.4 的入口」自本节起读作
**`agenerp.explain.explain`**（`agenerp/explain/__init__.py` 的 `__all__` 两项之一，
返回 `ExplainResult`）。改写理由与出处见 §9 的执行期续行。

**开工前四条验证命令的基线**（改一行代码之前跑）：
`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **0**（389 passed）；
`python3 -m pytest tests/contracts -q` → **0**（151 passed）；
`python3 -m pytest tests/tools -q` → **0**（81 passed, 12 skipped）；
`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **0**（All checks passed!）。

## 1. Current Baseline

**起草基线 sha `5ffb8fb`**（`git status --porcelain` 无输出）。以下每条本轮实读。

### 1.1 D-15 已经把 P1.5 拆成两件东西，且**明说这可能改设计**

`docs/masterplan/DECISIONS.md` D-15「⚠️ 对 P1 的具体后果（**可能改设计**）」逐字：

> **洞察 Agent 的「巡检」这一段，本质是纯规则执行。** 行业包若是声明式规则清单
> （P1.6 要求「每条带 `test_case`」），那么「按清单逐条查、命中即报」**是代码，不是 Agent**。
> 模型真正不可替代的位置在**命中之后**：为什么会这样、要不要紧、该怎么办 —— 那才是模糊的。
> → P1.5 的措辞「洞察 Agent 按行业包规则清单巡检」应重估：**巡检器（规则引擎）与解释器（Agent）
> 是两件东西**，混在一个「Agent」里会让规则的确定性被模型的随机性污染，且成本白花

同表「反向边界（不许滥用）」逐字：判据是**「路径能否预先枚举」**，不是「看起来复不复杂」。
→ **归因叙述的组织枚举不完**，那一段仍归模型；**巡检枚举得完**，那一段必须是代码。

### 1.2 `docs/design/agents-and-roles.md` §5.0 ② 给了巡检器存在的实测理由

Spike 08 实测：老板身份 + 34 个业务 DocType 只读权限 + 开放式指令「你自己找异常」，
Agent 找到两笔逾期账款，**漏掉 1,010 台积压**并把该区域判为「✅ 正常」（依据 `achievement_rate = 100%`）。
文中给出的原因表逐字：逾期账款的异常**在一个字段上**，积压**不在任何字段上**，
必须「汇总入库 − 出库，对照订单量判断『多出来的有没有道理』」，前提是
**「必须先知道『产出远大于销出』是个问题」**。

→ 结论逐字：「**『无需指令』成立，『无需规则』不成立。**」这就是消融判据的靶子。

### 1.3 「行业包」今天在本仓**不存在**，且与 `agenerp/pack.py` 的「包」**不是一回事**

- `agenerp/tools/queries.py:124` 的 `rule_lookup` docstring 逐字：「**本期没有行业包，
  因此它的完整正确行为就是指名报错。**……**不伪造一个空包**，返回空会被读成
  『查过了，没有规则』。**重开事件是 P1.6 交付第一个行业包**」。
- `agenerp/pack.py` 的「包」是**定制包（customization pack）**——Custom Field / Property Setter
  的导出与 apply（`module-boundaries.md` §11），**与行业规则包毫无关系**。
  → **命名必须消歧**，见 `Decision` D2；本 plan 不得复用 `pack.py` 的任何结构。
- `anomaly.scan` / `benchmark.compare` **不在十个只读契约里**，
  `agenerp/tools_readonly.py:9` 逐字给了排除理由：「属洞察 Agent，依赖行业包规则（P1 才有）」。

### 1.4 固定测例已经就绪，且它的构造是**可复算的**

roadmap「已经就绪的前置」逐字：成品仓积压 **1,010 台 / ¥3,110,200**；
算式在 `docs/design/agents-and-roles.md:71`（**§5.0 ①**，不是 ②）：
**入库 2,000（自制工单 1,000 + 外协收货 1,000）− 发货 990 = 1,010**；
§5.0 ② 的 `:105` 说的是另一件事（发现方式「汇总入库 − 出库」），**两条不许混引**；
账面全绿的原因是订单被人工置为 `Closed`（`status = "Closed"` + `per_delivered = 99`，STATE §3 `[resolved] 2026-08-23T09:22Z`）。
站点侧对账 30 项（`python3 -m agenerp.seedsite --verify-site` 退 0）是这套数的既有守卫。

**这套数在代码里是常量，不是手抄的**（本轮实读）：`agenerp/seed/model.py:38-42` →
`ORDER_QTY = 1000` / `INHOUSE_QTY = 1000` / `SUBCON_QTY = 1000` / `DELIVERY_QTY = 990` /
`SHORTFALL_QTY = 10`；`agenerp/seed/checks.py:23` → `EXPECTED_BACKLOG_QTY = 1010.0`
（注释逐字「这个数据集存在的理由」）。
→ **Phase 1 的夹具必须由 `agenerp/seed/` 派生，一行数据都不许手写**（见 `Decision` D4）。

→ 巡检器 v0 的最小规则集必须能命中它，**且不许照单号写规则**（同 L3 的教训：
照答案写规则会自证为真而毫无信息量）。

### 1.4a 「判自由文本前先跑通标注集」这条新规矩，**对本 plan 是真约束，不是例外**

起草期间人往 roadmap 追加了一节（`e08ca4b`）：**「⚠️ 判自由文本答案之前，先跑通标注集
（P1.4 / P1.5 动手前必读）」**，指向 `tests/fixtures/p1_entry_gate_labels.jsonl`（24 条人工标注）
与 `tests/unit/test_answer_judging_fixture.py`，理由是人侧用关键词正则判答案**判了四次、四次都判错**。
该节对 P1.5 的措辞逐字：「**P1.5 判『洞察 Agent 找没找到』……比 P1.0 那道题更难判**」。

→ **本 plan 的判据分成两侧，逐条点清，不许含糊**：

| 判据 | 哪一侧 | 依据 |
|---|---|---|
| H1 消融（命中 / 零命中 + 数量等于 `EXPECTED_BACKLOG_QTY`） | **结构化事实** | 命中是结构化记录，不是自由文本 |
| H2 零 LLM（调用次数 == 0 + 阳性对照） | **结构化事实** | 判的是调用次数 |
| H3 无关数据不误报 | **结构化事实** | 判的是命中集合 |
| H4 取证不足时归因被门禁拒 | **结构化事实** | 判的是轨迹，不是归因文本 |
| 「巡检结论不可被模型改写」 | **结构化事实** | 判的是命中记录逐字不变 |

→ **本 plan 因此不写任何自由文本判定器**：归因文本的**质量**（说得对不对、有没有道理）
**不在本 plan 的判据里**。
⚠️ **反过来的约束写死立着**：执行期若要补一条「归因说得对不对」的判据，
**它落在自由文本那一侧**——必须先让判定器跑通那 24 条标注（`tests/unit/test_answer_judging_fixture.py`
已在仓，含「一律判 correct 会失败」的元判据），跑不通就不许往下写。
**本 plan 不开这个口子，也不把「归因质量」算进任何 Exit Criteria。**

### 1.5 Phase 1 不依赖 P1.4，Phase 2 依赖

- **巡检器是纯规则引擎，零 LLM**：它只需要站点只读查询（`agenerp/site.py` + `agenerp/tools/` 已在）。
- **洞察 Agent 的归因**需要取证与叙述，那是 P1.4 交付的解释循环。
  本 plan **不另起第二条控制循环**（那会让证据充分性门禁在洞察侧失效）。

### 1.6 判据落点的硬约束（与同批第一个 plan **同一条**，不重复推导）

`.github/workflows/gates.yml` 步骤 ⑦ 写死了 `tests/` 的目录集合，新增目录即红，而
`.github/workflows/**` / `missions/*.json` / `tests/gates/**` 三者在
`docs/context/ai-autonomy-policy.md` Protected Areas 里**全是 `blocked`**。
→ **本 plan 的判据一律落 `tests/unit/`**；WBS §4 P1.5 的两条 🔴 门禁
（`tests/gates/test_insight_rule_ablation.py` + 巡检器零 LLM 门禁）**本 plan 不得创建**，
按 P1.0a 先例交付断言体并交接给人（Phase 3）。

## 2. Goals

1. `agenerp/inspection/` 落地**巡检器**：声明式规则清单 → 逐条查 → 命中即报，**零 LLM 调用**。
2. 交付**规则的声明形状 v0**（含 `rule_id` / 判据表达 / `test_case`），
   并自带**够跑固定测例的最小规则集**；行业包 v0 的内容归 P1.6。
3. **消融判据**：抽掉那条规则，固定测例就查不出来 —— 证明发现力来自规则而非模型。
4. `agenerp/insight/` 落地**洞察 Agent**：只负责命中**之后**的归因，
   取证走 P1.4 的解释循环（含证据充分性门禁），**不另起循环**。
5. 判据落 `tests/unit/`，`GATE_VERIFY` 与 CI 两侧都复跑得到。

## 3. Non-Goals

1. **不交付行业包 v0**（P1.6）。本 plan 的最小规则集是**引擎自带的判据夹具**，
   不是行业包制品；收口时不得说成「行业包已有」。
2. **不翻转 `rule.lookup` 的报错行为**。`queries.py:124` 的 docstring 逐字写着重开事件是 **P1.6**；
   本 plan 若翻转它，等于替 P1.6 宣布行业包已装载。
3. **不实现 `anomaly.scan` / `benchmark.compare` 两个契约**（它们不在十个只读契约里，
   新增契约要动 `tools_readonly.py` 的契约表与 `tests/contracts` 的回归面，属另一个交付面）。
4. **不另起第二条控制循环**（见 §1.5）。
5. **不写任何业务数据**（②端只读）。
6. **不动** `agenerp/pack.py`（定制包，与行业规则包无关）。
7. **不动** `missions/**` / `.github/workflows/**` / `tests/gates/**` / `docs/masterplan/` 已有行。
8. **不判归因文本的质量**（说得对不对、有没有道理）。理由与边界见 §1.4a：
   那属**自由文本**判定，受 roadmap「先跑通标注集」一节约束。
   **归因质量不进本 plan 的任何 Exit Criteria 与 Closure Gates**；
   要补这条判据须先让判定器跑通那 24 条标注，且属另一个 plan。

## 4. Task Route

- Type: `app-layer design change`（D-15 已逐字预告「P1.5 的措辞应重估」，本 plan 把重估结果落成代码与 owner doc）
- Owner Docs: `docs/design/agents-and-roles.md` §5.0 ② / §5.1 · `docs/architecture/module-boundaries.md`（**新增 §7.9**）· `docs/masterplan/DECISIONS.md` D-15（**只读，不改**）
- Skill Selection Basis: `docs/skills/README.md` 无对应方法件；评审与收口走独立子代理。各 Phase 记 `Skill: none`。

## 5. Infrastructure And Config Prereqs

- **Phase 1 零外部依赖**：巡检器判据全部在假站点上跑（零网络、零凭据、零 docker、**零 LLM**）。
- **Phase 2 的归因判据**用假 transport，不调真模型。
- **Phase 3 的一次实跑**需要活站点四个 `AGENERP_*`。**凭据齐备时必做**；不齐备时照实记
  「未跑 · 未验证」并在 §10 逐字写 `verification scope limited`。**没有第三种处置**（Phase 3 的同一项已如此写）。
- 无 DDL、无写操作。

## 6. 开工前写死的假设（硬约束②）

- **H1（消融）**：最小规则集完整时，巡检器在**由 `agenerp/seed/` 派生的**数据集上
  **报出成品仓积压这一条**；把该条规则从清单里抽掉后，**同一次巡检零命中**。两侧都成立才算吻合。
  **命中记录必须带一个算出来的数**，并断言它等于 `agenerp/seed/checks.py:23` 的
  `EXPECTED_BACKLOG_QTY`（1010.0）—— 只断言「报出了一条」分不清「算出来的命中」
  与「写死的命中」（硬约束①）。
  ⚠️ **一个数据集还是不够**：只在固定测例上断言「== 1010.0」，
  一个把 `1010.0` 写死进命中记录的假实现照样全绿（**P1.3 的 M6 就是这样第一轮绿的**）。
  → **H1 必须跑两个数据集**：固定测例 + **一个按 `agenerp/seed/model.py:38-42` 的
  `INHOUSE_QTY` / `SUBCON_QTY` / `DELIVERY_QTY` 改过参数、期望积压量不等于 1010 的**第二个，
  断言命中里的数**随之变化**。写死的实现在第二个上必然红。
- **H2（零 LLM）**：整条巡检路径上**没有任何一次模型调用**。
  **探针的安装点写死**：把 `agenerp/routing` 的 adapter / transport 构造面**整体换成
  一被调用就直接失败的替身**（进程级），**不是**给巡检器留一个「可注入模型」的口子再往里塞替身
  —— D-15 要求巡检器**根本没有模型接缝**，往接缝里塞替身这件事本身就假设了接缝存在。
  **必须配阳性对照**：同一测试模块里另跑一条**故意调模型**的路径，同一个探针**必须让它失败**。
  没有阳性对照的「零调用」什么都没测 —— 替身没装上、或装错了位置，两种情况都会静静地绿。
- **H3（不许照答案写规则）**：规则的表达里**不出现任何具体单号**；
  用一条**与积压陷阱无关**的合成数据反测，规则不得在它上面误报。
- **H4（归因不绕过取证门禁）**：洞察 Agent 的归因走 P1.4 的循环，
  取证不足时**同样被证据充分性门禁拒绝**——判据落在轨迹上。

## 7. Execution Plan

### Phase 1 — 巡检器：纯规则引擎（零 LLM）

Status: completed
Targets: `agenerp/inspection/` · `tests/unit/test_inspection_rules.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: 无（不依赖 P1.4）

- [x] **Decision D1 · 规则的声明形状 v0。** 至少含 `rule_id`、人话陈述、
      **确定性判据表达**、`test_case`（P1.6 的验收原文「无 `test_case` 的规则即失败」，
      形状必须现在就留出这个位）。备选：(A) 自由 Python 谓词 —— **否决**：不可 diff、不可迁移，
      违背北极星里的「可 diff、可回滚、可迁移的产物」；(B) **声明式数据 + 有限算子**（选定）；
      (C) 直接照搬 `agenerp/contracts.py` 的 `Condition` —— **否决**：那套算子是给工具契约的
      前置/后置设计的，语义是「什么时候允许停下来」，与「业务数据是否荒谬」不是一回事，
      硬套会让两处语义互相污染。**残余风险**：有限算子集在 P1.6 填内容时可能不够用，
      重开条件写进 §11。
- [x] **Decision D2 · 模块与目录命名消歧（`constrained choice`：备选被既有命名与标准库挤掉，无实质取舍空间）。**
      `agenerp/pack.py` 已占用「包」，
      `inspect` 是标准库名。选定 `agenerp/inspection/`（巡检器）与 `agenerp/insight/`（洞察 Agent），
      **两者分开**是 D-15 的直接后果，不许合并成一个模块。
- [x] **Add** 规则清单的装载与校验（无 `test_case` 即拒绝装载）
- [x] **Add** 巡检执行体：按清单逐条查、命中即报，产出结构化命中记录（可 diff）
- [x] **Add** 最小规则集：**一条**够命中固定测例的规则（产出 vs 销出的口径），
      措辞保持通用，**不出现任何具体单号 / 数量**
- [x] **Proof H1** 消融：完整清单 → 报出；抽掉该条 → 零命中
- [x] **Proof H2** 零 LLM：模型侧替身在被调用时直接失败，整条路径跑完仍绿
- [x] **Proof（缺 `test_case` 必须拒载）** 装载一条**没有 `test_case`** 的规则，
      装载器必须**拒绝**（抛错 / 拒载），**不许是「过滤掉它然后静默继续」** ——
      静默过滤在退出码上与正确实现长得一模一样，而 P1.6 的验收原文是
      「无 `test_case` 的规则**即失败**」。**这是 M4 的杀手。**
- [x] **Proof H3** 反测：与积压陷阱无关的合成数据上不误报
- [x] **Proof（规则声明的结构判据）** 直接对**序列化后的规则声明**断言：
      **不含任何单据号字面量**（ERPNext 单号形状：至少三段全大写数字，如 `SAL-ORD-2026-00001`），
      **也不含 `1010` / `2000` / `990` 这三个数**。
      D1 选了「声明式数据 + 有限算子」，规则因此是可读的数据结构 —— 这条判据成立正是那个选择换来的。
      **这是 M7 的杀手**；没有它，「不许照答案写规则」就只是一句劝告。
- [x] **Decision D4 · 判据夹具由 `agenerp/seed/` 派生，不许手写数据行。**
      备选：(A) 在测试里手写几行库存与单据 —— **否决**：手写夹具可以被调到「怎么写规则都命中」，
      消融判据就测不出发现力（硬约束①）；(B) **从 `agenerp/seed/` 的常量与装载模型派生**（选定），
      命中记录里的数与 `checks.py:23` 的 `EXPECTED_BACKLOG_QTY` 对齐。
      **两侧取数的方向写死，不许合并**：夹具（数据）从**构造侧**取
      （`agenerp/seed/model.py` / `dataset.py` 的常量与装载模型）；期望值从
      `agenerp/seed/checks.py:23` 取。`checks.py:18-20` 的注释逐字警告过原因：
      「这一段刻意不从 `agenerp.seed.model` 取数。从那里取会让断言变成**同义反复**——
      改一个构造常量，数据与期望一起动，判据不会发红。」**本 plan 照抄这条纪律。**
      第二个数据集（见 §6 H1）的期望积压量**由本 plan 在判据里显式写死一个字面量**，
      同样不从构造常量算出来。
      **残余风险**：夹具与种子数据集**耦合**了——种子改了夹具会跟着变。
      这是想要的耦合（改了就该红），但收口时须逐字登记，不许说成「夹具独立」。
- [x] **Proof** 变异自查 **M1–M8 —— 八个变异在此逐字写死**，不许执行期看着自己的实现现编：
      **M1** 巡检器把命中写死（不读规则清单）；
      **M2** 规则清单里那条被抽掉后仍然报出命中（消融失效）；
      **M3** 命中记录里的数量写死成 1010 而不是算出来的；
      **M4** 装载器接受**没有 `test_case`** 的规则（由下面那条「缺 `test_case` 必须拒载」的 Proof 打红；
      **H1/H2/H3 与结构判据都杀不了它** —— 最小规则集自己带着 `test_case`，把校验删掉它们照样全绿）；
      **M5** 巡检路径上偷偷调一次模型（H2 的探针必须打红）；
      **M6** 阳性对照那条故意调模型的路径被改成不调（探针必须由绿转红——**这是探针自身的判据**）；
      **M7** 规则表达里写死具体单号或具体数量（**由下面那条「规则声明的结构判据」打红，
      不是 H3** —— H3 只判「无关数据上不误报」，一条钉死单号的规则在真夹具上照样命中、
      在无关数据上照样不命中，H3 对它是绿的）；
      **M8** 巡检器对无关合成数据误报（规则口径被放宽）。
      任一变异打不红即说明判据有缺口，**就地补断言并登记为 M9…**，不许略过
      —— **执行期实测结果照实记**：M1/M2/M3/M4/M5/M6/M8 **一轮就红**；
      **M7 第一轮是绿的**（变异形态：把 `对应 SAL-ORD-2026-00001，预期 1010` 塞进规则声明的一个
      装载器不认识的键里）。根因是装载器**静默丢弃未知键**，于是那句话在源码里明晃晃写着、
      在序列化后的声明里却看不见，而结构判据只判后者。
      → **就地补了两条断言**（不是放过）：① 结构判据改为**源声明与装载后形态两侧都判**；
      ② 装载器**未知键一律拒载**（`rules.py` 的 `_reject_unknown`，逐层有限键集）。
      → **登记 M12**（**不是 M9** —— M9/M10/M11 已被 Phase 2 预先占用，续编从 M12 起，
      免得两处同号）：「答案夹带在装载器不认识的键里（源声明可见、序列化后不可见）」——
      由上面两条断言打红。补断言之后 **M1–M8 + M12 九个变异逐个复跑，全部由绿转红**。

Exit Criteria:

- [x] H1 / H2 / H3 与 §6 原文逐条对照，吻合与否照实记
- [x] **四条验证命令全退 0**：① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`；
      ② `python3 -m pytest tests/contracts -q`；③ `python3 -m pytest tests/tools -q`；
      ④ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
      （CI `lint` job 第 569 行的原文作用域，新增的 `agenerp/inspection/**` 全在里面）
- [x] owner-doc 落地**延至 Phase 3**（§7.9）；本阶段不改任何 owner doc

Phase 1 执行记录（sha `33c65b4` 基线上落地）：

- 落点：`agenerp/inspection/{__init__,rules,engine,minimal}.py` ·
  `tests/unit/inspection_fakes.py` · `tests/unit/test_inspection_rules.py`（16 条）
- **H1 与 §6 原文对照 → 吻合**。固定测例（`agenerp/seed/generate()` 派生）恰好报出**一条**，
  `subject = {item_code: HRD-PACK-5K, warehouse: 成品仓 - HRD}`，
  `quantity == EXPECTED_BACKLOG_QTY`（`agenerp/seed/checks.py:23`，取自**期望侧**）。
  抽掉那条规则 → 零命中；另把同一条规则的 `trigger.value` 由 `0.5` 改到 `10.0` → 也零命中
  （证明引擎读的是判据表达，不是清单长度）。
  **第二个数据集**（`INHOUSE_QTY→800` / `SUBCON_QTY→600` / `DELIVERY_QTY→500`）
  命中量 `== 900.0`（判据里写死的字面量，不从构造常量算）且 `!= 1010.0` —— 数**随之变化**。
- **H2 与 §6 原文对照 → 吻合，且比 §6 多一条**。探针按 §6 装在**进程级**：
  `ChatAdapter` 的 `__init__` / `chat` / `_send` / `_post`、`_ssl_context`、`urllib.request.urlopen`
  一律换成一被碰就抛 `ModelCallDetected` 的替身；巡检器**没有**任何可注入模型的口子。
  **阳性对照**在同一模块：`route("explain", …)` 在同一探针下必抛（M6 由它打红），
  另配一条「探针不装时那条路径是通的」以排除红在别的原因上。
  **多出来的那条**：全新解释器里 `import agenerp.inspection` 之后
  `agenerp.routing` **不在 `sys.modules`** —— 判的是导入图（可观测量），不是源码文本（风险 ②）。
- **H3 与 §6 原文对照 → 吻合**。合成的无关轨迹（两个物料产多少卖多少、订单交清）零命中；
  规则声明里不出现任何单号（`DOC_NAME` 正则复用 `agenerp/explain/gate.py`，不另写）、
  不出现 `1010` / `2000` / `990`、不出现 `FINISHED_ITEM` / `WH_FINISHED`。
- 另有两条非 §6 要求但顺带钉住的事实：巡检请求**全是 `GET`**（②端只读）；
  命中记录两次跑**字节相同**（可 diff）。
- **变异自查 M1–M8 + M12 全红**（M7 的第一轮缺口与补断言见上一条）。
- 四条验证命令：见 `## Closure` 的证据表。

### Phase 2 — 洞察 Agent：命中之后的归因

Status: completed
Targets: `agenerp/insight/` · `tests/unit/test_insight_attribution.py`
Skill: `none`

- Item Types: `Add | Decision | Proof`
- Prereqs: **Phase 1 完成**，且 **P1.4（同批第一个 plan）已 `completed`**

- [x] **Decision D3 · 归因走 P1.4 的解释循环，不另起一条。**
      备选：(A) 洞察侧自己开一条轻循环（不带证据门禁）—— **否决**：那正是 §5.0 ① 要修的
      「停在第一层证据上」，在洞察侧重新打开这个口子等于把 P1.4 白做；
      (B) **复用 P1.4 的入口**（选定）：命中记录作为问题的一部分进循环，取证与门禁全部沿用。
      **残余风险**：命中记录里的数字会进答案文本，从而触发 L3 的取证要求 ——
      **这是想要的行为**（覆盖判据），但会抬高单次归因成本，照实登记。
- [x] **Add** 命中 → 归因的接线：一条命中产出一段归因（为什么会这样 / 要不要紧），
      归因文本与**取证轨迹**一起落盘，可回放
- [x] **Add** 边界执行：巡检器**不接受**模型输出改写命中结果（确定性不被随机性污染，D-15）
- [x] **Proof H4** 取证不足时归因**被证据充分性门禁拒绝**，判据落在轨迹上
- [x] **Proof** 断言「巡检结论不被模型改写」：给替身模型一个与命中相反的输出，
      最终命中记录**一个字不变**
- [x] **Proof** 变异自查续编，**三个在此写死**：
      **M9** 洞察侧绕开 P1.4 循环、自己直连模型（D3 的判据必须打红）；
      **M10** 取证不足时归因照样交出（H4 必须打红）；
      **M11** 模型输出被用来改写命中记录（「不可被改写」那条必须打红）。
      打不红即补断言并续编 M12…

Exit Criteria:

- [x] H4 与 §6 原文对照并记录
- [x] 「巡检结论不可被模型改写」有一条独立断言
- [x] Phase 1 的四条验证命令**原样复跑一遍**并全退 0（洞察侧改动不得把巡检侧打红）
- [x] owner-doc 落地**延至 Phase 3**（§7.9）；本阶段不改任何 owner doc

Phase 2 执行记录：

- 前置核对：P1.4（同批第一个 plan）实读 `Plan Status: completed`、四个 Phase 全 `completed`、
  `[ ]` 项为 0 → **开工前置成立**，§0 的停滞分支未触发。
- **D3 的符号重绑（§0 要求的那一条）**：「复用 P1.4 的入口」= **`agenerp.explain.explain`**，
  返回 `ExplainResult`。`agenerp/insight/attribution.py` 逐字消费它，**不另起循环**。
- 落点：`agenerp/insight/{__init__,attribution}.py` · `tests/unit/test_insight_attribution.py`（9 条）
- **H4 与 §6 原文对照 → 吻合**。取证不足的那一次：`accepted is False`、`answer == ""`，
  轨迹上门禁记了两条不满足 —— L3 要求的两张入库凭证
  （`MAT-SCR-2026-00001` / `MAT-STE-2026-00003`，`missing_count == 2`）一张没查；
  补齐取证之后同一条归因被放行（`gate_checks[-1]["failed"] == []`）。判据全落在轨迹上。
- **「巡检结论不可被模型改写」有一条独立断言**：替身模型给出与命中**相反**的输出
  （「其实一台都没积压，这条命中应当撤销」），最终 `attribution.hit is hit`、
  `hit.as_dict()` 与进循环之前逐字相同、`report.hits[0]` 也一字未动。
  边界执行本身另有落点（`ensure_unchanged`），并有一条直接判据打它。
- **执行期新增的残余风险，照实登记（D3 选项 B 的代价，之前只记了一条）**：
  命中的 `subject` 里可能有**长得像单号**的取值 —— `HRD-PACK-5K` 是三段全大写数字，
  正好落进 `agenerp/explain/gate.py` 的 `DOC_NAME`，于是 **L1 把物料号当成「问题点名的单据」**
  并要求 `doc.links`。实测确认（判据里逐字断言了这一条）。
  **不擅自绕开**：门禁措辞归 owner doc 与人的裁定面，且它误报的方向是**更严**（保守侧）。
  归因成本因此比 D3 起草时估的还要高一点 —— 写进 §7.9 的判据缺口小节。
- **变异自查 M9 / M10 / M11 逐个复跑，全部打红。**
- Phase 1 的四条验证命令**原样复跑**：见 `## Closure` 的证据表。

### Phase 3 — 门禁交接 · owner doc 落点 · 日志

Status: completed
Targets: `docs/architecture/module-boundaries.md` · `docs/design/agents-and-roles.md` · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/`
Skill: `none`

- Item Types: `Fix | Proof | Follow-up`
- Prereqs: Phase 1, Phase 2

- [x] **Proof** 固定测例在**活站点**上跑一次巡检（零 LLM，成本可忽略），
      确认命中与离线夹具一致；跑不了就照实记「未跑 · 未验证」，**不得用夹具结果冒充站点结果**
- [x] **Fix** owner doc 落点：`module-boundaries.md` **新增 §7.9**「巡检器与洞察 Agent 在本仓的落点（P1.5）」
      —— 规则声明形状、**D1–D4 四个 `Decision`**、零 LLM 的判据口径、判据缺口与验证范围。
      **必须有一句显式的**「**巡检规则 ≠ 行业包制品**」：否则将来读到
      `agenerp/tools/queries.py:125`「本期没有行业包」时会误判成过期漂移（Non-Goals 1/2 的同一件事）
- [x] **Fix** `agents-and-roles.md` §5.1 的洞察行**只补落点指针**（`anomaly.scan` /
      `benchmark.compare` **仍未实现**这一事实照实写），**不改 §5.0 ② 的实测结论一个字**
- [x] **Follow-up → 交接**（**触发条件写死**：本 plan 的 Phase 1 与 Phase 2 全绿、
      且 §11 的移交分支未被触发；触发分支被走时，交接内容随之只剩巡检器那一条门禁）
      两条 🔴 门禁由**人**创建（红线 1）：
      `tests/gates/test_insight_rule_ablation.py` 与「巡检器在零 LLM 调用下跑通固定测例」那一条。
      本 plan 交付断言体在 `tests/unit/`，按 P1.0a 先例（「断言体不重写，按路径加载开发期那份」）；
      **并在 `docs/masterplan/STATE.md` §3 追加一条 needs-human**（只追加），
      含命令原文 + 退出码 + sha + 「本 plan 未创建门禁文件、未声称 WBS §4 P1.5 的 🔴 验收已满足」
- [x] **Fix** `docs/logs/` 按执行日写一条，含命令原文 + 退出码 + sha

Exit Criteria:

- [x] §7.9 存在；§5.1 只补指针未改结论
- [x] STATE §3 已追加（只追加）；`git diff docs/masterplan/` 除追加行外无改动
- [x] `docs/logs/` 已更新

Phase 3 执行记录：

- **活站点巡检一次 → 做了，退出码 0，命中与离线夹具逐字一致。** 凭据齐备
  （本地 compose 站点 `frontend@http://127.0.0.1:18080`，口径与 `.github/workflows/gates.yml` 的
  live job 相同）。命令原文与结果见 `## Closure` 的证据表。
  → **§5 的「不齐备则记未验证 + `verification scope limited`」这一支没有被走到**；
  但**归因那一半确实没有在活端点上跑过**，那一条照实写在 `## Closure` 与 §7.9 的验证范围里。
- **§7.9 已新增**（`docs/architecture/module-boundaries.md`），含规则声明形状、D1–D4 四个 `Decision`、
  零 LLM 的两个可观测量、判据缺口与验证范围，且逐字写了「**巡检规则 ≠ 行业包制品**」。
- **`agents-and-roles.md` §5.1 只补了落点指针**（10 行纯新增，`git diff` 删除行为 **0**），
  `anomaly.scan` / `benchmark.compare` **仍未实现**这一事实照实写；**§5.0 ② 的实测结论一个字未动**。
- **`docs/masterplan/STATE.md` §3 已追加一条 `[open]` needs-human**（只追加，`git diff` 删除行为 **0**），
  含四条命令原文 + 退出码 + 基线 sha + 「本 plan 未创建门禁文件、未声称 WBS §4 P1.5 的 🔴 验收已满足」。
- **`docs/logs/2026/08-24.md` 已追加一条**（含命令原文 + 退出码 + sha）。

## 8. 风险

| # | 风险 | 处置 |
|---|---|---|
| ① | **规则照着答案写** → 自证为真、零信息量 | H3 用无关合成数据反测；规则措辞禁止出现单号 |
| ② | **「零 LLM」退化成源码文本检查** | H2 判在「模型侧被调用次数 == 0」这个可观测量上，替身被调即失败 |
| ③ | **消融只验一侧** | H1 强制两侧（完整 → 报出；抽掉 → 零命中） |
| ④ | **洞察侧偷偷绕过证据门禁** | D3 选定复用 P1.4 入口；H4 判在轨迹上 |
| ⑤ | **模型改写巡检结论** | Phase 2 一条独立断言：相反输出下命中记录一字不变 |
| ⑥ | **最小规则集被读成「行业包已有」** | Non-Goals 1；`rule.lookup` 的报错行为不翻转（Non-Goals 2） |
| ⑦ | **起草期基线在执行期已过时**（P1.4 尚未落地） | §0 强制开工先重取基线；Phase 2 在 P1.4 未 `completed` 时不得开工 |
| ⑧ | **两条 🔴 门禁本 plan 交付不了** | Phase 3 按 P1.0a 先例交接；收口时不得声称验收已满足 |

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-24）
  —— 6 条 blocking，**逐条处置**：
  ① 验证命令集漏了 `ruff` 与 `tests/contracts`，而新增的 `agenerp/inspection/**` 就在 CI `lint` 的
  作用域里（`gates.yml:569`）→ 四条命令写进每个 Phase 的 Exit Criteria 与 §10；
  ② **H2「零 LLM」是空的** —— 「往接缝里塞替身」本身就假设了接缝存在，而 D-15 要求巡检器
  **根本没有模型接缝** → 探针安装点改为**进程级替换 `agenerp/routing` 的构造面**，
  并强制**阳性对照**（同模块里一条故意调模型的路径必须被同一探针打红）；
  ③ H1 的消融跑在**手写夹具**上，调得好怎么写规则都命中 → 新增 `Decision` D4：
  夹具**由 `agenerp/seed/` 派生**，命中记录必须带**算出来的数**并断言等于
  `agenerp/seed/checks.py:23` 的 `EXPECTED_BACKLOG_QTY`；
  ④ D3 没点名它消费的符号，且 P1.4 停滞时本 plan 无出口（§10 又禁止降级）→ §0 增两条：
  开工前把 D3 重绑到 `agenerp/explain/__init__.py` 的真实导出符号；
  **停滞分支写死**——按 authoring guide Minimum Rule 10 把 Phase 2 移交具名后继 plan，
  本 plan 只以巡检器那一半收口并逐字写明只满足了两条 🔴 里的哪一条；
  ⑤ §5「Phase 3 的一次实跑（**若做**）」命中 Anti-Slacking 禁用词，且与 Phase 3 自己的确定写法矛盾
  → 改成「凭据齐备时必做；不齐备照实记未验证 + `verification scope limited`」；
  ⑥ §1.4 把算式归给 §5.0 ②，实为 `agents-and-roles.md:71`（§5.0 ①）→ 改准，并点明 `:105` 是另一件事。
  另采纳 4 条非阻断项：D2 标注为 `constrained choice`；Phase 1/2 的
  `No owner-doc update required` 与「落点节统一在 Phase 3」自相矛盾 → 改为「owner-doc 落地延至 Phase 3」；
  `Follow-up` 项补触发条件；§7.9 必须写一句「**巡检规则 ≠ 行业包制品**」，
  免得将来把 `queries.py:125` 读成过期漂移。
  另主动补两处（非评审要求）：**M1–M8 / M9–M11 逐字写死**（P1.3 的 M6 第一轮是绿的，
  不写死等于允许执行期照着自己的实现现编）；新增 §1.4a —— 起草期间人追加的
  「判自由文本前先跑通标注集」一节，逐条把本 plan 的五条判据划到**结构化事实**那一侧，
  并写死「归因质量不进任何 Exit Criteria」。
- Independent draft review iteration 2: **needs revision**（同一独立子代理，2026-08-24）
  —— 6 条**全部判为已关闭**（含逐条回仓核实：`checks.py:23` 确为 `EXPECTED_BACKLOG_QTY = 1010.0`、
  ruff 作用域与 `gates.yml:569` 逐字相同、`agents-and-roles.md:71` 原文吻合、
  标注集确为 24 行），§1.4a 的「结构化事实」主张**被判为诚实而非规避**
  （理由：D-15 把「发现」整个移出模型后，「找没找到」变成结构化命中记录而不是自由文本；
  且本 plan 自己写死了「不补自由文本判据、归因质量不进 Exit Criteria」）。
  **但查出两条新 blocking：两个变异没有任何判据能打红它们。** 逐条处置：
  ① **M3 打不红** —— H1 只在固定测例上断言「== 1010.0」，一个把 1010.0 写死进命中记录的
  假实现照样全绿（**与 P1.3 的 M6 第一轮绿是同一种失败**）→ H1 改为**跑两个数据集**：
  第二个按 `model.py:38-42` 改参数、期望积压 ≠ 1010，断言命中里的数**随之变化**；
  并在 D4 里把两侧取数方向钉死（数据取构造侧、期望取 `checks.py`），
  照抄 `checks.py:18-20` 那条「从同一侧取会变成**同义反复**」的警告；
  ② **M7 打不红** —— 一条钉死单号的规则在真夹具上照样命中、在无关数据上照样不命中，**H3 对它是绿的**
  → 新增一条**规则声明的结构判据**（对序列化后的规则断言不含单号字面量、不含 `1010`/`2000`/`990`），
  并把 M7 的杀手从 H3 改指到它。
  另采纳一条非阻断项：「归因质量不进任何 Exit Criteria」原先只写在 §1.4a
  → 已补进 §3 Non-Goals 第 8 条，收口时只读 Non-Goals 也看得见。
- Independent draft review iteration 3: **needs revision（一条，一行修）**（同一独立子代理，2026-08-24）
  —— M3 / M7 两条**判为真正关闭**（评审逐字比对了 `checks.py:18-19` 的引文、
  确认结构判据的禁用字面量与规则的「产出 vs 销出」口径不冲突），
  并逐个走了 M1–M11 的「变异 → 杀手」对照表。
  **查出一条孤儿变异**：**M4（装载器接受没有 `test_case` 的规则）没有任何判据能打红它** ——
  `test_case` 强制只出现在 D1 与一个 `Add` 项里，而最小规则集自己带着 `test_case`，
  把校验删掉 H1/H2/H3 与结构判据**全都还是绿的**（**与 M7 修好之前是同一种形状**）。
  → 已新增一条 Phase 1 Proof：「缺 `test_case` 必须**拒载**（抛错/拒载，**不许静默过滤**）」，
  并按 M7 的写法把杀手名字写进 M4 的括注里。
  评审同时确认无新引入缺陷：Non-Goal 8 与 Phase 2 的交付项不冲突（排除的是判**质量**，不是不产出归因）。
- Independent draft review iteration 4: **acceptable as-is** —— **共识达成**（同一独立子代理，2026-08-24）
  —— M4 判为已可打红（新判据禁掉了唯一能让它活下来的写法：「静默过滤」与「正确拒载」在退出码上一模一样），
  且该判据有 owner-doc 锚（P1.6 验收原文「无 `test_case` 的规则**即失败**」）而不是执行者自创的标准。
  **十一个变异全部绑到了具名杀手**：M1/M2 → H1 消融；M3 → H1 的双数据集协变；M4 → 拒载判据；
  M5 → H2 的进程级探针；M6 → H2 的阳性对照；M7 → 规则声明的结构判据；M8 → H3；M9/M10 → H4；
  M11 → 「命中记录一个字不变」。新增项未引入任何冲突，不触任何红线路径。
  **结论：可作为执行契约 → `Plan Status: active`。**
  评审同时点名了三条**收口时必须保持可见**的诚实限制（本 plan 已各自写着）：
  ① 两条 🔴 门禁文件交人（P1.0a 先例），**不得宣称 WBS §4 P1.5 验收已满足**；
  ② Phase 2 在 P1.4 `completed` 之前不得开工，受 §0 的停滞分支与 D3 符号重绑约束；
  ③ 归因文本的质量本 plan 无任何判据（Non-Goal 8）。

- **执行期续行（2026-08-24，执行基线 sha `04aa9ea`）—— §0 要求的两处改写，逐条记在案**：
  ① **§1 逐条重读结果**：七条里六条**吻合**，唯一过时的是 §0 自己那句「`agenerp/explain/` 不存在」——
  P1.4 已执行完，该包在仓且 `Plan Status: completed`。就地改写在 **§0.1**，原 §0 一个字未删。
  ② **D3 的符号重绑**：「复用 P1.4 的入口」自 §0.1 起读作 **`agenerp.explain.explain`**
  （`agenerp/explain/__init__.py` 的 `__all__` 两项之一，返回 `ExplainResult`）。起草期它只是个承诺，没有符号名。
  ③ **停滞分支未触发**：P1.4 `completed` 已核实，Phase 2 正常开工，§11 因此不记移交。
- **执行期新增一个变异（M12），因为 M7 第一轮打不红**：装载器**静默丢弃未知键**，
  把 `对应 SAL-ORD-2026-00001，预期 1010` 夹带进一个不认识的键里 —— 它在源码里明晃晃写着、
  在序列化后的声明里却看不见，而起草期的结构判据**只判后者**。这与 M7 修好之前、M4 补上之前
  是**同一种形状**（判据只覆盖了实现的一侧）。已就地补两条断言（结构判据**两侧都判** +
  装载器**未知键一律拒载**，后者有 owner-doc 锚：未知键静默失效本身就是装载器的缺陷），
  编号取 **M12** 而非 M9 —— M9/M10/M11 是 Phase 2 起草期就写死的，同号会让两处指同一个变异。
- **执行期新增一条残余风险登记**（不是缺陷，是 D3 选项 B 的代价）：命中 `subject` 里的物料号
  `HRD-PACK-5K` 长得像单号，L1 会把它当成「问题点名的单据」。方向是**更严**，不擅自绕开。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.9 新增；§5.1 补指针）
- [x] verification has run：`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts -q` · `python3 -m pytest tests/tools -q` · `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` · Phase 3 的活站点巡检一次
- [x] scoped verification is not conflated with full verification —— **活站点那一次做了**（退出码 0，命中与离线夹具逐字一致），
      因此这条 gate 不走「未做」那一支；**但验证范围仍然有边**，逐条写在 `## Closure`：
      活站点跑的是**巡检那一半**，**归因那一半没有在活端点上跑过**（判据全是假 transport + 假站点），
      且**归因文本的质量本 plan 没有任何判据**。
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§9 四轮，第四轮 `acceptable as-is`）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— **本轮未做**，照实留白（先例：工作项 5 / 6 首次收口同此）。
      理由：本轮执行环境不具备独立子代理（会话级约束禁止执行器自行派子代理），
      而**执行者自审不算独立**。⚠️ **不得把 §9 的四轮起草评审读成关闭审计** —— 那是开工前的，判的是 plan；
      关闭审计判的是**已落地的实现**。重开条件：由独立会话（fresh session，不带实现上下文）在本 sha 上补做。
- [x] closure evidence exists in files
- [x] **红线自查**：`git diff --name-only` 对 `tests/gates/**` · `.github/workflows/**` · `missions/**` · `docs/masterplan/DECISIONS.md` 均无输出；`STATE.md` 只有追加行

## 11. Deferred But Adjudicated

> **§0 的停滞分支未被触发**（执行期实读：P1.4 `Plan Status: completed`），
> 因此本节**不记 Phase 2 的移交**，也不存在具名后继 plan。

### WBS §4 P1.5 的两条 🔴 门禁文件

- Classification: `out-of-scope improvement`（红线 1 禁止 loop 创建）
- Why Not Blocking Closure: 交付断言体 + 交接说明；P1.0a 已有同形态先例
- Successor Required: `yes` —— 由**人**创建
- 重开条件：人补齐后，§7.9 的「判据缺口」小节与 STATE §3 对应行须由人或后继 plan 收口

### 有限算子集在 P1.6 可能不够用

- Classification: `watch-only residual`
- Why Not Blocking Closure: v0 的判据是「够跑固定测例 + 形状可扩」，不是「覆盖离散制造全部规则」
- Successor Required: `no`
- 重开条件：**P1.6 起草时**发现某条业务合理性规则用现有算子集表达不出来 —— 届时由 P1.6 的 plan 决定是扩算子还是改形状

## Closure

Status Note:

三个 Phase 全部执行完毕，`Plan Status: completed`。执行基线 sha `04aa9ea`（§0.1 重取）。

**命令原文 + 退出码**（裁判规则 2；四条 + 活站点那一次）：

| # | 命令原文 | 退出码 | 输出 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0** | `门禁 11 项：预期红 0，绿 11，跳过 0` · `414 passed`（基线 389 → +25） |
| ② | `python3 -m pytest tests/contracts -q` | **0** | `151 passed`（与基线逐字相同） |
| ③ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped`（与基线逐字相同，零回归） |
| ④ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` |
| ⑤ | `AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -c "…inspect_site(minimal_rules(), client_from_env('frontend'))…"` | **0** | 一条命中：`on_hand 1010.0` / `received 2000.0` / `issued 990.0` / `ordered 1000.0` / `request_count 5` —— **与离线夹具逐字一致** |

**交付面**：`agenerp/inspection/`（`rules.py` / `engine.py` / `minimal.py` / `__init__.py`）·
`agenerp/insight/`（`attribution.py` / `__init__.py`）· `tests/unit/inspection_fakes.py` ·
`tests/unit/test_inspection_rules.py`（16 条）· `tests/unit/test_insight_attribution.py`（9 条）·
`docs/architecture/module-boundaries.md` §7.9（新增）· `docs/design/agents-and-roles.md` §5.1（只补指针）·
`docs/masterplan/STATE.md` §3（只追加）· `docs/logs/2026/08-24.md` · `docs/backlog/p1-insight-roadmap.md` 工作项 7。

**§6 的四条假设逐条对照，全部吻合，假设一个字未改**：H1（双数据集消融）· H2（进程级探针 + 阳性对照
+ 导入图）· H3（无关合成数据不误报 + 规则声明的结构判据）· H4（取证不足时归因被门禁拒，判在轨迹上）。
逐条实测记录见各 Phase 的「执行记录」小节。

**变异自查**：M1–M8（Phase 1 写死的八个）+ M9–M11（Phase 2 写死的三个）+ **M12**（执行期新增）
逐个复跑，**全部由绿转红**。⚠️ **M7 第一轮是绿的**，缺口与补断言见 Phase 1 执行记录与 §9 的执行期续行。

**必须保持可见的诚实限制**（§9 第四轮评审点名的三条，逐条仍成立，外加执行期新增的两条）：

1. **两条 🔴 门禁文件本 plan 未创建，也不声称 WBS §4 P1.5 的验收已满足。** 红线 1 禁止 loop 创建
   `tests/gates/**`。交付的是它们的**断言体**（见 §11 与 STATE §3 的交接行），由**人**按 P1.0a 先例按路径加载。
2. **Phase 2 的开工前置已核实成立**（P1.4 `completed`），§0 的停滞分支**未被触发**，D3 已重绑到
   `agenerp.explain.explain`。
3. **归因文本的质量本 plan 没有任何判据**（Non-Goal 8）。判自由文本要先跑通
   `tests/unit/test_answer_judging_fixture.py` 的 24 条人工标注 —— 本 plan 不开这个口子。
4. **verification scope**：活站点那一次跑的是**巡检那一半**（零 LLM）；**归因那一半没有在活端点上跑过**，
   本 plan 也不声称跑过。**不得把 ⑤ 的退出码读成「洞察 Agent 已在活站点验证」。**
5. **未交付行业包 v0**（Non-Goal 1/2）：最小规则集**一条**，是引擎自带的判据夹具；
   `rule.lookup` 的报错行为**未翻转**，重开事件仍是 P1.6；`anomaly.scan` / `benchmark.compare` **仍未实现**。

**红线自查**（在执行基线 `04aa9ea` 上跑）：

- `git status --porcelain -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md` → **无输出**
- `git diff --numstat -- docs/masterplan/` → `8	0	docs/masterplan/STATE.md`（**删除列为 0**，只追加）
- 其余文档改动同样是纯新增：`module-boundaries.md` `99	0` · `agents-and-roles.md` `10	0` ·
  `docs/logs/2026/08-24.md` `42	0`；`p1-insight-roadmap.md` `1	1`（动态状态块的那一行，本就是唯一可改的状态落点）

Closure Audit Evidence:

- Auditor / Agent: **未做** —— 本轮执行环境不具备独立子代理（会话级约束禁止执行器自行派子代理），
  **执行者自审不算独立**，因此这条 gate 照实留白，不勾。
- Evidence: 无。⚠️ §9 的四轮独立起草评审**不能顶这一条**：那是开工前的、判的是 plan；
  关闭审计判的是**已落地的实现**。重开条件：由独立会话（fresh session，不带实现上下文）在本 sha 上补做，
  先例见 plan `2026-08-24-1755-1` 的「独立关闭审计补做记录」。

Follow-up:

- 由**人**创建 WBS §4 P1.5 的两条 🔴 门禁文件（§11 第一条）。
- 由**独立会话**补做关闭审计（上一行）。
- 两条都**不是本 plan 确认的缺陷**，是本 plan 无权自己做的动作。
