"""P2.2 · 渲染器活体判据的**断言体**。

**这一份是判据本体，`tests/render/test_renderer.py` 是它的严格模式**（形态与
`tests/unit/test_desk_sidebar_body.py` / `tests/ui/test_sidebar.py` 同族，
落点 `module-boundaries.md` §7.23.5）。

住在 `tests/unit/` 是刻意的：这一轮 `pytest tests/unit -q` 每次都跑，
改坏了当天看得见；住进 `tests/render/` 就只有跑活体那一轮才看得见。

## ⚠️ 一处诚实的边界：`/agenerp/view` 那一跳是打桩的，原因不是图省事

活栈的 `agenerp-serve` 容器挂载的是**主工作树**的 `agenerp/`
（`docker inspect` 实读：`/Users/lize/Claude/Projects/AgenERP/agenerp -> /opt/agenerp/agenerp`），
而本分支在一个独立 worktree 里。**往主工作树写会污染正在那儿跑的循环**，所以不写。

⇒ 本文件用 `page.route` 兜住 `/agenerp/view`，**但填进去的 JSON 是真的
`agenerp.serve.app.view_plan()` 算出来的**，不是手写的。被桩掉的只有 HTTP 传输那一段。

**没有被这一层覆盖到的，逐条写在这里，不含糊**：
- `/agenerp/view` 的**路由接线**（`do_GET` 里那个等值分支）—— 由
  `tests/unit/test_render_static_and_plan.py` 判 `SERVED_PATHS`，但没有真发过一次 HTTP。
- `/agenerp/app` 壳页经 nginx 发出来这件事。
⇒ **要覆盖它们，得让活栈吃到本分支的代码**（合并，或让栈指向本 worktree）。

## 真的被覆盖到的（这才是这一层的价值）

**真站点、真数据、真权限、真浏览器、真渲染器**：
- 工人的会话取真数据、渲染成真表格
- 工人读不到的 DocType → **后端拒**，前端只提示
- 恶意 URL / 恶意富文本喂进渲染器 → 不产出可点击元素、不执行
"""

from __future__ import annotations

import json
import os
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
RENDER_ASSET = REPO / "agenerp" / "serve" / "assets" / "render.js"
FIXTURE = REPO / "tests" / "dsl" / "fixtures" / "site-schema-subset.json"
CHILD_FIXTURE = REPO / "tests" / "dsl" / "fixtures" / "child-tables.json"

BASE_ENV = "AGENERP_SERVE_BASE_URL"
PORT_ENV = "AGENERP_HTTP_PORT"
WORKER_USER = "worker@hrd.example.com"
WORKER_PASSWORD_ENV = "AGENERP_WORKER_PASSWORD"

VIEW_PLAN_GLOB = "**/agenerp/view*"
RESOURCE_GLOB = "**/api/resource/**"


