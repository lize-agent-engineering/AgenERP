"""🔴 渲染器活体门禁 —— `02-WBS.md` §5 第 102 行那条验收命令打的就是本文件。

    AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_WORKER_PASSWORD=… \
      python3 -m pytest -m live tests/render -q -rs

**判据只有一份，本文件是它的严格模式**（形态与 `tests/ui/test_sidebar.py` 逐条同族，
落点 `module-boundaries.md` §7.23.5）。断言体住在 `tests/unit/test_render_body.py` ——
那里**受 `pytest tests/unit -q` 那一轮保护**，日常改坏了看得见；
住进 `tests/render/` 就不受保护了。

**本文件按顺序做四件事，缺一条都会长出一个静默出口**：

1. **先自己 `import playwright`，失败即 `pytest.fail`** —— 不是 `importorskip`。
   驱动不在时门禁必须**红**，不是跳过。
2. 按路径 `exec_module()` 加载断言体。
3. 把断言体的 `_unavailable` **这一个名字**重绑成 `pytest.fail`。
   ⚠️ 重绑的是**断言体模块自己的属性**，不是 `pytest` 模块的属性 ——
   后者是进程级污染（同一轮里别的测试文件也被改）。
   ⚠️ **收严必须在 `exec_module()` 之后**：模块级的 skip 在 `exec_module()` 里就抛完了，
   收严那一行还没执行 ⇒ 结果是**门禁退 0 且 `1 skipped`——一条绿着的、不存在的门禁**。
4. **把断言体里每一个 `test_` 函数逐条重绑进本模块命名空间。**
   ⚠️ 漏了这一步，本文件**一条都收集不到 ⇒ 退出码 5**（`no tests collected`），
   而「零 skip」这句话在**一条都没跑**的情况下也成立。
   下面 `test_every_assertion_in_the_body_got_rebound` 逐条比对两个名字集合，**不靠人眼数**。

⚠️ **basename 与断言体那份不同**（`test_renderer.py` vs `test_render_body.py`，已不同）——
`tests/` 下没有 `__init__.py`，同名 basename 会让整轮 `pytest` `import file mismatch`。
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.live

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BODY_PATH = "tests/unit/test_render_body.py"


def _require_driver() -> None:
    """① 驱动不在 ⇒ **红**，不是跳过。

    `pyproject.toml` 的 `ui` extra（D-25）声明的是 `playwright` 这个**包**，
    **不含浏览器二进制** —— 逐字「装包不等于能跑」。二进制那一层由断言体的
    `driver` fixture 判（它此刻的 `_unavailable` 已被重绑成 `fail`）。
    """
    try:
        import playwright  # noqa: F401  (只为确认它在)
    except ImportError as exc:  # pragma: no cover - 装了就走不到
        pytest.fail(
            f"playwright 没装（{exc}）—— 活体门禁在驱动缺失时必须红，不许跳过。\n"
            "  python3 -m pip install -e '.[ui]' && python3 -m playwright install chromium"
        )


def _load_body():
    """② 按路径加载断言体，③ 随后立刻把 `_unavailable` 收严。"""
    path = _REPO_ROOT / _BODY_PATH
    if not path.exists():
        pytest.fail(f"断言体不见了：{_BODY_PATH}")
    spec = importlib.util.spec_from_file_location("agenerp_render_body", path)
    if spec is None or spec.loader is None:
        pytest.fail(f"加载不了断言体：{_BODY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _fail(reason: str):
        pytest.fail(f"活体门禁不许跳过：{reason}")

    module._unavailable = _fail
    return module


_require_driver()
_BODY = _load_body()

# ④ 逐条重绑。**fixture 也要**（`driver` / `worker` 是 module 作用域的 fixture，
#   它们由 pytest 按本模块的命名空间解析）。
_BOUND: dict[str, object] = {}
for _name in dir(_BODY):
    if _name.startswith("test_") or _name in ("driver", "worker"):
        _BOUND[_name] = getattr(_BODY, _name)
globals().update(_BOUND)


def test_every_assertion_in_the_body_got_rebound():
    """④ 的守卫：**不靠人眼数**。

    断言体里新增一条判据而这里忘了重绑时，本文件会少收集一条 ——
    而少收集在退出码上与「全过」一模一样。
    """
    in_body = {n for n in dir(_BODY) if n.startswith("test_")}
    here = {n for n in globals() if n.startswith("test_")} - {
        "test_every_assertion_in_the_body_got_rebound"
    }
    missing = in_body - here
    assert not missing, f"断言体里这些判据没被重绑进活体门禁：{sorted(missing)}"


def test_the_body_is_in_strict_mode():
    """③ 的守卫：`_unavailable` 确实被换成了「红」而不是「跳过」。

    没有这一条，收严那一行被误删时门禁会安静地退回 skip 模式，
    而 `-q` 的输出里 `1 skipped` 很容易被读成「过了」。
    """
    # ⚠️ `pytest.fail` 抛的 `Failed` 继承自 **`BaseException`**，不是 `Exception`
    # —— 写成 `pytest.raises(Exception)` 时它根本捕不到，那一格会以「本条判据自己红了」
    # 的形态失败，而不是判出被守的东西。这一行是执行期实测踩出来的。
    with pytest.raises(BaseException) as caught:  # noqa: B017, PT011
        _BODY._unavailable("守卫自检")
    assert "活体门禁不许跳过" in str(caught.value)
