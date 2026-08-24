# 01 `ACC_OPERATING` 少一个空格，在活站点上永远命不中

> Status: **fixed（2026-08-23）** —— 由 plan
> [`2026-08-22-2325-1`](../plans/p0-foundation/2026-08-22-2325-1-acc-operating-constant-fix.md) 修复，
> 落地 sha `bbd25ae`。修法见下面 `## Fix` 的 2026-08-23 追加段，回归覆盖见 `## Tests`。
>
> **原状态原文保留，它是当时的裁定证据**：`open（登记不修）` —— 修改落点在 `agenerp/seed/model.py`，
> 而发现它的 plan `2026-08-22-2107-1` 的 Closure Gate 逐字要求「`agenerp/seed/**` 一个字节未改」。
> 重开事件写在该 plan 的 `## Deferred But Adjudicated`：第二个 plan（`2026-08-22-2107-2`）的站点侧对账。

## Problem

- `agenerp/seed/model.py:60` 逐字 `ACC_OPERATING = "生产费用（计入估值）- XM"` —— **`- XM` 前少一个空格**。
  同文件其余 10 个 `ACC_*` 常量全部是 ` - XM`（实测 `endswith(" - XM")` 唯独这一个为 `False`）。
- ERPNext v15 的 `Account.autoname` 走 `" - ".join([account_name, abbr])`，**只可能产出 `生产费用（计入估值） - XM`**。
- 因此这个常量**在任何活站点上都不会等于任何一条科目的 `name`**。
- 影响：A 半（纯内存数据集）不受影响——`ledger.py` 的 GL 分录只是把这个字符串当标签用，自洽。
  受影响的是 **B 半的站点侧对账**：任何「按 `ACC_OPERATING` 去站点查这条科目」的代码都会查空，
  而查空最容易被读成「这条科目没建」而不是「常量拼错了」。**血径 = 工作项 7 的站点侧断言。**

## Reproduction

- 前置：活站点 `frontend`（`AGENERP_HTTP_PORT=18080 docker compose up -d --wait`），
  站点上已有公司 `XM 演示纺织有限公司`（`abbr = XM`）。
- 纯本机一行即可看见常量侧：

  ```
  python3 -c "from agenerp.seed.model import ACC_OPERATING as a; print(repr(a), a.endswith(' - XM'))"
  # '生产费用（计入估值）- XM' False
  ```

- 站点侧（2026-08-22 实测）：`POST /api/resource/Account`，载荷
  `{"account_name":"生产费用（计入估值）","company":"XM 演示纺织有限公司","parent_account":"Stock Expenses - XM","root_type":"Expense","account_type":"Expenses Included In Valuation","is_group":0}`
  → 200，`data.name = '生产费用（计入估值） - XM'`（**有空格**）。

## Diagnostic Method

诊断是**直接的**，不需要迭代，原因写清楚：装载器要把 `model.py` 的 11 个科目常量反推成
`account_name`（站点不采纳显式 `name`，见 plan `2026-08-22-2107-1` 的 E3），
反推规则只能是「去掉尾部的公司缩写后缀」。写这条规则时对 11 个常量做了一次机械核对
（`endswith(" - XM")`），**唯一的 `False` 当场暴露**。

排除过的另一条解释：「是不是 ERPNext 在某些情况下不加空格」——用真载荷在活站点上建了一次，
回的是带空格的名字，**该解释被实测否掉**，不是靠读源码推的。

## Root Cause

- 单点：`agenerp/seed/model.py:60` 的字面量少一个空格。是一个**书写错误**，不是设计取舍。
- 之所以能活到今天没被发现：`agenerp.seed` 的 31 条单测与 `tests/gates/test_seed_dataset_absurdity.py`
  的 6 条**全部在纯内存数据集上判**，一条都不打站点。常量只要**自洽**就够，
  它跟 ERPNext 的派生规则**对不上**这件事在纯内存世界里不可观测。

## Fix

**本次不修。** 修法是显然的（补一个空格），但落点在 `agenerp/seed/**`，
被发现它的 plan 的 Closure Gate 逐字挡住。本次交付的是**不让它静默**：