def _unavailable(reason: str):
    """**唯一的「跑不了」出口。**

    默认 `skip`（`tests/unit` 那一轮）。`tests/render/test_renderer.py`
    加载完本模块后把**这一个名字**重绑成 `pytest.fail` —— 整份断言体切成严格模式。
    ⚠️ 重绑的是本模块自己的属性，不是 `pytest` 模块的属性（无进程级污染）。
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


def _worker_password() -> str:
    password = (os.environ.get(WORKER_PASSWORD_ENV) or "").strip()
    if not password:
        _unavailable(f"{WORKER_PASSWORD_ENV} 未设置 —— 换不到车间工人的真会话")
    return password


def _schema():
    from agenerp.dsl.schema import SchemaView

    fields = json.loads(FIXTURE.read_text(encoding="utf-8"))["fields"]
    raw = json.loads(CHILD_FIXTURE.read_text(encoding="utf-8"))
    children = {(k.split(".", 1)[0], k.split(".", 1)[1]): v for k, v in raw.items()}
    return SchemaView(fields, children)


def _plan_json(view_name: str) -> str:
    """用**真的** `view_plan()` 算一份计划。schema 取自提交在仓里的活站点导出子集。"""
    from agenerp.serve.app import view_plan

    return json.dumps(view_plan(view_name, _schema()), ensure_ascii=False)


def _falling_back_plan_json() -> str:
    """一份**真的会落回**的计划。

    ⚠️ 为什么要专门造一个：路线 C 已经把工人日常视图的落回压到 **0** ——
    于是「落回卡片长什么样」这条路在活体里**一次都走不到**。
    P2.2 Phase 5 的变异 **M6**（把落回卡片改成静默丢弃）**没有见血**，
    就是被这个窟窿放过去的。这个函数是补上它的。

    ⚠️ 计划仍由**真的 `plan_payload()`** 算出来，不是手写 JSON ——
    手写就变成「验我写得对不对」。
    """
    from agenerp.dsl.blocks import Block, View
    from agenerp.serve.app import plan_payload

    view = View(
        name="probe-falls-back",
        title="落回探针",
        blocks=(
            # `item_tax_rate` 是 `Code`，今天仍在 RENDERABLE_FIELDTYPES 之外。
            Block(type="list", title="画不了的一块", doctype="Sales Order Item",
                  fields=("item_code", "item_tax_rate")),
        ),
    )
    return json.dumps(plan_payload(view, _schema()), ensure_ascii=False)


# ── 浏览器与会话 ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def driver():
    """浏览器驱动。**`import playwright` 写在这里，不在模块顶层。**"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        _unavailable(f"driver missing: {exc}")
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(headless=True)
    except Exception as exc:
        manager.stop()
        _unavailable(f"起不了 chromium（{exc}）—— `python -m playwright install chromium` 没跑过？")
    try:
        yield browser
    finally:
        browser.close()
        manager.stop()


@pytest.fixture(scope="module")
def worker(driver):
    """一个**真登录过的车间工人**上下文。

    ⚠️ **必须是工人，不是 Administrator。** 用管理员跑，「越权被后端拒」那一格
    就永远绿着而什么都没验 —— 管理员什么都读得到。
    """
    base = _base_url()
    password = _worker_password()
    session = driver.new_context(viewport={"width": 1400, "height": 900})
    tab = session.new_page()
    try:
        tab.goto(f"{base}/login", wait_until="domcontentloaded", timeout=60_000)
        tab.fill("#login_email", WORKER_USER)
        tab.fill("input[type=password]", password)
        tab.click("button.btn-login")
        tab.wait_for_url("**/app**", timeout=60_000)
        tab.wait_for_timeout(2_000)
    except Exception as exc:
        session.close()
        _unavailable(
            f"{base} 上换不到车间工人的会话（{exc}）—— 活栈没起，"
            "或没跑过 `python3 -m agenerp.seedusers --load-users`"
        )
    tab.close()
    yield session, base
    session.close()


def _render(worker_ctx, view_name: str, *, resource_stub=None, plan_json=None):
    """开一张干净的页，注入渲染器，渲染一个视图。返回那张页。

    ⚠️ **每格一张新页**：一张页被 `page.route` 碰过之后，后续真请求会挂住而不是
    把真状态码交上来（`tests/unit/test_desk_sidebar_body.py::_desk_tab` 实测记的那条）。
    """
    session, base = worker_ctx
    tab = session.new_page()
    plan = plan_json if plan_json is not None else _plan_json(view_name)
    tab.route(
        VIEW_PLAN_GLOB,
        lambda route: route.fulfill(
            status=200, content_type="application/json; charset=utf-8", body=plan
        ),
    )
    if resource_stub is not None:
        tab.route(RESOURCE_GLOB, resource_stub)
    tab.goto(f"{base}/app", wait_until="domcontentloaded", timeout=60_000)
    tab.wait_for_timeout(1_500)
    tab.add_script_tag(content=RENDER_ASSET.read_text(encoding="utf-8"))
    tab.wait_for_function("() => !!window.agenerpRenderView", timeout=30_000)
    tab.evaluate(
        "(name) => { const d = document.createElement('div'); d.id = 'agenerp-view-root';"
        " document.body.appendChild(d); return window.agenerpRenderView(name); }",
        view_name,
    )
    tab.wait_for_selector("#agenerp-view-root[data-agenerp-rendered]", timeout=30_000)
    return tab


