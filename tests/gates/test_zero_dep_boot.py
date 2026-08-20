"""P0 门禁 · 零依赖启动。

判据（roadmap P0 验收）：**空环境变量**下 `docker compose config && up -d` 成功，
所有服务 healthy，且首页显示「AI 能力未配置」而不是崩溃或白屏。

为什么是门禁而不是优化项：Spike 10 实测当前是失败的，而修法只是 compose 语法——
这是 P0 里最便宜、却守着第一转化率的一项。一个 `git clone && docker compose up` 跑不起来的项目，
后面所有能力都没人看得到。
"""
import os
import subprocess

import pytest

pytestmark = pytest.mark.live

COMPOSE = ["docker", "compose", "-f", "docker-compose.yml"]
# 只留 PATH/HOME：模拟「什么 key 都没配」的新用户
CLEAN_ENV = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}


def test_compose_config_valid_with_empty_env():
    r = subprocess.run(COMPOSE + ["config", "-q"], env=CLEAN_ENV, capture_output=True, text=True)
    assert r.returncode == 0, f"空环境变量下 compose 配置就不合法：{r.stderr[:400]}"


def test_stack_boots_and_all_services_healthy(compose_stack):
    """compose_stack fixture 负责 up -d 与拆栈；这里只判所有服务 healthy。"""
    unhealthy = [s.name for s in compose_stack.services() if s.health != "healthy"]
    assert not unhealthy, f"这些服务没到 healthy：{unhealthy}"


def test_homepage_states_ai_disabled_instead_of_crashing(compose_stack):
    """没配 AI 能力时，首页要明确告诉用户「AI 能力未配置」，而不是 500 或空白。"""
    resp = compose_stack.http_get("/")
    assert resp.status_code == 200, f"首页返回 {resp.status_code}"
    assert "AI 能力未配置" in resp.text, "首页没有说明 AI 能力未配置——用户会以为产品坏了"
