# P1.8a 第 2 个 plan · 解释服务接进 compose + nginx 同源反代（活体验收那一半）

> Plan Status: completed
> Mission: p1-insight
> Work Item: 10. **解释服务的 HTTP 面**（P1.8a，见 D-19）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个，本 plan 用掉最后一格）
> Last Reviewed: 2026-08-25
> Source: `docs/masterplan/DECISIONS.md` **D-19** · `docs/masterplan/02-WBS.md` §4 **P1.8a** 行 ·
> `docs/backlog/p1-insight-roadmap.md` 工作项 10
> Related: [`2026-08-25-1159-1-explain-http-service.md`](./2026-08-25-1159-1-explain-http-service.md)
> （`completed`。**本 plan 是它 `Deferred But Adjudicated` 第一条逐字指名的承接者**，
> 重开事件「本 plan 收口」已于 2026-08-25 触发。⚠️ **文件名与它指名的路径不同** ——
> 它写的是 `2026-08-25-1159-2-…`，而 mission-driver 的命名规则是「起草时刻 + 序号」，
> 故落 `2026-08-25-1423-1-…`。**指的是同一格预算、同一件事**，此处照实记，不改它那一行）·
> [`2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`](./2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md)
> （`deferred`；它 Phase 2 落地的 `sid` 互斥模式是本 plan 的**输入**，不重做）
> Audit: required

## 0. 执行前必做：重取基线

**起草期读到的一切都可能在开工时已经变了。** 下面十一处逐条重读，实读值填进 §0.1，
与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`（判据收窄成：**除本 plan 文件外无输出**，
   先例与理由见 `2026-08-25-1159-1` §0.1 第 1 行）
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时的最大节号**
   （起草期实读 **§7.20**，本 plan 预定落 **§7.21**；被别的 plan 占用就顺延，以开工时实读为准）
3. `agenerp/serve/app.py` 的 `LOOPBACK` / `PORT_ENV` / `DEFAULT_PORT` / `ROUTE_PREFIX` 四个常量
   （起草期实读 `127.0.0.1` / `AGENERP_SERVE_PORT` / `8330` / `/agenerp`）
   与 `agenerp/serve/__main__.py` 的 `main()` **把 `host=LOOPBACK` 写死**这一行
4. `tests/gates/conftest.py` 的 `_running_frontend_port()`（**只读，红线 1**）——
   起草期实读它要求 `Service == "frontend"` 且 `TargetPort == 8080`，**这是本 plan 最硬的一条外部约束**
5. `tests/gates/test_zero_dep_boot.py` 的三条（**只读**）与 `compose_stack.services()` 的
   「一次性容器豁免名单」（起草期实读 `{"configurator", "create-site"}`）
6. `tests/unit/test_compose_zero_dep.py` 的判据清单
   （起草期实读 **12 个 `test_` 函数 / 14 条 collected** —— `test_ai_variable_defaults_to_empty`
   参数化 ×3；⚠️ **两个数都要记**，只记一个会让「条数只增不减」对不上）
7. `tests/unit/test_explain_service_body.py` 的 `DEFAULT_SERVE_BASE`
   （起草期实读 `http://127.0.0.1:18080`）与 `TIMEOUT`（起草期实读 `30`）
8. `.github/workflows/gates.yml` 的 `gates-l2-live` job 里那**两处 `env:` 块**，
   **以及 `gates-l2-seed` 的 job 级 `env:` 块**（起草期实读 `:399-404`，
   含 `AGENERP_SITE_URL: http://127.0.0.1:8080`）——**逐字**（**只读，红线 2**）。
   起草期实读：`gates-l2-live` 不设 `AGENERP_HTTP_PORT`、不设 `AGENERP_SERVE_BASE`，
   `AGENERP_SITE=frontend` / `AGENERP_SITE_URL=http://127.0.0.1:8080` / `AGENERP_ADMIN_PASSWORD=admin`。
   ⚠️ **`gates-l2-seed` 那块是 job 级的**，会被它 `:419` 那步 `up -d --wait` 一并继承 ——
   这一条直接决定 `D-b-3` 能不能把回程地址写成 `${AGENERP_SITE_URL:-…}`
9. `docker-compose.yml` 的 `frontend` 服务块与 `x-erpnext-image` 锚点
   （起草期实读 `frappe/erpnext:v15.119.3`，`frontend` 发布 `127.0.0.1:${AGENERP_HTTP_PORT:-8080}:8080`）
10. `tests/unit/test_explain_service_body.py` 里那条 **503 分支上的 `pytest.skip`**
    （起草期实读 **`:201`**），**行号与原文逐字重取** —— §1.11 / §5.1 第 10 条 / **H7**
    三处都靠它；行号漂了要把三处一起对齐
11. `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 的**开工基线数字**
    （**起草期实跑**：`门禁 26 项：预期红 0，绿 26，跳过 0` / `✅ 与预期红名单完全一致`，exit **0**；
    `756 passed, 6 skipped in 8.83s`，exit **0** —— 与 `2026-08-25-1159-1` 收口时逐字相同。
    执行期若不同，照实记）

### 0.1 执行期重取基线的**实读结果**

（执行期填，一条不许留空；与起草期不同的用 ⚠️ 标出）

| # | 起草期 | **执行期实读** | 吻合 |
|---|---|---|---|
| 1 | — | sha `b072e484053c2444fb16d5de7b59e9bae59ddd9b`；`git status --porcelain` **三行**：`M tools/gates/expected-red.txt` · `?? docs/plans/p1-insight/2026-08-25-1423-1-…md`（本 plan）· `?? tests/gates/test_explain_service_live.py` | ⚠️ **不吻合** |
| 2 | 最大 §7.20，落 §7.21 | 最大仍是 **§7.20**（`:2971`），**§7.21 未被占用** ⇒ 本 plan 落 §7.21 | ✅ |
| 3 | `127.0.0.1` / `AGENERP_SERVE_PORT` / `8330` / `/agenerp`；`main()` 写死 `host=LOOPBACK` | `app.py:44/49/50/53` 逐字 `127.0.0.1` / `AGENERP_SERVE_PORT` / `8330` / `/agenerp`；`__main__.py` 逐字 `build_server(site=site, host=LOOPBACK, port=port)` | ✅ |
| 4 | `Service=="frontend"` 且 `TargetPort==8080` | `tests/gates/conftest.py:83-87` 逐字 `row.get("Service") != "frontend"` / `pub.get("TargetPort") == 8080` | ✅ |
| 5 | 三条 + 豁免名单两项 | `test_zero_dep_boot.py` 三个 `def test_`（`:22` / `:27` / `:33`）；`conftest.py:144` 逐字 `if name in {"configurator", "create-site"}` | ✅ |
| 6 | 12 funcs / 14 collected | `grep -c 'def test_'` → **12**；`--collect-only` → **14 tests collected** | ✅ |
| 7 | `http://127.0.0.1:18080` / `30` | `:64` `DEFAULT_SERVE_BASE = "http://127.0.0.1:18080"`；`:77` `TIMEOUT = 30` | ✅ |
| 8 | `gates-l2-live` 不设 `AGENERP_HTTP_PORT` / 不设 `AGENERP_SERVE_BASE`；`gates-l2-seed` job 级 `env:` 在 `:399-404` | `gates-l2-live` `:251` 起栈、`:266-268` 与 `:279-281` 两处 `env:` 只有 `AGENERP_SITE` / `AGENERP_SITE_URL` / `AGENERP_ADMIN_PASSWORD`，**无** `AGENERP_HTTP_PORT`、**无** `AGENERP_SERVE_BASE`；`gates-l2-seed` job 级 `env:` **`:399`**，三个变量 **`:402-404`**（含 `AGENERP_SITE_URL: http://127.0.0.1:8080`），其 `up -d --wait` 在 `:419` | ✅ |
| 9 | `frappe/erpnext:v15.119.3`；`127.0.0.1:${AGENERP_HTTP_PORT:-8080}:8080` | `:28-29` `x-erpnext-image: &erpnext_image` / `image: frappe/erpnext:v15.119.3`；`:285-286` `ports: - "127.0.0.1:${AGENERP_HTTP_PORT:-8080}:8080"` | ✅ |
| 10 | 503 分支的 `pytest.skip` 在 `:201` | `:201` 逐字 `pytest.skip("活栈上一个 AI 变量都没配 —— 503 已判，答案面留给配了的那次跑")` | ✅ |
| 11 | `预期红 0，绿 26，跳过 0` + `756 passed, 6 skipped` | `python3 tools/gates/check_expected_red.py` → `门禁 26 项：预期红 0，绿 26，跳过 0` / `✅ 与预期红名单完全一致`，exit **0**；`python3 -m pytest tests/unit -q` → `756 passed, 6 skipped in 8.39s`，exit **0** | ✅ |

⚠️ **第 1 行不吻合，展开照实记（这是本 plan 执行期最重要的一处基线变化）**：

- `?? tests/gates/test_explain_service_live.py`（81 行）与 `M tools/gates/expected-red.txt`（+14 行、六条判据名）
  **是人做的**，文件头与账本注释逐字写着 `Gates-Change-Approved-By: lize`、日期 `2026-08-25`。
- ⇒ §11 第一条 Deferred「`tests/gates/test_explain_service_live.py` 本体只能由人创建」的**承接者已经动手了**，
  **早于本 plan 开工**。它按路径加载 `tests/unit/test_explain_service_body.py`，正是交接说明写的形状。
