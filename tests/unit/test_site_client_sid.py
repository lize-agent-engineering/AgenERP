"""非门禁测试 · 钉死 `SiteClient` 的**第三条认证模式 `sid`**（P1.8 下半 Phase 2）。

出处：plan `docs/plans/p1-insight/2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`
的 `Decision D-下-1`；owner doc 是 `docs/architecture/module-boundaries.md` §7.14
（输入契约 §7.13 的 **D2**：身份口径 = 当前登录用户，Administrator 被逐字判为一次**已知的信息越权**）。

**每条判据都注明它挡的是哪种假实现** —— 这一组的共同敌人只有一个：
**「`sid` 失效时静默降级成管理员」**。它有两种藏法，因此这里有两类判据：

- **行为反测**（①②③）：这一次没有降级 —— 请求里既没有 `Authorization`，也没有 `login`。
- **构造判据**（⑧）：压根降级不了 —— `client_from_sid` 的函数体里一个凭据零件都没有。

两类都要。只做行为反测，一条 `if sid_invalid: fall back` 的分支在「sid 有效」的用例里
永远不会被走到，判据会**全绿而回退真的存在**。

⚠️ **本文件不连真站点、不起本地端口**，理由与 `tests/unit/test_site_client.py` 模块头一致。
⚠️ **本文件一个字都不改 `tests/unit/test_site_client.py`**，写方法登记面（判据⑦）
   **复用那边的 `WRITE_METHOD_ALLOWLIST`，不抄第二套** —— 抄一套就等于把那道守卫复制成两份，
   改其中一份的人不会知道另一份还在。
"""

import ast
import inspect
import json

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
    client_from_sid,
)

from explain_fakes import load_repo_module

# `tests/` 下没有 `__init__.py`，同目录模块不能用相对 import。
# 复用 `explain_fakes.load_repo_module`（先注册进 `sys.modules` 再 `exec_module`）——
# **不抄第二套加载器**，理由与它自己的 docstring 一致。
_SITE_CLIENT_TESTS = load_repo_module("tests/unit/test_site_client.py", "_p1_8_test_site_client")

WRITE_METHOD_ALLOWLIST = _SITE_CLIENT_TESTS.WRITE_METHOD_ALLOWLIST
FakeTransport = _SITE_CLIENT_TESTS.FakeTransport
_public_methods = _SITE_CLIENT_TESTS._public_methods

SID = "a-fake-but-well-formed-session-token-0123456789"
BASE = "http://127.0.0.1:18080"


def _sid_client(transport, sid=SID):
    return SiteClient("frontend", base_url=BASE, sid=sid, transport=transport)


# ① ---------------------------------------------------------------------------


def test_sid_mode_sends_the_cookie_header():
    """① `sid` 模式下请求头**有** `Cookie: sid=<那一串>`，且值与传进去的**逐字相同**。

    挡的假实现：`_headers()` 压根不发 `Cookie`（**M1**）—— 那样服务端认不出浏览器里那个人，
    整条 D3⑦ 变成同义反复：客户端说它转发了，站点那边什么都没收到。
    """
    transport = FakeTransport()

    _sid_client(transport).get("/api/method/frappe.auth.get_logged_user")

    assert transport.last.headers["Cookie"] == f"sid={SID}"


# ② ---------------------------------------------------------------------------


def test_sid_mode_sends_no_authorization_header():
    """② `sid` 模式下**没有** `Authorization` 头。

    挡的假实现：把 `sid` 加成「额外一个头」而 token 照发 —— 站点会优先认 token，
    于是「用那个人的身份读」在浏览器看来生效了，实际读的是 token 那个身份。
    """
    transport = FakeTransport()

    _sid_client(transport).get("/api/resource/Item")

    assert "Authorization" not in transport.last.headers


# ③ ---------------------------------------------------------------------------


def test_sid_mode_issues_zero_login_requests():
    """③ `sid` 模式下**没有任何** `POST /api/method/login`（逐条断言假传输记下的全部请求）。

    挡的假实现：`_ensure_authenticated()` 在 `sid` 模式下仍走会话登录（**M2**）——
    那就是回退链本身：一次登录换来的是**管理员**会话，`sid` 只是被白发了一次。
    """
    transport = FakeTransport()

    _sid_client(transport).get("/api/resource/Item")

    assert [(r.method, r.url) for r in transport.requests] == [
        ("GET", f"{BASE}/api/resource/Item")
    ]
    assert not any("login" in r.url for r in transport.requests)


