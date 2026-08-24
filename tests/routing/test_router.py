"""路由器的判据 —— 零网络。

**只断言「抛了」是不够的**：一个"永远抛"的假实现同样能让那种判据全绿。
所以每条失败判据都同时要求**异常文本说得出缺什么、缺在谁身上**，
每条成功判据都同时要求**选中的是哪一个**。

四组：

① 满足 → 回对应 adapter，且 adapter 绑的就是那个模型；
② 不满足 → 抛，且文本里含**缺失能力名**与**模型名**；
③ `requested` 与默认两条路径**共用同一条校验** —— 同一组用例参数化跑两遍，判定必须一致；
④ **降级反测** —— 强模型不在候选里时，`route('lineage')` 抛，**不回**那个凑合的弱模型。
"""

from __future__ import annotations

import pytest

from agenerp.routing import route
from agenerp.routing.adapter import ChatAdapter
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES, ModelProfile
from agenerp.routing.config import LlmConfig
from agenerp.routing.errors import DeclarationError, RoutingError

CONFIG = LlmConfig(base_url="https://endpoint.invalid/v1", model="unused", api_key="sk-test")

STRONG = KNOWN_MODEL_PROFILES["qwen3.6-plus"]
WEAK = KNOWN_MODEL_PROFILES["qwen-plus"]
LOCAL = KNOWN_MODEL_PROFILES["qwen3:14b"]

# (模型, 任务类目, 该不该放行)。**同一组用例**下面跑两遍：默认路径一遍，`requested` 路径一遍。
SHARED_CASES = [
    (STRONG, "permission", True),
    (STRONG, "explain", True),
    (STRONG, "lineage", True),
    (STRONG, "shape", True),
    (WEAK, "permission", True),
    (WEAK, "explain", True),
    (WEAK, "lineage", False),
    (WEAK, "shape", False),
    (LOCAL, "permission", True),
    (LOCAL, "explain", True),
    (LOCAL, "lineage", False),
    (LOCAL, "shape", False),
]

CASE_IDS = [f"{p.name}-{task}-{'ok' if allowed else 'blocked'}" for p, task, allowed in SHARED_CASES]


def _route(task, models, requested=None):
    return route(task, models=models, requested=requested, config=CONFIG, transport=lambda p: {})


# --- ① 满足 → 回对应 adapter -------------------------------------------------


def test_a_satisfying_model_yields_an_adapter_bound_to_that_model():
    adapter = _route("lineage", [STRONG])
    assert isinstance(adapter, ChatAdapter)
    assert adapter.model == "qwen3.6-plus"
    assert adapter.profile is STRONG


def test_the_first_satisfying_candidate_wins_in_declaration_order():
    """候选顺序 = 调用方的偏好顺序。刻意不按快 / 便宜排序（那不是能力）。"""
    assert _route("explain", [LOCAL, STRONG]).model == "qwen3:14b"
    assert _route("explain", [STRONG, LOCAL]).model == "qwen3.6-plus"


def test_an_unsatisfying_candidate_is_skipped_for_a_satisfying_one():
    """跳过不合格的去选合格的**不是降级** —— 回来的那个满足最低能力。"""
    assert _route("lineage", [LOCAL, WEAK, STRONG]).model == "qwen3.6-plus"


# --- ② 不满足 → 抛，且文本说得出缺什么、缺在谁身上 ---------------------------


def test_failure_text_names_every_missing_capability_and_the_model():
    with pytest.raises(RoutingError) as caught:
        _route("shape", [LOCAL])
    text = str(caught.value)
    assert "qwen3:14b" in text
    for missing in ("long_context", "multi_hop", "reasoning"):
        assert missing in text, f"异常文本没说缺 {missing}，那就定位不到问题"
    assert "tool_calling" not in text.split("缺 ", 1)[1], "不该把已具备的能力也报成缺失"


def test_failure_text_lists_every_candidate_not_just_the_first():
    with pytest.raises(RoutingError) as caught:
        _route("lineage", [LOCAL, WEAK])
    text = str(caught.value)
    assert "qwen3:14b" in text and "qwen-plus" in text


def test_an_unknown_task_class_is_rejected_before_any_model_is_picked():
    with pytest.raises(DeclarationError, match="未知任务类目"):
        _route("vibes", [STRONG])


def test_an_empty_candidate_set_fails_loudly():
    with pytest.raises(RoutingError, match="没有任何候选模型档案"):
        _route("explain", [])


# --- ③ `requested` 与默认路径共用同一条校验 ----------------------------------


@pytest.mark.parametrize(("profile", "task", "allowed"), SHARED_CASES, ids=CASE_IDS)
def test_default_path_verdict(profile: ModelProfile, task: str, allowed: bool):
    if allowed:
        assert _route(task, [profile]).model == profile.name
    else:
        with pytest.raises(RoutingError):
            _route(task, [profile])


@pytest.mark.parametrize(("profile", "task", "allowed"), SHARED_CASES, ids=CASE_IDS)
def test_requested_path_verdict_is_identical(profile: ModelProfile, task: str, allowed: bool):
    """「我点名要它」**不是豁免**。静默降级最常见的形态就是"用户点名了，那就别拦"。"""
    if allowed:
        assert _route(task, [profile], requested=profile.name).model == profile.name
    else:
        with pytest.raises(RoutingError):
            _route(task, [profile], requested=profile.name)


@pytest.mark.parametrize(("profile", "task", "allowed"), SHARED_CASES, ids=CASE_IDS)
def test_requesting_a_weak_model_out_of_a_full_candidate_set_is_still_checked(
    profile: ModelProfile, task: str, allowed: bool
):
    """点名之后**不许回落到别的候选**：候选集里有强模型也救不了被点名的弱模型。"""
    everything = [STRONG, WEAK, LOCAL]
    if allowed:
        assert _route(task, everything, requested=profile.name).model == profile.name
    else:
        with pytest.raises(RoutingError) as caught:
            _route(task, everything, requested=profile.name)
        assert profile.name in str(caught.value)


def test_requesting_a_model_outside_the_candidates_fails_by_name():
    with pytest.raises(RoutingError, match="不在候选档案里"):
        _route("explain", [STRONG], requested="gpt-9-omni")


# --- ④ 降级反测 --------------------------------------------------------------


def test_when_the_strong_model_is_unavailable_lineage_raises_instead_of_falling_back():
    """**这是本模块存在的理由。** 强模型不可用时，跨单据血缘推理**不许**改派弱模型。
    §12.1 ③ 逐字："不满足则明确失败，绝不静默降级"。"""
    available = [WEAK, LOCAL]  # 强模型不在候选里
    assert WEAK.satisfies("explain"), "前提：弱模型确实可用，只是不够做 lineage"
    with pytest.raises(RoutingError) as caught:
        _route("lineage", available)
    text = str(caught.value)
    assert "multi_hop" in text and "reasoning" in text
    assert "不降级" in text


def test_the_same_weak_model_is_still_handed_out_for_the_task_it_does_satisfy():
    """降级反测不能靠"一律拒绝"蒙过去：同一批候选下 `explain` 必须照常放行。"""
    assert _route("explain", [WEAK, LOCAL]).model == "qwen-plus"


def test_route_falls_back_to_env_config_only_when_no_config_is_given(monkeypatch):
    """没给 config 时读环境；环境也没有则**明确失败**，不内置端点。"""
    for name in ("AGENERP_LLM_BASE_URL", "AGENERP_LLM_API_KEY", "AGENERP_LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RoutingError, match="配置不全"):
        route("explain", models=[STRONG])
