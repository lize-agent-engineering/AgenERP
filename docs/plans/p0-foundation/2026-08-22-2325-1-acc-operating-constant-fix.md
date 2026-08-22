# 2026-08-22-2325-1 修 `ACC_OPERATING` 常量缺陷，并给 15 个带缩写后缀的常量补一条机械判据

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 工作项 7（种子数据）—— 已确认的**活缺陷**修复，非新功能
> Last Reviewed: 2026-08-22
> Source: `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`（`Status: open（登记不修）`）
>   + plan `2026-08-22-2107-1` `## Deferred But Adjudicated` 最后一条（`Classification: confirmed defect`，`Successor Required: yes`）
> Related: `2026-08-22-2107-1-seed-site-write-surface-and-masters.md` · `2026-08-22-2107-2-seed-documents-site-computed-backlog.md`
> Audit: required

## Current Baseline

**这一节全部来自 2026-08-22 对 `20f5679` 的实读，不是回忆。**

- `agenerp/seed/model.py:60` 逐字 `ACC_OPERATING = "生产费用（计入估值）- XM"` —— `- XM` 前**少一个空格**。
  同文件另外 10 个 `ACC_*`（`:55`–`:65`）与 4 个 `WH_*`（`:26`–`:29`）全部是 ` - XM`。
- ERPNext v15 的 `Account.autoname` 走 `" - ".join([account_name, abbr])`，只可能产出带空格的名字；
  bug note `## Reproduction` 记着 2026-08-22 用真载荷在活站点上建过一次，回的 `data.name` 带空格。
  **这不是推理，是实测。**
- 缺陷**至今未修**：`grep -n ACC_OPERATING agenerp/seed/model.py` 仍是那一行。
  bug note 的 `> Status:` 仍是 `open（登记不修）`。
- **现有的代偿是「容忍 + 报告」，不是修复**：
  - `agenerp/seedsite.py:80` `strip_abbr` 对 ` - XM` 与 `- XM` **两种后缀都剥**，docstring 逐字写着
    「本 plan 的 Closure Gate 要求 `agenerp/seed/**` 一个字节未改，故**只容忍、只报告，不修改**」。
  - `agenerp/seedsite.py:566` `LoadReport.mismatches` + `:609` 在站点回的真名与**原始常量**不符时追加一条，
    `:585` 在 `LoadReport.lines()` 内生成告警行、由 CLI 原样打印。活站点上实测打出来过。
  - **两条**单测把这个告警行为钉住（**不是一条** —— `2107-1` 的 Deferred 逐字写着「有**两条**单测（报告 + 不空转）」）：
    ① `tests/unit/test_seedsite_loader.py:181`–`:195` `test_account_name_mismatch_is_reported_not_swallowed`
    （**四条** assert：`:188` / `:193` / `:194` / `:195`），`:188` 逐字「常量若被修好，本测试应随之改写」；
    ② `tests/unit/test_seedsite_loader.py:198`–`:202` `test_the_mismatch_check_is_silent_for_every_other_constant`，
    `:202` 逐字 `assert len(report.mismatches) == 1, report.mismatches`。
    **② 会在 Phase 2 之后必然转红**（修完之后 `mismatches` 恒为空），它和 ① 一样必须被改写。
- **`strip_abbr` 的输入面已逐个枚举过，不是抽样**（`grep -rn "strip_abbr\|site_name_of" --include='*.py'`）：
  **直接调用 3 处** —— `agenerp/seedsite.py:100`（`site_name_of` 内）、`:148`、`:163`；
  **经 `site_name_of` 间接汇入 23 处** —— 产品代码 **13 处**（`:147` `:162` `:168` `:472` `:528` `:539`
  `:542` `:552` `:554` `:775` `:776` `:792` `:795`）+ 测试 **10 处**
  （`test_seedsite_loader.py:121` `:135` `:140` `:188` `:193` ·
  `test_seedsite_documents.py:196` `:372` `:375` `:378` `:381`）。**合计 26 处。**
  ⚠️ `:147` 与 `:162` 是**驱动 `plan_steps()` 的两个主调用点**，起草时漏掉过，此处已逐条重数补上。
  **这 26 处喂进去的全部是 `ACC_*` 或 `WH_*`**（含 `masters.warehouses()` 那一路，其 `name` 取自 `WH_*`，
  见 `agenerp/seed/masters.py:62`–`:65`）；`M.COMPANY` / `TRANSIT_WAREHOUSE_TYPE` / `ROOT_WAREHOUSE` /
  `PARENT_*` **一条都不经过它**。
  这一点决定了「无后缀即报错」这个方向可行，不会误伤既有调用方 —— **`Decision` 依赖的是这份枚举，不是印象。**
- **没有任何判据钉住「常量必须能被站点派生出来」**：`tests/unit/test_seedsite_loader.py:188` 钉的是
  它**派生不出来**（即钉住了缺陷本身）；`tests/gates/test_seed_dataset_absurdity.py` 判的是数量与金额，
  不判科目名（实测该文件内 `grep 生产费用` 零命中，`grep -rn 生产费用 tests/` 全目录零命中）。
  **所以修完这一个常量之后，第 12 个常量再拼错，仓里一条判据都不会红。**
  **这不是第二个结果面**（Minimum Rule 4）：本 plan 只有一条关闭判据 —— 「15 个带后缀常量全部可被站点派生，
  且这一点由机械判据与一次活站点实跑同时证实」。修常量是**当下的实例**，机械判据是**同一条判据的回归证明**，
  两者共用同一组证据、同一次关闭审计。若把它们拆成两个 plan，第二个 plan 的关闭判据将与第一个逐字相同。