def _json_route(payload: dict):
    """同时兜住**列表**与**单据详情**两条 URL 形状。

    ⚠️ 这不是为了省事：Frappe 的两个端点回的**形状本来就不同** ——
    `/api/resource/<DocType>` 回 `{"data": [...]}`，
    `/api/resource/<DocType>/<name>` 回 `{"data": {...}}`。
    桩只兜一种时，`detail` 块会拿到一个数组当单据用，
    而失败长得像「渲染器坏了」。这一行是执行期实测踩出来的。
    """

    def handler(route):
        from urllib.parse import urlsplit

        segments = [s for s in urlsplit(route.request.url).path.split("/") if s]
        # ['api', 'resource', '<DocType>']  vs  ['api', 'resource', '<DocType>', '<name>']
        is_single_doc = len(segments) >= 4
        body = {"data": payload["data"][0]} if is_single_doc else payload
        route.fulfill(
            status=200,
            content_type="application/json; charset=utf-8",
            body=json.dumps(body, ensure_ascii=False),
        )

    return handler


# ── R5 · 权限由后端强制，前端只做提示 ────────────────────────────────────────


def test_the_worker_actually_sees_real_rows_from_the_site(worker):
    """工人的会话取到真数据并画了出来。**这一格不打桩任何 `/api/resource`。**"""
    tab = _render(worker, "worker-items")
    try:
        tab.wait_for_selector("#agenerp-view-root table.agenerp-table", timeout=20_000)
        text = tab.inner_text("#agenerp-view-root")
        assert "物料" in text
        # 表头是 DSL 里声明的字段，画出来的就该是这几列。
        # ⚠️ **2026-08-27 改过，照实记**：原来断言的是 `item_code`（英文 fieldname）。
        # P2.7 术语层接进渲染器之后表头变成中文，这条当场红了 ——
        # **红得正确，那正是术语层起作用的证据**。改成断言中文列名。
        assert "物料编码" in text
        # 种子数据里恒锐动力有三个物料（REST 实测：HRD-CELL-280 / HRD-PACK-5K /
        # HRD-ASSY-SVC）—— 表里不该是「没有数据」。
        assert "HRD-" in text, "工人读得到 Item，却渲染成了空表"
        # detail 块的子表（uoms / barcodes）**必须走单据详情接口** ——
        # 列表接口从不返回子表。这一格是执行期实测撞出来的缺口，钉在这里。
        # ⚠️ 同上：P2.7 之后子表表头也变成中文，`conversion_factor` → 「换算系数」。
        assert "换算系数" in text, "子表的列没画出来"
    finally:
        tab.close()


def test_a_doctype_the_worker_cannot_read_is_refused_by_the_backend_not_by_the_frontend(worker):
    """🔴 R5 · `system-baseline.md` §4：**权限由后端强制，前端只做呈现与提示。**

    直接用工人的会话去打一个他读不到的 DocType。**这一格证明两件事**：
    ① 后端确实拒（不是前端替它拒的）
    ② 前端拿到 403 之后只提示，不自己编一行数据出来
    """
    session, base = worker
    tab = session.new_page()
    try:
        res = tab.request.get(
            f"{base}/api/resource/Sales Order?fields=%5B%22name%22%5D&limit_page_length=1"
        )
        assert res.status == 403, (
            f"车间工人竟然读得到 Sales Order（HTTP {res.status}）—— "
            "要么权限没装载，要么这个角色被放宽了。两种都让本条判据失去着力点。"
        )
    finally:
        tab.close()


def test_the_panel_says_why_when_the_backend_refuses(worker):
    """后端回 403 时，渲染器**照实显示**，不静默留白。"""
    tab = _render(worker, "worker-items", resource_stub=lambda route: route.fulfill(
        status=403, content_type="application/json", body='{"exc_type":"PermissionError"}'
    ))
    try:
        text = tab.inner_text("#agenerp-view-root")
        assert "403" in text
        assert "你看不到这个" in text
        assert not tab.query_selector("#agenerp-view-root tbody tr td:not(.agenerp-empty)")
    finally:
        tab.close()


# ── R4 · 附件 URL 的 scheme 白名单 ───────────────────────────────────────────


