"""解释服务的 HTTP 面 —— **请求面本身**，不含 compose 接线与 nginx 同源反代。

落点节 `docs/architecture/module-boundaries.md` **§7.20**（D-19 的第一半）。
`sid` 认证模式那一层在 **§7.14**（`agenerp/site.py`，本模块是它的**调用方**，不改它）；
① 即时上下文在 **§7.12**；四项 token 账的口径在 **§7.11 / §7.17**，本模块一个字不重定。

四条规矩，每条都有判据（`tests/unit/test_explain_service.py`）：

1. **身份只从请求带上来的 `sid` 来。** 本模块**不读任何凭据环境变量、不构造站点客户端** ——
   客户端只能由注入进来的那一个工厂造（默认 `client_from_sid`）。凭据回退最省事的藏法
   就是藏在服务面的一句「取不到就用本机那份」里，判据⑧ 用 AST 扫全模块挡它。
2. **只读。** `SiteClient` 的写方法一个都不进本模块（判据⑩ 用 AST 扫）。
3. **「未配置」与「坏了」在响应上分得开。** `/health` 恒 200 且不碰 LLM 变量；
   `/explain` 在取不到模型配置时回 **503 并指名缺哪个变量**，**绝不回 200 空回答**
   （空回答与「模型选择不作答」长得一样，`agenerp/routing/errors.py` 已经登记过这个亏）。
4. **调用方声明的东西不进模型。** 请求体只收 `question` / `task_class` / `doctype` / `name`
   四个键；① 层的 `fields` / `role` / `view` / `actions` 由服务端按 §7.20 `D-a-3b` 各自定的
   那一格产出，**请求体给了一律 400**（不是静默忽略 —— 静默忽略之后，
   「调用方试图越权」与「调用方没试」在事后无从分辨）。

⚠️ **本模块不假装自己是生产级并发形态**（§7.20 `D-a-1` 逐字）：`ThreadingHTTPServer`
每连接一线程，无连接池、无请求超时、无限流、无 TLS。它只绑 `127.0.0.1`、不出宿主。
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from agenerp.context.immediate import ImmediateContext, assemble
from agenerp.explain.loop import explain
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES, TASK_CLASSES, ModelProfile
from agenerp.routing.config import from_env as config_from_env
from agenerp.routing.errors import RoutingError
from agenerp.site import RESOURCE_PATH, SiteError, client_from_sid

# 监听面。**地址写死回环**：本期服务不出宿主（§7.20 `D-a-1` 的残余风险那一条）。
LOOPBACK = "127.0.0.1"

# ⚠️ **不是 `AGENERP_HTTP_PORT`。** 那个变量是 **Frappe 站点的端口**（「要打谁」），
# 复用它就等于用一个变量同时决定「打谁」和「监听谁」，配错时的失败形态是静默的。
# 依据与备选见 §7.20 `D-a-5`。
PORT_ENV = "AGENERP_SERVE_PORT"
DEFAULT_PORT = 8330

# 前缀字面值在 §7.20 `D-a-2` 定稿 —— 第 2 个 plan 的 nginx `location` 必须与它逐字一致。
ROUTE_PREFIX = "/agenerp"
HEALTH_PATH = f"{ROUTE_PREFIX}/health"
EXPLAIN_PATH = f"{ROUTE_PREFIX}/explain"

# Desk 注入接缝的静态资产（§7.22 `D-c-2` 选 (a) / `D-c-4` 裁定 `D-a-2` 不适用于本条）。
# **文件名是模块级常量** —— 调用方一个字都拼不进去（判据用 AST 扫全模块守它）。
# 路径由 `__file__` 推出，**不读任何环境变量**。
ASSET_FILENAME = "desk.js"
ASSET_PATH = f"{ROUTE_PREFIX}/{ASSET_FILENAME}"
ASSET_CONTENT_TYPE = "text/javascript; charset=utf-8"
ASSET_DIR = Path(__file__).resolve().parent / "assets"

# 本服务实际服务的路径集合。**404 文案从它算出来，不另写一份字面量** ——
# 漏改文案就是一条会说谎的错误信息，而说谎的错误信息比没有更贵。
SERVED_PATHS = (HEALTH_PATH, EXPLAIN_PATH, ASSET_PATH)

# 只读白名单方法：把浏览器带上来的 `sid` 解析成一个人。
LOGGED_USER_METHOD = "frappe.auth.get_logged_user"

DEFAULT_TASK_CLASS = "explain"
DEFAULT_SESSION_ID = "explain-service"

# §7.20 `D-a-3b` 的 (C) 两格：服务端写死，请求体给了也不生效（给了直接 400）。
SERVICE_VIEW = "explain-service"
SERVICE_ACTIONS: tuple[str, ...] = ()

ALLOWED_BODY_KEYS = frozenset({"question", "task_class", "doctype", "name"})

# 这五个键是**越权向量**，不是普通的多余键：它们各自对应 ① 层一个「谁说了算」的位置。
# 单独点名是为了让 400 的文案说得出「你试图自己声明身份/上下文」，而不是笼统一句「多了个键」。
CALLER_CLAIMED_KEYS = ("fields", "role", "view", "actions", "user")

# 401 一律回这一句**固定文案**。理由有两条：① 站点原文里那句
# `Function ... is not whitelisted` 是误导性的（活站点实测见
# `docs/analysis/2026-08-25-1159-explain-service-sid-probe.md`）；② 不透传站点原文，
# 就没有把站点内部信息经由本服务漏给浏览器的路径。
UNAUTHENTICATED = "未认到人：请求里没有可用的 sid，或站点不认它"

INTERNAL_ERROR = "服务内部出错"


class ServiceError(Exception):
    """一次请求的失败：**带着它该回的状态码**。映射表见 §7.20 `D-a-4`。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class ServiceDeps:
    """服务面的全部外部依赖，**一个都可以从外部传进来**。

    不做依赖注入的话，判据只能靠打补丁，而打补丁之后「真实现」与「假实现」在代码里
    分不出来 —— 那正是本模块最该被判的地方（判据⑧ 要能指着**默认值**说
    「产品路径上就是这一个工厂」）。
    """

    site: str
    client_factory: Callable[..., Any] = client_from_sid
    site_transport: Any = None
    models: Sequence[ModelProfile] = field(
        default_factory=lambda: tuple(KNOWN_MODEL_PROFILES.values())
    )
    doctypes: Sequence[str] | None = None
    config_factory: Callable[[], Any] = config_from_env
    llm_transport: Any = None
    explain_fn: Callable[..., Any] = explain
    log_sink: Callable[[str], None] | None = None


