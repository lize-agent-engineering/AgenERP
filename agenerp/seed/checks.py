"""场景断言：`verify(dataset)` 返回失败原因列表，空列表 = 全过。

两组断言，缺一不可：

- **荒谬组**：入库 2,000 台 / 发货 990 台 / 成品仓结余 1,010 台 / `LOSS-00003` 10 台已审批 /
  结余价值 ¥6,450 / 两笔逾期。
- **账面全绿组**：GL 借贷差额为 0、负库存条目数为 0、毛利与凭证差额 < ¥0.01、销售订单达成率 100%。
  **这一组必须全绿**——荒谬藏在「没有任何一个字段是红的」的地方，
  一旦这四项里有一项红了，这个测例就退化成一个普通的错账，证明不了它想证明的事。
"""

from __future__ import annotations

from agenerp.seed import names as N
from agenerp.seed.model import FINISHED_ITEM, MONEY_TOLERANCE, WH_FINISHED, Dataset

# ── 期望值：**已知业务事实的字面量，独立于生成器的构造常量** ──────────────
# 这一段刻意不从 `agenerp.seed.model` 取数。从那里取会让断言变成同义反复——
# 改一个构造常量，数据与期望一起动，判据不会发红。
# 数字出处与对账过程见 `docs/architecture/module-boundaries.md` §12.1 / §12.2。
EXPECTED_RECEIPT_QTY = 2000.0        # 自制 1,000 + 外协 1,000（台）
EXPECTED_DELIVERY_QTY = 990.0        # 发货（台）
EXPECTED_BACKLOG_QTY = 1010.0        # 成品仓结余（台）—— 这个数据集存在的理由
EXPECTED_BACKLOG_VALUE = 3110200.0   # 结余价值（元），FIFO 分层：10 × 3,020 + 1,000 × 3,080
EXPECTED_SHORTFALL_QTY = 10.0        # 订单被人工关闭而永不交付的缺口（台）
EXPECTED_ORDER_STATUS = "Closed"      # 订单被人工关闭 —— 账面全绿的来源
EXPECTED_RECEIVABLE_OVERDUE = 4237200.0   # 990 × ¥4,280
EXPECTED_PAYABLE_OVERDUE = 120000.0       # 外协组装服务费
EXPECTED_COGS = 2989800.0            # 990 × ¥3,020（FIFO 全部出自制批）
EXPECTED_GROSS_PROFIT = 1247400.0    # 4,237,200 − 2,989,800
EXPECTED_ORDER_QTY = 1000.0          # 销售单量（台）
EXPECTED_ACHIEVEMENT_RATE = 100.0    # 达成率（%）——必须是绿的，见模块 docstring

_ACC_REVENUE_MARK = "主营业务收入"
_ACC_COGS_MARK = "主营业务成本"


def _close(actual: float, expected: float) -> bool:
    return abs(actual - expected) < MONEY_TOLERANCE


def _receipt_qty(dataset: Dataset) -> float:
    total = 0.0
    for row in dataset.of("Stock Ledger Entry"):
        if row["item_code"] == FINISHED_ITEM and row["actual_qty"] > 0:
            total += float(row["actual_qty"])
    return total


def _finished_bin(dataset: Dataset) -> dict | None:
    for row in dataset.of("Bin"):
        if row["item_code"] == FINISHED_ITEM and row["warehouse"] == WH_FINISHED:
            return row
    return None


def _check_backlog(dataset: Dataset) -> list[str]:
    failures: list[str] = []
    received = _receipt_qty(dataset)
    if not _close(received, EXPECTED_RECEIPT_QTY):
        failures.append(
            f"入库合计应为 {EXPECTED_RECEIPT_QTY} 台（自制 1,000 + 外协 1,000），实为 {received}"
        )
    delivered = sum(
        -float(row["actual_qty"])
        for row in dataset.of("Stock Ledger Entry")
        if row["item_code"] == FINISHED_ITEM and row["actual_qty"] < 0
    )
    if not _close(delivered, EXPECTED_DELIVERY_QTY):
        failures.append(f"发货应为 {EXPECTED_DELIVERY_QTY} 台，实为 {delivered}")
    finished = _finished_bin(dataset)
    if finished is None:
        failures.append(f"成品仓（{WH_FINISHED}）没有 {FINISHED_ITEM} 的结存条目")
        return failures
    if not _close(float(finished["actual_qty"]), EXPECTED_BACKLOG_QTY):
        failures.append(
            f"成品仓结余应为 {EXPECTED_BACKLOG_QTY} 台，实为 {finished['actual_qty']}"
        )
    if not _close(float(finished["stock_value"]), EXPECTED_BACKLOG_VALUE):
        failures.append(
            f"成品仓结余价值应为 ¥{EXPECTED_BACKLOG_VALUE:.2f}"
            "（自制余 10 台 × ¥5.00 + 外协 1,000 台 × ¥6.40，FIFO 分层），"
            f"实为 ¥{float(finished['stock_value']):.2f}"
        )
    return failures