- ⇒ 对本 plan 的影响，逐条：
  ① **红线 1 的处置不变**：该文件与其中任何一行**本 plan 一个字不碰**，
     也**不 `git add`、不提交**（提交它等于替人做「加载」这个动作）。它留在工作区里，
     §7 各 Phase 的 `git status --porcelain -- tests/gates/` 自证因此**会有一行 `??`** —— 照实记，不清理。
  ② `tools/gates/expected-red.txt` **不在红线 1 内**（红线 1 的「边界」段逐字：它是账本不是裁判）。
     但那 6 行是**人**加的、且带 `Gates-Change-Approved-By:`；本 plan **也不划掉它们** ——
     划掉的条件是「测试转绿」，而 §1.11 那条 skip 未拆之前它**不会绿**（零 skip 契约）。
     ⇒ 账本原样留着，处置写进 Phase 3 的 needs-human。
  ③ `check_expected_red.py` 在 default 模式下**实测仍是「26 项：预期红 0，绿 26，跳过 0」**、exit 0
     —— 那 6 行没有把本地判定器打红（default 模式不收集 `-m live`）。**基线第 11 行因此仍吻合。**
- §0 第 1 条那句「除本 plan 文件外无输出」**在执行期不成立**。起草期原文不改，此处照实记。

⚠️ **上面那段本身在 Phase 1 执行途中就过期了，照实记、不改写**（这是本轮的第二处基线变化）：
Phase 1 收口时复读 `git log`，发现**人在本 plan 开工之后又提交了两次**，两次都落在 `main` 上：

| sha | 时刻 | author | 做了什么 |
|---|---|---|---|
| `f09b8f0` | 15:10:05 | `lize` | `test(gates): 建 P1.8a 的活站点门禁` —— 把 `tests/gates/test_explain_service_live.py`（**87 行**，比 15:09 工作区里那份多 6 行）**提交进仓** |
| `24529ec` | 15:24:39 | `lize` | `docs: 登记 main 上的预期红` —— **把 `expected-red.txt` 那 6 行撤回了**，改成在 `STATE.md` §3 追加一条 `[open]` |

⇒ 逐条修正上面的记述：

1. **本 plan 的 Phase 1 提交 `ac2d456` 的父提交是 `f09b8f0`，不是基线那个 `b072e48`。**
   本 plan **没有** `git add` 过 `tests/gates/**` 的任何文件（那次 `git add` 只列了三个 docs 路径）；
   那个文件是**人自己提交的**。红线 1 的自证从「有一行 `??`」变成**真正的无输出**。
2. **`expected-red.txt` 现在与基线逐字相同（名单为空）**，上面「账本原样留着」那句已不适用 ——
   人撤回的理由逐字记在 `24529ec` 里，且是**实测出来的**：
   「该名单对 live 门禁**两种模式下都无效**（默认模式按标记排除 live 那批；live 模式逐字**不读预期红名单**）。
   live 门禁没有『预期红』档位，**要么绿要么红**」。
   ⇒ 本 plan **不划任何一行**，理由从「它还没绿」换成「**那本账上根本没有这一笔**」。
3. **人已裁定「就让它红着」**，并在 `STATE.md` §3 追加了 `[open] 2026-08-25T07:24Z`：
   `main` 上 `L2 全量 live 判定` 这一个 job 会持续红在那六条上、其余 13 个 job 全绿，
   **红因不是坏了**；人侧监控已收严成「只有当红的**不只是**这六条时才告警」。
   `24529ec` 的提交信息给 loop 写了三条，逐条照办：
   ① 不要去「修」那个门禁（红线 1 内且红得对）—— **本 plan 一个字未碰**；
   ② 不要因为 CI 红就停下或改判据 —— **本 plan 未停、未改任何判据的判定口径**；
   ③ 「第 2 个 plan 弄绿之后在同一提交里收掉 STATE 那条 open」——
   ⚠️ **这一条本 plan 做不到，且有两个各自独立的理由，都必须照实交出去**：
   **(a)** 把 `[open]` 改成 `[resolved]` 是**改写 STATE.md 的已有行**，红线 5 明禁（loop 只能追加）；
   **(b)** 更硬的一条：**那六条并不会全绿**。第 4 条在 503 分支上**自带 `pytest.skip`**（§1.11），
   而 `gates-l2-live` 起栈时一个 AI 变量都不配 ⇒ 它必然 skip，而契约是**零 skip**。
   ⇒ 本 plan 交付后，那个 job 的红因**从「六条全红」收窄成「五条转绿、第四条 skip」**，
   但**仍然是红的**。本 plan 按 §11 的写法把它**追加**进 STATE §3 的 needs-human，
   **不代人翻那一行的状态**。
   ⚠️ 注意 `24529ec` 的提交信息说「roadmap 里给 loop 写了三条」，但**实读该 commit 只改了
   `docs/masterplan/STATE.md`（2 行插入）**，`docs/backlog/p1-insight-roadmap.md` 未被触及。
   照实记，不代改（roadmap 的工作项 10 那一行由本 plan 的 Phase 3 按自己的职责回写）。

**另一条执行期实读（Phase 3 的前置）**：`docker compose ps` —— 栈在不在跑、`frontend` 发布在哪个端口。
**观测出来的事实，不是配置出来的期望**（口径抄 `tests/gates/conftest.py` 的同名教训）。

**实读**（`docker compose ps --format '{{.Service}}\t{{.State}}\t{{.Health}}\t{{.Publishers}}'`）：
栈**在跑**，长期运行服务**九个**全部 `running`（`backend` / `db` / `frontend` / `redis-cache` /
`redis-queue` / `websocket` 六个 `healthy`；`queue-long` / `queue-short` / `scheduler` 三个无探针，
按 `conftest.services()` 的口径折算成运行状态）。
`frontend` 的发布口实读 **`{127.0.0.1 8080 18080 tcp}`** ⇒ **宿主侧 18080 → 容器侧 8080**。
⚠️ 仓根 `.env` 里**没有** `AGENERP_HTTP_PORT` —— 这套栈是**用当时 shell 里的 `AGENERP_HTTP_PORT=18080` 起的**，
所以 `18080` 是**观测到的事实**，不是本仓配置的期望值。§1.6 那条「默认值只对起草者那台机器成立」
在执行期**再次被同一台机器证实**。

## 1. Current Baseline

### 1.1 第 1 个 plan 交下来的东西，是本 plan 的输入，不重做

`agenerp/serve/` 三个模块已在仓里（`__init__.py` / `__main__.py` / `app.py`）：
`python3 -m agenerp.serve` 起标准库 `ThreadingHTTPServer`，两条端点
`GET /agenerp/health`（不认人、不碰 LLM、不打站点，恒 200）与 `POST /agenerp/explain`（认人）。
离线判据 `tests/unit/test_explain_service.py` **59 条**全绿。
**本 plan 不改这三个模块的任何既有行为**，只补一格：监听地址（§7 `D-b-4`）。

### 1.2 今天这个服务**没有任何东西在起它**，也没有任何东西反代它

- `docker-compose.yml` 实读**十二个服务**（`db` / `redis-cache` / `redis-queue` / `configurator` /
  `create-site` / `bootstrap-homepage` / `backend` / `websocket` / `queue-short` / `queue-long` /
  `scheduler` / `frontend`），**没有 `agenerp-serve`**。其中**长期运行的九个**
  （`db` / `redis-cache` / `redis-queue` / `backend` / `websocket` / `queue-short` /
  `queue-long` / `scheduler` / `frontend`）落进零依赖启动门禁的判定面；
  一次性的三个（`configurator` / `create-site` / `bootstrap-homepage`）不落 ——
  前两个由 `conftest.py` 的豁免名单排除，第三个跑完即退且被 `frontend` 以
  `service_completed_successfully` 依赖。
- `frontend` 容器里 `/etc/nginx/conf.d/frappe.conf` 由 `nginx-entrypoint.sh` 用
  `envsubst` 从 `/templates/nginx/frappe.conf.template` 生成，**没有 `location /agenerp/`**。
- ⇒ 第 1 个 plan 交付的十条判据**全部离线**；`02-WBS.md` §4 P1.8a 的验收
  （`pytest -m live tests/gates/test_explain_service_live.py` 退 0 + 零依赖启动门禁仍绿）
  **两条今天都不成立**。roadmap 工作项 10 因此刻意仍是 `todo`。

### 1.3 `main()` 把监听地址写死在回环上 —— 这是本 plan 的第一个硬缺口

`agenerp/serve/__main__.py` 的 `main()` 实读 `build_server(site=site, host=LOOPBACK, port=port)`，
`LOOPBACK = "127.0.0.1"` 是模块常量、**没有任何环境变量能改它**。
容器里绑 `127.0.0.1` 等于**只有它自己连得上** ⇒ nginx 那一跳到不了。
⚠️ 这不是「实现漏了一格」，是 §7.20 `D-a-1` 逐字写下的取舍：
「本期服务只绑 `127.0.0.1`、不出宿主……**它一旦要对本机之外提供，这一条就必须重开**」。
⇒ **本 plan 就是那次重开**，必须在 `D-b-4` 里逐条裁定，不许顺手改掉了事。

### 1.4 `frontend` 这个服务名与那格 `8080` 发布口**不能动**（红线 1 的间接约束）

`tests/gates/conftest.py` 的 `_running_frontend_port()` 逐字要求
`row["Service"] == "frontend"` 且 `pub["TargetPort"] == 8080`，
`compose_stack` fixture 拿它算 `base_url`。⇒ **任何「把对外端口挪到一个新的前置 nginx 上」的方案，
都会让 `tests/gates/` 下所有走 `compose_stack` 的门禁连不上**，而修那份 conftest 在红线 1 内。
⇒ 同源那一跳**只能长在 `frontend` 容器自己的 nginx 里**（`D-b-1` 的候选集因此先被砍掉一半）。

### 1.5 零依赖启动门禁的判据面**因 D-19 变宽了**，本 plan 是第一个吃这个代价的

D-19「代价照实记」逐字：「多一个要运维的进程……零依赖启动门禁的判据面随之变宽 ——
**新服务必须也能在『一个 AI 变量都不配』时起得来**」。
`tests/gates/test_zero_dep_boot.py::test_stack_boots_and_all_services_healthy` 判的是
**全部长期运行服务 healthy**，豁免名单实读只有 `{"configurator", "create-site"}`
⇒ **新服务一旦进 compose，它就自动进了那条门禁的判定面**，且**没有任何办法把它豁免掉**
（改 conftest 的豁免名单在红线 1 内）。这是本 plan 最容易翻车的一格，写在最前面。

