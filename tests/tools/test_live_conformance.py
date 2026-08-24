"""活站点合规判据：十个工具各跑一次，断言**返回形状合契约**。

⚠️ **判据不许只验「调得通」。**「调得通」与「守约」是两件事，而后者才是契约存在的理由
（CP9 继承项①：退出码 0 不是充分判据）。因此这里逐条核对的是：
`must_keep` 的字段都在 · 行数 ≤ `max_rows` · 框架管道字段已剥离 · 自由文本带数据边界标记。

**核对逻辑在本文件里重写了一遍**，不调 `runtime` 的私有函数：
拿被测代码去验被测代码，等于让它自己给自己判卷。

⚠️ **本文件是 P1.0a §5.1 说的那份「将来要被人提升进 `tests/gates/` 的内容」。**
断言强度不因为换了路径而降低。**执行者不得自行搬运**——`tests/gates/**` 在红线内，
提升进去并接进 CI 需要人操作（`Gates-Change-Approved-By:` trailer）。

无凭据 / 无站点时 **skip**（本目录不在 `tests/gates/**` 内，那边的「不许 skip」不适用），
但 skip 的理由必须打印出来：静默跳过与「跑过且全绿」在退出码上一样。
"""

from __future__ import annotations

import os

import pytest

from agenerp.contracts import ReadOnlyContext
from agenerp.site import SiteError, client_from_env
from agenerp.seedusers import WORKER_EMAIL, WORKER_PASSWORD_ENV, READABLE_DOCTYPES
from agenerp.site import SiteClient, default_base_url
from agenerp.tools.runtime import (
    DATA_BOUNDARY_CLOSE,
    DATA_BOUNDARY_OPEN,
    FRAMEWORK_KEYS,
    STRUCTURAL_KEYS,
    execute,
)
from agenerp.tools_readonly import READONLY_CONTRACTS, get as contract_of

SITE_ENV = "AGENERP_SITE"

ORDER = ("Sales Order", "SAL-ORD-2026-00001")

# 十个工具各一组调用参数。`rule.lookup` 在本期没有行业包，它的**合规行为是指名报错**，
# 因此单列在下面的 `test_rule_lookup_...` 里，不混进「成功返回」这一组。
CASES = {
    "system.overview": {},
    "schema.search": {"keywords": "stock"},
    "meta.fields": {"doctype": ORDER[0]},
    "doc.get": {"doctype": ORDER[0], "name": ORDER[1]},
    "doc.links": {"doctype": ORDER[0], "name": ORDER[1]},
    "lineage.trace": {"doctype": ORDER[0], "name": ORDER[1], "depth": 2},
    "query.read": {"doctype": "Bin", "fields": ["item_code", "warehouse", "actual_qty"]},
    "snapshot.read": {"scope": "doctypes"},
    "permission.scope": {"doctypes": ["Sales Order", "Work Order", "Item", "GL Entry"]},
}

CONTEXT = ReadOnlyContext(
    {
        # 证据充分性门禁的取证记录：本判据问的是形状，不是某道业务题，故三条都以空集满足。
        "doc_links_called_for": [],
        "documents_named_in_question": [],
        "doc_get_called_for": [],
        "submitted_downstream_documents": [],
        "inbound_vouchers_of_quantities_in_answer": [],
        # 开场自动注入是**编排面**的事实（P1.3 的行为），工具自己推不出来，只能由调用方给。
        "injected_at_session_start": True,
    }
)


def _skip(reason: str) -> None:
    print(f"[live-conformance] 跳过：{reason}")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def live_client():
    site = os.environ.get(SITE_ENV, "").strip()
    if not site:
        _skip(f"没有活站点：设置 {SITE_ENV} 与站点凭据后重跑")
    try:
        return client_from_env(site)
    except SiteError as exc:
        _skip(f"站点凭据不全：{exc}")


def _rows_and_envelope(result):
    """把返回值拆成 `(信封, 行)`。行的位置取执行体声明的 `rows_key`——从形状上猜会猜错：
    `schema.search` 的信封里有两个数组（`keywords` 与 `candidates`）。"""
    data = result.data
    if result.rows_key is not None:
        return data, data.get(result.rows_key, [])
    if isinstance(data, list):
        return {}, data
    return (data if isinstance(data, dict) else {}), []


