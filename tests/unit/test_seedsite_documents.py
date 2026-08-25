"""非门禁测试 · 钉死单据装载器与站点侧对账的**纯逻辑半**（`agenerp/seedsite.py` 单据段）。

**不连站点**：装载顺序、占位符绑定、幂等计数、补提交、失败即停、以及
「`--verify-site` 的期望值确实来自 `checks.EXPECTED_*` 而非本地字面量」这条**结构约束**，
六件事全都可以在假传输上判死。活站点那一半由 plan `2026-08-22-2107-2` Phase 3 的 CLI 实跑负责
（退出码 + 第二跑「新建 0」+ 三条变异验证），两者不互相冒充 —— **本文件通过不等于装载器在真站点上跑得通。**
"""

import ast
import json
from pathlib import Path

import pytest

from agenerp import seedsite
from agenerp.seed import checks as CH
from agenerp.seed import generate as seed_generate
from agenerp.seed import model as M
from agenerp.seed import names
from agenerp.site import SiteClient, SiteError, SiteResponse

SEEDSITE_SOURCE = Path(seedsite.__file__).read_text(encoding="utf-8")


class FakeDocSite:
    """够用的假站点：按业务键答存在性、按命名序列回 `name`、支持 `PUT docstatus`。

    **刻意照抄实测的命名行为**：显式 `name` 一律不采纳（2026-08-22 活站点实测），
    否则单测会在一条站点根本不遵守的假设上变绿。
    """

    SERIES = {
        "Stock Entry": "MAT-STE-2026-{:05d}", "Sales Order": "SAL-ORD-2026-{:05d}",
        "Work Order": "MFG-WO-2026-{:05d}", "Delivery Note": "MAT-DN-2026-{:05d}",
        "Sales Invoice": "ACC-SINV-2026-{:05d}", "Purchase Invoice": "ACC-PINV-2026-{:05d}",
        # D-12：外协四步链
        "Purchase Order": "PUR-ORD-2026-{:05d}",
        "Subcontracting Order": "SC-ORD-2026-{:05d}",
        "Subcontracting Receipt": "MAT-SCR-2026-{:05d}",
    }

    # 服务端工厂方法的替身。**只回站点会回的那几个字段**，不多不少 ——
    # 假站点越像真站点，判据越可信；多回字段会掩盖「装载器漏送必填」这类缺陷。
    FACTORY_DRAFTS = {
        "erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order": {
            "doctype": "Subcontracting Order", "name": "new-subcontracting-order-1",
            "supplier": M.SUPPLIER, "company": M.COMPANY, "docstatus": 0,
            "items": [{"item_code": M.FINISHED_ITEM, "qty": M.SUBCON_QTY, "bom": names.BOM}],
            "service_items": [{"item_code": M.SERVICE_ITEM, "qty": M.SUBCON_QTY,
                               "rate": M.SUBCONTRACT_FEE / M.SUBCON_QTY}],
        },
        "erpnext.controllers.subcontracting_controller.make_rm_stock_entry": {
            "doctype": "Stock Entry", "name": "new-stock-entry-1", "purpose": "Send to Subcontractor",
            "docstatus": 0,
            "items": [{"item_code": M.RAW_ITEM, "qty": M.BOM_RAW_QTY}],
        },
        "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt": {
            "doctype": "Subcontracting Receipt", "name": "new-subcontracting-receipt-1",
            "supplier": M.SUPPLIER, "company": M.COMPANY, "docstatus": 0,
            "items": [{"item_code": M.FINISHED_ITEM, "qty": M.SUBCON_QTY}],
        },
    }

    def __init__(self, fail_on: str | None = None, bom_operating_cost: float = 800.0,
                 bom_quantity: float = 1000.0, drafts: tuple[str, ...] = ()):
        self.docs: dict[str, dict] = {}
        self.requests: list = []
        self.fail_on = fail_on
        self.bom = {"name": names.BOM, "operating_cost": bom_operating_cost,
                    "quantity": bom_quantity}
        self.leave_draft = set(drafts)

    def __call__(self, request):
        self.requests.append(request)
        if "/api/method/" in request.url and "update_status" in request.url:
            # 关单是**只有副作用**的调用：Frappe 对无返回值的方法回 `{}`。
            # 这里同时把副作用做出来，否则装载器读回状态时会判失败 ——
            # 假站点不模拟副作用，等于让判据测一个不存在的世界。
            import json as _json
            body = _json.loads(request.body or "{}")
            doc = self.docs.get(body.get("name", ""))
            if doc is not None:
                doc["status"] = body.get("status")
            return SiteResponse(200, "{}")
        if "/api/method/" in request.url:
            method = request.url.split("/api/method/", 1)[1].split("?")[0]
            if method not in self.FACTORY_DRAFTS:
                return SiteResponse(200, json.dumps({}))   # 方法名写错时 Frappe 就回这个
            return SiteResponse(200, json.dumps({"message": self.FACTORY_DRAFTS[method]}))
        from urllib.parse import parse_qs, unquote, urlparse

        path = unquote(urlparse(request.url).path)
        doctype = path.split("/api/resource/")[1].split("/")[0]
        tail = path.split("/api/resource/")[1][len(doctype):].lstrip("/")
        if request.method == "GET" and tail:
            if doctype == "BOM":
                return SiteResponse(200, json.dumps({"data": self.bom}))
            return SiteResponse(200, json.dumps({"data": self.docs[tail]}))
        if request.method == "GET":
            query = parse_qs(urlparse(unquote(request.url)).query)
            filters = json.loads(query["filters"][0]) if "filters" in query else []
            hits = [d for d in self.docs.values()
                    if d["doctype"] == doctype
                    and all(str(d.get(f[0])) == str(f[2]) for f in filters)]
            return SiteResponse(200, json.dumps({"data": hits[:1] if filters else hits}))
        if request.method == "PUT":
            doc = self.docs[tail]
            doc["docstatus"] = json.loads(request.body)["docstatus"]
            return SiteResponse(200, json.dumps({"data": doc}))
        if doctype == self.fail_on:
            return SiteResponse(417, '{"exc_type":"ValidationError"}')
        payload = json.loads(request.body)
        doc = {**payload, "doctype": doctype, "name": self._derive(doctype, payload),
               "docstatus": 0}
        for idx, row in enumerate(doc.get("items") or []):
            row.setdefault("name", f"{doc['name']}-item-{idx}")
        self.docs[doc["name"]] = doc
        return SiteResponse(200, json.dumps({"data": doc}))

    @property
    def posts(self):
        """**只数建档 POST**，不数工厂方法调用。

        D-12 后工厂方法也走 POST（`/api/method/`），混在一起数会让「一步一 POST」
        这条不变量失去意义。工厂调用次数由
        `test_the_factory_is_not_called_when_the_document_already_exists` 单独把守。
        """
        return [r for r in self.requests
                if r.method == "POST" and "/api/method/" not in r.url]

    @property
    def puts(self):
        return [r for r in self.requests if r.method == "PUT"]

    def _derive(self, doctype: str, payload: dict) -> str:
        if doctype in self.SERIES:
            seq = 1 + sum(1 for d in self.docs.values() if d["doctype"] == doctype)
            return self.SERIES[doctype].format(seq)
        for key in ("year", "price_list_name", "name"):
            if key in payload:
                return str(payload[key])
        raise AssertionError(f"假站点不知道 {doctype} 怎么命名：{payload}")


