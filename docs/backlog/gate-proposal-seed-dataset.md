# 门禁提案 · 工作项 7「种子数据」

> Status: `proposed`（**提案文本，不是测试代码**）
> Created: 2026-08-21
> 由 plan `docs/plans/p0-foundation/2026-08-21-1634-1-seed-dataset-deterministic.md` 的 Phase 1 产出
> 采纳者：**人**。loop 不得据此在 `tests/gates/` 下创建任何文件（`AGENTS.md` 红线 1）

## 为什么需要这份提案

**⚠️ 2026-08-22 就地改准（plan `2026-08-22-2107-1`）。本节起草时（2026-08-21）逐字写的是**
「`docs/backlog/p0-foundation-roadmap.md` 的对照表里，工作项 7 是八项中**唯一**在
『关闭它的门禁测试』一格写着『尚无门禁——开工前先补一条，否则这一项没有判据』的」——
**这句话已经过期，属确认的 owner-doc 漂移，此处改准；`Status: proposed` 未改，不代人采纳。**

**改准后的事实**：`tests/gates/test_seed_dataset_absurdity.py` **已由人于 2026-08-21 补齐**
（**6 条**，实跑全绿，从未进过 `tools/gates/expected-red.txt`），roadmap 对照表的
`| 7 |` 一格现在写的就是它。所以「唯一写着尚无门禁」不再成立，
mission 规则「判据先行」对工作项 7 **已经满足**。

**那这份提案为什么还在？** 因为人补的那条是 **L1**，断的是**生成器**
（`:23-24` 自带 `1010.0` / `6450.0` 两个常量副本，刻意不从 `agenerp.seed.model` 取数）。
本文件提的三条是 **L2**，断的是**站点自己算出来的数** —— 两者判的不是同一件事，
后者至今**没有任何门禁**。同一份 roadmap 的「判据先行」规则给出的满足路径没有变：
**补一条红的，且补测试要人批，走 `Gates-Change-Approved-By:` trailer**。

loop 走不了最后一步（带 trailer 的提交只有人能做），但可以把提案备好、把决定摆到人面前。
这份文件就是那个提案。

**主数据段的现状（2026-08-22 更新）**：本提案的三条 L2 断言都要求站点上**先有数据**。
那一步已经不是空白了 —— plan
`docs/plans/p0-foundation/2026-08-22-2107-1-seed-site-write-surface-and-masters.md`
交付了 `agenerp/seedsite.py`：从冷起的空站点连跑两次幂等（第一跑新建 40、第二跑新建 0，均 exit 0），
公司 / 11 个科目 / 4 个仓库 / 3 个物料 / 工位 / 3 道工序 / 客户 / 供应商 / 已提交 BOM 全部在站点上。
**单据段与站点侧对账**（`Bin` / `Stock Ledger Entry` / `GL Entry`，也就是本提案三条断言的判据来源）
由本批第二个 plan
`docs/plans/p0-foundation/2026-08-22-2107-2-seed-documents-site-computed-backlog.md` 承接。
**这不改变本提案的 `Status`**：断言写进 `tests/gates/**` 仍然只有人能做。

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

### ⚠️ 三条拟断言的现状（2026-08-22 由 plan `2026-08-22-2107-2` 在活站点上实测后逐条标注）

**`Status: proposed` 未改，不代人采纳。** 本节只把「人采纳时会拿到什么」写准。
实现已就绪的形态是一条 **CLI 退出码**（`python3 -m agenerp.seedsite --verify-site --site <site>`），
**不是门禁**；把它变成门禁只差人的一次带 `Gates-Change-Approved-By:` trailer 的提交。

- **拟断言 ① —— 实现已就绪，站点上实测通过，期望值 = 实测值。**
  从 `docker compose down -v` 冷起的空站点装载后，站点自己算出
  `Bin(XM-LACE-1000, XM 成品仓 - XM).actual_qty = 1010.00`、`stock_value = 6450.00`。
  **本仓一行 `Bin` / `Stock Ledger Entry` / `GL Entry` 都没构造**，这三类行全部由站点产生。
  两条变异实测该断言有牙齿：改发货量 990→980 → 站点算出 `1020.00`，断言红；
  改外协服务费 2200→2100 → 数量仍 `1010.00` 而金额红在 `6350.00`。
