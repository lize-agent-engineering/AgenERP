#!/usr/bin/env python3
"""把 STATE.md 的老条目轮转进归档 —— 追加式账本必然长到超预算。

主计划给每份文档定的硬约束是 30,720 字节。STATE 是**冷启动第一个被读的文件**，
它一胖，RESUME 那条路就跟着变贵变慢。

轮转不是删除：老条目整段搬进 `docs/masterplan/archive/STATE-<日期>.md`，
原处留指针。**只增不改**的纪律不受影响 —— 历史一个字没丢，只是不再挤占每轮预算。

⚠️ **条目是多行的**：`- 2026-…` 开头，后跟若干 `· **…` 续行。
   按行搬会把头搬走、续行留下，账本当场错乱 —— 这是写这个工具时实测踩到的坑。
   所以下面一律按「条目块」处理，不按行。

搬什么：
  §2 会话日志  —— 只保留最近 N 条（RESUME 只读末行）
  §3 needs-human —— 只搬 `[resolved]`，`[open]` 一条不动（那是待办，必须留在眼前）

用法：python3 tools/rotate-state.py [--budget BYTES] [--dry-run]
"""
import argparse
import datetime
import pathlib
import re
import sys

STATE = pathlib.Path("docs/masterplan/STATE.md")
ARCHIVE_DIR = pathlib.Path("docs/masterplan/archive")
BUDGET = 30720
LOG_HEAD = re.compile(r"^- 20\d\d-")
QUEUE_HEAD = re.compile(r"^- \[(open|resolved)\]")


def blocks(lines, lo, hi, head_re):
    """把 [lo,hi) 切成条目块：(起, 止)。止 = 下一条目头或区间末。"""
    heads = [i for i in range(lo, hi) if head_re.match(lines[i])]
    out = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else hi
        out.append((start, end))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    text = STATE.read_text()
    lines = text.split("\n")
    before = len(text.encode())

    s2 = next((i for i, l in enumerate(lines) if l.startswith("## §2")), -1)
    s3 = next((i for i, l in enumerate(lines) if l.startswith("## §3")), -1)
    if s2 < 0 or s3 < 0:
        print("FATAL: 找不到 §2 / §3 分节标题", file=sys.stderr)
        return 2

    log_blocks = blocks(lines, s2, s3, LOG_HEAD)
    queue_blocks = blocks(lines, s3, len(lines), QUEUE_HEAD)
    resolved = [(s, e) for s, e in queue_blocks if lines[s].startswith("- [resolved]")]

    def size_after(drop_ranges):
        drop = {i for s, e in drop_ranges for i in range(s, e)}
        return len("\n".join(l for i, l in enumerate(lines) if i not in drop).encode())

    # 先搬 §3 的 resolved（单条最长、且已无行动价值），不够再从 §2 最老的往前搬
    move = list(resolved)
    keep_log = len(log_blocks)
    while size_after(move) > a.budget and keep_log > 1:
        keep_log -= 1
        move = list(resolved) + log_blocks[: len(log_blocks) - keep_log]

    if not move:
        print(f"[rotate] STATE.md {before:,} 字节，在预算 {a.budget:,} 内，无需轮转")
        return 0

    after = size_after(move)
    n_log = len(log_blocks) - keep_log
    if a.dry_run:
        print(f"[rotate] 干跑：搬 §3 resolved {len(resolved)} 条 + §2 最老 {n_log} 条，"
              f"保留 §2 最近 {keep_log} 条")
        print(f"[rotate] {before:,} → {after:,} 字节（预算 {a.budget:,}）")
        return 0

    stamp = datetime.date.today().isoformat()
    archive = ARCHIVE_DIR / f"STATE-{stamp}.md"
    drop = {i for s, e in move for i in range(s, e)}
    body = "\n".join(lines[i] for i in sorted(drop)).strip("\n") + "\n"
    header = (f"# STATE 归档 · 截至 {stamp}\n\n"
              f"> 由 `tools/rotate-state.py` 从 `docs/masterplan/STATE.md` 整段搬来："
              f"§3 已处置条目 {len(resolved)} 条 + §2 较早证据行 {n_log} 条。\n"
              f"> **一个字都没改**。轮转是为了让 STATE 回到 {a.budget:,} 字节预算内 —— "
              f"它是冷启动第一个被读的文件。历史在这里，不在别处。\n\n---\n\n")

    kept = [l for i, l in enumerate(lines) if i not in drop]
    ptr_log = (f"> 📦 较早的 {n_log} 条证据行已整段归档到 "
               f"[archive/{archive.name}](./archive/{archive.name})（一字未改）。"
               f"冷启动读的是 §1 + 本节末行 + §3，不受影响。")
    ptr_q = (f"> 📦 已处置（`resolved`）的 {len(resolved)} 条已整段归档到 "
             f"[archive/{archive.name}](./archive/{archive.name})。**`open` 的一条没动** —— "
             f"待办必须留在眼前。")
    i2 = next(i for i, l in enumerate(kept) if l.startswith("## §2"))
    kept.insert(i2 + 1, "\n" + ptr_log)
    i3 = next(i for i, l in enumerate(kept) if l.startswith("## §3"))
    kept.insert(i3 + 1, "\n" + ptr_q)
    new_text = "\n".join(kept)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive.write_text((archive.read_text() if archive.exists() else header) + body)
    STATE.write_text(new_text)
    print(f"[rotate] 搬走 §3 resolved {len(resolved)} 条 + §2 最老 {n_log} 条 → {archive}")
    print(f"[rotate] STATE.md {before:,} → {len(new_text.encode()):,} 字节（预算 {a.budget:,}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
