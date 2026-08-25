"""行业包**离线↔活站点比对链**的离线判据 —— 全部走假两侧，零网络、零站点、零 LLM。

被判的对象是 `tools/experiments/p1_pack_parity/parity.py`（判定逻辑所在）
与 `tools/experiments/p1_pack_parity/run.py`（编排）。**两份都按路径加载出货的那一份**，
本文件里**不另写一份比对逻辑** —— 那样判据测的就是自己的副本，
而 `tools/` 既不在 `ruff` 的作用域里、也不在任何 CI job 里
（`docs/backlog/tools-dir-has-no-static-check-coverage.md`，`Status: deferred`，处置者是人）。
⇒ 这条按路径加载的纪律，是那份出货脚本**唯一**一条在 CI 里跑的判据。

plan 是 `docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`（Phase 3）。

十一条判据，逐条注明挡哪种假实现：

① 两侧逐字相同 → 判一致
② 一侧少一条命中 → 判不一致，**且差异指名是哪条 `rule_id` 的哪个 `subject`**
③ 一侧 `quantity` 差 1.0 → 判不一致（挡「只比 `rule_id` 不比数」）
④ `measures` 不同而 `quantity` 相同 → 判不一致（挡「只比七个键里的一个」）
⑤ **两侧都空 → 判「比不了」，不判「一致」**（挡「两个空集相等也叫逐字一致」）
⑥ 一侧空、另一侧非空 → 判不一致（且不许崩）
⑦ **顺序无关**：一侧命中列表倒序 → 仍判一致（否则比对器在测排序，不是在测内容）
⑧ `rule_ids` 不同而 `hits` 相同 → 判不一致（挡「规则一条没查到、恰好也一条没命中」那种绿）
⑨ 零 LLM 两条 + 两条对照
⑩ 判据测的必须是**出货的那份代码**：按路径加载，**源文件没了就是红**
⑪ 离线那一支**一次网络都不打**：`urllib.request.urlopen` 换成一被碰就炸的替身

⚠️ ⑪ 那个替身是 **`autouse` 的**：本文件**除 ⑨(a) 的子进程之外的每一条判据**
都在它下面跑，所以「其余判据照样全绿」不是一句写着好看的话，是本文件的构造事实。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import urllib.request

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as model_fakes  # noqa: E402
import inspection_fakes as fakes  # noqa: E402

from agenerp.routing import adapter as routing_adapter  # noqa: E402
from agenerp.routing.router import route  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PARITY_TARGET = "tools/experiments/p1_pack_parity/parity.py"
RUN_TARGET = "tools/experiments/p1_pack_parity/run.py"


def load_shipped(relative_path: str, module_name: str):
    """按路径加载**出货的那一份**。**源文件没了就是红**，不是少跑几条判据。

    纯 `importlib`（照抄 `tests/unit/test_insight_live_harness.py` 的 `_load_run()`）——
    **不走** `explain_fakes.load_repo_module`：后者会把 `agenerp.routing`
    拖进判据进程，白白污染 ⑨(b) 的观测面。
    """
    target = REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"本文件判的就是 {relative_path}，它不在了 —— 判据失去被测对象。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parity = load_shipped(PARITY_TARGET, "_p1_pack_parity_parity_under_test")
run = load_shipped(RUN_TARGET, "_p1_pack_parity_run_under_test")


# ── ⑪ 离线那一支一次网络都不打（`autouse`，覆盖本文件其余每一条判据）──────────


class NetworkCallDetected(RuntimeError):
    """替身被触发 —— 有人在判据这条路径上打了网络。"""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise NetworkCallDetected("判据侧不许打任何网络")

    monkeypatch.setattr(urllib.request, "urlopen", boom)


# ── 假两侧 ──────────────────────────────────────────────────────────────────


def hit(
    rule_id: str,
    subject: dict,
    quantity: float,
    measures: dict,
    *,
    pack_id: str = "discrete",
    statement: str = "一句话陈述",
    quantity_name: str = "shortfall",
) -> dict:
    """一条命中的**七个键**，逐字写死在本文件里（不引用被测模块的常量 ——
    那样改常量就同时改了判据）。"""
    return {
        "pack_id": pack_id,
        "rule_id": rule_id,
        "statement": statement,
        "subject": dict(subject),
        "quantity_name": quantity_name,
        "quantity": quantity,
        "measures": dict(measures),
    }


BACKLOG = hit(
    "discrete/finished-goods-backlog",
    {"item_code": "HRD-PACK-5K", "warehouse": "成品仓 - HRD"},
    1010.0,
    {"inbound": 2000.0, "outbound": 990.0, "backlog": 1010.0},
    quantity_name="backlog",
)
SHORTFALL = hit(
    "discrete/closed-order-short-delivered",
    {"name": "SAL-ORD-2026-00001"},
    10.0,
    {"ordered": 1000.0, "delivered": 990.0, "shortfall": 10.0},
)

RULE_IDS = [
    "discrete/finished-goods-backlog",
    "discrete/subcontracting-issued-not-received",
    "discrete/closed-order-short-delivered",
]


def report(hits: list[dict], *, rule_ids: list[str] | None = None, requests: int = 10) -> dict:
    """一份 `InspectionReport.as_dict()` 的形状：**三个键，一个不多一个不少**。"""
    return {
        "rule_ids": list(RULE_IDS if rule_ids is None else rule_ids),
        "request_count": requests,
        "hits": copy.deepcopy(hits),
    }


def both_sides(hits: list[dict]) -> tuple[dict, dict]:
    # 两侧 `request_count` **刻意不同**（10 vs 9）—— 那正是契约 ② 的实测依据。
    return report(hits, requests=10), report(hits, requests=9)


# ── ① 两侧逐字相同 → 判一致 ────────────────────────────────────────────────


def test_identical_sides_are_judged_identical():
    """两侧逐字相同 ⇒ `identical`，且 `request_count` 的差异**不参与判定**（契约 ②）。"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    result = parity.compare(offline, live)

    assert result["verdict"] == "identical"
    assert result["rule_ids"]["equal"] is True
    assert result["hits"]["equal"] is True
    assert result["hits"]["matched"] == 2
    # 两侧请求数不同（10 vs 9），照样判一致 —— 这是一条取舍，不是最佳实践。
    assert result["request_count"] == {
        "offline": 10,
        "live": 9,
        "judged": False,
        "note": result["request_count"]["note"],
    }
    assert result["request_count"]["note"]


