# 2026-08-21-1634-1 种子数据 · 确定性程序化生成（内置 1,010 米积压）

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 7. 种子数据（确定性生成，内置 1,010 米积压这个已知业务荒谬）
> Last Reviewed: 2026-08-21
> Source: `docs/backlog/p0-foundation-roadmap.md` Work Item Status 第 7 项（起草时 `todo`）·验收命令取自 `docs/masterplan/02-WBS.md` **P0.6** 行 ·数值取自 `docs/design/view-dsl-and-eval.md` §13.2
> Related: `2026-08-21-1022-2-tool-contract-layer-v0.md`（**判据归属的先例**：工作项的验收命令不是 `tests/gates/` 里的测试时，该 plan 如何合法关闭）·`2026-08-20-2341-3-snapshot-structured-diff.md`（本 plan 复用它交付的 `Snapshot` / `diff` 做「两次生成 diff 为空」）·`2026-08-21-1634-2-compose-healthcheck-app-services.md`（同批第 2 顺位，与本 plan 无依赖，可并行）
> Audit: required

## Current Baseline

以下每条都在 `07d684c` 上实测读出，不是转述。

**已就位：**

- `agenerp` 是仓根扁平包，零第三方依赖可导入。现有模块：`__init__.py`(9) / `apply.py`(113) / `contracts.py`(320) / `pack.py`(87) / `snapshot.py`(256) / `tools_readonly.py`(392)。
- `agenerp.snapshot` 已交付可复用的三件套：`Snapshot` / `diff(before, after) -> Diff` / `Diff.is_empty()`（`agenerp/snapshot.py:81,207,215,233`），以及 `read_scope_dir(root, scope)`（`:152`）——**目录形状的读取器已经存在**，本 plan 的产物落盘形状应当与它对齐，而不是另造一套。
- `pyproject.toml` 的 `[tool.pytest.ini_options].pythonpath = ["."]`，裸 `pytest` 与 `python3 -m pytest` 两种跑法都能 import `agenerp`。
- `[tool.ruff] line-length = 100`、`target-version = "py312"`；配置里**没有 include 列表**，只有 `exclude = ["tests/gates"]`——
  作用域由命令行参数给定（`docs/context/project-context.md` 验证命令表那行是 `ruff check agenerp tests/unit tests/contracts`）。
  ⚠️ 同时 `pyproject.toml` 的 `requires-python = ">=3.11"`，而 ruff 的 `target-version` 是 `py312`——
  **新代码若用 3.12 才有的语法，会跌破自己声明的下限**。Phase 2 有对应的自检项。
- 代码文件行数闸 `tools/check-oversized-code-files.mjs` **管不到本 plan 的产物**：
  它的 `codeExtensions` 只含 `.js/.jsx/.ts/.tsx/.mjs/.cjs`（无 `.py`），`rootPrefixes` 默认也不含 `agenerp/`。
  实跑 `node tools/check-oversized-code-files.mjs` 只报 `tools/mission-driver/**` 的 JS 文件。
  所以 500/700 行**不是本 plan 头上的既有闸**；本 plan 自愿沿用这个尺度，并在 Phase 2 用 `wc -l` 自带一条可执行检查。
- ⚠️ `node tools/check-doc-references.mjs` 在 `07d684c` 上**已经是 exit 1**（不是本 plan 引入的）：
  `ERROR: line-number citations found in active docs` → `docs/architecture/module-boundaries.md:172 [line-ref] -> docs/analysis/2026-08-19-pre-build-validation.md:143`。
  该检查器**不在 CI 的任何 job 里**（`gates.yml` 六个 job：`gates-untouched` / `expected-red-ratchet` / `gates-l1` / `masterplan-links` / `roadmap-parseable` / `loop-wiring`）。
  两个后果，Phase 1/4 都有对应条目：① 本 plan 往 `docs/architecture/**` 写字时**不得使用 `文件:行号` 形式的引用**，只按小节名引；
  ② Exit Criteria 不能写「该命令退 0」，只能写「违规集合与 `07d684c` 相同」。

**缺口：**

- `agenerp/seed.py` **不存在**（`ls agenerp/seed.py` → No such file）。
- `grep -rn "__main__" agenerp/` → **无命中**：本包此刻没有任何 CLI 入口，`python -m agenerp.seed` 这条形态是本 plan 首次引入。
- roadmap 工作项 7 是 8 项里**唯一在门禁测试列写着「尚无门禁」**的（`docs/backlog/p0-foundation-roadmap.md:47` 对照表第 7 行逐字写
  「尚无门禁——**开工前先补一条**，否则这一项没有判据」；`:72` 又重复一次）。
  （**说法要精确**：第 4 行写的是「提供 `live_site` fixture，解锁 L2 各项」，也不是一个测试文件名，但那是**有绑定判据**的，
  与第 7 行的空白不是一回事——下面「判据从哪来」一节靠的正是这个区别，别混。）
- `which python` → **exit 1，本机没有 `python`**；只有 `python3`（`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`）。
  WBS P0.6 的验收原文写的是 `python -m agenerp.seed …`，**本仓实际可执行的形态是 `python3 -m agenerp.seed …`**。
  本 plan 全程用 `python3`，这处替换在此声明，不藏在 Exit Criteria 里。

**判据从哪来（这是本 plan 最需要说清的一件事）：**

- `docs/masterplan/02-WBS.md:68` 的 P0.6 行**给了一条可执行验收**，且它不需要活站点：

  > 同种子两次生成 `diff` 为空，且断言积压场景存在：`python -m agenerp.seed --seed 42 --verify` 退 0

  前置写的是 P0.3（状态快照与 diff），该行状态已是 **done**（`02-WBS.md:65`；`:66` 是 P0.4）。
