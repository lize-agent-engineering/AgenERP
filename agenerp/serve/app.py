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
from urllib.parse import parse_qs, urlsplit

from agenerp.context.immediate import ImmediateContext, assemble
from agenerp.explain.loop import explain
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES, TASK_CLASSES, ModelProfile
from agenerp.routing.config import from_env as config_from_env
from agenerp.routing.errors import RoutingError
from agenerp.dsl.blocks import Block, View
from agenerp.dsl.fallback import plan_render
from agenerp.dsl.roles import WORKER_DAILY_VIEWS, home_for_roles
from agenerp.dsl.schema import SchemaView
from agenerp.dsl.validate import validate
from agenerp.i18n import load_terms
from agenerp.site import RESOURCE_PATH, SiteError, client_from_sid

# 可渲染的视图，**按名字查表**。v0 硬编码（P2.4 的 GitOps 会把它换成存储）。
VIEWS_BY_NAME = {view.name: view for view in WORKER_DAILY_VIEWS}

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

# P2.2 的视图渲染器资产。**同样是模块级常量**，理由与 `ASSET_FILENAME` 一字不差：
# 调用方一个字都拼不进文件路径（判据 `test_the_asset_file_path_is_never_built_from_request_data`
# 用 AST 扫全模块守着）。加第二个资产**没有引入按请求名查文件**那条路 ——
# 两个常量、两次等值比较，没有映射表、没有拼接。
RENDER_ASSET_FILENAME = "render.js"
RENDER_ASSET_PATH = f"{ROUTE_PREFIX}/{RENDER_ASSET_FILENAME}"

# 视图渲染计划端点：给一个视图名，回「哪些块画得了、哪些落回、哪些画不全」。
# **它不取业务数据** —— 数据由浏览器同源直打 Frappe 的 `/api/resource`，
# 带自己的 sid，**权限由后端强制**（`system-baseline.md` §4：前端只做呈现与提示）。
# 让本服务代取数据等于给它开一条绕过浏览器身份的路。
VIEW_PLAN_PATH = f"{ROUTE_PREFIX}/view"

# ②③端的壳页（`system-baseline.md` §3.1 的「AgenERP Web」）。**同样是模块级常量。**
# ⚠️ **服务端一个字都不往这份 HTML 里拼** —— 要渲染哪个视图由页面自己从
# `location.search` 读。一旦服务端开始拼，就出现了一条反射型注入面，
# 而它恰好绕过 `render.js` 那条「建 DOM 只走 textContent」的约束。
APP_PAGE_FILENAME = "app.html"
APP_PAGE_PATH = f"{ROUTE_PREFIX}/app"
APP_PAGE_CONTENT_TYPE = "text/html; charset=utf-8"

# 角色首页解析（P2.6）。**用调用方自己的 sid 问站点「你是谁、有哪些角色」** ——
# 前端不判身份（`system-baseline.md` §4：权限由后端强制，前端只做呈现与提示）。
HOME_PATH = f"{ROUTE_PREFIX}/home"

# 取当前用户角色的白名单方法。与 `LOGGED_USER_METHOD` 同族：只读、只问身份。
USER_ROLES_METHOD = "frappe.core.doctype.user.user.get_roles"

# 本服务实际服务的路径集合。**404 文案从它算出来，不另写一份字面量** ——
# 漏改文案就是一条会说谎的错误信息，而说谎的错误信息比没有更贵。
SERVED_PATHS = (
    HEALTH_PATH,
    EXPLAIN_PATH,
    ASSET_PATH,
    RENDER_ASSET_PATH,
    VIEW_PLAN_PATH,
    APP_PAGE_PATH,
    HOME_PATH,
)

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
    # P2.2 · 站点 schema 的取法。**默认从活站点取**，判据可以塞一份固定快照进来。
    # ⚠️ **取不到时回 `None`，不回一个空 `SchemaView`** —— 后者会被
    # `validate()` 读成「站点什么都没有」从而把每个字段都判成不存在，
    # 那是一条**看起来在工作、其实在说谎**的路径。回 `None` ⇒ `view_plan` 抛 503。
    schema_factory: Callable[["ServiceDeps"], "SchemaView | None"] = None  # type: ignore[assignment]

    def schema(self) -> "SchemaView | None":
        factory = self.schema_factory or _schema_from_site
        return factory(self)


