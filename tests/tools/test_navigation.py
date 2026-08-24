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
CANDIDATES = (*READABLE, *UNREADABLE)


@pytest.fixture
def worker_site(fake_site):
    """把假站点收窄成受限身份看到的样子：三个可读、三个读不到。"""
    for doctype in UNREADABLE:
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
        **{doctype: False for doctype in UNREADABLE},
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