- roadmap 的「判据先行」规则**原文照抄，含它自己给的出路**（`docs/backlog/p0-foundation-roadmap.md:76`）：

  > 任何工作项**开工前**，先确认它有绑定的门禁测试。没有就先补一条红的（**补测试要人批，走 `Gates-Change-Approved-By:`**）。

  即：这条规则并没有把路堵死——它指名的满足路径是**一次人工批准的提交**。loop 不能替人走这一步，
  但可以**把提案备好、把决定摆到人面前，并且在动手写实现之前就摆过去**。
  因此本 plan 把「门禁提案 + `STATE.md` §3 登记」放在 **Phase 1**（实现之前），不是收尾时补票。
- **可以援引的先例是窄的，别把它放大**：plan `2026-08-21-1022-2` 的 Current Baseline 逐字写着工作项 4
  **是有绑定判据的**（门禁测试列写的是「提供 `live_site` fixture，解锁 L2 各项」），并明确提醒
  「对照第 7 行，它的门禁测试列才真的写着「尚无门禁 …」。**两者不是一回事，别混。**」
  所以那个先例成立的部分只有这一条，本 plan 只援引这一条：
  **当一个 plan 主动把工作项切成 A/B 两半、只交付纯逻辑那半时，它可以拿 WBS 的验收命令当自己的判据，
  前提是 ① 明说这个切分的责任在本 plan、② 把缺口登记给人、③ 工作项收尾时置 `planned` 而非 `done`。**
  三个前提在本 plan 分别落在 `## Non-Goals`、Phase 1 的登记项、Phase 4 的 `Decision`。
- ⚠️ **必须一并说清的一件事：本 plan 的验收命令没有外部裁判。**
  `missions/p0-foundation.json` 的 `commands.test` 里**没有** `python3 -m agenerp.seed --seed 42 --verify`，
  也没有 `pytest tests/contracts`——`GATE_VERIFY` 子进程复跑不到它。
  这意味着这条命令的绿**是 loop 自己给自己判的分**。`missions/**` 是角色 B 禁区（`01-EXECUTION-MODEL.md` §1 禁止项 ③），
  要把它接进 `commands.test` 只有人能做。代偿控制有两条，都在本 plan 内：
  ① Phase 2 的**变异验证**（故意破坏 → 命令必须转红），证明判据有牙齿；
  ② 独立关闭审计（fresh session 子代理）复跑该命令。工作项 4 用的也是这两条。

**业务荒谬的数值出处（逐字核对过）：**

- `docs/design/view-dsl-and-eval.md:102`：自制入库 1,000 米 + 外协收货 1,000 米 = 2,000 米，发货 990 米，成品仓结余 **1,010 米、价值 6,450 元**。
- `docs/analysis/2026-08-19-pre-build-validation.md:95`：漏掉成品仓积压 **1,010 米 / ¥6,450**；同页 **`:94`** 另给两笔逾期：应收 **¥18,612**、应付 **¥2,200**。
- `docs/backlog/implementation-roadmap.md:107`：990 米已发、**10 米为已审批合理损耗 `LOSS-00003`**，业务已完结。
- **原始出处已在冻结的证据仓里找到**（`${XM_PATH}`，红线 6 只读；起草时已读，未写入）：
  `spike/08-insight/FINDINGS.md:19` 逐字是 `Bin: XM 成品仓 - XM   actual_qty = 1010.0   stock_value = 6450.0`
  —— **两个数是同一行 Bin 读出来的实测值**，隐含单价 `6450 / 1010 = 6.3861…`。
  也就是说 `6,450` 不是算错，是移动加权均价在那个站点上滚出来的真实结果。
- ⚠️ 但**这不能直接搬进种子数据**：要让生成的数据集自然长出 `6.3861…` 这个均价，得先知道那个站点上自制与外协两批的真实单价，
  而 `FINDINGS.md` 那一行没给。Phase 1 的 `Explore` 只剩一件事：确认证据仓里**有没有**更早的、含单价的原始记录；
  查不到就写「查不到」，然后按 `Decision` 的结论处置——**不许反推一个自洽的单价再宣称那是原始事实**。

## Goals

- 交付 `agenerp/seed.py`：**确定性程序化生成**的离散制造数据集，零第三方依赖，同 `--seed` 可复现。
- 交付 `python3 -m agenerp.seed --seed 42 --verify` 这条 CLI（WBS 原文写的是 `python`，本机没有 `python`，见 Baseline），其退出码即 P0.6 的判据：
  同种子两次生成的 `diff` 为空 **且** 内置荒谬场景的断言全部成立 → 退 0；任一不成立 → 退非 0。
- 数据集内置 `docs/design/view-dsl-and-eval.md` §13.2 那个已知业务荒谬：产出 2,000 米、发货 990 米、成品仓结余 1,010 米，
  且**所有账面门禁指标都是绿的**（GL 借贷平、负库存 0、毛利与凭证差额 < ¥0.01，外加达成率 100%）——
  荒谬必须藏在「没有任何一个字段是红的」的地方，否则它不是那个测例。
- 数据集同时内置 Spike 08 那两笔**能被自由巡检找到的**异常（应收逾期 ¥18,612、应付逾期 ¥2,200）。
  它们是这个测例的对照组：`docs/analysis/2026-08-19-pre-build-validation.md:99` 那张表的全部意义就是
  「逾期在一个字段上，积压不在任何字段上」——**只有荒谬没有对照组，这个测例证明不了它想证明的事**。
- 把数据集的结构边界、数值取舍、以及「为什么这个荒谬必须账面全绿」写进 owner doc，供 P1 行业包规则与 P5 评测集引用。

## Non-Goals

