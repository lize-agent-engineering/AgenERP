"""🔴 P1.0a 门禁 · 工具执行层：十个工具在活站点上**守约**。

判据来源（WBS `02-WBS.md` §4 第 P1.0a 行，逐字）：

    🔴 `tests/gates/test_tool_execution_live.py` —— 每个工具在活站点上各跑一次，
    断言**返回形状合约束**（`must_keep` 字段在、`max_rows` 不超、裁剪规则生效）。
    ⚠️ 判据不许只验「调得通」

**本文件与 `tests/tools/test_live_conformance.py` 的关系**：后者是同一套断言的
**开发期形态**，由执行层的实现者写在红线外（`tests/gates/**` 在红线内，loop
不得修改门禁），并在文件里指名「提升进 gates 需要人操作」。本文件就是人做的
那一半 —— **断言逻辑复用，语义只改一处**：

    无站点时          tests/tools/  → skip（开发期便利）
                      tests/gates/  → **fail**（判定器不接受 skip，未跑就是红）

这一处差别是本文件存在的**全部理由**。一条会 skip 的判据在没有站点的环境里
是绿的 ——「我检查了，全过」与「我根本没看」又一次在退出码上长得一样，
那正是 CP9 继承项①要挡的形状。

⚠️ **断言强度不因为换了路径而改变。** 本文件不重写断言，直接 import 开发期
那份的用例表与核对函数；若那边被改弱，这边同步变弱 —— 这是有意的：
**判据只有一份，不许出现「门禁版」与「开发版」两套标准**。
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_sibling_module(relative_path: str, module_name: str):
    """按路径加载仓内另一个测试模块。找不到就**抛**，不静默降级。

    静默降级会让「判据源文件被删/改名」表现为「门禁少跑几条」——
    那正是判定器不许有的形状。
    """
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"工具执行层门禁依赖 {relative_path}，但它不存在。"
            "判据的断言逻辑只有一份，源文件没了就是红，不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# `tests/` 不是包（没有 `__init__.py`），跨目录 import 不成立 —— 按路径加载。
# **这是有意保留的耦合**：判据只有一份，本文件是它的严格模式。
# 若开发期那份被改弱，这里同步变弱且立刻可见，不会出现「门禁版」与「开发版」
# 两套标准各自漂移。
_CONFORMANCE = _load_sibling_module(
    "tests/tools/test_live_conformance.py", "_p1_0a_live_conformance"
)
CASES = _CONFORMANCE.CASES
CONTEXT = _CONFORMANCE.CONTEXT
_framework_keys_present = _CONFORMANCE._framework_keys_present
_rows_and_envelope = _CONFORMANCE._rows_and_envelope

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def gated_client(request):
    """活站点客户端。**没有站点就红**，不 skip。

    不复用 `conftest.py` 的 `live_site`：那个 fixture 会拉起并接管整套 compose
    环境变量（为定制包往返那类判据准备的），而本判据只要一个能打 REST 面的
    客户端。多接管一层环境 = 多一处能让失败指向错误地方的东西。
    """
    import os

    from agenerp.site import SITE_ENV as _SITE_ENV
    from agenerp.site import SiteError, client_from_env

    site = os.environ.get(_SITE_ENV, "").strip()
    if not site:
        pytest.fail(
            f"工具执行层门禁需要活站点：设置 {_SITE_ENV} 与站点凭据后重跑。\n"
            "    AGENERP_LIVE=1 AGENERP_SITE=frontend "
            "AGENERP_SITE_URL=http://127.0.0.1:18080 \\\n"
            "    AGENERP_ADMIN_PASSWORD=admin python3 -m pytest "
            "tests/gates/test_tool_execution_live.py -q\n"
            "这不是 skip —— 判定器不接受 skip，未跑就是红。"
        )
    try:
        return client_from_env(site)
    except SiteError as exc:
        pytest.fail(f"站点凭据不全，判据无法执行（这是红，不是跳过）：{exc}")


@pytest.mark.parametrize("tool", sorted(CASES), ids=sorted(CASES))
def test_every_tool_returns_a_shape_its_contract_allows(tool, gated_client):
    """十个工具各跑一次，逐条核对返回形状合契约。

    核对的四件事（照 WBS 判据逐字）：`must_keep` 字段都在 · 行数 ≤ `max_rows` ·
    框架管道字段已剥离 · 自由文本带数据边界标记。

    **断言体不在这里重写**，直接调开发期那份 —— 重写会得到两套标准，
    而且我这次重写就写错了一处：`must_keep` 允许落在**信封**上而不是每一行，
    照抄字面判据反而比原实现严，会把守约的实现判成红。
    """
    _CONFORMANCE.test_live_return_shape_conforms_to_the_contract(tool, gated_client)


def test_free_text_from_the_site_is_fenced(gated_client):
    """站点上的用户可写自由文本必须带数据边界标记。

    没有边界，站点上任何一条备注都是一次 prompt injection —— 而备注是**用户写的**，
    不是我们能控制的输入。
    """
    _CONFORMANCE.test_live_free_text_carries_the_data_boundary_marker(gated_client)


def test_rule_lookup_says_what_is_missing_instead_of_faking_an_empty_pack(gated_client):
    """P1.6 之前没有行业包 —— `rule.lookup` 必须**明确报缺**，不许伪造一个空包。

    伪造空包会让「没有规则」与「规则查了但没命中」变成同一件事，
    而 §5.0 ② 的结论正是「无需规则不成立」。
    """
    _CONFORMANCE.test_live_rule_lookup_names_what_is_missing(gated_client)


def test_permission_scope_produces_at_least_one_real_negative(gated_client):
    """**这一条是 `permission.scope` 唯一有意义的判据。**

    站点上只有 Administrator 时它对什么都有权限，所有调用都回 `True` ——
    **一个永远返回 `True` 的实现与正确实现长得一模一样。** 因此必须在受限身份
    下跑，并断言至少出现一个 `False`；否则这个工具的判据是空的。
    """
    import os

    from agenerp.seedusers import WORKER_PASSWORD_ENV

    if not os.environ.get(WORKER_PASSWORD_ENV, "").strip():
        pytest.fail(
            f"受限身份口令未设（{WORKER_PASSWORD_ENV}），本条判据无法执行。\n"
            "    装载受限身份：python3 -m agenerp.seedusers --site frontend\n"
            "**在门禁里这必须是红**：跳过它等于 `permission.scope` 完全没有判据 ——\n"
            "站点上只有 Administrator 时，一个永远回 True 的假实现与正确实现\n"
            "在所有其它断言下都长得一模一样。"
        )
    _CONFORMANCE.test_live_permission_scope_has_a_real_negative(gated_client)
