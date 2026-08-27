# 🔴 **本文件是裁判本体（红线 1）。改它一个字都要人批准，提交带
#    `Gates-Change-Approved-By:`。** 落地经过：人 2026-08-27 就本次落地明确指派
#    （「两份草稿落进 tests/gates/……你帮我做了吧」），源草稿仍留在
#    `tools/experiments/p2_role_home/GATE-DRAFT-test_no_empty_workspace.py.txt`。
#
# 落地时的实测状态（**不是「应该能过」，是真跑过的**）：
#   · 三格 **3 passed**，耗时 ~5s
#   · D-26 变异两轮都能咬红它 —— (M1) 把 schema 快照挪走 ⇒ 首页那格红；
#     (M2) 从快照里删掉 `Work Order` 的字段 ⇒ 首格红。两轮之后 `sha256` 原状恢复。
#     ⇒ **它不是空转的绿。**
#
# ⚠️ **配套的另一份门禁（schema 字段任务完成率）本轮刻意没落地**，
#    理由不是红线，是 `gates.yml:237`「L2 全量 live 判定（全部门禁，零 skip）」——
#    live 模式**不读**预期红名单、要求零红零 skip，而那一份有两条**故意的红**
#    （等第二份评测集）。落进来就会打红那个 job。它留在
#    `tools/experiments/p2_schema_retrieval/GATE-DRAFT-*.txt`，**等评测集到位再落**。
#
# ============================================================================
# 落之前请先读这五条 —— 都是执行期实测撞出来的，不是风格建议
# ============================================================================
#
# ① 🔴 **「不空」必须是内容意义上的，不是 DOM 意义上的。**
#    一个画出了表头、下面一行数据都没有的首页，DOM 上「不空」，用户眼里是空的。
#    ⇒ 判据必须要求**至少一行来自真站点的数据**。这是硬约束 ① 在本项上的形态。
#
# ② 🔴 **必须用受限身份跑，不能用 Administrator。**
#    管理员什么都读得到 ⇒ 「首页有数据」那一格会永远绿着而什么都没验。
#    本仓已有的受限身份：`worker@hrd.example.com`（`agenerp/seedusers.py`），
#    口令从 `AGENERP_WORKER_PASSWORD` 读，**不进代码不进仓库**。
#
# ③ 🔴 **「认不出角色」与「角色没配首页」是两件事，要分开验。**
#    前者是「不知道你是谁」，后者是「知道你是谁但没给你配页」。
#    两种都**不许兜底到别人的首页** —— 给一个不属于他的首页，
#    用户看到的是一片「你看不到这个」，那比落回 Desk 糟得多。
#
# ④ 🔴 **本文件怎么绕开「活栈挂主工作树」这件事 —— 以及它的代价。**
#    `docker inspect agenerp-agenerp-serve-1` 实读：活栈挂的是
#    `/Users/lize/Claude/Projects/AgenERP/agenerp`（主工作树），吃不到本分支的代码。
#    而 `app.html` 是**同源** fetch `/agenerp/home` 的，所以浏览器必须落在
#    「跑着本分支代码」的那个源上。做法：
#
#      1. 先在**活栈**上用真口令登录成车间工人，从浏览器上下文里取出 `sid`
#      2. `build_server(port=0)` 在本地起**本分支的真服务**（内核派端口，不猜数）
#      3. 把 `sid` 种到 `127.0.0.1` 这个源上 —— 服务端据此**真的去问站点**「你有哪些角色」
#      4. 浏览器打开本地服务的 `/agenerp/app`（**不带 `?view=`**）
#      5. `/api/resource/**` 用 `route.fetch()` **转发到活栈**并带上同一个 sid
#
#    ⚠️ **代价照实记**：第 5 步意味着资源请求是**测试转手**的，不是浏览器直连。
#    数据仍然是真的、仍然是**以工人身份**取的（sid 一路带着），
#    但**跨源/反向代理那一层本文件验不到** —— 生产上 serve 与 Frappe 同源，
#    这里不同源。要覆盖那一层，得让活栈吃到本分支代码，那不是判据能自己解决的事。
#
# ⑤ ⚠️ **路由那两格（③）在单测层已有覆盖**：
#    `tests/unit/test_render_static_and_plan.py` 用同样的 `build_server(port=0)` 真服务
#    验过「工人 → 自己的页」与「认不出人 → 落回 Desk」。
#    本门禁**不重写那两格的断言**，而是从**浏览器可见的结果**再判一次 ——
#    单测判的是服务回了什么 JSON，本门禁判的是**用户眼睛看到了什么**。
#    两者判的不是同一件事，不算重复。
#
# ============================================================================

"""🔴 门禁 · 角色首页不能是一个空工作台

判据来源：WBS `02-WBS.md` §5 P2.6。

## 它防的是什么

ERPNext 最经典的那个抱怨：装完之后打开是一片空白，用户不知道该点哪。
AgenERP 的 ②③ 端若重复这一点，路线 C 那套「按角色做到 100%」就白做了 ——
覆盖率再高，用户第一眼看到的还是空的。

## 它**不**验什么（写清楚，免得有人以为验了）

- **不验首页选得对不对**（那个人是不是该看这一页）—— 那是 `home_for_roles` 的映射表，
  由 `tests/unit/test_render_static_and_plan.py` 判。
- **不验数据本身对不对** —— 它只验「有」，不验「对」。
- **不验同源部署那一层** —— 见文件头 ④ 的代价说明。
"""
from __future__ import annotations

