#!/usr/bin/env bash
# T1 的机械部分（静态预检）——RESUME 协议要的四件事，是否都能从文件里机械地取到。
# 这不能替代 T1（T1 要的是「全新会话真的做到了」），但能挡住最常见的文档腐烂：
# STATE 指向一个不存在的 WBS 行，或指向一个没有验收命令的行。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MP="$ROOT/docs/masterplan"
fail=0

# 1. 北极星句可唯一提取
star=$(awk '/^## 1\. 北极星/,/^---/' "$MP/00-GOALS.md" | grep -E '^> \*\*.+\*\*$' | head -1)
if [ -z "$star" ]; then echo "FAIL 1/4 北极星句提取不到（00-GOALS.md §1 应有一行 > **…**）"; fail=1
else echo "OK   1/4 北极星：${star:0:40}…"; fi

# 2. STATE §1 有「下一个未阻塞工作项」且能取出 ID
row=$(grep -E '^\| \*\*下一个未阻塞工作项\*\*' "$MP/STATE.md" | head -1)
id=$(printf '%s' "$row" | grep -oE '(W-?[0-9]+\.[0-9]+[a-z]?|P[0-5]\.[0-9]+)' | head -1)
if [ -z "$id" ]; then echo "FAIL 2/4 STATE §1 取不到下一项的 WBS 行 ID"; fail=1
else echo "OK   2/4 下一项 ID：$id"; fi

# 3. 该 ID 在 02-WBS 里存在
if [ -n "$id" ]; then
  line=$(grep -F "| $id " "$MP/02-WBS.md" | head -1)
  if [ -z "$line" ]; then echo "FAIL 3/4 02-WBS 里没有 $id 这一行"; fail=1
  else echo "OK   3/4 02-WBS 命中 $id"; fi
fi

# 4. 该行的「验收」列非空（表结构：| ID | 工作项 | 前置 | 验收 | 状态源 | …）
if [ -n "${line:-}" ]; then
  acc=$(printf '%s' "$line" | awk -F'|' '{print $5}' | sed 's/^ *//; s/ *$//')
  if [ -z "$acc" ] || [ "$acc" = "—" ]; then echo "FAIL 4/4 $id 的验收列为空——按表规这一行不许存在"; fail=1
  else echo "OK   4/4 验收：${acc:0:60}…"; fi
fi

echo "----"
[ "$fail" -eq 0 ] && echo "RESUME 协议四要素静态可解析。" || echo "有要素解析不出来，T1 必然失败。"
exit "$fail"
