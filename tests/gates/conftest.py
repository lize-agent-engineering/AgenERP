"""门禁测试的 harness 接缝 —— 裁判的感官。

这些 fixture 不做判断，但它们决定裁判**能不能看见真相**：一个假的 `live_site`
能让 L2 全绿而站点根本没起来。所以它们和断言体一样在红线内，只有人能写。

三条不可动摇的规矩，写在最前面，因为它们比代码本身重要：

1. **绝不伪装成功。** 环境不具备时必须**失败**（`pytest.fail`），不许 `skip`、
   不许返回替身对象。skip 会被 `tools/gates/check_expected_red.py` 判为违规——
   那正是为了挡住「用跳过换绿灯」这条路。
2. **不碰不属于自己的东西。** 若整栈在 fixture 启动前就已经跑着，用完**不拆**
   （那是人的栈）；只拆自己拉起来的。站点上建的探针字段一律在 teardown 删干净。
3. **默认不跑。** L2 要拉起完整 ERPNext，分钟级。快门禁每轮都跑一次的话循环没法用。
   因此需显式 `AGENERP_LIVE=1` 才真跑，否则**红着**并说明怎么跑——
   红在「本轮没打算跑 L2」，而不是红在「实现不存在」。

跑 L2：

    AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q

⚠️ 本文件在 `tests/gates/**` 红线内：loop 不得修改（含把 fail 改成 skip）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ["docker", "compose", "-f", str(REPO_ROOT / "docker-compose.yml")]
SITE_NAME = "frontend"
HTTP_PORT = os.environ.get("AGENERP_HTTP_PORT", "8080")
BASE_URL = f"http://127.0.0.1:{HTTP_PORT}"
ADMIN_USER = "Administrator"
ADMIN_PASSWORD = os.environ.get("AGENERP_ADMIN_PASSWORD", "admin")
UP_TIMEOUT = int(os.environ.get("AGENERP_LIVE_UP_TIMEOUT", "900"))

_LIVE_HINT = (
    "L2 门禁默认不跑（要拉起完整 ERPNext，分钟级）。真要跑：\n"
    "    AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q\n"
    "这不是 skip —— 判定器不接受 skip，未跑就是红。"
)


def _require_live(what: str) -> None:
    if os.environ.get("AGENERP_LIVE") != "1":
        pytest.fail(f"{what} 需要 AGENERP_LIVE=1。\n{_LIVE_HINT}")
    if shutil.which("docker") is None:
        pytest.fail(f"{what} 需要 docker，但本机 PATH 里没有。")


def _compose(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(COMPOSE + list(args), capture_output=True, text=True, timeout=timeout)


def _port_occupant(port: str) -> str:
    """谁占着这个端口。空字符串表示没人占。

    实测教训：本机另有一套 ERPNext 演示栈常驻 8080，`up` 会以
    `Bind for 0.0.0.0:8080 failed: port is already allocated` 失败 —— 那条报错
    埋在几十行容器启动日志里，不预检的话看半天才明白是端口的事。
    """
    try:
        r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=15)
        lines = [ln for ln in r.stdout.splitlines()[1:] if ln.strip()]
        return lines[0].split()[0] if lines else ""
    except Exception:
        return ""


# --------------------------------------------------------------------------
# compose_stack —— 整栈
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Service:
    name: str
    health: str


@dataclass(frozen=True)
class Response:
    status_code: int
    text: str


class ComposeStack:
    def __init__(self, started_by_us: bool) -> None:
        self.started_by_us = started_by_us

    def services(self) -> list[Service]:
        """当前栈里**长期运行**的服务及其健康状态。

        一次性容器（configurator / create-site）跑完即退，不计入——它们的
        `exited` 状态不代表不健康，混进来会让「全部 healthy」永远不成立。
        没有 healthcheck 的服务按运行状态折算，避免空字符串被误判为不健康。
        """
        r = _compose("ps", "--format", "json")
        if r.returncode != 0:
            pytest.fail(f"docker compose ps 失败（exit {r.returncode}）：{r.stderr[:400]}")
        out: list[Service] = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            name = row.get("Service") or row.get("Name") or "?"
            if name in {"configurator", "create-site"}:
                continue
            health = (row.get("Health") or "").strip()
            if not health:
                health = "healthy" if row.get("State") == "running" else (row.get("State") or "unknown")
            out.append(Service(name=name, health=health))
        return out

    def http_get(self, path: str, timeout: int = 30) -> Response:
        req = urllib.request.Request(BASE_URL + path, headers={"Host": SITE_NAME})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return Response(resp.status, resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return Response(e.code, e.read().decode("utf-8", "replace"))
        except Exception as e:  # 连不上也要给出可判定的结果，而不是抛到测试外
            pytest.fail(f"GET {path} 连不上 {BASE_URL}：{e}")


@pytest.fixture(scope="session")
def compose_stack():
    _require_live("compose_stack")
    before = _compose("ps", "--format", "json")
    already_up = bool(before.stdout.strip()) and before.returncode == 0
    if not already_up:
        occupant = _port_occupant(HTTP_PORT)
        if occupant:
            pytest.fail(
                f"端口 {HTTP_PORT} 已被 `{occupant}` 占用，门禁栈起不来。\n"
                f"本机另有服务常驻该端口时，换一个跑：\n"
                f"    AGENERP_HTTP_PORT=8099 AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q\n"
                f"（不自动挑空闲端口 —— 那会把一个真实冲突藏起来）"
            )
        # --wait 让 docker 自己等 healthcheck，不用我们轮询猜
        r = _compose("up", "-d", "--wait", timeout=UP_TIMEOUT)
        if r.returncode != 0:
            # 先拆掉自己起的那部分再 fail。fixture 在 yield 之前 fail 的话
            # teardown 不会执行，半拉起的栈会漏在机器上 —— 实测踩过。
            _compose("down", timeout=300)
            pytest.fail(f"docker compose up 失败（exit {r.returncode}）：{r.stderr[-1200:]}")
    stack = ComposeStack(started_by_us=not already_up)
    yield stack
    if stack.started_by_us:
        _compose("down", timeout=300)
    # 栈本来就跑着的话不拆 —— 那是别人的栈


# --------------------------------------------------------------------------
# live_site —— 可写的活站点
# --------------------------------------------------------------------------
class LiveSite:
    """经 REST API 操作真站点。每一次调用都真的打到站点上，没有本地缓存。"""

    def __init__(self) -> None:
        self.name = SITE_NAME
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor()
        )
        self._created: list[str] = []
        self._login()

    def _call(self, path: str, payload: dict | None = None, method: str | None = None) -> tuple[int, str]:
        data = json.dumps(payload).encode() if payload is not None else None
        # DocType 名带空格（`Custom Field`），不编码的话 http.client 直接以
        # "URL can't contain control characters" 拒掉 —— 实测踩过。
        # 只编码路径段，保留 `/` 分隔。
        safe_path = urllib.parse.quote(path, safe="/")
        req = urllib.request.Request(
            BASE_URL + safe_path, data=data,
            headers={"Host": SITE_NAME, "Content-Type": "application/json", "Accept": "application/json"},
            method=method or ("POST" if data else "GET"),
        )
        try:
            with self._opener.open(req, timeout=60) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def _login(self) -> None:
        code, body = self._call("/api/method/login", {"usr": ADMIN_USER, "pwd": ADMIN_PASSWORD})
        if code != 200:
            pytest.fail(f"站点登录失败（HTTP {code}）：{body[:400]}")

    @staticmethod
    def _cf_name(doctype: str, fieldname: str) -> str:
        return f"{doctype}-{fieldname}"

    def add_custom_field(self, doctype: str, fieldname: str, fieldtype: str = "Data") -> None:
        code, body = self._call("/api/resource/Custom Field", {
            "dt": doctype, "fieldname": fieldname, "label": fieldname, "fieldtype": fieldtype,
        })
        if code not in (200, 201):
            pytest.fail(f"建 Custom Field {doctype}.{fieldname} 失败（HTTP {code}）：{body[:400]}")
        self._created.append(self._cf_name(doctype, fieldname))

    def has_custom_field(self, doctype: str, fieldname: str) -> bool:
        code, _ = self._call(f"/api/resource/Custom Field/{self._cf_name(doctype, fieldname)}")
        return code == 200

    def _delete_custom_field(self, name: str) -> None:
        self._call(f"/api/resource/Custom Field/{name}", method="DELETE")

    def cleanup(self) -> None:
        """探针字段一律删掉 —— 门禁不该在站点上留垃圾，否则下一轮的现状就不干净了。"""
        for name in reversed(self._created):
            self._delete_custom_field(name)
        self._created.clear()


@pytest.fixture
def live_site(compose_stack):
    _require_live("live_site")
    # 站点得先答得上 ping，否则后面的失败会指向错误的地方
    ping = compose_stack.http_get("/api/method/ping")
    if ping.status_code != 200:
        pytest.fail(f"站点未就绪：GET /api/method/ping → HTTP {ping.status_code}")
    site = LiveSite()
    yield site
    site.cleanup()


# --------------------------------------------------------------------------
# pack_repo —— git 管理的定制包工作副本
# --------------------------------------------------------------------------
class PackRepo:
    """磁盘布局与 `agenerp.snapshot.read_scope_dir` 同源：`<root>/doctypes/<DocType>.json`。

    这里刻意**不复用** agenerp 的读写函数：fixture 是判据的一部分，若它和被测实现
    共用同一份解析代码，实现里的口径错误会在两边同时发生、互相抵消而测不出来。
    """

    SCOPE = "doctypes"
    ENTRIES_KEY = "custom_fields"
    IDENTITY_KEY = "fieldname"

    def __init__(self, root: Path) -> None:
        self.path = str(root)
        self._root = root
        (root / self.SCOPE).mkdir(parents=True, exist_ok=True)
        self._git("init", "-q")
        self._git("config", "user.email", "gate@agenerp.invalid")
        self._git("config", "user.name", "gate")

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", self.path, *args], capture_output=True, text=True)

    def _doctype_file(self, doctype: str) -> Path:
        return self._root / self.SCOPE / f"{doctype}.json"

    def _load(self, doctype: str) -> dict:
        f = self._doctype_file(doctype)
        return json.loads(f.read_text()) if f.is_file() else {"doctype": doctype, self.ENTRIES_KEY: []}

    def contains_field(self, doctype: str, fieldname: str) -> bool:
        rows = self._load(doctype).get(self.ENTRIES_KEY, [])
        return any(isinstance(r, dict) and r.get(self.IDENTITY_KEY) == fieldname for r in rows)

    def remove_field(self, doctype: str, fieldname: str) -> None:
        payload = self._load(doctype)
        rows = [r for r in payload.get(self.ENTRIES_KEY, [])
                if not (isinstance(r, dict) and r.get(self.IDENTITY_KEY) == fieldname)]
        payload[self.ENTRIES_KEY] = rows
        self._doctype_file(doctype).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def commit(self, message: str) -> None:
        self._git("add", "-A")
        r = self._git("commit", "-m", message, "--allow-empty")
        if r.returncode != 0:
            pytest.fail(f"定制包提交失败：{r.stderr[:300]}")

    def changed_lines(self) -> list[str]:
        """自上次提交以来变动的**内容行**（去掉 diff 头与 +++/--- 元行）。"""
        r = self._git("diff", "HEAD", "--unified=0")
        if r.returncode != 0:
            r = self._git("diff", "--unified=0")
        out = []
        for line in r.stdout.splitlines():
            if line.startswith(("+++", "---", "@@", "diff ", "index ", "new file", "deleted file")):
                continue
            if line.startswith(("+", "-")):
                out.append(line[1:].strip())
        return [line for line in out if line]


@pytest.fixture
def pack_repo(tmp_path):
    _require_live("pack_repo")
    yield PackRepo(tmp_path / "pack")
