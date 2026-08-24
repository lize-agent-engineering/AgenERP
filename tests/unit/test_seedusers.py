"""非门禁测试 · 钉死受限身份装载器的纯逻辑半（`agenerp/seedusers.py`）。

**不连站点**：装载顺序、载荷字段、幂等计数、缺口令即停，四件事都能在假传输上判死。
活站点那一半由 CLI 实跑负责（退出码 + 第二跑「新建 0」），两者不互相冒充——
本文件通过**不等于**这个身份在真站点上真的读不到东西。
"""

import json

import pytest

from agenerp import seedusers
from agenerp.site import SiteClient, SiteError, SiteResponse


class FakeSite:
    """记住建过什么，按 `filters` 答存在性。**不实现 upsert**——`ensure_doc` 只建不改。"""

    def __init__(self) -> None:
        self.docs: dict[tuple[str, str], dict] = {}
        self.requests: list = []

    def __call__(self, request):
        from urllib.parse import parse_qs, unquote, urlparse

        self.requests.append(request)
        doctype = unquote(request.url.split("/api/resource/")[1].split("?")[0])
        if request.method == "GET":
            filters = json.loads(parse_qs(urlparse(unquote(request.url)).query)["filters"][0])
            hit = [
                doc
                for (dt, _), doc in self.docs.items()
                if dt == doctype and all(str(doc.get(f)) == str(v) for f, _, v in filters)
            ]
            return SiteResponse(200, json.dumps({"data": hit[:1]}))
        payload = json.loads(request.body)
        doc = {**payload, "name": self._derive(doctype, payload)}
        self.docs[(doctype, doc["name"])] = doc
        return SiteResponse(200, json.dumps({"data": doc}))

    def _derive(self, doctype: str, payload: dict) -> str:
        """照抄 2026-08-24 实测的站点命名规则，**不照抄载荷里的 `name`**。

        `Role` 走 `field:role_name`、`User` 走 `field:email`（两者实测回的就是这个值），
        `Custom DocPerm` 由站点生成哈希名（实测形如 `cnslq189jc`）——
        它的幂等键因此不能是 `name`，只能是 `(parent, role, permlevel)`。
        """
        if doctype == "Role":
            return payload["role_name"]
        if doctype == "User":
            return payload["email"]
        return f"{doctype.lower().replace(' ', '')}-{len(self.docs):04d}"

    @property
    def posts(self):
        return [r for r in self.requests if r.method == "POST"]


def _client(transport):
    return SiteClient(
        "frontend", base_url="http://127.0.0.1:18080", api_key="k", api_secret="s",
        transport=transport,
    )


def test_missing_password_stops_before_any_request(monkeypatch):
    """缺口令即停，且**指名缺哪个环境变量**——产品代码不内置口令默认值。"""
    monkeypatch.delenv(seedusers.WORKER_PASSWORD_ENV, raising=False)
    site = FakeSite()

    with pytest.raises(SiteError) as excinfo:
        seedusers.load_users(_client(site))

    assert seedusers.WORKER_PASSWORD_ENV in str(excinfo.value)
    assert site.requests == []


def test_role_is_created_before_the_user(monkeypatch):
    """角色必须早于用户：角色不存在时建用户会把 `roles` 子表静默丢掉，返回的却是一份正常文档。"""
    monkeypatch.setenv(seedusers.WORKER_PASSWORD_ENV, "x")
    site = FakeSite()

    seedusers.load_users(_client(site))

    order = [r.url.split("/api/resource/")[1] for r in site.posts]
    assert order[0].startswith("Role")
    assert order[1].startswith("User")


def test_first_run_creates_and_second_run_creates_nothing(monkeypatch):
    """幂等的判据是**「新建 0」**，不是「没报错」。第二跑必须一个 POST 都不发。"""
    monkeypatch.setenv(seedusers.WORKER_PASSWORD_ENV, "x")
    site = FakeSite()

    first = seedusers.load_users(_client(site))
    posts_after_first = len(site.posts)
    second = seedusers.load_users(_client(site))

    assert first.total_created == 2 + len(seedusers.READABLE_DOCTYPES)
    assert second.total_created == 0
    assert len(site.posts) == posts_after_first


def test_the_user_gets_read_on_exactly_the_declared_doctypes(monkeypatch):
    """只读那几个 DocType。多给一个就少一个反例，判别力就少一分。"""
    monkeypatch.setenv(seedusers.WORKER_PASSWORD_ENV, "x")
    site = FakeSite()

    seedusers.load_users(_client(site))

    perms = [doc for (dt, _), doc in site.docs.items() if dt == seedusers.CUSTOM_DOCPERM]
    assert {perm["parent"] for perm in perms} == set(seedusers.READABLE_DOCTYPES)
    assert all(perm["read"] == 1 and perm["role"] == seedusers.WORKER_ROLE for perm in perms)
    assert all(perm.get("write") is None for perm in perms)


def test_password_never_appears_in_the_report(monkeypatch):
    """报告是要进日志的。口令不进报告——不进 git 只是最低要求，不进日志才是。"""
    monkeypatch.setenv(seedusers.WORKER_PASSWORD_ENV, "Sup3rSecret")
    site = FakeSite()

    report = seedusers.load_users(_client(site))

    assert "Sup3rSecret" not in "\n".join(report.lines())
