"""视图 DSL v0（P2.1）· 五种只读块的声明格式、两层校验器、落回 Desk 的规则面判定。

形状照 `agenerp/contracts.py`：**纯 Python 声明，取值封闭，校验器对注入进来的数据
结构求值、本层不连任何站点**。理由与契约层同一条：CI 的 `gates-l1` 只
`pip install pytest`，任何第三方依赖都会红在缺依赖上；而「不连站点」正是
「可独立测试」得以成立的机制。

**载体已由 P2.0 定死**：视图产物落 AgenERP 自己的表，**不落标准 `Workspace`**。
Workspace 会被 app 升级整条 `delete_doc` + 重插，只有 `is_hidden` 幸存
（`docs/architecture/module-boundaries.md` §11.4 端到端实测）。
⇒ 本模块的声明格式**刻意不是** Workspace fixture 的形状。

三个文件各管一件事：

- `blocks.py`   声明格式（`View` / `Block`），取值封闭
- `schema.py`   schema 视图 —— 校验器问「这个字段存在吗」的那个对象
- `validate.py` 两层校验器（L1 结构 / L2 字段存在性）
- `fallback.py` 「未支持的一律落回 Desk」，**规则面，无模型调用**（D-15）
- `wire.py`     线格式（JSON ↔ `View`），**只解析形状不判对错**
"""

from agenerp.dsl.blocks import BLOCK_TYPES, Block, View
from agenerp.dsl.fallback import RenderPlan, plan_render
from agenerp.dsl.schema import SchemaView
from agenerp.dsl.wire import WireError, view_from_json, view_from_text, view_to_json
from agenerp.dsl.validate import DslError, SchemaUnavailable, ValidationResult, validate

__all__ = [
    "BLOCK_TYPES",
    "Block",
    "DslError",
    "RenderPlan",
    "SchemaUnavailable",
    "SchemaView",
    "ValidationResult",
    "View",
    "WireError",
    "view_from_json",
    "view_from_text",
    "view_to_json",
    "plan_render",
    "validate",
]
