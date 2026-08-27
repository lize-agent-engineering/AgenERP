"""工具契约层 v0 · 十个只读工具的契约声明。

**选法**（owner doc 没给过清单，这是 plan `2026-08-21-1022-2` Phase 2 的 `Decision`）：
取 `docs/design/agents-and-roles.md` §5.1 **解释 Agent** 的七个（`query.read` / `schema.search` /
`snapshot.read` / `lineage.trace` / `rule.lookup` / `system.overview` / `permission.scope`），
加上 §5.0 ① 与 `docs/design/context-and-memory.md` 在**证据充分性门禁**里点名的三个
（`doc.get` / `doc.links` / `meta.fields`）。名字逐字取自 owner doc。

**排除项与理由**：`anomaly.scan` / `benchmark.compare` 属洞察 Agent，依赖行业包规则（P1 才有）；
`dsl.schema` / `field.catalog` / `dsl.validate` / `dsl.preview` 属视图 Agent，依赖视图 DSL（P2 才有）。
选法是「P0 阶段就有真实约束可写的只读工具」，不是「随手凑十个」。

**实测硬约束写在声明里，不写在注释里**——注释不可测。每条都带 `source` 指回出处，
`tests/contracts/test_readonly_registry.py` 逐条回归。
"""

from __future__ import annotations

from agenerp.contracts import (
    APPROVAL_NOT_REQUIRED,
    Condition,
    Returns,
    ToolContract,
)

ROLES = "docs/design/agents-and-roles.md"
BOUNDARIES = "docs/architecture/module-boundaries.md"
MEMORY = "docs/design/context-and-memory.md"

# 只读工具统一的两项：违约就地中止并上报（没有可回滚的东西），且不需要人批（§5 风险表 L0）。
ABORT = "abort_and_report"

# 大多数只读工具要的是「对被访问 DocType 的读权限」，具体 DocType 由调用参数决定。
DOC_READ = "<被访问 DocType>.read"

# ---------------------------------------------------------------------------
# 证据充分性门禁 L1 / L2 / L3（`docs/design/agents-and-roles.md` §5.0 ①）
#
# §7.3.1 把它归为只读工具契约约束的第一件事：**什么时候允许停下来**。
#
# **L1/L2 由 Spike 02 实测产出**：受约束 Agent 对销售订单只调一次 `doc.get` 就下结论，
# 每个数字都对、业务结论完全错。L2 由 `qwen3:14b` 补出——它照 L1 调了 `doc.links`、
# 看到了那张解释单，**却没打开它**，于是得出与不查血缘时同样错误的结论。
#
# ⚠️ **原案例已随 D-9 退役**（那张解释单是 XM 自建的 custom DocType）。
# 规则 L1/L2 本身不依赖它，措辞未动；失效的只是推出它们的那个案例。
#
# **L3 由 P1.0 入口关口实验设计**，针对的是一种 L1/L2 都盖不住的形状：
# 答案涉及某个仓库的库存**数量**时，从任何一张单据出发的血缘都可能只覆盖
# 部分入库来源 —— 恒锐动力的数据集里，外协批那 1,000 台在 ERPNext v15 的结构上
# 就挂不回销售订单（`Subcontracting Order` 没有 `sales_order` 字段）。
# 沿订单查得再深也看不见它，**必须从库存流水反查凭证**。
#
# → L1/L2 管「顺着链条查得够不够深」，**L3 管「入库来源查得够不够全」**。
# 前两条是**深度**，第三条是**覆盖**。
# ---------------------------------------------------------------------------

EVIDENCE_GATE_L1 = Condition(
    text="问题点名了某张单据 → 接受 answer 之前，必须已对它调用过 doc.links",
    fact="doc_links_called_for",
    operator="covers_fact",
    value="documents_named_in_question",
    source=f"{ROLES} §5.0 ① 规则 L1",
)

EVIDENCE_GATE_L2 = Condition(
    text="doc.links 查出的已提交下游单据 → 必须逐张 doc.get 之后才能作答",
    fact="doc_get_called_for",
    operator="covers_fact",
    value="submitted_downstream_documents",
    source=f"{ROLES} §5.0 ① 规则 L2（由 qwen3:14b 实测补出）",
)

