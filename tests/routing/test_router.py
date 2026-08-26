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
from agenerp.routing.config import LlmConfig, from_env
from agenerp.routing.errors import DeclarationError, RoutingError

# `model=""` 而不是 `"unused"`：那个 `"unused"` 字面量编码的正是「`config.model` 反正会被忽略」
# 这个缺陷本身。空串 = **不点名** ⇒「第一个满足的胜出」那条路径的全部既有判据原样继续有效。
# `from_env()` 造不出空 model（它对空值抛「配置不全」），所以这个分支只在直接构造的判据里可达。
CONFIG = LlmConfig(base_url="https://endpoint.invalid/v1", model="", api_key="sk-test")

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


def test_models_may_be_given_as_a_mapping_not_only_a_sequence():
    """收口审计 F10：`route` 自己的签名写着 `Mapping[str, ModelProfile]`，
    那条分支原先没有判据 —— 一个文档里写着的入参形态必须被判。"""
    as_mapping = {p.name: p for p in (LOCAL, STRONG)}
    assert _route("lineage", as_mapping).model == "qwen3.6-plus"
    assert _route("explain", as_mapping, requested="qwen3:14b").model == "qwen3:14b"
    with pytest.raises(RoutingError):
        _route("shape", {"qwen3:14b": LOCAL})


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


# --- ⑤ `config.model` 就是点名（本节整段是 2026-08-26-1728-1 的新语义判据）-----
#
# 本节钉的是 `route()` 的**选择语义**：给定候选集与 `config.model`，选中的是哪一个、
# 选不动时怎么失败。**从环境配到实际调用**那条端到端路径由
# `tests/unit/test_configured_model_is_the_one_used.py` 钉，两者不互相冒充。


def _cfg(model):
    return LlmConfig(base_url="https://endpoint.invalid/v1", model=model, api_key="sk-test")


def test_configured_model_is_used_even_when_it_is_not_the_first_satisfying_candidate():
    """P2 · 成功面：点名的是候选里**第二个**满足的 —— 「第一个胜出」的旧实现蒙不过去。"""
    assert STRONG.satisfies("explain"), "前提：候选里第一个本来就满足，旧实现会选它"
    adapter = route(
        "explain", models=[STRONG, WEAK], config=_cfg("qwen-plus"), transport=lambda p: {}
    )
    assert adapter.model == "qwen-plus"


def test_configured_model_is_used_when_candidates_come_as_the_known_profile_mapping():
    """P2 · 成功面第二组：候选是映射形态（生产路径的形状），点名的是表里最弱的那个。"""
    adapter = route(
        "explain",
        models=KNOWN_MODEL_PROFILES,
        config=_cfg("qwen3:14b"),
        transport=lambda p: {},
    )
    assert adapter.model == "qwen3:14b"


def test_a_configured_model_outside_the_candidates_fails_by_name():
    """P3 · 失败面之一：点名了候选里没有的名字 ⇒ 抛，且**文本里含那个名字**。

    只断「抛了」不够 —— 一个「永远抛」的假实现同样全绿（见本文件模块头第 3 行）。"""
    with pytest.raises(RoutingError, match="不在候选档案里") as caught:
        route("explain", models=[STRONG], config=_cfg("gpt-9-omni"), transport=lambda p: {})
    assert "gpt-9-omni" in str(caught.value)


def test_a_configured_model_that_lacks_the_capability_does_not_fall_back_to_a_stronger_one():
    """P4 · 失败面之二：点名的在候选里但能力不够 ⇒ 抛，**不回**那个够格的强模型。

    §12.1 ③「绝不静默降级」在新路径上的反测。"""
    assert STRONG.satisfies("lineage"), "前提：候选里确实有一个够格的，回落是可能的"
    with pytest.raises(RoutingError) as caught:
        route(
            "lineage", models=[LOCAL, STRONG], config=_cfg("qwen3:14b"), transport=lambda p: {}
        )
    assert "不降级" in str(caught.value)


def test_an_explicit_request_wins_over_the_configured_model():
    """P5 · 优先级：`requested` 与 `config.model` 同时给且不同 ⇒ **`requested` 胜出**。"""
    adapter = route(
        "explain",
        models=[STRONG, WEAK],
        requested="qwen3.6-plus",
        config=_cfg("qwen-plus"),
        transport=lambda p: {},
    )
    assert adapter.model == "qwen3.6-plus"


def test_an_empty_configured_model_keeps_the_first_satisfying_candidate_path():
    """P6 · 空模型名 ⇒ 不点名 ⇒ 「第一个满足的胜出」原样保留。"""
    adapter = route(
        "explain", models=[LOCAL, STRONG], config=_cfg(""), transport=lambda p: {}
    )
    assert adapter.model == "qwen3:14b"


def test_a_blank_configured_model_is_also_treated_as_not_named():
    """P6b（变异 M3 的判据化）· 纯空白的模型名同样视同**未点名**，不当成一个叫「   」的模型。"""
    adapter = route(
        "explain", models=[LOCAL, STRONG], config=_cfg("   "), transport=lambda p: {}
    )
    assert adapter.model == "qwen3:14b"


def test_the_empty_model_branch_is_unreachable_from_env_config():
    """P6 后半 · 那条空串分支**只在直接构造 `LlmConfig` 的判据里可达**。

    `from_env()` 对空值抛「配置不全」⇒ 生产路径造不出它。"""
    with pytest.raises(RoutingError, match="配置不全"):
        from_env(
            {
                "AGENERP_LLM_BASE_URL": "https://endpoint.invalid/v1",
                "AGENERP_LLM_API_KEY": "sk-test",
                "AGENERP_LLM_MODEL": "",
            }
        )


def test_env_built_config_always_names_a_model():
    """P7 · 生产路径必然点名：三个变量都给全时 `from_env()` 造出的 `model` 恒非空。"""
    built = from_env(
        {
            "AGENERP_LLM_BASE_URL": "https://endpoint.invalid/v1",
            "AGENERP_LLM_API_KEY": "sk-test",
            "AGENERP_LLM_MODEL": "qwen3.6-plus",
        }
    )
    assert built.model == "qwen3.6-plus"