- `agenerp/seedsite.py` 的装载器在建完每一条科目后，**把站点实际回的 `name` 与 `model.py` 的常量比对**，
  不一致就打印一行 `⚠️ 科目名与 model.py 常量不符` 并列出两边的原文。
- 装载器**不因此退非 0**：科目本身建成功了，这不是装载失败；把它判成失败会让一条正确的装载被一处拼写错误挡死。
  该取舍写在这里，不藏。

### 2026-08-23 追加：**已修**（plan `2026-08-22-2325-1`，落地 sha `bbd25ae`）

上面「本次不修」那一段**一个字不删**——它是 `2107-1` 当时的真实裁定。以下是后继 plan 实际做的三件事：

1. **常量本身**：`agenerp/seed/model.py:60` 补上那个空格 —— `生产费用（计入估值） - XM`。
   **同一行不做任何别的改动**，`git diff agenerp/seed/` 的增删行恰好只有这一对。
2. **`strip_abbr` 从「容忍」改成「失败即停」**（`agenerp/seedsite.py`）：
   收到不以 ` - XM` 结尾的串时 `raise ValueError`，异常信息含**那个串本身**、
   所要求的形状 `<name> - XM`、以及机械判据的路径。三个候选与残余风险记在
   `docs/architecture/module-boundaries.md` **§12.11**。
   **不选「原样返回」**：那个串会被 `site_name_of` 再拼一次后缀，在站点上真建出 `X - XM - XM`
   —— 正是本文件 `## Notes For Future Refactors` 第二条预告过的那种坏。
3. **告警机制保留，一行未动**：`LoadReport.mismatches` 及其 `⚠️` 告警行仍在，
   它是「站点回名 vs 本仓预期」的**通用**对账，不是为这一个常量造的（理由见 §12.11）。
   自本次修复起它**没有已知的活触发点**。

**活站点实证**（从 `docker compose down -v` 冷起的空站点，本机 18080）：
`--load-masters` → exit 0 `合计：新建 40 / 已存在 0` 且**输出里 `⚠️` 零命中**（`2107-1` 实测打印过它）·
`--load-documents` → exit 0 `合计：新建 17 / 已存在 0 / 提交 11`，原样第二跑 `新建 0 / 已存在 17 / 提交 0` ·
`--verify-site` → exit 0，9 项全过，`actual_qty = 1010.00` / `stock_value = 6450.00`
**与 `2107-2` 的记录逐字相同**（修常量没有改变任何一个数）。

## Tests

- `tests/unit/test_seedsite_loader.py::test_account_name_mismatch_is_reported_not_swallowed`（unit）——
  用 FakeTransport 让站点回一个与常量不同的 `name`，断言装载结果里出现该条不一致记录。
  这条测试**保护的是「不静默」这个行为**，不是保护常量本身。
- 常量本身**没有回归覆盖**（补了空格之后才谈得上）。照实记。

### 2026-08-23 追加：**怎么防止它回来**

上面那句「常量本身没有回归覆盖」**已经不成立**，由 plan `2026-08-22-2325-1` 补上：

- **`tests/unit/test_seed_model_constants.py`**（净新增，3 条）—— 本文件所说的那条机械判据。
  `test_every_suffixed_constant_can_be_derived_by_the_site_autoname` 对 `model.py` 里
  **全部** `ACC_*` / `WH_*` 常量断言 `constant == " - ".join([<x>_name, ABBR])`。
  三处设计要点，缺一条它就会退化成摆设：
  ① **遍历模块属性取清单，不手抄** —— 第 16 个常量加进来时判据自己长；
  ② **不经由 `strip_abbr` / `site_name_of` 求值** —— 拿容忍它的那段代码给它开证明，判据会空转；
  ③ **失败信息指名常量与实际值**，另有 `test_the_constant_sweep_actually_finds_something`
  钉住「遍历不许扫到空集」（扫到空集时上面那条会真空通过）。
  第三条 `test_the_company_abbr_in_the_constants_is_bound_to_seedsite_abbr` 把
  `seedsite.ABBR` 与常量里字面的 `XM` 绑在一起，改公司缩写时不会集体失配而无人告知。
