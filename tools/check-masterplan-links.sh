#!/usr/bin/env bash
# T2 断链测试 —— 校验 docs/masterplan/README.md §5 引用登记表里的每一条引用真实存在。
# 用法：tools/check-masterplan-links.sh        退出码 0 = 全部命中；非 0 = 有断链
# 这是长期资产，不是一次性校验：Day 0 拆分 ARCHITECTURE.md / 改写 ROADMAP.md 之后必须复跑。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="$ROOT/docs/masterplan/README.md"
ENVF="$ROOT/docs/masterplan/evidence-repo.env"

[ -f "$README" ] || { echo "FATAL: 找不到 $README"; exit 2; }
[ -f "$ENVF" ]   || { echo "FATAL: 找不到 $ENVF"; exit 2; }

# shellcheck disable=SC1090
set -a; . "$ENVF"; set +a
XM="${XM_PATH:?evidence-repo.env 缺 XM_PATH}"

# 证据仓不在场（CI、换机器、新克隆）时：E 类引用跳过校验，M 类照查。
# 不这么做的话，CI 里这个 job 就是「注定红」——而一个注定红的检查等于没有检查，
# 还会把「CI 连续 2 轮红 → 停机」这条停机条件废掉。
EVIDENCE_PRESENT=1
if [ ! -d "$XM" ]; then
  EVIDENCE_PRESENT=0
  echo "NOTE    证据仓不在 $XM —— E 类（只读引证）引用本轮跳过，M 类（随仓迁移）照查"
  echo "        要连 E 类一起查：先 git clone 证据仓到该路径并 checkout 钉死的 sha"
  echo ""
fi

total=0; bad=0; skipped=0
while IFS= read -r line; do
  ref=$(  printf '%s' "$line" | awk -F'|' '{print $2}' | tr -d ' `')
  cls=$(  printf '%s' "$line" | awk -F'|' '{print $3}' | tr -d ' `')
  target=$(printf '%s' "$line" | awk -F'|' '{print $4}' | sed 's/^ *//; s/ *$//' | tr -d '`')
  anchor=$(printf '%s' "$line" | awk -F'|' '{print $5}' | sed 's/^ *//; s/ *$//' | tr -d '`')

  # 展开 ${XM}；仓内相对路径按仓根解析
  target="${target//\$\{XM\}/$XM}"
  case "$target" in /*) path="$target" ;; *) path="$ROOT/$target" ;; esac

  if [ "$cls" = "E" ] && [ "$EVIDENCE_PRESENT" -eq 0 ]; then
    skipped=$((skipped+1)); continue
  fi

  total=$((total+1))
  if [ ! -e "$path" ]; then
    echo "BROKEN  $ref [$cls]  目标不存在: $path"; bad=$((bad+1)); continue
  fi
  if [ -n "$anchor" ] && [ "$anchor" != "-" ]; then
    if [ -d "$path" ]; then
      echo "OK      $ref [$cls]  目录存在: $path"
      continue
    fi
    if ! grep -Fq -- "$anchor" "$path"; then
      echo "BROKEN  $ref [$cls]  锚串不在目标里: 「$anchor」 @ $path"; bad=$((bad+1)); continue
    fi
  fi
  echo "OK      $ref [$cls]"
done < <(grep -E '^\| *`REF:' "$README")

echo "----"
echo "共校验 $total 条引用，断链 $bad 条$( [ "$skipped" -gt 0 ] && echo "（另跳过 $skipped 条 E 类：证据仓不在场）" )。"
[ "$bad" -eq 0 ] || exit 1

# ---- 反向校验：正文里引用的每个 REF 都必须在登记表里有定义 ----
defined=$(grep -oE '^\| *`REF:[A-Z0-9-]+`' "$README" | tr -d ' `|')
undef=0
for used in $(grep -rhoE 'REF:[A-Z0-9-]+' "$ROOT/docs/masterplan" | sort -u); do
  if ! printf '%s\n' "$defined" | grep -qx "$used"; then
    echo "UNDEFINED  $used  —— 正文引用了它，但 README §5 登记表里没有"
    undef=$((undef+1))
  fi
done
echo "正文引用的 REF 中，未登记 $undef 个。"
[ "$undef" -eq 0 ] || exit 1

