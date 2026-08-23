"""非门禁测试 · 钉死站点只读传输的行为（`agenerp/site.py`）。

**不连真站点，也不起本地 `http.server`**：本机端口冲突已经是实测事实
（8080 被另一套常驻栈占着），在 `GATE_VERIFY` 与 CI 的 `gates-l1` 里再绑一个端口
是自找的不稳定源。传输是注入进来的假件，请求对象本身就是可断言的值。

唯一的例外是「连不上」那条：它必须走真的 `UrllibTransport`，因为假传输**证明不了**
真传输会把 `URLError` 翻成 `SiteError`。那条用一个刚释放的端口构造 connection refused，
不留下监听。
"""

import json
import socket

import pytest

from agenerp import site as site_mod
from agenerp.contracts import WRITE_VERBS
from agenerp.site import (
    ADMIN_PASSWORD_ENV,
    API_KEY_ENV,
    API_SECRET_ENV,
    CUSTOM_FIELD_DOCTYPE,
    SITE_ENV,
    SiteClient,
    SiteError,
    SiteResponse,
    UrllibTransport,
    client_from_env,
    custom_field_name,
    encode_path,
)

# 每加宽一次写面就留一次痕 —— 这个列表是那道痕。**只登记，不取消判据**。
#
# `SiteClient.delete_custom_field`（2026-08-21，plan `2026-08-21-1922-3` 差集 apply 的 B 半）：
#   差集 apply 要在站点上**真的删掉** Custom Field，否则 Frappe 那条纯 upsert 路径下
#   「从包里删掉字段 → apply → 字段仍在」，`git revert` 撤不掉定制（承重条款
#   `tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`）。
#   写面被**刻意限死在 Custom Field 一种文档上**：不提供「删任意 DocType 文档」的通用方法，
#   那等于把业务数据交出去。
#
# `SiteClient.create_doc` / `SiteClient.ensure_doc`（2026-08-22，plan `2026-08-22-2107-1` 种子主数据装载）：
#   种子数据的 B 半要把公司 / 科目 / 仓库 / 物料 / BOM 装进活站点，`agenerp/seedsite.py` 是唯一调用方。
#   ⚠️ **这一次写面从「结构定制」扩到了「业务主数据」**，`agenerp/site.py` 模块头第 4 条
#   与 `docs/architecture/module-boundaries.md` §11.7 已同步改准，不是默默扩的。
#   ⚠️ `ensure_doc` 的名字里**一个 `WRITE_VERB` 都没有**（`create`/`write`/`submit`/`cancel`/`delete`/`amend`），
#   下面那条守卫**扫不到它**——它是**主动登记**的。只登记守卫扫得到的，等于让守卫替人决定该留什么痕。
#   `find_one` 是纯读，不登记。
WRITE_METHOD_ALLOWLIST: tuple[str, ...] = (
    "SiteClient.delete_custom_field",
    "SiteClient.create_doc",
    "SiteClient.ensure_doc",
    "SiteClient.submit_doc",
)

# 名字里**不含任何 `WRITE_VERB`**、因而下面那道扫描守卫**看不见**的写方法。
# 它们是**主动登记**的，靠 `test_deliberately_registered_write_methods_stay_registered`
# 上锁 —— 否则「把 `ensure_doc` 从白名单里删掉」这个动作会**静默通过**，
# 「每加一个写方法就要付一次留痕」这条规矩就只对名字取得巧的方法生效。
NON_VERB_WRITE_METHODS: tuple[str, ...] = ("SiteClient.ensure_doc",)

ALL_ENV = (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV, "AGENERP_ADMIN_USER",
           "AGENERP_SITE_URL", "AGENERP_HTTP_PORT")


class FakeTransport:
    """记下每一次请求，按预设答复。默认答一个空的 Frappe 列表载荷。"""

    def __init__(self, responses=None):
        self.requests = []
        self._responses = list(responses or [])

    def __call__(self, request):
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return SiteResponse(200, json.dumps({"data": []}))

    @property
    def last(self):
        return self.requests[-1]


@pytest.fixture
def clean_env(monkeypatch):
    for name in ALL_ENV:
        monkeypatch.delenv(name, raising=False)


