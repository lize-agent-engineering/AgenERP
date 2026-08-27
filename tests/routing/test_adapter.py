"""adapter 与配置的判据 —— **全部零网络**，一律走假 transport。

四组判据：

1. **正常路径**：纯文本回包 / 工具调用回包 / 三项 token 分开解析 /
   `completion_tokens_details.reasoning_tokens` 缺失时回 0（**不是**回退成算进 completion）。
2. **失败路径**：非 2xx · 连不上 · 载荷不是 JSON · 回包缺 `choices` ——
   四类各抛一次，且**一次都不许降级成空 `Reply`**。
3. **凭据不外泄**：塞一个哨兵 key 进配置，断言它不出现在 `repr(config)` /
   `repr(adapter)` / 任何一条异常文本里。靠断言，不靠 code review。
4. **CI 依赖面反测**：`agenerp/**` 模块级不许 `import certifi`，
   且 `agenerp.routing` 在**全新解释器**里 import 完后 `certifi` 不在 `sys.modules`。
   这一条直接对着「CI 的 `unit-and-contracts` job 只 `pip install pytest`」那个坑
   —— 模块级 import 会让 CI 当场 ImportError。

**两道都做，不是重复**：AST 那道确定性强、不受 pytest 会话里别处 import 的污染；
子进程那道是行为判据，能抓到 AST 抓不到的形态（模块级 `importlib.import_module("certifi")`、
或 import 期就调用了构造 SSL 上下文的函数）。任一单独一道都有盲区。
"""

from __future__ import annotations

import ast
import dataclasses
import io
import json
import ssl
import subprocess
import sys
import traceback
import urllib.error
from pathlib import Path

import pytest

from agenerp.routing import adapter as adapter_module
from agenerp.routing.adapter import DEFAULT_ENABLE_THINKING, DEFAULT_TIMEOUT, ChatAdapter, Reply, Usage, usage_of
from agenerp.routing.config import (
    API_KEY_ENV,
    BASE_URL_ENV,
    MODEL_ENV,
    REQUIRED_ENV,
    LlmConfig,
    from_env,
)
from agenerp.routing.errors import RoutingError

REPO_ROOT = Path(__file__).resolve().parents[2]
SENTINEL_KEY = "sk-sentinel-DO-NOT-LEAK-4f3a9c"


def _config(**over) -> LlmConfig:
    base = {
        "base_url": "https://endpoint.invalid/compatible-mode/v1",
        "model": "qwen3.6-plus",
        "api_key": SENTINEL_KEY,
    }
    return LlmConfig(**(base | over))


def _adapter(transport) -> ChatAdapter:
    return ChatAdapter(_config(), transport=transport)


def _body(message: dict, usage: dict | None = None) -> dict:
    return {"choices": [{"message": message}], "usage": usage or {}}


# --- 1. 正常路径 -------------------------------------------------------------


def test_plain_text_reply_is_parsed_and_stripped():
    adapter = _adapter(lambda payload: _body({"content": "  1,010 台  "}))
    reply = adapter.chat([{"role": "user", "content": "问"}])
    assert reply.text == "1,010 台"
    assert reply.tool_calls == ()
    assert reply.model == "qwen3.6-plus"


def test_tool_call_reply_is_parsed():
    call = {"id": "c1", "type": "function", "function": {"name": "doc.get", "arguments": "{}"}}
    adapter = _adapter(lambda payload: _body({"content": None, "tool_calls": [call]}))
    reply = adapter.chat([{"role": "user", "content": "问"}], tools=[{"type": "function"}])
    assert reply.text == ""
    assert reply.tool_calls == (call,)


def test_tools_key_is_omitted_when_no_tools_are_given():
    """空 `tools` 数组在部分兼容端点上会 400 —— 那会把"这次不带工具"变成一次假故障。"""
    seen: list[dict] = []

    def transport(payload):
        seen.append(payload)
        return _body({"content": "ok"})

    _adapter(transport).chat([{"role": "user", "content": "问"}])
    assert "tools" not in seen[0]
    assert seen[0]["model"] == "qwen3.6-plus"
    assert seen[0]["max_tokens"] > 0