@pytest.mark.parametrize(
    "hostile",
    ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
     "vbscript:msgbox(1)", "//evil.example/x.png"],
    ids=["javascript", "data", "vbscript", "protocol-relative"],
)
def test_a_hostile_attachment_url_never_becomes_a_clickable_element(worker, hostile: str):
    """🔴 R4 · 附件字段的值是**用户可写字段**里的 URL。白名单之外一律不做成链接/图片。"""
    payload = {"data": [{
        "name": "STE-PWN-1",
        "item_code": "PWN-1", "item_name": "x", "qty": 1, "uom": "Nos",
        "s_warehouse": "", "t_warehouse": "", "image": hostile,
        "stock_entry_type": "", "posting_date": "", "work_order": "",
        "from_warehouse": "", "to_warehouse": "", "fg_completed_qty": 0,
        "purpose": "", "items": [{
            "item_code": "PWN-1", "item_name": "x", "qty": 1, "uom": "Nos",
            "s_warehouse": "", "t_warehouse": "", "image": hostile,
        }],
    }]}
    tab = _render(worker, "worker-stock-entries", resource_stub=_json_route(payload))
    try:
        blocked = tab.query_selector_all("#agenerp-view-root [data-agenerp-blocked-url]")
        assert blocked, f"{hostile!r} 没有被判成不安全 URL"
        hrefs = tab.eval_on_selector_all(
            "#agenerp-view-root a", "els => els.map(e => e.getAttribute('href'))")
        srcs = tab.eval_on_selector_all(
            "#agenerp-view-root img", "els => els.map(e => e.getAttribute('src'))")
        assert hostile not in hrefs, f"{hostile!r} 被做成了可点击链接"
        assert hostile not in srcs, f"{hostile!r} 被当成了图片地址"
    finally:
        tab.close()


def test_a_same_site_attachment_url_is_still_rendered(worker):
    """白名单**不是把功能关掉**：站内相对路径该画就画。

    没有这一格，上一条可以靠「一律不渲染附件」拿满分 —— 那是把功能删掉冒充安全。

    ⚠️ `Stock Entry Detail.image` 的类型是 **`Attach` 而不是 `Attach Image`**
    （活站点导出实读），所以它渲染成 `<a href>` 而不是 `<img src>`。
    这一行是执行期实测订正的 —— 原来断言 `img` 时它红了，红在我的假设上，不在实现上。
    """
    ok_url = "/files/panel.png"
    payload = {"data": [{
        "name": "STE-PROBE-1",
        "item_code": "OK-1", "item_name": "x", "qty": 1, "uom": "Nos",
        "s_warehouse": "", "t_warehouse": "", "image": ok_url,
        "stock_entry_type": "", "posting_date": "", "work_order": "",
        "from_warehouse": "", "to_warehouse": "", "fg_completed_qty": 0, "purpose": "",
        "items": [{"item_code": "OK-1", "item_name": "x", "qty": 1, "uom": "Nos",
                   "s_warehouse": "", "t_warehouse": "", "image": ok_url}],
    }]}
    tab = _render(worker, "worker-stock-entries", resource_stub=_json_route(payload))
    try:
        hrefs = tab.eval_on_selector_all(
            "#agenerp-view-root a", "els => els.map(e => e.getAttribute('href'))")
        assert ok_url in hrefs, "站内相对路径的附件也没画出来 —— 白名单把功能一起关掉了"
    finally:
        tab.close()


# ── R3 · 富文本剥标签，且**不执行** ──────────────────────────────────────────


def test_rich_text_is_never_parsed_as_html(worker):
    """🔴 R3 · `module-boundaries.md` §7.23 第 1 条：建 DOM 只走 `textContent`。

    喂一段会自曝的富文本。**若渲染器在任何环节把它当 HTML 解析过一次**
    （包括「塞进临时节点再取 textContent」那个假安全写法），
    `onerror` 就在解析那一刻跑了 —— `window.__agenerp_pwned` 会出现。
    """
    hostile = '<img src=x onerror="window.__agenerp_pwned=1">恒锐动力 <b>储能</b> 电池包'
    payload = {"data": [{
        "name": "RT-1",
        "item_code": "RT-1", "item_name": "x", "item_group": "", "stock_uom": "Nos",
        "image": "", "description": hostile, "is_stock_item": 1,
        "uoms": [], "barcodes": [],
    }]}
    tab = _render(worker, "worker-items", resource_stub=_json_route(payload))
    try:
        assert tab.evaluate("() => window.__agenerp_pwned") is None, (
            "富文本被当 HTML 解析过 —— onerror 跑起来了"
        )
        cell = tab.inner_text("#agenerp-view-root [data-agenerp-degraded='text-editor']")
        assert "储能" in cell, "剥标签把正文也剥掉了"
        assert "<img" not in cell and "<b>" not in cell, "标签没剥干净"
        assert not tab.query_selector("#agenerp-view-root b"), "富文本里的标签变成了真元素"
    finally:
        tab.close()