def _schema_from_site(deps: "ServiceDeps") -> "SchemaView | None":
    """从活站点取 schema。**任何失败都回 `None`，不吞成空 schema。**

    v0 只取本服务真会渲染的那几张表（视图里出现过的 DocType 与它们声明的子表）——
    整站六千多个字段没必要每次请求都拉一遍，而「只拉用得着的」也让
    「视图引用了一张没拉的表」这件事**当场变成 `has_doctype` 为假**，
    而不是悄悄放行。
    """
    wanted: set[str] = set()
    for view in VIEWS_BY_NAME.values():
        for block in view.blocks:
            if block.doctype:
                wanted.add(block.doctype)
            for _table_field, child_doctype, _names in block.child_fields:
                wanted.add(child_doctype)
    try:
        client = deps.client_factory(site=deps.site, transport=deps.site_transport)
        rows: list[dict] = []
        for doctype in sorted(wanted):
            meta = client.get(f"/api/resource/DocType/{doctype}")
            for field_row in (meta.get("data") or {}).get("fields") or []:
                rows.append(
                    {
                        "doctype": doctype,
                        "fieldname": field_row.get("fieldname"),
                        "fieldtype": field_row.get("fieldtype"),
                        "options": field_row.get("options"),
                    }
                )
    except Exception:
        return None
    if not rows:
        return None
    return SchemaView.from_meta_rows(rows)


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
            # **`AGENERP_LLM_MODEL` 必须真的决定用哪个模型。**
            # 2026-08-26 实测：不传 `requested` 时 `route()` 取的是「第一个满足
            # 该任务类目的档案」，用的是 `profile.name` ——**配置里的模型名被完全
            # 忽略**。实测配 `qwen3.7-flash`、实际走 `qwen3.8-max`，而后者没有免费
            # 额度 ⇒ 每一次解释都 403，用户却只看到一个空答案。
            # 点名的模型不在候选档案里时 `route()` 会明确抛 —— **那正是要的**：
            # 配了一个系统不认识的模型，应当明确失败，不该悄悄换一个跑。
            requested=config.model,
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
        # **不接受时必须说出为什么。** 2026-08-26 实测：模型端点回 403
        # （免费额度耗尽）时，循环把 `RoutingError` 记进账本后正常返回，
        # 服务于是回 `{"answer": "", "accepted": false}` —— **一个字的理由都没有**。
        # 人侧当时是绕开服务、直接调路由层才逼出那条 403 的。
        # 空答案 + 无理由是最难查的失败形态：它看起来像「模型没话说」，
        # 实际是「根本没调成」。两者对使用者的意义完全不同。
        **_failure_detail(result),
    }


def _failure_detail(result) -> dict:
    """`accepted` 为假时，把停下来的原因原样带回。接受时返回空 dict。

    **只在不接受时出现**，因此不改变成功路径的回包形状（既有判据逐字断言
    `set(payload["cost"]["total"])`，没有断言顶层键集合，本函数不与之冲突）。
    """
    if result.accepted:
        return {}
    trace = getattr(result, "trace", None)
    stopped = getattr(trace, "stopped", None)
    if stopped is None:
        return {}
    detail = ""
    for turn in reversed(getattr(trace, "turns", []) or []):
        if isinstance(turn, dict) and turn.get("detail"):
            detail = str(turn["detail"])
            break
    return {"stopped": stopped, "reason": detail} if detail else {"stopped": stopped}


def view_plan(name: str, schema: SchemaView | None) -> dict:
    """给一个视图名，回它的渲染计划。**不取任何业务数据。**

    ⚠️ `schema` 为 `None` 时**抛**，不回一个「都画得了」的乐观计划 ——
    与 `agenerp/dsl/validate.py` 同一条：**验不了的东西不许算过。**

    ⚠️ 视图名只做**字典查表**（`VIEWS_BY_NAME`），不参与任何路径拼接、不做前缀匹配。
    查不到就 404，不回显调用方给的名字（那是一条反射面）。
    """
    view = VIEWS_BY_NAME.get(name)
    if view is None:
        raise ServiceError(404, "没有这个视图")
    if schema is None:
        raise ServiceError(503, "站点 schema 取不到，无法判定字段是否存在 —— 验不了的不算过")

    result = validate(view, schema)
    if not result.ok:
        # 校验不过的视图**不许渲染**。它指向了不存在的字段，画出来就是错字段。
        raise ServiceError(500, "视图定义与站点 schema 对不上")

    return plan_payload(view, schema)