def test_three_token_counts_are_kept_apart():
    usage = {
        "prompt_tokens": 1200,
        "completion_tokens": 40,
        "completion_tokens_details": {"reasoning_tokens": 195},
    }
    adapter = _adapter(lambda payload: _body({"content": "在线"}, usage))
    reply = adapter.chat([{"role": "user", "content": "问"}])
    assert reply.usage == Usage(prompt=1200, completion=40, reasoning=195)
    assert reply.usage.total == 1240, (
        "total = prompt + completion，与端点自报的 total_tokens 一致；"
        "reasoning 是 completion 的细分，**不许再加一遍**（活端点实读：15 + 178 = 193）"
    )
    assert reply.usage.as_dict()["reasoning"] == 195


def test_missing_reasoning_detail_reads_as_zero_not_as_completion():
    parsed = usage_of({"prompt_tokens": 10, "completion_tokens": 7})
    assert parsed == Usage(prompt=10, completion=7, reasoning=0)


def test_reasoning_is_never_folded_into_completion():
    """M4 变异自查当场补的一条：原先只有一处断言拦得住"reasoning 记进 completion"。
    这条直接判解析函数本身 —— reasoning 与 completion 常常不同价，
    折进去会让 P1.7 的成本模型算错一个量级。"""
    parsed = usage_of(
        {
            "prompt_tokens": 5,
            "completion_tokens": 12,
            "completion_tokens_details": {"reasoning_tokens": 900},
        }
    )
    assert parsed.completion == 12
    assert parsed.reasoning == 900
    assert parsed.total == 17


def test_usage_plus_adds_all_three_dimensions():
    assert Usage(1, 2, 3).plus(Usage(10, 20, 30)) == Usage(11, 22, 33)


# --- 1b. 出站请求本身（`_post`）——收口审计 F1 当场补的一整组 -------------------
#
# 独立收口审计用四个变异证明了这里原先是**完全空的**：把 `messages` 换成空数组、
# 让 `tools` 永不转发、拿掉 `context=_ssl_context()`（D-11 明文要求的 certifi）、
# 把 `Authorization` 换成别的头 —— **四个变异全都绿着过去**。
# 根因是每条单测都注入 transport，`_post` 一次都没被执行过。
# 下面这组直接判**发出去的那个请求**：URL / 方法 / 请求头 / 载荷 / SSL 上下文。


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


@pytest.fixture
def sent(monkeypatch):
    """打桩 `urlopen`，把真正发出去的那个 `Request` 原样接住。"""
    captured: dict = {}

    def fake_urlopen(request, timeout=None, context=None):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["context"] = context
        captured["timeout"] = timeout
        return _FakeResponse(_body({"content": "在线"}, {"prompt_tokens": 3}))

    monkeypatch.setattr(adapter_module.urllib.request, "urlopen", fake_urlopen)
    return captured


def _post_once(sent, **kw):
    """走**真** `_post`（transport=None），不是假 transport。"""
    return ChatAdapter(_config(), transport=None).chat(**kw), sent


def test_post_sends_the_messages_verbatim(sent):
    """杀 Mut-A1：`messages` 被换成空数组时必须红 —— 用户的问题没发出去是最坏的静默失败。"""
    messages = [{"role": "system", "content": "系统指令"}, {"role": "user", "content": "1,010 台哪来的"}]
    _post_once(sent, messages=messages)
    assert sent["body"]["messages"] == messages


def test_post_forwards_tools_when_they_are_supplied(sent):
    """杀 Mut-A2：`if tools:` 被改成永不转发时必须红 —— 工具没发出去，Agent 就成了纯聊天。"""
    tools = [{"type": "function", "function": {"name": "doc.get"}}]
    _post_once(sent, messages=[{"role": "user", "content": "问"}], tools=tools, max_tokens=321)
    assert sent["body"]["tools"] == tools
    assert sent["body"]["max_tokens"] == 321
    assert sent["body"]["model"] == "qwen3.6-plus"


