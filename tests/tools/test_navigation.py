"""编排层（P1.3）的判据 —— 开场自动注入 / 导航质量 / 权限拒绝熔断。

`docs/masterplan/02-WBS.md` §4 第 82 行的验收原文点名的就是这个文件。
全部判据跑在 `tests/tools/conftest.py` 的假站点上：**零网络、零凭据、零 docker**。

**判据落在行为上，不落在标志位上。** 「开场注入发生过」这条事实从
`FakeSite.requests` 里核出那几次 `POST /api/method/frappe.client.has_permission`；
一个只写 `opening_injection_verified = True` 而不真注入的装配器必须在这里红
（`test_a_flag_without_a_real_injection_is_not_verified`）。
"""

from __future__ import annotations

import json

import pytest

from agenerp.orchestration.opening import (
    CONTRACT_FACT,
    PACK_FACT,
    InjectionCost,
    OpeningPack,
    open_session,
)

# 受限身份「车间工人」的可见范围（`agenerp/seedusers.py` 的 READABLE_DOCTYPES 同形）。
# ⚠️ **现成的 `fake_site` 夹具对一切回 `True`**（`permissions` / `forbidden` 都是空的），
# 拿它验不出「`can_read: False` 的行照样返回」——判据必须自己把某几个置 `False`。
READABLE = ("Work Order", "Item", "Stock Entry")
UNREADABLE = ("Sales Order", "GL Entry", "Customer")

# 「能回答同一个问题的其它路线」—— §7.4 记的越权探测形状里模型挨个试过的那些。
# 不知道可见范围时它们会被逐条试，知道时一条都不用试。
ALTERNATES = ("Payment Entry", "Journal Entry", "Cost Center", "Sales Invoice")

CANDIDATES = (*READABLE, *UNREADABLE, *ALTERNATES)


@pytest.fixture
def worker_site(fake_site):
    """把假站点收窄成受限身份看到的样子：三个可读，其余一律读不到。"""
    for doctype in (*UNREADABLE, *ALTERNATES):
        fake_site.permissions[doctype] = False
        fake_site.forbidden.add(doctype)
    for doctype in READABLE:
        fake_site.permissions[doctype] = True
    return fake_site


def has_permission_calls(site) -> list[dict]:
    """站点上真的发生过的每一次权限探测。**这是「注入发生过」的唯一判据面。**"""
    return [
        json.loads(request.body or b"{}")
        for request in site.requests
        if request.url.endswith("/api/method/frappe.client.has_permission")
    ]


def doctype_metadata_calls(site) -> list[str]:
    """元数据枚举请求（发现式路径的形状）。带候选集注入时这里必须为空。"""
    return [
        request.url
        for request in site.requests
        if "/api/resource/DocType" in request.url and request.method == "GET"
    ]


# ── ① WBS 验收原文那一条：开场注入**真的发生**了 ──────────────────────────────
def test_opening_injection_really_happens_on_the_site(worker_site, fake_client):
    """断言落在 `FakeSite.requests` 上，不落在标志位上。

    一个只把 `opening_injection_verified` 写成 `True` 的装配器在这里必然红：
    它一个 `has_permission` 都发不出来。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    probed = [call["doctype"] for call in has_permission_calls(worker_site)]
    assert probed == list(CANDIDATES)
    assert pack.injection_verified is True
    assert pack.result is not None and pack.result.ok, pack.result.report()


# ── ② 注入产物里含 `can_read: False` 的行 ────────────────────────────────────
def test_the_injected_scope_keeps_the_rows_it_cannot_read(worker_site, fake_client):
    """全是 `True` 是假实现的形状：一个永远回 true 的 `permission.scope`
    与正确实现在「只返回可见的那一半」的口径下长得一模一样。"""
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    answers = {row["doctype"]: row["can_read"] for row in pack.scope}
    assert answers == {
        **{doctype: True for doctype in READABLE},
        **{doctype: False for doctype in (*UNREADABLE, *ALTERNATES)},
    }
    assert any(row["can_read"] is False for row in pack.scope)


def test_the_pack_separates_unknown_from_unreadable(worker_site, fake_client):
    """`readable()` 对没探过的 DocType 回 `None`，不回 `False`。

    混成一件事的话，导航策略会把「我不知道」当成「不可读」而提前拒答。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    assert pack.readable("Work Order") is True
    assert pack.readable("Sales Order") is False
    assert pack.readable("Delivery Note") is None