import json
import os
import threading
import urllib.parse

import pytest

from agenerp.serve.app import APP_PAGE_PATH, build_server

pytestmark = pytest.mark.live

WORKER_USER = "worker@hrd.example.com"
WORKER_PASSWORD_ENV = "AGENERP_WORKER_PASSWORD"
SITE_ENV = "AGENERP_SITE"
BASE_ENV = "AGENERP_SITE_URL"

RESOURCE_GLOB = "**/api/resource/**"
VIEW_ROOT = "#agenerp-view-root"


# ── 起本地真服务 ────────────────────────────────────────────────────────────


class _LocalServe:
    """在 `127.0.0.1:0` 上真起**本分支的**服务。端口由内核分配，不猜数。

    形态同 `tests/unit/test_render_static_and_plan.py::_Live`，但**不换掉
    `client_factory`** —— 这里要的就是它拿着真 sid 去真站点问角色。
    """

    def __init__(self, site: str) -> None:
        self.server = build_server(site=site, port=0)
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


def _fail_missing(reason: str):
    """⚠️ **fail 不是 skip** —— 本仓规矩 1：一条会 skip 的门禁等于一条不存在的门禁。"""
    pytest.fail(reason)


@pytest.fixture(scope="module")
def driver():
    """浏览器驱动。**`import playwright` 写在这里，不在模块顶层。**"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        _fail_missing(
            f"playwright 没装（{exc}）—— 活体门禁在驱动缺失时必须红，不许跳过。\n"
            "  python3 -m pip install -e '.[ui]' && python3 -m playwright install chromium"
        )
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(headless=True)
    except Exception as exc:
        manager.stop()
        _fail_missing(f"起不了 chromium（{exc}）—— `playwright install chromium` 没跑过？")
    try:
        yield browser
    finally:
        browser.close()
        manager.stop()


@pytest.fixture(scope="module")
def live_base() -> str:
    base = (os.environ.get(BASE_ENV) or "").strip()
    if not base:
        _fail_missing(f"{BASE_ENV} 没设 —— 不知道活栈在哪")
    return base.rstrip("/")


@pytest.fixture(scope="module")
def worker_session(driver, live_base):
    """一个**真登录过的车间工人**上下文，外加它的 `sid`。

    ⚠️ **必须是工人，不是 Administrator**（文件头 ②）。
    """
    password = (os.environ.get(WORKER_PASSWORD_ENV) or "").strip()
    if not password:
        _fail_missing(f"{WORKER_PASSWORD_ENV} 未设置 —— 换不到受限身份的真会话")

    session = driver.new_context(viewport={"width": 1400, "height": 900})
    tab = session.new_page()
    try:
        tab.goto(f"{live_base}/login", wait_until="domcontentloaded", timeout=60_000)
        tab.fill("#login_email", WORKER_USER)
        tab.fill("input[type=password]", password)
        tab.click("button.btn-login")
        tab.wait_for_url("**/app**", timeout=60_000)
        tab.wait_for_timeout(2_000)
    except Exception as exc:
        session.close()
        _fail_missing(
            f"{live_base} 上换不到车间工人的会话（{exc}）—— 活栈没起，"
            "或没跑过 `python3 -m agenerp.seedusers --load-users`"
        )

    sid = next((c["value"] for c in session.cookies() if c["name"] == "sid"), "")
    tab.close()
    if not sid:
        session.close()
        _fail_missing("登录成功但取不到 sid —— 后面每一格都会红在环境上而不是红在实现上")
    # ⚠️ sid 是明文短期凭据：**只在进程内传，不落盘、不进日志、不进断言消息**（§7.14）
    yield session, sid
    session.close()


@pytest.fixture(scope="module")
def local_serve(worker_session):
    """本地起本分支的服务，并把工人的 sid 种到 `127.0.0.1` 这个源上。"""
    site = (os.environ.get(SITE_ENV) or "").strip()
    if not site:
        _fail_missing(f"{SITE_ENV} 没设 —— 服务不知道该把 sid 拿去问哪个站点")
    session, sid = worker_session
    serve = _LocalServe(site)
    host = urllib.parse.urlparse(serve.base).hostname or "127.0.0.1"
    session.add_cookies([{"name": "sid", "value": sid, "domain": host, "path": "/"}])
    try:
        yield serve
    finally:
        serve.close()


def _open_home_as_worker(worker_session, local_serve, live_base):
    """登录态下打开**本地服务**的 `/agenerp/app`（不带 `?view=`）→ 等首页渲染完。

    ⚠️ **不带 `?view=`** 是关键：带了就变成「点名一个视图」，
    绕过了「这个人该落在哪一页」那一跳 —— 而那正是本门禁要验的。

    ⚠️ `/api/resource/**` **转发到活栈**并带上同一个 sid（文件头 ④ 第 5 步）：
    数据是真的、身份是工人的，但跨源那一层验不到。
    """
    session, sid = worker_session
    tab = session.new_page()

    def _to_live(route):
        target = urllib.parse.urlparse(route.request.url)
        url = f"{live_base}{target.path}"
        if target.query:
            url = f"{url}?{target.query}"
        try:
            resp = route.fetch(url=url, headers={**route.request.headers, "Cookie": f"sid={sid}"})
            route.fulfill(response=resp)
        except Exception as exc:  # noqa: BLE001
            # 转发失败要**看得出是转发失败**，不许长得像「渲染器没画出来」
            route.fulfill(
                status=599,
                content_type="application/json; charset=utf-8",
                body=json.dumps({"exception": f"判据转发到活栈失败：{exc}"}),
            )

    tab.route(RESOURCE_GLOB, _to_live)
    tab.goto(f"{local_serve.base}{APP_PAGE_PATH}", wait_until="domcontentloaded", timeout=60_000)
    tab.wait_for_selector(f"{VIEW_ROOT}[data-agenerp-rendered]", timeout=60_000)
    return tab


# ── 判据 ────────────────────────────────────────────────────────────────────


def test_the_role_home_is_not_an_empty_workspace(worker_session, local_serve, live_base):
    """三条缺一不可（见文件头 ①）：≥1 个块 · **≥1 行真数据** · 无落回卡片。"""
    page = _open_home_as_worker(worker_session, local_serve, live_base)

    blocks = page.query_selector_all(f"{VIEW_ROOT} [data-agenerp-block-type]")
    assert blocks, "首页一个块都没渲染出来"

    rows = page.query_selector_all(f"{VIEW_ROOT} table.agenerp-table tbody tr")
    real_rows = [r for r in rows if not r.query_selector("td.agenerp-empty")]
    assert real_rows, (
        "首页画出了表头，但**一行真数据都没有** —— DOM 上不空，用户眼里是空的。"
        "（硬约束 ①：渲染出来 ≠ 渲染对了）"
    )

    assert not page.query_selector(f"{VIEW_ROOT} [data-agenerp-fallback]"), (
        "目标角色的首页上出现了落回卡片 —— 路线 C 的承诺是这个角色日常路径上落回 = 0"
    )


def test_an_unresolvable_identity_gets_desk_not_an_empty_home(driver, local_serve):
    """见文件头 ③ 的前一半：**不知道你是谁** ⇒ 落回 Desk。

    用一个**全新、没有任何 cookie** 的上下文 —— 服务端拿不到 sid，
    正是「认不出人」那个形态。
    """
    anonymous = driver.new_context()
    tab = anonymous.new_page()
    try:
        tab.goto(f"{local_serve.base}{APP_PAGE_PATH}", wait_until="domcontentloaded",
                 timeout=60_000)
        tab.wait_for_selector("[data-agenerp-home-fallback]", timeout=30_000)
        host = tab.query_selector("[data-agenerp-home-fallback]")
        assert host.get_attribute("data-agenerp-home-fallback") == "desk", (
            "认不出身份时没有落回 Desk —— 给一个不属于他的首页，"
            "用户看到的是一片「你看不到这个」，那比落回 Desk 糟得多"
        )
        assert not tab.query_selector(f"{VIEW_ROOT} [data-agenerp-block-type]"), (
            "认不出身份，却still渲染出了块 —— 那就是在给别人的首页"
        )
    finally:
        anonymous.close()


def test_a_role_without_a_configured_home_gets_desk_not_someone_elses_home(
    driver, local_serve, worker_session, live_base
):
    """见文件头 ③ 的后一半：**知道你是谁但没配页** ⇒ 同样落回 Desk。

    ⚠️ 这一格**必须造一个真的「认得出但没配页」的身份**，不能拿匿名冒充 ——
    两者的服务端路径不同，用匿名跑等于把上一格跑了两遍。
    做法：把 `/agenerp/home` 的回包换成「角色解析成功但没有匹配的视图」那个形状，
    **只换这一条**，其余（含 `/agenerp/app` 本体）仍走本地真服务。
    """
    session, sid = worker_session
    tab = session.new_page()
    try:
        tab.route(
            "**/agenerp/home*",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json; charset=utf-8",
                body=json.dumps({"role": "某个没配首页的角色", "view": None,
                                 "fallback": "desk"}),
            ),
        )
        tab.goto(f"{local_serve.base}{APP_PAGE_PATH}", wait_until="domcontentloaded",
                 timeout=60_000)
        tab.wait_for_selector("[data-agenerp-home-fallback]", timeout=30_000)
        host = tab.query_selector("[data-agenerp-home-fallback]")
        assert host.get_attribute("data-agenerp-home-fallback") == "desk", (
            "角色认得出、但没配首页时没有落回 Desk"
        )
        assert not tab.query_selector(f"{VIEW_ROOT} [data-agenerp-block-type]"), (
            "没配首页却渲染出了块 —— 那就是把别人的首页给了他"
        )
    finally:
        tab.close()