def _client(transport):
    return SiteClient("frontend", base_url="http://127.0.0.1:18080",
                      api_key="k", api_secret="s", transport=transport)


def _by_label(label: str):
    return next(s for s in seedsite.document_steps() if s.label == label)


def _order():
    return [s.label for s in seedsite.document_steps()]


def test_dependency_order_is_the_one_the_site_actually_requires():
    """结构前置在最前、两批各自「工单 → 转料 → 入库」、发货在两批之后、发票在发货之后。"""
    order = _order()

    def idx(label):
        return order.index(label)

    assert idx(f"会计年度 {seedsite.FISCAL_YEAR}") == 0
    for earlier, later in (
        (f"价格表 {seedsite.SELLING_PRICE_LIST}", "销售订单"),
        ("期初原料入库", "原料转在制品仓（自制批）"),
        ("工单（自制批）", "原料转在制品仓（自制批）"),
        ("原料转在制品仓（自制批）", "自制批入库"),
        # 外协四步链（D-12）：每一步都依赖前一步的站点回值
        ("采购订单（外协）", "外协订单"),
        ("外协订单", "发料到供应商仓（外协）"),
        ("发料到供应商仓（外协）", "外协收货"),
        ("自制批入库", "发货单"),
        ("外协收货", "发货单"),
        ("销售订单", "发货单"),
        ("发货单", "销售发票（逾期）"),
        ("外协收货", "采购发票（逾期）"),
    ):
        assert idx(earlier) < idx(later), f"{earlier} 必须早于 {later}"


def test_fifo_ordering_puts_the_inhouse_batch_before_the_subcontract_batch():
    """FIFO 的成立条件：自制批（¥3,020）必须**先入库**，否则发货 990 米出的就不是那一层。"""
    inhouse = _by_label("自制批入库").payload["posting_date"]
    subcon = _by_label("外协收货").payload["posting_date"]

    assert inhouse < subcon, f"自制批 {inhouse} 必须早于外协批 {subcon}"
    assert subcon < _by_label("发货单").payload["posting_date"]