def test_post_hits_the_openai_compatible_path_with_post(sent):
    _post_once(sent, messages=[{"role": "user", "content": "问"}])
    assert sent["url"] == "https://endpoint.invalid/compatible-mode/v1/chat/completions"
    assert sent["method"] == "POST"
    assert sent["headers"]["Content-type"] == "application/json"


def test_post_carries_the_bearer_authorization_header(sent):
    """杀 Mut-A4：换掉 `Authorization` 时必须红 —— 端点会 401，而那是一次假故障。"""
    _post_once(sent, messages=[{"role": "user", "content": "问"}])
    assert sent["headers"]["Authorization"] == f"Bearer {SENTINEL_KEY}"


def test_post_always_supplies_an_explicit_ssl_context(sent):
    """杀 Mut-A3。D-11 的环境注记**明文**要求产品代码显式给 CA 根证书
    （本机 python.org 版 Python 未装系统 CA，依赖默认必报 CERTIFICATE_VERIFY_FAILED）。
    拿掉 `context=` 在装了 CA 的机器上照样跑得通 —— 所以只有这条断言拦得住它。"""
    pytest.importorskip("certifi", reason="_post 构造 SSL 上下文需要 certifi（D-11）")
    _post_once(sent, messages=[{"role": "user", "content": "问"}])
    assert isinstance(sent["context"], ssl.SSLContext), "没有显式 SSL 上下文 —— D-11 的环境注记被绕过了"
    assert sent["timeout"] == DEFAULT_TIMEOUT


def test_the_ssl_context_is_built_from_certifi_and_only_then_is_certifi_imported():
    """惰性 import 的**另一半**：不但模块级不许 import，真要用时还必须**真的**用 certifi 的 CA。"""
    certifi = pytest.importorskip("certifi")
    context = adapter_module._ssl_context()
    assert isinstance(context, ssl.SSLContext)
    loaded = {cert["subject"] for cert in context.get_ca_certs()}
    reference = ssl.create_default_context(cafile=certifi.where())
    assert loaded == {cert["subject"] for cert in reference.get_ca_certs()}


def test_post_maps_a_real_http_error_the_same_way_the_transport_path_does(monkeypatch):
    """真网络那一段的失败映射也要判，别让"两条路一段映射"这句话只停在 docstring 里。"""

    def boom(request, timeout=None, context=None):
        raise _http_error(503, "upstream down")

    monkeypatch.setattr(adapter_module.urllib.request, "urlopen", boom)
    with pytest.raises(RoutingError, match="HTTP 503"):
        ChatAdapter(_config(), transport=None).chat([{"role": "user", "content": "问"}])


# --- 2. 失败路径：四类各一次，一次都不许降级成空 Reply -------------------------


def _http_error(code: int, detail: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://endpoint.invalid/compatible-mode/v1/chat/completions",
        code,
        "boom",
        {},
        io.BytesIO(detail.encode("utf-8")),
    )


def _raises(exc):
    def transport(payload):
        raise exc

    return transport


def test_non_2xx_raises_and_carries_the_status():
    adapter = _adapter(_raises(_http_error(429, "rate limited")))
    with pytest.raises(RoutingError, match="HTTP 429"):
        adapter.chat([{"role": "user", "content": "问"}])


def test_unreachable_endpoint_raises():
    adapter = _adapter(_raises(urllib.error.URLError("name resolution failed")))
    with pytest.raises(RoutingError, match="连不上端点"):
        adapter.chat([{"role": "user", "content": "问"}])


def test_payload_that_is_not_json_raises():
    adapter = _adapter(_raises(ValueError("Expecting value: line 1 column 1")))
    with pytest.raises(RoutingError, match="不是 JSON"):
        adapter.chat([{"role": "user", "content": "问"}])


def test_reply_without_choices_raises_instead_of_degrading_to_empty_text():
    adapter = _adapter(lambda payload: {"usage": {}})
    with pytest.raises(RoutingError, match="没有 choices"):
        adapter.chat([{"role": "user", "content": "问"}])


