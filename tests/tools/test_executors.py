"""十个执行体的判据（假站点，不连网络）。

每条断言都对着**契约里写死的一条实测硬约束**，不是对着「调得通」。
「调得通」与「守约」是两件事，而后者才是契约存在的理由。
"""

from __future__ import annotations

import json

import pytest

from agenerp.contracts import ReadOnlyContext
from agenerp.tools.registry import EXECUTORS
from agenerp.tools.runtime import DATA_BOUNDARY_OPEN, Outcome, execute
from agenerp.tools_readonly import READONLY_CONTRACTS, get as contract_of

SO = {"doctype": "Sales Order", "name": "SAL-ORD-2026-00001"}

GATE = ReadOnlyContext(
    {
        "doc_links_called_for": [],
        "documents_named_in_question": [],
        "doc_get_called_for": [],
        "submitted_downstream_documents": [],
        "inbound_vouchers_of_quantities_in_answer": [],
        "injected_at_session_start": True,
        "industry_pack_loaded": True,
    }
)


def _run(tool, params, client, **kwargs):
    return execute(tool, params, client=client, context=GATE, **kwargs)


def _method_calls(site, method):
    return [
        json.loads(r.body)
        for r in site.requests
        if r.url.endswith(f"/api/method/{method}")
    ]


# ── 后置断言确实挂上了：十个工具一个都不能漏 ────────────────────────────────
@pytest.mark.parametrize("contract", READONLY_CONTRACTS, ids=lambda c: c.tool)
def test_every_contract_enforces_its_postconditions(contract, fake_client):
    """形状合法但**事实缺席**的返回值必须被挡下。

    挡的是「加了工具却没接后置断言」——那种工具在返回值上看不出任何异样，
    只有在这里会红。
    """
    envelope = {key: "x" for key in contract.returns.must_keep}

    result = execute(
        contract.tool,
        {},
        client=fake_client,
        context=GATE,
        executors={contract.tool: lambda session, params: Outcome(envelope, {})},
    )

    assert result.ok is False
    assert result.stage == "postconditions"
    assert result.violation == "abort_and_report"


# ── system.overview ─────────────────────────────────────────────────────────
def test_system_overview_carries_company_and_time_range(fake_site, fake_client):
    """公司名与数据时间范围缺一不可：缺公司名模型会把公司名当客户名查，白费 2–3 次调用。"""
    result = _run("system.overview", {}, fake_client)

    assert result.ok, result.report()
    assert result.data["companies"] == ["恒锐动力科技有限公司"]
    assert result.data["data_time_range"] == {"from": "2026-02-02", "to": "2026-02-08"}


def test_system_overview_filters_framework_and_empty_doctypes(fake_site, fake_client):
    """按 app 过滤掉框架 DocType、按有无数据过滤掉空表——两条都是实测裁剪规则。"""
    result = _run("system.overview", {}, fake_client)

    listed = {row["doctype"] for row in result.data["core_doctypes"]}
    assert "Token Cache" not in listed  # 框架 app
    assert "Customer" not in listed  # 业务 app，但表里没有行
    assert {"Sales Order", "Delivery Note", "Work Order"} <= listed


def test_system_overview_aborts_without_a_company(fake_site, fake_client):
    """站点上没有公司 → 后置断言不成立 → abort，而不是回一份「公司名为空」的概览。"""
    fake_site.rows["Company"] = []

    result = _run("system.overview", {}, fake_client)

    assert result.ok is False
    assert result.stage == "postconditions"


# ── permission.scope ────────────────────────────────────────────────────────
def test_permission_scope_probes_each_candidate_once(fake_site, fake_client):
    """**请求序列断言**：N 个候选 → N 次 `has_permission`。

    这是「必须逐个调、不得从 DocPerm 反推」这条**过程约束**唯一可验的形态：
    从返回值上看不出来它是怎么算出来的。
    """
    candidates = ["Sales Order", "Delivery Note", "Work Order", "Company"]

    result = _run("permission.scope", {"doctypes": candidates}, fake_client)

    assert result.ok, result.report()
    probes = _method_calls(fake_site, "frappe.client.has_permission")
    assert [call["doctype"] for call in probes] == candidates
    assert all(call["perm_type"] == "read" for call in probes)
    assert result.facts["permission_probe_method"] == "has_permission"