def _client(transport, **kwargs):
    kwargs.setdefault("base_url", "http://127.0.0.1:18080")
    kwargs.setdefault("admin_password", "secret")
    return SiteClient("frontend", transport=transport, **kwargs)


def test_non_2xx_raises_instead_of_returning_empty():
    """非 2xx 必须抛。返回空结果会让「未改动 → diff 为空」在站点报错时照样绿。"""
    transport = FakeTransport([SiteResponse(500, "boom")])

    with pytest.raises(SiteError) as excinfo:
        _client(transport, api_key="k", api_secret="s").get("/api/resource/Custom Field")

    assert "500" in str(excinfo.value)


def test_unauthorized_login_raises():
    """认证失败是站点侧失败，不是「站点上没有东西」。"""
    transport = FakeTransport([SiteResponse(401, '{"message":"Invalid login"}')])

    with pytest.raises(SiteError) as excinfo:
        _client(transport).get("/api/resource/Custom Field")

    assert "401" in str(excinfo.value)


def test_non_json_payload_raises():
    """载荷不是 JSON（例如被反代喂了一页 HTML）也必须抛，不许当成空。"""
    transport = FakeTransport([
        SiteResponse(200, json.dumps({"message": "Logged In"})),
        SiteResponse(200, "<html>login page</html>"),
    ])

    with pytest.raises(SiteError) as excinfo:
        _client(transport).get("/api/resource/Custom Field")

    assert "JSON" in str(excinfo.value)


def test_unreachable_site_raises_site_error():
    """连不上必须抛 `SiteError` —— 这条走真传输，假件证明不了 URLError 被翻译了。"""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # 端口立即释放：随后的连接必然被拒，且不留监听

    client = SiteClient(
        "frontend", base_url=f"http://127.0.0.1:{port}",
        api_key="k", api_secret="s", transport=UrllibTransport(timeout=5),
    )

    with pytest.raises(SiteError):
        client.get("/api/method/ping")


def test_missing_credentials_names_the_variables(clean_env):
    """缺凭据的报错必须指名缺哪个环境变量，否则人只知道「失败了」。"""
    with pytest.raises(SiteError) as excinfo:
        client_from_env("frontend")

    message = str(excinfo.value)
    for name in (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV):
        assert name in message, f"报错没指名 {name}：{message}"


def test_half_a_token_pair_is_an_error_not_a_silent_fallback(clean_env, monkeypatch):
    """只给 key 不给 secret = 配错。静默回退会让「token 没生效」完全看不见。"""
    monkeypatch.setenv(API_KEY_ENV, "k")
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, "admin")

    with pytest.raises(SiteError) as excinfo:
        client_from_env("frontend")

    assert API_SECRET_ENV in str(excinfo.value)


def test_no_builtin_password_default(clean_env, monkeypatch):
    """产品代码不内置口令默认值 —— conftest 里那个 `admin` 是测试脚手架，不是产品口径。"""
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, "")

    with pytest.raises(SiteError):
        client_from_env("frontend")


def test_token_credentials_skip_the_login_roundtrip(clean_env, monkeypatch):
    """配了 token 就不该再发登录请求（登录端点有速率限制，且会把口令带进每次运行）。"""
    monkeypatch.setenv(API_KEY_ENV, "k")
    monkeypatch.setenv(API_SECRET_ENV, "s")
    transport = FakeTransport()

    client_from_env("frontend", transport=transport).get("/api/method/ping")

    assert len(transport.requests) == 1, "token 认证下不该有登录往返"
    assert transport.last.headers["Authorization"] == "token k:s"


def test_session_login_is_the_fallback_and_happens_once():
    """没有 token 时回退会话登录，且只登一次 —— 每次调用都登录会撞上速率限制。"""
    transport = FakeTransport([
        SiteResponse(200, json.dumps({"message": "Logged In"})),
        SiteResponse(200, json.dumps({"data": []})),
        SiteResponse(200, json.dumps({"data": []})),
    ])
    client = _client(transport)

    client.get("/api/method/ping")
    client.get("/api/method/ping")

    methods = [r.method for r in transport.requests]
    assert methods == ["POST", "GET", "GET"], methods
    assert json.loads(transport.requests[0].body)["pwd"] == "secret"


