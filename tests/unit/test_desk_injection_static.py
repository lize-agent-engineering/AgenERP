"""Desk 注入段的**离线**判据（§7.22 `D-c-1`）—— 不起活栈就能判的那一半。

**口径（沿用 §14.11）：从两个文件各读一次再比，判据里不写第三个字面量。**
写了第三个之后，这份判据就只是在验证一个字符串等于它自己，而两个真正要对齐的文件
可以一起漂走 —— 那正是「绿着坏掉」。

守八件事：
① 注入的 URL 前缀 == `agenerp/serve/app.py` 的 `ROUTE_PREFIX`
② 注入的文件名 == `ASSET_FILENAME`
③ 注入段坐在那**一对**哨兵之间（在外面 ⇒ 红）
④ 注入段**不许整段被注释掉**（只 grep 字符串会把注释里的 URL 也数进去）
⑤ 自起的 `location ^~ /app` 的头集合 ⊇ 上游 `@webserver` 的头集合（`D-c-1` 代价 1 的孪生漂移）
⑥ `sub_filter` 的锚点与替换串**自洽**（换完之后锚点仍在，且只多出一个 `<script>`）
⑦ `sub_filter_once on`（`H7` 的「恰好 1 次」）
⑧ 模板里 `/agenerp/` 上游端口 == compose 的 `AGENERP_SERVE_PORT`
"""

from __future__ import annotations

import pathlib
import re

from agenerp.serve.app import ASSET_FILENAME, ROUTE_PREFIX

REPO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "tools" / "nginx" / "frappe.conf.template"
COMPOSE = REPO / "docker-compose.yml"

_OPEN = "# >>> AgenERP"
_CLOSE = "# <<< AgenERP"


def _template_text() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _sentinel_body() -> str:
    """那一对哨兵之间的内容（**含注释行**，④ 要靠注释行在不在来判）。"""
    text = _template_text()
    assert text.count(_OPEN) == 1, f"`{_OPEN}` 应当只有一处，实际 {text.count(_OPEN)}"
    assert text.count(_CLOSE) == 1, f"`{_CLOSE}` 应当只有一处，实际 {text.count(_CLOSE)}"
    start = text.index(_OPEN)
    end = text.index(_CLOSE)
    assert start < end, "哨兵顺序反了：`>>>` 应当在 `<<<` 之前"
    return text[start:end]


def _effective_lines(block: str) -> list[str]:
    """剔掉注释行与空行之后的**生效行**。

    ⚠️ 这一步是 ④ 的全部要害：只 grep 字符串会把注释里的 URL 也数进去 ⇒
    把整段注入注释掉、URL 留在注释里，判据照样全绿而注入根本不发生。
    """
    out = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _injected_script_tags(lines: list[str]) -> list[str]:
    """从**生效行**里取出 `sub_filter` 替换串中的 `<script src="...">`。"""
    found = []
    for line in lines:
        if not line.startswith("sub_filter "):
            continue
        found.extend(re.findall(r'<script src="([^"]+)"></script>', line))
    return found


# --- ①② 注入的 URL == 服务发出的 URL（两个文件各读一次） -----------------------------


def test_injected_url_prefix_equals_route_prefix():
    """① 注入的 URL 前缀与 `ROUTE_PREFIX` 逐字一致。

    失败意味着：页面去取 `/xxx/desk.js` 而服务在 `/agenerp/desk.js` 上应答 ⇒
    浏览器拿 404，**而 `nginx -t` 全绿、页面照常渲染**。绿着坏掉。
    """
    srcs = _injected_script_tags(_effective_lines(_sentinel_body()))
    assert len(srcs) == 1, f"生效行里应当恰好有一个注入的 <script src>，实际：{srcs}"
    src = srcs[0]
    assert src.startswith(ROUTE_PREFIX + "/"), (
        f"注入的 URL 是 {src!r}，而 app.py 的 ROUTE_PREFIX 是 {ROUTE_PREFIX!r}"
    )