- **不装载进活站点**。把数据集灌进 ERPNext 需要 `live_site`，该 fixture 在 `tests/gates/conftest.py`（红线 1），
  且 `docs/masterplan/STATE.md` §3 那行 `[open]` 的 (a)/(b)/(c)/(d) 只有人能选。本 plan 不碰。
- **不新增、不修改 `tests/gates/**` 下任何文件**，包括「给工作项 7 补一条红门禁」。本 plan 只产出**提案文本**放在红线外供人取用。
- 不做行业包规则清单、不做洞察 Agent、不做「移除规则可复现漏报」——那是 P1（`implementation-roadmap.md:109`）。
- 不引第三方依赖（faker / factory-boy / pandas 一概不用）。零依赖可导入是本包的既有约束。
- 不产出二进制、不产出图片（`docs/architecture/open-questions.md:26`：生成物须无第三方权利）。
- 不改 `missions/**`、不改 `.github/workflows/**`、不改 `docs/masterplan/` 已有行。

**这个 A/B 切分的责任在本 plan，不推给别处**：把工作项 7 切成「纯逻辑生成器」与「装载进站点 + 站点侧断言」两半，
是本 plan 自己做的决定，理由是后半被红线 1 挡着（见 `## Current Baseline`）。
因此工作项 7 收尾时置 `planned` 而非 `done`，缺口登记在 `STATE.md` §3，B 半登记在 `## Deferred But Adjudicated`。

## Task Route

- Type: `implementation-only change`（判据已由 owner doc 给死，无需求澄清）
- Owner Docs: `docs/masterplan/02-WBS.md` P0.6 ·`docs/design/view-dsl-and-eval.md` §13.2 ·`docs/backlog/implementation-roadmap.md` P0 交付表「种子数据」行 ·`docs/architecture/open-questions.md` 第 6 行
- Skill Selection Basis: `docs/skills/` **存在且有 15 份技能 + 一张 Skill Registry**（起草时已读 `docs/skills/README.md`）。
  逐条比对后：`plan-audit-prompt.md` 适用的是**对本草案的独立评审**（已在 `## Draft Review Record` 里用上），
  `closure-audit-prompt.md` 适用的是**关闭审计**（Closure Gates 里点名），二者都不是执行期的方法技能；
  `code-quality-audit-prompt.md` / `code-refactor-*` 针对既有代码，而本 plan 的产物是**净新增文件**；
  `bug-diagnosis-prompt.md` 需要一个已存在的缺陷，本 plan 没有。
  → 按 `docs/skills/README.md` 的 Skill Routing Rule 第 5 条「If no existing skill clearly fits, record `Skill: none`」，
  执行期各阶段记 `Skill: none`。**这是比对后的结论，不是「目录不存在」**。
- ⚠️ **顺带查实一处 owner-doc 漂移，而且比一处更大**：`docs/context/project-context.md` 的
  「Optional Layers Currently In Use」七个复选框**全是未勾选**，但七个目录**全部存在且非空**
  （`discussions` 2 / `audits` 4 / `testing` 3 / `skills` 16 / `analysis` 3 / `retrospectives` 2 / `lessons` 1 个文件）。
  按 plan-guide 规则 14，确认的 owner-doc 漂移**不得降级为 follow-up**——Phase 4 有一条 `Fix` 负责改正它。

## Infrastructure And Config Prereqs

- 无。本 plan 全程纯 Python 标准库，不需要 docker、不需要活站点、不需要网络、不需要任何环境变量。
- 产物落盘位置由 CLI 的 `--out` 决定，默认写进临时目录；**仓库里不落生成物**（生成物是可复现的，落盘等于把可推导的东西冻进 git）。
  该取舍是 Phase 1 的 `Decision` 之一。
- 回滚策略：本 plan 只新增文件（`agenerp/seed.py` + 单测 + 文档小节），`git revert` 即可完全撤销，无数据迁移。

## Execution Plan

### Phase 1 - 数值对账与数据集形状定稿

Status: completed
Targets: `docs/architecture/module-boundaries.md`（追加小节）·本 plan 文件
Skill: `none`

- Item Types: 逐条标注（见每条开头）。本阶段 9 条：2 条 `Proof`（其一是 Explore）、5 条 `Decision`、2 条 `Add`——
  没有任何一类占到 80%，因此**不做阶段级统一标注**（plan-guide 规则 7）。
- Prereqs: 无
- **本阶段必须先于 Phase 2 完成**：其中「门禁提案」与「`STATE.md` §3 登记」两条是 roadmap「判据先行」规则要求的动作，
  放在实现之后就等于补票。

- [x] `Proof`（Explore）**把单价查到底**，只查不判。原始出处起草时已找到（见 Baseline：证据仓
      `spike/08-insight/FINDINGS.md:19` 的 Bin 行，`actual_qty = 1010.0` / `stock_value = 6450.0`），
      本条只剩一件事：在冻结的证据仓（`evidence-repo.env` 的 `XM_PATH`，**只读，红线 6**）里确认
      **有没有更早的、含自制/外协两批单价的记录**。
      **查不到就写「查不到」**，不许反推一个自洽的单价再宣称那是原始事实。
  - Skill: `none`
- [x] **Decision：哪个数字是硬断言，哪个是派生量。**
      候选：(a) 数量 1,010 米硬断言、金额由数据集自身单价派生并如实记录（可能 ≠ 6,450）；
      (b) 金额 6,450 硬断言、反推单价（会得到 6.3861… 这种非整洁单价）；
      (c) 两者都硬断言、通过构造自制/外协两档不同单价去凑。
      **起草时的倾向是 (a)**，理由：`02-WBS.md:68` 的验收原文只说「断言积压场景存在」，没说金额；
      而 `open-questions.md:26` 说的是「1,010 米积压」这个**数量**。金额是移动加权均价的函数，
      把它钉死会让数据集为了一个二手数字扭曲成本结构。
      残余风险：P1 验收文案 `implementation-roadmap.md:109` 逐字写着「积压 1,010 米、价值 6,450 元」，
      若最终派生金额不等于 6,450，**P1 那句话就会与种子数据对不上**——这条漂移必须写进 owner doc 与 `Deferred But Adjudicated`，不许闷着。
      Explore 的结论若推翻倾向，以 Explore 为准并在此处改写。
  - Skill: `none`
