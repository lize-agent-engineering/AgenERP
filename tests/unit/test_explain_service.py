"""P1.8a 第 1 个 plan 的**十条判据** —— 解释服务的 HTTP 面（进程 + 端点 + `sid` 认人）。

落点节 `docs/architecture/module-boundaries.md` **§7.20**；plan
`docs/plans/p1-insight/2026-08-25-1159-1-explain-http-service.md` Phase 2。

**每一条都指名一个可观测量**，没有一条判的是「函数存在」：

| 判据 | 判什么 | 可观测量 |
|---|---|---|
| ① | 真 socket、真 HTTP、404 / 405 | `http.client` 拿到的状态码与回包 |
| ② | 没有 `sid` → 401 且**不打站点** | 状态码 + 假站点的请求条数 |
| ③ | `sid` 认不出人（`SiteError`）→ 401 | 状态码 + 回包文案 |
| ④ | 好 `sid` → 200，且 `explain()` 收到的 `user` **等于站点回的那个人** | 传给 `explain()` 的**实参** |
| ⑤ | 未配置 → 503 指名变量名；上游坏了 → 502 | 状态码 + 消息里的变量名 |
| ⑥ | 三个 `AGENERP_LLM_*` 全空时进程照起、`/health` 200 | 真 socket 上的状态码 |
| ⑦ | `assemble()` **六个入参**的出处逐个可判 | 传给 `explain()` 的 `ImmediateContext` + 站点实际被打的路径 |
| ⑧ | 服务面**零凭据零件**，构造客户端只有注入的工厂一条 | AST 扫 `agenerp/serve/**` 全文 |
| ⑨ | 回包与日志**不含 `sid` 字面量** | 回包字节 + 日志行 |
| ⑩ | 服务面**零写方法** | AST 扫 `agenerp/serve/**` 全文 |

⚠️ **本文件不是门禁。** `tests/gates/**` 在红线内，本 plan 一个文件都不建；
要活栈的那一半（`tests/gates/test_explain_service_live.py`）的断言体在
`tests/unit/test_explain_service_body.py`，由人按路径加载。
"""

from __future__ import annotations

import ast
import http.client
import json
import pathlib
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402
import serve_fakes  # noqa: E402

from agenerp.explain.loop import explain as real_explain  # noqa: E402
from agenerp.routing.config import REQUIRED_ENV  # noqa: E402
from agenerp.routing.errors import RoutingError  # noqa: E402
from agenerp.serve import app as serve_app  # noqa: E402
from agenerp.serve.app import (  # noqa: E402
    EXPLAIN_PATH,
    HEALTH_PATH,
    SERVICE_ACTIONS,
    SERVICE_VIEW,
    ServiceDeps,
    ServiceError,
    build_server,
    handle_explain,
)
from agenerp.site import client_from_sid  # noqa: E402

SITE = "frontend"
QUESTION = "成品仓还有多少台？"

SERVE_PACKAGE = pathlib.Path(serve_app.__file__).resolve().parent


class SpyExplain:
    """把 `explain()` 收到的**实参**逐次留痕，然后原样转给真实现。

    ⚠️ 断言必须落在**实参**上，不落在标志位上：一个「我确实传了 user」的布尔量
    由被测代码自己写，它和「传了什么」不是同一件事。
    """

    def __init__(self, inner=None, raises: Exception | None = None) -> None:
        self.inner = inner if inner is not None else real_explain
        self.raises = raises
        self.calls: list[dict] = []

    def __call__(self, question, **kwargs):
        self.calls.append({"question": question, **kwargs})
        if self.raises is not None:
            raise self.raises
        return self.inner(question, **kwargs)

    @property
    def last(self) -> dict:
        assert self.calls, "explain() 一次都没被调到"
        return self.calls[-1]