def test_host_header_is_the_site_name():
    """gunicorn 按 Host 解析站点：打 127.0.0.1 会被当成一个叫 127.0.0.1 的站点而 404。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").get("/api/method/ping")

    assert transport.last.headers["Host"] == "frontend"


def test_path_is_url_encoded_keeping_slashes():
    """DocType 名带空格，不编码时 http.client 直接以 control characters 拒掉。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").get("/api/resource/Custom Field")

    url = transport.last.url
    assert "/api/resource/Custom%20Field" in url
    assert " " not in url


def test_list_resource_explicitly_disables_paging():
    """Frappe 的 `/api/resource` 默认只回 20 条。不显式关分页 = 一条静默截断的假绿。"""
    transport = FakeTransport()

    _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")

    url = transport.last.url
    assert f"{site_mod.PAGE_LENGTH_PARAM}={site_mod.UNLIMITED_PAGE_LENGTH}" in url
    assert f"{site_mod.FIELDS_PARAM}=" in url
    assert "%2A" in url or "*" in url, f"没显式要全部字段：{url}"


def test_list_resource_returns_every_row_the_site_gave():
    """25 条（超过默认页长 20）必须一条不少地带回来。"""
    rows = [{"dt": "Item", "fieldname": f"probe_{i}"} for i in range(25)]
    transport = FakeTransport([SiteResponse(200, json.dumps({"data": rows}))])

    got = _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")

    assert len(got) == 25


def test_list_resource_rejects_a_payload_without_data():
    """载荷形状不对时抛，不返回空列表 —— 空列表会被读成「站点上没有定制」。"""
    transport = FakeTransport([SiteResponse(200, json.dumps({"exc": "boom"}))])

    with pytest.raises(SiteError):
        _client(transport, api_key="k", api_secret="s").list_resource("Custom Field")


def _created(name, **extra):
    return SiteResponse(200, json.dumps({"data": {"name": name, **extra}}))


def _rows(*rows):
    return SiteResponse(200, json.dumps({"data": list(rows)}))


def test_create_doc_returns_the_document_the_site_built():
    """`name` 由站点说了算：实测站点对 Warehouse/Account/Item/BOM 不采纳显式 `name`。"""
    transport = FakeTransport([_created("XM 原料仓 - XM", warehouse_name="XM 原料仓")])

    doc = _client(transport, api_key="k", api_secret="s").create_doc(
        "Warehouse", {"warehouse_name": "XM 原料仓", "company": "XM 演示纺织有限公司"}
    )

    assert doc["name"] == "XM 原料仓 - XM"
    assert transport.last.method == "POST"
    assert "/api/resource/Warehouse" in transport.last.url
    assert json.loads(transport.last.body)["warehouse_name"] == "XM 原料仓"


def test_create_doc_raises_on_non_2xx_instead_of_pretending_it_exists():
    """409 DuplicateEntryError 不许被吞成「已经有了、算成功」——幂等靠先查后建，不靠吞异常。"""
    transport = FakeTransport([SiteResponse(409, '{"exc_type":"DuplicateEntryError"}')])

    with pytest.raises(SiteError) as excinfo:
        _client(transport, api_key="k", api_secret="s").create_doc("Item", {"item_code": "XM-LACE-1000"})

    assert "409" in str(excinfo.value)
    assert "DuplicateEntryError" in str(excinfo.value)


def test_create_doc_rejects_a_payload_without_a_data_object():
    """载荷形状不对时抛。回一个没有 data 的 200 就当建成功，等于凭空造一个假文档。"""
    transport = FakeTransport([SiteResponse(200, json.dumps({"exc": "boom"}))])

    with pytest.raises(SiteError):
        _client(transport, api_key="k", api_secret="s").create_doc("Item", {"item_code": "X"})


def test_find_one_returns_the_row_when_the_site_has_it():
    transport = FakeTransport([_rows({"name": "织造"})])

    got = _client(transport, api_key="k", api_secret="s").find_one("Operation", {"name": "织造"})

    assert got == {"name": "织造"}
    url = transport.last.url
    assert f"{site_mod.PAGE_LENGTH_PARAM}={site_mod.SINGLE_PAGE_LENGTH}" in url
    assert f"{site_mod.FILTERS_PARAM}=" in url


