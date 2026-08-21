# 门禁提案 · 工作项 7「种子数据」

> Status: `proposed`（**提案文本，不是测试代码**）
> Created: 2026-08-21
> 由 plan `docs/plans/p0-foundation/2026-08-21-1634-1-seed-dataset-deterministic.md` 的 Phase 1 产出
> 采纳者：**人**。loop 不得据此在 `tests/gates/` 下创建任何文件（`AGENTS.md` 红线 1）

## 为什么需要这份提案

`docs/backlog/p0-foundation-roadmap.md` 的对照表里，工作项 7 是八项中**唯一**在「关闭它的门禁测试」
一格写着「尚无门禁——开工前先补一条，否则这一项没有判据」的。同一份 roadmap 的「判据先行」规则
自己给出了满足路径：**补一条红的，且补测试要人批，走 `Gates-Change-Approved-By:` trailer**。

loop 走不了最后一步（带 trailer 的提交只有人能做），但可以把提案备好、把决定摆到人面前，
并且**在动手写实现之前**摆过去。这份文件就是那个提案。

## 它该断言什么

工作项 7 的完整形态是两半：

- **A 半（纯逻辑）**：确定性生成一份内置 1,010 米积压的离散制造数据集，并自验。
  已由上述 plan 交付，判据是 `python3 -m agenerp.seed --seed 42 --verify` 的退出码，
  外加 `tests/unit/test_seed_deterministic.py` 的单测。
- **B 半（站点侧）**：把数据集装载进活站点，并断言**荒谬在站点上真的存在**——
  也就是站点自己算出来的 `Bin` 上确实是 1,010 米 / ¥6,450，而不是生成器自说自话。

**A 半不需要新门禁**（它的判据已经可执行）。这份提案要补的是 **B 半**。

拟断言（三条，逐条都要能独立发红）：

1. `test_seed_backlog_exists_on_site` —— 装载后查站点的 `Bin`，
   成品仓的 `actual_qty == 1010`、`stock_value == 6450.00`（容差 ¥0.01）。
   **这一条是整个工作项存在的理由**：它证明「1,010 米积压」不是本仓生成器里的一个常量，
   而是 ERPNext 自己按 FIFO 分层算出来的结果（成本构成见 `docs/architecture/module-boundaries.md` §12.1）。
2. `test_seed_scenario_is_green_on_every_gate` —— 同一份数据装载后，站点侧的四项指标**全绿**：
   GL 借贷差额为 0、负库存条目数为 0、毛利与凭证差额 < ¥0.01、销售订单达成率 100%。
   **必须是绿的**——荒谬藏在「没有任何一个字段发红」的地方，一旦这四项里有一项红了，
   这个测例就退化成一个普通的错账，证明不了它想证明的事。
3. `test_seed_overdue_pair_is_findable` —— 应收逾期合计 ¥18,612、应付逾期 ¥2,200
   在站点上可由 `status == "Overdue"` 直接查到。这是第 1 条的**对照组**：
   逾期落在一个字段上、积压不落在任何字段上——两类异常的可发现性根本不同，
   只有荒谬没有对照组，这个测例证明不了「schema 能表达是什么、表达不了什么样算不对」。

## 放在哪个文件

`tests/gates/test_seed_dataset_backlog.py`（新建）。

不并进既有文件的理由：`test_snapshot_diff_structured.py` 与 `test_customization_roundtrip_delete.py`
断的是**结构定制**的往返，本项断的是**业务数据**；混在一起会让预期红名单里一行同时代表两件事，
关闭工作项时不知道该划哪行。

## 为什么它必须是 L2

三条断言全部要求「**在站点上**」成立，因此都要 `live_site` fixture（以及装载数据用的写权限），
按本仓分层即 L2（`@pytest.mark.live`）。

把它降成 L1（只查生成器的内存对象）**会让这条门禁失去全部意义**——
那样断的还是生成器自己，与 A 半的单测重复，而工作项 7 真正没被证明的恰恰是「ERPNext 也这么算」。

**因此这条门禁在 `live_site` 解锁之前会一直红在 fixture 层**，这是预期内的：
它与工作项 5/6/8 一起排在同一个前置后面（`docs/masterplan/STATE.md` needs-human 队列里那行 `[open]`）。

## 人若采纳，需要的提交形态

```
test(gates): 工作项 7 补一条 L2 红门禁（种子数据的荒谬须在站点上成立）

新增 tests/gates/test_seed_dataset_backlog.py 三条断言，全部 @pytest.mark.live。
三条同时加进 tools/gates/expected-red.txt（名单变长需人工批准）。

Gates-Change-Approved-By: <人的标识>
```

配套动作两条，同一提交里做完：

1. `tools/gates/expected-red.txt` 追加三行（**名单变长只有人能批**；
   loop 只允许在测试转绿时把已绿的行划掉，名单在 loop 手里只能变短）。
2. `docs/backlog/p0-foundation-roadmap.md` 对照表第 7 行改为指向新文件，
   并把工作项 7 从 `planned` 推进到 `todo`/`planned` 之外的相应状态——
   注意 roadmap 对 `done` 的定义是「对应门禁测试已转绿并从预期红名单划掉」，
   在 `live_site` 解锁前这条新门禁不可能转绿，所以采纳提案**不等于**可以把工作项 7 置 `done`。

## 不采纳的代价

工作项 7 会停在 `planned`，B 半永远没有判据；A 半交付的
`python3 -m agenerp.seed --seed 42 --verify` 仍然可跑、仍然有牙齿（做过变异验证），
但它证明的只是「生成器自洽」，不是「ERPNext 也这么算」。

处置选项的完整列表见 `docs/masterplan/STATE.md` 的 needs-human 队列中对应的那一行。