def test_injected_filename_equals_asset_route_constant():
    """② 注入的文件名与 `ASSET_FILENAME` 逐字一致。

    失败意味着：改了服务侧的文件名而模板没跟（或反之）—— 同样是 404 + 全绿。
    """
    src = _injected_script_tags(_effective_lines(_sentinel_body()))[0]
    assert src == f"{ROUTE_PREFIX}/{ASSET_FILENAME}", (
        f"注入的是 {src!r}，而服务发的是 {ROUTE_PREFIX}/{ASSET_FILENAME!r}"
    )


# --- ③④ 注入段在哨兵之内，且不是一段被注释掉的死文本 -------------------------------


def test_injection_lives_between_the_agenerp_sentinels():
    """③ 注入段坐在那**一对**哨兵之间。

    ⚠️ 哨兵不是装饰：`docker run --rm --entrypoint cat <上游镜像> /templates/nginx/frappe.conf.template
    | diff - tools/nginx/frappe.conf.template` 那条复核靠它把「本仓加的」与「上游的」分开。
    注入段跑到哨兵外面 ⇒ 差集里出现一段无主的内容，K3（差集只许是本仓那两段）当场不成立。

    失败意味着：本仓改动混进了上游那部分，回滚与升级时分不出谁是谁。
    """
    text = _template_text()
    body = _sentinel_body()
    marker = 'sub_filter '
    assert marker in body, "哨兵之间没有 sub_filter —— 注入段不在哨兵内"
    assert text.count(marker) == body.count(marker), (
        "哨兵之外也出现了 sub_filter —— 注入段有一部分跑到上游那段里去了"
    )
    assert "location ^~ /app" in body, "自起的 `location ^~ /app` 不在哨兵之间"
    assert text.count("location ^~ /app") == 1


def test_injection_is_on_effective_lines_not_commented_out():
    """④ 注入段**不许整段被注释掉**。

    ⚠️ **这是这份静态判据最容易被绕的一格**：把 `sub_filter` 那几行前面加个 `#`、
    URL 原样留在注释里 —— 只 grep 字符串的判据会**全绿**，而注入根本不发生。
    所以这里先剔注释行，再在**生效行**上判。

    失败意味着：配置看起来有、实际不生效。
    """
    lines = _effective_lines(_sentinel_body())
    assert any(line.startswith("sub_filter ") for line in lines), (
        "生效行里没有 sub_filter —— 注入段被整段注释掉了（或被删了）"
    )
    assert _injected_script_tags(lines), "生效行里没有注入的 <script src>"


# --- ⑤ 上游孪生：自起的 location 必须带齐 @webserver 的头 ---------------------------


def _block_body(text: str, header: str) -> str:
    """取 `header` 那个块的 `{...}` 正文（按花括号配平，不用正则数括号）。"""
    start = text.index(header)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"`{header}` 的块没有配平的花括号")


def _proxy_directives(block: str) -> set[str]:
    """块里 `proxy_set_header <名字>` 与 `proxy_read_timeout` 一类的**指令名集合**。"""
    names = set()
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("proxy_set_header "):
            names.add("proxy_set_header " + line.split()[1])
        elif line.startswith("proxy_"):
            names.add(line.split()[0])
    return names


def test_self_started_app_location_carries_the_webserver_header_set():
    """⑤ 自起的 `location ^~ /app` 的头集合 **⊇** 上游 `location @webserver` 的头集合。

    ⚠️ **为什么必须自带、不能 `try_files ... @webserver`**（`D-c-1` 代价 1，结构性原因）：
    nginx 的体过滤器与 `proxy_set_header` 都按**最终处理请求的那个 location** 取配置。
    写成 `try_files` 会让请求内部跳进 `@webserver`，**本块的 `sub_filter` 随之静默失效** ——
    配置全绿、注入物不见。

    ⇒ 哨兵段里从此养着一份**需随镜像 tag 升级同步的上游孪生**。这条判据守的就是它：
    上游 `@webserver` 加了一个头而本块没跟 ⇒ Desk **静默走偏**（不是报错，是行为不同）。

    失败意味着：孪生漂移了。处置是把上游新增的那一项抄进本块，**不是放宽这条判据**。
    """
    text = _template_text()
    upstream = _proxy_directives(_block_body(text, "location @webserver {"))
    ours = _proxy_directives(_block_body(text, "location ^~ /app {"))
    missing = upstream - ours
    assert not missing, (
        f"自起的 `location ^~ /app` 缺了上游 `@webserver` 的这些项：{sorted(missing)} —— "
        f"缺一项 Desk 就静默走偏。把它抄进本块，不要改这条判据。"
    )