def test_no_document_step_keys_on_name_because_the_site_ignores_explicit_name():
    """E4 实测：站点不采纳显式 `name`。幂等键因此不许出现 `name`（除结构前置那三类）。"""
    keyed_by_name = [s.label for s in seedsite.document_steps()
                     if "name" in s.key and s.doctype not in
                     ("Fiscal Year", "Stock Entry Type", "Price List")]

    assert keyed_by_name == [], keyed_by_name
    assert all("name" not in s.payload for s in seedsite.document_steps()
               if s.doctype not in ("Stock Entry Type",))


def test_the_factory_is_not_called_when_the_document_already_exists():
    """**幂等先于工厂。** 单据已在站点上时，不得再调服务端工厂方法。

    这条守的是一个实测踩到的缺陷（2026-08-23）：把工厂调用放在 `ensure_doc`
    之前时，重跑装载会撞 `This PO has been fully subcontracted` —— 因为工厂方法
    **有副作用感知**，它按源单的已外协量判定，不是纯函数。幂等在它之后就太晚了。

    判据取「`/api/method/` 的调用次数」，不取「装载是否报错」：报错只是这个缺陷
    在真站点上的表现，假站点未必复现；而多调一次工厂是缺陷本身。
    """
    site = FakeDocSite()
    client = _client(site)
    seedsite.load_documents(client)
    # **排除关单**：`update_status` 是只有副作用的调用，不是"由另一张单派生
    # 出一份草稿"的工厂方法。混进来会让这条判据在加任何一个副作用调用时假红。
    first_run_factory_calls = len([r for r in site.requests
                                   if "/api/method/" in r.url and "update_status" not in r.url])
    assert first_run_factory_calls == 3, (
        f"外协四步链应调三次工厂方法（外协订单/发料/收货），实为 {first_run_factory_calls}"
    )

    seedsite.load_documents(client)
    total = len([r for r in site.requests
                 if "/api/method/" in r.url and "update_status" not in r.url])

    assert total == first_run_factory_calls, (
        f"第二次装载又调了 {total - first_run_factory_calls} 次工厂方法 —— "
        "幂等检查跑在工厂之后了"
    )


def test_stock_entry_keys_are_pairwise_distinct():
    keys = [tuple(sorted(s.key.items())) for s in seedsite.document_steps()
            if s.doctype == "Stock Entry"]

    assert len(keys) == len(set(keys)), keys


def test_every_stock_entry_sends_both_stock_entry_type_and_purpose():
    """实测：只送 `stock_entry_type` 时站点不带出 `purpose`，`Material Receipt` 直接回 417。"""
    for step in seedsite.document_steps():
        if step.doctype == "Stock Entry":
            assert step.payload["stock_entry_type"] == step.payload["purpose"], step.label


def test_manufacture_entries_never_send_the_finished_item_rate():
    """站点自己算成品单位成本。送 `basic_rate` 等于用本仓的数覆盖站点的数，B 半就白做了。"""
    finished = next(row for row in _by_label("自制批入库").payload["items"]
                    if row["item_code"] == M.FINISHED_ITEM)
    assert "basic_rate" not in finished and "valuation_rate" not in finished
    assert "amount" not in finished

    # 外协收货由工厂方法派生（D-12），本仓**一行 items 都不送** —— 比「不送
    # basic_rate」更强的形式。站点自己算出 rm_cost_per_qty 2,960 + service_cost_per_qty
    # 120 = rate 3,080（活站点实测）。
    assert "items" not in _by_label("外协收货").payload


def test_work_order_payload_does_not_carry_required_items():
    """`required_items` 由站点从 BOM 派生（实测 `required_qty 120.0 / rate 35.0 / amount 4200.0`）。"""
    assert "required_items" not in _by_label("工单（自制批）").payload


def test_the_inhouse_operating_cost_is_a_placeholder_not_a_local_number():
    """工序成本必须是**从站点读回来的**那个数，不是本仓算出来的。"""
    cost = _by_label("自制批入库").payload["additional_costs"][0]

    assert cost["amount"] == seedsite.REF_OPERATING_COST
    assert cost["expense_account"] == seedsite.site_name_of(M.ACC_OPERATING)


def test_the_subcontract_fee_is_an_input_constant_from_the_seed_package():
    """外协服务费是 §12.1 的**输入**，从 `model.py` 取；派生费率一个都不许出现。

    D-12 后它的落点变了：从前塞在外协那张 `Manufacture` 分录的 `additional_costs`
    里，现在走**外协采购订单的服务行**（`rate = 费用 / 数量`）—— 那才是 ERPNext
    表达外协加工费的地方。收货单的估值由站点自己算（实测
    `rm_cost_per_qty 2,960 + service_cost_per_qty 120 = rate 3,080`）。
    """
    service_row = _by_label("采购订单（外协）").payload["items"][0]

    assert service_row["item_code"] == M.SERVICE_ITEM
    assert service_row["qty"] * service_row["rate"] == M.SUBCONTRACT_FEE
    # 收货单一分钱都不由本仓送 —— 送了就是用本仓的数覆盖站点的数。
    assert "additional_costs" not in _by_label("外协收货").payload