EVIDENCE_GATE_L3 = Condition(
    text=(
        "作答涉及某个仓库的库存数量 → 必须已对该库存的全部入库来源逐个 doc.get，"
        "且来源集合覆盖库存流水里每一张使数量增加的凭证"
    ),
    fact="doc_get_called_for",
    operator="covers_fact",
    value="inbound_vouchers_of_quantities_in_answer",
    source=f"{ROLES} §5.0 ① 规则 L3（由 P1.0 入口关口实验设计）",
)

# ⚠️ **L3 的措辞必须保持通用**，不得出现任何具体单号、DocType 名或数量。
# 它是照着一个已知陷阱设计的，天然对那个陷阱有效；写进具体单号就成了
# 「照答案写规则」，实验会自证为真而毫无信息量。
# 判据：`tests/unit/test_evidence_gate.py` 用一条**与该陷阱无关**的合成轨迹反测。

EVIDENCE_GATE = (EVIDENCE_GATE_L1, EVIDENCE_GATE_L2, EVIDENCE_GATE_L3)

# 门禁挂在**作答类**工具上：这两个工具的返回值就是答案里的数字。
# `doc.get` / `doc.links` 本身是 L1/L2 要求的**取证步骤**，拿门禁去卡取证步骤是循环依赖
# （L1 卡住第一次 doc.links 就再也调不出 doc.links），所以它们不挂。
ANSWERING_TOOLS = ("query.read", "snapshot.read")