def test_find_one_returns_none_only_for_an_empty_result_set():
    """「查得到、但零行」是唯一的「不存在」。实测站点对未命中回 HTTP 200 `{"data": []}`。"""
    transport = FakeTransport([_rows()])

    assert _client(transport, api_key="k", api_secret="s").find_one("Operation", {"name": "没有"}) is None


@pytest.mark.parametrize("status", [401, 403, 500, 502])
def test_find_one_raises_on_any_non_2xx_and_never_reads_it_as_absent(status):
    """站点挂掉必须抛。判成「不存在」会让 `ensure_doc` 一路重复建 —— 最难发现的那种坏。"""
    transport = FakeTransport([SiteResponse(status, '{"exc_type":"PermissionError"}')])

    with pytest.raises(SiteError) as excinfo:
        _client(transport, api_key="k", api_secret="s").find_one("Operation", {"name": "织造"})

    assert str(status) in str(excinfo.value)


def test_find_one_rejects_a_payload_without_data():
    transport = FakeTransport([SiteResponse(200, json.dumps({"exc": "boom"}))])

    with pytest.raises(SiteError):
        _client(transport, api_key="k", api_secret="s").find_one("Operation", {"name": "织造"})


def test_ensure_doc_issues_zero_posts_when_the_document_already_exists():
    """幂等的判据是「第二跑零 POST」，不是「没报错」。"""
    transport = FakeTransport([_rows({"name": "织造", "workstation": "XM 织造机台"})])

    doc, created = _client(transport, api_key="k", api_secret="s").ensure_doc(
        "Operation", {"name": "织造"}, {"name": "织造"}
    )

    assert (doc["name"], created) == ("织造", False)
    assert [r.method for r in transport.requests] == ["GET"], [r.method for r in transport.requests]


def test_ensure_doc_posts_exactly_once_when_the_document_is_missing():
    transport = FakeTransport([_rows(), _created("织造")])

    doc, created = _client(transport, api_key="k", api_secret="s").ensure_doc(
        "Operation", {"name": "织造"}, {"name": "织造"}
    )

    assert (doc["name"], created) == ("织造", True)
    assert [r.method for r in transport.requests] == ["GET", "POST"]


def test_ensure_doc_does_not_update_an_existing_document():
    """`ensure_doc` 只建不改：站点上字段不对的对象**不会被悄悄改写**（代价写在 §12.9）。"""
    transport = FakeTransport([_rows({"name": "织造", "workstation": "旧工位"})])

    doc, created = _client(transport, api_key="k", api_secret="s").ensure_doc(
        "Operation", {"name": "织造"}, {"name": "织造", "workstation": "新工位"}
    )

    assert doc["workstation"] == "旧工位"
    assert created is False
    assert [r.method for r in transport.requests] == ["GET"]


def test_write_methods_report_missing_credentials_by_name(clean_env):
    """认证未就绪时，写路径的报错必须和读路径一样指名缺哪个环境变量。"""
    client = SiteClient("frontend", base_url="http://127.0.0.1:18080", transport=FakeTransport())

    for call in (
        lambda: client.create_doc("Item", {"item_code": "X"}),
        lambda: client.find_one("Item", {"name": "X"}),
        lambda: client.ensure_doc("Item", {"name": "X"}, {"item_code": "X"}),
    ):
        with pytest.raises(SiteError) as excinfo:
            call()
        message = str(excinfo.value)
        for name in (API_KEY_ENV, API_SECRET_ENV, ADMIN_PASSWORD_ENV):
            assert name in message, f"报错没指名 {name}：{message}"


def _public_methods() -> list[str]:
    """`agenerp.site` 对外暴露的全部公开可调用名（模块级函数 + 公开类的公开方法）。"""
    names: list[str] = []
    for attr in dir(site_mod):
        if attr.startswith("_"):
            continue
        obj = getattr(site_mod, attr)
        if callable(obj) and getattr(obj, "__module__", "") == site_mod.__name__:
            names.append(attr)
            if isinstance(obj, type):
                names.extend(f"{attr}.{m}" for m in dir(obj) if not m.startswith("_"))
    return names


