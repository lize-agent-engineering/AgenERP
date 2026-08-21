"""十个只读工具的清单与实测硬约束回归。

**失败意味着什么**：某条本项目付过学费的约束从声明里掉了。这些点靠 review 记不住——
`permission.scope` 的两条、`doc.links` 的 `from_is_submittable`、`lineage.trace` 的子表扫描、
`doc.get` 的裁剪与 §7.5 声明位，每一条都是 Spike 实测撞出来的。

清单本身是 plan `2026-08-21-1022-2` Phase 2 的 `Decision`（owner doc 没给过清单）。
人若要换一组十个，改的是 `agenerp/tools_readonly.py` 的声明与本文件的清单断言，
**契约格式本身不受影响**。
"""

import pytest

from agenerp.contracts import APPROVAL_NOT_REQUIRED, check_registry, validate_registry
from agenerp.tools_readonly import READONLY_CONTRACTS, READONLY_TOOL_NAMES, get

# 名字逐字取自 owner doc：前七个是 agents-and-roles.md §5.1 解释 Agent 的工具集，
# 后三个由 §5.0 ① 与 context-and-memory.md 在证据充分性门禁 / 结构化导航里点名。
EXPECTED_TOOLS = (
    "query.read",
    "schema.search",
    "snapshot.read",
    "lineage.trace",
    "rule.lookup",
    "system.overview",
    "permission.scope",
    "doc.get",
    "doc.links",
    "meta.fields",
)

# 明确排除的，连同理由。写出来是为了让「这不是随手凑十个」可被复核。
EXCLUDED_TOOLS = (
    "anomaly.scan",      # 洞察 Agent，依赖行业包规则（P1）
    "benchmark.compare",  # 洞察 Agent，依赖行业包规则（P1）
    "dsl.schema",        # 视图 Agent，依赖视图 DSL（P2）
    "field.catalog",     # 视图 Agent，依赖视图 DSL（P2）
    "dsl.validate",      # 视图 Agent，依赖视图 DSL（P2）
    "dsl.preview",       # 视图 Agent，依赖视图 DSL（P2）
)


def test_there_are_exactly_ten():
    assert len(READONLY_CONTRACTS) == 10


def test_the_ten_names_match_owner_doc_verbatim():
    assert READONLY_TOOL_NAMES == EXPECTED_TOOLS


@pytest.mark.parametrize("tool", EXCLUDED_TOOLS)
def test_out_of_scope_tools_are_not_declared(tool):
    assert tool not in READONLY_TOOL_NAMES


def test_the_whole_registry_is_structurally_valid():
    assert validate_registry(READONLY_CONTRACTS) == ()
    check_registry(READONLY_CONTRACTS)


@pytest.mark.parametrize("contract", READONLY_CONTRACTS, ids=lambda c: c.tool)
def test_every_contract_is_read_only_l0_and_needs_no_approval(contract):
    """§5 风险表：L0 = 只读，无副作用，直接放行。"""
    assert contract.read_only
    assert contract.risk == "L0"
    assert contract.side_effects == ()
    assert contract.approval == APPROVAL_NOT_REQUIRED
    assert contract.on_violation == "abort_and_report"


@pytest.mark.parametrize("contract", READONLY_CONTRACTS, ids=lambda c: c.tool)
def test_every_contract_declares_the_full_returns_segment(contract):
    """§7.3.1 的三项：裁剪规则 / 上限条数 / 必须保留什么。缺一不可。"""
    returns = contract.returns
    assert returns is not None
    assert returns.trim_rules
    assert isinstance(returns.max_rows, int) and returns.max_rows > 0
    assert returns.must_keep


@pytest.mark.parametrize("contract", READONLY_CONTRACTS, ids=lambda c: c.tool)
def test_every_contract_declares_the_7_5_free_text_bit(contract):
    """§7.5 的声明位必须是显式布尔——「没想过」和「不会返回」不是一回事。"""
    assert isinstance(contract.returns.user_writable_free_text, bool)


@pytest.mark.parametrize("contract", READONLY_CONTRACTS, ids=lambda c: c.tool)
def test_every_measured_constraint_carries_its_source(contract):
    """约束没有出处就退回成意见。每条条件都得指回 owner doc。"""
    for condition in contract.preconditions + contract.postconditions:
        assert condition.source, f"{contract.tool}: {condition.text}"


def test_get_returns_the_contract_and_raises_on_unknown_name():
    assert get("doc.links").tool == "doc.links"
    with pytest.raises(KeyError):
        get("doc.submit")


# --- 逐条实测硬约束 ---------------------------------------------------------------


def test_permission_scope_declares_the_app_filter_trim_rule():
    """不过滤：老板 83 / 工人 61，九成是框架管道；过滤后 34 / 12。"""
    rules = " ".join(get("permission.scope").returns.trim_rules)
    assert "按 app 过滤" in rules
    for number in ("83", "61", "34", "12"):
        assert number in rules, rules


def test_permission_scope_forbids_inferring_from_docperm():
    """反推版漏报了 Sales Invoice。漏报比噪声更危险——Agent 会据此错误地拒绝回答。"""
    texts = [c.text for c in get("permission.scope").postconditions]
    assert any("has_permission" in t and "DocPerm" in t for t in texts), texts


def test_permission_scope_is_injected_at_session_start():
    """补上后同一道越权问题的工具调用从 35 次降到 1 次——不依赖模型想起来调用。"""
    facts = [c.fact for c in get("permission.scope").postconditions]
    assert "injected_at_session_start" in facts


def test_doc_links_must_keep_from_is_submittable():
    """架构文档（module-boundaries.md §7.3.1）是该字段名的 owner。"""
    assert "from_is_submittable" in get("doc.links").returns.must_keep


def test_doc_links_filters_by_excluding_cancelled_not_by_requiring_submitted():
    """「只要已提交」会滤掉草稿下游，把 L2 门禁架空。"""
    rules = " ".join(get("doc.links").returns.trim_rules)
    assert "排除已取消" in rules
    assert "**不是**「只要已提交」" in rules


def test_lineage_trace_declares_both_link_levels_and_parent_resolution():
    """实测 21 个指向 Sales Order 的 Link 里 14 个在子表，只扫主表会返回空结果。"""
    contract = get("lineage.trace")
    levels = {c.value for c in contract.postconditions if c.fact == "scanned_link_levels"}
    assert levels == {"doctype", "child_table"}
    assert any(c.fact == "child_hits_resolved_to_parent" for c in contract.postconditions)


def test_doc_get_trims_framework_pipe_fields():
    rules = " ".join(get("doc.get").returns.trim_rules)
    assert "_comments" in rules and "_liked_by" in rules


def test_doc_get_declares_it_returns_user_writable_free_text():
    """§7.5：备注 / 评论 / 异常处理说明是真实的提示注入攻击面（Spike 01 探针 5 可提权）。"""
    assert get("doc.get").returns.user_writable_free_text is True


def test_only_doc_get_is_marked_as_returning_free_text_for_now():
    """声明位不是摆设——把它全填 True 等于没声明。v0 只有 doc.get 会倒回自由文本。"""
    flagged = [c.tool for c in READONLY_CONTRACTS if c.returns.user_writable_free_text]
    assert flagged == ["doc.get"]