⚠️ **爆炸半径不止那一条门禁**：`.github/workflows/gates.yml` 实读**三处** `up -d --wait`
（`:189` `gates-l2` · `:251` `gates-l2-live` · `:419` `gates-l2-seed`），触发是 `push: branches: [main]`
⇒ **一个起不来或不 healthy 的新服务，会把三个 CI job 一起红在「起栈」这一步上**，
而 `AGENTS.md` 裁判规则 4 的停机条件里就有「**CI 连续 2 轮红**」。处置见 §5 的**回退义务**。

### 1.6 `tests/unit/test_explain_service_body.py` 的默认基址与 CI 实际端口对不上（**确认的漂移**）

- 断言体实读 `DEFAULT_SERVE_BASE = "http://127.0.0.1:18080"`；
- `.github/workflows/gates.yml` 的 `gates-l2-live` **不设** `AGENERP_HTTP_PORT`
  ⇒ compose 走默认，`frontend` 发布在 **`127.0.0.1:8080`**；该 job 也**不设** `AGENERP_SERVE_BASE`。
- ⇒ 人一旦把断言体按路径加载进 `tests/gates/` 并按交接说明把 `skip` 改成 `fail`，
  **CI 上那六条会红在「连不上 18080」**，而不是红在实现。
  修法若走「给 job 加一行 env」就落进红线 2（且要人批），
  而**本 plan 完全可以在红线外把它修直**：默认基址改成与 `agenerp/site.py` `default_base_url()`
  **同一套解析**（`AGENERP_SERVE_BASE` > `AGENERP_SITE_URL` > `http://127.0.0.1:${AGENERP_HTTP_PORT:-8080}`）。
- **`18080` 不是随手写错的一个数**：起草期 `docker compose ps` 实读本机栈的 `frontend` 发布在
  `127.0.0.1:18080`，断言体文件头那段交接说明的示例命令用的正是它。
  ⇒ 这是**「默认值只对起草者那台机器成立」**，不是「有人抄错了」。
  新口径对**两边都成立**：本机跑时显式给 `AGENERP_SERVE_BASE=http://127.0.0.1:18080`；
  CI 的 `gates-l2-live` 已有的 `AGENERP_SITE_URL=http://127.0.0.1:8080` 直接命中第二级。
  **文件头示例命令一并对齐，不留一处指着 18080 却不说明前提的写法。**
- 按 `00-plan-authoring-and-execution-guide.md` Minimum Rule 14，**确认的契约漂移必须是 `Fix`，
  不许降级成 `Follow-up`**。

### 1.7 nginx 那一跳的可注入点，起草期实读结果

`frontend` 容器内实读（只读探测，未改动任何运行中的容器）：

- `nginx -v` → **nginx/1.22.1**（与 D-19 记的一致）；
- `/etc/nginx/conf.d/` 只有一个 `frappe.conf`，由 `nginx-entrypoint.sh` **每次启动时重新生成**
  （`envsubst '<八个变量>' </templates/nginx/frappe.conf.template >/etc/nginx/conf.d/frappe.conf`
  —— 实读逐字为 `BACKEND` / `SOCKETIO` / `UPSTREAM_REAL_IP_ADDRESS` / `UPSTREAM_REAL_IP_HEADER` /
  `UPSTREAM_REAL_IP_RECURSIVE` / `FRAPPE_SITE_NAME_HEADER` / `PROXY_READ_TIMEOUT` / `CLIENT_MAX_BODY_SIZE`。
  ⚠️ **`envsubst` 只替换这份清单里的名字**，`$host` / `$uri` / `$scheme` 等**原样留下** ——
  这一条是候选 (A) 能不能成立的前提，起草期已在容器内实证）；
- 模板里 `server { listen 8080; server_name ${FRAPPE_SITE_NAME_HEADER}; … }` **只有一个 server 块**，
  内含 `location /assets` / `location ~ ^/protected/` / `location /socket.io` / `location /` /
  `location @webserver`；
- `/etc/nginx/snippets/` 下有三个文件（`security_headers.conf` / `fastcgi-php.conf` / `snakeoil.conf`），
  但模板里**只 `include` 了 `security_headers.conf` 一个**，且 `include` 了**两处**
  （server 块内一处、`location ~ ^/files/…` 内一处）。⚠️ **另两个片段没有被任何地方 include**
  —— 起草期原文曾写成「三个片段被 server 块 include」，**实读不成立，此处改直**。
  ⚠️ **那第二处 `include` 在一条 regex location（`~ ^/files/.*`）之内** ⇒ 候选 (D)
  （往被 `include` 的片段里塞一段 `location`）不是「不优雅」，是**会让整个 `frontend` 起不来**：
  容器内实测 `nginx -t` 逐字
  `[emerg] location "/agenerp/" is outside location "^/files/.*.(htm|html|svg|xml)"`，退 **1**。
  `D-b-1` 否决 (D) 时**照抄这条实测**，不许写成推测。

⇒ **要加一条同源 `location`，就必须让那个 server 块里多出一段**；
`conf.d` 下另放一个文件只能生成**第二个 server 块** —— 同 `listen` / 同 `server_name` 时
nginx **不报错**：容器内实测逐字 `[warn] conflicting server name … ignored`，
而 `nginx -t` 仍退 **0**，第二个 server 块被**静默丢弃**。
⇒ **做不出同源，且失败形态是「配置测试全绿、反代根本不存在」**，比报错更难发现。
候选与否决逐条见 `D-b-1`。

### 1.8 `agenerp` 包不在镜像里 —— 代码怎么送进容器是一格必须裁定的事

`frappe/erpnext:v15.119.3` 里 `python3 -V` 实读 **3.11.6**，
`python3 -c "import certifi"` 实读 **可导入**（`/usr/local/lib/python3.11/site-packages/certifi/`）
⇒ 镜像自带的解释器**满足 `pyproject.toml` 的 `requires-python >= 3.11`，也满足本仓唯一那条运行期依赖**。
但 `agenerp/**` **不在镜像里**（这正是 `0119-1` §1.7 那条「(iii) 是唯一合规选项」的实读理由）。
⇒ 送达方式在 `D-b-2` 裁定。

### 1.9 回程：服务要打站点，而站点按 Host 分站

`agenerp/site.py` 的 `default_base_url()` 实读：`AGENERP_SITE_URL` 优先，否则
`http://127.0.0.1:${AGENERP_HTTP_PORT:-8080}` —— **容器里那个 `127.0.0.1` 是错的目标**。
而 `docker-compose.yml` 的 `backend` 块注释逐字：「Host 头不能省：gunicorn 按 Host 解析站点，
打 127.0.0.1 会被当成一个叫 127.0.0.1 的站点而 404」。
`SiteClient` 今天**没有自定义 Host 头的入口**。⇒ 回程地址在 `D-b-3` 裁定。

### 1.10 红线与判据设施的既有形状（与第 1 个 plan 同，只列不重述）

- `tools/gates/expected-red.txt` 名单为空；`gates-l2-live` 的契约是「全部绿、零 red、零 skip」。
- ⇒ 本 plan **不创建 `tests/gates/**` 下任何文件**（红线 1），也**不改 `.github/workflows/**`**（红线 2）。
- `pyproject.toml` 的 `[tool.ruff]` 用 `exclude` + `force-exclude` 把 `tests/gates` 挡在 ruff 之外。

### 1.11 断言体第 4 条**自己带一个 `skip`**，而门禁契约是零 skip —— 这一格只有人能拆

**这是本 plan 起草期查出的、此前无人登记的一条**，比 §1.6 那处漂移更硬：

- `tests/unit/test_explain_service_body.py:201` 逐字 `pytest.skip("活栈上一个 AI 变量都没配 …")`
  —— 它在 **503 分支**上，即「站点认了人、服务也回了 503 并指名缺哪个变量」之后**跳过**答案面；
- `tools/gates/check_expected_red.py` 的 live 契约逐字「**全部门禁绿、零 red、零 skip**」
  （`:11` / `:142` / `:150`），**任何一条 skip 都让判定器退 1**；
- `.github/workflows/gates.yml` 的 `gates-l2-live` 起栈时**一个 AI 变量都不配**（`:250`）。

⇒ **即便 §1.6 那处默认基址修直，人一按路径加载，`gates-l2-live` 仍会红在这一条 skip 上。**
出路只有两条，**两条都是人的**：
① 给 `gates-l2-live` 补 `AGENERP_LLM_*`（改 `.github/workflows/**`，红线 2）；
② 把 503 分支从 `skip` 改成 `pass`（**那是在改判据自身的口径** ——
改完之后，一次**从未真正调过模型**的跑也能让门禁绿，正是硬约束① 要挡的「跑了且过」）。

⚠️ **本 plan 不选、不试探、不替人预选**。它进 §5.1 见即停清单第 10 条，
并在 Phase 3 作为一条 `[needs-human]` 交出去。
⇒ **本 plan 能做到的上限是「五条 passed + 那一条 skip」**，§2 Goal 4 与 §6 H7 已按这个上限写死，
**不写成「加载后就能绿」**。

## 2. Goals

1. **解释服务作为 compose 的一个服务跑起来**，`docker compose up -d --wait`
   在**一个 AI 变量都不配**的空环境下退 0，且**全部长期运行服务 healthy**（含新服务自己）。
2. **同源那一跳真的在**：经 `frontend` 的对外端口 `GET /agenerp/health` 回 200，
   判据用**真 HTTP 请求经 nginx** 证明，不是「配置文件里有那一行」。
3. **`client_from_sid()` 在活站点上第一次被证明认得出人** —— 承接第 1 个 plan
   `Deferred But Adjudicated` 第二条（重开事件逐字「第 2 个 plan 起栈的那一刻」）。
