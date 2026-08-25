# P1.8b 上半 · Desk 注入接缝的裁定与落地（把本仓的一段 JS 送进 Desk 页面，同源、可 diff、可回滚）

> Plan Status: completed
> Mission: p1-insight
> Work Item: 11. **Desk 侧边栏**（⌘K，调 P1.8a 的面）（P1.8b）—— **本 plan 是它的第 1 个 plan**（表规 3 的 1–2 个）
> Last Reviewed: 2026-08-25
> Source: `docs/masterplan/02-WBS.md` §4 **第 88 行 P1.8b** · `docs/masterplan/DECISIONS.md` **D-19**（只读）·
> `docs/backlog/p1-insight-roadmap.md` 工作项 11
> Related: [`2026-08-24-2311-2-desk-embed-carrier-decision.md`](./2026-08-24-2311-2-desk-embed-carrier-decision.md)
> （`completed`。它的 **D1 选 (A) 自建 Frappe app**，**已被后来的 D-19 逐字否掉**；
> 但它 Phase 1 那张**只读探测表**里「哪些候选结构上到不了 Desk」的实测格**仍然有效**，是本 plan 的输入，不重做）·
> [`2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`](./2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md)
> （`deferred`。它 §11 第一条的重开事件逐字是「**`sid` 接缝被重新裁定（由人或一个新 plan）**」，
> **已由 P1.8a 的两个 plan 触发并落地**；第二条「承载面的激活与 WBS 验收命令」的重开事件逐字含
> 「**人在 `02-WBS.md` 把 P1.8 拆行**」，**已由 commit `ec74161` 触发**）·
> [`2026-08-25-1423-1-explain-service-compose-and-same-origin.md`](./2026-08-25-1423-1-explain-service-compose-and-same-origin.md)
> （`completed`。它交付的 `agenerp-serve` + nginx 同源那一跳是本 plan 的**地基**，本 plan 在它的哨兵段里加东西，不重做它任何一格）
> Audit: required

## 0. 执行前必做：重取基线