def test_the_user_is_told_the_rich_text_lost_its_formatting(worker):
    """降级要**说出来**。一段莫名其妙变了样的文字比一句「这里只显示纯文本」难受得多。"""
    tab = _render(worker, "worker-items")
    try:
        notes = tab.inner_text("#agenerp-view-root")
        assert "富文本" in notes
        assert "Desk" in notes, "降级提示里没给「去 Desk 看格式」的出路"
    finally:
        tab.close()


# ── 落回 Desk 的那一块，长什么样 ─────────────────────────────────────────────


def test_a_block_that_cannot_be_drawn_shows_a_fallback_card_with_a_reason(worker):
    """🔴 §10.3：未支持的落回 Desk，**明说、说清为什么、给一个去 Desk 的入口**。

    ⚠️ 这一条是 **Phase 5 的变异 M6 没见血之后补的**。
    路线 C 把工人视图的落回压到 0 ⇒ 落回渲染那条路在活体里一次都没被走过 ⇒
    把它整段删掉，12 条判据一条都不红。**「落回 = 0」不等于「落回画对了」。**
    """
    tab = _render(worker, "probe-falls-back", plan_json=_falling_back_plan_json())
    try:
        card = tab.wait_for_selector("#agenerp-view-root [data-agenerp-fallback]", timeout=20_000)
        text = card.inner_text()
        assert "画不了" in text, "落回卡片没说自己画不了"
        assert "item_tax_rate" in text, "落回卡片没说清是哪个字段卡住的"
        assert "Code" in text, "落回卡片没说清是哪种类型卡住的"
        href = tab.get_attribute("#agenerp-view-root [data-agenerp-fallback] a", "href")
        assert href and href.startswith("/app/"), f"落回卡片没给站内的 Desk 入口：{href!r}"
    finally:
        tab.close()


def test_a_fallback_block_never_renders_a_half_drawn_table(worker):
    """落回是**整块**落回，不许「把画不了的那一列删掉再画剩下的」。

    那是「画出来了，但画的不是用户要的东西」——比一句「这里画不了」危险得多。
    """
    tab = _render(worker, "probe-falls-back", plan_json=_falling_back_plan_json())
    try:
        assert not tab.query_selector("#agenerp-view-root table.agenerp-table"), (
            "落回的块还是画出了一张表"
        )
    finally:
        tab.close()


# ── P2.7 · 表头是中文 ────────────────────────────────────────────────────────


def test_the_worker_sees_chinese_column_headers(worker):
    """🔴 P2.7 · 术语层接进渲染器之后，表头必须是中文。

    基线是**零**：活站点导出实读，业务 app 全量 6,350 个字段里
    label 含中文的 = 0。一个中国工人看着 `item_code` / `stock_uom` 这样的表头，
    既读不懂也猜不出。
    """
    tab = _render(worker, "worker-items")
    try:
        headers = tab.eval_on_selector_all(
            "#agenerp-view-root table.agenerp-table th", "els => els.map(e => e.textContent)")
        assert headers, "一个表头都没有"
        chinese = [h for h in headers if re.search(r"[\u4e00-\u9fff]", h)]
        ratio = len(chinese) * 100 / len(headers)
        assert ratio >= 90.0, (
            f"{len(headers)} 个表头里只有 {len(chinese)} 个是中文（{ratio:.1f}%）："
            f"{[h for h in headers if h not in chinese][:8]}"
        )
        # 具体钉几个，防止「有中文」被一句无关的中文蒙混过去
        assert "物料编码" in headers, f"表头里没有「物料编码」：{headers[:10]}"
    finally:
        tab.close()