DERIVED_CONSTANTS = ("BACKLOG_QTY", "BACKLOG_VALUE", "COGS_VALUE", "GROSS_PROFIT",
                     "INHOUSE_RATE", "SUBCON_RATE", "INHOUSE_VALUE", "SUBCON_VALUE")


def _is_money_literal(node, forbidden: set) -> bool:
    """源码里的这个数字字面量，是不是那组被禁数值之一？

    ⚠️ **口径限定，照实写**：`M.INHOUSE_RATE` 恰好等于 `5.0`，而 `5` 这个**裸整数**在本模块里
    是日期偏移（`M.day(5)`）。把裸整数一并判违规会让这条断言在一个跟钱无关的地方误报，
    于是它很快会被人放宽掉 —— 那比现在这个口径更糟。
    因此只判**带小数点写出来的 `float`**（`3020.0` / `3110200.0` 这种钱的写法）**或 ≥ 100 的整数**。
    代价是「有人把 `INHOUSE_RATE` 写成裸 `5` 再乘出来」这条路它抓不到 ——
    那条路由上面那两条 `M.<NAME>` / `model.<NAME>` 的文本断言与关闭时的人工 `grep` 兜。
    """
    if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
        return False
    if not isinstance(node.value, (int, float)):
        return False
    if isinstance(node.value, int) and node.value < 100:
        return False
    return float(node.value) in forbidden


def test_no_derived_quantity_is_ever_fed_to_the_site():
    """**把答案喂给站点再读回来，等于什么都没证明。**

    八个派生量分两组守：`BACKLOG_*` / `COGS_VALUE` / `GROSS_PROFIT` 是终值，
    `INHOUSE_RATE` / `SUBCON_RATE` / `INHOUSE_VALUE` / `SUBCON_VALUE` 是**单位成本类**
    —— 只守前四个而放任后四个，会让闸子在「站点被喂了除最后一次减法之外的一切」时照样绿。
    """
    for name in DERIVED_CONSTANTS:
        assert f"M.{name}" not in SEEDSITE_SOURCE, f"agenerp/seedsite.py 里出现了派生量 M.{name}"
        assert f"model.{name}" not in SEEDSITE_SOURCE, name

    numbers = {getattr(M, name) for name in DERIVED_CONSTANTS}
    offenders = [f"{node.lineno}:{node.value}" for node in ast.walk(ast.parse(SEEDSITE_SOURCE))
                 if _is_money_literal(node, numbers)]

    assert offenders == [], f"派生量的字面量出现在 agenerp/seedsite.py：{offenders}"


def test_verify_site_takes_every_expectation_from_checks_and_never_from_a_local_literal():
    """结构约束：`--verify-site` 的期望值必须来自 `agenerp.seed.checks.EXPECTED_*`。

    `checks.py:23-24` 自述「刻意不从 `agenerp.seed.model` 取数」——它才是判官侧那份副本。
    在 `seedsite.py` 里写一个新的期望字面量等于给判据加第四份副本，改一处就能让对账静默变绿。
    """
    expected = {name: getattr(CH, name) for name in dir(CH)
                if name.startswith("EXPECTED_") and isinstance(getattr(CH, name), float)}
    tree = ast.parse(SEEDSITE_SOURCE)

    literals = [f"{node.lineno}:{node.value}" for node in ast.walk(tree)
                if _is_money_literal(node, set(expected.values()))]
    assert literals == [], f"期望值的字面量出现在 agenerp/seedsite.py：{literals}"

    referenced = {node.attr for node in ast.walk(tree)
                  if isinstance(node, ast.Attribute) and node.attr.startswith("EXPECTED_")}
    assert {"EXPECTED_BACKLOG_QTY", "EXPECTED_BACKLOG_VALUE", "EXPECTED_GROSS_PROFIT",
            "EXPECTED_COGS", "EXPECTED_RECEIVABLE_OVERDUE",
            "EXPECTED_PAYABLE_OVERDUE"} <= referenced, referenced
    for name in referenced:
        assert name in expected, f"{name} 不是 agenerp.seed.checks 上的期望值"


def test_that_structural_assertion_actually_has_teeth():
    """上一条不能是空转的：给它喂一份写死期望值的源码，它必须判成违规。"""
    forged = f"expected = {CH.EXPECTED_BACKLOG_VALUE}\n"
    offenders = [node.lineno for node in ast.walk(ast.parse(forged))
                 if _is_money_literal(node, {CH.EXPECTED_BACKLOG_VALUE})]

    assert offenders == [1]