def _sid_from_cookie(header: str | None) -> str:
    """`Cookie` 头 → `sid`。**取不到就 401，绝不回退到别的凭据。**"""
    if not header:
        raise ServiceError(401, UNAUTHENTICATED)
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(header)
    except CookieError:
        raise ServiceError(401, UNAUTHENTICATED) from None
    morsel = jar.get("sid")
    value = morsel.value.strip() if morsel is not None else ""
    if not value:
        raise ServiceError(401, UNAUTHENTICATED)
    return value


def parse_request(raw: bytes) -> dict:
    """请求体 → 四个已校验的字段。**允许清单之外的键一律 400**（§7.20 `D-a-3b`）。"""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ServiceError(400, "请求体不是 UTF-8 编码的 JSON") from None
    if not isinstance(payload, dict):
        raise ServiceError(400, "请求体必须是一个 JSON 对象")

    unknown = sorted(set(payload) - ALLOWED_BODY_KEYS)
    claimed = [key for key in unknown if key in CALLER_CLAIMED_KEYS]
    if claimed:
        raise ServiceError(
            400,
            f"请求体不许自带 {claimed}：当前单据的字段表、发起人、视图与已执行动作"
            f"一律由服务端按调用者自己的 sid 产出，调用方声明的不作数。"
            f"允许的键只有 {sorted(ALLOWED_BODY_KEYS)}",
        )
    if unknown:
        raise ServiceError(
            400, f"请求体出现允许清单以外的键：{unknown}；允许的只有 {sorted(ALLOWED_BODY_KEYS)}"
        )

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ServiceError(400, "question 必须是非空字符串")

    task_class = payload.get("task_class", DEFAULT_TASK_CLASS)
    if task_class not in TASK_CLASSES:
        raise ServiceError(
            400, f"task_class {task_class!r} 不是已声明的任务类目；已声明的是 {list(TASK_CLASSES)}"
        )

    doctype = payload.get("doctype")
    name = payload.get("name")
    if (doctype is None) != (name is None):
        raise ServiceError(400, "doctype 与 name 必须同时给或同时不给")
    if doctype is not None and not (
        isinstance(doctype, str) and doctype.strip() and isinstance(name, str) and name.strip()
    ):
        raise ServiceError(400, "doctype 与 name 必须是非空字符串")

    return {
        "question": question,
        "task_class": task_class,
        "doctype": doctype.strip() if isinstance(doctype, str) else None,
        "name": name.strip() if isinstance(name, str) else None,
    }


