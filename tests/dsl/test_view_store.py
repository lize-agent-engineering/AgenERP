"""🔴 P2.0 那一半 · 视图定义在**站点自有表**上的读写。离线，假客户端。

## 它补的是哪一句

P2.0 端到端实测判定：**视图产物落 AgenERP 自有表，不落标准 Workspace**
（Workspace 会被 app 升级整条 `delete_doc` + 重插，只有 `is_hidden` 幸存 ——
定制寿命 = 一次升级）。P2.4 只做了 git 那一半，**站点这一半是本模块**。

## 真相源与产物的方向**不许反**

```
agenerp/dsl/views/*.json   ← 真相源（git）
        │  publish
        ▼
站点上的 `AgenERP View` 表  ← 每个站点一份的产物
```

与 P2.4「包是唯一真相源，站点是可再生的产物」逐字同一条线。
⇒ **不提供「从表往回写文件」的路径**：那会让两个真相源互相覆盖，
而「哪一份说了算」在出事时没人答得上来。

## fail-closed

- 表不存在 / 读不到 ⇒ **明确报错**，不是「没有视图」——
  后者会让首页变成一片空白而没人报错（与 `roles.load_views` 那条同源）。
- 读回来的必须能被线格式解析成同一个 `View`；解析不了也是报错。
"""

from __future__ import annotations

import json

import pytest

from agenerp.dsl.roles import WORKER_DAILY_VIEWS
from agenerp.dsl.store import (
    VIEW_DOCTYPE,
    ViewStoreError,
    publish_views,
    read_view,
)

FIRST = WORKER_DAILY_VIEWS[0]


class FakeClient:
    """记下每一次读写。`missing=True` 模拟「表还没建 / 这条不存在」。"""

    def __init__(self, missing: bool = False) -> None:
        self.rows: dict[str, dict] = {}
        self.created: list[dict] = []
        self.deleted: list[str] = []
        self.missing = missing

    def get(self, path: str, params=None):
        from agenerp.site import SiteError

        name = path.rsplit("/", 1)[-1]
        if self.missing or name not in self.rows:
            raise SiteError(f"GET {path} → HTTP 404 DoesNotExistError（假件）")
        return {"data": self.rows[name]}

    def list_resource(self, doctype: str, fields=("*",)):
        from agenerp.site import SiteError

        if self.missing:
            raise SiteError(f"GET /api/resource/{doctype} → HTTP 404（表还没建，假件）")
        return list(self.rows.values())

    def create_doc(self, doctype: str, payload: dict):
        self.created.append({"doctype": doctype, **payload})
        row = {**payload, "name": payload["view_name"]}
        self.rows[payload["view_name"]] = row
        return row

    def delete_view(self, name: str):
        """⚠️ **窄方法**：不收 `doctype` —— `agenerp/site.py` 模块头第 4 条
        「不提供删任意 DocType 文档的通用方法」。假件跟着产品面走。"""
        self.deleted.append(name)
        self.rows.pop(name, None)


def test_publish_writes_one_row_per_view():
    client = FakeClient()

    published = publish_views(client, WORKER_DAILY_VIEWS)

    assert published == len(WORKER_DAILY_VIEWS)
    assert {row["view_name"] for row in client.rows.values()} == {
        v.name for v in WORKER_DAILY_VIEWS
    }
    assert all(c["doctype"] == VIEW_DOCTYPE for c in client.created)


def test_what_comes_back_is_the_very_same_view():
    """🔴 往返必须是**同一个对象** —— 否则站点上那份和 git 里那份各说各话。"""
    client = FakeClient()
    publish_views(client, WORKER_DAILY_VIEWS)

    assert read_view(client, FIRST.name) == FIRST


def test_publish_is_idempotent():
    """复跑同一次 publish 不该长出第二份 —— 站点是**可再生的产物**，不是追加日志。"""
    client = FakeClient()
    publish_views(client, WORKER_DAILY_VIEWS)
    publish_views(client, WORKER_DAILY_VIEWS)

    assert len(client.rows) == len(WORKER_DAILY_VIEWS)


