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
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

from agenerp.routing.adapter import ChatAdapter, Reply, Usage, usage_of
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