def test_permission_scope_returns_the_negatives_too(fake_site, fake_client):
    """读不到的行照样返回：全 `True` 的返回值与「永远回 true 的假实现」长得一模一样。"""
    fake_site.permissions = {"Sales Order": False, "Work Order": True}

    result = _run("permission.scope", {"doctypes": ["Sales Order", "Work Order"]}, fake_client)

    assert result.ok, result.report()
    assert result.data == [
        {"doctype": "Work Order", "can_read": True},
        {"doctype": "Sales Order", "can_read": False},
    ]


def test_permission_scope_puts_readable_first(fake_site, fake_client):
    """可读的排前面：`max_rows` 截断只能截掉读不到的那一半，截掉可见项等于答错。"""
    fake_site.permissions = {"Sales Order": False, "Delivery Note": True}

    result = _run(
        "permission.scope", {"doctypes": ["Sales Order", "Delivery Note"]}, fake_client
    )

    assert [row["can_read"] for row in result.data] == [True, False]


# ── schema.search ───────────────────────────────────────────────────────────
def test_schema_search_returns_candidates_not_a_single_pick(fake_site, fake_client):
    """召回器不是选择器：命中多少就交多少，收窄只允许发生在 `max_rows` 那一步。"""
    result = _run("schema.search", {"keywords": "order"}, fake_client)

    assert result.ok, result.report()
    assert len(result.data["candidates"]) >= 2
    assert result.facts["returns_candidate_list_not_single_pick"] is True


def test_schema_search_skips_empty_tables(fake_site, fake_client):
    """只索引表里真有数据的 DocType——干扰项几乎全部来自空表。"""
    result = _run("schema.search", {"keywords": "customer"}, fake_client)

    assert [row["doctype"] for row in result.data["candidates"]] == []


# ── doc.get ─────────────────────────────────────────────────────────────────
def test_doc_get_includes_child_tables(fake_site, fake_client):
    """子表明细必须一并返回，否则拿不到挂在子表上的事实。"""
    result = _run("doc.get", SO, fake_client)

    assert result.ok, result.report()
    assert [row["item_code"] for row in result.data["items"]] == [
        f"{DATA_BOUNDARY_OPEN}HRD-PACK-5K⟦数据结束⟧"
    ]


def test_doc_get_aborts_when_a_declared_child_table_is_missing(fake_site, fake_client):
    """元数据里声明了子表、返回值里却没有 → abort。这是「漏子表」唯一验得出来的地方。"""
    del fake_site.rows["Sales Order"][0]["items"]

    result = _run("doc.get", SO, fake_client)

    assert result.ok is False
    assert result.stage == "postconditions"


# ── doc.links ───────────────────────────────────────────────────────────────
def test_doc_links_keeps_drafts_and_drops_cancelled(fake_site, fake_client):
    """下游筛选规则是「排除已取消」，**不是**「只要已提交」——草稿下游同样是证据。"""
    result = _run("doc.links", SO, fake_client)

    assert result.ok, result.report()
    names = {row["name"]: row["docstatus"] for row in result.data}
    assert names == {"MAT-DN-2026-00001": 1, "MFG-WO-2026-00001": 0}


def test_doc_links_returns_from_is_submittable(fake_site, fake_client):
    """缺 `from_is_submittable` 的话，下游筛选会整类丢掉不可提交的业务单据。"""
    result = _run("doc.links", SO, fake_client)

    assert all("from_is_submittable" in row for row in result.data)
    assert result.facts["fields_returned"] == (
        "name", "doctype", "docstatus", "from_is_submittable", "linked_via",
    )


def test_doc_links_scans_child_level_links(fake_site, fake_client):
    """21 个指向 Sales Order 的 Link 里 14 个在子表——只扫主表会返回空结果。"""
    result = _run("doc.links", SO, fake_client)

    via = {row["linked_via"] for row in result.data}
    assert "Delivery Note Item.against_sales_order" in via
    assert "Work Order.sales_order" in via


# ── lineage.trace ───────────────────────────────────────────────────────────
def test_lineage_trace_resolves_child_hits_to_the_parent_document(fake_site, fake_client):
    """子表命中必须回溯到父单据，否则返回的是明细行而不是单据。"""
    result = _run("lineage.trace", SO, fake_client)

    assert result.ok, result.report()
    assert result.facts["child_hits_resolved_to_parent"] is True
    assert result.facts["child_table_hits"] >= 1
    assert all(row["doctype"] != "Delivery Note Item" for row in result.data)
    assert "MAT-DN-2026-00001" in {row["name"] for row in result.data}