def test_reply_whose_choice_has_no_message_raises():
    adapter = _adapter(lambda payload: {"choices": [{"finish_reason": "stop"}], "usage": {}})
    with pytest.raises(RoutingError, match="没有成形的 message"):
        adapter.chat([{"role": "user", "content": "问"}])


def test_a_reply_with_neither_text_nor_tool_calls_raises_instead_of_coming_back_empty():
    """收尾自查（`development-wisdom-gate-prompt.md` 第 1 条"深度"）当场补的：
    原实现在这里会**回一个空 `Reply`** —— 那正是模块头拒绝的那种降级，
    与"模型选择不作答"长得一模一样。`finish_reason='length'` 是 max_tokens 截断，
    调用方必须知道，不能被当成一次回答。"""
    body = {
        "choices": [{"message": {"content": ""}, "finish_reason": "length"}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 64},
    }
    with pytest.raises(RoutingError) as caught:
        _adapter(lambda payload: body).chat([{"role": "user", "content": "问"}])
    assert "length" in str(caught.value)
    assert "不降级成空回答" in str(caught.value)


def test_a_reply_with_only_tool_calls_and_no_text_is_still_valid():
    """反过来不能矫枉过正：只回工具调用、不回文本是**正常**的一轮。"""
    call = {"id": "c1", "type": "function", "function": {"name": "doc.get", "arguments": "{}"}}
    reply = _adapter(lambda payload: _body({"content": None, "tool_calls": [call]})).chat(
        [{"role": "user", "content": "问"}]
    )
    assert reply.text == "" and reply.tool_calls == (call,)


def test_non_dict_body_raises():
    adapter = _adapter(lambda payload: "OK")
    with pytest.raises(RoutingError, match="不是 JSON 对象"):
        adapter.chat([{"role": "user", "content": "问"}])


@pytest.mark.parametrize(
    "transport",
    [
        _raises(_http_error(500, "server error")),
        _raises(urllib.error.URLError("down")),
        _raises(ValueError("bad json")),
        lambda payload: {"usage": {}},
        lambda payload: "OK",
        lambda payload: {"choices": [{"message": {"content": "  "}}], "usage": {}},
    ],
    ids=["http-5xx", "unreachable", "not-json", "no-choices", "not-an-object", "empty-answer"],
)
def test_no_failure_mode_ever_returns_a_reply(transport):
    """**降级反测**：五类失败没有一类能拿到 `Reply`。
    空回答与「模型选择不作答」长得一样，降级会把一次故障记成一次真实结果。"""
    with pytest.raises(RoutingError):
        result = _adapter(transport).chat([{"role": "user", "content": "问"}])
        assert not isinstance(result, Reply)


# --- 3. 配置：三个变量、零默认值、凭据不外泄 ---------------------------------


def test_from_env_reads_all_three_variables():
    env = {
        BASE_URL_ENV: " https://endpoint.invalid/v1/ ",
        API_KEY_ENV: SENTINEL_KEY,
        MODEL_ENV: "qwen3.6-plus",
    }
    config = from_env(env)
    assert config.base_url == "https://endpoint.invalid/v1"
    assert config.model == "qwen3.6-plus"
    assert config.chat_completions_url.endswith("/v1/chat/completions")


@pytest.mark.parametrize("dropped", REQUIRED_ENV)
def test_each_missing_variable_fails_by_name_with_no_default(dropped):
    env = {
        BASE_URL_ENV: "https://endpoint.invalid/v1",
        API_KEY_ENV: SENTINEL_KEY,
        MODEL_ENV: "qwen3.6-plus",
    }
    del env[dropped]
    with pytest.raises(RoutingError) as caught:
        from_env(env)
    assert dropped in str(caught.value)


BANNED_VENDOR_TOKENS = ("DASHSCOPE", "dashscope", "aliyuncs", "api.openai.com", "api.deepseek.com")


