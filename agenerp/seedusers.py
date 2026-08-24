"""受限身份装载器 —— 在活站点上建一个**只读少数几个 DocType** 的「车间工人」。

**为什么必须有它**：`permission.scope` 的判别力在只有 Administrator 的站点上验不出来。
Administrator 对什么都有权限，所有探测都回 `true`，于是
**一个永远返回 `true` 的假实现与正确实现长得一模一样**
（`docs/masterplan/STATE.md` §3 2026-08-24T03:18Z 那条 `[open]`，CP9 继承项①的形状）。
本模块建的这个身份，就是那条判据的**真反例**来源。

**为什么由代码建、不由手工点**：CI 的 live job 每次都是全新栈，手工在本机站点上点出来的
用户在那里不存在，合规判据会因此不可复现。形态与 `agenerp/seedsite.py` 一致：
`SiteClient.ensure_doc` 先查后建、只建不改，**第二跑的判据是「新建 0」**，不是「没报错」。

**口令不进代码、不进仓库**：从 `AGENERP_WORKER_PASSWORD` 读，缺了就指名报错
（`agenerp/site.py` 模块头第 3 条：产品代码不内置口令默认值）。

**回滚**：删掉这个用户即可。本模块不写任何业务数据。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Any

from agenerp.site import SiteClient, SiteError, client_from_env, credential_from_env

WORKER_PASSWORD_ENV = "AGENERP_WORKER_PASSWORD"

WORKER_ROLE = "车间工人"
WORKER_EMAIL = "worker@hrd.example.com"
WORKER_FIRST_NAME = "车间工人"

# 只读这三个 —— 与 Spike 01 探针 3 的「仅可读 3 个 DocType」同一形态。
# **刻意不给 `DocType` 的读权限**：stock Frappe 只把它给 System Manager / Administrator，
# 且对它建 `Custom DocPerm` 不生效（2026-08-24 实测）。给工人发 System Manager 能让
# 发现式候选集跑通，但那等于把「受限」这件事取消掉，判别力也就没了。
# 受限身份下的候选集因此由调用方给（`permission.scope` 的 `doctypes` 参数）。
READABLE_DOCTYPES: tuple[str, ...] = ("Work Order", "Stock Entry", "Item")

CUSTOM_DOCPERM = "Custom DocPerm"


@dataclass
class UserLoadReport:
    """一次受限身份装载的结果。`created` / `existing` 按 DocType 计数，口径与 `seedsite` 同源。"""

    created: dict[str, int] = field(default_factory=dict)
    existing: dict[str, int] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def record(self, doctype: str, was_created: bool) -> None:
        if doctype not in self.order:
            self.order.append(doctype)
            self.created.setdefault(doctype, 0)
            self.existing.setdefault(doctype, 0)
        bucket = self.created if was_created else self.existing
        bucket[doctype] += 1

    @property
    def total_created(self) -> int:
        return sum(self.created.values())

    def lines(self) -> list[str]:
        out = [
            f"{doctype}：新建 {self.created[doctype]} / 已存在 {self.existing[doctype]}"
            for doctype in self.order
        ]
        out.append(
            f"合计：新建 {self.total_created} / 已存在 {sum(self.existing.values())}"
        )
        return out


def worker_password() -> str:
    """口令从环境读，且**读取动作在 `agenerp.site` 里**：本模块不碰环境变量表。

    这不只是分层洁癖 —— `tests/unit/test_seed_deterministic.py` 把 `agenerp/seed*.py`
    整片当「生成路径」扫，环境读取出现在这里就是红。凭据读取本来就归 §11.7 那一层。
    """
    return credential_from_env(WORKER_PASSWORD_ENV)


def _role_step() -> tuple[str, dict[str, Any], dict[str, Any]]:
    return (
        "Role",
        {"name": WORKER_ROLE},
        {"doctype": "Role", "role_name": WORKER_ROLE, "desk_access": 1},
    )


def _user_step(password: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    return (
        "User",
        {"name": WORKER_EMAIL},
        {
            "doctype": "User",
            "email": WORKER_EMAIL,
            "first_name": WORKER_FIRST_NAME,
            "user_type": "System User",
            "enabled": 1,
            "send_welcome_email": 0,
            "new_password": password,
            "roles": [{"role": WORKER_ROLE}],
        },
    )


def _perm_steps() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    return [
        (
            CUSTOM_DOCPERM,
            {"parent": doctype, "role": WORKER_ROLE, "permlevel": 0},
            {
                "doctype": CUSTOM_DOCPERM,
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": WORKER_ROLE,
                "permlevel": 0,
                "read": 1,
            },
        )
        for doctype in READABLE_DOCTYPES
    ]


def load_users(client: SiteClient) -> UserLoadReport:
    """按「角色 → 用户 → 逐个 DocType 的读权限」的顺序装载。**任一步抛就整段停**。

    顺序不可换：角色不存在时建用户会把 `roles` 子表静默丢掉，用户于是没有任何角色，
    而返回的却是一份看着正常的用户文档。
    """
    password = worker_password()
    report = UserLoadReport()
    for doctype, key, payload in [_role_step(), _user_step(password), *_perm_steps()]:
        _, created = client.ensure_doc(doctype, key, payload)
        report.record(doctype, created)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m agenerp.seedusers",
        description="在活站点上建一个只读少数几个 DocType 的受限身份（幂等）",
    )
    parser.add_argument("--load-users", action="store_true", help="装载受限身份（只建不改）")
    parser.add_argument("--site", default="", help="站点名（必填，例如 frontend）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.load_users:
        print("需要 --load-users", file=sys.stderr)
        return 2
    if not args.site:
        print("需要 --site <站点名>：不猜站点，产品代码不内置默认站点", file=sys.stderr)
        return 2
    try:
        report = load_users(client_from_env(args.site))
    except SiteError as exc:  # 失败即停：不留半装状态，不吞错误原文
        print(f"失败，已停在出错那一步：{exc}", file=sys.stderr)
        return 1
    for line in report.lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