- 缺陷的血径已被下游代码写死为字符串标签，**不涉及金额**：
  `agenerp/seed/documents.py:101`、`agenerp/seed/ledger.py:123` 只把它当 `account` 标签用；
  `agenerp/seedsite.py:472` / `:554` 取的是 `site_name_of(M.ACC_OPERATING)`（已被容忍分支纠正过的名字）。
  **因此改这一个常量不改变任何一个数**，1,010 米 / ¥6,450 不受影响 —— 但这是**待验证的预期，不是结论**，
  Phase 3 用实跑退出码确认。

## Goals

- `agenerp/seed/model.py` 的 15 个带公司缩写后缀的常量（11 个 `ACC_*` + 4 个 `WH_*`）**全部**满足
  `constant == " - ".join([<x>_name, ABBR])`，即站点的 `autoname` 有可能派生出它们。
- `agenerp/seedsite.py` 的 `strip_abbr` **不再容忍畸形后缀**：喂进一个站点派生不出来的常量时**失败即停**，
  而不是悄悄纠正后照样往站点写。
- 仓里存在一条**机械判据**，任何一个新增或改动的带后缀常量拼错时立刻红，且红得指名道姓。
- `docs/bugs/01-...md` 从 `open` 转为已修复，并按 `docs/bugs/00-bug-fix-note-writing-guide.md` 补齐修复记录。

## Non-Goals

- **不动 `tests/gates/**` 一个字节**（红线 1）。本 plan 不新增、不修改任何门禁。
- **不改任何金额常量**，不碰 `agenerp/seed/checks.py` 的期望值。
- **不给种子装载补门禁形态**——那是 `docs/backlog/gate-proposal-seed-dataset.md` 里人的动作（红线 1）。
- **不碰 `.github/workflows/**`**。CI 覆盖面归本批第二个 plan `2026-08-22-2325-2`。
- 不给装载器补 teardown / cancel（`2107-1` / `2107-2` 已裁定，重开事件未触发）。
- **不重构** `docs/context/project-context.md` 的验证命令表的**结构**（`1041-1` 登记的 `optimization candidate`，
  重开事件是「人明确裁定要重构该表时」，**未触发**）。
  ⚠️ **「不重构结构」不等于「不改准事实」**：该表 `:57` 与 `docs/architecture/module-boundaries.md:1126`
  都把「`tests/unit` **283** 条」写成代偿控制的一部分，而 Phase 1 会让这个数变大 —— 那是**确认的漂移**，
  Phase 4 有专门的 `Fix` 项就地改准它，**不是「只在需要时」**（Anti-Slacking Rule 不许留这种条件式承诺）。

## Task Route

- Type: `bug investigation`（诊断已完成于 bug note）+ `implementation-only change`（修复面）
- Owner Docs: `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md` ·
  `docs/architecture/module-boundaries.md` §12.9（装载器）· `docs/backlog/p0-foundation-roadmap.md` 工作项 7
- Skill Selection Basis: `none`。修一个常量 + 补一条机械判据 + 一轮活站点实跑，
  `docs/skills/README.md` 里没有对应工作方法的技能；活站点验证的做法已由 `2107-1` / `2107-2` 固化在
  `docs/context/project-context.md` 的验证命令表里，照抄即可。

## Infrastructure And Config Prereqs

- 活站点，起法逐字沿用 `2107-2`：`AGENERP_HTTP_PORT=18080 docker compose up -d --wait`。
- **强制前置：每次测量前 `docker compose down -v` 冷起。** 理由是 `2107-1` / `2107-2` 已裁定的既有事实——
  装载器没有 teardown，`SiteClient.submit_doc` 不可逆，提交过的单据在站点侧回不去。
- 环境变量（沿用）：`AGENERP_LIVE=1` / `AGENERP_SITE=frontend` /
  `AGENERP_SITE_URL=http://127.0.0.1:18080` / `AGENERP_ADMIN_PASSWORD=admin`。
- **回滚策略**：本 plan 对站点只做「建对象」，不做 DDL、不做删除。站点侧复位路径只有一条且已实测过：
  `docker compose down -v` 冷起。代码侧回滚是 `git revert`，无数据迁移。

## Execution Plan

### Phase 1 - 先立判据，再修常量

Status: completed
Targets: `tests/unit/test_seed_model_constants.py`（新建）· `tests/unit/test_seedsite_loader.py`
Skill: `none`

- Item Types: 逐项标注（两项 `Add | Proof` —— 两个净新增判据；其余 `Proof`）
- Prereqs: 无

- [x] `Add | Proof` 新建 `tests/unit/test_seed_model_constants.py`：对 `agenerp/seed/model.py` 里
      **全部** `ACC_*` 与 `WH_*` 常量做机械核对——每一个都必须等于 `" - ".join([<x>_name, ABBR])`。
      判据**自己遍历模块属性**（`ACC_` / `WH_` 前缀），不手抄清单，否则第 16 个常量加进来时判据不会长。
      失败信息必须点名是哪一个常量、实际值是什么。
      ⚠️ **判据不得经由 `seedsite.strip_abbr` / `site_name_of` 求值** —— 拿那两个函数去证明常量合规，
      是用「容忍它的那段代码」给它开证明，判据会空转。直接对字符串本身断言。
      **这一步先跑，必须红，且只红一条（`ACC_OPERATING`）** —— 红不止一条说明基线读错了，停下来重读。
      - Skill: `none`