def deps_for(site=None, *, explain_fn=None, config_factory=None, log_sink=None, **overrides):
    """一套**全离线**依赖：假站点 + 假模型档案 + 假端点配置 + 剧本模型。

    `client_factory` **刻意不替换** —— 走产品路径上那一个 `client_from_sid`，
    只把传输层换成假件。替掉工厂的话，判据⑧ 说的「产品路径上就是这一个工厂」就没人验了。
    """
    site = site if site is not None else serve_fakes.sid_site()
    return ServiceDeps(
        site=SITE,
        site_transport=site,
        models=fakes.models(),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        config_factory=config_factory if config_factory is not None else fakes.config,
        explain_fn=explain_fn if explain_fn is not None else real_explain,
        log_sink=log_sink,
        **{"llm_transport": serve_fakes.scripted_model(), **overrides},
    )


def body(**payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def cookie(sid: str) -> str:
    return f"sid={sid}"


def ask(deps, *, sid: str | None = serve_fakes.VALID_SID, cookie_header=..., **payload) -> dict:
    header = cookie(sid) if cookie_header is ... else cookie_header
    if cookie_header is ... and sid is None:
        header = None
    return handle_explain(
        deps, cookie_header=header, raw_body=body(question=QUESTION, **payload)
    )


def status_of(deps, **kwargs) -> tuple[int, str]:
    """一次注定失败的请求 → （状态码，消息）。**成功了就是判据本身写错了**，当场红。"""
    with pytest.raises(ServiceError) as caught:
        ask(deps, **kwargs)
    return caught.value.status, caught.value.message


# ── 真进程 / 真 socket 的夹具 ───────────────────────────────────────────────


class LiveService:
    """在 `127.0.0.1:0` 上真起一个服务，另起线程 `serve_forever()`。

    端口由**内核**分配（`port=0`），不猜一个「大概没人用」的数 —— 猜错的失败形态
    是判据偶发红，而那种红没人查得动。
    """

    def __init__(self, server) -> None:
        self.server = server
        self.host, self.port = server.server_address[:2]
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)
        self.thread.start()

    def request(self, method: str, path: str, *, headers=None, payload=None):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
            head = dict(headers or {})
            if raw is not None:
                head.setdefault("Content-Type", "application/json")
            conn.request(method, path, body=raw, headers=head)
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
    started: list[LiveService] = []

    def start(**overrides):
        site = overrides.pop("site_transport", None) or serve_fakes.sid_site()
        server = build_server(
            site=SITE,
            port=0,
            site_transport=site,
            models=fakes.models(),
            doctypes=list(fakes.SCOPE_CANDIDATES),
            config_factory=overrides.pop("config_factory", fakes.config),
            llm_transport=serve_fakes.scripted_model(),
            **overrides,
        )
        service = LiveService(server)
        started.append(service)
        return service

    yield start
    for service in started:
        service.close()


# ── ① 真 socket、真 HTTP：两条路径 + 404 / 405 ───────────────────────────────


def test_c1_health_answers_over_a_real_socket(live):
    """① `/health` 在**真端口**上回 200。判的是 socket 上的回包，不是「函数存在」。

    M9「未知路径回 200」在下面那条同族判据里红。
    """
    service = live()
    status, raw = service.request("GET", HEALTH_PATH)

    assert status == 200
    assert json.loads(raw) == {"status": "ok", "service": "agenerp-explain"}
    assert service.port != 0, "内核没有分配端口 ⇒ 根本没绑上"


def test_c1_explain_answers_over_a_real_socket(live):
    """① `/explain` 在**真端口**上跑完一次完整解释并回 200 + 答案 + 四项账。"""
    service = live()
    status, raw = service.request(
        "POST",
        EXPLAIN_PATH,
        headers={"Cookie": cookie(serve_fakes.VALID_SID)},
        payload={"question": QUESTION},
    )
    payload = json.loads(raw)

    assert status == 200
    assert payload["user"] == serve_fakes.SESSION_USER
    assert payload["answer"]
    assert set(payload["cost"]["total"]) == {"prompt", "completion", "reasoning", "cached", "total"}


@pytest.mark.parametrize(
    "method, path, expected",
    [
        ("GET", "/nope", 404),
        ("POST", "/nope", 404),
        ("GET", "/agenerp", 404),
        ("POST", HEALTH_PATH, 405),
        ("GET", EXPLAIN_PATH, 405),
    ],
)
def test_c1_unknown_paths_and_wrong_methods(live, method, path, expected):
    """① 未知路径 404、方法不对 405（`D-a-4` 表末两行）。**M9 在这里红。**"""
    service = live()
    status, raw = service.request(method, path, payload={} if method == "POST" else None)

    assert status == expected
    assert "error" in json.loads(raw)


