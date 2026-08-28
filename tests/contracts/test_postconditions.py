"""后置断言组 —— 构造「成立」与「不成立」两种结果各求值一次。

**失败意味着什么**：后置断言不可脱离活站点被独立测试，`docs/masterplan/02-WBS.md` P0.2
的判据同样不成立。

只读工具的后置断言约束的是**返回了什么**（§7.3.1 第 2 条）——所以这里构造的上下文
是「一次调用返回了什么」的事实集，不是站点。
"""

import pytest

from agenerp.contracts import ReadOnlyContext, check_postconditions, unsatisfied
from agenerp.tools_readonly import ALL_CONTRACTS, get

# 每个工具一组「全部成立」的返回事实。不成立的那一半由下面逐条打掉一个事实来构造。
SATISFYING_FACTS = {
    # 巡检族（P2.5）。两条都从**观测到的行为**算出来（`agenerp/tools/drift.py:derive_facts`），
    # 判据在 `tests/tools/test_schema_drift.py`：喂该为假的输入时它们必须翻成 False。
    "schema.drift": {
        "uses_frappe_trim_table_dry_run": True,
        "reports_without_dropping": True,
    },
    "query.read": {"rows_all_from_requested_doctype": True},
    "schema.search": {"returns_candidate_list_not_single_pick": True},
    "snapshot.read": {"snapshot_normalized": True},
    "lineage.trace": {
        "scanned_link_levels": ["doctype", "child_table"],
        "child_hits_resolved_to_parent": True,
    },
    "rule.lookup": {"rules_carry_provenance": True},
    "system.overview": {
        "company_names": ["示例纺织有限公司"],
        "data_time_range": ("2026-01-01", "2026-08-21"),
    },
    "permission.scope": {
        "permission_probe_method": "has_permission",
        "injected_at_session_start": True,
    },
    "doc.get": {"child_tables_included": True},
    "doc.links": {"fields_returned": ["name", "doctype", "docstatus", "from_is_submittable"]},
    "meta.fields": {"fields_tagged_by_level": True},
}


# ⚠️ **2026-08-28 由 `READONLY_CONTRACTS` 改为 `ALL_CONTRACTS`**（独立收口审计 B1）：
# P2.5 分出巡检族之后，这些**逐契约**的不变量原本只参数化那十个，新族整族逃逸 ——
# 「只读 L0 / returns 三段齐 / 实测约束带 source / 至少一条后置」这些是**对每一份契约**
# 的要求，不是对「那十个」的要求。今天 `schema.drift` 逐条都过，
# 但**下一条巡检契约就没有任何东西拦着它违约**。
# ⚠️ 「恰好十个」与「十个名字逐字对齐 owner doc」两条**仍按 `READONLY_CONTRACTS`**，
#    那两条守的就是那十个本身。
@pytest.mark.parametrize("contract", ALL_CONTRACTS, ids=lambda c: c.tool)
def test_every_tool_has_at_least_one_postcondition(contract):
    """一个没有后置断言的只读工具契约 = 没人管它返回了什么。"""
    assert contract.postconditions, contract.tool


@pytest.mark.parametrize("contract", ALL_CONTRACTS, ids=lambda c: c.tool)
def test_postconditions_hold_on_a_conforming_result(contract):
    context = ReadOnlyContext(SATISFYING_FACTS[contract.tool])
    failures = unsatisfied(check_postconditions(contract, context))
    assert failures == (), [f.reason for f in failures]


@pytest.mark.parametrize("contract", ALL_CONTRACTS, ids=lambda c: c.tool)
def test_postconditions_fail_on_an_empty_result(contract):
    """空上下文 = 一次什么都没记录的调用。每一条后置断言都必须判为不成立。"""
    failures = unsatisfied(check_postconditions(contract, ReadOnlyContext({})))
    assert len(failures) == len(contract.postconditions), contract.tool


@pytest.mark.parametrize(
    "tool,fact,broken_value,expected_in_reason",
    [
        # permission.scope 从 DocPerm 反推 —— 实测漏报了 Sales Invoice
        ("permission.scope", "permission_probe_method", "docperm", "docperm"),
        # doc.links 丢掉 from_is_submittable —— 下游筛选整类丢掉不可提交的业务单据
        (
            "doc.links",
            "fields_returned",
            ["name", "doctype", "docstatus"],
            "from_is_submittable",
        ),
        # lineage.trace 只扫主表 —— 实测 21 个 Link 里 14 个在子表，会返回空结果
        ("lineage.trace", "scanned_link_levels", ["doctype"], "child_table"),
        # system.overview 不给公司名 —— 模型把公司名当客户名查，白费 2–3 次调用
        ("system.overview", "company_names", [], "0"),
    ],
)
def test_each_measured_failure_mode_is_caught(tool, fact, broken_value, expected_in_reason):
    """这些不是假想的失败，是本项目 Spike 里真踩过的。逐条留一条回归。"""
    contract = get(tool)
    facts = dict(SATISFYING_FACTS[tool])
    facts[fact] = broken_value
    failures = unsatisfied(check_postconditions(contract, ReadOnlyContext(facts)))
    assert failures, f"{tool} 的后置断言放过了 {fact}={broken_value!r}"
    assert any(expected_in_reason in f.reason for f in failures), [f.reason for f in failures]


def test_reason_is_reported_even_when_satisfied():
    """原因是给人看的，`satisfied` 才是判定面——两者都得有。"""
    contract = get("doc.get")
    for result in check_postconditions(contract, ReadOnlyContext(SATISFYING_FACTS["doc.get"])):
        assert result.satisfied
        assert result.reason