def test_the_output_is_a_structured_diff_not_a_boolean():
    """契约 ④：输出是结构化差异。**布尔判不出「差在哪」。**"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    result = parity.compare(offline, live)

    assert isinstance(result, dict)
    assert sorted(result) == sorted(
        ["verdict", "reason", "empty_sides", "rule_ids", "hits", "request_count"]
    )
    assert sorted(result["hits"]) == sorted(
        ["equal", "matched", "count", "only_offline", "only_live", "differing"]
    )


# ── ② 一侧少一条命中 → 判不一致，且指名到 `rule_id` + `subject` ──────────────


def test_a_hit_missing_on_one_side_is_named_by_rule_id_and_subject():
    """挡「只比条数」与「静默跳过一侧缺失的规则」两种假实现（变异 M2 / M5）。"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    live["hits"] = [h for h in live["hits"] if h["rule_id"] != SHORTFALL["rule_id"]]

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert result["hits"]["equal"] is False
    assert result["hits"]["count"] == {"offline": 2, "live": 1}
    assert result["hits"]["only_live"] == []
    assert len(result["hits"]["only_offline"]) == 1
    named = result["hits"]["only_offline"][0]
    # **指名**：哪条规则、哪个 subject、那个数是多少 —— 三样都要读得出来。
    assert named["rule_id"] == "discrete/closed-order-short-delivered"
    assert named["subject"] == {"name": "SAL-ORD-2026-00001"}
    assert named["quantity"] == 10.0
    assert named["pack_id"] == "discrete"


# ── ③ `quantity` 差 1.0 → 判不一致 ─────────────────────────────────────────