4. **`tests/unit/test_explain_service_body.py` 的前三条与后两条（共五条）在活的同源栈上 `passed`**；
   **第 4 条在未配 AI 的栈上按它自己的口径 `skip`，本 plan 照实记、不改它一个字**（§1.11）。
   同时把 §1.6 那处**确认的漂移**修直。
   ⚠️ **本 plan 不声称「人一加载就能绿」** —— §1.11 那条 skip 与门禁的零 skip 契约冲突，
   拆它的两条出路**都是人的**。
5. **监听地址成为可配置的一格，且默认仍是回环**：判据要能挡住「默认就对外」这种假实现，
   不只是「配了 `0.0.0.0` 能通」。
6. **零依赖启动的既有判据一条不许变松**：`tests/unit/test_compose_zero_dep.py` 全绿，
   并为新服务**补**静态判据（不发布宿主端口 / 插值带默认 / AI 变量不进 healthcheck /
   镜像 tag 不浮动 / nginx 上游端口与 compose 侧逐字一致）。

## 3. Non-Goals

1. **不创建 `tests/gates/**` 下任何文件**（红线 1）；`tests/gates/test_explain_service_live.py`
   仍只能由人按路径加载。本 plan 交付的是**它加载所需的活栈与同源那一跳**，
   **不是**「加载后就能绿」（§1.11 那条 skip 未拆之前它不会绿，拆它归人）。
2. **不改 `.github/workflows/**` 一个字**（红线 2）—— §1.6 的漂移在红线外修直，不靠改 job。
3. **不做 Desk 侧边栏、不做 ⌘K、不写任何前端资源** —— 那是工作项 11（P1.8b）。
4. **不新增任何第三方依赖**（`pyproject.toml` 的 `dependencies` 一个字不加），
   **也不新增任何镜像**（新服务复用已钉死的 `frappe/erpnext:v15.119.3`）。
5. **不做写操作**：②端只读，服务面不新增任何写路径；对活站点零写。
6. **不 `bench install-app` / 不 `bench new-app` / 不建 DocType / 不改权限 / 不改 Workflow**
   —— 一格风险档 L3 都不碰。
7. **不做 TLS、不做限流、不做连接池、不做异步/流式回包**（§7.20 `D-a-1` 残余风险原样继承，
   只重开「绑哪个地址」这一格）。
8. **不向宿主发布解释服务的端口** —— 对外只有 `frontend` 既有那一格。
9. **不改 `agenerp/explain/**` 与 `agenerp/serve/app.py` 的任何既有行为**
   （`app.py` 只允许**新增**一个监听地址常量/参数，不许改既有分支）。
10. **不声称跑过 `pytest -m live tests/gates/test_explain_service_live.py`** —— 那个文件不存在，
    建它在红线 1 内。本 plan 跑的是它的**断言体**。

## 4. Task Route

- Type: `app-layer design change`（含 deployment 面：`docker-compose.yml` 与 nginx 配置）
- Owner Docs: `docs/architecture/module-boundaries.md`（落点 **§7.21**，本 plan 的主写入面）·
  `docs/architecture/system-baseline.md` **§14 族**（零依赖启动的三条写作规则**只读引用**；
  是否需要就地追加一节由 `D-b-7` 裁定）· `docs/masterplan/DECISIONS.md` **D-19（只读，红线 3）**
- 保护区核对（`docs/context/ai-autonomy-policy.md` Protected Areas 逐行扫）：
  `docker-compose.yml` **不在表内** ⇒ 默认 `implement`；本 plan 触及的
  `tests/gates/**` / `.github/workflows/**` / `docs/masterplan/**` 三处**全部只读**。
  「对活站点的写」两行**不触及**（本 plan 对站点零写）。
- Skill Selection Basis: `docs/skills/README.md` 无 compose / nginx 条目 ⇒ 各 Phase 一律 `Skill: none`；
  方法论纪律由 §6 的预注册假设与 Phase 3 的变异自查承担。

## 5. Infrastructure And Config Prereqs

- **不新增基础设施依赖**：不拉新镜像、不加新卷、不加新对外端口。
- **新增一个 compose 服务**与**一处 nginx 配置注入**（形态由 `D-b-1` / `D-b-2` 裁定）。
- **活栈是 Phase 3 的硬前置**。栈起不来或同源那一跳复现不出来时的处置**在此写死**：
  按裁判规则 3「复跑优先于分析」原样复跑一次；仍不出来就记「**不可复现**」、
  **不猜根因**、把该条写进 `STATE.md` §3 needs-human，
  并**把接线 `git revert` 掉之后再收口**（见下一条；Phase 1/2 的**离线**判据仍算数，
  Phase 3 整体转 `Deferred But Adjudicated`）。
- ⚠️ **回退义务（起草期写死，不是执行期现编）**：走上面那条分支时，
  **`docker-compose.yml` 与 nginx 的那两处接线必须 `git revert` 掉再收口，不许留在 `main` 上**。
  理由是**可观测的**，不是保守：`.github/workflows/gates.yml` 的
  `gates-l2` / `gates-l2-live` / `gates-l2-seed` **三个 job 的第一步都是 `up -d --wait`**，
  一个起不来或不 healthy 的新服务会把三条 L2 链一起打红在「起栈」这一步上；
  而 `AGENTS.md` 裁判规则 4 的停机条件里就有「**CI 连续 2 轮红**」。
  **离线判据（Phase 2 的那九条）可以留**——它们不依赖活栈，也不会让任何 job 红。
- **回滚**：本 plan 的产物是 ① `docker-compose.yml` 增一个服务块 + `frontend` 增一处挂载与依赖；
  ② 一个新增的 nginx 配置文件；③ `agenerp/serve/` 增一格监听地址；④ 新增/修改若干 `tests/unit/`。
  **全部可 `git revert`**；站点侧**零残留**（不写站点、不装 app、不改 site_config）。

### 5.1 见即停清单（起草期写死，执行期不许现编）

遇到下列任一，**当场停下、写进 `STATE.md` §3 needs-human、不试探**：

1. 任何要改 `tests/gates/**` 的冲动（红线 1）—— **包括**「把新服务加进 `conftest.py` 的豁免名单」
2. 任何要改 `.github/workflows/**` 的冲动（红线 2）—— **包括**「给 `gates-l2-live` 加一行 env」
3. 任何 `bench install-app` / `bench new-app` / `bench set-config` / `bench build`
4. 任何往 `site_config.json` / `common_site_config.json` 写东西的动作（那是 §7.13 (E)，判定为停机交人）
5. 任何 `pip install` 新包 / 往 `pyproject.toml` 加依赖（Non-Goal 4）
6. 任何把解释服务端口发布到宿主的动作（Non-Goal 8）
7. 任何让服务暴露写路径的设计（Non-Goal 5）
8. 任何把真 `sid` 值写进文件、日志、证据、提交信息的动作
9. 任何要动 `frontend` 这个**服务名**或它那格 `TargetPort 8080` 发布口的方案（§1.4）
10. 任何要动 `tests/unit/test_explain_service_body.py:201` 那条 `pytest.skip`（503 分支）的冲动 ——
    **那是在改判据自身的口径**（§1.11），两条出路都归人。⚠️ **注意与 §1.6 那处 `Fix` 的边界**：
    改「去哪里判」的默认基址是本 plan 的活；改「判成什么」的任何一行**不是**

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下面每一条在开工前已写死，执行期只填「实测」列，不许回头改预测。**
**不吻合的照实记，预测原文一个字不改。**