# ── ③ `permission_probe_method` 来自执行体，未被装配器覆盖 ────────────────────
def test_the_probe_method_fact_comes_from_the_executor(worker_site, fake_client):
    """执行体从**本次实际调过的方法名**推出这条事实（`runtime.Session.methods()`）。
    装配器在 `ToolResult` 之后重写它，就等于让被考的人填成绩单（变异 M6）。"""
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    assert pack.facts["permission_probe_method"] == "has_permission"
    assert pack.result is not None
    assert pack.facts["permission_probe_method"] == pack.result.facts["permission_probe_method"]


class _TracedMethod(str):
    """与 `"has_permission"` **相等、但不是同一个对象**的字符串。

    `str` 的子类实例不会被 CPython 驻留，因此 `is` 判得出「这个值是不是执行体那一个」。
    """


def test_the_probe_method_fact_is_carried_over_by_identity(worker_site, fake_client):
    """**同一性，不是相等** —— 装配器必须把执行体那个值原样搬过来。

    ⚠️ 这一条是变异自查 **M6 当场逼出来的**：原先只断言
    `pack.facts[...] == result.facts[...]`，而一个「装配路径上把它写死成
    `'has_permission'`」的假实现让两边**同时**变成那个字面量，断言照样绿。
    换成 `is` 之后，写死的字面量不可能是执行体交出来的那个对象。
    """
    from agenerp.tools.runtime import Outcome

    traced = _TracedMethod("has_permission")

    def probing_executor(session, params):
        session.call_method("frappe.client.has_permission", {"doctype": CANDIDATES[0]})
        rows = [{"doctype": name, "can_read": name in READABLE} for name in CANDIDATES]
        return Outcome(data=rows, facts={"permission_probe_method": traced})

    pack = open_session(
        client=fake_client,
        doctypes=CANDIDATES,
        executors={"permission.scope": probing_executor},
    )

    assert pack.result is not None and pack.result.ok, pack.result.report()
    assert pack.facts["permission_probe_method"] is traced


def test_the_pack_never_invents_a_probe_method(worker_site, fake_client):
    """执行体没推出这条事实时，开场包**不许凭空补一个** —— 补了就是替被考的人填成绩单。

    执行体一个 `has_permission` 都没调 → 后置断言不成立 → `execute` abort →
    `ToolResult.facts` 为空 → 开场包里这个键必须**不存在**。
    """
    from agenerp.tools.runtime import Outcome

    def silent_executor(session, params):
        session.list_rows("DocType", {})
        return Outcome(data=[{"doctype": "Item", "can_read": True}], facts={})

    pack = open_session(
        client=fake_client,
        doctypes=CANDIDATES,
        executors={"permission.scope": silent_executor},
    )

    assert pack.result is not None and pack.result.ok is False
    assert "permission_probe_method" not in pack.facts
    assert pack.injection_verified is False


def test_the_caller_cannot_smuggle_the_pack_fact_in(worker_site, fake_client):
    """调用方传进来的同名值**一律不进开场包**。

    ⚠️ 这一条与契约面那条 `injected_at_session_start` **不是同一件事**：
    后者按机制**必须**由调用方交进去（否则契约在后置上 abort），且本层不宣称它被加强。
    """
    pack = open_session(
        client=fake_client,
        doctypes=CANDIDATES,
        facts={PACK_FACT: "调用方塞进来的", "industry_pack_loaded": True},
    )

    assert pack.facts[PACK_FACT] is True  # 推导出来的，不是调用方那个字符串
    assert CONTRACT_FACT not in pack.facts
    assert "industry_pack_loaded" not in pack.facts


def test_the_assembler_must_hand_the_contract_fact_to_execute(worker_site, fake_client):
    """契约面那条由装配器交进 `ReadOnlyContext` —— 不交就必然 abort。

    这条判据钉住的是**机制**（`runtime.py` 的 `{**caller_facts, **outcome.facts}` +
    `contracts.py` 的「事实缺席即判否」），免得有人以为「不传也能过」。
    """
    from agenerp.contracts import ReadOnlyContext
    from agenerp.tools.runtime import execute

    without = execute(
        "permission.scope",
        {"doctypes": list(CANDIDATES)},
        client=fake_client,
        context=ReadOnlyContext({}),
    )

    assert without.ok is False
    assert without.stage == "postconditions"
    assert any(CONTRACT_FACT in reason for reason in without.reasons)
    # 而装配器交了，所以它拿到的是 ok=True
    assert open_session(client=fake_client, doctypes=CANDIDATES).result.ok is True