def test_the_page_says_so_when_the_terminology_layer_is_missing(worker):
    """术语层缺失时**说出来**，不静默退回英文。

    「术语层没装上」与「这个字段没有中文名」在界面上长得一模一样 ——
    前者是部署问题，后者是覆盖率问题。分不开就没人会去修。
    """
    plan = json.loads(_plan_json("worker-items"))
    plan["terminology"] = "术语层读不到：FileNotFoundError"
    plan["labels"] = {}
    tab = _render(worker, "worker-items", plan_json=json.dumps(plan, ensure_ascii=False))
    try:
        text = tab.inner_text("#agenerp-view-root")
        assert "术语层没装上" in text
    finally:
        tab.close()


# ── P2.6 · 角色首页：进来就有东西看，且那东西不是空的 ────────────────────────


HOME_PATH = "/agenerp/home"


def test_the_home_endpoint_resolves_the_worker_to_their_own_home_view(worker):
    """H1 · 「这个人 → 哪一页」。**用浏览器自己的 sid 问站点**，前端不判身份。"""
    session, base = worker
    tab = session.new_page()
    try:
        res = tab.request.get(f"{base}{HOME_PATH}")
        assert res.status == 200, f"首页解析回了 {res.status}"
        body = res.json()
        assert body.get("view") == "worker-work-orders", body
        assert body.get("role") == "车间工人", body
    finally:
        tab.close()


def test_an_unauthenticated_caller_is_sent_to_desk_not_given_an_empty_home(worker):
    """🔴 H2 · fail-closed：认不出人就落回 Desk，**不给一个空首页**。

    给空首页比落回 Desk 糟得多 —— 后者用户至少还能干活，
    而一片空白的首页让人以为系统坏了或者自己没权限。
    """
    session, base = worker
    context = session.browser.new_context()  # 一个**没有登录过**的新上下文
    tab = context.new_page()
    try:
        res = tab.request.get(f"{base}{HOME_PATH}")
        assert res.status in (401, 403), f"未认到人却回了 {res.status}"
        body = res.json()
        assert body.get("fallback") == "desk", body
        assert not body.get("view"), f"未认到人却给了一个视图：{body}"
    finally:
        tab.close()
        context.close()


def test_the_workers_home_is_not_an_empty_workspace(worker):
    """🔴 H3 · 判据名字说的那件事：**首页不能是空的工作台**。

    「不空」按 plan §2.1 事先写死的三条判，缺一不可：
      ① 至少渲染出 1 个块
      ② 那些块里**至少有 1 行来自真站点的数据**
      ③ 页面上没有落回卡片

    ⚠️ 第 ② 条是硬约束 ①（**渲染出来 ≠ 渲染对了**）在本项上的形态：
    一个画出了表头、下面一行数据都没有的首页，DOM 上「不空」，用户眼里是空的。
    """
    session, base = worker
    tab = session.new_page()
    try:
        res = tab.request.get(f"{base}{HOME_PATH}")
        home_view = res.json()["view"]
    finally:
        tab.close()

    page = _render(worker, home_view)
    try:
        blocks = page.query_selector_all("#agenerp-view-root [data-agenerp-block-type]")
        assert blocks, "首页一个块都没渲染出来"

        rows = page.query_selector_all("#agenerp-view-root table.agenerp-table tbody tr")
        real_rows = [r for r in rows if not r.query_selector("td.agenerp-empty")]
        assert real_rows, (
            "首页画出了表头，但**一行真数据都没有** —— DOM 上不空，用户眼里是空的"
        )

        assert not page.query_selector("#agenerp-view-root [data-agenerp-fallback]"), (
            "车间工人的首页上出现了落回卡片 —— 路线 C 的承诺是这个角色日常路径上落回 = 0"
        )
    finally:
        page.close()


def test_the_shell_no_longer_hardcodes_a_default_view():
    """H4 · 防我自己：旧的写死默认视图必须**消失**，不是「还在但没走到」。

    没有这一条，H1 可以在旧路径仍然存在的情况下绿 ——
    而那条路径会在 `/agenerp/home` 挂掉时**静默**接管，把所有人送到工人的首页。
    """
    shell = (REPO / "agenerp" / "serve" / "assets" / "app.html").read_text(encoding="utf-8")
    assert '"worker-work-orders"' not in shell, "app.html 里还写死着一个默认视图名"
    assert "/agenerp/home" in shell, "app.html 没有去问首页解析端点"