def test_sid_mode_issues_zero_login_requests_even_across_many_calls():
    """③ 的补丁：多次调用也不许在某一次上偷偷登录一下。

    挡的假实现：只在第一次请求前判 `sid`，之后某条路径把 `_authenticated` 重置了。
    """
    transport = FakeTransport()
    client = _sid_client(transport)

    client.get("/api/resource/Item")
    client.get("/api/resource/Work Order")
    client.get("/api/method/frappe.auth.get_logged_user")

    assert all(r.method == "GET" for r in transport.requests)
    assert len(transport.requests) == 3


# ④ ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, other",
    [
        ({"api_key": "k", "api_secret": "s"}, "api_key/api_secret"),
        ({"api_key": "k"}, "api_key/api_secret"),
        ({"api_secret": "s"}, "api_key/api_secret"),
        ({"admin_password": "secret"}, "admin_password"),
    ],
)
def test_sid_is_mutually_exclusive_with_the_other_two_and_names_the_conflict(kwargs, other):
    """④ `sid` 与另两种凭据**两两同给即报错**，且消息里**指名冲突的是哪两个**。

    挡的假实现：静默取其一。留着另一份凭据就等于把回退链的燃料留在构造里——
    今天不回退，明天有人加一行 `except` 就回退了，而判据看不见。

    ⚠️ **定界（本 plan 的执行期偏离，照实记）**：plan 判据④ 原文写的是
    「**三种**凭据两两同给即报错」。执行期实读发现第三对
    （`api_key/api_secret` + `admin_password`）是模块**原有**的「token 优先、会话登录回退」，
    `tests/unit/test_site_client.py` 的 `_client()` 助手正是这么构造客户端的
    （`admin_password` 默认给上，用例再补 `api_key`/`api_secret`）。
    把那一对也判成错，会打红 **21 条既有判据**，而本 plan 的 Exit Criteria 逐字要求
    `git diff -- tests/unit/test_site_client.py` **无输出**，R5 也逐字写着
    「改动只加一条互斥模式、**不碰既有两条路径**」。
    → **取窄：`sid` ⊥ 另两者，既有那一对一个字不改。** 见下一条判据。
    """
    with pytest.raises(SiteError) as excinfo:
        SiteClient("frontend", base_url=BASE, sid=SID, **kwargs)

    message = str(excinfo.value)
    assert "sid" in message
    assert other in message


def test_the_pre_existing_token_plus_password_pair_is_untouched():
    """④ 的定界判据：既有的 `api_key/api_secret` + `admin_password` 那一对**仍然合法**。

    挡的是本 plan 自己的越界：把互斥写宽一格就顺手推翻了模块原有的回退语义，
    而那不在本 plan 的 Targets 里。这条钉住「本次一个字未改」是**可判的**，不是一句声明。
    """
    client = SiteClient(
        "frontend", base_url=BASE, api_key="k", api_secret="s",
        admin_password="secret", transport=FakeTransport(),
    )

    assert client._headers(False)["Authorization"] == "token k:s"


# ⑤ ---------------------------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n  "])
def test_blank_sid_raises_instead_of_being_treated_as_absent(blank):
    """⑤ `sid` 为空串 / 全空白 → 报错，**不静默当成「没给」**（**M23**）。

    挡的假实现：`if sid:` 把空串读成「没给 sid」，于是客户端**退回**到别的凭据模式。
    浏览器那边只要 `sid` 取不到（例如它是 `HttpOnly` —— Phase 1 实测正是如此），
    就会一路静默滑到管理员身份，而没有任何一条日志会说这件事发生过。
    """
    with pytest.raises(SiteError) as excinfo:
        SiteClient("frontend", base_url=BASE, sid=blank, transport=FakeTransport())

    assert "sid" in str(excinfo.value)


def test_sid_none_is_still_a_legitimate_absence():
    """⑤ 的反面：`sid=None`（真的没给）**不是**错误，否则既有两条路径全部构造不出来。"""
    client = SiteClient("frontend", base_url=BASE, admin_password="secret",
                        transport=FakeTransport())

    assert "Cookie" not in client._headers(False)


# ⑥ ---------------------------------------------------------------------------


def test_site_error_message_never_carries_the_sid_value():
    """⑥ `SiteError` 的消息里**不出现** `sid` 的值（故意让站点回 500，搜那一串）。

    挡的假实现：把请求头拼进异常消息以便"好排查"（**M21**）。
    `sid` 是明文短期凭据；异常消息会进日志、进证据文件、进 issue，
    一旦带上它，「不落盘、不进日志」那三条缓解全部作废。
    """
    transport = FakeTransport([SiteResponse(500, json.dumps({"exception": "boom"}))])

    with pytest.raises(SiteError) as excinfo:
        _sid_client(transport).get("/api/resource/Item")

    assert SID not in str(excinfo.value)


