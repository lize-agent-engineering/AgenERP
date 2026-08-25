"""🔴 WBS §4 P1.8a 那条验收（`tests/gates/test_explain_service_live.py`）的**断言体**。

**这个文件是交接件。** 红线 1 禁止 loop 创建 `tests/gates/**` 下的任何文件，所以门禁那份
由**人**创建；人只需按路径加载本文件，**一行断言都不重写**（先例：P1.0a 的
`tests/gates/test_tool_execution_live.py`，commit `3b6d071`，`Gates-Change-Approved-By: lize`）。

## 为什么现在还不能加载

`.github/workflows/gates.yml` 的 `gates-l2-live` 契约逐字是「全部绿、零 red、零 skip」。
本文件要的两样东西**今天都还不存在**：

1. **服务本身没有接进 compose** —— 它今天只能由人手工 `python3 -m agenerp.serve` 起在宿主上；
2. **nginx 还没有 `location /agenerp/` 反代** —— 而 `sid` 是 `HttpOnly` **且按同源发送**，
   不同源就根本拿不到 cookie，这条判据的整个前提不成立。

两样都是**同一工作项第 2 个 plan** 的内容
（`docs/plans/p1-insight/2026-08-25-1159-2-explain-service-compose-and-same-origin.md`，
待起草）。⇒ **它落地的同一个提交里，人才应该把本文件按路径加载进 `tests/gates/`。**

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

    AGENERP_SERVE_BASE=http://127.0.0.1:18080 AGENERP_SITE=frontend \\
      AGENERP_ADMIN_PASSWORD=... python3 -m pytest -m live tests/gates/test_explain_service_live.py

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

pytestmark = pytest.mark.live

SERVE_BASE_ENV = "AGENERP_SERVE_BASE"
DEFAULT_SERVE_BASE = "http://127.0.0.1:18080"
SITE_ENV = "AGENERP_SITE"
ADMIN_USER_ENV = "AGENERP_ADMIN_USER"
ADMIN_PASSWORD_ENV = "AGENERP_ADMIN_PASSWORD"

HEALTH_PATH = "/agenerp/health"
EXPLAIN_PATH = "/agenerp/explain"
LOGIN_PATH = "/api/method/login"
LOGGED_USER_PATH = "/api/method/frappe.auth.get_logged_user"

FORGED_SID = "deadbeefdeadbeefdeadbeefdeadbeef"
QUESTION = "这张单据现在什么情况？"

TIMEOUT = 30


def _target() -> tuple[str, int, str]:
    """**同源前端**的地址 —— 判的是「经过 nginx 那一跳」，不是直连服务端口。

    直连服务端口能过而同源过不去，正是这条门禁唯一要抓的失败形态：
    `sid` 是 `HttpOnly` 且按同源发送，浏览器根本走不到直连那条路。
    """
    base = (os.environ.get(SERVE_BASE_ENV) or DEFAULT_SERVE_BASE).strip()
    parsed = urllib.parse.urlsplit(base)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    site = (os.environ.get(SITE_ENV) or "").strip()
    if not site:
        pytest.skip(f"{SITE_ENV} 未设置 —— 站点名决定 Host 头，compose 栈按 Host 分站")
    return host, port, site


def _request(method, path, *, headers=None, payload=None, expect_reachable=True):
    host, port, site = _target()
    head = {"Host": site, **(headers or {})}
    raw = None
    if payload is not None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        head["Content-Type"] = "application/json"
    conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
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
    status, raw, _ = _request("POST", EXPLAIN_PATH, payload={"question": QUESTION})

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
    )

    assert status in (200, 503), f"真 sid 却拿到了 HTTP {status}：{raw[:200]!r}"
    payload = json.loads(raw)
    if status == 503:
        # 「AI 未配置」是**未配置**状态，不是错误状态（`docker-compose.yml` 文件头规则 ②）。
        # 但它必须**指名缺哪个变量**，且**绝不是 200 空回答**。
        assert "AGENERP_LLM_" in payload["error"]
        pytest.skip("活栈上一个 AI 变量都没配 —— 503 已判，答案面留给配了的那次跑")

    assert payload["user"] == expected
    assert payload["answer"] or payload["accepted"] is False
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
        _, raw, _ = _request(method, path, headers=header, payload=payload)
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