# ── ④ 反测 A：跳过 `execute`、只写标志 → 必须红 ──────────────────────────────
def test_a_flag_without_a_real_injection_is_not_verified(worker_site, fake_client):
    """「只写标志不真注入」的形状：手工造一个 `opening_injection_verified = True`
    的开场包。判据面是站点留痕 —— 站点上一次探测都没发生过。"""
    faked = OpeningPack(facts={PACK_FACT: True}, cost=InjectionCost(0, len(CANDIDATES)))

    assert faked.injection_verified is True  # 标志位骗得过
    assert has_permission_calls(worker_site) == []  # 行为骗不过
    assert faked.scope == ()
    assert faked.readable("Work Order") is None


def test_the_derivation_rejects_a_result_that_never_touched_the_site(fake_client):
    """推导判据本身的反测：`ok=True` 但 `request_count == 0` 的产物不算注入发生过。

    只看 `ok is True` 的推导会在这里绿 —— 那正是变异 M1 要钻的空子。
    """
    from agenerp.orchestration.opening import _verified
    from agenerp.tools.runtime import ToolResult

    rows = [{"doctype": "Item", "can_read": True}]
    assert _verified(ToolResult("permission.scope", True, rows, request_count=1), rows) is True
    assert _verified(ToolResult("permission.scope", True, rows, request_count=0), rows) is False
    assert _verified(ToolResult("permission.scope", False, rows, request_count=1), rows) is False
    assert _verified(ToolResult("doc.get", True, rows, request_count=1), rows) is False
    assert _verified(ToolResult("permission.scope", True, [], request_count=1), []) is False
    assert (
        _verified(
            ToolResult("permission.scope", True, [{"doctype": "Item"}], request_count=1),
            [{"doctype": "Item"}],
        )
        is False
    )


# ── ⑤ 反测 B：带候选集注入时不得走发现式路径 ─────────────────────────────────
def test_a_given_candidate_set_never_triggers_metadata_discovery(worker_site, fake_client):
    """受限身份枚举不出 DocType 清单（§7.6 限制 1），所以带候选集的注入
    **一个元数据枚举请求都不许发**，且探测次数恰等于候选集大小。"""
    open_session(client=fake_client, doctypes=CANDIDATES)

    assert doctype_metadata_calls(worker_site) == []
    assert len(has_permission_calls(worker_site)) == len(CANDIDATES)


def test_without_a_candidate_set_it_does_discover(fake_site, fake_client):
    """对照组：不给候选集才走发现式路径 —— 那条路径的形状就是元数据枚举请求。"""
    open_session(client=fake_client)

    assert doctype_metadata_calls(fake_site) != []


