"""P1.8a 服务面判据的共用假件：**一个认 `sid` 的假站点**，零网络、零凭据、零 docker。

假模型端点与假站点数据**不在这里另写一份** —— 按路径复用 `tests/unit/explain_fakes.py`
（它自己又按路径复用 `tests/tools/conftest.py` 的 `FakeSite`）。多写一份就会各自漂移，
而它们是本 plan 全部判据的地基。

本模块只加**一层 `sid` 认人**：`FakeSite` 不认 cookie（它是给工具执行层写的），
而服务面的全部判据恰恰在问「这次请求是谁发的」。这一层把
`frappe.auth.get_logged_user` 的活站点实测形状搬进来（依据逐字见
`docs/analysis/2026-08-25-1159-explain-service-sid-probe.md`）：

- 有效 `sid` → **200** `{"message": "<user>"}`
- 伪造 `sid` / 完全不带 `Cookie` → **403**（**不是 200 空包**，也不是「200 + Guest」）
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import explain_fakes as fakes  # noqa: E402

from agenerp.site import SiteRequest, SiteResponse  # noqa: E402

LOGGED_USER_PATH = "/api/method/frappe.auth.get_logged_user"

VALID_SID = "sid-of-a-real-browser-session"
OTHER_SID = "sid-of-a-second-browser-session"
FORGED_SID = "sid-nobody-ever-issued"

# ⚠️ **刻意不是 `Administrator`。** 用一个别处不会凑巧出现的名字，
# 「`user` 真的来自 `sid` 解析」与「`user` 恰好等于某个默认值」才分得开。
SESSION_USER = "che.jian@example.test"
OTHER_USER = "cang.guan@example.test"

SESSIONS = {VALID_SID: SESSION_USER, OTHER_SID: OTHER_USER}


class SidAwareSite:
    """`FakeSite` 外面套一层 `sid` 认人。**每次请求的 `Cookie` 头逐条留痕。**"""

    def __init__(self, inner, sessions: dict[str, str] | None = None) -> None:
        self.inner = inner
        self.sessions = dict(SESSIONS if sessions is None else sessions)
        self.denied: set[tuple[str, str]] = set()
        self.requests: list[SiteRequest] = []
        self.cookies: list[str | None] = []
        self.authorizations: list[str | None] = []

    # ── 观测面 ──────────────────────────────────────────────────────────────
    @property
    def paths(self) -> list[str]:
        """**解码后**的路径 —— DocType 名带空格时 `SiteClient` 会编成 `%20`
        （`site.py` 模块头第二条硬约束），判据不该跟着编码走。"""
        return [
            urllib.parse.unquote(urllib.parse.urlparse(r.url).path) for r in self.requests
        ]

    @property
    def sids(self) -> list[str]:
        return [c.split("sid=", 1)[-1] if c else "" for c in self.cookies]

    def deny(self, doctype: str, name: str) -> None:
        """让站点对这一份单据回 403 —— 模拟「Frappe 判当前身份无权看它」。"""
        self.denied.add((doctype, name))

    # ── 传输面 ──────────────────────────────────────────────────────────────
    def __call__(self, request: SiteRequest) -> SiteResponse:
        self.requests.append(request)
        self.cookies.append(request.headers.get("Cookie"))
        self.authorizations.append(request.headers.get("Authorization"))

        sid = self._sid_of(request)
        path = urllib.parse.unquote(urllib.parse.urlparse(request.url).path)

        if path == LOGGED_USER_PATH:
            user = self.sessions.get(sid)
            if user is None:
                return self._forbidden(session_expired=bool(sid))
            return SiteResponse(200, json.dumps({"message": user}, ensure_ascii=False))

        if sid not in self.sessions:
            return self._forbidden(session_expired=bool(sid))

        tail = path[len("/api/resource/") :] if path.startswith("/api/resource/") else ""
        parts = tail.split("/", 1)
        if len(parts) == 2 and (parts[0], parts[1]) in self.denied:
            return self._forbidden(session_expired=False)

        return self.inner(request)

    @staticmethod
    def _sid_of(request: SiteRequest) -> str:
        cookie = request.headers.get("Cookie") or ""
        for chunk in cookie.split(";"):
            key, _, value = chunk.strip().partition("=")
            if key == "sid":
                return value.strip()
        return ""

    @staticmethod
    def _forbidden(*, session_expired: bool) -> SiteResponse:
        """活站点实测的形状：403 + `PermissionError`，伪造 `sid` 时多一个 `session_expired`。"""
        body: dict = {
            "exception": "frappe.exceptions.PermissionError: Login to access",
            "exc_type": "PermissionError",
        }
        if session_expired:
            body["session_expired"] = 1
        return SiteResponse(403, json.dumps(body))


def sid_site(sessions: dict[str, str] | None = None) -> SidAwareSite:
    """一个认 `sid` 的假站点，底下是 P1.4 那份带真实轨迹的 `FakeSite`。"""
    return SidAwareSite(fakes.explain_site(), sessions)


# ⚠️ **刻意不报任何数量、不点名任何单据。** 服务面判的是**请求面**，
# 不是 ② 作答前门禁的判定面（那归 `tests/unit/test_explain_loop.py`）。
# 报了数量就会被 L3 拦下、`answer` 变成空串，于是「服务把答案交出来了」与
# 「门禁拦住了」在服务面的判据里混成一件事 —— 那正是这里最不该混的两件事。
ANSWER = "这张单据看起来一切正常。"


def answered_script() -> list[dict]:
    """单轮剧本：模型直接作答，且**答案会被 ② 门禁放行**（`accepted is True`）。"""
    return [fakes.answer_step(ANSWER)]


def scripted_model(script: list[dict] | None = None):
    return fakes.ScriptedModel(script if script is not None else answered_script())
