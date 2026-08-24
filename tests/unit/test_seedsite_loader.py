"""非门禁测试 · 钉死主数据装载器的**纯逻辑半**（`agenerp/seedsite.py`）。

**不连站点**：装载顺序、载荷字段、幂等计数、失败即停，四件事全都可以在假传输上判死。
活站点那一半由 plan `2026-08-22-2107-1` Phase 3 的 CLI 实跑负责（退出码 + 第二跑「新建 0」），
两者不互相冒充 —— 本文件通过**不等于**装载器在真站点上跑得通。
"""

import json

import pytest

from agenerp import seedsite
from agenerp.seed import masters, names
from agenerp.seed import model as M
from agenerp.site import SiteClient, SiteError, SiteResponse


class FakeSite:
    """一个够用的假站点：记住建过什么，按 `filters` 答存在性，按派生规则回 `name`。

    **刻意不实现 upsert**：`ensure_doc` 只建不改，假站点也就没有「改」这条路可走。
    """

    def __init__(self, fail_on: str | None = None):
        self.docs: dict[tuple[str, str], dict] = {}
        self.requests: list = []
        self.fail_on = fail_on

    def __call__(self, request):
        self.requests.append(request)
        doctype = self._doctype(request.url)
        if request.method == "GET":
            wanted = self._wanted_name(request.url)
            hit = self.docs.get((doctype, wanted))
            return SiteResponse(200, json.dumps({"data": [hit] if hit else []}))
        if doctype == self.fail_on:
            return SiteResponse(417, '{"exc_type":"LinkValidationError"}')
        payload = json.loads(request.body)
        name = self._derive(doctype, payload)
        doc = {**payload, "name": name}
        self.docs[(doctype, name)] = doc
        return SiteResponse(200, json.dumps({"data": doc}))

    @property
    def posts(self):
        return [r for r in self.requests if r.method == "POST"]

    @staticmethod
    def _doctype(url: str) -> str:
        from urllib.parse import unquote

        return unquote(url.split("/api/resource/")[1].split("?")[0])

    @staticmethod
    def _wanted_name(url: str) -> str:
        from urllib.parse import parse_qs, unquote, urlparse

        filters = json.loads(parse_qs(urlparse(unquote(url)).query)["filters"][0])
        return filters[0][2]

    def _derive(self, doctype: str, payload: dict) -> str:
        """照抄 2026-08-22 实测的站点命名规则，**不照抄载荷里的 `name`**。"""
        if doctype == "BOM":
            # 命名序列 `BOM-{item}-{###}`：显式 `name` 不采纳，第二条同 item 的 BOM 回 `-002`。
            seq = 1 + sum(1 for dt, _ in self.docs if dt == "BOM")
            return f"BOM-{payload['item']}-{seq:03d}"
        derived_from = {
            "Warehouse": "warehouse_name", "Account": "account_name", "Item": "item_code",
            "Company": "company_name", "Customer": "customer_name", "Supplier": "supplier_name",
        }
        if doctype in ("Warehouse", "Account"):
            return f"{payload[derived_from[doctype]]} - {seedsite.ABBR}"
        if doctype in derived_from:
            return payload[derived_from[doctype]]
        for key in ("uom_name", "item_group_name", "customer_group_name",
                    "territory_name", "supplier_group_name", "workstation_name", "name"):
            if key in payload:
                return payload[key]
        raise AssertionError(f"假站点不知道 {doctype} 怎么命名：{payload}")


def _client(transport):
    return SiteClient("frontend", base_url="http://127.0.0.1:18080",
                      api_key="k", api_secret="s", transport=transport)


def _order(steps):
    return [s.doctype for s in steps]


def _index(steps, doctype):
    return _order(steps).index(doctype)


def test_dependency_order_puts_workstation_and_operation_before_bom():
    """评审第 1 轮点名的那条：少了 `Workstation`/`Operation`，`BOM` 建不出来。"""
    steps = seedsite.plan_steps()

    assert _index(steps, "Workstation") < _index(steps, "Operation") < _index(steps, "BOM")


