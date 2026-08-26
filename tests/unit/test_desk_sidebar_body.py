"""⌘K 侧边栏的**活体**断言体（§7.23.5）—— 真浏览器、真登录、真 Desk 页面。

**这一份是判据本体，`tests/ui/test_sidebar.py` 是它的严格模式。**
两处共用同一批断言，差别只有一个：**「跑不了」时这里 `skip`，那里 `fail`**。
取舍差是**有意的**：日常 `pytest tests/unit -q` 那一轮不该因为没起 docker 就整轮红
（那会让人学会忽略红）；门禁那一轮「跑不了 = 没跑 = 红」。

⚠️ **三条硬约束，违反任何一条都会把今天绿着的 `unit-and-contracts` 弄红（那是纯回归）**：

1. **模块顶层不许 `import playwright`。** runner 上只装 `pytest certifi`
   （`.github/workflows/gates.yml` 的 `unit-and-contracts`）⇒ 顶层导入的结果是
   收集期 `ImportError`，**那是 `error` 不是 `skip`**。驱动导入写在 fixture 体内。
2. **不许依赖 `pytest-playwright` 插件的任何 fixture**（`page` / `browser` / `context` /
   `browser_type`）与它的任何 CLI 选项 —— `ui` extra 里逐字只有 `playwright`，
   本机那份 `pytest-playwright` 是**碰巧装着**。用了它，runner 上是 `fixture not found`（`error`）。
3. **「跑不了」的出口一律只调 `_unavailable(reason)`，不许直调 `pytest.skip`。**
   加载器靠重绑这**一个**名字把整份断言体切成严格模式；直调就绕过了收严，
   门禁上会重新长出 skip —— 而「一条会 skip 的门禁等于一条不存在的门禁」。

**这三条各有一条离线源码守卫盯着**（`tests/unit/test_desk_sidebar_static.py` 的四条追加守卫），
**外加两条运行时实证**（`-p no:playwright` 一条 + 遮蔽 `playwright` 包一条），见 §7.23.5。
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ASSET = REPO / "agenerp" / "serve" / "assets" / "desk.js"

BASE_ENV = "AGENERP_SERVE_BASE_URL"
PORT_ENV = "AGENERP_HTTP_PORT"
ADMIN_USER_ENV = "AGENERP_ADMIN_USER"
ADMIN_PASSWORD_ENV = "AGENERP_ADMIN_PASSWORD"

EXPLAIN_PATH = "/agenerp/explain"
QUESTION = "这张单据现在什么情况？"

# 面板侧可分辨的九个码 + `200`，共 10 条。**两个 `502` 合并成一条是正确行为** ——
# 面板只看得见状态码，看不见它是谁回的；想分开只能嗅响应体，那撞上「响应体不进渲染面」。
# 按十种**来源**判是不可满足的（两个 502 必然全等），会把正确行为判成缺陷。
DISTINGUISHABLE_CODES = (200, 400, 401, 403, 404, 405, 500, 502, 503, 504)

# 未枚举的码。写死一个**服务端不会回**的值，判的是兜底态而不是某个真分支。
UNENUMERATED_CODE = 418

# ⚠️ **超时下限写死 ≥ 90 秒**：一次真解释实测中位约 50 秒，
# Playwright 默认 30 秒**会先超时** ⇒ 判据红在超时上、长得像「面板坏了」，
# 而实际是模型在正常作答。那是一条会把人引向错误根因的假红。
REAL_RESPONSE_TIMEOUT_MS = 120_000
STUB_RESPONSE_TIMEOUT_MS = 15_000


def _unavailable(reason: str):
    """**唯一的「跑不了」出口。**

    默认实现是 `skip`（`tests/unit` 那一轮）。
    `tests/ui/test_sidebar.py` 在加载完本模块之后把**这一个名字**重绑成 `pytest.fail`，
    整份断言体就切成了严格模式。

    ⚠️ **重绑的是本模块自己的属性，不是 `pytest` 模块的属性。**
    先例 `tests/gates/test_explain_service_live.py` 改的是全局 `pytest.skip`，
    那是**进程级污染**（同一轮里别的测试文件也被改）。本形态没有这个副作用。
    """
    _skip = pytest.skip
    _skip(reason)


def _base_url() -> str:
    explicit = (os.environ.get(BASE_ENV) or "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = (os.environ.get(PORT_ENV) or "").strip()
    if not port:
        _unavailable(f"{PORT_ENV} 与 {BASE_ENV} 都没设 —— 不知道活栈在哪个端口")
    return f"http://127.0.0.1:{port}"


def _admin_password() -> str:
    password = (os.environ.get(ADMIN_PASSWORD_ENV) or "").strip()
    if not password:
        _unavailable(f"{ADMIN_PASSWORD_ENV} 未设置 —— 换不到真会话")
    return password


def _launch_browser(sync_playwright):
    """起 chromium。

    ⚠️ **`H2b` 实测：浏览器发出的 `Host: 127.0.0.1:<port>` 落到默认站 `frontend`**
    （`/login` 回 200、真登录表单在）⇒ **不需要** `--host-resolver-rules`。
    站点哪天不再 `--set-default`、或 compose 起多站，这一跳会**静默**落到别的站，
    届时的第一处置写在 §7.23 的翻案条件表第 1 行 —— **不是改 compose / nginx 去迁就判据**。
    """
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(headless=True)
    except Exception as exc:  # 驱动装了但浏览器二进制没装：Executable doesn't exist
        manager.stop()
        _unavailable(f"起不了 chromium（{exc}）—— `python -m playwright install chromium` 没跑过？")
    return manager, browser


@pytest.fixture(scope="module")
def driver():
    """浏览器驱动。**`import playwright` 写在这里，不在模块顶层**（硬约束 1）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        _unavailable(f"driver missing: {exc}")
    manager, browser = _launch_browser(sync_playwright)
    try:
        yield browser
    finally:
        browser.close()
        manager.stop()