def test_c1_the_404_body_does_not_echo_the_request_path(live):
    """① 404 的回包**不回显调用方给的路径** —— 回显就是一条反射面。"""
    service = live()
    _, raw = service.request("GET", "/agenerp/<script>bing</script>")

    assert b"script" not in raw


# ── ②③ 身份：认不到人一律 401，且没有第二条路 ─────────────────────────────


@pytest.mark.parametrize(
    "cookie_header",
    [None, "", "other=1", "sid=", "sid=   ", "sid=;other=2"],
    ids=["no-header", "empty", "no-sid", "empty-sid", "blank-sid", "empty-sid-among-others"],
)
def test_c2_without_a_usable_sid_it_is_401_and_the_site_is_never_touched(cookie_header):
    """② 拿不到 `sid` → 401，**且一个站点请求都没发出去**。

    「不打站点」这半条是要点：它排除了「先拿别的凭据去问一次，问不出来才 401」那种实现。
    M2「缺 `sid` 时不 401 照常跑」在这里红。
    """
    site = serve_fakes.sid_site()
    status, message = status_of(deps_for(site), cookie_header=cookie_header)

    assert status == 401
    assert message == serve_app.UNAUTHENTICATED
    assert site.requests == [], f"401 之前不该打站点，却打了 {site.paths}"


def test_c3_a_sid_the_site_does_not_know_is_401(): 
    """③ `sid` 有值但站点认不出（活站点实测回 403 ⇒ `SiteError`）→ 401。

    M3「`SiteError` 被吞掉后继续」在这里红：吞掉之后这条会拿到 200。
    """
    site = serve_fakes.sid_site()
    status, message = status_of(deps_for(site), sid=serve_fakes.FORGED_SID)

    assert status == 401
    assert message == serve_app.UNAUTHENTICATED
    assert site.paths == [serve_fakes.LOGGED_USER_PATH], "认人这一跳该发生且只发生一次"


def test_c3_the_401_text_never_leaks_the_sites_own_words():
    """③ 401 的文案是**本仓固定文案**，不透传站点原文。

    站点那句 `Function ... is not whitelisted` 是误导性的（活站点实测见
    `docs/analysis/2026-08-25-1159-explain-service-sid-probe.md` 第 a 行），
    而且透传等于给站点内部信息开一条经由本服务到浏览器的路。
    """
    _, message = status_of(deps_for(), sid=serve_fakes.FORGED_SID)

    assert "whitelist" not in message.lower()
    assert "PermissionError" not in message
    assert "session_expired" not in message


# ── ④ 好 `sid` → 200，且 `user` 就是站点解析出的那个人 ──────────────────────


@pytest.mark.parametrize(
    "sid, expected",
    [
        (serve_fakes.VALID_SID, serve_fakes.SESSION_USER),
        (serve_fakes.OTHER_SID, serve_fakes.OTHER_USER),
    ],
)
def test_c4_the_user_handed_to_explain_comes_from_the_sid(sid, expected):
    """④ 断言落在**传给 `explain()` 的实参**上，且**随 `sid` 变**。

    两个 `sid` 参数化是关键：只测一个的话，「真的解析了」与「写死了一个默认值」
    分不开。M10「`user` 从请求体取而不是从 `sid` 解析」在这里红
    —— 请求体里根本没有 `user`（给了是 400，见判据⑦）。
    """
    spy = SpyExplain()
    payload = ask(deps_for(explain_fn=spy), sid=sid)

    assert spy.last["user"] == expected
    assert payload["user"] == expected


def test_c4_the_response_carries_the_four_token_columns():
    """④ 四项 token 账随响应回，且 **`cached` 不进 `total`**（§7.11 / §7.17 的既定口径）。"""
    payload = ask(deps_for())
    total = payload["cost"]["total"]

    assert payload["cost"]["calls"] >= 1
    assert total["total"] == total["prompt"] + total["completion"]
    assert total["reasoning"] > 0, "剧本模型自报了 reasoning，账里却是 0 ⇒ 这一栏被折掉了"
    # M4「只记 completion 不记 reasoning」在上一行红。
    assert set(total) == {"prompt", "completion", "reasoning", "cached", "total"}


