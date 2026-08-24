# P1.8 上半 · Desk 承载面选型（只读探测 + Decision）

> Plan Status: active
> Mission: p1-insight
> Work Item: 10. Agent 侧边栏嵌 Desk（P1.8）
> Execution Order: 2 / 2（本批第二个。**必须在 `2026-08-24-2311-1-immediate-context-into-explain-loop.md` 收口之后开工** —— 两者共用三处文档落点：`module-boundaries.md` 新增节 · `STATE.md` 只追加 · `docs/logs/2026/08-24.md`；开写前重读当时的最大节号再顺延）
> Last Reviewed: 2026-08-25（iteration 5 评审；起草基线 sha `e3de756`，`git status --porcelain` 除本批两个未跟踪的 plan 文件外无输出）
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 10 · `docs/masterplan/02-WBS.md` §4 **P1.8 行**（验收 `pytest -m live tests/ui/test_sidebar.py` 退 0）· `docs/masterplan/DECISIONS.md` **D-10**（自修改走构建期，不解开运行期）· `docs/architecture/system-baseline.md` §14.3「红线 7 在本节的落点」
> Related: 前置 = 本批第一个 plan（① 即时上下文接线）· 后继 = **P1.8 下半**（按本 plan 的 D1 落地承载面 + ⌘K + `tests/ui/test_sidebar.py`，**本轮不起草**，理由见 §3 Non-Goals 1）
> Audit: required

## 0. 执行前必做：重取基线

```bash
git -C . log -1 --format=%H && git status --porcelain
docker compose ps --format '{{.Service}} {{.Status}} {{.Ports}}'
sed -n '77,90p'  docs/context/ai-autonomy-policy.md   # Protected Areas 全表
grep -n "Client Script\|Server Script" docs/architecture/system-baseline.md
grep -rn "^### 7\." docs/architecture/module-boundaries.md | tail -3
```

### 0.1 执行期重取基线的**实读结果**

> 执行者填。**本节为空即视为未重取基线。** 落点节号在本节落定，后文一律引本节。

## 1. Current Baseline

### 1.1 P1.8 要的东西，本仓一行都没有

- **无任何产品侧前端资产**：`find . -iname "*sidebar*"` 无输出；没有产品侧 `.js` / `.vue` / `.css`；
  没有 `tests/ui/` 目录。
  ⚠️ **工装侧不在此列**（`tools/mission-driver/**` 的 40+ 个 `.js`、`docs/masterplan/plan.html`）——
  它们是构建设施，不是产品。
- `agenerp` 是一个纯 Python 包。**唯一经 HTTP 打「站点」的模块**是 `agenerp/site.py`；
  另一条是带外容器命令 `agenerp/oob.py`。
  ⚠️ 「唯一 HTTP 落点」这句（`site.py:5` 的模块头）**自 P1.1 起已不准确**：
  `agenerp/routing/adapter.py:197/206` 也在发 `urllib.request`（打 LLM 端点出网）。
  本 plan 只引「唯一经 HTTP 打**站点**」这一半。
- `agenerp.explain.explain()` 是**进程内函数**，跑在本机 Python 里，用 `SiteClient` 的
  **管理员凭据**打站点。**没有任何「被浏览器调用」的服务面。**

### 1.2 站点是官方镜像，`agenerp` 不在容器里

`docker-compose.yml` 用 `frappe/erpnext:v15.119.3` 官方镜像，**没有任何自建 app**，
也没有把本仓代码挂进去；唯一的宿主侧 bind mount 是 `./tools/bootstrap`，
且被判据钉成**字面路径**（`tests/unit/test_compose_zero_dep.py::test_bootstrap_script_dir_is_mounted_literally`）。
→ **今天浏览器无论如何都调不到 `agenerp` 的任何一行代码。**
⚠️ 顺带一个对 D1 有决定性影响的事实：若走自建 app 这条路，代码跑在 **backend 容器内**，
那里能直接用 Frappe ORM —— 也就是说 `agenerp/tools/**` 那套走 REST 的执行层
**在那条路上是用不上的、要重写第二份**。这不是本 plan 要解决的问题，但它是 D1 的输入。

### 1.3 本仓对「运行期注入代码」的既有立场，比红线 7 的字面更宽

- **红线 7 的字面**只禁 **Server Script**（`AGENTS.md` 红线表第 7 行；
  `ai-autonomy-policy.md` Protected Areas「运行时 Server Script 生成」= `blocked`）。
- **但** `docs/architecture/system-baseline.md` §14.3 逐字写着：引导交付物
  「不出现 `<script`……**不建 `Server Script` / `Client Script` 任何一种**」，
  判据是 `test_bootstrap_delivers_no_runtime_code`。
  ⚠️ **那条判据扫的是 `tools/bootstrap/` 目录与 `docker-compose.yml` 的 bootstrap 服务块两处**，
  作用域**不覆盖本 plan** —— 所以它是**文化立场**，不是能自动挡住本 plan 的判据。
  照实说清；**并且本 plan 不去利用这个缺口**（Non-Goals 2）。
- `DECISIONS.md` **D-10** 给出方向判据：**运行期**（文本存数据库、写完立刻生效、不可 diff / 不可 revert）
  vs **构建期**（代码进 git、走人审、装 app + **重启**才生效，「重启本身就是闸」）。
  结论是**走构建期那扇门**，重估「不早于 P2 跑通」，且「**loop 不得以『反正将来要解开』为由试探**」。
- `docs/architecture/open-questions.md` #20 实测记录：站点上 `Client Script` / `Server Script`
  **均为 0 条**，`server_script_enabled` 未启用。

### 1.4 三条候选承载路径（起草期已取到的实测事实，逐格标注出处）

| 候选 | 资产怎么到浏览器 | 解释请求跑在谁的进程里 | 身份 | 已知事实 / 待测 |
|---|---|---|---|---|
| **(A) 自建 Frappe app（构建期）** | app 的 `app_include_js` hook → `/assets/<app>/js/…` | app 里的 whitelisted method，**跑在 backend 容器内** | **原生就是当前登录用户** | **待测**：要改镜像 / 加挂载 / `bench install-app` + 重启中的哪几步。⚠️ **`bench install-app` 是否真的建 DocType / 发 DDL，本项目没测过**（H2b）—— 在测出之前**按见即停处理**，但**不得**据此先验地把 (A) 判成风险档 L3 |
| **(B) `Client Script` 文档（运行期）** | 站点 DB 里的一条 `Client Script` 记录 | **调不到 `agenerp`** —— 浏览器只能再去打别处 | 浏览器带当前用户 cookie | **起草期已实测**（`docker compose exec -T backend` 读镜像内 `client_script.json`）：`dt` 是 **`reqd: 1`** 的 `Link/DocType`，`view` 取值只有 `List` / `Form` ⇒ **它按 DocType 逐条挂，没有全局注入点**，做不出「全站 ⌘K 侧边栏」。且它正落在 D-10 的**运行期**那扇门 |
| **(C) 本机 HTTP 服务 + 浏览器跨源调用** | **到不了 Desk 页面**（没有注入点） | 本机 `python3 -m agenerp.serve` | **只有管理员凭据，认不出当前用户** | 不碰站点；但 (C) 单独**满足不了「嵌 Desk」**，只能与 (A)/(B) 组合 |
| **(B′) 同一扇门的其它入口**（`Website Script` / `Custom HTML Block`） | 同 (B)，另一张表 | 同 (B) | 同 (B) | **起草期已实测**：`custom_html_block.json` 有 `script`（`Code`/`JS`）、`website_script.json` 有 `javascript`（`Code`）⇒ **与 (B) 是同一扇门**（文本存 DB、写完立刻生效）。**待测**：它们各自的注入范围。⚠️ 它们**不在** §14.3 的措辞里、也不在那条判据的禁词表里 —— 这正是 §6 护栏必须按「门」而不是按「名字」定义的原因 |

**另外两条起草期实测（活栈 `127.0.0.1:18080`，`docker compose ps` 显示已 Up 14 小时）**：

- `GET /assets/frappe/images/frappe-favicon.svg` → **200，无任何 cookie**（`/assets/**` 由 nginx 公开静态服务）
- `GET /app` → **301**（跳 `/login?redirect-to=%2Fapp`）
- → **静态资产公开可取是承载面的已知属性，不是缺陷**；任何「未登录取不到资产」的判据在 (A) 上按构造判不绿。
  这条直接写进 D3 的残余风险，**不许当成权限判据**。

### 1.5 身份边界：今天的解释跑在 Administrator 上