def test_first_run_creates_and_submits_everything_second_run_creates_nothing():
    """幂等的判据是「第二跑零 POST / 新建 0」，不是「没报错」。"""
    site = FakeDocSite()
    steps = seedsite.document_steps()

    first = seedsite.load_documents(_client(site))
    posts_after_first = len(site.posts)
    puts_after_first = len(site.puts)
    second = seedsite.load_documents(_client(site))

    assert first.total_created == len(steps)
    assert posts_after_first == len(steps)
    assert sum(first.submitted.values()) == sum(1 for s in steps if s.submit)
    assert second.total_created == 0
    assert len(site.posts) == posts_after_first, "第二跑不该再发任何 POST"
    assert len(site.puts) == puts_after_first, "第二跑不该再提交任何单据"
    assert sum(second.existing.values()) == len(steps)


def test_a_draft_left_behind_by_a_crashed_run_is_submitted_not_counted_as_existing_and_done():
    """半装状态的处置：命中一份 `docstatus 0` 的草稿要**补提交**。

    没有这一格，一次中途失败留下的草稿会让第二跑「新建 0」在**留着草稿**的情况下照样绿。
    """
    site = FakeDocSite()
    seedsite.load_documents(_client(site))
    victim = next(d for d in site.docs.values() if d["doctype"] == "Delivery Note")
    victim["docstatus"] = 0

    report = seedsite.load_documents(_client(site))

    assert report.total_created == 0
    assert report.submitted["Delivery Note"] == 1
    assert victim["docstatus"] == 1
    assert any("补提交" in line for line in report.lines())


def test_a_failing_step_stops_the_whole_load_instead_of_carrying_on():
    """失败即停：`Sales Order` 建不出来时，后面的工单/分录一个都不许被尝试。"""
    site = FakeDocSite(fail_on="Sales Order")

    with pytest.raises(SiteError):
        seedsite.load_documents(_client(site))

    attempted = {json.loads(r.body).get("doctype", "") for r in site.posts}
    assert "Work Order" not in attempted and "Delivery Note" not in attempted


def test_placeholders_are_bound_from_what_the_site_returned():
    site = FakeDocSite()
    seedsite.load_documents(_client(site))

    delivery = next(d for d in site.docs.values() if d["doctype"] == "Delivery Note")
    sales_order = next(d for d in site.docs.values() if d["doctype"] == "Sales Order")
    manufacture = [d for d in site.docs.values()
                   if d["doctype"] == "Stock Entry" and d["purpose"] == seedsite.PURPOSE_MANUFACTURE]

    assert delivery["items"][0]["against_sales_order"] == sales_order["name"]
    assert delivery["items"][0]["so_detail"] == sales_order["items"][0]["name"]
        # D-12 后只剩自制批走 `Manufacture` —— 外协批走原生收货，不再伪造成制造分录。
    assert [d["additional_costs"][0]["amount"] for d in manufacture] == [800.0]


def test_the_operating_cost_comes_from_the_site_not_from_this_repo():
    """站点改了 BOM 的工序成本，送出去的附加成本必须跟着改 —— 否则那个数其实是本仓写死的。"""
    site = FakeDocSite(bom_operating_cost=1234.0, bom_quantity=1000.0)

    seedsite.load_documents(_client(site))

    inhouse = next(d for d in site.docs.values()
                   if d["doctype"] == "Stock Entry" and d["purpose"] == seedsite.PURPOSE_MANUFACTURE)
    assert inhouse["additional_costs"][0]["amount"] == 1.234 * M.INHOUSE_QTY


def test_an_unbound_placeholder_is_raised_not_silently_sent():
    with pytest.raises(SiteError, match="没有被绑定"):
        seedsite.resolve_refs({"a": seedsite.REF_SALES_ORDER}, {})


def test_loading_documents_never_touches_the_masters_plan():
    """`--load-documents` 与 `--load-masters` 是两条互不相干的 CLI 面。"""
    master_doctypes = {s.doctype for s in seedsite.plan_steps()}
    document_doctypes = {s.doctype for s in seedsite.document_steps()}

    assert master_doctypes & document_doctypes == set()