def _strings(value, keep):
    """递归收集返回值里所有**该被包裹**的字符串（结构键与 `must_keep` 不算）。"""
    if isinstance(value, dict):
        return [s for k, v in value.items() if k not in keep for s in _strings(v, keep)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item, keep)]
    return [value] if isinstance(value, str) and value else []


def _framework_keys_present(value) -> set[str]:
    if isinstance(value, dict):
        found = set(value) & set(FRAMEWORK_KEYS)
        for item in value.values():
            found |= _framework_keys_present(item)
        return found
    if isinstance(value, list):
        found = set()
        for item in value:
            found |= _framework_keys_present(item)
        return found
    return set()


@pytest.mark.parametrize("tool", sorted(CASES), ids=sorted(CASES))
def test_live_return_shape_conforms_to_the_contract(tool, live_client):
    contract = contract_of(tool)
    result = execute(tool, CASES[tool], client=live_client, context=CONTEXT)
    assert result.ok, result.report()

    envelope, rows = _rows_and_envelope(result)
    keep = set(contract.returns.must_keep)
    missing = keep - set(envelope)
    for row in rows:
        assert not (missing - set(row)), f"{tool} 的行缺少 must_keep 字段：{missing - set(row)}"
    if not rows:
        assert not missing, f"{tool} 的返回值缺少 must_keep 字段：{missing}"

    assert len(rows) <= contract.returns.max_rows, f"{tool} 超过 max_rows"
    leaked = _framework_keys_present(result.data)
    assert not leaked, f"{tool} 把框架管道字段倒了出来：{sorted(leaked)}"


def test_live_free_text_carries_the_data_boundary_marker(live_client):
    """声明了会返回用户可写自由文本的工具（本期只有 `doc.get`），每一条都必须带标记。"""
    declared = [c.tool for c in READONLY_CONTRACTS if c.returns.user_writable_free_text]
    assert declared == ["doc.get"]

    result = execute("doc.get", CASES["doc.get"], client=live_client, context=CONTEXT)
    assert result.ok, result.report()

    keep = set(contract_of("doc.get").returns.must_keep) | set(STRUCTURAL_KEYS)
    values = _strings(result.data, keep)
    assert values, "doc.get 没有返回任何自由文本，这条判据会变成空断言"
    unwrapped = [
        value
        for value in values
        if not (value.startswith(DATA_BOUNDARY_OPEN) and value.endswith(DATA_BOUNDARY_CLOSE))
    ]
    assert not unwrapped, f"这些自由文本没有被数据边界标记包住：{unwrapped[:3]}"


def test_live_rule_lookup_names_what_is_missing(live_client):
    """本期没有行业包 → 指名报错才是合规行为，返回空清单会被读成「查过了，没有规则」。"""
    result = execute(
        "rule.lookup",
        {"doctype": ORDER[0]},
        client=live_client,
        context=ReadOnlyContext({**dict(CONTEXT.facts), "industry_pack_loaded": True}),
    )

    assert result.ok is False
    assert "行业包" in " ".join(result.reasons)


def test_live_permission_scope_has_a_real_negative(live_client):
    """**判别力的真反例**：以受限身份跑一次，结果里必须至少有一个 DocType 读不到。

    全 `true` 的返回值不算通过 —— 一个永远回 `true` 的假实现在 Administrator 身上
    与正确实现长得一模一样（`docs/masterplan/STATE.md` §3 2026-08-24T03:18Z）。
    """
    password = os.environ.get(WORKER_PASSWORD_ENV, "").strip()
    if not password:
        _skip(f"受限身份口令未设：设置 {WORKER_PASSWORD_ENV}（装载见 agenerp.seedusers）")
    worker = SiteClient(
        os.environ[SITE_ENV],
        base_url=default_base_url(),
        admin_user=WORKER_EMAIL,
        admin_password=password,
    )
    candidates = [*READABLE_DOCTYPES, "Sales Order", "GL Entry", "Account"]

    result = execute("permission.scope", {"doctypes": candidates}, client=worker, context=CONTEXT)

    assert result.ok, result.report()
    readable = {row["doctype"] for row in result.data if row["can_read"]}
    denied = {row["doctype"] for row in result.data if not row["can_read"]}
    assert denied, "受限身份对每个候选都读得到 —— 判别力没验出来"
    assert readable == set(READABLE_DOCTYPES), f"可读集合与装载器声明的不符：{readable}"
    assert result.facts["permission_probe_method"] == "has_permission"