def test_site_module_exposes_no_unlisted_write_method():
    """只读不变量：公开方法名里出现写动词的，必须在**显式白名单**里（本 plan 白名单为空）。

    写成「一个写动词都不许出现」的话，第 3 顺位在同一个模块上加 `delete_custom_field`
    会被一条已关闭 plan 的判据当场打红 —— 那时只剩「动别人的判据」和「卡住」两条路。
    白名单让它按**收窄**演进：加一个写方法就要付一次 diff 和一次留痕。
    """
    offenders = [
        name for name in _public_methods()
        if any(verb in name.split(".")[-1].lower() for verb in WRITE_VERBS)
        and name not in WRITE_METHOD_ALLOWLIST
    ]

    assert offenders == [], f"未登记的写方法：{offenders}；白名单={WRITE_METHOD_ALLOWLIST}"


def test_deliberately_registered_write_methods_stay_registered():
    """扫描守卫的补丁：名字里没有 verb 的写方法，删掉登记也必须转红。

    2026-08-22 实测过：把 `SiteClient.ensure_doc` 从白名单删掉，
    `test_site_module_exposes_no_unlisted_write_method` **一声不响地照样绿**——
    因为 `ensure_doc` 里一个 `WRITE_VERB` 都没有，扫描器根本看不见它。
    没有这一条，「主动登记」就只是一句自觉，不是判据。
    """
    missing = [name for name in NON_VERB_WRITE_METHODS if name not in WRITE_METHOD_ALLOWLIST]

    assert missing == [], f"写方法被从白名单里删掉了：{missing}；白名单={WRITE_METHOD_ALLOWLIST}"


def test_every_allowlisted_name_resolves_to_a_real_method():
    """白名单不许留陈迹：登记的每个名字都必须在模块上真的存在。"""
    for entry in WRITE_METHOD_ALLOWLIST:
        cls_name, method = entry.split(".")
        assert callable(getattr(getattr(site_mod, cls_name), method, None)), f"{entry} 不存在"


def test_the_allowlist_assertion_actually_has_teeth():
    """白名单断言不能是空转的：给它喂一个写方法名，它必须判成违规。"""
    verb = WRITE_VERBS[0]
    fabricated = f"SiteClient.{verb}_custom_field"

    assert any(v in fabricated.split(".")[-1].lower() for v in WRITE_VERBS)
    assert fabricated not in WRITE_METHOD_ALLOWLIST


def test_submit_doc_pushes_docstatus_to_one_and_returns_what_the_site_said():
    """2026-08-22 活站点实测：`PUT /api/resource/<dt>/<name>` 带 `{"docstatus": 1}` 即是提交。"""
    transport = FakeTransport([SiteResponse(200, json.dumps(
        {"data": {"name": "MAT-STE-2026-00001", "docstatus": 1}}))])
    client = SiteClient("frontend", base_url="http://s", api_key="k", api_secret="s",
                        transport=transport)

    doc = client.submit_doc("Stock Entry", "MAT-STE-2026-00001")

    assert doc["docstatus"] == 1
    assert transport.last.method == "PUT"
    assert transport.last.url.endswith("/api/resource/Stock%20Entry/MAT-STE-2026-00001")
    assert json.loads(transport.last.body) == {"docstatus": 1}


def test_submit_doc_raises_when_the_site_answers_2xx_but_the_doc_is_still_a_draft():
    """200 但没提交上去，与提交成功长得一模一样 —— 那正是「不伪装成功」要挡的形状。"""
    transport = FakeTransport([SiteResponse(200, json.dumps(
        {"data": {"name": "MAT-STE-2026-00001", "docstatus": 0}}))])
    client = SiteClient("frontend", base_url="http://s", api_key="k", api_secret="s",
                        transport=transport)

    with pytest.raises(SiteError, match="没被提交"):
        client.submit_doc("Stock Entry", "MAT-STE-2026-00001")


@pytest.mark.parametrize("status", [400, 401, 403, 417, 500])
def test_submit_doc_never_swallows_a_non_2xx(status):
    transport = FakeTransport([SiteResponse(status, '{"exc_type":"ValidationError"}')])
    client = SiteClient("frontend", base_url="http://s", api_key="k", api_secret="s",
                        transport=transport)

    with pytest.raises(SiteError):
        client.submit_doc("Stock Entry", "MAT-STE-2026-00001")


