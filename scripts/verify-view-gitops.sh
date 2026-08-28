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

# 不需要活栈、不需要凭据、不需要模型：观察点是 `build_server(port=0)` 起的本地真服务，
# 读的就是宿主仓库里那份 JSON。**这也是它能进 CI 的原因。**
exec python3 tools/gitops/verify_view_gitops.py
