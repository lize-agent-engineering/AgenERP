"""🔴 P1.8a 门禁 · 解释服务的 HTTP 面（同源 + `sid` 认人）

判据来源：`docs/masterplan/02-WBS.md` §4 第 P1.8a 行 ——
`pytest -m live tests/gates/test_explain_service_live.py` 退 0，
且**零依赖启动门禁须仍绿**（新服务必须在「一个 AI 变量都不配」时也起得来）。

**本文件不重写断言体**，按路径加载 `tests/unit/test_explain_service_body.py`。
与 `test_tool_execution_live.py` 同一取舍：判据只有一份，门禁是它的严格模式。

## ⚠️ 本文件现在**预期是红的**

它要的两样东西今天还不存在（P1.8a 的第 2 个 plan 才做）：

1. 服务没接进 compose —— 今天只能人手工 `python3 -m agenerp.serve` 起
2. nginx 还没有 `location /agenerp/` 反代 —— 而 `sid` 是 `HttpOnly` **且按同源发送**，
   不同源就根本拿不到 cookie，**这条判据的整个前提不成立**

⚠️ **它不进 `expected-red.txt`，那个名单对 live 门禁无效。** 2026-08-25 实测确认：
判定器在**默认模式**下按标记把 `live` 那批整体排除（junit 里 26 条，
`test_zero_dep_boot` / `test_tool_execution_live` 一条都没有），而在 **live 模式**下
逐字「**不读**预期红名单，契约是全部绿、零 red、零 skip」。
→ 登记进名单在两种模式下都不起作用，**登了等于骗自己**。

**那它今天怎么不挡路？** 因为 live 门禁只在 `AGENERP_LIVE=1` 时跑，而那是
CI 的 `gates-l2-live` job 与人手工的事。第 2 个 plan 把 compose + nginx 接好之前，
**跑 live 判定就会红在这六条上** —— 这是对的：它如实反映「P1.8a 还没做完」。

**先建后绿，不是先绿后建。** 判据先立着，实现追上来 —— 这样「实现到位」
有一个客观的判定时刻，而不是由做的人自己宣布。
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.live

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(relative_path: str, module_name: str):
    """按路径加载仓内另一个测试模块。找不到就**抛**，不静默降级。"""
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"{relative_path} 不存在。判据的断言体只有一份，源文件没了就是红，"
            "不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BODY = _load("tests/unit/test_explain_service_body.py", "_gate_body_explain_service")


# ── 收严：skip → fail（这一行由人写，理由见断言体的 docstring）──────────
#
# 断言体住在 `tests/unit/`，日常那一轮不该因为没起服务就整轮红，所以它
# **够不到服务时 skip**。门禁这一份不行：`gates-l2-live` 的契约逐字是
# 「全部绿、零 red、零 skip」——**一条会 skip 的门禁等于一条不存在的门禁**。
#
# 做法是把断言体模块里的 `pytest.skip` 换成 `pytest.fail`，而不是在每条测试
# 外面包一层：包一层要写六遍，漏一条就留一个静默出口；换掉模块级引用只需
# 一处，且**新增的测试自动受管**。
def _skip_is_a_failure_here(reason: str) -> None:
    pytest.fail(
        f"{reason}\n"
        "—— 在门禁里这是**红**，不是跳过。`gates-l2-live` 的契约是「零 skip」：\n"
        "一条会 skip 的门禁等于一条不存在的门禁。\n"
        "要跑它：先接 compose + nginx 同源反代（P1.8a 第 2 个 plan），再\n"
        "    AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=admin \\\n"
        "    python3 -m pytest -m live tests/gates/test_explain_service_live.py"
    )


_BODY.pytest.skip = _skip_is_a_failure_here

test_health_is_200_through_the_same_origin_front = _BODY.test_health_is_200_through_the_same_origin_front
test_explain_without_any_cookie_is_401_through_the_same_origin_front = _BODY.test_explain_without_any_cookie_is_401_through_the_same_origin_front
test_explain_with_a_forged_sid_is_401_and_never_falls_back = _BODY.test_explain_with_a_forged_sid_is_401_and_never_falls_back
test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to = _BODY.test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to
test_no_response_through_the_front_ever_echoes_the_sid = _BODY.test_no_response_through_the_front_ever_echoes_the_sid
test_caller_claimed_context_is_rejected_through_the_front = _BODY.test_caller_claimed_context_is_rejected_through_the_front
