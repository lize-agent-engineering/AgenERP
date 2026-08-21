"""带外容器命令传输 —— `agenerp` 里**唯一够得到物理表**的地方。

结构边界见 `docs/architecture/module-boundaries.md` §11.8。四条约束写在最前面，
因为它们比实现细节重要：

1. **不伪装成功。** 命令起不来 / 非零退出 / 载荷不是 JSON —— 一律抛 `OobError`。
   降级成空列表会让「没有孤儿列」和「命令没跑起来」长得一模一样，门禁随之假绿。
   **唯一的例外是「退出码 0 且 stdout 全空」**，它在 `bench execute` 的协议里恰好等价于
   「被调函数返回了**假值**」——`apps/frappe/frappe/commands/utils.py:285` 逐字 `if ret:`，
   假值不打印任何东西（v15.119.3 容器内实读）。这个例外**不是降级**：它返回哨兵
   `FALSY_RESULT` 而不是任何一种「正常结果」，逼调用方按自己的返回类型把它翻译成
   `[]` / `{}` / `0`，翻译不了就自己抛。三种真故障都够不到这个分支——
   2026-08-22 冷起站点实测：函数不存在 → exit 1、函数内部抛错 → exit 1、站点不存在 → exit 1，
   全部先被 `_run` 拦掉（判据 `tests/unit/test_schema_drift.py`）。
2. **能执行什么被钉死到参数一级。** `ALLOWED_CALLS` 是**「函数名 → 钉死的 kwargs」映射**，
   不是名字集合。调用方只能给 `doctype`；`trim_table` 的 `dry_run` 恒为 `True`，
   给不了 `False`——只钉名字挡不住「把该 DocType 的孤儿列一次删光」。
3. **与红线 7 的界线。** 红线 7 禁的是把可执行脚本**装进站点**、由站点在处理请求时自己执行
   （持久化的 RCE 面）。本模块是运维侧的一次性带外调用：不留任何站点态，进程退出即结束。
   这条界线靠约束 2 兜住——一旦白名单退化成「能传任意函数或任意 SQL」，界线就没了。
4. **零第三方依赖。** 只用 `subprocess` + `json`，与 `agenerp/site.py` 同一条约束。

**三个 exec 目标**（这也是模块不叫 `bench.py` 的原因——它不只跑 bench）：

| 目标 | 命令 | 方向 |
|---|---|---|
| `backend` | `bench --site <site> execute <白名单函数>` | 读 |
| `backend` | `cat sites/<site>/site_config.json` | 读 |
| `db` | `mariadb … -e "ALTER TABLE … DROP COLUMN …"` | **写**（本模块唯一的写动作） |

`read_site_config` 是一条 `cat`，不执行任何 Python，因此**不进 `ALLOWED_CALLS`**；
它同时是 DDL 拿库名的**唯一**来源——`docker-compose.yml` 的 `db` 服务只设
`MYSQL_ROOT_PASSWORD`、不设 `MYSQL_DATABASE`，库名（形如 `_5e5899d8398b5f7b`）
从站点名推不出来，只能读。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

SITE_ENV = "AGENERP_SITE"
BACKEND_SERVICE_ENV = "AGENERP_OOB_BACKEND_SERVICE"
DB_SERVICE_ENV = "AGENERP_OOB_DB_SERVICE"
COMPOSE_FILE_ENV = "AGENERP_OOB_COMPOSE_FILE"

DEFAULT_BACKEND_SERVICE = "backend"
DEFAULT_DB_SERVICE = "db"
DEFAULT_COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
DEFAULT_TIMEOUT = 180

# 允许经 `bench execute` 调用的函数，**连 kwargs 一起钉死**（见模块头第 2 条）。
# v0 只有一条。加一条就要付一次 diff 和一次留痕，与 `agenerp/site.py` 的写方法白名单同一条纪律。
ALLOWED_CALLS: dict[str, dict[str, Any]] = {
    "frappe.model.meta.trim_table": {"dry_run": True},
}

# 进 DDL 的标识符白名单。**v0 的刻意收窄**：它会拒掉含 `-` / `&` 的合法 DocType 名，
# 本仓此刻只需覆盖 `Item`，拒掉即抛错而不是静默放行。
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_ ]+$")

TRIM_TABLE = "frappe.model.meta.trim_table"


class _FalsyResult:
    """`run_json` 的哨兵：被调函数**成功返回了一个假值**，因此 `bench execute` 什么都没打印。

    刻意**不是** `None` 也不是 `[]`：`json.loads("null")` 就是 `None`，用它兼表两件事会
    重新制造本模块要挡的那种歧义；而直接给 `[]` 等于替调用方猜「这个函数返回列表」——
    白名单以后多一条返回 dict 的函数，那个猜就会静默错掉。哨兵逼调用方显式翻译。
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "FALSY_RESULT"


