"""P2.2 · 渲染器的**离线**判据：静态约束 + `/agenerp/view` 端点。

这一层不开浏览器。它守的是「**改坏了会不会红**」里那些**读源码就能判**的部分：

- `render.js` 里 HTML 注入那一族 sink 是零命中
- 附件 URL 的 scheme 白名单封闭且与 Python 侧一字对应
- `/agenerp/view` 取不到 schema 时**不回一个乐观计划**

真浏览器那一层在 `tests/render/`（WBS 点名的验收路径）。
**两层各守各的**：这里判源码，那里判画出来的东西。

⚠️ 住在 `tests/unit/` 是刻意的 —— 这一轮 `pytest tests/unit -q` 每次都跑，
改坏了当天就看得见；住进 `tests/render/` 就只有跑活体那一轮才看得见了。
（形态与 `tests/unit/test_desk_sidebar_static.py` 同族。）
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from agenerp.dsl.fallback import ALLOWED_ATTACHMENT_SCHEMES
from agenerp.dsl.schema import SchemaView
from agenerp.serve.app import (
    RENDER_ASSET_FILENAME,
    RENDER_ASSET_PATH,
    SERVED_PATHS,
    VIEW_PLAN_PATH,
    ServiceError,
    view_plan,
)

_ASSET = pathlib.Path(__file__).resolve().parents[2] / "agenerp/serve/assets" / RENDER_ASSET_FILENAME
_SRC = _ASSET.read_text(encoding="utf-8")

_FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/site-schema-subset.json"
_CHILD = pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/child-tables.json"


@pytest.fixture
def site_schema() -> SchemaView:
    fields = json.loads(_FIXTURE.read_text(encoding="utf-8"))["fields"]
    raw = json.loads(_CHILD.read_text(encoding="utf-8"))
    children = {(k.split(".", 1)[0], k.split(".", 1)[1]): v for k, v in raw.items()}
    return SchemaView(fields, children)


# ---------------------------------------------------------------- 静态约束


# **扫使用形态，不扫提及。** 注释里点名这些 sink 是应该的（约束就写在那儿），
# 拿 `"innerHTML" in src` 去判会把「写着不许用」也判成「用了」——
# 那样判据要么逼人删掉注释，要么被加一句豁免绕过去。两条都比现在差。
_SINK_USES = (
    r"\.innerHTML\s*=",
    r"\.outerHTML\s*=",
    r"\.insertAdjacentHTML\s*\(",
    r"document\.write\s*\(",
    r"\.insertAdjacentElement\s*\(\s*['\"]",  # 不是注入面，但绕过 el() 这一层
)


@pytest.mark.parametrize("pattern", _SINK_USES)
def test_the_renderer_never_uses_an_html_injection_sink(pattern: str):
    """约束 1（`module-boundaries.md` §7.23）：建 DOM 只走 `textContent`。

    失败意味着：渲染器把一段**站点上用户可写的文本**当 HTML 解析了。
    """
    hits = [m.group(0) for m in re.finditer(pattern, _SRC)]
    assert not hits, f"render.js 用了 HTML 注入 sink：{hits}"


def test_the_renderer_does_not_reparse_html_to_strip_tags():
    """剥标签**不许**用「塞进一个临时节点再取 textContent」那一招。

    那一招会真的解析一次 HTML —— `<img src=x onerror=...>` 在解析那一刻就跑了，
    即便你随后只取纯文本。这是个很常见的假安全。
    """
    assert "createElement(\"div\")" not in _SRC or ".innerHTML" not in _SRC
    assert "DOMParser" not in _SRC


def test_the_url_scheme_allowlist_is_closed_and_matches_the_python_side():
    """约束：附件 URL 只放行站内相对路径与 https，**两侧一字对应**。

    两份白名单各写各的，迟早会错开；错开的表现是「Python 说画得了、JS 放行了别的」。
    """
    match = re.search(r"var SAFE_URL_PREFIXES = \[(.*?)\];", _SRC, re.S)
    assert match, "render.js 里找不到 SAFE_URL_PREFIXES"
    in_js = [p.strip().strip('"').strip("'") for p in match.group(1).split(",") if p.strip()]
    assert tuple(in_js) == tuple(ALLOWED_ATTACHMENT_SCHEMES), (
        f"JS 的白名单 {in_js} 与 Python 的 {list(ALLOWED_ATTACHMENT_SCHEMES)} 对不上"
    )


def test_protocol_relative_urls_are_not_treated_as_same_site():
    """`//evil.example` 是协议相对 URL —— 它等于放行任意 host。

    一个只判「以 / 开头」的实现会放它过去。这条判据钉住那个区别。
    """
    assert 'v.charAt(1) !== "/"' in _SRC, "render.js 没有把 //host 与 /path 区分开"


def test_data_is_fetched_same_origin_with_the_browsers_own_session():
    """约束 2：权限由后端强制。渲染器带浏览器自己的 sid，不自己造凭据。"""
    assert 'credentials: "same-origin"' in _SRC
    for forbidden in ("Authorization", "api_key", "api_secret", "token"):
        assert forbidden not in _SRC, f"render.js 里出现了凭据字样：{forbidden}"


def test_the_renderer_asset_is_actually_served():
    assert RENDER_ASSET_PATH in SERVED_PATHS
    assert VIEW_PLAN_PATH in SERVED_PATHS
    assert "/" not in RENDER_ASSET_FILENAME


# ---------------------------------------------------------------- `/agenerp/view`


def test_view_plan_returns_a_renderable_plan_for_a_known_view(site_schema):
    payload = view_plan("worker-items", site_schema)
    assert payload["view"] == "worker-items"
    assert payload["fallbacks"] == []
    assert len(payload["blocks"]) == 2
    # 富文本那一条必须出现在 degraded 里 —— 用户得知道自己少看了什么。
    assert any(d["field"] == "Item.description" for d in payload["degraded"])


def test_view_plan_carries_the_fieldtypes_the_renderer_needs(site_schema):
    payload = view_plan("worker-items", site_schema)
    assert payload["fieldtypes"]["Item.description"] == "Text Editor"
    assert payload["fieldtypes"]["Item.image"] == "Attach Image"
    # 子表字段的类型也要带上 —— 子表里的 Attach 是真实存在的一格。
    plan = view_plan("worker-stock-entries", site_schema)
    assert plan["fieldtypes"]["Stock Entry Detail.image"] == "Attach"


def test_view_plan_without_a_schema_refuses_instead_of_being_optimistic():
    """🔴 与 `agenerp/dsl/validate.py` 同一条：**验不了的东西不许算过。**

    取不到 schema 时回一个「都画得了」的乐观计划，等于让渲染器去画一堆
    没人核对过存在性的字段 —— 而那正是 P2 硬约束 ④ 要挡的。
    """
    with pytest.raises(ServiceError) as caught:
        view_plan("worker-items", None)
    assert caught.value.status == 503


def test_an_unknown_view_name_is_404_and_does_not_echo_the_name():
    """视图名是调用方能控制的。回显它就是一条反射面。"""
    with pytest.raises(ServiceError) as caught:
        view_plan("<script>alert(1)</script>", None)
    assert caught.value.status == 404
    assert "script" not in str(caught.value)


def test_the_view_name_only_ever_hits_a_dict_lookup():
    """视图名不许参与路径拼接，也不许做前缀匹配。

    判法：把 `VIEWS_BY_NAME.get(name)` 那棵子树从 AST 里摘掉，
    **剩下的地方一次都不许再读 `name`**。用 AST 而不是逐行 grep ——
    行匹配会被函数签名、注释、字符串各绊一次，而每绊一次都要往判据里加一条豁免，
    加着加着这条判据就只剩壳了。
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(view_plan)))

    lookups = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "VIEWS_BY_NAME"
    ]
    assert len(lookups) == 1, f"期望恰好一次 VIEWS_BY_NAME.get(...)，实际 {len(lookups)}"
    inside_lookup = {id(node) for node in ast.walk(lookups[0])}

    stray = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "name"
        and isinstance(node.ctx, ast.Load)
        and id(node) not in inside_lookup
    ]
    assert not stray, (
        f"view_plan 里 name 在查表之外被读了 {len(stray)} 次 —— "
        "第一次出现在第 " + str(stray[0].lineno) + " 行"
    )
