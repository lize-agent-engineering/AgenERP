# 01 `ACC_OPERATING` 少一个空格，在活站点上永远命不中

> Status: **open（登记不修）** —— 修改落点在 `agenerp/seed/model.py`，
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

## Tests

- `tests/unit/test_seedsite_loader.py::test_account_name_mismatch_is_reported_not_swallowed`（unit）——
  用 FakeTransport 让站点回一个与常量不同的 `name`，断言装载结果里出现该条不一致记录。
  这条测试**保护的是「不静默」这个行为**，不是保护常量本身。
- 常量本身**没有回归覆盖**（补了空格之后才谈得上）。照实记。

## Affected Artifacts

- `agenerp/seed/model.py:60` —— 缺陷所在，**本次未改**。
- `agenerp/seedsite.py` —— 比对与告警的落点。
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

## Prevention Gap

- 数值常量有对账（§12.1/§12.2），**名字常量没有**：没有任何一步检查过
  `model.py` 里那些「看起来像 ERPNext 派生名」的字符串**真的能被 ERPNext 派生出来**。
  在站点侧对账落地之前，这一类拼写错误只能靠人眼。
