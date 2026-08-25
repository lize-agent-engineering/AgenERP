"""Desk 静态资产路由的判据（§7.22 `D-c-2` / `D-c-4`）—— 起真 socket 打真路由。

**这一份守的是「服务这一端」**，模板那一端在 `test_desk_injection_static.py`。
两份合起来才是那一跳：nginx 注入的 URL 与服务发出的 URL 必须是**同一个字面量的两次读取**。

⚠️ **为什么要另起一份 AST 扫描，而不是靠既有判据⑧/⑩**：那两条只扫 `do_GET` 那几个函数，
把资产逻辑挪进 `do_GET` 之外的 helper 就整个绕过去了。本文件扫**本模块全部函数**。
"""

from __future__ import annotations

import ast
import http.client
import json
import pathlib
import re
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402
import serve_fakes  # noqa: E402

from agenerp.serve import app as serve_app  # noqa: E402
from agenerp.serve.app import (  # noqa: E402
    ASSET_CONTENT_TYPE,
    ASSET_DIR,
    ASSET_FILENAME,
    ASSET_PATH,
    SERVED_PATHS,
    build_server,
)

SITE = "unit-test-site"


class _Live:
    """在 `127.0.0.1:0` 上真起一个服务（端口由内核分配，不猜数）。"""

    def __init__(self, server) -> None:
        self.server = server
        self.host, self.port = server.server_address[:2]
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.thread.start()

    def get(self, path: str, *, headers=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request("GET", path, headers=dict(headers or {}))
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def request(self, method: str, path: str):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            conn.request(method, path)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


@pytest.fixture
def live():
    started: list[_Live] = []

    def start():
        server = build_server(
            site=SITE,
            port=0,
            site_transport=serve_fakes.sid_site(),
            models=fakes.models(),
            doctypes=list(fakes.SCOPE_CANDIDATES),
            config_factory=fakes.config,
            llm_transport=serve_fakes.scripted_model(),
        )
        service = _Live(server)
        started.append(service)
        return service

    yield start
    for service in started:
        service.close()


# --- ① 不认人：不带任何 Cookie 就该拿到 200 -----------------------------------------


def test_asset_is_served_without_any_cookie(live):
    """① `<script src>` 那一跳浏览器会带 Cookie，但**资产本身不得依赖它**。

    认人会多出一条「未登录时页面报错」的噪声路径，而 `H4` 实测未登录根本拿不到 Desk HTML
    ⇒ 那条路径永远走不到，是纯负债。

    失败意味着：资产开始认人 ⇒ 多一个认人面，正是 §7.20 `D-a-2` 否决 `whoami` 时点名要避免的。
    """
    service = live()
    status, headers, body = service.get(ASSET_PATH)
    assert status == 200, f"不带 Cookie 取 {ASSET_PATH} 应当回 200，实际 {status}"
    assert body, "资产体是空的"
    assert "Content-Length" in headers, "没有显式 Content-Length"
    assert headers["Content-Length"] == str(len(body))


# 浏览器认得的 JavaScript MIME 集合（HTML 规范 "JavaScript MIME type" 那张表的常用子集）。
# ⚠️ **这是判据里唯一一处刻意写死的字面量，理由必须说清**：它对齐的不是本仓的另一个文件，
# 而是**浏览器那一侧的契约** —— 没有第二个仓内文件可以「各读一次再比」。
# 拿 `ASSET_CONTENT_TYPE` 自己比自己**挡不住把它整个改掉**（本轮变异 M5 实测：
# 改成 `application/json` 后判据**全绿**，因为两边是同一个常量的两次读取）。
_JAVASCRIPT_MIME_TYPES = frozenset(
    {"text/javascript", "application/javascript", "application/x-javascript"}
)


def test_asset_content_type_is_javascript(live):
    """① `Content-Type` **必须是浏览器会执行的 JavaScript 类型**。

    两层一起判，缺一不可：
    ① 服务实际发出的与 `ASSET_CONTENT_TYPE` 一致（服务与自己的常量没漂）；
    ② **那个常量本身的 media type 落在 JavaScript MIME 集合里**（常量没被改成不会被执行的类型）。

    ⚠️ 只判 ① 是不够的 —— 变异 M5 实测坐实：把 `ASSET_CONTENT_TYPE` 改成
    `application/json` 之后，只判 ① 的版本**全绿**，而浏览器**不会执行**这段脚本，
    HTML 里那个 `<script>` 标签照样在、`curl` 照样 200。**绿着坏掉。**

    失败意味着：这段 JS 送到了浏览器却不会被执行。
    """
    service = live()
    _, headers, _ = service.get(ASSET_PATH)
    assert headers.get("Content-Type") == ASSET_CONTENT_TYPE

    media_type = ASSET_CONTENT_TYPE.split(";")[0].strip().lower()
    assert media_type in _JAVASCRIPT_MIME_TYPES, (
        f"Content-Type 的 media type 是 {media_type!r}，不在浏览器会执行的 "
        f"JavaScript MIME 集合 {sorted(_JAVASCRIPT_MIME_TYPES)} 里 —— 脚本送到了也不会跑"
    )
    assert "charset=utf-8" in ASSET_CONTENT_TYPE.lower(), (
        "没有声明 charset=utf-8 —— 资产里有中文注释，编码靠猜时行为依浏览器而异"
    )


def test_asset_file_is_not_gutted(live):
    """① 资产**不是一份空文件或被掏空的壳**。

    ⚠️ **这一格是变异 M6 逼出来的，照实记**：「体与仓里那份逐字节相同」是一条
    **两个源各读一次**的判据 —— 改了磁盘上那份，服务发的也跟着变，**它按构造照不红**。
    它守的是「服务发出的 ≠ git 里那份」（变异 M6b 实测打红它），**不是**「文件内容没被改坏」。

    所以这里补一条**只看内容形状**的下限判据：非空、含自己的版本标记、含 IIFE 的收尾。
    它不锁死具体字节（那会让每次改 JS 都要同步改判据，是纯 churn），只挡「掏空」。

    失败意味着：资产被清空或替换成了一段不成形的东西。
    """
    text = (ASSET_DIR / ASSET_FILENAME).read_text(encoding="utf-8")
    assert len(text) > 200, f"资产只有 {len(text)} 字符 —— 像是被掏空了"
    assert "agenerpDesk" in text, "资产里没有它挂到 window 上的那个标记名"
    assert "Object.freeze" in text, "标记不再是只读的（`Object.freeze` 不见了）"
    assert text.rstrip().endswith(")();"), "资产不是一个收尾完整的 IIFE"


def test_asset_body_is_byte_identical_to_the_repo_file(live):
    """① 体与 `agenerp/serve/assets/desk.js` **逐字节相同**。

    ⚠️ 不比「包含某个子串」—— 那样改动一个字节仍然全绿，而进浏览器执行的是全部字节。

    失败意味着：服务发出的不是 git 里那份 ⇒ 「可 diff、可回滚」当场不成立。
    """
    service = live()
    _, _, body = service.get(ASSET_PATH)
    on_disk = (ASSET_DIR / ASSET_FILENAME).read_bytes()
    assert body == on_disk, "服务发出的字节与仓里那份不同"


def test_asset_rejects_non_get_methods(live):
    """① 资产只接受 GET。POST 回 405，**不是 404** —— 路径是存在的，方法不对。"""
    status, raw = service_post(live)
    assert status == 405, f"POST {ASSET_PATH} 应当回 405，实际 {status}"
    assert ASSET_PATH in json.loads(raw)["error"]


def service_post(live):
    service = live()
    return service.request("POST", ASSET_PATH)


# --- ② 未知路径仍 404，且不回显请求路径 ---------------------------------------------


# 每条都带一个**不属于任何已服务路径**的标记串。
# ⚠️ 不能拿 `path` 的末段当探针 —— 404 文案**本来就**枚举 `desk.js` 等真路由，
# 那样断言会在一条完全正确的实现上变红（本判据自己先踩过这一脚，照实记）。
_REFLECTION_MARK = "zzREFLECTzz"


@pytest.mark.parametrize(
    "path",
    [
        f"/agenerp/{_REFLECTION_MARK}.js",
        f"/agenerp/desk.js{_REFLECTION_MARK}",
        f"/agenerp/../{_REFLECTION_MARK}",
        f"/agenerp/health?x={_REFLECTION_MARK}",
        f"/{_REFLECTION_MARK}",
    ],
)
def test_unknown_paths_stay_404_and_do_not_reflect_the_request(live, path: str):
    """② 未知路径回 404，且**请求里调用方能控制的那部分一个字不回显**。

    回显就是一条反射面：调用方能把任意内容放进响应体。

    ⚠️ 最后一条带 query —— `/agenerp/health?x=…` 的 **path 部分是真路由**，
    它必须仍回 200 且不把 query 带进任何响应；这里用它顺带守「query 不进响应体」。

    失败意味着：新加的资产分支把 404 的那条既有性质带塌了。
    """
    service = live()
    status, _, body = service.get(path)
    message = body.decode("utf-8")
    if "?" in path:
        assert status == 200, f"{path} 的 path 部分是真路由，应当回 200，实际 {status}"
    else:
        assert status == 404, f"{path} 应当回 404，实际 {status}"
    assert _REFLECTION_MARK not in message, f"响应回显了调用方控制的串：{message!r}"


def test_404_message_enumerates_exactly_the_paths_this_module_serves(live):
    """② **404 文案枚举的路径集合 == 本模块实际服务的路径常量集合。**

    ⚠️ 两边都从常量算出来，**判据里不写第三个字面量** —— 写了之后这条判据就只是在
    验证一个字符串等于它自己，而文案与实际路由可以一起漂走。

    ⚠️ 这一格是补的：落地前 `grep -rn "本服务只有" tests/` **无输出** ⇒ 漏改、改错、
    改成一条不存在的第四条路径，**当时全绿**。一条会说谎的错误信息比没有更贵。

    失败意味着：加/删了一条路由而文案没跟，或文案枚举了一条不存在的路径。
    """
    service = live()
    _, _, body = service.get("/agenerp/definitely-not-a-route")
    message = json.loads(body)["error"]

    mentioned = {path for path in SERVED_PATHS if path in message}
    assert mentioned == set(SERVED_PATHS), (
        f"404 文案没有枚举全部实际路由。文案：{message!r}；"
        f"缺：{set(SERVED_PATHS) - mentioned}"
    )
    # 反向：文案里不许出现本模块**不**服务的 `/agenerp/*` 路径。
    quoted = set(re.findall(r"/agenerp/[A-Za-z0-9_.\-]+", message))
    assert quoted == set(SERVED_PATHS), (
        f"404 文案枚举了本模块并不服务的路径：{quoted - set(SERVED_PATHS)}；文案：{message!r}"
    )


# --- ③ AST：扫本模块全部函数，不只是 `do_GET` -----------------------------------------


def _module_tree() -> ast.Module:
    return ast.parse(pathlib.Path(serve_app.__file__).read_text(encoding="utf-8"))


def test_no_credential_env_var_anywhere_in_the_module():
    """③ 本模块**不读任何凭据环境变量**。

    ⚠️ 扫的是**整个模块**（含新加的 helper），不是某几个函数 —— 既有判据⑧/⑩ 只扫
    `do_GET` 那几个，凭据回退最省事的藏法就是藏在一个 helper 的一句
    「取不到就用本机那份」里。

    失败意味着：身份不再只从请求带上来的 `sid` 来。
    """
    tree = _module_tree()
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    forbidden_names = {"getenv", "environ", "environb"}
    assert not (names & forbidden_names), f"模块里出现了环境读取名：{names & forbidden_names}"
    assert not (attrs & forbidden_names), f"模块里出现了环境读取属性：{attrs & forbidden_names}"

    credential_literals = {
        text
        for text in literals
        if "API_KEY" in text or "PASSWORD" in text or "AGENERP_ADMIN" in text
    }
    assert not credential_literals, f"模块里出现了凭据字面量：{credential_literals}"


def test_the_asset_file_path_is_never_built_from_request_data():
    """③ **请求里的值一个字都拼不进文件路径。**

    路径只能由模块级常量 `ASSET_DIR` / `ASSET_FILENAME` 组成；
    `self.path` / `self.headers` / `urlsplit(...)` 的产物**不许**出现在任何
    `read_bytes` / `read_text` / `open` / `Path(...)` 的实参链里。

    ⚠️ 这条挡的是最经典的那个洞：`Path(ASSET_DIR) / path.rsplit("/", 1)[-1]`
    —— 它看起来「只取文件名」，`..%2f` 一编码就穿出去了。

    失败意味着：一条任意读文件的路径。
    """
    tree = _module_tree()
    readers = {"read_bytes", "read_text", "open"}

    def mentions_request_data(node: ast.AST) -> set[str]:
        found: set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr in {"path", "headers", "rfile"}:
                value = sub.value
                if isinstance(value, ast.Name) and value.id == "self":
                    found.add(f"self.{sub.attr}")
            if isinstance(sub, ast.Name) and sub.id in {"path", "body", "raw"}:
                found.add(sub.id)
        return found

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_reader = isinstance(func, ast.Attribute) and func.attr in readers
        is_open = isinstance(func, ast.Name) and func.id == "open"
        if not (is_reader or is_open):
            continue
        tainted = mentions_request_data(node)
        if tainted:
            offenders.append(f"{ast.dump(func)[:60]} ← {sorted(tainted)}")

    assert not offenders, f"读文件的实参链里出现了请求侧的值：{offenders}"


def test_asset_filename_is_a_module_level_constant():
    """③ 文件名是**模块级常量**，不是某个函数里现拼的字符串。

    失败意味着：调用方有可能把字拼进去，而上一条判据是按「常量」这个前提写的。
    """
    tree = _module_tree()
    top_level = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert "ASSET_FILENAME" in top_level
    assert "ASSET_DIR" in top_level
    assert isinstance(ASSET_FILENAME, str) and "/" not in ASSET_FILENAME
    assert ASSET_PATH.endswith("/" + ASSET_FILENAME)
