# Runbook · 重建站点（清空重来）

**什么时候用**：站点数据被污染、要换样板公司、或验证「干净站点能否从仓库完整复现」。

## 步骤

```bash
# ① 丢站（数据会没，站点内容全部可从种子包重生成）
docker compose exec -T backend bench drop-site frontend \
  --force --db-root-password changeit --no-backup

# ② 建站 —— **必须走 compose 的 create-site 服务，不要手搓 bench new-site**
docker compose up create-site

# ③ 首页横幅（「AI 能力未配置」）—— 建站不含它，要单独跑
docker compose up bootstrap-homepage

# ④ 装数据
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
       AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin
python3 -m agenerp.seedsite --site frontend --load-masters
python3 -m agenerp.seedsite --site frontend --load-documents
python3 -m agenerp.seedsite --site frontend --verify-site   # 应为 9 项全过

# ⑤ 活门禁
AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q      # 应为 8 passed
```

## ⚠️ 第 ② 步为什么不能手搓

2026-08-23 实测踩过：在 backend 容器里直接跑 `bench new-site`（不带
`--no-mariadb-socket`），MariaDB 的授权会被**钉死在创建者容器的 IP** 上：

```
mysql.user →  _5e5899d8398b5f7b @ 172.25.0.9     ← 只有 backend 连得上
```

后果是**静默的、错位的**：`bench` 命令和 HTTP API 装载全都正常（它们都从
backend 走），只有 `bootstrap-homepage` 这类**另一个容器**的直连数据库步骤
会 `Access denied`，表现为「首页横幅丢了」，看不出跟建站有关。

compose 的 `create-site` 带了 `--no-mariadb-socket`，授权发给 `%`：

```
mysql.user →  _5e5899d8398b5f7b @ %              ← 全网段可连
```

**判据**：重建后跑一次
`docker compose exec -T db mysql -uroot -pchangeit -N -e "SELECT user,host FROM mysql.user WHERE user LIKE '\_%';"`，
host 必须是 `%`。

## 第 ③ 步为什么单列

`create-site` 只建站装 app。首页横幅由 `bootstrap-homepage` 一次性服务写进
`Website Settings.banner_html`（`tools/bootstrap/homepage_notice.py`）。
`docker compose up -d` 会带上它，但**单跑 `up create-site` 不会**——
漏了它，`test_homepage_states_ai_disabled_instead_of_crashing` 会红。
