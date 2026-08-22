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
        return [r for r in self.requests if r.method == "POST"]

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
        ("工单（外协批）", "原料转外协仓（外协批）"),
        ("原料转外协仓（外协批）", "外协批入库"),
        ("自制批入库", "发货单"),
        ("外协批入库", "发货单"),
        ("销售订单", "发货单"),
        ("发货单", "销售发票（逾期）"),
        ("外协批入库", "采购发票（逾期）"),
    ):
        assert idx(earlier) < idx(later), f"{earlier} 必须早于 {later}"


def test_fifo_ordering_puts_the_inhouse_batch_before_the_subcontract_batch():
    """FIFO 的成立条件：自制批（¥5.00）必须**先入库**，否则发货 990 米出的就不是那一层。"""
    inhouse = _by_label("自制批入库").payload["posting_date"]
    subcon = _by_label("外协批入库").payload["posting_date"]

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


def test_the_two_work_orders_are_told_apart_by_their_wip_warehouse():
    """两张工单的物料与公司相同，只有在制仓不同 —— 幂等键必须靠它分开，否则第二张永远命中第一张。"""
    inhouse = _by_label("工单（自制批）")
    subcon = _by_label("工单（外协批）")

    assert inhouse.key["wip_warehouse"] == M.WH_WIP
    assert subcon.key["wip_warehouse"] == M.WH_SUBCON
    assert inhouse.key != subcon.key


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
    for label in ("自制批入库", "外协批入库"):
        finished = next(row for row in _by_label(label).payload["items"]
                        if row["item_code"] == M.FINISHED_ITEM)
        assert "basic_rate" not in finished and "valuation_rate" not in finished, label
        assert "amount" not in finished, label


def test_work_order_payload_does_not_carry_required_items():
    """`required_items` 由站点从 BOM 派生（实测 `required_qty 120.0 / rate 35.0 / amount 4200.0`）。"""
    assert "required_items" not in _by_label("工单（自制批）").payload


def test_the_inhouse_operating_cost_is_a_placeholder_not_a_local_number():
    """工序成本必须是**从站点读回来的**那个数，不是本仓算出来的。"""
    cost = _by_label("自制批入库").payload["additional_costs"][0]

    assert cost["amount"] == seedsite.REF_OPERATING_COST
    assert cost["expense_account"] == seedsite.site_name_of(M.ACC_OPERATING)


def test_the_subcontract_fee_is_an_input_constant_from_the_seed_package():
    """外协服务费是 §12.1 的**输入**，从 `model.py` 取；派生费率一个都不许出现。"""
    assert _by_label("外协批入库").payload["additional_costs"][0]["amount"] == M.SUBCONTRACT_FEE


DERIVED_CONSTANTS = ("BACKLOG_QTY", "BACKLOG_VALUE", "COGS_VALUE", "GROSS_PROFIT",
                     "INHOUSE_RATE", "SUBCON_RATE", "INHOUSE_VALUE", "SUBCON_VALUE")


def _is_money_literal(node, forbidden: set) -> bool:
    """源码里的这个数字字面量，是不是那组被禁数值之一？

    ⚠️ **口径限定，照实写**：`M.INHOUSE_RATE` 恰好等于 `5.0`，而 `5` 这个**裸整数**在本模块里
    是日期偏移（`M.day(5)`）。把裸整数一并判违规会让这条断言在一个跟钱无关的地方误报，
    于是它很快会被人放宽掉 —— 那比现在这个口径更糟。
    因此只判**带小数点写出来的 `float`**（`5.0` / `6450.0` 这种钱的写法）**或 ≥ 100 的整数**。
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
    assert [d["additional_costs"][0]["amount"] for d in manufacture] == [800.0, M.SUBCONTRACT_FEE]


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
            "Sales Invoice": [{"name": "ACC-SINV-2026-00001", "status": "Overdue",
                               "outstanding_amount": CH.EXPECTED_RECEIVABLE_OVERDUE,
                               "due_date": "2026-03-10", "docstatus": 1}],
            "Purchase Invoice": [{"name": "ACC-PINV-2026-00001", "status": "Overdue",
                                  "outstanding_amount": CH.EXPECTED_PAYABLE_OVERDUE,
                                  "due_date": "2026-03-09", "docstatus": 1}],
        }
        self.data.update(overrides)

    def __call__(self, request):
        from urllib.parse import unquote, urlparse

        doctype = unquote(urlparse(request.url).path).split("/api/resource/")[1]
        return SiteResponse(200, json.dumps({"data": self.data[doctype]}))


def _verify(**overrides):
    return seedsite.verify_site(_client(FakeVerifySite(**overrides)))


def test_verify_site_passes_on_the_numbers_the_plan_exists_to_prove():
    results = _verify()

    assert [r.label for r in results if not r.ok] == []
    assert len(results) == 9


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
         "outstanding_amount": 0.0, "due_date": "2026-03-10", "docstatus": 1}]})

    assert any("Sales Invoice" in r.label and not r.ok for r in results)


def test_cli_requires_exactly_one_action_and_a_site():
    assert seedsite.main([]) == 2
    assert seedsite.main(["--load-documents"]) == 2
    assert seedsite.main(["--load-masters", "--verify-site", "--site", "frontend"]) == 2
