"""定制包（customization pack）的导出、规范化与 apply。

`normalize` 已实现（工作项 1）：纯函数、零第三方依赖、不改入参。
其余函数仍只有**签名**没有行为，函数体 raise NotImplementedError，
让门禁红在「实现还不存在」而不是红在「import 失败」——与 tests/gates/conftest.py
已确立的约定一致。签名逐字对齐 tests/gates/ 里的调用处，实现到位时不需要改调用方。
"""

from typing import Any

_TODO = "尚未实现 —— 见 docs/backlog/p0-foundation-roadmap.md 的工作项对照表"

# 易变字段的判定口径：按**键名子串**黑名单剥离，不按值猜。
# 新增易变键时改这里——这是唯一落点，行为覆盖在 tests/unit/test_pack_normalize.py。
VOLATILE_KEY_SUBSTRINGS: tuple[str, ...] = ("modified", "creation", "owner", "_comments")

# 列表条目的稳定身份键（Frappe 定制导出里 custom_fields / property_setters 都用它）。
_IDENTITY_KEY = "fieldname"


def normalize(export: dict[str, Any]) -> dict[str, Any]:
    """把一次原始定制导出规范化成可 diff 的确定性结构。

    剥掉 modified / creation / owner / _comments 等易变字段，并稳定排序。

    纯函数：返回全新对象，绝不就地修改入参（调用方的两次快照必须互不污染）。
    幂等：``normalize(normalize(x)) == normalize(x)``。
    """
    return _normalize_value(export)


def _is_volatile_key(key: Any) -> bool:
    """键名**含**任一易变词即算易变（`modified_by` / `owner_id` 一并剥掉）。

    门禁断言对 `repr(normalize(...))` 做子串检查，精确键名匹配挡不住派生键。
    """
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(word in lowered for word in VOLATILE_KEY_SUBSTRINGS)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not _is_volatile_key(key)
        }
    if isinstance(value, (list, tuple)):
        items = [_normalize_value(item) for item in value]
        if items and all(isinstance(item, dict) for item in items):
            items.sort(key=_entry_sort_key)
        return items
    return value


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    """条目的稳定身份：优先 `fieldname`，缺失时退化为规范化后的表示。"""
    identity = entry.get(_IDENTITY_KEY)
    return ("" if identity is None else str(identity), repr(entry))


def export_customizations(doctype: str, into: str) -> None:
    """把某个 DocType 的定制从活站点导出到定制包工作副本 `into`。"""
    raise NotImplementedError(
        f"export_customizations {_TODO}（工作项 6 · 定制包往返验证）"
    )


def apply_pack(path: str, site: str) -> None:
    """把定制包 `path` 应用到站点 `site`，**含对差集执行删除**。"""
    raise NotImplementedError(f"apply_pack {_TODO}（工作项 5 · 差集 apply 引擎）")
