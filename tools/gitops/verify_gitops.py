"""P2.4 · 定制包 GitOps 四步流水的**本体**。壳是 `scripts/verify-gitops.sh`。

    bash scripts/verify-gitops.sh

## 它要证明的那句话

> **包（git 里那些 JSON）是唯一真相源，站点是可再生的产物。**

四步逐条对着这句话的一部分：

| 步 | 证明 |
|---|---|
| ① 改   | 站点上的定制能被导出成包 |
| ② diff | 改动在 git 里是**干净可读**的 diff，不夹带时间戳噪声 |
| ③ revert | 真 `git revert` 之后 apply，站点上的字段**真的消失** |
| ④ 迁站点 | 同一个包在**另一个站点**上把字段从**无**建到**有** |

前三步都在同一个站点上打转，证明的是「改动可追踪、可撤回」。
**只有第四步证明「可复制到别处」** —— 而那才是 GitOps 这三个字的全部意义。

## 每一步都先断言前置状态

⚠️ 不先断言「这个字段本来不存在」，第③步的「消失」就可能是**它压根没出现过**；
不先断言「第二站点上没有它」，第④步就证不出**是迁过去的**。
这两条前置断言是本文件里最容易被省掉、也最不能省的东西。

## 边界

- 探针字段前缀 `agenerp_gitops_`，**成败两条路径都清理**（不清的话一次失败会污染下一次的前置断言）
- 第二站点**没有 erpnext** ⇒ 用 frappe core 的 `ToDo`，不是 `Item`。
  与 P0.5 那条门禁（用 `Item`）**互不替代**
- 本层**没有事务**：中途失败会留下部分应用的状态（P3.1 的活），这一点不假装有
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agenerp.pack import apply_pack, export_customizations  # noqa: E402
from agenerp.site import SiteError, client_from_env, custom_field_name  # noqa: E402
from agenerp.snapshot import SITE_ENV  # noqa: E402

PROBE_DOCTYPE = "ToDo"
PROBE_FIELD = "agenerp_gitops_probe"
HOME_SITE = "frontend"
TARGET_SITE = "gitops.test"


class StepFailed(RuntimeError):
    """某一步没达成。消息里必须能看出是**哪一步**、**期望什么**、**实际什么**。"""


def git(*args: str, cwd: pathlib.Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise StepFailed(f"git {' '.join(args)} 退 {result.returncode}：{result.stderr.strip()}")
    return result.stdout


def field_exists(site: str, doctype: str, fieldname: str) -> bool:
    """那个站点上有没有这个 Custom Field。

    ⚠️ **查不到与查不动要分开**：站点答 404 是「没有」，站点连不上是 `SiteError` 往上抛。
    把两者合并成 `False` 会让「栈坏了」长得像「字段被删干净了」—— 那正是第③步会误判的形态。
    """
    client = client_from_env(site)
    try:
        client.get(f"/api/resource/Custom Field/{custom_field_name(doctype, fieldname)}")
    except SiteError as exc:
        if "404" in str(exc) or "DoesNotExist" in str(exc) or "not found" in str(exc).lower():
            return False
        raise
    return True


def add_probe(site: str) -> None:
    client_from_env(site).create_doc(
        "Custom Field",
        {"dt": PROBE_DOCTYPE, "fieldname": PROBE_FIELD, "fieldtype": "Data",
         "label": "AgenERP GitOps 探针"},
    )


def drop_probe(site: str) -> None:
    """删探针字段，**并且把它留下的物理列一起清掉**。

    🔴 2026-08-28 由 P2.5 的巡检工具第一次真跑抓到：
    只删 Custom Field 时 Frappe **不删物理列**（Spike 06 的结论在 v15 上仍成立），
    于是每跑一轮 `verify-gitops.sh` 就在 `gitops.test` 上多积一条孤儿列 ——
    `schema.drift` 当场把它报了出来（`ToDo.agenerp_gitops_probe`）。
    **一个自己制造孤儿列的验收脚本，没有资格验别人干不干净。**
    """
    from agenerp.apply import drop_orphan_columns
    from agenerp.snapshot import SnapshotEntry

    try:
        if field_exists(site, PROBE_DOCTYPE, PROBE_FIELD):
            client_from_env(site).delete_custom_field(PROBE_DOCTYPE, PROBE_FIELD)
        # 清除面**自带收窄**：只碰「本次删掉的 fieldname ∩ Frappe 判定的孤儿列」，
        # 历轮残留的别人家的列一个都不碰（§11.6）。
        drop_orphan_columns((SnapshotEntry(PROBE_DOCTYPE, PROBE_FIELD),), site)
    except Exception as exc:  # noqa: BLE001 —— 清理失败不改变本轮结论，但必须说出来
        print(f"  ⚠️ 清理 {site} 上的探针失败：{type(exc).__name__}: {exc}")


def export_from(site: str, pack: pathlib.Path) -> None:
    """导出**指定站点**的定制。`export_customizations` 按 `AGENERP_SITE` 取来源。"""
    previous = os.environ.get(SITE_ENV)
    os.environ[SITE_ENV] = site
    try:
        export_customizations(doctype=PROBE_DOCTYPE, into=str(pack))
    finally:
        if previous is None:
            os.environ.pop(SITE_ENV, None)
        else:
            os.environ[SITE_ENV] = previous


def step(number: int, title: str) -> None:
    print(f"\n[{number}/4] {title}")


def ok(message: str) -> None:
    print(f"  ✅ {message}")


def run(pack: pathlib.Path) -> None:
    # ── ① 改 ────────────────────────────────────────────────────────────────
    step(1, f"改：在 {HOME_SITE} 上加 {PROBE_DOCTYPE}.{PROBE_FIELD} 并导出成包")
    if field_exists(HOME_SITE, PROBE_DOCTYPE, PROBE_FIELD):
        raise StepFailed(
            f"{HOME_SITE} 上已经有 {PROBE_FIELD} —— 上一轮没清理干净。"
            "不先确认它不存在，第③步的「消失」证明不了任何事。"
        )
    ok(f"前置：{HOME_SITE} 上没有 {PROBE_FIELD}")

    git("init", "-q", cwd=pack)
    git("config", "user.email", "gitops@agenerp.local", cwd=pack)
    git("config", "user.name", "AgenERP GitOps", cwd=pack)
    export_from(HOME_SITE, pack)
    git("add", "-A", cwd=pack)
    git("commit", "-q", "-m", "baseline", cwd=pack)
    ok("基线已提交")

    add_probe(HOME_SITE)
    export_from(HOME_SITE, pack)
    ok(f"{HOME_SITE} 上已加字段并重新导出")

    # ── ② diff ──────────────────────────────────────────────────────────────
    step(2, "diff：改动在 git 里干净可读，不夹带时间戳噪声")
    changed = [
        line[1:]
        for line in git("diff", "-U0", cwd=pack).splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith(("+++", "---"))
    ]
    if not changed:
        raise StepFailed("改了定制却没产生任何 diff —— 导出没把改动写进包")
    noise = [line for line in changed if PROBE_FIELD not in line and line.strip() not in "{}[],"]
    if noise:
        raise StepFailed(f"diff 里夹带了与本次改动无关的内容：{noise[:5]}")
    ok(f"diff 只含本次改动（{len(changed)} 行）")
    git("add", "-A", cwd=pack)
    git("commit", "-q", "-m", f"add {PROBE_FIELD}", cwd=pack)
    added_commit = git("rev-parse", "HEAD", cwd=pack).strip()

    # ── ③ revert ────────────────────────────────────────────────────────────
    step(3, "revert：真 git revert 之后 apply，站点上的字段真的消失")
    git("revert", "--no-edit", "-n", added_commit, cwd=pack)
    git("commit", "-q", "-m", f"revert {PROBE_FIELD}", cwd=pack)
    apply_pack(str(pack), site=HOME_SITE)
    if field_exists(HOME_SITE, PROBE_DOCTYPE, PROBE_FIELD):
        raise StepFailed(
            f"revert 之后 apply，{HOME_SITE} 上的 {PROBE_FIELD} **还在** —— "
            "这正是 Frappe 原生 sync_customizations（纯 upsert）的形态，撤不回。"
        )
    ok(f"{HOME_SITE} 上的 {PROBE_FIELD} 已消失")

    # ── ④ 迁站点 ────────────────────────────────────────────────────────────
    step(4, f"迁站点：同一个包在 {TARGET_SITE} 上把字段从无建到有")
    if field_exists(TARGET_SITE, PROBE_DOCTYPE, PROBE_FIELD):
        raise StepFailed(
            f"{TARGET_SITE} 上已经有 {PROBE_FIELD} —— 不先确认它不存在，"
            "证不出字段是被包迁过去的。"
        )
    ok(f"前置：{TARGET_SITE} 上没有 {PROBE_FIELD}")

    git("revert", "--no-edit", "-n", "HEAD", cwd=pack)
    git("commit", "-q", "-m", f"restore {PROBE_FIELD}", cwd=pack)
    apply_pack(str(pack), site=TARGET_SITE)
    if not field_exists(TARGET_SITE, PROBE_DOCTYPE, PROBE_FIELD):
        raise StepFailed(f"apply 到 {TARGET_SITE} 之后，{PROBE_FIELD} 没有出现")
    ok(f"{TARGET_SITE} 上长出了 {PROBE_FIELD} —— **包是唯一真相源**")

    if field_exists(HOME_SITE, PROBE_DOCTYPE, PROBE_FIELD):
        raise StepFailed(
            f"迁到 {TARGET_SITE} 之后 {HOME_SITE} 上也出现了 {PROBE_FIELD} —— "
            "站点隔离没成立，这一步证不了跨站点。"
        )
    ok(f"{HOME_SITE} 不受影响")


def main() -> int:
    pack = pathlib.Path(tempfile.mkdtemp(prefix="agenerp-gitops-"))
    try:
        run(pack)
    except StepFailed as exc:
        print(f"\n❌ {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 —— 非预期失败也要留全貌，不吞
        import traceback

        print(f"\n❌ 非预期失败：{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 2
    finally:
        # 🔴 **成败两条路径都清理。** 不清的话一次失败会污染下一次的前置断言，
        # 而那个污染的表现是「第①步说上一轮没清理干净」—— 症状离病因很远。
        for site in (HOME_SITE, TARGET_SITE):
            drop_probe(site)
        shutil.rmtree(pack, ignore_errors=True)
    print("\n✅ 四步全过：包是唯一真相源，站点是可再生的产物。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
