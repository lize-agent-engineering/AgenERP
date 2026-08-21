"""非门禁测试 · 把 `system-baseline.md` §14 的规则固化成对 `docker-compose.yml` 的判据。

门禁 `tests/gates/test_zero_dep_boot.py::test_compose_config_valid_with_empty_env` 只判
「空环境下 `config -q` 退 0」。那一条**不覆盖**下面这些：一份写了 `${VAR:?}` 的 compose 在
配了变量的机器上照样 `config` 退 0，红只会在别人 `git clone` 之后才出现。所以规则要有自己的判据。

本文件**只用标准库**：`tests/unit` 唯一的运行处是本机 `GATE_VERIFY` 复跑
`missions/p0-foundation.json` 的 `commands.test`。判定面一旦依赖某个包，换台机器就会红在
环境而不是红在实现上。

判据全部是对**原始文本**的扫描，不经 `docker compose config`——这是刻意的：
仓根有 gitignored 的 `.env`，`config` 会读它做插值（实测 `AGENERP_HTTP_PORT=9999` 会把
`published` 改成 9999），于是「解析后的结果」在不同机器上不是同一个东西。原始文本是。
代价是要自己处理 `$$` 转义与 YAML 语法，下面逐条写明。
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"

# compose 里 `$$` 是给容器内 shell 的**字面 `$`**，不是 compose 插值
# （实测：`command: ["sh","-c","echo $${HOME}"]` 经 `config` 后原样是 `echo $${HOME}`）。
# frappe/erpnext 的 command 块大量用它——不先剔除，下面的插值判据会对着正确的 compose 报红。
_ESCAPED_DOLLAR = re.compile(r"\$\$")

# 剔除 `$$` 之后，真正的 compose 插值就是 `${...}`。
_INTERPOLATION = re.compile(r"\$\{([^}]*)\}")


def _raw() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


def _text_without_escapes() -> str:
    """把 `$$` 换成不含 `$` 的占位，其余原样保留。"""
    return _ESCAPED_DOLLAR.sub("<ESCAPED-DOLLAR>", _raw())


# --- 元测试：与本 plan 的实现无关，只守「文件还在原地」 ------------------------------
# 仓根用 __file__ 解析而不是 cwd：门禁那条本来就是 cwd 相关的
# （`docker compose -f docker-compose.yml`），这条元测试的价值恰恰在于不跟着 cwd 一起坏。


def test_compose_file_exists_at_repo_root():
    """失败意味着有人挪走了 docker-compose.yml。

    门禁会红在 `no such file or directory`（正是 2026-08-21 之前的红因），
    那个报错不会告诉你文件该在哪；这一条会。
    """
    assert COMPOSE_PATH.is_file(), f"仓库根目录没有 docker-compose.yml：{COMPOSE_PATH}"
    assert COMPOSE_PATH.stat().st_size > 0, "docker-compose.yml 是空文件"


# --- §14 规则 ① 禁止硬失败插值 ------------------------------------------------------


def test_no_hard_fail_interpolation():
    """规则 ①：不许出现 `${VAR:?}` / `${VAR:?msg}`。

    失败意味着：某个变量变成必填。新用户 `git clone && docker compose up` 会在 `config`
    这一步就失败——这正是 Spike 10 定位到的确切成因，不是启动失败，是连解析都过不去。
    """
    offenders = [
        m.group(0)
        for m in _INTERPOLATION.finditer(_text_without_escapes())
        if ":?" in m.group(1)
    ]
    assert not offenders, f"这些插值是硬失败语法，会让零依赖启动在 config 就崩：{offenders}"


def test_every_interpolation_has_a_default():
    """「零必填」的正面表述：每个 `${...}` 都必须带 `:-` 默认值。

    比只禁 `:?` 更严——`${VAR}` 不写默认值虽然不会让 `config` 失败，但会静默插成空串，
    把「没配」变成「配了个空的」，故障会挪到运行时才炸。

    失败意味着：有人加了一个没有默认值的变量，`clone && up` 不再是零配置的。
    """
    bad = [
        m.group(0)
        for m in _INTERPOLATION.finditer(_text_without_escapes())
        if ":-" not in m.group(1)
    ]
    assert not bad, f"这些插值没有 `:-` 默认值，零依赖启动不再成立：{bad}"


# --- §14 规则 ② 未配置是合法状态 ----------------------------------------------------

AI_VARS = ["AGENERP_LLM_ENDPOINT", "AGENERP_LLM_API_KEY", "AGENERP_LLM_MODEL"]


@pytest.mark.parametrize("var", AI_VARS)
def test_ai_variable_defaults_to_empty(var: str):
    """规则 ②：外部 AI 能力缺失是「未配置」状态，不是错误状态。

    失败意味着：AI 变量有了非空默认值（指向某个真实 endpoint 或塞了 key），
    于是「没配 AI」这件事在栈里不再可判别——服务会拿着一个假地址去连。
    """
    hits = re.findall(re.escape(var) + r":-([^}]*)\}", _text_without_escapes())
    assert hits, f"{var} 没有以 `${{{var}:-…}}` 的形式出现在 compose 里"
    assert all(h == "" for h in hits), f"{var} 的默认值必须是空字符串，实际：{hits}"


# --- §14「⚠️ 附带风险」段：默认口令必须配回环绑定 -----------------------------------
# 出处是 §14 的「附带风险」段，**不是规则 ③**。规则 ③（前置检查属于 verify 脚本）
# 在本仓此刻没有对象，处置记在 plan 的 `## Deferred But Adjudicated`。

_PORT_ENTRY = re.compile(r'^\s*-\s*"?([^"\n]+)"?\s*$')


def _published_port_entries() -> list[str]:
    """收集 `ports:` 块下的条目。只认短语法（`- "127.0.0.1:8080:8080"`）。

    刻意不解析 YAML：一是不引依赖，二是长语法（`host_ip: …`）本来就被下面那条禁掉了，
    出现即失败，不需要为它写解析。
    """
    entries: list[str] = []
    in_ports = False
    ports_indent = 0
    for line in _text_without_escapes().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped == "ports:":
            in_ports = True
            ports_indent = indent
            continue
        if in_ports:
            if indent <= ports_indent:
                in_ports = False
            elif stripped.startswith("- "):
                entries.append(stripped[2:].strip().strip('"').strip("'"))
            else:
                # 长语法的 `host_ip:` / `published:` 之类，原样收进去让判据去红
                entries.append(stripped)
    return entries


def test_published_ports_bind_loopback_literally():
    """默认口令的对冲手段：所有发布端口只绑 127.0.0.1，且 IP **字面写死**。

    必须字面写死、不许写成 `${BIND:-127.0.0.1}`：本条是静态文本扫描，而 `.env` 能在
    `config` 时把变量改掉。变量驱动的绑定地址会「单测绿、真实绑到 0.0.0.0」——
    默认弱口令就此暴露到局域网。

    失败意味着：某个端口发布到了回环之外，而栈里跑的是 changeit / admin。
    """
    entries = _published_port_entries()
    assert entries, "compose 里一个发布端口都没有——前端起来了也访问不到，判据形同虚设"
    for entry in entries:
        assert entry.startswith("127.0.0.1:"), (
            f"端口条目 {entry!r} 的宿主侧不是字面的 127.0.0.1。"
            "默认口令只在回环绑定的前提下才是可接受的。"
        )


def test_ports_use_short_syntax_only():
    """只允许短语法。

    长语法（`host_ip: 127.0.0.1`）本身没问题，但上面那条判据是按短语法写的；
    混用会让它扫不到而静默放行。要改用长语法，得先回来改判据，不许在执行时临时放宽。

    失败意味着：有人用了长语法，回环绑定判据对那个端口是失效的。
    """
    for entry in _published_port_entries():
        assert ":" in entry and not entry.endswith(":"), f"端口条目 {entry!r} 不是短语法"
        assert not re.match(r"^(target|published|host_ip|protocol|mode)\s*:", entry), (
            f"端口条目 {entry!r} 是长语法；回环绑定判据只覆盖短语法"
        )


# --- 版本与写法约束 -----------------------------------------------------------------


def test_no_top_level_version_key():
    """compose v2+ 已弃用顶层 `version:`。

    实测它只是告警不是报错（带 `version: "3.9"` 时 `config -q` 仍退 0，只打
    `the attribute 'version' is obsolete`），所以这条判据守的是「别再写回来」，
    不是守 `config` 的退出码。
    """
    for line in _raw().splitlines():
        assert not re.match(r"^version\s*:", line), "不要写顶层 version: 键，compose v2+ 已弃用"


def test_no_floating_image_tags():
    """镜像 tag 必须写死具体版本。

    失败意味着：某个镜像用了 `latest` 或干脆没写 tag。栈会在某天因为上游发版而
    自己变形，而「零依赖启动能不能起来」这件事就不再可复现——今天绿明天红，
    且 diff 里看不出任何改动。
    """
    for line in _raw().splitlines():
        m = re.match(r"^\s*image:\s*(\S+)\s*$", line)
        if not m:
            continue
        ref = m.group(1)
        assert not ref.endswith(":latest"), f"{ref} 用了 latest tag"
        name = ref.rsplit("/", 1)[-1]
        assert ":" in name, f"{ref} 没写 tag，等同 latest"


# --- 引导服务（plan 2026-08-21-2220-2 新增，只加不改） -------------------------------
# 三条新判据全部服务于同一件事：首页那句「AI 能力未配置」是**编排层的可复现产物**，
# 而不是谁在站点上手点出来的。既有判据一条不动。

BOOTSTRAP_SERVICE = "bootstrap-homepage"
BOOTSTRAP_DIR = REPO_ROOT / "tools" / "bootstrap"


def _service_block(name: str) -> list[str]:
    """取 `services:` 下某个服务的整块（含其下所有更深缩进的行）。

    同样刻意不解析 YAML：理由与 `_published_port_entries` 一致，见文件头。
    """
    lines = _raw().splitlines()
    out: list[str] = []
    header = f"  {name}:"
    inside = False
    for line in lines:
        if line.rstrip() == header:
            inside = True
            continue
        if inside:
            if line.strip() and not line.startswith("    "):
                break
            out.append(line)
    return out


def test_bootstrap_service_is_one_shot():
    """引导服务必须存在，且是「跑完即退」的一次性形状。

    失败意味着两件事之一：引导服务没了（首页那句话回到「靠人手点」，
    `git clone && docker compose up` 不再自带它）；或者它被改成了常驻服务
    —— 那样 `up -d --wait` 会一直等它 healthy，而它根本没有探针。
    """
    block = _service_block(BOOTSTRAP_SERVICE)
    assert block, f"compose 里没有 {BOOTSTRAP_SERVICE} 服务——首页文案不再是启动路径的产物"
    joined = "\n".join(block)
    assert re.search(r'^\s*restart:\s*"no"\s*$', joined, re.M), (
        f"{BOOTSTRAP_SERVICE} 不是一次性形状（缺 `restart: \"no\"`），"
        "与 configurator / create-site 的纪律不一致"
    )
    assert re.search(r"^\s*create-site:\s*$", joined, re.M), (
        f"{BOOTSTRAP_SERVICE} 没有等 create-site 完成——站点还不存在时写 Website Settings 必然失败"
    )


def test_bootstrap_script_dir_is_mounted_literally():
    """引导服务挂的必须**就是**上面那条判据扫的那个目录，且路径字面写死。

    没有这一条，红线 7 判据就是悬空的：它扫 `tools/bootstrap/`，而 compose 可以挂别处。
    实测两条绕过路径都能让本文件全绿——把挂载换成 `./tools/evilboot`（新目录里放脚本标签），
    或写成 `${AGENERP_BOOTSTRAP_DIR:-./tools/bootstrap}`（`:-` 默认值满足既有插值判据，
    而仓根 `.env` 能在 `config` 时把它改掉）。这是 2026-08-21 关闭审计实测出来的洞。

    与 `test_published_ports_bind_loopback_literally` 是同一条理由：静态文本扫描管不到 `.env`，
    所以凡是判据依赖的路径，都必须字面写死。

    失败意味着：红线 7 的判据扫的目录和容器里真正跑的目录不是同一个。
    """
    joined = "\n".join(_service_block(BOOTSTRAP_SERVICE))
    mounts = [ln.strip()[2:].strip() for ln in joined.splitlines()
              if ln.strip().startswith("- ") and ":/" in ln]
    host_side = [m.split(":", 1)[0] for m in mounts if m.startswith(".")]
    assert host_side == ["./tools/bootstrap"], (
        f"{BOOTSTRAP_SERVICE} 的宿主侧 bind mount 必须且只能是字面的 `./tools/bootstrap`，实际：{host_side}。"
        "写成变量或换成别的目录，红线 7 判据就扫不到真正跑起来的脚本了。"
    )


def _healthcheck_blocks() -> list[str]:
    """取所有 `healthcheck:` 块的正文。"""
    blocks: list[str] = []
    current: list[str] | None = None
    indent = 0
    for line in _text_without_escapes().splitlines():
        stripped = line.strip()
        if stripped == "healthcheck:":
            if current is not None:
                blocks.append("\n".join(current))
            current = []
            indent = len(line) - len(line.lstrip())
            continue
        if current is not None:
            if stripped and (len(line) - len(line.lstrip())) <= indent:
                blocks.append("\n".join(current))
                current = None
            else:
                current.append(line)
    if current is not None:
        blocks.append("\n".join(current))
    return blocks


def test_ai_vars_absent_from_healthchecks():
    """§14 规则 ② 的可执行化：AI 变量不得出现在任何 `healthcheck:` 块内。

    规则原话是「不进 healthcheck / command 的成败路径」，但「成败路径」是语义，
    文本扫描判不了；能判的是「出现在哪个块里」。healthcheck 块整块都是成败路径，
    所以「出现即违规」在这里是精确的，不是近似。

    失败意味着：某个服务的存活判定开始依赖 AI 配置。没配 AI 的机器上，
    栈会因为「未配置」这个**正常状态**而判成不健康——`clone && up` 不再零依赖。
    """
    for block in _healthcheck_blocks():
        for var in AI_VARS:
            assert var not in block, f"{var} 出现在 healthcheck 块里，未配置会变成不健康：\n{block}"


def test_bootstrap_delivers_no_runtime_code():
    """红线 7 的可执行判据：引导逻辑只交付静态文本，不交付可执行代码。

    扫两处：`tools/bootstrap/` 下的全部文件（横幅 HTML 的唯一出处就在这里），
    以及 compose 里引导服务那一块。

    失败意味着：首页横幅里出现了脚本标签或模板定界符，或者引导步骤开始建
    运行时代码类 DocType。那等同于让 Agent 生成可执行代码（AGENTS.md 红线 7）——
    交付的必须是可 diff、可回滚的静态产物，不是站点上跑起来的代码。
    """
    forbidden = ["<script", "{{", "{%", "Server Script", "Client Script"]
    assert BOOTSTRAP_DIR.is_dir(), f"引导脚本目录不在：{BOOTSTRAP_DIR}"
    targets = {str(f): f.read_text(encoding="utf-8") for f in sorted(BOOTSTRAP_DIR.rglob("*")) if f.is_file()}
    assert targets, f"{BOOTSTRAP_DIR} 是空的——引导逻辑没有落盘处，判据也就没有对象"
    targets["docker-compose.yml::" + BOOTSTRAP_SERVICE] = "\n".join(_service_block(BOOTSTRAP_SERVICE))
    for where, text in targets.items():
        for token in forbidden:
            assert token not in text, f"{where} 含 {token!r}——红线 7：引导逻辑不得交付运行时代码"
