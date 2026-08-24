"""行业包（P1.6）—— **包在盘上、校验器判得动它**。落点节是
`docs/architecture/module-boundaries.md` §7.10。

⚠️ **本包不把行业包接进 `rule.lookup`。** `agenerp/tools/queries.py` 的
`rule_lookup` 仍然指名报错，理由变了但结论没变（见该函数 docstring 与
`docs/masterplan/STATE.md` §3 的 needs-human）：接线会让一条 L2 门禁由绿转红，
复绿只能改裁判或改它委派的断言体，两者都在红线内。**接线由人裁定。**

CLI：`python3 -m agenerp.packs validate --pack discrete`。
"""

from __future__ import annotations

from agenerp.packs.loader import (
    DISCRETE,
    PACK_FILE,
    PACK_KEYS,
    Pack,
    PackLoadError,
    PackNotFound,
    available_packs,
    describe_failure,
    load_pack,
    packs_root,
    validate_pack,
)

__all__ = (
    "DISCRETE",
    "PACK_FILE",
    "PACK_KEYS",
    "Pack",
    "PackLoadError",
    "PackNotFound",
    "available_packs",
    "describe_failure",
    "load_pack",
    "packs_root",
    "validate_pack",
)
