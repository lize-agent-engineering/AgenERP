"""角色的日常视图 —— P2.2 路线 C 的分母。

人 2026-08-27 选定路线 **C · 按角色做到 100%**：不重写 Desk（`system-baseline.md`
§3.2 已判那条走不通），而是把「100% 完备」的**分母**从「全部 1000+ DocType」
换成「**这个角色每天碰的那几个**」。

本模块就是那个分母的定义。**它先于渲染器实现提交**（plan §2.1 的 R1 靠这个顺序成立）：
若允许事后调整视图定义，「落回 = 0」这条验收就退化成「我挑了一组不会落回的字段」。

## 车间工人

`agenerp/seedusers.py:30-39` 在站点上建的真实受限身份：
`worker@hrd.example.com`，**仅可读 `Work Order` / `Stock Entry` / `Item`**，
权限由 `Custom DocPerm` 强制。⚠️ **不得为了让渲染器好做而放宽它。**

## ✅ 定义已经落成 git 文件（P2.4 欠账，2026-08-28 了结）

**这几份视图不再硬编码在 Python 里** —— 它们住在 `agenerp/dsl/views/*.json`，
一个视图一个文件，用**视图 DSL 自己的线格式**（`agenerp/dsl/wire.py`）写成。
本模块只负责**读**它们。

⇒ 「一句话改老板首页 → `git diff` 看得见 → `git revert` 撤得回」这条链
（`00-GOALS.md` §2 的 **S3** 前三段）对它们**真的成立**，不再是一句设想。

⚠️ **这一版仍然只覆盖车间工人一个角色**（`ROLE_HOMES` 只有一条）。
⚠️ **P2.0 判的「产物落 AgenERP 自有表」这一半仍然欠着**：今天定义只在 git 里，
**没有落进站点的表**。后果是 S3 的第四段「同步到另一站点**生效**」对视图这一层
**不成立** —— 第二个站点上没有服务进程、也没有那张表。
照 P1.2 会话 DocType 的既定形态（`module-boundaries.md` §449 的方案 B）：
**DocType 声明落 git、建表是人的动作**。那一步没做，这句话写在这里，
免得「视图落库」也悄悄变成「反正 git 里有」。
"""

from __future__ import annotations

import json
import pathlib

from agenerp.dsl.blocks import View
from agenerp.dsl.wire import WireError, view_from_json

WORKER_ROLE = "车间工人"
WORKER_DOCTYPES: tuple[str, ...] = ("Work Order", "Stock Entry", "Item")


VIEW_DIR = pathlib.Path(__file__).resolve().parent / "views"


def load_views(directory: pathlib.Path | None = None) -> tuple[View, ...]:
    """从 `<directory>/*.json` 读出全部视图，按文件名排序。

    🔴 **坏文件要响，不许跳过。** 一个「读不懂就跳过」的加载器，会让
    「首页少了一块」长得像「本来就没有这一块」—— 而那正是 P2.6 的
    `test_no_empty_workspace` 在守的东西的上游。

    🔴 **一个视图都没读到 = 报错，不是「没有视图」。** 目录空了 / 路径给错了
    与「这个角色确实没有视图」是两件事；合并成后者，首页会变成一片空白而没人报错。
    与 `agenerp/dsl/schema.py` 那条「空的 `SchemaView` 不是『别查了』」同源。
    """
    target = directory if directory is not None else VIEW_DIR
    files = sorted(target.glob("*.json"))
    if not files:
        raise ViewDefinitionError(
            f"{target} 下一个视图定义都没有 —— 这与「这个角色没有视图」不是一回事，"
            "多半是目录空了或路径给错了。空首页必须来自一个显式的决定，不能来自一次读空。"
        )
    views: list[View] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            views.append(view_from_json(payload))
        except (OSError, ValueError, WireError) as exc:
            raise ViewDefinitionError(f"读不了视图定义 {path.name}：{exc}") from exc
    return tuple(views)


class ViewDefinitionError(ValueError):
    """视图定义文件读不了。**不降级成「少一个视图」** —— 见 `load_views` 的 docstring。"""


WORKER_DAILY_VIEWS: tuple[View, ...] = load_views()

#: 名字 → 视图。`ROLE_HOMES` 与 `serve` 都按名字查。
VIEWS_BY_NAME: dict[str, View] = {view.name: view for view in WORKER_DAILY_VIEWS}

# 车间工人的首页视图名。**写常量不写下标** —— 下标会在文件名排序变化时静默串页。
WORKER_HOME_VIEW = "worker-work-orders"


# ── 角色 → 首页（P2.6）─────────────────────────────────────────────────────

# **封闭映射**，规则面（硬约束 ③ / D-15）：这个人该看哪一页，不问模型。
# `system-baseline.md` §4 逐字：「②③ 共用一套前端，差别在渲染哪套视图 DSL、
# **默认落在哪个首页**」。
ROLE_HOMES: tuple[tuple[str, str], ...] = (
    (WORKER_ROLE, WORKER_HOME_VIEW),
)


def home_for_roles(
    roles: "tuple[str, ...] | list[str]",
    table: "tuple[tuple[str, str], ...] | None" = None,
) -> tuple[str, str] | None:
    """这个人的首页视图。**认不出就回 `None`，不给一个默认页。**

    ⚠️ **为什么不兜底到某一页**：给一个不属于他的首页，用户会看到一片
    「你看不到这个」——那比落回 Desk 糟得多，后者他至少还能干活。
    fail-closed 的方向在这里是「**不给**」，不是「随便给一个」。

    ⚠️ 顺序是 `ROLE_HOMES` 里的顺序，不是传入 `roles` 的顺序 ——
    一个人有多个角色时，**首页由本表的优先级决定**，而不是由站点返回顺序决定
    （后者是不稳定的，会让同一个人今天落这页、明天落那页）。

    ⚠️ `table` 可注入，**只为判据**：`ROLE_HOMES` 今天只有一条，
    而「按表的优先级挑」这件事**在只有一条时是恒真的** —— 判据会变成空壳。
    P2.6 的变异 M3（把挑法改成按站点返回顺序）第一轮**没见血**，就是被这个放过去的。
    产品路径一律走默认值。
    """
    owned = set(roles or ())
    for role, view_name in (table if table is not None else ROLE_HOMES):
        if role in owned:
            return role, view_name
    return None