def _resolve_identity(deps: ServiceDeps, sid: str) -> tuple[Any, str]:
    """`sid` → （客户端，人）。**客户端只由注入的工厂造**，本模块不自己拼。"""
    client = deps.client_factory(deps.site, sid, transport=deps.site_transport)
    try:
        user = client.call_method(LOGGED_USER_METHOD)
    except SiteError:
        raise ServiceError(401, UNAUTHENTICATED) from None
    if not isinstance(user, str) or not user.strip():
        raise ServiceError(401, UNAUTHENTICATED)
    return client, user.strip()


def _immediate_context(client: Any, user: str, doctype: str, name: str) -> ImmediateContext:
    """① 即时上下文（§7.20 `D-a-3` 的 (iii)）：**字段表用调用者自己的 `sid` 现取**。

    ⇒ 权限由 Frappe 判。调用者读不到的单据，这一跳就被站点拒掉，模型永远看不到它。
    """
    try:
        payload = client.get(f"{RESOURCE_PATH}/{doctype}/{name}")
    except SiteError:
        raise ServiceError(403, f"当前身份取不到 {doctype} {name} 的字段表") from None
    fields = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(fields, dict):
        raise ServiceError(403, f"当前身份取不到 {doctype} {name} 的字段表")
    return assemble(
        doctype=doctype,
        name=name,
        fields=fields,
        role=user,
        view=SERVICE_VIEW,
        actions=SERVICE_ACTIONS,
    )


def handle_explain(deps: ServiceDeps, *, cookie_header: str | None, raw_body: bytes) -> dict:
    """`POST <前缀>/explain` 的全部逻辑。失败一律抛 `ServiceError`（带状态码）。"""
    sid = _sid_from_cookie(cookie_header)
    request = parse_request(raw_body)
    client, user = _resolve_identity(deps, sid)

    immediate = None
    if request["doctype"] is not None:
        immediate = _immediate_context(client, user, request["doctype"], request["name"])

    # 503 与 502 的分法是**结构性**的：先显式取一次配置，这一步抛就是「未配置」；
    # 配置拿到之后再进循环，那之后抛的才是「上游坏了」。不靠读异常文本猜。
    try:
        config = deps.config_factory()
    except RoutingError as exc:
        raise ServiceError(503, str(exc)) from None

    try:
        result = deps.explain_fn(
            request["question"],
            task_class=request["task_class"],
            client=client,
            models=deps.models,
            config=config,
            transport=deps.llm_transport,
            doctypes=deps.doctypes,
            session_id=DEFAULT_SESSION_ID,
            user=user,
            immediate=immediate,
        )
    except RoutingError as exc:
        raise ServiceError(502, str(exc)) from None

    ledger = result.cost_ledger
    return {
        "user": user,
        "answer": result.answer,
        "accepted": result.accepted,
        # 四项 token 账随响应回（§7.11 / §7.17 的既定口径，本模块不重定）：
        # `reasoning` 是 `completion` 的细分、`cached` 是 `prompt` 的细分，
        # **`cached` 不进 `total`**。数由账本给，本模块不自己写加法。
        "cost": {"calls": len(ledger), "total": ledger.total.as_dict()},
    }