- [x] `Proof` 同一文件内补一条：`ABBR`（`agenerp/seedsite.py`）与 `model.py` 常量后缀的一致性——
      两处此刻各写各的（`seedsite.ABBR` 与常量里字面的 `XM`），判据要把它们绑在一起，
      否则改公司缩写时常量会集体失配而无人告知。
      - Skill: `none`
- [x] `Proof` 改写 `tests/unit/test_seedsite_loader.py` 里**钉住缺陷本身**的那**两条**单测（不是一条）：
      ① `:181`–`:195` `test_account_name_mismatch_is_reported_not_swallowed`（`:188` 逐字
      「常量若被修好，本测试应随之改写」）；② `:198`–`:202`
      `test_the_mismatch_check_is_silent_for_every_other_constant`（`:202` 断 `len(mismatches) == 1`，
      **修复后 `mismatches` 恒为空，它必然转红**）。
      改写后两条必须**仍然覆盖**「报告」与「不空转」这两半行为，但输入换成**测试内构造的畸形 `Step`**，
      不再依赖 `M.ACC_OPERATING` 是坏的。**不得删掉任何一条覆盖** —— 删掉等于修好一个缺陷、丢掉一层保护。
      - Skill: `none`
- [x] `Add | Proof` 补一条钉住 Phase 2 那个 `Decision` 的单测：`strip_abbr` 收到不以 ` - {ABBR}` 结尾的串时
      **抛异常**（`pytest.raises`），且异常信息里含**那个常量本身**与所要求的形状 `<name> - {ABBR}`。
      **这条测试在 Phase 2 之前必然红**（此刻 `strip_abbr` 只会容忍地返回），一并记进本 Phase 的红清单。
      - Skill: `none`
- [x] `Proof` 记录这一步的实跑：`python3 -m pytest tests/unit -q` 的退出码与红的条数，逐字抄进 plan。
      **预期红的是三类**：新机械判据 1 条（`ACC_OPERATING`）+ `strip_abbr` 抛异常那条 + 改写中的两条覆盖。
      与预期不符就停下来重读基线，**不许改判据去凑**。
      - Skill: `none`

Exit Criteria:

- [x] 新判据存在且**在修复之前实测为红**，点名 `ACC_OPERATING`，退出码与点名集合逐字记录在案
- [x] `test_seedsite_loader.py` 的**两条**告警覆盖均为改写而非删除，改写后二者在修复前后**都绿**
- [x] `strip_abbr` 畸形输入抛异常的那条单测已存在（此刻红，Phase 2 转绿）
- [x] `tests/gates/**` `git diff --numstat` 无输出（红线 1 自查）
- [x] No owner-doc update required（本 Phase 只动 `tests/unit/`）

#### Phase 1 实跑记录（2026-08-22，修复之前）

命令原文与退出码，逐字抄录：

```
$ python3 -m pytest tests/unit/test_seed_model_constants.py -q      → exit 1（新判据单独跑，1 failed, 2 passed）
$ python3 -m pytest tests/unit -q                                    → exit 1
3 failed, 285 passed in 0.63s
FAILED tests/unit/test_seed_model_constants.py::test_every_suffixed_constant_can_be_derived_by_the_site_autoname
FAILED tests/unit/test_seedsite_loader.py::test_the_real_master_data_plan_reports_no_mismatch_at_all
FAILED tests/unit/test_seedsite_loader.py::test_strip_abbr_refuses_a_name_the_site_could_never_derive
$ ruff check agenerp tests/unit tests/contracts                      → exit 0（All checks passed!）
$ python3 tools/gates/check_expected_red.py                          → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）
$ git diff --numstat -- tests/gates .github/workflows docs/masterplan/DECISIONS.md → 无输出（红线 1/2/3 自查）
```

新机械判据的失败信息逐字（它确实指名道姓）：

```
AssertionError: ACC_OPERATING = '生产费用（计入估值）- XM' 不以 ' - XM' 结尾，
站点的 autoname（" - ".join([<x>_name, abbr])）永远派生不出它；常量必须形如 `<name> - XM`
```

**⚠️ 与本 Phase 第 5 项「预期红三类（共四条）」的偏差，照实记，不改判据去凑**：
实测红 **3 条**，不是 4 条。差异全部落在「改写中的两条覆盖」这一类上，原因是本 Phase 第 3 项
与本节 Exit Criteria 第 2 条**要求改写后的两条在修复前后都绿**（输入换成测试内构造的畸形 `Step`，
不再依赖 `M.ACC_OPERATING` 的死活）。两处要求互斥时按 Exit Criteria 执行：

- `test_account_name_mismatch_is_reported_not_swallowed`（改写后）→ **修复前后都绿**，覆盖「报告」；
- `test_the_mismatch_check_is_silent_for_every_other_constant`（改写后）→ **修复前后都绿**，覆盖「不空转」；
- 「真实产品数据此刻零 mismatch」这半覆盖**没有被丢掉**，而是拆成**净新增**的第三条
  `test_the_real_master_data_plan_reports_no_mismatch_at_all`（修复前必红、修复后转绿），
  它就是活站点上 Phase 3 那条「不再出现 ⚠️ 告警行」的单测级同构。
  **覆盖面只增不减**：改写前 2 条 → 改写后 3 条 + `strip_abbr` 抛异常 1 条 = 4 条。

### Phase 2 - 修常量，并把 `strip_abbr` 从「容忍」改成「失败即停」

Status: completed
Targets: `agenerp/seed/model.py` · `agenerp/seedsite.py`
Skill: `none`

- Item Types: `Fix | Decision`
- Prereqs: Phase 1 完成（判据先红）

