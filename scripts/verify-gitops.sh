#!/usr/bin/env bash
# P2.4 · 定制包 GitOps 四步验收。`02-WBS.md` §5 第 104 行那条验收命令打的就是本文件。
#
#     bash scripts/verify-gitops.sh
#
# 🔴 **本文件是薄壳**：环境检查 + 幂等建站 + 调 Python + 退出码。
# 四步本体在 `tools/gitops/verify_gitops.py` —— 那里的断言是「字段**真的**在/不在
# 那个站点上」，在 shell 里那要靠 grep JSON，脆且失败时说不清哪一步坏的。
#
# ⚠️ **缺东西时明确报错并指名缺什么**，不静默跳过：
# 一个「环境没配好就当过了」的验收脚本，退 0 时什么都没证明。
set -euo pipefail

HOME_SITE="frontend"
TARGET_SITE="gitops.test"
BACKEND="${AGENERP_BACKEND_CONTAINER:-agenerp-backend-1}"

fail() { echo "❌ $*" >&2; exit 1; }

# ── 站点入口：**必须绕开 nginx** ────────────────────────────────────────────
#
# 🔴 2026-08-28 实测：`frontend` 那一格（18080）走 nginx，而 nginx 的
# `FRAPPE_SITE_NAME_HEADER=frontend` 把**所有**请求钉在 `frontend` 上 ——
# 带 `Host: gitops.test` 打过去，落地的仍然是 `frontend`
# （判别方式：问它有没有 `Item` DocType，那是 erpnext 的表，gitops.test 上没有）。
# 走 18080 时第四步会**假绿**：字段其实建在了 frontend 上。
#
# gunicorn 自己按 Host 正确分站 ⇒ 直打 backend 那一格（compose 2026-08-28 加的
# `127.0.0.1:${AGENERP_BACKEND_PORT:-8001}:8000`）。
# 调用方显式设了 AGENERP_SITE_URL 就尊重它 —— 但那时**分站对不对由调用方负责**。
# ⚠️ **交接文档 §6 那套「活栈环境」会把 AGENERP_SITE_URL 设成 18080** ——
# 照它配好再跑本脚本，第④步会落到 `frontend` 并被隔离断言咬红。
# 结论是**响的**（不是假绿），但它会把一个环境问题伪装成「跨站点坏了」，
# 正是交接文档 §3② 记着的那类误归因。⇒ 显式设了 18080 时**当场拦下并说清楚**。
if [ "${AGENERP_SITE_URL:-}" = "http://127.0.0.1:18080" ] ||    [ "${AGENERP_SITE_URL:-}" = "http://localhost:18080" ]; then
  fail "AGENERP_SITE_URL 指向 nginx（18080），而 nginx 把**所有**请求钉在 frontend 上
  ⇒ 第四步「迁站点」会落到 frontend，被隔离断言咬红，看起来像跨站点坏了。
  改用 backend 那一格，或者干脆 unset 让本脚本自己选：
    unset AGENERP_SITE_URL   # 本脚本会用 http://127.0.0.1:\${AGENERP_BACKEND_PORT:-8001}"
fi
export AGENERP_SITE_URL="${AGENERP_SITE_URL:-http://127.0.0.1:${AGENERP_BACKEND_PORT:-8001}}"
echo "站点入口：$AGENERP_SITE_URL"

# ── 环境 ────────────────────────────────────────────────────────────────────
if [ -z "${AGENERP_ADMIN_PASSWORD:-}" ] && [ -z "${AGENERP_API_KEY:-}" ]; then
  fail "缺站点凭据：设 AGENERP_ADMIN_PASSWORD，或 AGENERP_API_KEY + AGENERP_API_SECRET"
fi
command -v docker >/dev/null || fail "找不到 docker —— 建站与站点都在 compose 栈里"
docker inspect "$BACKEND" >/dev/null 2>&1 \
  || fail "找不到容器 $BACKEND —— 先 docker compose up -d（可用 AGENERP_BACKEND_CONTAINER 覆盖）"

# ── 幂等建站 ────────────────────────────────────────────────────────────────
# 惯例照 docker-compose.yml 的 create-site：**已存在则跳过，跑完不删**。
# 第一次慢（bench new-site），之后每次都快，且重复跑幂等。
# ⚠️ 刻意**不装 erpnext**：Custom Field / Property Setter 是 frappe core 的机制，
#    跨站点这件事用 core 就验得了，而装 erpnext 会把建站从「分钟以内」变成分钟级起。
#    代价：包里只能用 core 有的 DocType（本项用 ToDo，不是 Item）。
if docker exec "$BACKEND" test -f "/home/frappe/frappe-bench/sites/$TARGET_SITE/site_config.json"; then
  echo "站点 $TARGET_SITE 已存在，跳过建站"
else
  echo "站点 $TARGET_SITE 不存在，建站中（只装 frappe core，不装 erpnext）…"
  docker exec "$BACKEND" bash -c "
    cd /home/frappe/frappe-bench &&
    bench new-site '$TARGET_SITE' \
      --no-mariadb-socket \
      --db-root-password '${AGENERP_DB_PASSWORD:-changeit}' \
      --admin-password '${AGENERP_ADMIN_PASSWORD}'
  " >/dev/null 2>&1 || fail "建站失败 —— 手动复跑上面那条 bench new-site 看原文"
  echo "站点 $TARGET_SITE 建好了"
fi

# ── 四步 ────────────────────────────────────────────────────────────────────
exec python3 "$(dirname "$0")/../tools/gitops/verify_gitops.py"
