"""S3 前三段 · 用**真的首页视图**跑一遍「改 → diff → revert」。**本体，壳是 scripts/。**

## 它补的是哪一句

`00-GOALS.md` §2 的 **S3**：

> 一句话改老板首页 → `git diff` 看得见 → `git revert` 撤得回 → 同步到另一站点生效

P2.4 的 `verify-gitops.sh` 跑通了四步，**但用的是一个探针 Custom Field**
（`ToDo.agenerp_gitops_probe`），**不是首页视图**。
⇒ 那时 S3 的四段「各自有实测，整条链没有」。本文件补上**前三段对真视图**的那一条。

⚠️ **第四段「同步到另一站点生效」本文件不做，也做不了** —— 照实说清楚：
视图定义今天只在 git 里，**没有落进站点的表**（P2.0 判的「产物落自有表」那一半仍欠着，
形态照 P1.2 会话 DocType：DocType 声明落 git、**建表是人的动作**）。
第二个站点上既没有那张表，也没有服务进程。**这句话不许被「反正 git 里有」盖过去。**

## 观察点

`build_server(port=0)` 在本地起**真服务**、发**真 HTTP** 打 `/agenerp/view`
—— 与 P2.6 的端点判据同一个观察点，读的正是**宿主仓库**里那份 JSON，
也就是 git 操作发生的地方。

⚠️ **不打 compose 里的 `agenerp-serve` 容器**：那个进程在启动时就把视图读进内存了，
改文件不重启看不出来；而重启容器会把「观察」和「重启时机」搅在一起。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import threading
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEW_FILE = REPO / "agenerp" / "dsl" / "views" / "worker-work-orders.json"
PROBE_COLUMN = "produced_qty"  # 首页那张列表里真实存在的一列，改它最看得出来


class StepFailed(RuntimeError):
    """某一步没达成。消息里要能看出**哪一步、期望什么、实际什么**。"""


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise StepFailed(f"git {' '.join(args)} 退 {result.returncode}：{result.stderr.strip()}")
    return result.stdout


def home_columns() -> list[str]:
    """起一个**真服务**、发**真 HTTP**，把首页那张列表的列取回来。

    ⚠️ 每次都**重新 import** 视图定义：`roles.py` 在模块级 `load_views()`，
    不重载的话第二次读到的还是第一次的内存副本 —— 那会让整条判据**恒绿**。
    """
    for name in [m for m in list(sys.modules) if m.startswith("agenerp.")]:
        del sys.modules[name]
    from agenerp.serve.app import build_server

    # `site` 是必填 —— 服务要知道 sid 拿去问谁。视图计划端点**不认人**
    # （P2.6 裁定：schema 全局共享，回的是视图定义不是业务数据），占位站点名即可。
    server = build_server(site="s3-chain-local", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/agenerp/view?name=worker-work-orders"
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    for block in payload.get("blocks", []):
        if block.get("type") == "list":
            return list(block.get("fields") or [])
    raise StepFailed(f"首页视图里没有 list 块，取不到列：{str(payload)[:200]}")


def step(number: int, title: str) -> None:
    print(f"\n[{number}/3] {title}")


def ok(message: str) -> None:
    print(f"  ✅ {message}")


def run() -> None:
    # 🔴 **整个工作树必须干净，不只是那一个文件。**
    #
    # 2026-08-28 实测踩到：清理路径用的是 `git reset --hard`，那是**仓库级**的 ——
    # 它把当时尚未提交的一处修复**一起抹掉了**，而现象是「sha 对得上、改动却不见了」，
    # 离病因很远。⇒ 要么别用 reset --hard，要么**先保证没有东西可丢**。
    # 这里取后者并把门槛提到整个工作树：本判据要做**历史手术**（commit + revert），
    # 在脏工作树上做历史手术是拿别人的活冒险。
    dirty = git("status", "--porcelain").strip()
    if dirty:
        raise StepFailed(
            "工作树不干净，本判据拒绝运行 —— 它会 commit / revert / reset，"
            "在脏工作树上做这些是拿未提交的改动冒险。\n"
            f"  未提交：{dirty.splitlines()[:5]}\n"
            "  先提交或 stash 再跑。"
        )

    # ── ① 改 ────────────────────────────────────────────────────────────────
    step(1, f"改：把首页列表里的 {PROBE_COLUMN} 这一列去掉")
    before = home_columns()
    if PROBE_COLUMN not in before:
        raise StepFailed(f"首页本来就没有 {PROBE_COLUMN} 这一列，改它证明不了任何事：{before}")
    ok(f"前置：首页现在有 {len(before)} 列，含 {PROBE_COLUMN}")

    payload = json.loads(VIEW_FILE.read_text(encoding="utf-8"))
    for block in payload["blocks"]:
        if block.get("type") == "list":
            block["fields"] = [f for f in block["fields"] if f != PROBE_COLUMN]
    VIEW_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    after = home_columns()
    if PROBE_COLUMN in after:
        raise StepFailed(f"改了定义，首页却照旧有 {PROBE_COLUMN} —— 服务读的不是这份文件？")
    if len(after) != len(before) - 1:
        raise StepFailed(f"列数不对：改前 {len(before)}、改后 {len(after)}")
    ok(f"首页真的少了一列（{len(before)} → {len(after)}）")

    # ── ② diff ──────────────────────────────────────────────────────────────
    step(2, "diff：改动在 git 里干净可读")
    changed = [
        line for line in git("diff", "-U0", "--", str(VIEW_FILE)).splitlines()
        if (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---"))
    ]
    if not changed:
        raise StepFailed("改了首页却没产生任何 diff")
    noise = [line for line in changed if PROBE_COLUMN not in line]
    if noise:
        raise StepFailed(f"diff 夹带了与本次改动无关的内容：{noise[:5]}")
    ok(f"diff 只含那一列（{len(changed)} 行）")

    git("add", "--", str(VIEW_FILE))
    git("-c", "user.email=s3@agenerp.local", "-c", "user.name=S3 chain",
        "commit", "-q", "-m", f"chore(s3): 临时去掉首页的 {PROBE_COLUMN} 列")
    ok("已提交（下一步 revert 它）")

    # ── ③ revert ────────────────────────────────────────────────────────────
    step(3, "revert：真 git revert 之后，首页真的变回去")
    git("revert", "--no-edit", "-n", "HEAD")
    git("-c", "user.email=s3@agenerp.local", "-c", "user.name=S3 chain",
        "commit", "-q", "-m", f"Revert \"chore(s3): 临时去掉首页的 {PROBE_COLUMN} 列\"")

    restored = home_columns()
    if restored != before:
        raise StepFailed(f"revert 之后首页没回到原样：\n  之前 {before}\n  现在 {restored}")
    ok(f"首页回到 {len(restored)} 列，与改动前**逐列相同**")


def main() -> int:
    head_before = git("rev-parse", "HEAD").strip()
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
        # 🔴 **把这两笔临时提交清掉。** 本判据是「跑一遍看看」，不是往历史里塞两条噪声。
        # ⚠️ 只在 HEAD 确实是本判据造出来的那两条时才 reset —— 不碰别人的提交。
        current = git("rev-parse", "HEAD").strip()
        if current != head_before:
            subjects = git("log", "--format=%s", f"{head_before}..HEAD").splitlines()
            still_clean = not git("status", "--porcelain").strip()
            mine = subjects and all(
                "chore(s3)" in s or 'Revert "chore(s3)' in s for s in subjects
            )
            if mine and still_clean:
                # ⚠️ `reset --hard` 是仓库级的破坏性动作。上面两个条件缺一不可：
                # ① 要回退的每一笔都是本判据造的；② 此刻**没有任何未提交改动可丢**。
                git("reset", "--hard", "-q", head_before)
                print(f"\n（已清掉本判据造的 {len(subjects)} 笔临时提交，HEAD 回到 {head_before[:8]}）")
            elif not mine:
                print(f"\n⚠️ HEAD 变了但不全是本判据造的，**不动它**：{subjects}")
            else:
                print(
                    "\n⚠️ 工作树里出现了未提交改动，**不做 reset --hard**（那会连它一起抹掉）。\n"
                    f"   本判据造的 {len(subjects)} 笔提交留在历史里，请自行处置：\n"
                    f"   git reset --hard {head_before[:12]}"
                )
    print("\n✅ S3 前三段全过：改老板首页 → git diff 看得见 → git revert 撤得回。")
    print("⚠️ 第四段「同步到另一站点生效」**未做**：视图定义只在 git 里，没落进站点的表。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