- [x] `Fix` `agenerp/seed/model.py:60`：`生产费用（计入估值）- XM` → `生产费用（计入估值） - XM`。
      **只加一个空格，同一行不做任何别的改动。**
      - Skill: `none`
- [x] `Decision` `strip_abbr` 的畸形输入语义。三个候选，选 (c)，理由与残余风险写进
      `docs/architecture/module-boundaries.md` §12.9 的追加段：
      **(a) 维持现状（两种后缀都剥）** —— 代价：下一个拼错的常量继续被静默纠正，缺陷不可见，
      而本 plan 存在的理由正是这种静默；
      **(b) 严格 `removesuffix(" - {ABBR}")`，不匹配就原样返回** —— 代价更坏：原样返回的串会被
      `site_name_of` 再拼一次后缀，往站点上**真建出** `X - XM - XM` 这种对象（bug note `:80`–`:81` 已预告），
      污染面比不修还大；
      **(c) 不匹配即抛（失败即停，站点上一个对象都不建）** —— 选它。
      **可行性已在 `## Current Baseline` 里查实**：`strip_abbr` 的全部输入只有 `ACC_*` / `WH_*`，
      没有无后缀的调用方，不会误伤。
      **残余风险**：将来若有人要用无后缀常量走这条路，会撞上这个异常——那正是希望发生的事，
      且异常信息里要写清「常量必须形如 `<name> - {ABBR}`」。
      - Skill: `none`
- [x] `Fix` 改准 `agenerp/seedsite.py` 里**两处**在本 plan 之后不再成立的行内陈述（确认的漂移，
      Minimum Rule 14 不降级）：① `:84`–`:90` `strip_abbr` 的 docstring，它逐字引用「本 plan 的 Closure Gate
      要求 `agenerp/seed/**` 一个字节未改，故只容忍、只报告，不修改」——那句话说的是 `2107-1`；
      ② `:116` `Step.source_constant` 的注释「（`M.ACC_OPERATING` 少一个空格）」。
      - Skill: `none`
- [x] `Fix` 处置 `docs/architecture/module-boundaries.md:1003`–`:1008`。**该段三句话的真假必须分开判，
      不许一锅端**（起草时写成「三句全为假」，那是错的，就地改准）：
      ① `:1003` 「`model.ACC_OPERATING` 在活站点上永远命不中」—— **Phase 2 之后确为假**，
      加 `就地改准` 块并点名本 plan id；
      ② `:1005`–`:1006` 「装载器**报告不静默**……但**不因此退非 0**」—— **仍然为真**。
      Phase 2 明文保留 `LoadReport.mismatches`（`agenerp/seedsite.py:598`–`:609` 本 plan 一行不动），
      名字不符照样报告、照样不退非 0。**准确的说法是「机制保留，但自本 plan 起没有已知的活触发点」**，
      不是「假」。**把它标成假，就是拿这个 `Fix` 项自己制造一条新漂移**，正是本项要消灭的东西；
      ③ `:1008` 「**本次不修**」—— **作为历史陈述为真**（「本次」指 §12.9 自己那个 plan `2107-1`，
      它确实没修）。**不加改准**，只加一条指向本 plan 的前向指引。
      与**本项自己**那句「原文一句不删（它是当时的证据）」以及 Phase 4 对 bug note 的同一条原则保持一致。
      ⚠️ **只追加一段不足以中和一句现在时的假陈述**，必须按本仓既有写法（本文件已有的先例：`:624` 与 `:881` 两处逐字
      `就地改准`、`:894` 一处 `改准二`、`:1135` 一处 `就地记准`）**在原处**加改准块并点名本 plan id。
      **原文一句不删**（它是当时的证据），只在其后加改准。
      - Skill: `none`
- [x] `Fix` 复查 `LoadReport.mismatches` 那条路径**没有因此变成死代码**：
      `Step.source_constant` 的存在理由是「常量与站点派生名不同」，修完之后两者恒等。
      **不得删除该机制**（它是站点回名与本仓预期的通用对账，不是为这一个缺陷造的），
      但要在 §12.9 里写明它此刻**没有已知的活触发点**，以及它仍然值得留着的理由。
      - Skill: `none`

Exit Criteria:

- [x] `python3 -c "from agenerp.seed import model as M; print(M.ACC_OPERATING.endswith(' - XM'))"` → `True`
- [x] Phase 1 那条机械判据由红转绿，`python3 -m pytest tests/unit -q` → exit 0，通过数不低于修复前的 283
- [x] Phase 1 那条 `pytest.raises` 单测由红转绿（`strip_abbr` 确实失败即停，异常信息含常量名与所需形状）
- [x] `docs/architecture/module-boundaries.md` §12.9 追加段落记录 `Decision` 的三个候选、选择与残余风险
- [x] `module-boundaries.md:1003`–`:1008` 的三句**分别**按 ①改准 / ②记为「无活触发点」/ ③只加前向指引
      处置完毕，**没有把仍然为真的 ② ③ 标成假**，且原文一句未删
- [x] `agenerp/seedsite.py:84`–`:90` 与 `:116` 两处行内陈述均已改准
- [x] `docs/logs/` 更新

#### Phase 2 实跑记录（2026-08-22，修复之后）

```
$ python3 -c "from agenerp.seed import model as M; print(M.ACC_OPERATING.endswith(' - XM'))"
True
$ python3 -m pytest tests/unit -q                        → exit 0（288 passed in 0.61s，修复前 283）
$ ruff check agenerp tests/unit tests/contracts          → exit 0（All checks passed!）
$ python3 tools/gates/check_expected_red.py              → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）
$ python3 -m agenerp.seed --seed 42 --verify             → exit 0
$ git diff --numstat -- tests/gates .github/workflows docs/masterplan/DECISIONS.md → 无输出
```

