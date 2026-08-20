"""定制包（customization pack）的导出、规范化与 apply。

此刻只有**签名**，没有行为：函数体一律 raise NotImplementedError，
让门禁红在「实现还不存在」而不是红在「import 失败」——与 tests/gates/conftest.py
已确立的约定一致。签名逐字对齐 tests/gates/ 里的调用处，实现到位时不需要改调用方。
"""

from typing import Any

_TODO = "尚未实现 —— 见 docs/backlog/p0-foundation-roadmap.md 的工作项对照表"


def normalize(export: dict[str, Any]) -> dict[str, Any]:
    """把一次原始定制导出规范化成可 diff 的确定性结构。

    剥掉 modified / creation / owner / _comments 等易变字段，并稳定排序。
    """
    raise NotImplementedError(f"normalize {_TODO}（工作项 1 · 定制包规范化器）")


def export_customizations(doctype: str, into: str) -> None:
    """把某个 DocType 的定制从活站点导出到定制包工作副本 `into`。"""
    raise NotImplementedError(
        f"export_customizations {_TODO}（工作项 6 · 定制包往返验证）"
    )


def apply_pack(path: str, site: str) -> None:
    """把定制包 `path` 应用到站点 `site`，**含对差集执行删除**。"""
    raise NotImplementedError(f"apply_pack {_TODO}（工作项 5 · 差集 apply 引擎）")