@pytest.fixture(scope="module")
def desk(driver):
    """一个**真登录过**的浏览器上下文，外加活栈基址。

    ⚠️ **走站点自己的 `/login` 表单换会话，不手工伪造 Cookie** ——
    伪造就等于把 `H6` 那格要证的东西假设掉了。

    ⚠️ **返回的是「上下文 + 基址」而不是一张页**，理由见 `_desk_tab` 的注释：
    每一格各开一张**没被 `page.route` 碰过**的新页，会话（cookie）由上下文共享，
    **登录只做一次**。
    """
    base = _base_url()
    password = _admin_password()
    user = (os.environ.get(ADMIN_USER_ENV) or "Administrator").strip()
    session = driver.new_context(viewport={"width": 1400, "height": 900})
    tab = session.new_page()
    try:
        tab.goto(f"{base}/login", wait_until="domcontentloaded", timeout=60_000)
        tab.fill("#login_email", user)
        tab.fill("input[type=password]", password)
        tab.click("button.btn-login")
        tab.wait_for_url("**/app**", timeout=60_000)
        tab.wait_for_timeout(2_500)
    except Exception as exc:
        session.close()
        _unavailable(f"{base} 上换不到真会话（{exc}）—— 活栈没起，或站点没起来")
    tab.close()
    yield session, base
    session.close()


def _desk_tab(desk):
    """给一格开一张**干净的** Desk 页（会话沿用，登录不重做）。

    ⚠️ **为什么每格一张新页，而不是全程复用同一张 —— 这是执行期实测踩出来的，钉在这里**：
    一张页只要被 `page.route(...)` 碰过，**即便随后 `page.unroute(...)`**，
    后续那些**上游真的挂了**的请求会**挂住不返回**（`expect_response` 超时），
    而不是把 nginx 那个真 502 交上来。
    最小对照实验（`/tmp` 里跑的，两支只差「有没有过一次 route/unroute」）：
    **没碰过 → `status 502`；碰过 → `TIMEOUT`。**
    ⇒ 这是**驱动侧的请求拦截残留**，不是 `desk.js` 的缺陷；
    复用同一张页会让 `H8c`（真 nginx 502）红在一个与被判对象无关的地方。
    """
    session, base = desk
    tab = session.new_page()
    tab.goto(f"{base}/app", wait_until="domcontentloaded", timeout=60_000)
    tab.wait_for_timeout(2_500)
    _inject(tab)
    return tab, base


