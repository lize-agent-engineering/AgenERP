"""S3 **第四段** · 视图定义同步到另一个站点并**在那边存在**。

## 它补的是哪一句

`00-GOALS.md` §2 的 **S3** 最后一段：「…… → **同步到另一站点生效**」。

前三段由 `verify_view_gitops.py` 跑（改 → diff → revert，全在 git 上）。
第四段要求视图定义**落到目标站点自己的库里** —— 那正是 P2.0 判的
「视图产物落 AgenERP 自有表」那一半（`agenerp/dsl/store.py`）。

## 真相源与产物的方向

```
agenerp/dsl/views/*.json   ← 真相源（git）
        │  publish_views
        ▼
每个站点的 `AgenERP View` 表  ← 产物，一站一份
```

⚠️ **本判据不打服务端** —— `gitops.test` 上没有 serve 进程。
它验的是「**定义到了那个站点、读回来与 git 里那份逐字段相同**」，
**不是**「那个站点的浏览器里画出来了」。这个边界写在这里，不许被读成后者。

## 迁站点会带着依赖走

`AgenERP View` 的权限行引用角色 `车间工人`。目标站点上没有它时，
Frappe 回 `LinkValidationError` —— **这不是 bug，是迁站点的真实形状**。
本文件把「补齐前置依赖」做成**显式的一步**，不藏在建表里。
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agenerp.dsl.roles import WORKER_DAILY_VIEWS  # noqa: E402
from agenerp.dsl.store import DECLARATION, VIEW_DOCTYPE, ensure_table, publish_views, read_view  # noqa: E402
from agenerp.site import SiteError, client_from_env  # noqa: E402

HOME_SITE = "frontend"
TARGET_SITE = "gitops.test"
PROBE_VIEW = WORKER_DAILY_VIEWS[0]


class StepFailed(RuntimeError):
    """某一步没达成。消息要能看出**哪一步、期望什么、实际什么**。"""


def declared_roles() -> list[str]:
    payload = json.loads(DECLARATION.read_text(encoding="utf-8"))
    return sorted({row["role"] for row in payload.get("permissions", [])})


def ensure_roles(client, site: str) -> list[str]:
    """把声明里引用到、而目标站点上没有的角色补上。**显式一步，逐条打印。**"""
    have = {row["name"] for row in client.list_resource("Role", ("name",))}
    made = []
    for role in declared_roles():
        if role not in have:
            client.create_doc("Role", {"role_name": role, "desk_access": 1})
            made.append(role)
    return made


def has_view(client, name: str) -> bool:
    """那个站点上有没有这个视图。⚠️ **查不到与查不动要分开**。"""
    from agenerp.dsl.store import ViewStoreError

    try:
        read_view(client, name)
    except ViewStoreError as exc:
        cause = str(exc)
        if "404" in cause or "DoesNotExist" in cause or "not found" in cause.lower():
            return False
        raise
    return True


def step(number: int, title: str) -> None:
    print(f"\n[{number}/4] {title}")


def ok(message: str) -> None:
    print(f"  ✅ {message}")


def run() -> None:
    home = client_from_env(HOME_SITE)
    target = client_from_env(TARGET_SITE)

    # ── ① 前置依赖 ──────────────────────────────────────────────────────────
    step(1, f"前置依赖：{TARGET_SITE} 上补齐声明引用到的角色")
    made = ensure_roles(target, TARGET_SITE)
    ok(f"补了 {made}" if made else "声明引用的角色都已存在")

    # ── ② 建表（幂等）────────────────────────────────────────────────────────
    step(2, f"建表：两个站点上的 {VIEW_DOCTYPE}（已存在则跳过）")
    for site, client in ((HOME_SITE, home), (TARGET_SITE, target)):
        ok(f"{site}: {'建了' if ensure_table(client) else '已存在，跳过'}")

    # ── ③ 前置断言 ──────────────────────────────────────────────────────────
    step(3, f"前置：{TARGET_SITE} 上还没有 {PROBE_VIEW.name}")
    for name in (v.name for v in WORKER_DAILY_VIEWS):
        if has_view(target, name):
            raise StepFailed(
                f"{TARGET_SITE} 上已经有 {name} —— 上一轮没清理干净。"
                "不先确认它不存在，第④步证不出是同步过去的。"
            )
    ok(f"{TARGET_SITE} 上一个视图都没有")

    publish_views(home, WORKER_DAILY_VIEWS)
    ok(f"{HOME_SITE} 上已同步 {len(WORKER_DAILY_VIEWS)} 个视图（基线）")

    # ── ④ 迁站点 ────────────────────────────────────────────────────────────
    step(4, f"迁站点：同一份定义同步到 {TARGET_SITE}，读回来必须逐字段相同")
    published = publish_views(target, WORKER_DAILY_VIEWS)
    if published != len(WORKER_DAILY_VIEWS):
        raise StepFailed(f"应同步 {len(WORKER_DAILY_VIEWS)} 个，实际 {published}")

    for view in WORKER_DAILY_VIEWS:
        got = read_view(target, view.name)
        if got != view:
            raise StepFailed(f"{TARGET_SITE} 上的 {view.name} 与 git 里那份不同")
    ok(f"{TARGET_SITE} 上读回 {len(WORKER_DAILY_VIEWS)} 个视图，**与 git 里逐字段相同**")

    # 站点隔离：从 git 里拿掉一个，只同步目标站点，本站不受影响。
    publish_views(target, WORKER_DAILY_VIEWS[:-1])
    dropped = WORKER_DAILY_VIEWS[-1].name
    if has_view(target, dropped):
        raise StepFailed(f"真相源里去掉 {dropped} 之后，{TARGET_SITE} 上还留着 —— 只增不减")
    if not has_view(home, dropped):
        raise StepFailed(f"只同步了 {TARGET_SITE}，{HOME_SITE} 上的 {dropped} 却没了 —— 站点隔离没成立")
    ok(f"删得掉，且 {HOME_SITE} 不受影响")


def cleanup() -> None:
    """两个站点上的视图行都清掉。**成败两条路径都清** —— 不清会污染下一次的前置断言。

    ⚠️ **表本身不删**：建表是结构性改动，删表更是；回滚由人做（见 `store.ensure_table`）。
    """
    for site in (HOME_SITE, TARGET_SITE):
        try:
            publish_views(client_from_env(site), ())
        except (SiteError, Exception) as exc:  # noqa: BLE001
            print(f"  ⚠️ 清理 {site} 的视图行失败：{type(exc).__name__}: {exc}")


def main() -> int:
    try:
        run()
    except StepFailed as exc:
        print(f"\n❌ {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        import traceback

        print(f"\n❌ 非预期失败：{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 2
    finally:
        cleanup()
    print(f"\n✅ S3 第四段：同一份定义同步到了 {TARGET_SITE}，读回来逐字段相同。")
    print("⚠️ 边界：本判据**不打服务端** —— 那个站点上没有 serve 进程，")
    print("   验的是「定义到了那边」，不是「那边的浏览器里画出来了」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
