"""非门禁测试 · 钉死站点只读传输的行为（`agenerp/site.py`）。

**不连真站点，也不起本地 `http.server`**：本机端口冲突已经是实测事实
（8080 被另一套常驻栈占着），在 `GATE_VERIFY` 与 CI 的 `gates-l1` 里再绑一个端口
是自找的不稳定源。传输是注入进来的假件，请求对象本身就是可断言的值。

唯一的例外是「连不上」那条：它必须走真的 `UrllibTransport`，因为假传输**证明不了**
真传输会把 `URLError` 翻成 `SiteError`。那条用一个刚释放的端口构造 connection refused，
不留下监听。
"""

import json
import socket

import pytest

from agenerp import site as site_mod
from agenerp.contracts import WRITE_VERBS
from agenerp.site import (
    ADMIN_PASSWORD_ENV,
    API_KEY_ENV,
    API_SECRET_ENV,
    SiteClient,
    SiteError,
    SiteResponse,
    UrllibTransport,
    client_from_env,
)

# 本 plan 的客户端只读，白名单为空。第 3 顺位加 `delete_custom_field` 时，
# 把它连同理由加进这个**可见的字面量**列表 —— 每加宽一次面就留一次痕。
WRITE_METHOD_ALLOWLIST: tuple[str, ...] = ()

ALL_ENV = (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV, "AGENERP_ADMIN_USER",
           "AGENERP_SITE_URL", "AGENERP_HTTP_PORT")


class FakeTransport:
    """记下每一次请求，按预设答复。默认答一个空的 Frappe 列表载荷。"""

    def __init__(self, responses=None):
        self.requests = []
        self._responses = list(responses or [])

    def __call__(self, request):
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return SiteResponse(200, json.dumps({"data": []}))

    @property
    def last(self):
        return self.requests[-1]


@pytest.fixture
def clean_env(monkeypatch):
    for name in ALL_ENV:
        monkeypatch.delenv(name, raising=False)


def _client(transport, **kwargs):
    kwargs.setdefault("base_url", "http://127.0.0.1:18080")
    kwargs.setdefault("admin_password", "secret")
    return SiteClient("frontend", transport=transport, **kwargs)


def test_non_2xx_raises_instead_of_returning_empty():
    """非 2xx 必须抛。返回空结果会让「未改动 → diff 为空」在站点报错时照样绿。"""
    transport = FakeTransport([SiteResponse(500, "boom")])

    with pytest.raises(SiteError) as excinfo:
        _client(transport, api_key="k", api_secret="s").get("/api/resource/Custom Field")

    assert "500" in str(excinfo.value)


def test_unauthorized_login_raises():
    """认证失败是站点侧失败，不是「站点上没有东西」。"""
    transport = FakeTransport([SiteResponse(401, '{"message":"Invalid login"}')])

    with pytest.raises(SiteError) as excinfo:
        _client(transport).get("/api/resource/Custom Field")

    assert "401" in str(excinfo.value)


def test_non_json_payload_raises():
    """载荷不是 JSON（例如被反代喂了一页 HTML）也必须抛，不许当成空。"""
    transport = FakeTransport([
        SiteResponse(200, json.dumps({"message": "Logged In"})),
        SiteResponse(200, "<html>login page</html>"),
    ])

    with pytest.raises(SiteError) as excinfo:
        _client(transport).get("/api/resource/Custom Field")

    assert "JSON" in str(excinfo.value)


def test_unreachable_site_raises_site_error():
    """连不上必须抛 `SiteError` —— 这条走真传输，假件证明不了 URLError 被翻译了。"""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # 端口立即释放：随后的连接必然被拒，且不留监听

    client = SiteClient(
        "frontend", base_url=f"http://127.0.0.1:{port}",
        api_key="k", api_secret="s", transport=UrllibTransport(timeout=5),
    )

    with pytest.raises(SiteError):
        client.get("/api/method/ping")


def test_missing_credentials_names_the_variables(clean_env):
    """缺凭据的报错必须指名缺哪个环境变量，否则人只知道「失败了」。"""
    with pytest.raises(SiteError) as excinfo:
        client_from_env("frontend")

    message = str(excinfo.value)
    for name in (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV):
        assert name in message, f"报错没指名 {name}：{message}"


def test_half_a_token_pair_is_an_error_not_a_silent_fallback(clean_env, monkeypatch):
    """只给 key 不给 secret = 配错。静默回退会让「token 没生效」完全看不见。"""
    monkeypatch.setenv(API_KEY_ENV, "k")
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, "admin")

    with pytest.raises(SiteError) as excinfo:
        client_from_env("frontend")

    assert API_SECRET_ENV in str(excinfo.value)


def test_no_builtin_password_default(clean_env, monkeypatch):
    """产品代码不内置口令默认值 —— conftest 里那个 `admin` 是测试脚手架，不是产品口径。"""
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, "")

    with pytest.raises(SiteError):
        client_from_env("frontend")


