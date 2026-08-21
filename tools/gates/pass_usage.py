#!/usr/bin/env python3
"""按「趟」计量循环的真实用量，写入台账。

为什么不用 entrypoint 之类的标记区分循环会话与人的会话：实测循环起的
`claude -p` 会继承父进程的 CLAUDE_CODE_ENTRYPOINT，49 个会话全都标成
claude-desktop —— 标记会骗人。改用文件集差分：跑之前拍快照，跑完新出现的
会话文件就是这一趟产生的。不依赖任何可被继承的环境变量。

用法：
  pass_usage.py snapshot <快照文件>              # 开跑前
  pass_usage.py measure  <快照文件> [--label L]  # 跑完，追加进台账
台账：_tmp/loop-usage.jsonl（每趟一行）
"""
import argparse, datetime, json, pathlib, sys

LEDGER = pathlib.Path("_tmp/loop-usage.jsonl")


def sessions_dir() -> pathlib.Path:
    return pathlib.Path.home() / ".claude/projects" / str(pathlib.Path.cwd().resolve()).replace("/", "-")


def current_files() -> set[str]:
    d = sessions_dir()
    return {f.name for f in d.glob("*.jsonl")} if d.is_dir() else set()


def sum_usage(names: set[str]) -> dict:
    d = sessions_dir()
    tot = {"input": 0, "output": 0, "msgs": 0}
    for name in names:
        f = d / name
        if not f.is_file():
            continue
        for line in f.open(errors="ignore"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("type") != "assistant":
                continue
            u = (r.get("message") or {}).get("usage") or {}
            if not u:
                continue
            tot["msgs"] += 1
            tot["input"] += (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) \
                + (u.get("cache_read_input_tokens") or 0)
            tot["output"] += u.get("output_tokens") or 0
    return tot


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["snapshot", "measure"])
    ap.add_argument("snapfile")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    snap = pathlib.Path(a.snapfile)

    if a.mode == "snapshot":
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text("\n".join(sorted(current_files())))
        return 0

    before = set(snap.read_text().split("\n")) if snap.exists() else set()
    new = current_files() - before
    tot = sum_usage(new)
    rec = {"at": datetime.datetime.now(datetime.UTC).isoformat(), "label": a.label,
           "sessions": len(new), **tot}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[usage] 本趟 {len(new)} 个会话 · 输入 {tot['input']:,} · 输出 {tot['output']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