# ── ⑤⑥ 「未配置」与「坏了」在响应上分得开 ───────────────────────────────────


@pytest.fixture
def no_llm_env(monkeypatch):
    """把三个 `AGENERP_LLM_*` 逐个抹掉 —— 「一个 AI 变量都不配」的那台机器。"""
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    return REQUIRED_ENV


def test_c5_unconfigured_llm_is_503_and_names_the_missing_variables(no_llm_env):
    """⑤ 未配置 → **503**，且消息里**逐个指名**缺的变量。

    503（服务暂时不可用，缺外部能力）与 502（上游坏了）分开的依据是**结构性**的：
    服务面先显式取一次配置，这一步抛就是「未配置」。不靠读异常文本猜。
    M6「未配置时回 200 空回答」在这里红 —— 空回答与「模型选择不作答」长得一样。
    """
    deps = ServiceDeps(
        site=SITE,
        site_transport=serve_fakes.sid_site(),
        models=fakes.models(),
        llm_transport=serve_fakes.scripted_model(),
    )
    status, message = status_of(deps)

    assert status == 503
    for name in no_llm_env:
        assert name in message


def test_c5_a_broken_upstream_is_502_not_503():
    """⑤ 配置取到了、之后才抛的 `RoutingError` → **502**。

    两格必须分开：把「上游坏了」说成「你没配」，人会去改一份本来就对的配置。
    """
    spy = SpyExplain(raises=RoutingError("模型回包不成形"))
    status, message = status_of(deps_for(explain_fn=spy))

    assert status == 502
    assert "不成形" in message


def test_c6_the_service_starts_and_health_is_200_with_no_llm_configured(live, no_llm_env):
    """⑥ 三个变量全空时**进程照样起得来**，`/health` 回 200。

    这正是 P1.8a 验收里「零依赖启动门禁须仍绿」在本服务上的那一半：
    外部能力缺失是**未配置**状态，不是错误状态（`docker-compose.yml` 文件头规则 ②）。
    """
    service = live(config_factory=serve_app.config_from_env)
    status, raw = service.request("GET", HEALTH_PATH)

    assert status == 200
    assert json.loads(raw)["status"] == "ok"


def test_c6_health_reads_no_llm_variable_at_all():
    """⑥ `/health` 的实现里**一个 `AGENERP_LLM_*` 都读不到**（M5 在这里红）。

    行为面（上一条）只能证明「这一次没读」；本条扫的是「代码里根本没有读的路径」。
    """
    source = ast.parse(pathlib.Path(serve_app.__file__).read_text(encoding="utf-8"))
    handler = next(
        node for node in ast.walk(source)
        if isinstance(node, ast.FunctionDef) and node.name == "do_GET"
    )
    literals = {
        node.value for node in ast.walk(handler)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    names = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}

    assert not any(name in literals for name in REQUIRED_ENV)
    assert "config_from_env" not in names
    assert "environ" not in {
        node.attr for node in ast.walk(handler) if isinstance(node, ast.Attribute)
    }


# ── ⑦ `assemble()` 六个入参的出处，逐个可判（§7.20 `D-a-3b` 一格一条）──────


def immediate_of(spy: SpyExplain):
    context = spy.last["immediate"]
    assert context is not None, "给了 doctype/name 却没有 ① 上下文"
    return context


def test_c7_doctype_and_name_come_from_the_request_body():
    """⑦ `doctype` / `name` 两格：**请求体**给。它们是「指名读哪份单据」，不是权限声明。"""
    spy = SpyExplain()
    ask(spy_deps := deps_for(explain_fn=spy), doctype="Sales Order", name=fakes.ORDER_B)
    document = immediate_of(spy).document

    assert (document.doctype, document.name) == ("Sales Order", fakes.ORDER_B)
    assert spy_deps.site == SITE


