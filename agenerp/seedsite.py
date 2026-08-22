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
from dataclasses import dataclass, field
from typing import Any

from agenerp.seed import masters, names
from agenerp.seed import model as M
from agenerp.site import SiteClient, SiteError, client_from_env

# ── 本模块自有的纯 ERPNext 结构常量（不参与任何断言，§12.9 逐条列名）────────────
ABBR = "XM"
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
WORKSTATION = "XM 织造机台"

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

    ⚠️ 容忍两种写法（` - XM` 与 `- XM`），**不是宽容，是被迫**：
    `M.ACC_OPERATING` 逐字为 `生产费用（计入估值）- XM`，**少一个空格**，
    而 ERPNext 的 `Account.autoname` 走 `" - ".join(...)`，只可能产出带空格的名字。
    这是 `agenerp/seed/model.py` 的一处真缺陷，登记在
    `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`；
    本 plan 的 Closure Gate 要求 `agenerp/seed/**` 一个字节未改，故**只容忍、只报告，不修改**。
    严格 `removesuffix(" - XM")` 会让那个常量整串被当成 `<x>_name` 送进站点，
    建出 `生产费用（计入估值）- XM - XM` —— 那才是真的坏。
    """
    for suffix in (f" - {ABBR}", f"- {ABBR}"):
        if derived.endswith(suffix):
            return derived[: -len(suffix)].rstrip()
    return derived


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
    # `agenerp.seed` 里那个**原始常量**。多数时候与 `expected_name` 相同；
    # 两者不同就说明本仓的常量**不可能**被 ERPNext 派生出来（`M.ACC_OPERATING` 少一个空格）。
    # 比对拿它做基准，不拿 `expected_name` —— 拿后者比对是自己跟自己比，永远相等。
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
    """
    report = LoadReport()
    for step in plan_steps():
        doc, created = client.ensure_doc(step.doctype, step.key, step.payload)
        report.record(step.doctype, created)
        actual = doc.get("name")
        if actual is not None and actual != step.source:
            report.mismatches.append((step.doctype, step.source, str(actual)))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m agenerp.seedsite",
        description="把 agenerp.seed 的主数据装进活站点（幂等，只建不改）",
    )
    parser.add_argument("--load-masters", action="store_true", help="装载主数据段")
    parser.add_argument("--site", default="", help="站点名（必填，例如 frontend）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.load_masters:
        print("需要 --load-masters：本模块此刻只有主数据装载这一个动作", file=sys.stderr)
        return 2
    if not args.site:
        print("需要 --site <站点名>：不猜站点，产品代码不内置默认站点", file=sys.stderr)
        return 2
    try:
        client = client_from_env(args.site)
        report = load_masters(client)
    except SiteError as exc:  # 失败即停：不留半装状态，不吞错误原文
        print(f"装载失败，已停在出错那一步：{exc}", file=sys.stderr)
        return 1
    for line in report.lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