def test_dependency_order_matches_the_plan():
    """`Warehouse Type` → `Company` → `Account` → `Warehouse` → 目录 → 工艺 → `Item` → 客商 → `BOM`。"""
    steps = seedsite.plan_steps()

    for earlier, later in (
        ("Warehouse Type", "Company"), ("Company", "Account"), ("Account", "Warehouse"),
        ("Item Group", "Item"), ("UOM", "Item"), ("Item", "BOM"),
        ("Customer Group", "Customer"), ("Territory", "Customer"),
        ("Supplier Group", "Supplier"),
    ):
        assert _index(steps, earlier) < _index(steps, later), f"{earlier} 必须早于 {later}"
    assert _order(steps)[-1] == "BOM"


def test_every_number_that_takes_part_in_an_assertion_comes_from_the_seed_package():
    """装载器不得持有第二份数值：抽查的每一个数都必须是 `agenerp.seed` 的常量。"""
    by_name = {s.expected_name: s for s in seedsite.plan_steps()}

    assert set(by_name) >= {M.COMPANY, M.CUSTOMER, M.SUPPLIER, names.BOM}
    assert set(by_name) >= {seedsite.site_name_of(w["name"]) for w in masters.warehouses()}
    assert set(by_name) >= {i["name"] for i in masters.items()}
    bom = by_name[names.BOM].payload
    assert bom["quantity"] == masters.bom()[0]["quantity"]
    assert [o["hour_rate"] for o in bom["operations"]] == [M.WORKSTATION_HOUR_RATE] * 3
    assert by_name[seedsite.WORKSTATION].payload["hour_rate_labour"] == M.WORKSTATION_HOUR_RATE


def test_warehouse_payload_uses_the_derived_name_field_not_name():
    """站点不采纳显式 `name`（E3 实测）：仓必须靠 `warehouse_name` + 公司缩写落成常量那个名字。"""
    step = next(s for s in seedsite.plan_steps() if s.expected_name == M.WH_RAW)

    assert "name" not in step.payload
    assert step.payload["warehouse_name"] == "原料仓"
    assert step.payload["account"] == seedsite.site_name_of(M.WAREHOUSE_ACCOUNT[M.WH_RAW])
    assert step.key == {"name": M.WH_RAW}


def test_account_payload_carries_structure_only():
    step = next(s for s in seedsite.plan_steps() if s.expected_name == seedsite.site_name_of(M.ACC_RAW))

    assert step.payload["account_name"] == "原材料"
    assert (step.payload["root_type"], step.payload["account_type"]) == ("Asset", "Stock")
    assert step.payload["parent_account"] == seedsite.PARENT_STOCK_ASSETS


def test_bom_is_submitted_and_does_not_overwrite_site_computed_costs():
    step = next(s for s in seedsite.plan_steps() if s.doctype == "BOM")

    assert step.payload["docstatus"] == 1
    for computed in ("raw_material_cost", "operating_cost", "total_cost"):
        assert computed not in step.payload, f"{computed} 是站点算的，不许由本仓覆盖"


def test_first_run_creates_everything_and_second_run_posts_nothing():
    """幂等的判据是「第二跑零 POST / 新建 0」，不是「没报错」。"""
    site = FakeSite()

    first = seedsite.load_masters(_client(site))
    posts_after_first = len(site.posts)
    second = seedsite.load_masters(_client(site))

    assert first.total_created == len(seedsite.plan_steps())
    assert posts_after_first == len(seedsite.plan_steps())
    assert second.total_created == 0
    assert len(site.posts) == posts_after_first, "第二跑不该再发任何 POST"
    assert sum(second.existing.values()) == len(seedsite.plan_steps())


def test_a_failing_step_stops_the_whole_load_instead_of_carrying_on():
    """失败即停：`Company` 建不出来时，后面的科目/仓库一个都不许被尝试。"""
    site = FakeSite(fail_on="Company")

    with pytest.raises(SiteError):
        seedsite.load_masters(_client(site))

    attempted = {FakeSite._doctype(r.url) for r in site.posts}
    assert attempted == {"Warehouse Type", "Company"}, attempted