| # | 预测 | 怎么验（命令原文） | **执行期实测** |
|---|---|---|---|
| **H1** | 新服务进 compose 后，空环境下 `docker compose config -q` **仍退 0** | `env -i PATH=$PATH HOME=$HOME docker compose -f docker-compose.yml config -q; echo $?` | ✅ **吻合**。exit **0** |
| **H2** | 冷起栈后**全部长期运行服务 healthy**，其中包含 `agenerp-serve` | `docker compose ps --format '{{.Service}}\t{{.Health}}'` | ✅ **吻合**。`down -v` → `up -d --wait --wait-timeout 900` 退 **0**，墙钟 **100 秒**。十个长期运行服务全 `running`，其中 `agenerp-serve` / `backend` / `db` / `frontend` / `redis-cache` / `redis-queue` / `websocket` 七个 `healthy`，`queue-long` / `queue-short` / `scheduler` 三个无探针（与基线同，按 `conftest.services()` 口径折算）|
| **H3** | 经 `frontend` 对外端口 `GET /agenerp/health` → **200**，且 body 里 `service == "agenerp-explain"` | `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<实测端口>/agenerp/health` | ✅ **吻合**。实测端口 **18080**。`curl -H 'Host: frontend' …/agenerp/health` → **200**，body 逐字 `{"status": "ok", "service": "agenerp-explain"}`。**旁证**：同一跳 `/api/method/ping` 仍 **200** —— 加的前缀 location 没遮住既有路由 |
| **H4** | **不带任何 cookie** 打 `POST /agenerp/explain` → **401** | 同上路径，`-X POST` | ✅ **吻合**。**401**，body 逐字 `{"error": "未认到人：请求里没有可用的 sid，或站点不认它"}` |
| **H5** | **伪造 `sid`** 打 `POST /agenerp/explain` → **401**，且回包里**不出现**那个伪造值 | 断言体第 3 条 | ✅ **吻合**。**401**，`grep -c deadbeef` → **0**；断言体第 3 条 `PASSED` |
| **H6** | **真 `sid`** 打 `POST /agenerp/explain` → **200 或 503**；在**未配 AI** 的栈上走的是 **503** 分支，且**在 30 秒内返回**（断言体 `TIMEOUT = 30`） | 断言体第 4 条 | ✅ **吻合**。**503**，墙钟 **0.02 秒**（远在 30 秒内）。body 逐字指名缺哪几个变量：`模型端点配置不全，缺：['AGENERP_LLM_BASE_URL', 'AGENERP_LLM_API_KEY']…`。回包里**不含**真 `sid`。⚠️ **一处照实记的偏差**：缺的变量名实测是 `AGENERP_LLM_BASE_URL`，而 §1.11 / `x-ai-env` 锚点里写的是 `AGENERP_LLM_ENDPOINT` —— 仓根 `.env` 里有 `AGENERP_LLM_MODEL=qwen3.6-plus`，故三缺二。**本 plan 不改这处命名分歧**（不在结果面内），只记 |
| **H7** | 断言体实测 **5 passed, 1 skipped** —— skip 的**必须是且只能是**第 4 条（`test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`），理由是它 503 分支上**自带**的 `pytest.skip`（§1.11）。**若实测 6 passed**，说明环境配了 AI 变量，按 K5 记；**若 skip 的是别的条**，说明同源那一跳没通，按 §5 的回退义务处置 | `AGENERP_SERVE_BASE=… AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/unit/test_explain_service_body.py -q -rs` | ✅ **逐字吻合**。**`5 passed, 1 skipped`**，exit **0**。`-v` 实读 skip 的**正是第 4 条** `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`，其余五条 `PASSED`。skip 理由逐字 `活栈上一个 AI 变量都没配 —— 503 已判，答案面留给配了的那次跑`，位置 **`tests/unit/test_explain_service_body.py:223`**（起草期实读 `:201`，⚠️ **行号漂了 22 行** —— 本 plan 的 `D-b-5` 改写了文件头交接说明，**那条 `skip` 本身一个字未动**）。**M8 之后原样复跑一次，逐字相同。****另跑一次不给 `AGENERP_SERVE_BASE`、只给 `AGENERP_SITE_URL`**（模拟 `gates-l2-live` 的形状）→ 同样 `5 passed, 1 skipped` ⇒ `D-b-5` 的第二级解析在 CI 那种形状上成立 |
| **H8** | 服务在容器里**绑的不是回环**（否则 nginx 到不了），而**默认值仍是回环** —— 两句同时成立 | 离线判据 + `docker compose exec agenerp-serve …` 实读监听地址 | ✅ **两句都成立**。容器内 `/proc/net/tcp` 实读 `00000000:208A` ⇒ **LISTEN 0.0.0.0:8330**；服务自报日志逐字 `agenerp explain service listening on http://0.0.0.0:8330`。默认那半由离线判据④ 承担（`resolve_host({}) == "127.0.0.1"`，`1 passed`）。**旁证**：宿主上 `curl http://127.0.0.1:8330/agenerp/health` → **connection refused（curl exit 7）**，且 `docker compose ps` 里发布到宿主的只有 `db` / `frontend` / `redis-cache` / `redis-queue`，**没有 `agenerp-serve`** ⇒ 「绑 0.0.0.0 ≠ 对本机之外提供」这句有实测支撑，不只是论证 |
| **H9** | `pyproject.toml` 的 `dependencies` **一个字未变** | `git diff -- pyproject.toml` → 无输出 | ✅ **吻合**。**0 行** |
| **H10** | 本 plan **新增**的 `agenerp/**/*.py` 文件数 **为 0**（只改既有文件的一格监听地址，不新增模块） | `git ls-files --others --exclude-standard -- 'agenerp/**/*.py'` → **0 行**（⚠️ **不用** `git status --porcelain -- 'agenerp/**'`：它把计划内的 `M` 行也报出来，永远不会是「无输出」，量不出「新增几个」） | ✅ **吻合**。**0 行**。本 plan 对 `agenerp/**` 的改动只有 `serve/__main__.py` 一个文件的一格监听地址 |
| **H11** | `tests/gates/**` 与 `.github/workflows/**` 的 `git status --porcelain` **无输出** | 同左 | ✅ **吻合**。**无输出**。⚠️ 基线时它**有**一行 `?? tests/gates/test_explain_service_live.py`，那是**人**放的；人已于 `f09b8f0` 自行提交，故执行期真的是无输出（见 §0.1 第 1 行的展开）|

⚠️ **H6 的两半必须分开读**：「200 或 503」是断言体自己的口径（它不判答案对不对）；
「未配 AI 时走 503」是**本 plan 的预测**。若实测走的是 200，说明执行环境**配了 AI 变量** ——
那不是断言体错了，是**判据跑在了一个不是 CI 那个的环境上**，必须在实测列逐字记明。

## 7. Execution Plan

### Phase 1 — 先裁定，后写配置（`D-b-1` … `D-b-7`）

Status: completed
Targets: `docs/architecture/module-boundaries.md`（新增 **§7.21**）
Skill: `none`

- Item Types: `Decision`（7 项全部是 `Decision`，**Decision-uniform phase**）
- Prereqs: §0 十一处重取完成

- [x] `Decision` **`D-b-1` 同源那一跳注入到哪里**。候选**至少**四条，逐条给否决/选中理由，
      **每条都要指着 §1.4 / §1.7 的实读说话，不许引起草期推测**：
      (A) 覆盖 `frontend` 的 `/templates/nginx/frappe.conf.template`（fork 上游模板，加一段 `location` + 一段 `upstream`）·
      (B) 往 `/etc/nginx/conf.d/` 再放一个文件（**第二个 server 块**）·
      (C) 新起一个前置 nginx 服务、把对外端口挪过去 ·
      (D) 覆盖被 server 块 `include` 的 `snippets/*.conf` 之一 ·
      **(E) 不 fork 模板**：把 `frontend` 的 `command:` 换成仓内一个小 wrapper ——
      原样跑上游那条 `envsubst`（**模板一个字不动**），再把一段 `location` 追加进生成出来的
      `/etc/nginx/conf.d/frappe.conf`，最后 `exec nginx -g 'daemon off;'`。
      ⚠️ **(A) 与 (E) 必须逐条对比代价，不许只列不比**：(A) 的代价是「在本仓维护一份上游文件的副本」（K3）；
      (E) 的代价是「启动路径上多一段 loop 写的 shell」。**取哪条都要写明为什么另一条更贵。**
      **选中项必须同时满足三条**：① 与 `agenerp/serve/app.py` 的 `ROUTE_PREFIX` **逐字一致**；
      ② **不动** `frontend` 服务名与 `TargetPort 8080` 发布口（§1.4）；
      ③ **代价照实记** —— 若选中项等于在本仓维护一份上游文件的副本，
      必须逐字写明它钉在哪个镜像 tag 上、升级镜像时要一起看哪几行（口径抄 D-19「代价照实记」与 R-5）
- [x] `Decision` **`D-b-2` `agenerp` 包怎么送进容器**。候选：
      (i) bind mount 仓内 `agenerp/` 到镜像里一个路径 + `PYTHONPATH` ·
      (ii) 新建一个 `Dockerfile` 把包 `COPY` 进去 · (iii) 起容器时 `pip install` 本仓。
      **判据面**：选中项必须让 `docker compose up` 在**只有 `git clone` 的机器上**成立（零依赖），
      且**不引入新镜像 tag**（Non-Goal 4）。挂载路径**字面写死、不许经变量**
      （理由抄 `docker-compose.yml` §14.1 那条：仓根 `.env` 能在 config 时把变量改掉，
      而单测是静态文本扫描，管不到 `.env`）。
      ⚠️ **同一条理由外推到另外两个值**：**上游端口**（`AGENERP_SERVE_PORT`）与
      **回程地址**（`D-b-3`）**同样字面写死、不许经 `${…}`** ——
      判据③ 匹配的就是 compose 侧那个端口值，写成插值形式时仓根 `.env`
      能在 `config` 时把它改掉而判据看不见（仓根实读**存在** `.env`）；
      判据③ 因此**额外断言那个端口值不是插值形式**
- [x] `Decision` **`D-b-3` 服务打站点的回程地址**。候选：
      (i) `http://frontend:8080`（经 nginx，`FRAPPE_SITE_NAME_HEADER` 由它加）·
      (ii) `http://backend:8000` + 自定义 `Host`/`X-Frappe-Site-Name` 头（**要改 `SiteClient`**）。
      **必须回答的两个问题**：① 会不会与 `frontend depends_on agenerp-serve` 构成 **compose 依赖环**
      （逐字写出为什么不构成，或写出怎么破环）；
      ② 选 (ii) 的话，改 `SiteClient` 是否越出本 plan 的 Non-Goal 9，越出就不许选；
      ③ **回程地址必须字面写死在容器侧，不得写成 `${AGENERP_SITE_URL:-…}`** ——
      `gates-l2-seed` 的**job 级** `env:`（§0 第 8 条）会在它那步 `up -d --wait` 时
      把它插成 `http://127.0.0.1:8080`，**容器于是打自己**；
      而 `/agenerp/health` 恒 200 ⇒ **healthcheck 与 `up --wait` 照样绿，只有 `/agenerp/explain` 静默打不到站点**
- [x] `Decision` **`D-b-4` 监听地址这一格怎么开**（§7.20 `D-a-1` 残余风险的**正式重开**）。
      必须逐字写明：① 新变量名与**默认值仍是回环**；② 为什么「容器内绑 `0.0.0.0`」
      不等于「对本机之外提供」（compose 侧**不发布该端口**是这条论证的**唯一支点**，
      因此它必须有一条静态判据守着，见 Phase 2）；③ 被否决的备选
      （例如「直接把 `LOOPBACK` 改成 `0.0.0.0`」——它会让**宿主上手工起的服务默认对外**，
      是一次静默的暴露面扩大）
- [x] `Decision` **`D-b-5` 断言体默认基址的解析口径**（§1.6 那处**确认的漂移**）。
      必须写明新口径与 `agenerp/site.py` `default_base_url()` **同一套**，
      并逐字写出「为什么这不是把判据迁就环境」——
      **判的东西一个字没变，变的只是『去哪里判』的默认值**，
      而那个默认值此前指着一个 CI 上根本不存在的端口
- [x] `Decision` **`D-b-6` 新服务的 healthcheck 形状**。必须满足：
      ① 不含任何 `AGENERP_LLM_*`（`tests/unit/test_compose_zero_dep.py::test_ai_vars_absent_from_healthchecks`）；
      ② 打的是 `/agenerp/health` 而**不是** `/agenerp/explain`（后者认人、碰站点，
      拿它做探针等于让「AI 未配置」把服务判成不健康 —— 正是 `docker-compose.yml` 规则 ② 要挡的）；
      ③ 写明 `start_period` / `retries` 的取值依据，**不许抄一个数不说理由**
