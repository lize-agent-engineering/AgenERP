"""`python3 -m agenerp.serve` —— 起进程。落点节 `docs/architecture/module-boundaries.md` §7.20。

**一个 AI 变量都不配也起得来**（`docker-compose.yml` 文件头规则 ②：外部能力缺失是
「未配置」状态，不是错误状态）。模型配置是**惰性**取的，失败只发生在真去调模型的那一刻，
而那时回的是 503 并指名缺哪个变量 —— 不是启动失败，也不是 200 空回答。
"""

from __future__ import annotations

import ipaddress
import os
import sys

from agenerp.serve.app import DEFAULT_PORT, LOOPBACK, PORT_ENV, build_server
from agenerp.site import SITE_ENV

# 监听**地址**这一格。§7.20 `D-a-1` 的残余风险逐字写着「它一旦要对本机之外提供，
# 这一条就必须重开」—— nginx 在**另一个容器**里，绑回环它就到不了 ⇒ 条件成立。
# 重开的裁定在 `docs/architecture/module-boundaries.md` §7.21 `D-b-4`。
#
# ⚠️ **重开的是「能不能配」，不是「默认是什么」。** 默认值仍是 `app.py` 的 `LOOPBACK`：
# 直接把那个常量改成 `0.0.0.0` 会让**宿主上手工起的那次跑**也默认对外 ——
# 一次静默的暴露面扩大，diff 里只有一行、看不出后果。
HOST_ENV = "AGENERP_SERVE_HOST"


def resolve_port(env: dict[str, str] | None = None) -> int:
    """监听端口。**默认值必须存在** —— 不配也能起（§7.20 `D-a-5`）。

    配了但不是合法端口就**当场失败并指名变量**，不悄悄退回默认值：
    悄悄退回之后，「我配了 9000」与「我配错了所以在 8330」在运行时看不出区别。

    **`0` 是合法值**，含义是「由内核分配一个空闲端口」—— 判据用它起真进程、真 socket，
    不必猜一个「大概没人用」的数。
    """
    source = os.environ if env is None else env
    raw = (source.get(PORT_ENV) or "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"{PORT_ENV}={raw!r} 不是整数") from None
    if not 0 <= port <= 65535:
        raise ValueError(f"{PORT_ENV}={port} 不在 0..65535 之内")
    return port


def resolve_host(env: dict[str, str] | None = None) -> str:
    """监听地址。**默认值仍是回环** —— 不配时的行为与开这一格之前逐字相同。

    纪律与 `resolve_port()` 完全一致：配了但不是合法监听地址就**当场失败并指名变量**，
    不悄悄退回默认值。悄悄退回之后，「我配了 0.0.0.0」与「我配错了所以还在 127.0.0.1」
    在运行时看不出区别 —— 而这两者的暴露面差一整个网段。

    **只收 IP 字面量**（v4/v6 皆可），主机名一律拒。监听地址是**地址**不是名字：
    一个名字能解析出多条记录，「绑到哪张网卡上」就成了不确定的。
    拒绝的代价只是 `localhost` 要写成 `127.0.0.1`。
    """
    source = os.environ if env is None else env
    raw = (source.get(HOST_ENV) or "").strip()
    if not raw:
        return LOOPBACK
    try:
        ipaddress.ip_address(raw)
    except ValueError:
        raise ValueError(
            f"{HOST_ENV}={raw!r} 不是 IP 字面量（只收 IPv4/IPv6 地址，主机名不收）"
        ) from None
    return raw


def main(argv: list[str] | None = None) -> int:
    site = (os.environ.get(SITE_ENV) or "").strip()
    if not site:
        print(f"站点名为空：设置 {SITE_ENV}", file=sys.stderr)
        return 2
    try:
        port = resolve_port()
        host_addr = resolve_host()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    server = build_server(site=site, host=host_addr, port=port)
    host, bound = server.server_address[:2]
    print(f"agenerp explain service listening on http://{host}:{bound}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