- `Decision` 落点：**新增 §12.11**（`docs/architecture/module-boundaries.md`），
  三个候选 (a)/(b)/(c)、选 (c) 的理由、26 处调用点枚举、残余风险与爆炸半径全部在内。
  §12.9 原段**一行未删**，其后加改准块，三句**分开处置**：①「永远命不中」判为**现已为假**并改准；
  ②「报告不静默但不退非 0」判为**仍然为真**，只补「机制保留、无活触发点」的准确说法；
  ③「本次不修」判为**历史陈述为真，不加改准**，只加前向指引。
- `docs/architecture/module-boundaries.md` `git diff --numstat` = `60 0`（**纯追加，删除列为 0**）。
- `LoadReport.mismatches` 机制**一行未动**（`agenerp/seedsite.py` 的 `record` / `lines` / `load_masters`
  比对分支全部原样），只在 docstring 内补了「无活触发点」的说明与 §12.11 指引。

### Phase 3 - 活站点实证：从冷起的空站点重跑整条种子链

Status: completed
Targets: 无代码改动（只跑，只记）
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 2 完成

- [x] `Proof` `docker compose down -v` 冷起空站点，依次跑：
      `--load-masters` → `--load-documents` → `--verify-site`，三条命令的退出码与关键输出行逐字抄进 plan。
      **承重判据**：`--verify-site` → exit 0 且 9 项全过，`actual_qty = 1010.00` / `stock_value = 6450.00`
      两行逐字与 `2107-2` 记录的**完全相同**（修常量不该改变任何一个数——这是要被证实或证伪的预期，不是结论）。
      - Skill: `none`
- [x] `Proof` **新增的正向判据**：`--load-masters` 的输出里**不再出现那条 `⚠️` 告警行**
      （`2107-1` 在活站点上实测打印过它）。`mismatches` 为空是本 plan 的直接结果面，必须被看见。
      - Skill: `none`
- [x] `Proof` 幂等复跑：`--load-documents` 连跑第二次 → `新建 0`。
      理由是修常量改变了科目的 `name`，幂等键跟着变；不复跑就不知道第二跑会不会重复建科目。
      - Skill: `none`
- [x] `Proof` 门禁不受影响：`AGENERP_LIVE=1 … python3 tools/gates/check_expected_red.py` → exit 0
      （`门禁 19 项：红 0，绿 19，跳过 0`）；默认判定环境下同一命令 → exit 0
      （`预期红 7，绿 12，跳过 0`）。**两个环境都要跑**，只跑一个不算。
      - Skill: `none`
- [x] `Proof` `python3 -m agenerp.seed --seed 42 --verify` → exit 0（纯内存那半没被改坏）。
      - Skill: `none`
- [x] `Proof` **变异验证（必须做，否则新判据是否有牙齿不可知）**：把另一个常量（取 `M.WH_RAW`）
      故意改成缺空格，跑 `python3 -m pytest tests/unit -q` → 必须 exit 1 且**逐字点名 `WH_RAW`**；
      复原后回 exit 0，`git diff --stat agenerp/seed/` 无输出。
      **变异对象选 `WH_RAW` 而不是 `ACC_OPERATING`**：后者是刚修好的那一个，拿它做变异等于只证明
      判据认得这一个常量，证不出「遍历」真的在遍历。
      ⚠️ **预先声明爆炸半径，免得执行者把它误判成基线读错**：Phase 2 之后 `strip_abbr` 失败即停，
      所以这次变异会让 `plan_steps()` 在调用点直接抛，`test_seedsite_loader.py` 与
      `test_seedsite_documents.py` 会**成片报错**，而不是只红新判据一条。
      **承重的是「点名集合里含 `WH_RAW`」**，不是「只红一条」——这与 Phase 1 那条「只红一条」的要求
      不冲突：那一条说的是修复之前、`strip_abbr` 还在容忍的时候。
      - Skill: `none`

Exit Criteria:

- [x] 上述六条实跑的命令原文、退出码、关键输出行**逐字**记录在 plan 与 `docs/masterplan/STATE.md` §2 追加行里
- [x] `--verify-site` exit 0 且两个承重数值与 `2107-2` 的记录逐字相同（若不同，**立即停下来**，
      按裁判规则 3 原样复跑，不猜根因，把差异写进 STATE §3 needs-human 队列）
- [x] 变异验证的红/点名/复原三段齐全
- [x] `docs/logs/` 更新

#### Phase 3 实跑记录（2026-08-22 → 08-23，本机，端口 18080，从 `down -v` 冷起的空站点）

**① 冷起 + 整条种子链**（命令原文与退出码逐字）：

```
$ AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v                       → exit 0
$ AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300 → exit 0
$ AGENERP_HTTP_PORT=18080 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin python3 -m agenerp.seedsite --load-masters   --site frontend   → exit 0
  合计：新建 40 / 已存在 0
$ …                                                    --load-documents --site frontend       → exit 0
  合计：新建 17 / 已存在 0 / 提交 11
$ …                                                    --verify-site    --site frontend       → exit 0
  站点侧对账：9 项，通过 9，失败 0
```

**承重判据，逐字与 `2107-2` 的记录相同**（`--verify-site` 的前两行）：

```
✅ Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00 / expected = 1010.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）
✅ Bin(XM-LACE-1000, XM 成品仓 - XM).stock_value = 6450.00 / expected = 6450.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_VALUE）
```