# --- ⑥⑦ sub_filter 自洽，且只换一次 -------------------------------------------------


def test_sub_filter_anchor_survives_its_own_replacement():
    """⑥ 替换串里**必须仍含锚点本身**，否则同一份响应上第二次匹配就无从谈起，
    更要紧的是：锚点 `</body>` 被吃掉的页面**结构就坏了**。

    失败意味着：注入把 HTML 的结束标签换没了。
    """
    lines = _effective_lines(_sentinel_body())
    subs = [line for line in lines if line.startswith("sub_filter ")]
    directive = next(line for line in subs if line.startswith("sub_filter '"))
    parts = re.findall(r"'([^']*)'", directive)
    assert len(parts) == 2, f"sub_filter 应当是「锚点 + 替换串」两个引号串，实际：{parts}"
    anchor, replacement = parts
    assert anchor in replacement, (
        f"替换串 {replacement!r} 里没有锚点 {anchor!r} —— 注入会把它吃掉"
    )
    assert replacement.count(anchor) == 1, "替换串里锚点出现了不止一次"


def test_sub_filter_once_is_on():
    """⑦ `sub_filter_once on;` —— `H7` 那格「注入标记恰好 1 次」的配置侧保证。

    ⚠️ 单靠「`</body>` 在体内只出现一次」不够：那是**今天这份页面**的性质，
    上游哪天多渲染一个 `</body>`（或注入面扩到别的页面）就会变成两次，
    而两次注入 = 脚本执行两次 = `desk.js` 里那个 `defineProperty` 走进 catch 分支。

    失败意味着：`sub_filter_once off;` 或这一行被删。
    """
    lines = _effective_lines(_sentinel_body())
    assert "sub_filter_once on;" in lines, (
        f"生效行里没有 `sub_filter_once on;`，实际的 sub_filter 相关行："
        f"{[line for line in lines if line.startswith('sub_filter')]}"
    )


# --- ⑧ 上游端口与 compose 一致（沿用 §14.11 口径） -----------------------------------


def test_template_upstream_port_equals_compose_serve_port():
    """⑧ 模板里 `/agenerp/` 的上游端口 == compose 里 `AGENERP_SERVE_PORT`。

    ⚠️ **这条与 `test_explain_same_origin.py` 的判据③ 同源但不重复** —— 那条守的是
    「本仓加的那一跳」在 P1.8a 落成时的形态；本文件在同一段哨兵里又加了东西，
    这一格保证新加的内容没有把它挤歪（例如把 `location /agenerp/` 挪走）。

    失败意味着：反代打到一个没人监听的端口 ⇒ 页面取 `desk.js` 拿 502。
    """
    body = _block_body(_template_text(), f"location {ROUTE_PREFIX}/ {{")
    ports = re.findall(r"proxy_pass\s+http://\$\w+:(\d+)\s*;", body)
    assert len(ports) == 1, f"`location {ROUTE_PREFIX}/` 里应当恰好一条变量形式的 proxy_pass，实际：{ports}"

    compose = COMPOSE.read_text(encoding="utf-8")
    declared = re.findall(r'AGENERP_SERVE_PORT:\s*"(\d+)"', compose)
    assert len(declared) == 1, f"compose 里 AGENERP_SERVE_PORT 应当只有一处字面声明，实际：{declared}"
    assert ports[0] == declared[0], (
        f"模板里上游端口是 {ports[0]}，compose 里是 {declared[0]}"
    )
