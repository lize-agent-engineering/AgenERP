"""活端点冒烟：**一次**最小请求，证明"三项分开记"在真实回包上也成立。

假 transport 只能证明解析逻辑对，证明不了**真实端点真的把 reasoning token
放在 `completion_tokens_details.reasoning_tokens` 里**。这一条只有真跑一次能拿到。

预期在开工前就写死在 plan 里（Phase 3）：`usage.reasoning > 0`。
依据 D-11 —— `qwen3.6-plus` 是推理模型，**回两个字也烧约 195 reasoning token**。
所以这条断言同时是两件事的判据：三项确实分开了，且 reasoning 没被算进 completion。

⚠️ 断言写死了"默认模型是推理模型"这个前提。换成非推理模型时它**应该**红 ——
那时该改的是配置或本文件的前提说明，**不是把断言放松成 `>= 0`**（那等于没判据）。

无凭据时 **skip 并打印理由**（照 `tests/tools/test_live_conformance.py` 的先例）：
静默跳过与"跑过且全绿"在退出码上一样。
"""

from __future__ import annotations

import os

import pytest

from agenerp.routing import route
from agenerp.routing.adapter import Reply
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES, ModelProfile
from agenerp.routing.config import REQUIRED_ENV, from_env
from agenerp.routing.errors import RoutingError

pytestmark = pytest.mark.live


def _skip(reason: str) -> None:
    print(f"[routing-live] 跳过：{reason}")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def live_config():
    missing = [name for name in REQUIRED_ENV if not (os.environ.get(name) or "").strip()]
    if missing:
        _skip(
            f"没有模型凭据 / 端点：设置 {missing} 后重跑"
            "（活站点冒烟由跑的人显式转手，例如 AGENERP_LLM_API_KEY=$DASHSCOPE_API_KEY）"
        )
    return from_env()


@pytest.fixture(scope="module")
def live_profile(live_config) -> ModelProfile:
    profile = KNOWN_MODEL_PROFILES.get(live_config.model)
    if profile is None:
        _skip(
            f"模型 {live_config.model!r} 没有能力档案（本仓实测过的是 "
            f"{sorted(KNOWN_MODEL_PROFILES)}）—— 补档案是人的活，不由判据代填"
        )
    if not profile.is_reasoning_model:
        _skip(
            f"模型 {live_config.model!r} 的档案写着它不计 reasoning token，"
            "本判据的预期（reasoning > 0）对它不成立"
        )
    return profile


def test_a_single_live_call_comes_back_with_the_three_token_counts_kept_apart(
    live_config, live_profile
):
    adapter = route("explain", models=[live_profile], config=live_config)
    assert adapter.model == live_config.model

    try:
        reply = adapter.chat([{"role": "user", "content": "只回两个字：在线"}], max_tokens=64)
    except RoutingError as exc:
        pytest.fail(f"活端点调用失败（**没有降级成空回答**，这是对的）：{exc}")

    assert isinstance(reply, Reply)
    assert reply.usage.prompt > 0, "真实回包应当报 prompt token"
    assert reply.usage.reasoning > 0, (
        f"D-11：{live_config.model} 是推理模型，回两个字也该烧 reasoning token；"
        f"拿到 {reply.usage.as_dict()}。**不要把这条放松成 >= 0**"
    )
    print(f"[routing-live] {live_config.model} usage={reply.usage.as_dict()} text={reply.text!r}")
