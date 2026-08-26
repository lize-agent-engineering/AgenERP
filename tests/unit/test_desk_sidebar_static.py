"""⌘K 侧边栏的**离线**判据（§7.23）—— 不起浏览器、不跑 JS 运行时就能判的那一半。

**口径（沿用 §7.22 / §14.11）：两个源各读一次再比，判据里不写第三个字面量。**
写了第三个之后，这份判据就只是在验证一个字符串等于它自己，而真正要对齐的两个文件
可以一起漂走 —— 那正是「绿着坏掉」。

守五件事：
① 资产里出现的请求路径 == `agenerp/serve/app.py` 的 `EXPLAIN_PATH`
② 资产里出现的请求体键名集合 ⊆ `ALLOWED_BODY_KEYS`，且与 `CALLER_CLAIMED_KEYS` 交集为空
③ `window.agenerpDesk` 标记仍在（`Object.freeze` 那一格由 `test_desk_asset_route.py` 守）
④ 九个可分辨的已枚举码的字面量在资产里各出现过 —— 挡「只写了 200 分支」的半成品
⑤ 响应体不外泄的三格源码守卫：⑤a 渲染面 sink 零命中 · ⑤b `document.cookie` 零命中 ·
   ⑤c `JSON.stringify(` 命中 ≤ 1 次

⚠️ **这五件全是文本下限，不证运行时行为。**
本判据是离线、零浏览器、零 JS 运行时的 —— Python 读 `.js` 纯文本，
**可达性是控制流属性，这里唯一能实现的手段就是关键字匹配**，而那条路 roadmap 已记着走不通。
**「兜底态真的接得住」由活体判据（浏览器里真喂 418 / 真 abort）承担，这一份不承担、也不假装承担。**
"""

from __future__ import annotations

import re

from agenerp.serve.app import ALLOWED_BODY_KEYS, ASSET_DIR, ASSET_FILENAME, CALLER_CLAIMED_KEYS, EXPLAIN_PATH

ASSET = ASSET_DIR / ASSET_FILENAME

# 面板侧可分辨的九个码。**这不是第三个字面量** —— 服务端那八种来源 + 反代两种
# 折成九个码的推导写在 §7.23.3，两个 502 合并是**正确行为**（想分开只能嗅响应体，
# 那撞上「响应体不进渲染面」那条禁令）。九个码是**判据自己的口径**，不是从资产里抄来的。
DISTINGUISHABLE_CODES = ("400", "401", "403", "404", "405", "500", "502", "503", "504")

# ⑤a 的 sink 名单：把字符串塞进这些位置就等于把它当 HTML 解析。
# 建 DOM 只走 `textContent` / `createTextNode` —— 那是正路，不是变通。
HTML_SINKS = ("innerHTML", "outerHTML", "insertAdjacentHTML")


def _asset_text() -> str:
    return ASSET.read_text(encoding="utf-8")


def test_request_path_in_the_asset_is_the_one_the_service_serves():
    """① 资产里的请求路径与 `app.py` 的 `EXPLAIN_PATH` **各读一次再比**。

    失败意味着：面板打的是一个服务端不认的路径 —— 而那种失败在界面上
    和「服务挂了」长得一样（都是非 200），排查会先去看服务。
    """
    text = _asset_text()
    assert EXPLAIN_PATH in text, f"资产里找不到服务端的 `EXPLAIN_PATH`（{EXPLAIN_PATH}）"

    # 反向：资产里出现的 `/agenerp/...` 路径字面量**只许**是那一条与资产自己那条。
    found = set(re.findall(r'"(/agenerp/[A-Za-z0-9_.\-/]*)"', text))
    allowed = {EXPLAIN_PATH}
    assert found <= allowed, f"资产里出现了服务端没声明的 /agenerp 路径：{sorted(found - allowed)}"


def test_request_body_keys_are_a_subset_of_what_the_service_accepts():
    """② 请求体键名 ⊆ `ALLOWED_BODY_KEYS`，且与五个越权键的交集为空。

    **两个集合都从 `app.py` 读**，判据里不抄。

    这一格不是形式主义：服务端对 `fields`/`role`/`view`/`actions`/`user` 回 400，
    前端带上就是**必然 400**，而那种 400 在界面上和「问题不合法」长得一样。
    """
    text = _asset_text()
    body = _request_body_literal(text)
    keys = set(re.findall(r"(?:^|[\s{,])([A-Za-z_][A-Za-z0-9_]*)\s*:", body))
    assert keys, "没能从资产里认出请求体的键 —— 请求体的拼法变了，先改判据的取法再往下"
    assert keys <= set(ALLOWED_BODY_KEYS), (
        f"请求体里有服务端不收的键：{sorted(keys - set(ALLOWED_BODY_KEYS))}"
    )
    assert not (keys & set(CALLER_CLAIMED_KEYS)), (
        f"请求体里出现了越权键：{sorted(keys & set(CALLER_CLAIMED_KEYS))}"
    )

    # `doctype` / `name` 是**成对**的（`app.py` 的 `parse_request` 逐字：同时给或同时不给）。
    paired = {"doctype", "name"}
    assert not (keys & paired), (
        "`doctype` / `name` 不该出现在请求体字面量里 —— 它们是有上下文时才挂上去的，"
        "写死在字面量里就等于**无上下文时也会带**，服务端一律 400"
    )
    assert 'body.doctype' in text and 'body.name' in text, (
        "找不到把 `doctype` / `name` 挂上去的那两行 —— 上下文根本没被带进请求"
    )