- [x] **Decision：数据集的落盘形状。**
      候选：(a) 复用 `agenerp.snapshot.read_scope_dir` 的目录形状（一 scope 一目录、一 DocType 一文件）；
      (b) 单个 JSON 文件；(c) 一 DocType 一 JSONL。
      倾向 (a)，理由：P0.6 的验收要「两次生成 `diff` 为空」，而 `agenerp.snapshot.diff` 吃的正是 `Snapshot`，
      用 (a) 可以**直接复用已通过门禁的 diff 实现**，不必为验证再写第二套比较逻辑（本仓已有「别写第二个判定器」的成文教训）。
      残余风险：`read_scope_dir` 的形状是为定制包设计的，装载业务数据时字段面更宽；
      若实测发现 `SnapshotEntry` 装不下业务单据，退回 (c) 并在 owner doc 记下退回理由。
  - Skill: `none`
- [x] **Decision：确定性的来源。**
      候选：(a) 完全不用 RNG，数据集由纯构造式代码写死结构、数量由参数算出；
      (b) `random.Random(seed)` 驱动明细的抖动。
      倾向 (a) + 受控的 (b)：结构与关键数量（2,000 / 990 / 1,010 / 10）必须是构造出来的常量，
      只有「不影响任何断言的装饰性字段」（如客户名尾号、批次号序列）才允许走 `random.Random(seed)`。
      理由：`random.Random` 的 Mersenne Twister 序列在 CPython 各版本间稳定，但 `random.shuffle` / `random.sample`
      的**实现细节**历史上变过；把判据押在它上面是把确定性押在实现细节上。
      残余风险：若最终一个 RNG 都不用，`--seed` 参数就只是形式参数——**那也要如实写在 `--help` 与 owner doc 里**，
      不许让 `--seed 42` 看起来在起作用而实际不起作用。
  - Skill: `none`
- [x] `Decision`：**两笔逾期账款的数值定稿**（应收 ¥18,612、应付 ¥2,200，出处 `pre-build-validation.md:94`）。
      要定的是：这两个数是**按原值硬写**，还是**由若干张逾期单据的金额自然加总得到**。
      倾向后者：硬写一个合计数会让数据集里出现一个「没有单据支撑的余额」，那本身就是新的业务荒谬，会污染测例。
      残余风险：若拆单后合计与原值差几分钱（舍入），以**单据金额为准、合计随之改写**，并把差异记进 owner doc。
  - Skill: `none`
- [x] `Decision`：**生成物的落盘位置——仓库里落不落。**
      候选：(a) 只写 `--out` 指定的目录，默认临时目录，仓库里不落任何生成物；
      (b) 把一份生成物提交进仓库当基准，`--verify` 与它比对。
      **选 (a)**。理由：生成物是可复现的，落盘等于把可推导的东西冻进 git，且每次改生成器都要重跑一次「更新基准」的仪式；
      而 P0.6 的验收原文是「同种子两次生成 `diff` 为空」——它比的是两次**当场**生成，本来就不需要仓内基准。
      残余风险：没有仓内基准，跨版本/跨机器的确定性回归**不会被 CI 自动发现**（只有同一次运行内的两次生成被比过）。
      该残余风险写进 owner doc；若日后需要跨机器基准，由后继 plan 引入，不在本 plan 内。
  - Skill: `none`
- [x] `Add`：**把门禁提案写在红线外**——新建 `docs/backlog/gate-proposal-seed-dataset.md`，
      内容是「若要给工作项 7 补一条门禁测试，它该断言什么、放在哪个文件、为什么它必须是 L2（因为要断言荒谬**在站点上**存在）」，
      并附上人若采纳时需要的提交 trailer 形态 `Gates-Change-Approved-By:`。
      **这是提案文本，不是测试代码**；本 plan 不在 `tests/gates/` 下创建任何文件。
  - Skill: `none`
- [x] `Add`：**按「拿不准就写进 needs-human 队列」往 `STATE.md` §3 追加一行**，登记「工作项 7 没有绑定门禁」这个判据缺口，
      写清：触发条件、最后一条命令原文与退出码、sha、以及**人可选的处置项**
      （(a) 采纳 `docs/backlog/gate-proposal-seed-dataset.md` 并带 trailer 提交那条 L2 红门禁；
      (b) 裁定 WBS P0.6 的验收命令即本项判据、把 roadmap 对照表第 7 行改成指向该命令；
      (c) 维持现状——代价是工作项 7 永远停在 `planned`）。**只追加，不改写任何已有行。**
      ⚠️ **授权链有争议，照实写进那一行，不擅自消解**：`01-EXECUTION-MODEL.md` §1 的表说角色 B「不得手写 STATE」，
      而执行器人格 `tools/mission-driver/agents/build.claude.md:16` 逐字指示「拿不准就停下来写进 `STATE.md` 的 needs-human 队列，等人」；
      `STATE.md` §3 现存那行 `[open]` 已经把同一处矛盾摆出来过。本条照它的做法办。
  - Skill: `none`