class FakeVerifySite:
    """一个只答对账那几条读取的假站点。默认答**正确**的那组数，用来验证判定不空转。"""

    def __init__(self, **overrides):
        self.data = {
            "Bin": [{"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
                     "actual_qty": CH.EXPECTED_BACKLOG_QTY,
                     "stock_value": CH.EXPECTED_BACKLOG_VALUE, "valuation_rate": 0.0}],
            "GL Entry": [
                {"account": seedsite.site_name_of(M.ACC_REVENUE), "debit": 0.0,
                 "credit": CH.EXPECTED_RECEIVABLE_OVERDUE, "voucher_type": "Sales Invoice",
                 "voucher_no": "x", "is_cancelled": 0},
                {"account": seedsite.site_name_of(M.ACC_RECEIVABLE),
                 "debit": CH.EXPECTED_RECEIVABLE_OVERDUE, "credit": 0.0,
                 "voucher_type": "Sales Invoice", "voucher_no": "x", "is_cancelled": 0},
                {"account": seedsite.site_name_of(M.ACC_COGS), "debit": CH.EXPECTED_COGS,
                 "credit": 0.0, "voucher_type": "Delivery Note", "voucher_no": "y",
                 "is_cancelled": 0},
                {"account": seedsite.site_name_of(M.ACC_FINISHED), "debit": 0.0,
                 "credit": CH.EXPECTED_COGS, "voucher_type": "Delivery Note", "voucher_no": "y",
                 "is_cancelled": 0},
            ],
            "Stock Ledger Entry": [{"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
                                    "qty_after_transaction": CH.EXPECTED_BACKLOG_QTY,
                                    "is_cancelled": 0}],
            # ⚠️ 三个键（`company` / `customer|supplier` / `posting_date`）不是装饰：
            # `_overdue_checks` 按**装载器自己的幂等键**把预期发票认出来，缺键会直接 `KeyError`。
            "Sales Invoice": [{"name": "ACC-SINV-2026-00001", "status": "Overdue",
                               "outstanding_amount": CH.EXPECTED_RECEIVABLE_OVERDUE,
                               "due_date": "2026-03-10", "docstatus": 1,
                               "company": M.COMPANY, "customer": M.CUSTOMER,
                               "posting_date": M.day(6)}],
            "Purchase Invoice": [{"name": "ACC-PINV-2026-00001", "status": "Overdue",
                                  "outstanding_amount": CH.EXPECTED_PAYABLE_OVERDUE,
                                  "due_date": "2026-03-09", "docstatus": 1,
                                  "company": M.COMPANY, "supplier": M.SUPPLIER,
                                  "posting_date": M.day(5)}],
        }
        # 文档图对账（D-12）要读每一种单据的条数。默认按离线数据集**逐一对齐**，
        # 使默认这组数是「全绿」的那组 —— 这个假站点的契约就是「默认答对的」。
        # 不硬写条数：写死会让它与数据集脱钩，改数据集时这里静默变错。
        dataset = seed_generate()
        for doctype in dataset.doctypes():
            if doctype in seedsite._DERIVED_DOCTYPES:
                continue
            self.data.setdefault(doctype, [{"name": f"{doctype}-{i}"}
                                           for i in range(len(dataset.of(doctype)))])
        self.data.update(overrides)

    def __call__(self, request):
        from urllib.parse import unquote, urlparse

        tail = unquote(urlparse(request.url).path).split("/api/resource/")[1]
        if "/" in tail:
            # 取单份文档（`_link_field_checks` 用它读 Link 字段）。
            # **答离线数据集里那一份，逐字回**——这个假站点的契约是「默认答对的」，
            # 于是默认这组数全绿，各条测试再按需 override 成错的那组。
            doctype, name = tail.split("/", 1)
            for row in seed_generate().of(doctype):
                if str(row.get("name")) == name:
                    return SiteResponse(200, json.dumps({"data": row}, default=str))
            return SiteResponse(404, json.dumps({"data": None}))
        return SiteResponse(200, json.dumps({"data": self.data[tail]}))


def _verify(**overrides):
    return seedsite.verify_site(_client(FakeVerifySite(**overrides)))


def test_verify_site_passes_on_the_numbers_the_plan_exists_to_prove():
    results = _verify()

    assert [r.label for r in results if not r.ok] == []
    assert len(results) == 32, (
        "9 条财务/库存口径 + 9 条文档图条数对账（D-12）+ 12 条跨单据 Link 字段对账"
        "（P1.0 前置 T0）。条数变了就必须来这里改，不许让判据悄悄少跑"
    )


def test_verify_site_prints_the_actual_value_and_the_expected_value_with_its_source():
    """⚠️ 只打「通过」或只回显期望值不算数 —— 那样的输出用 grep 就能伪造。"""
    line = next(r.line() for r in _verify() if r.label.endswith(".stock_value"))

    assert f"Bin({M.FINISHED_ITEM}, {M.WH_FINISHED}).stock_value" in line
    assert f"{CH.EXPECTED_BACKLOG_VALUE:.2f}" in line
    assert "agenerp.seed.checks.EXPECTED_BACKLOG_VALUE" in line


def test_verify_site_goes_red_when_the_site_computed_a_different_backlog():
    """变异 ①/② 的纯逻辑对照：数量或金额不对，必须红在那一条并打出站点实得值。"""
    qty = _verify(Bin=[{"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
                        "actual_qty": 1020.0, "stock_value": CH.EXPECTED_BACKLOG_VALUE}])
    value = _verify(Bin=[{"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
                          "actual_qty": CH.EXPECTED_BACKLOG_QTY, "stock_value": 6394.0}])

    assert [r.label for r in qty if not r.ok] == [f"Bin({M.FINISHED_ITEM}, {M.WH_FINISHED}).actual_qty"]
    assert "1020.00" in next(r.line() for r in qty if not r.ok)
    assert [r.label for r in value if not r.ok] == [f"Bin({M.FINISHED_ITEM}, {M.WH_FINISHED}).stock_value"]
    assert "6394.00" in next(r.line() for r in value if not r.ok)