`agenerp/site.py` 的凭据来自环境变量；P1.4 的活跑逐字记着「Administrator 不撞 403」。
P1.3 交付的开场 `permission.scope` 注入**是按 `SiteClient` 的身份算的**，不是按「浏览器里那个人」算的。
→ **一旦让浏览器发起解释，「答案按谁的权限算」立刻变成必须回答的问题**，
而 (A)/(B)/(C) 对它的答案完全不同（§1.4 身份列）。
本批第一个 plan 已把这条作为 `watch-only residual` 交接过来（其 §11 第三条，
重开事件逐字「P1.8 让浏览器发起解释的那一刻」）—— **本 plan 是那一刻的前一步**：
它不让浏览器发起解释，但它**必须替那一刻把身份口径定下来**（D2）。

### 1.6 WBS 那条验收命令的性质，以及一个必须现在就说清的账

`02-WBS.md` 表规 6 逐字：P1 及以后各行的验收命令是「**占位形状**，不是承诺存在的命令」，
「可改的是字符串，不可改的是形状」。`tests/ui/test_sidebar.py` 是具体路径，形状合规。
**本 plan 不交付它、也不声称满足它** —— 它属于 P1.8 下半。
⚠️ **账要现在记**：表规 3 是「一个工作项 = 1–2 个 plan，超过就拆行」，而拆行是
`docs/masterplan/` 编辑，**只有人能做**（红线 5）。本 plan + P1.8 下半 = 2 个，**刚好用满**。
若本 plan 的 D1 结论是「承载面需人批」，P1.8 下半就会卡在激活上、
`tests/ui/test_sidebar.py` 同样跑不起来 —— **那时工作项 10 在 2 个 plan 内交不出 WBS 验收命令**。
这个事实本身要写进 `STATE.md` §3 交人（§7 Phase 2 那条 `Add … STATE.md` 项的第 ② 小条），由人决定拆行还是等激活。

## 2. Goals

1. **把「Agent 侧边栏怎么进 Desk」从推测变成实测** —— 三条候选逐条探到
   「能 / 不能 / 需人批」，每格附命令原文与退出码或源码出处。**全程只读。**
2. **出一条有依据的 `Decision`**：选定承载面（D1）、身份口径（D2）、判定面口径（D3），
   各写清备选、否决理由、残余风险、翻案条件，并逐条对照 **D-10** 的两扇门。
3. **把 P1.8 下半需要的一切交接干净**：落点节 + `docs/analysis/` 探测记录 +
   `STATE.md` §3 的 needs-human（含命令原文与回滚原文）。
4. **越权处停机**：任何一步落到「强制人批」，就停在那里记进 needs-human，
   **不代人做、也不绕过去**。

## 3. Non-Goals

1. **不落地任何承载面、不写 ⌘K、不写侧边栏 UI、不建 `tests/ui/test_sidebar.py`。**
   理由不是省事，是**基线还不存在**：那一半的实现形态**完全由本 plan 的 D1 决定**
   （Minimum Rule 1「Start from live baseline」）。
   ⚠️ **连「先把与承载面无关的处理核写了」也不做** —— §1.2 已实测：走 (A) 时代码跑在
   backend 容器内、直接用 Frappe ORM，`agenerp/tools/**` 那套 REST 执行层用不上。
   在 D1 之前动手，有一半的概率是在造要扔的东西。
2. **不在活站点上建、也不改、也不写任何「运行期承载」**。
   ⚠️ 三个动词缺一不可：只写「不**建**」会漏掉 **Single**（它只能改、不能建），
   而 `Website Settings.head_html` 就是一个完整的注入点（§6 洞三）。
   点名覆盖：`Client Script` · `Server Script` · `Website Script` · `Custom HTML Block` ·
   `Workspace Custom Block` · **Single / Settings 上的 `Code` 字段**
   （`Website Settings.head_html` / `.banner_html` / `.brand_html` · `Website Theme` · `Navbar Settings`）·
   以及**任何在 §6 属性判定下「第一问有任一条不满足、或第二问有任一条为是」的承载物**（含不落 DB 的 userscript / 扩展 /
   `docker cp` / bind-mount 覆盖 `public/js`）。
   **点名是例子，判定以 §6 的属性为准。**
   §1.3 已指出 §14.3 那条判据扫不到本 plan —— **本 plan 不去利用这个缺口**。
   D-10 逐字禁止「以『反正将来要解开』为由试探」，而 (B) 想知道的结构事实
   **从镜像内的 doctype 定义就读得出来**（§1.4 已读出，一次写都没发）。
3. **不改 `docker-compose.yml`**（被 `tests/unit/test_compose_zero_dep.py` 与
   `tests/gates/test_zero_dep_boot.py` 两侧钉着；后者是**裁判**，红线 1）。
4. **不装 app、不发 DDL、不改权限、不改 Workflow、不跑 `bench migrate`**。
   ⚠️ 理由是 §5.1 的见即停清单，**不是**「`install-app` 会发 DDL」——
   后者本项目**没测过**（H2b），起草期第一版把它当事实写了，iteration 2 评审指出后撤回。
   **在测出之前按见即停处理，但不许先验地把 (A) 判成风险档 L3。**
5. **不建任何 HTTP 服务面**（`agenerp.serve` 之类）—— 归 P1.8 下半，且形态由 D1 决定。
6. **不对活站点做任何写**：本 plan 全程只读，因此
   `ai-autonomy-policy.md` 的「对活站点的非破坏性写」那一行**不被触发**，
   它括号里「`agenerp/seedsite.py` 目前是这两个写方法的唯一调用方」那句**仍然为真**，
   本 plan 不产生 owner-doc drift。