- [x] `Proof`（本阶段）：上述结论写进 `docs/architecture/module-boundaries.md` **新增顶级小节
      「§12 种子数据集在本仓的落点」**（§11 是「定制包与 GitOps」，种子数据集不是定制包，塞进 §11.x 会错位），
      含：单价对账结果、落盘形状、确定性来源、两笔逾期的构造方式、以及**已知漂移**清单。
      ⚠️ **写进 `docs/architecture/**` 的文字一律不得使用 `文件:行号` 形式的引用**（`check-doc-references.mjs` 的 line-ref 规则），
      只按小节名 / 锚点引。
  - Skill: `none`

Exit Criteria:

- [x] 五条 Decision 全部有结论、有备选、有残余风险，且写进 `module-boundaries.md` §12（不是只写在本 plan 里）
- [x] 单价对账结果落纸：证据仓里「有更早的含单价记录」还是「查不到」——二选一，不许含糊
- [x] `docs/backlog/gate-proposal-seed-dataset.md` 存在
- [x] `STATE.md` §3 新增一行，且 `git diff --numstat docs/masterplan/STATE.md` 第二列为 **0**（只增不删）
- [x] `node tools/check-doc-references.mjs` 的违规集合与 `07d684c` 相同（逐行对照，**本阶段不得引入新的 line-ref 违规**）
- [x] `docs/logs/2026/08-21.md`（或执行当日文件）追加本阶段条目

### Phase 2 - 生成器与 CLI

Status: completed
Targets: `agenerp/seed.py`
Skill: `none`

- Item Types: `Add`-heavy（5/6 条 Add）
- Prereqs: Phase 1（形状与数值定稿后才动手，否则要返工）

- [x] `agenerp/seed.py`：数据集的**结构定义**——离散制造最小闭环。
      至少覆盖：物料（成品「布」以米计 + 原料）、仓库（成品仓 / 原料仓）、BOM、工单（自制入库 1,000 米）、
      采购/外协收货（1,000 米）、销售订单、发货单（990 米）、库存分录，
      以及 `LOSS-00003` 那 10 米**已审批合理损耗**（`implementation-roadmap.md:107` 的「990 米之谜」靠它成立）。
      单文件若逼近 500 行就拆成 `agenerp/seed/` 包，**不许为了不拆而压缩可读性**。
      （500 行是本 plan 自愿沿用的尺度，不是既有闸——`check-oversized-code-files.mjs` 不看 `.py`，见 Baseline。
      Exit Criteria 里用 `wc -l agenerp/seed*.py` 或 `wc -l agenerp/seed/*.py` 自带一条可执行检查。）
  - Skill: `none`
- [x] 生成函数：`generate(seed: int) -> <Phase 1 定的形状>`，纯函数，无 IO、无时钟、无环境读取。
      **禁止任何 `datetime.now()` / `time.time()` / `os.environ` 出现在生成路径上**——它们是确定性的头号杀手。
      单据日期一律由 `seed` 与固定基准日推出。
  - Skill: `none`
- [x] 落盘函数：把生成结果写进 `--out` 目录，字节级确定（JSON `sort_keys=True`、固定 `indent`、固定换行、UTF-8 无 BOM）。
  - Skill: `none`
- [x] 场景断言函数：`verify(dataset) -> list[str]`，返回**失败原因列表**（空列表 = 全过）。至少含：
      入库合计 2,000 米 · 发货 990 米 · 成品仓结余 1,010 米 · `LOSS-00003` 存在且为 10 米且状态为已审批 ·
      应收逾期合计与应付逾期合计等于 Phase 1 定稿的数值 ·
      **以及「账面全绿」那一组**：GL 借贷差额为 0、负库存条目数为 0、**毛利与凭证差额 < ¥0.01**
      （这三条是 `view-dsl-and-eval.md:104` 逐字列的那三个 ✅），外加销售订单达成率 100%
      （这一条出自 `pre-build-validation.md:95`，是 Spike 08 里 Agent 判「正常」的依据）。
      最后这一组是这个测例的**要害**——它证明荒谬藏在没有任何字段发红的地方。
  - Skill: `none`
- [x] CLI：`python -m agenerp.seed`，参数 `--seed N`（默认 42）、`--out DIR`、`--verify`。
      `--verify` 的语义定死为：**生成两次 → 求 diff → diff 非空即失败；再跑 `verify()` → 有失败原因即失败**；
      两者都过退 0，任一不过把原因逐条打到 stderr 并退 1。
      不带 `--verify` 时只生成、只落盘、退 0。
  - Skill: `none`
- [x] `ruff check agenerp` 通过（line-length 100）。
      并自检**不使用 3.12 才有的语法**——`pyproject.toml` 声明的下限是 `requires-python >= 3.11`，
      ruff 的 `target-version = "py312"` 不会替你守住这条线。
  - Skill: `none`

Exit Criteria:

- [x] `python3 -m agenerp.seed --seed 42 --verify` → **exit 0**（命令原文与退出码抄进 `docs/logs/`。
      注意 WBS 原文写的是 `python`，本机没有 `python`，见 Baseline）
- [x] 故意破坏一条断言（改常量后跑、跑完还原、`git diff` 确认字节一致）→ 该命令 **exit 1** 且 stderr 指名道姓说出是哪条断言。
      **不做这步就等于不知道判据有没有牙齿**——本仓在 `2026-08-21-1022-1` 已用变异验证立过这个规矩
- [x] `ruff check agenerp` → exit 0
- [x] `wc -l agenerp/seed*.py`（或拆包后的 `agenerp/seed/*.py`）每个文件 < 500 行，输出抄进 `docs/logs/`
- [x] `docs/logs/` 追加本阶段条目

### Phase 3 - 单测覆盖（判据的第二只脚）

Status: completed
Targets: `tests/unit/test_seed_deterministic.py`
Skill: `none`