def _make_handler(deps: ServiceDeps) -> type[BaseHTTPRequestHandler]:
    def _to_stderr(line: str) -> None:
        print(line, file=sys.stderr)

    sink = deps.log_sink if deps.log_sink is not None else _to_stderr

    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "agenerp-explain"
        sys_version = ""

        def log_message(self, fmt: str, *args: Any) -> None:
            """**`fmt` 与 `args` 一律不用。**

            默认实现会把整条请求行打出去，而请求行里的 query 串是调用方能控制的 ——
            那就是一条「调用方能往日志里塞任意内容」的路径。日志行只由本服务自己拼，
            且**只拼方法与不带 query 的路径**（判据⑨）。
            """
            path = urlsplit(getattr(self, "path", "") or "").path
            sink(f"{getattr(self, 'command', '-')} {path}")

        def do_GET(self) -> None:  # noqa: N802 - 标准库约定的方法名
            path = urlsplit(self.path).path
            if path == HEALTH_PATH:
                # **不认人、不碰 LLM 变量、不打站点**（§7.20 `D-a-2`）。
                self._respond(200, {"status": "ok", "service": "agenerp-explain"})
                return
            if path == EXPLAIN_PATH:
                self._respond(405, {"error": f"{EXPLAIN_PATH} 只接受 POST"})
                return
            if path == ASSET_PATH:
                # **不认人**（不读 Cookie）、**不碰 LLM**、**不打站点**（§7.22 `D-c-4` 的端点表第三行）。
                self._respond_asset()
                return
            self._not_found()

        def do_POST(self) -> None:  # noqa: N802 - 标准库约定的方法名
            path = urlsplit(self.path).path
            if path == HEALTH_PATH:
                self._respond(405, {"error": f"{HEALTH_PATH} 只接受 GET"})
                return
            if path == ASSET_PATH:
                self._respond(405, {"error": f"{ASSET_PATH} 只接受 GET"})
                return
            if path != EXPLAIN_PATH:
                self._not_found()
                return
            try:
                body = self._read_body()
                payload = handle_explain(
                    deps, cookie_header=self.headers.get("Cookie"), raw_body=body
                )
            except ServiceError as exc:
                self._respond(exc.status, {"error": exc.message})
            except Exception:
                # **异常文本一个字不回给调用方。** 站点回包、内部路径、栈帧都可能在里面。
                self._respond(500, {"error": INTERNAL_ERROR})
            else:
                self._respond(200, payload)

        def _read_body(self) -> bytes:
            raw = self.headers.get("Content-Length") or "0"
            try:
                length = int(raw)
            except ValueError:
                raise ServiceError(400, "Content-Length 不是整数") from None
            if length < 0:
                raise ServiceError(400, "Content-Length 不能是负数")
            return self.rfile.read(length) if length else b""

        def _respond_asset(self) -> None:
            """把 `assets/` 下那个**名字写死在模块常量里**的文件原样发出去。

            **请求里的任何一个字都进不了文件路径** —— 路径 = `ASSET_DIR / ASSET_FILENAME`，
            两项都是模块级常量，`self.path` 只被用来做等值比较（`path == ASSET_PATH`），
            从不参与拼接。判据用 AST 扫**本模块全部函数**守这一条（既有判据⑧/⑩ 只扫
            `do_GET` 那几个，把逻辑挪进 helper 就绕过去了 —— 这一格是补的）。

            读不到文件时回 500 且**不回显任何路径**：那是部署缺件，不是调用方能修的事。
            """
            try:
                body = (ASSET_DIR / ASSET_FILENAME).read_bytes()
            except OSError:
                self._respond(500, {"error": INTERNAL_ERROR})
                return
            self.send_response(200)
            self.send_header("Content-Type", ASSET_CONTENT_TYPE)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _not_found(self) -> None:
            """**不回显请求路径。** 路径与 query 是调用方能控制的，回显就是一条反射面。

            枚举的路径**从 `SERVED_PATHS` 算出来**，不另写一份 —— 判据比对的是
            「文案里枚举的集合 == 本模块实际服务的常量集合」，漏改一条当场红。
            """
            served = "、".join(SERVED_PATHS)
            self._respond(404, {"error": f"未知路径；本服务只有 {served}"})

        def _respond(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _Handler


def build_server(
    *,
    site: str,
    host: str = LOOPBACK,
    port: int = 0,
    **overrides: Any,
) -> ThreadingHTTPServer:
    """建一个可直接 `serve_forever()` 的服务。

    `port=0` 让内核分配端口 —— 判据用它拿一个真端口起真 socket，
    不必猜一个「大概没人用」的数。
    """
    if not site or not site.strip():
        raise ValueError("站点名为空：服务不知道该把 sid 拿去问谁")
    deps = ServiceDeps(site=site.strip(), **overrides)
    return ThreadingHTTPServer((host, port), _make_handler(deps))
