"""种子主数据装载器 —— 把 `agenerp.seed` 的主数据装进**活站点**。

**为什么这个模块不在 `agenerp/seed/` 里**（plan `2026-08-22-2107-1` 的 `Decision` D1）：
`docs/architecture/module-boundaries.md` §12 逐字规定 `agenerp.seed`
「零第三方依赖，纯标准库，**不读时钟、不读环境、不联网**」。装载器必然读环境（站点凭据）并联网。
把它放进那个包等于把一条**好的**不变量改松，所以它是同级的独立单文件模块
（先例：`agenerp/oob.py`）。`agenerp/seed/**` 在本模块落地时**一个字节未改**，只被只读引用。

**本模块拥有什么、不拥有什么**（同一个 `Decision` 的第二半）：

- **参与断言的数值一律从 `agenerp.seed.model` / `masters` / `names` 取**，本模块里不得出现第二份。
- **纯 ERPNext 结构字段由本模块自己拥有**（公司缩写、币种、国别、科目表模板、
  `root_type` / `account_type` / `parent_account`、工位归属、以及 setup wizard 本该建的前置 fixture 名）。
  它们**不参与任何断言**，逐条列在 §12.9。

**幂等口径**：`SiteClient.ensure_doc` 先查后建、**只建不改**。第二跑的判据是「新建 0」，不是「没报错」。

**没有 teardown。** 装进站点的对象删不掉；复位手段只有 `docker compose down -v` 冷起
（丢整站数据）或事前 `bench backup` + **人工** `restore`。这条代价写在 §12.9，不粉饰。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from dataclasses import dataclass, field
from typing import Any

from agenerp.seed import checks as CH
from agenerp.seed import generate as seed_generate
from agenerp.seed import masters, names
from agenerp.seed import model as M
from agenerp.site import SiteClient, SiteError, client_from_env

# ── 本模块自有的纯 ERPNext 结构常量（不参与任何断言，§12.9 逐条列名）────────────
ABBR = M.COMPANY_ABBR
DEFAULT_CURRENCY = "CNY"
COUNTRY = "China"
CHART_TEMPLATE = "Standard Template"
CHART_NAME = "Standard"

# ERPNext setup wizard 本该建、而本仓的建站命令（`bench new-site --install-app erpnext`，
# 无 setup wizard）没有建的前置 fixture。名字**照抄 ERPNext 的标准 fixture 名**，不自造。
# 2026-08-22 实测：不先建 `Warehouse Type: Transit`，`POST /api/resource/Company` 直接
# 417 `LinkValidationError: Could not find Warehouse Type: Transit`。
TRANSIT_WAREHOUSE_TYPE = "Transit"
ROOT_ITEM_GROUP = "All Item Groups"
ROOT_CUSTOMER_GROUP = "All Customer Groups"
LEAF_CUSTOMER_GROUP = "Commercial"
ROOT_TERRITORY = "All Territories"
LEAF_TERRITORY = "Rest Of The World"
ROOT_SUPPLIER_GROUP = "All Supplier Groups"
LEAF_SUPPLIER_GROUP = "Local"
WORKSTATION = "模组装配线"

# 建公司时由站点自己生成的树根（实测 82 条科目 + 5 个仓库），本模块只挂在它们下面。
ROOT_WAREHOUSE = f"All Warehouses - {ABBR}"
PARENT_STOCK_ASSETS = f"Stock Assets - {ABBR}"
PARENT_STOCK_EXPENSES = f"Stock Expenses - {ABBR}"
PARENT_STOCK_LIABILITIES = f"Stock Liabilities - {ABBR}"
PARENT_PAYABLE = f"Accounts Payable - {ABBR}"
PARENT_RECEIVABLE = f"Accounts Receivable - {ABBR}"
PARENT_INCOME = f"Direct Income - {ABBR}"

# `model.py` 的 11 个科目常量 → ERPNext 的结构三元组。**只有结构，没有数值。**
ACCOUNT_SHAPE: dict[str, tuple[str, str, str]] = {
    M.ACC_RAW: ("Asset", "Stock", PARENT_STOCK_ASSETS),
    M.ACC_WIP: ("Asset", "Stock", PARENT_STOCK_ASSETS),
    M.ACC_FINISHED: ("Asset", "Stock", PARENT_STOCK_ASSETS),
    M.ACC_SUBCON_STOCK: ("Asset", "Stock", PARENT_STOCK_ASSETS),
    M.ACC_STOCK_ADJ: ("Expense", "Stock Adjustment", PARENT_STOCK_EXPENSES),
    M.ACC_OPERATING: ("Expense", "Expenses Included In Valuation", PARENT_STOCK_EXPENSES),
    M.ACC_GRNI: ("Liability", "Stock Received But Not Billed", PARENT_STOCK_LIABILITIES),
    M.ACC_PAYABLE: ("Liability", "Payable", PARENT_PAYABLE),
    M.ACC_RECEIVABLE: ("Asset", "Receivable", PARENT_RECEIVABLE),
    M.ACC_REVENUE: ("Income", "", PARENT_INCOME),
    M.ACC_COGS: ("Expense", "Cost of Goods Sold", PARENT_STOCK_EXPENSES),
}


def strip_abbr(derived: str) -> str:
    """把 `model.py` 里那些**已经带着公司缩写后缀**的常量还原成 `<x>_name`。

    ⚠️ **畸形后缀失败即停，不容忍、不纠正**（plan `2026-08-22-2325-1` 的 `Decision`，
    三个候选与残余风险见 `docs/architecture/module-boundaries.md` §12.11）：
    ERPNext 的 `autoname` 走 `" - ".join([<x>_name, abbr])`，只可能产出带空格的名字，
    所以送进来的常量必须逐字形如 `<name> - {ABBR}`。此前这里容忍 `- {ABBR}` 这种少一个空格的写法，
    是被 `M.ACC_OPERATING` 的一处真缺陷逼出来的代偿（`docs/bugs/01-...md`）；
    该常量已在同一个 plan 里修好，代偿随之撤掉——继续容忍等于让下一个拼错的常量继续静默。
    **不选「原样返回」**：那个串会被 `site_name_of` 再拼一次后缀，在站点上真建出 `X - HRD - HRD`。
    """
    suffix = f" - {ABBR}"
    if not derived.endswith(suffix):
        raise ValueError(
            f"{derived!r} 不是站点派生得出的名字：ERPNext 的 autoname 走 "
            f'" - ".join([<x>_name, abbr])，常量必须形如 `<name> - {ABBR}`。'
            f"机械判据见 tests/unit/test_seed_model_constants.py"
        )
    return derived[: -len(suffix)]


def site_name_of(derived: str) -> str:
    """站点**实际会**派生出来的名字（`" - ".join([<x>_name, abbr])`，2026-08-22 实测）。"""
    return f"{strip_abbr(derived)} - {ABBR}"


@dataclass(frozen=True)
class Step:
    """一步装载。`key` 是幂等判据（喂给 `find_one`），`payload` 是建档载荷。

    `expected_name` 是「站点应当派生出来的名字」；站点回的真名与它不符时，
    装载器**报告**而不是静默 —— 见 `LoadReport.mismatches`。
    """

    doctype: str
    key: dict[str, Any]
    payload: dict[str, Any]
    expected_name: str
    # `agenerp.seed` 里那个**原始常量**。此刻恒与 `expected_name` 相同（`2026-08-22-2325-1`
    # 修好了唯一一个不相同的常量，并用机械判据钉住），两者不同就说明本仓的常量
    # **不可能**被 ERPNext 派生出来。比对拿它做基准，不拿 `expected_name` ——
    # 拿后者比对是自己跟自己比，永远相等。
    source_constant: str = ""

    @property
    def source(self) -> str:
        return self.source_constant or self.expected_name


def _step(doctype: str, expected_name: str, payload: dict[str, Any],
          source: str = "") -> Step:
    return Step(doctype, {"name": expected_name}, payload, expected_name, source)


def _company_steps() -> list[Step]:
    return [
        _step("Warehouse Type", TRANSIT_WAREHOUSE_TYPE, {"name": TRANSIT_WAREHOUSE_TYPE}),
        _step("Company", M.COMPANY, {
            "company_name": M.COMPANY,
            "abbr": ABBR,
            "default_currency": DEFAULT_CURRENCY,
            "country": COUNTRY,
            "create_chart_of_accounts_based_on": CHART_TEMPLATE,
            "chart_of_accounts": CHART_NAME,
        }),
    ]


def _account_steps() -> list[Step]:
    steps = []
    for constant, (root_type, account_type, parent) in ACCOUNT_SHAPE.items():
        steps.append(_step("Account", site_name_of(constant), {
            "account_name": strip_abbr(constant),
            "company": M.COMPANY,
            "parent_account": parent,
            "root_type": root_type,
            "account_type": account_type,
            "is_group": 0,
        }, source=constant))
    return steps


def _warehouse_steps() -> list[Step]:
    steps = []
    for row in masters.warehouses():
        constant = row["name"]
        steps.append(_step("Warehouse", site_name_of(constant), {
            "warehouse_name": strip_abbr(constant),
            "company": row["company"],
            "is_group": row["is_group"],
            "parent_warehouse": ROOT_WAREHOUSE,
            # 仓 → 科目的对应取自 `model.WAREHOUSE_ACCOUNT`，本模块不另写一份。
            "account": site_name_of(M.WAREHOUSE_ACCOUNT[constant]),
        }, source=constant))
    return steps


def _catalog_steps() -> list[Step]:
    """物料前置：`Item Group` 树与 `UOM`。两者的取值都从 `masters.items()` 读出来，不另写清单。"""
    steps = [_step("Item Group", ROOT_ITEM_GROUP, {
        "item_group_name": ROOT_ITEM_GROUP, "is_group": 1,
    })]
    rows = masters.items()
    for group in dict.fromkeys(row["item_group"] for row in rows):
        steps.append(_step("Item Group", group, {
            "item_group_name": group, "parent_item_group": ROOT_ITEM_GROUP, "is_group": 0,
        }))
    for uom in dict.fromkeys(row["stock_uom"] for row in rows):
        steps.append(_step("UOM", uom, {"uom_name": uom}))
    return steps


def _routing_steps() -> list[Step]:
    """`Workstation` → `Operation`。**顺序不可换**，也不可省。

    `masters.bom()` 的 `operations` 三行的 `operation` 是 Link 到 `Operation` DocType
    （2026-08-22 实测：缺它 `POST /api/resource/BOM` 回 417 `LinkValidationError`），
    少了这一段 BOM 建不出来，CLI 会按「失败即停」退非 0。
    """
    steps = [_step("Workstation", WORKSTATION, {
        "workstation_name": WORKSTATION,
        # ⚠️ 直接给 `hour_rate` 会被站点算掉回 0.0（实测）：它是几个分项之和的派生量。
        "hour_rate_labour": M.WORKSTATION_HOUR_RATE,
    })]
    for row in masters.bom()[0]["operations"]:
        steps.append(_step("Operation", row["operation"], {
            "name": row["operation"], "workstation": WORKSTATION,
        }))
    return steps


def _item_steps() -> list[Step]:
    return [
        _step("Item", row["name"], {
            "item_code": row["name"],
            "item_name": row["item_name"],
            "item_group": row["item_group"],
            "stock_uom": row["stock_uom"],
            "is_stock_item": row["is_stock_item"],
            # D-12：原生外协链的前置。不带这个标志，建外协采购订单回 417
            # `Row #1: Finished Good Item ... must be a sub-contracted item`（实测两次）。
            # 用 `.get` 而不是 `row[...]`：只有成品需要它，原料与服务件不该被迫声明。
            "is_sub_contracted_item": row.get("is_sub_contracted_item", 0),
        })
        for row in masters.items()
    ]


def _party_steps() -> list[Step]:
    """客户 / 供应商，以及它们的分组前置。

    ⚠️ `Customer` **必须挂非组 `Customer Group`**（实测：挂组回
    `417 ValidationError: Cannot select a Group type Customer Group.`）；
    `Supplier` 挂组反而放行。ERPNext 两边校验不对称，这里一律挂非组叶子，照实注不解释成对称。
    """
    return [
        _step("Customer Group", ROOT_CUSTOMER_GROUP, {
            "customer_group_name": ROOT_CUSTOMER_GROUP, "is_group": 1}),
        _step("Customer Group", LEAF_CUSTOMER_GROUP, {
            "customer_group_name": LEAF_CUSTOMER_GROUP,
            "parent_customer_group": ROOT_CUSTOMER_GROUP, "is_group": 0}),
        _step("Territory", ROOT_TERRITORY, {
            "territory_name": ROOT_TERRITORY, "is_group": 1}),
        _step("Territory", LEAF_TERRITORY, {
            "territory_name": LEAF_TERRITORY,
            "parent_territory": ROOT_TERRITORY, "is_group": 0}),
        _step("Supplier Group", ROOT_SUPPLIER_GROUP, {
            "supplier_group_name": ROOT_SUPPLIER_GROUP, "is_group": 1}),
        _step("Supplier Group", LEAF_SUPPLIER_GROUP, {
            "supplier_group_name": LEAF_SUPPLIER_GROUP,
            "parent_supplier_group": ROOT_SUPPLIER_GROUP, "is_group": 0}),
        _step("Customer", M.CUSTOMER, {
            "customer_name": M.CUSTOMER,
            "customer_group": LEAF_CUSTOMER_GROUP,
            "territory": LEAF_TERRITORY}),
        _step("Supplier", M.SUPPLIER, {
            "supplier_name": M.SUPPLIER,
            "supplier_group": LEAF_SUPPLIER_GROUP}),
    ]


def _bom_step() -> Step:
    """BOM 建成**已提交**（`docstatus: 1`，实测 `POST` 直接收）。

    `masters.bom()` 逐字给了 `is_active: 1` / `is_default: 1` —— 草稿 BOM 上这两个字段没有意义。
    **成本三项（`raw_material_cost` / `operating_cost` / `total_cost`）不往载荷里塞**：
    它们是站点自己算的派生量，塞进去等于用本仓的数覆盖站点的数，
    而 B 半存在的全部理由正是「让站点自己算」。
    """
    row = masters.bom()[0]
    stock_uom = {item["name"]: item["stock_uom"] for item in masters.items()}
    return _step("BOM", names.BOM, {
        "item": row["item"],
        "company": row["company"],
        "quantity": row["quantity"],
        "uom": stock_uom[row["item"]],
        "currency": DEFAULT_CURRENCY,
        "is_active": row["is_active"],
        "is_default": row["is_default"],
        "with_operations": 1,
        "docstatus": 1,
        "items": [
            {"item_code": i["item_code"], "qty": i["qty"], "rate": i["rate"],
             "uom": stock_uom[i["item_code"]]}
            for i in row["items"]
        ],
        "operations": [
            {"operation": o["operation"], "time_in_mins": o["time_in_mins"],
             "hour_rate": o["hour_rate"], "workstation": WORKSTATION}
            for o in row["operations"]
        ],
    })


def plan_steps() -> tuple[Step, ...]:
    """全部装载步骤，**依赖顺序写死在这里**。纯函数：不读环境、不联网，可被单测直接判。

    `Warehouse Type` → `Company` → `Account` → `Warehouse` → `Item Group` → `UOM` →
    **`Workstation` → `Operation`** → `Item` → 客户/供应商分组 → `Customer`/`Supplier` → `BOM`。
    """
    return tuple(
        _company_steps()
        + _account_steps()
        + _warehouse_steps()
        + _catalog_steps()
        + _routing_steps()
        + _item_steps()
        + _party_steps()
        + [_bom_step()]
    )


# ══════════════════════════════════════════════════════════════════════════
# 单据段（plan `2026-08-22-2107-2`）—— 让**站点自己**算出 1,010 台 / ¥3,110,200
# ══════════════════════════════════════════════════════════════════════════
#
# **本段与主数据段的分工**：主数据段只建不提交；单据段建完就提交（`docstatus` 0→1）。
# **`--load-masters` 的行为一个字节没动** —— 本段是另一条 CLI 面。
#
# **站点算了 §12.1 的哪几段、哪几段是喂进去的**（D1 的逐字列举，owner doc §12.10 同文）：
#
# - **站点算的**：① BOM 的 `operating_cost`（三条工序 × 工位费率 → ¥800）；
#   ② `Manufacture` 分录里原料的实际估值（120 Kg × 原料仓 FIFO 估值 → ¥4,200）；
#   ③ 自制批单位成本 `(4,200 + 800) / 1,000 = ¥5.00`；④ 外协批单位成本 `(4,200 + 2,200) / 1,000 = ¥6.40`；
#   ⑤ FIFO 分层与发货成本；⑥ `Bin` / `Stock Ledger Entry` / `GL Entry` 三类行全部由站点产生。
# - **喂进去的**（都是 §12.1 的**输入**，不是它的结论）：`RAW_RATE` / `OPENING_RAW_QTY` /
#   `BOM_RAW_QTY` / 工序分钟数 / `WORKSTATION_HOUR_RATE` / `SUBCONTRACT_FEE` / `SALES_RATE` /
#   各单据的数量与日期，以及**从站点读回来再送回去**的 `BOM.operating_cost`。
# - **八个派生量（`INHOUSE_RATE` / `SUBCON_RATE` / `INHOUSE_VALUE` / `SUBCON_VALUE` 四个费率，
#   `BACKLOG_QTY` / `BACKLOG_VALUE` / `COGS_VALUE` / `GROSS_PROFIT` 四个终值）
#   一个都不进送往站点的载荷。** 把答案喂给站点再读回来，等于什么都没证明。
#   ⚠️ **口径要说准（2026-08-22 独立关闭审计指出，此处改准）**：裸名 `grep` 在本文件里**有命中** ——
#   `CH.EXPECTED_BACKLOG_QTY` / `CH.EXPECTED_BACKLOG_VALUE` / `CH.EXPECTED_GROSS_PROFIT`
#   出现在**对账侧**，那是本模块被要求去做的事。可判的判据是
#   **`M.<NAME>` / `model.<NAME>` 在本文件零命中**（`tests/unit/test_seedsite_documents.py` 那条
#   `test_no_derived_quantity_is_ever_fed_to_the_site` 判的正是这个），不是裸名零命中。
#
# **外协批走 ERPNext v15 原生四步链**（D-12，2026-08-23 落地）：
#   采购订单(外协) → 外协订单 → 发料到供应商仓 → 外协收货。
#   后三步全部由服务端工厂方法派生（见 `SiteClient.call_method`），不手工拼载荷。
#
#   此前这里是一条**具名残余风险**：外协批伪造成第二张 `Work Order` +
#   `Stock Entry(Manufacture)` + 服务费附加成本，理由是原生链要求成品带
#   `is_sub_contracted_item = 1` 而当时的 plan 逐字禁止改主数据载荷。那条注释
#   声称「复现的是 ERPNext 给外协收货算成本的同一道公式」——**现已实测证实**：
#   换成原生链后 `Bin.stock_value` 仍为 3,110,200.00，分文不差；收货单实算
#   `rm_cost_per_qty 2,960 + service_cost_per_qty 120 = rate 3,080`。
#   推理是对的，但**走的 DocType 不同**这一点当时就写明了不能含糊 —— 而洞察
#   Agent 读的正是 DocType。风险已消除，判据见 `_document_graph_checks`。

# ── 单据段自有的纯 ERPNext 结构常量（不参与任何断言）────────────────────────
FISCAL_YEAR = str(M.BASE_DATE.year)
FISCAL_YEAR_START = f"{M.BASE_DATE.year}-01-01"
FISCAL_YEAR_END = f"{M.BASE_DATE.year}-12-31"
SELLING_PRICE_LIST = "Standard Selling"
BUYING_PRICE_LIST = "Standard Buying"

# `Stock Entry` 的 `purpose`。**载荷里 `stock_entry_type` 与 `purpose` 必须都送**：
# 2026-08-22 实测，只送 `stock_entry_type` 时站点不自动带出 `purpose`，
# 建 `Material Receipt` 直接回 417 `ValidationError: Source warehouse is mandatory for row 1`。
PURPOSE_RECEIPT = "Material Receipt"
PURPOSE_TRANSFER = "Material Transfer for Manufacture"
PURPOSE_SEND_TO_SUBCONTRACTOR = "Send to Subcontractor"
PURPOSE_MANUFACTURE = "Manufacture"
STOCK_ENTRY_PURPOSES = (PURPOSE_RECEIPT, PURPOSE_TRANSFER, PURPOSE_MANUFACTURE,
    PURPOSE_SEND_TO_SUBCONTRACTOR,
)

# 装载期解析的站点事实。`document_steps()` 是**纯函数**（不联网、不读环境），
# 站点才知道的值以占位符出现在载荷里，由 `load_documents` 边跑边绑。
# 自制批的**整批**工序成本（= 站点算的每单位工序成本 × 该批产量），在 `load_documents` 里绑。
REF_OPERATING_COST = "{{operating_cost}}"
REF_SALES_ORDER = "{{sales_order}}"
REF_SO_DETAIL = "{{so_detail}}"
REF_WORK_ORDER_INHOUSE = "{{work_order_inhouse}}"
REF_SUBCON_PO = "{{subcon_po}}"
REF_SUBCON_ORDER = "{{subcon_order}}"
REF_DELIVERY_NOTE = "{{delivery_note}}"


@dataclass(frozen=True)
class DocStep:
    """一步单据装载。

    `key` 是幂等判据（喂给 `find_one`）。**不能用 `name` 做键**：2026-08-22 实测，
    送 `name: "MAT-STE-9999-88888"` 建 `Stock Entry`，站点回 `MAT-STE-2026-00009` ——
    命名序列胜出，显式 `name` 被静默忽略。冷起空站点上序列号恰好等于 `agenerp/seed/names.py`
    那几个字面量，但那是「按顺序建」的巧合，不是站点承诺，幂等不许押在它上面。

    `submit` 为真时建完就提交。`binds` 形如 `("sales_order=name", "so_detail=items.0.name")`，
    把站点回值里的字段绑成后续步骤的占位符实参。
    """

    doctype: str
    key: dict[str, Any]
    payload: dict[str, Any]
    label: str
    submit: bool = False
    binds: tuple[str, ...] = ()
    # ── 服务端工厂方法（D-12：真实外协语义）────────────────────────────
    # `factory` 非空时，载荷**由站点派生**：先调 `POST /api/method/<factory>` 拿草稿，
    # 再用 `payload` 覆盖需要指定的少数字段。理由见 `SiteClient.call_method` 的
    # docstring —— `Subcontracting Order` 手工 POST 直接 500，那些派生字段只在
    # 工厂方法里算。**凡「本该由另一张单派生出来」的单据一律走这条路。**
    factory: str | None = None
    factory_args: dict[str, Any] | None = None


_FRAMEWORK_KEYS = frozenset({
    "name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
    "__islocal", "__unsaved", "doctype",
})


def _strip_framework_keys(draft: dict) -> dict:
    """剥掉工厂方法草稿里的框架字段，只留业务载荷。

    **`name` 必须剥掉**：草稿里带的是 `new-subcontracting-order-xxxxx` 这类本地占位名，
    原样 POST 会让站点拿它当显式 `name`（而命名序列本该胜出，见 `DocStep` 的 docstring）。
    `docstatus` 也剥：提交由 `DocStep.submit` 统一管，不由草稿说了算。
    """
    return {k: v for k, v in draft.items() if k not in _FRAMEWORK_KEYS}


def _pick(doc: dict, path: str) -> Any:
    """按 `items.0.name` 这样的路径从站点回值里取一个字段。取不到就抛，不静默给 `None`。"""
    node: Any = doc
    for part in path.split("."):
        node = node[int(part)] if part.isdigit() else node[part]
    return node


def resolve_refs(payload: Any, bindings: dict[str, Any]) -> Any:
    """把载荷里的占位符换成已绑定的站点事实。**未绑定的占位符直接抛**，不静默送出去。"""
    if isinstance(payload, dict):
        return {k: resolve_refs(v, bindings) for k, v in payload.items()}
    if isinstance(payload, list):
        return [resolve_refs(v, bindings) for v in payload]
    if isinstance(payload, str) and payload.startswith("{{") and payload.endswith("}}"):
        name = payload[2:-2]
        if name not in bindings:
            raise SiteError(f"载荷里的占位符 {payload} 没有被绑定 —— 装载顺序错了")
        return bindings[name]
    return payload


def _prerequisite_steps() -> list[DocStep]:
    """三个结构前置。本仓建站命令（`bench new-site --install-app erpnext`，无 setup wizard）
    一条都没建，2026-08-22 实测各自的报错原文见 `docs/logs/2026/08-22.md` Phase 1 E1。"""
    steps = [DocStep("Fiscal Year", {"name": FISCAL_YEAR}, {
        "year": FISCAL_YEAR,
        "year_start_date": FISCAL_YEAR_START,
        "year_end_date": FISCAL_YEAR_END,
    }, f"会计年度 {FISCAL_YEAR}")]
    for purpose in STOCK_ENTRY_PURPOSES:
        steps.append(DocStep("Stock Entry Type", {"name": purpose},
                             {"name": purpose, "purpose": purpose}, f"库存分录类型 {purpose}"))
    steps.append(DocStep("Price List", {"name": SELLING_PRICE_LIST}, {
        "price_list_name": SELLING_PRICE_LIST, "currency": DEFAULT_CURRENCY,
        "selling": 1, "buying": 0, "enabled": 1}, f"价格表 {SELLING_PRICE_LIST}"))
    steps.append(DocStep("Price List", {"name": BUYING_PRICE_LIST}, {
        "price_list_name": BUYING_PRICE_LIST, "currency": DEFAULT_CURRENCY,
        "selling": 0, "buying": 1, "enabled": 1}, f"价格表 {BUYING_PRICE_LIST}"))
    return steps


def _stock_entry(purpose: str, posting_date: str, payload: dict[str, Any],
                 label: str) -> DocStep:
    """`Stock Entry` 的幂等键取 `(company, purpose, posting_date)` —— 本装载的五张分录两两不同。"""
    return DocStep(
        "Stock Entry",
        {"company": M.COMPANY, "purpose": purpose, "posting_date": posting_date},
        {"stock_entry_type": purpose, "purpose": purpose, "company": M.COMPANY,
         "posting_date": posting_date, "set_posting_time": 1, **payload},
        label,
        submit=True,
    )


def _work_order_step(wip_warehouse: str, transaction_date: str, start: str,
                     label: str, bind: str) -> DocStep:
    """`Work Order` 的幂等键取 `(company, production_item, wip_warehouse)` —— 自制批与外协批靠在制仓分开。

    **`required_items` 不往载荷里塞**：站点自己从 BOM 派生（实测回
    `required_qty 120.0 / rate 35.0 / amount 4200.0`），塞进去等于用本仓的数覆盖站点的数。
    """
    return DocStep(
        "Work Order",
        {"company": M.COMPANY, "production_item": M.FINISHED_ITEM, "wip_warehouse": wip_warehouse},
        {"production_item": M.FINISHED_ITEM, "bom_no": names.BOM, "company": M.COMPANY,
         "qty": M.ORDER_QTY, "wip_warehouse": wip_warehouse, "fg_warehouse": M.WH_FINISHED,
         "source_warehouse": M.WH_RAW, "transaction_date": transaction_date,
         # 工单挂回销售订单。**离线数据集一直有这个字段，站点上此前是 NULL** ——
         # `_document_graph_checks` 只比每种 DocType 的条数，比不到字段，故未抓到。
         # 补一层 `_link_field_checks` 把这类字段级分歧也钉住（P1.0 前置 T0）。
         # 它同时决定了 `doc.links` 从销售订单出发能看到什么，进而决定 P1.0
         # 实验的难度：挂上之后自制批可见、外协批仍不可见（ERPNext v15 的
         # `Subcontracting Order` 结构上没有 sales_order 字段），使实验测的是
         # **一件事**（外协是孤儿）而不是两件。
         "sales_order": REF_SALES_ORDER,
         "planned_start_date": f"{start} 09:00:00"},
        label,
        submit=True,
        binds=(f"{bind}=name",),
    )


def _manufacture_step(work_order_ref: str, wip_warehouse: str, posting_date: str,
                      produced_qty: int, additional_cost: Any, cost_label: str,
                      label: str) -> DocStep:
    """`Manufacture` 分录：消耗在制仓的原料、产出成品。

    **成品行不送 `basic_rate`**：站点自己算（实测 `basic_rate 4.2 + additional_cost → valuation_rate 5.0`）。
    **`additional_costs` 必须由装载器送**：2026-08-22 实测，走 `/api/resource` 建档时
    ERPNext 的 `add_operations_cost()` 不跑（它只在服务端 `make_stock_entry` 路径上跑），
    不送时成品行回 `valuation_rate 4.2` —— 工序成本整段丢掉。
    """
    return _stock_entry(PURPOSE_MANUFACTURE, posting_date, {
        "work_order": work_order_ref, "from_bom": 1, "bom_no": names.BOM,
        "fg_completed_qty": produced_qty, "use_multi_level_bom": 0,
        "additional_costs": [{
            "expense_account": site_name_of(M.ACC_OPERATING),
            "description": cost_label,
            "amount": additional_cost,
        }],
        "items": [
            {"item_code": M.RAW_ITEM, "s_warehouse": wip_warehouse, "qty": M.BOM_RAW_QTY},
            {"item_code": M.FINISHED_ITEM, "t_warehouse": M.WH_FINISHED,
             "qty": produced_qty, "is_finished_item": 1},
        ],
    }, label)


def document_steps() -> tuple[DocStep, ...]:
    """全部单据步骤，**依赖顺序写死在这里**。纯函数：不读环境、不联网，可被单测直接判。"""
    steps = _prerequisite_steps()
    steps += [
        _stock_entry(PURPOSE_RECEIPT, M.day(0), {
            "items": [{"item_code": M.RAW_ITEM, "t_warehouse": M.WH_RAW,
                       "qty": M.OPENING_RAW_QTY, "basic_rate": M.RAW_RATE}],
        }, "期初原料入库"),
        DocStep("Sales Order",
                {"company": M.COMPANY, "customer": M.CUSTOMER, "transaction_date": M.day(0)},
                {"customer": M.CUSTOMER, "company": M.COMPANY, "transaction_date": M.day(0),
                 "delivery_date": M.day(14), "currency": DEFAULT_CURRENCY, "conversion_rate": 1,
                 "selling_price_list": SELLING_PRICE_LIST, "price_list_currency": DEFAULT_CURRENCY,
                 "plc_conversion_rate": 1,
                 "items": [{"item_code": M.FINISHED_ITEM, "qty": M.ORDER_QTY, "rate": M.SALES_RATE,
                            "warehouse": M.WH_FINISHED, "delivery_date": M.day(14)}]},
                "销售订单", submit=True,
                binds=("sales_order=name", "so_detail=items.0.name")),
        _work_order_step(M.WH_WIP, M.day(0), M.day(1), "工单（自制批）", "work_order_inhouse"),
        _stock_entry(PURPOSE_TRANSFER, M.day(1), {
            "work_order": REF_WORK_ORDER_INHOUSE, "from_bom": 1, "bom_no": names.BOM,
            "fg_completed_qty": M.INHOUSE_QTY,
            "items": [{"item_code": M.RAW_ITEM, "s_warehouse": M.WH_RAW,
                       "t_warehouse": M.WH_WIP, "qty": M.BOM_RAW_QTY}],
        }, "原料转在制品仓（自制批）"),
        _manufacture_step(REF_WORK_ORDER_INHOUSE, M.WH_WIP, M.day(3), M.INHOUSE_QTY,
                          REF_OPERATING_COST, "工序费用（站点按 BOM 工序汇总）", "自制批入库"),
        # ── 外协批：ERPNext v15 原生四步链（D-12）────────────────────────
        # 采购订单(外协) → 外协订单 → 发料到供应商仓 → 外协收货。
        # 后三步**全部由工厂方法派生**，不手工拼载荷 —— 见 `SiteClient.call_method`。
        DocStep("Purchase Order",
                {"company": M.COMPANY, "supplier": M.SUPPLIER},
                {"supplier": M.SUPPLIER, "company": M.COMPANY,
                 "transaction_date": M.day(3), "schedule_date": M.day(4),
                 "is_subcontracted": 1, "supplier_warehouse": site_name_of(M.WH_SUBCON),
                 # 从哪个仓发料给供应商。**不设则 ERPNext 把 `reserve_warehouse` 推成
                 # 采购行的 `warehouse`（即成品仓）**，而电芯在原料仓 —— 发料时查不到
                 # 估值，回 417 `Valuation Rate for the Item HRD-CELL-280, is required`（实测）。
                 "set_reserve_warehouse": site_name_of(M.WH_RAW),
                 "currency": DEFAULT_CURRENCY, "conversion_rate": 1,
                 "items": [{"item_code": M.SERVICE_ITEM, "qty": M.SUBCON_QTY,
                            "rate": M.SUBCONTRACT_FEE / M.SUBCON_QTY,
                            "schedule_date": M.day(4),
                            "warehouse": site_name_of(M.WH_FINISHED),
                            "fg_item": M.FINISHED_ITEM, "fg_item_qty": M.SUBCON_QTY}]},
                "采购订单（外协）", submit=True, binds=("subcon_po=name",)),
        DocStep("Subcontracting Order",
                {"company": M.COMPANY, "supplier": M.SUPPLIER},
                {"transaction_date": M.day(3)},
                "外协订单", submit=True, binds=("subcon_order=name",),
                factory="erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order",
                factory_args={"source_name": REF_SUBCON_PO}),
        DocStep("Stock Entry",
                {"stock_entry_type": PURPOSE_SEND_TO_SUBCONTRACTOR, "posting_date": M.day(4)},
                # `stock_entry_type` 必须自己送：工厂方法回的草稿只带 `purpose`，
                # 而 Frappe 的必填校验看的是 `stock_entry_type`（实测 MandatoryError）。
                # 两个都显式送。`stock_entry_type` 是 Frappe 的必填校验看的字段
                # （实测 MandatoryError），`purpose` 虽然工厂草稿里有，但依赖草稿等于
                # 把不变量押在工厂的实现上 —— 见同文件那条「只送 stock_entry_type 时
                # 站点不带出 purpose，Material Receipt 直接回 417」。
                {"posting_date": M.day(4), "set_posting_time": 1,
                 "stock_entry_type": PURPOSE_SEND_TO_SUBCONTRACTOR,
                 "purpose": PURPOSE_SEND_TO_SUBCONTRACTOR},
                "发料到供应商仓（外协）", submit=True,
                factory="erpnext.controllers.subcontracting_controller.make_rm_stock_entry",
                factory_args={"subcontract_order": REF_SUBCON_ORDER}),
        DocStep("Subcontracting Receipt",
                {"company": M.COMPANY, "supplier": M.SUPPLIER},
                {"posting_date": M.day(5), "set_posting_time": 1},
                "外协收货", submit=True,
                factory="erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
                factory_args={"source_name": REF_SUBCON_ORDER}),
        DocStep("Delivery Note",
                {"company": M.COMPANY, "customer": M.CUSTOMER, "posting_date": M.day(6)},
                {"customer": M.CUSTOMER, "company": M.COMPANY, "posting_date": M.day(6),
                 "set_posting_time": 1, "currency": DEFAULT_CURRENCY, "conversion_rate": 1,
                 "selling_price_list": SELLING_PRICE_LIST, "price_list_currency": DEFAULT_CURRENCY,
                 "plc_conversion_rate": 1,
                 "items": [{"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
                            "qty": M.DELIVERY_QTY, "rate": M.SALES_RATE,
                            "expense_account": site_name_of(M.ACC_COGS),
                            "against_sales_order": REF_SALES_ORDER,
                            "so_detail": REF_SO_DETAIL}]},
                "发货单", submit=True, binds=("delivery_note=name",)),
        DocStep("Sales Invoice",
                {"company": M.COMPANY, "customer": M.CUSTOMER, "posting_date": M.day(6)},
                {"customer": M.CUSTOMER, "company": M.COMPANY, "posting_date": M.day(6),
                 "set_posting_time": 1, "due_date": M.day(6 + M.INVOICE_TERM_DAYS),
                 "currency": DEFAULT_CURRENCY, "conversion_rate": 1,
                 "selling_price_list": SELLING_PRICE_LIST, "price_list_currency": DEFAULT_CURRENCY,
                 "plc_conversion_rate": 1, "update_stock": 0,
                 "debit_to": site_name_of(M.ACC_RECEIVABLE),
                 "items": [{"item_code": M.FINISHED_ITEM, "qty": M.DELIVERY_QTY,
                            "rate": M.SALES_RATE,
                            "income_account": site_name_of(M.ACC_REVENUE),
                            "delivery_note": REF_DELIVERY_NOTE}]},
                "销售发票（逾期）", submit=True),
        DocStep("Purchase Invoice",
                {"company": M.COMPANY, "supplier": M.SUPPLIER, "posting_date": M.day(5)},
                {"supplier": M.SUPPLIER, "company": M.COMPANY, "posting_date": M.day(5),
                 "set_posting_time": 1, "due_date": M.day(5 + M.INVOICE_TERM_DAYS),
                 "currency": DEFAULT_CURRENCY, "conversion_rate": 1,
                 "buying_price_list": BUYING_PRICE_LIST, "price_list_currency": DEFAULT_CURRENCY,
                 "plc_conversion_rate": 1,
                 "credit_to": site_name_of(M.ACC_PAYABLE),
                 "items": [{"item_code": M.SERVICE_ITEM, "qty": 1, "rate": M.SUBCONTRACT_FEE,
                            "expense_account": site_name_of(M.ACC_OPERATING)}]},
                "采购发票（逾期）", submit=True),
    ]
    return tuple(steps)

@dataclass
class LoadReport:
    """一次装载的结果。`created` / `existing` 按 DocType 计数；`mismatches` 是不静默的那一半。"""

    created: dict[str, int] = field(default_factory=dict)
    existing: dict[str, int] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    mismatches: list[tuple[str, str, str]] = field(default_factory=list)

    def record(self, doctype: str, was_created: bool) -> None:
        if doctype not in self.order:
            self.order.append(doctype)
            self.created.setdefault(doctype, 0)
            self.existing.setdefault(doctype, 0)
        bucket = self.created if was_created else self.existing
        bucket[doctype] += 1

    @property
    def total_created(self) -> int:
        return sum(self.created.values())

    def lines(self) -> list[str]:
        out = [
            f"{doctype}：新建 {self.created[doctype]} / 已存在 {self.existing[doctype]}"
            for doctype in self.order
        ]
        for doctype, expected, actual in self.mismatches:
            out.append(
                f"⚠️ {doctype} 的站点名与 agenerp.seed 常量不符："
                f"常量 {expected!r} ≠ 站点 {actual!r}"
                "（见 docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md）"
            )
        out.append(f"合计：新建 {self.total_created} / 已存在 {sum(self.existing.values())}")
        return out


def load_masters(client: SiteClient) -> LoadReport:
    """按 `plan_steps()` 的顺序把主数据装进站点。**任一步抛就整段停**，不吞、不续跑。

    名字不符**不算装载失败**：文档建成功了，只是本仓的常量与站点派生规则对不上。
    判成失败会让一处拼写错误挡死一次正确的装载；**但它必须被看见**，所以记进
    `LoadReport.mismatches` 并由 CLI 原样打印。取舍写在
    `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md` 的 `## Fix`。

    ⚠️ **自 plan `2026-08-22-2325-1` 起这条路径没有已知的活触发点**（15 个带后缀常量全部规整）。
    保留它的理由与它仍然值得留着的判据见 §12.11：它是「站点回名 vs 本仓预期」的**通用**对账，
    不是为某一个常量造的。
    """
    report = LoadReport()
    for step in plan_steps():
        doc, created = client.ensure_doc(step.doctype, step.key, step.payload)
        report.record(step.doctype, created)
        actual = doc.get("name")
        if actual is not None and actual != step.source:
            report.mismatches.append((step.doctype, step.source, str(actual)))
    return report


@dataclass
class DocLoadReport:
    """一次单据装载的结果。三个计数分开记：**新建 / 已存在 / 补提交**。

    「补提交」不算「新建」：`find_one` 不分 `docstatus`，命中一份 `docstatus 0` 的草稿时
    装载器把它推到 1。没有这一格，一次中途失败留下的草稿会让第二跑「新建 0」照样绿。
    """

    created: dict[str, int] = field(default_factory=dict)
    existing: dict[str, int] = field(default_factory=dict)
    submitted: dict[str, int] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    lines_detail: list[str] = field(default_factory=list)

    def record(self, doctype: str, label: str, was_created: bool, was_submitted: bool,
               name: str) -> None:
        if doctype not in self.order:
            self.order.append(doctype)
            for bucket in (self.created, self.existing, self.submitted):
                bucket.setdefault(doctype, 0)
        (self.created if was_created else self.existing)[doctype] += 1
        if was_submitted:
            self.submitted[doctype] += 1
        verb = "新建" if was_created else "已存在"
        tail = " + 补提交" if was_submitted and not was_created else ""
        self.lines_detail.append(f"  {label}（{doctype}）→ {name} · {verb}{tail}")

    @property
    def total_created(self) -> int:
        return sum(self.created.values())

    def lines(self) -> list[str]:
        out = list(self.lines_detail)
        out += [
            f"{doctype}：新建 {self.created[doctype]} / 已存在 {self.existing[doctype]}"
            f" / 提交 {self.submitted[doctype]}"
            for doctype in self.order
        ]
        out.append(
            f"合计：新建 {self.total_created} / 已存在 {sum(self.existing.values())}"
            f" / 提交 {sum(self.submitted.values())}"
        )
        return out


def operating_cost_per_unit(client: SiteClient) -> float:
    """从**站点**读回它自己算的 BOM 工序成本，换算成每单位。

    ERPNext 自己的 `get_operating_cost_per_unit()` 在拿不到工单实际工时时走的正是
    `BOM.operating_cost / BOM.quantity`（容器内实读 `stock_entry.py:3776-3779`）。
    本函数复现的是那一行，**数是站点的，不是本仓的** —— `agenerp/seed` 里没有任何常量参与这里。
    """
    bom = client.get(f"/api/resource/BOM/{names.BOM}")
    doc = bom.get("data") if isinstance(bom, dict) else None
    if not isinstance(doc, dict):
        raise SiteError(f"读 BOM {names.BOM} 的响应缺少 data 对象：{str(bom)[:200]}")
    quantity = float(doc.get("quantity") or 0)
    if quantity <= 0:
        raise SiteError(f"站点上的 BOM {names.BOM} 的 quantity 是 {doc.get('quantity')!r}，无法换算工序成本")
    return float(doc.get("operating_cost") or 0) / quantity


def load_documents(client: SiteClient) -> DocLoadReport:
    """按 `document_steps()` 的顺序把业务单据装进站点并提交。**任一步抛就整段停**。

    占位符（站点才知道的名字、以及站点自己算出的工序成本）在这里边跑边绑。
    """
    report = DocLoadReport()
    # 自制批那张 `Manufacture` 分录的工序附加成本。换算方式**照抄 ERPNext 自己那一行**
    # （`bom.py:add_operations_cost` → `operating_cost_per_unit * flt(stock_entry.fg_completed_qty)`，
    # 容器内实读）；`operating_cost_per_unit()` 的输入是**站点算出来的** `BOM.operating_cost`。
    inhouse_operating_cost = operating_cost_per_unit(client) * M.INHOUSE_QTY
    bindings: dict[str, Any] = {"operating_cost": inhouse_operating_cost}
    for step in document_steps():
        payload = resolve_refs(step.payload, bindings)
        # **幂等先于工厂**：单据已在站点上时不得再调工厂方法。实测（2026-08-23）
        # 重跑装载会撞 `This PO has been fully subcontracted` —— 工厂方法**有副作用感知**，
        # 它按源单的已外协量判定，不是纯函数。`ensure_doc` 的幂等在它之后就太晚了。
        if step.factory and client.find_one(step.doctype, step.key) is None:
            draft = client.call_method(step.factory, resolve_refs(step.factory_args or {}, bindings))
            if not isinstance(draft, dict):
                raise SiteError(f"{step.label}：工厂方法 {step.factory} 没回一份文档草稿：{str(draft)[:160]}")
            payload = {**_strip_framework_keys(draft), **payload}
        doc, created = client.ensure_doc(step.doctype, step.key, payload)
        name = str(doc.get("name"))
        submitted = False
        if step.submit and int(doc.get("docstatus") or 0) == 0:
            doc = client.submit_doc(step.doctype, name)
            submitted = True
        report.record(step.doctype, step.label, created, submitted, name)
        if step.binds:
            full = client.get(f"/api/resource/{step.doctype}/{name}").get("data", doc)
            for spec in step.binds:
                key, _, path = spec.partition("=")
                bindings[key] = _pick(full, path)
    return report


# ── 站点侧对账（`--verify-site`）─────────────────────────────────────────────
#
# ⚠️ **期望值一律从 `agenerp.seed.checks` 取，本模块里不得出现第二份**。
# `checks.py:23-24` 自述「刻意不从 `agenerp.seed.model` 取数」——它才是判官侧那份副本；
# 在这里写一个新的字面量等于给判据加第四份副本，改一处就能让对账静默变绿。
# `tests/unit/test_seedsite_documents.py` 有一条结构断言把这件事钉死。


@dataclass(frozen=True)
class CheckResult:
    """一条对账结果。**成功与失败都打出带出处的实得值与期望值** —— 只打「通过」用 grep 就能伪造。"""

    label: str
    actual: str
    expected: str
    source: str
    ok: bool

    def line(self) -> str:
        return (f"{'✅' if self.ok else '❌'} {self.label} = {self.actual}"
                f" / expected = {self.expected}（出处：{self.source}）")


def _close(actual: float, expected: float) -> bool:
    return abs(actual - expected) < M.MONEY_TOLERANCE


def _numeric_check(label: str, actual: float, expected: float, source: str) -> CheckResult:
    return CheckResult(label, f"{actual:.2f}", f"{expected:.2f}", source, _close(actual, expected))


def _finished_bin(client: SiteClient) -> dict | None:
    for row in client.list_resource(
        "Bin", ("item_code", "warehouse", "actual_qty", "stock_value", "valuation_rate")
    ):
        if row["item_code"] == M.FINISHED_ITEM and row["warehouse"] == M.WH_FINISHED:
            return row
    return None


def _live_gl_rows(client: SiteClient) -> list[dict]:
    rows = client.list_resource(
        "GL Entry", ("account", "debit", "credit", "voucher_type", "voucher_no", "is_cancelled")
    )
    return [row for row in rows if not row.get("is_cancelled")]


def _account_side(rows: list[dict], account: str, side: str) -> float:
    return sum(float(row[side]) for row in rows if row["account"] == account)


def _backlog_checks(client: SiteClient) -> list[CheckResult]:
    """承重判据：站点自己算出的成品仓结存。**这是整个工作项存在的理由。**"""
    where = f"Bin({M.FINISHED_ITEM}, {M.WH_FINISHED})"
    row = _finished_bin(client)
    if row is None:
        return [CheckResult(f"{where}.actual_qty", "站点上没有这条 Bin",
                            f"{CH.EXPECTED_BACKLOG_QTY:.2f}",
                            "agenerp.seed.checks.EXPECTED_BACKLOG_QTY", False)]
    return [
        _numeric_check(f"{where}.actual_qty", float(row["actual_qty"]),
                       CH.EXPECTED_BACKLOG_QTY, "agenerp.seed.checks.EXPECTED_BACKLOG_QTY"),
        _numeric_check(f"{where}.stock_value", float(row["stock_value"]),
                       CH.EXPECTED_BACKLOG_VALUE, "agenerp.seed.checks.EXPECTED_BACKLOG_VALUE"),
    ]


def _books_checks(client: SiteClient) -> list[CheckResult]:
    """拟断言 ② 中**站点算得出来**的三项。达成率那一项按 D2 明确移出本 plan 结果面。"""
    rows = _live_gl_rows(client)
    debit = sum(float(row["debit"]) for row in rows)
    credit = sum(float(row["credit"]) for row in rows)
    revenue = _account_side(rows, site_name_of(M.ACC_REVENUE), "credit")
    cogs = _account_side(rows, site_name_of(M.ACC_COGS), "debit")
    negative = [
        row for row in client.list_resource("Bin", ("item_code", "warehouse", "actual_qty"))
        if float(row["actual_qty"]) < 0
    ] + [
        row for row in client.list_resource(
            "Stock Ledger Entry", ("item_code", "warehouse", "qty_after_transaction", "is_cancelled"))
        if not row.get("is_cancelled") and float(row["qty_after_transaction"]) < 0
    ]
    return [
        _numeric_check("GL 借贷差额（借合计 − 贷合计）", debit - credit, 0.0,
                       "复式记账的结构不变量（不是业务期望值，故无 checks.EXPECTED_* 出处）"),
        CheckResult("负库存条目数（Bin.actual_qty < 0 + SLE.qty_after_transaction < 0）",
                    str(len(negative)), "0",
                    "复式记账的结构不变量（不是业务期望值，故无 checks.EXPECTED_* 出处）",
                    not negative),
        _numeric_check(f"GL 收入贷方合计（{site_name_of(M.ACC_REVENUE)}）", revenue,
                       CH.EXPECTED_RECEIVABLE_OVERDUE,
                       "agenerp.seed.checks.EXPECTED_RECEIVABLE_OVERDUE"),
        _numeric_check(f"GL 成本借方合计（{site_name_of(M.ACC_COGS)}）", cogs,
                       CH.EXPECTED_COGS, "agenerp.seed.checks.EXPECTED_COGS"),
        _numeric_check("毛利（GL 收入贷方 − GL 成本借方）", revenue - cogs,
                       CH.EXPECTED_GROSS_PROFIT, "agenerp.seed.checks.EXPECTED_GROSS_PROFIT"),
    ]


OVERDUE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")

# 诊断里那个「今天」的口径。2026-08-23 实测（plan `2026-08-23-0120-2` Proof B④）：
# `frappe.utils.nowdate` 没有 whitelist，HTTP 面读不到站点侧的「今天」；`SiteClient` 也没有
# 带 filter 的列表方法。所以这里用的是**宿主时钟**，必须逐字标注，不许冒充站点口径。
TODAY_CALIBER = "宿主侧"


def _overdue_identity_keys() -> dict[str, dict[str, Any]]:
    """两张预期发票在站点上的识别键 —— **直接取装载器自己的幂等键**，不另写一份字面量。

    不拿 `agenerp/seed/names.py` 的单据号做键：`DocStep` 的 docstring 已经写明那几个号是
    「按顺序建」的巧合、不是站点承诺。也不拿站点的 `status == "Overdue"` 过滤结果做候选集 ——
    那样站点回零张 `Overdue` 时候选集为空，诊断恰好在它唯一存在理由的那个场景下空转。
    """
    return {step.doctype: dict(step.key)
            for step in document_steps() if step.doctype in OVERDUE_DOCTYPES}


def _matches_key(row: dict, key: dict[str, Any]) -> bool:
    return all(str(row[field]) == str(value) for field, value in key.items())


def _overdue_row_facts(row: dict, today: str) -> str:
    due = str(row["due_date"])
    submitted = int(row["docstatus"]) == 1
    return (f"{row['name']}：status={row['status']}"
            f" / due_date={due}（{'已到期' if due < today else '未到期'}，"
            f"今天 {today}（{TODAY_CALIBER}））"
            f" / docstatus={row['docstatus']}（{'已提交' if submitted else '未提交'}）"
            f" / outstanding_amount={float(row['outstanding_amount']):.2f}")


def _overdue_diagnosis(rows: list[dict], key: dict[str, Any], today: str) -> str:
    """本仓预期的那张发票在站点上的实况 —— 只进 `label`，不参与 `ok` 的计算。

    读不到字段就让它抛：诊断自己坏掉必须红出来，不能 `try/except: pass` 成一句「无」。
    """
    expected_rows = [r for r in rows if _matches_key(r, key)]
    facts = [_overdue_row_facts(r, today) for r in expected_rows]
    if not facts:
        facts = [f"按装载器幂等键 {key} 在站点上认不出这张发票"]
    unexpected = [r["name"] for r in rows
                  if int(r["docstatus"]) == 1 and not _matches_key(r, key)]
    if unexpected:
        facts.append(f"另有 {len(unexpected)} 张不在预期内的已提交单据：{', '.join(unexpected)}")
    return "；".join(facts)


def _overdue_checks(client: SiteClient, today: str | None = None) -> list[CheckResult]:
    """拟断言 ③：两笔逾期由站点上的 `status == "Overdue"` 查到。

    ⚠️ **成立条件照实说**：`status` 是站点拿**真实时钟**跟 `due_date` 比出来的，
    不是拿数据集的 `as_of` 比的。种子日期固定在过去，故恒成立 —— 但这条断言依赖
    「今天 > due_date」，不写出来会被误读成结构性成立。
    **2026-08-23 已实测取证**（plan `2026-08-23-0120-2` Proof A/B/C，分流 (i)）：写 `status` 的是
    **提交时的同步调用链** `validate()` → `set_status()` → `is_overdue()`
    （容器内 ERPNext v15.119.3 `erpnext/accounts/doctype/sales_invoice/sales_invoice.py:350`
    / `:2037-2038` / `:2077-2100`，`purchase_invoice.py:292` / `:2012-2013` 且 `:22` 直接 import 同一个
    `is_overdue`），比的是 `today = getdate()`（真实时钟）；`scheduler` 的日任务
    `erpnext.controllers.accounts_controller.update_invoice_status`（`erpnext/hooks.py:447`）**不参与** ——
    它的 `conditions` 只更新 `status LIKE "Unpaid%" / "Partly Paid%"` 的行。
    ⚠️ 精确形态：本仓两张发票都有 `payment_schedule`，`is_overdue` 走的是子表分支，
    比的是 `payment_schedule.due_date`（实测与发票头上的 `due_date` 同值）。

    `today` 可注入，默认取宿主时钟；它**只进诊断文字**，不进 `ok`。
    """
    today = today or date.today().isoformat()
    keys = _overdue_identity_keys()
    results = []
    for doctype, expected, source in (
        ("Sales Invoice", CH.EXPECTED_RECEIVABLE_OVERDUE,
         "agenerp.seed.checks.EXPECTED_RECEIVABLE_OVERDUE"),
        ("Purchase Invoice", CH.EXPECTED_PAYABLE_OVERDUE,
         "agenerp.seed.checks.EXPECTED_PAYABLE_OVERDUE"),
    ):
        rows = client.list_resource(
            doctype, ("name", "status", "outstanding_amount", "due_date", "docstatus",
                      *keys[doctype]))
        overdue = [r for r in rows if r["status"] == "Overdue" and int(r["docstatus"]) == 1]
        total = sum(float(r["outstanding_amount"]) for r in overdue)
        results.append(_numeric_check(
            f"{doctype} 中 status == 'Overdue' 的 outstanding_amount 合计"
            f"（命中 {len(overdue)} 张：{', '.join(r['name'] for r in overdue) or '无'}"
            f"；本仓预期 —— {_overdue_diagnosis(rows, keys[doctype], today)}）",
            total, expected, source))
    return results


def _document_graph_checks(client: SiteClient) -> list[CheckResult]:
    """**文档图对账**：站点上每种 DocType 的条数，必须与离线数据集逐一相等。

    这条判据是 D-12 的直接产物，补的是一道**结构性的缝**。在它之前，站点与离线
    数据集对同一桩业务可以讲两个不同的故事而两边都绿：外协批在离线是
    `Subcontracting Order` + `Subcontracting Receipt`，在站点上却是第二张工单 ——
    财务与库存口径完全一致，所以 `_backlog_checks` / `_books_checks` 全都过。

    **谁读谁，决定了这道缝有多深**：洞察 Agent 读的是站点。规则写在
    `Subcontracting Order` 上时，站点零命中而单测（跑离线数据集）照样绿。
    测试通过、线上零命中，且无任何信号 —— 这正是本判据要挡的形状。

    条数是最粗但最不可绕过的一层。它不保证字段一致，只保证**两边讲的是同一个
    故事的同一批单据**。字段级一致由各单据自己的判据管。
    """
    dataset = seed_generate()
    results: list[CheckResult] = []
    for doctype in dataset.doctypes():
        if doctype in _DERIVED_DOCTYPES:
            continue
        expected = len(dataset.of(doctype))
        actual = len(client.list_resource(doctype, fields=("name",)))
        results.append(CheckResult(
            label=f"{doctype} 的文档条数",
            actual=str(actual),
            expected=str(expected),
            source=f"agenerp.seed 生成的数据集（{doctype}）",
            ok=actual == expected,
        ))
    return results


# 站点自己派生、离线数据集不建模的 DocType —— 不参与条数对账。
# 逐条列名而不是按前缀排除：新增一种就必须显式决定它算不算，不留静默通道。
_DERIVED_DOCTYPES = frozenset({
    "Bin",              # 站点按库存流水实时维护
    "GL Entry",         # 提交单据时由站点自动生成
    "Stock Ledger Entry",  # 同上
    "Item", "Warehouse", "BOM",  # 主数据段装，不在单据段
})


def _link_field_checks(client: SiteClient) -> list[CheckResult]:
    """**跨单据 Link 字段对账**：离线数据集里指向另一张单据的字段，站点上必须相同。

    这条补的是 `_document_graph_checks` 的盲区 —— 那条只比每种 DocType 的**条数**。
    2026-08-24 实测到的分歧正是它抓不到的形状：离线 `Work Order.sales_order =
    "SAL-ORD-2026-00001"`，**站点上是 NULL**（装载器未送该字段），而两边条数一致，
    于是全绿。

    **为什么这个盲区要紧**：`doc.links` 走的就是这些字段。少一个 Link，Agent 从
    某张单出发能看到的下游就少一片 —— 这不是「数据小瑕疵」，是**证据面的缺口**。
    P1.0 的实验难度直接由它决定。

    **判据不硬写字段清单，从数据集自己推**：凡某字段的值恰好等于数据集里另一份
    单据的 `name`，即认定为跨单据 Link。将来新增关联自动被覆盖，不需要有人记得
    回来加一行 —— 硬写清单的判据会随数据集演进而静默失效。
    """
    dataset = seed_generate()
    all_names = {
        str(row["name"]): doctype
        for doctype in dataset.doctypes()
        for row in dataset.of(doctype)
        if row.get("name")
    }
    results: list[CheckResult] = []
    for doctype in dataset.doctypes():
        if doctype in _DERIVED_DOCTYPES:
            continue
        for row in dataset.of(doctype):
            name = str(row.get("name") or "")
            links = {
                field: value for field, value in row.items()
                if field != "name" and isinstance(value, str) and value in all_names
            }
            if not links:
                continue
            site_doc = client.get(f"/api/resource/{doctype}/{name}").get("data", {})
            for field, expected in sorted(links.items()):
                actual = site_doc.get(field)
                results.append(CheckResult(
                    label=f"{doctype} {name}.{field}",
                    actual=repr(actual),
                    expected=repr(expected),
                    source=f"agenerp.seed 生成的数据集（{doctype}.{field} → {all_names[expected]}）",
                    ok=actual == expected,
                ))
    return results


def verify_site(client: SiteClient, today: str | None = None) -> list[CheckResult]:
    """站点侧对账：读回**站点自己算出来**的数，跟 `checks.EXPECTED_*` 比。"""
    return (_backlog_checks(client) + _books_checks(client) + _overdue_checks(client, today)
            + _document_graph_checks(client) + _link_field_checks(client))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m agenerp.seedsite",
        description="把 agenerp.seed 的主数据与业务单据装进活站点，并做站点侧对账（幂等）",
    )
    parser.add_argument("--load-masters", action="store_true", help="装载主数据段（只建不改，不提交）")
    parser.add_argument("--load-documents", action="store_true",
                        help="装载业务单据段并提交（前置：--load-masters 已跑过）")
    parser.add_argument("--verify-site", action="store_true",
                        help="站点侧对账：读回站点自己算出的数，跟 agenerp.seed.checks 的期望值比")
    parser.add_argument("--site", default="", help="站点名（必填，例如 frontend）")
    return parser


ACTIONS = ("load_masters", "load_documents", "verify_site")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    chosen = [name for name in ACTIONS if getattr(args, name)]
    if len(chosen) != 1:
        print("需要且只需要一个动作：--load-masters / --load-documents / --verify-site",
              file=sys.stderr)
        return 2
    if not args.site:
        print("需要 --site <站点名>：不猜站点，产品代码不内置默认站点", file=sys.stderr)
        return 2
    try:
        client = client_from_env(args.site)
        if args.load_masters:
            lines, code = load_masters(client).lines(), 0
        elif args.load_documents:
            lines, code = load_documents(client).lines(), 0
        else:
            results = verify_site(client)
            lines = [r.line() for r in results]
            failed = [r for r in results if not r.ok]
            lines.append(
                f"站点侧对账：{len(results)} 项，通过 {len(results) - len(failed)}，失败 {len(failed)}"
            )
            code = 1 if failed else 0
    except SiteError as exc:  # 失败即停：不留半装状态，不吞错误原文
        print(f"失败，已停在出错那一步：{exc}", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