def test_c7_fields_are_fetched_server_side_with_the_callers_own_sid():
    """⑦ `fields` 落 **(A)**：服务端用**调用者自己的 `sid`** 现取（`D-a-3` 的 (iii) 本体）。

    两半都要判：① 站点上真的被打了那一跳；② 那一跳带的 `Cookie` 就是调用者的 `sid`
    —— 只判第一半的话，「用服务端自己的凭据去取」也能过。
    """
    site = serve_fakes.sid_site()
    spy = SpyExplain()
    ask(deps_for(site, explain_fn=spy), sid=serve_fakes.OTHER_SID,
        doctype="Sales Order", name=fakes.ORDER_A)

    fetch = f"/api/resource/Sales Order/{fakes.ORDER_A}"
    assert fetch in site.paths, f"字段表没从站点取，站点只被打了 {site.paths}"
    assert set(site.sids) == {serve_fakes.OTHER_SID}, "有一跳没用调用者的 sid"
    assert site.authorizations == [None] * len(site.requests), "sid 模式下不该发 Authorization"

    # 字段值经 §7.5 的自由文本边界标记包过一层（`assemble()` 的既有行为，本 plan 不改），
    # 所以判「站点取回的值在里面」，不判逐字相等。
    fields = immediate_of(spy).document.fields
    assert "北方新能源工程有限公司" in fields["customer"]


def test_c7_a_document_the_caller_cannot_read_is_403_and_never_reaches_the_model():
    """⑦ Frappe 判无权 → **403**，且**模型一次都没被调到**。

    403 这一格是执行期补的（§7.20 `D-a-4` 补格 1）：把「你无权看这份单据」说成 401
    会让调用方去做一次无用的重登录。
    """
    site = serve_fakes.sid_site()
    site.deny("Sales Order", fakes.ORDER_A)
    model = serve_fakes.scripted_model()
    spy = SpyExplain()
    deps = deps_for(site, explain_fn=spy, llm_transport=model)

    status, message = status_of(deps, doctype="Sales Order", name=fakes.ORDER_A)

    assert status == 403
    assert fakes.ORDER_A in message
    assert "PermissionError" not in message
    assert spy.calls == [], "被拒的单据不该进模型"


def test_c7_role_is_the_person_the_sid_resolved_to():
    """⑦ `role` 落 **(A)**：服务端把 `sid` 解析出的**那个人**放进去。

    ⚠️ 它的字面就是身份词 —— 调用方自称的 role 与 `sid` 解析出的人不是同一件事，
    因此它**绝不落 (B)**。随 `sid` 变这一半排除了「写死一个常量」。
    """
    spy = SpyExplain()
    ask(deps_for(explain_fn=spy), sid=serve_fakes.OTHER_SID,
        doctype="Sales Order", name=fakes.ORDER_A)

    assert immediate_of(spy).role == serve_fakes.OTHER_USER
    assert immediate_of(spy).role == spy.last["user"]


def test_c7_view_and_actions_are_server_side_constants():
    """⑦ `view` / `actions` 落 **(C)**：服务端写死。

    `actions` 是「**已执行动作的审计记录**」（§8.2 的 `TIER_ACTIONS`，不可压缩）——
    让调用方声明「我已经执行过什么」＝让外部输入伪造一份审计记录喂给模型。
    本期服务不执行任何动作 ⇒ 它按构造就该是空。
    """
    spy = SpyExplain()
    ask(deps_for(explain_fn=spy), doctype="Sales Order", name=fakes.ORDER_A)
    context = immediate_of(spy)

    assert context.view == SERVICE_VIEW == "explain-service"
    assert context.actions == SERVICE_ACTIONS == ()


@pytest.mark.parametrize(
    "key, value",
    [
        ("fields", {"customer": "我说了算"}),
        ("role", "System Manager"),
        ("view", "form"),
        ("actions", ["submitted"]),
        ("user", "Administrator"),
    ],
)
def test_c7_caller_claimed_context_is_400_not_silently_ignored(key, value):
    """⑦ 五个越权向量：请求体给了 → **400 并指名是哪个键**，**不是静默忽略**。

    静默忽略之后，「调用方试图越权」与「调用方没试」在事后无从分辨 ——
    那是一条没人看得见的攻击面。M7「请求体字段表直接透传」在这里红。
    """
    spy = SpyExplain()
    status, message = status_of(deps_for(explain_fn=spy), **{key: value})

    assert status == 400
    assert key in message
    assert spy.calls == []