QUERY_READ = ToolContract(
    tool="query.read",
    target="任意业务 DocType（由调用参数指定）",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=EVIDENCE_GATE,
    postconditions=(
        Condition(
            text="返回的每一行都必须来自调用方声明的 DocType，不得跨表拼装",
            fact="rows_all_from_requested_doctype",
            source=f"{BOUNDARIES} §7.2",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "只返回调用方点名的字段；未点名时按 DocType 的 in_list_view 字段集返回",
            "剥离 modified / creation / owner / _comments / _liked_by 等框架管道字段",
        ),
        max_rows=200,
        must_keep=("name", "docstatus"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

SCHEMA_SEARCH = ToolContract(
    tool="schema.search",
    target="DocType 元数据（全站）",
    risk="L0",
    requires_permission=(),
    preconditions=(),
    postconditions=(
        Condition(
            text="检索按「召回器」而非「选择器」设计：只负责给候选清单，由模型结合 meta.fields 定夺",
            fact="returns_candidate_list_not_single_pick",
            source=f"{MEMORY} §8.1 修正后的 ②（Top-10 有 90%、Top-1 只有 65%）",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "只索引表里真有数据的 DocType（本站点 542 → 88，干扰项几乎全部来自空表）",
            "每个候选只回名字 + 人话描述，不回整份 schema",
        ),
        max_rows=10,
        must_keep=("doctype", "module"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

SNAPSHOT_READ = ToolContract(
    tool="snapshot.read",
    target="站点状态快照",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=EVIDENCE_GATE,
    postconditions=(
        Condition(
            text="快照必须已被规范化（剥离 modified / creation / owner / _comments 并稳定排序），否则两份快照 diff 无意义",
            fact="snapshot_normalized",
            source=f"{BOUNDARIES} §11.1「规范化器」",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "剥离 modified / creation / owner / _comments 等易变字段",
            "键按字典序稳定排序，使同一状态两次读出字节一致",
        ),
        max_rows=500,
        must_keep=("snapshot_id", "captured_at"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

LINEAGE_TRACE = ToolContract(
    tool="lineage.trace",
    target="单据血缘（任意业务单据）",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=(),
    postconditions=(
        Condition(
            text="必须扫主表级 Link 字段",
            fact="scanned_link_levels",
            operator="contains",
            value="doctype",
            source=f"{ROLES} §5.1「lineage.trace 的硬约束」",
        ),
        Condition(
            text="必须扫子表级 Link 字段——实测 21 个指向 Sales Order 的 Link 里 14 个在子表，只扫主表会返回空结果",
            fact="scanned_link_levels",
            operator="contains",
            value="child_table",
            source=f"{ROLES} §5.1「lineage.trace 的硬约束」",
        ),
        Condition(
            text="子表命中必须回溯到父单据，否则返回的是明细行而不是单据",
            fact="child_hits_resolved_to_parent",
            source=f"{ROLES} §5.1「lineage.trace 的硬约束」",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "每张关联单据只回单号 / DocType / docstatus / 关联字段，不回整单",
            "排除已取消（docstatus == 2）的关联单据",
        ),
        max_rows=100,
        must_keep=("name", "doctype", "docstatus", "linked_via"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

RULE_LOOKUP = ToolContract(
    tool="rule.lookup",
    target="行业包业务合理性规则",
    risk="L0",
    requires_permission=(),
    preconditions=(
        Condition(
            text="行业包必须已装载——「无需指令」成立，「无需规则」不成立",
            fact="industry_pack_loaded",
            source=f"{ROLES} §5.0 ②",
        ),
    ),
    postconditions=(
        Condition(
            text="返回的规则必须带出处（行业包 ID + 规则 ID），否则下游无法回溯谁定的这条判断",
            fact="rules_carry_provenance",
            source=f"{ROLES} §5.0 ②",
        ),
    ),
    returns=Returns(
        trim_rules=("只回与被问 DocType / 场景相关的规则，不倒整份规则库",),
        max_rows=50,
        must_keep=("pack_id", "rule_id", "statement"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

SYSTEM_OVERVIEW = ToolContract(
    tool="system.overview",
    target="站点全局（公司、核心 DocType、数据时间范围）",
    risk="L0",
    requires_permission=(),
    preconditions=(),
    postconditions=(
        Condition(
            text="必须给出公司名——实测中缺它导致模型把公司名当客户名查，白费 2–3 次调用",
            fact="company_names",
            operator="not_empty",
            source=f"{ROLES} §5.1（Spike 01 实测产出）",
        ),
        Condition(
            text="必须给出数据时间范围，否则模型会对着空区间提问",
            fact="data_time_range",
            operator="not_empty",
            source=f"{ROLES} §5.1（Spike 01 实测产出）",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "核心 DocType 只回有数据的，按记录数降序",
            "按 app 过滤掉 Frappe 框架自身的 DocType",
        ),
        max_rows=40,
        must_keep=("companies", "core_doctypes", "data_time_range"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

PERMISSION_SCOPE = ToolContract(
    tool="permission.scope",
    target="当前身份的可见范围",
    risk="L0",
    requires_permission=(),
    preconditions=(),
    postconditions=(
        Condition(
            text="必须逐个调 frappe.has_permission，不能从 DocPerm / Custom DocPerm 表反推"
            "——反推版漏报了 Sales Invoice，而该用户明明读得到；漏报比噪声更危险",
            fact="permission_probe_method",
            operator="equals",
            value="has_permission",
            source=f"{ROLES} §5.1 实现约束 1（Spike 01/02 实测）",
        ),
        Condition(
            text="由控制循环在会话开场自动注入，不依赖模型想起来调用"
            "——补上后同一道越权问题的工具调用从 35 次降到 1 次",
            fact="injected_at_session_start",
            source=f"{ROLES} §5.1（Spike 02 复测）",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "必须按 app 过滤掉 Frappe 框架自身的 DocType"
            "——不过滤时老板 83 个、工人 61 个，九成是 Token Cache / Desktop Icon / "
            "Voice Call Settings 这类管道；过滤后分别是 34 个和 12 个",
        ),
        max_rows=60,
        must_keep=("doctype", "can_read"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

DOC_GET = ToolContract(
    tool="doc.get",
    target="单张业务单据",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=(),
    postconditions=(
        Condition(
            text="单据的子表明细必须一并返回，否则下游拿不到 warehouse / against_sales_order 这类挂在子表上的事实",
            fact="child_tables_included",
            source=f"{ROLES} §5.1「lineage.trace 的硬约束」同源",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "剔除 _comments / _liked_by / _assign / _user_tags 一类框架字段——不裁剪等于把它们倒给模型",
            "剔除 modified_by / idx 等无业务含义的管道字段",
        ),
        max_rows=1,
        must_keep=("name", "doctype", "docstatus"),
        # §7.5 的声明位：备注 / 评论 / 异常处理说明 / 附件描述都是用户可写自由文本，
        # 由 doc.get 原样返回，构成真实的提示注入攻击面（Spike 01 探针 5 已复现可提权路径）。
        # v0 只留声明，**包裹动作不在 v0 内**。
        user_writable_free_text=True,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

DOC_LINKS = ToolContract(
    tool="doc.links",
    target="单据的上下游关联",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=(),
    postconditions=(
        Condition(
            text="必须返回 from_is_submittable，否则下游筛选会整类丢掉不可提交的业务单据",
            fact="fields_returned",
            operator="contains",
            value="from_is_submittable",
            source=f"{BOUNDARIES} §7.3.1（架构文档是该字段名的 owner）",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "下游筛选规则是「排除已取消（docstatus == 2）」，**不是**「只要已提交」"
            "——草稿下游同样是证据，滤掉它会把 L2 门禁架空",
            "每条关联只回单号 / DocType / 关联字段，不回整单",
        ),
        max_rows=100,
        # `from_is_submittable` 取自 module-boundaries.md §7.3.1；
        # docs/analysis/2026-08-19-pre-build-validation.md 写的是 `is_submittable`，
        # 那是历史分析记录，架构文档是 owner，实现照架构文档取。
        must_keep=("name", "doctype", "docstatus", "from_is_submittable"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)

META_FIELDS = ToolContract(
    tool="meta.fields",
    target="单个 DocType 的字段表",
    risk="L0",
    requires_permission=(DOC_READ,),
    preconditions=(),
    postconditions=(
        Condition(
            text="必须区分主表字段与子表字段，否则结构化导航会在子表上失明",
            fact="fields_tagged_by_level",
            source=f"{MEMORY} §8.1（结构化导航打赢了语义检索）",
        ),
    ),
    returns=Returns(
        trim_rules=(
            "剔除 Section Break / Column Break / HTML 一类纯排版 fieldtype",
            # 🔴 2026-08-27 改：原文是「剔除 hidden 且无数据的字段」，而实现逐字
            # `or field.get("hidden")` —— **无条件剔**，实现比契约严。
            # 实测代价：独立评测集里 2 个正解字段是 hidden ⇒ agent 永远看不见，
            # 而失败会伪装成「它答不出来」。⇒ 改成**保留并标记**，两边对齐。
            "hidden 字段**保留并标记 `hidden: true`** —— 界面上不显示 ≠ 不是那个字段",
            "给了 keywords 就只回命中的行；一个都没命中则回全量（空结果会让"
            "「关键词写偏了」和「真没有」长得一样）",
        ),
        max_rows=200,
        must_keep=("fieldname", "fieldtype", "label"),
        user_writable_free_text=False,
    ),
    on_violation=ABORT,
    approval=APPROVAL_NOT_REQUIRED,
)


READONLY_CONTRACTS: tuple[ToolContract, ...] = (
    QUERY_READ,
    SCHEMA_SEARCH,
    SNAPSHOT_READ,
    LINEAGE_TRACE,
    RULE_LOOKUP,
    SYSTEM_OVERVIEW,
    PERMISSION_SCOPE,
    DOC_GET,
    DOC_LINKS,
    META_FIELDS,
)

READONLY_TOOL_NAMES: tuple[str, ...] = tuple(c.tool for c in READONLY_CONTRACTS)

_BY_NAME = {c.tool: c for c in READONLY_CONTRACTS}


def get(tool: str) -> ToolContract:
    """按工具名取契约。取不到就抛 `KeyError`——静默返回 None 会让调用方在下一行才炸。"""
    return _BY_NAME[tool]
