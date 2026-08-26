"""⌘K 侧边栏活体门禁 —— `02-WBS.md:89` 那条验收命令打的就是本文件。

    AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin \
      python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs

**判据只有一份，本文件是它的严格模式**（形态与 `tests/gates/test_explain_service_live.py`
同族，落点写在 `docs/architecture/module-boundaries.md` §7.23.5）。
断言体住在 `tests/unit/test_desk_sidebar_body.py` —— 那里**受 `pytest tests/unit -q`
那一轮保护**，日常改坏了看得见；住进 `tests/ui/` 就不受保护了。

**本文件按顺序做四件事，缺一条都会长出一个静默出口**：

1. **先自己 `import playwright`，失败即 `pytest.fail`** ——
   不是 `importorskip`。驱动不在时门禁必须**红**，不是跳过。
2. 按路径 `exec_module()` 加载断言体。
3. 把断言体的 `_unavailable` **这一个名字**重绑成 `pytest.fail`。
   ⚠️ **重绑的是断言体模块自己的属性，不是 `pytest` 模块的属性** ——
   先例那种 `_BODY.pytest.skip = …` 改的是全局 `pytest` 模块，属**进程级污染**
   （同一轮里别的测试文件也被改）。本形态没有这个副作用，
   且**断言体里新增的「跑不了」出口自动受管**（好处与先例相同）。
   ⚠️ **收严必须在 `exec_module()` 之后**：模块级的 skip 在 `exec_module()` 里就抛完了，
   收严那一行还没执行 ⇒ 结果是**门禁退 0 且 `1 skipped`——一条绿着的、不存在的门禁**。
   断言体因此**禁用**模块级 `pytest.skip` / `pytest.importorskip`（离线守卫①② 盯着）。
4. **把断言体里每一个 `test_` 函数逐条重绑进本模块命名空间。**
   ⚠️ 漏了这一步，本文件**一条都收集不到 ⇒ 退出码 5**（`no tests collected`），
   而「零 skip」这句话在**一条都没跑**的情况下也成立。
   离线守卫④（`tests/unit/test_desk_sidebar_static.py`）逐条比对这两个名字集合，**不靠人眼数**。

⚠️ **basename 必须与断言体那份不同**（`test_sidebar.py` vs `test_desk_sidebar_body.py`，已不同）——
`tests/` 下没有 `__init__.py`，同名 basename 会让整轮 `pytest` `import file mismatch` 收集失败。
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.live

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BODY_PATH = "tests/unit/test_desk_sidebar_body.py"


def _require_driver() -> None:
    """① 驱动不在 ⇒ **红**，不是跳过。

    `pyproject.toml` 的 `ui` extra（D-25）声明的是 `playwright` 这个**包**，
    **不含浏览器二进制** —— 逐字「装包不等于能跑」。
    包在而二进制不在时，红会出在断言体那个自建 fixture 里（`Executable doesn't exist`），
    同样是红，同样不是跳过。
    """
    try:
        import playwright  # noqa: F401
    except ImportError as exc:
        pytest.fail(
            f"浏览器驱动导入不了：{exc}\n"
            "—— 在门禁里这是**红**，不是跳过。一条会 skip 的门禁等于一条不存在的门禁。\n"
            "要跑它：\n"
            "    python3 -m pip install -e '.[ui]'   # D-25 的 ui extra\n"
            "    python3 -m playwright install chromium   # 装包不等于能跑\n"
        )


def _load(relative_path: str, module_name: str):
    """② 按路径加载断言体。找不到就**抛**，不静默降级。"""
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"{relative_path} 不存在。判据的断言体只有一份，源文件没了就是红，不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_require_driver()
_BODY = _load(_BODY_PATH, "_gate_body_desk_sidebar")


def _unavailable_is_a_failure_here(reason: str) -> None:
    """③ 收严：断言体的 `_unavailable` 在这里是 `fail`。"""
    pytest.fail(
        f"{reason}\n"
        "—— 在门禁里这是**红**，不是跳过。本文件的契约是「全部绿、零 skip」：\n"
        "一条会 skip 的门禁等于一条不存在的门禁。\n"
        "要跑它：先按 §5 起活栈，再\n"
        "    AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin \\\n"
        "    python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs"
    )


_BODY._unavailable = _unavailable_is_a_failure_here

# ④ 逐条重绑。**新增断言体里的测试或 fixture 时这里必须跟着加一行**，守卫④ 会逐条比对。
#
# ⚠️ **fixture 也要重绑，不只是 `test_` 函数** —— 这是执行期实测踩出来的，钉在这里：
# 只重绑测试函数时，`pytest` 在**本模块**的命名空间里找不到 `desk` / `driver` / `real_exchange`，
# 结果是 **11 个 `error`（`fixture 'desk' not found`）**，退出码非 0。
# 先例 `tests/gates/test_explain_service_live.py` 没踩到它，只因为**它的断言体里一个 fixture 都没有**。
driver = _BODY.driver
desk = _BODY.desk
real_exchange = _BODY.real_exchange

test_the_browser_carries_the_httponly_sid_to_the_explain_endpoint = _BODY.test_the_browser_carries_the_httponly_sid_to_the_explain_endpoint
test_the_request_body_carries_only_the_keys_the_service_accepts = _BODY.test_the_request_body_carries_only_the_keys_the_service_accepts
test_the_panel_renders_the_state_of_whatever_code_actually_came_back = _BODY.test_the_panel_renders_the_state_of_whatever_code_actually_came_back
test_the_real_exchange_never_echoes_the_session_cookie_into_the_panel = _BODY.test_the_real_exchange_never_echoes_the_session_cookie_into_the_panel
test_every_distinguishable_code_renders_a_distinct_non_empty_state = _BODY.test_every_distinguishable_code_renders_a_distinct_non_empty_state
test_an_unenumerated_code_renders_the_fallback_state = _BODY.test_an_unenumerated_code_renders_the_fallback_state
test_a_transport_level_failure_renders_instead_of_hanging = _BODY.test_a_transport_level_failure_renders_instead_of_hanging
test_a_real_nginx_502_renders_without_assuming_the_body_is_json = _BODY.test_a_real_nginx_502_renders_without_assuming_the_body_is_json
test_the_shortcut_opens_toggles_and_escapes_and_gives_focus_back = _BODY.test_the_shortcut_opens_toggles_and_escapes_and_gives_focus_back
test_the_panel_states_the_context_it_is_about_to_send = _BODY.test_the_panel_states_the_context_it_is_about_to_send
test_the_site_rejects_a_browser_session_sid_without_a_csrf_token = _BODY.test_the_site_rejects_a_browser_session_sid_without_a_csrf_token