def test_verify_site_goes_red_when_the_finished_bin_is_missing_entirely():
    results = _verify(Bin=[])

    assert not results[0].ok and "站点上没有这条 Bin" in results[0].actual


def test_verify_site_goes_red_on_an_unbalanced_ledger_and_on_negative_stock():
    unbalanced = _verify(**{"GL Entry": [
        {"account": "x", "debit": 1.0, "credit": 0.0, "voucher_type": "t", "voucher_no": "v",
         "is_cancelled": 0}]})
    negative = _verify(**{"Stock Ledger Entry": [
        {"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
         "qty_after_transaction": -1.0, "is_cancelled": 0}]})

    assert any(r.label.startswith("GL 借贷差额") and not r.ok for r in unbalanced)
    assert any(r.label.startswith("负库存条目数") and not r.ok for r in negative)


def test_verify_site_ignores_cancelled_ledger_rows():
    """已取消的 GL / SLE 行不算数 —— 否则一次人工 cancel 会让对账凭空变红或变绿。"""
    results = _verify(**{"Stock Ledger Entry": [
        {"item_code": M.FINISHED_ITEM, "warehouse": M.WH_FINISHED,
         "qty_after_transaction": -999.0, "is_cancelled": 1}]})

    assert [r.label for r in results if not r.ok] == []


def test_verify_site_goes_red_when_an_invoice_is_not_overdue():
    results = _verify(**{"Sales Invoice": [
        {"name": "ACC-SINV-2026-00001", "status": "Paid",
         "outstanding_amount": 0.0, "due_date": "2026-03-10", "docstatus": 1,
         "company": M.COMPANY, "customer": M.CUSTOMER, "posting_date": M.day(6)}]})

    assert any("Sales Invoice" in r.label and not r.ok for r in results)


# ---------------------------------------------------------------------------
# `_overdue_checks` 的诊断（plan `2026-08-23-0120-2` Phase 2，五态）
#
# 诊断只进 `label`，**不参与 `ok` 的计算** —— 因此每一态都同时断言 `ok` 与消息内容：
# 只断言消息会放过「诊断说得头头是道、判定却错了」，只断言 `ok` 会放过「红了但读不懂」。
# 「今天」由 `_verify_at` 显式注入，否则状态 ③ 会变成随墙钟漂移的测试。
# ---------------------------------------------------------------------------

SI_KEY = {"company": M.COMPANY, "customer": M.CUSTOMER, "posting_date": M.day(6)}
PI_KEY = {"company": M.COMPANY, "supplier": M.SUPPLIER, "posting_date": M.day(5)}


def _verify_at(today, **overrides):
    return seedsite.verify_site(_client(FakeVerifySite(**overrides)), today=today)


def _overdue_lines(results):
    return [r for r in results if "outstanding_amount 合计" in r.label]


def test_overdue_diagnosis_names_both_expected_invoices_when_everything_is_right():
    """状态 ①：全对时也必须逐张打出「按幂等键认出来了」。

    ⚠️ 这条正向断言是唯一堵得住「键永远匹配不上」的口：`FakeVerifySite.__call__` 完全忽略
    query 参数，对任何 filters 都回整份数据，所以一个从不匹配的实现会在其余各态下全部通过，
    同时在每一次绿的运行里打印垃圾。
    """
    sales, purchase = _overdue_lines(_verify_at("2026-08-23"))

    assert sales.ok and purchase.ok
    assert "ACC-SINV-2026-00001：status=Overdue" in sales.label
    assert "ACC-PINV-2026-00001：status=Overdue" in purchase.label
    assert "认不出" not in sales.label and "认不出" not in purchase.label


