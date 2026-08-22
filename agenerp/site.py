"""连活站点的只读传输 —— `agenerp` 里**唯一经 HTTP/REST** 打到真站点的地方。

（2026-08-21 起不再是唯一打到站点的模块：`agenerp/oob.py` 是第二条传输，走带外容器命令、
够得到物理表——REST 没有任何白名单方法回物理列，那不是取舍问题是够不到。见 §11.8。
本模块仍是唯一的 HTTP 落点，两条传输不互相代理。）

结构边界见 `docs/architecture/module-boundaries.md` §11.7。四条约束写在最前面，
因为它们比实现细节重要：

1. **不伪装成功。** 连不上 / 认证失败 / 非 2xx / 载荷不是 JSON —— 一律抛 `SiteError`。
   降级成空结果会让「未改动 → diff 为空」这条判据在站点宕机时照样绿。
2. **零第三方依赖。** 只用标准库（CI 的 `gates-l1` 只 `pip install pytest`）。
3. **产品代码不内置口令默认值。** 缺凭据时显式报错并指名缺哪个环境变量。
   `tests/gates/conftest.py` 给 fixture 留的 `admin` 默认值是测试脚手架，不是产品口径。
4. **写方法必须登记。** 公开方法名里出现 `agenerp.contracts.WRITE_VERBS` 的，
   必须在 `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST` 里逐条列名。
   2026-08-21 起有 `SiteClient.delete_custom_field`（差集 apply 的 B 半，plan `2026-08-21-1922-3`）；
   **2026-08-22 起再加三条**：`SiteClient.create_doc` 与 `SiteClient.ensure_doc`
   （种子主数据装载，plan `2026-08-22-2107-1`），以及 `SiteClient.submit_doc`
   （种子单据装载，plan `2026-08-22-2107-2`；名字里含 `submit`，扫描守卫看得见它，仍逐条登记）。
   这是**收窄式演进**——
   每加一个写方法就要付一次 diff 和一次留痕，不是把只读约束取消了。
   ⚠️ `ensure_doc` 的名字里**一个 `WRITE_VERB` 都没有**，守卫扫不到它；
   它是**主动登记**的——漏登记等于把「加写面要付一次留痕」这条规矩掏空。
   **不提供「删任意 DocType 文档」的通用方法**：通用删除接口等于把业务数据交出去。
   ⚠️ **「本模块的写面只覆盖结构定制」这句话 2026-08-22 起不再成立**：`create_doc` / `ensure_doc`
   是**通用建档面**，覆盖业务主数据（公司 / 科目 / 仓库 / 物料 / BOM…）。
   代偿有三条，且都可判：`docs/context/ai-autonomy-policy.md` Protected Areas 新增的
   「对活站点的非破坏性写（建 / 改）」行（`plan-first`）· 上面那道登记守卫 ·
   `agenerp/seedsite.py` 是这三个方法**目前唯一的调用方**。落点见 §11.7 与 §12.9 / §12.10。
   ⚠️ **`submit_doc` 比另外两个更进一步：它不可逆**——本模块没有 cancel/amend，
   提交过的单据在站点侧回不去，只能由人手工 cancel/amend 或 `docker compose down -v` 冷起丢掉整站数据。
   代价逐字写在 §12.10，不粉饰。

两条实测得来的硬约束（不是猜的）：

- **`Host` 头必须等于站点名**：gunicorn 按 Host 解析站点，打 `127.0.0.1` 会被当成
  一个叫 `127.0.0.1` 的站点而 404（`docker-compose.yml` 的 backend 探针注释）。
- **路径必须 URL 编码**：DocType 名带空格（`Custom Field`），不编码时 `http.client`
  直接以 `URL can't contain control characters` 拒掉。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

SITE_ENV = "AGENERP_SITE"
SITE_URL_ENV = "AGENERP_SITE_URL"
HTTP_PORT_ENV = "AGENERP_HTTP_PORT"
API_KEY_ENV = "AGENERP_API_KEY"
API_SECRET_ENV = "AGENERP_API_SECRET"
ADMIN_USER_ENV = "AGENERP_ADMIN_USER"
ADMIN_PASSWORD_ENV = "AGENERP_ADMIN_PASSWORD"

DEFAULT_HTTP_PORT = "8080"
DEFAULT_ADMIN_USER = "Administrator"
DEFAULT_TIMEOUT = 60

# Frappe 的 `/api/resource` 默认只回 20 条。`limit_page_length=0` 是它关分页的口径；
# 少读一页会让「未改动 → diff 为空」在缺条目时照样绿 —— 一条最难发现的假绿。
PAGE_LENGTH_PARAM = "limit_page_length"
UNLIMITED_PAGE_LENGTH = "0"
FIELDS_PARAM = "fields"
ALL_FIELDS = ("*",)

LOGIN_PATH = "/api/method/login"
RESOURCE_PATH = "/api/resource"

# 存在性判断走列表端点 + `filters`，不走「GET 单文档、404 判不存在」：
# 2026-08-22 实测，站点对 `Warehouse` / `Account` / `Item` / `BOM` **不采纳显式 `name`**
# （分别按 `warehouse_name`/`account_name` + 公司缩写、`item_code`、命名序列派生），
# 按 name 取单文档因此对半数 DocType 无从下手。列表端点的「零行」是 HTTP 200，
# 与「站点答不上话」在状态码上天然分开 —— 这正是本模块第 1 条约束要的形状。
FILTERS_PARAM = "filters"
SINGLE_PAGE_LENGTH = "1"

# 承载「某个 DocType 上的某个定制字段」的 DocType，以及它的文档名口径。
# 名字形如 `Item-agenerp_gate_roundtrip` —— 2026-08-21 在活站点上实测确认
# （`POST /api/resource/Custom Field` 回的 `data.name`），不是从 fixture 推断的。
CUSTOM_FIELD_DOCTYPE = "Custom Field"

# 提交后的 `docstatus`。ERPNext 的三态是 0 草稿 / 1 已提交 / 2 已取消；本模块只推 0→1。
SUBMITTED_DOCSTATUS = 1


def custom_field_name(doctype: str, fieldname: str) -> str:
    """Custom Field 的文档名。**唯一落点**——读回那侧将来若要按 name 查，也走这里。"""
    return f"{doctype}-{fieldname}"


class SiteError(RuntimeError):
    """站点侧的一切失败：连不上、认证失败、非 2xx、载荷不是 JSON。

    **绝不降级成空结果。** 「这个 scope 还没有定制」是合法状态（离线来源返回空元组），
    「站点答不上话」不是 —— 两者长得一样的话，站点宕机会被读成「站点上什么都没有」。
    """


@dataclass(frozen=True)
class SiteRequest:
    """一次待发的请求。传输是可注入的接缝，所以请求必须是可检视的值对象。"""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None


@dataclass(frozen=True)
class SiteResponse:
    status: int
    body: str


class Transport(Protocol):
    """把一次 `SiteRequest` 送出去。连不上必须抛 `SiteError`，不得返回伪造的状态码。"""

    def __call__(self, request: SiteRequest) -> SiteResponse:
        ...


class UrllibTransport:
    """标准库传输。带 cookie jar —— 会话登录拿到的 `sid` 要跨请求留住。"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self._timeout = timeout

    def __call__(self, request: SiteRequest) -> SiteResponse:
        req = urllib.request.Request(
            request.url, data=request.body, headers=dict(request.headers), method=request.method
        )
        try:
            with self._opener.open(req, timeout=self._timeout) as resp:
                return SiteResponse(resp.status, resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            return SiteResponse(exc.code, exc.read().decode("utf-8", "replace"))
        except Exception as exc:  # 连不上、超时、DNS —— 都是站点答不上话
            raise SiteError(f"{request.method} {request.url} 连不上：{exc}") from exc


def encode_path(path: str) -> str:
    """只编码路径段，保留 `/` 分隔。DocType 名带空格时非编码不可。"""
    return urllib.parse.quote(path, safe="/")


def default_base_url() -> str:
    """站点基址：`AGENERP_SITE_URL` 优先，否则按 compose 的端口映射拼。"""
    explicit = os.environ.get(SITE_URL_ENV, "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = os.environ.get(HTTP_PORT_ENV, "").strip() or DEFAULT_HTTP_PORT
    return f"http://127.0.0.1:{port}"


class SiteClient:
    """活站点的客户端：读全部；写四条（`create_doc` / `ensure_doc` / `submit_doc` / `delete_custom_field`，见模块头第 4 条）。

    认证取「token 优先、会话登录回退」：token 贴生产且不把口令带进每次运行，
    但零依赖栈上没有现成的 key，只做 token 会让 L2 门禁跑不起来。取舍与残余风险
    见 `docs/architecture/module-boundaries.md` §11.7。
    """

    def __init__(
        self,
        site: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        admin_user: str = DEFAULT_ADMIN_USER,
        admin_password: str | None = None,
        transport: Transport | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        if not site:
            raise SiteError(f"站点名为空：设置 {SITE_ENV}")
        self.site = site
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self._api_key = api_key
        self._api_secret = api_secret
        self._admin_user = admin_user
        self._admin_password = admin_password
        self._transport: Transport = transport or UrllibTransport(timeout)
        self._authenticated = bool(api_key and api_secret)

    @property
    def identity(self) -> str:
        return f"{self.site}@{self.base_url}"

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """GET 一个站点资源，返回已解析的 JSON 载荷。非 2xx 抛 `SiteError`。"""
        self._ensure_authenticated()
        return self._request("GET", path, params=params)

    def list_resource(self, doctype: str, fields: tuple[str, ...] = ALL_FIELDS) -> list[dict]:
        """列出某个 DocType 的**全部**行 —— 显式关分页、显式要全部字段。

        默认参数漏掉任何一个都会静默截断：Frappe 不报错，只是少给几行。
        """
        payload = self.get(
            f"{RESOURCE_PATH}/{doctype}",
            {
                FIELDS_PARAM: json.dumps(list(fields)),
                PAGE_LENGTH_PARAM: UNLIMITED_PAGE_LENGTH,
            },
        )
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise SiteError(f"{doctype} 的列表载荷缺少 data 数组：{str(payload)[:200]}")
        return rows

    def create_doc(self, doctype: str, payload: dict) -> dict:
        """在站点上建一份文档，返回站点回的 `data`（**站点回什么就是什么**）。

        实测语义（2026-08-22，活站点 ERPNext v15.119.3）：

        - 成功回 **HTTP 200** `{"data": {...整份文档...}}`；
        - **`name` 由站点说了算**，不是由载荷说了算。`Warehouse` / `Account` 按
          `<x>_name + " - " + 公司缩写` 派生，`Item` 按 `Stock Settings.item_naming_by` 派生，
          `BOM` 走命名序列 `BOM-{item}-{###}` —— 显式塞 `name` 会被**静默忽略**。
          调用方要用真名，就得读返回值里的 `data.name`。
        - 建重名回 **HTTP 409 `DuplicateEntryError`**；缺 Link 前置回 **HTTP 417 `LinkValidationError`**。

        **不吞任何错误**：非 2xx 沿用 `_request` 抛 `SiteError`，站点错误原文进消息。
        把 409 判成「已经有了、算成功」是有诱惑力的，但那会让「载荷写错导致建了两份」
        与「本来就在」长得一模一样 —— 幂等由 `ensure_doc` 用**先查后建**做，不靠吞异常做。
        """
        self._ensure_authenticated()
        response = self._request("POST", f"{RESOURCE_PATH}/{doctype}", body=payload)
        doc = response.get("data") if isinstance(response, dict) else None
        if not isinstance(doc, dict):
            raise SiteError(f"建 {doctype} 的响应缺少 data 对象：{str(response)[:200]}")
        return doc

    def find_one(self, doctype: str, filters: dict[str, Any]) -> dict | None:
        """按 `filters` 找**至多一份**文档；找不到回 `None`。

        **只把「查得到、但零行」判成不存在。** 其余一切（连不上、401、403、5xx、载荷形状不对）
        一律经 `_request` / 本方法抛 `SiteError`。把非 2xx 判成「不存在」会让站点挂掉时
        `ensure_doc` 一路重复建 —— 这是本模块第 1 条约束在写路径上的同一件事。
        """
        self._ensure_authenticated()
        payload = self.get(
            f"{RESOURCE_PATH}/{doctype}",
            {
                FILTERS_PARAM: json.dumps([[k, "=", v] for k, v in filters.items()]),
                FIELDS_PARAM: json.dumps(list(ALL_FIELDS)),
                PAGE_LENGTH_PARAM: SINGLE_PAGE_LENGTH,
            },
        )
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise SiteError(f"{doctype} 的查询载荷缺少 data 数组：{str(payload)[:200]}")
        return rows[0] if rows else None

    def ensure_doc(self, doctype: str, key: dict[str, Any], payload: dict) -> tuple[dict, bool]:
        """幂等落地：`key` 命中则原样读回 `(doc, False)`，未命中则建并回 `(doc, True)`。

        **不改已存在的文档**（没有 upsert 的 update 半）。代价照实说：
        站点上已存在但字段不对的对象**不会被纠正**，也不会报错。取这一侧的理由是
        「少写」比「悄悄改写站点」安全；漏网的字段错误会由第二个 plan 的站点侧对账
        表现成「站点自己算出的数对不上」，**不会静默通过**。
        取舍与重开事件见 `docs/architecture/module-boundaries.md` §12.9。
        """
        existing = self.find_one(doctype, key)
        if existing is not None:
            return existing, False
        return self.create_doc(doctype, payload), True

    def submit_doc(self, doctype: str, name: str) -> dict:
        """把一份已存在的文档由 `docstatus 0` 推到 `1`（提交），返回站点回的 `data`。

        实测语义（2026-08-22，活站点 ERPNext v15.119.3，plan `2026-08-22-2107-2` Phase 1 E1）：
        `PUT /api/resource/<doctype>/<name>` 带 `{"docstatus": 1}` 即是提交，成功回
        **HTTP 200** `{"data": {...整份文档...}}` 且 `data.docstatus == 1`；
        提交期的业务校验失败回 **HTTP 417**（实测撞到过 `FiscalYearError` / `NegativeStockError`），
        沿用 `_request` 抛 `SiteError`，站点错误原文进消息。

        ⚠️ **`submit` 是不可逆动作**：本模块**不提供** cancel/amend，站点侧回滚只能由人手工做，
        或用 `docker compose down -v` 冷起丢掉整站数据。取舍见 `docs/architecture/module-boundaries.md` §12.10。

        回值的 `docstatus` 不为 1 时**主动抛错**，不看 HTTP 状态码就算数 ——
        200 但没提交上去，与提交成功长得一模一样，那正是「不伪装成功」这条约束要挡的形状。
        """
        self._ensure_authenticated()
        response = self._request(
            "PUT", f"{RESOURCE_PATH}/{doctype}/{name}", body={"docstatus": SUBMITTED_DOCSTATUS}
        )
        doc = response.get("data") if isinstance(response, dict) else None
        if not isinstance(doc, dict):
            raise SiteError(f"提交 {doctype} {name!r} 的响应缺少 data 对象：{str(response)[:200]}")
        if doc.get("docstatus") != SUBMITTED_DOCSTATUS:
            raise SiteError(
                f"提交 {doctype} {name!r} 后站点回的 docstatus 是 {doc.get('docstatus')!r}，不是 "
                f"{SUBMITTED_DOCSTATUS} —— 站点回了 2xx 但文档没被提交"
            )
        return doc

    def delete_custom_field(self, doctype: str, fieldname: str) -> None:
        """删掉站点上的一条 Custom Field。**本模块唯一的写动作**（见模块头第 4 条）。

        实测语义（2026-08-21，活站点）：成功回 **HTTP 202** `{"data":"ok"}`（不是 200/204），
        随后 `GET` 同一路径回 404；删一个不存在的 name 回 **404 `DoesNotExistError`**。
        因此成败判据沿用 `_request` 的 `200 <= status < 300`，不为删除另开分支——
        **「要删的东西不在」被判为失败并抛 `SiteError`**，不静默吞掉。

        路径由 `_request` 统一 URL 编码（`Custom Field` 带空格，不编码时 `http.client` 直接拒）。
        """
        self._ensure_authenticated()
        name = custom_field_name(doctype, fieldname)
        self._request("DELETE", f"{RESOURCE_PATH}/{CUSTOM_FIELD_DOCTYPE}/{name}")

    def _ensure_authenticated(self) -> None:
        if self._authenticated:
            return
        if not self._admin_password:
            raise SiteError(
                f"缺少站点凭据：设置 {API_KEY_ENV} + {API_SECRET_ENV}，"
                f"或设置 {ADMIN_PASSWORD_ENV}（产品代码不内置口令默认值）"
            )
        self._request(
            "POST",
            LOGIN_PATH,
            body={"usr": self._admin_user, "pwd": self._admin_password},
        )
        self._authenticated = True

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {"Host": self.site, "Accept": "application/json"}
        if has_body:
            headers["Content-Type"] = "application/json"
        if self._api_key and self._api_secret:
            headers["Authorization"] = f"token {self._api_key}:{self._api_secret}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        body: dict | None = None,
    ) -> Any:
        url = self.base_url + encode_path(path)
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        response = self._transport(
            SiteRequest(method=method, url=url, headers=self._headers(payload is not None),
                        body=payload)
        )
        if not 200 <= response.status < 300:
            raise SiteError(
                f"{method} {path} → HTTP {response.status}（站点 {self.site}）：{response.body[:300]}"
            )
        try:
            return json.loads(response.body)
        except ValueError as exc:
            raise SiteError(
                f"{method} {path} 的响应不是 JSON（HTTP {response.status}）：{response.body[:200]}"
            ) from exc


def client_from_env(site: str, transport: Transport | None = None) -> SiteClient:
    """环境变量 → 客户端。缺凭据时抛 `SiteError` 并**指名缺哪个变量**。

    半套 token（只给 key 或只给 secret）视为配错，直接报错 —— 静默回退到会话登录
    会让「token 没生效」这件事在日志里完全看不见。
    """
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    api_secret = os.environ.get(API_SECRET_ENV, "").strip()
    if bool(api_key) != bool(api_secret):
        missing = API_SECRET_ENV if api_key else API_KEY_ENV
        raise SiteError(f"token 凭据不完整：缺少 {missing}（两个必须成对出现）")
    admin_password = os.environ.get(ADMIN_PASSWORD_ENV, "")
    if not api_key and not admin_password:
        raise SiteError(
            f"站点 {site} 缺少凭据：设置 {API_KEY_ENV} + {API_SECRET_ENV}，"
            f"或设置 {ADMIN_PASSWORD_ENV}（产品代码不内置口令默认值）"
        )
    return SiteClient(
        site,
        base_url=default_base_url(),
        api_key=api_key or None,
        api_secret=api_secret or None,
        admin_user=os.environ.get(ADMIN_USER_ENV, "").strip() or DEFAULT_ADMIN_USER,
        admin_password=admin_password or None,
        transport=transport,
    )