def test_lineage_trace_scans_both_link_levels(fake_site, fake_client):
    """主表级与子表级两级都要扫，缺一级就是一整类关联看不见。"""
    result = _run("lineage.trace", SO, fake_client)

    assert set(result.facts["scanned_link_levels"]) == {"doctype", "child_table"}


# ── meta.fields ─────────────────────────────────────────────────────────────
def test_meta_fields_tags_level_and_drops_layout_fields(fake_site, fake_client):
    """主表字段与子表字段分标，否则结构化导航会在子表上失明；排版 fieldtype 一律剔掉。"""
    result = _run("meta.fields", {"doctype": "Sales Order"}, fake_client)

    assert result.ok, result.report()
    levels = {row["fieldname"]: row["level"] for row in result.data}
    assert levels["customer"] == "doctype"
    assert levels["item_code"] == "child_table"
    assert "layout" not in levels


def test_meta_fields_aborts_on_an_unknown_doctype(fake_site, fake_client):
    """站点上没有这个 DocType → 报错，不回空字段表。"""
    result = _run("meta.fields", {"doctype": "No Such DocType"}, fake_client)

    assert result.ok is False


# ── query.read ──────────────────────────────────────────────────────────────
def test_query_read_rows_all_come_from_the_requested_doctype(fake_site, fake_client):
    """不得跨表拼装：事实由**本次取过行的端点**推出来，不是执行体自报。"""
    result = _run("query.read", {"doctype": "Sales Order"}, fake_client)

    assert result.ok, result.report()
    assert result.facts["rows_all_from_requested_doctype"] is True


def test_query_read_defaults_to_list_view_fields_and_keeps_must_keep(fake_site, fake_client):
    """不点名字段时按 `in_list_view` 返回，**不回 `*`**；`name` / `docstatus` 永远在。"""
    result = _run("query.read", {"doctype": "Sales Order"}, fake_client)

    assert set(result.data[0]) == {"name", "docstatus", "customer"}


def test_query_read_aborts_without_a_doctype(fake_site, fake_client):
    """不猜 DocType：缺参即停，且原因说得出是调用立不住而不是站点挂了。"""
    result = _run("query.read", {}, fake_client)

    assert result.ok is False
    assert "调用无法执行" in " ".join(result.reasons)


# ── snapshot.read ───────────────────────────────────────────────────────────
def test_snapshot_read_is_normalised_and_stable(fake_site, fake_client):
    """规范化由产出核对，不由自报；同一状态两次读出**同一个 id**（采集时刻不进 id）。"""
    first = _run("snapshot.read", {"scope": "doctypes"}, fake_client)
    second = _run("snapshot.read", {"scope": "doctypes"}, fake_client)

    assert first.ok, first.report()
    assert first.data["snapshot_id"] == second.data["snapshot_id"]
    assert first.facts["snapshot_normalized"] is True
    assert all("modified" not in entry["attributes"] for entry in first.data["entries"])


def test_snapshot_read_rejects_an_unknown_scope(fake_site, fake_client):
    """未知 scope 显式报错：返回空会让「scope 拼错了」与「这个 scope 下没有定制」长得一样。"""
    result = _run("snapshot.read", {"scope": "nope"}, fake_client)

    assert result.ok is False
    assert "nope" in " ".join(result.reasons)


# ── rule.lookup ─────────────────────────────────────────────────────────────
def test_rule_lookup_names_what_is_missing(fake_site, fake_client):
    """本期没有行业包，它的完整正确行为就是**指名报错**，不是返回空清单。"""
    result = _run("rule.lookup", {"doctype": "Sales Order"}, fake_client)

    assert result.ok is False
    assert "行业包" in " ".join(result.reasons)
    assert result.data is None


def test_registry_covers_every_contract():
    """注册表少一边就是一个静默缺口——完整的双向判据在 `test_registry_pairing.py`。"""
    assert set(EXECUTORS) == {contract.tool for contract in READONLY_CONTRACTS}
    assert contract_of("doc.get").returns.user_writable_free_text is True