# ── ⑥ 注入代价可断言（M7 的靶子）────────────────────────────────────────────
def test_the_injection_cost_matches_what_really_happened(worker_site, fake_client):
    """代价必须与**实际发生的请求**对得上。

    只断言 `request_count > 0` 挡不住把代价写成常量的实现，所以这里钉的是
    「等于站点上 `has_permission` 的条数」且「等于候选集大小」两条。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    assert pack.cost.candidate_count == len(CANDIDATES)
    assert pack.cost.request_count == len(has_permission_calls(worker_site))
    assert pack.cost.request_count == len(CANDIDATES)


def test_the_cost_tracks_a_smaller_candidate_set(worker_site, fake_client):
    """换一组候选集，代价跟着变 —— 常量实现在这一条上红。"""
    pack = open_session(client=fake_client, doctypes=READABLE)

    assert pack.cost.candidate_count == len(READABLE)
    assert pack.cost.request_count == len(READABLE)
    assert pack.cost.request_count == len(has_permission_calls(worker_site))


def test_the_discovery_path_reports_an_unknown_candidate_count(fake_site, fake_client):
    """发现式路径下装配器数不出候选集大小，就照实回 `None`，不编一个数出来。"""
    pack = open_session(client=fake_client)

    assert pack.cost.candidate_count is None
    assert pack.cost.request_count == pack.result.request_count > len(has_permission_calls(fake_site))


# ── 开场包与 ① 即时上下文 / ② 会话的接缝 ─────────────────────────────────────
def test_the_injection_is_recorded_into_the_conversation_session(worker_site, fake_client):
    """注入产物记进 ② 对话会话的「已执行动作」档（§8.2 规则 ②：不可压缩）。"""
    from agenerp.context.session import start

    pack = open_session(
        client=fake_client, doctypes=CANDIDATES, session=start("s-1", user="worker")
    )

    assert pack.session is not None
    assert [action.tool for action in pack.session.actions] == ["permission.scope"]
    assert pack.session.actions[0].request_count == len(CANDIDATES)
    assert "permission.scope" in pack.session.audit_records()[0]


def test_the_pack_carries_the_immediate_context_untouched(worker_site, fake_client):
    """① 即时上下文由 P1.2 装配，本层只把它摆进开场包，不改一个字段。"""
    from agenerp.context.immediate import assemble

    immediate = assemble(
        doctype="Work Order",
        name="MFG-WO-2026-00001",
        fields={"status": "In Process"},
        role="车间工人",
        view="工单详情",
    )
    pack = open_session(client=fake_client, doctypes=CANDIDATES, immediate=immediate)

    assert pack.immediate is immediate


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 · 导航质量判据 —— 在本仓自己的夹具上量，不搬外部数字
#
# 判据形状是 **方向 + 上界**，不钉具体次数（`Decision`，plan Phase 2）：次数会随夹具
# 演进漂移，钉死它会让判据红在夹具而不是红在实现。两组的具体数字记进
# `module-boundaries.md` §7.6a 的落点节，并逐字标注「本仓夹具实测，非站点实测」。
# ══════════════════════════════════════════════════════════════════════════════

from agenerp.orchestration.navigation import (  # noqa: E402
    Hop,
    NavigationTask,
    ScopeFirstStrategy,
    run_metric,
)

WORK_ORDER = "MFG-WO-2026-00001"

# **题目与预期路径写死在这里，不许执行期改题**（硬约束 ②）。三题的来源逐条注明。
TASKS = (
    # ① 受限身份问不可见 DocType —— §7.4 的越权探测场景（Spike 01 探针 3）。
    NavigationTask(
        name="① 受限身份问不可见 DocType",
        target="GL Entry",
        hops=(Hop("doc.get", {"doctype": "GL Entry", "name": "GL-1"}),),
        alternates=ALTERNATES,
    ),
    # ② 可见范围内的单跳取数 —— 最平常的一问，用来给 H3 的「注入不是免费的」记账。
    NavigationTask(
        name="② 可见范围内的单跳取数",
        target="Work Order",
        hops=(Hop("doc.get", {"doctype": "Work Order", "name": WORK_ORDER}),),
    ),
    # ③ 需要 meta.fields / doc.links 的多跳导航 —— §8.1「结构化导航优先」的形状。
    NavigationTask(
        name="③ 多跳结构化导航",
        target="Work Order",
        hops=(
            Hop("doc.get", {"doctype": "Work Order", "name": WORK_ORDER}),
            Hop("meta.fields", {"doctype": "Work Order"}),
            Hop("doc.links", {"doctype": "Work Order", "name": WORK_ORDER}),
        ),
    ),
)

TASK_UNREADABLE = TASKS[0].name
TASK_SINGLE_HOP = TASKS[1].name
TASK_MULTI_HOP = TASKS[2].name


@pytest.fixture
def strategy():
    """**一个**策略对象。on / off 两组共用它 —— 两组各造一个就测不出注入的差异。"""
    return ScopeFirstStrategy()


@pytest.fixture
def empty_pack():
    """off 组的开场包：没有注入产物，`opening_injection_verified` 为假。"""
    return OpeningPack(cost=InjectionCost(0, None), facts={PACK_FACT: False})


def _run(strategy, pack, site_factory, label):
    return run_metric(strategy, pack, TASKS, client=site_factory(), label=label)


def test_the_two_runs_share_one_strategy_object(worker_site, fake_client, strategy, empty_pack):
    """**同一性，不是相等。** 没有这一条，「骨架内部按开场包分叉、off 那一路另造一个
    实例」的假实现（变异 M3）会恒绿 —— 两份逐位相同的代码产出逐位相同的数字。"""
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    on = run_metric(strategy, pack, TASKS, client=fake_client, label="on")
    off = run_metric(strategy, empty_pack, TASKS, client=fake_client, label="off")

    assert on.strategy is off.strategy
    assert on.strategy is strategy


def test_h1_injection_strictly_cuts_the_calls_on_an_out_of_scope_question(
    worker_site, fake_client, strategy, empty_pack
):
    """**H1**：受限身份问不可见 DocType 时，on 组的 `execute()` 次数**严格小于** off 组。

    off 组不知道可见范围，撞了 403 也不会收手，而是挨个试能回答同一问题的其它路线
    （§7.4 实测的 35 次形状）；on 组开场就知道这些路线一条都读不到。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    on = run_metric(strategy, pack, TASKS, client=fake_client, label="on")
    off = run_metric(strategy, empty_pack, TASKS, client=fake_client, label="off")

    assert on.calls(TASK_UNREADABLE) < off.calls(TASK_UNREADABLE)
    assert on.by_task()[TASK_UNREADABLE].ending == "refuse"
    assert off.by_task()[TASK_UNREADABLE].ending == "refuse"


