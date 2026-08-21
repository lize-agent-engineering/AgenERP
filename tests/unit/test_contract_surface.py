"""非门禁测试 · 锁住 agenerp 的契约面「存在，且红得有据」。

这不是门禁（门禁在 tests/gates/**，红线内不可改），而是我们自己的回归覆盖：
它守两件事——签名不被误删，以及未实现的函数必须红在 NotImplementedError。

维护方式：**只搬名字，不改结构。** 某个函数真正实现之后，把它的名字从
NOT_YET_IMPLEMENTED 搬到 IMPLEMENTED 即可，且那一步必须是对应 plan 的显式执行项。

⚠️ 关于 skip：pytest 对**零条目**的参数化会报 skipped。本文件收尾时 IMPLEMENTED 为空，
将来六个函数全部实现后 NOT_YET_IMPLEMENTED 也会变空——两种情况下对应那条测试报 skipped
都属预期，不是故障。tools/gates/check_expected_red.py 的「不许 skip」只扫 tests/gates，
tests/unit 不在它的范围内，`pytest tests/unit -q` 仍退 0。
"""

import importlib

import pytest

from agenerp.site import ADMIN_PASSWORD_ENV, API_KEY_ENV, API_SECRET_ENV, SiteError
from agenerp.snapshot import Snapshot

# 已实现、有真实行为的契约面。
IMPLEMENTED: list[str] = [
    "agenerp.pack:normalize",
    "agenerp.snapshot:capture",
    "agenerp.snapshot:diff",
]

# 签名已定稿、行为未实现（调用即 NotImplementedError）的契约面。
NOT_YET_IMPLEMENTED: list[str] = [
    "agenerp.pack:export_customizations",
    "agenerp.pack:apply_pack",
    "agenerp.snapshot:schema_drift",
]

# 每个契约面的一组合法调用参数，逐字对齐 tests/gates/ 里的调用处。
CALL_ARGS: dict[str, tuple[tuple, dict]] = {
    "agenerp.pack:normalize": (({"custom_fields": []},), {}),
    "agenerp.pack:export_customizations": ((), {"doctype": "Item", "into": "/nonexistent"}),
    "agenerp.pack:apply_pack": (("/nonexistent",), {"site": "gate.invalid"}),
    "agenerp.snapshot:capture": ((), {"scope": "doctypes"}),
    "agenerp.snapshot:diff": ((Snapshot(scope="doctypes"), Snapshot(scope="doctypes")), {}),
    "agenerp.snapshot:schema_drift": ((), {"doctype": "Item"}),
}


# 「未实现」不等于「一定抛 NotImplementedError」。`apply_pack` 是**委派链的入口**，
# 不是叶子：工作项 4 的 B 半落地后，它在离线环境里先撞上站点侧——没有活站点、没有凭据，
# `SiteSnapshotSource.read` 拒绝伪装成功而抛 `SiteError`，根本走不到工作项 6 的 `execute_plan`。
# 把它的期待硬写成 NotImplementedError 等于要求站点侧降级返回空，那正是本仓明令禁止的假判据。
# 维护方式不变：函数真正实现之后把名字搬进 IMPLEMENTED，并同步删掉这里的条目。
EXPECTED_RED: dict[str, type[Exception]] = {
    "agenerp.pack:apply_pack": SiteError,
}


def _resolve(name: str):
    module_name, _, attr = name.partition(":")
    return getattr(importlib.import_module(module_name), attr)


@pytest.mark.parametrize("name", IMPLEMENTED + NOT_YET_IMPLEMENTED)
def test_contract_surface_exists_and_is_callable(name):
    assert callable(_resolve(name)), f"{name} 存在但不可调用"


@pytest.mark.parametrize("name", NOT_YET_IMPLEMENTED)
def test_unimplemented_surface_raises_not_implemented(name, monkeypatch):
    """未实现的契约面调用即红，且红在**被登记过的那种失败**上，不是静默返回空。"""
    for env in (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV):
        monkeypatch.delenv(env, raising=False)
    args, kwargs = CALL_ARGS[name]
    with pytest.raises(EXPECTED_RED.get(name, NotImplementedError)):
        _resolve(name)(*args, **kwargs)
