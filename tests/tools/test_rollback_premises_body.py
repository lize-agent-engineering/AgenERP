"""P3.2 回滚前提的**断言体** —— 门禁 `tests/gates/test_no_commit_in_submit_path.py` 的判据源。

`docs/architecture/module-boundaries.md` §7.1 逐字要求那三个前提「必须纳入 CI 回归」。
本文件就是那条回归，形态照 `tests/tools/test_live_conformance.py`：
**断言只有一份**，门禁那边按路径加载本文件并把 `_unavailable` 收严成 `fail`。

⚠️ **本文件是那份「将来要被人提升进 `tests/gates/` 的内容」。**
`tests/gates/**` 在红线 1 内，**执行者不得创建也不得搬运** ——
提升需要人操作并带 `Gates-Change-Approved-By:` trailer。

## 两族断言，分工不同，都不许省

- **离线族**：对着 `docs/evidence/p3-rollback/*.json` 里 2026-08-29 的实测值求值。
  它钉住的是**结论本身**（前提 0 够不着 / 三个前提的实得数 / 「4 道 `before_submit`」不可判），
  以及「预测写在结果之前」这件事。无站点也能跑，是 L1 面。
- **活体族**（`@pytest.mark.live`）：**当场重跑探测**。
  三个前提是 ERPNext 的**实现细节，不是承诺**（§7.1 原话），
  升级一次镜像就可能变 —— 只钉住旧 JSON 的话，判据钉住的是一份历史，不是站点。

## 🔴 为什么有 `test_the_instrument_can_count`

前提 1 与前提 2 的实测值都是 **0**。plan 原定的变异是「把打桩计数改成恒 0 → 判据必须红」，
**那条变异咬不动**：被致盲的仪器与真值恰好同形，任何判据都分不开。
（与 P3.0 那条「阳性对照臂也 0 执行 ⇒ 四格全绿不含信息」是同一个形状。）

所以探针里加了阳性对照（`payload.py::_instrument_selftest`）：故意各触发一次，
把「桩确实记到了」当成结果的一部分。**本文件断它必须为 1** ——
计数一旦被改成恒 0，红的是这一条。变异实得值见 `docs/evidence/p3-rollback/README.md`。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = REPO_ROOT / "docs" / "evidence" / "p3-rollback"
PREMISES_JSON = EVIDENCE / "premises.json"
MUTATION_JSON = EVIDENCE / "mutation-check.json"
HYPOTHESES_MD = EVIDENCE / "HYPOTHESES.md"

SITE_ENV = "AGENERP_SITE"

# 探测当天的场景名。两格都要有值：只测当日那格会漏掉倒填触发的重估值链路，
# 而那正是 `docs/architecture/open-questions.md:92` 登记的缺口。
SCENARIOS = ("normal", "backdated")


def _unavailable(reason: str) -> None:
    """「跑不了」的**唯一**出口。

    门禁那边把本模块的这个名字重绑成 `pytest.fail` —— 重绑的是**本模块自己的属性**，
    不是 `pytest` 模块的属性（后者是进程级污染）。所有跑不了的分支都必须经过它，
    否则门禁的「零 skip」就有漏网的路径。
    """
    print(f"[p3-rollback] 跑不了：{reason}")
    pytest.skip(reason)


def _load(path: Path) -> dict:
    if not path.is_file():
        _unavailable(
            f"缺少实测结果 {path.relative_to(REPO_ROOT)}。"
            "重跑：AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 "
            "AGENERP_ADMIN_PASSWORD=admin python3 tools/experiments/p3_rollback/probe.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def premises() -> dict:
    return _load(PREMISES_JSON)["measurement"]


@pytest.fixture(scope="module")
def mutation() -> dict:
    return _load(MUTATION_JSON)


def _scenario(premises: dict, name: str) -> dict:
    for item in premises["scenarios"]:
        if item["scenario"] == name:
            return item
    raise AssertionError(f"实测结果里没有场景 {name!r}，只有 "
                         f"{[s['scenario'] for s in premises['scenarios']]}")


# ── 阳性对照 ───────────────────────────────────────────────────────────────────


def test_the_instrument_can_count(premises):
    """🔴 仪器有牙齿：桩故意被触发一次时，它数到了 1。

    这一条**必须排在前提 1/2 之前读**：那两条的实得值是 0，
    而「0」与「仪器坏了」在没有本条的情况下完全同形。
    """
    selftest = premises["instrument_selftest"]
    assert selftest["commit_counter_registered"] == 1, (
        f"`db.commit` 的桩故意触发了一次却数到 {selftest['commit_counter_registered']} 次 —— "
        "仪器是瞎的，那么下面「前提 1 = 0 次」这句话不含任何信息"
    )
    assert selftest["enqueue_counter_registered"] == 1, (
        f"`enqueue` 的桩故意触发了一次却数到 {selftest['enqueue_counter_registered']} 次"
    )
    assert selftest["sendmail_counter_registered"] == 1, (
        f"`sendmail` 的桩故意触发了一次却数到 {selftest['sendmail_counter_registered']} 次"
    )


# ── 前提 0：我们的通道够不着 savepoint ────────────────────────────────────────


def test_premise_0_a_savepoint_does_not_survive_across_connections(premises):
    """跨连接够不着 —— 工具层是跨 HTTP 调用的，这是「够不着」的直接证据。"""
    zero = premises["premise_0"]
    assert zero["cross_connection_savepoint_visible"] is False, (
        "另一条连接看得见本连接开的 savepoint —— 若真如此，§7.1 那套跨调用回滚就有戏了，"
        "阶段 D 要回到 `rollback_and_report` 那一支重想"
    )
    assert "does not exist" in (zero["cross_connection_error"] or ""), (
        f"跨连接报的不是「savepoint 不存在」，而是 {zero['cross_connection_error']!r} —— "
        "错因不同，结论不能照搬"
    )


def test_premise_0_b_a_post_is_committed_before_the_response_returns(premises):
    """就算同一条连接也已经晚了：POST 在响应返回前就 commit 了。"""
    zero = premises["premise_0"]
    assert zero["post_is_unsafe"] is True, (
        f"POST 不在 UNSAFE_HTTP_METHODS 里（实得 {zero['unsafe_http_methods']}）"
    )
    assert zero["commits_on_unsafe_method"] is True, (
        "`frappe/app.py::sync_database` 不再按 UNSAFE_HTTP_METHODS 提交 —— "
        f"当期原文见 premises.json 的 measurement.premise_0.source（{zero['source_file']}）"
    )


# ── 前提 1 / 2 / 3 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_premise_1_the_submit_path_does_not_commit(premises, scenario):
    """前提 1：提交路径不自行 `db.commit()`。**实测 0 次。**

    🔴 这个数字一旦不再是 0，**冻结它、不要删断言** —— 删掉等于用绿换掉一条正在说真话的红。
    """
    case = _scenario(premises, scenario)
    assert case["premise_1_commit_calls"] == 0, (
        f"{scenario}：提交路径调了 {case['premise_1_commit_calls']} 次 `db.commit()`。"
        f"栈见 premises.json 的 premise_1_commit_detail。"
        "⇒ 该 DocType 退出可回滚集合；把这个数字冻进判据，不要删断言。"
    )
    assert case["premise_1_raw_txn_sql"] == [], (
        f"{scenario}：提交路径发了裸事务 SQL {case['premise_1_raw_txn_sql']} —— "
        "只堵 `db.commit()` 挡不住它"
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_premise_2_the_submit_path_does_not_enqueue(premises, scenario):
    """前提 2：提交路径不 `enqueue` 后台任务。**两格实测均 0 次。**

    ⚠️ 「0 次 enqueue」**不等于**「没有异步工作项」——
    倒填那一格产出的是一行单据，见下面那条。
    """
    case = _scenario(premises, scenario)
    assert case["premise_2_enqueue_calls"] == 0, (
        f"{scenario}：提交路径入队了 {case['premise_2_enqueue_calls']} 个后台任务，"
        f"详情 {case['premise_2_enqueue_detail']} —— 任务会对着已回滚的数据跑"
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_premise_3_no_irreversible_side_effect_escapes_the_transaction(premises, scenario):
    """前提 3：没有回滚回不掉的事务外动作。

    两条腿：① 提交过程中不发信、不触发 Notification；
    ② 事务边界上的回调**两边对称** —— `after_commit` 上挂的每一类，
    `after_rollback` 上都有对应的一条。只数条数分不清「9 个缓存失效」与「9 封信」。
    """
    case = _scenario(premises, scenario)
    assert case["premise_3_sendmail_calls"] == 0, (
        f"{scenario}：提交过程中发了 {case['premise_3_sendmail_calls']} 封信 —— 回滚回不掉"
    )
    assert case["premise_3_notification_alerts"] == [], (
        f"{scenario}：触发了 Notification {case['premise_3_notification_alerts']}"
    )
    callbacks = case["callbacks_registered"]
    assert callbacks["before_commit"]["count"] == 0, (
        f"{scenario}：`before_commit` 上挂了 {callbacks['before_commit']['functions']}"
    )
    committed = {f["qualname"] for f in callbacks["after_commit"]["functions"]}
    rolled_back = {f["qualname"] for f in callbacks["after_rollback"]["functions"]}
    unmatched = committed - rolled_back - {"flush_realtime_log"}
    assert not unmatched, (
        f"{scenario}：`after_commit` 上有 {sorted(unmatched)} 在 `after_rollback` 上没有对应项 —— "
        "回滚补不掉它们"
    )


# ── 倒填：一个**已提交的**异步工作项 ──────────────────────────────────────────


def test_backdating_creates_a_work_item_for_an_async_consumer(premises):
    """🔴 倒填**真的**触发了 `Repost Item Valuation`（`open-questions.md:92` 那条缺口）。

    形状与「前提 2 不成立」不同，别混成一件事：重估值不是入队的，是**插进去的一行单据**。
    在进程内 savepoint 里它跟着回滚掉了；在 REST 面上 POST 提前 commit
    ⇒ **那一行会被提交下去**，而后置断言此刻还没求值。
    """
    normal = _scenario(premises, "normal")
    backdated = _scenario(premises, "backdated")
    key = "Repost Item Valuation"

    assert normal["counters_after_submit"][key] == normal["counters_before"][key], (
        "当日提交也产生了 Repost Item Valuation —— 那会让「倒填才触发」这句话失效"
    )
    delta = backdated["counters_after_submit"][key] - backdated["counters_before"][key]
    assert delta >= 1, (
        "倒填没有触发 Repost Item Valuation。⇒ 逐字记「重估值链路仍未测到」，"
        "`docs/architecture/open-questions.md` B.1 那条**不许划掉**"
    )
    rows = backdated["repost_item_valuation_rows"]
    assert rows and rows[0]["status"] == "Queued", (
        f"新增的那行不是 Queued 状态：{rows} —— "
        "「等 scheduler 来捡」这句话就要重说"
    )
    assert backdated["premise_2_enqueue_calls"] == 0, (
        "它同时也走了 enqueue —— 那就是两条异步路径，写契约要各声明一次"
    )


# ── savepoint 语义在进程内的复现 ──────────────────────────────────────────────


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_savepoint_rollback_restores_every_counter(premises, scenario):
    """§7.1「单据 / SLE / GL / **naming series 计数器**全部回退」在本仓的复现。

    ⚠️ **条件依赖**：探针把 `db.commit` 打了桩并拦截。本条只在前提 1 实测为 0
    （即那个桩从未触发）时是无条件的 —— 所以上面那条 `test_premise_1_*` 必须一起读。
    """
    case = _scenario(premises, scenario)
    assert case["rollback_restored_every_counter"], (
        f"{scenario}：回滚之后这些计数没回到原位：{case['counter_drift']}"
    )
    series = next(k for k in case["counters_before"] if k.startswith("series:"))
    assert case["counters_after_submit"][series] > case["counters_before"][series], (
        f"{scenario}：提交根本没推进 {series} —— 那么「不产生单号空洞」这句话没被测到"
    )


# ── A3：「4 道 `before_submit`」在本仓不可判 ──────────────────────────────────


def test_no_doctype_has_the_four_before_submit_hooks_the_wbs_names(premises):
    """WBS P3.3 的验收条款「不绕过 **4 道 `before_submit`**」在本仓字面不可判。

    出处是 XM 的 `xm_pattern_demo/hooks.py`，已随 D-9 退役；`agenerp/` 里零命中。
    本条把实测的链长钉住，好让 P3.3 重述验收时有个可引的数。
    """
    chains = premises["before_submit_chain"]
    lengths = {
        doctype: (int(bool(chain["controller_defines_before_submit"]))
                  + len(chain["doc_events_for_doctype"])
                  + len(chain["doc_events_for_all"]))
        for doctype, chain in chains.items()
    }
    assert 4 not in lengths.values(), (
        f"某个 DocType 的 `before_submit` 链真的是 4 道：{lengths} —— "
        "那么 WBS P3.3 的验收条款有了字面依据，本条应当由人重写"
    )
    assert lengths["Stock Entry"] == 0 and lengths["Delivery Note"] == 0, (
        f"Stock Entry / Delivery Note 的链不再是空的：{lengths}"
    )


# ── 三层防线 ─────────────────────────────────────────────────────────────────


def test_the_site_fingerprint_has_teeth(mutation):
    """🔴 防线③：指纹被证明会报红，「跑前跑后逐项相等」才含信息。"""
    assert mutation["fingerprint_bites"], (
        "改了一条数据之后站点指纹照样全绿 —— 指纹没牙，整条探测的结论作废"
    )
    assert mutation["site_restored"], "变异之后站点没还原回去"
    red = mutation["step_4_fingerprint_after_mutation"]["failed_lines"]
    assert any("EXPECTED_BACKLOG_QTY" in line for line in red), (
        f"报红的不是被改的那一项：{red}"
    )


def test_the_probe_left_the_site_identical(premises):
    """跑前跑后指纹逐行相等 —— 探测污染站点时，结论按 plan 直接作废。"""
    result = _load(PREMISES_JSON)
    assert result["fingerprint_before"]["all_green"], "跑前指纹就不绿"
    assert result["fingerprint_identical"], (
        f"探测改了站点：{result['fingerprint_diff']}。"
        "⇒ 结论作废、冷起重来，**不许**用「大概是指纹太严」解释"
    )


# ── 「预测写在结果之前」是可判的 ──────────────────────────────────────────────


def _first_commit_timestamp(path: Path) -> int:
    """该文件**首次落库**的时间。

    用首次（`--diff-filter=A`）而不是最近一次：后者会被一次 `--amend`
    或一次改错别字挪到结果之后去，那样这条判据就自己失效了。
    """
    proc = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ct", "--", str(path.relative_to(REPO_ROOT))],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    stamps = [int(line) for line in proc.stdout.split() if line.strip()]
    if not stamps:
        _unavailable(f"{path.name} 还没进 git，无从判定落库次序")
    return stamps[-1]


def test_hypotheses_were_frozen_before_the_result_landed():
    """CP9 继承项②：**假设事先写死**。这条把它变成机器可判的。

    不写死的话，「预测对了」与「照着结果编了一份预测」在文档上长得一模一样。
    """
    hypotheses_at = _first_commit_timestamp(HYPOTHESES_MD)
    result_at = _first_commit_timestamp(PREMISES_JSON)
    assert hypotheses_at < result_at, (
        f"HYPOTHESES.md 首次落库 {hypotheses_at} 不早于 premises.json 的 {result_at} —— "
        "预测没有写在结果之前，这次探测的「预测命中」不成立"
    )


def test_the_hypotheses_say_which_predictions_were_not_blind():
    """预测记分只有在标了「哪几条不盲」之后才含信息。

    H5（savepoint 进程内回滚）与 H6（前提 0）在冻结前就已经被观测过，
    把它们和 H1/H2/H4/H7 一起数成「7 条全中」是虚报证据强度。
    """
    text = HYPOTHESES_MD.read_text(encoding="utf-8")
    for marker in ("H5", "H6", "不盲"):
        assert marker in text, f"HYPOTHESES.md 里找不到 {marker!r} —— 非盲声明被删掉了"


# ── 活体族：当场重跑，不只钉住一份历史 ────────────────────────────────────────


@pytest.mark.live
def test_live_the_three_premises_still_hold_today():
    """三个前提是 ERPNext 的**实现细节，不是承诺**（§7.1 原话）—— 所以要当场复跑。

    只钉住 2026-08-29 那份 JSON 的话，判据钉住的是一份历史：
    升一次镜像它照样绿，而站点上的语义已经变了。
    """
    site = os.environ.get(SITE_ENV, "").strip()
    if not site:
        _unavailable(
            f"没有活站点：设置 {SITE_ENV} 与站点凭据后重跑。\n"
            "    AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend \\\n"
            "    AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin \\\n"
            "    python3 -m pytest tests/tools/test_rollback_premises_body.py -q"
        )
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from tools.experiments.p3_rollback import probe as probe_module

    try:
        result = probe_module.premises(site)
    except probe_module.ProbeError as exc:
        pytest.fail(f"探测跑不起来（这是红，不是跳过）：{exc}")

    measurement = result["measurement"]
    assert measurement["instrument_selftest"]["commit_counter_registered"] == 1, (
        "阳性对照没记到 —— 仪器是瞎的，下面的 0 不含信息"
    )
    for name in SCENARIOS:
        case = _scenario(measurement, name)
        assert case["premise_1_commit_calls"] == 0, f"{name}：提交路径开始自己 commit 了"
        assert case["premise_2_enqueue_calls"] == 0, f"{name}：提交路径开始入队了"
        assert case["premise_3_sendmail_calls"] == 0, f"{name}：提交过程中发信了"
        assert case["rollback_restored_every_counter"], f"{name}：{case['counter_drift']}"
    assert measurement["premise_0"]["cross_connection_savepoint_visible"] is False
    assert result["fingerprint_identical"], f"复跑污染了站点：{result['fingerprint_diff']}"
