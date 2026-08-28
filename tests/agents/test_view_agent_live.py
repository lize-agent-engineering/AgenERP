"""🔴 P2.3 · 视图 Agent 活体判据的**严格模式壳** —— 真模型 · 真站点 · 真 schema。

    set -a; . ~/.config/agenerp/secrets.env; set +a
    export AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY"
    export AGENERP_LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
    export AGENERP_LLM_MODEL=qwen3.8-2.4t-a95b
    export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
           AGENERP_ADMIN_PASSWORD=admin
    python3 -m pytest -m live tests/agents/test_view_agent_live.py -q -rs

**判据只有一份，本文件是它的严格模式**（形态与 `tests/render/test_renderer.py`
逐条同族）。断言体住 `tests/unit/test_view_agent_live_body.py` ——
那里受 `pytest tests/unit -q` 那一轮保护，日常改坏了看得见。

## 本文件按顺序做三件事，缺一条都会长出一个静默出口

1. 按路径 `exec_module()` 加载断言体。
2. 把断言体的 `_unavailable` **这一个名字**重绑成 `pytest.fail`。
   ⚠️ 重绑的是**断言体模块自己的属性**，不是 `pytest` 模块的属性 ——
   后者是进程级污染。
   ⚠️ **收严必须在 `exec_module()` 之后**：模块级的 skip 在 `exec_module()` 里就抛完了。
3. **把断言体里每一个 `test_` 函数与 fixture 逐条重绑进本模块命名空间。**
   ⚠️ 漏了这一步，本文件**一条都收集不到 ⇒ 退出码 5**，
   而「零 skip」在**一条都没跑**的情况下也成立。
   下面 `test_every_assertion_in_the_body_got_rebound` 逐条比对，**不靠人眼数**。

## ⚠️ 它现在**不在** `tests/gates/`

人 2026-08-28 裁定：本项先写在 `tests/agents/`，落 `tests/gates/**` 另行指派
（红线 ②，提交要带 `Gates-Change-Approved-By:`）。
🔴 **将来落地时必须在最终位置重跑** —— `docs/logs/2026/08-28-handoff-p2.md` §3⑤：
「在最终位置跑一遍」和「跑过」是两件事。**换位置本身就是一个变量。**

## ⚠️ 本文件带 `live` 标记，日常那一轮要用 `-m "not live"` 排除它

`pyproject.toml` 的 marker 注释逐字：「L1 快门禁跑 `-m 'not live'`」。
既有的三个活体目录（`gates` / `render` / `ui`）是**按目录** `--ignore` 排除的，
而 `tests/agents/` 里两种判据同住 —— WBS 第 103 行那条命令打的是
`test_view_agent.py` 单文件，不受影响；跑整个 `tests/` 时**要带 `-m "not live"`**。
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.live

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BODY_PATH = "tests/unit/test_view_agent_live_body.py"


def _load_body():
    """① 按路径加载断言体，② 随后立刻把 `_unavailable` 收严。"""
    path = _REPO_ROOT / _BODY_PATH
    if not path.exists():
        pytest.fail(f"断言体不见了：{_BODY_PATH}")
    spec = importlib.util.spec_from_file_location("agenerp_view_agent_live_body", path)
    if spec is None or spec.loader is None:
        pytest.fail(f"加载不了断言体：{_BODY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _fail(reason: str):
        pytest.fail(f"活体判据不许跳过：{reason}")

    module._unavailable = _fail
    return module


_BODY = _load_body()

# ③ 逐条重绑。**fixture 也要** —— `live_client` / `live_schema` / `proposal`
#   是 module 作用域的 fixture，由 pytest 按**本模块**的命名空间解析。
_BOUND: dict[str, object] = {}
for _name in dir(_BODY):
    if _name.startswith("test_") or _name in (
        "live_client", "live_schema", "proposal", "metric_proposal"
    ):
        _BOUND[_name] = getattr(_BODY, _name)
globals().update(_BOUND)


def test_every_assertion_in_the_body_got_rebound():
    """③ 的守卫：**不靠人眼数**。

    断言体里新增一条判据而这里忘了重绑时，本文件会少收集一条 ——
    而少收集在退出码上与「全过」一模一样。
    """
    in_body = {n for n in dir(_BODY) if n.startswith("test_")}
    here = {n for n in globals() if n.startswith("test_")} - {
        "test_every_assertion_in_the_body_got_rebound",
        "test_the_body_is_in_strict_mode",
    }
    missing = in_body - here
    assert not missing, f"断言体里这些判据没被重绑进来：{sorted(missing)}"


def test_the_body_is_in_strict_mode():
    """② 的守卫：`_unavailable` 确实被换成了「红」而不是「跳过」。

    没有这一条，收严那一行被误删时判据会安静地退回 skip 模式，
    而 `-q` 的输出里 `5 skipped` 很容易被读成「过了」。
    """
    # ⚠️ `pytest.fail` 抛的 `Failed` 继承自 **`BaseException`**，不是 `Exception`。
    with pytest.raises(BaseException) as caught:  # noqa: B017, PT011
        _BODY._unavailable("守卫自检")
    assert "活体判据不许跳过" in str(caught.value)