- Item Types: `Proof`-heavy（全部 Proof）
- Prereqs: Phase 2

- [x] 确定性：`generate(42)` 连跑两次结果相等；落盘两次**字节相同**（不只是对象相等——序列化层也可能引入不确定性）。
  - Skill: `none`
- [x] 种子敏感性：若 Phase 1 定稿保留了受控 RNG，则 `generate(42) != generate(43)`；
      若定稿是「一个 RNG 都不用」，则改为断言 `generate(42) == generate(43)` **并在测试里写明这是有意为之**，
      同时断言 `--help` 文本如实说明 `--seed` 不影响产物。二选一，由 Phase 1 的结论决定，不许两边都不写。
  - Skill: `none`
- [x] 场景断言：逐条覆盖 `verify()` 的每一项（2,000 / 990 / 1,010 / `LOSS-00003` 10 米 / 逾期两笔 / 账面三绿）。
  - Skill: `none`
- [x] 负例：构造一个被篡改的数据集，断言 `verify()` 返回**非空**且原因文案能定位到具体哪条。
  - Skill: `none`
- [x] 纯净性：扫描**生成器的全部源码文件**（用 `Path("agenerp").glob("seed*.py")` 与 `agenerp/seed/*.py` 两者的并集，
      而不是写死 `agenerp/seed.py`——Phase 2 允许拆包，写死路径会在拆包后静默扫了个空、假绿），
      断言其中不出现 `datetime.now` / `time.time` / `os.environ` / `random.random(`。
      并断言**至少扫到 1 个文件**（否则「扫描无违规」是空真）。
      这是把「确定性」从口头承诺变成可执行断言的唯一便宜办法。
  - Skill: `none`

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` → **exit 0**（全量 unit，不只是新增文件）
- [x] `python3 tools/gates/check_expected_red.py` → **exit 0**（本 plan 不该让任何门禁变色；若变色说明踩到了别处）
- [x] `ruff check agenerp tests/unit tests/contracts` → exit 0
- [x] `docs/logs/` 追加本阶段条目

### Phase 4 - roadmap 写回、owner-doc 漂移修正与收尾

Status: completed
Targets: `docs/architecture/module-boundaries.md` ·`docs/backlog/p0-foundation-roadmap.md` ·`docs/context/project-context.md` ·`docs/logs/`
（`docs/masterplan/STATE.md` §3 与 `docs/backlog/gate-proposal-seed-dataset.md` 归 **Phase 1**，本阶段不再写；若引擎在本阶段追加 `STATE.md` §2 会话日志行，同样**只增不删**）
Skill: `none`

- Item Types: `Decision | Add | Fix`
- Prereqs: Phase 3（门禁提案与 `STATE.md` §3 登记已在 **Phase 1** 完成，本阶段不重复）

- [x] **Fix：改正 `docs/context/project-context.md` 的 Optional Layers 漂移。**
      七个复选框全未勾选，而七个目录全部存在且非空（起草时实测，见 Task Route 的注）。
      按 plan-guide 规则 14，这是**确认的 owner-doc 漂移**，不得降级为 follow-up。
      勾上实际在维护的那些，并在该节下补一行说明「本仓七个可选层均在用」。
  - Skill: `none`
- [x] **Decision：roadmap 工作项 7 的状态怎么写。**
      roadmap 自己给 `done` 的定义是「完成，且通过 closure 审计（**对应门禁测试已转绿并从预期红名单划掉**）」——
      工作项 7 没有门禁测试，这个定义**在字面上不可满足**。
      候选：(a) 关闭时写 `planned` + 上面那条 needs-human；(b) 写 `done` 并自行放宽 `done` 的定义；
      (c) 留 `todo` 假装没做。
      **选 (a)**。理由：(b) 等于 loop 自己改判据的定义，属放松裁判；(c) 是谎报。
      残余风险：工作项 7 会停在 `planned` 直到人处置，引擎因此不会再选它——**这正是想要的结果**，
      未完成的那部分（装载进站点 + 站点侧断言）本来就被红线 1 挡着。
      落点：本 plan 自带幂等写入（工作项 4/5 的先例已证明没有任何引擎产物会替你写这一步：
      `closure-audit.md` 里 `roadmap` 出现 0 次，`plan-review.md` 只改 plan 自己的 `Plan Status`）。
      顺带把 roadmap 对照表第 7 行「尚无门禁」那格改成指向本 plan 交付的验收命令 + 指向
      `docs/backlog/gate-proposal-seed-dataset.md`，**但不删「尚无门禁」这个事实**——那格要同时说清「仍然没有门禁」。
  - Skill: `none`
- [x] Add：`docs/context/project-context.md` 的验证命令表追加 `python3 -m agenerp.seed --seed 42 --verify` 一行，
      并**如实注明它不在 `missions/p0-foundation.json` 的 `commands.test` 里**（`missions/**` 是角色 B 禁区，要补由人做）——
      与工作项 4 的 `tests/contracts` 那一行同样的处理，理由相同。
  - Skill: `none`
- [x] Add：`docs/logs/` 当日文件写入本 plan 的聚合条目：四个阶段、每条命令原文 + 退出码 + 收尾 sha。
  - Skill: `none`

Exit Criteria:

- [x] `git diff --name-only` 对 `tests/gates/`、`.github/workflows/`、`missions/` **零命中**（执行时逐字跑一遍并抄下输出）
- [x] roadmap 工作项 7 由 `todo` → `planned`；对照表第 7 行已更新且**仍如实写着「尚无门禁」**
- [x] `docs/context/project-context.md`：验证命令表已加 `python3 -m agenerp.seed --seed 42 --verify` 一行（含「不在 `commands.test` 里」的注），
      且 Optional Layers 漂移已改正
- [x] `docs/logs/` 已更新
- [x] `bash tools/check-masterplan-links.sh` → exit 0
- [x] `node tools/check-doc-references.mjs` 的**违规集合与 `07d684c` 相同**（该命令在起草时已是 exit 1，见 Baseline；
      本 plan 不负责修那处存量违规，但**一条新的都不许加**）

## Draft Review Record

- Independent draft review iteration 1: `needs revision` → 已就地修订为 `accept`（mission-driver `2026-08-21-171157` review 步骤，独立于起草会话）。
  复核方式：逐条实跑核对 Current Baseline 的可验证断言，而非通读。实跑并核准的有：
  `node tools/check-doc-references.mjs` → exit 1 且违规集合只有 `module-boundaries.md` 那一条（与 Baseline 一致）；
  该检查器的 active 作用域实为 `docs/architecture,docs/design,docs/references`（`activeDocRoots` 默认值）——
  **`docs/plans/**` 不在内**，所以本 plan 自身满篇的 `文件:行号` 引用不会污染 Phase 1/4 的「违规集合不变」判据，该 Exit Criteria 成立；
  `tools/check-oversized-code-files.mjs` 的 `codeExtensions` 确无 `.py`（`rootPrefixes` 含 `tests/` 但扩展名闸在前），
  故 500 行确系本 plan 自愿尺度；`python3 tools/gates/check_expected_red.py` → exit 0；
  `02-WBS.md` P0.6 行、P0.3 已 `done`、roadmap 对照表第 7 行「尚无门禁」、`project-context.md` Optional Layers 七个复选框全未勾、
  `agenerp/snapshot.py` 的 `Snapshot`/`diff`/`is_empty`/`read_scope_dir`、`agenerp/seed.py` 不存在——逐条属实。
  修订内容（三处，均为完整性/一致性缺陷，非方向问题）：
  ① Phase 1 的 Exit Criteria 写「五条 Decision」而执行清单只有四条，且 `## Infrastructure And Config Prereqs`
  把「仓库里不落生成物」称作「Phase 1 的 `Decision` 之一」却没有对应条目——**补上该 `Decision` 条目**（含备选与残余风险），
  两处于是自洽；② Phase 1 的 `Item Types` 计数（7 条 / 1 条 Proof）与实际条目数对不上，改为 9 条 / 2 Proof / 5 Decision / 2 Add；
  ③ Phase 4 的 `Targets` 列着 `STATE.md`，而其 `Prereqs` 明说 STATE 登记归 Phase 1，本阶段无对应条目——改为注明归属。
  另把 `## Goals` 里残留的 `python -m …` 对齐为 `python3 -m …`（全篇其余处已是 `python3`）。
- 判定：可执行合同成立，`Plan Status` 置 `active`。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`module-boundaries.md` §12 ·`project-context.md` ·roadmap ·`STATE.md` §3）
- [x] verification has run：`python3 -m agenerp.seed --seed 42 --verify` ·`python3 -m pytest tests/unit -q` ·`python3 tools/gates/check_expected_red.py` ·`ruff check agenerp tests/unit tests/contracts` ·`bash tools/check-masterplan-links.sh` ·`node tools/check-doc-references.mjs`（**后者以「违规集合不变」为准，不以退 0 为准**）
- [x] **verification scope limited 已显式声明**，两层都要写明：
      ① 上列命令是本仓此刻可跑的全部（无 build、无 typecheck、L2 门禁未解锁），不得报为「全量验证通过」；
      ② **核心验收命令不在 `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它**，
      代偿控制是变异验证 + 独立关闭审计复跑（见 Baseline）
- [x] 判据有牙齿：变异验证做过（故意破坏 → 命令转红 → 还原 → `git diff` 字节一致）
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent（独立子代理，fresh session，不带实现上下文）
- [x] closure evidence exists in files
- [x] `git diff --name-only` 对 `tests/gates/**`、`.github/workflows/**`、`missions/**` 全部零命中

## Deferred But Adjudicated

### 把数据集装载进活站点 + 站点侧的荒谬断言（工作项 7 的 B 半）

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 需要 `live_site`，该 fixture 在 `tests/gates/conftest.py`（红线 1），
  且 `STATE.md` §3 那行 `[open]` 的四个处置项只有人能选。本 plan 关闭时工作项 7 置 `planned`（不是 `done`），
  不存在「把没做完的活报成 done」。
- Successor Required: `yes` —— 工作项 7 的第二个 plan（roadmap 规则允许一个工作项 1–2 个 plan）
- 重开事件：人对 `STATE.md` §3 的 (a)/(b)/(c)/(d) 作出选择之后

### 给工作项 7 补一条门禁测试

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 新建 `tests/gates/` 下的文件在红线 1 内，loop 不得为之；
  本 plan 已在 **Phase 1（实现之前）** 把提案写在红线外（`docs/backlog/gate-proposal-seed-dataset.md`）并登记进 `STATE.md` §3，
  符合 roadmap「判据先行」规则自己指名的那条路径——只是最后一步（带 trailer 的提交）只有人能走。
- Successor Required: `yes`（**人动作**：带 `Gates-Change-Approved-By:` trailer 的提交）
- 重开事件：人采纳提案时

### ~~¥6,450 与 1,010 米单价对不上的数值漂移~~ —— 已对账关闭，漂移不存在

- Classification: `resolved during execution`（起草时登记为 `watch-only residual`）
- **执行期结论（以 Phase 1 的 Explore 为准，推翻了 Current Baseline 的推测）**：
  在冻结的证据仓里**查到了更早的、含单价的原始记录**（`xm_pattern_demo/demo/business_flow.py` 的 `DEMO` 常量表
  与 `xm_pattern_demo/demo/bootstrap.py` 的工位 `operating_cost`）。两个数**对得上**：
  自制批 1,000 米 @ ¥5.00（原料 120 Kg × ¥35 + 工序 600 分钟 × ¥80/小时）、
  外协批 1,000 米 @ ¥6.40（原料 ¥4,200 + 服务费 ¥2,200），**FIFO** 发货 990 米全部出自制批 →
  结余 10 × 5.00 + 1,000 × 6.40 = **¥6,450**、数量 **1,010 米**。
  ⚠️ **Current Baseline 里「6,450 是移动加权均价滚出来的真实结果」那句话是错的**：
  均价口径应得 ¥5,757。原文保留不改（起草时读到什么就是什么），更正记在此处与 `module-boundaries.md` §12.1。
  该对照已写成可执行断言（`tests/unit/test_seed_deterministic.py::test_backlog_value_is_fifo_layered_not_moving_average`）。
- Why Not Blocking Closure: 已关闭，本就不阻塞。
- Successor Required: `no`
- **残留的 watch-only 部分（缩窄后）**：站点的存货计价方法（FIFO）是**从两个实测数反推出来的**，
  证据仓里没有一行直接写着 `valuation_method`；且 P1 的验收文案只引结果不引成本构成，仍可能被再次读成「均价 6.39」。
  重开事件：P1 写行业包规则、需要报出「价值 X 元」时。

### 行业包规则与「移除规则可复现漏报」

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: `implementation-roadmap.md:109` 明确划给 P1；P0 阶段不引入任何 LLM。
- Successor Required: `no`（属 P1 mission）
- 重开事件：P1 开工时

## Closure

Status Note: 四个阶段全部执行完毕并逐条打勾，`Plan Status: completed`。
**独立关闭审计尚未跑**——`## Closure Gates` 里「closure audit was independent」一框**如实留空**，
它归 mission-driver 的 `CLOSURE_VERIFY` 步（fresh session 子代理，不带实现上下文），不由执行会话自封。

**交付物**：`agenerp/seed/`（10 个模块，最大 300 行）· `tests/unit/test_seed_deterministic.py`（31 条）·
`docs/architecture/module-boundaries.md` §12 · `docs/backlog/gate-proposal-seed-dataset.md` ·
`docs/masterplan/STATE.md` needs-human 新增一行 · `docs/context/project-context.md` 两处 ·
`docs/backlog/p0-foundation-roadmap.md` 工作项 7 → `planned`。

**验证（命令原文 + 退出码，收尾时现跑）**：

| 命令 | 退出码 |
|---|---|
| `python3 -m agenerp.seed --seed 42 --verify` | **0** |
| `python3 -m pytest tests/unit -q` | **0**（104 passed） |
| `python3 tools/gates/check_expected_red.py` | **0**（预期红 7，绿 6，跳过 0） |
| `ruff check agenerp tests/unit tests/contracts` | **0** |
| `bash tools/check-masterplan-links.sh` | **0** |
| `node tools/check-doc-references.mjs` | **1**，违规集合与基线**逐行相同**（判据是集合不变，不是退 0） |

⚠️ **verification scope limited，两层**：① 上列即本仓此刻可跑的全部（无 build、无 typecheck，L2 未解锁），
**不是「全量验证通过」**；② **核心验收命令不在 `missions/p0-foundation.json` 的 `commands.test` 里，
`GATE_VERIFY` 复跑不到它**，代偿是变异验证 + 独立关闭审计。

**判据有牙齿（变异验证，5 条全部转红且指名道姓）**：`DELIVERY_QTY 990→980`（报 7 条）·
`APPROVED_LOSS_QTY 10→12`（2 条）· `SUBCONTRACT_FEE 2200→2500`（2 条）· `SALES_RATE 18.8→19.0`（2 条）·
`LOSS_REVIEW_STATUS Approved→Pending Approval`（1 条）。
还原后 `agenerp/seed/**` 摘要与变异前一致（`6b48864b…`）。
⚠️ **两处与 plan 原文的偏差，如实记下**：① `agenerp/seed/**` 是本轮新增、尚未入库，`git diff` 对未跟踪文件为空，
**不能用它当还原证据**，改用 `shasum` 摘要比对；② 首轮变异的第 2、3 条结果因 `__pycache__` 复用旧字节码而作废，
已清缓存 + `python3 -B` 重跑，日志里记了这个坑。

**红线自查**：`git diff --name-only -- tests/gates/ .github/workflows/ missions/` → 输出为空；
`git status --porcelain -- tests/gates/ .github/workflows/ missions/ tools/gates/ docs/masterplan/DECISIONS.md`
→ 输出同样为空（`git diff` 看不见未跟踪文件，故两条都跑）。
`git diff --numstat docs/masterplan/STATE.md` → `5	0`，只增不删。

Closure Audit Evidence:

- Auditor / Agent: <pending —— 归 `CLOSURE_VERIFY` 步的独立子代理>
- Evidence: <pending>

Follow-up:

- **等人处置** `docs/masterplan/STATE.md` needs-human 队列里新增那行 `[open]` 的 (a)/(b)/(c)。
  在那之前工作项 7 停在 `planned`，B 半不开工。
- **执行期发现的一处 plan 文本缺陷（已就地修复，记此备查）**：本 plan 的 `## Task Route` 正文里
  出现了字符串 `## Draft Review Record`，用它当锚点做区间编辑会命中正文而非小节标题。
  收尾时因此一度把 Phase 1–3 的区间重复写入（文件由 443 行涨到 1,024 行），已按「四份副本逐字相同」核验后去重还原至 443 行，
  再改用 `\n## Draft Review Record\n` 作锚点。**对后继 plan 的教训**：区间编辑的锚点要带换行边界。