7. **不生成运行时 Server Script**（红线 7，无条件）。
8. **不动 `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块**：工作项 10 保持 `todo`。
9. **不碰 `tests/gates/**`、`.github/workflows/**`、`missions/*.json`、`docs/masterplan/**`**
   （红线 1/2/3/5）；`STATE.md` 只追加。

## 4. Task Route

- Type: `app-layer design change`（承载面选型 + 身份边界裁定；**无实现落地**）
- Owner Docs:
  - `docs/masterplan/DECISIONS.md` **D-10 / D-16**（**只读**；红线 3：一个字不改）
  - `docs/architecture/system-baseline.md` **§14.1**（**只读**，「回环 IP 必须字面写死」的出处）
    与 **§14.3**（**只读**，「不建 Client Script」的立场与其判据作用域）
  - `docs/architecture/system-baseline.md` **§13 三端划分**（Desk 原样保留、兜底落回 Desk）
  - `docs/architecture/open-questions.md` **#20**（**只读**，站点 Client Script 实测为 0 的出处）
  - `docs/design/agents-and-roles.md` **§9 风险档表**（**只读**，L0–L3 的出处；
    ⚠️ 与 §5.0 的**证据门禁 L1–L3 同名不同义**，全文引用必须带「风险档」三字）
  - `docs/context/ai-autonomy-policy.md` **Protected Areas**（**只读**）
  - `docs/architecture/module-boundaries.md`（落点表，本 plan 追加一节）
- Skill Selection Basis:
  Phase 1 是探测而非实现 → `Skill: none`（registry 无探索类 skill；`bug-diagnosis-prompt.md`
  不适用 —— 本 phase 没有 bug）；
  Phase 2 的裁定用 `development-wisdom-gate-prompt.md` 自查（它的 required input
  「assumption inventory」正是 §6 的假设表）；
  草案评审 `plan-audit-prompt.md`，关闭审计 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

- 活栈（起草期实测已 Up，`frontend` 映射 `127.0.0.1:18080->8080/tcp`）。
  **若需重起，命令原文照抄 `docs/context/project-context.md`**：
  `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300`
  ⚠️ 裸跑 `docker compose up -d` 会落到 **8080**（compose 里是 `${AGENERP_HTTP_PORT:-8080}`，
  `.env` 没有这个变量），而 8080 被本机另一套常驻 ERPNext 栈占着。
- 只读访问需要的环境变量：`AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` ·
  `AGENERP_ADMIN_PASSWORD`（或 `AGENERP_API_KEY` / `AGENERP_API_SECRET`）。
- **不需要** LLM 凭据：本 plan 不跑任何模型。
- **回滚**：本 plan 对活站点**只读**（Non-Goals 6），站点侧无需回滚；
  仓内改动 `git revert` 即完整回滚。
- **不做备份，因为不需要**：上一轮评审指出 `bench backup` 会往共用的 `sites:` volume 里写文件，
  正撞 §5.1 的「任何写 `sites/` 的命令」见即停，也与 Non-Goals 6「全程只读」自相矛盾；
  而且本仓**没有写过任何 restore 命令**，那份备份买不到任何东西。
  → **本 plan 不跑 `bench backup`**。保护手段是 §5.1 的白名单 / 见即停清单本身。

### 5.1 Phase 1 容器内探测的**命令白名单**与**见即停清单**（起草期写死，执行期不许现编）

上一轮草案评审点名：`sites:` 是 backend / worker / frontend **共用的 volume**，
里面装着已跑 14 小时的种子数据；「越权由执行者当场判定」不是契约。

**允许跑（只读）**：
`bench --help` · `bench --site frontend list-apps` · `bench --site frontend version` ·
`docker compose exec -T backend cat <镜像内文件>` · `docker compose exec -T backend ls <目录>` ·
`docker compose exec -T backend python3 -c "<表达式>"` —— ⚠️ **机械约束，不靠形容词**：
该表达式**不许 `import frappe`、不许建立任何 DB 连接**；需要站点数据一律走
`SiteClient` 的只读方法或 `curl` 的 `GET`（`frappe.init(); frappe.connect(); frappe.db.sql(...)`
这种一行式在字面上落在白名单里，正是这条要堵的缝）·
`SiteClient` 的只读方法 · `curl` 的 `GET`。

**见即停（一律不跑，直接记进 needs-human）**：
`bench install-app` · `bench new-app` · `bench get-app` · `bench build` · `bench migrate` ·
`bench uninstall-app` · `bench set-config` · `bench --site frontend drop-site` ·
`bench --site frontend restore` · `bench --site frontend reinstall` ·
`bench --site frontend backup` · `bench --site frontend mariadb` · `bench --site frontend console` ·
`bench --site frontend execute <method>` · 任何 `pip install` 进容器 · 任何写 `sites/` 的命令 ·
任何 `POST` / `PUT` / `DELETE` 到站点 · 任何对 `docker-compose.yml` 的编辑 ·
**裸跑 `docker compose up -d`**（会落到 8080，撞本机另一套常驻栈，见 §5）。

⚠️ **一条无例外的常设线**：**任何 `docker volume` 子命令、任何 `docker compose down` 子命令
（尤其带 `-v` / `--volumes` 的）一律见即停。**
`sites:` 是 backend / worker / frontend **共用**的 volume，里面是已跑 14 小时的种子站点；
删掉它不是「重起一下」，是要重跑整条种子装载链。

⚠️ **清单之外拿不准的命令，按「见即停」处理**，不按「允许」处理。

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

> **本 plan 的 Phase 1 是实验性质**，本表因此是它的判定骨架：下面七条在**跑任何一条命令之前**
> 逐字定稿，事后**只在「实际」列追加**。不吻合的照实记，并写清前提哪里错了。
> ⚠️ 结论只覆盖**本机这一套栈、这个镜像 tag、这一次**，不得外推（D-16）。
> ⚠️ **标了「复核项」的行（H3 / H4）是起草期就已读出答案的**，执行期是 **re-verify** 而不是预测。
> 它们**不计入「逐条吻合」的统计**（拿已知答案充预测会把那个统计注水）；
> 但**必须照跑** —— 镜像 tag 没变不等于读过的东西不用再读一遍（D-16 的纪律）。

| # | 假设（预测） | 怎么判 | 实际 |
|---|---|---|---|
| **H1** | 站点上**五类「代码存 DB」文档全部为 0 条**：`Client Script` · `Server Script` · `Website Script` · `Custom HTML Block` · `Workspace Custom Block`（前两类是复核 open-questions #20 今天是否仍成立，后三类本项目此前**没测过**）。**外加**：`Website Settings` 的 `head_html` / `brand_html` 为空、`banner_html` 为引导脚本写进去的那段静态文本；`Website Theme` / `Navbar Settings` 上的 `Code` 字段值一并记下作基准 | `SiteClient` 只读 list 五次 + 读 `Website Settings` / `Website Theme` / `Navbar Settings` 各一次；**这些值同时是 Phase 1「零写」读回的基准** | 待填 |
| **H2** | **(A) 走不完的第一处卡点，是一条外部规则而不是本 plan 自己的 Non-Goals**。预测：卡点是**把 app 源码弄进容器**这一步，它要么改 `docker-compose.yml`、要么写共用的 `sites:` volume；**外部约束是 `tests/gates/test_zero_dep_boot.py`（裁判，红线 1 保护）与 `tests/unit/test_compose_zero_dep.py`**。⚠️ **判定时必须指名外部规则的具体哪一行**，可引来源**五类**：Protected Areas · 风险档表 · 红线表 · **`tests/gates/**` 与 `tests/unit/**` 里的既有判据**（红线 1 保护的裁判）· `02-WBS.md` 表规。五类都引不到，则记 **`未测出`** 并走下面的分支 | 按 §5.1 白名单逐步探到第一处见即停命令为止 | 待填 |
| **H2b** | **`bench install-app` 到底发不发 DDL，本项目没测过**。预测：**对一个零 DocType 的最小 app，它不建表、不发 DDL**，只插 `Module Def` / `Installed Application` 两类行。⚠️ 因此**不得**先验地把 (A) 归到风险档 L3 第一格「新建 DocType（DDL）」—— 起草期第一版正是这么写的，iteration 2 评审指出该断言未经验证 | **只读**查证：读镜像内 `install_app` 的源码路径；**不跑该命令**（§5.1 见即停） | 待填 |
| **H3**<br>**复核项** | **(B) 无全局注入点**：`Client Script.dt` 是 `reqd: 1` 的 `Link/DocType`，因此它只能按 DocType 逐条挂 ⇒ **做不出「全站 ⌘K」** | 读镜像内 `client_script.json`，**只读，不建任何文档** | 待填 |
| **H4**<br>**复核项** | **(B) 的 `view` 取值只有 `List` / `Form`**，因此即使逐条挂也只覆盖两种视图。⚠️ **`view` 本身不是必填**（起草期实读 `reqd` 未设）—— 别据此推出「范围强制收窄」这种不存在的约束 | 同上，读同一个文件 | 待填 |
| **H5** | **(C) 单独满足不了「嵌 Desk」**：不存在**不改站点、不改镜像**的办法把一段 JS 送进 Desk 页面 | Phase 1 穷举并逐条记否决理由（含 `Website Script` / `app_include_js` / `bench build` 各自的落点） | 待填 |
| **H6a** | **(A) 上身份守得住**：whitelisted method 跑在 backend 容器内的**调用帧**里，`frappe.session.user` 天然是登录用户 | 纸面推演 + 指名接缝（调用帧）；**本 plan 不实跑解释**（Non-Goals 5） | 待填 |
| **H6b** | **(B) / (B′) 上身份守得住一半**：浏览器带 cookie 打站点那一段是登录用户，但它**够不到 `agenerp`**，真正作答的那一段身份未定 | 纸面推演 + 指名接缝（浏览器 cookie） | 待填 |
| **H6c** | **(C) 上身份守不住**：`SiteClient` 用的是环境变量里的管理员凭据，**服务端认不出浏览器里那个人** | 纸面推演 + 指名接缝（`agenerp/site.py` 的凭据来源） | 待填 |
| **H7** | **三条候选没有一条是 loop 今天走得完的**：(A) 卡人批、(B) 撞 §14.3 立场且无全局注入点、(C) 到不了 Desk。⚠️ **若此条不吻合**（即真有一条走得完），**停机交人，不由 loop 重排 D1** —— iteration 3 评审指出：原写法「停下来重判」把决定权留在了 loop 手里，而 H5 的反例（userscript 恰好就是「不改站点不改镜像也能送 JS 进 Desk」的办法）会经由 H7 悄悄变成一条可选路 | Phase 1 三格结论合取 | 待填 |

⚠️ **对称护栏 —— 按「门」定义，不按「名字」定义（iteration 2 评审逼出的第二版，逐字保留）**：

> **触发条件是一次属性判定，不是一张名单。**
>
> **判定对象：部署之后活在站点 / 浏览器 / 容器文件系统里的那个承载物本身 ——
> 不是把它送过去的那条管道。管道合规不豁免承载物。**
>
> **第一问 · D-10 的构建期三条**：① **代码进 git** ② **走人审** ③ **装 app 或重启才生效**。
> **第二问 · D-10 的运行期三个标记**（任一为「是」即落运行期那扇门）：
> ① 承载物是站点 DB / 浏览器 / 容器文件系统里的**一段文本**，
> **且它的内容不是逐字来自 git 跟踪的源文件**吗？
> ② **写完立刻生效**（没有「装 app / 重启」这道闸）吗？
> ③ 撤销**只能靠人手动删 / 手动改** —— `git revert` + 重起栈之后那份文本**仍然在**吗？
>
> **第一问有任一条不满足，或第二问有任一条为「是」，该结论本身即触发停机交人，不由 loop 裁定。**
> 「被选中」即触发，**不要求它是唯一可行项**（单独选中、或与 (C) 组合选中，一样触发）。

**两个词的定义写死，不留给执行者解释**：

- **「走人审」= 人**按 `docs/context/ai-autonomy-policy.md` Protected Areas 规定的批准手段放行
  （例如提交信息里的人工批准 trailer）。
  ⚠️ **子代理评审不算人审** —— 本 plan 自己的独立草案评审也不算。
  本仓的 loop 直接提交 `main`、不开 PR，若不写死这一条，loop 可以拿「我过了独立评审」自我认定 ②。
- **「装 app 或重启才生效」** 问的是**承载物的生命周期属性**，不是安装它的那一步做了什么。
  按这个读法，候选 (A)（真正的自建 Frappe app）**第一问三条仍然全满足** ——
  属性判定**没有**宽到「对什么都触发」，「选 (A)，但激活需人批」仍是 loop 走得完的合法结局。

**两问必须落在同一个承载物上、逐格答出来。起草期先把两个基准形状答死，执行期照抄这张表的格式
（iteration 5 评审逼出 —— 原稿只替 (A) 辩护了第一问，没答第二问）**：

| 承载物 | 一① 代码进 git | 一② 走人审 | 一③ 装 app/重启才生效 | 二① 非 git 源的文本 | 二② 写完立刻生效 | 二③ revert+重起后仍在 | 判定 |
|---|---|---|---|---|---|---|---|
| **(A) 真正的自建 Frappe app** | 是 | 是（人批放行） | 是 | **否** —— `apps/<app>/**` 逐字来自本仓 git | **否** —— 要 `install-app` + 重启 | **否** —— revert 源码 + 重起栈后那份文本不再来自本仓；卸载仍需人做，已由一② 的人批罩住 | **不触发** ⇒「选 (A)，但激活需人批」是合法结局 |
| **(D) 引导服务在起栈时写 `Website Settings.head_html`**（洞四那个形状） | 是 | 是 | 是（只在起栈时写） | 否 —— 内容来自 git 里的 `.py` | **是** —— 写进 DB 那一刻就生效，没有重启闸 | **是** —— `git revert` 撤不掉 DB 里那一行，本仓没有删任意文档的手段 | **触发停机交人** |

⚠️ **第二问 ① 那半句限定不可删**：光问「是不是某处的一段文本」，对**任何已部署的东西**都为「是」
（任何代码最终都是某处的一段文本），(A) 会被自己的护栏误杀，与上一段那句保证直接打架。
**真正做区分的是第二问 ②** —— 有没有「装 app / 重启」这道闸。

**已知落进「不满足」那一侧的例子（是例子，不是名单的全部）**：
`Server Script` · `Client Script` · `Website Script` · `Custom HTML Block` ·
`Workspace Custom Block` · **Single / Settings 上的 `Code` 字段**
（`Website Settings.head_html` / `.banner_html` / `.brand_html`、`Website Theme`、`Navbar Settings`）·
**浏览器侧 userscript / 扩展 / bookmarklet** ·
**`docker cp` 或 bind-mount 覆盖 `apps/frappe/frappe/public/js`** ·
**「由引导服务在起栈时写 Single 的 `Code` 字段」这种拆成两半的形状**（见下面洞四 ——
管道合规、承载物不合规，**按承载物判**）。

**为什么最终写成属性判定 —— 三版护栏各被打穿一次，照实记**：
- **洞一 · 按标签划范围**：第一版只点名 (B) = `Client Script`。而**同一扇门在镜像里不止一个入口** ——
  起草期实读 `frappe/desk/doctype/custom_html_block/custom_html_block.json` 有
  `script`（`Code`/`JS`）字段、`frappe/website/doctype/website_script/website_script.json` 有
  `javascript`（`Code`）字段，**两者都是「文本存数据库、写完立刻生效」**，正是 D-10 的运行期那扇门；
  而它们**既不在 §14.3 的措辞里、也不在 `test_bootstrap_delivers_no_runtime_code` 的禁词表里**。
  偏偏 Phase 1 第四项还专门派执行者「去找第四类」—— 于是选中 `Custom HTML Block`
  可以**一边落进运行期那扇门、一边如实报告「护栏不适用」**。
  （`Workspace Custom Block` 自身没有 `Code` 字段，是外壳；它引到的仍是上面那两类，一并罩住。）
- **洞二 ·「唯一」二字**：§1.4 自己写着 (C)「只能与 (A)/(B) 组合」。
  于是「(B)+(C) 组合走得完」在字面上就不是「(B) 是**唯一**」，护栏按自己的措辞不触发。
  → **删掉「唯一」，触发条件改为「被选中」而不是「排他」。**

- **洞三 · 枚举本身就是漏的**（iteration 3 评审实证，也是最终改成属性判定的原因）：
  按名单写的第二版仍漏掉两整类。
  ① **Single 上的 `Code` 字段** —— 起草期实读
  `frappe/website/doctype/website_settings/website_settings.json` 是 `issingle: 1`，
  带 `head_html` / `banner_html` / `brand_html` 三个 `Code`/`HTML` 字段；
  往 `head_html` 里塞一行 `<script src=…>` 就是完整的注入点。**它躲得过三重判据**：
  不在五个名字里 · Non-Goals 只写「不**建**文档」而 Single 只能改不能建 ·
  零写读回按**条数**比对而 Single 恒为 1 行。
  ⚠️ 本仓**已经在用这条路**：`tools/bootstrap/homepage_notice.py:70-74` 就在写 `banner_html`
  （`system-baseline.md` §14.3 决策① 采纳的那个首页横幅）—— 那一处是**静态文本**、且判据钉着它不含 `<script`；
  但同一个字段对本 plan 就是一扇没上锁的门。
  ② **根本不落在站点 DB 上的运行期承载** —— userscript / 浏览器扩展 / bookmarklet，
  或 `docker cp` / bind-mount 覆盖 `apps/frappe/frappe/public/js`：
  代码不进 git、写完立刻生效、没有重启闸，**是 D-10 运行期那扇门的实质**，
  而按「站点 DB 里的一行」写的护栏对它们**永远不会触发**。
  → **结论：名单挡不住这件事，只有属性判定挡得住。** 五个名字降级成例子。

- **洞四 · 拆成两半就能骗过属性判定**（iteration 4 评审实证，属性判定第一版仍有的洞）：
  把 JS **提交进 git**，再由**一次性引导服务**在 `docker compose up` 时写进
  `Website Settings.head_html`。逐条问构建期三条，**三条都能如实答「是」**
  （源码进了 git · 走了和仓里任何文件一样的评审 · 只在起栈时才写）——
  **护栏不触发，而部署后活在站点上的那个东西正是 D-10 的运行期那扇门**：
  文本存 DB、写完立刻生效、`git revert` 撤不掉（本仓没有删任意文档的手段）。
  ⚠️ 这不是硬凑出来的形状：**§14.3 决策① + `tools/bootstrap/homepage_notice.py:70-74`
  就是这个形状，而且是仓里已被采纳的做法**；再加上 §1.3 已经写明那条判据不覆盖本 plan，
  执行者完全可能顺着「先例在此」滑过去。
  → **修法是把判定对象钉在「承载物本身」而不是「管道」上，并补上第二问那三个运行期标记。**

⚠️ 还有一条不可逆性的事实要一起摆着：`agenerp/site.py` 有 `create_doc` / `ensure_doc`，
**删只有 `delete_custom_field` 一个** —— 本仓**没有**删除任意文档的手段。
运行期那扇门一旦落地，回滚只能人工在 Desk 里删。

## 7. Execution Plan

### Phase 1 — 只读探测：三条候选各探到「能 / 不能 / 需人批」

Status: planned
Targets: `docs/analysis/2026-08-24-2311-desk-embed-carrier-probe.md`（新建）· **无产品代码、无站点写**
Skill: `none`
Prereqs: 本批第一个 plan 已 `completed`；§0.1 已填（⚠️ **不做备份** —— §5 已说明理由，`bench backup` 在 §5.1 见即停清单里）

- Item Types: `Explore | Proof`（前五项为探索项、末项为 `Proof`；
  **结论未出之前不许写任何产品代码**。`Explore` 的授权出处是 Minimum Rule 9）

- [ ] `Explore` **(A) 自建 app**：从「资产怎么进 Desk」倒推所需的每一步，
      按 §5.1 **白名单**逐步探，**探到第一条「见即停」命令就停**。
      记下：是哪一步、命令原文（**写下来但不跑**）、它触发的**外部规则具体哪一行**
      （五类来源见 H2：Protected Areas · 风险档表 · 红线表 · `tests/gates/**` 与 `tests/unit/**`
      的既有判据 · `02-WBS.md` 表规）。
      ⚠️ **五类都引不到时记 `未测出`，并走下面写死的分支** —— 不许记成「需人批」
      （那是拿本 plan 自己的 Non-Goals 当外部规则，即 R2 点名的推卸）
- [ ] `Explore` **(A) 的 `未测出` 分支（起草期写死，不许现编）**：
      若 (A) 的卡点只能引到本 plan 自己的 Non-Goals，则
      ① 在 `STATE.md` §3 追加一条 needs-human，逐字写明「(A) **从未被真正测过**，
      挡住它的是本 plan 自己的定界，不是外部规则」；
      ② D1 **必须逐字复述这一句**，不许把 (A) 静默当成「已排除」；
      ③ H7 中 (A) 那一格记 `未测出`（**既不算吻合、也不算不吻合**）
- [ ] `Explore` **(B) `Client Script`**：**只读**镜像内 `apps/frappe/frappe/custom/doctype/client_script/client_script.json`
      验 H3 / H4；`SiteClient` 只读 list 验 H1。
      **一条文档都不建**（Non-Goals 2）。同时逐字核对它与 D-10 两扇门的对应关系
- [ ] `Explore` **(C) 本机 HTTP 服务**：只验「浏览器能不能从 Desk 页面调到它」，
      验 H5；同源策略 / cookie / CORS 三个障碍逐条记（**纸面 + 只读 `curl`，不起任何服务**）
- [ ] `Explore` **穷举第四类可能**：把「除上述三条之外还有没有别的办法」写成一段，
      逐条记否决理由。**写不出第四类就写「穷举到此为止，边界是……」** —— 不许留空
- [ ] `Proof` 把四项结果写成一张**与 §1.4 同结构的表**（同样的列），
      每格附命令原文 + 退出码或源码出处；**§1.4 原文保留不改**，两张表并排

Exit Criteria:

- [ ] 三条候选各有一格明确结论：`能（附证据）` / `不能（附失败命令与退出码）` /
      `需人批（附外部规则的具体哪一行）` / **`未测出`（附「挡住它的是本 plan 自己的定界」这句 + 一条 needs-human）**
- [ ] **H1 · H2 · H2b · H3 · H4 · H5 · H6a · H6b · H6c** 的「实际」列已填；H7 的合取结论已写
- [ ] **对活站点零写（两种读回，缺一不可）**：
      ① `bench --site frontend list-apps` 前后一致，且**五类「代码存 DB」文档**
      —— `Client Script` · `Server Script` · `Website Script` · `Custom HTML Block` ·
      `Workspace Custom Block` —— 的**计数**逐类仍为 H1 记下的值；
      ② **Single 上那几个 `Code` 字段的值前后逐字比对** ——
      `Website Settings.head_html` / `.banner_html` / `.brand_html`
      **以及 `Website Theme` 与 `Navbar Settings` 上的 `Code` 字段**
      （⚠️ 检测面必须与 Non-Goals 2 的禁止面**一样宽**，窄了等于禁了却测不到）。
      ⚠️ **② 不能省**：Single 恒为 1 行，**计数对它按构造无效**（§6 洞三）
- [ ] `docs/analysis/2026-08-24-2311-desk-embed-carrier-probe.md` 已落盘
- [ ] No owner-doc update required（本 phase 不改 owner doc）

### Phase 2 — Decision：承载面、身份口径、判定面口径

Status: planned
Targets: `docs/architecture/module-boundaries.md`（新增落点节，**接在 `### 7.11` 之后**，节号见 §0.1；⚠️ 该文件有 `### 7.x` 与 `### 11.x` / `### 12.x` 两套并存的编号族，本 plan 只进 `7.x` 族）· `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-24.md`
Skill: `development-wisdom-gate-prompt.md`
Prereqs: Phase 1

- Item Types: `Decision | Add | Fix`

- [ ] `Decision` **D1 · 承载面**：从 Phase 1 的实测表里选一条，写清
      ① 选中项 ② 三条备选各自的否决理由（**引实测格，不引 §1.4 的起草期推测**）
      ③ 它落在 D-10 的**哪扇门**、为什么这不构成对 D-10 的试探
      ④ 残余风险 ⑤ 翻案条件。
      ⚠️ **「选它，但它需要人批」是合法结论**；⚠️ **§6 的对称护栏优先于本项** ——
      **若 D1 选中项在 §6 的属性判定下「第一问有任一条不满足、或第二问有任一条为是」，
      则停机交人，不出 D1**。
      ⚠️ 这里**不写「只剩 (B)」那种窄触发** —— 那是枚举时代的措辞，
      一个「(D) 由引导服务写 `head_html`」的 D1 读到它会正确地得出「不适用」（§6 洞四）
- [ ] `Decision` **D2 · 身份口径**：解释请求按谁的权限作答？三个候选：
      (i) 当前登录用户（只有 (A) 原生做得到）
      (ii) Administrator（**今天的实然**，等于把信息越权暴露给任何能打开侧边栏的人）
      (iii) 显式降权（服务面按传入身份重建一个受限 `SiteClient`）。
      必须选一个并写清残余风险；**选 (ii) 必须逐字写明它是一次已知的信息越权**，
      给出重开事件，**不许粉饰成「暂未实现」**。
      ⚠️ 无论选哪个，都要**逐字写出 P1.8 下半必须交付的那条判据的形状**：
      「登录判定必须把请求里的 Frappe `sid` cookie 转发给站点、断言
      `frappe.auth.get_logged_user` 回的是那个用户」+「伪造 / 过期 `sid` 必须被拒」
      —— 上一轮评审实证：不写死这条，一个自定义 `X-Logged-In` 头就能骗过所有判据
- [ ] `Decision` **D3 · 判定面口径（交给 P1.8 下半的判据清单）**：逐字写死下半必须满足的最小集，
      **每条注明它挡的是哪种假实现**。起草期已知必须包含这五条：
      **① 静态资产公开可取是承载面的已知属性**（§1.4 实测：`/assets/**` 无 cookie 也回 200），
      **不许拿它当权限判据**；权限只判解释端点那一侧。
      **② 同一性**：注入内容里必须出现只有该 `{doctype, name}` 才有的值。
      **③ 差分**：换一个 `name` 跑第二次，结果必须**不同** —— 挡「服务端忽略 `name`、
      永远取回同一张单据」（本仓已踩过同形状的坑：roadmap 工作项 5 逐字「M6 第一轮是绿的」）。
      **④ 绑定地址字面写死 `127.0.0.1`、不经环境变量**（`system-baseline.md` §14.1 同一条理由的又一次应用），
      且缺失 / 异常 `Origin` 的请求被拒；配变异「改成 `0.0.0.0` → 应红」。
      **⑤ 坏输入的期望在动手前写死**：不存在的 `{doctype, name}` / 空 `question` / 超长 `question`
      三种，各自的状态码与错误标识**逐条预先写死**（先例：P1.6 的 `0/3/4/5` 四种可区分退出码），
      事后只填「实际」
- [ ] `Add` 落点节（节号见 §0.1）：写 D1/D2/D3 与被否决的备选、Phase 1 的实测表、
      以及本 plan **没有落地任何承载面**这个事实
- [ ] `Add` `docs/masterplan/STATE.md` §2 追加证据行；**§3 追加 needs-human，至少两条**：
      ① D1 若需人批 —— 命令原文 + 回滚原文 + 它触发的外部规则那一行；
      ② **工作项 10 的 plan 预算账**（§1.6）：本 plan + P1.8 下半已用满表规 3 的 2 个；
      若承载面卡在人批上，`tests/ui/test_sidebar.py` 跑不起来，
      **工作项 10 将在 2 个 plan 内交不出 WBS 验收命令** —— 拆行是 `docs/masterplan/` 编辑，
      **只有人能做**（红线 5），loop 不代改
- [ ] `Fix` **改准 `agenerp/site.py:5` 的那句陈旧模块注释**：
      「本模块仍是唯一的 HTTP 落点」自 P1.1 起为**假** ——
      `agenerp/routing/adapter.py:196-208` 也在发 `urllib.request`（打 LLM 端点出网）。
      改成「唯一经 HTTP 打**站点**的模块；出网打 LLM 端点的是 `agenerp/routing/adapter.py`」。
      ⚠️ **这是 Minimum Rule 14 的不可降级项**（confirmed contract drift），
      §1.1 发现了它就必须给它一个归宿，**只改注释、不动行为**。
      验证：`ruff check agenerp` 退 0（本 plan 唯一一条会跑的命令）
      ⚠️ `docs/architecture/module-boundaries.md:1397` 的「连活站点的**唯一 HTTP** 传输落点」
      在「打站点」这个读法下**仍然成立**，**不改它**
- [ ] `Add` `docs/logs/2026/08-24.md` 追加一条

Exit Criteria:

- [ ] **D1**：选中项 + 备选 + 否决理由 + 残余风险 + 翻案条件
      （**或**：按 §6 对称护栏停机交人，停机理由必须**逐格引到 §6 两问的哪一格**，
      并在 `STATE.md` §3 追加对应 needs-human）
- [ ] **D2 与 D3 无论 D1 走哪条路都必须落盘** —— ⚠️ 上一条的「或」**只覆盖 D1 这一项**。
      D3 的五条判据形状是本 plan 交给 P1.8 下半的**全部价值**（§8 R5：硬约束① 前移到 D3）；
      若允许它随 D1 停机一起消失，本 plan 就退化成 iteration 1 已判定为「逃生舱」的那种结局。
      D2/D3 各有：选中项 + 备选 + 否决理由 + 残余风险 + 翻案/重开条件
- [ ] D1 逐字对照过 D-10 的两扇门
- [ ] D3 的五条判据形状逐字落盘（它们是 P1.8 下半的输入契约）
- [ ] 落点节存在；`docs/masterplan/DECISIONS.md` **一个字未改**（红线 3）——
      本 plan 的三条裁定是**应用层裁定**，不是主计划决策，这句写进落点节
- [ ] `STATE.md` §3 的两条 needs-human 已追加
- [ ] **`agenerp/site.py:5` 的陈旧注释已改准**（Minimum Rule 14 不可降级项），
      `ruff check agenerp` 退 0 —— 命令原文与退出码写进 `## Closure`；**行为代码一行未动**
- [ ] `docs/logs/` 已更新

## 8. 风险

**R1 · 本 plan 交付的是「结论」，不是「代码」**

这是有意的（§3 Non-Goals 1）。它的合法性来自 Minimum Rule 9
（「If a decision requires prototyping or exploration before committing, add a temporary
`Explore` item that must conclude before the `Decision` resolves」）—— **Rule 9 本身就是足够的授权**。
⚠️ **不拿 P1.0 当先例**：上一轮评审核过，`2026-08-24-P1.0-entry-gate-experiment.md`
的 Targets 含 `tools/experiments/p1_entry_gate/` 等五处，`Item Types: Add`，还有独立的 `Proof` phase
—— **它交付了实验设施与可跑证据**。本 plan **连实验设施都不交付**，
理由是 §3 Non-Goals 1（承载面未定之前动手，有一半概率在造要扔的东西）。
两者不是同一种 plan，照实说清。
⚠️ **真正的失败形态是探索没做完就开始写代码** —— Phase 1 的 Item Types 逐字写着
「结论未出之前不许写任何产品代码」。

**R2 · loop 可能越界替人做决定**

处置：D1 允许输出「选它，但它需要人批」；**判断标准不是"难不难"，是"哪条规则说了算"** ——
每一处「需人批」都必须引到 Protected Areas / 风险档表 / 红线表的**具体某一行**，
引不到就不许自称越权（那是推卸）。H2 的判定栏已把这条写成硬要求。

**R3 · Explore 可能被自己的 Non-Goals 预先决定了结果**

上一轮评审的核心指控。处置有三条，都写在纸上：
① H2 要求卡点必须引到**外部**规则，引不到就记「同义反复，未测出」；
② §6 的**对称护栏**：按属性判定，**选中项只要落进运行期那扇门就停机交人**，
不由 loop 裁定（**不是**「只剩 (B)」那种窄触发 —— 见 §6 洞三 / 洞四）；
③ H7 的默认预测就是「三条没有一条走得完」，且写明不吻合时必须**重判而不是顺手改**。
⚠️ 残余风险照实记：**这三条挡得住"结论被 Non-Goals 决定"，挡不住"探索做得浅"**。
后者由收口审计核 —— Phase 1 的第四项（穷举第四类）就是给它准备的抓手。

**R4 · 身份不守是一个真实的信息越权，不是"待完善"**

§1.5 已摆明。D2 若选 (ii)，必须逐字写明它是已知的信息越权，
并把「今天不守」的判据形状交给下半（D3 ②③ 之外的那条）——
钉住之后它会在有人修好那天变红，逼人来处理；写成注释则永远没人处理。

**R5 · 本 plan 没有代码判据，硬约束①（判据不许只验「调得通」）怎么兑现**

**照实说：本 plan 没有可跑的判据，因为它没有交付可跑的东西。**
它对硬约束①的兑现方式是**把那条约束前移到 D3** —— D3 的五条判据形状是
P1.8 下半的**输入契约**，每一条都写明「挡的是哪种假实现」。
收口审计**核 D3 那五条是否逐字落盘**，而不是核本 plan 跑了多少测试。
⚠️ 这条替代关系是显式的、写在纸上的；**不许在收口时被当成"本 plan 免于判据要求"**。

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，fresh session，2026-08-24）
  because 11 条 BLOCKING + 12 条 NON-BLOCKING。最重的两条是结构性的：
  ① **Phase 1 原本要 loop 在活站点上真建一条 `Client Script`** —— 那正是 D-10 逐字禁止的「试探」，
  而且**多余**：想知道的结构事实从镜像内的 doctype 定义就读得出来；
  ② **原稿的 Non-Goals 2/3 + H2 + H5 在起草期就关掉了 (A) 与 (C)**，
  使「实测」在结论出来之前只剩 (B) 一个出口，而 (B) 正是 §14.3 说不做的那扇门 ——
  **预设立场是结构性的，不是措辞上的**。
  其余 BLOCKING：本仓没有删任意文档的手段（建了删不掉）· E1「未登录拿不到资产」在 (A) 上
  按构造判不绿（`/assets/**` 公开可取，评审侧实测）· 一个自定义 `X-Logged-In` 头能骗过
  E1/M1 全部判据 · E2/M2/M3 挡不住「服务端忽略 `name`、字段表写死」· §8 R5 与
  Phase 3「结局乙」直接矛盾 · 结局乙没有任何可跑形状 · (A) 的探测面比 Non-Goals 宽
  （`bench build` 等会动共享 `sites:` volume）· 新开的服务面没有绑定地址与跨源契约 ·
  Phase 1 会让 Protected Areas 的一句话变成假话而无人负责改准。
- 处置（iteration 1 → 本稿）：**23 条全部就地处置，无一降级为 follow-up。**
  其中三条改动改变了 plan 的形状，逐条记：
  (a) **删掉原 Phase 3（最小端到端接线）整节**，本 plan 收窄为**只读探测 + Decision**。
  连带删掉「甲 / 乙两分支」那套分支规则 —— 评审逐字判定它是**逃生舱**
  （乙分支是默认结局却写得最松）。
  ⚠️ **这是缩小 scope，按 Minimum Rule 10 记账**：被移出的工作**整体移交 P1.8 下半**，
  不是删掉；移交内容不是空话，而是 D3 那五条**逐字写死的判据形状**。
  另有一条独立理由（原稿没有、评审逼出来的）：§1.2 实测表明走 (A) 时代码跑在 backend 容器内、
  直接用 Frappe ORM，`agenerp/tools/**` 那套 REST 执行层用不上 ——
  **在 D1 之前动手，有一半概率是在造要扔的东西**；
  (b) **Phase 1 全面改成只读**，新增 §5.1 的命令白名单 / 见即停清单 + 探测前备份；
  连带 Non-Goals 6 成立（对活站点零写 ⇒ 不产生 owner-doc drift）；
  (c) **新增 §6 的对称护栏**（「只剩 (B)」这个结论本身即触发停机交人）与 H2 的
  「卡点必须引外部规则、引不到即记同义反复」，用来堵死 R3 那条预设立场的路。
- Independent draft review iteration 2: **needs revision**（独立子代理，fresh session，2026-08-24）
  after 删掉原 Phase 3、Phase 1 全面改只读、新增对称护栏。
  评审侧**确认**：scope 缩小合法且 §9 记录诚实，D3 的五条判据形状**足以承载被移走的工作**
  （不是空头承诺）；「只出决策不出代码」在此处可接受，R5 的前移**不是变相豁免**。
  **但判定「去偏」没做完**，八条 BLOCKING：
  ① **护栏按标签划范围**——同一扇门在镜像里不止一个入口：`Custom HTML Block` 有 `script`（`Code`/`JS`）、
  `Website Script` 有 `javascript`（`Code`），**两者都是「代码存 DB」**，
  却既不在 §14.3 的措辞里、也不在那条判据的禁词表里，而 Phase 1 第四项还专门派人「去找第四类」
  ⇒ 选中 `Custom HTML Block` 可以一边落进运行期那扇门、一边如实报告「护栏不适用」；
  ② **护栏里的「唯一」二字是字面漏洞**——§1.4 自己写着 (C)「只能与 (A)/(B) 组合」，
  于是「(B)+(C) 组合」在字面上就不是「唯一」；
  ③ **H2 的可引来源清单排除了真正管着 (A) 的那条规则**（挡住 (A) 的是
  `test_zero_dep_boot.py` / `test_compose_zero_dep.py` 这两条判据，不是那三张表里的任何一行），
  于是 (A) 既不能记「走得完」也不能正当地记「需人批」，而 `未测出` 分支**没有定义**
  ⇒ H7 关于 (A) 的那一格既不可证实也不可证伪（**另一个方向上的不可证伪**）；
  ④ §5 的 `bench backup` 撞自己 §5.1 的见即停、也撞「全程只读」，且本仓没有 restore；
  ⑤ 见即停清单漏掉真正能毁掉共用 `sites:` volume 的命令（`docker compose down -v` / `docker volume rm` /
  `drop-site` / `restore` / `reinstall` / `get-app` / `mariadb` / `console` / `execute`）；
  ⑥ §1.1 确认了一处 drift（`site.py:5` 的「唯一 HTTP 落点」自 P1.1 起为假）却**没给它任何归宿**（违反 Rule 14）；
  ⑦ §11 第三条把从上一个 plan **继承来**的重开事件改晚了（「对本机以外开放」晚于「浏览器第一次发起解释」），
  而 D2 自己说伤害在回环上就已发生；
  ⑧ 红线自证只钉 `DECISIONS.md`，而 §1.6 点名的诱惑是去 `02-WBS.md` 拆行 —— 门禁会照样绿。
  另有六条 NON-BLOCKING（拿 P1.0 当「不交付制品」的先例是错的 · H3/H4 是已知答案充预测 ·
  H6 不可证伪且对 (A) 按构造为假 · 零写读回没覆盖最容易误写的那几张表 ·
  白名单里的 `python3 -c "<纯读表达式>"` 用形容词把执行者判断又放回来了 · 两处文字不一致）。
- 处置（iteration 2 → 本稿）：**十四条全部就地改**，无一降级为 follow-up。形状改动四处：
  (a) **对称护栏改成按「门」定义**（枚举五类「代码存 DB」文档 + 任何等价物），
  **删掉「唯一」**、触发条件由「排他」改为「被选中」，并加一条不可逆性事实
  （本仓只有 `delete_custom_field`，**没有删任意文档的手段**）；
  §1.4 补第四行 (B′)、Non-Goals 2 同步按门列举；
  (b) **H2 拆成 H2 + H2b**，可引来源加到四类（含红线 1 保护的既有判据与 `02-WBS.md` 表规；**后于 iteration 3 扩为五类**），
  **`未测出` 分支在起草期写死**（needs-human + D1 必须逐字复述「(A) 从未被真正测过」+ H7 那格既不算吻合也不算不吻合）；
  同时**撤回未经验证的「install-app 会发 DDL」断言**，改成 H2b 的只读查证目标；
  (c) **删掉 `bench backup`**（本 plan 真的全程只读），见即停清单补全并加一条无例外的常设线；
  `python3 -c` 改成机械约束（不许 `import frappe`、不许建 DB 连接）；
  (d) **新增一条 `Fix` 项**：改准 `agenerp/site.py:5`（Rule 14 不可降级），只改注释不动行为。
  H3/H4 标成**复核项**且明确不计入吻合统计，H6 拆成 H6a/H6b/H6c 各自钉一条接缝，
  §11 第三条恢复继承来的重开事件并把原措辞降为附加条件。
- Independent draft review iteration 3: **needs revision**（独立子代理，fresh session，2026-08-24）
  after 护栏按「门」重写、`未测出` 分支写死、见即停补全、新增 Rule 14 的 `Fix` 项。
  评审侧**确认**：iteration 2 的十四条修复全部真的落进正文；**候选 (A) 现在可判**
  （五类可引来源 + `未测出` 分支 + H7 那格「既不算吻合也不算不吻合」，三种走向都有落点）。
  **但护栏又被打穿一次**，四条 BLOCKING：
  ① **Single 上的 `Code` 字段整类逃逸** —— `Website Settings` 是 `issingle: 1`，
  带 `head_html` / `banner_html` / `brand_html` 三个 `Code`/`HTML` 字段。它躲得过三重判据：
  不在五个名字里 · Non-Goals 只写「不**建**文档」而 Single 只能改不能建 ·
  零写读回按**条数**比对而 Single 恒为 1 行。⚠️ 本仓 `tools/bootstrap/homepage_notice.py:70-74`
  **已经在写 `banner_html`**（首页横幅），同一个字段对本 plan 就是没上锁的门；
  ② **不落 DB 的运行期承载整类逃逸** —— userscript / 扩展 / bookmarklet /
  `docker cp` / bind-mount 覆盖 `public/js`，都是「代码不进 git、写完立刻生效、无重启闸」，
  而按「站点 DB 里的一行」写的护栏对它们永不触发；更糟的是 **H5 的预测正好被 userscript 反证**，
  而 H5 不吻合只落到 H7，H7 的处置写的却是 loop「重判」而不是停机；
  ③ Phase 1 的 `Prereqs` 仍写「§5 的备份已跑」，而 §5 已删掉备份、§5.1 把 `bench backup` 列进见即停；
  ④ H2b 撤回的断言**没在正文撤干净** —— §1.4 (A) 行与 Non-Goals 4 仍以事实语气写着
  「`install-app` 会发 DDL ⇒ L3 ⇒ 强制人批」，而 Non-Goals 是 binding 的，
  (A) 因此仍被起草期预先判成需人批。
  另三条 NON-BLOCKING（(B′) 行脱出表格 · 「四类」实列五项 · Phase 1 Exit 漏了 H6a/b/c）。
- 处置（iteration 3 → 本稿）：**七条全部就地改**，无一降级为 follow-up。**一处根本性改动**：
  **护栏由「名单」改成「属性判定」** —— 对 D1 打算选中的承载物逐条问 D-10 的构建期三条
  （代码进 git · 走人审 · 装 app 或重启才生效），**只要有一条不满足就停机交人**；
  五个名字与新补的两类（Single 的 `Code` 字段、不落 DB 的 userscript / bind-mount）
  **一并降级为例子**。理由写进 §6「洞三」：**三版护栏被打穿三次，每次都是枚举漏了一类；
  名单挡不住这件事，只有属性判定挡得住。**
  连带：Non-Goals 2 改成「不建、**不改、不写**」（只写「不建」漏得掉 Single）；
  Phase 1 的零写读回加**第二种**——Single 那几个 `Code` 字段的**值**前后逐字比对
  （计数对 Single 按构造无效）；H1 的基准值一并扩到 `Website Settings`；
  H7 不吻合的处置由「停下来重判」改为「**停机交人，不由 loop 重排 D1**」。
- **共识达成**：iteration 3 的四条 BLOCKING 已就地改完，且第 ① / ② 条的修法是**取消枚举本身**
  而不是往名单里再加两个名字 —— 后者是前三版被连续打穿的原因。
  ⚠️ **本 plan 仍为 `draft`**：护栏刚做过一次根本性重写，**该改动本身未经独立复核**。
  按 `docs/plans/00-plan-authoring-and-execution-guide.md` 的 Plan Status Flow，
  转 `active` 需要再过一轮独立评审（iteration 4）确认属性判定这一版没有新洞。
- Independent draft review iteration 4: **needs revision**（独立子代理，fresh session，2026-08-25）
  after 护栏由「名单」改成「属性判定」。
  评审侧**确认**：iteration 3 的八处修复全部落进正文；且属性判定**没有**宽到「对什么都触发」——
  候选 (A) 三条全过，「选 (A)，但激活需人批」仍是 loop 走得完的合法结局，
  Phase 1 的探索没有被预先注销。
  **但属性判定第一版仍被打穿一次**，三条 BLOCKING：
  ① **拆成两半就能骗过它** —— 把 JS 提交进 git，再由一次性引导服务在 `docker compose up` 时
  写进 `Website Settings.head_html`：构建期三条**逐条如实答「是」**（源码进了 git · 走了正常评审 ·
  只在起栈时才写），护栏不触发；**而部署后活在站点上的那个东西正是运行期那扇门**。
  ⚠️ 关键在于 **`tools/bootstrap/homepage_notice.py:70-74` + §14.3 决策① 就是这个形状、
  且是仓里已被采纳的做法**，执行者顺着「先例在此」就滑过去了。
  病根：三条问的是**管道**，不是**承载物**；
  ② **「走人审」没有定义** —— 本仓 loop 直接提交 `main`、不开 PR，
  它可以拿「我过了独立子代理评审」自我认定 ②（而 `plan-audit-prompt.md` 明说子代理从不批准 protected area）；
  ③ **Phase 2 D1 项与 §8 R3 ② 仍写着枚举时代的窄触发「若结论是『只剩 (B)』」** ——
  那是执行者真正会读的那行契约，一个「(D) 引导服务写 `head_html`」的 D1 读到它会正确地得出「不适用」。
  另两条 NON-BLOCKING（检测面窄于禁止面：Non-Goals 2 点名了 `Website Theme` / `Navbar Settings`
  而 H1 与零写读回只覆盖 `Website Settings` · §9 里一处历史记述与正文的「五类」易被引成矛盾）。
- 处置（iteration 4 → 本稿）：**五条全部就地改**，无一降级为 follow-up。核心改动三处：
  (a) **给属性判定钉死判定对象** ——「部署之后活在站点 / 浏览器 / 容器文件系统里的**那个承载物本身**，
  不是把它送过去的管道；**管道合规不豁免承载物**」；
  (b) **补第二问：D-10 的三个运行期标记**（是不是 DB / 浏览器 / 容器里的一段文本 ·
  写完是否立刻生效 · 撤销是否只能人手删、`git revert` 撤不掉），**任一为「是」即停机交人**；
  (c) **把「走人审」写死**为「人按 Protected Areas 的批准手段放行，**子代理评审不算**」，
  并注明三条问的是承载物的**生命周期属性**，故 (A) 按构造仍全满足。
  连带：D1 项与 R3 ② 的窄触发换成属性判定；检测面扩到 `Website Theme` / `Navbar Settings`。
  §6 新增「洞四」，把这次被打穿的形状与它的仓内先例照实写进去。
- Independent draft review iteration 5: **accept**（独立评审步骤，fresh session，2026-08-25）
  after 属性判定钉死判定对象 + 补第二问三个运行期标记 + 「走人审」写死 + D1/R3 换掉窄触发。
  评审侧**核过**：iteration 4 的五条修复全部真的落进正文（判定对象那句、第二问三标记、
  「子代理评审不算人审」、Phase 2 D1 项与 §8 R3 ② 的窄触发已换成属性判定、
  检测面已扩到 `Website Theme` / `Navbar Settings`）；`site.py:5` 那处 drift **实读复核为真**
  （逐字「本模块仍是唯一的 HTTP 落点」），`### 7.11` 实读确为 `7.x` 族末节，落点节号顺延成立；
  forbidden-words 扫描无命中，Rule 12 的 `Status: completed` + 未打勾扫描为空。
  **四条 BLOCKING / MAJOR 已在本轮就地改完，无一降级为 follow-up**：
  ① **属性判定第二版会误杀 (A)** —— 第二问 ①「是不是某处的一段文本」对**任何已部署的东西**
  都为「是」（(A) 的 `apps/<app>/**` 也是容器文件系统里的文本），而触发条件是「任一为是」，
  于是 (A) 必被判停机；正文却在两段之后逐字保证「选 (A)，但激活需人批仍是走得完的合法结局」
  —— **护栏最核心的那条规则和它自己的保证直接打架，执行者无所适从**。
  修法：给第二问 ① 补上「**且内容不是逐字来自 git 跟踪的源文件**」这半句、给 ② 补「没有装 app/重启这道闸」、
  给 ③ 改成「`git revert` + 重起栈之后那份文本仍然在」，并新增一张**两问逐格实答表**，
  起草期就把 (A) 与洞四那个 (D) 形状答死（(A) 六格全不触发；(D) 命中二②、二③）。
  ⚠️ 照实记：真正做区分的是**第二问 ②**，①/③ 是配套。
  ② **Non-Goals 2 与 Closure Gates 仍只引「不满足构建期三条」** —— 第二问是 iteration 4 才加的，
  这两处没同步 ⇒ 洞四那个形状在 binding 的 Non-Goals 里**照样不被禁**。已同步成「两问」。
  ③ **Phase 2 Exit Criteria 的「或按护栏停机」把 D2/D3 一起带走了** —— 原写法「D1/D2/D3 三条各有…
  （**或**：停机交人）」，那个「或」在字面上覆盖三条。而 §8 R5 逐字把硬约束① **前移到 D3**，
  R1 又声明本 plan 不交付任何代码 ⇒ 一旦 D1 停机，本 plan 可以什么都不留就收口，
  **正是 iteration 1 判定为「逃生舱」的同一物种**。已把「或」收窄到只覆盖 D1，
  并写死「D2 与 D3 无论 D1 走哪条路都必须落盘」。
  ④ **Phase 2 Exit Criteria 漏了 Rule 14 那条 `Fix` 的落地判据** —— `agenerp/site.py:5` 改准 +
  `ruff check agenerp` 退 0 只出现在 Closure Gates，phase 自己的 Exit 里没有；
  按本指南「finish a slice → check off all its execution items and exit criteria」，
  这一项可以在 phase 收口时无声掉队。已补进 Phase 2 Exit Criteria。
  另一条 NON-BLOCKING 已顺手改：Phase 1 的 `Item Types` 只写 `Explore`，而末项是 `Proof`，
  已改为 `Explore | Proof` 并注明 `Explore` 的授权出处是 Minimum Rule 9。
  ⚠️ **残余风险照实记**：本轮改的仍是**纸面判定规则**，护栏至此被打穿过四次、每次都是
  执行前想不到的形状；两问逐格实答表把判定成本降下来了，但**挡不住「探索做得浅」**（§8 R3 残余）。
  这条留给收口审计，抓手仍是 Phase 1 第五项（穷举第四类）。
- **转 `active` 的依据**：本轮四条已就地改完，且第 ① 条的修法经两问逐格实答表**自证不误杀 (A)**
  （(A) 六格全不触发），护栏既不空转也不误杀；无未决的上游决策、无必须靠猜的定界。

## 10. Closure Gates

- [ ] in-scope behavior is complete（三条候选各有结论 + **D2/D3 落盘**
      + D1 落盘**或**按 §6 对称护栏停机且理由逐格写清）
- [ ] relevant docs are aligned（落点节 + `docs/analysis/` 探测记录）
- [ ] verification has run：Phase 1 的命令原文与退出码逐条写进 `## Closure`
- [ ] scoped verification is not conflated with full verification —— 本 plan 的代码改动
      **只有 `agenerp/site.py:5` 那句注释**（Phase 2 的 `Fix` 项）。
      `ruff check agenerp` 退 0 要写进 `## Closure`；
      其余逐字写明「本 plan 未交付任何行为代码，因此无行为判据可跑」，
      **不许拿别的 plan 的绿冒充本 plan 的验证**
- [ ] no in-scope item downgraded to deferred/follow-up（scope 缩小已按 Minimum Rule 10 记在 §9）
- [ ] independent draft review completed and recorded（§9）
- [ ] text consistency verified
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] **红线自证**：`git diff --stat` 对 `tests/gates/` `.github/workflows/` `missions/`
      **`docs/masterplan/`（整个目录，不是只有 `DECISIONS.md`）** `docker-compose.yml`
      **五个** pathspec 无输出 —— ⚠️ 只钉 `DECISIONS.md` 的话，
      §1.6 点名的那个诱惑（去 `02-WBS.md` 拆行）会让门禁**照样绿**；
      `docs/masterplan/STATE.md` 是唯一的挖孔，单独由下一行判「只增不改」
- [ ] **§6 的 H1 / H2 / H2b / H3 / H4 / H5 / H6a / H6b / H6c / H7 逐条有「实际」**，预测列一个字未改（H3 / H4 是复核项，不计入吻合统计）
- [ ] **对活站点零写**：Phase 1 Exit 的读回证据在 `## Closure` 里
- [ ] **`tests/ui/test_sidebar.py` 未被创建、也未被声称满足**（Non-Goals 1）
- [ ] **§1.1 发现的那处 drift 已落地**（`agenerp/site.py:5` 改准，Minimum Rule 14）
- [ ] **§6 对称护栏是一次属性判定（第一问构建期三条 + 第二问运行期三标记，**两问都答**）
      而不是一张名单**，且名单降级为例子；D1 若触发护栏，停机理由逐格引到具体哪一格
- [ ] **`docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块未被改动**

## 11. Deferred But Adjudicated

### P1.8 下半：按 D1 落地承载面 + 解释请求面 + ⌘K + `tests/ui/test_sidebar.py`

- Classification: `out-of-scope improvement`（**显式定界，不是遗漏**；由本 plan 的 D3 逐字交接输入契约）
- Why Not Blocking Closure: 它的基线由本 plan 的 D1 产生，起草期不存在（§3 Non-Goals 1）。
- Successor Required: `yes`。重开事件：**本 plan 转 `completed` 的那一刻**，
  由 mission-driver 按 roadmap 工作项 10 派下一个 plan。
  ⚠️ 若 D1 结论是「需人批」，该 successor 会卡在激活上 —— 这个账已按 §1.6 记进
  `STATE.md` §3 交人，**不在这里悄悄消化掉**。

### 承载面的激活（若 D1 选中项需人批）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 越权动作只有人能做（§2 目标 4）。
- Successor Required: `yes`。重开事件：**人在 `STATE.md` §3 把那条 `open` 改成 `resolved`**。

### 身份降权的实现（D2 若选 (ii)）

- Classification: `watch-only residual`
- Why Not Blocking Closure: D2 已要求把「今天不守」的判据形状写进 D3，交给下半钉成断言。
- Successor Required: `yes`。重开事件（**主**）：**浏览器第一次发起解释的那一刻** ——
  这是本 plan 从 `2026-08-24-2311-1-…` §11 第三条**继承**过来的触发条件，逐字保留。
  ⚠️ 上一轮评审抓到：本 plan 原本把它改写成「第一次对本机以外的地址开放」，
  **那比继承来的触发条件更晚**，而 D2 的 (ii) 自己写着「等于把信息越权暴露给**任何能打开侧边栏的人**」
  —— 伤害在**回环上**就已经发生了。**继承来的触发条件不许被下游改松。**
  另有两个**更晚的附加**重开事件：承载面第一次对本机以外的地址开放；P3 引入写工具。

## Closure

Status Note: <待填>

Closure Audit Evidence:

- Auditor / Agent: <待填>
- Evidence: <待填>

Follow-up:

- <待填>
