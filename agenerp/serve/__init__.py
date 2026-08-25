"""解释服务的 HTTP 面。落点节 `docs/architecture/module-boundaries.md` §7.20。"""

from agenerp.serve.app import (
    DEFAULT_PORT,
    EXPLAIN_PATH,
    HEALTH_PATH,
    LOOPBACK,
    PORT_ENV,
    ROUTE_PREFIX,
    ServiceDeps,
    ServiceError,
    build_server,
    handle_explain,
)

__all__ = [
    "DEFAULT_PORT",
    "EXPLAIN_PATH",
    "HEALTH_PATH",
    "LOOPBACK",
    "PORT_ENV",
    "ROUTE_PREFIX",
    "ServiceDeps",
    "ServiceError",
    "build_server",
    "handle_explain",
]