def test_site_error_message_carries_no_request_headers_at_all():
    """⑥ 的构造侧：异常消息里**一个请求头名都不出现** —— 不只是 `sid` 那一串。

    只搜 `sid` 的值会被「把头名和值分开拼」绕过；这条把整个请求头面挡在消息之外。
    """
    transport = FakeTransport([SiteResponse(500, json.dumps({"exception": "boom"}))])

    with pytest.raises(SiteError) as excinfo:
        _sid_client(transport).get("/api/resource/Item")

    message = str(excinfo.value)
    for header in ("Cookie", "Authorization", "Host:", "Accept:"):
        assert header not in message


# ⑦ ---------------------------------------------------------------------------


def test_the_write_registration_surface_is_unchanged_by_the_sid_mode():
    """⑦ 写方法登记面**未变**：公开写方法集合与 `WRITE_METHOD_ALLOWLIST` 逐字相等（**M24**）。

    挡的假实现：借这次认证面改动顺手加一个写方法。本 plan 通篇声称对活站点**只读**
    （Non-Goals 4），这条把那句声明变成可判的。

    ⚠️ 白名单**从 `tests/unit/test_site_client.py` 导入**，不在本文件抄第二套 ——
    抄一套就等于把守卫复制成两份，改其中一份的人不会知道另一份还在。
    """
    offenders = [
        name for name in _public_methods()
        if any(verb in name.split(".")[-1].lower() for verb in WRITE_VERBS)
        and name not in WRITE_METHOD_ALLOWLIST
    ]

    assert offenders == [], f"未登记的写方法：{offenders}；白名单={WRITE_METHOD_ALLOWLIST}"
    assert WRITE_METHOD_ALLOWLIST == (
        "SiteClient.delete_custom_field",
        "SiteClient.create_doc",
        "SiteClient.ensure_doc",
        "SiteClient.submit_doc",
    ), "写方法白名单变了 —— 本 plan 逐字声明它一个字不动"


# ⑧ ---------------------------------------------------------------------------

CREDENTIAL_PARTS: tuple[str, ...] = (
    "client_from_env",
    "credential_from_env",
    "os",
    "environ",
    "getenv",
    ADMIN_PASSWORD_ENV,
    API_KEY_ENV,
    API_SECRET_ENV,
    "ADMIN_PASSWORD_ENV",
    "API_KEY_ENV",
    "API_SECRET_ENV",
)


def _identifiers_and_strings(func) -> set[str]:
    """把一个函数体拆成「所有出现过的标识符 + 所有字符串字面量」。

    只扫字符串字面量会被**常量引用**整个绕过（`os.environ[ADMIN_PASSWORD_ENV]` 里
    一个字符串字面量都没有）；只扫标识符会被**拼出来的变量名**绕过。两个都扫。
    """
    tree = ast.parse(inspect.getsource(func).strip())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)
    return found


def test_client_from_sid_body_contains_zero_credential_parts():
    """⑧ `client_from_sid` 的函数体里**零凭据零件**（AST + 字面量双扫，**M20**）。

    挡的假实现：在工厂函数里加一句「`sid` 没给就 `client_from_env` 兜底」——
    那是回退链最省事的藏法，而且行为反测抓不到它（那些用例里 `sid` 总是给了的）。
    与 `tests/unit/test_explain_service.py` 的判据⑩ 是同一条道理的两侧：
    ⑩ 扫服务面，本条扫工厂函数。

    ⚠️ 这条与 ①②③ **不重复**：那三条判「这一次没回退」，本条判「代码里根本没有回退所需的零件」。
    """
    found = _identifiers_and_strings(client_from_sid)

    leaked = sorted(found & set(CREDENTIAL_PARTS))
    assert leaked == [], f"`client_from_sid` 的函数体里出现了凭据零件：{leaked}"


def test_the_credential_part_scan_actually_has_teeth():
    """⑧ 的变异自查：扫描器对一个**故意带凭据零件**的函数必须判成违规。

    没有这一条，`_identifiers_and_strings` 返回空集时上一条会**空转全绿**。
    """

    def _fabricated(site):
        return site_mod.client_from_env(site)

    found = _identifiers_and_strings(_fabricated)

    assert sorted(found & set(CREDENTIAL_PARTS)) == ["client_from_env"]


def test_client_from_sid_builds_a_client_that_only_sends_the_cookie():
    """⑧ 的行为侧：工厂函数造出来的客户端，请求头形状与手工构造的**逐字一致**。

    挡的假实现：工厂函数造的是另一种客户端（例如多塞一个 token），
    而上面全部判据测的都是手工构造的那个 —— 产品路径于是没有判据。
    """
    transport = FakeTransport()

    client = client_from_sid("frontend", SID, transport=transport)
    client.get("/api/resource/Item")

    assert transport.last.headers["Cookie"] == f"sid={SID}"
    assert "Authorization" not in transport.last.headers
    assert transport.last.method == "GET"
