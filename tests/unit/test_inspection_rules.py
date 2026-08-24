"""P1.5 巡检器（纯规则引擎）的判据 —— 判的是「**发现力来自规则清单，不来自模型**」。

判据全部落在**结构化事实**上（命中记录、命中数量、调用次数、序列化后的规则声明），
一条都不落在自由文本上：plan §1.4a 已把五条判据逐条划到那一侧，
「归因说得对不对」不在本文件里，也不在本 plan 的任何 Exit Criteria 里。

夹具由 `agenerp/seed/` 派生（`inspection_fakes`），期望值取自
`agenerp/seed/checks.py` 或由本文件写死字面量 —— **两侧不许合并**（`Decision` D4）。
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import urllib.request

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as model_fakes  # noqa: E402
import inspection_fakes as fakes  # noqa: E402

from agenerp.explain.gate import DOC_NAME  # noqa: E402
from agenerp.inspection import (  # noqa: E402
    RuleLoadError,
    check_test_cases,
    inspect_site,
    load_rules,
    minimal_rules,
)
from agenerp.inspection.engine import without  # noqa: E402
from agenerp.inspection.minimal import (  # noqa: E402
    DECLARATIONS,
    RULE_OUTPUT_FAR_EXCEEDS_SOLD,
)
from agenerp.routing import route  # noqa: E402
from agenerp.routing import adapter as routing_adapter  # noqa: E402
from agenerp.seed.checks import EXPECTED_BACKLOG_QTY  # noqa: E402
from agenerp.seed.model import FINISHED_ITEM, WH_FINISHED  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# 第二个数据集的期望积压量。**本文件写死的字面量**，不从构造常量算出来
# （`agenerp/seed/checks.py:18-20` 的同一条纪律：从同一侧取会变成同义反复）。
VARIANT_INHOUSE = 800
VARIANT_SUBCON = 600
VARIANT_DELIVERY = 500
VARIANT_EXPECTED_BACKLOG_QTY = 900.0


def run_on(site) -> object:
    return inspect_site(minimal_rules(), fakes.client_for(site))


# ── H1 消融：完整清单 → 报出；抽掉那条 → 零命中 ──────────────────────────────


def test_h1_the_full_rule_list_reports_the_finished_goods_backlog():
    """固定测例上恰好报出一条，且命中里的数**是算出来的**，等于 `EXPECTED_BACKLOG_QTY`。"""
    site = fakes.seed_site()
    report = run_on(site)

    assert report.rule_ids == (RULE_OUTPUT_FAR_EXCEEDS_SOLD,)
    assert len(report.hits) == 1, report.as_dict()
    hit = report.hits[0]
    assert dict(hit.subject) == {"item_code": FINISHED_ITEM, "warehouse": WH_FINISHED}
    assert hit.quantity == EXPECTED_BACKLOG_QTY
    assert dict(hit.measures)["received"] - dict(hit.measures)["issued"] == hit.quantity
    assert report.request_count > 0, "巡检必须真查过站点，不是凭空报"


def test_h1_ablation_removing_that_rule_yields_zero_hits():
    """消融的另一侧。**两种抽法都验**：整条抽掉、以及只把它的判据表达改严。

    只验前者不够 —— 一个把命中写死的实现在「清单为空」时也许恰好不报，
    但它读不读判据表达仍然没被测到（M1）。
    """
    site = fakes.seed_site()
    client = fakes.client_for(site)

    ablated = without(minimal_rules(), RULE_OUTPUT_FAR_EXCEEDS_SOLD)
    assert ablated == ()
    assert inspect_site(ablated, client).hits == ()

    stricter = json.loads(json.dumps(list(DECLARATIONS)))
    stricter[0]["trigger"]["value"] = 10.0
    assert inspect_site(load_rules(stricter), client).hits == (), "判据表达没被读"


def test_h1_the_reported_quantity_moves_with_the_dataset():
    """**第二个数据集**：换掉 `INHOUSE_QTY` / `SUBCON_QTY` / `DELIVERY_QTY` 三个参数，
    命中里的数必须跟着变（M3 —— 把 1010 写死进命中记录的假实现在这里必红）。"""
    site = fakes.seed_site(
        inhouse=VARIANT_INHOUSE, subcon=VARIANT_SUBCON, delivery=VARIANT_DELIVERY
    )
    report = run_on(site)

    assert len(report.hits) == 1, report.as_dict()
    assert report.hits[0].quantity == VARIANT_EXPECTED_BACKLOG_QTY
    assert report.hits[0].quantity != EXPECTED_BACKLOG_QTY


# ── H3 反测：与积压陷阱无关的合成数据上不误报 ───────────────────────────────


def test_h3_no_false_positive_on_unrelated_data():
    """产多少卖多少、订单也交清了 —— 规则口径被放宽的话这里必红（M8）。"""
    report = run_on(fakes.unrelated_site())
    assert report.rule_ids == (RULE_OUTPUT_FAR_EXCEEDS_SOLD,)
    assert report.hits == ()


# ── 规则声明的结构判据：不许照答案写规则 ────────────────────────────────────

FORBIDDEN_NUMBERS = ("1010", "2000", "990")


def _assert_clean(label: str, text: str) -> None:
    assert DOC_NAME.search(text) is None, f"{label} 里出现了单号字面量"
    for number in FORBIDDEN_NUMBERS:
        assert number not in text, f"{label} 里出现了固定测例的答案 {number}"
    assert FINISHED_ITEM not in text and WH_FINISHED not in text


def test_rule_declarations_name_no_document_and_no_answer_quantity():
    """直接对规则声明断言（M7 的杀手）。

    H3 杀不了 M7：一条钉死单号的规则在真夹具上照样命中、在无关数据上照样不命中。
    单号形状复用 `agenerp/explain/gate.py` 的 `DOC_NAME`，不另写一个正则。

    ⚠️ **两侧都断言，不许只判一侧**（执行期变异自查实测撞出来的，见 plan §9）：
    只判**装载后**的序列化形态，一条把单号写在装载器不认识的键里的声明会躲过去 ——
    那种键被丢掉、序列化里看不见，可它就明晃晃写在仓库的源码里。
    所以**源声明**（`DECLARATIONS`）也一起判；装载器那一侧的未知键拒载是同一件事的另一半。
    """
    _assert_clean("最小规则集的源声明", json.dumps(DECLARATIONS, ensure_ascii=False))
    for rule in minimal_rules():
        _assert_clean(f"规则 {rule.rule_id} 装载后的声明", rule.serialized())


def test_the_loader_refuses_keys_it_does_not_know():
    """未知键拒载。静默丢弃会让打错的键名失效，也会给「把答案夹带进声明」开一条暗道。"""
    smuggled = json.loads(json.dumps(DECLARATIONS[0]))
    smuggled["note"] = "对应 SAL-ORD-2026-00001，预期 1010"
    with pytest.raises(RuleLoadError, match="不认识的键"):
        load_rules([smuggled])


# ── 缺 `test_case` 必须拒载（M4 的杀手） ────────────────────────────────────


def _declaration_without_test_case() -> dict:
    stripped = json.loads(json.dumps(DECLARATIONS[0]))
    stripped.pop("test_case")
    stripped["rule_id"] = "stock/no-test-case"
    return stripped


def test_a_rule_without_a_test_case_is_refused_not_filtered():
    """P1.6 的验收原文是「无 `test_case` 的规则**即失败**」。

    **静默过滤与正确拒载在退出码上一模一样**，所以这里同时断言两件事：
    ① 单独装载它抛错；② 把它混进一份好清单里，**整份清单一起拒载**，
    而不是「装上好的那条、悄悄丢掉坏的那条」。
    """
    with pytest.raises(RuleLoadError, match="test_case"):
        load_rules([_declaration_without_test_case()])

    mixed = [json.loads(json.dumps(DECLARATIONS[0])), _declaration_without_test_case()]
    with pytest.raises(RuleLoadError, match="test_case"):
        load_rules(mixed)


def test_an_empty_test_case_is_also_refused():
    for empty in ({}, {"name": "x", "rows": {}, "expect_hit": True}):
        broken = json.loads(json.dumps(DECLARATIONS[0]))
        broken["test_case"] = empty
        with pytest.raises(RuleLoadError):
            load_rules([broken])


def test_every_shipped_rule_passes_its_own_test_case():
    """`test_case` 不是装饰：引擎拿它在内存行集上真跑一遍。"""
    assert check_test_cases(minimal_rules()) == ()


def test_the_loader_refuses_operators_outside_the_finite_set():
    """有限算子集是 D1 的选择本身。越界的算子必须拒载，不许静默当成 no-op。"""
    broken = json.loads(json.dumps(DECLARATIONS[0]))
    broken["trigger"]["operator"] = "looks_wrong_to_me"
    with pytest.raises(RuleLoadError, match="有限算子集"):
        load_rules([broken])

    dangling = json.loads(json.dumps(DECLARATIONS[0]))
    dangling["trigger"]["reference"] = "nope"
    with pytest.raises(RuleLoadError, match="未声明的度量"):
        load_rules([dangling])


# ── H2 零 LLM：进程级探针 + 阳性对照 ────────────────────────────────────────


class ModelCallDetected(RuntimeError):
    """探针被触发 —— 有人在这条路径上碰了模型面。"""


@pytest.fixture
def no_model_calls(monkeypatch):
    """把 `agenerp/routing` 的 **adapter / transport 构造面整体**换成一被碰就炸的替身。

    **不是**给巡检器留一个「可注入模型」的口子再往里塞替身：D-15 要求巡检器
    **根本没有模型接缝**，往接缝里塞替身这件事本身就假设了接缝存在。
    这里换的是进程里那个类本身，谁 import 过它都逃不掉。
    """

    def boom(*args, **kwargs):
        raise ModelCallDetected("巡检路径上不许有任何模型调用")

    monkeypatch.setattr(routing_adapter.ChatAdapter, "__init__", boom)
    monkeypatch.setattr(routing_adapter.ChatAdapter, "chat", boom)
    monkeypatch.setattr(routing_adapter.ChatAdapter, "_send", boom)
    monkeypatch.setattr(routing_adapter.ChatAdapter, "_post", boom)
    monkeypatch.setattr(routing_adapter, "_ssl_context", boom)
    monkeypatch.setattr(urllib.request, "urlopen", boom)


def test_h2_the_whole_inspection_runs_with_the_model_face_booby_trapped(no_model_calls):
    site = fakes.seed_site()
    report = run_on(site)

    assert len(report.hits) == 1
    assert report.hits[0].quantity == EXPECTED_BACKLOG_QTY


def test_h2_positive_control_a_path_that_does_call_the_model_is_caught(no_model_calls):
    """**阳性对照**：同一个探针必须让一条故意调模型的路径失败。

    没有它，「零调用」什么都没测 —— 替身没装上、或装错了位置，两种情况都会静静地绿。
    """
    with pytest.raises(ModelCallDetected):
        route(
            "explain",
            models=model_fakes.models(),
            config=model_fakes.config(),
            transport=model_fakes.ScriptedModel([model_fakes.answer_step("hi")]),
        )


def test_h2_the_probe_is_off_by_default():
    """探针不装的时候那条路径是通的 —— 否则上面那条阳性对照可能红在别的原因上。"""
    adapter = route(
        "explain",
        models=model_fakes.models(),
        config=model_fakes.config(),
        transport=model_fakes.ScriptedModel([model_fakes.answer_step("hi")]),
    )
    assert adapter.chat([{"role": "user", "content": "hi"}]).text == "hi"


def test_h2_importing_the_inspector_never_pulls_in_the_model_face():
    """**全新解释器**里 import 巡检器：`agenerp.routing` 不许出现在 `sys.modules` 里。

    这不是源码文本检查，判的是一个可观测量（导入图）。它与上面的进程级探针互补：
    探针管「跑的时候没调」，这一条管「根本没有那条接缝」。
    """
    code = (
        "import sys; import agenerp.inspection; "
        "assert 'agenerp.routing' not in sys.modules, sorted(sys.modules)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


# ── ②端只读 ────────────────────────────────────────────────────────────────


def test_the_inspection_only_reads():
    """巡检不写任何业务数据（Non-Goals 5）。判在假站点的请求记录上。"""
    site = fakes.seed_site()
    run_on(site)
    assert {request.method for request in site.requests} == {"GET"}


def test_the_hit_record_is_diffable():
    """命中记录必须是可 diff 的产物（北极星）：JSON 可序列化、两次跑字节相同。"""
    site = fakes.seed_site()
    first = json.dumps(run_on(site).as_dict(), ensure_ascii=False, sort_keys=True)
    second = json.dumps(run_on(site).as_dict(), ensure_ascii=False, sort_keys=True)
    assert first == second
    assert re.search(r'"quantity": 1010', first)
