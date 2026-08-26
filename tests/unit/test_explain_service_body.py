"""🔴 WBS §4 P1.8a 那条验收（`tests/gates/test_explain_service_live.py`）的**断言体**。

**这个文件是交接件。** 红线 1 禁止 loop 创建 `tests/gates/**` 下的任何文件，所以门禁那份
由**人**创建；人只需按路径加载本文件，**一行断言都不重写**（先例：P1.0a 的
`tests/gates/test_tool_execution_live.py`，commit `3b6d071`，`Gates-Change-Approved-By: lize`）。

## 加载前提：两样东西已经到位，第三样还没有

`.github/workflows/gates.yml` 的 `gates-l2-live` 契约逐字是「全部绿、零 red、零 skip」。

原先挡着加载的两样，**已由 P1.8a 的第 2 个 plan 交付**
（`docs/plans/p1-insight/2026-08-25-1423-1-explain-service-compose-and-same-origin.md`，
落点 `docs/architecture/module-boundaries.md` §7.21）：

1. ✅ **服务已接进 compose** —— `docker-compose.yml` 的 `agenerp-serve` 服务块；
2. ✅ **nginx 已有 `location /agenerp/` 反代** —— `tools/nginx/frappe.conf.template`
   覆盖上游那份模板，那段 `location` 坐在唯一那个 `listen 8080` server 块里。

⚠️ **但还有第三样，它挡着「加载后就能绿」，且两条出路都是人的**：
本文件第 4 条（`test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`）
在 **503 分支上自带一个 `pytest.skip`**，而 `gates-l2-live` 起栈时**一个 AI 变量都不配**
⇒ 那一条在 CI 上必然 `skip`，而契约是**零 skip**。
两条出路：① 给 `gates-l2-live` 补 `AGENERP_LLM_*`（改 `.github/workflows/**`，红线 2）；
② 把 503 分支从 `skip` 改成 `pass`（**那是在改判据自身的口径** —— 改完之后，一次
**从未真正调过模型**的跑也能让门禁绿）。**loop 无权选**，见 `STATE.md` §3 的 `[needs-human]`。

## 给人的加载片段

    _BODY = _load_sibling_module(
        "tests/unit/test_explain_service_body.py", "_p1_8a_explain_service_body"
    )
    test_health_is_200_through_the_same_origin_front = (
        _BODY.test_health_is_200_through_the_same_origin_front
    )
    ...

⚠️ 加载器必须**先把模块塞进 `sys.modules` 再 `exec_module`**（`explain_fakes` 里那个
`load_repo_module` 是同一形状，理由写在那里）。
⚠️ **basename 必须与门禁那份不同**（本文件 `..._body.py`，门禁那份
`test_explain_service_live.py`）：`tests/` 没有 `__init__.py`，同名 basename 会让整轮
`pytest` `import file mismatch` 收集失败。

## 加载后跑什么

    AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=... \\
      python3 -m pytest -m live tests/gates/test_explain_service_live.py

**基址不用手给**：`_target()` 的解析口径与 `agenerp/site.py` 的 `default_base_url()`
**是同一套** —— `AGENERP_SERVE_BASE` > `AGENERP_SITE_URL` > `http://127.0.0.1:${AGENERP_HTTP_PORT:-8080}`。
`gates-l2-live` 已有的 `AGENERP_SITE_URL=http://127.0.0.1:8080` 直接命中第二级。

⚠️ **本机栈如果不是发布在默认的 8080 上，就要显式给**（观测出来的事实，不是配置出来的期望 ——
`docker compose ps` 看 `frontend` 那格发布口）：

    AGENERP_SERVE_BASE=http://127.0.0.1:18080 AGENERP_SITE=frontend \\
      AGENERP_ADMIN_PASSWORD=... python3 -m pytest tests/unit/test_explain_service_body.py -q

（本文件此前把 `http://127.0.0.1:18080` 写成**默认值**，那个默认值只对起草者那台机器成立，
在 CI 上指着一个根本不存在的端口 ⇒ 六条会红在「连不上」而不是红在实现。
已按 §7.21 `D-b-5` 修直，**六条断言的判定逻辑一个字未改**。）

## ⚠️ 人要做的**一处收严**，loop 不替人做

本文件在**够不到服务时 `skip`**（它住在 `tests/unit/`，日常那一轮不该因为没起服务就红）。
门禁那份**必须把 skip 改成 fail** —— `gates-l2-live` 的契约是「零 skip」，
一条会 skip 的门禁等于一条不存在的门禁。收严的那一行由人写，理由同 P1.0a。

⚠️ **本文件零写操作、零 `sid` 落盘**：只发 `GET` 与两条只读白名单 `POST`
（`/api/method/login` 与本服务的 `/agenerp/explain`）；真 `sid` 只存在于进程内存里，
不 `print`、不写文件、不进任何断言消息（断言只判「它**不**在回包里」）。
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.parse

import pytest

from agenerp.site import default_base_url

pytestmark = pytest.mark.live

SERVE_BASE_ENV = "AGENERP_SERVE_BASE"
SITE_ENV = "AGENERP_SITE"
ADMIN_USER_ENV = "AGENERP_ADMIN_USER"
ADMIN_PASSWORD_ENV = "AGENERP_ADMIN_PASSWORD"

HEALTH_PATH = "/agenerp/health"
EXPLAIN_PATH = "/agenerp/explain"
LOGIN_PATH = "/api/method/login"
LOGGED_USER_PATH = "/api/method/frappe.auth.get_logged_user"

FORGED_SID = "deadbeefdeadbeefdeadbeefdeadbeef"
QUESTION = "这张单据现在什么情况？"

# 两个预算，**故意分开**（人 2026-08-26 改，见 `DECISIONS.md` D-26）。
#
# 原先只有一个 `TIMEOUT = 30`，便宜请求与真解释共用 —— 那是 `gates-l2-live`
# 间歇红的**唯一机制**（loop 的机制陈述：`docs/evidence/p1-8a-fix/`）：
# 某一次真解释的服务端墙钟越过 30 秒，客户端在 `recv_into` 抛 `TimeoutError`，
# 判据红；**而服务端没坏** —— 它算完仍去写 200，因对端已断开抛 `BrokenPipeError`。
# 次数逐一对得上：`758b7bc` 1 次 ↔ 1 failed，`82a144a` 2 次 ↔ 2 failed。
#
# ⚠️ **为什么是「分开」而不是「把 30 调大」**：调大单个值会把便宜请求的预算
# 一起放宽 —— 而健康检查/404 那几条**卡住就是真故障**，它们的短预算有判别力，
# 不能陪着一起松。**一个判据只测一件事。**
#
# ⚠️ **30 从来不是产品承诺**：2026-08-26 实读 `DECISIONS.md` 与 `02-WBS.md`，
# **本项目从未承诺过任何解释延迟 SLO**；这个数原本就摆在 `FORGED_SID` /
# `QUESTION` 这些测试夹具中间，无注释、无决策条背书 —— **是测试便利值**。
# 若将来要立延迟 SLO，那是**另一条独立判据**的事，不该由这几条正确性判据
# 顺带承担（它们问的是「答案里的人对不对」，不是「答案多久回来」）。
CHEAP_TIMEOUT = 30
# 真解释要等模型。实测墙钟：本机 1.72s / 1.90s，CI 绿 run ≈3–6s；长尾越过 30s。
# 180 是「服务真挂了仍能失败退出」与「不被模型长尾误判」之间的取值 ——
# **它不是承诺，只是判据的上限**；长尾成因（P1-8 未查明那一格）不因本改动而消失。
EXPLAIN_TIMEOUT = 180


def _target() -> tuple[str, int, str]:
    """**同源前端**的地址 —— 判的是「经过 nginx 那一跳」，不是直连服务端口。

    直连服务端口能过而同源过不去，正是这条门禁唯一要抓的失败形态：
    `sid` 是 `HttpOnly` 且按同源发送，浏览器根本走不到直连那条路。
    """
    base = (os.environ.get(SERVE_BASE_ENV) or default_base_url()).strip()
    parsed = urllib.parse.urlsplit(base)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    site = (os.environ.get(SITE_ENV) or "").strip()
    if not site:
        pytest.skip(f"{SITE_ENV} 未设置 —— 站点名决定 Host 头，compose 栈按 Host 分站")
    return host, port, site


def _request(method, path, *, headers=None, payload=None, expect_reachable=True, timeout=CHEAP_TIMEOUT):
    host, port, site = _target()
    head = {"Host": site, **(headers or {})}
    raw = None
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        head["Content-Type"] = "application/json"
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(method, path, body=raw, headers=head)
        response = conn.getresponse()
        return response.status, response.read(), response.getheader("Set-Cookie") or ""
    except OSError as exc:
        if expect_reachable:
            # ⚠️ 人把本文件加载进 `tests/gates/` 时，**这一句要改成 fail**（见文件头）。
            pytest.skip(f"{host}:{port} 够不到（{exc}）—— 同源前端没在跑")
        raise
    finally:
        conn.close()


def _real_sid() -> str:
    """真登录换一个真 `sid`。**它只存在于本进程内存里** —— 不打印、不落盘、不进断言消息。"""
    user = (os.environ.get(ADMIN_USER_ENV) or "Administrator").strip()
    password = (os.environ.get(ADMIN_PASSWORD_ENV) or "").strip()
    if not password:
        pytest.skip(f"{ADMIN_PASSWORD_ENV} 未设置 —— 换不到真 sid")
    status, _, set_cookie = _request(
        "POST", LOGIN_PATH, payload={"usr": user, "pwd": password}
    )
    assert status == 200, f"登录没成功：HTTP {status}"
    for chunk in set_cookie.split(","):
        for part in chunk.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "sid" and value.strip():
                return value.strip()
    raise AssertionError("登录回包里没有 sid cookie")


def _who_am_i(sid: str) -> str:
    status, raw, _ = _request("POST", LOGGED_USER_PATH, headers={"Cookie": f"sid={sid}"})
    assert status == 200, f"站点认不出这个 sid：HTTP {status}"
    return json.loads(raw)["message"]


# ── 断言体 ──────────────────────────────────────────────────────────────────


def test_health_is_200_through_the_same_origin_front():
    """`/agenerp/health` **经 nginx** 回 200 —— 反代那条 `location` 真的在。

    它**不认人**：这一条刻意不带任何 cookie。带上就分不清
    「反代通了」与「碰巧登录着」。
    """
    status, raw, _ = _request("GET", HEALTH_PATH)

    assert status == 200, f"同源前端没把 {HEALTH_PATH} 反代到服务：HTTP {status}"
    assert json.loads(raw)["service"] == "agenerp-explain"


def test_explain_without_any_cookie_is_401_through_the_same_origin_front():
    """没有 cookie → **401**。这是「身份只从 `sid` 来」在活栈上的那一半。"""
    status, raw, _ = _request("POST", EXPLAIN_PATH, payload={"question": QUESTION}, timeout=EXPLAIN_TIMEOUT)

    assert status == 401, f"没带 cookie 却拿到了 HTTP {status}：{raw[:200]!r}"


def test_explain_with_a_forged_sid_is_401_and_never_falls_back():
    """伪造 `sid` → **401**，**不是 200**。

    ⚠️ 这一条才是整份门禁的核心：**回退到环境凭据**的实现在这里会回 200
    （服务端本机有 `AGENERP_ADMIN_PASSWORD`，回退之后它会以管理员身份作答）。
    离线判据⑧ 扫的是「代码里没有回退零件」，本条判的是「活栈上真的没回退」。
    """
    status, raw, _ = _request(
        "POST", EXPLAIN_PATH,
        headers={"Cookie": f"sid={FORGED_SID}"},
        payload={"question": QUESTION},
    )

    assert status == 401, f"伪造 sid 却拿到了 HTTP {status}：{raw[:200]!r}"


def test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to():
    """真 `sid` → **200**，且回包里的 `user` **等于站点自己解析出的那个人**。

    「等于站点解析出的那个人」是要点：断言的右边取自
    `frappe.auth.get_logged_user`，不是取自本仓写死的常量 ——
    写死之后这条判据就只是在验证一个字符串等于它自己。
    """
    sid = _real_sid()
    expected = _who_am_i(sid)

    status, raw, _ = _request(
        "POST", EXPLAIN_PATH,
        headers={"Cookie": f"sid={sid}"},
        payload={"question": QUESTION},
        timeout=EXPLAIN_TIMEOUT,   # 真 sid ⇒ 会真调模型，用长预算
    )

    assert status in (200, 503), f"真 sid 却拿到了 HTTP {status}：{raw[:200]!r}"
    payload = json.loads(raw)
    if status == 503:
        # 「AI 未配置」是**未配置**状态，不是错误状态（`docker-compose.yml` 文件头规则 ②）。
        # 但它必须**指名缺哪个变量**，且**绝不是 200 空回答**。
        assert "AGENERP_LLM_" in payload["error"]
        pytest.skip("活栈上一个 AI 变量都没配 —— 503 已判，答案面留给配了的那次跑")

    assert payload["user"] == expected

    # 🔴 **这一条 2026-08-26 由 `or` 收严成两条独立断言。**
    #
    # 原本逐字是 `assert payload["answer"] or payload["accepted"] is False` ——
    # 一个 `or`。模型拒绝时 `accepted` 恰好就是 `False`，于是**空答案照过**。
    # 实测后果：CI 里配的模型走到 `route()` 后被换成一个没有免费额度的模型，
    # 每一次解释都 403、每一次都回空答案，而这条判据**一路绿着**。
    # ⇒ 那阵子的「全绿」在「Agent 到底能不能答」这一维上是空的。
    #
    # 收严后两条各测一件事，谁坏了都指得出来：
    assert payload["accepted"] is True, (
        f"真 sid、真模型，解释却没被接受。回包：{payload!r}\n"
        "服务在不接受时会带回 `stopped` / `reason` —— 先读那两个字段，不要靠猜。"
    )
    assert payload["answer"].strip(), (
        f"`accepted` 为真却交回空答案 —— 判定面与产出面不一致。回包：{payload!r}"
    )
    assert set(payload["cost"]["total"]) == {
        "prompt", "completion", "reasoning", "cached", "total"
    }
    total = payload["cost"]["total"]
    assert total["total"] == total["prompt"] + total["completion"], "cached 混进 total 了"


def test_no_response_through_the_front_ever_echoes_the_sid():
    """回包**逐字节**不含 `sid` 值 —— 经过反代之后依然如此。

    断言只判「它**不**在里面」：真 `sid` 一个字节都不会出现在失败消息里。
    """
    sid = _real_sid()
    raw_sid = sid.encode("utf-8")
    header = {"Cookie": f"sid={sid}"}

    for method, path, payload in (
        ("GET", HEALTH_PATH, None),
        ("GET", "/agenerp/nope", None),
        ("POST", EXPLAIN_PATH, {"question": QUESTION}),
        ("POST", EXPLAIN_PATH, {"role": "System Manager"}),
    ):
        # 本循环混着便宜请求与真解释：**逐条按 path 选预算**，不要为了少写
        # 一行就把便宜的那几条也放宽（理由见文件头 CHEAP_TIMEOUT 注释）。
        _, raw, _ = _request(
            method, path, headers=header, payload=payload,
            timeout=EXPLAIN_TIMEOUT if path == EXPLAIN_PATH else CHEAP_TIMEOUT,
        )
        assert raw_sid not in raw, f"{method} {path} 的回包里回显了 sid"


def test_caller_claimed_context_is_rejected_through_the_front():
    """请求体自带 `fields` / `role` / `view` / `actions` / `user` → **400**，不是静默忽略。

    经过反代这一跳之后依然如此 —— nginx 不会替谁把请求体洗一遍。
    """
    sid = _real_sid()
    for key, value in (
        ("fields", {"grand_total": 0}),
        ("role", "System Manager"),
        ("view", "form"),
        ("actions", ["submitted"]),
        ("user", "Administrator"),
    ):
        status, raw, _ = _request(
            "POST", EXPLAIN_PATH,
            headers={"Cookie": f"sid={sid}"},
            payload={"question": QUESTION, key: value},
        )
        assert status == 400, f"{key} 被收下了：HTTP {status} {raw[:200]!r}"
        assert key in json.loads(raw)["error"]
