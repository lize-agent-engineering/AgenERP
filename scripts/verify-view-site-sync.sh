#!/usr/bin/env bash
# S3 **第四段** · 视图定义同步到另一个站点。
#
#     bash scripts/verify-view-site-sync.sh
#
# 与另外两条的分工：
#   verify-gitops.sh        定制包（Custom Field）的四步 —— 探针是 ToDo.agenerp_gitops_probe
#   verify-view-gitops.sh   S3 前三段（改 → diff → revert），全在 git 上，**不需要活栈**
#   本条                    S3 第四段（迁站点），**需要活栈 + 两个站点**
set -euo pipefail
fail() { echo "❌ $*" >&2; exit 1; }
cd "$(dirname "$0")/.."

# ⚠️ 与 verify-gitops.sh 同一条：**不能走 nginx（18080）** —— 它把所有请求钉在 frontend 上，
# 第四段会落到本站，看起来像「同步坏了」。默认直打 backend 那一格。
if [ "${AGENERP_SITE_URL:-}" = "http://127.0.0.1:18080" ]; then
  fail "AGENERP_SITE_URL 指向 nginx（18080），它把所有请求钉在 frontend 上 ——
  第四段会落到本站。unset 它，或指向 backend 那一格。"
fi
export AGENERP_SITE_URL="${AGENERP_SITE_URL:-http://127.0.0.1:${AGENERP_BACKEND_PORT:-8001}}"
[ -n "${AGENERP_ADMIN_PASSWORD:-}" ] || [ -n "${AGENERP_API_KEY:-}" ] \
  || fail "缺站点凭据：设 AGENERP_ADMIN_PASSWORD，或 AGENERP_API_KEY + AGENERP_API_SECRET"
echo "站点入口：$AGENERP_SITE_URL"

exec python3 tools/gitops/verify_view_site_sync.py
