"""归因活跑脚手架的**离线判据** —— 全部走假件，零网络、零站点、零凭据。

被判的对象是 `tools/experiments/p1_insight_live/run.py`（实验设施，不是产品代码）。
plan 是 `docs/plans/p1-insight/2026-08-25-0225-2-insight-attribution-live-run.md`。

⚠️ **本文件不判归因文本的质量**（plan §1.5 / Non-Goal 1）：判定器的**标签取值**
在这里只作为「退出码对它免疫」的输入出现，一条断言都不建立在它上面。

五条判据对着 plan Phase 1 的 ①–⑤：
① 证据落盘形状（键集合固定、含逐次账本、取证轨迹 `tool_calls` 非空且可枚举、无凭据字面量）·
② `hits_unchanged` 为假 ⇒ 非零退出 ·
③ 请求记录器：白名单内的 `POST frappe.client.has_permission` 放行、
   白名单外的 `POST /api/resource/Item` 指名报错并非零退出 ·
④ 账本条数 != `chat()` 计数 ⇒ 非零退出 ·
⑤ **退出码在三个判定标签下逐一不变**（§2 Goal 3 的可判形式，M6 的靶子）。
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as model_fakes  # noqa: E402
import inspection_fakes as fakes  # noqa: E402

from agenerp.judging import LABELS  # noqa: E402
from agenerp.site import SiteClient, SiteRequest  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = "tools/experiments/p1_insight_live/run.py"

# 长度 ≥ `MIN_SCANNED_SECRET_LEN`，扫描器会**真扫它** —— 短值会被跳过，那样 M4 就自证了。
FAKE_API_KEY = "fake-llm-key-0123456789abcdef"
FAKE_ENV = {"AGENERP_LLM_API_KEY": FAKE_API_KEY}


def _load_run():
    """按路径加载实验脚本。**源文件没了就是红**，不是少跑几条判据。"""
    target = REPO_ROOT / TARGET
    if not target.is_file():
        raise FileNotFoundError(f"本文件判的就是 {TARGET}，它不在了 —— 判据失去被测对象。")
    spec = importlib.util.spec_from_file_location("_p1_insight_live_run", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run = _load_run()


# ── 假件接线 ────────────────────────────────────────────────────────────────

ITEM_LINK_STEP = model_fakes.tools_step(
    model_fakes.call("doc.links", "c0", doctype="Item", name="HRD-PACK-5K")
)
INBOUND_STEP = model_fakes.tools_step(
    model_fakes.call(
        "doc.get", "c1", doctype="Subcontracting Receipt", name="MAT-SCR-2026-00001"
    ),
    model_fakes.call("doc.get", "c2", doctype="Stock Entry", name="MAT-STE-2026-00003"),
)
GROUNDED_ANSWER = model_fakes.answer_step(
    "成品仓积压 1,010 台：自制与外协各入库 1,000 台，只发出 990 台，"
    "订单被人工关闭所以账面达成率还是 100%。"
)
SCRIPT = [ITEM_LINK_STEP, INBOUND_STEP, GROUNDED_ANSWER]


def fake_judge(label: str):
    """判定器替身。**注入的是结果，不是端点** —— 判据侧一次网络都不发。"""

    def judge(answer: str) -> dict:
        return {
            "ok": True,
            "error": "",
            "label": label,
            "note": run.O1_NOTE.format(label=label),
            "verdict": {"label": label, "model": "fake-judge", "raw_text": label},
            "ledger": {"calls": 1, "total": {}, "entries": []},
        }

    return judge


def single_hit_site():
    """假站点摆成**活站点今天的形状**：`discrete` 包只命中 `finished-goods-backlog` 一条。

    做法是把 `Sales Order.status` 由 `Closed` 改成 `To Deliver and Bill` ——
    那正是活站点上的实际取值（plan §1.4b，已登记在 `docs/bugs/02-…`，归属种子装载面）。
    **不改规则、不改期望值**：命中数由数据决定，改的是数据的那一个字段。
    """
    site = fakes.seed_site()
    site.rows["Sales Order"] = [
        {**row, "status": "To Deliver and Bill"} for row in site.rows["Sales Order"]
    ]
    return site


class Pieces:
    """一次假件实跑的全部接线，测完还能回头看记录器与计数探针。"""

    def __init__(self, *, steps=None, site=None, judge=None, env=None):
        self.site = single_hit_site() if site is None else site
        self.recorder = run.RecordingTransport(self.site)
        self.client = SiteClient(
            "fake", base_url="http://fake", api_key="k", api_secret="s",
            transport=self.recorder,
        )
        self.scripted = model_fakes.ScriptedModel(list(steps or SCRIPT))
        self.probe = run.CountingModel(self.scripted)
        self.judge = judge or fake_judge("correct")
        self.env = dict(FAKE_ENV if env is None else env)

    def wiring(self, args) -> dict:
        return {
            "client": self.client,
            "recorder": self.recorder,
            "probe": self.probe,
            "judge": self.judge,
            "models": model_fakes.models(),
            "requested": "fake-explainer",
            "config": model_fakes.config(),
            "env": self.env,
        }


def run_main(pieces: Pieces, tmp_path, *, out="live-run-01.json") -> int:
    return run.main(
        ["--evidence-dir", str(tmp_path), "--out", out], wiring=pieces.wiring
    )


def evidence_of(tmp_path, out="live-run-01.json") -> dict:
    return json.loads((tmp_path / out).read_text(encoding="utf-8"))


# ── ① 证据落盘形状 ──────────────────────────────────────────────────────────


def test_the_evidence_shape_is_fixed_and_carries_every_structured_fact(tmp_path):
    """键集合**写死在本文件里**（不引用被测模块的常量 —— 那样改常量就同时改了判据）。"""
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 0

    evidence = evidence_of(tmp_path)
    assert sorted(evidence) == sorted(
        [
            "run", "at", "pack", "site", "model", "inspection", "attributions",
            "checks", "requests", "credential_scan", "elapsed_seconds", "notes",
        ]
    )
    assert len(evidence["attributions"]) == 1
    record = evidence["attributions"][0]
    assert sorted(record) == sorted(
        [
            "rule_id", "pack_id", "hit", "question", "answer", "accepted",
            "gate_l1", "tool_calls", "cost_ledger", "usage_total", "trace", "judge",
        ]
    )

    # 命中、题面、答案全文、门禁判定、逐次账本、端点原始 usage —— 一样都不许省。
    assert record["hit"]["rule_id"] == "discrete/finished-goods-backlog"
    assert record["question"] and record["answer"]
    assert record["gate_l1"]["gate_check_count"] >= 1
    entries = record["cost_ledger"]["entries"]
    assert record["cost_ledger"]["calls"] == len(entries) == pieces.scripted.calls
    assert all("endpoint_total_tokens" in entry for entry in entries)
    assert all("total_matches_endpoint" in entry for entry in entries)


def test_the_evidence_trace_is_non_empty_and_its_tool_calls_are_enumerable(tmp_path):
    """§2 目标 2 第五条事实的判据落点：**取证轨迹非空且工具调用可枚举**。"""
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 0

    record = evidence_of(tmp_path)["attributions"][0]
    tools = [call["tool"] for call in record["tool_calls"]]
    assert tools, "取证轨迹为空 = 没有可回放的取证过程"
    assert tools == ["doc.links", "doc.get", "doc.get"]
    assert evidence_of(tmp_path)["checks"]["evidence_trace_enumerable"] is True


def test_no_credential_literal_lands_in_the_evidence_file(tmp_path):
    """凭据一个字节不进证据文件。假 key **足够长**，扫描器会真扫它。"""
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 0

    text = (tmp_path / "live-run-01.json").read_text(encoding="utf-8")
    assert FAKE_API_KEY not in text
    scan = evidence_of(tmp_path)["credential_scan"]
    assert scan["found"] == []
    assert "AGENERP_LLM_API_KEY" in scan["scanned"]
    assert scan["skipped_too_short"] == [], "假 key 被当成短值跳过 = 本条判据自证"


def test_m4_a_credential_literal_in_the_evidence_fails_the_run(tmp_path):
    """M4 的靶子：把凭据混进证据 ⇒ **非零退出且不落盘**。"""
    pieces = Pieces()
    pieces.judge = lambda answer: {
        "ok": True, "error": "", "label": "correct", "note": FAKE_API_KEY,
        "verdict": {}, "ledger": {"calls": 0},
    }
    assert run_main(pieces, tmp_path) == 1
    assert not (tmp_path / "live-run-01.json").exists()


# ── ② `hits_unchanged` 为假 ⇒ 非零退出 ───────────────────────────────────────


def test_it_exits_non_zero_when_the_hits_were_rewritten(tmp_path, monkeypatch):
    """**不许把「命中被改写」记成一次成功实跑**（M1 的靶子）。"""
    monkeypatch.setattr(run, "hits_unchanged", lambda report, attributions: False)
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 1

    evidence = evidence_of(tmp_path)
    assert evidence["checks"]["hits_unchanged"] is False
    assert evidence["inspection"]["hits_unchanged"] is False


# ── M5：空集不是成功 ────────────────────────────────────────────────────────


def test_it_exits_non_zero_when_the_inspection_found_nothing(tmp_path):
    """**空集不是成功**：零命中就没有任何归因被跑过，不许退 0。"""
    empty = single_hit_site()
    empty.rows["Stock Ledger Entry"] = []
    pieces = Pieces(site=empty)
    assert run_main(pieces, tmp_path) == 1

    evidence = evidence_of(tmp_path)
    assert evidence["inspection"]["hits"] == []
    assert evidence["checks"]["hits_not_empty"] is False


# ── ③ 请求记录器：按端点语义判，不按 HTTP 动词判 ────────────────────────────


def test_the_recorder_lets_a_whitelisted_post_through(tmp_path):
    """白名单内的 `POST /api/method/frappe.client.has_permission` **本来就该放行**。

    一个完全只读的会话也会发出大量 `POST`（`permission.scope` 逐个 DocType 探权限），
    照"零 POST"跑会在第二个请求上误停机 —— plan §1.3b 起草期实读改准的那一处。
    """
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 0

    requests = evidence_of(tmp_path)["requests"]
    assert requests["post"] > 0, "只读会话一个 POST 都没有 = 这条判据没测到东西"
    assert requests["denied"] == []
    assert requests["by_endpoint"]["POST /api/method/frappe.client.has_permission"] > 0
    assert all(
        record["method"] == "GET" or record["path"] in run.ALLOWED_METHOD_PATHS
        for record in pieces.recorder.records
    )


def test_the_recorder_names_and_refuses_a_write_to_api_resource():
    """白名单外的 `POST /api/resource/Item` ⇒ **指名报错**。"""
    pieces = Pieces()
    write = SiteRequest(
        method="POST", url="http://fake/api/resource/Item", body=b"{}"
    )
    with pytest.raises(run.RequestNotAllowed) as excinfo:
        pieces.recorder(write)

    assert "/api/resource/Item" in str(excinfo.value)
    assert "POST" in str(excinfo.value)
    assert pieces.recorder.denied == [
        {"method": "POST", "path": "/api/resource/Item", "allowed": False}
    ]


def test_a_denied_request_makes_the_whole_run_fail(tmp_path):
    """M3 的靶子：记录器**放过**一次白名单外的写 ⇒ 整跑必须非零退出。"""
    pieces = Pieces()
    pieces.recorder(SiteRequest(method="GET", url="http://fake/api/resource/Item"))
    with pytest.raises(run.RequestNotAllowed):
        pieces.recorder(SiteRequest(method="PUT", url="http://fake/api/resource/Item/x"))

    assert run_main(pieces, tmp_path) == 1
    evidence = evidence_of(tmp_path)
    assert evidence["checks"]["no_denied_requests"] is False
    assert evidence["requests"]["denied"][0]["method"] == "PUT"


# ── ④ 账本条数 != `chat()` 计数 ⇒ 非零退出 ──────────────────────────────────


def test_it_exits_non_zero_when_the_ledger_does_not_match_the_chat_count(tmp_path):
    """M2 的靶子。两个数**来自不同的采集面**：账本在循环里记，计数探针在 transport 上数。

    从账本自己数账本是同义反复，测不出「有一次调用没记账」。
    """
    pieces = Pieces()
    pieces.probe.calls = 99  # 预置 99 次「已发生但没记账」的调用 ⇒ 两侧必然对不上
    assert run_main(pieces, tmp_path) == 1

    evidence = evidence_of(tmp_path)
    assert evidence["checks"]["ledger_matches_chat_calls"] is False
    assert evidence["model"]["chat_calls"] == 99 + pieces.scripted.calls
    assert evidence["model"]["ledger_calls"] == pieces.scripted.calls


def test_the_two_counts_agree_on_the_happy_path(tmp_path):
    pieces = Pieces()
    assert run_main(pieces, tmp_path) == 0

    model = evidence_of(tmp_path)["model"]
    assert model["chat_calls"] == model["ledger_calls"] == pieces.scripted.calls


# ── ⑤ 退出码在三个判定标签下逐一不变（§2 Goal 3 / M6 的靶子）─────────────────


def test_the_exit_code_is_identical_under_every_verdict_label(tmp_path):
    """**判定器的标签取值不构成任何通过 / 失败条件。**

    喂 `correct` / `incomplete` / `truncated` 三种判定结果各跑一次，退出码逐字相同。
    在 `run.py` 的退出码路径上加一条 `if verdict.label != "correct": raise SystemExit(1)`，
    本条必须发红 —— 那就是 M6 的变异。
    """
    assert sorted(LABELS) == sorted(["correct", "incomplete", "truncated"])

    codes = {}
    for label in sorted(LABELS):
        pieces = Pieces(judge=fake_judge(label))
        codes[label] = run_main(pieces, tmp_path, out=f"{label}.json")
        assert evidence_of(tmp_path, f"{label}.json")["attributions"][0]["judge"]["label"] == label

    assert len(set(codes.values())) == 1, f"退出码随判定标签变了：{codes}"
    assert set(codes.values()) == {0}


def test_the_verdict_note_is_recorded_verbatim_as_pending_review(tmp_path):
    """D-16：判定结果只能写成「判为 X，**待复验**」，不能写成结论。"""
    pieces = Pieces(judge=fake_judge("incomplete"))
    assert run_main(pieces, tmp_path) == 0

    note = evidence_of(tmp_path)["attributions"][0]["judge"]["note"]
    assert "据判定器，判为 incomplete，待复验" in note
    assert "不据此对归因质量下任何结论" in note


def test_the_decision_path_never_reads_the_verdict_label(tmp_path):
    """判据侧的第二道锁：把 `judge` 换成一个**根本没有 `label` 键**的替身，
    退出码照样是 0 —— 退出码路径若读了标签，这里会 `KeyError`。"""
    pieces = Pieces(judge=lambda answer: {"ok": True, "note": "（替身：不带 label）"})
    assert run_main(pieces, tmp_path) == 0


# ── M7（变异自查时新发现的缺口，就地补上）─────────────────────────────────────


def test_m7_an_empty_evidence_trace_fails_the_run(tmp_path):
    """**取证轨迹为空 ⇒ 非零退出。**

    ⚠️ 这一条是 Phase 4 变异自查**当场补出来**的：原来只有一条「快乐路径上
    `evidence_trace_enumerable` 为真」的断言，把 `decide()` 里那一项**改成恒真**，
    14 条判据**照样全绿** —— 一条恒真的判据等于没判。

    构造：剧本第一步就直接作答（一次工具都不调）。② 门禁因 L1 未覆盖而拦下，
    `ScriptedModel` 重复最后一步 ⇒ 循环耗尽轮数、`answer` 为空、`tool_calls` 为空。
    """
    pieces = Pieces(steps=[GROUNDED_ANSWER])
    assert run_main(pieces, tmp_path) == 1

    evidence = evidence_of(tmp_path)
    record = evidence["attributions"][0]
    assert record["tool_calls"] == []
    assert record["accepted"] is False
    assert evidence["checks"]["evidence_trace_enumerable"] is False
    # 其余五项**不受牵连**：本条只测这一项，不靠"反正红了"蒙混。
    assert evidence["checks"]["hits_not_empty"] is True
    assert evidence["checks"]["hits_unchanged"] is True
    assert evidence["checks"]["ledger_matches_chat_calls"] is True
    assert evidence["checks"]["no_denied_requests"] is True
    assert evidence["checks"]["no_credentials_in_evidence"] is True