`## Current Baseline` 末条那个「待验证的预期」**由此被证实**：修常量**没有改变任何一个数**，
1,010 米 / ¥6,450 与 `--load-documents` 的 `新建 17 / 提交 11` 全部逐字不变。

**② 新增的正向判据 —— ⚠️ 告警行消失**（`2107-1` 在活站点上实测打印过它）：

```
$ grep -c "⚠️" <load-masters 第一跑输出>   → 0（grep 退出码 1 = 零命中）
```

`--load-masters` 的 16 行输出里**只有计数行**，没有任何 `⚠️ Account 的站点名与 agenerp.seed 常量不符`。
`mismatches` 为空是本 plan 的直接结果面，它被看见了。

**③ 幂等复跑**（修常量改变了科目的 `name`，幂等键跟着变，所以必须复跑）：

```
$ …  --load-documents --site frontend （第二跑） → exit 0   合计：新建 0 / 已存在 17 / 提交 0
$ …  --load-masters   --site frontend （第二跑） → exit 0   合计：新建 0 / 已存在 40
                                                            grep -c "⚠️" → 0
```

**科目没有被重复建**：`Account：新建 0 / 已存在 11`。

**④ 门禁两个环境各一次，都跑了**：

```
$ AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py → exit 0
  门禁 19 项：红 0，绿 19，跳过 0 / ✅ live 判定：全部门禁绿，零 red、零 skip
$ python3 tools/gates/check_expected_red.py                              → exit 0
  门禁 19 项：预期红 7，绿 12，跳过 0 / ✅ 与预期红名单完全一致
```

**⑤ 纯内存那半**：`python3 -m agenerp.seed --seed 42 --verify` → **exit 0**
（`✅ 种子 42：两次生成 diff 为空，场景断言全过`）。

**⑥ 变异验证（`WH_RAW`）—— 红 / 点名 / 复原三段齐全**：

```
变异：agenerp/seed/model.py:26  WH_RAW = "XM 原料仓 - XM" → "XM 原料仓- XM"
$ python3 -m pytest tests/unit -q  → exit 1，11 failed, 277 passed
逐字点名：AssertionError: WH_RAW = 'XM 原料仓- XM' 不以 ' - XM' 结尾，
          站点的 autoname（" - ".join([<x>_name, abbr])）永远派生不出它；常量必须形如 `<name> - XM`
复原：    $ python3 -m pytest tests/unit -q → exit 0（288 passed）
```

**爆炸半径与本 Phase 事先声明的一致，不是基线读错**：Phase 2 之后 `strip_abbr` 失败即停，
`plan_steps()` 在调用点直接抛，`test_seedsite_loader.py` / `test_seedsite_documents.py` **成片报错**
（11 条），承重的是「点名集合里含 `WH_RAW`」，实测**含**。

⚠️ **复原判据的措辞就地改准（本项写的是「`git diff --stat agenerp/seed/` 无输出」）**：
该措辞预设了 Phase 2 的修复**已经提交**；在本次执行里它尚未提交，所以复原后 `agenerp/seed/` 的 diff
**不可能为空**。可判的等价形式是「变异零残留」，实测：
`git diff agenerp/seed/` 的增删行**恰好只有** `-ACC_OPERATING = "生产费用（计入估值）- XM"` /
`+ACC_OPERATING = "生产费用（计入估值） - XM"` 这一对，`WH_RAW` 那行**一个字节未留**。

### Phase 4 - 收尾：bug note 转已修复 + owner doc 与 roadmap 对齐

Status: completed
Targets: `docs/bugs/01-...md` · `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md` · `docs/logs/`
Skill: `none`

- Item Types: `Fix`-heavy（4/5 项 `Fix`，末项 `Proof`）
- Prereqs: Phase 3 完成

- [x] `Fix` `docs/bugs/01-...md`：`> Status:` 从 `open（登记不修）` 改为已修复并点名本 plan id 与落地 sha；
      按 `docs/bugs/00-bug-fix-note-writing-guide.md` 的必备小节补齐 `Fix` 与「怎么防止它回来」，
      逐字点名 Phase 1 那条机械判据。**`Problem` / `Reproduction` / `Diagnostic Method` 三节一个字不改**——
      那是证据，改它等于销毁证据。
      - Skill: `none`
- [x] `Fix` `docs/backlog/p0-foundation-roadmap.md` 工作项 7 那段**追加**一行现状（不改写既有行）：
      本 plan 修了什么、`--verify-site` 的实测结论、以及**工作项 7 的状态一个字不改**（仍 `planned`，
      卡点仍是「那条 L1 门禁从未进过 `expected-red.txt`，划掉这个动作没有对象」）。
      **落点形状**：该文件 `:58` 已经指向「「7 现状」」而对照表里**没有这一行**（只有 4/5/6/8/9 现状）——
      本次追加按 `| 7 现状 |` 表行的形状落，顺带补上那个悬空指向。
      `git diff --numstat` 的删除列必须为 `0`。
      - Skill: `none`
- [x] `Fix` `docs/masterplan/STATE.md` §2 **追加**一条证据行（红线 5：只追加）。
      - Skill: `none`
- [x] `Fix` 就地改准**两处把「`tests/unit` 283 条」写成代偿控制**的行 —— Phase 1 新增判据后这个数必然变大，
      属确认的漂移（Minimum Rule 14，不降级）：① `docs/architecture/module-boundaries.md:1126`；
      ② `docs/context/project-context.md:57`。**只改那个数与随附的一句说明，不动表结构**
      （表结构重构是 `1041-1` 登记的人裁定题，重开事件未触发）。
      - Skill: `none`
