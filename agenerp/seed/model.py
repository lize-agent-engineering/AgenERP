"""种子数据集的值对象与常量表。

**本模块是唯一的数值落点**：所有参与断言的数量、单价、日期都在这里，
生成器与校验器都从这里取，不各自写一遍。数值出处与对账过程见
`docs/architecture/module-boundaries.md` §12.1 / §12.2。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

SCOPE = "seed"

# ── 硬断言：构造式常量 ────────────────────────────────────────────────
# 这些数字来自冻结证据仓里含单价的原始记录，不是二手转述（对账见 §12.1）。
COMPANY = "XM 演示纺织有限公司"
CUSTOMER = "杭州春季服饰有限公司"
SUPPLIER = "绍兴染整演示厂"

FINISHED_ITEM = "XM-LACE-1000"
RAW_ITEM = "XM-YARN-WHITE"
SERVICE_ITEM = "XM-DYE-SERVICE"

WH_RAW = "XM 原料仓 - XM"
WH_WIP = "XM 在制品仓 - XM"
WH_FINISHED = "XM 成品仓 - XM"
WH_SUBCON = "XM 外协仓 - XM"

ORDER_QTY = 1000          # 销售单量（米）
INHOUSE_QTY = 1000        # 自制入库（米）
SUBCON_QTY = 1000         # 外协收货（米）
DELIVERY_QTY = 990        # 发货（米）
APPROVED_LOSS_QTY = 10    # 已审批合理损耗（米），单据号 LOSS-00003

OPENING_RAW_QTY = 300     # 期初原料入库（Kg）
BOM_RAW_QTY = 120         # 每 1,000 米成品的原料用量（Kg）
RAW_RATE = 35.0           # 原料单价（元/Kg）
OPERATION_MINUTES = 300 + 180 + 120   # 织造 + 定型 + 成品检验
WORKSTATION_HOUR_RATE = 80.0          # 工位费率（元/小时）
SUBCONTRACT_FEE = 2200.0              # 外协服务费（元）
SALES_RATE = 18.8                     # 售价（元/米）

LOSS_REVIEW_NAME = "LOSS-00003"
LOSS_REVIEW_STATUS = "Approved"

# 日期一律由基准日推出，生成路径上不读时钟。「逾期 3 天」是数据不是跑出来的：
# 数据集自带 as_of，逾期与否由 as_of 与 due_date 相比得出。
BASE_DATE = date(2026, 2, 2)
INVOICE_TERM_DAYS = 30
OVERDUE_DAYS = 3

# 账户表。名字即科目，借贷方向由分录自己给。
ACC_RAW = "原材料 - XM"
ACC_WIP = "在制品 - XM"
ACC_FINISHED = "成品 - XM"
ACC_SUBCON_STOCK = "外协物料 - XM"
ACC_STOCK_ADJ = "库存调整 - XM"
ACC_OPERATING = "生产费用（计入估值）- XM"
ACC_GRNI = "已收货未开票 - XM"
ACC_PAYABLE = "应付账款 - XM"
ACC_RECEIVABLE = "应收账款 - XM"
ACC_REVENUE = "主营业务收入 - XM"
ACC_COGS = "主营业务成本 - XM"

WAREHOUSE_ACCOUNT = {
    WH_RAW: ACC_RAW,
    WH_WIP: ACC_WIP,
    WH_FINISHED: ACC_FINISHED,
    WH_SUBCON: ACC_SUBCON_STOCK,
}

# ── 派生量：由上面那些算出来，不许在别处硬写 ──────────────────────────
INHOUSE_VALUE = BOM_RAW_QTY * RAW_RATE + OPERATION_MINUTES / 60 * WORKSTATION_HOUR_RATE
INHOUSE_RATE = INHOUSE_VALUE / INHOUSE_QTY
SUBCON_VALUE = BOM_RAW_QTY * RAW_RATE + SUBCONTRACT_FEE
SUBCON_RATE = SUBCON_VALUE / SUBCON_QTY

# FIFO：发货 990 米全部出自制批（自制批先入）。
COGS_VALUE = DELIVERY_QTY * INHOUSE_RATE
BACKLOG_QTY = INHOUSE_QTY + SUBCON_QTY - DELIVERY_QTY
BACKLOG_VALUE = (INHOUSE_QTY - DELIVERY_QTY) * INHOUSE_RATE + SUBCON_VALUE

RECEIVABLE_OVERDUE = DELIVERY_QTY * SALES_RATE
PAYABLE_OVERDUE = SUBCONTRACT_FEE
GROSS_PROFIT = RECEIVABLE_OVERDUE - COGS_VALUE

MONEY_TOLERANCE = 0.01


def day(offset: int) -> str:
    return (BASE_DATE + timedelta(days=offset)).isoformat()


@dataclass(frozen=True)
class Dataset:
    """一份生成好的数据集。

    `records` 按 DocType 分组，组内按单据号排序——**排序在生成期做死**，
    不留给落盘或比较环节，否则「确定性」会依赖两个地方而不是一个。
    """

    seed: int
    as_of: str
    records: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)

    def of(self, doctype: str) -> tuple[dict[str, Any], ...]:
        return self.records.get(doctype, ())

    def doctypes(self) -> tuple[str, ...]:
        return tuple(sorted(self.records))
