#!/usr/bin/env bash
# S3 前三段 · 用**真的首页视图**跑「改 → diff → revert」。
#
#     bash scripts/verify-view-gitops.sh
#
# 与 `scripts/verify-gitops.sh` 的分工：那一条跑的是**定制包**（Custom Field）的四步，
# 探针是 `ToDo.agenerp_gitops_probe`；**本条跑的是首页视图定义**，
# 补的正是 P2 复盘记下的那句「S3 四段各自有实测，整条链没有」。
#
# ⚠️ **第四段「同步到另一站点生效」本条不做** —— 视图定义今天只在 git 里、
#    没落进站点的表（P2.0 判的「产物落自有表」那一半仍欠着）。本条只跑前三段，
#    跑完会把这句话再打印一遍，免得「三段全过」被读成「S3 完成了」。
set -euo pipefail

fail() { echo "❌ $*" >&2; exit 1; }

command -v git >/dev/null || fail "找不到 git"
cd "$(dirname "$0")/.."

# ⚠️ **2026-08-28 起本条需要活栈 + 凭据**（此前不需要）。
# 原因：服务端不再从 git 文件读视图定义，改成按调用者 sid **从站点表**读 ⇒
# 「改了 git、首页就变」中间多了一次 publish。**那不是绕路，那就是真实流程。**
# 代价照实记：它因此**进不了 CI**（与其它活体判据同族）。
if [ "${AGENERP_SITE_URL:-}" = "http://127.0.0.1:18080" ]; then
  fail "AGENERP_SITE_URL 指向 nginx（18080），它把所有请求钉在 frontend 上。
  unset 它，或指向 backend 那一格。"
fi
export AGENERP_SITE_URL="${AGENERP_SITE_URL:-http://127.0.0.1:${AGENERP_BACKEND_PORT:-8001}}"
export AGENERP_SITE="${AGENERP_SITE:-frontend}"
[ -n "${AGENERP_ADMIN_PASSWORD:-}" ] || [ -n "${AGENERP_API_KEY:-}" ] \
  || fail "缺站点凭据：设 AGENERP_ADMIN_PASSWORD，或 AGENERP_API_KEY + AGENERP_API_SECRET"
echo "站点入口：$AGENERP_SITE_URL"

exec python3 tools/gitops/verify_view_gitops.py