@pytest.mark.parametrize(
    "payload, hint",
    [
        ({}, "question"),
        ({"question": ""}, "question"),
        ({"question": "  "}, "question"),
        ({"question": 7}, "question"),
        ({"question": QUESTION, "task_class": "no-such-class"}, "task_class"),
        ({"question": QUESTION, "doctype": "Sales Order"}, "name"),
        ({"question": QUESTION, "name": fakes.ORDER_A}, "doctype"),
        ({"question": QUESTION, "extra": 1}, "extra"),
    ],
)
def test_c7_a_malformed_body_is_400_and_names_the_key(payload, hint):
    """⑦ 请求体不成形 → 400 **并指名是哪个键**（`D-a-4` 第三行）。

    `task_class` 那一格是执行期补的（补格 2）：未知类目抛的 `DeclarationError` 是
    `RoutingError` 的**子类**，不在请求层先判就会掉进 502 ——
    把「调用方写错了参数」说成「上游坏了」。
    """
    deps = deps_for()
    with pytest.raises(ServiceError) as caught:
        handle_explain(
            deps,
            cookie_header=cookie(serve_fakes.VALID_SID),
            raw_body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    assert caught.value.status == 400
    assert hint in caught.value.message


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1,2]", b'"a string"', b"\xff\xfe"])
def test_c7_a_body_that_is_not_a_json_object_is_400(raw):
    deps = deps_for()
    with pytest.raises(ServiceError) as caught:
        handle_explain(deps, cookie_header=cookie(serve_fakes.VALID_SID), raw_body=raw)

    assert caught.value.status == 400


# ── ⑧⑩ AST 扫 `agenerp/serve/**` 全文 ───────────────────────────────────────

# 凭据零件（判据⑧）。⚠️ **只禁 `client_from_env` 挡不住等价回退**
# `SiteClient(site, admin_password=credential_from_env(ADMIN_PASSWORD_ENV))` ——
# 那条路一个 `client_from_env` 都不用。所以取件的函数与四个 `*_ENV` 常量一并禁。
CREDENTIAL_PARTS = (
    "client_from_env",
    "credential_from_env",
    "ADMIN_PASSWORD_ENV",
    "ADMIN_USER_ENV",
    "API_KEY_ENV",
    "API_SECRET_ENV",
    "AGENERP_ADMIN_PASSWORD",
    "AGENERP_ADMIN_USER",
    "AGENERP_API_KEY",
    "AGENERP_API_SECRET",
)

# 写方法（判据⑩）。`SiteClient` 的四条写方法 + 裸 `post_method`。
# 非 `GET` 但**只读**的白名单方法。`call_method()` 一律走 POST（`site.py:312`），
# 动词分不出读写 ⇒ 逐个点名。名单之外的非 GET 一律算写。
READONLY_METHODS = frozenset(
    {"frappe.auth.get_logged_user", "frappe.client.has_permission"}
)

WRITE_PARTS = (
    "create_doc",
    "ensure_doc",
    "submit_doc",
    "delete_custom_field",
    "post_method",
)


def serve_sources() -> dict[str, str]:
    """`agenerp/serve/**` 的**全部** `.py` 源码。**一个文件都不许漏。**

    按目录遍历而不是逐个点名：新加一个模块就自动进扫描面，
    否则「加了个 `helpers.py` 把回退藏在里面」这条路没人挡。
    """
    files = sorted(SERVE_PACKAGE.rglob("*.py"))
    assert files, f"{SERVE_PACKAGE} 下一个 .py 都没有 ⇒ 扫描面是空的"
    return {str(f.relative_to(SERVE_PACKAGE)): f.read_text(encoding="utf-8") for f in files}