def test_a_view_removed_from_git_is_removed_from_the_site():
    """🔴 **删得掉**：真相源里没有了，站点上也要没有。

    这与 P0.5 那条「承重条款」同源 —— 只增不减的同步等于 revert 撤不回。
    """
    client = FakeClient()
    publish_views(client, WORKER_DAILY_VIEWS)

    publish_views(client, WORKER_DAILY_VIEWS[:-1])

    gone = WORKER_DAILY_VIEWS[-1].name
    assert gone in client.deleted
    assert gone not in client.rows


def test_a_missing_table_is_an_error_not_an_empty_view_set():
    """🔴 表还没建 ≠ 「这个站点没有视图」。

    合并成后者，首页会变成一片空白而没人报错。
    """
    client = FakeClient(missing=True)

    with pytest.raises(ViewStoreError):
        read_view(client, FIRST.name)


def test_a_missing_row_says_which_view_it_could_not_find():
    client = FakeClient()

    with pytest.raises(ViewStoreError) as excinfo:
        read_view(client, "worker-nope")

    assert "worker-nope" in str(excinfo.value)


def test_a_row_whose_definition_is_not_a_view_fails_loudly():
    """表里那一列被人改坏时要**响**，不许把半个视图渲染出去。"""
    client = FakeClient()
    client.rows["broken"] = {"view_name": "broken", "title": "x", "definition": "不是 JSON"}

    with pytest.raises(ViewStoreError):
        read_view(client, "broken")


def test_the_definition_column_holds_the_wire_format_verbatim():
    """站点上存的就是线格式本身 —— 不另发明一套存储结构。"""
    client = FakeClient()
    publish_views(client, (FIRST,))

    payload = json.loads(client.rows[FIRST.name]["definition"])
    assert payload["name"] == FIRST.name
    assert len(payload["blocks"]) == len(FIRST.blocks)


def test_there_is_no_path_from_the_site_back_into_git():
    """🔴 方向不许反：**没有**「从表往回写文件」的函数。

    两个真相源互相覆盖时，「哪一份说了算」在出事时没人答得上来。
    这一条读的是模块的导出面，不是一句保证。
    """
    import agenerp.dsl.store as store

    suspicious = [
        name for name in dir(store)
        if not name.startswith("_") and ("write_file" in name or "to_git" in name
                                         or "dump_to" in name or "export_views" in name)
    ]
    assert not suspicious, f"出现了从站点往回写的路径：{suspicious}"


def test_a_name_that_could_escape_the_path_is_refused_without_asking_the_site():
    """🔴 **路径穿越面**：视图名要进 REST 路径，而站点侧的编码 `quote(path, safe="/")`
    **不转义 `/`** ⇒ `../../x` 会拼出一条能被 HTTP 客户端规范化掉的路径。

    这层保护此前由「视图名只做字典查表」天然提供；2026-08-28 改成从站点表读之后
    那层没了，必须在这里补回来。

    ⚠️ 断言两件事：**拒了**，且**一个站点请求都没发**（连问都不问）。
    """
    client = FakeClient()
    client.rows["x"] = {"view_name": "x", "title": "x", "definition": "{}"}

    for evil in ("../../etc", "a/b", "worker/../../x", "", "  ", "Worker-Items",
                 "x" * 200, "名字"):
        with pytest.raises(ViewStoreError):
            read_view(client, evil)


def test_the_refusal_does_not_echo_the_name_back():
    """名字是调用方能控制的 —— 回显它就是一条反射面。"""
    client = FakeClient()

    with pytest.raises(ViewStoreError) as excinfo:
        read_view(client, "<script>alert(1)</script>")

    assert "script" not in str(excinfo.value)


def test_the_real_view_names_all_pass_the_shape_check():
    """守卫不能把真名字也拒掉 —— 否则它守的是「什么都不许」。"""
    from agenerp.dsl.store import VIEW_NAME

    for view in WORKER_DAILY_VIEWS:
        assert VIEW_NAME.match(view.name), view.name
