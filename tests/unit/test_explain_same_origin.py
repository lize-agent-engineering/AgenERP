"""非门禁测试 · 解释服务**接线那一半**的离线判据（P1.8a 第 2 个 plan）。

落点节 `docs/architecture/module-boundaries.md` **§7.21**。
进程与请求面本身的判据在 `tests/unit/test_explain_service.py`（§7.20），本文件一条不重做。

**这九条各挡一种假实现**，不是九种写法的同一件事：

| # | 挡的是 | 变异 |
|---|---|---|
| ① | 「顺手把服务端口发布到宿主」—— 它是 `D-b-4` 那条「绑 0.0.0.0 ≠ 对外提供」论证的**唯一支点** | M3 |
| ② | nginx 的 `location` 前缀与 `ROUTE_PREFIX` 分叉 | M1 |
| ③ | nginx 上游端口与 compose 侧分叉，或被写成插值形式（仓根 `.env` 能在 `config` 时改掉它） | M2 |
| ④ | 「默认就对外」 | M4 |
| ⑤ | 非法监听地址被**静默回退**成回环 | M5 |
| ⑥ | 让「AI 未配置」把新服务判成不健康 | M6 |
| ⑦ | 断言体的默认基址指着一个 CI 上不存在的端口 | M7 |
| ⑧ | **「配置测试全绿、反代根本不存在」** —— 一段坐在第二个 server 块里的 `location /agenerp/` 能同时满足②③ | M9 |
| ⑨ | **假服务** —— 一段只会对 `/agenerp/health` 回 `200 {"service":"agenerp-explain"}` 的应答脚本能让①–⑦ 全绿 | M10 |

判据全部是对**原始文本**的扫描（口径与理由抄 `test_compose_zero_dep.py` 文件头：
仓根有 gitignored 的 `.env`，`docker compose config` 会读它做插值，
于是「解析后的结果」在不同机器上不是同一个东西；原始文本是）。
只用标准库 —— 判定面一旦依赖某个包，换台机器就会红在环境而不是红在实现上。
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from agenerp.serve.__main__ import HOST_ENV, resolve_host
from agenerp.serve.app import LOOPBACK, ROUTE_PREFIX
from agenerp.site import HTTP_PORT_ENV, SITE_ENV, SITE_URL_ENV, default_base_url

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"
NGINX_TEMPLATE_PATH = REPO_ROOT / "tools" / "nginx" / "frappe.conf.template"
BODY_PATH = REPO_ROOT / "tests" / "unit" / "test_explain_service_body.py"

# 被判的那个服务。**只有这一个字面量**：其余每个值都从两个文件各读一次再比，
# 不在判据里写第三个字面量（那样判据就只是在验证一个字符串等于它自己）。
SERVICE = "agenerp-serve"

SERVE_BASE_ENV = "AGENERP_SERVE_BASE"
AI_VAR_PREFIX = "AGENERP_LLM_"


# --- 取原始文本的小工具（不解析 YAML / 不跑 nginx） ---------------------------------


def _compose_text() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


def _nginx_text() -> str:
    return NGINX_TEMPLATE_PATH.read_text(encoding="utf-8")


def _service_block(name: str) -> str:
    """取 `services:` 下某个服务的整块（含其下所有更深缩进的行）。

    与 `test_compose_zero_dep.py::_service_block` 同一形状、同一理由（见那里的 docstring）。
    """
    out: list[str] = []
    header = f"  {name}:"
    inside = False
    for line in _compose_text().splitlines():
        if line.rstrip() == header:
            inside = True
            continue
        if inside:
            if line.strip() and not line.startswith("    "):
                break
            out.append(line)
    return "\n".join(out)


def _sub_block(block: str, key: str) -> str:
    """从服务块里取某个子键（如 `healthcheck:`）的正文。"""
    out: list[str] = []
    inside = False
    indent = 0
    for line in block.splitlines():
        if not inside:
            if line.strip() == f"{key}:":
                inside = True
                indent = len(line) - len(line.lstrip())
            continue
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        out.append(line)
    return "\n".join(out)


def _env_value(block: str, key: str) -> str:
    """从服务块的 `environment:` 里取一个键的**原始文本值**（不解引号、不插值）。"""
    env = _sub_block(block, "environment")
    for line in env.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped[len(key) + 1 :].strip().strip('"').strip("'")
    raise AssertionError(f"{SERVICE} 的 environment 里没有 {key}")


# --- nginx 配置文本的**块结构**解析（判据⑧ 的对象） --------------------------------


def _strip_nginx_comments(text: str) -> str:
    """按行剔除 `#` 之后的内容。

    刻意不做完整词法分析：本文件扫的是**本仓维护的那一份模板**，全文没有含 `#` 的字符串字面量
    （已核对）。做成完整词法器会引入一个比被判对象更复杂的东西，而它自己没有判据。
    """
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _parse_blocks(text: str, pos: int = 0) -> tuple[list[dict], int]:
    """把 nginx 配置切成块树。每个节点：`directive`（`{` 之前那截）· `span` · `children`。

    只认三个字符：`{` 开块、`}` 闭块、`;` 断指令。够用且没有隐藏状态。
    """
    nodes: list[dict] = []
    buf_start = pos
    i = pos
    while i < len(text):
        char = text[i]
        if char == "{":
            directive = " ".join(text[buf_start:i].split())
            children, end = _parse_blocks(text, i + 1)
            nodes.append({"directive": directive, "span": (i, end), "children": children})
            i = end + 1
            buf_start = i
        elif char == "}":
            return nodes, i
        elif char == ";":
            i += 1
            buf_start = i
        else:
            i += 1
    return nodes, i


def _nginx_tree() -> list[dict]:
    return _parse_blocks(_strip_nginx_comments(_nginx_text()))[0]


def _load_body_module():
    """按路径加载断言体（判据⑦ 要的是它**算出来的值**，不是它的源码文本）。

    模块名刻意与门禁那份加载器用的不同 —— `tests/` 没有 `__init__.py`，
    重名会让整轮 pytest `import file mismatch` 收集失败。
    """
    name = "_p1_8a_body_under_same_origin_proofs"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BODY_PATH)
    assert spec and spec.loader, f"加载不了断言体：{BODY_PATH}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module          # 先塞进 sys.modules 再 exec，理由见 explain_fakes
    spec.loader.exec_module(module)
    return module


# --- 判据① 新服务不发布任何宿主端口 -------------------------------------------------


def test_serve_publishes_no_host_port():
    """① `agenerp-serve` 块里**没有 `ports:`**。

    这一条不是洁癖：§7.21 `D-b-4` 论证「容器内绑 `0.0.0.0` ≠ 对本机之外提供」时，
    **唯一的支点**就是「compose 不发布这个端口」。没有这条判据，那句论证就是一句没人守的话。

    失败意味着：解释服务对宿主可达了。它没有 TLS、没有限流、没有请求超时
    （§7.20 `D-a-1` 的残余风险原样继承），而对外那格端口本该只有 `frontend` 一条。
    """
    block = _service_block(SERVICE)
    assert block, f"compose 里没有 {SERVICE} 服务"
    assert not re.search(r"^\s{4}ports:\s*$", block, re.M), (
        f"{SERVICE} 出现了 ports: 块 —— 服务端口被发布到宿主了。\n"
        f"§7.21 `D-b-4` 那条「绑 0.0.0.0 不等于对外提供」的论证靠的就是这里没有它。"
    )


# --- 判据② nginx 前缀 ↔ ROUTE_PREFIX 逐字一致 ---------------------------------------


def _agenerp_location_directives() -> list[str]:
    found: list[str] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            if node["directive"].startswith("location ") and ROUTE_PREFIX in node["directive"]:
                found.append(node["directive"])
            walk(node["children"])

    walk(_nginx_tree())
    return found


def test_nginx_location_prefix_equals_route_prefix():
    """② nginx 那段 `location` 的前缀与 `agenerp/serve/app.py` 的 `ROUTE_PREFIX` 逐字一致。

    **两个文件各读一次再比**，判据里不写第三个字面量 —— 写了之后这条判据就只是在
    验证一个字符串等于它自己，而两个真正要对齐的文件可以一起漂走。

    尾部那个 `/` 是 nginx 前缀 location 的写法（`location /agenerp/` 不会匹配到
    `/agenerpfoo`），不是第二个字面量：判据用 `ROUTE_PREFIX + "/"` 算出来，不抄。

    失败意味着：服务在 `/agenerp/*` 上应答，而 nginx 反代的是别的前缀 ——
    经同源打过去一律 404，且 `nginx -t` 全绿。
    """
    directives = _agenerp_location_directives()
    assert len(directives) == 1, f"含 {ROUTE_PREFIX} 的 location 应当有且只有一段，实际：{directives}"
    prefix = directives[0].split(None, 1)[1].strip()
    assert prefix == ROUTE_PREFIX + "/", (
        f"nginx 侧前缀是 {prefix!r}，而 app.py 的 ROUTE_PREFIX 是 {ROUTE_PREFIX!r}"
    )


# --- 判据③ nginx 上游端口 ↔ compose 侧端口，且两边都不是插值形式 ---------------------

# 运行期解析的形状（§7.21 `D-b-8`）：主机名放变量、端口跟在 `proxy_pass` 后面。
_SET_HOST = re.compile(r"^\s*set\s+\$(?P<var>\w+)\s+(?P<host>[^\s;]+)\s*;", re.M)
_PROXY_PASS = re.compile(r"^\s*proxy_pass\s+http://\$(?P<var>\w+):(?P<port>[^\s/;]+)\s*;", re.M)


def _agenerp_location_body() -> str:
    """取那段 `location /agenerp/` 的块正文（已剔注释）。"""
    text = _strip_nginx_comments(_nginx_text())

    def walk(nodes):
        for node in nodes:
            if node["directive"] == f"location {ROUTE_PREFIX}/":
                start, end = node["span"]
                return text[start:end]
            found = walk(node["children"])
            if found is not None:
                return found
        return None

    body = walk(_nginx_tree())
    assert body is not None, f"nginx 模板里没有 `location {ROUTE_PREFIX}/` 块"
    return body


def _agenerp_upstream() -> tuple[str, str]:
    """从 nginx 模板里取解释服务上游的 `host` 与 `port`（原始文本）。

    **形状是「`set $var <host>;` + `proxy_pass http://$var:<port>;`」，不是 `upstream` 块** ——
    理由见 §7.21 `D-b-8`：`upstream` 块里的名字由 nginx 在**加载配置那一刻**解析，
    解析不出来就 `[emerg]` 退出，而 `frontend` 是 `restart: on-failure` ⇒ 整个前端陷入重启循环。
    """
    server_body = _strip_nginx_comments(_nginx_text())
    passes = _PROXY_PASS.findall(_agenerp_location_body())
    assert len(passes) == 1, f"`location {ROUTE_PREFIX}/` 里应当有且只有一条变量形式的 proxy_pass，实际：{passes}"
    var, port = passes[0]
    hosts = [h for v, h in _SET_HOST.findall(server_body) if v == var]
    assert len(hosts) == 1, f"`set ${var} <host>;` 应当有且只有一条，实际：{hosts}"
    return hosts[0], port


def test_nginx_upstream_port_equals_compose_serve_port():
    """③ nginx 上游端口与 compose 侧 `AGENERP_SERVE_PORT` 逐字相等，**且两边都不是插值形式**。

    「不是插值形式」不是多余的一句：仓根有 gitignored 的 `.env`，
    `docker compose config` 会读它做插值，而本判据是**静态文本扫描**，管不到 `.env`。
    写成 `${AGENERP_SERVE_PORT:-8330}` 时它照样满足「两边相等」，
    但运行时那个端口可以被 `.env` 改掉，而 nginx 侧改不掉 —— 反代打到一个没人听的端口上。
    同一条理由已有两条先例（`test_published_ports_bind_loopback_literally` 的宿主 IP、
    `test_bootstrap_script_dir_is_mounted_literally` 的挂载目录），这是第三条。

    失败意味着：反代打到一个服务没在听的端口上，或那个端口被 `.env` 悄悄改掉。
    """
    _, nginx_port = _agenerp_upstream()
    compose_port = _env_value(_service_block(SERVICE), "AGENERP_SERVE_PORT")

    assert "${" not in compose_port, f"compose 侧端口写成了插值：{compose_port!r}，仓根 .env 能把它改掉"
    assert "${" not in nginx_port, f"nginx 侧端口写成了插值：{nginx_port!r}"
    assert nginx_port == compose_port, f"nginx 上游端口 {nginx_port!r} ≠ compose 侧 {compose_port!r}"


# --- 判据④⑤ 监听地址：默认是回环；配了才放宽；非法值当场失败 -------------------------


def test_listen_host_defaults_to_loopback():
    """④ 不给 `AGENERP_SERVE_HOST` 时，监听地址**默认仍是回环**。

    §7.20 `D-a-1` 重开的是「**能不能配**」，不是「**默认是什么**」。
    把 `LOOPBACK` 常量直接改成 `0.0.0.0` 会让宿主上手工起的那次跑也默认对外 ——
    一次静默的暴露面扩大，diff 里只有一行、看不出后果。

    失败意味着：任何一次 `python3 -m agenerp.serve`（包括开发者本机手工起的那次）默认对外。
    """
    assert LOOPBACK == "127.0.0.1"
    assert resolve_host({}) == LOOPBACK
    assert resolve_host({HOST_ENV: ""}) == LOOPBACK
    assert resolve_host({HOST_ENV: "   "}) == LOOPBACK


def test_listen_host_widens_only_when_explicitly_given():
    """⑤a 显式给了才放宽 —— 且给什么就绑什么，不做任何「善意的」改写。"""
    assert resolve_host({HOST_ENV: "0.0.0.0"}) == "0.0.0.0"
    assert resolve_host({HOST_ENV: " 0.0.0.0 "}) == "0.0.0.0"
    assert resolve_host({HOST_ENV: "::"}) == "::"
    assert resolve_host({HOST_ENV: "192.168.1.5"}) == "192.168.1.5"


@pytest.mark.parametrize("bad", ["not-an-address", "999.1.1.1", "frontend", "localhost", "0.0.0.0:8330"])
def test_listen_host_rejects_illegal_values_instead_of_falling_back(bad: str):
    """⑤b 非法值**当场失败并指名变量**，**不静默回退**成回环。

    口径逐字抄既有的 `resolve_port()`：悄悄退回默认值之后，
    「我配了 `0.0.0.0`」与「我配错了所以还在 `127.0.0.1`」在运行时看不出区别 ——
    而这两者的暴露面差一整个网段。

    `localhost` 也在拒绝之列，这是刻意的：监听地址是**地址**不是名字，
    一个名字能解析出多条记录，「绑到哪张网卡上」就成了不确定的。

    失败意味着：一个配错的监听地址被吞掉，服务起在一个没人预期的地址上。
    """
    with pytest.raises(ValueError) as excinfo:
        resolve_host({HOST_ENV: bad})
    message = str(excinfo.value)
    assert HOST_ENV in message, f"报错没指名是哪个变量：{message}"
    assert bad in message, f"报错没带上那个非法值：{message}"


# --- 判据⑥ 新服务的 healthcheck 里没有 AI 变量 --------------------------------------


def test_ai_vars_absent_from_the_serve_healthcheck():
    """⑥ `agenerp-serve` 的 `healthcheck:` 块内不出现任何 `AGENERP_LLM_*`，且探针打的是 `/health`。

    既有的 `test_compose_zero_dep.py::test_ai_vars_absent_from_healthchecks` 是**全局扫**；
    这一条**点名新服务**，并多判一格：探针打的必须是 `/agenerp/health` 而**不是** `/agenerp/explain`。
    后者认人、碰站点、可能碰 LLM ⇒ 拿它做探针等于让「AI 未配置」这个**正常状态**
    把服务判成不健康，正是 `docker-compose.yml` 文件头规则 ② 要挡的。

    失败意味着：没配 AI 的机器上 `docker compose up -d --wait` 会挂在这个服务上，
    `clone && up` 不再零依赖 —— 而 D-19 逐字写过「新服务必须也能在『一个 AI 变量都不配』时起得来」。
    """
    healthcheck = _sub_block(_service_block(SERVICE), "healthcheck")
    assert healthcheck, f"{SERVICE} 没有 healthcheck —— `up -d --wait` 判不出它起没起来"
    assert AI_VAR_PREFIX not in healthcheck, (
        f"AI 变量出现在 {SERVICE} 的 healthcheck 里，未配置会变成不健康：\n{healthcheck}"
    )
    assert f"{ROUTE_PREFIX}/health" in healthcheck, f"探针打的不是 {ROUTE_PREFIX}/health：\n{healthcheck}"
    assert f"{ROUTE_PREFIX}/explain" not in healthcheck, (
        f"探针打的是 {ROUTE_PREFIX}/explain —— 它认人、碰站点，"
        f"会把「AI 未配置」判成「服务坏了」：\n{healthcheck}"
    )


# --- 判据⑦ 断言体的默认基址与 default_base_url() 同源 --------------------------------


@pytest.mark.parametrize(
    "env",
    [
        {},
        {HTTP_PORT_ENV: "18080"},
        {HTTP_PORT_ENV: "9999"},
        {SITE_URL_ENV: "http://frontend:8080"},
        {SITE_URL_ENV: "http://127.0.0.1:8080", HTTP_PORT_ENV: "18080"},
    ],
)
def test_body_default_base_resolves_exactly_like_site_default_base_url(monkeypatch, env: dict):
    """⑦ 不给 `AGENERP_SERVE_BASE` 时，断言体算出的 host:port 与 `default_base_url()` **完全相同**。

    这是 §7.21 `D-b-5` 那处 `Fix` 的判据。原先断言体把 `http://127.0.0.1:18080` 写成**默认值**，
    而 `gates-l2-live` **不设** `AGENERP_HTTP_PORT`、也**不设** `AGENERP_SERVE_BASE`
    ⇒ 人一按路径加载，六条会红在「连不上 18080」，而不是红在实现 —— **红错了地方**。

    ⚠️ 这一条判的是「**去哪里判**」，不是「**判成什么**」：六条断言的判定逻辑一个字未改。

    失败意味着：判据指向的靶子和栈实际发布的地方不是同一个。
    """
    for key in (SERVE_BASE_ENV, SITE_URL_ENV, HTTP_PORT_ENV):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv(SITE_ENV, "frontend")

    host, port, _ = _load_body_module()._target()
    expected = urlsplit(default_base_url())

    assert (host, port) == (expected.hostname, expected.port), (
        f"环境 {env} 下断言体算出 {host}:{port}，而 default_base_url() 算出 "
        f"{expected.hostname}:{expected.port}"
    )


def test_body_serve_base_env_still_wins(monkeypatch):
    """⑦b 显式给 `AGENERP_SERVE_BASE` 时它仍然压过前两级 —— 本机栈发布在非默认口时要靠它。"""
    monkeypatch.setenv(SERVE_BASE_ENV, "http://127.0.0.1:18080")
    monkeypatch.setenv(SITE_URL_ENV, "http://127.0.0.1:8080")
    monkeypatch.setenv(SITE_ENV, "frontend")

    host, port, _ = _load_body_module()._target()

    assert (host, port) == ("127.0.0.1", 18080)


def test_body_carries_no_hardcoded_default_base():
    """⑦c 断言体里**不许再有**一个写死的默认基址常量。

    行为判据（⑦）在没人给环境变量时才生效；这一条挡的是「常量还在、只是暂时没被读到」
    那种半修 —— 它会在下一次有人「顺手用回它」时复活。
    """
    source = BODY_PATH.read_text(encoding="utf-8")
    assert "DEFAULT_SERVE_BASE" not in source, "断言体里又出现了写死的默认基址常量"


# --- 判据⑧ 那段 location 必须在**唯一那个** listen 8080 的 server 块之内 --------------


def test_agenerp_location_lives_inside_the_sole_listen_8080_server_block():
    """⑧ 那段 `location` 坐在唯一那个 `listen 8080` 的 server 块**之内**。

    ⚠️ **这一条挡的是本节点名过的那个失败形态：「配置测试全绿、反代根本不存在」。**
    判据②③ 是纯文本比对 —— 一段坐在**第二个** server 块里的 `location /agenerp/`
    两条都满足。而 nginx 对「同 `listen` 同 `server_name` 的第二个 server 块」
    执行期实测只 warn（逐字 `conflicting server name "frontend" on 0.0.0.0:8080, ignored`），
    `nginx -t` 退 **0**，第二个块被**静默丢弃** ⇒ 运行时 `/agenerp/health` 回 404。

    所以这条不比对文本，它**解析块结构**：整份配置必须只有一个 server 块，
    它必须 `listen 8080`，而那段 `location` 必须是它的直接子块。

    失败意味着：反代那一跳在配置里「看起来有」，实际不存在。
    """
    tree = _nginx_tree()
    servers = [node for node in tree if node["directive"] == "server"]
    assert len(servers) == 1, (
        f"这份模板应当只有一个 server 块，实际 {len(servers)} 个 —— "
        f"同 listen 同 server_name 的第二个块会被 nginx 静默丢弃（nginx -t 仍退 0）"
    )

    server = servers[0]
    start, end = server["span"]
    body = _strip_nginx_comments(_nginx_text())[start:end]
    assert re.search(r"^\s*listen\s+8080\s*;", body, re.M), (
        "唯一那个 server 块不是 listen 8080 —— 对外那格端口由 tests/gates/conftest.py "
        "按 TargetPort == 8080 观测，改不了（红线 1）"
    )

    children = [
        node["directive"]
        for node in server["children"]
        if node["directive"].startswith("location ")
    ]
    assert f"location {ROUTE_PREFIX}/" in children, (
        f"`location {ROUTE_PREFIX}/` 不是那个 server 块的直接子块，实际子块：{children}"
    )


# --- 判据⑨ 跑的必须是本仓那个服务，反代打的必须是它 ----------------------------------


def test_the_service_actually_runs_this_repos_explain_service():
    """⑨a `agenerp-serve` 的 `command:` 字面包含 `agenerp.serve`，且包按字面路径挂进去。

    ⚠️ **这一条挡的是「假服务」**：一段自造的、只会对 `/agenerp/health` 回
    `200 {"service":"agenerp-explain"}` 的应答脚本，能让判据①–⑦ 全绿、
    变异 M1–M8 全部按预测打红 —— 因为**没有任何一条判据读过新服务的 `command:`**。

    失败意味着：栈里跑的不是 `agenerp/serve/`，而门禁却以为它在判这个仓的实现。
    """
    block = _service_block(SERVICE)
    command = _sub_block(block, "command")
    assert "agenerp.serve" in command, f"{SERVICE} 的 command 里没有 agenerp.serve：\n{command}"

    mounts = [
        line.strip()[2:].strip()
        for line in _sub_block(block, "volumes").splitlines()
        if line.strip().startswith("- ") and ":/" in line
    ]
    host_side = [m.split(":", 1)[0] for m in mounts if m.startswith(".")]
    assert host_side == ["./agenerp"], (
        f"{SERVICE} 的宿主侧 bind mount 必须且只能是字面的 `./agenerp`，实际：{host_side}。"
        "写成变量或换成别的目录，跑起来的就不是本仓这份实现了（理由同 bootstrap 那条）。"
    )


def test_nginx_upstream_host_equals_the_compose_service_name():
    """⑨b nginx 上游主机名 == 该服务在 compose 里的**服务名**，且不是插值形式。

    与⑨a 是同一条防线的另一半：⑨a 保证「那个服务跑的是本仓的实现」，
    这一条保证「反代打的就是那个服务」。把上游指向 `backend:8000` 时⑨a 仍全绿。

    两个文件各读一次再比 —— compose 侧确认服务名存在，nginx 侧读上游主机名。
    """
    assert _service_block(SERVICE), f"compose 里没有名为 {SERVICE} 的服务"
    nginx_host, _ = _agenerp_upstream()

    assert "${" not in nginx_host, f"nginx 侧上游主机名写成了插值：{nginx_host!r}"
    assert nginx_host == SERVICE, (
        f"nginx 上游主机名是 {nginx_host!r}，而 compose 里那个服务叫 {SERVICE!r}"
    )


# --- 判据⑩ 反代那一跳不得让 nginx 的**启动**依赖上游在不在 --------------------------


def test_the_reverse_proxy_does_not_make_nginx_startup_depend_on_the_upstream():
    """⑩ `/agenerp/` 那一跳必须是**运行期解析**：`resolver` + 变量形式的 `proxy_pass`，
    且**不许**为解释服务声明 `upstream` 块。

    ⚠️ **这一条是从一个真实缺陷里长出来的，不是预防性洁癖**（§7.21 `D-b-8`）：
    nginx 在**加载配置那一刻**解析所有 `upstream` 块里的主机名，解析不出来就
    `[emerg] host not found in upstream` 并**退出、不重试**。而 `frontend` 是
    `restart: on-failure` ⇒ 只要 `agenerp-serve` 那一刻不在（重启中 / 还没起 / 被停掉），
    **整个 frontend 陷入重启循环，连 Frappe 本身都对外不可用**。
    实测复现逐字：
        docker compose stop agenerp-serve
        docker compose up -d --force-recreate --no-deps frontend
        → [emerg] host not found in upstream "agenerp-serve:8330"，frontend `restarting`

    这是**本仓加的那一跳把 frontend 的可用性绑在了一个它不需要的服务上** ——
    一个新服务不该有能力拖垮整个前端。

    失败意味着：那格脆弱性回来了。`docker compose up -d --wait` 会在三个 CI job 的
    **第一步**上红，而红因看起来是 nginx 的报错、与解释服务毫无关系。
    """
    text = _strip_nginx_comments(_nginx_text())

    upstream_blocks = [
        node["directive"]
        for node in _nginx_tree()
        if node["directive"].startswith("upstream ") and SERVICE in node["directive"]
    ]
    assert not upstream_blocks, (
        f"给 {SERVICE} 声明了 upstream 块：{upstream_blocks}。"
        "upstream 里的名字由 nginx 在加载配置那一刻解析，解析不出来整个 frontend 就起不来。"
    )

    body = _agenerp_location_body()
    assert not re.search(rf"proxy_pass\s+http://{re.escape(SERVICE)}", body), (
        f"proxy_pass 直接写了主机名 {SERVICE} —— 那同样是启动期解析"
    )
    assert _PROXY_PASS.search(body), (
        f"`location {ROUTE_PREFIX}/` 里没有变量形式的 proxy_pass（`proxy_pass http://$var:<port>;`）"
    )
    assert re.search(r"^\s*resolver\s+\S+", text, re.M), (
        "没有 `resolver` 指令 —— 变量形式的 proxy_pass 需要它才能在运行期解析"
    )


def test_the_compose_front_does_not_depend_on_the_explain_service():
    """⑩b `frontend` 的 `depends_on` 里**不许**出现 `agenerp-serve`。

    与⑩ 是同一条防线的另一半。加那条边**挡不住**⑩ 描述的失败形态
    （`depends_on` 只管 `up` 的次序，管不到 `restart: on-failure` 触发的重启），
    却把 `frontend` 的可用性绑在一个它其实不需要的服务上 —— 代价真、收益假。

    失败意味着：有人用「加一条 depends_on」当作⑩ 的修法。那不是修法。
    """
    depends = _sub_block(_service_block("frontend"), "depends_on")
    # 只看**指令行**，不看注释 —— 那一格现在正由一条注释占着，写明它为什么刻意是空的。
    directives = "\n".join(
        line for line in depends.splitlines() if not line.lstrip().startswith("#")
    )
    assert SERVICE not in directives, (
        f"frontend 的 depends_on 里出现了 {SERVICE}：\n{directives}\n"
        "挡不住那个失败形态，却把前端的可用性绑在解释服务上。真正的修法在 nginx 侧（判据⑩）。"
    )