- **变异验证证明它有牙齿**（不是「写了就算」）：把 `M.WH_RAW` 故意改成缺空格 →
  `python3 -m pytest tests/unit -q` **exit 1**，逐字点名
  `AssertionError: WH_RAW = 'XM 原料仓- XM' 不以 ' - XM' 结尾…`；复原后回 exit 0。
  **刻意不拿 `ACC_OPERATING` 做变异对象**：它是刚修好的那一个，拿它变异只证明判据认得这一个常量，
  证不出「遍历」真的在遍历。
- **`tests/unit/test_seedsite_loader.py::test_strip_abbr_refuses_a_name_the_site_could_never_derive`**
  钉住上面 `## Fix` 第 2 条那个 `Decision`：畸形输入必须抛，且异常信息含常量与所需形状。
- **`…::test_the_real_master_data_plan_reports_no_mismatch_at_all`** 钉住「产品数据此刻确实干净」，
  它是活站点上那条「`⚠️` 告警行消失」的单测级同构。
- 原有两条告警覆盖是**改写而非删除**：输入换成测试内构造的畸形 `Step`，
  不再依赖 `M.ACC_OPERATING` 是坏的，修复前后都绿。**覆盖面 2 条 → 4 条。**

## Affected Artifacts

- `agenerp/seed/model.py:60` —— 缺陷所在，**本次未改**。
  **2026-08-23 追加**：已由 plan `2026-08-22-2325-1` 改准为 `生产费用（计入估值） - XM`。
- `agenerp/seedsite.py` —— 比对与告警的落点。
  **2026-08-23 追加**：`strip_abbr` 在同一个 plan 里由「容忍」改成「失败即停」；
  `LoadReport.mismatches` 一行未动。
- **2026-08-23 追加** `tests/unit/test_seed_model_constants.py` —— 机械判据的落点（净新增）。
- **2026-08-23 追加** `docs/architecture/module-boundaries.md` §12.11 —— `Decision` 与残余风险的落点。
- `docs/plans/p0-foundation/2026-08-22-2107-1-seed-site-write-surface-and-masters.md` ——
  `## Deferred But Adjudicated` 里登记了重开事件。

## Notes For Future Refactors

- 修这个常量**会连带改动 `ledger.py` 生成的 GL 分录里的科目字符串**，
  而 `tests/gates/test_seed_dataset_absurdity.py` 与 `agenerp/seed/checks.py` 判的是**金额**不是科目名，
  所以补空格**大概率不会让任何一条现有测试转红**——这恰恰是危险处：**没有测试会替你确认你改对了**。
  修的时候要连带补一条「11 个 `ACC_*` 常量必须都能由 `" - ".join([account_name, abbr])` 产出」的单测。
- 装载器里那个「去掉尾部公司缩写」的反推规则，如果将来有人把它改成严格 `removesuffix(" - XM")`，
  `ACC_OPERATING` 会**整串原样**当成 `account_name` 送进站点，建出
  `生产费用（计入估值）- XM - XM` 这种名字。反推规则必须同时容忍两种写法，或者等常量修好后再收紧。
  **2026-08-23 追加**：走的是后一条路——常量已修好，`strip_abbr` 随之收紧成失败即停
  （plan `2026-08-22-2325-1`，`Decision` 见 §12.11）。这条 note 已被消费，保留原文作为当时的预判证据。

## Prevention Gap

- 数值常量有对账（§12.1/§12.2），**名字常量没有**：没有任何一步检查过
  `model.py` 里那些「看起来像 ERPNext 派生名」的字符串**真的能被 ERPNext 派生出来**。
  在站点侧对账落地之前，这一类拼写错误只能靠人眼。

**2026-08-23 追加：这个缺口已经补上，但补的范围要说准。**
`tests/unit/test_seed_model_constants.py` 现在覆盖 `model.py` 里带公司缩写后缀的 15 个常量
（11 个 `ACC_*` + 4 个 `WH_*`）。**它不覆盖**：`M.COMPANY` / `M.CUSTOMER` / `M.SUPPLIER` /
物料编码等**不带后缀**的名字常量，也不覆盖 `agenerp/seedsite.py` 自有的那批
ERPNext 结构 fixture 名（`ROOT_ITEM_GROUP` / `LEAF_TERRITORY` 等——它们是照抄 ERPNext 标准名，
不由 `autoname` 派生）。那两类此刻仍然只有活站点实跑能发现拼写错误。**照实记，不夸大。**
