"""配了哪个模型就必须用哪个 —— 配置面的「配了就该生效」判据。

判据来源：人 2026-08-26 裁定（P1 复盘 B④）。

## 它防的是什么 —— 一个活了很久没人发现的死配置

`route()` 不传 `requested` 时取「**第一个满足该任务类目的档案**」，
用的是 `profile.name` —— **`AGENERP_LLM_MODEL` 被完全忽略**。

实测后果（2026-08-26）：CI 配的是 `qwen3.7-flash`，实际走 `qwen3.8-max`，
而后者**没有免费额度** ⇒ 端点 403 ⇒ 每一次解释都失败、回空答案。
**配置面没有任何判据发现这件事**，它是人手动跑真解释才撞出来的。

## 判据形状

配一个值 → 走一次真实的构造路径 → **断言实际用的就是它**。
不打站点、不调模型（本判据是纯离线的）。

⚠️ **点名一个系统不认识的模型时必须明确失败**，不许悄悄换一个跑 ——
那正是这个 bug 当初的形态。
"""
from __future__ import annotations

import pytest

from agenerp.routing import capabilities, config as routing_config
from agenerp.routing.router import route, RoutingError


def _cfg(model: str):
    return routing_config.from_env(
        {
            "AGENERP_LLM_BASE_URL": "https://example.invalid/v1",
            "AGENERP_LLM_API_KEY": "test-only-not-a-real-key",
            "AGENERP_LLM_MODEL": model,
        }
    )


@pytest.mark.parametrize(
    "model",
    # `KNOWN_MODEL_PROFILES` 是 dict —— 直接迭代拿到的是键（字符串），要 `.values()`
    [p.name for p in capabilities.KNOWN_MODEL_PROFILES.values() if p.satisfies("explain")],
)
def test_the_model_actually_used_is_the_one_configured(model: str) -> None:
    """逐个已声明模型：配它 ⇒ 用它。"""
    adapter = route(
        "explain",
        models=capabilities.KNOWN_MODEL_PROFILES,
        requested=model,
        config=_cfg(model),
    )
    assert adapter.model == model, (
        f"配的是 {model!r}，实际却用了 {adapter.model!r} —— 配置没生效。\n"
        "这正是 2026-08-26 那个 bug 的形态：route() 不传 requested 时取"
        "「第一个满足能力的档案」，配置里的模型名被完全忽略。"
    )


def test_an_unknown_model_fails_loudly_instead_of_silently_swapping() -> None:
    """配了系统不认识的模型 ⇒ **明确失败**，不许悄悄换一个跑。"""
    with pytest.raises(RoutingError) as caught:
        route(
            "explain",
            models=capabilities.KNOWN_MODEL_PROFILES,
            requested="a-model-nobody-declared",
            config=_cfg("a-model-nobody-declared"),
        )
    assert "a-model-nobody-declared" in str(caught.value), (
        "拒绝时必须点名是哪个模型不认识，否则使用者无从下手"
    )