def _step_the_site_will_answer_with_a_different_name() -> seedsite.Step:
    """一条**测试内构造**的畸形步骤：`source_constant` 少一个空格，站点必然回另一个名字。

    刻意不拿 `M.ACC_OPERATING` 当输入（plan `2026-08-22-2325-1` Phase 2 已把它修好）——
    覆盖的是 `LoadReport.mismatches` 这个**通用对账机制**，不是某一个常量当下的死活。
    """
    return seedsite.Step(
        doctype="Account",
        key={"name": "对账演示科目 - HRD"},
        payload={"account_name": "对账演示科目", "company": M.COMPANY,
                 "parent_account": seedsite.PARENT_STOCK_EXPENSES,
                 "root_type": "Expense", "account_type": "", "is_group": 0},
        expected_name="对账演示科目 - HRD",
        source_constant="对账演示科目- HRD",
    )


def _well_formed_step() -> seedsite.Step:
    """一条站点会原样回名的步骤：`source_constant` 与派生名相同，不该产生任何报告。"""
    return seedsite.Step(
        doctype="Account",
        key={"name": "规整演示科目 - HRD"},
        payload={"account_name": "规整演示科目", "company": M.COMPANY,
                 "parent_account": seedsite.PARENT_STOCK_EXPENSES,
                 "root_type": "Expense", "account_type": "", "is_group": 0},
        expected_name="规整演示科目 - HRD",
        source_constant="规整演示科目 - HRD",
    )


def test_account_name_mismatch_is_reported_not_swallowed(monkeypatch):
    """站点回的真名与本仓常量不符时，装载器必须说出来，而不是悄悄咽掉。

    比对基准是 `Step.source`（本仓那个**原始常量**），不是装载器自己算出来的派生名：
    拿派生名比对是自己跟自己比，永远相等，这条断言就会空转。
    """
    bad = _step_the_site_will_answer_with_a_different_name()
    monkeypatch.setattr(seedsite, "plan_steps", lambda: [bad])

    report = seedsite.load_masters(_client(FakeSite()))
    text = "\n".join(report.lines())

    assert report.mismatches == [("Account", bad.source, bad.expected_name)]
    assert bad.source in text and "⚠️" in text
    assert "新建" in text


def test_the_mismatch_check_is_silent_for_every_other_constant(monkeypatch):
    """不空转的另一半：只有畸形的那一条报不符，规整的那些一条都不报。

    第二半更要紧 —— `agenerp.seed` 现有的 15 个带后缀常量**全部**规整
    （由 `tests/unit/test_seed_model_constants.py` 的机械判据钉住），
    真实 `plan_steps()` 因此必须一条 mismatch 都不产生。
    """
    bad = _step_the_site_will_answer_with_a_different_name()
    monkeypatch.setattr(seedsite, "plan_steps", lambda: [_well_formed_step(), bad])

    report = seedsite.load_masters(_client(FakeSite()))

    assert len(report.mismatches) == 1, report.mismatches
    assert report.mismatches[0][1] == bad.source
    assert not any("规整演示科目" in line for line in report.lines()), report.lines()


def test_the_real_master_data_plan_reports_no_mismatch_at_all():
    """本 plan 的**直接结果面**：`agenerp.seed` 现有的常量一条都不该报不符。

    与上面那条的分工：那条钉「机制会报、且不是每条都报」（输入全是测试内构造的），
    这条钉「产品数据此刻确实是干净的」。前者在缺陷修好前后都绿，后者在修好之前必红。
    活站点上的同一条判据是 plan `2026-08-22-2325-1` Phase 3 的「不再出现 ⚠️ 告警行」。
    """
    report = seedsite.load_masters(_client(FakeSite()))

    assert report.mismatches == [], report.mismatches
    assert not any("⚠️" in line for line in report.lines()), report.lines()


def test_strip_abbr_refuses_a_name_the_site_could_never_derive():
    """`strip_abbr` 的畸形输入语义是**失败即停**，不是容忍纠正（plan `2026-08-22-2325-1` D）。

    容忍会让下一个拼错的常量被静默改好照样往站点写；原样返回更坏 —— `site_name_of`
    会再拼一次后缀，在站点上真建出 `X - HRD - HRD`。所以：不匹配即抛，一个对象都不建。
    """
    malformed = "生产费用（计入估值）- HRD"

    with pytest.raises(ValueError) as excinfo:
        seedsite.strip_abbr(malformed)

    message = str(excinfo.value)
    assert malformed in message, message
    assert f"<name> - {seedsite.ABBR}" in message, message


def test_cli_requires_both_the_action_and_the_site():
    assert seedsite.main([]) == 2
    assert seedsite.main(["--load-masters"]) == 2