# ---------------------------------------------------------------------------
# 写方法的行为判据（plan `2026-08-23-1056-1` Phase 1）
#
# 缺口的准确表述：`delete_custom_field` 被 L2 门禁
# `tests/gates/test_customization_roundtrip_delete.py::test_removing_from_pack_actually_deletes_on_site`
# 真正走过，但那道门禁要 docker + 活站点，**默认判定面（`pytest tests/unit`）复跑不到它**。
# 实测确认过：把该方法整个函数体换成 `return None`，`tests/unit` + `tests/contracts`
# 471 条全绿 —— 破坏性写变成 no-op 而当轮自证为绿。下面这几条补的正是那一层。
# ---------------------------------------------------------------------------


def test_delete_custom_field_issues_exactly_one_delete_request():
    """删除必须**真的发出去**。函数体被掏空成 no-op 时，只有「请求条数」看得见。

    断言落在**编码后**的 URL 上：`agenerp/site.py:350` 是 `base_url + encode_path(path)`，
    `Custom Field` 的空格在那一步变成 `%20`，写未编码字面量会与真发出的请求对不上。
    """
    transport = FakeTransport([SiteResponse(202, json.dumps({"data": "ok"}))])

    _client(transport, api_key="k", api_secret="s").delete_custom_field("Item", "agenerp_x")

    assert len(transport.requests) == 1, [(r.method, r.url) for r in transport.requests]
    assert transport.last.method == "DELETE"
    assert transport.last.url.endswith("/api/resource/Custom%20Field/Item-agenerp_x"), \
        transport.last.url


def test_delete_custom_field_raises_when_the_field_is_not_there():
    """「要删的东西不在」判为失败，不静默吞掉 —— 实测站点回 404 `DoesNotExistError`。

    吞掉它会让「包里删了字段但站点上从来没建过」与「删成功了」长得一模一样。
    """
    transport = FakeTransport([SiteResponse(404, '{"exc_type":"DoesNotExistError"}')])

    with pytest.raises(SiteError) as excinfo:
        _client(transport, api_key="k", api_secret="s").delete_custom_field("Item", "agenerp_x")

    assert "404" in str(excinfo.value)


def test_custom_field_name_is_doctype_then_fieldname():
    """名字形如 `Item-agenerp_x`（2026-08-21 活站点实测的 `data.name`）。顺序对调 = 删到不存在的 name。"""
    assert custom_field_name("Item", "agenerp_x") == "Item-agenerp_x"


def test_delete_custom_field_targets_the_name_custom_field_name_computes():
    """删除路径打的 name 必须与 `custom_field_name` **同源**，不是碰巧长得一样。

    期望值用函数本身求值、不手抄字符串：手抄的话，两处一起改错时这条判据会跟着一起错。
    形状本身由 `test_custom_field_name_is_doctype_then_fieldname` 单独钉死。
    """
    transport = FakeTransport([SiteResponse(202, json.dumps({"data": "ok"}))])

    _client(transport, api_key="k", api_secret="s").delete_custom_field("Item", "agenerp_x")

    expected = encode_path(
        f"/api/resource/{CUSTOM_FIELD_DOCTYPE}/{custom_field_name('Item', 'agenerp_x')}"
    )
    assert transport.last.url.endswith(expected), (transport.last.url, expected)


@pytest.mark.parametrize("body", ['{"data": "ok"}', "{}", "[]"])
def test_submit_doc_rejects_a_response_without_a_data_object(body):
    """`data` 不是对象时抛。回 `{}` 当成提交成功，等于凭空造一份没提交的单据。"""
    transport = FakeTransport([SiteResponse(200, body)])
    client = SiteClient("frontend", base_url="http://s", api_key="k", api_secret="s",
                        transport=transport)

    with pytest.raises(SiteError, match="缺少 data 对象"):
        client.submit_doc("Stock Entry", "MAT-STE-2026-00001")


def test_empty_site_name_raises_and_names_the_env_var():
    """空站点名必须当场炸，且指名 `AGENERP_SITE` —— 放过去会把空 Host 头带进每次请求。"""
    with pytest.raises(SiteError) as excinfo:
        SiteClient("", base_url="http://s", api_key="k", api_secret="s")

    assert SITE_ENV in str(excinfo.value), str(excinfo.value)
