"""P1.8a-fix 的离线判据：**守住 `D-26` 那次「一个预算拆成两个」的修法。**

## 它守的是什么

`gates-l2-live` 的间歇红只有一个机制（`docs/evidence/p1-8a-fix/p1-8-mechanism-statement.md`）：
一轮门禁恰好发 **2 次**真解释，某次的服务端墙钟越过断言体写死的客户端预算 `30`
⇒ 客户端在 `recv_into` 抛 `TimeoutError`，判据红；**而服务端没坏** —— 它算完仍去写
`200`，因对端已断开抛 `BrokenPipeError`，次数逐次相等（`758b7bc` 1↔1、`82a144a` 2↔2）。

人在 `D-26` 裁定那个 `30` 是**测试便利值**而非产品承诺，并把它拆成
`CHEAP_TIMEOUT = 30`（便宜请求，**卡住就是真故障，短预算有判别力**）与
`EXPLAIN_TIMEOUT = 180`（真解释，要等模型）。本文件挡的正是这次拆分被改回去。

## 它**不是**怎么写的（这三条是本文件的设计约束，别顺手改掉）

1. ⚠️ **不是「两边读同一个常量再比」。** 那种写法判据恒绿、修法被掏空也看不出来
   （工作项 11 的 M5 实测过这个窟窿：判据绿着、浏览器不执行）。**下面四条里有三条
   真的把断言体那几个函数跑起来**，用一个记录型的假 `HTTPConnection` 把
   「每一次请求实际拿到的预算」逐条录下来再判。
2. ⚠️ **不判「调得通」。** 「`_request()` 能跑完」不构成任何证据 —— 掏空之后它照样跑得完。
   判的是**预算有没有真的到达 `HTTPConnection`**、以及**哪几个调用点拿到了哪一个预算**。
3. ⚠️ **本文件不碰 `tests/unit/test_explain_service_body.py` 一个字节**（那是
   `tests/gates/test_explain_service_live.py:57` 经 `_load` 整体 `exec_module` 的唯一判据正文，
   **红线 1**）。它**按路径把那份加载进来**再驱动，加载器与 `explain_fakes` 同一个。

## 已知的一处不吻合，本文件**故意不判**（照实记，不粉饰）

`D-26` 的「哪几处用长预算」一格逐字列了三处（真 `sid` 的解释调用 + `echoes_the_sid` 循环里
`path == EXPLAIN_PATH` 的两条），并逐字把「伪造 `sid`（401 挡下）」「非法参数（400 挡下）」
留在短预算；而**落地的代码里第四处也用了长预算** ——
`test_explain_without_any_cookie_is_401_...`（`:201`，没带 cookie，同样在 401 就被挡下、
根本到不了模型）。按 `D-26` 自己那条理由它该是短预算。
⚠️ **本文件不把这一处写进断言**：改它要动断言体（**红线 1**），改 `D-26` 要动
`DECISIONS.md`（**红线 3**），**两条 loop 都无权**。已登记在 plan `2026-08-25-1118-1` 的
`Deferred But Adjudicated`，重开事件写在那里。
"""

from __future__ import annotations

import json

import pytest

from explain_fakes import load_repo_module

_BODY = load_repo_module(
    "tests/unit/test_explain_service_body.py", "_p1_8a_fix_explain_service_body"
)

BODY_PATH = "tests/unit/test_explain_service_body.py"

# 实测钉住的两个数，来源都不是本文件的偏好：
#   30  —— `D-26` 逐字保留给便宜请求的短预算上限（再宽就没有判别力了）
#   120 —— `P1-3` 量到的长尾越过 30s、上界未测出；长预算必须**远**大于它才叫修法，
#          而不是把 30 挪到 31。`D-26` 落地的是 180，本条只判下界。
CHEAP_CEILING = 30
EXPLAIN_FLOOR = 120


class _Response:
    """假回包。`status` / `body` 由每条判据自己给，本类不替它们决定任何事。"""

    def __init__(self, status: int, body: bytes, set_cookie: str = "") -> None:
        self.status = status
        self._body = body
        self._set_cookie = set_cookie

    def read(self) -> bytes:
        return self._body

    def getheader(self, name: str):
        return self._set_cookie if name == "Set-Cookie" else None