- [x] `Proof` 收尾复跑：`python3 -m pytest tests/unit -q` + 默认判定环境的
      `python3 tools/gates/check_expected_red.py` + `ruff check agenerp tests/unit tests/contracts`
      三条全 exit 0，退出码抄进 plan。
      - Skill: `none`

Exit Criteria:

- [x] bug note 状态与本 plan 一致，证据三节未被改写
- [x] roadmap 与 STATE 均为**纯追加**（`git diff --numstat` 删除列为 `0`）
- [x] 工作项 7 的状态值**未被本 plan 改动**
- [x] `module-boundaries.md:1126` 与 `project-context.md:57` 的 `283` 已改准为实测新值，表结构未动
- [x] `docs/logs/` 更新

#### Phase 4 收尾复跑（2026-08-23）

```
$ python3 -m pytest tests/unit -q                        → exit 0（288 passed in 0.67s）
$ python3 tools/gates/check_expected_red.py              → exit 0（门禁 19 项：预期红 7，绿 12，跳过 0）
$ ruff check agenerp tests/unit tests/contracts          → exit 0（All checks passed!）
$ python3 -m pytest tests/contracts -q                   → exit 0（151 passed，顺带确认未波及）
$ git diff --numstat -- tests/gates .github/workflows docs/masterplan/DECISIONS.md → 无输出
$ git diff --numstat -- docs/backlog/p0-foundation-roadmap.md docs/masterplan/STATE.md
  1  0  docs/backlog/p0-foundation-roadmap.md      ← 删除列 0
  14 0  docs/masterplan/STATE.md                   ← 删除列 0
```

- **bug note**：`> Status:` → `fixed（2026-08-23）`，点名本 plan id 与落地 sha；
  `## Fix` / `## Tests` / `## Affected Artifacts` / `## Notes For Future Refactors` / `## Prevention Gap`
  五节各加一个 2026-08-23 追加段，**原文一句未删**；
  `Problem` / `Reproduction` / `Diagnostic Method` **三节一个字未改**（`git diff` 内该三节零改动行）。
  `## Prevention Gap` 的追加段**把补上的范围说准**：只覆盖 15 个带后缀常量，
  **不覆盖** `M.COMPANY` 等无后缀名字常量与 `seedsite.py` 自有的 ERPNext 结构 fixture 名。
- **roadmap**：新增一行 `| 7 现状 |`，落点按对照表既有的 `| N 现状 |` 表行形状，
  **顺带补上该文件第 58 行此前悬空的那个指向**；**工作项 7 的状态值一个字未改**（仍 `planned`），
  卡点逐字沿用（那条 L1 门禁从未进过 `expected-red.txt`，「划掉」没有对象）。
- **283 → 288 的改准**：`docs/architecture/module-boundaries.md`（§12.10 代偿控制那句）与
  `docs/context/project-context.md`（验证命令表「种子数据站点侧对账」一行）各一处，
  两处都标了「2026-08-23 就地改准」并写明口径是 `pytest tests/unit -q` 的实测通过数。**表结构未动。**

## Draft Review Record

- 独立评审第 1 轮：**needs revision**（独立子代理，fresh session）—— 七条阻塞项 B1–B7。
  承重的两条：① 起草时把钉住缺陷的单测写成「一条」，实际是**两条**——
  `test_the_mismatch_check_is_silent_for_every_other_constant`（`:198`–`:202`）在修复后**必然转红**而无人认领，
  且 `2107-1` 的 Deferred 逐字写着「两条单测（报告 + 不空转）」，起草时读漏了自己引用的那份文件；
  ② `strip_abbr` 调用点数错，而 `Decision` 的可行性正是压在那份枚举上。
  另有 B3（`module-boundaries.md:1003`–`:1008` 的现在时假陈述只追加不改准，中和不掉）、
  B4（两处 `tests/unit` 283 条的代偿控制会因新增判据而失真，却只用「只在需要时」这种条件式承诺兜着，
  违反 Anti-Slacking Rule）、B5（Phase 4 挂了一个「列出但永不勾选」的框，与执行指南第 8 条和
  Minimum Rule 12 冲突，会让 `EXECUTE`/`VERIFY` 死循环）、B6（`strip_abbr` 抛异常的退出判据无对应执行项）、
  B7（自陈「第二个交付面」= 当面写下一条 Minimum Rule 4 违规）。六条非阻塞观察一并采纳。
- 独立评审第 2 轮：**needs revision** —— 七条全部落地；剩余两条**由本次修订自己引入**：
  R1（改后的枚举仍然数错，漏了 `:147` / `:162` 这两个驱动 `plan_steps()` 的主调用点，
  正确数是 3 + 23 = 26；评审同时更正了它上一轮给我的那个错数）、
  R2（**更要紧**：B3 的执行项写成「三句全为假」，实测只有 ① 为假——
  ② 仍然为真、③ 是历史陈述，照原稿执行会往 owner doc 里**写进一条新漂移**，
  正是该项存在的目的的反面）。
- 独立评审第 3 轮：**accept** —— R1 机器复数为 3 + 13 + 10 = 26 且逐条核对无重复计数；
  R2 的三分判断逐句复核属实（含「`agenerp/seedsite.py:598`–`:609` 本 plan 一行不动」这条支撑事实）；
  Minimum Rule 12 机械自查为空，禁用词扫描的唯一命中是本 plan **否定**该措辞的那一句。
  两条 cosmetic 提示（`:894` 的字面 token 是「改准二」而非「就地改准」；一处自引行号因改写而失效）
  **已一并改掉**。

## Closure Gates