def _request_body_literal(text: str) -> str:
    """取 `var body = { … };` 那一段。取不到就让判据红在这里，不静默放行。"""
    match = re.search(r"var body = \{(.*?)\};", text, re.S)
    assert match, "资产里找不到 `var body = { … };` —— 请求体的拼法变了"
    return match.group(1)


def test_the_window_marker_is_still_there():
    """③ `window.agenerpDesk` 标记仍在。

    ⚠️ **`Object.freeze` 那一格由 `test_desk_asset_route.py:167` 守，这里不重复**
    —— 同一件事两处断言，改的时候只会改一处。
    """
    text = _asset_text()
    assert "agenerpDesk" in text, "资产不再把标记挂到 window 上"
    assert 'Object.defineProperty(window, "agenerpDesk"' in text, (
        "标记不再是用 `Object.defineProperty` 挂的 —— 别的脚本改得动它了"
    )


def test_every_distinguishable_status_code_appears_in_the_asset():
    """④ 九个可分辨的已枚举码各出现过 —— 挡「只写了 200 分支」的半成品。

    ⚠️ **这一格不证明任何分支可达。** 它是**文本下限**：码的字面量都不在，
    那些态一定没写；都在，也**不代表**它们各自渲染得出东西。
    「渲染得出、且互不相同」那一半只有真浏览器判得了。
    """
    text = _asset_text()
    missing = [code for code in DISTINGUISHABLE_CODES if code not in text]
    assert not missing, f"资产里没有这些状态码的字面量：{missing}"


def test_the_fallback_state_is_present_by_name():
    """④b 兜底态在源码里有名字 —— 挡「把兜底顺手删了」这个最粗的形态。

    ⚠️ 同样是文本下限：**有这个函数名不等于它接得住 418**。
    那一格由活体判据真喂一个未枚举的码来判。
    """
    text = _asset_text()
    assert "renderFallback" in text, "兜底态的函数没了 —— 未枚举的码会掉进空白"
    assert "renderTransportFailure" in text, "网络层失败的态没了 —— `fetch` 抛出时面板会空着"


def test_the_asset_never_pours_the_response_body_into_the_dom():
    """⑤ 响应体不外泄，三格，全是纯文本判定。

    **理由两条，都不依赖任何 CI 现状**（§7.23.4）：
    (i) `sid` 是 `HttpOnly`，其存在意义就是不进 JS 可读面、更不进 DOM ——
        把整份响应铺进 DOM 等于**自己造一个绕过 `HttpOnly` 的显示面**；
    (ii) **真 nginx 502/504 回默认 HTML 不回 JSON**，任何「把响应体当结构化数据铺开」
        的写法在真 502 上都会抛，正好落进「失败形态渲染成空白」。

    ⚠️ **`JSON.stringify(` 不是零命中，也不该是**：`app.py` 的 `parse_request()` 逐字
    `json.loads(raw.decode("utf-8"))` ⇒ 请求体必须是 JSON，资产必然要 `stringify` 一次来拼它。
    **1 次正常；2 次起必有一次落在渲染面** —— 而 ⑤a 只挡 `innerHTML` 一族，
    挡不住 `el.textContent = JSON.stringify(resp)`，那同样是把整份响应铺进 DOM。

    ⚠️ **`≤ 1` 是下限不是等价物**：它挡不住逐字段拼接出来的等价泄漏，
    那一半由活体判据的「每一态只含该码字面量 + 已知键」承担。
    """
    text = _asset_text()

    for sink in HTML_SINKS:
        assert sink not in text, (
            f"⑤a 资产里出现了 `{sink}` —— 建 DOM 只许走 `textContent` / `createTextNode`"
        )

    assert "document.cookie" not in text, "⑤b 资产读了 `document.cookie`"

    hits = text.count("JSON.stringify(")
    assert hits <= 1, (
        f"⑤c `JSON.stringify(` 命中 {hits} 次（上限 1）—— 第 2 次起必有一次落在渲染面。"
        "拼请求体那一次是正常的，渲染面上一次都不许有"
    )


def test_rendering_only_reads_the_four_known_keys():
    """⑤ 的正面一半：渲染只取 `user` / `answer` / `accepted` / `cost`。

    取法是「有一处集中的读取点，且它只读这四个键」——
    这样加第五个键时判据会红，而不是悄悄多渲染一格出来。
    """
    text = _asset_text()
    match = re.search(r"function readKnownKeys\(payload\) \{(.*?)\n\t\}", text, re.S)
    assert match, "找不到 `readKnownKeys` —— 响应体的读取点散掉了，这条判据失去着力点"
    body = match.group(1)
    read = set(re.findall(r"payload\.([A-Za-z_][A-Za-z0-9_]*)", body))
    assert read == {"user", "answer", "accepted", "cost"}, (
        f"`readKnownKeys` 读的键集合是 {sorted(read)}，与 §1.3 那四个已知键不一致"
    )