def plan_payload(view: View, schema: SchemaView) -> dict:
    """把一个视图 + schema 变成渲染面的 JSON。**序列化只有这一处。**

    从 `view_plan` 里分出来是为了让判据能拿**自己构造的视图**走同一段序列化 ——
    否则「落回卡片」那条路在活体里永远走不到：路线 C 已经把工人视图的落回压到 0，
    而判据若自己手写一份计划 JSON，验的就是我手写得对不对，不是这段代码。
    ⚠️ 这个接缝是**判据用的**，产品路径仍然只经 `view_plan()` 进来（要过视图名查表）。
    """
    plan = plan_render(view, schema)
    # 渲染器要靠字段类型决定「剥标签」还是「当图片」。**只交这个视图用得着的那些**，
    # 且**查不到就不放进来** —— 渲染器对缺类型的字段一律按纯文本处理（最保守的一档）。
    fieldtypes = {}
    for doctype, fieldname in view.field_refs():
        kind = schema.fieldtype(doctype, fieldname)
        if kind:
            fieldtypes[f"{doctype}.{fieldname}"] = kind

    labels, terminology = _chinese_labels(view)

    return {
        "view": view.name,
        "title": view.title,
        "fieldtypes": fieldtypes,
        "labels": labels,
        # ⚠️ 术语层缺失时**说出来**，不静默退回英文 ——
        # 「术语层没装上」与「这个字段没有中文名」在界面上长得一模一样，
        # 而前者是部署问题，后者是覆盖率问题。分不开就没人会去修。
        "terminology": terminology,
        "blocks": [_block_payload(b) for b in plan.rendered],
        "fallbacks": [
            {
                "index": f.index,
                "blockType": f.block_type,
                "reason": f.reason,
                # 落回卡片要给一个「在 Desk 中打开」的入口，得知道打开哪张单。
                "doctype": view.blocks[f.index].doctype or "",
            }
            for f in plan.fallbacks
        ],
        "degraded": [
            {"index": d.index, "field": d.fieldname, "fieldtype": d.fieldtype, "reason": d.reason}
            for d in plan.degraded
        ],
    }


def _chinese_labels(view: View) -> tuple[dict, str]:
    """这个视图用到的字段 → 中文名（P2.7 术语层）。

    ⚠️ **没有中文名的字段不放进来**，不拿 fieldname 兜底 ——
    兜底会让「有中文名」与「没有中文名」在渲染器那里分不出来，覆盖率也就没法验了。
    """
    try:
        table = load_terms()["terms"]
    except (FileNotFoundError, ValueError) as exc:
        return {}, f"术语层读不到：{type(exc).__name__}"
    labels = {}
    for doctype, fieldname in view.field_refs():
        name = table.get(f"{doctype}.{fieldname}")
        if name:
            labels[f"{doctype}.{fieldname}"] = name
    return labels, "ok"