class _Recorder:
    """记录型假连接：**把每一次请求实际拿到的预算逐条录下来。**

    `routes` 是 `(method, path) -> _Response`；命中不了就抛 `AssertionError`，
    **不静默回一个空壳** —— 断言体多发一条请求时本文件必须当场红，而不是悄悄放过。
    """

    def __init__(self, routes: dict[tuple[str, str], _Response]) -> None:
        self.routes = routes
        self.calls: list[dict] = []

    def factory(self, host, port, timeout=None):
        recorder = self

        class _Conn:
            def __init__(self) -> None:
                self._key: tuple[str, str] | None = None

            def request(self, method, path, body=None, headers=None):
                self._key = (method, path)
                recorder.calls.append(
                    {"method": method, "path": path, "timeout": timeout,
                     "host": host, "port": port}
                )

            def getresponse(self):
                assert self._key in recorder.routes, f"断言体发了一条没预备的请求：{self._key}"
                return recorder.routes[self._key]

            def close(self):
                return None

        return _Conn()

    def budget_for(self, method: str, path: str) -> list:
        return [c["timeout"] for c in self.calls if c["method"] == method and c["path"] == path]


def _arm(monkeypatch, routes) -> _Recorder:
    """把假连接与最小环境装上。**每条判据各装一次**，不留全局状态。"""
    recorder = _Recorder(routes)
    monkeypatch.setattr(_BODY.http.client, "HTTPConnection", recorder.factory)
    monkeypatch.setenv(_BODY.SERVE_BASE_ENV, "http://127.0.0.1:8080")
    monkeypatch.setenv(_BODY.SITE_ENV, "frontend")
    monkeypatch.setenv(_BODY.ADMIN_PASSWORD_ENV, "not-a-real-password")
    return recorder


_SID = "sid-value-that-must-never-be-echoed"
_LOGIN_OK = _Response(200, b'{"message":"Logged In"}', set_cookie=f"sid={_SID}; HttpOnly")
_WHOAMI_OK = _Response(200, json.dumps({"message": "Administrator"}).encode())
_EXPLAIN_OK = _Response(
    200,
    json.dumps(
        {
            "user": "Administrator",
            "answer": "一句答案",
            "accepted": True,
            "cost": {"total": {"prompt": 1, "completion": 2, "reasoning": 0,
                               "cached": 0, "total": 3}},
        }
    ).encode(),
)


def test_the_two_budgets_are_separate_and_the_merged_name_is_gone():
    """两个预算各自存在、方向正确，**且合并回去的那个名字已经不在了**。

    ⚠️ 最后一条断言是本条的要点：只判「有 `EXPLAIN_TIMEOUT`」挡不住有人把
    `TIMEOUT = 30` 加回来再让调用点用它 —— 那正是「悄悄改回去」的形状。
    """
    assert hasattr(_BODY, "CHEAP_TIMEOUT"), f"{BODY_PATH} 里没有 CHEAP_TIMEOUT —— D-26 的拆分被改回去了"
    assert hasattr(_BODY, "EXPLAIN_TIMEOUT"), f"{BODY_PATH} 里没有 EXPLAIN_TIMEOUT —— D-26 的拆分被改回去了"
    assert not hasattr(_BODY, "TIMEOUT"), (
        f"{BODY_PATH} 里又出现了合并的 TIMEOUT —— D-26 逐字裁定「拆成两个预算，不是把 30 调大」"
    )

    assert _BODY.EXPLAIN_TIMEOUT > _BODY.CHEAP_TIMEOUT
    assert _BODY.CHEAP_TIMEOUT <= CHEAP_CEILING, (
        "便宜请求的预算被放宽了 —— 健康检查/404 卡住就是真故障，短预算是它们唯一的判别力"
    )
    assert _BODY.EXPLAIN_TIMEOUT >= EXPLAIN_FLOOR, (
        "长预算不足以越过 P1-3 实测的长尾（>30s 且上界未测出）—— 把 30 挪到 31 不是修法"
    )


def test_the_budget_actually_reaches_the_socket(monkeypatch):
    """**行为判据**：给出去的预算真的到了 `HTTPConnection`，不是被吞掉的形参。

    ⚠️ 这一条挡的是「改成空壳」：有人给 `_request()` 加了 `timeout=` 形参却仍在
    内部写死一个数 —— 那时上一条判据照样绿，只有本条会红。
    """
    routes = {("GET", "/whatever"): _Response(200, b"{}")}

    recorder = _arm(monkeypatch, routes)
    _BODY._request("GET", "/whatever")
    assert recorder.budget_for("GET", "/whatever") == [_BODY.CHEAP_TIMEOUT], (
        "不给 timeout 时的默认预算没到达 socket"
    )

    recorder = _arm(monkeypatch, routes)
    _BODY._request("GET", "/whatever", timeout=7)
    assert recorder.budget_for("GET", "/whatever") == [7], (
        "显式给的 timeout 没到达 socket —— timeout= 是个被吞掉的形参"
    )