FALSY_RESULT = _FalsyResult()


class OobError(RuntimeError):
    """带外命令的一切失败：命令起不来、非零退出、载荷不是 JSON、标识符不合法。

    与 `agenerp.site.SiteError` 平级，**绝不降级成空结果**（见模块头第 1 条）。
    """


@dataclass(frozen=True)
class OobCommand:
    """一次待发的带外命令。传输是可注入的接缝，所以命令必须是可检视的值对象。"""

    service: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class OobResult:
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    """把一次 `OobCommand` 送进容器。起不来必须抛 `OobError`，不得伪造退出码。"""

    def __call__(self, command: OobCommand) -> OobResult:
        ...


class ComposeExecRunner:
    """`docker compose exec -T <service> <argv…>`。产品路径上的唯一实现。

    `-T` 不分配 TTY —— 带 TTY 时 docker 会往 stdout 混进控制字符，JSON 解析随之失败。
    """

    def __init__(self, compose_file: Path | str | None = None, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._compose_file = Path(compose_file) if compose_file is not None else default_compose_file()
        self._timeout = timeout

    def __call__(self, command: OobCommand) -> OobResult:
        argv = [
            "docker", "compose", "-f", str(self._compose_file),
            "exec", "-T", command.service, *command.argv,
        ]
        try:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=self._timeout)
        except Exception as exc:  # docker 不在、compose 文件没了、超时 —— 都是命令没跑起来
            raise OobError(f"带外命令起不来（{' '.join(argv)}）：{exc}") from exc
        return OobResult(done.returncode, done.stdout, done.stderr)


def default_compose_file() -> Path:
    explicit = os.environ.get(COMPOSE_FILE_ENV, "").strip()
    return Path(explicit) if explicit else DEFAULT_COMPOSE_FILE


def backend_service() -> str:
    return os.environ.get(BACKEND_SERVICE_ENV, "").strip() or DEFAULT_BACKEND_SERVICE


def db_service() -> str:
    return os.environ.get(DB_SERVICE_ENV, "").strip() or DEFAULT_DB_SERVICE


def resolve_site(site: str | None = None) -> str:
    """站点名：显式实参优先，否则读 `AGENERP_SITE`。**没有默认值**——猜一个站点名去跑
    DDL 是本模块最不该有的行为。"""
    resolved = (site or os.environ.get(SITE_ENV, "")).strip()
    if not resolved:
        raise OobError(f"带外命令需要站点名：显式传 site，或设置 {SITE_ENV}")
    return resolved


def _resolve_runner(runner: Runner | None) -> Runner:
    return runner if runner is not None else ComposeExecRunner()


