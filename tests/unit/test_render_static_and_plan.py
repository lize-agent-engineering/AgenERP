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
from agenerp.site import SiteError
from agenerp.serve.app import (
    HOME_PATH,
    RENDER_ASSET_FILENAME,
    RENDER_ASSET_PATH,
    SERVED_PATHS,
    VIEW_PLAN_PATH,
    ServiceError,
    build_server,
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


# ---------------------------------------------------------------- `/agenerp/home`
#
# ⚠️ **为什么这一层在本地起真服务，而不是打活栈**：
# 活栈的 `agenerp-serve` 容器挂载的是**主工作树**的 `agenerp/`（`docker inspect` 实读），
# 吃不到本分支的代码。往主工作树写会污染那儿正在跑的循环 ⇒ 不写。
# ⇒ 用 `build_server(port=0)` 在本地起一个**真服务**、发**真 HTTP** ——
# 这比打那个容器**更严格**，因为它跑的确实是本分支的代码。


class _Live:
    """在 `127.0.0.1:0` 上真起一个服务（端口由内核分配，不猜数）。形态同 `test_desk_asset_route.py`。"""

    def __init__(self, server) -> None:
        import threading

        self.server = server
        self.host, self.port = server.server_address[:2]
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.thread.start()

    def get(self, path: str, *, cookie: str | None = None):
        import http.client

        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request("GET", path, headers={"Cookie": cookie} if cookie else {})
            res = conn.getresponse()
            return res.status, json.loads(res.read() or b"{}")
        finally:
            conn.close()

    def request(self, method: str, path: str):
        import http.client

        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request(method, path)
            res = conn.getresponse()
            return res.status, json.loads(res.read() or b"{}")
        finally:
            conn.close()

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


FAKE_USER = "worker@hrd.example.com"


def _client_returning(roles):
    """一个只会答「你有哪些角色」的假站点客户端。

    ⚠️ 它**必须收得下 `sid`** —— 服务端拿不到 sid 时根本走不到这里，
    而那正是 `test_..._unauthenticated_...` 那一格要验的。
    """

    class _Client:
        """🔴 **这个假件曾经放走两个真 bug，两条都是「它比真站点宽松」造成的。**

        ① 它不检查参数 ⇒ 产品代码调 `get_roles({})` 缺 `uid`，
           真站点回 **HTTP 500 `KeyError: 'uid'`**，而这里照样返回角色。
        ② 它不区分 GET/POST ⇒ 产品代码走 `call_method`（POST），
           真站点对**浏览器会话**的 POST 要 CSRF token，回 **400 `CSRFTokenError`**。

        两条都被服务面吞成 401「未认到人」，于是 `/agenerp/home` 对**每一个真人**
        都解析不出角色，而单测全绿。⇒ 假件现在把这两条**都模拟出来**：
        再有人改回 POST、或漏掉 `uid`，这里当场红。
        """

        def call_method(self, method, params=None):  # noqa: ARG002
            raise SiteError(
                "假站点：浏览器会话的 POST 要 CSRF token（真站点实测回 400 CSRFTokenError）"
                " —— 只读身份查询请走 read_method（GET）"
            )

        def read_method(self, method, params=None):
            if isinstance(roles, Exception):
                raise roles
            if method.endswith("get_logged_user"):
                # ⚠️ 必须回**字符串**：`_resolve_identity` 拿它当 `uid` 用，
                # 回个列表的话身份解析当场判 401，而失败长得像「站点不认这个 sid」。
                return FAKE_USER
            if method.endswith("get_roles") and not (params or {}).get("uid"):
                raise SiteError(
                    "假站点：get_roles 缺 uid（真站点实测回 HTTP 500 KeyError: 'uid'）"
                )
            return roles

    def factory(*args, **kwargs):
        # ⚠️ **位置与关键字两种调法都要收得下。**
        # `client_from_sid(site, sid, *, transport)` 的前两个是位置参数，
        # 而服务面两处的调法不一致（`_resolve_identity` 用位置、旧 home 用关键字）。
        # 假件只认关键字的话，改成位置调用就会红在假件上而不是红在实现上。
        sid = kwargs.get("sid") or (args[1] if len(args) > 1 else "")
        if not sid:
            raise AssertionError("首页解析没有把 sid 传下去")
        return _Client()

    return factory


@pytest.fixture
def serve():
    started: list[_Live] = []

    def start(roles):
        server = build_server(site="unit-test-site", port=0, client_factory=_client_returning(roles))
        live = _Live(server)
        started.append(live)
        return live

    yield start
    for live in started:
        live.close()


def test_home_resolves_the_worker_role_to_their_own_view(serve):
    """H1 · 「这个人 → 哪一页」，且身份是**问站点**问出来的，不是前端说的。"""
    live = serve(["车间工人", "All"])
    status, body = live.get(HOME_PATH, cookie="sid=whatever")
    assert status == 200, body
    assert body["view"] == "worker-work-orders"
    assert body["role"] == "车间工人"


def test_home_refuses_instead_of_giving_an_empty_page_when_nobody_is_authenticated(serve):
    """🔴 H2 · 认不出人 ⇒ **落回 Desk，不回 200 + 空视图**。

    给一个不属于他的首页，用户看到的是一片「你看不到这个」——
    那比落回 Desk 糟得多，后者他至少还能干活。
    """
    live = serve(["车间工人"])
    status, body = live.get(HOME_PATH)  # 不带 Cookie
    assert status in (401, 403), body
    assert body.get("fallback") == "desk"
    assert not body.get("view"), f"未认到人却给了一个视图：{body}"


def test_a_role_with_no_home_falls_back_to_desk_rather_than_a_default_page(serve):
    """认得出人、但这个角色没配首页 ⇒ 同样落回 Desk。

    ⚠️ 这一格与上一格**不是同一件事**：上一格是「不知道你是谁」，
    这一格是「知道你是谁，但没给你配页」。两种都不许兜底到别人的首页。
    """
    live = serve(["Accounts Manager", "All"])
    status, body = live.get(HOME_PATH, cookie="sid=whatever")
    assert status == 403, body
    assert body.get("fallback") == "desk"
    assert not body.get("view")


def test_home_falls_back_to_desk_when_the_site_blows_up(serve):
    """站点那一跳炸了也要落回 Desk，**不许 500 一片白**。"""
    live = serve(RuntimeError("站点挂了"))
    status, body = live.get(HOME_PATH, cookie="sid=whatever")
    assert status in (401, 403), body
    assert body.get("fallback") == "desk"


def test_home_only_accepts_get(serve):
    live = serve(["车间工人"])
    status, _ = live.request("POST", HOME_PATH)
    assert status == 405


def test_the_role_to_home_mapping_is_a_closed_table_with_no_model_call():
    """硬约束 ③ / D-15：「这个人该看哪一页」是规则面。

    判法与 `fallback.py` 那条同族：**读源码**，比一句「我保证没调」硬。
    """
    import agenerp.dsl.roles as mod

    src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("route(", "llm", "LLM", "complete(", "chat(", "openai", "dashscope"):
        assert forbidden not in src, f"角色→首页的映射里出现了模型入口：{forbidden}"
    assert isinstance(mod.ROLE_HOMES, tuple)


def test_home_picks_by_the_tables_priority_not_by_what_the_site_happened_to_return_first():
    """一个人有多个角色时，首页由**本表的优先级**决定。

    按站点返回顺序决定会让同一个人今天落这页、明天落那页 ——
    而站点的返回顺序是不保证稳定的。

    ⚠️ **这条判据 2026-08-27 改过，起因照实记**：原来它拿 `ROLE_HOMES` 自己去测，
    而那张表**今天只有一条** —— 把一元列表反转是空操作 ⇒ **判据恒真**。
    变异 M3（把挑法改成按站点返回顺序）**第一轮没见血**，就是被这个放过去的。
    现在用一张**两条的合成表**，`home_for_roles` 为此开了一个只给判据用的注入位。
    """
    from agenerp.dsl.roles import ROLE_HOMES, home_for_roles

    two = (("角色甲", "view-a"), ("角色乙", "view-b"))
    # 两种传入顺序都必须挑到表里靠前的那一个。
    assert home_for_roles(["角色乙", "角色甲"], two) == ("角色甲", "view-a")
    assert home_for_roles(["角色甲", "角色乙"], two) == ("角色甲", "view-a")
    # 只有其中一个角色时，挑那一个。
    assert home_for_roles(["角色乙"], two) == ("角色乙", "view-b")
    assert home_for_roles([], two) is None
    # 产品路径仍走默认表。
    assert home_for_roles([name for name, _v in ROLE_HOMES]) == ROLE_HOMES[0]