def _inject(tab):
    """把仓里那份资产装进当前页。**幂等**。

    ⚠️ 判的是**仓里那一份**，不是 nginx 注入的那一份 —— 后者由
    `tests/unit/test_desk_asset_route.py` 的「逐字节相同」那条守着，这里不重复判。

    ⚠️ **必须幂等，而且不许「先摘掉面板再重注」** —— 那是执行期实测踩到的一个坑，
    钉在这里免得下一个人再踩：资产第二次执行时会撞上
    `Object.defineProperty(window, "agenerpDesk")` 已存在 ⇒ 它**按设计 `return`**
    （「已经挂过就不抢、不覆盖」）⇒ 第二份**没有注册任何快捷键**；
    而第一份的内部状态仍指着那个已被摘掉的 DOM 节点 ⇒ 按 ⌘K 时它把
    `display:flex` 设在一个**已脱离文档的节点**上，选择器永远等不到可见。
    ⇒ **一张页只注入一次，之后复用同一份实例。**
    """
    if tab.evaluate("() => !!window.agenerpDesk"):
        return
    tab.add_script_tag(content=ASSET.read_text(encoding="utf-8"))


def _open_panel(tab):
    """唤起面板。**已经开着就不再按** —— 那个键位是 toggle，再按一次会把它关掉。

    ⚠️ **按键之前先等资产真的执行完**（`window.agenerpDesk` 出现）——
    快捷键是资产**执行时**注册的；在它执行完之前按下去，那一次按键**谁也收不到**，
    而失败长得像「⌘K 坏了」。这是一条执行期实测出来的间歇红，钉在这里。

    ⚠️ **这个 helper 允许补按一次，`D-d-4` 那一格不允许** ——
    它只是别的格的**前置动作**；「⌘K 到底灵不灵」由
    `test_the_shortcut_opens_toggles_and_escapes_and_gives_focus_back` **单按一次**判定，
    那一条**不补按**。分开写是有意的：前置动作的健壮性不该盖住被判对象的缺陷。
    """
    tab.wait_for_function("() => !!window.agenerpDesk", timeout=30_000)
    for attempt in range(2):
        if tab.is_visible("#agenerp-desk-panel"):
            break
        tab.keyboard.press("Control+k")
        try:
            tab.wait_for_selector("textarea.agenerp-desk-input", state="visible", timeout=5_000)
            break
        except Exception:
            if attempt == 1:
                raise
    tab.wait_for_selector("textarea.agenerp-desk-input", state="visible", timeout=10_000)


def _panel_text(tab) -> str:
    return tab.inner_text(".agenerp-desk-output").strip()


# ── 那**一次**未打桩的真请求 ────────────────────────────────────────────────
#
# ⚠️ **只此一次。** `H6` / `H7` / `H9` 三格的证据都只能取自它 ——
# `page.route` 打桩的请求**根本到不了服务端**，从它们身上取不到「服务端看到了 sid」。
# 其余所有格一律打桩，**不许为了「多测几遍」重复发真请求**（配了 AI 变量时那是真烧 token）。


@pytest.fixture(scope="module")
def real_exchange(desk):
    """发一次真请求，把**请求头 / 请求体 / 状态码 / 面板文本**一起带回来。"""
    tab, _ = _desk_tab(desk)
    _open_panel(tab)
    tab.fill("textarea.agenerp-desk-input", QUESTION)
    with tab.expect_response(f"**{EXPLAIN_PATH}", timeout=REAL_RESPONSE_TIMEOUT_MS) as info:
        tab.click("button.agenerp-desk-send")
    response = info.value
    request = response.request
    tab.wait_for_timeout(1_000)
    return {
        "status": response.status,
        "cookie": request.all_headers().get("cookie", ""),
        "post_data": request.post_data or "",
        "method": request.method,
        "url": request.url,
        "panel": _panel_text(tab),
        "tab": tab,
    }


