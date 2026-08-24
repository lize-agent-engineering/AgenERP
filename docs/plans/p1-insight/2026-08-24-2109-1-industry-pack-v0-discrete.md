# P1.6 行业包 v0（离散制造）：每条规则带 test_case

> Plan Status: completed
> Mission: p1-insight
> Work Item: 8. 行业包 v0（离散制造），每条规则带 test_case（P1.6）
> Execution Order: 1 / 2（本批第一个；与同批第二个 `2026-08-24-2109-2-explain-cost-accounting.md` **无相互依赖**，顺序取 roadmap 原序）
> Last Reviewed: 2026-08-24（起草基线 sha `928a888`，`git status --porcelain` 无输出）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 8 · `docs/masterplan/02-WBS.md` §4 **P1.6 行** · `docs/masterplan/DECISIONS.md` **D-15 / D-12** · 前置 plan `2026-08-24-1755-2-inspector-and-insight-agent.md` §11「有限算子集在 P1.6 可能不够用」
> Related: 前置 P1.5（已 `completed`）· 同批第二个 P1.7（无依赖）
> Audit: required

## 0. 执行前必做：重取基线

起草基线是 sha `928a888`。**开工第一件事是重读仓库**，把 §1 每一条与当时的实际代码逐条核对，
不吻合的就地改写 §1 并把改动记进 `## Draft Review Record` 的续行（照 P1.5 §0.1 的做法列一张对照表）。

**必须重新实读、不许凭本文件转述的四处**：

1. `agenerp/inspection/rules.py` 的 `RULE_KEYS` / `MEASURE_KEYS` / `TRIGGER_KEYS` /
   `TEST_CASE_KEYS` / `ROW_FILTER_KEYS` 五个有限键集与三组算子常量 —— §6 的 H1 逐条依赖它们。
2. `tests/gates/test_tool_execution_live.py` 里 `rule.lookup` 那一条与它委派到的
   `tests/tools/test_live_conformance.py::test_live_rule_lookup_names_what_is_missing`
   —— §3 Non-Goal 2 的全部理由在这两处，**改任一处都越红线 1**。
3. `.github/workflows/gates.yml` 的 `pip install pytest certifi`（实读**五处**：`:104` / `:176` / `:241` / `:451` / `:505`）
   与步骤 ⑦ 的 `tests/` 目录集合断言 —— D2（格式取 JSON）与判据落点的依据。
4. `agenerp/seed/model.py` 的数量常量与 `agenerp/seed/checks.py` 的 `EXPECTED_BACKLOG_QTY`（`:23`）/
   `EXPECTED_SHORTFALL_QTY`（`:25`）/ `EXPECTED_ORDER_STATUS`（`:26`）—— 后两者是 R3 的阳性对照来源（§1.8）。
5. **打包现状**（D4 的依据）：仓里**没有 `MANIFEST.in`**、`pyproject.toml` **没有
   `[tool.setuptools.package-data]`**、CI 与 `tools/` 里**没有任何 wheel 构建步骤**
   —— 因此「随 wheel 打包」与「wheel 装不到」**两条今天都不可验证**，D4 不许拿它们当理由。