- [x] in-scope behavior is complete（15 个常量全部可被站点派生；`strip_abbr` 失败即停）
- [x] relevant docs are aligned（bug note · §12.9 · roadmap 追加行 · STATE 追加行 · `docs/logs/`）
- [x] verification has run：`python3 -m pytest tests/unit -q` · `ruff check agenerp tests/unit tests/contracts` ·
      默认判定环境与 live 环境各一次 `python3 tools/gates/check_expected_red.py` ·
      `python3 -m agenerp.seed --seed 42 --verify` · 冷起站点上的 `--load-masters` / `--load-documents` / `--verify-site`
- [x] **scoped verification is not conflated with full verification**：本仓无全量套件；
      本 plan **不跑 CI**（CI 覆盖面归 `2026-08-22-2325-2`），必须逐字写「验证范围限于本机，不含 CI」
      —— **验证范围限于本机，不含 CI。**
- [x] 变异验证（`WH_RAW` 那条）的红 / 点名 / 复原三段齐全
- [x] `tests/gates/**` 与 `.github/workflows/**` 与 `docs/masterplan/DECISIONS.md` 均 `git diff` 无输出
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— **待独立审计，执行者不自证**
- [x] closure evidence exists in files

## Deferred But Adjudicated

### `tests/unit/test_contract_surface.py` 的 `apply_pack` 台账漂移

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `1041-1` 登记该条时写死的重开事件是「下一个改动 `agenerp/pack.py::apply_pack`
  或 `tests/unit/test_contract_surface.py` 的 plan 开工时」。**本 plan 两个文件都不动，事件未触发。**
  按 Plan Decision Table 它属「test-only cleanup → No plan」，`1041-1` 已就此裁定过一次，本 plan 不重裁。
- Successor Required: `no`
- 重开事件：**不变**，仍是上面那一条。

### `LoadReport.mismatches` 修复后没有已知的活触发点

- Classification: `watch-only residual`
- Why Not Blocking Closure: 它是「站点回名 vs 本仓预期」的**通用**对账，不是为这一个常量造的；
  Phase 2 保留它并在 §12.9 写明现状，同时 Phase 1 用测试内构造的畸形 `Step` 保住覆盖。
  删掉它等于修好一个缺陷、丢掉一层保护。
- Successor Required: `no`
- 重开事件：**站点的 `autoname` 口径变化时**（届时它会重新有活触发点），
  或**有人提议删除该机制时**（届时必须先证明覆盖不减少）。

### 种子站点侧的三条断言仍无门禁形态

- Classification: `watch-only residual`
- Why Not Blocking Closure: 新建 `tests/gates/**` 在红线 1 内，只有人能做
  （`docs/backlog/gate-proposal-seed-dataset.md`，`Status: proposed`）。本 plan 不代人采纳。
- Successor Required: `no`（**人动作**）
- 重开事件：**人出具 `Gates-Change-Approved-By:` trailer 采纳提案时**。

### 工作项 7 仍卡在「从预期红名单划掉」这条 `done` 定义上

- Classification: `watch-only residual`
- Why Not Blocking Closure: 已登记的人裁定题（`docs/backlog/needs-human-expected-red-handoff.md`）。
  ⚠️ **不得把理由写成「工作项 7 没有门禁」**——它有一条 L1 门禁，只是那条门禁从未进过名单。
- Successor Required: `no`
- 重开事件：**人从那份 handoff 文档的候选处置里选定时**。

## Closure

Status Note: 四个 Phase 全部执行完毕，本机全绿。逐条自陈，**不粉饰**：

1. **结果面成立**：`agenerp/seed/model.py` 的 15 个带公司缩写后缀的常量全部满足
   `constant == " - ".join([<x>_name, ABBR])`，由 `tests/unit/test_seed_model_constants.py`
   机械判据钉住（遍历模块属性，不手抄，不经由 `strip_abbr` / `site_name_of` 求值），
   并由一次冷起活站点实跑同时证实（`--verify-site` exit 0，9 项全过，两个承重数值与 `2107-2` 逐字相同）。
2. **`strip_abbr` 已从「容忍」改成「失败即停」**，`Decision` 的三个候选、26 处调用点枚举、
   残余风险与爆炸半径记在 `docs/architecture/module-boundaries.md` **§12.11**（新增段）。
3. **`LoadReport.mismatches` 一行未动**，保留理由与「此刻无已知活触发点」的说法同写在 §12.11；
   覆盖没有因此空转（测试内构造的畸形 `Step` 保住「报告」与「不空转」两半）。
4. **两处 plan 内部的措辞冲突已就地记准，不是执行偏差**：
   ① Phase 1 第 5 项预期红 4 条 vs 同 Phase Exit Criteria 要求改写后两条「修复前后都绿」——
   按 Exit Criteria 执行，实测红 3 条，覆盖面 2 条 → 4 条**只增不减**（详见 Phase 1 实跑记录）；
   ② Phase 3 变异复原判据写的「`git diff --stat agenerp/seed/` 无输出」预设修复已提交，
   本次执行时尚未提交，改判为可判的等价形式「变异零残留」并实测（详见 Phase 3 实跑记录）。
5. **工作项 7 的状态值本 plan 一个字未改**，仍 `planned`，卡点不变。
6. **验证范围限于本机，不含 CI。** 本仓无全量套件，**这不是 full green**。

Closure Audit Evidence:

- Auditor / Agent: 待独立审计（执行者不自证）
- Evidence: 待回填 —— 可复跑的清单见 Phase 1–4 的四个「实跑记录」小节与
  `docs/logs/2026/08-22.md` / `docs/logs/2026/08-23.md`；落地 sha `dcefafa`。