def test_the_browser_carries_the_httponly_sid_to_the_explain_endpoint(real_exchange):
    """`H6` —— **本仓第一次直接观测**：浏览器把 `HttpOnly` 的 `sid` 自动带上了。

    `sid` 是 `HttpOnly`（真登录后 `document.cookie` 里看不到它，Phase 1 实读）。
    「`HttpOnly` 只挡 JS 读、不挡浏览器发」这句话本仓一直是**推断**，这里第一次被直接观测。

    ⚠️ **判法用的是请求头本身，不是「回的不是 401」那个代理指标 —— 那个指标已被实测证伪。**
    plan 原写「直接证据是回的不是 401」，理由是 `handle_explain` 的顺序
    `_sid_from_cookie` → `parse_request` → `_resolve_identity`(401) → `config_factory`(503)。
    这条**正向蕴含仍然成立**（非 401 ⇒ 站点认到人了），
    但它的**逆否**（401 ⇒ 没带 sid）是**假的**：站点也会因为 **CSRF** 拒绝一个**确实带上了的** sid。
    实测见本文件末尾那条 `test_..._csrf` 与 `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md`。
    ⇒ 这里改用**直接测量**（读那次请求真正发出去的 `Cookie` 头），
    **比原来的代理指标更强，不是更松**。
    """
    cookie = real_exchange["cookie"]
    assert cookie, "那次请求的 `Cookie` 头是空的 —— 浏览器一个 cookie 都没带"
    morsels = {chunk.split("=", 1)[0].strip() for chunk in cookie.split(";") if chunk.strip()}
    assert "sid" in morsels, f"`Cookie` 头里没有 `sid`（带上的是 {sorted(morsels)}）"
    value = ""
    for chunk in cookie.split(";"):
        key, _, raw = chunk.strip().partition("=")
        if key == "sid":
            value = raw.strip()
            break
    # ⚠️ 只断言非空，**绝不把它写进断言消息**（它是一个真会话）。
    assert value, "`Cookie` 头里的 `sid` 是空值"
    assert real_exchange["method"] == "POST"
    assert real_exchange["url"].endswith(EXPLAIN_PATH)


def test_the_request_body_carries_only_the_keys_the_service_accepts(real_exchange):
    """`H9` —— 面板实际发出的请求体键集 ⊆ 白名单，且不含五个越权键。

    这一格不是形式主义：服务端对 `fields`/`role`/`view`/`actions`/`user` 回 400，
    前端带上就是**必然 400**，而那种 400 在界面上和「问题不合法」长得一样。

    ⚠️ 证据只能取自这一次**未打桩**的真请求 —— 打桩那批的请求体也拿得到，
    但它们证明不了「面板对真服务端发的是这个形状」。
    """
    from agenerp.serve.app import ALLOWED_BODY_KEYS, CALLER_CLAIMED_KEYS

    payload = json.loads(real_exchange["post_data"])
    keys = set(payload)
    assert keys, "请求体是空的"
    assert keys <= set(ALLOWED_BODY_KEYS), f"请求体里有服务端不收的键：{sorted(keys - set(ALLOWED_BODY_KEYS))}"
    assert not (keys & set(CALLER_CLAIMED_KEYS)), f"请求体里出现了越权键：{sorted(keys & set(CALLER_CLAIMED_KEYS))}"
    # `doctype` 与 `name` **同时给或同时不给**（`app.py` 的 `parse_request` 逐字）。
    assert ("doctype" in keys) == ("name" in keys), f"`doctype` / `name` 没有成对出现：{sorted(keys)}"
    assert payload.get("question"), "请求体里没有问题正文"


def test_the_panel_renders_the_state_of_whatever_code_actually_came_back(real_exchange):
    """`H7` —— **先观测实际状态码，再断言面板渲染的是该码对应的那一态。**

    ⚠️ **不许把某个具体的码钉死进断言。**「配没配 AI 变量」在人手里、还会来回变
    （fork 的 PR 拿不到 secret ⇒ 那种 run 上回 503，`gates.yml` 那段注释逐字
    「这是预期，不是故障」）。把 `503` 钉死，判据会因为**环境变好**而变红；
    把 `200` 钉死，判据在 fork PR 的 run 上**恒红**。两头都是重蹈覆辙。
    """
    status = real_exchange["status"]
    panel = real_exchange["panel"]
    assert panel, f"HTTP {status} 之后面板是空的 —— 那正是 Goal 2 明令禁止的空白"
    assert str(status) in panel, f"面板文本里没有实际拿到的那个码（{status}）：{panel!r}"
    assert "正在问" not in panel, f"面板停在了 pending 态 —— HTTP {status} 没有覆盖它"