def test_a_one_point_zero_quantity_drift_is_judged_different():
    """挡「只比 `rule_id` 不比数」（变异 M3）。**同一条规则、同一个 subject、数不同。**"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    live["hits"][1] = {**live["hits"][1], "quantity": 11.0}

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert len(result["hits"]["differing"]) == 1
    entry = result["hits"]["differing"][0]
    assert entry["differing_keys"] == ["quantity"]
    assert entry["identity"]["rule_id"] == "discrete/closed-order-short-delivered"
    assert entry["offline"]["quantity"] == 10.0
    assert entry["live"]["quantity"] == 11.0


# ── ④ `measures` 不同而 `quantity` 相同 → 判不一致 ──────────────────────────


def test_measures_drift_with_an_unchanged_quantity_is_judged_different():
    """挡「只比七个键里的一个」（变异 M4）。**`quantity` 一模一样，`measures` 里差一个数。**"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    live["hits"][1] = {
        **live["hits"][1],
        "measures": {"ordered": 1000.0, "delivered": 991.0, "shortfall": 10.0},
    }

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert len(result["hits"]["differing"]) == 1
    entry = result["hits"]["differing"][0]
    assert entry["differing_keys"] == ["measures"]
    assert entry["offline"]["quantity"] == entry["live"]["quantity"] == 10.0


# ── ⑤ 两侧都空 → 判「比不了」，不判「一致」 ────────────────────────────────


def test_two_empty_sides_are_incomparable_not_identical():
    """挡 plan §6 H4 那种假实现（变异 M1）：**先比后判的实现会在这里返回「一致」。**

    `incomparable` 不是一种「一致」—— 它逐字说的是「这次比对没有判别力」。
    """
    offline, live = both_sides([])
    result = parity.compare(offline, live)

    assert result["verdict"] == "incomparable"
    assert result["verdict"] != "identical"
    assert sorted(result["empty_sides"]) == ["live", "offline"]
    assert result["reason"]
    # 差异面照样落出来（两侧都空时它当然相等）—— 但**判定**不是「一致」。
    assert result["hits"]["equal"] is True


def test_two_empty_sides_stay_incomparable_even_when_rule_ids_match():
    """`rule_ids` 相同也救不了它 —— 非空断言写在**任何比对之前**（契约 ③）。"""
    offline, live = both_sides([])
    assert offline["rule_ids"] == live["rule_ids"]
    assert parity.compare(offline, live)["verdict"] == "incomparable"


# ── ⑥ 一侧空、另一侧非空 → 判不一致（且不许崩）────────────────────────────


def test_one_empty_side_is_judged_different_and_does_not_crash():
    """恰好一侧空是**另一件事**：两侧显然不同，判 `different` 比 `incomparable` 更强。"""
    offline = report([BACKLOG, SHORTFALL], requests=10)
    live = report([], requests=9)

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert result["empty_sides"] == ["live"]
    assert result["hits"]["count"] == {"offline": 2, "live": 0}
    assert len(result["hits"]["only_offline"]) == 2
    assert result["hits"]["only_live"] == []

    # 反过来也一样，且照样不崩。
    flipped = parity.compare(report([], requests=10), report([BACKLOG], requests=9))
    assert flipped["verdict"] == "different"
    assert flipped["empty_sides"] == ["offline"]


# ── ⑦ 顺序无关 ─────────────────────────────────────────────────────────────