- [x] `Decision` **`D-b-7` 本 plan 的风险档自评与 owner doc 落点**。
      逐条对 `docs/design/agents-and-roles.md` §9 **风险档表**（L0–L3）自评并给理由；
      同时裁定 `system-baseline.md` §14 族**要不要就地追加一节**
      （判据：本 plan 是否新增了一条「compose 写作规则」。是则追加，否则只在 §7.21 记，
      **不许两处各写一半**）

Exit Criteria:

- [x] §7.21 存在，`D-b-1` … `D-b-7` 七条**逐条**有「选中项 + 备选 + 否决理由 + 残余风险」四段
- [x] `D-b-1` 的选中项与 `ROUTE_PREFIX` 逐字一致这件事，在 §7.21 里有**可复核的引用**（文件 + 行）
- [x] `docs/masterplan/DECISIONS.md` **一个字未改**（红线 3）——`git diff` 自证
- [x] `docs/logs/` 更新

### Phase 2 — 落地接线 + 离线判据（不需要活栈就能判的那一半）

Status: completed
Targets: `docker-compose.yml` · `agenerp/serve/`（只加监听地址一格）·
`tests/unit/test_explain_service_body.py`（`Fix`：默认基址）· `tests/unit/`（新增判据）·
`D-b-1` 选中项落地处（nginx 配置文件，路径由 `D-b-1` 定）
Skill: `none`

- Item Types: `Add | Fix | Proof`
- Prereqs: Phase 1 七条 Decision 全部落 §7.21

- [x] `Add` **compose 增 `agenerp-serve` 服务**（按 `D-b-2` / `D-b-3` / `D-b-6`）：
      **只复用 `x-erpnext-image`（不新增镜像）与 `x-ai-env`（AI 变量空默认值）两个锚点，
      不复用 `x-backend-defaults`；新服务不挂 `sites` / `logs` 卷** ——
      镜像 entrypoint 每次启动都 `rm -rf sites/assets` 再重建软链，
      挂了就会在**每次重启时抖掉 `frontend` 的 `/assets`**（起草期实测背景，照实记）·
      **无 `ports:` 块** · healthcheck 打 `/agenerp/health` ·
      **必须给出 `AGENERP_SITE`，写成 `${AGENERP_SITE:-frontend}`**
      （`agenerp/serve/__main__.py:41-43` 逐字：站点名为空即 `return 2` ⇒ 容器起不来、H2 必挂）。
      `:-` 默认值**不可省** —— `tests/unit/test_compose_zero_dep.py::test_every_interpolation_has_a_default`
      逐字要求每个 `${…}` 都带 `:-`。站点名与 `create-site --set-default`、
      `frontend` 的 `FRAPPE_SITE_NAME_HEADER` 是**同一个值**
- [x] `Add` **`frontend` 增同源那一跳**（按 `D-b-1`）+ 增 `depends_on: agenerp-serve`。
      ⚠️ **`frontend` 既有的服务名、`ports:` 那一行、`FRAPPE_SITE_NAME_HEADER`、
      三条既有 `depends_on` 一个字不许动**（§1.4）
- [x] `Add` **`agenerp/serve/` 增监听地址一格**（按 `D-b-4`）：新变量 + 解析函数，
      **默认值仍是 `LOOPBACK`**；`app.py` 既有分支一行不改（Non-Goal 9）
- [x] `Fix` **断言体默认基址改直**（按 `D-b-5`）。⚠️ **只改「去哪里判」，
      六条断言的判定逻辑一个字不改**；文件头那段交接说明里凡提到端口的地方一并对齐
- [x] `Proof` **新增离线判据**（落 `tests/unit/`，文件名执行期定，**不进 `tests/gates/`**），
      **至少九条，逐条挡一种假实现**：
      ① compose 里 `agenerp-serve` **没有 `ports:` 块**（`D-b-4` 那条论证的唯一支点）；
      ② nginx 侧的 `location` 前缀与 `agenerp/serve/app.py` 的 `ROUTE_PREFIX` **逐字相等**
      （**从两个文件各读一次再比**，不许两边各写一个字面量）；
      ③ nginx 侧上游端口与 compose 侧 `AGENERP_SERVE_PORT` **逐字相等**；
      ④ 监听地址**默认是回环**（不给变量时）；
      ⑤ 显式给了才放宽，且**给了非法值当场失败、不静默回退**（口径抄既有 `resolve_port()`）；
      ⑥ `agenerp-serve` 块里**没有** `AGENERP_LLM_*` 出现在 healthcheck 内；
      ⑦ 断言体的默认基址解析与 `agenerp/site.py` `default_base_url()` **同源**
      （同一组环境变量下两者算出同一个 host:port）；
      **⑧ 那段 `location` 在唯一那个 `listen 8080` server 块之内** ——
      解析 nginx 配置文本、判定 server 块起止，**两个 server 块或块外一律红**。
      ⚠️ 这一条挡的正是 §1.7 点名的那个失败形态（「配置测试全绿、反代根本不存在」）：
      判据② / ③ 是纯文本比对，**一段坐在第二个 server 块里的 `location /agenerp/` 两条都满足**；
      **⑨ compose 里 `agenerp-serve` 的 `command:` 字面包含 `agenerp.serve`**，
      且 **nginx 上游主机名字面等于该服务在 compose 里的服务名**（两个文件各读一次再比）。
      ⚠️ 这一条挡的是**假服务**：一段自造的、只会对 `/agenerp/health` 回
      `200 {"service":"agenerp-explain"}` 的应答脚本，能让 ①–⑦ 全绿、M1–M8 全部按预测打红
- [x] `Proof` **既有零依赖判据复跑**：`python3 -m pytest tests/unit/test_compose_zero_dep.py -q` → 退 0；
      **H1** 空环境 `docker compose config -q` → 退 0

Exit Criteria:

- [x] **`docker compose -f docker-compose.yml up -d --wait --wait-timeout 900` → exit 0**，
      且 `docker compose ps` 里 `agenerp-serve` 为 **healthy**。
      ⚠️ **这一条不过，Phase 2 的接线不许提交**（§5 回退义务 / §1.5 的三个 job 爆炸半径）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → **exit 0**，
      条数**只增不减**（对照 §0.1 **第 11 行**的基线数字）