def test_the_real_exchange_never_echoes_the_session_cookie_into_the_panel(real_exchange):
    """面板任何一态都不把响应体原样倾泻进 DOM（§7.23.4 的运行时那一半）。

    离线那三格（`innerHTML` 一族零命中 / `document.cookie` 零命中 / `JSON.stringify(` ≤ 1）
    是**文本下限**，挡不住逐字段拼接出来的等价泄漏。这一条在真页面上正面判：
    **面板可见文本里不出现那个真 `sid` 的值。**
    """
    tab = real_exchange["tab"]
    cookie = real_exchange["cookie"]
    value = ""
    for chunk in cookie.split(";"):
        key, _, raw = chunk.strip().partition("=")
        if key == "sid":
            value = raw.strip()
            break
    assert value, "拿不到那次请求的 `sid` —— 这条判据失去着力点"
    panel = real_exchange["panel"]
    # ⚠️ 断言消息里**只报「出现了」，不回显那个值**。
    assert value not in panel, "面板文本里出现了会话 `sid` —— 自己造了一个绕过 HttpOnly 的显示面"
    assert value not in tab.inner_html("#agenerp-desk-panel"), "面板 DOM 里出现了会话 `sid`"


# ── 打桩那一批（`page.route`，一次真请求都不发）────────────────────────────


def _ask_with_stub(tab, handler) -> str:
    _inject(tab)
    _open_panel(tab)
    tab.route(f"**{EXPLAIN_PATH}", handler)
    try:
        tab.fill("textarea.agenerp-desk-input", QUESTION)
        with tab.expect_response(f"**{EXPLAIN_PATH}", timeout=STUB_RESPONSE_TIMEOUT_MS):
            tab.click("button.agenerp-desk-send")
        tab.wait_for_timeout(400)
        return _panel_text(tab)
    finally:
        tab.unroute(f"**{EXPLAIN_PATH}")


def _json_stub(code: int):
    def handler(route, _request=None):
        body = (
            json.dumps({"user": "Administrator", "answer": "这是回答", "accepted": True,
                        "cost": {"calls": 1, "total": 123}})
            if code == 200
            else json.dumps({"error": "stub"})
        )
        route.fulfill(status=code, content_type="application/json", body=body)

    return handler


def test_every_distinguishable_code_renders_a_distinct_non_empty_state(desk):
    """`H8` —— 九个可分辨的已枚举码 + `200`，共 **10** 条。

    判定口径写死，不留「人眼看着不一样」：
    **① 两两全等比较全部为假 ② 每一条都含该状态码的字面量 ③ 每一条都非空 ④ 无一停在 pending。**

    ⚠️ **不许把两个 `502` 拆成两条来凑数**（服务端「上游模型坏了」与反代
    「`agenerp-serve` 不在」在面板上必然合并 —— 面板只看得见状态码）。
    合并是**正确行为**，按十种来源判是不可满足的。
    """
    tab, _ = _desk_tab(desk)
    seen: dict[int, str] = {}
    for code in DISTINGUISHABLE_CODES:
        text = _ask_with_stub(tab, _json_stub(code))
        assert text, f"HTTP {code} 渲染成了空白"
        assert str(code) in text, f"HTTP {code} 那一态的可见文本里没有 {code}：{text!r}"
        assert "正在问" not in text, f"HTTP {code} 停在了 pending 态"
        seen[code] = text

    collisions = [
        (a, b)
        for i, a in enumerate(DISTINGUISHABLE_CODES)
        for b in DISTINGUISHABLE_CODES[i + 1:]
        if seen[a] == seen[b]
    ]
    assert not collisions, (
        f"这些码渲染成了同一句话：{collisions} —— 用户与判据都分不出它们，那是缺陷不是风格问题"
    )


def test_an_unenumerated_code_renders_the_fallback_state(desk):
    """`H8b` 上半 —— 喂一个**未枚举**的码（`418`），必须落进兜底态。

    这一格不是凑数：`500`（`app.py` 的 `except Exception` 兜底）与 `504`
    （`proxy_read_timeout`）在真环境里**会**发生，而封闭枚举接不住将来新增的码。
    """
    tab, _ = _desk_tab(desk)
    text = _ask_with_stub(tab, _json_stub(UNENUMERATED_CODE))
    assert text, f"HTTP {UNENUMERATED_CODE} 渲染成了空白 —— 兜底态缺失"
    assert str(UNENUMERATED_CODE) in text, f"兜底态没带上那个码本身：{text!r}"
    assert "正在问" not in text, "兜底态停在了 pending"