def test_reversing_one_sides_hit_list_is_still_identical():
    """否则比对器在测排序，不是在测内容（变异 M6：按列表下标比）。"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    live["hits"] = list(reversed(live["hits"]))

    result = parity.compare(offline, live)

    assert result["verdict"] == "identical"
    assert result["hits"]["matched"] == 2


def test_a_duplicate_hit_on_one_side_is_still_different():
    """顺序无关**不等于**去重：同一条命中出现两次，两侧就不是一回事。"""
    offline, live = both_sides([BACKLOG, SHORTFALL])
    live["hits"] = live["hits"] + [copy.deepcopy(SHORTFALL)]

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert result["hits"]["count"] == {"offline": 2, "live": 3}
    assert len(result["hits"]["only_live"]) == 1


# ── ⑧ `rule_ids` 不同而 `hits` 相同 → 判不一致 ─────────────────────────────


def test_rule_ids_drift_with_identical_hits_is_judged_different():
    """挡 plan §6 H3 那种假实现（变异 M7）：**一条规则根本没查、而它恰好也不命中。**"""
    offline = report([BACKLOG, SHORTFALL], requests=10)
    live = report(
        [BACKLOG, SHORTFALL],
        rule_ids=[r for r in RULE_IDS if r != "discrete/subcontracting-issued-not-received"],
        requests=9,
    )

    result = parity.compare(offline, live)

    assert result["verdict"] == "different"
    assert result["hits"]["equal"] is True, "命中集合本身是相同的 —— 差异只在 rule_ids 上"
    assert result["rule_ids"]["equal"] is False
    assert "discrete/subcontracting-issued-not-received" in result["rule_ids"]["offline"]
    assert "discrete/subcontracting-issued-not-received" not in result["rule_ids"]["live"]


def test_rule_ids_are_compared_with_their_order():
    """H3 逐字是「同一份包、同一个顺序」—— 顺序变了就是变了。"""
    offline = report([BACKLOG, SHORTFALL], requests=10)
    live = report([BACKLOG, SHORTFALL], rule_ids=list(reversed(RULE_IDS)), requests=9)

    assert parity.compare(offline, live)["verdict"] == "different"


# ── 比对面本身：报告形状变了就抛，不降级成「判不一致」 ───────────────────────


def test_a_report_with_an_extra_key_is_rejected_not_silently_compared():
    """`InspectionReport.as_dict()` 多一键少一键 ⇒ **当场抛**。

    降级成「判不一致」会把「比对面失效了」和「数据不同」混成一件事。
    ⚠️ 这条守住的是 `Decision D1` 残余里可判的那一半（新增键不会被静默排除在判定外）；
    **它守不住的那一半**是「有人主动把新键加进排除清单」—— 那没有守卫，照实记进 §7.19。
    """
    offline, live = both_sides([BACKLOG])
    live["elapsed_seconds"] = 0.1
    with pytest.raises(parity.ParityInputError, match="键集合"):
        parity.compare(offline, live)

    offline2, live2 = both_sides([BACKLOG])
    del live2["request_count"]
    with pytest.raises(parity.ParityInputError, match="键集合"):
        parity.compare(offline2, live2)


def test_a_hit_with_a_missing_key_is_rejected():
    """`Hit.as_dict()` 的七个键同理 —— 少一个就不是一条可比的命中。"""
    offline, live = both_sides([BACKLOG])
    del live["hits"][0]["measures"]
    with pytest.raises(parity.ParityInputError, match="键集合"):
        parity.compare(offline, live)


# ── ⑨ 零 LLM：(a) 进程级导入图 + (b) 构造面替身计数 + 两条对照 ──────────────


def test_h7a_importing_the_comparator_never_pulls_in_the_model_face():
    """**全新解释器**里 `import` **比对器**：`agenerp.routing` 不许出现在 `sys.modules`。

    ⚠️ **主语刻意只是 `parity.py`，不是整个脚本。** 起草期实测：按路径加载
    `tests/unit/inspection_fakes.py` **会**把 `agenerp.routing` 拉进 `sys.modules`
    （`:39` → `explain_fakes` → routing），而 `run.py` 正要加载那份夹具。
    **把主语写成「整个脚本」按构造为假 —— 本文件不提出那个主张，也不靠删依赖去凑它。**
    """
    code = (
        "import importlib.util, sys;"
        "spec = importlib.util.spec_from_file_location('parity', "
        f"{PARITY_TARGET!r});"
        "module = importlib.util.module_from_spec(spec);"
        "sys.modules['parity'] = module;"
        "spec.loader.exec_module(module);"
        "assert 'agenerp.routing' not in sys.modules, sorted(sys.modules);"
        "assert not [k for k in sys.modules if k.startswith('agenerp')], "
        "'比对器 import 了本仓模块 —— 契约要求它零仓内 import'"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


class ModelCallDetected(RuntimeError):
    """探针被触发 —— 有人在比对链上碰了模型面。"""


class ChatAdapterProbe:
    """`ChatAdapter` **构造面整体替身**：一被碰就计数**并且**炸。

    **替身由观测方装、不由被观测方自装**（plan `Decision D2`）——
    从账本自己数账本是同义反复。
    """

    calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.calls = 0

    @classmethod
    def touch(cls, *args, **kwargs):
        cls.calls += 1
        raise ModelCallDetected("比对链上不许有任何模型调用")


@pytest.fixture
def no_model_calls(monkeypatch):
    """换的是进程里那个类本身，谁 import 过它都逃不掉（照抄
    `tests/unit/test_inspection_rules.py:211-226` 的口径）。"""
    ChatAdapterProbe.reset()
    for name in ("__init__", "chat", "_send", "_post"):
        monkeypatch.setattr(routing_adapter.ChatAdapter, name, ChatAdapterProbe.touch)
    monkeypatch.setattr(routing_adapter, "_ssl_context", ChatAdapterProbe.touch)
    return ChatAdapterProbe


def whole_chain() -> dict:
    """**整条比对链**：装夹具 → 离线巡检 → 出货比对器比一次。走的都是出货的那份代码。"""
    offline_report = run.inspect_once(run.offline_client())[1]
    live_report = copy.deepcopy(offline_report)
    return parity.compare(offline_report, live_report)


def test_h7b_the_whole_parity_chain_makes_zero_model_calls(no_model_calls):
    """(b) `ChatAdapter` 构造面替身在整条比对链上的计数为 **0**。"""
    result = whole_chain()

    assert result["verdict"] == "identical"
    assert result["hits"]["matched"] == 2
    assert no_model_calls.calls == 0


def test_h7b_positive_control_a_path_that_does_touch_the_model_is_caught(no_model_calls):
    """**阳性对照**：同一个探针必须让一条故意碰模型的路径失败并把计数打到非 0。

    没有它，「零调用」什么都没测 —— 替身没装上、或装错了位置，两种情况都会静静地绿。
    """
    assert no_model_calls.calls == 0
    with pytest.raises(ModelCallDetected):
        route(
            "explain",
            models=model_fakes.models(),
            config=model_fakes.config(),
            transport=model_fakes.ScriptedModel([model_fakes.answer_step("hi")]),
        )
    assert no_model_calls.calls == 1


def test_h7b_the_probe_is_off_by_default():
    """**探针默认关闭对照** —— 否则上面那条阳性对照**可能红在别的原因上**。

    （逐字照抄 `tests/unit/test_inspection_rules.py:254` 的口径与理由。）
    """
    adapter = route(
        "explain",
        models=model_fakes.models(),
        config=model_fakes.config(),
        transport=model_fakes.ScriptedModel([model_fakes.answer_step("hi")]),
    )
    assert adapter.chat([{"role": "user", "content": "hi"}]).text == "hi"


# ── ⑩ 判据测的必须是出货的那份代码 ─────────────────────────────────────────


def test_the_judged_object_is_the_shipped_file_on_disk():
    """本文件按路径加载 `tools/experiments/p1_pack_parity/parity.py`，**不另写一份比对**。

    ⇒ 变异 M9（改坏出货的 `parity.py`、判据一个字不动）时 ①–⑧ 里必有一条红。
    """
    assert pathlib.Path(parity.__file__) == (REPO_ROOT / PARITY_TARGET)
    assert pathlib.Path(run.__file__) == (REPO_ROOT / RUN_TARGET)
    source = (REPO_ROOT / PARITY_TARGET).read_text(encoding="utf-8")
    assert "def compare(" in source


def test_a_missing_source_file_is_red_not_fewer_criteria():
    """**源文件没了就是红**，不是少跑几条判据（`explain_fakes.py:40` 的同一条纪律）。"""
    with pytest.raises(FileNotFoundError, match="判据失去被测对象"):
        load_shipped("tools/experiments/p1_pack_parity/does-not-exist.py", "_gone")


# ── ⑪ 离线那一支一次网络都不打 ─────────────────────────────────────────────


def test_h11_the_offline_branch_runs_with_urlopen_booby_trapped(tmp_path):
    """`urllib.request.urlopen` 已被 `autouse` 替身换成一被碰就炸的东西（见文件头）。

    在它下面跑**出货入口点**的离线支 ⇒ 那一支一次网络都没打。
    ⚠️ **判据不是**「判据文件里零 `SiteClient` 真实构造」—— 假站点本来就要真构造一个
    `SiteClient` 再塞进假 transport，那句话按构造为假，**不写它**。
    """
    # 先反证替身确实在位 —— 否则「跑通了」可能只是因为替身没装上。
    with pytest.raises(NetworkCallDetected):
        urllib.request.urlopen("http://127.0.0.1:18080")

    assert run.main(["--offline-only", "--evidence-dir", str(tmp_path)]) == 0


def test_h11_the_offline_row_source_is_derived_from_the_seed_not_read_back(tmp_path):
    """R1 的第二层：离线侧的行**由 `agenerp.seed.generate()` 派生**，不是从站点读回来的。

    否则比对就在拿站点跟站点比，永远绿。
    """
    report_dict = run.inspect_once(run.offline_client())[1]
    assert report_dict["request_count"] == 10
    assert len(report_dict["hits"]) == 2
    assert [h["rule_id"] for h in report_dict["hits"]] == [
        "discrete/finished-goods-backlog",
        "discrete/closed-order-short-delivered",
    ]


# ── 编排面：`main()` 的整跑（假两侧、零站点）───────────────────────────────


def test_main_writes_three_evidence_files_and_exits_zero_when_identical(tmp_path):
    """出货入口点的整跑支：三份 JSON 落盘，`*-hits.json` 存的是**整份报告**（三个键）。"""
    offline = fakes.client_for(fakes.seed_site())
    live = fakes.client_for(fakes.seed_site())

    def wiring(args):
        return {"offline_client": offline, "live_client": live, "recorder": None}

    assert run.main(["--evidence-dir", str(tmp_path)], wiring=wiring) == 0

    for name in ("offline-hits.json", "live-hits.json"):
        payload = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert sorted(payload) == ["hits", "request_count", "rule_ids"]
    result = json.loads((tmp_path / "parity.json").read_text(encoding="utf-8"))
    assert result["verdict"] == "identical"


def test_main_exits_non_zero_and_still_lands_the_evidence_when_sides_differ(tmp_path):
    """**先落盘再退码**：结论不一致时证据比退出码重要（§6 H2 的三种处置都要它）。"""
    offline = fakes.client_for(fakes.seed_site())
    drifted = fakes.seed_site()
    drifted.rows["Sales Order"] = [
        {**row, "status": "To Deliver and Bill"} for row in drifted.rows["Sales Order"]
    ]

    def wiring(args):
        return {
            "offline_client": offline,
            "live_client": fakes.client_for(drifted),
            "recorder": None,
        }

    assert run.main(["--evidence-dir", str(tmp_path)], wiring=wiring) == 1

    result = json.loads((tmp_path / "parity.json").read_text(encoding="utf-8"))
    assert result["verdict"] == "different"
    assert [h["rule_id"] for h in result["hits"]["only_offline"]] == [
        "discrete/closed-order-short-delivered"
    ]


def test_main_denies_a_non_allowlisted_site_request(tmp_path):
    """只读白名单：`POST /api/resource/Item` 指名报错。**按实际动词判，不按方法名判。**"""
    recorder = run.ReadOnlyTransport(fakes.seed_site())
    with pytest.raises(run.RequestNotAllowed, match="白名单外的站点请求"):
        recorder(run.SiteRequest("POST", "http://fake/api/resource/Item", {}, b"{}"))
    assert recorder.denied and recorder.denied[0]["path"] == "/api/resource/Item"
    assert recorder.summary()["allowlist"] == ["/api/method/login"]
