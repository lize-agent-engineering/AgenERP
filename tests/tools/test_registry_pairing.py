"""契约 ↔ 执行体的双向注册判据。

少一边就是一个静默缺口：
**加了执行体忘了契约** → 它绕过前置门禁、裁剪与后置断言整层；
**加了契约忘了执行体** → 控制循环调它时才在运行期炸，而不是在判据里红。

这条判据故意写得笨：它不认识任何一个具体工具，只比对两个集合。
"""

from __future__ import annotations

import inspect

from agenerp.tools.registry import EXECUTORS
from agenerp.tools_readonly import ALL_CONTRACTS, ALL_TOOL_NAMES


def test_every_contract_has_an_executor():
    missing = sorted(set(ALL_TOOL_NAMES) - set(EXECUTORS))
    assert not missing, f"这些契约没有执行体：{missing}"


def test_every_executor_has_a_contract():
    orphans = sorted(set(EXECUTORS) - set(ALL_TOOL_NAMES))
    assert not orphans, f"这些执行体没有契约（会绕过前置/裁剪/后置整层）：{orphans}"


def test_the_two_sides_are_the_same_size():
    """集合相等还不够：契约表里重名会让「按名取契约」静默取错一条。"""
    assert len(ALL_CONTRACTS) == len(set(ALL_TOOL_NAMES)) == len(EXECUTORS)


def test_every_executor_takes_the_session_seam():
    """执行体必须收 `(session, params)`。

    收 `client` 的执行体绕得过 `Session` 的调用留痕，而「过程约束」类后置断言
    （逐个探权限、不跨表拼装）**只能**从那份留痕上推出来。
    """
    for tool, executor in sorted(EXECUTORS.items()):
        params = list(inspect.signature(executor).parameters)
        assert params[:2] == ["session", "params"], f"{tool} 的签名是 {params}"