def _live_strings(path: Path) -> list[str]:
    """一个模块里**真正参与运行**的字符串字面量 —— docstring 不算。

    扫原文会把 docstring 里"我们**不读** `DASHSCOPE_*`"这句话本身判成厂商绑定，
    那就成了"越是把理由写清楚越红"。判据要判的是代码，不是散文。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(id(node.body[0].value))
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    ]


def test_no_vendor_env_name_or_endpoint_is_baked_into_the_product_package():
    """§12.1 ①：产品配置面不许把厂商写进去。`DASHSCOPE_*` 只属于实验设施。"""
    assert REQUIRED_ENV == (BASE_URL_ENV, API_KEY_ENV, MODEL_ENV)
    for path in sorted((REPO_ROOT / "agenerp").rglob("*.py")):
        for literal in _live_strings(path):
            for banned in BANNED_VENDOR_TOKENS:
                assert banned not in literal, f"{path} 里出现了厂商绑定：{banned}"


def test_the_api_key_never_shows_up_in_a_repr():
    config = _config()
    assert SENTINEL_KEY not in repr(config)
    assert SENTINEL_KEY not in str(config)
    assert SENTINEL_KEY not in repr(ChatAdapter(config, transport=lambda p: _body({})))


@pytest.mark.parametrize(
    "transport",
    [
        _raises(_http_error(401, "invalid api key")),
        _raises(urllib.error.URLError("down")),
        _raises(ValueError("bad json")),
        lambda payload: {"usage": {}},
    ],
    ids=["http-401", "unreachable", "not-json", "no-choices"],
)
def test_the_api_key_never_shows_up_in_an_exception_text(transport):
    with pytest.raises(RoutingError) as caught:
        _adapter(transport).chat([{"role": "user", "content": "问"}])
    rendered = f"{caught.value}\n{caught.value!r}\n{caught.value.__cause__!r}"
    assert SENTINEL_KEY not in rendered


def test_the_api_key_never_shows_up_in_a_config_error():
    with pytest.raises(RoutingError) as caught:
        from_env({API_KEY_ENV: SENTINEL_KEY})
    assert SENTINEL_KEY not in str(caught.value)


def test_the_api_key_survives_no_bulk_serialization_path():
    """收口审计 F6：`repr` 不够。`dataclasses.asdict()` 会把 `repr=False` 的字段照样倒出来，
    `vars()` / `__dict__` 也一样 —— 那两条不是假想，任何一句"把配置打进日志看看"都会走上去。
    现在 `LlmConfig` 用 `__slots__` 且不是 dataclass，这两条路整个不存在。"""
    config = _config()
    assert not dataclasses.is_dataclass(config)
    with pytest.raises(TypeError):
        vars(config)
    assert not hasattr(config, "__dict__")
    with pytest.raises(TypeError):
        dataclasses.asdict(config)
    with pytest.raises(AttributeError):
        config.base_url = "https://elsewhere.invalid"


def test_the_api_key_is_absent_from_a_standard_traceback(monkeypatch):
    """**边界照实判**：标准库 `traceback.format_exc()` 不打栈帧 locals，本层判的就是它。
    ⚠️ 带 locals 的打印器（rich / cgitb / `pytest -l`）**仍读得到** `_post` 栈帧里那个
    `Request` 的请求头 —— 本层挡不住，`config.py` 的模块头与 §12.5 都逐字写明了这条边界。"""

    def boom(request, timeout=None, context=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(adapter_module.urllib.request, "urlopen", boom)
    try:
        ChatAdapter(_config(), transport=None).chat([{"role": "user", "content": "问"}])
    except RoutingError:
        rendered = traceback.format_exc()
    assert SENTINEL_KEY not in rendered


def test_authorization_header_is_the_only_place_the_key_is_used():
    """key 的读取面收在 `config.authorization()` 一处 —— 面越小，泄漏点越少。"""
    assert _config().authorization() == f"Bearer {SENTINEL_KEY}"
    for path in sorted((REPO_ROOT / "agenerp/routing").glob("*.py")):
        if path.name == "config.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        touched = [
            n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "api_key"
        ]
        assert not touched, f"{path.name} 直接读了 api_key，应只经 config.authorization()"


# --- 4. CI 依赖面反测 --------------------------------------------------------

PRODUCT_MODULES = sorted((REPO_ROOT / "agenerp").rglob("*.py"))


@pytest.mark.parametrize("path", PRODUCT_MODULES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_product_module_imports_certifi_at_module_level(path):
    """CI 的 `unit-and-contracts` job 只 `pip install pytest` —— 模块级 import 会当场 ImportError。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        assert "certifi" not in names, f"{path} 在模块级 import 了 certifi"


