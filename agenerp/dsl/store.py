"""视图定义在**站点自有表**上的读写。P2.0 判的「产物落自有表」那一半。

## 为什么是自有表，不是 Workspace

P2.0 的 Spike 11 端到端实测：`Workspace` 会被 app 升级**整条 `delete_doc` + 重插**，
只有 `is_hidden` 幸存 ⇒ **定制寿命 = 一次升级**。
声明在 `agenerp/dsl/doctype/agenerp_view.json`（`custom: 1`）。

## 方向不许反

```
agenerp/dsl/views/*.json   ← 真相源（git）
        │  publish_views
        ▼
站点上的 `AgenERP View` 表  ← 每个站点一份的产物
```

与 P2.4「包是唯一真相源，站点是可再生的产物」逐字同一条线。
🔴 **本模块刻意不提供「从表往回写文件」的路径** —— 两个真相源互相覆盖时，
「哪一份说了算」在出事时没人答得上来。判据 `test_there_is_no_path_from_the_site_back_into_git`
读的是本模块的导出面，不是一句保证。

## fail-closed：**读不到 ≠ 没有视图**

表还没建、行不存在、那一列被改坏 —— 一律抛 `ViewStoreError`。
合并成「这个站点没有视图」会让首页变成一片空白而没人报错
（与 `agenerp/dsl/roles.py:load_views` 和 `agenerp/dsl/schema.py` 那两条同源）。
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Sequence

from agenerp.dsl.blocks import View
from agenerp.dsl.wire import WireError, view_from_json, view_to_json

#: 自有表的名字。声明落 `agenerp/dsl/doctype/agenerp_view.json`。
VIEW_DOCTYPE = "AgenERP View"


class ViewStoreError(RuntimeError):
    """站点上的视图定义读不了 / 写不了。**不降级成「没有视图」** —— 见模块头。"""


DECLARATION = (
    pathlib.Path(__file__).resolve().parent / "doctype" / "agenerp_view.json"
)


def ensure_table(client) -> bool:
    """在站点上建这张表。**已存在则跳过**，回「这次建了没有」。

    ⚠️ **这是对活站点的结构性改动。** P1.2 的先例（`module-boundaries.md` §449 方案 B）
    是「声明落 git、**建表交人**」；人 2026-08-28 明确授权由 loop 建
    （「授权我建」）—— **本项因此偏离那条先例，写在这里供复核。**

    🔴 **回滚只能手工做，本函数不提供**（与 P1.2 那条逐字同源）：

        docker compose exec -T backend bench --site <站点> backup   # 先备份
        # 再在 Desk 里删掉 DocType「AgenERP View」

    幂等：先查后建（不靠吞 409）—— `agenerp/site.py:create_doc` 的 docstring 逐字
    「把 409 判成『已经有了、算成功』有诱惑力，但那会让『载荷写错导致建了两份』
    与『本来就在』长得一模一样」。
    """
    from agenerp.site import RESOURCE_PATH, SiteError

    # ⚠️ **路径不要自己编码**：`agenerp/site.py` 的 `_request` 统一做 URL 编码
    #（模块头逐字：DocType 名带空格，不编码时 `http.client` 直接拒）。
    # 自己先 `%20` 一次就是**双重编码** —— 2026-08-28 实测踩到：
    # `AgenERP%2520View` 回 404 ⇒ 幂等检查把「已存在」读成「不在」⇒ 接着 409。
    try:
        client.get(f"{RESOURCE_PATH}/DocType/{VIEW_DOCTYPE}")
        return False
    except SiteError:
        pass  # 不在 ⇒ 往下建。**只有「不在」这一种情况会往下走**，别的错在 create 那步再炸。

    payload = json.loads(DECLARATION.read_text(encoding="utf-8"))
    # 站点自己算的那几项不往上传：传了会被忽略或打架，而「被静默忽略的载荷」最难查。
    for computed in ("creation", "modified", "owner", "doctype"):
        payload.pop(computed, None)
    client.create_doc("DocType", payload)
    return True


def publish_views(client, views: Sequence[View]) -> int:
    """把真相源里的视图**同步**到站点表，返回写了几条。

    🔴 **同步不是追加**：真相源里没有了的，站点上也要删掉。
    只增不减的同步等于 `git revert` 撤不回 —— 与 P0.5 那条「承重条款」同源。

    幂等：复跑同一次 publish 不长出第二份（先删后建，名字由 `view_name` 决定）。
    """
    from agenerp.site import SiteError

    wanted = {view.name: view for view in views}
    try:
        existing = {
            str(row.get("view_name") or row.get("name")): row
            for row in client.list_resource(VIEW_DOCTYPE, ("name", "view_name"))
        }
    except SiteError as exc:
        raise ViewStoreError(
            f"读不到 {VIEW_DOCTYPE} 表：{exc}\n"
            "  表还没建的话先建表 —— 「读不到」不等于「这个站点没有视图」。"
        ) from exc

    # 先删后建：`autoname: field:view_name` 让名字由内容决定，
    # 重复 create 会撞 409，而「先删再建」是这一层能做到的最简单的幂等。
    for name in sorted(set(existing) - set(wanted)):
        client.delete_view(existing[name].get("name", name))
    for name in sorted(wanted):
        if name in existing:
            client.delete_view(existing[name].get("name", name))
        view = wanted[name]
        client.create_doc(
            VIEW_DOCTYPE,
            {
                "view_name": view.name,
                "title": view.title,
                # 存**线格式本身**，不另发明一套存储结构。
                "definition": json.dumps(view_to_json(view), ensure_ascii=False),
            },
        )
    return len(wanted)


def read_view(client, name: str) -> View:
    """按名字从站点表读一个视图。

    ⚠️ `client` 由调用方给 —— `agenerp/serve/**` 传的是**按调用者 sid 造的**那个
    （判据⑧：服务端只以调用者的身份对站点说话）。本模块不自己造客户端。
    """
    from agenerp.site import RESOURCE_PATH, SiteError

    try:
        payload = client.get(f"{RESOURCE_PATH}/{VIEW_DOCTYPE}/{name}")
    except SiteError as exc:
        raise ViewStoreError(
            f"站点上读不到视图 {name!r}：{exc}\n"
            "  「读不到」不等于「没有这个视图」—— 表没建、没权限、名字错都长这样。"
        ) from exc

    row = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(row, dict) or not row.get("definition"):
        raise ViewStoreError(f"视图 {name!r} 在站点上没有 definition 那一列：{str(payload)[:200]}")
    try:
        return view_from_json(json.loads(row["definition"]))
    except (ValueError, WireError) as exc:
        raise ViewStoreError(f"视图 {name!r} 的 definition 不是一份视图：{exc}") from exc