def test_h2_the_injected_run_needs_at_most_two_calls(worker_site, fake_client, strategy):
    """**H2**：on 组在该题上 ≤ 2 次（1 次注入 + 至多 1 次确认）。上界，不是等号。"""
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    on = run_metric(strategy, pack, TASKS, client=fake_client, label="on")

    assert on.calls(TASK_UNREADABLE) <= 2


def test_h3_injection_is_not_free_on_a_fully_visible_question(
    worker_site, fake_client, strategy, empty_pack
):
    """**H3**（成本记账，不是判别性假设）：完全在可见范围内的题上，
    on 组的调用次数**不小于** off 组。**本 plan 不假装注入没有代价。**

    站点请求那一栏更能说明问题：注入本身就要逐个探候选集，那些请求在 off 组一次都没发。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    on = run_metric(strategy, pack, TASKS, client=fake_client, label="on")
    off = run_metric(strategy, empty_pack, TASKS, client=fake_client, label="off")

    for task in (TASK_SINGLE_HOP, TASK_MULTI_HOP):
        assert on.calls(task) >= off.calls(task)
        assert on.requests(task) > off.requests(task)


def test_h4_a_flag_alone_does_not_reproduce_the_gain(
    worker_site, fake_client, strategy, empty_pack
):
    """**H4 反测**：把 on 组的开场包换成**空包**、但人工把 `opening_injection_verified`
    置真（不经装配器推导）→ **H1 不再成立**。

    ⚠️ 判据取「on 组**不小于** off 组」，不取等号：空包变体里注入那一次算不算、
    怎么算会让计数差 1，钉死等号是给自己挖坑。
    ⚠️ 置真的是**开场包面**那条，不是契约面那条 —— 后者从不进开场包，策略读不到它。
    空包变体仍带这条为真的标志，以确保策略不是靠「包是不是空的」这个旁路分叉。
    """
    faked = OpeningPack(cost=InjectionCost(0, None), facts={PACK_FACT: True})

    on = run_metric(strategy, faked, TASKS, client=fake_client, label="empty-pack")
    off = run_metric(strategy, empty_pack, TASKS, client=fake_client, label="off")

    assert faked.injection_verified is True  # 标志置真了，但没有任何事实
    assert not on.calls(TASK_UNREADABLE) < off.calls(TASK_UNREADABLE)  # H1 不再成立
    assert on.calls(TASK_UNREADABLE) >= off.calls(TASK_UNREADABLE)


def test_the_metric_counts_the_opening_injection_itself(worker_site, fake_client, strategy):
    """计数口径（§6）：`execute()` 次数**含开场注入那一次**，站点请求**另计一栏**。

    口径若能事后选，H1/H3 的真假就由执行者说了算 —— 这条判据把它钉住。
    """
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    on = run_metric(strategy, pack, TASKS, client=fake_client, label="on")

    assert pack.execute_calls == 1
    assert on.calls(TASK_UNREADABLE) == 1  # 拒答不需要再取任何东西，只剩注入那一次
    assert on.requests(TASK_UNREADABLE) >= pack.cost.request_count


def test_every_task_ends_at_an_answer_or_a_refusal(worker_site, fake_client, strategy, empty_pack):
    """终点只有两种，两者都算终点（§6 计数口径第三行）。"""
    pack = open_session(client=fake_client, doctypes=CANDIDATES)

    for run in (
        run_metric(strategy, pack, TASKS, client=fake_client, label="on"),
        run_metric(strategy, empty_pack, TASKS, client=fake_client, label="off"),
    ):
        assert {metric.ending for metric in run.tasks} <= {"answer", "refuse"}
        assert run.by_task()[TASK_UNREADABLE].ending == "refuse"
        assert run.by_task()[TASK_MULTI_HOP].ending == "answer"


def test_the_strategy_reads_facts_not_the_emptiness_of_the_pack(worker_site, fake_client, strategy):
    """策略的分叉点是**开场包里已知的事实**，不是「包是不是空的」。

    一个带着为真标志、却什么事实都没有的包，必须与空包**行为完全一致**。
    """
    from agenerp.orchestration.navigation import NavigationState

    flagged = OpeningPack(cost=InjectionCost(0, None), facts={PACK_FACT: True})
    silent = OpeningPack(cost=InjectionCost(0, None), facts={PACK_FACT: False})

    for task in TASKS:
        assert strategy(task, NavigationState(pack=flagged)) == strategy(
            task, NavigationState(pack=silent)
        )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 · §7.4 权限拒绝熔断
#
# ⚠️ 本组判据证明的是**策略对象的行为**：喂它 N 次权限拒绝，它会刹车、会给出所需权限清单。
# 它**不**证明「真实会话里它一定被调用到」—— 接到真实控制循环上是 P1.4 的动作。
# ══════════════════════════════════════════════════════════════════════════════

from agenerp.orchestration.circuit import (  # noqa: E402
    DENIAL_THRESHOLD,
    DenialBreaker,
    is_permission_denial,
    result_is_permission_denial,
)
from agenerp.site import SiteError  # noqa: E402
from agenerp.tools.runtime import ToolResult  # noqa: E402


def denial(doctype: str = "GL Entry") -> ToolResult:
    """`execute` 对 403 的收敛形态：`ok=False`，站点原文进 `reasons`（不改写）。"""
    return ToolResult(
        tool="doc.get",
        ok=False,
        stage="execute",
        violation="abort_and_report",
        reasons=(f"站点侧失败：GET /api/resource/{doctype}/x → HTTP 403（站点 fake）：{{}}",),
        request_count=1,
    )


def outage() -> ToolResult:
    """站点答不上话。**不是权限拒绝** —— 把它计进熔断就是把「站点坏了」读成「你没权限」。"""
    return ToolResult(
        tool="doc.get",
        ok=False,
        stage="execute",
        violation="abort_and_report",
        reasons=("站点侧失败：GET /api/resource/Item/x → HTTP 500（站点 fake）：{}",),
        request_count=1,
    )


def success() -> ToolResult:
    return ToolResult(tool="doc.get", ok=True, data={}, request_count=1)


def test_five_consecutive_denials_trip_the_breaker():
    """§7.4 第一行：单次会话内连续 N 次权限拒绝 → 立即终止（N 默认 5）。"""
    breaker = DenialBreaker()

    for index in range(DENIAL_THRESHOLD - 1):
        assert breaker.record(denial(f"D{index}"), doctype=f"D{index}") is False
    assert breaker.record(denial("GL Entry"), doctype="GL Entry") is True
    assert breaker.tripped is True


def test_a_success_in_the_middle_clears_the_streak():
    """**「连续」不是「累计」** —— 4 次 403 + 1 次成功 + 4 次 403 → **不刹车**。

    累计版会把一个跑了两小时、零星撞过 5 次权限边界的正常会话误刹。
    """
    breaker = DenialBreaker()

    for _ in range(4):
        breaker.record(denial(), doctype="GL Entry")
    breaker.record(success())
    for _ in range(4):
        breaker.record(denial(), doctype="GL Entry")

    assert breaker.tripped is False
    assert breaker.streak == 4


def test_site_outages_are_not_permission_denials():
    """5 次**非 403** 失败 → **不刹车**。站点宕机不是越权探测。"""
    breaker = DenialBreaker()

    for _ in range(DENIAL_THRESHOLD):
        assert breaker.record(outage(), doctype="Item") is False

    assert breaker.tripped is False
    assert breaker.streak == 0
    assert breaker.denied == ()


def test_an_outage_neither_counts_nor_clears():
    """非 403 的失败**既不计数、也不清零**。

    当成清零处理的话，「每两次 403 之间制造一次超时」就是一条现成的绕过路径；
    当成计数的话，一次站点故障看起来就像一次越权探测。两头都不取，这条钉住它。
    """
    breaker = DenialBreaker()

    for _ in range(4):
        breaker.record(denial(), doctype="GL Entry")
    breaker.record(outage(), doctype="Item")
    assert breaker.streak == 4
    assert breaker.record(denial(), doctype="Payment Entry") is True


def test_the_breaker_names_the_doctypes_it_needs_permission_for():
    """§7.4 第二行：终止时明确返回「你的权限不足以回答这个问题」+ **所需权限清单**。"""
    breaker = DenialBreaker()

    for doctype in ("GL Entry", "Payment Entry", "Journal Entry", "Cost Center", "GL Entry"):
        breaker.record(denial(doctype), doctype=doctype)

    report = breaker.report()
    assert breaker.tripped is True
    assert report.message == "你的权限不足以回答这个问题"
    assert report.required_permissions == (
        "read:GL Entry",
        "read:Payment Entry",
        "read:Journal Entry",
        "read:Cost Center",
    )
    assert "GL Entry" in report.text()


# ── 403 口径与已实测的那一处**行为一致** ─────────────────────────────────────
class _NonForbiddenFailure:
    """包一层 transport，让站点回一个**非 403** 的失败。

    ⚠️ 现成的 `FakeSite` 造不出这种输入：它对 `get_count` 只回 200 或 403。
    """

    def __init__(self, site, doctype):
        self._site = site
        self._doctype = doctype

    def __call__(self, request):
        if self._doctype in (request.body or b"").decode("utf-8", "ignore"):
            from agenerp.site import SiteResponse

            return SiteResponse(500, '{"exception": "站点内部错误"}')
        return self._site(request)


def test_the_orchestration_layer_classifies_403_exactly_like_the_executor(fake_site):
    """**拿行为作基准，不比源码文本。**

    用 `FakeSite` 驱动 `agenerp/tools/site_scope.py` 的 `doctypes_with_data` 两次：
    403 那次进 `unreadable`、非 403 那次原样抛出。断言
    `agenerp/orchestration/circuit.py` 对同样两种输入给出**相同的分类**。

    ⚠️ **残余风险**：两处口径靠这一条断言绑定，有人只改一处且顺手改断言就会漂移。
    """
    from agenerp.site import SiteClient
    from agenerp.tools.runtime import Session
    from agenerp.tools.site_scope import doctypes_with_data

    # ① 403：执行体把它读成「这个身份读不到」
    fake_site.forbidden.add("Sales Order")
    counted, unreadable = doctypes_with_data(Session(client_for_site(fake_site)))
    assert "Sales Order" in unreadable
    assert all(entry["doctype"] != "Sales Order" for entry in counted)

    # 同一种输入交给编排层：同样判成权限拒绝
    forbidden_error = _capture(lambda: fake_site_denial(fake_site, "Sales Order"))
    assert is_permission_denial(forbidden_error) is True

    # ② 非 403：执行体**原样抛出去**，不读成「读不到」
    fake_site.forbidden.discard("Sales Order")
    broken = SiteClient(
        "fake",
        base_url="http://fake",
        api_key="k",
        api_secret="s",
        transport=_NonForbiddenFailure(fake_site, "Sales Order"),
    )
    with pytest.raises(SiteError) as raised:
        doctypes_with_data(Session(broken))

    # 同一种输入交给编排层：同样**不**判成权限拒绝
    assert is_permission_denial(raised.value) is False


def client_for_site(site):
    from agenerp.site import SiteClient

    return SiteClient("fake", base_url="http://fake", api_key="k", api_secret="s", transport=site)


def fake_site_denial(site, doctype):
    from agenerp.tools.runtime import Session
    from agenerp.tools.site_scope import COUNT_METHOD

    Session(client_for_site(site)).call_method(COUNT_METHOD, {"doctype": doctype})


def _capture(call):
    try:
        call()
    except SiteError as exc:
        return exc
    raise AssertionError("期望一次 SiteError，实际没有抛")


def test_the_two_classification_surfaces_agree():
    """异常那一侧与 `ToolResult` 那一侧判的是同一串 —— 两条路都归一个口径。"""
    assert is_permission_denial(SiteError("GET /x → HTTP 403（站点 fake）")) is True
    assert is_permission_denial(SiteError("GET /x → HTTP 500（站点 fake）")) is False
    assert is_permission_denial(ValueError("HTTP 403")) is False

    assert result_is_permission_denial(denial()) is True
    assert result_is_permission_denial(outage()) is False
    assert result_is_permission_denial(success()) is False
