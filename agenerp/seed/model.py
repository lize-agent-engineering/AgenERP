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
# 样板公司为**虚构**实体（D-9：本项目与 XM 演示项目彻底切开；门禁
# `test_no_third_party_rights` 亦禁止夹带真实品牌）。行业取储能电池包制造——
# 离散制造、有 BOM／工单／外协三段，正好把 ERPNext 的制造闭环用满。
# 数值口径与对账过程见 `docs/architecture/module-boundaries.md` §12.1 / §12.2。
COMPANY = "恒锐动力科技有限公司"
COMPANY_ABBR = "HRD"
CUSTOMER = "北方新能源工程有限公司"
SUPPLIER = "临港储能科技有限公司"

FINISHED_ITEM = "HRD-PACK-5K"      # 户用储能电池包 5 kWh，单位：台
RAW_ITEM = "HRD-CELL-280"          # 磷酸铁锂电芯 280Ah，单位：只
SERVICE_ITEM = "HRD-ASSY-SVC"      # 电池模组组装外协服务

UOM_FINISHED = "台"
UOM_RAW = "只"

WH_RAW = f"原料仓 - {COMPANY_ABBR}"
WH_WIP = f"在制品仓 - {COMPANY_ABBR}"
WH_FINISHED = f"成品仓 - {COMPANY_ABBR}"
WH_SUBCON = f"外协仓 - {COMPANY_ABBR}"

ORDER_QTY = 1000          # 销售单量（台）
INHOUSE_QTY = 1000        # 自制入库（台）
SUBCON_QTY = 1000         # 外协收货（台）
DELIVERY_QTY = 990        # 发货（台）
SHORTFALL_QTY = 10        # 少发（台）—— 订单被人工关闭，这 10 台永远不会发

OPENING_RAW_QTY = 40000   # 期初电芯入库（只）——够两批各 16,000，余 8,000
BOM_RAW_QTY = 16000       # 每 1,000 台成品的电芯用量（只）= 16 只/台
RAW_RATE = 185.0          # 电芯单价（元/只）
OPERATION_MINUTES = 25000 + 12000 + 8000   # 模组装配 + BMS 调试老化 + 成品检验（分钟/批）
WORKSTATION_HOUR_RATE = 80.0               # 工位费率（元/小时）
SUBCONTRACT_FEE = 120000.0                 # 外协组装服务费（元/批）= ¥120/台
SALES_RATE = 4280.0                        # 售价（元/台）

# 「990 台之谜」的原生承载物：销售订单被**人工关闭**（ERPNext 原生
# `Sales Order.status = "Closed"`）。系统据此按完成计，达成率显示 100%，
# 而实际只发了 990 台 —— 这就是账面全绿却仓存积压的那道缝。
# D-9 之前这里挂的是 XM 自建的 `Loss Review` custom DocType，已弃用：
# 原生 ERPNext 无此表，继承它等于把演示项目的定制带进生产项目。
SALES_ORDER_STATUS = "Closed"
SALES_ORDER_PER_DELIVERED = 99.0   # 原生字段：实发 990 / 订单 1,000

# 日期一律由基准日推出，生成路径上不读时钟。「逾期 3 天」是数据不是跑出来的：
# 数据集自带 as_of，逾期与否由 as_of 与 due_date 相比得出。
BASE_DATE = date(2026, 2, 2)
INVOICE_TERM_DAYS = 30
OVERDUE_DAYS = 3

# 账户表。名字即科目，借贷方向由分录自己给。
ACC_RAW = "原材料 - HRD"
ACC_WIP = "在制品 - HRD"
ACC_FINISHED = "成品 - HRD"
ACC_SUBCON_STOCK = "外协物料 - HRD"
ACC_STOCK_ADJ = "库存调整 - HRD"
ACC_OPERATING = "生产费用（计入估值） - HRD"
ACC_GRNI = "已收货未开票 - HRD"
ACC_PAYABLE = "应付账款 - HRD"
ACC_RECEIVABLE = "应收账款 - HRD"
ACC_REVENUE = "主营业务收入 - HRD"
ACC_COGS = "主营业务成本 - HRD"

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

# FIFO：发货 990 台全部出自制批（自制批先入）。
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