- [x] `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → **exit 0**
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → **exit 0**
- [x] **H1 / H9 / H10 / H11** 四格有实测值
- [x] `git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md` → **无输出**
- [x] §7.21 记下交付形状；`docs/logs/` 更新

### Phase 3 — 活栈实证 + 变异自查 + 交接

Status: completed
Targets: 活栈（不改代码）· `docs/masterplan/STATE.md`（**只追加**）· `docs/architecture/module-boundaries.md` §7.21
Skill: `none`

- Item Types: `Proof | Follow-up`
- Prereqs: Phase 2 全绿；**活栈可起**（起不来按 §5 写死的分支停，不猜）

- [x] `Proof` **从干净状态冷起栈**（`down -v` → `up -d --wait`），
      记**命令原文 + 退出码 + 墙钟秒数**；`docker compose ps` 逐服务健康状态落进 §7.21（**H1 / H2**）
- [x] `Proof` **同源那一跳的四条实测**（**H3 / H4 / H5 / H6**），命令原文与状态码逐条记
- [x] `Proof` **跑断言体六条**（**H7**）：
      `AGENERP_SERVE_BASE=… AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=… python3 -m pytest tests/unit/test_explain_service_body.py -q`
      → 目标 **5 passed, 1 skipped**（§1.11：skip 的必须是且只能是第 4 条，
      理由是它 503 分支自带的 `pytest.skip`）。⚠️ **skip 的若是别的条，一律算没做到** ——
      那说明同源那一跳没通，按 §5 的回退义务处置。
      ⚠️ **那一条 skip 不许被本 plan「顺手修掉」**（§5.1 第 10 条）
- [x] `Proof` **`client_from_sid()` 的活体那一半**（承接第 1 个 plan 的 Deferred 第二条）：
      逐字记明它在活站点上**认出了谁**，以及**认的是不是发请求那个人**。
      ⚠️ **真 `sid` 不落盘、不进日志、不进提交信息**（§5.1 第 8 条）
- [x] `Proof` **`agenerp-serve` 容器内实读监听地址**（**H8** 的另一半），
      与离线判据④ 的「默认是回环」**两句一起记**
- [x] `Proof` **变异自查 M1–M10，逐条施加一次、记红点、复原**。
      **一个都不许跳过；某条打不红就当场补断言并登记为新编号（Mn+1），不许改预测**：
      M1 把 nginx 的 `location` 前缀改成别的字面量 → 预测：判据② 打红 ·
      M2 把 nginx 上游端口改掉 → 判据③ 打红 ·
      M3 给 `agenerp-serve` 加一格 `ports:` 发布到宿主 → 判据① 打红 ·
      M4 把监听地址默认值改成 `0.0.0.0` → 判据④ 打红 ·
      M5 给监听地址喂一个非法值 → 判据⑤ 打红（**不许静默回退**）·
      M6 把 `AGENERP_LLM_ENDPOINT` 塞进新服务的 healthcheck → 判据⑥ 打红 ·
      M7 把断言体默认基址改回一个 CI 上不存在的端口 → 判据⑦ 打红 ·
      M8 把 `/agenerp/health` 改成需要认人 → **H3 打红**（健康端点必须恒 200，
      否则「AI 未配置」与「服务坏了」在响应上又分不开了）·
      **M9** 把那段 `location` 挪进 `conf.d/` 下**第二个**同 `listen` / 同 `server_name` 的 server 块
      → **判据⑧ 打红**（起草期实测背景：`nginx -t` 退 **0** 且只 warn，
      运行时 `/agenerp/health` 回 **404** —— 这正是「配置测试全绿、反代根本不存在」）·
      **M10** 把 `agenerp-serve` 的 `command:` 换成一段自造的应答脚本，
      或把 nginx 上游指向 `backend:8000` → **判据⑨ 打红**
- [x] `Proof` **在 `STATE.md` §3 追加**（**只追加，不改写任何既有行**；
      这是无条件的在场工作、没有触发条件，因此**不标 `Follow-up`**）：
      ① 本 plan 的证据行（命令原文 + 退出码 + sha）；
      ② `[needs-human]` —— **人现在可以把 `tests/unit/test_explain_service_body.py`
      按路径加载进 `tests/gates/test_explain_service_live.py` 了**，
      并把文件头写明的那一处 `skip → fail` 收严做掉（`Gates-Change-Approved-By:`）；
      **逐字写明本 plan 已经把它加载后需要的环境准备到哪一步**；
      ③ `[needs-human]` —— **§1.11 那条 skip 与零 skip 契约的冲突**，
      两条出路（补 `AGENERP_LLM_*` 进 `gates-l2-live` / 改 503 分支的口径）**逐条列出、不预选**
- [x] `Add` **更新 `docs/backlog/p1-insight-roadmap.md` 工作项 10 那一行**
      （**不是 `docs/masterplan/`，不触红线 5**）：逐字写明本 plan 交付了 WBS 验收的**哪一半**
      （活栈 + 同源 + 断言体实测）、**没交付哪一半**
      （`tests/gates/test_explain_service_live.py` 本体归人，红线 1；§1.11 那条 skip 归人），
      以及**状态怎么定的理由**（口径抄 `2026-08-25-1159-1` 收口时写那一行的做法）。
      ⚠️ **表规 3 的账在同一行写死**：工作项 10 **2/2 已满**，
      出处是**人**做的 WBS 拆行 commit `ec74161`（`docs(wbs): P1.8 拆成 a/b 两行`，author `lize`）；
      此后的后继**只能由人拆行**（红线 5）
- [x] `Proof` **§6 的 H1–H11 逐条填实测**，不吻合的照实记、预测原文不改

Exit Criteria:

- [x] H1–H11 十一格逐条有实测值（不可复现的照实写「不可复现」，不猜根因）
- [x] M1–M10 逐条有红点记录（补出来的新编号一并记）
- [x] 断言体 **5 passed, 1 skipped** 有命令原文与退出码，
      且那 1 条 skip 的**行号与原文**逐字记进 §7.21
- [x] `STATE.md` 只追加（`git diff -- docs/masterplan/STATE.md` 的删除行数为 **0**）
- [x] §7.21 收口段写清**本 plan 没做到什么**（至少：`tests/gates/` 那份仍不存在、
      未经 CI 服务端复跑、未做浏览器侧验证）
- [x] `docs/logs/` 更新

## 8. 风险

| # | 风险 | 触发信号（客观可观测） | 起草期写死的处置 |
|---|---|---|---|
| K1 | **新服务把零依赖启动门禁打红**（§1.5：它自动进判定面，且豁免名单改不了） | `up -d --wait` 非 0，或 `test_stack_boots_and_all_services_healthy` 红 | 先原样复跑一次；仍红则按 §5 的**回退义务**把接线 `git revert` 掉再收口，Phase 3 整体转 Deferred，写 needs-human。**绝不去改 `tests/gates/conftest.py` 的豁免名单**（红线 1） |
| K2 | **compose 依赖成环**（`frontend` 依赖新服务，新服务又依赖 `frontend`） | `docker compose config` 报 cycle | `D-b-3` 必须在写配置**之前**回答这个问题；成环即说明回程地址选错，换 (ii) 或破环，不硬塞 |
| K3 | **fork 上游 nginx 模板后与镜像 tag 分叉**（若 `D-b-1` 选 (A)） | 升级 `frappe/erpnext` tag | 按 R-5 处置：钉死 tag；在 §7.21 逐字写明「升级镜像时要一起看哪几行」，并写进 `docker-compose.yml` 的升级步骤注释 |
| K4 | **解释请求超过 nginx 的读超时**（实测单次解释 9.7 万–12.8 万 token） | 同源打 `/agenerp/explain` 挂在读超时上 | `D-b-1` 必须为这条 `location` **显式**给读超时并写明取值依据；⚠️ 断言体自己的 `TIMEOUT = 30` 是**客户端**侧，两者别混（见 H6 的两半） |
| K5 | **执行环境配了 AI 变量，H6 走 200 而不是 503** | 实测状态码 200 | 照实记在 H6 实测列，并逐字写明「本轮判据跑在一个不是 CI 那个的环境上」。**不改预测、不改断言体** |
| K6 | **本 plan 用掉工作项 10 的最后一格预算**（表规 3：一个工作项 1–2 个 plan） | — | 起草期即写死：本 plan 之后，工作项 10 若还有未尽事项，**只能由人在 `02-WBS.md` 拆行 / 加行**（红线 5，loop 无权）。§11 的 Deferred 逐条写明重开事件归谁 |
| K7 | **半接线的栈留在 `main` 上，把三个 L2 job 一起打红** | `gates-l2` / `gates-l2-live` / `gates-l2-seed` 任一在 `main` 上红 | 见 §5 的**回退义务**：Phase 3 走不通时**不是「停在 Phase 2 收口」就完事** —— compose 与 nginx 那两处接线必须 `git revert` 掉再收口（离线判据可以留，接线不许留）。理由：`up -d --wait` 是那三个 job 的**第一步**，新服务不 healthy 会让它们红在起栈上，而本仓的停机条件里「CI 连续 2 轮红」本身就是一条 |

## 9. Draft Review Record

**两轮、两个独立子代理（各自 fresh session，均非本 plan 的起草者），基线 sha `b072e48`。**

- **Independent draft review iteration 1**：`needs revision → 已在本文件内逐条修正`
  （独立子代理 A，2026-08-25）。逐条实读复核了 plan 引用的每一条事实，产出 **2 Blocker /
  5 Major / 5 Minor**，另附 58 行「已核对事实表」。修正如下（全部改在本文件内，起草期原文不改写）：
  - **B1**（Blocker）**本 plan 起草期查出、此前无人登记的一条**：
    `tests/unit/test_explain_service_body.py:201` 的 503 分支**自带一个 `pytest.skip`**，
    而 `check_expected_red.py` 的 live 契约是**零 skip**，`gates-l2-live` 起栈时**一个 AI 变量都不配`
    ⇒ 原 Goal 4 / H7 写的「六条全部 passed、零 skip」与「加载后就能绿」**按构造不可能成立**。
    ⇒ 新增 **§1.11**、Goal 4 与 H7 改写成**上限「5 passed, 1 skipped」**、
    §5.1 见即停增第 10 条、§11 增一条 Deferred（**两条出路都归人，本 plan 不预选**）。
  - **B2**（Blocker）原「停在 Phase 2 收口」会把**未经 `up -d --wait` 证明的 compose 服务留在 `main`**，
    而 `gates.yml` 有**三处** `up -d --wait`（`:189` / `:251` / `:419`）⇒ 爆炸半径是三个 job，
    且撞裁判规则 4「CI 连续 2 轮红」。⇒ §5 增**回退义务**（接线必须 `git revert`，离线判据可留）、
    §1.5 增爆炸半径段、K1 改写、K7 新增、Phase 2 Exit **置首**加 `up -d --wait` 那一条。
  - **M1–M5 / m1–m5**：服务计数 九→**十二**（并点明长期运行的是九个）· `envsubst` 变量 七→**八**并列全名 ·
    snippets 「三个被 include」→**只 include 了一个、且第二处在 regex location 内**（附 `nginx -t` 实测）·
    `D-b-1` 增候选 **(E)**（wrapper，不 fork 模板）并要求与 (A) **逐条比代价** ·
    Phase 2 补 **`AGENERP_SITE`**（`__main__.py:41-43`：站点名为空即 `return 2`）·
    Phase 3 增 **roadmap 工作项 10 回写项**（含表规 3 的账与人做的拆行 commit `ec74161`）·
    §9 引用改直 · (B) 的否决理由改成**实测的静默丢弃**而非「会冲突」·
    `STATE.md` 追加项由 `Follow-up` 改标 `Proof` · §1.6 保留 `18080` 的来历 · §0 基线数字起草期实跑。