def test_the_routing_package_imports_in_a_fresh_interpreter_without_pulling_certifi():
    """行为判据，跑在**全新解释器**里 —— 会话里别处的 import 污染不到它。"""
    script = (
        "import importlib, sys, json;"
        "mods = ['agenerp.routing', 'agenerp.routing.adapter', 'agenerp.routing.capabilities',"
        " 'agenerp.routing.config', 'agenerp.routing.errors', 'agenerp.routing.router'];"
        "[importlib.import_module(m) for m in mods];"
        "print(json.dumps({'certifi_loaded': 'certifi' in sys.modules, 'count': len(mods)}))"
    )
    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout.strip().splitlines()[-1])
    assert result["count"] == 6
    assert result["certifi_loaded"] is False


def test_the_export_surface_stays_small():
    import agenerp.routing as routing

    assert routing.__all__ == (
        "route",
        "ChatAdapter",
        "RoutingError",
        "CAPABILITIES",
        "TASK_MINIMUM_CAPABILITIES",
        "ModelProfile",
    )
    for internal in ("LlmConfig", "Usage", "usage_of", "validate_declarations", "DeclarationError"):
        assert internal not in routing.__all__


# ── 关思考是产品默认（人 2026-08-27 裁定）──────────────────────────────────


def _payload_of(**kwargs) -> dict:
    """跑一次 `chat()`，把**真正发出去的载荷**抓回来。"""
    seen: dict = {}

    def transport(payload):
        seen.clear()
        seen.update(payload)
        return {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}], "usage": {}}

    ChatAdapter(
        LlmConfig("http://endpoint.invalid", "m", "k"), transport=transport, **kwargs
    ).chat([{"role": "user", "content": "hi"}])
    return seen


def test_thinking_is_off_by_default_and_the_flag_really_goes_out():
    """🔴 **产品默认必须是「显式关思考」**，而且要真的发出去。

    人 2026-08-27 裁定「关思考 + 保持 4096」。两条是**绑在一起的一个决定**：
    不关时 `glm-5.2` 做难题会把整个输出预算烧在 reasoning 上
    （实测 `completion=16385 / reasoning=16384`、`finish_reason='length'`，
    **一个字都没吐**），把上限调大不解决 —— 它只是想得更多。
    关掉之后同一条题实测 reasoning **每次调用都是 0**，截断消失。

    ⚠️ 本条判的是**默认值**，不是「能不能设」。默认值被改回去而没人发现，
    等于那次裁定没有发生 —— 而症状是**真人拿到一片空白**，很难指回这里。
    """
    payload = _payload_of()

    assert payload.get("enable_thinking") is False, (
        f"产品默认没有关思考：载荷里的 enable_thinking = {payload.get('enable_thinking')!r}"
    )
    assert DEFAULT_ENABLE_THINKING is False


def test_passing_none_sends_nothing_so_a_foreign_endpoint_can_opt_out():
    """逃生口：`enable_thinking=None` ⇒ **一个字节都不发**。

    这个键不在 OpenAI 兼容四件套里，是百炼一侧的扩展。§12.1 ① 要求
    「默认不指向任何商业 API」，而默认值确实把一个厂商扩展写进了默认路径
    —— **那是一处让步**。本条钉住让步的**出口**：
    换到不认这个键的端点时，传 `None` 就回到「不发送」。
    """
    assert "enable_thinking" not in _payload_of(enable_thinking=None)
    assert _payload_of(enable_thinking=True).get("enable_thinking") is True