def test_a_transport_level_failure_renders_instead_of_hanging(desk):
    """`H8b` 下半 —— **网络层失败**（`route.abort()`，连响应都没有）。

    `fetch` 在这里是 `reject`，不是一个状态码 ⇒ 走的是与状态码分支**完全不同**的一条路。
    没有这一格，「面板永远转圈」这个失败形态无人认领。
    """
    tab, _ = _desk_tab(desk)
    _open_panel(tab)
    tab.route(f"**{EXPLAIN_PATH}", lambda route, _request=None: route.abort())
    try:
        tab.fill("textarea.agenerp-desk-input", QUESTION)
        tab.click("button.agenerp-desk-send")
        tab.wait_for_timeout(1_500)
        text = _panel_text(tab)
    finally:
        tab.unroute(f"**{EXPLAIN_PATH}")
    assert text, "网络层失败之后面板是空的"
    assert "正在问" not in text, "网络层失败之后面板停在了 pending —— 那就是永久 spinner"
    assert "请求没能发出去" in text, f"网络层失败没有被渲染成可分辨的一态：{text!r}"


def _probe_status(url: str, timeout: float = 10.0) -> int:
    """同源探活。**走浏览器之外的 HTTP 客户端，不走 `page.request`。**

    ⚠️ **这不是「换个顺手的写法」，是执行期实测逼出来的一条修法，钉在这里**：
    原来这里用的是 `tab.request.get(...)`（页面自己的请求上下文）。
    实测在 6 次整轮里**复现 2 次**：`agenerp-serve` 停掉之后，第一次探活
    `APIRequestContext.get` **挂满 30 秒默认超时**，整格红在探活上 ——
    而红的样子长得像「面板没渲染 502」，与被判对象毫无关系。

    **同一时刻从浏览器外面量到的是另一回事**（`curl -w time_total`，连打 12 次、
    跨过 `resolver valid=10s` 的窗口）：**12/12 都是 `502`，墙钟 3–20 毫秒。**
    ⇒ **反代侧没有慢**，挂住的是**驱动侧的请求路径**
    （与 `_desk_tab` 那条注释记的「请求拦截残留」同族；本 plan 只测到「在里面挂、在外面不挂」，
    **没有测出它到底是哪一层拦的，因此不写根因**）。

    ⇒ **探活这件事本来就不该由被判对象所在的那个浏览器承担** ——
    它是个同步屏障，不是判据。**判据那一半（面板把真 502 渲染成什么）一个字没动，
    仍然整条走浏览器。**
    """
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def _compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args], cwd=REPO, capture_output=True, text=True, timeout=300
    )