def _block_payload(block: Block) -> dict:
    """块的**渲染面**表示。只交渲染器画得着的那几段，不把整个 dataclass 倒出去。"""
    return {
        "type": block.type,
        "title": block.title,
        "doctype": block.doctype,
        "fields": list(block.fields),
        "filters": [list(entry) for entry in block.filters],
        "sort": list(block.sort) if block.sort else None,
        "limit": block.limit,
        "agg": block.agg,
        "chartKind": block.chart_kind,
        "question": block.question,
        "childFields": [
            {"tableField": t, "doctype": d, "fields": list(fns)}
            for t, d, fns in block.child_fields
        ],
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
            if path == RENDER_ASSET_PATH:
                # 同上。**两个资产各走各的等值分支**，不共用一个「按名字找文件」的函数。
                self._respond_render_asset()
                return
            if path == VIEW_PLAN_PATH:
                self._respond_view_plan()
                return
            if path == APP_PAGE_PATH:
                self._respond_app_page()
                return
            if path == HOME_PATH:
                self._respond_home()
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
            if path == RENDER_ASSET_PATH:
                self._respond(405, {"error": f"{RENDER_ASSET_PATH} 只接受 GET"})
                return
            if path == VIEW_PLAN_PATH:
                self._respond(405, {"error": f"{VIEW_PLAN_PATH} 只接受 GET"})
                return
            if path == APP_PAGE_PATH:
                self._respond(405, {"error": f"{APP_PAGE_PATH} 只接受 GET"})
                return
            if path == HOME_PATH:
                self._respond(405, {"error": f"{HOME_PATH} 只接受 GET"})
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

        def _respond_render_asset(self) -> None:
            """把 `assets/render.js` 原样发出去。

            与 `_respond_asset` **刻意重复**，不抽成 `_send(filename)` ——
            抽出来那一刻就出现了「文件名是个参数」的形状，
            而判据 `test_the_asset_file_path_is_never_built_from_request_data`
            守的正是「文件名只能是模块级常量」。**两行重复换一条封死的路径，值。**
            """
            try:
                body = (ASSET_DIR / RENDER_ASSET_FILENAME).read_bytes()
            except OSError:
                self._respond(500, {"error": INTERNAL_ERROR})
                return
            self.send_response(200)
            self.send_header("Content-Type", ASSET_CONTENT_TYPE)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _respond_app_page(self) -> None:
            """把 `assets/app.html` **原样**发出去。

            与另外两个资产分支一样是等值比较 + 模块级常量，且**不做任何模板替换** ——
            页面里没有一个字来自请求。
            """
            try:
                body = (ASSET_DIR / APP_PAGE_FILENAME).read_bytes()
            except OSError:
                self._respond(500, {"error": INTERNAL_ERROR})
                return
            self.send_response(200)
            self.send_header("Content-Type", APP_PAGE_CONTENT_TYPE)
            self.send_header("Content-Length", str(len(body)))
            # 壳页不该被别人嵌进 iframe 里当皮 —— 它带着用户的会话。
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.end_headers()
            self.wfile.write(body)

        def _respond_home(self) -> None:
            """这个人该落在哪一页。

            🔴 **fail-closed 的方向是「不给」，不是「随便给一个」**：
            认不出人、或角色没有对应首页时，回一个**明确的落回 Desk**，
            **不回 200 + 一个空视图**。给一个不属于他的首页，用户会看到一片
            「你看不到这个」—— 那比落回 Desk 糟得多，后者他至少还能干活。
            """
            try:
                sid = _sid_from_cookie(self.headers.get("Cookie"))
                client = deps.client_factory(
                    sid=sid, site=deps.site, transport=deps.site_transport
                )
                answer = client.call_method(USER_ROLES_METHOD, {})
            except ServiceError as exc:
                self._respond(exc.status, {"error": exc.message, "fallback": "desk"})
                return
            except Exception:
                self._respond(401, {"error": UNAUTHENTICATED, "fallback": "desk"})
                return

            roles = answer if isinstance(answer, list) else (answer or {}).get("message") or []
            resolved = home_for_roles([str(r) for r in roles])
            if resolved is None:
                self._respond(
                    403,
                    {
                        "error": "这个身份还没有配角色首页",
                        "fallback": "desk",
                    },
                )
                return
            role, view_name = resolved
            self._respond(200, {"role": role, "view": view_name})

        def _respond_view_plan(self) -> None:
            """回一个视图的渲染计划。**不认人、不取业务数据。**

            为什么不认人：本端点只回「这个视图长什么样、哪些块画得了」——
            那是**视图定义**，不是业务数据。业务数据由浏览器同源直打 Frappe，
            带自己的 sid，权限由后端强制（`system-baseline.md` §4）。
            让本服务代取数据等于给它开一条绕过浏览器身份的路。
            """
            params = parse_qs(urlsplit(self.path).query)
            names = params.get("name") or []
            if len(names) != 1:
                self._respond(400, {"error": "要恰好一个 name 参数"})
                return
            try:
                payload = view_plan(names[0], deps.schema())
            except ServiceError as exc:
                self._respond(exc.status, {"error": exc.message})
            except Exception:
                self._respond(500, {"error": INTERNAL_ERROR})
            else:
                self._respond(200, payload)

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
