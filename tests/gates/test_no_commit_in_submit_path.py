"""🔴 P3.2 门禁 · 回滚前提：§7.1 那三个前提在活站点上仍然成立。

判据来源（WBS `02-WBS.md` §6 第 P3.2 行，逐字）：

    🔴 `tests/gates/test_no_commit_in_submit_path.py`

**本文件与 `tests/tools/test_rollback_premises_body.py` 的关系**：后者是同一套断言的
开发期形态，由 P3.2 的实现者写在红线外，并在文件里指名「提升进 gates 需要人操作」。
本文件就是人做的那一半 —— **断言逻辑复用，语义只改一处**：无站点时那边 skip，这边 fail。

⚠️ **本门禁会在活站点上真提交一张单据然后回滚。** 那是它唯一能验到提交路径的方式
（前提 1/2/3 都只在提交过程中才有值）。三层防线在探针里：跑前跑后取站点指纹并逐行比对，
提交全程裹在 savepoint 里且 `finally` 一律回滚，`db.commit` 的桩不放行。
2026-08-29 实测：跑完站点 32 项指纹逐行不变。**若哪天它污染了站点，红的是
`test_the_defences_that_make_the_measurement_trustworthy_held`，不是静默通过。**

⚠️ 断言强度不因为换了路径而改变。本文件不重写断言，直接按路径加载开发期那份；
若那边被改弱，这边同步变弱 —— 这是有意的：判据只有一份，不许出现
「门禁版」与「开发版」两套标准。
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BODY_PATH = "tests/tools/test_rollback_premises_body.py"


def _load_sibling_module(relative_path: str, module_name: str):
    """按路径加载仓内另一个测试模块。找不到就**抛**，不静默降级。"""
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"回滚前提门禁依赖 {relative_path}，但它不存在。"
            "判据的断言逻辑只有一份，源文件没了就是红，不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BODY = _load_sibling_module(_BODY_PATH, "_p3_2_rollback_premises")

# 🔴 **唯一的语义改动**：把断言体的「跑不了」出口收严成 fail。
# 重绑的是 `_BODY` 自己的属性，不是 `pytest.skip` —— 后者是进程级污染。
_BODY._unavailable = pytest.fail

pytestmark = pytest.mark.live


def _premises():
    return _BODY._load(_BODY.PREMISES_JSON)["measurement"]


def test_the_instrument_can_count():
    """阳性对照先跑：前提 1/2 的真值都是 0，仪器瞎了的话那两个 0 不含信息。"""
    _BODY.test_the_instrument_can_count(_premises())


def test_our_channel_cannot_reach_a_savepoint():
    """前提 0 · 两条腿：跨连接够不着 + POST 在响应返回前就 commit。"""
    premises = _premises()
    _BODY.test_premise_0_a_savepoint_does_not_survive_across_connections(premises)
    _BODY.test_premise_0_b_a_post_is_committed_before_the_response_returns(premises)


@pytest.mark.parametrize("scenario", _BODY.SCENARIOS)
def test_the_submit_path_neither_commits_nor_enqueues(scenario):
    premises = _premises()
    _BODY.test_premise_1_the_submit_path_does_not_commit(premises, scenario)
    _BODY.test_premise_2_the_submit_path_does_not_enqueue(premises, scenario)
    _BODY.test_premise_3_no_irreversible_side_effect_escapes_the_transaction(premises, scenario)
    _BODY.test_savepoint_rollback_restores_every_counter(premises, scenario)


def test_backdating_creates_a_work_item_for_an_async_consumer():
    _BODY.test_backdating_creates_a_work_item_for_an_async_consumer(_premises())


def test_the_four_before_submit_hooks_the_wbs_names_do_not_exist_here():
    _BODY.test_no_doctype_has_the_four_before_submit_hooks_the_wbs_names(_premises())


def test_the_defences_that_make_the_measurement_trustworthy_held():
    """三层防线里可判的两层：指纹会咬人 · 探测没污染站点。"""
    _BODY.test_the_site_fingerprint_has_teeth(_BODY._load(_BODY.MUTATION_JSON))
    _BODY.test_the_probe_left_the_site_identical(_premises())


def test_hypotheses_were_frozen_before_the_result_landed():
    _BODY.test_hypotheses_were_frozen_before_the_result_landed()
    _BODY.test_the_hypotheses_say_which_predictions_were_not_blind()


def test_live_the_three_premises_still_hold_today():
    """**当场重跑探测**，不只钉住 2026-08-29 那份 JSON。

    三个前提是 ERPNext 的实现细节、不是承诺（§7.1 原话）——
    只钉历史的话，升一次镜像它照样绿而站点上的语义已经变了。
    """
    _BODY.test_live_the_three_premises_still_hold_today()