**起草期读到的一切都可能在开工时已经变了。** 下面九处**逐条重读**，把实读值填进 §0.1；
与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`。
   **起草期经过两次实读，且两次不同，照实记两次**：① 起草开始时工作树有一行
   ` M docs/masterplan/DECISIONS.md`（人正在写 **D-20**）；② 评审期复读时**人已提交** ——
   `2f08ea3`（D-20 风险档裁 L1）、`554b827`（D-21 / D-17）、`d321097`（STATE 交接 CI 那条红），
   HEAD = `d321097`，`git status --porcelain` **只剩本 plan 文件自己那一行 `??`**。
   ⇒ 开工判据：**除本 plan 文件外 `git status --porcelain` 无输出**。
   ⚠️ 无论哪种情形，`docs/masterplan/**` 一个字节不碰、不 `git add`（红线 3 / 5）。
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时最大节号**（起草期实读 **§7.21**，
   本 plan 预定落 **§7.22**；被别的 plan 占用就顺延，以开工时实读为准）。
3. `docs/architecture/system-baseline.md` 的 `14.x` 族最大节号（起草期实读 **§14.11**）。
   **本 plan 默认不占 §14.x** —— 只有在 Phase 1 裁定产出一条新的「判据口径规则」时才占，届时落 §14.12。
4. `tools/nginx/frappe.conf.template` 的 **AgenERP 哨兵行**逐字与行号。
   ⚠️ **实读是一对，不是两对** —— `:51` `# >>> AgenERP —— 同源那一跳（§7.21 \`D-b-1\` / \`D-b-8\`）`
   与 `:89` `# <<< AgenERP`，全文 **153** 行非空行。
   文件头注释块（`:1-19`）是本仓加的**第二段内容**，但它**没有哨兵包围** ——
   「上游差集只有本仓那两段」里的「两段」= 文件头注释块 + 这一对哨兵之间的内容。
   本 plan 加的东西**必须落在这一对哨兵之间**（判据守它）。
5. `agenerp/serve/app.py` 的 `ROUTE_PREFIX` / `HEALTH_PATH` / `EXPLAIN_PATH` 三个字面量与
   `do_GET` 的分发结构（起草期实读：前缀 `/agenerp`，只有 `/agenerp/health` 与 `/agenerp/explain`
   两条路径，**全部回 JSON**，`_not_found()` 的文案逐字点名「本服务只有」那两条）。
6. `docker-compose.yml` 里 `agenerp-serve` 的 `volumes:`（起草期实读**唯一一条**
   `- ./agenerp:/opt/agenerp/agenerp:ro`）与 `frontend` 的模板挂载那一行。
7. `.github/workflows/gates.yml` 的 `COVERED` 逐字（起草期实读 `:560`
   `contracts context experiments fixtures gates routing tools unit`）。
   **本 plan 不新增 `tests/*` 目录**，此项只为确认那条守卫没被改动。
8. `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 的**开工基线数字**。
   起草期**自己跑过一次**：`门禁 26 项：预期红 0，绿 26，跳过 0` + **`779 passed, 6 skipped`**。
   ⚠️ roadmap 工作项 10 那段收口文字里的 `777 passed` 是 `D-b-8` **修复之前**的数，
   **不要拿它当基线** —— 修复提交 `1d852a5` 之后是 779。
9. `docker compose ps` 与宿主对外口（起草期实读：十个长期服务全 `running`，
   `frontend` 发布在 `127.0.0.1:18080->8080/tcp`；**本机 `8080` 被另一个 compose 项目占着**，
   见 roadmap 工作项 10 那条「本机 Docker 另有两处不稳定」）。

### 0.1 执行期重取基线的**实读结果**

（执行期逐条填写，命令原文 + 输出。**不许留空、不许写「同起草期」了事**。）

执行期实读时间：2026-08-25（本轮执行）。**九条逐条如下。**

1. `git log -1 --format=%H` → `d321097f9e5736bc3305644667510ac5b0fd577e`
   `git status --porcelain` → **只有一行** `?? docs/plans/p1-insight/2026-08-25-1615-1-desk-injection-seam-and-asset-route.md`
   ⇒ **与起草期评审复读那一次逐字一致**（HEAD = `d321097`，除本 plan 文件外无输出）⇒ **开工判据成立**。
2. `grep -nE '^#+ 7\.[0-9]+' docs/architecture/module-boundaries.md | tail -1`
   → `3192:### 7.21 解释服务接进 compose + nginx 同源反代在本仓的落点（P1.8a 第 2 个 plan · 2026-08-25）`
   ⇒ `7.x` 族当时最大节号仍是 **§7.21**，**§7.22 未被占用**，本 plan 落 **§7.22**（与起草期预定一致）。
3. `grep -nE '^#+ 14\.[0-9]+' docs/architecture/system-baseline.md | tail -1`
   → `1632:## 14.11 判据要比对的 compose 值一律字面写死（规则 ④，plan `2026-08-25-1423-1` 交付）`
   ⇒ `14.x` 族最大节号仍是 **§14.11**（与起草期一致）。**本 plan 最终未产出新的「判据口径规则」，故不占 §14.x**
   （落地沿用 §14.11 已定的「两个文件各读一次再比、不写第三个字面量」口径，不新立规则）。
4. `grep -n 'AgenERP' tools/nginx/frappe.conf.template` →
   `2:# │ AgenERP · 这是上游 frappe/erpnext:v15.119.3 里 …` ·
   `6:# │ 本仓加的两段一律用成对哨兵注释围起来（见下文那两对 AgenERP 哨兵行）。 …` ·
   **`51:	# >>> AgenERP —— 同源那一跳（§7.21 \`D-b-1\` / \`D-b-8\`）`** ·
   **`89:	# <<< AgenERP`**
   `grep -cve '^\s*$' tools/nginx/frappe.conf.template` → **153**（非空行）；`wc -l` → **173**（总行）。
   ⇒ **哨兵实读是一对（`:51` / `:89`），行号与起草期逐字一致**；文件头注释块 `:1-19` 无哨兵，
   与 §0 第 4 条所记相符。⚠️ 照实记一处**起草期未记的措辞**：文件头 `:6` 那句自己写的是
   「用成对哨兵注释围起来（见下文那两对 AgenERP 哨兵行）」——**它说的是「两对」**，
   而实读只有一对。这是上游副本里**本仓自己那段注释的措辞旧账**，**本 plan 不改它**
   （改它会扩大与上游的差集之外的编辑面，且它不进任何判据），登记为观察，不作处置。
5. `grep -n 'ROUTE_PREFIX\|HEALTH_PATH\|EXPLAIN_PATH' agenerp/serve/app.py` →
   `53:ROUTE_PREFIX = "/agenerp"` · `54:HEALTH_PATH = f"{ROUTE_PREFIX}/health"` ·
   `55:EXPLAIN_PATH = f"{ROUTE_PREFIX}/explain"`；`do_GET` 分发结构实读为
   `path == HEALTH_PATH → 200 JSON` / `path == EXPLAIN_PATH → 405 JSON` / 其余 `_not_found()`；
   `_not_found()` 逐字 `{"error": f"未知路径；本服务只有 {HEALTH_PATH} 与 {EXPLAIN_PATH}"}`，
   `_respond()` 一律 `Content-Type: application/json; charset=utf-8`。
   ⇒ **与起草期实读逐字一致**：两条路径、全部回 JSON、无任何静态资产路由、无任何读文件代码。
6. `sed -n '305,308p' docker-compose.yml` → `agenerp-serve` 的 `volumes:` **唯一一条**
   `- ./agenerp:/opt/agenerp/agenerp:ro`；`grep -n 'frappe.conf.template' docker-compose.yml` →
   `357:      - ./tools/nginx/frappe.conf.template:/templates/nginx/frappe.conf.template:ro`。
   ⇒ 与起草期一致。**`agenerp/serve/assets/desk.js` 天然已送达容器**，不需要新增任何挂载。
7. `grep -n 'COVERED=' .github/workflows/gates.yml` → `560:          COVERED="contracts context experiments fixtures gates routing tools unit"`
   ⇒ **逐字未变**。本 plan **不新增 `tests/*` 目录**（两份新判据都落在既有 `tests/unit/` 下），那条守卫不受影响。
8. `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` →
   `判定模式：default —— 按 tools/gates/expected-red.txt 判定` / `门禁 26 项：预期红 0，绿 26，跳过 0` /
   `✅ 与预期红名单完全一致` + **`779 passed, 6 skipped in 9.52s`**，退出码 **0**。
   ⇒ **开工基线数字 = 26 项全绿 + 779 passed / 6 skipped**（与起草期一致；roadmap 工作项 10 那段里的
   `777 passed` 是 `D-b-8` 修复前的数，按 §0 第 8 条不当基线）。
9. `docker compose ps` → **十个长期服务全 `running`**（`agenerp-serve` / `backend` / `db` / `frontend` /
   `queue-long` / `queue-short` / `redis-cache` / `redis-queue` / `scheduler` / `websocket`），
   有探针的六个全 `healthy`；`frontend` 发布在 **`127.0.0.1:8080->18080`** 形态实读为
   `[{127.0.0.1 8080 18080 tcp}]`（即宿主 `127.0.0.1:18080` → 容器 `8080`）。
   ⇒ 与起草期一致：**宿主对外口是 `18080`**，`8080` 仍被另一个 compose 项目占着。

## 1. Current Baseline

### 1.1 WBS 那一行要什么，本 plan 交不交付它

`02-WBS.md` §4 **第 88 行**逐字：

> | P1.8b | **Desk 侧边栏**（⌘K 唤起，保留当前单据上下文），调 P1.8a 的面 | P1.8a | `pytest -m live tests/ui/test_sidebar.py` 退 0 | `MD:p1-explain` |

**本 plan 不声称满足这条验收命令**（Non-Goals 2）。它交付的是那条命令成立所必需的、
今天完全不存在的一格：**Desk 页面上如何才能加载到本仓的一段 JS**。

### 1.2 承载面裁定今天是**空的**，这是本 plan 存在的理由

两条记载相撞，且相撞处正好落在 P1.8b 的头上：

- `module-boundaries.md` **§7.13 D1** 逐字：承载面 = **(A) 自建 Frappe app**，走 `hooks["app_include_js"]`，
  激活属风险档 L3，强制人批。
- `DECISIONS.md` **D-19**（后写，masterplan 层，优先）逐字：承载形态定为
  **独立进程 + nginx 同源反代，不是 Frappe custom app**。

⇒ **D-19 把 §7.13 D1 选中的那条路否掉了，但没有给出替代的注入口。**
`STATE.md` §3 `[resolved] 2026-08-25T02:25Z` 认的是「`sid` 接缝 + L3 激活」这两件事被 D-19 解决，
**没有认「Desk 侧 JS 从哪进去」被解决** —— 那一格至今没有任何裁定。本 plan 补的就是它。

⚠️ **这不是 loop 在推翻应用层裁定。** D-19 是人写的 masterplan 决策，本 plan 只是**执行它**，
并把执行所需的那一格补上。**§7.13 一个字不改**（它是历史记录，其探测表仍有效）。

### 1.3 §7.13 那张探测表里**今天仍然有效**的部分（本 plan 的输入，不重做）

出处 `apps/frappe/frappe/www/app.py:47` 实读：Desk 全局 JS 的**完整来源只有两项** ——
`hooks["app_include_js"]` 与 `frappe.conf["app_include_js"]`。表里逐条否决且**与 D-19 无关**的：

- **(B) `Client Script`**：`dt` 是 `reqd: 1` 的 Link，消费端按 `dt` 过滤 ⇒ 做不出全站 ⌘K。**结构上不成立。**
- **(B′) `Website Script` / `Website Theme.js`**：`web_include_js` 是门户页，**Desk 不取**。
- **(B″) `Custom HTML Block`**：只在放了该 widget 的那一张 Workspace 页上。
- **(D) `Website Settings.head_html` 一族**：`www/app.html` **不 extends `base.html`** ⇒ Desk 根本不渲染它。
- **(F) 覆盖镜像层 `apps/**` / `assets/**`**：`frappe-bench` 下只有 `sites` / `logs` 两个 volume ⇒ 容器重建即丢。

还有一条**不是否决、是定性**的（评审补上，比只引五条否决更说明问题）：

- **(C) 本机 HTTP 服务**：原表结论逐字是「**不能（单独）**……**它可以作为 (A) 的下游**」——
  理由是 `www/app.py:47` 实读证明 Desk 的 JS 只有两个来源，(C) 不在其中，**它必须借别人的注入口**。

⇒ **在「不建 Frappe custom app」这个 D-19 约束下，Frappe 自己一个可用注入口都没留下。**
而 D-19 选中的形态正是 **(C)**，于是「借谁的注入口」这个问题原封不动地留了下来。
今天本仓手里唯一还能改 Desk 页面的位置是**反代那一层**（§7.21 的模板副本）——
**本 plan 就是去回答「借不借得成、怎么借」。**

### 1.4 P1.8a 的**地基已落成**，但**它那一行本身没关** —— 两句都要说

- `agenerp/serve/app.py`（351 行）：`ThreadingHTTPServer`，两条路径 `/agenerp/health`（恒 200、不认人、
  不碰 LLM、不打站点）与 `/agenerp/explain`（`sid` 认人、只读、四键白名单），**响应全部是 JSON**，
  没有任何静态资产路由、没有任何读文件的代码。
- `docker-compose.yml` 的 `agenerp-serve`：复用 `x-erpnext-image`，`PYTHONPATH: /opt/agenerp`，
  **唯一挂载** `- ./agenerp:/opt/agenerp/agenerp:ro` ⇒ **`agenerp/` 下任何文件天然已送达容器**。
- `tools/nginx/frappe.conf.template`：上游模板副本 + **一对哨兵**（`:51` `# >>> AgenERP …` / `:89` `# <<< AgenERP`；
  文件头注释块 `:1-19` 是本仓加的第二段内容，但**它没有哨兵**）；`location /agenerp/` 用
  `resolver 127.0.0.11` + `set $agenerp_serve_host` 做**运行期解析**（§7.21 `D-b-8`，
  修的是「新服务不在就拖垮整个 frontend」）。
- 实测过的同源那一跳：经 `frontend` 对外口 `GET /agenerp/health` → **200**，`/api/method/ping` 仍 **200**。

⚠️ **同时照实记，不许含糊过去**：`02-WBS.md` 第 88 行 P1.8b 的「前置」列逐字是 **P1.8a**，
而 roadmap **工作项 10 的状态词今天仍是人改回去的 `todo`**（人 2026-08-25 从 `done` 改回），
它那条验收命令 `pytest -m live tests/gates/test_explain_service_live.py` 最后一次实跑是
**`1 failed, 5 passed`**。**本 plan 不改 roadmap 那一行、不替它宣布关闭。**

**那为什么 P1.8b 仍然可以开工**，三条一起成立：
① 前置要的是**能力**，而能力实测在（`/agenerp/health` 200、同源那一跳通、`agenerp-serve` 在 compose 里）；
② 工作项 10 的表规 3 预算 **2/2 已满**，loop 无权再派第 3 个 plan（拆行只有人能做，红线 5）；
③ 它剩下那条红的处置面在 `tests/gates/**` 与 `.github/workflows/**` 里（红线 1 / 2），**归人** ——
人已于 `61cd2f3` 给 `gates-l2-live` 配上 AI 变量、于 `d321097` 把这条交接记进 `STATE.md`。
⇒ **loop 在工作项 10 上无事可做，不是「跳过它」。**

### 1.5 本仓今天**零** Desk 前端资产

`git ls-files agenerp | grep -cE '\.(js|css|html)$'` → **0**。
`ls apps` → `No such file or directory`。
⇒ 本 plan 是本仓第一段会被浏览器执行的 JS，**没有既有惯例可循**，因此裁定必须写清楚。

### 1.6 起草期已经实测到、但**只当假设的前提、不当结论**的两条

- `docker compose exec -T frontend nginx -V` 的编译参数含 **`--with-http_sub_module`**
  **与 `--with-http_addition_module`**（`nginx -v` → `nginx/1.22.1`）。
  ⇒ 反代那一层**有能力**改写响应体，且**有两种改法**（`sub_filter` 换字符串 ·
  `add_after_body` 在响应体后追加一个子请求的输出）。**两种都必须进 `D-c-1` 的候选集。**
  ⚠️ **这只是「能力存在」，不是「这条路走得通」** —— `sub_filter` 对**压缩过的上游响应无效**，
  而上游 backend 会不会回 gzip，起草期**没测**。这是 §6 `H3` 的内容。
- 未登录 `GET http://127.0.0.1:18080/app` → **301**，`Location: /login?redirect-to=%2Fapp`，
  `Content-Length: 0`。⇒ Desk 页面对 Guest 不发 HTML，注入段自然也发不出去。

### 1.7 CI 侧两条与本 plan 相关的既有守卫

- `gates.yml:560` `COVERED="contracts context experiments fixtures gates routing tools unit"` ——
  **新增 `tests/*` 目录会让那一步红**。本 plan **不新增测试目录**（Non-Goals 2）。
- `61cd2f3`（人，`Gates-Change-Approved-By: lize`）刚给 `gates-l2-live` 配上 AI 变量。
  **与本 plan 无关，此处只记不用** —— 本 plan 一次模型都不调。

### 1.8 ⚠️ 与 `D-a-2` 的正面冲突：本 plan 要加**第三条端点**

`module-boundaries.md` **§7.20 `D-a-2`**（`:2993`）标题逐字是
**「端点集合：两条，前缀 `/agenerp`」**，正文逐字 **「不加第三条。」**
被它否决的备选是 `GET /agenerp/whoami`，否决理由逐字是**「它是第二个认人面，判据要跟着翻倍」**。

而本 plan 的 `D-c-2` 候选 (a) 要加的正是**第三条** `GET /agenerp/desk.js`。
**这是一次 source-of-truth 冲突，不许默默加了事** —— Phase 1 的 `D-c-4` 就地裁定它。
裁定要正面回答一件事：`whoami` 的否决理由（**第二个认人面**）**适不适用于一条
不认人、不碰站点、不碰 LLM 的静态资产路由**。

⚠️ **这一条也是本 plan 里唯一一处会去动 P1.8a 落下的 owner doc 措辞的地方。**
处置方式**写死**：**不改 `D-a-2` 一个字**，在 §7.22 里写一条「就地扩展」并逐字引它的否决理由，
说明扩展后端点表变成几行、每行的「认人？/ 碰 LLM？/ 碰站点？」三列各是什么。

## 2. Goals

1. **裁定** Desk 侧的 JS 注入接缝：在「不建 Frappe custom app、不落 D-10 那扇运行期门」的约束下，
   哪一条路走得通、其余为什么走不通。**裁定依据是执行期自己的探针，不是起草期推测。**
2. 裁定成立时**落地那一跳**：让**登录后的 Desk 页面**加载到一段来自本仓 git 的 JS，
   且该 JS 与解释服务**同源**（同一个 `frontend` 对外口）。
3. 交付**离线可判**的判据（字面量一致性、注入段在哨兵内、上游副本差集只有本仓两段、资产路由不认人且不可拼路径）
   + 一次**活栈实测**（真登录会话取 `/app` 见到注入标记；经对外口取那段 JS 回 200 且 `Content-Type` 是 JS）。
4. **不回归**：零依赖启动门禁仍绿；`agenerp-serve` 不在时 `frontend` 仍起得来（§7.21 `D-b-8` 的不回归）。

## 3. Non-Goals

1. **不做 ⌘K、不做侧边栏 UI、不写任何调 `/agenerp/explain` 的前端逻辑。** 那是工作项 11 的**第 2 个 plan**。
   本 plan 交付的 JS 是**自证存在的最小脚本**，不发任何请求。
2. **不建 `tests/ui/`、不交付 `tests/ui/test_sidebar.py`。** WBS §4 P1.8b 的验收命令本 plan **不声称满足**。
3. **不建 `apps/**`、不跑 `bench install-app`、不写站点任何一行数据**（P1 是②端只读）。
4. **不碰 `tests/gates/**` / `.github/workflows/**` 的任何一行**（红线 1/2）；
   **`docs/masterplan/**` 全部只读**，唯一允许的写动作是往 `STATE.md` §3 **追加**（红线 3/5）。
   ⚠️ 评审期实读：**D-20 / D-21 人已提交**（`2f08ea3` / `554b827` / `d321097`），
   工作树里**没有**任何未提交的 masterplan 改动 —— 起草期那句「工作树里那 14 行 D-20」已过期，此处改准。
5. **不引第三方依赖、不做真浏览器驱动。** 活体证据用 `curl` / `http.client` 带真 `sid` 取页面。
   ⇒ **「真浏览器会不会执行这段 script」本 plan 不声称已证**，登记为残余风险（§8 R3）。
6. **不动上游 nginx 模板副本里属于上游的任何一行**（K3：副本与上游的差集只许是本仓那两段）。
   若裁定要求改上游块 ⇒ 走 §7 Phase 1 写死的停机分支，交人。

## 4. Task Route

- Type: `architecture change`（补一格承载接缝裁定）+ `implementation-only change`（落地那一跳）
- Owner Docs: `docs/architecture/module-boundaries.md`（落点节 **§7.22**，新增）·
  `docs/architecture/system-baseline.md`（**默认不占 §14.x**，见 §0 第 3 条）·
  `docs/masterplan/DECISIONS.md` **D-19 / D-10**（**只读**）·
  `docs/design/agents-and-roles.md` §9 风险档表（用于给本次改动定档）
- Skill Selection Basis: 实现期 `Skill: none` —— `docs/skills/` 全部 15 个都是**审计 / 评审 / 重构发现**类提示词，
  没有一个覆盖「探测 + 裁定 + 改反代配置」这个工作方法。
  评审与收口期用 `plan-audit-prompt.md` / `closure-audit-prompt.md`，见 §9 / §10。

## 5. Infrastructure And Config Prereqs

- **活栈**：`docker compose up -d --wait --wait-timeout 900`。宿主对外口经 `AGENERP_HTTP_PORT` 给，
  **本机必须给 `18080`**（`8080` 被另一个 compose 项目占着 —— 不给会死在
  `Bind for 0.0.0.0:8080 failed: port is already allocated`）。
- **一个真登录会话**：`POST /api/method/login`（`usr=Administrator`，口令取 `AGENERP_ADMIN_PASSWORD`，
  本仓一贯取值是字面 `admin`），拿回 `Set-Cookie: sid=…`。
  ⚠️ **`sid` 真值一个字节不许落盘**，按 §7.14 先例：证据文件写完后对 `sid` 前 8 位 grep 全仓自证无命中。
- **零新增依赖**：`pyproject.toml` 收口时 `git diff` 必须是 **0 行**。
- **回滚策略**（本 plan 全部改动都是可 revert 的构建期产物）：
  `git revert <sha>` + `docker compose up -d --force-recreate --no-deps frontend agenerp-serve`。
  nginx 模板是 `:ro` bind mount，revert 文件 + 重建 `frontend` 即彻底复原，**站点里不留任何东西**。

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下面每条的「预测」列在开工前已逐字写死。执行期只许填「实际」，不许改「预测」。**

| # | 探针（命令原文） | 预测 |
|---|---|---|
| **H1** | `docker compose exec -T frontend nginx -V 2>&1 \| tr ' ' '\n' \| grep -c -- --with-http_sub_module`（再跑一次同形命令查 `--with-http_addition_module`） | **两条都是 `1`**（起草期已实测含；执行期复测。**若 `sub_module` 为 `0` ⇒ (H)/(I) 出局；若两条都为 `0` ⇒ 走停机分支**） |
| **H2** | 带真 `sid` `GET /app` 经对外口 | **200**，`Content-Type` 含 `text/html`，响应体含字面 **`</body>`** |
| **H3** | **必须带真 `sid`**（不带就是 301 空体，空体天然不压缩 ⇒ 那个探针对任何实现都「吻合」，是套套逻辑）。在 `frontend` 容器内：`curl -H 'Host: frontend' -H 'Cookie: sid=<真 sid>' -H 'Accept-Encoding: gzip' -sD- -o /dev/null http://backend:8000/app`，看**上游回给 nginx 的那一跳**有没有 `Content-Encoding` | **不带 `Content-Encoding`**（评审在 `/login`——347KB 的 `text/html`——上实测过一次不带，**但那不能替代带 sid 打 `/app` 这一跑**）。⚠️ **两处 gzip 必须分开看**：模板 `:149` 的 `gzip on` 是 **nginx→客户端**方向、跑在 `sub_filter` **之后**，**无害**；只有**上游→nginx** 这一跳的压缩才会让 `sub_filter` 静默失效 |
| **H3b** | 若 H3 实际**带**压缩：在候选 (I) 的 `location ^~ /app` 里加 `proxy_set_header Accept-Encoding "";` 后复跑 H3 | **不带 `Content-Encoding`**。⚠️ 这条对冲**只动本仓哨兵段内自己新起的那个 location，上游一行不动**（K3 不扩大） |
| **H4** | 不带 Cookie `GET /app` | **301**，`Location` 含 `/login`，`Content-Length: 0`（起草期已实测） |
| **H5** | 落地后：一次性容器里 `nginx -t` | **exit 0**，且回归两条仍在：`/api/method/ping` **200** · `/agenerp/health` **200** |
| **H6** | 落地后：不带 Cookie 取**资产 URL** 经对外口。⚠️ **URL 不在本表里写死** —— 由脚本从 `tools/nginx/frappe.conf.template` 的注入段里读出来（口径同判据②「两个文件各读一次再比」，本 plan 全程不写第三个字面量） | **200**，`Content-Type: text/javascript; charset=utf-8`。**不认人** —— `<script src>` 那一跳浏览器会带 Cookie，但资产本身不得依赖它 |
| **H7** | 落地后：带真 `sid` `GET /app`，数**注入标记**出现次数。**注入标记的定义写死在这里**：`D-c-1` 落地时写进模板注入段的那一整串（`<script …></script>` 或 `add_after_body` 的等价物），由脚本从模板里读出后原样在响应体里 `count()` | **恰好 1 次** |
| **H8** | `docker compose stop agenerp-serve` 后 `docker compose up -d --force-recreate --no-deps frontend` | `frontend` **不进重启循环**（§7.21 `D-b-8` 不回归）；`/app` 仍 **200** 且注入标记**仍在**；**资产 URL**（口径同 H6：从模板注入段读出，**不写第三个字面量**）回 **502** —— 脚本取不到，页面照常 |
| **H9** | `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` | **exit 0，14 条全绿，一条未改松** |
| **H10a** | 落地后：**不带 Cookie** `GET /login`（一张 Desk 之外的、会真回 HTML 的页面），数注入标记出现次数 | 选 **(H)**（server 级 `sub_filter`）⇒ 预测 **1 次**，即**确实误伤门户页** —— 这是选 (H) 必须当场承认的代价，不是事后发现的缺陷；选 **(I)**（只在 `location ^~ /app` 内改写）⇒ 预测 **0 次**；选 **(M)** ⇒ 按其作用面所在的 location 同理判 |
| **H10b** | 落地后：`GET /files/<一个不存在的名字>.html` 经对外口 —— 它走的正是模板 `:118-122` 那条 `location ~ ^/files/.*\.(htm\|html\|svg\|xml)`（带 `Content-disposition: attachment`）再 `try_files` 落 `@webserver`。数注入标记出现次数 | 选 **(H)** ⇒ 预测 **1 次**；选 **(I)** / **(M)** ⇒ 预测 **0 次**。评审期实测该请求今天回 **404** / `Content-Type: text/html` / 体 **330,562 字节**（**有体可数**） |
| **H11** | 落地后：带真 `sid` `GET /app`，看注入标记落在 `</body>` 之前还是 `</html>` 之后 | 选 (H)/(I) ⇒ **在 `</body>` 之前**；选 (M) ⇒ **在整个响应体之后**（`add_after_body` 的构造如此）。⚠️ 这条决定「浏览器会不会在 DOM 就绪前执行它」，是 (M) 与 (H)/(I) 的**实质差别**，不是风格差别 |

🔴 **`H10b` 为什么测的是「404 的 HTML 体」而不是「一份真实附件」—— 降级路径开跑前写死，不留执行期现编**：

活栈实读 `/home/frappe/frappe-bench/sites/frontend/public/files/` **目录在、文件 0 个**
（`find … -type f | wc -l` → `0`，没有任何 `.htm/.html/.svg/.xml`）。
⇒ 「取一份真实 HTML 附件」**今天没有对象可取**，而唯一造得出对象的办法是往站点**上传**一个附件 ——
**Non-Goals 3 逐字禁止**（不写站点任何一行数据，P1 ②端只读）。三条逐字定死：

1. **逐字禁止为取证上传附件。** Non-Goals 3 优先于取证便利。
2. **H10b 用上面那条降级探针**（`/files/<不存在>.html` 的 404 体），它回答的是
   **「经这条 location 出去的 HTML 会不会被改写」**。
3. ⚠️ **边界照实记，不许把降级读成完整**：它测的是**代理回来的 404 体**，
   **不是真实静态附件那条 `try_files` 命中路径**。后者仍是**推论**
   （依据：`sub_filter` 是输出体过滤器，对 nginx 自己发的静态文件同样生效
   ⇒ 代理体被改写时静态体只会更确定被改写）。
   ⇒ **「真附件被损坏」这一格降级为 `D-c-1` 里 (H) 的残余风险 + `not observed on this stack` 的照实登记**，
   **不留在 Phase 3 Exit Criteria 里当必须有的定量值**。

⚠️ **H3 是本 plan 最可能被证伪的一条。** 0119-1 就是被 `H1`（`sid` 带 `HttpOnly`）一条实测掀翻了三个 Phase；
本 plan 把同形态的停机分支**预先写死在 §7 Phase 1 的 Exit Criteria 里**，不留「到时候再看」。
⚠️ **但停机条件不是「H3 一被证伪就停」** —— H3b 那条对冲（在自起的 location 内清 `Accept-Encoding`）
是 in-scope 的、不动上游行的解法。**有解法却停机，等于把活儿甩给人。** 逐字条件见 Phase 1 Exit Criteria 第 3 条。

## 7. Execution Plan

### Phase 1 — 先探测，再裁定（`D-c-1` … `D-c-4`），一行配置都还不写

Status: completed
Targets: `docs/analysis/2026-08-25-1615-desk-injection-seam-probe.md` · `docs/architecture/module-boundaries.md`（§7.22 新增）
Skill: `none`

- Item Types: 逐项标注（本 Phase 是 `Explore` 2 项 + `Decision` 4 项 + `Proof` 1 项，**没有任何一类占到 80%，故不作 Phase 级统一声明**）
- Prereqs: §0 九条重取基线全部填完

- [x] **`Explore` E-1**：先拿到一个真登录会话（`POST /api/method/login`），再逐条跑
      **H1 / H2 / H3 /（必要时 H3b）/ H4**，把命令原文与逐字输出记进探测记录。
      ⚠️ **H3 必须带真 `sid`** —— 不带 Cookie 打 `/app` 只会拿到 301 空体，
      而空体天然不压缩，那个探针**对任何实现都「吻合」**，什么也没证。
      **`sid` 真值零落盘**，写完对其前 8 位 grep 全仓自证无命中。
      - Skill: `none`
- [x] **`Explore` E-2**：实读 `frontend` 容器里 envsubst **之后**那份 `/etc/nginx/conf.d/frappe.conf`，
      确认本仓那**一对**哨兵（`:51` / `:89`）确实落在**唯一那个 `listen 8080` 的 server 块**里
      （§7.21 已实测过一次，本 plan 要在它旁边加东西，复核一次）。
      - Skill: `none`
- [x] **`Decision` `D-c-1` · 注入接缝选型。** 候选**六个**，**否决依据分两类写，不许混**：
      - **经验性候选（否决/选中依据必须引执行期探针格）**：
        **(H)** 在哨兵段内对 Desk 页面开 `sub_filter`，把 `</body>` 换成注入标记 + `</body>` ·
        **(I)** 在哨兵段内另起 `location ^~ /app`，**只在该块内**反代 backend 并开 `sub_filter`
        （改写面收窄到 Desk 一条路由；`Accept-Encoding` 那条对冲也只能加在这里）·
        **(M)** `add_after_body`（`ngx_http_addition_module`，**实测已与 `sub_module` 一同编译进 1.22.1**）：
        不改原体、在响应体后追加一个内部子请求的输出。**它与 (H)/(I) 的失败模式不同**
        （追加位置在 `</html>` 之后、对每个匹配响应各发一次子请求），**必须当场测清**，见 H11。
      - **决策性候选（依据是文档原文，`不需要探针`，逐字注明）**：
        **(J)** 自建 Frappe app —— 依据 `DECISIONS.md` **D-19** 逐字「不是 Frappe custom app」 ·
        **(K)** `frappe.conf["app_include_js"]` —— 依据 §7.13 (E)：承载物在共用 `sites:` volume 里
        ⇒ 落 **D-10** 运行期那扇门，**停机交人** ·
        **(L)** 不嵌 Desk、改做 `/agenerp/` 下的独立页面 —— 依据 `02-WBS.md` **第 88 行**逐字
        「**保留当前单据上下文**」，(L) 按构造做不到，**只作退路登记，不作选项**。
      裁定要写清**作用面有多宽**（`H10a` / `H10b` 的预测已写死，不许事后补；
      **`H10b` 那条「注入串被写进用户下载的 HTML 附件」必须逐字写进 (H) 的代价**）、**残余风险**与**翻案条件**，
      并按 §6 两问答一遍 D-10 的护栏格（进 git / 走人审 / 重启才生效）。
      ⚠️ **若选 (I)，代价必须写进依据里**：自起的 `location ^~ /app` 得自带上游 `@webserver` 那套头
      （`Host` / `X-Frappe-Site-Name` / `X-Use-X-Accel-Redirect` / `X-Forwarded-*` / `proxy_read_timeout`），
      否则 Desk 会**静默走偏**；那等于在哨兵段里养一份**需随镜像 tag 升级同步的上游孪生**。
  - Skill: `none`
- [x] **`Decision` `D-c-2` · 那段 JS 从哪儿来、由谁发。** 候选三个：
      **(a)** `agenerp/serve/assets/desk.js`，随**现有**那条 `./agenerp:/opt/agenerp/agenerp:ro` 挂载送达，
      由 `agenerp/serve/app.py` 加一条只读 GET 路由发出去 ·
      **(b)** 打进镜像（**否**：`x-erpnext-image` 是钉死的上游镜像，本仓不自建镜像层；
      且 §7.13 (F) 实测 `frappe-bench` 下只有 `sites` / `logs` 两个 volume，容器重建即丢）·
      **(c)** 给 `frontend` 再加一个 bind mount，由 nginx `alias` 直接发。
      ⚠️ **(c) 有一条硬碰撞，必须写进裁定**：`tests/unit/test_explain_same_origin.py:218` 逐字断言
      **含 `ROUTE_PREFIX` 的 `location` 有且只有一段**（`len(directives) == 1`）。(c) 必然新增
      `location /agenerp/desk.js` ⇒ **那条既有判据当场变红**。这不是「顺手放宽一下」——
      **放宽一条既有判据是一次独立裁定**，要单写。⇒ 这条碰撞本身就是 **(a) 胜过 (c) 的硬理由**。
      裁定还要回答：**这段资产要不要认人**（预答 **不认人** —— `<script src>` 取不到就整个白做，
      而它本身零业务信息；认人反而多一条「未登录时页面报错」的噪声路径）。
  - Skill: `none`
- [x] **`Decision` `D-c-3` · 本次改动的风险档自评**（`docs/design/agents-and-roles.md` §9 风险档表）。
      **必须做，不许省** —— 本 plan 改的是**所有登录 Desk 的用户浏览器里会执行的东西**，
      而 §7.13 `D1` 曾把承载面激活判成 **L3 强制人批**。两个兄弟 plan 都做了自评
      （§7.20 `D-a-6` 自评 L0、§7.21 `D-b-7` 自评 L1），本 plan 不能是例外。
      自评要逐格对表，并写清**结论若是 L3 会怎样**。
      🔴 **写死的分支：若自评结论为 L3 ⇒ Phase 2 / 3 必须挂在人批之后**，
      在 `STATE.md` §3 追加一条 needs-human 并停在 Phase 1，**loop 不自批、不试探**。
  - Skill: `none`
- [x] **`Decision` `D-c-4` · 与 §7.20 `D-a-2`「不加第三条」的冲突就地裁定**（见 §1.8）。
      **不改 `D-a-2` 一个字**；在 §7.22 写一条「就地扩展」，逐字引它的否决理由
      （「它是**第二个认人面**，判据要跟着翻倍」），回答它**适不适用于一条不认人、不碰站点、
      不碰 LLM 的静态资产路由**，并给出扩展后的端点表（三列：认人？/ 碰 LLM？/ 碰站点？）。
      🔴 **裁定认为「适用」（即不该加第三条）时，停机前有一格强制动作，不许跳过**：
      先枚举并实测「**能不能在不新增任何含 `ROUTE_PREFIX` 字符串的 `location` 的前提下**由 nginx 发这段资产」——
      两条候选，**主次已定，不是并列**：
      **① 主路径 —— 具名 location**（如 `location @agenerp_asset`，指令串里不含 `/agenerp`），
      `location /agenerp/` **原封不动** ·
      **② 保留但当场注明其代价 —— 在现有 `location /agenerp/` 内 `try_files $uri` 再落回代理**：
      ⚠️ **按 nginx 语义，「落回同一个 block 里的 `proxy_pass`」写不出来** ——
      `try_files` 的兜底项只能是文件/目录/`=code`/**具名 location**，
      其唯一可跑形态（`location /agenerp/ { try_files $uri @agenerp_proxy; }` +
      `location @agenerp_proxy { proxy_pass …; }`）**把 `proxy_pass` 移出了 `location /agenerp/`**，
      正好打红 `test_explain_same_origin.py` 的**判据③**（`location /agenerp/` 里有且只有一条变量形式的 `proxy_pass`）。
      ⇒ 候选 ② 与 `D-c-2` 的 (c) **同性质**：要用它就得先把「放宽既有判据」当作**一次独立裁定**写清楚。
      **候选 ① 足以撑住这条链条，不要照着一条写不出来的配置去撞判据。**
      ⚠️ 理由与 Exit Criteria 第 3 条同一条：`test_explain_same_origin.py:218` 判的是
      「指令串里**含 `/agenerp`** 的 location 有且只有一段」，**不是「不许再发别的东西」** ——
      把它读成后者会在**有 in-scope 解法时停机**，正是本 plan 自己立规矩要挡的形态。
      **只有连这两条也被实测否掉，才停在 Phase 1 交人。**
  - Skill: `none`
- [x] **`Proof` P-1**：四条裁定 + H1–H4 的实际值落 `module-boundaries.md` **§7.22**
      （新增节，**§7.13 / §7.20 / §7.21 一个字不改**）。
  - Skill: `none`

Exit Criteria:

- [x] **H1 / H2 / H3 /（触发时）H3b / H4 的「实际」列全部填满**，与「预测」逐条对照；
      不吻合的**照实记，不改预测**
- [x] `D-c-1` … `D-c-4` 四条各自写下选中项、依据（**经验性候选引探针格；决策性候选引文档原文并注明「不需要探针」**）、
      残余风险、翻案条件
- [x] 🔴 **写死的停机分支（三条，满足任一即停在 Phase 1，Phase 2/3 整体转 `Deferred But Adjudicated`）**：
      ① **H1 两项都为 `0`**（`sub_module` 与 `addition_module` 都不在）⇒ 反代那一层根本改不了响应体；
      ② **(H) 与 (I) 与 (M) 三条经验性候选被执行期探针逐条证伪** ——
      ⚠️ **逐字写清什么不算证伪**：H3 实际带压缩**不构成停机**，因为 H3b 那条对冲
      （在 (I) 自起的 location 内 `proxy_set_header Accept-Encoding "";`）**只动本仓哨兵段、上游一行不动**；
      只有连 H3b 也不成立时 (I) 才算被证伪。**有 in-scope 解法却停机 = 把活儿甩给人，禁止**；
      ③ `D-c-3` 自评为 **L3**（人批之前不得进 Phase 2/3），
      **或** `D-c-4` 裁定「`D-a-2` 适用、不得加第三条」**且**「不新增含 `ROUTE_PREFIX` 的 location 就发不出这段资产」
      也被实测坐实（具名 location 与现有 location 内 `try_files` 两条都不成立）。
      ⚠️ **只满足前半句不构成停机** —— 理由同上一条：有 in-scope 解法却停机，禁止。
      **三条之外，逐字禁止**：绕过去改上游模板自己的行（K3）· 降格成 (L) 独立页面充数
      （那会产出一个关不掉 WBS P1.8b 的残件，正是 Minimum Rule 4 要挡的形态）
- [x] `docs/analysis/2026-08-25-1615-desk-injection-seam-probe.md` 落盘，**零 `sid` 真值**（grep 自证）
- [x] `module-boundaries.md` §7.22 落地（insertions > 0，**deletions == 0**）
- [x] `docs/logs/2026/08-25.md` 追加

### Phase 2 — 落地那一跳 + 离线判据（不需要活栈就能判的那一半）

Status: completed
Targets: `agenerp/serve/assets/desk.js` · `agenerp/serve/app.py` · `tools/nginx/frappe.conf.template` ·
`tests/unit/test_desk_asset_route.py` · `tests/unit/test_desk_injection_static.py`
Skill: `none`

- Item Types: 逐项标注（`Add` 4 项 + `Proof` 2 项。**达不到 80% 的统一门槛，故不作 Phase 级声明**）
- Prereqs: Phase 1 的**三条停机分支一条都没触发**

- [x] **`Add`** `agenerp/serve/assets/desk.js`：**自证存在的最小脚本**。只做两件事 ——
      在 `window` 上挂一个带版本号的只读标记、往 console 打一行。
      **不注册任何快捷键、不发任何请求、不碰 DOM**（Non-Goals 1）。
- [x] **`Add`** `agenerp/serve/app.py` 加 `GET <前缀>/desk.js`（按 `D-c-4` 的裁定）：
      **不认人**（不读 Cookie）、**不接受任何路径参数**（文件名是模块级常量，调用方一个字都拼不进去）、
      `Content-Type: text/javascript; charset=utf-8`、显式 `Content-Length`。
      读文件的路径由 `__file__` 推出，**不读任何环境变量**。
      ⚠️ **落点提醒**：既有判据⑧/⑩ 的 AST 扫描**只扫到它扫的那几个函数**；
      把资产逻辑挪进 `do_GET` 之外的 helper 就绕过去了。判据要显式覆盖新 helper，见 P-2。
- [x] **`Add`** `_not_found()` 那句「本服务只有 …」的文案随之更新
      （它逐字枚举了路径，漏改就是一条会说谎的错误信息）。
      ⚠️ **实读确认过今天没有任何守卫**：`grep -rn "本服务只有" tests/` **无输出** ⇒ 漏改、改错、
      改成一条不存在的第四条路径，**今天全绿**。P-2 要补上这一格。
- [x] **`Add`** `tools/nginx/frappe.conf.template`：按 `D-c-1` 在**那一对哨兵之间**加注入那一跳
      （若选 (I)，新起的 `location ^~ /app` 也必须坐在同一对哨兵之间）。
      **上游任何一行不动**（K3）。
- [x] **`Proof` P-2 · 判据两份，各自守一件事**：
      `tests/unit/test_desk_asset_route.py` —— 起真 socket 打真路由：不带 Cookie 回 200 ·
      `Content-Type` 逐字 · 体与 `agenerp/serve/assets/desk.js` **逐字节相同** ·
      未知路径仍 404 且**不回显请求路径** ·
      **404 文案枚举的路径集合 == 本模块实际服务的路径常量集合**（两边都从常量算出，**不写第三个字面量**）·
      用 AST 扫本模块（**含新加的 helper，不只是 `do_GET`**）：没有出现任何凭据环境变量、
      没有用请求里的值拼过文件路径。
      `tests/unit/test_desk_injection_static.py` —— **从两个文件各读一次再比，判据里不写第三个字面量**：
      模板里注入的 URL 前缀 == `app.py` 的 `ROUTE_PREFIX` · 注入的文件名 == 资产路由常量 ·
      注入段**在那一对哨兵之间**（在外面 ⇒ 红）· **注入段不许整段被注释掉**
      （只 grep 字符串会把注释里的 URL 也数进去，判据要判它在生效行上）·
      模板里 `/agenerp/` 上游端口 == compose 的 `AGENERP_SERVE_PORT`（沿用 §14.11 口径）。
  - Skill: `none`
- [x] **`Proof`** 三条验证命令一次跑完并记退出码：
      `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，
      `passed` **只增不减**（对照 §0.1 第 8 条的开工数字，起草期实测基线是 **779 passed, 6 skipped**）·
      `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
      → `All checks passed!` · `git diff -- pyproject.toml` → **0 行**。
  - Skill: `none`

Exit Criteria:

- [x] 三份产物（JS 资产 / 服务路由 / 模板注入段）齐全，且**注入的 URL 与服务发出的 URL 是同一个字面量的两次读取**
- [x] 两份判据全绿；**失败模式说得出**：改前缀 / 改文件名 / 把注入段挪出哨兵 / 把注入段整段注释掉 /
      让资产路由认人 / 改 `Content-Type` / 改上游端口 / 404 文案说谎，**八种各自打红哪一条**
- [x] `tests/unit` 的 `passed` 只增不减；`ruff` 全过；`pyproject.toml` 零 diff（零新增依赖）
- [x] 相关 owner doc 已更新（§7.22 回填落地面 + `D-c-4` 的端点表），或写明 `No owner-doc update required`
- [x] `docs/logs/2026/08-25.md` 追加

### Phase 3 — 活栈实证 + 变异自查 + 交接

Status: completed
Targets: `docs/evidence/p1-desk-seam/` · `docs/architecture/module-boundaries.md` §7.22 · `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Proof`（本 Phase 全部 6 项均为 `Proof`）
- Prereqs: Phase 2 全绿

- [x] **H5 / H6 / H7 / H8 / H9 / H10a / H10b / H11 八条逐条填「实际」。**
      每条记命令原文 + 退出码 / 状态码。不吻合的照实记，**不改预测**。
      ⚠️ **H10a（误伤门户页）/ H10b（误伤 HTML 附件）/ H11（注入位置）不许略过** ——
      它们是 `D-c-1` 选中项的**代价**那一半，预测已在 §6 写死，此处只填实际。
- [x] **一次真正的冷起**：`docker compose down -v` → `up -d --wait --wait-timeout 900` → 记退出码与墙钟。
      零依赖启动门禁（`H9`）在**冷起后**复跑一次。
- [x] **变异自查 M1…Mn**：每条只改一处、跑判据、记下被打红的**具体那一条**、复原、`sha256` 比对 `RESTORED OK`。
      **至少含**：M1 改 `ROUTE_PREFIX` · M2 改注入的文件名 · M3 把注入段挪出哨兵 ·
      M4 让资产路由读 Cookie 才发 · M5 把 `Content-Type` 改成 `application/json` ·
      M6 把资产内容改一个字节（判据要求逐字节相同）· M7 改模板里上游端口 ·
      M8 把 `resolver` 那行删掉（§7.21 `D-b-8` 的不回归，应打红或让 `H8` 不成立）·
      **M9** 只改 `_not_found()` 那句文案（漏改守卫）·
      **M10** 把注入段**整段注释掉**但把 URL 留在注释里（**静态判据最可能的漏洞**：只 grep 字符串会全绿）·
      **M11** 加 `sub_filter_once off;`（`H7` 的「恰好 1 次」还成不成立）·
      **M12** 让资产路由用请求路径拼文件名（验证那条 AST 扫描真咬得住）。
      ⚠️ **打不红的照实写「没打红」并当场补断言**；补不了的写清为什么 —— 先例见 roadmap 工作项 10 的 M7。
- [x] **上游副本差集复核**：`docker run --rm --entrypoint cat frappe/erpnext:<钉死 tag> /templates/nginx/frappe.conf.template | diff - tools/nginx/frappe.conf.template`
      → 差集**只有本仓那两段**（本 plan 之后是两段还是三段，以 `D-c-1` 的形态为准，逐字记）。
- [x] `docs/evidence/p1-desk-seam/` 落盘（响应头、注入前后的 `/app` 片段——**只留含标记的那几行，不落整页**、
      变异红点表）。**零 `sid` 真值**，grep 自证。
- [x] `STATE.md` §3 **追加**证据行与 needs-human 行（**只追加，不改写已有行**）。

Exit Criteria:

- [x] **H5 / H6 / H7 / H8 / H9 / H10a / H10b / H11 八条全部有「实际」值**，与预测逐条对照。
      **H10a 与 H10b（降级形态）的实际值是选中项代价的定量记录，不许省略或写成「未观察」。**
      ⚠️ **「真实静态附件会不会被损坏」不在本格内** —— 按 §6 那条降级路径，它是
      `D-c-1` 里 (H) 的残余风险 + `not observed on this stack` 的照实登记，**不得反过来当成已证或已排除**
- [x] 冷起后 `up -d --wait` **exit 0**，十个长期服务全 `running`，有探针的全 `healthy`
- [x] `tests/unit/test_compose_zero_dep.py` **14 条全绿，一条未改松**
- [x] 变异表 **M1–M12** 逐条有红点记名；未打红的**照实记且当场补断言**，补不了的写清为什么
- [x] 上游差集复核跑过，结果逐字入档
- [x] §7.22 回填实测值；`docs/logs/2026/08-25.md` 追加；`STATE.md` §3 只追加

## 8. 风险

- **R1 · H3 被证伪（上游回 gzip）** —— 处置**已写死且分了两级**：先试 H3b 那条**只动本仓哨兵段**的对冲
  （在 (I) 自起的 location 内 `proxy_set_header Accept-Encoding "";`）；**连它也不成立时才停机交人**。
  **任何情况下不许自行去改上游 `@webserver` 块**（K3）。
  ⚠️ 评审期在 `/login`（347KB `text/html`）上实测过一次上游**不回** `Content-Encoding`，
  ⇒ R1 的概率**可能比起草期估的低**；但那不是 `/app` 上带 `sid` 的那一跑，**不当结论**（D-16）。
- **R2 · `sub_filter` 改的是「所有匹配到的响应」** —— 选 (H) 会误伤 Desk 之外的 HTML（门户页、`/login`）。
  **这条已经从「事后回答」升格成 §6 的 `H10a` / `H10b`，预测在跑之前写死**（选 (H) 诚实预测是
  门户页误伤 1 次、**且把注入串写进走 `location ~ ^/files/…` 的 HTML 附件里 —— 那是损坏用户文件**；
  选 (I) 两条都预测 0 次），Phase 3 Exit Criteria 有对应一格。**不许等选完再补预测**（硬约束②）。
- **R2b · 注入位置** —— (M) `add_after_body` 把内容追加在 `</html>` 之后，
  与 (H)/(I) 插在 `</body>` 之前**是实质差别**，写进 `H11`，同样预测在前。
- **R3 · 「HTML 里有 `<script>` 标签」≠「浏览器执行了它」** —— 本 plan 用 `curl` 取页面，
  **不声称已证浏览器行为**（Non-Goals 5）。登记为残余风险，承接者是第 2 个 plan。
- **R4 · 本机 Docker 不稳** —— roadmap 工作项 10 记过两处（`8080` 被别的项目占、
  冷起偶报 `No such container`）。遇到失败**先原样复跑**（裁判规则 3），复跑不出来记「不可复现」，
  **不猜根因**。
- **R5 · `docs/masterplan/**` 在起草期正被人高频改动**（起草到评审这段时间里就落了三个提交：
  `2f08ea3` / `554b827` / `d321097`）。全程不碰、不 `add`、不 commit（红线 3 / 5）。
  提交前 `git status --porcelain -- docs/masterplan/` 必须无输出；
  `STATE.md` §3 的追加是本 plan 唯一允许写 `docs/masterplan/` 的动作，且**只许追加**。

## 9. Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理 `a785fdc452c9d1f7d`，
  fresh session，不带起草期上下文，2026-08-25）。评审器**未采信 plan 自报的任何数字**，
  逐条实跑复核了 `## 1. Current Baseline` 的每一条断言。
  **判定「授权成立」**：独立数完 19 个 plan 的 `> Work Item:` 行，拆行前那三份（`2311-1` / `2311-2` /
  `0119-1`）绑在旧 P1.8 上，人在 `ec74161` 的提交信息里逐字写「据此拆行，**各自有预算**」
  ⇒ 拆行后 P1.8a 用掉 2/2、**P1.8b 用掉 0/2**，本 plan 是它的第 1 个，表规 3 不越界。
  **提出 11 条阻塞问题 + 11 条非阻塞建议**，逐条处置如下（**全部采纳**）：

  | # | 阻塞问题 | 本轮处置 |
  |---|---|---|
  | 1 | `H3` 探针不带 Cookie ⇒ 打到的是 301 空体，空体天然不压缩，**对任何实现都「吻合」**（套套逻辑） | `H3` 改成**必须带真 `sid`**，并显式区分两处 gzip（模板 `:149` 的 `gzip on` 是 nginx→客户端、跑在 `sub_filter` 之后，无害） |
  | 2 | 停机分支是**假二难**：候选 (I) 里加一行 `proxy_set_header Accept-Encoding "";` 即可解决，**上游一行不动** | 新增 `H3b` 对冲；停机条件改成「(H)/(I)/(M) 三条**都**被证伪」，并逐字写明「H3 带压缩**不构成停机**」 |
  | 3 | 与 §7.20 `D-a-2`（「端点集合：两条…**不加第三条**」）正面冲突，全文一次没提 | 新增 **§1.8** 记冲突；Phase 1 新增 **`D-c-4`** 就地裁定，**不改 `D-a-2` 一个字**，并写死「裁定认为适用 ⇒ 停在 Phase 1」的分支 |
  | 4 | 缺**风险档自评**，而两个兄弟 plan 都做了（`D-a-6` L0 / `D-b-7` L1），§7.13 `D1` 曾判 L3 | Phase 1 新增 **`D-c-3`**，并写死「自评为 L3 ⇒ Phase 2/3 挂在人批之后」 |
  | 5 | 「否决依据必须引探针」对 (J)/(K)/(L) 按构造无法满足，执行器要么编探针要么违反 Exit Criteria | 候选**分两类**：经验性候选引探针格；决策性候选引 `D-19` / `D-10` / WBS 第 88 行原文并**逐字注明「不需要探针」** |
  | 6 | 候选集漏了 `--with-http_addition_module`（实测与 `sub_module` 同时编译在内） | 新增候选 **(M) `add_after_body`**，并新增 `H11` 当场测清它与 (H)/(I) 的实质差别（注入位置） |
  | 7 | §8 R2（作用面）没有开跑前写死的预测 ⇒ 事后补预测，违反硬约束② | 升格成 §6 **`H10`**，两个分支各写死预测（选 (H) 诚实预测「误伤 1 次」），Phase 3 增一格 Exit Criteria |
  | 8 | `_not_found()` 文案**零守卫**（`grep -rn "本服务只有" tests/` 无输出） | P-2 增一条「404 文案枚举的路径集合 == 实际服务的路径常量集合」；变异集增 **M9** |
  | 9 | `D-c-2` 候选 (c) 会打红既有判据 `test_explain_same_origin.py:218`（`len(directives) == 1`），与「passed 只增不减」直接冲突 | 写进 `D-c-2`，并明说**这条碰撞就是 (a) 胜过 (c) 的硬理由**；若仍选 (c)，放宽既有判据是**一次独立裁定** |
  | 10 | §1.4 标题「P1.8a 已经落成」隐去了「工作项 10 那一行今天仍是 `todo`、验收仍 `1 failed`」 | §1.4 改标题并补两句照实记 + 三条「为什么 P1.8b 仍可开工」；**不改 roadmap 那一行** |
  | 11 | Phase 2 的 `Item Types` Phase 级声明不成立（`Add` 达不到 80%） | Phase 1 / Phase 2 **改为逐项标注**，并写明为何不作 Phase 级声明 |

  **11 条非阻塞建议同样全部落地**：§0 第 1 条开工判据改成「除本 plan 文件外无输出」（人已把 D-20 提交，
  HEAD 现为 `d321097`）· `H6` / `H7` 的 URL 与注入标记改成**从模板里读**、不写第三个字面量 ·
  (I) 的「上游孪生」代价写进 `D-c-1` 依据 · 变异集补 **M9–M12** ·
  红线自证扩成四条（覆盖红线 1/2/3/5/6，`STATE.md` 单独判「只增不删」）·
  AST 扫描只覆盖 `do_GET` 的口子写进 Phase 2 提醒 · §11 补「引浏览器驱动是一次需人拍板的依赖决策」·
  §1.3 补引 §7.13 的 **(C)** 行（「不能（**单独**）……可以作为 (A) 的下游」）·
  第三条 Deferred 的「顺手对齐」改成事件式表述。
  评审器另**独立确认三条**：Anti-Slacking 扫描零命中 · Minimum Rule 4 成立（不该合并、也不该再拆）·
  「HTML 里有 `<script>` ≠ 浏览器执行了它」在 Non-Goals 5 / §8 R3 / §11 三处各自登记，无一处被读成已证。

- **Independent draft review iteration 2: `needs revision`（局部）**（同一独立子代理，2026-08-25）。
  复核方式逐字是「**逐条复核了落地文本而不是采信表格自述**」。
  结论：**11 条阻塞里 10 条已真正堵上**（① H3 带 `sid` + 两处 gzip 分开 · ② `H3b` + 停机条件改成三条都被证伪 ·
  ③ §1.8 + `D-c-4` · ⑤ 两类依据 · ⑦ `H10` 预测在前 · 以及 ④⑥⑧⑨⑩⑪）。
  评审器另**独立复核过两处行号与断言原文**：`test_explain_same_origin.py:218` 的
  `assert len(directives) == 1` 逐字对得上；§9 那张表**零失真**（逐行比对，无一条说重或说轻）。
  **仍然阻塞 3 条 + 新引入 2 条，逐条处置（全部采纳）**：

  | # | 问题 | 本轮处置 |
  |---|---|---|
  | 仍阻塞 1 | §11 第一条 Deferred 还挂着**旧**停机口径（「H1 **或 H3** 不吻合 ⇒ 唯一出口是人裁定 K3」），与修订后的 Phase 1 Exit Criteria 第 3 条**直接打架** | 改成「**三条停机分支任一**触发」，并按触发的是哪一条分出口（①/② ⇒ 人裁 K3；③ ⇒ 人批风险档 / 人裁 `D-a-2`），逐字补「**H3 不吻合本身不是停机条件**」 |
  | 仍阻塞 2 | §1.4 仍写「上游模板副本 + **两对哨兵**」，与 §0 第 4 条自相矛盾 | 改成「**一对哨兵**（`:51` / `:89`）」，并注明文件头注释块 `:1-19` 是没有哨兵的第二段内容 |
  | 仍阻塞 3 | Non-Goals 4「`DECISIONS.md` 工作树里那 **14 行 D-20** 一个字节不碰」已过期（人已提交，工作树里没有它） | 改成「`docs/masterplan/**` 全部只读，唯一允许的写动作是往 `STATE.md` §3 追加」，并照实记 D-20 / D-21 已由人提交 |
  | 新引入 1 | `D-c-4` 的停机链条把两处「必然」说死了，**重演了阻塞 2 的形状** —— `:218` 判的是「指令串里**含 `/agenerp`** 的 location 有且只有一段」，而具名 location（`@agenerp_asset`）或现有 `location /agenerp/` 内 `try_files $uri` 都不新增此类 location ⇒ **有 in-scope 解法却会停机** | `D-c-4` 停机前加一格**强制动作**：先枚举并实测那两条候选，**只有连它们也被否掉才停机**；停机条件 ③ 同步改成合取式，并逐字写「只满足前半句不构成停机」 |
  | 新引入 2 | `H10` 只测 `/login`，漏了模板 `:118-122` 那条带 `Content-disposition: attachment` 的 `location ~ ^/files/.*\.(htm\|html\|svg\|xml)` —— server 级 `sub_filter` 会把注入串写进**被下载的 HTML 附件**，那是**损坏用户文件**，是选 (H) 最重的代价 | `H10` 拆成 **`H10a`（门户页）/ `H10b`（HTML 附件）**，各自写死两分支预测；`D-c-1` 要求把 `H10b` 逐字写进 (H) 的代价；Phase 3 的填表与 Exit Criteria 同步改成八条 |
  | 提请注意（评审明说不必改，本轮仍改） | `H8` 仍硬编码 `/agenerp/desk.js`，与 H6/H7 已改成「从模板读」不一致 | `H8` 同步改成从模板注入段读，**全 plan 零第三个字面量** |

  评审器另就本人提问给出两条判断：**`D-c-3` 与 `D-c-4` 不互相打架**（停机条件③里是 `OR`，各自独立、无循环依赖）；
  **不会「大概率停在 Phase 1」**（H1 两项实测均为 `1`；H3 在 `/login` 上实测上游不回 `Content-Encoding`，
  且有 `H3b` 兜底；`D-c-3` 按 `D-b-7` 先例大概率落 L1）。
  并逐条核过 **`H10a` 预测「(H) 误伤 1 次」不会破「passed 只增不减」**：
  `:218` 的 `len(directives)==1`、「唯一 server 块」、「`location /agenerp/` 是直接子块」三条全不受影响；
  全仓 `tests/` 无任何断言 `/login` 页面正文；`frontend` 探针打 `/api/method/ping` 回 JSON，
  而 `sub_filter_types` 默认只吃 `text/html` ⇒ 探针不受影响。

- **Independent draft review iteration 3: `needs revision`（两处局部编辑）**（同一独立子代理，2026-08-25）。
  评审器逐条读了落地文本，判定 iteration 2 那**六条全部真堵上**（§11 出口分列且与 Exit Criteria 逐字对齐 ·
  §1.4 一对哨兵 · Non-Goals 4 与 `git status` 实读相符 · `D-c-4` 强制动作**没有**给「改既有判据」开口子 ·
  `H10a`/`H10b` 与 Phase 3 八条同步 · `H8` 第三个字面量清零）。剩两条，**均已改**：

  | # | 问题 | 本轮处置 |
  |---|---|---|
  | 仍阻塞 1 | **`H10b` 在今天这台栈上取不到证**：活栈实读 `sites/frontend/public/files/` **目录在、文件 0 个**，而唯一造得出对象的办法是往站点上传附件 —— **Non-Goals 3 逐字禁止**；Exit Criteria 又逐字禁止写「未观察」⇒ 三条凑在一起，执行器必违反其一 | §6 加一段🔴**开跑前写死的降级路径**：① 逐字禁止为取证上传附件；② `H10b` 改成打 `/files/<不存在>.html`（评审期实测回 **404** / `text/html` / 体 **330,562 字节**，有体可数），回答「经这条 location 出去的 HTML 会不会被改写」；③ 逐字写清边界 —— 它测的是**代理回来的 404 体**，「真实静态附件被损坏」仍是**推论**，降级为 `D-c-1` 里 (H) 的残余风险 + `not observed on this stack` 的照实登记，**从 Phase 3 Exit Criteria 的必填定量值里移出**（同步改了那一格） |
  | 新引入 1 | `D-c-4` 强制动作的**候选二按 nginx 语义写不出来**：`try_files` 的兜底项只能是文件/目录/`=code`/具名 location，其唯一可跑形态会把 `proxy_pass` **移出** `location /agenerp/`，正好打红 `test_explain_same_origin.py` 的**判据③** ⇒ 与 `D-c-2` 的 (c) 同性质，不是免费逃生口 | 两条候选**改成主次而非并列**：**① 具名 location（`@agenerp_asset`）为主路径**，`location /agenerp/` 原封不动；② 保留但当场逐字注明它撞判据③、与 (c) 同属「放宽既有判据是一次独立裁定」的形态。并补一句「**候选 ① 足以撑住这条链条，不要照着一条写不出来的配置去撞判据**」 |

  评审器同时确认**无其它新引入问题**、**§9 的 iteration 2 转述零失真**
  （逐行比对，「重演了阻塞 2 的形状」「损坏用户文件」这两处最刺的措辞都被保留、未软化），
  并给出收尾判断逐字：「**改完不需要再走一轮实质评审 —— 若你按此改定，我认为可以直接转 `active`**」。

- **Independent draft review iteration 4: `acceptable as-is`**（同一独立子代理，2026-08-25）。逐字三条理由：
  ① `H10b` **从「不可执行 + 禁止写未观察」的死结里解开了** —— 探针改成实测确有 330,562 字节
  `text/html` 体的 `/files/<不存在>.html`（今天就能跑），三条降级路径**写死在开跑之前而不是留给执行期现编**，
  且「降级形态的定量值仍是必填」与「真实静态附件被损坏 = 残余风险 + `not observed on this stack`」
  分得干净，那句「**不得反过来当成已证或已排除**」还堵上了「降级」与「已排除」之间最容易被后人读混的缝；
  ② `D-c-4` 的逃生口不再是一条写不出来的配置 —— 停机链条由候选①（具名 location）独立撑住，
  **既不会误停，也不会诱导执行器去放宽既有判据**；
  ③ 两处改法与评审给的写法逐条一致，四处措辞（Phase 3 填表项 / Exit Criteria / §6 降级段 / `D-c-1` 的代价要求）互相对齐，
  **未引入新的口径冲突**。
  评审器逐字结论：「**可以把 `> Plan Status: draft` 改成 `active`**」。

- **收敛过程**：`needs revision`（11 阻塞 + 11 非阻塞）→ `needs revision`（3 仍阻塞 + 2 新引入 + 1 提请注意）
  → `needs revision`（1 仍阻塞 + 1 新引入）→ **`acceptable as-is`**。**四轮全部由同一个独立子代理做，
  每轮都实跑复核而非采信 plan 自报**；四轮共 25 条问题，**零条被降级成 follow-up，全部就地改进 plan**。

- **评审器随最终裁定登记、且已在 plan 内各有归属的残余风险（不阻塞开工）**：
  `H3` 仍是最可能被证伪的一条（有 `H3b` 兜底、停机条件已写成合取式）·
  「真浏览器会不会执行这段 script」本 plan 不声称已证（承接者 = 工作项 11 的第 2 个 plan）·
  **WBS §4 P1.8b 的验收命令本 plan 从不声称满足**。

## 10. Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（§7.22 落地并回填实测值；roadmap 工作项 11 记下第 1 个 plan 的交付，**状态词仍是 `todo` —— 本 plan 不交付 ⌘K、不声称满足 WBS 第 88 行的验收命令**）
- [x] verification has run：`python3 tools/gates/check_expected_red.py` · `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` ·
      `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` · `docker compose up -d --wait`（冷起）
- [x] scoped verification is not conflated with full verification —— 未跑整仓 `pytest tests -q -m "not live"`
      / 未经 CI 服务端复跑 / 未做浏览器验证的，**逐条写明 `verification scope limited`**
- [x] no in-scope item downgraded to deferred/follow-up（Phase 1 的停机分支是**起草期写死**的，不算降级）
- [x] independent draft review completed and recorded（§9，**四轮**，末轮 `acceptable as-is`）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent（`docs/skills/closure-audit-prompt.md`）—— ⚠️ **留白，未做**。本轮执行环境不具备独立子代理，**执行者自己复跑不算独立审计**。先例：工作项 10 的收口同样留白（roadmap 该行末条）。**不自称已做。**
- [x] closure evidence exists in files（`docs/evidence/p1-desk-seam/` + `docs/analysis/…-probe.md`）
- [x] 红线自证（**四条一起，覆盖红线 1 / 2 / 3 / 5 / 6**）：
      ① `git status --porcelain -- tests/gates/ .github/workflows/` → 无输出 ·
      ② `git status --porcelain -- docs/masterplan/` → **只许出现 `STATE.md`**（红线 5：其余文件只读）·
      ③ `git diff -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **`0`**（只追加，不改写已有行）·
      ④ 证据仓（`evidence-repo.env` 的 `XM_PATH`）**一次都没写过** —— 本 plan 全程不触及它（红线 6）

### 收口实跑（命令原文 + 退出码，2026-08-25）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `门禁 26 项：预期红 0，绿 26，跳过 0` |
| `python3 -m pytest tests/unit -q` | **0** | **`801 passed, 6 skipped`**（开工基线 `779 passed, 6 skipped`，**+22 条，只增不减**） |
| `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` | **0** | `456 passed, 13 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` |
| `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` | **0** | `14 passed`（冷起后复跑同样 14 绿） |
| `git diff -- pyproject.toml` | — | **0 行**（零新增依赖） |
| `bash tools/check-masterplan-links.sh` | **0** | `共校验 35 条引用，断链 0 条` |
| `docker compose down -v` → `up -d --wait --wait-timeout 900` | **0** | 墙钟 **68 秒**，十个长期服务全 `running` |

⚠️ **收口途中被一条既有判据拦下一次，照实记，不粉饰**：§7.22 初稿有一行把
`tests/unit` 基线的 passed 与 skipped **用一条斜杠连着写**，命中了
`tests/unit/test_entry_gate_tally.py` 那条 P1.0 逐格计数守卫的数字面
（其前 4 行内有语境标识「门禁」）⇒ **2 failed**。
**语义上是误报**，但**处置是改本 plan 自己的措辞，不是放宽那条守卫** ——
放宽一条既有判据是**一次独立裁定**。改完复跑 **801 passed, 6 skipped**。
⚠️ 第一次改完**又红了一次**：解释那段误报时**把那个形状原样抄了进去**，
第二次改成描述性写法才转绿。**两次都记，不合并成一次。**

### 红线自证（四条实跑结果）

| # | 命令 | 结果 |
|---|---|---|
| ① | `git status --porcelain -- tests/gates/ .github/workflows/` | **无输出**（红线 1 / 2） |
| ② | `git status --porcelain -- docs/masterplan/` | **只出现 `STATE.md`**（红线 5：其余文件只读） |
| ③ | `git diff -- docs/masterplan/STATE.md \| grep -c '^-[^-]'` | **`0`**（只追加，不改写已有行） |
| ④ | 证据仓（`evidence-repo.env` 的 `XM_PATH`） | **一次都没写过**，全程未触及（红线 6） |

**另**：未生成任何运行时 Server Script（红线 7）；未改项目名 / 包名 / 命名空间（红线 4）；
未新增任何 `tests/*` 顶级目录（`gates.yml:560` 的 `COVERED` 守卫不受影响）。


## 11. Deferred But Adjudicated

### ⌘K 侧边栏本体 · `tests/ui/test_sidebar.py` · WBS P1.8b 的验收命令

- Classification: `moved to explicit successor ownership`
- Why Not Blocking Closure: 一个 plan 一个结果面（Minimum Rule 4）。本 plan 的结果面是
  **「本仓的 JS 到得了 Desk 页面吗」**，侧边栏的结果面是**「按下 ⌘K 之后发生了什么」**，
  两者的闭合判据不同、失败模式不同。**本 plan 从不声称满足 WBS P1.8b 的验收命令。**
- Successor Required: `yes`。**承接者写死：工作项 11 的第 2 个 plan**（表规 3 的最后一格预算），
  本 plan 收口后由 mission-driver 起草。
  **重开事件：本 plan `Plan Status` 转 `completed` 的那一刻。**
- ⚠️ 若本 plan 的 Phase 1 **三条停机分支任一**触发，**承接者不成立**。
  **出口按触发的是哪一条走**（逐字对齐 Phase 1 Exit Criteria 第 3 条，**不另立口径**）：
  触发 ① 或 ② ⇒ 出口是**人裁定 K3**（要不要动上游模板自己的行）；
  触发 ③ ⇒ 出口是**人批风险档**（`D-c-3` 落 L3 时）**或人裁 `D-a-2`**（`D-c-4` 判定适用时）。
  ⚠️ **「H3 不吻合」本身不是停机条件** —— `H3b` 那条只动本仓哨兵段的对冲优先。

### 真浏览器里的执行与 `sid` 自动携带

- Classification: `watch-only residual`
- Why Not Blocking Closure: 引浏览器驱动要装第三方依赖（Non-Goals 5）。
  ⚠️ **本仓至今没有任何真浏览器侧的实证** —— roadmap 工作项 10 逐字记过同一条
  （「真浏览器会不会把 `sid` 带到 `/agenerp/*` 上，本仓仍无实证 —— 那是工作项 11 的面」）。
  本 plan **没有把它关掉**，只是把它推进到「HTML 里确实有那个 `<script>`」这一步。
- Successor Required: `yes`。重开事件：**第 2 个 plan 需要判「⌘K 之后发生了什么」的那一刻** ——
  到那一步不引浏览器就判不动，届时「装不装驱动」成为必须回答的问题。
  ⚠️ **照实记一个已经看得见的紧处**：第 2 个 plan 是工作项 11 的**最后一格预算**，
  却要同时交 ⌘K + `tests/ui/test_sidebar.py` + 浏览器实证；而本 plan 用 Non-Goals 5
  立了「不引第三方依赖」的先例。若那个 plan 判定**必须引浏览器驱动**，
  那是一次**需人拍板的依赖决策**，且此后 P1.8b 的后继**只能由人在 `02-WBS.md` 拆行 / 加行**（红线 5）。
  **本 plan 只指明，不代人选。**

### `agenerp/site.py:485` docstring 里的悬空引用

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它在 docstring 里，不进运行路径、不进任何判据。
  `2026-08-25-0119-1` 的关闭审计已把它登记为非阻塞 follow-up，**本 plan 不改写那条登记**。
- Successor Required: `no`。**重开事件（事件式，不写「顺手」）**：
  **下一个 plan 的 diff 触及 `agenerp/site.py` 的那一段时** —— 届时由那个 plan 一并对齐；
  若那时 `tests/unit/test_explain_service.py` 仍不存在，则改成删掉这句引用。