def test_the_call_that_waits_on_the_model_gets_the_long_budget(monkeypatch):
    """**行为判据**：真跑一遍那条「真 `sid` → 200」的断言体，逐条录预算。

    要点在**对照**：同一次跑里，登录与 `get_logged_user` 拿短预算、
    只有那一发真解释拿长预算。⇒ 「整份文件一起放宽」与「只放宽真解释」在本条上分得开。
    """
    recorder = _arm(monkeypatch, {
        ("POST", _BODY.LOGIN_PATH): _LOGIN_OK,
        ("POST", _BODY.LOGGED_USER_PATH): _WHOAMI_OK,
        ("POST", _BODY.EXPLAIN_PATH): _EXPLAIN_OK,
    })

    _BODY.test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to()

    assert recorder.budget_for("POST", _BODY.EXPLAIN_PATH) == [_BODY.EXPLAIN_TIMEOUT], (
        "真解释那一发没拿到长预算 —— 这正是 gates-l2-live 间歇红的那一发"
    )
    assert recorder.budget_for("POST", _BODY.LOGIN_PATH) == [_BODY.CHEAP_TIMEOUT]
    assert recorder.budget_for("POST", _BODY.LOGGED_USER_PATH) == [_BODY.CHEAP_TIMEOUT], (
        "登录/认人这两发被一起放宽了 —— 它们到不了模型，卡住就是真故障"
    )


def test_the_sid_echo_loop_picks_its_budget_per_request(monkeypatch):
    """**行为判据**：`echoes_the_sid` 那个循环混着便宜请求与真解释，**逐条选预算**。

    ⚠️ 这一条挡的是「为了少写一行就把整个循环放宽」：那样改完之后
    健康检查与 404 也拿到 180 秒，而**它们卡住就是真故障**。
    """
    clean = _Response(200, b'{"ok":true}')
    recorder = _arm(monkeypatch, {
        ("POST", _BODY.LOGIN_PATH): _LOGIN_OK,
        ("GET", _BODY.HEALTH_PATH): clean,
        ("GET", "/agenerp/nope"): _Response(404, b'{"error":"nope"}'),
        ("POST", _BODY.EXPLAIN_PATH): clean,
    })

    _BODY.test_no_response_through_the_front_ever_echoes_the_sid()

    assert recorder.budget_for("GET", _BODY.HEALTH_PATH) == [_BODY.CHEAP_TIMEOUT]
    assert recorder.budget_for("GET", "/agenerp/nope") == [_BODY.CHEAP_TIMEOUT], (
        "循环里的便宜请求跟着真解释一起被放宽了"
    )
    assert recorder.budget_for("POST", _BODY.EXPLAIN_PATH) == [
        _BODY.EXPLAIN_TIMEOUT, _BODY.EXPLAIN_TIMEOUT
    ], "循环里那两发真解释没拿到长预算"


def test_the_recorder_itself_would_notice_a_wrong_budget(monkeypatch):
    """**自反判据**：假连接不是摆设 —— 换一个预算，上面那几条会真的看见差别。

    ⚠️ 没有这一条，`_Recorder` 悄悄不记录时上面三条会**恒绿**
    （`budget_for()` 返回空列表，而空列表 `== [x]` 是假 —— 但若有人把断言写成
    `all(...)` 形态就会恒真）。本条把「录得到」这件事本身钉住。
    """
    routes = {("GET", "/whatever"): _Response(200, b"{}")}
    recorder = _arm(monkeypatch, routes)

    _BODY._request("GET", "/whatever", timeout=1)
    _BODY._request("GET", "/whatever", timeout=2)

    assert recorder.budget_for("GET", "/whatever") == [1, 2]
    assert len(recorder.calls) == 2


def test_the_body_still_loads_from_its_pinned_path():
    """源文件没了就是红，不是少跑几条判据（与 `explain_fakes` 同一条规矩）。"""
    with pytest.raises(FileNotFoundError):
        load_repo_module("tests/unit/no-such-body.py", "_p1_8a_fix_missing_body")
