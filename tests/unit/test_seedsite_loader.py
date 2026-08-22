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
    assert step.payload["warehouse_name"] == "XM 原料仓"
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


def test_account_name_mismatch_is_reported_not_swallowed():
    """`M.ACC_OPERATING` 少一个空格，在活站点上永远命不中 —— 装载器必须说出来。

    比对基准是 `agenerp.seed` 的**原始常量**，不是装载器自己算出来的派生名：
    拿派生名比对是自己跟自己比，永远相等，这条断言就会空转。
    见 `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`。
    """
    assert seedsite.site_name_of(M.ACC_OPERATING) != M.ACC_OPERATING, "常量若被修好，本测试应随之改写"

    report = seedsite.load_masters(_client(FakeSite()))
    text = "\n".join(report.lines())

    assert report.mismatches == [("Account", M.ACC_OPERATING, seedsite.site_name_of(M.ACC_OPERATING))]
    assert M.ACC_OPERATING in text and "⚠️" in text
    assert "新建" in text


def test_the_mismatch_check_is_silent_for_every_other_constant():
    """不空转的另一半：只有那一个常量报不符，不是「每一条都报」。"""
    report = seedsite.load_masters(_client(FakeSite()))

    assert len(report.mismatches) == 1, report.mismatches


def test_cli_requires_both_the_action_and_the_site():
    assert seedsite.main([]) == 2
    assert seedsite.main(["--load-masters"]) == 2
