"""视图 schema 的**静态快照**：离线生成，服务端只读。

## 为什么是快照，而不是服务端现取

人 2026-08-27 裁定：**「schema 可以全部共享，但操作一定要按调用者的权限来。」**
两句话各自落到一处：

- **schema 全局共享** ⇒ 视图计划端点「不认人」是对的，它回的是**视图定义**，
  不是业务数据。既然人人可见，就没必要按调用者取，也就没必要认人。
- **操作按调用者权限** ⇒ 业务数据由浏览器**同源直打 Frappe、带自己的 sid**，
  权限由后端强制。服务端不代取一行业务数据。

而 `agenerp/serve/**` 被 `tests/unit/test_explain_service.py` 判据⑧ 钉死了两条：
**零凭据零件**，且**不许自己构造 `SiteClient`**（默认工厂必须就是 `client_from_sid`）。
用意是「**服务端永远只以调用者的身份对站点说话**」。

⇒ 结论：**服务端根本不该去取 schema。** 取这件事挪到离线，产物是一份 JSON，
服务端只 `json.load`。这样判据⑧ 一条都不用绕，
也正对应 `docs/design/context-and-memory.md` §8.2 第 ④ 层「静态/半静态」。

## 🔴 这么做的代价，照实记

**快照会过期。** 站点上加了字段而快照没更新时，
`plan_render()` 会把那个字段判成「不存在」⇒ 落回卡片，**不会画错**（fail-closed）。
反过来更值得警惕：**站点上删了字段而快照还留着** ⇒ 服务端以为它在、放行渲染，
而浏览器真取数时拿不到值。⇒ **改了 DocType 就要重新生成快照**，
生成命令见下方 `main()`。这条**不是自动的**，是运维步骤。

⚠️ 本模块**故意不被 `agenerp/serve/**` import** —— 它拿的是服务端凭据，
一旦被 serve 引用，判据⑧ 那条「不许有第二条造客户端的路」就等于被绕开了。
服务端只认那份 JSON 文件。
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

DEFAULT_PATH = pathlib.Path(__file__).resolve().parent / "schema" / "view-schema.json"

# 快照里只留这四项 —— **够 `SchemaView` 用，且一个字节的业务数据都不带**。
# 特意**不存 rowcount**：那会泄露站点上有多少数据，而仓库是公开的。
KEPT = ("doctype", "fieldname", "fieldtype", "options")


def view_doctypes() -> tuple[str, ...]:
    """快照要覆盖哪些 DocType：**视图里出现过的，加上它们声明的子表**。

    与服务端原来那段 `wanted` 的算法逐字相同 —— 口径不许有两套，
    否则「快照里有没有」与「视图要不要」会悄悄错开。
    """
    # ⚠️ 从 `dsl.roles` 取，**不从 `serve.app` 取**：那边的 `VIEWS_BY_NAME` 是同一份
    # 数据的派生，但引它就把生成器绑到了服务面上 —— 而这个模块**刻意不与 serve 相互引用**。
    from agenerp.dsl.roles import WORKER_DAILY_VIEWS

    wanted: set[str] = set()
    for view in WORKER_DAILY_VIEWS:
        for block in view.blocks:
            if block.doctype:
                wanted.add(block.doctype)
            for _table_field, child_doctype, _names in block.child_fields:
                wanted.add(child_doctype)
    return tuple(sorted(wanted))


def build_from_site(site: str) -> dict[str, Any]:
    """从活站点取一份快照。**只在离线生成时调用，服务端永不走这里。**"""
    from agenerp.site import client_from_env

    client = client_from_env(site)
    rows: list[dict] = []
    for doctype in view_doctypes():
        meta = client.get(f"/api/resource/DocType/{doctype}")
        for field_row in (meta.get("data") or {}).get("fields") or []:
            if not field_row.get("fieldname"):
                continue
            rows.append(
                {
                    "doctype": doctype,
                    "fieldname": field_row.get("fieldname"),
                    "fieldtype": field_row.get("fieldtype"),
                    "options": field_row.get("options"),
                }
            )
    if not rows:
        raise RuntimeError(f"{site} 上一个字段都没取到 —— 不写空快照（空快照 = 静默全落回）")
    return {"site": site, "doctypes": list(view_doctypes()), "fields": rows}


def load(path: pathlib.Path | str | None = None):
    """读快照 → `SchemaView`。**读不到就回 `None`，绝不返回空 schema。**

    区别是要命的：`None` 让 `validate()` 抛 `SchemaUnavailable`（「验不了的不算过」），
    而一个空 `SchemaView` 会让每个字段都判成「不存在」—— 那是**静默全落回**，
    看起来像「站点上什么都没有」，而不是「我读不到 schema」。
    """
    from agenerp.dsl.schema import SchemaView

    target = pathlib.Path(path) if path else DEFAULT_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        rows = payload["fields"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not rows:
        return None
    return SchemaView.from_meta_rows(rows)


def main() -> None:
    """重新生成快照。**改了 DocType 就跑一次** —— 见模块头「代价」。

        AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=… \\
            python3 -m agenerp.schema_snapshot
    """
    import os

    site = os.environ.get("AGENERP_SITE") or ""
    if not site:
        raise SystemExit("AGENERP_SITE 没设 —— 不猜站点")
    payload = build_from_site(site)
    DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(  # noqa: T201
        f"→ {DEFAULT_PATH}（{len(payload['doctypes'])} 个 DocType，"
        f"{len(payload['fields'])} 个字段）"
    )


if __name__ == "__main__":
    main()