def _check_closed_order(dataset: Dataset) -> list[str]:
    """订单被人工关闭 —— 「990 台之谜」的原生承载物。

    这一条是荒谬的**成因**：订单 1,000 台、实发 990 台，缺口 10 台既没发
    也没记欠货，只是有人把 `status` 置成 `Closed`。ERPNext 据此按完成计。
    """
    rows = [row for row in dataset.of("Sales Order") if row["name"] == N.SALES_ORDER]
    if not rows:
        return [f"{N.SALES_ORDER} 的关闭记录不存在——「990 台之谜」失去成因，达成率也讲不通"]
    row = rows[0]
    item = row["items"][0]
    failures: list[str] = []
    if row["status"] != EXPECTED_ORDER_STATUS:
        failures.append(
            f"{N.SALES_ORDER} 的状态应为 {EXPECTED_ORDER_STATUS}（人工关闭），实为 {row['status']!r}"
        )
    # 缺口从**原生字段自己**算出来，不另存一份，否则就成了自说自话的标签。
    gap = float(item["qty"]) - float(item["delivered_qty"])
    if not _close(gap, EXPECTED_SHORTFALL_QTY):
        failures.append(
            f"{N.SALES_ORDER} 的交付缺口应为 {EXPECTED_SHORTFALL_QTY} 台"
            f"（订单 {item['qty']} − 发货 {item['delivered_qty']}），实为 {gap}"
        )
    return failures


def _check_overdue(dataset: Dataset) -> list[str]:
    failures: list[str] = []
    as_of = dataset.as_of
    receivable = sum(
        float(row["outstanding_amount"])
        for row in dataset.of("Sales Invoice")
        if row["status"] == "Overdue" and row["due_date"] < as_of
    )
    if not _close(receivable, EXPECTED_RECEIVABLE_OVERDUE):
        failures.append(f"应收逾期合计应为 ¥{EXPECTED_RECEIVABLE_OVERDUE:.2f}，实为 ¥{receivable:.2f}")
    payable = sum(
        float(row["outstanding_amount"])
        for row in dataset.of("Purchase Invoice")
        if row["status"] == "Overdue" and row["due_date"] < as_of
    )
    if not _close(payable, EXPECTED_PAYABLE_OVERDUE):
        failures.append(f"应付逾期合计应为 ¥{EXPECTED_PAYABLE_OVERDUE:.2f}，实为 ¥{payable:.2f}")
    return failures


def _check_books_all_green(dataset: Dataset) -> list[str]:
    """账面四项指标必须**全绿**。红了就说明这个测例坏了，不是数据集发现了问题。"""
    failures: list[str] = []
    debit = sum(float(row["debit"]) for row in dataset.of("GL Entry"))
    credit = sum(float(row["credit"]) for row in dataset.of("GL Entry"))
    if not _close(debit - credit, 0.0):
        failures.append(f"GL 借贷不平：借 ¥{debit:.2f} / 贷 ¥{credit:.2f}，差额 ¥{debit - credit:.2f}")

    negative = [
        row for row in dataset.of("Bin") if float(row["actual_qty"]) < 0
    ] + [
        row
        for row in dataset.of("Stock Ledger Entry")
        if float(row["qty_after_transaction"]) < 0
    ]
    if negative:
        failures.append(f"负库存条目数应为 0，实为 {len(negative)}：{[r['name'] for r in negative]}")

    revenue = sum(
        float(row["credit"]) for row in dataset.of("GL Entry") if _ACC_REVENUE_MARK in row["account"]
    )
    cogs = sum(
        float(row["debit"]) for row in dataset.of("GL Entry") if _ACC_COGS_MARK in row["account"]
    )
    voucher_profit = revenue - cogs
    doc_profit = (
        sum(float(row["grand_total"]) for row in dataset.of("Sales Invoice")) - EXPECTED_COGS
    )
    if not _close(voucher_profit - doc_profit, 0.0):
        failures.append(
            f"毛利与凭证差额应 < ¥{MONEY_TOLERANCE:.2f}："
            f"单据侧 ¥{doc_profit:.2f} / 凭证侧 ¥{voucher_profit:.2f}"
        )
    if not _close(voucher_profit, EXPECTED_GROSS_PROFIT):
        failures.append(f"毛利应为 ¥{EXPECTED_GROSS_PROFIT:.2f}，实为 ¥{voucher_profit:.2f}")

    orders = [row for row in dataset.of("Sales Order") if row["name"] == N.SALES_ORDER]
    if not orders:
        failures.append(f"销售订单 {N.SALES_ORDER} 不存在，达成率无从算起")
    else:
        item = orders[0]["items"][0]
        ordered = float(item["qty"])
        if not _close(ordered, EXPECTED_ORDER_QTY):
            failures.append(f"销售单量应为 {EXPECTED_ORDER_QTY} 台，实为 {ordered}")
        # **这里是这个数据集的要害。** 达成率取自 ERPNext 的原生口径：订单一旦
        # 被置为 Closed，系统就按完成计，达成率 100% —— 哪怕实发只有 990 台。
        # 分子不取常量、也不取发货数，而取「系统认定的完成量」，因为荒谬正在于
        # 这个口径与实物的背离：账面 100%，仓里躺着 1,010 台。
        settled = ordered if orders[0]["status"] == EXPECTED_ORDER_STATUS else float(item["delivered_qty"])
        rate = settled / ordered * 100 if ordered else 0.0
        if not _close(rate, EXPECTED_ACHIEVEMENT_RATE):
            failures.append(
                f"销售订单达成率应为 {EXPECTED_ACHIEVEMENT_RATE:.0f}%"
                f"（订单被置为 {EXPECTED_ORDER_STATUS}，系统按 {ordered} 台完成计，"
                f"而实发仅 {item['delivered_qty']} 台），实为 {rate:.2f}%"
            )
    return failures


def verify(dataset: Dataset) -> list[str]:
    """返回失败原因列表。空列表 = 全过。"""
    failures: list[str] = []
    failures += _check_backlog(dataset)
    failures += _check_closed_order(dataset)
    failures += _check_overdue(dataset)
    failures += _check_books_all_green(dataset)
    return failures