def _check_identifier(kind: str, value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.match(value):
        raise OobError(
            f"{kind} {value!r} 不在标识符白名单 {_IDENTIFIER.pattern} 内 —— "
            "拒绝把未经验证的标识符拼进命令（v0 的刻意收窄，见模块头）"
        )
    return value


def _run(runner: Runner, command: OobCommand) -> str:
    result = runner(command)
    if result.returncode != 0:
        raise OobError(
            f"带外命令失败（exit {result.returncode}，服务 {command.service}）："
            f"{' '.join(command.argv)[:200]} → {(result.stderr or result.stdout)[:400]}"
        )
    return result.stdout


def run_json(function: str, doctype: str, site: str | None = None, runner: Runner | None = None) -> Any:
    """在 `backend` 容器里调用一个**白名单内**的 Frappe 函数，返回它已解析的 JSON 结果。

    调用方能给的只有 `doctype`：其余 kwargs 由 `ALLOWED_CALLS[function]` 钉死并**最后合并**，
    所以 `dry_run` 这类开关传不进来（模块头第 2 条）。

    非零退出、stdout 不是 JSON —— 一律抛 `OobError`，不返回空。

    **退出码 0 且 stdout 全空**是唯一的例外，返回 `FALSY_RESULT`（模块头第 1 条）：
    `bench execute` 只在返回值为真时才打印，所以「没有孤儿列」这个**合法结论**在
    这条通道上就是零字节。以前它被当成「载荷不是 JSON」抛掉，于是
    `test_no_orphan_column_left_behind` 在**全新站点**上必然红——清干净了反而红
    （2026-08-22 冷起实测 3/3、CI runner 2/2）。
    """
    pinned = ALLOWED_CALLS.get(function)
    if pinned is None:
        raise OobError(
            f"函数 {function!r} 不在带外调用白名单内；已允许：{sorted(ALLOWED_CALLS)}"
        )
    kwargs = {"doctype": _check_identifier("DocType 名", doctype), **pinned}
    stdout = _run(
        _resolve_runner(runner),
        OobCommand(
            service=backend_service(),
            argv=(
                "bench", "--site", resolve_site(site), "execute", function,
                "--kwargs", _python_literal(kwargs),
            ),
        ),
    )
    if not stdout.strip():
        return FALSY_RESULT
    try:
        return json.loads(stdout)
    except ValueError as exc:
        raise OobError(f"{function} 的输出不是 JSON：{stdout[:300]!r}") from exc


def _python_literal(kwargs: dict[str, Any]) -> str:
    """`bench execute --kwargs` 的载荷是 **Python 字面量**，不是 JSON。

    2026-08-21 活站点实测：`frappe/commands/utils.py:258` 对它做 `eval(kwargs)`，
    喂 `json.dumps` 的结果会红在 `NameError: name 'true' is not defined`
    （JSON 的 `true` / `false` / `null` 在 Python 里不存在）。所以这里用 `repr`。
    值全部先过 `_check_identifier` 或来自 `ALLOWED_CALLS` 的字面量，
    `repr` 拼不出引号逃逸——**这条安全性依赖上面那次校验，不是 `repr` 自带的**。
    """
    return repr(kwargs)


def read_site_config(site: str | None = None, runner: Runner | None = None) -> dict[str, Any]:
    """读站点的 `site_config.json`。**DDL 拿库名的唯一来源**（见模块头）。

    一条 `cat`，不执行任何 Python，因此不进 `ALLOWED_CALLS`。
    """
    resolved = resolve_site(site)
    stdout = _run(
        _resolve_runner(runner),
        OobCommand(
            service=backend_service(),
            argv=("cat", f"sites/{_check_site_path(resolved)}/site_config.json"),
        ),
    )
    try:
        payload = json.loads(stdout)
    except ValueError as exc:
        raise OobError(f"站点 {resolved} 的 site_config.json 不是 JSON：{stdout[:300]!r}") from exc
    if not isinstance(payload, dict):
        raise OobError(f"站点 {resolved} 的 site_config.json 必须是对象，读到 {type(payload).__name__}")
    return payload


def drop_columns(
    doctype: str,
    columns: tuple[str, ...] | list[str],
    site: str | None = None,
    runner: Runner | None = None,
) -> None:
    """把 `columns` 从 `tab<doctype>` 上删掉。**本模块唯一的写动作**（见模块头的三个 exec 目标表）。

    走 `db` 容器直发 DDL，**不经任何 Python 执行面**——`ALTER TABLE … DROP COLUMN` 不是任何
    Frappe 白名单函数，为它开一个「调用方给整条 SQL」的入口等于把 `ALLOWED_CALLS` 作废。
    因此它**不共用 `ALLOWED_CALLS`**：那张表管的是 Python 函数调用，管不到 DDL（§11.8）。

    **本函数不做「这列该不该删」的判断**——判断在 `agenerp.apply`（列必须同时满足
    「Frappe 判它是孤儿」与「本次 apply 真删过同名字段」，§11.6）。这里只做三件事：
    空集合直接返回（**不发空 DDL**）、标识符白名单、发命令。

    库名来自 `read_site_config(site)["db_name"]`，**不写死也不猜**：`docker-compose.yml` 的
    `db` 服务不设 `MYSQL_DATABASE`，`mariadb` 没有默认库，库名从站点名也推不出来。

    口令不进 argv：`sh -c` 里引用容器自己的 `$MYSQL_ROOT_PASSWORD`。
    ⚠️ SQL 用**单引号**包住（不是双引号）：MariaDB 的标识符引号是反引号，
    落在双引号里会被 `sh` 当成命令替换执行掉——2026-08-21 实测红过一次
    （`sh: 1: tabItem: not found`）。标识符已过 `_IDENTIFIER`，不含单引号，故单引号安全。
    判据 `test_ddl_single_quotes_the_statement_so_backticks_are_not_command_substituted`。
    """
    wanted = tuple(columns)
    if not wanted:
        return
    table = f"tab{_check_identifier('DocType 名', doctype)}"
    drops = ", ".join(f"DROP COLUMN `{_check_identifier('列名', c)}`" for c in wanted)
    resolved_runner = _resolve_runner(runner)
    db_name = _check_identifier(
        "库名", str(read_site_config(site, runner=resolved_runner).get("db_name", ""))
    )
    statement = f"ALTER TABLE `{table}` {drops};"
    _run(
        resolved_runner,
        OobCommand(
            service=db_service(),
            argv=(
                "sh", "-c",
                f"""mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" {db_name} -e '{statement}'""",
            ),
        ),
    )


# 站点名会被拼进容器内路径，因此过一次比标识符更严的白名单（站点名带 `.`，但不许有 `/` 与 `..`）。
_SITE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _check_site_path(site: str) -> str:
    if not _SITE_NAME.match(site) or ".." in site:
        raise OobError(f"站点名 {site!r} 不在白名单 {_SITE_NAME.pattern} 内，拒绝拼进容器内路径")
    return site