def test_token_credentials_skip_the_login_roundtrip(clean_env, monkeypatch):
    """配了 token 就不该再发登录请求（登录端点有速率限制，且会把口令带进每次运行）。"""
    monkeypatch.setenv(API_KEY_ENV, "k")
    monkeypatch.setenv(API_SECRET_ENV, "s")
    transport = FakeTransport()

    client_from_env("frontend", transport=transport).get("/api/method/ping")

    assert len(transport.requests) == 1, "token 认证下不该有登录往返"
    assert transport.last.headers["Authorization"] == "token k:s"


def test_session_login_is_the_fallback_and_happens_once():
    """没有 token 时回退会话登录，且只登一次 —— 每次调用都登录会撞上速率限制。"""
    transport = FakeTransport([
        SiteResponse(200, json.dumps({"message": "Logged In"})),
        SiteResponse(200, json.dumps({"data": []})),
        SiteResponse(200, json.dumps({"data": []})),
    ])
    client = _client(transport)

    client.get("/api/method/ping")
    client.get("/api/method/ping")

    methods = [r.method for r in transport.requests]
    assert methods == ["POST", "GET", "GET"], methods
    assert json.loads(transport.requests[0].body)["pwd"] == "secret"


def test_host_header_is_the_site_name():
    """gunicorn 按 Host 解析站点：打 127.0.0.1 会被当成一个叫 127.0.0.1 的站点而 404。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").get("/api/method/ping")

    assert transport.last.headers["Host"] == "frontend"


def test_path_is_url_encoded_keeping_slashes():
    """DocType 名带空格，不编码时 http.client 直接以 control characters 拒掉。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").get("/api/resource/Custom Field")

    url = transport.last.url
    assert "/api/resource/Custom%20Field" in url
    assert " " not in url


def test_list_resource_explicitly_disables_paging():
    """Frappe 的 `/api/resource` 默认只回 20 条。不显式关分页 = 一条静默截断的假绿。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")

    url = transport.last.url
    assert f"{site_mod.PAGE_LENGTH_PARAM}={site_mod.UNLIMITED_PAGE_LENGTH}" in url
    assert f"{site_mod.FIELDS_PARAM}=" in url
    assert "%2A" in url or "*" in url, f"没显式要全部字段：{url}"


def test_list_resource_returns_every_row_the_site_gave():
    """25 条（超过默认页长 20）必须一条不少地带回来。"""
    rows = [{"dt": "Item", "fieldname": f"probe_{i}"} for i in range(25)]
    transport = FakeTransport([SiteResponse(200, json.dumps({"data": rows}))])

    got = _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")

    assert len(got) == 25


def test_list_resource_rejects_a_payload_without_data():
    """载荷形状不对时抛，不返回空列表 —— 空列表会被读成「站点上没有定制」。"""
    transport = FakeTransport([SiteResponse(200, json.dumps({"exc": "boom"}))])

    with pytest.raises(SiteError):
        _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")


def _public_methods() -> list[str]:
    """`agenerp.site` 对外暴露的全部公开可调用名（模块级函数 + 公开类的公开方法）。"""
    names: list[str] = []
    for attr in dir(site_mod):
        if attr.startswith("_"):
            continue
        obj = getattr(site_mod, attr)
        if callable(obj) and getattr(obj, "__module__", "") == site_mod.__name__:
            names.append(attr)
            if isinstance(obj, type):
                names.extend(f"{attr}.{m}" for m in dir(obj) if not m.startswith("_"))
    return names


def test_site_module_exposes_no_unlisted_write_method():
    """只读不变量：公开方法名里出现写动词的，必须在**显式白名单**里（本 plan 白名单为空）。

    写成「一个写动词都不许出现」的话，第 3 顺位在同一个模块上加 `delete_custom_field`
    会被一条已关闭 plan 的判据当场打红 —— 那时只剩「动别人的判据」和「卡住」两条路。
    白名单让它按**收窄**演进：加一个写方法就要付一次 diff 和一次留痕。
    """
    offenders = [
        name for name in _public_methods()
        if any(verb in name.split(".")[-1].lower() for verb in WRITE_VERBS)
        and name not in WRITE_METHOD_ALLOWLIST
    ]

    assert offenders == [], f"未登记的写方法：{offenders}；白名单={WRITE_METHOD_ALLOWLIST}"


def test_the_allowlist_assertion_actually_has_teeth():
    """白名单断言不能是空转的：给它喂一个写方法名，它必须判成违规。"""
    verb = WRITE_VERBS[0]
    fabricated = f"SiteClient.{verb}_custom_field"

    assert any(v in fabricated.split(".")[-1].lower() for v in WRITE_VERBS)
    assert fabricated not in WRITE_METHOD_ALLOWLIST