def identifiers_and_strings(source: str) -> set[str]:
    """AST 面 + 字面量面双扫：名字、属性名、字符串常量。

    只扫 `ast.Name` 挡不住 `getattr(mod, "client_from_env")`，也挡不住直接写
    `os.environ["AGENERP_ADMIN_PASSWORD"]` —— 字面量那一半不是冗余。
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)
    return found


@pytest.mark.parametrize("relative", sorted(serve_sources()))
def test_c8_the_service_surface_holds_zero_credential_parts(relative):
    """⑧ 服务面**零凭据零件**（逐文件参数化 —— 哪个文件破的当场看得见）。

    与 `tests/unit/test_site_client_sid.py` 判据⑧ 是同一条道理的两侧：
    那条扫工厂函数，本条扫服务面。M1 / M11 都在这里红。
    """
    leaked = sorted(identifiers_and_strings(serve_sources()[relative]) & set(CREDENTIAL_PARTS))

    assert leaked == [], f"agenerp/serve/{relative} 里出现了凭据零件：{leaked}"


def test_c8_the_only_way_the_service_builds_a_client_is_the_injected_factory():
    """⑧ 服务面**不自己构造 `SiteClient`** —— 唯一的路是注入进来的那个工厂。

    ⚠️ 这半条比禁用名单更根本：名单挡的是「用了哪个零件」，本条挡的是
    「有没有第二条造客户端的路」。`SiteClient(...)` 一旦出现在服务面，
    它想怎么认证就怎么认证，禁用名单再长也拦不住下一个花样。
    """
    for relative, source in serve_sources().items():
        found = identifiers_and_strings(source)
        assert "SiteClient" not in found, f"agenerp/serve/{relative} 自己构造了 SiteClient"

    assert ServiceDeps.client_factory is client_from_sid, (
        "产品路径上的默认工厂必须就是 client_from_sid —— 默认值才是没人显式传参时真正走的那条"
    )


def test_c8_the_credential_scan_actually_has_teeth():
    """⑧ **扫描器自证有牙**：把两条等价回退喂给它，必须都被抓住。

    没有这一条的话，一个「永远返回空集」的扫描器也能让上面两条全绿。
    """
    obvious = "def f(site, sid):\n    return client_from_env()\n"
    equivalent = (
        "def f(site, sid):\n"
        "    return SiteClient(site, admin_password=credential_from_env(ADMIN_PASSWORD_ENV))\n"
    )
    sneaky = "import os\n\ndef f():\n    return os.environ['AGENERP_ADMIN_PASSWORD']\n"

    for source in (obvious, equivalent, sneaky):
        assert identifiers_and_strings(source) & set(CREDENTIAL_PARTS), source
    assert "SiteClient" in identifiers_and_strings(equivalent)


@pytest.mark.parametrize("relative", sorted(serve_sources()))
def test_c10_the_service_surface_holds_zero_write_methods(relative):
    """⑩ 服务面**零写方法**（Non-Goal 5：②端只读，写方法不进服务面）。

    风险档自评落 L0 靠的就是这一条（§7.20 `D-a-6`）—— 它是自评的**判据**，不是复述。
    """
    used = sorted(identifiers_and_strings(serve_sources()[relative]) & set(WRITE_PARTS))

    assert used == [], f"agenerp/serve/{relative} 里出现了写方法：{used}"


def test_c10_the_write_scan_actually_has_teeth():
    """⑩ 扫描器自证有牙：五个写零件逐个喂进去，必须都被抓住。"""
    for part in WRITE_PARTS:
        assert identifiers_and_strings(f"def f(c):\n    return c.{part}()\n") & set(WRITE_PARTS)


def test_c10_the_service_never_sends_a_non_get_to_the_site_except_reading_who_you_are():
    """⑩ 行为面的另一半：一次完整解释里，站点上**没有一条写请求**。

    AST 面判「代码里没有写零件」，本条判「这一次真的没写」。两者不重复。
    `POST /api/method/frappe.auth.get_logged_user` 是**只读白名单方法**
    （活站点实测第 f 行），它是这条判据里唯一允许的非 `GET`。
    """
    site = serve_fakes.sid_site()
    ask(deps_for(site), doctype="Sales Order", name=fakes.ORDER_A)

    # `/api/resource/**` 上**一条非 GET 都不许有** —— 写单据只能走那条路。
    resource_writes = [
        (r.method, path)
        for r, path in zip(site.requests, site.paths)
        if path.startswith("/api/resource") and r.method != "GET"
    ]
    assert resource_writes == [], f"服务面往 /api/resource 发了非 GET：{resource_writes}"

    # 非 GET 的 `/api/method/**` 只允许**已声明的只读白名单方法**。
    # `call_method()` 一律用 POST（`site.py:312` 逐字），所以动词本身分不出读写，
    # 只能按方法名逐个点名 —— 名单之外的一律算写。
    methods = {
        path[len("/api/method/") :]
        for r, path in zip(site.requests, site.paths)
        if r.method != "GET" and path.startswith("/api/method/")
    }
    assert methods <= READONLY_METHODS, f"服务面调了名单外的方法：{sorted(methods - READONLY_METHODS)}"
    assert "frappe.auth.get_logged_user" in methods, "认人那一跳没发生 ⇒ 这条判据没判到东西"


# ── ⑨ `sid` 不进回包、不进日志 ──────────────────────────────────────────────


def test_c9_no_response_body_ever_contains_the_sid(live):
    """⑨ 四条路径的回包**逐字节**不含 `sid` 值（M8「响应回显 `sid`」在这里红）。

    `sid` 是明文短期凭据：回包会进浏览器控制台、进代理日志、进用户贴出来的截图。
    """
    service = live()
    raw_sid = serve_fakes.VALID_SID.encode("utf-8")
    header = {"Cookie": cookie(serve_fakes.VALID_SID)}

    seen = [
        service.request("GET", HEALTH_PATH, headers=header)[1],
        service.request("GET", "/nope", headers=header)[1],
        service.request("POST", EXPLAIN_PATH, headers=header, payload={"question": QUESTION})[1],
        service.request("POST", EXPLAIN_PATH, headers=header, payload={"role": "x"})[1],
        service.request("POST", EXPLAIN_PATH, payload={"question": QUESTION})[1],
    ]

    for raw in seen:
        assert raw_sid not in raw, raw
    # ⚠️ 判的是 **`sid` 的值**，不是「sid」这三个字母：400 的文案里就有一句
    # 「一律由服务端按调用者自己的 sid 产出」——那是**说明**，不是泄漏。
    # 把字面词也禁掉会逼着把话说得含糊，那对调用方是净损失。


def test_c9_no_log_line_ever_contains_the_sid_or_the_callers_query_string():
    """⑨ 日志行只由本服务自己拼，**只有方法与不带 query 的路径**。

    默认 `log_message` 会把整条请求行打出去，而 query 串是调用方能控制的 ——
    那是一条「调用方能往日志里塞任意内容」的路。
    """
    lines: list[str] = []
    server = build_server(
        site=SITE,
        port=0,
        site_transport=serve_fakes.sid_site(),
        models=fakes.models(),
        doctypes=list(fakes.SCOPE_CANDIDATES),
        config_factory=fakes.config,
        llm_transport=serve_fakes.scripted_model(),
        log_sink=lines.append,
    )
    service = LiveService(server)
    try:
        service.request(
            "POST",
            f"{EXPLAIN_PATH}?leak=INJECTED&sid={serve_fakes.VALID_SID}",
            headers={"Cookie": cookie(serve_fakes.VALID_SID)},
            payload={"question": QUESTION},
        )
        service.request("GET", f"{HEALTH_PATH}?leak=INJECTED")
    finally:
        service.close()

    assert lines, "一行日志都没有 ⇒ 这条判据没判到东西"
    for line in lines:
        assert serve_fakes.VALID_SID not in line, line
        assert "INJECTED" not in line, line
        assert "?" not in line, line
    assert f"POST {EXPLAIN_PATH}" in lines
    assert f"GET {HEALTH_PATH}" in lines


def test_c9_the_service_error_texts_never_carry_the_sid():
    """⑨ 异常文本这一路也不带 `sid` —— 它常常是被打进日志的那一份。"""
    for sid in (serve_fakes.FORGED_SID, serve_fakes.VALID_SID):
        _, message = status_of(deps_for(), sid=sid, role="System Manager")
        assert sid not in message