def test_a_real_nginx_502_renders_without_assuming_the_body_is_json(desk):
    """`H8c` —— **真 nginx 502**，不是打桩。

    ⚠️ **这一格打桩替代不了。** `tools/nginx/frappe.conf.template` **没有 `error_page`、
    没有 `proxy_intercept_errors`** ⇒ 真 nginx 502/504 回的是**默认 HTML 错误页**，
    而服务端的 502/503 回的是 **JSON `{"error": …}`**。
    ⇒ 喂一个「JSON 体的假 502」走的是面板的 JSON 分支，
    **真 502 上 `r.json()` 会直接抛**，正好落进「失败渲染成空白」——而打桩判据全绿。

    本格零额外成本：`H10` 本来就要停一次 `agenerp-serve`。
    """
    tab, base = _desk_tab(desk)
    probe = _compose("ps", "--format", "{{.Service}}")
    if probe.returncode != 0:
        _unavailable(f"`docker compose ps` 退 {probe.returncode} —— 够不到活栈，真 502 造不出来")
    stopped = _compose("stop", "agenerp-serve")
    if stopped.returncode != 0:
        _unavailable(f"停不掉 `agenerp-serve`（退 {stopped.returncode}）—— 真 502 造不出来")
    try:
        # ⚠️ **等到反代真的开始回 502 再往下** —— `docker compose stop` 返回 ≠ 上游立刻不可达
        # （容器收到 SIGTERM 之后还有一段优雅退出窗口，那期间服务仍在正常应答）。
        # 不等就是一条间歇红，而且红得像「面板没渲染 502」，与被判对象毫无关系。
        #
        # ⚠️ **每次探活带一个不重样的 query** —— 不带的话响应会被复用，
        # 轮询到的永远是第一次那个 200，等到超时为止。这也是执行期实测出来的。
        for tick in range(180):
            if _probe_status(f"{base}/agenerp/health?agenerp-probe={tick}") == 502:
                break
            tab.wait_for_timeout(500)
        else:
            _unavailable("`agenerp-serve` 停了 90 秒，反代仍不回 502 —— 真 502 造不出来")
        _inject(tab)
        _open_panel(tab)
        tab.fill("textarea.agenerp-desk-input", QUESTION)
        with tab.expect_response(f"**{EXPLAIN_PATH}", timeout=REAL_RESPONSE_TIMEOUT_MS) as info:
            tab.click("button.agenerp-desk-send")
        status = info.value.status
        content_type = (info.value.header_value("content-type") or "").lower()
        tab.wait_for_timeout(600)
        text = _panel_text(tab)
        # `H10` 的不回归那一半：服务停了，同源前端仍在。
        # ⚠️ 同样走浏览器之外（理由见 `_probe_status`）：这一条判的是**反代还活着**，
        # 而它此前与探活共用同一条会挂住的驱动侧路径。
        front_status = _probe_status(f"{base}/app", timeout=30.0)
    finally:
        started = _compose("start", "agenerp-serve")
        assert started.returncode == 0, f"没能把 `agenerp-serve` 起回来（退 {started.returncode}）"
        # ⚠️ **起回来之后等它真的应答再走** —— 不等就把「服务还没起好」这个状态
        # 留给下一格（或下一轮），红会出现在一个与它无关的地方。
        for tick in range(180):
            if _probe_status(f"{base}/agenerp/health?agenerp-restore={tick}") == 200:
                break
            tab.wait_for_timeout(500)

    assert status == 502, f"停掉服务之后同源前端回的是 HTTP {status}，不是 502"
    assert "json" not in content_type, (
        f"真 nginx 502 的 `Content-Type` 是 {content_type!r} —— 它变成 JSON 了，"
        "本格赖以成立的那条前提（真 502 回默认 HTML）已经不成立，先重读 §7.23.4"
    )
    assert text, "真 502 之后面板是空的 —— 兜底路径假设了响应体是 JSON"
    assert "502" in text, f"真 502 那一态没带上码本身：{text!r}"
    assert "正在问" not in text, "真 502 之后面板停在了 pending"
    assert front_status == 200, (
        f"停掉 `agenerp-serve` 之后 `/app` 回了 {front_status} —— §7.21 `D-b-8` 回归了"
    )


# ── 唤起 / 关闭 / 焦点归还（`D-d-4`）──────────────────────────────────────


def test_the_shortcut_opens_toggles_and_escapes_and_gives_focus_back(desk):
    """`D-d-4` 的四条行为，逐条在真 Desk 页上判。

    `H3` 实测：Frappe v15 的 `frappe.ui.keys.handlers` 里没有 `"k"`（awesomebar 走 `ctrl+g`），
    真按下去 `defaultPrevented=false` ⇒ **这个键位没被占，不抢任何既有绑定。**
    """
    tab, _ = _desk_tab(desk)
    tab.evaluate(
        "() => { const b = document.createElement('button');"
        " b.id = 'agenerp-focus-probe'; b.textContent = 'probe';"
        " document.body.appendChild(b); b.focus(); }"
    )
    assert tab.evaluate("document.activeElement && document.activeElement.id") == "agenerp-focus-probe"

    tab.keyboard.press("Control+k")
    tab.wait_for_selector("textarea.agenerp-desk-input", state="visible", timeout=10_000)
    assert tab.is_visible("#agenerp-desk-panel"), "⌘K 没有把面板唤起来"

    tab.keyboard.press("Escape")
    tab.wait_for_timeout(300)
    assert not tab.is_visible("#agenerp-desk-panel"), "`Esc` 没有关掉面板"
    assert tab.evaluate("document.activeElement && document.activeElement.id") == "agenerp-focus-probe", (
        "关闭之后焦点没有还给唤起前那个元素 —— 在单据页上这是实实在在的可用性缺陷"
    )

    tab.keyboard.press("Control+k")
    tab.wait_for_selector("textarea.agenerp-desk-input", state="visible", timeout=10_000)
    tab.keyboard.press("Control+k")
    tab.wait_for_timeout(300)
    assert not tab.is_visible("#agenerp-desk-panel"), "再按一次同一组合键没有把面板关掉（toggle 不成立）"
    assert tab.evaluate("document.activeElement && document.activeElement.id") == "agenerp-focus-probe", (
        "toggle 关闭之后焦点没有还回去"
    )

    tab.evaluate("() => { const n = document.getElementById('agenerp-focus-probe'); if (n) n.remove(); }")