def test_overdue_diagnosis_still_lists_the_expected_invoices_when_the_site_found_none():
    """状态 ②（反空转）：站点一张 `Overdue` 都没算出来时，诊断**恰恰**必须说得出话。

    候选集若取自站点的 `Overdue` 过滤结果，这里就会空转 —— 诊断在它唯一存在理由的场景下失灵。
    """
    none_overdue = _overdue_lines(_verify_at("2026-08-23", **{
        "Sales Invoice": [{"name": "ACC-SINV-2026-00001", "status": "Unpaid",
                           "outstanding_amount": CH.EXPECTED_RECEIVABLE_OVERDUE,
                           "due_date": "2026-03-10", "docstatus": 1, **SI_KEY}],
        "Purchase Invoice": [{"name": "ACC-PINV-2026-00001", "status": "Unpaid",
                              "outstanding_amount": CH.EXPECTED_PAYABLE_OVERDUE,
                              "due_date": "2026-03-09", "docstatus": 1, **PI_KEY}]}))

    for line, name, due in ((none_overdue[0], "ACC-SINV-2026-00001", "2026-03-10"),
                            (none_overdue[1], "ACC-PINV-2026-00001", "2026-03-09")):
        assert line.ok is False
        assert "命中 0 张：无" in line.label
        assert f"{name}：status=Unpaid" in line.label
        assert f"due_date={due}" in line.label
        assert "docstatus=1（已提交）" in line.label

    missing = _overdue_lines(_verify_at("2026-08-23", **{"Sales Invoice": []}))[0]

    assert missing.ok is False
    assert "认不出这张发票" in missing.label


def test_overdue_diagnosis_points_at_due_date_and_labels_whose_today_it_used():
    """状态 ③：`due_date` 还没到期时，必须点名 `due_date` **并**标注「今天」的口径。"""
    early = _overdue_lines(_verify_at("2026-03-01", **{
        "Sales Invoice": [{"name": "ACC-SINV-2026-00001", "status": "Unpaid",
                           "outstanding_amount": CH.EXPECTED_RECEIVABLE_OVERDUE,
                           "due_date": "2026-03-10", "docstatus": 1, **SI_KEY}]}))[0]

    assert early.ok is False
    assert "due_date=2026-03-10（未到期，今天 2026-03-01（宿主侧））" in early.label


def test_overdue_diagnosis_points_at_an_unsubmitted_invoice():
    """状态 ④：单据压根没提交时，必须点名「未提交」，而不是只报一个对不上的金额。"""
    draft = _overdue_lines(_verify_at("2026-08-23", **{
        "Purchase Invoice": [{"name": "ACC-PINV-2026-00001", "status": "Draft",
                              "outstanding_amount": CH.EXPECTED_PAYABLE_OVERDUE,
                              "due_date": "2026-03-09", "docstatus": 0, **PI_KEY}]}))[1]

    assert draft.ok is False
    assert "docstatus=0（未提交）" in draft.label


def test_overdue_diagnosis_does_not_eat_the_load_bearing_amount_assertion():
    """状态 ⑤：两张都 `Overdue` 但金额不对时，仍必须红在金额上并把两个数都打出来。"""
    wrong = _overdue_lines(_verify_at("2026-08-23", **{
        "Sales Invoice": [{"name": "ACC-SINV-2026-00001", "status": "Overdue",
                           "outstanding_amount": 17000.0, "due_date": "2026-03-10",
                           "docstatus": 1, **SI_KEY}]}))[0]

    assert wrong.ok is False
    assert wrong.actual == "17000.00"
    assert f"= 17000.00 / expected = {CH.EXPECTED_RECEIVABLE_OVERDUE:.2f}" in wrong.line()
    assert "ACC-SINV-2026-00001：status=Overdue" in wrong.label


def test_cli_requires_exactly_one_action_and_a_site():
    assert seedsite.main([]) == 2
    assert seedsite.main(["--load-documents"]) == 2
    assert seedsite.main(["--load-masters", "--verify-site", "--site", "frontend"]) == 2


def test_link_field_check_catches_a_missing_link_the_count_check_cannot_see():
    """Link 字段对账必须抓住「条数对、字段空」这个形状。

    这是它存在的理由：2026-08-24 实测到离线 `Work Order.sales_order =
    "SAL-ORD-2026-00001"` 而站点上是 NULL，两边**条数一致**，`_document_graph_checks`
    全绿。少一个 Link 不是数据小瑕疵——`doc.links` 走的就是这些字段，
    缺一条，Agent 从那张单出发能看到的下游就少一片。
    """
    class SiteWithABrokenLink(FakeVerifySite):
        def __call__(self, request):
            from urllib.parse import unquote, urlparse
            tail = unquote(urlparse(request.url).path).split("/api/resource/")[1]
            if tail == f"Work Order/{names.WORK_ORDER}":
                doc = dict(next(r for r in seed_generate().of("Work Order")))
                doc["sales_order"] = None      # 站点上字段空着，条数照样对
                return SiteResponse(200, json.dumps({"data": doc}, default=str))
            return super().__call__(request)

    results = seedsite.verify_site(_client(SiteWithABrokenLink()))
    reds = [r for r in results if not r.ok]

    assert len(reds) == 1, f"应恰好红一条，实为 {[r.label for r in reds]}"
    assert reds[0].label == f"Work Order {names.WORK_ORDER}.sales_order"
    assert "SAL-ORD" in reds[0].expected and reds[0].actual == "None"
    # 条数那一族必须仍是绿的 —— 证明这个缺口确实是它看不见的
    assert all(r.ok for r in results if "文档条数" in r.label)