- **拟断言 ② —— ⚠️ 四项里有一项在当前口径下站点算不出来，采纳前必须知道。**
  · GL 借贷差额为 0 → **实测 `0.00`，可查**（`GL Entry` 滤掉 `is_cancelled` 后借贷合计相等）；
  · 负库存条目数为 0 → **实测 `0`，可查**（`Bin.actual_qty < 0` + `SLE.qty_after_transaction < 0`）；
  · 毛利与凭证差额 < ¥0.01 → **实测 `13662.00`，可查**（GL 收入贷方 `18612.00` − GL 成本借方 `4950.00`）；
  · **销售订单达成率 100% → 站点上算不出来。** 站点实测 `Sales Order.per_delivered = 99.0`。
    **原因**：达成率 100% 依赖「已审批合理损耗 10 米」，而它落在 `Loss Review` 这个
    **本仓虚构的 DocType** 与 `Delivery Note.xm_loss_review` 这个**本仓虚构的自定义字段**上，
    **ERPNext v15 里两者都不存在**。给站点建它们会造出物理表（**DDL**），
    并改变 `schema_drift` 的观测面（可能弄红既有门禁）。
    **人采纳提案时若照抄这一项，会拿到一条注定红的门禁。**
    可选处置由人裁定：(a) 允许为 `Loss Review` 建 DocType / 自定义字段；
    (b) 给出一条站点可表达的达成率口径；(c) 采纳时把这一项摘掉，只留前三项。
- **拟断言 ③ —— 实现已就绪，站点上实测通过，期望值 = 实测值。**
  `Sales Invoice` 中 `status == "Overdue"` 的 `outstanding_amount` 合计 = **¥18,612.00**（`ACC-SINV-2026-00001`）；
  `Purchase Invoice` 同口径 = **¥2,200.00**（`ACC-PINV-2026-00001`）。
  ⚠️ **一条成立条件照实写**：`status` 是站点拿**真实时钟**跟 `due_date` 比出来的，
  不是拿数据集的 `as_of` 比的。种子日期固定在 2026-02/03 故恒成立，但这不是结构性成立。
  **⚠️ 2026-08-23 补取证出处（句子本体未改 —— 实测证实了它）**，plan `2026-08-23-0120-2` 分流 (i)：
  写 `status` 的是**提交时的同步调用链**，容器内 ERPNext v15.119.3 实读
  `erpnext/accounts/doctype/sales_invoice/sales_invoice.py:274 validate()` → `:350 self.set_status()`
  → `:2037-2038` → `:2077-2100 is_overdue()`（逐字 `today = getdate()`）；
  `purchase_invoice.py:258` / `:292` / `:2012-2013` 同构，`:22` 直接 import 同一个 `is_overdue`。
  `scheduler` 的日任务 `erpnext.controllers.accounts_controller.update_invoice_status`
  （`erpnext/hooks.py:447`）**不参与** —— 它只更新 `status LIKE "Unpaid%" / "Partly Paid%"` 的行；
  本仓站点侧 scheduler 实测 disabled、`tabScheduled Job Log` 0 行。
  ⚠️ 精确形态：两张发票都有 `payment_schedule`，`is_overdue` 走子表分支，比的是
  `payment_schedule.due_date`（实测与发票头 `due_date` 同值）。
  **采纳时这段出处可以一并照抄；本 plan 不改本文件的 `Status: proposed`，不代人采纳。**

**采纳时可直接照抄的读取路径与期望值出处**：全部 9 项的实现见
`agenerp/seedsite.py` 的 `verify_site()`；期望值一律取自 `agenerp/seed/checks.py` 的 `EXPECTED_*`
（`checks.py` 自述「刻意不从 `agenerp.seed.model` 取数」，它才是判官侧那份副本）。
落点与残余风险见 `docs/architecture/module-boundaries.md` §12.10 ——
其中**外协批走的 DocType 不是 `Subcontracting Receipt`**，采纳时不要把结论写得比这更强。

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