def test_the_panel_states_the_context_it_is_about_to_send(desk):
    """唤起时面板要说清「这次带不带单据上下文」。

    ⚠️ **本机站点 `setup_complete=False` ⇒ Desk 把任何 `/app/**` 强制改写成 `setup-wizard`
    ⇒ 够不到任何一张真单据页**（跑完 setup wizard 要往站点写数据，撞本 plan 的 Non-Goals 2）。
    ⇒ 这里判的是**「无单据上下文」那一支的活体证据**：面板明说了它不带上下文，
    且请求体里确实没有 `doctype` / `name`（由 `H9` 那条判）。

    **「在真单据页上唤起会把 `doctype`/`name` 带进请求」这一支本机拿不到活体证据**，
    它由离线判据（对取值函数的直接调用）承担 —— **两者不是一回事，收口文字里不许混。**
    """
    tab, _ = _desk_tab(desk)
    _open_panel(tab)
    hint = tab.inner_text(".agenerp-desk-hint").strip()
    assert hint, "面板没说这次带不带单据上下文"
    on_document = tab.evaluate(
        "() => { try { const r = frappe.get_route();"
        " return !!(r && r.length >= 3 && r[0] === 'Form'); } catch (e) { return false; } }"
    )
    if on_document:
        assert "当前单据：" in hint, f"在单据页上却说没有上下文：{hint!r}"
    else:
        assert "不在单据页" in hint, f"不在单据页上却声称有上下文：{hint!r}"
    tab.keyboard.press("Escape")


def test_the_site_rejects_a_browser_session_sid_without_a_csrf_token(desk, real_exchange):
    """⚠️ **本 plan 执行期的头号发现，钉在这里免得它悄悄变回去。**

    **两条路拿到的 `sid` 在服务端的命运不同**（实测，不是推断）：

    | `sid` 来源 | 站点对 `frappe.auth.get_logged_user`（无 CSRF token）的回应 | `/agenerp/explain` |
    |---|---|---|
    | `POST /api/method/login`（**本仓既有门禁走的路**） | **200** | **200** |
    | 浏览器 `/login` 网页表单（**真人走的路**） | **400 `CSRFTokenError`** | **401** |

    ⇒ 既有那份活体门禁之所以绿，是因为它用的会话是**真人永远不会有的那一种**。
    `agenerp-serve` 不带 CSRF token 去解析 `sid`，而 Frappe 对网页会话的 POST 要求它。

    ⚠️ **这不推翻 `H6`**：浏览器**确实**把 `sid` 带上了（上面那条判据直接读到了请求头）。
    被推翻的只是「回的不是 401」这个**代理指标**。

    **本 plan 不修它** —— 修法落在 `agenerp/serve/**` 的身份解析上，
    那是 P1.8a 的请求契约面，本 plan 的 Non-Goals 1 逐字禁止改它一个字。
    已交人：`docs/masterplan/STATE.md` §3 的 `[needs-human]`。

    本条判的是**现状**，不是**应然**：它只要求「浏览器会话的那次请求确实带上了 `sid`，
    而面板把服务端真回的那个码渲染成了对应的一态」。
    ⚠️ 站点哪天不再要 CSRF、或服务端补上了 token，这一条**照样绿** —— 它不钉死任何一个码。
    """
    from agenerp.serve.app import UNAUTHENTICATED

    status = real_exchange["status"]
    panel = real_exchange["panel"]
    assert "sid" in {c.split("=", 1)[0].strip() for c in real_exchange["cookie"].split(";") if c.strip()}
    assert str(status) in panel, f"面板没把真实拿到的码（{status}）渲染出来"
    if status == 401:
        assert UNAUTHENTICATED in panel, (
            "拿到 401，但面板没把服务端那句固定文案渲染出来 —— "
            f"401 那一态坏了，或服务端换了文案：{panel!r}"
        )
