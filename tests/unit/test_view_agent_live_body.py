"""P2.3 · 视图 Agent 活体判据的**断言体**（严格壳在 `tests/agents/test_view_agent_live.py`）。

    set -a; . ~/.config/agenerp/secrets.env; set +a
    export AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY"
    export AGENERP_LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
    export AGENERP_LLM_MODEL=qwen3.8-2.4t-a95b
    export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
           AGENERP_ADMIN_PASSWORD=admin
    python3 -m pytest -m live tests/agents/test_view_agent_live.py -q -rs

## ⚠️ 它现在**不在** `tests/gates/`

人 2026-08-28 裁定：本项先写在 `tests/agents/`，落 `tests/gates/**` 要另行指派
（红线 ②，提交要带 `Gates-Change-Approved-By:`）。
🔴 **将来落地时必须在最终位置重跑** —— `docs/logs/2026/08-28-handoff-p2.md` §3⑤：
「在最终位置跑一遍」和「跑过」是两件事，门禁在草稿位置 5 passed、
落进 `tests/gates/` 后一格都跑不了（fixture 依赖变了）。**换位置本身就是一个变量。**

## 为什么断言体住在 `tests/unit/`，且这里是 `skip` 不是 `fail`

形态与 `tests/unit/test_explain_service_body.py` / `test_render_body.py` 逐条同族：

- **住 `tests/unit/`** ⇒ 受 `pytest tests/unit -q` 那一轮保护，日常改坏了看得见。
  住进判据目录就不受保护了。
- **这里 `skip`** ⇒ 日常那一轮不该因为「没起活栈」而红。
- **严格壳把 `_unavailable` 收严成 `fail`** ⇒ 判据那一份跑起来时，
  缺凭据/够不着站点必须**红**。一条会 skip 的判据等于一条不存在的判据。

🔴 **收严的那一行在壳里，不在这里。** 两份口径分开是刻意的：
把 `fail` 写死在断言体里，日常那轮就会因为没起栈而全红。

## 边界：本文件**不打开浏览器**

「真能画」在本层的含义是 **`plan_render()` 判定落回 = 0**，
即每个块的每个字段类型都在这一版渲染器的封闭表里。
**浏览器那一层归 `tests/render/`**（P2.2 的活体门禁，已过）。
⚠️ 写清楚，免得有人以为本文件证明了「生成的视图在浏览器里长对了」——**它没有**。
P2.3 也没有把任意生成的视图接进服务端渲染那条路（视图落库是 P2.4）。
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

from agenerp import schema_snapshot
from agenerp.dsl.fallback import RENDERABLE_FIELDTYPES
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES
from agenerp.site import SiteError, client_from_env
from agenerp.views.loop import STOP_PROPOSED, propose_view

pytestmark = pytest.mark.live

# 车间工人域 —— 快照覆盖的那 8 张表就是本轮的分母（P2.2 路线 C 的分母）。
# ⚠️ 域外的表**不在快照里**，模型找到域外字段会被 L2 顶回去。那是正确行为，
# 但也意味着**本文件只证明工人域**，推广要另量（同 P2.2 plan 的那句话）。
# ⚠️ **两道题，第二道是防「照抄例子」的。**
#
# 系统提示词里带了一个 `list` 块的例子，而它用的正是工单那几个字段。
# 只问第一道时，「模型答对了」与「模型照抄了提示词里的例子」**在结果上长得一样** ——
# 那正是本仓最忌讳的那种判据（`p1-insight` 复盘 §1.2：绿着，但验的不是它名字说的那件事）。
#
# 第二道刻意换一张表、换一种块类型（`metric` + `agg`），**例子抄不出来**。
REQUEST_LIST = "我想看今天要做的工单，把物料、计划数量和状态列出来"
REQUEST_METRIC = "库存转移一共有多少笔？给我一个数就行"

REQUESTS = (REQUEST_LIST, REQUEST_METRIC)


def _unavailable(reason: str) -> None:
    """跑不了这件事的**唯一出口**。

    🔴 严格壳把这**一个名字**重绑成 `pytest.fail` —— 因此本模块内任何
    「跑不了」都必须经由它，不许有第二条 `pytest.skip`。
    判据侧有一条断言逐条比对，不靠人眼数。
    """
    pytest.skip(reason)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        _unavailable(
            f"{name} 未设置 —— 活体判据要真凭据。\n"
            "  set -a; . ~/.config/agenerp/secrets.env; set +a"
        )
    return value


@pytest.fixture(scope="module")
def live_client():
    _require("AGENERP_LLM_API_KEY")
    _require("AGENERP_LLM_BASE_URL")
    site = _require("AGENERP_SITE")
    try:
        return client_from_env(site)
    except SiteError as exc:
        _unavailable(f"站点凭据不齐：{exc}")


@pytest.fixture(scope="module")
def live_schema():
    schema = schema_snapshot.load()
    if schema is None:
        _unavailable(
            "读不到 schema 快照 —— `agenerp/schema/view-schema.json` 缺失或为空。"
            "重新生成：python3 -m agenerp.schema_snapshot"
        )
    return schema


# 一道题**只跑一次真模型**：参数化夹具与 `metric_proposal` 共用这一份缓存，
# 否则第二道题会被跑两遍 —— 白花的是真钱。
_RUNS: dict[str, object] = {}


def _proposal_for(question: str, client, schema):
    if question not in _RUNS:
        result = propose_view(
            question,
            client=client,
            schema=schema,
            models=KNOWN_MODEL_PROFILES,
            doctypes=list(schema.doctypes()),
        )
        _record(question, result)
        _RUNS[question] = result
    return _RUNS[question]


@pytest.fixture(scope="module", params=REQUESTS, ids=["list", "metric"])
def proposal(request, live_client, live_schema):
    """两道题都要过的那几条断言用它。"""
    return _proposal_for(request.param, live_client, live_schema)


@pytest.fixture(scope="module")
def metric_proposal(live_client, live_schema):
    """只有第二道题要过的那条断言用它。**不 skip** —— 一条会 skip 的判据等于不存在。"""
    return _proposal_for(REQUEST_METRIC, live_client, live_schema)


def _record(question: str, result) -> None:
    """留档：**用量 + 轨迹 + 产出的那份视图**。

    ⚠️ D-17：**「调得通」证明不了「免费」** —— 额度在控制台不在响应里，账要自己记一份。
    ⚠️ 产出也要留：一句「7 passed」证明不了它生成的是什么。
      下一个人要能不重跑就看见那份视图长什么样。
    """
    view = result.view
    payload = {
        "model": result.trace.model,
        "request": question,
        "stop_reason": result.stop_reason,
        "turns": [
            {k: v for k, v in turn.items() if k != "usage"} for turn in result.trace.turns
        ],
        "usage": [t["usage"] for t in result.trace.turns if t.get("usage")],
        "view": None
        if view is None
        else {
            "name": view.name,
            "title": view.title,
            "field_refs": [f"{d}.{f}" for d, f in view.field_refs()],
            "blocks": [
                {"type": b.type, "title": b.title, "doctype": b.doctype,
                 "fields": list(b.fields), "sort": list(b.sort) if b.sort else None,
                 "limit": b.limit, "agg": b.agg}
                for b in view.blocks
            ],
        },
        "fallbacks": []
        if result.render_plan is None
        else [f.reason for f in result.render_plan.fallbacks],
    }
    target = (
        pathlib.Path(__file__).resolve().parents[2]
        / "tools" / "experiments" / "p2_view_agent"
        / ("live-run-metric.json" if question is REQUEST_METRIC else "live-run-list.json")
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_a_real_model_produces_a_view_that_validates(proposal):
    assert proposal.stop_reason == STOP_PROPOSED, (
        f"没交出视图（{proposal.stop_reason}）；轨迹：{proposal.trace.turns}"
    )
    assert proposal.view is not None
    assert proposal.validation is not None and proposal.validation.ok


def test_every_field_points_at_a_real_field(proposal, live_schema):
    """🔴 `p2-views-roadmap.md` 硬约束 ④：产出必须指回真实存在的 DocType 字段。

    ⚠️ **按块自己的 DocType 查** —— P2.0R 实测的头号错法是「语义对了，单据错了」。
    """
    refs = proposal.view.field_refs()
    assert refs, "一个字段引用都没有的视图，不是视图"
    for doctype, fieldname in refs:
        assert live_schema.has_field(doctype, fieldname), f"{doctype}.{fieldname} 不存在"


def test_the_model_actually_navigated_the_schema(proposal):
    """它是**查出来**的，不是背出来的。一次工具都不调就交对，那是巧合不是能力。"""
    tool_turns = [t for t in proposal.trace.turns if t["kind"] == "tools"]
    assert tool_turns, f"模型一次工具都没调；轨迹：{proposal.trace.turns}"
    called = {c["tool"] for turn in tool_turns for c in turn["calls"]}
    assert called <= {"system.overview", "schema.search", "meta.fields"}


def test_nothing_falls_back_to_desk(proposal):
    """P2.2 路线 C 的分母上，**落回 = 0**。"""
    assert proposal.render_plan is not None
    assert proposal.render_plan.fallbacks == (), (
        "有块落回 Desk：" + str([f.reason for f in proposal.render_plan.fallbacks])
    )
    assert proposal.render_plan.rendered, "一块都画不了的视图，等于没生成"


def test_every_field_type_is_one_this_renderer_can_draw(proposal, live_schema):
    """落回判定之外再钉一层：字段类型逐个落在封闭表里。

    ⚠️ 这**不等于**「在浏览器里长对了」—— 浏览器那一层归 `tests/render/`（见模块头）。
    """
    for doctype, fieldname in proposal.view.field_refs():
        fieldtype = live_schema.fieldtype(doctype, fieldname)
        assert fieldtype in RENDERABLE_FIELDTYPES, f"{doctype}.{fieldname} 是 {fieldtype}"


def test_the_metric_question_is_not_answered_by_copying_the_prompt_example(metric_proposal):
    """🔴 第二道题的**专属**断言：提示词里的例子是 `Work Order` 上的 `list` 块，
    照抄它答不了「一共多少笔」。

    没有这一条，两道题跑出同一种块也算过 —— 那就等于没加第二道题。
    """
    types = {block.type for block in metric_proposal.view.blocks}
    assert "metric" in types, f"要的是一个数，交的是 {types}"
    doctypes = {block.doctype for block in metric_proposal.view.blocks if block.doctype}
    assert doctypes == {"Stock Entry"}, f"问的是库存转移，答到了 {doctypes}"