**开工前四条基线命令**（改一行代码之前先跑，把退出码与数字抄进 §0.1）：
① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
② `python3 -m pytest tests/contracts -q`
③ `python3 -m pytest tests/tools -q`
④ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`

## 0.1 基线复取记录（执行期实测，2026-08-24）

**四条基线命令（改一行代码之前跑，逐条抄退出码与数字）**：

| # | 命令原文 | 退出码 | 数字 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0** | `门禁 11 项：预期红 0，绿 11，跳过 0` · `414 passed` |
| ② | `python3 -m pytest tests/contracts -q` | **0** | `151 passed` |
| ③ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped` |
| ④ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` |

工作树基线：`git log --oneline -1` → `928a888`；`git status --porcelain` 只有本批两个 plan 文件未跟踪（起草产物）。

**§0 点名必读的五处逐条复核 —— 与 §1 的转述全部吻合，§1 未做任何改写**：

| # | 必读处 | 实读结论 | 与 §1 |
|---|---|---|---|
| 1 | `rules.py` 五个有限键集与三组算子常量 | `EXCLUDE=(truthy, falsy)` · `MEASURE=(sum_positive, sum_negative_abs, difference, related_sum)` · `TRIGGER=(greater_than, at_least_fraction_of)` · `ROW_FILTER_KEYS={field, operator}` · `TRIGGER_KEYS={measure, operator, reference, value}` | **吻合** |
| 2 | `rule.lookup` 的三处判据 | 三处均在，`tests/gates/test_tool_execution_live.py` 那条是裁判 | **吻合** |
| 3 | `gates.yml` 的 `pip install pytest certifi` 与步骤 ⑦ | 五处；步骤 ⑦ 的 `ls -d tests/*/` **只管一层** → 坏包夹具放 `tests/unit/` 子目录不触发它 | **吻合** |
| 4 | 种子常量与期望侧常量 | `ORDER_QTY=1000` / `INHOUSE_QTY=1000` / `SUBCON_QTY=1000` / `DELIVERY_QTY=990`；`EXPECTED_BACKLOG_QTY=1010.0` / `EXPECTED_SHORTFALL_QTY=10.0` / `EXPECTED_ORDER_STATUS="Closed"` | **吻合** |
| 5 | 打包现状 | 无 `MANIFEST.in`、`pyproject.toml` 无 `[tool.setuptools.package-data]`、CI 与 `tools/` 无 wheel 构建 | **吻合**（D4 据此只用可判口径） |

另实读确认 §1.10：`agenerp/seed/documents.py` 的 `Subcontracting Order.status = "Completed"`、
`Subcontracting Receipt` 的 `qty` / `received_qty` 均等于 `SUBCON_QTY` —— 外协链完整属实。

## 1. Current Baseline

以下每条本轮实读（起草基线 `928a888`）。

### 1.1 P1.5 已经交付「引擎」，本 plan 交付的是「内容」

`agenerp/inspection/` 四个模块已在：`rules.py`（声明形状 + 装载器）· `engine.py`（执行体 +
`check_test_cases`）· `minimal.py`（**一条**规则的最小规则集）· `__init__.py`（`__all__` **九个名字**）。
`minimal.py` 模块头逐字：「**这不是行业包**……本清单是**引擎自带的判据夹具**」；
`module-boundaries.md:582` 同样逐字写着「**巡检规则 ≠ 行业包制品**」。
→ 本 plan 的交付面是**行业包制品**（`pack_id` + `rule_id` 的来源）与**它的校验器**，
**不是**再写一个引擎。

### 1.2 装载器已经把 P1.6 的验收原文预先执行了一半

`rules.py` 的 `_test_case()` 逐字：「**缺 `test_case` 即拒载**。P1.6 的验收原文是
『无 `test_case` 的规则即失败』，静默过滤掉它与正确拒载在退出码上一模一样，所以这里只抛错」。
`_reject_unknown()` 对**五层**键集逐层拒载（M7 实测撞出来的加严）。
`engine.check_test_cases` 拿 `test_case` 在内存行集上**真跑**。
→ 本 plan 的校验器**不重写这三件事**，只是把它们串成一条有退出码的命令；
**但「校验器真的跑了 test_case」这件事必须自带判据**（见 §6 H3），
否则「装载成功」会被读成「测例通过」。

### 1.3 有限算子集是 P1.5 显式登记的残余风险，重开事件写死为「P1.6 起草时」

P1.5 plan §11 逐字：「**重开条件：P1.6 起草时**发现某条业务合理性规则用现有算子集表达不出来
—— 届时由 P1.6 的 plan 决定是扩算子还是改形状」。现有算子集（`rules.py` 实读）：

| 位置 | 算子 |
|---|---|
| 行过滤 | `truthy` / `falsy` |
| 度量 | `sum_positive` / `sum_negative_abs` / `difference` / `related_sum` |
| 触发 | `greater_than` / `at_least_fraction_of` |

→ **重开事件在本 plan 起草这一刻即被触发**，处置写在 Phase 1（Explore → Decision D3），
预测写在 §6 H1。

### 1.4 D-12 已经点名「外协逾期未收」是离散制造规则绕不开的一类

`DECISIONS.md` D-12「为什么必须治理」一栏逐字：「**P1.6 的离散制造规则绕不开『外协逾期未收』**，
这类规则自然写在 `Subcontracting Order` 上，在站点上会**零命中**；而规则的单测若跑离线数据集
**是绿的** —— 测试通过、线上零命中，且无任何信号」。
`agenerp/seed/dataset.py:36-37` 实读：`Subcontracting Order` / `Subcontracting Receipt` 均在数据集里。
→ 这一类是**候选规则清单的必选项**（§6 H1 逐条判可表达性），
且它自带一条 D-12 点名的失败形态：**离线绿、站点零命中**（处置见 §6 H4）。

### 1.5 D01 的建议格式与本仓现实**有两处硬冲突**，必须由本 plan 裁定

证据仓（只读，`XM_SHA=1c622c8`）`spike/D01-decisions/FINDINGS.md` §D-3 建议：
YAML 文件 `industry-packs/discrete-manufacturing/rules.yaml`，规则含
`query`（裸 SQL）+ `assert`（自然语言）+ `params` + `explain` + `test_case`，
另有 `thresholds` 与 `terminology` 两个顶层块；四条设计原则里第 1 条是「每条规则必须带 `test_case`」，
第 2 条是「判据用**可执行查询 + 断言**，不用自然语言描述」。

**冲突①（格式载体）**：CI **五处** `pip install pytest certifi`（`gates.yml:104/176/241/451/505` 实读），
**没有 PyYAML**；而 `.github/workflows/**` 在红线 2 / Protected Areas 里是 `blocked`，
本 plan 无权加装依赖。`agenerp/contracts.py:9-11` 已有同一条先例的记录：
「运行时用纯 Python 声明，因为 CI 的 `gates-l1` 只 `pip install pytest`，`import yaml` 会红在缺依赖上」。
→ 处置见 Decision **D2**。

**冲突②（判据表达）**：D01 的 `query`（裸 SQL）+ `assert`（自然语言）与 P1.5 的 D1
（「声明式数据 + 有限算子」，否决自由谓词）直接冲突，且裸 SQL 在本仓根本跑不通 ——
巡检器取数走站点 REST 只读端点（`engine.SiteRows`），没有 SQL 面。
D01 自己的第 2 条原则「判据必须可独立执行、可断言，不依赖 LLM 判断」**支持** P1.5 的选择。
→ 处置见 Decision **D1**：形状取 P1.5 的 `Rule`，**不引入 SQL、不引入自然语言判据**。

### 1.6 `rule.lookup` 的翻转被一条**不可改的裁判**挡住，这是本 plan 最重要的边界

`agenerp/tools/queries.py:124` 的 `rule_lookup` docstring 逐字：「重开事件是 **P1.6 交付第一个行业包**」。
但本轮实读发现三处判据钉着它的**现行报错行为**：

| 文件 | 位置 | 性质 |
|---|---|---|
| `tests/gates/test_tool_execution_live.py:119` | `test_rule_lookup_says_what_is_missing_instead_of_faking_an_empty_pack` | **裁判**（红线 1，一个字不许动） |
| `tests/tools/test_live_conformance.py:157` | 上面那条**委派进来的断言体**（`ok is False` 且 reasons 含「行业包」，且**上下文已声称 `industry_pack_loaded: True`**） | 裁判的实际断言面 |
| `tests/tools/test_executors.py:290` | 离线同形态 | 普通判据 |

→ **把行业包接进 `rule.lookup` 会让一条 L2 门禁由绿转红**，而让它重新变绿只有两条路：
改裁判（红线 1，停机）或改它委派的断言体（等价于间接改裁判）。**两条都不许走。**
→ 处置：Non-Goal 2 + §11 的 Deferred（重开事件 = **人**裁定），
并在 STATE §3 追加一条 needs-human（只追加，红线 5）。
**本 plan 交付的是「包在盘上、校验器能判它」，不是「包已装载进工具面」** —— 收口时逐字这么写。

### 1.7 判据落点的硬约束（与 P1.4 / P1.5 同一条，不重复推导）

`missions/p1-insight.json` 的 `commands.test` 是
`python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`；
`.github/workflows/gates.yml` 步骤 ⑦ 对 `tests/` 目录集合做逐字比对，新增目录即红，
而 `.github/workflows/**` / `missions/*.json` / `tests/gates/**` 三者均为 `blocked`。
→ **本 plan 的判据一律落 `tests/unit/`**，且 **CLI 的退出码必须由 `tests/unit` 里的子进程判据钉住**
—— 否则那条验收命令 `GATE_VERIFY` 与 CI 两侧都复跑不到（`gates-l2-seed` job 判四条 CLI 退出码，
但本 plan 无权往那个 job 里加第五条）。

### 1.8 固定测例与它的常量（与 P1.5 同源，取数方向不许合并）

`agenerp/seed/model.py:38-42`：`ORDER_QTY = 1000` / `INHOUSE_QTY = 1000` / `SUBCON_QTY = 1000` /
`DELIVERY_QTY = 990` / `SHORTFALL_QTY = 10`；`agenerp/seed/checks.py:23`：`EXPECTED_BACKLOG_QTY = 1010.0`。
`checks.py:18-20` 的纪律逐字：期望值**刻意不从 `agenerp.seed.model` 取**，否则断言变成同义反复。
→ 本 plan 照抄：夹具（数据）从构造侧取，期望值从期望侧取。
`docs/design/view-dsl-and-eval.md:120` 逐字：「**1,010 米积压就是行业包规则的 test case #1**」。
**另一条真实阳性对照照实点名**：`checks.py:25-26` 的 `EXPECTED_SHORTFALL_QTY = 10.0` 与
`EXPECTED_ORDER_STATUS = "Closed"` —— 「订单被人工关闭、实发少于订单量」这件事**在固定测例里是真的**。
→ **R3 是除 R1 之外第二条能在真实数据上验命中的规则**（外协那条不是，见 §1.10）。
⚠️ **那句话的单位是过期的**：D-9 之后成品单位是**台**（`agenerp/seed/model.py` 的 `UOM_FINISHED = "台"`）。
引用它时只引「它是 test case #1」这半句，**不许把「米」当现状**；那处 drift 不属本 plan 的修改面，
本 plan 只在此登记，不代改。

### 1.9 `Hit` **没有 `pack_id` 字段** —— Goal「出处可回溯」在现有结构上落不了地

`agenerp/inspection/engine.py` 实读：`Hit` 的字段是
`rule_id` / `statement` / `subject` / `quantity_name` / `quantity` / `measures` —— **没有 `pack_id`**，
`as_dict()` 同样没有。而 `rule.lookup` 契约的 `must_keep` 逐字是 `("pack_id", "rule_id", "statement")`
（`agenerp/tools_readonly.py:238`），后置断言叫 `rules_carry_provenance`。
→ 「命中记录带得出出处」这件事**必须由本 plan 显式解决**（Decision **D5**），
且它会碰到 P1.5 的交付面（`engine.py`），Targets 必须包含它。**不解决就等于 Goal 1 落空、M7 无法实现。**

### 1.10 种子数据集的**外协链是完整的** —— 外协类规则在固定测例上**没有阳性对照**

`agenerp/seed/documents.py:147-236` 实读：`Subcontracting Order` 的 `status` 是 `"Completed"`，
`Subcontracting Receipt` 的 `qty` / `received_qty` 都等于 `SUBCON_QTY`（= 订单量），
即**发出去多少收回来多少**。→ 「外协已发料迟迟未收」这类规则在固定测例与活站点上**都应零命中**，
而且**那个零命中是正确行为**，不是缺陷。
⚠️ 种子数据集被 `tests/gates/test_seed_dataset_absurdity.py`（**裁判**，红线 1）钉着，
**本 plan 不许往种子里加一个新异常**去给外协规则造阳性对照。
→ 直接后果（写进 §2 Goal 4 与 §6 H2/H4）：**每条规则的阳性对照由它自己的 `test_case` 承担**
（inline 合成行，这正是 `test_case` 存在的理由）；固定测例上则**逐条断言「该命中的命中、
不该命中的零命中」**，两侧都判。⚠️ **收口时不得说「外协规则已在真实数据上验证」** ——
真实数据里没有那个异常，能验的只有「它不误报」。

## 2. Goals

1. 落地**行业包 v0（离散制造）的制品**：一份可 diff 的声明式规则清单，
   **每条规则带 `test_case`**，且 `pack_id` + `rule_id` 是命中记录可回溯的出处。
2. 落地 `agenerp/packs`：包的**装载 + 校验器 + 一条有退出码的 CLI**，
   验收原文形状为 `python3 -m agenerp.packs validate --pack discrete` 退 0，
   **无 `test_case` 的规则即失败**。
3. **校验器真的跑 `test_case`**（不是只检查这个键存在），且「测例不通过」「规则缺 `test_case`」
   「查无此包」三者各自有**可区分的失败处置**（不同退出码 **或** 指名到具体对象的消息，口径由 H6 定稿）。
4. 包里至少一条规则在**由 `agenerp/seed/` 派生的**固定测例上命中，且命中量等于
   `EXPECTED_BACKLOG_QTY`；至少一条规则覆盖 D-12 点名的**外协**一类。
   ⚠️ **外协那条在固定测例上应当零命中**（§1.10：种子的外协链是完整的），
   它的**阳性对照落在自己的 `test_case`**（合成行），固定测例上判的是**它不误报**。
   **每条规则都必须同时有阳性与阴性对照**，缺一不算数（§6 H2）。
5. 命中记录**带得出出处**（`pack_id` + `rule_id`），落法由 Decision D5 定（§1.9）。
6. 判据落 `tests/unit/`（含 CLI 退出码的子进程判据），`GATE_VERIFY` 与 CI 两侧都复跑得到。
7. owner doc 的**失效归属改准**：`agents-and-roles.md:150-151` 与
   `module-boundaries.md:582-586` 里「行业包 v0 归 P1.6」那半句在本 plan 落地后即失效，
   而「`rule.lookup` 仍指名报错」那半句**依然成立**（理由变了：从「没有包」变成「包在盘上但未接线，接线待人裁定」）。

## 3. Non-Goals

1. **不重写巡检引擎**。`agenerp/inspection/` 的装载器与执行体是 P1.5 的交付面，本 plan 只**调用**它们。
   **两处例外，都是「加」不是「改语义」**：① 扩算子（D3）；
   ② D5 若选 (A)，给 `Hit` **加** `pack_id` 字段（§1.9）。
   两处都必须保证 `tests/unit` 既有判据**一条不红**。
2. **不翻转 `rule.lookup` 的报错行为、不把包接进工具面。** 理由见 §1.6：
   接线会让 `tests/gates/test_tool_execution_live.py` 的一条由绿转红，
   而让它复绿只能改裁判或改它委派的断言体，**两者都越红线 1**。
   → 交接给人，见 §11。**收口时不得说成「行业包已装载」。**
3. **不实现 `anomaly.scan` / `benchmark.compare`**（不在十个只读契约里，新增契约是另一个交付面）。
4. **不做行业包的分发机制**（D01 与 `open-questions.md` #5 都把机制放 P5：
   「只有一个行业包时，插件化机制是纯粹的复杂度」）。
5. **不做 `thresholds` / `terminology` 两个顶层块**（D01 建议格式里的另外两块）：
   它们服务的是呈现与检索（P2 的术语层），本期没有消费者；
   **没有消费者的声明块是没有判据的声明块**。⚠️ 这一条是**显式定界**，不是遗漏，重开事件见 §11。
6. **不写任何业务数据**（②端只读），**不发任何 DDL**。
7. **不判自由文本**：本 plan 的全部判据都落在结构化事实（命中记录 / 退出码 / 序列化后的声明）上，
   roadmap「判自由文本前先跑通标注集」一节因此不适用；⚠️ 反过来的约束立着：
   执行期若想补一条「规则的 `statement` 写得好不好」的判据，那属自由文本侧，本 plan 不开这个口子。
8. **不动** `missions/**` / `.github/workflows/**` / `tests/gates/**` / `docs/masterplan/` 已有行
   （`STATE.md` 只追加）· **不动** `agenerp/pack.py`（定制包，与行业规则包无关）。

## 4. Task Route

- Type: `app-layer design change`（行业包的声明格式是 `open-questions.md` #5 的未决项，本 plan 把它定稿并落成代码）
- Owner Docs: `docs/architecture/module-boundaries.md`（**新增落点节，编号执行期顺延**）·
  `docs/design/agents-and-roles.md` §5.1 · `docs/design/context-and-memory.md` §8.6 ·
  `docs/architecture/open-questions.md` #5（只改「格式」那一半）· `docs/masterplan/DECISIONS.md`（**只读**）
- Skill Selection Basis: `docs/skills/README.md` 无对应方法件；草案评审与关闭审计走独立子代理。各 Phase 记 `Skill: none`。

## 5. Infrastructure And Config Prereqs

- **零新依赖**（D2 的直接后果：JSON 走标准库）。CI 的 `pip install pytest certifi` 一个字不用改。
- Phase 1 / Phase 2 全部在离线夹具上跑：零网络、零凭据、零 docker、**零 LLM**。
- Phase 3 的**活站点核对一次**需要 `AGENERP_SITE` / `AGENERP_SITE_URL` / `AGENERP_ADMIN_PASSWORD`。
  **凭据齐备时必做**（D-12 点名的失败形态就是「离线绿、站点零命中」）；
  不齐备时照实记「未跑 · 未验证」并在 §10 逐字写 `verification scope limited`。**没有第三种处置。**
- 无 DDL、无写操作、无审批面变更。

## 6. 开工前写死的假设（硬约束②）

**逐字写死在跑之前，事后逐条对照，不许事后改写。**

- **H1（算子缺口的预测）**：下面五条候选规则里，**现有算子集能原样表达的是 R1 一条**，
  其余四条各缺一件东西 —— 预测逐条写死：

  | # | 候选规则（离散制造业务合理性） | 预测：现有算子够不够 | 预测缺的是（**已排除可绕开的**） |
  |---|---|---|---|
  | R1 | 产出远大于销出（成品积压） | **够** | — |
  | R2 | 外协已发料、迟迟未收货（D-12 点名） | **不够** | **按字段值相等筛行**（`exclude` 只有 `truthy`/`falsy`）；若要判「逾期」还缺**日期算术** |
  | R3 | 订单已关闭但实发少于订单量（账面全绿陷阱） | **不够** | 同上（按 `status` 相等筛行）；⚠️ **方向不缺** —— `difference` + `greater_than` 可以把「少于」写成「差额 > 0」 |
  | R4 | 某物料入库为零却有出库（漏记入库） | **不够** | 需要**触发侧的合取**（「入库 == 0」且「出库 > 0」），现有 `trigger` 只有一条 |
  | R5 | 同一物料在多个仓库重复堆积 | **不够** | 缺**按组计数**的度量（`count`） |

  ⚠️ **「缺『小于』方向」这条预测已在起草期自我推翻**（`difference` + `greater_than` 反过来写即可），
  上表已按推翻后的口径写死 —— **这就是硬约束②要的形态**：预测在跑之前定稿，推翻要留痕。
  执行期**逐条实测可表达性**，与上表**逐格对照**；**记法写死**：每格只许记
  `吻合` / `不吻合（实际缺的是 X）` / `部分吻合（预测缺 A，实际缺 A 与 B）` 三种之一，
  **不许回头改这张表**（P1.3 的 H1–H4 与 P1.5 的 H1–H4 都是这么做的）。
- **H2（每条规则一对阳性/阴性对照 —— 这是判别力的主判据）**：
  包里**每一条**规则各有两个数据集：**阳性**（含该异常 → 必须命中，且命中里的
  **数是算出来的**）与**阴性**（健康数据 → 必须零命中）。两侧都成立才算数。
  ⚠️ **判据形态的理由写死**：抽掉规则就查不出它那条异常这件事，在
  `engine.without()` + `run()` 的实现下**接近恒真**（规则没了自然没有它的命中）——
  它证明的是「引擎读清单」，**不是「规则有判别力」**。
  → 消融判据**保留但降级**为附带断言，收口时**逐字写明它是恒真的那一侧**，
  **不许拿它当发现力的证据**（P1.5 的 H1 是「有/无」两跑；本 plan 在它之上加阴性对照）。
  ⚠️ **R1 的阳性对照必须是由 `agenerp/seed/` 派生的固定测例**，命中量断言
  `== EXPECTED_BACKLOG_QTY`（取自 `checks.py:23`，**期望侧**）；
  **另加第二个数据集**（改 `INHOUSE_QTY`/`SUBCON_QTY`/`DELIVERY_QTY` 参数、
  期望值在判据里写死一个 `!= 1010` 的字面量）证明那个数**随数据集变**（M5 的杀手）。
  ⚠️ **外协那条的阴性对照就是固定测例本身**（§1.10：种子外协链完整），
  阳性对照落在它自己的 `test_case` 合成行上。
- **H3（校验器真的跑了 `test_case`，且**每一条**都跑了）**：把包里某条规则的
  `test_case.expect_hit` 由 `true` 改成 `false`（规则本身一个字不动），`validate` **必须非零退出**。
  ⚠️ **变异必须至少施加在「最后一条规则」上，且逐条各来一次** ——
  只变异第一条时，一个「只校验第一条就返回」的假校验器是**绿**的。
  ⚠️ 这条同时是「跑通就算」的杀手：只检查 `test_case` 这个键存在的假校验器在这个变异上也是绿的。
- **H4（离线绿 ≠ 站点绿，D-12 点名的失败形态）**：**整份包**在活站点上跑一次，
  命中集合与离线固定测例**逐字一致**（同 P1.5 收口那一跑的做法）。
  ⚠️ **必须先断言这个集合非空且含 R1 那一条** —— 否则「两个空集相等」也叫「逐字一致」，
  那是一条能骗过 H4 的假绿（外协那条两侧都零命中，见 §1.10）。
  ⚠️ 若实测是「离线命中、站点零命中」（R1 上出现），那**不是失败，是 D-12 预言的那件事被抓到了** ——
  照实记进 plan 与 STATE §3，**不许把规则改到能命中为止**（那是照答案写规则，H5 禁止）。
- **H5（不许照答案写规则）**：包的**序列化形态**里不出现任何单据号字面量
  （ERPNext 单号形状：至少三段全大写数字）、不出现 `1010` / `2000` / `990` 这三个数，
  也不出现 `FINISHED_ITEM` / `WH_FINISHED` 这类夹具符号的值。
  ⚠️ **判在源声明与装载后两侧**（P1.5 的 M7 教训：装载器丢弃未知键会让夹带的答案只在源码里可见）。
  ⚠️ **`test_case` 整块是这条判据的显式例外**（`rows` 里本来就要写具体数据行，
  `expect_quantity` 必然是由这些行算出来的数）。**例外只开给 `test_case`，
  规则的判据表达一侧不开**；且 `test_case.rows` 的取值**不许照抄固定测例的数**
  （合成行自成一套，避免测例变成把答案抄进包里）。
- **H6（四种输入四种可区分的处置）**：`validate` 对四种输入的处置**互相分得开** ——
  ① 健康包 → **0**；② 某规则缺 `test_case` → 非零；③ 某规则的 `test_case` 跑不过 → 非零；
  ④ 包目录不存在 / `--pack` 拼错 → 非零。
  ⚠️ **「非零」三个字不够**（Goal 3 要的是「各自可区分」）：②③④ 必须**互相分得开**，
  口径二选一、执行期定稿并写进落点节 —— (i) 三者用**不同的退出码**；
  或 (ii) 同一非零码但**消息里指名到具体对象**（②③ 指名到那条 `rule_id`，
  ③ 另带期望/实测，④ 指名到那个 `--pack` 取值）。判据按选定口径逐条断言，
  **不许只断言 `!= 0`** —— 那样 ④ 就成了同义反复。

- **H7（出处可回溯）**：任一条命中都能回答「这是哪个包的哪条规则报的」，
  且 `pack_id` **不是从 `rule_id` 里猜出来的**。判据形态写死：
  同一条 `rule_id` 挂在两个不同 `pack_id` 下时，两次命中的出处**不同**
  （§1.9：`Hit` 今天没有这个字段，落法由 D5 定）。

## 7. Execution Plan

### Phase 1 — 包的形状定稿：Explore 算子缺口 → Decision → 制品落盘

Status: completed
Targets: `industry-packs/discrete/`（或 D4 定稿的落点）· `agenerp/inspection/rules.py`（**仅在 D3 判定要扩算子时**）· `agenerp/inspection/engine.py`（**仅在 D5 选定「扩 `Hit`」时**）· `tests/unit/`
Skill: `none`

- Item Types: `Explore | Decision | Add | Proof`
- Prereqs: 无（P1.5 已 `completed`）

- [x] **Explore E1 · 算子缺口实测。** 把 §6 H1 那五条候选规则**逐条**试着用现有算子集写出来，
      写不出来的**逐条记下缺的是哪一件事**（不是「不好写」，是「哪个算子不存在」）。
      **E1 必须在 D3 之前结论**，结论逐条对照 H1 的预测表。
      - Skill: `none`
- [x] **Decision D1 · 判据表达取 P1.5 的 `Rule` 形状，不取 D01 的 SQL + 自然语言。**
      备选：(A) D01 建议的 `query`（裸 SQL）+ `assert`（自然语言）—— **否决**：本仓取数走站点 REST 只读端点，
      没有 SQL 面；自然语言 `assert` 不可执行，落地必然退回「让模型理解规则」，
      与 D01 自己的第 2 条原则和 P1.5 的 D1 同时冲突。
      (B) **复用 `agenerp/inspection/rules.py` 的 `Rule` 声明形状**（选定）：已有装载器、已有
      「缺 `test_case` 即拒载」、已有「未知键即拒载」、已有 `check_test_cases` 真跑测例。
      **残余风险**：本仓格式与 D01 建议格式不一致，将来若要吃外部按 D01 写的包需要一个转换层 ——
      登记进 §11，不在本期做。
      - Skill: `none`
- [x] **Decision D2 · 包文件用 JSON，不用 YAML（`constrained choice`）。**
      理由是实读出来的硬约束：CI 五处 `pip install pytest certifi`，**没有 PyYAML**，
      而 `.github/workflows/**` 是 `blocked`，本 plan 无权加装依赖；`agenerp/contracts.py:9-11`
      已有同一条先例。**代价照实记**：JSON 不能写注释，规则的「为什么」只能进 `statement` 字段；
      D01 建议的 YAML 形态因此**未采纳**，理由与本条一起写进落点节。
      - Skill: `none`
- [x] **Decision D3 · 扩算子还是收内容**（由 E1 的实测结论驱动，**不许在 E1 之前预判**）。
      判定口径写死：**只有当某算子的语义能被有限枚举、且能写出它自己的拒载判据时才许新增**；
      任何需要「传一段表达式/谓词/SQL 进来」的方案一律否决（P1.5 D1 的同一条理由）。
      新增算子必须同时交付：① 有限键集里的登记；② 求值判据；③ **拒载判据**（未知算子名一律拒载）。
      ⚠️ **对 Goal 4「必须覆盖外协一类」那条的解冲突写死在这里**（否则 D3 的「收内容」出路
      会与 Goal 4 直接对撞）：**「按字段值相等筛行」（`equals` + 字面量）是有限可枚举的、
      写得出拒载判据的**，因此 **E1 一旦确认 R2/R3 缺它，本 plan 就必须新增它**（连同拒载判据），
      不许用「收内容」把外协那条整类砍掉。**日期算术（「逾期 N 天」）明确不在本期**：
      它要引入时间基准与时区口径，属另一个交付面 → 外协那条 v0 按「**已发料 − 已收货 > 0**」
      这种不含时间的形态表达，「逾期」那一维登记进 §11。
      若 E1 结论是「除上述之外还有别的规则表达不出来」，那几条**收内容**：
      包 v0 只收能表达的，**并在落点节逐字写明哪一类规则本期表达不了**。
      **两条出路都不许是「先写进包里、判据以后补」。**
      - Skill: `none`
- [x] **Decision D4 · 包的落盘位置。**
      备选：(A) 仓库根 `industry-packs/<pack_id>/`（D01 建议，且与「生态伙伴独立提供行业包」一致）；
      (B) `agenerp/packs/data/<pack_id>/`（与代码同目录）。
      ⚠️ **权衡必须用本仓今天可判的口径写**（§0 第 5 条实读：无 `MANIFEST.in`、无 `package-data`、
      CI 无 wheel 构建）—— **「随 wheel 打包」与「wheel 装不到」两条都不可验证，不许拿来当理由**。
      可判的口径只有两条：① **路径解析方式**（相对仓库根 / 相对包目录 / `--packs-dir` 覆盖），
      ② **它自己的判据**（解析失败必须非零退出，即 H6 ④）。
      **选定与理由、被否决那条的代价、残余风险执行期写进本条**；
      残余风险若涉及打包，只许写成「今天不可验证的假设」，不许写成事实。
      - Skill: `none`
- [x] **Decision D5 · 命中记录怎么带出处（`pack_id`）。** 起因是 §1.9 的实读：
      `Hit` 今天**没有** `pack_id`，而 `rule.lookup` 契约的 `must_keep` 含它、后置断言叫
      `rules_carry_provenance`。备选：(A) **给 `Hit` 加 `pack_id` 字段**（碰 P1.5 的 `engine.py`，
      要保证 `tests/unit` 既有判据一条不红）；(B) **在包这一层包一层出处映射**
      （`rule_id → pack_id`，`Hit` 不动）；(C) 把 `pack_id` 编进 `rule_id` 前缀 ——
      **倾向否决**：出处与身份混成一个字符串，`rule_id` 一改出处就变，且 H7 的
      「同一 `rule_id` 挂两个包」判据在它上面无从构造。
      ⚠️ **选 (A) 时「加字段」只是一半**：`pack_id` 还得**有来源** ——
      `Rule` / `RULE_KEYS` 里加一位，或由 `run()` / 装载面传进来；
      本条必须把**来源那一层**一并点名，否则 H7 判不动。
      （既有 `Hit(...)` 全为关键字构造，加带默认值的字段不会打红既有判据。）
      **选定与理由、被否决项的代价、残余风险执行期写进本条**；无论选哪条，H7 必须成立。
      - Skill: `none`
- [x] **Add** 行业包制品 `discrete`：`pack_id` / `version` / `requires_doctypes` / `rules[]`，
      **每条规则带 `test_case`**。规则条数由 D3 定稿，**下限是 2 条**（其一必须命中固定测例，
      其一必须覆盖 D-12 点名的外协一类）；**上限不设**，但每多一条就要多一组 H2 消融判据。
- [x] **Proof H5** 包的序列化形态里不含单号 / `1010` / `2000` / `990` / 夹具符号值，
      **源声明与装载后两侧都判**；`test_case.rows` 是显式例外。
- [x] **Proof H2** 每条规则一对**阳性 / 阴性**对照（阳性必命中且数是算出来的、阴性必零命中）；
      R1 的阳性对照用固定测例，命中量断言 `== EXPECTED_BACKLOG_QTY`（取自 `checks.py:23`），
      **另跑第二个数据集**断言那个数随数据集变（M5 的杀手）；
      消融判据保留为附带断言，并**逐字标注它接近恒真**。
- [x] **Proof H7** 出处可回溯：同一 `rule_id` 挂两个 `pack_id` 时命中的出处不同。

Exit Criteria:

- [x] E1 的实测结论与 §6 H1 的预测表**逐条对照**，吻合与否照实记（预测错了不许改表）
- [x] **D1–D5 五条**各有选定、备选、否决理由与残余风险
- [x] H2 / H5 全绿
- [x] 四条基线命令全退 0（§0 那四条；新增的 `agenerp/packs/**` 在 `ruff` 作用域里）
- [x] owner-doc 落地**延至 Phase 3**；本阶段不改任何 owner doc

### Phase 2 — 校验器与 CLI：一条有退出码的命令

Status: completed
Targets: `agenerp/packs/`（`__init__.py` / `loader.py` / `__main__.py` 之类，结构执行期定）· `tests/unit/test_industry_pack.py`
Skill: `none`

- Item Types: `Add | Proof`
- Prereqs: Phase 1

- [x] **Add** 包的装载面：读 D4 定稿位置的 JSON → 过 `agenerp.inspection.rules.load_rules` →
      得到 `(pack_id, version, rules)`。**装载失败一律抛，不降级、不返回半份包**
      （`RuleLoadError` 的既有纪律逐字：「拒载，不降级 —— 半份规则清单跑出来的零命中
      读起来与『一切正常』一模一样」）。
- [x] **Add** 校验器：装载 + **逐条真跑 `test_case`**（走 `agenerp.inspection.engine.check_test_cases`），
      失败时消息指名「哪个包的哪条规则、期望什么、实测什么」。
- [x] **Add** CLI `python3 -m agenerp.packs validate --pack discrete`：退出码 0 / 非零，
      形状对齐 WBS §4 P1.6 的验收原文。**⚠️ 验收命令的字符串定稿**（`python` → `python3`）
      按 WBS 表规 6 处理：形状不变（仍是一条能跑、能给出退出码的命令），
      **定稿在 `docs/masterplan/STATE.md` §2 追加一条证据行**（只追加，红线 5）。
- [x] **Proof H6** 四种输入四种**可区分**的处置（健康 / 缺 `test_case` / 测例跑不过 / 查无此包），
      判在退出码上，且 ②③④ **互相分得开**（不同退出码 或 消息指名到具体对象，口径执行期定稿）；
      **不许只断言 `!= 0`**。
- [x] **Proof H3** 把某条规则的 `test_case.expect_hit` 翻转 → `validate` 必须非零，
      **且变异逐条各施加一次（含最后一条）** —— 只测第一条挡不住「只校验第一条就返回」的假实现；
      同一条纪律适用于 H6 ② 的「缺 `test_case`」变异。
      **这条判据用「坏包夹具」实现，坏包放 `tests/unit/` 下的夹具目录，不放进 `industry-packs/`**
      （产品制品目录里不许躺着故意写坏的包）。
- [x] **Proof（CLI 的退出码进 `tests/unit`）** 用子进程跑真实命令行并断言退出码，
      **不是只调 `main()` 的函数**：`gates.yml` 第 559 行附近已有一条实测教训 ——
      「`tests/unit` 直接 import main、从不经过那两行 —— 那是一条活的假绿路径」。
      **两种都写**：函数级（快）+ 子进程级（真）。
- [x] **Proof** 变异自查 **M1–M8，八个变异在此逐字写死**，不许执行期看着自己的实现现编：
      **M1** 校验器只检查 `test_case` 键存在、不真跑（H3 打红）；
      **M2** 校验器把「装载失败」吞掉后退 0（H6 ② 打红）；
      **M3** `--pack` 拼错时退 0（H6 ④ 打红 —— 「查无此包」被读成「校验通过」是最贵的假绿）；
      **M4** 包里某条规则的判据被改成**永远命中** —— **由 H2 的阴性对照打红**
      （消融那一侧对它是绿的：抽掉规则照样零命中。这正是 H2 把主判据从消融换成
      阳性/阴性对照的理由，不许再退回只做消融）；
      **M5** 命中量写死成 1010（**必须用第二个数据集打红**：按 `agenerp/seed/model.py` 的
      `INHOUSE_QTY` / `SUBCON_QTY` / `DELIVERY_QTY` 改参数、期望值在判据里写死一个 `!= 1010` 的字面量
      —— P1.5 的 H1 就是这么做的，P1.3 的 M6 是第一轮绿掉的反面教材）；
      **M6** 规则声明里夹带具体单号（H5 打红，且**源声明侧**那一半必须单独打红）；
      **M7** 包的 `pack_id` / `rule_id` 与命中记录的出处对不上（出处被写死或丢失）——
      **由 H7 打红**（`Hit` 今天没有这个字段，落法见 D5）；
      **M8** CLI 的退出码恒为 0（子进程判据打红；**函数级判据对它可能是绿的**，这正是要两种都写的理由）。
      任一变异打不红即说明判据有缺口，**就地补断言并登记为 M9…**，不许略过。

Exit Criteria:

- [x] H3 / H6 全绿，M1–M8 逐个复跑**全部由绿转红**（打不红的就地补断言并登记）
- [x] **五条验证命令全退 0**：§0 的四条 + `python3 -m agenerp.packs validate --pack discrete`
- [x] 新增判据条数与 `tests/unit` 的基线条数差**逐字记进 plan**（基线 414 passed，执行期重取）

### Phase 3 — 活站点核对 · owner doc 落点与失效归属改准 · 交接

Status: completed
Targets: `docs/architecture/module-boundaries.md`（新增落点节）· `docs/design/agents-and-roles.md` §5.1 · `docs/design/context-and-memory.md` §8.6 · `docs/architecture/open-questions.md` #5 · `agenerp/tools/queries.py`（**仅 docstring**）· `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-24.md`
Skill: `none`

- Item Types: `Fix | Proof | Follow-up`
- Prereqs: Phase 2

- [x] **Proof H4（活站点跑一次）** 用 **D4 定稿位置**的 `discrete` 包在活站点上跑一次巡检，
      命中集合与离线夹具**逐字比对**。⚠️ 若外协那条出现「离线命中、站点零命中」，
      **照实记进 plan 与 STATE §3，不改规则去迁就站点**（D-12 预言的正是这件事）。
      凭据不齐备时照实记「未跑 · 未验证」+ §10 逐字写 `verification scope limited`。
- [x] **Fix** owner doc 的**失效归属改准**（确认的 owner-doc drift 是 Minimum Rule 14 的非降级项）：
      ① `docs/design/agents-and-roles.md:150-151`「行业包 v0 归 P1.6，`rule.lookup` 因此仍然指名报错」
      —— 前半句本 plan 落地后失效，后半句**仍成立但理由变了**（从「没有包」变成「包在盘上、未接线，接线待人裁定」）；
      ② `docs/architecture/module-boundaries.md:582-586`「巡检规则 ≠ 行业包制品」那一段的
      「行业包 v0（`pack_id` + `rule_id` 的来源……）归 P1.6」同理。
      **两处都只改失效的那半句，成立的那半句一个字不动。**
- [x] **Add** 落点节（`module-boundaries.md` 新增一节，编号按当时最大编号顺延、收口时逐字记）：
      包的形状、**D1–D5 五条**决策与被否决的备选、**与 D01 建议格式的两处偏离及理由**、
      `industry-packs/` 与 `agenerp/pack.py` / `agenerp/inspection/` 的三方命名消歧、
      **本期表达不了的规则类别**（D3 的产物）、以及「包在盘上 ≠ 包已接进 `rule.lookup`」这一句。
      ⚠️ **新节里点一句消歧**：本节的 D1–D5 与 §7.9（P1.5 的落点节）里的 D1–D4 **不同源、不同编号空间**，
      不许互相引用编号。
- [x] **Fix** `docs/architecture/open-questions.md` #5：**只改「格式」那一半**
      （格式已由本 plan 定稿，指向落点节），**「分发机制首版不做 / 机制 P5」一个字不动**。
- [x] **Add** `docs/design/context-and-memory.md` §8.6 **只补落点指针**（纯新增行，
      §8.6 的既有结论一个字不动 —— 照 P1.5 对 `agents-and-roles.md` §5.1 的做法）。
- [x] **Fix** `agenerp/tools/queries.py` 的 `rule_lookup` docstring：
      现文逐字「重开事件是 P1.6 交付第一个行业包」，本 plan 落地后**这个重开事件已发生但翻转被裁判挡住**。
      改成指名说清三件事：包已在盘上（给出路径）· **未接线**· 接线为什么要人裁定（§1.6 的三处判据）。
      ⚠️ **报错消息的行为一个字不改**（`tests/tools` 与 `tests/gates` 都钉着它）。
- [x] **Follow-up → 交接**：在 `docs/masterplan/STATE.md` §3 追加一条 needs-human
      （只追加）：`rule.lookup` 接线需人裁定，二选一 ——
      (a) 人以 `Gates-Change-Approved-By:` 修改那条门禁并接线；(b) 人裁定 `rule.lookup` 维持报错、
      把「重开事件」改写到更后面的阶段。**loop 不替人选**，两条各自的代价照实列。
      触发条件（Follow-up 必须有）：**人给出上述任一裁定时**本条进入范围。
      **同一条 needs-human 追加第二个 bullet**：`docs/masterplan/02-WBS.md` P1.6 行的验收命令
      将长期写作 `python -m agenerp.packs validate`，而仓里跑的是 `python3 -m`。
      表规 6 允许改这个字符串，但 `docs/masterplan/` 已有行**只有人能改**（红线 5）——
      归属交给人，本 plan 只在 STATE §2 留定稿证据行。
- [x] **Add（结清前一个 plan 的 deferred）** P1.5 plan §11「有限算子集在 P1.6 可能不够用」的
      重开事件已在本 plan 起草时触发（§1.3）。**结清的落点是本 plan 的 §11 与落点节里 D3 的裁定**，
      **P1.5 那个已 `completed` 的 plan 文件一个字不改写**（追加式账本纪律）。
- [x] **Decision（归属声明，不是动作）** `docs/backlog/p1-insight-roadmap.md` 工作项 8 的状态回写
      **由引擎在 closure 审计通过后做**（该文件自己写着「由引擎在 closure 审计通过后回写」），
      本 plan **不代写状态**；收口时须确认它没有停在 `todo`。
- [x] **Add** `docs/logs/2026/08-24.md` 追加一条聚合日志（同一 sprint 同一交付面，聚合一条即可）。

Exit Criteria:

- [x] H4 逐条对照 §6 原文，吻合与否照实记（含「站点零命中」这一分支的处置）
- [x] owner doc 三处 `Fix` + 一处落点节 + 一处指针全部落地，且**只改失效的那半句**
- [x] STATE §3 的 needs-human 已追加（只追加，未改写任何已有行）
- [x] `docs/logs/` 已更新
- [x] 五条验证命令全退 0（§0 四条 + CLI）

## 8. 风险

| # | 风险 | 处置（写死，不留「到时候再看」） |
|---|---|---|
| ① | **扩算子把有限算子集撑成一门语言** | D3 的判定口径写死：能有限枚举 + 有自己的拒载判据才许加；需要传表达式的一律否决 |
| ② | **规则照答案写** | H5 两侧结构判据 + M6；`test_case.rows` 是唯一例外 |
| ③ | **离线绿、站点零命中**（D-12 点名） | H4 强制活站点跑一次；出现即照实记，**不改规则迁就站点** |
| ④ | **校验器退化成「跑通就算」** | H3（翻转 `expect_hit`，**逐条含最后一条**）+ H6（②③④ 可区分）+ M1/M3 |
| ⑤ | **CLI 假绿**（只测 `main()` 不测命令行） | 函数级 + 子进程级两种判据都写；M8 |
| ⑥ | **本 plan 被读成「行业包已装载」** | Non-Goal 2 + §11 + `queries.py` docstring 改准 + 收口逐字声明 |
| ⑦ | 判据落点漂移（新判据进不了 `GATE_VERIFY`） | 判据一律落 `tests/unit/`（§1.7） |
| ⑧ | **消融判据是恒真的**（`without` + `run` 天然成立） | H2 主判据换成阳性/阴性对照；消融降级为附带断言并逐字标注 |
| ⑨ | **外协规则在真实数据上没有阳性对照**（§1.10，种子外协链完整、且种子被裁判钉住） | 阳性对照落自己的 `test_case`；固定测例上判「不误报」；H4 先断言集合非空且含 R1；收口逐字声明「外协规则未在真实数据上验证过命中」 |
| ⑩ | **出处落不了地**（`Hit` 无 `pack_id`） | D5 + H7 + M7；D5 选 (A) 时 Targets 含 `engine.py`，且既有判据一条不许红 |
| ⑪ | **Goal 4 与 D3 的「收内容」出路对撞** | D3 判定口径写死：`equals` 行过滤必须新增；日期算术明确不在本期、登记 §11 |

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，不带起草上下文；
  2026-08-24）。五条 blocking + 若干事实更正，**逐条已改，无一条被驳回**：
  ① `Hit` 无 `pack_id`，Goal「出处可回溯」与 M7 在现有结构上落不了地 → 新增 **§1.9** + **Decision D5** +
  **H7** + Phase 1 Targets 条件性纳入 `engine.py`；
  ② 种子外协链完整（`documents.py:147-236`，`status Completed` / 收货 qty == 订单 qty），
  外协类规则在固定测例上**没有阳性对照**，H4 退化成「两个空集相等」 → 新增 **§1.10**，
  Goal 4 改写为「阳性对照落 `test_case`、固定测例上判不误报」，H4 补「先断言集合非空且含 R1」；
  ③ 判据夹具 `tests/unit/inspection_fakes.py` 的 `_DOCTYPES` 没有 `Subcontracting Order`，
  而种子被 `tests/gates/test_seed_dataset_absurdity.py`（裁判）钉住、不许加异常 →
  §1.10 写死「不许往种子加异常」，阳性对照改由 `test_case` 合成行承担；
  ④ H6 ④ 是同义反复、且与 Goal 3「可区分」冲突 → H6 改写为「②③④ 互相分得开，二选一口径，
  不许只断言 `!= 0`」；
  ⑤ H3 / H6② 只变异一条规则，挡不住「只校验第一条」的假实现；H2 的消融在
  `engine.without()` + `run()` 下**接近恒真** → H3 改为逐条变异（含最后一条），
  H2 主判据换成**每条规则一对阳性/阴性对照**、消融降级并逐字标注恒真，M4 的打红面随之改准。
  另修三处事实：`pip install pytest certifi` 是**五处**不是四处（`gates.yml:104/176/241/451/505`）；
  `agenerp/inspection/__init__.py` 的 `__all__` 是**九个名字**不是五样；
  §6 H1 表里「R3/R4 缺『小于』方向」的预测**起草期即被自我推翻**（`difference` + `greater_than`
  可反向表达），已按推翻后的口径重写并补上「部分吻合」的记法。
  四条 non-blocking 一并处理：P1.5 deferred 的结清落点、roadmap 工作项 8 状态回写的归属声明、
  WBS 行验收命令字符串分歧并入 STATE §3 needs-human 的第二个 bullet、
  `view-dsl-and-eval.md:120` 的「米」是过期单位（登记不代改）。
- Independent draft review iteration 2: **needs revision**（第二个独立子代理，fresh session；2026-08-24）。
  该轮**逐条复核并确认第 1 轮的事实主张全部属实**（`Hit` 无 `pack_id` · 外协链完整 ·
  `pip install` ×5 · `__all__` = 9 · 三处 `rule.lookup` 判据 · WBS/owner-doc 行号），
  并判定「第 1 轮五条 blocking 已被实质改掉，不是嘴上说改」。新出四条 blocking，**逐条已改**：
  ① Goal 4「必须覆盖外协」与 H1「R2 现有算子表达不出」+ D3「可以收内容」三者**没有解冲突规则** →
  D3 判定口径写死「`equals` 行过滤必须新增」「日期算术不在本期、外协按不含时间的形态表达」，
  并在 §11 登记日期算术的重开条件；
  ② Non-Goal 1 只给「扩算子」开了改 P1.5 引擎的口子，与 D5(A)「给 `Hit` 加字段」互相否定 →
  Non-Goal 1 的例外清单补第二条；
  ③ Goal 3 逐字要「可区分的**非零退出**」，而 H6 口径 (ii) 允许「同一非零码 + 指名消息」→
  Goal 3 改成「可区分的**失败处置**」，与 H6 对齐；
  ④ D4 的打包理由与仓库现状不符 —— **无 `MANIFEST.in`、无 `package-data`、CI 无 wheel 构建**，
  故「随 wheel 打包」与「wheel 装不到」**两条今天都不可验证** → D4 改用本仓可判的两条口径
  （路径解析方式 + 它自己的判据），§0 必读清单补第 5 条把这三个事实写死。
  五条 non-blocking 一并处理：Phase 3 / §11 统一写「D4 定稿位置」· §8 风险表编号重排并补 ⑪ ·
  H5 的例外扩到 `test_case` 整块并禁止测例照抄固定测例的数 ·
  §1.8 点名 **R3 在固定测例上有真实阳性对照**（`checks.py:25-26`）·
  本条即 iteration 2 的记录。
- Independent draft review iteration 3: **acceptable as-is**（第三个独立子代理，fresh session；2026-08-24）。
  **零 blocking**。该轮判定第 2 轮四条 blocking「已实质改掉且自洽」，并实跑复核了本 plan 依赖的事实：
  `Hit` 无 `pack_id`（`engine.py:88-110`）与 `tools_readonly.py:238` 的 `must_keep` 属实 → §1.9/D5/H7 成立；
  算子集与五个有限键集逐条吻合，`check_test_cases` 确实真跑测例、`expect_hit` 翻转判得红 → H3 可执行；
  `checks.py:23/25/26` 三个常量与行号全对；三处 `rule.lookup` 判据与 `tests/gates/test_seed_dataset_absurdity.py` 都在；
  `pip install pytest certifi` 确为五处，且 `gates.yml` 步骤 ⑦ 的目录比对**只管 `tests/*/` 一层**
  → **坏包夹具放 `tests/unit/` 子目录不会触发它**；D4 依据的三个打包事实（无 `MANIFEST.in`、
  无 `package-data`、CI 无 wheel 构建）逐条属实；另附带发现 `_trigger` 用
  `isinstance(value, (int, float))` 判类型而非真值，故 `value: 0` 不会被拒载 —— 外协那条按
  「已发料 − 已收货 > 0」表达在现有装载器上**确实落得了地**。
  基线复跑：`tests/unit` **414 passed** · `tests/contracts` + `tests/tools` 232 passed / 12 skipped ·
  `ruff` 全过 · `check_expected_red.py` exit 0。红线面确认未触及，E1→D3→D5 三段无「只能现编」的关键留白。
  三条 non-blocking 已就地改掉：Phase 1 Exit 与落点节的「D1–D4」→ **D1–D5**（否则唯一碰 P1.5
  交付面的决策不进 owner doc）· D5(A) 补「`pack_id` 还得有来源那一层」·
  新落点节补一句「本节 D1–D5 与 §7.9 的 D1–D4 不同源」。
  → **三轮评审收敛，本 plan 转 `active`。**
- **执行期续行（2026-08-24，Phase 1 开工前）**：§0 点名必读的**五处全部重新实读**，
  与 §1 的转述**逐条吻合**，因此 **§1 一个字未改写**（对照表见 §0.1）。
  四条基线命令全退 0，数字与第 3 轮评审记录的 `414 passed` / `232 passed, 12 skipped` 逐字相同。
  执行期唯一新增的事实是第 3 轮评审已附带发现的那一条的延伸：`gates.yml` 步骤 ⑦ 的
  `ls -d tests/*/` **只管一层**，故坏包夹具目录 `tests/unit/pack_fixtures/` 不触发它 —— 实测确认。

## 10. Closure Gates

- [x] in-scope behavior is complete（包制品 + 校验器 + CLI + 判据）
- [x] relevant docs are aligned（落点节 + 三处失效归属改准 + open-questions #5 格式那一半）
- [x] verification has run：§0 四条 + `python3 -m agenerp.packs validate --pack discrete`，**逐条抄命令原文与退出码**
- [x] scoped verification is not conflated with full verification —— 活站点那一跑若未做，逐字写 `verification scope limited`
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§9）
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent —— **2026-08-24 由独立会话补做**（mission-driver 派发的独立收口审计器，
      session `2026-08-24-203159-mission-driver`，fresh session、不带实现上下文，非执行者自审）。
      ⚠️ **执行当轮的原状照实保留、不粉饰**：那一轮执行环境不具备独立子代理，
      而**执行者自审不算独立**，此项曾留白为 `[ ]`（先例：P1.3 / P1.4 / P1.5 首次收口同此）。
      ⚠️ **仍然不得把 §9 的三轮起草评审读成关闭审计** —— 那是开工前的，判的是 plan；关闭审计判的是**已落地的实现**。
      补做记录见 `## Closure` 末尾的「独立关闭审计补做记录」一节 —— 原 `Closure Audit Evidence` 块**一个字未改写**。
- [x] closure evidence exists in files
- [x] `docs/backlog/p1-insight-roadmap.md` 工作项 8 未停在 `todo`（回写归属见 Phase 3 的归属声明）
- [x] **收口时逐字声明五件事**：① `rule.lookup` **未接线**（本 plan 交付的是包与校验器，不是装载）；
      ② WBS §4 P1.6 的验收命令字符串已定稿（`python` → `python3`）且已在 STATE §2 留证据行；
      ③ H1 的预测表与实测**逐条对照结果**（每格记 `吻合` / `不吻合（实际缺 X）` / `部分吻合`，原文保留）；
      ④ **外协那类规则未在真实数据上验证过命中**（真实数据里没有那个异常，验的只是「不误报」）；
      ⑤ **消融判据是恒真的那一侧**，发现力由阳性/阴性对照证明

## 11. Deferred But Adjudicated

### `rule.lookup` 接线（把行业包接进工具面）

- Classification: `out-of-scope improvement`（被红线 1 保护的裁判挡住，非能力问题）
- Why Not Blocking Closure: WBS §4 P1.6 的验收原文只要求 `packs validate` 退 0，不要求接线；
  接线会让一条 L2 门禁由绿转红，复绿只能改裁判或改它委派的断言体
- Successor Required: `yes` —— 由**人**裁定（(a) 批准改门禁并接线 / (b) 维持报错并改写重开事件）
- 重开条件：**人给出上述任一裁定时**

### 日期算术（「逾期 N 天」那一维）

- Classification: `out-of-scope improvement`（D3 的判定口径把它划在本期之外）
- Why Not Blocking Closure: 外协那条 v0 按「已发料 − 已收货 > 0」这种不含时间的形态表达即可成立；
  引入时间基准与时区口径是另一个交付面
- Successor Required: `no`
- 重开条件：**出现一条「不含时间就表达不了」的业务合理性规则时**（届时须连同时间基准与时区口径一起定）

### D01 建议格式（YAML + SQL + 自然语言 assert）与本仓格式的转换层

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 本期只有一个包、且是本仓自己写的，转换层没有输入
- Successor Required: `no`
- 重开条件：**出现第一份按 D01 格式写的外部行业包**（P5「行业包机制 v1」是它的自然归属）

### `thresholds` / `terminology` 两个顶层块

- Classification: `out-of-scope improvement`（Non-Goal 5 的显式定界）
- Why Not Blocking Closure: 本期没有消费者，声明块没有判据就是没有守卫的字符串
- Successor Required: `no`
- 重开条件：**P2 的术语层开工时**（`terminology`）或**首个需要按企业调阈值的规则出现时**（`thresholds`）

## 12. 执行记录（Phase 1–3 · 2026-08-24）

落点节是 `docs/architecture/module-boundaries.md` **§7.10**，D1–D5 的完整正文（选定 / 备选 /
否决理由 / 残余风险）在那里，本节只记**执行期的实测结果与对照**，不重复正文。

### 12.1 Explore E1 的实测结论 × §6 H1 预测表（逐格对照，预测原文未改）

E1 的做法是**实跑装载器**（`load_rules` 对每种写法各来一次），不是纸上判断：

| # | 候选规则 | H1 的预测 | 实测（装载器实际报的话） | **对照** |
|---|---|---|---|---|
| R1 | 产出远大于销出 | 够 | 够，原样表达（`sum_positive` + `sum_negative_abs` + `difference` + `related_sum` + `at_least_fraction_of`） | **吻合** |
| R2 | 外协已发料、迟迟未收 | 不够 · 缺按字段值相等筛行；判「逾期」还缺日期算术 | 确实缺：`{"field":"docstatus","operator":"equals","value":2}` → `行过滤 #0：不认识的键 ['value']`。`truthy` 会把 `docstatus == 1` 一起排掉，表达不出「只排作废的」 | **吻合** |
| R3 | 订单已关闭但实发少于订单量 | 不够 · 同上（按 `status` 相等筛行）；⚠️ 方向不缺 | 缺的是**反向**那一个：`exclude` 的语义是「命中即排除」，「只看 `status == "Closed"`」必须写成「排除 `status != "Closed"`」→ 缺 `not_equals`。方向确实不缺（`difference` + `greater_than` 反写即可） | **部分吻合（预测缺 `equals`，实际缺的是同族的 `not_equals`）** |
| R4 | 某物料入库为零却有出库 | 不够 · 缺触发侧的合取 | 确实缺：`{"and": {...}}` → `触发：不认识的键 ['and']` | **吻合** |
| R5 | 同一物料在多个仓库重复堆积 | 不够 · 缺按组计数 | 确实缺：`count` → `度量算子 'count' 不在有限算子集 [...] 里` | **吻合** |

⚠️ 预测表一格未改。R3 那格的偏差是**同一族里的方向**，不是「预测完全落空」，按 §6 写死的记法记 `部分吻合`。

### 12.2 五条 Decision 的裁定（正文见 §7.10）

| # | 裁定 | 一句话理由 |
|---|---|---|
| D1 | 判据表达取 P1.5 的 `Rule` 形状 | 本仓走站点 REST 只读端点，**没有 SQL 面**；自然语言 `assert` 不可执行 |
| D2 | 包文件用 **JSON** | CI 五处 `pip install pytest certifi` 没有 PyYAML，`.github/workflows/**` 在红线内 |
| D3 | **扩** `equals` / `not_equals` 两个行过滤算子；R4/R5 **收内容** | 两者语义有限可枚举、写得出自己的拒载判据；日期算术要引入时间基准与时区口径，不在本期 |
| D4 | 包落 **`industry-packs/<pack_id>/pack.json`** | 只用今天可判的两条口径（路径解析方式 + 它自己的判据）；打包那两条不可验证，未拿来当理由 |
| D5 | 出处落 **`Hit.pack_id`**，来源那一层是 `Pack.pack_id` → `run()` 形参 | 不进 `Rule`：同一 `rule_id` 挂两个包时出处必须不同，(C) 前缀方案上这条判据构造不出来 |

**D3 与 Goal 4 的解冲突按 §7 写死的口径执行**：E1 确认 R2/R3 缺「按字段值相等筛行」→
**本期必须新增它**，没有用「收内容」把外协那一类砍掉。新增算子同时交付了三样：
有限键集里的登记（`ROW_FILTER_KEYS` 加 `value`）· 求值判据 ·
**四种拒载判据**（未知算子名 / 缺字面量 / `truthy` 夹带 `value` / 非标量字面量）。

### 12.3 变异自查 M1–M8（逐个复跑，**八个全部由绿转红**）

| # | 变异 | 结果 | 打红它的判据（关键点） |
|---|---|---|---|
| M1 | 校验器只检查 `test_case` 键存在、不真跑 | **红** | `test_h3_flipping_expect_hit_on_any_rule_makes_validate_fail`（三条规则各一次） |
| M2 | 校验器把「装载失败」吞掉后退 0 | **红** | `test_h6_a_rule_without_a_test_case_exits_four_and_names_the_rule` |
| M3 | `--pack` 拼错时退 0 | **红** | `test_h6_a_missing_pack_exits_three_and_names_the_pack_argument` |
| M4 | 某条规则的判据被改成永远命中 | **红** | ⚠️ 由 **阴性对照** `test_h2_negative_no_rule_fires_on_healthy_data` 打红 —— **消融对它是绿的**，这正是 H2 把主判据从消融换成阳性/阴性对照的理由 |
| M5 | 命中量写死成 1010 | **红** | ⚠️ 由 **第二个数据集** `test_h2_the_backlog_quantity_moves_with_the_dataset` 打红；固定测例那条（期望正好是 1010）对它是**绿**的 |
| M6 | 规则声明里夹带具体单号 | **红** | **源声明侧那一半单独打红**：`test_h5_the_pack_source_carries_no_document_number_and_no_answer` |
| M7 | 出处被写死 / 丢失 | **红** | `test_h7_the_same_rule_under_two_packs_reports_two_different_origins` + `test_h7_the_engines_own_minimal_rules_claim_no_pack` |
| M8 | CLI 的退出码恒为 0 | **红** | ⚠️ **只被子进程判据打红**；`test_h6_the_function_level_entry_agrees_with_the_subprocess`（函数级）对它是**绿**的 —— 这正是两种都写的理由 |

**没有 M9**：八个变异无一需要就地补断言。

### 12.4 H2–H7 逐条对照

- **H2**（每条规则一对阳性 / 阴性对照）：**成立**。三条规则的 `test_case` 都是「期望命中」且都真跑得过（阳性）；
  三种异常一个都没有的健康合成数据上**三条全部零命中**（阴性）。
  R1 的阳性对照用固定测例，命中量 `== EXPECTED_BACKLOG_QTY`（1010.0）；
  第二个数据集（`inhouse=800` / `subcon=600` / `delivery=500`）命中 **900.0**，判据里写死的字面量 `!= 1010`。
  ⚠️ **消融判据保留为附带断言，并逐字标注它接近恒真。**
- **H3**（校验器真的跑了每一条测例）：**成立**。「翻转 `expect_hit`」与「摘掉 `test_case`」两种变异
  **逐条各施加一次（含最后一条）**，共 6 次，每次 `validate` 都非零退出且消息指名到那条 `rule_id`。
  另加一条 `test_h3_the_number_of_rules_is_what_the_per_rule_sweep_assumes`：
  包里加了第四条而扫描没跟着加时，「含最后一条」这句话会悄悄失效 —— 这条钉住它。
- **H4**（离线绿 ≠ 站点绿）：**部分吻合，照实记，见 §12.5。**
- **H5**（不许照答案写规则）：**成立**。源声明与装载后两侧都判，`test_case` 整块是显式例外，
  且另有一条断言测例的取值**不许照抄固定测例的数**。
- **H6**（四种输入四种可区分的处置）：**成立，口径取 (i)**（不同退出码 **并且** 消息指名到具体对象）：
  `0` 健康 / `3` 查无此包 / `4` 缺 `test_case` / `5` 测例跑不过；`2` 留给 argparse，不复用。
  四个码互不相等这件事本身也有一条断言。
- **H7**（出处可回溯）：**成立**。同一批 `rule_id` 写进两个不同 `pack_id` 的包，两次命中的
  `pack_id` 分别是 `discrete` 与 `other-pack`，`rule_id` 逐条相同 —— 出处不是从 `rule_id` 猜的。

### 12.5 H4：活站点核对的实测结果（**部分一致**，不改规则去迁就站点）

环境 `frontend@http://127.0.0.1:18080`，整份 `discrete` 包跑**一次**，9 次只读请求。

| 规则 | 离线固定测例 | 活站点 | 判定 |
|---|---|---|---|
| `discrete/finished-goods-backlog` | 命中 `1010.0`（`HRD-PACK-5K` / `成品仓 - HRD`） | **逐字一致** | ✅ |
| `discrete/subcontracting-issued-not-received` | 零命中 | 零命中 | ✅（两侧零命中是正确行为，§1.10） |
| `discrete/closed-order-short-delivered` | 命中 `10.0` | **零命中** | ⚠️ **D-12 预言的失败形态被抓到** |

⚠️ **H4 的防伪前提先成立**：活站点命中集合**非空且含 R1** —— 否则「两个空集相等」也叫「逐字一致」。

第三行的处置**照 §6 H4 与 §8 风险 ③ 写死的口径**：
- **先原样复跑那条命令**（裁判规则 3），结果相同 → **可复现**，不是偶发。
- 可观测事实：站点上 `Sales Order.status` 是 `"To Deliver and Bill"`，
  而 `agenerp/seed/model.py:57` 的 `SALES_ORDER_STATUS` 是 `"Closed"`；
  `agenerp/seedsite.py` 全文没有写这个 `status` 的地方。
- **到此为止不再往下猜根因**（ERPNext 提交时会不会自己重算 `status`、正确的置法是什么，**未取证**）。
- **规则一个字没改去迁就站点** —— 那是照答案写规则，且会让它在真正的「订单被人工关闭」场景上失效。
- 归属**不在本 plan 的交付面**（是种子装载面与离线数据集的一致性问题），
  已记 `docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md`，
  并在 `docs/masterplan/STATE.md` §3 追加 needs-human。

### 12.6 判据条数与验证命令

`tests/unit` 基线 **414 passed** → 收口 **453 passed**，差 **+39**（全部落 `tests/unit/test_industry_pack.py`）。

| # | 命令原文 | 退出码 |
|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` | **0**（`门禁 11 项：预期红 0，绿 11，跳过 0` · `453 passed`） |
| ② | `python3 -m pytest tests/contracts -q` | **0**（`151 passed`） |
| ③ | `python3 -m pytest tests/tools -q` | **0**（`81 passed, 12 skipped`，与基线逐字相同） |
| ④ | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0**（`All checks passed!`） |
| ⑤ | `python3 -m agenerp.packs validate --pack discrete` | **0** |

实现提交 sha **`6682b68`**。

### 12.7 红线复核

`git diff --name-only 928a888 HEAD -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md`
→ **无输出**。`docs/masterplan/STATE.md` 的 numstat 为 `14	0`（**删除列为 0**，只追加）。
`docs/masterplan/` 其余文件未改；证据仓（`XM_PATH`）未写入；未生成任何运行时 Server Script；
项目名 / 包名 / 命名空间未动。**红线 1–7 无一触碰。**


## Closure

Status Note: **completed**（2026-08-24）。三个 Phase 全部执行完毕，五条验证命令全退 0，
实现提交 sha `6682b68`。

**§10 要求的逐字声明五件事**：

1. ⚠️ **`rule.lookup` 未接线。** 本 plan 交付的是**包与校验器**，**不是「行业包已装载进工具面」**。
   `agenerp/tools/queries.py` 的 `rule_lookup` **仍然指名报错**（只改 docstring 的说法，
   报错消息的行为一个字未动），理由从「本仓没有行业包」变成「**包在盘上、未接线，接线待人裁定**」。
   接线的两条出路与各自代价已交人，见 `docs/masterplan/STATE.md` §3。
2. **WBS §4 P1.6 的验收命令字符串已定稿**（`python` → `python3`，形状不变），
   定稿证据行已追加到 `docs/masterplan/STATE.md` §2；`docs/masterplan/` 已有行只有人能改（红线 5），
   归属并入 §3 那条 needs-human 的第二个 bullet，**loop 未代改**。
3. **H1 的预测表与实测逐条对照结果见 §12.1**：五格里 **四格 `吻合`、R3 一格 `部分吻合`**
   （预测缺 `equals`，实际缺的是同族的 `not_equals` —— `exclude` 的语义是「命中即排除」）。
   **预测表原文一格未改。**
4. ⚠️ **外协那类规则未在真实数据上验证过命中。** 种子数据集的外协链是完整的（发出去多少收回来多少），
   固定测例与活站点上**都零命中，而那个零命中是正确行为**。它的阳性对照落在自己的 `test_case`
   （合成行）上，真实数据上验的只是**它不误报**（且那个零命中必须是**算出来的零**，判据钉住了这一点）。
5. ⚠️ **消融判据是恒真的那一侧。** `without()` + `run()` 的实现下抽掉规则自然零命中 ——
   它证明的是「引擎读清单」，**不证明「规则有判别力」**。发现力由**每条规则的阳性/阴性对照**证明
   （M4 就是被阴性对照打红的，消融对它是绿的）。

⚠️ **verification scope limited 的两处，照实写**：
- **活站点那一跑做了，但结论是「部分一致」不是「逐字一致」**（§12.5）：
  `closed-order-short-delivered` 离线命中 10、站点零命中。**这不是本包的缺陷**，
  是 D-12 预言的失败形态被抓到；根因**只写到可观测的那一层**（站点 `status` 与离线数据集对不上、
  装载器没写它），再往下**未取证、不猜**。
- **`tests/unit` 在 CI 与 `commands.test` 两侧都覆盖得到**，本 plan 新增的 39 条判据
  `GATE_VERIFY` 与 CI 都复跑得到；但 **`python3 -m agenerp.packs validate` 这条 CLI 本身不在任何 CI job 里**
  （`gates-l2-seed` 判四条 CLI 退出码，本 plan 无权往那个 job 加第五条）——
  它的退出码由 `tests/unit` 里的**子进程判据**钉住，**不得读成「CI 直接跑了那条命令」**。

Closure Audit Evidence:

- Auditor / Agent: ⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，
  执行者自审**不算独立**（照 P1.3 / P1.5 首次收口的同一处理）。
  `closure audit was independent` 这条 gate **留白**，不勾。
  可由后续独立会话按 P1.4 / P1.5 的先例补做，补做记录**追加**在本节末尾，不改写本段。
- Evidence: 命令原文与退出码见 §12.6（五条全 0）· 变异自查见 §12.3（M1–M8 全红，无 M9）·
  H1 逐格对照见 §12.1 · 活站点核对见 §12.5 · 红线复核见 §12.7 ·
  代码与文档落地见 sha `6682b68` 与 `docs/architecture/module-boundaries.md` §7.10 ·
  会话证据行见 `docs/masterplan/STATE.md` §2（2026-08-24T21:40Z）·
  日志见 `docs/logs/2026/08-24.md` 首条。

Follow-up:

- **`rule.lookup` 接线** —— 见 §11 第一条，`out-of-scope improvement`，重开条件是**人给出裁定**。
  **不是缺陷**：WBS §4 P1.6 的验收原文只要求 `packs validate` 退 0，不要求接线。
- **日期算术（「逾期 N 天」那一维）** —— 见 §11 第二条，D3 的判定口径把它划在本期之外。
- **D01 格式的转换层** / **`thresholds` / `terminology` 两个顶层块** —— 见 §11 第三、四条，
  都是显式定界，本期没有输入 / 没有消费者。
- ⚠️ **§12.5 那条活站点差异不放在这里** —— 它是**确认的缺陷**，按 §10 的口径不许降级成 follow-up：
  已按缺陷处理，落 `docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md`
  并在 STATE §3 立了 `[open]` 的 needs-human。它的归属（种子装载面）**不在本 plan 的交付面内**，
  因此不构成本 plan 的 in-scope 降级。

### 独立关闭审计补做记录（2026-08-24，追加节 —— 上方 `Closure Audit Evidence` 块一个字未改写）

- **Auditor / Agent**：mission-driver 派发的**独立收口审计器**（session `2026-08-24-203159-mission-driver`），
  fresh session、不带实现上下文、非本 plan 的执行者。这正是上方那一节写死的「补做条件」。
- **审计基线**：`git log --oneline -1` → `eda554f`（本 plan 的收口落账提交；实现提交是 `6682b68`）；
  `git status --porcelain` 只有同批第二个 plan `2026-08-24-2109-2-explain-cost-accounting.md` 未跟踪（起草产物），
  本 plan 交付面内的文件工作树干净。

- **复跑（命令原文 + 退出码，逐条抄自终端，与 §12.6 声称的数字逐字对照）**：
  - `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0** ·
    `门禁 11 项：预期红 0，绿 11，跳过 0` · `453 passed` **吻合**
  - `python3 -m pytest tests/contracts -q` → **exit 0** · `151 passed` **吻合**
  - `python3 -m pytest tests/tools -q` → **exit 0** · `81 passed, 12 skipped` **吻合**
  - `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
    → **exit 0** · `All checks passed!` **吻合**
  - `python3 -m agenerp.packs validate --pack discrete` → **exit 0** ·
    实测输出逐字列出**三条**规则及其测例名 **吻合**
  - `python3 -m pytest tests/unit/test_industry_pack.py -q` → **exit 0** · **`39 passed`** ——
    与 §12.6 的「基线 414 → 收口 453，差 **+39**」**逐字吻合**（新增判据条数不是估的，是复跑数出来的）

- **实读核对（不信 `[x]`，逐条对活代码）**：
  - 制品 `industry-packs/discrete/pack.json` 在盘上，`pack_id: discrete`、**三条规则各带 `test_case`**；
    三条分别是成品积压 / 外协发出未收 / 订单已关闭却少发 —— 覆盖 Goal 4 点名的**外协一类**。
  - `agenerp/packs/` 三个模块齐全（`__init__.py` / `loader.py` / `__main__.py`）：
    `load_pack` 把 `PackNotFound` 与 `PackLoadError` **分得开**（不是同一个非零）；
    `validate_pack` 真的委派到 `agenerp.inspection.engine.check_test_cases`，**不是只查键存在**；
    `__main__.py` 的四个退出码 `0/3/4/5` 互不相等且 `2` 留给 argparse。
  - **D3 的扩算子真的落到了求值面**（反空壳）：`agenerp/inspection/rules.py:56-62` 登记
    `EXCLUDE_EQUALS` / `EXCLUDE_NOT_EQUALS`、`ROW_FILTER_KEYS` 含 `value`，
    且 `agenerp/inspection/engine.py:170,172` **真的在 `_excluded()` 里分支求值** ——
    不是「登记了但没人读」。
  - **D5 的出处真的落到了 `Hit`**（反空壳）：`engine.py:109` 的 `pack_id: str = ""`、
    `:113` 进 `as_dict()`、`:215/251/263/283` 一路从 `run()` / `inspect_site()` 的形参盖进每条命中 ——
    来源那一层是 `Pack.pack_id`，**不是从 `rule_id` 猜的**。
  - 坏包夹具在 `tests/unit/pack_fixtures/`（`missing-test-case` / `failing-test-case`），
    **没有躺进 `industry-packs/`** —— 与 Phase 2 写死的口径一致。
  - `tests/unit/test_industry_pack.py` 里 H2 / H3 / H5 / H6 / H7 各自有具名判据，
    H3 的两种变异**各自 parametrize 逐条施加**（含最后一条），另有一条
    `test_h3_the_number_of_rules_is_what_the_per_rule_sweep_assumes` 钉住「含最后一条」这句话不会悄悄失效。

- **红线复核（独立复跑，不采信 §12.7 的转述）**：
  `git diff --name-only 928a888 HEAD -- tests/gates .github/workflows missions docs/masterplan/DECISIONS.md`
  → **无输出**；`git diff --numstat 928a888 HEAD -- docs/masterplan/STATE.md` → **`14 0`**（删除列为 0，只追加）。
  改动清单 21 个文件全部落在本 plan 声明的 Targets 内。**红线 1–7 无一触碰。**

- **五点一致性**：`Plan Status: completed` · Phase 1/2/3 三个 `Status: completed` ·
  三组 Exit Criteria 全 `[x]` · §10 Closure Gates 全 `[x]`（本条即最后一条）·
  `docs/logs/2026/08-24.md` 首条与 `docs/backlog/p1-insight-roadmap.md` 工作项 8（**`done`**，未停在 `todo`）
  所述数字与结论**逐条一致**。

- **Deferred 诚实性核查（重点看有没有把缺陷藏进 follow-up）**：§12.5 那条活站点差异
  （`closed-order-short-delivered` 离线命中 10、站点零命中）**没有**被降级成 follow-up ——
  已按缺陷落 `docs/bugs/02-live-site-sales-order-is-not-closed-so-the-account-green-trap-is-absent.md`
  并在 `docs/masterplan/STATE.md` §3 立了 `[open]` 的 needs-human，且归属（种子装载面 `agenerp/seedsite.py`）
  确实不在本 plan 的交付面内。§11 四条 Deferred 各有 classification 与重开条件，**无一条是确认的活缺陷**。

- **收口叙述的五件事逐条复核，无一处夸大**：① `rule.lookup` 确实**未接线**
  （`agenerp/tools/queries.py` 仍 `raise ToolError`，只改了 docstring）；② WBS 验收命令字符串定稿证据行在
  `STATE.md` §2:324-325，`docs/masterplan/` 已有行未被代改；③ H1 预测表**原文一格未改**，
  R3 那格记的是 `部分吻合`；④ 外协那条确实**未在真实数据上验证过命中**；
  ⑤ 消融判据确实被逐字标注为「接近恒真」并降级为附带断言。

- **判定**：**通过。** Exit Criteria 与活代码逐条吻合，新增代码全部有运行时调用面（无空壳），
  五点一致，Deferred 无藏缺陷，docs 已同步。本 plan 可保持 `completed`。
