"""`python3 -m agenerp.serve` —— 起进程。落点节 `docs/architecture/module-boundaries.md` §7.20。

**一个 AI 变量都不配也起得来**（`docker-compose.yml` 文件头规则 ②：外部能力缺失是
「未配置」状态，不是错误状态）。模型配置是**惰性**取的，失败只发生在真去调模型的那一刻，
而那时回的是 503 并指名缺哪个变量 —— 不是启动失败，也不是 200 空回答。
"""

from __future__ import annotations

import os
import sys

from agenerp.serve.app import DEFAULT_PORT, LOOPBACK, PORT_ENV, build_server
from agenerp.site import SITE_ENV


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


def main(argv: list[str] | None = None) -> int:
    site = (os.environ.get(SITE_ENV) or "").strip()
    if not site:
        print(f"站点名为空：设置 {SITE_ENV}", file=sys.stderr)
        return 2
    try:
        port = resolve_port()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    server = build_server(site=site, host=LOOPBACK, port=port)
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