- **Independent draft review iteration 2**：`needs revision → 已在本文件内逐条修正`
  （独立子代理 B，**未看过 A 的意见**，2026-08-25）。**结论：无 Blocker**，
  并在活环境里**正面证伪了两条本可能是 Blocker 的事**（一次性探针容器，运行中的栈未被改动）：
  ① 把 `location /agenerp/` 插进那个唯一的 `listen 8080` server 块后，
  `GET /agenerp/health` → **200** 且 `GET /api/method/ping` 仍 **200**
  ⇒ **加的前缀 location 确实压过既有 `location /`，也没遮住其余路由**；
  ② 用 `frappe/erpnext:v15.119.3` + bind mount + `PYTHONPATH` 起本仓的服务
  → **uid 1000(frappe) 绑上 `('0.0.0.0', 8330)`**，容器内 `/agenerp/health` 回 **200**
  ⇒ `D-b-2` 的候选 (i) 与 `D-b-4` 都不是空想。产出 **4 Major / 5 Minor**，逐条修正：
  - **M-A**：§1.7 自己点名的失败形态（「配置测试全绿、反代根本不存在」）**没有任何判据或变异盖得住** ——
    判据② / ③ 是纯文本比对，**一段坐在第二个 server 块里的 `location /agenerp/` 两条全满足**
    （实测：`nginx -t` 退 **0** 只 warn，运行时 `/agenerp/health` 回 **404**）。
    ⇒ 增**判据⑧**（`location` 必须在唯一那个 server 块之内）与**变异 M9**。
  - **M-B**：**一个假服务能过全部七条离线判据与 M1–M8** —— 没有任何离线判据读新服务的 `command:`
    或 nginx 上游**主机名**。⇒ 增**判据⑨**（`command:` 字面含 `agenerp.serve` +
    上游主机名等于服务名）与**变异 M10**。
  - **M-C**：`D-b-2` 只把**挂载路径**钉成字面值，而判据③ 比的**端口**仍可写成 `${…}` ——
    仓根实读**存在 `.env`**，同一条绕过路径（`test_bootstrap_script_dir_is_mounted_literally`
    的 docstring 记过）照样成立。⇒ 字面写死规则**外推到端口与回程地址**，判据③ 加一条「不是插值形式」。
  - **M-D**：`gates-l2-seed` 有一块 **job 级** `env:`（`:399-404`，含
    `AGENERP_SITE_URL: http://127.0.0.1:8080`），会被它 `:419` 那步 `up -d --wait` **一并继承** ——
    回程地址若写成 `${AGENERP_SITE_URL:-…}`，**容器在那个 job 里会打自己**，
    而 `/agenerp/health` 恒 200 ⇒ **healthcheck 与 `up --wait` 照样绿，只有 `/agenerp/explain` 静默坏掉**。
    ⇒ §0 第 8 条扩到该块，`D-b-3` 增第三问（**回程地址必须字面写死**）。
  - **Minor 1–5**：(D) 的 `nginx -t` 原文改准（`^/files/.*.(htm|html|svg|xml)`）·
    `test_compose_zero_dep.py` 「13 条」→ **12 funcs / 14 collected** ·
    **H10 的命令量不出 H10 的预测**（`git status --porcelain` 会报计划内的 `M` 行）→ 改成
    `git ls-files --others --exclude-standard` · Phase 2 Exit 的 `§0.1 第 10 行` → **第 11 行** ·
    Phase 2 增「**不复用 `x-backend-defaults`、不挂 `sites`/`logs`**」
    （镜像 entrypoint 每次启动 `rm -rf sites/assets` 再重建软链，挂了会抖掉 `frontend` 的 `/assets`）。
- **收敛判定**：两轮共 **2 Blocker / 9 Major / 10 Minor 全部在本文件内落实**，
  第 2 轮**无 Blocker**且其四条 Major 均为**加严**（多两条判据、多两条变异、多一处字面值约束、
  多一处 CI env 重取），不改动本 plan 的结果面与边界。
  ⇒ 按 `docs/plans/00-plan-authoring-and-execution-guide.md` **Minimum Rule 13** 与
  **When Executing 第 2 条**，`Plan Status` 由 `draft` 转 **`active`**。
- ⚠️ **两轮评审都没有跑过本 plan 的任何一个 Phase**：上面那些「实测」是**评审者的独立探针**，
  **不是本 plan 的交付证据**。§6 的 H1–H11 十一格执行期一格都不许留空。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.21 落地；`system-baseline.md` 按 `D-b-7` 的裁定新增 **§14.11**）
- [x] verification has run：`python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit -q` · `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
      `ruff check …` · `docker compose up -d --wait --wait-timeout 900` · 活栈那一组（**H1–H8**）
- [x] scoped verification is not conflated with full verification —— **verification scope limited**：
      未跑整仓 `pytest tests -q -m "not live"`、**未经 CI 服务端复跑**、**未做浏览器侧验证**（三处均已逐字写进 §7.21 收口段、`STATE.md` §2 与 roadmap）
- [x] no in-scope item downgraded to deferred/follow-up（§1.6 那处 `Fix` 已按 `Fix` 做完：`D-b-5` + 判据⑦ + 变异 M7；`Follow-up` 一条也没有）
- [x] independent draft review completed and recorded（§9 两轮，两个独立子代理）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— ⚠️ **留白**：本轮执行环境不具备独立子代理，执行者自己复跑不算独立审计（处置同 P1.4–P1.7 先例）
- [x] closure evidence exists in files（§7.21 · `STATE.md` §2 · `docs/logs/2026/08-25.md` · roadmap 工作项 10）
- [x] 红线自证：`git status --porcelain -- tests/gates/ .github/workflows/ missions/ docs/masterplan/DECISIONS.md` → **无输出**；
      `git diff --numstat -- docs/masterplan/STATE.md` → **`16  0`（删除行数 0）**；`tools/gates/expected-red.txt` **一个字未改**；
      证据仓 `XM_PATH` 未写入；未生成任何运行时 Server Script

## 11. Deferred But Adjudicated

### `tests/gates/test_explain_service_live.py` 本体只能由人创建

- Classification: `watch-only residual`
- Why Not Blocking Closure: **红线 1 的必然，不是偷懒**。本 plan 交付的是它加载所需的**活栈与同源那一跳**，
  以及它的**断言体实测**（H7：**5 passed, 1 skipped**）。
  ⚠️ **不写成「交付了加载后就能绿的环境」** —— §1.11 那条 skip 未拆之前它加载后**不会绿**，
  拆它归人（见本节下一条）。
- Successor Required: `yes`（**承接者是人**）。重开事件：**人带 `Gates-Change-Approved-By:` 按路径加载**，
  并做掉那一处 `skip → fail` 收严。

### §1.11 那条 `skip` 与门禁零 skip 契约的冲突

- Classification: `watch-only residual`
- Why Not Blocking Closure: **两条出路都在红线内或在判据口径内，loop 无权选**
  （① 改 `.github/workflows/**` 是红线 2；② 改 503 分支的判定口径会让一次
  **从未真正调过模型**的跑也能让门禁绿，正是硬约束① 要挡的）。
  本 plan 把它**查出来、写清楚、交出去**，并按这个上限写死 Goal 4 与 H7，**没有假装它不存在**。
- Successor Required: `yes`（**承接者是人**）。重开事件：**人在加载那份门禁时一并裁定**。

### Desk 侧边栏与 ⌘K（工作项 11 / P1.8b）

- Classification: `out-of-scope improvement`（起草期即定界，非执行期现编）
- Why Not Blocking Closure: 那是**另一个工作项**（Non-Goal 3），有自己的预算格。
- Successor Required: `yes`。重开事件：**本 plan 收口**。
  ⚠️ **起草期照实登记一处尚未解决的口径冲突，留给那个 plan 或人**：
  D-19 逐字「承载形态定为独立进程 + nginx 同源反代，**不是 Frappe custom app**」，
  而 `module-boundaries.md` §7.13 的 `D1` 逐字「承载面 = **(A) 自建 Frappe app**」，
  且 §7.13 的实测表说明 Desk 全局 JS 的注入口**只有** (A) 与 (E) 两处。
  **本 plan 不裁定这件事**（不在本 plan 的结果面内，且它是 owner doc 之间的口径冲突 ⇒ 归人）。

### 生产级并发形态（连接池 / 请求超时 / 限流 / TLS）

- Classification: `optimization candidate`
- Why Not Blocking Closure: §7.20 `D-a-1` 的残余风险原样继承；本 plan **只重开「绑哪个地址」一格**，
  且服务端口**不发布到宿主**。
- Successor Required: `yes`。重开事件：**出现「服务要对本机之外提供」的具体需求或缺陷**。

### `docs/context/codebase-map.md` 整份仍是模板占位符

- Classification: `out-of-scope improvement`（从 `2026-08-25-1159-1` §11 **继承，条件一个字未改松**）
- Why Not Blocking Closure: 全仓性漂移，非本 plan 造成、也非本 plan 的结果面；
  该文件自己的 Update Rule 规定占位符残留时不得当作权威 ⇒ 本 plan 的路由由 §0 的十一处实读承担。
- Successor Required: `yes`。重开事件：**有人把它列进一次专门的上下文文档对齐工作**，
  或**某个 plan 因为信了它的占位符而走错路由**（两者任一）。

## Closure

Status Note: **三个 Phase 全部执行完毕，全绿收口。** 交付「活栈 + 同源那一跳 + 断言体活体实测」；
**未交付**「WBS §4 P1.8a 那条验收命令退 0」—— 那条被 §1.11 的 skip 挡着，两条出路都归人。
⚠️ **执行途中人在 `main` 上提交了两次**（`f09b8f0` 自行创建门禁文件、`24529ec` 撤回 `expected-red.txt`
那 6 行并追加 `[open]`「就让它红着」），逐条照实记进 §0.1，本 plan 未碰其中任何一处。

Closure Audit Evidence:

- Auditor / Agent: ⚠️ **独立审计未做** —— 本轮执行环境不具备独立子代理，
  执行者自己复跑**不算**独立审计。Closure Gate `closure audit was independent` **留白**，
  处置同 P1.4–P1.7 的先例（由后续一轮补做）。
- Evidence（命令原文 + 退出码 + commit sha）:
  - `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml down -v` → exit **0**
  - `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 900` → exit **0**（墙钟 **100 秒**）
  - `AGENERP_SERVE_BASE=http://127.0.0.1:18080 AGENERP_SITE=frontend AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/unit/test_explain_service_body.py -q -rs` → exit **0**（`5 passed, 1 skipped`）
  - `python3 tools/gates/check_expected_red.py` → exit **0**（`门禁 26 项：预期红 0，绿 26，跳过 0`）
  - `python3 -m pytest tests/unit -q` → exit **0**（`777 passed, 6 skipped`）
  - `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → exit **0**（`456 passed, 13 skipped`）
  - `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → exit **0**
  - commit sha：Phase 1 `ac2d456` · Phase 2 `b669cbf` · Phase 3 见收尾提交
  - ⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`，**未经 CI 服务端复跑**，**未做浏览器侧验证**。

Follow-up:

- **无。** 本 plan 确认的两处缺陷都**没有**被降级到这里：
  §1.6 那处默认基址漂移已按 `Fix` 做完（`D-b-5` + 判据⑦ + 变异 M7）；
  §1.11 那条 skip 与零 skip 契约的冲突**不是本 plan 能处置的**，
  它作为 `Deferred But Adjudicated` 的一条交出去，承接者是**人**（见 §11 与 `STATE.md` §3 的三条 `[needs-human]`）。
