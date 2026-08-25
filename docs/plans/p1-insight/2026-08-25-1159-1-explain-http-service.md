# P1.8a 第 1 个 plan · 解释服务的 HTTP 面（进程 + 端点 + `sid` 认人）

> Plan Status: completed
> Mission: p1-insight
> Work Item: 10. **解释服务的 HTTP 面**（P1.8a，见 D-19）—— **本 plan 是它的第 1 个 plan**（表规 3 的 1–2 个）
> Last Reviewed: 2026-08-25
> Source: `docs/masterplan/DECISIONS.md` **D-19**（Agent 是独立服务，长在 Frappe/ERPNext 之上）·
> `docs/masterplan/02-WBS.md` §4 **P1.8a** 行 · `docs/backlog/p1-insight-roadmap.md` 工作项 10
> Related: [`2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`](./2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md)
> （`deferred`；**本 plan 承接它 §11 第一条的重开事件「`sid` 接缝被重新裁定」—— 裁定者是人，落成 D-19**。
> 它 Phase 2 落地的 `agenerp/site.py` `sid` 互斥模式与 `client_from_sid()` 是本 plan 的**输入**，不重做）·
> [`2026-08-24-2311-1-immediate-context-into-explain-loop.md`](./2026-08-24-2311-1-immediate-context-into-explain-loop.md)（① 即时上下文）
> Audit: required

## 0. 执行前必做：重取基线

**起草期读到的一切都可能在开工时已经变了。** 下面八处逐条重读，实读值填进 §0.1，
与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`（后者必须无输出才开工）
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时的最大节号**（起草期实读 **§7.19**，
   本 plan 预定落 **§7.20**；被别的 plan 占用就顺延，以开工时实读为准）
3. `agenerp/explain/loop.py` 的 `explain()` 形参表（起草期实读 `loop.py:622-666`，
   含 `question / task_class / client / models / requested / config / transport / doctypes /
   session_id / user / max_turns / executors / immediate`）
4. `agenerp/site.py` 的 `client_from_sid()` 与 `SiteClient.__init__` 的 `sid` 互斥分支
   （**草案评审实读修正**：`client_from_sid()` 在 `:493-503`，其 docstring 的判据引用在 `:499`；
   起草期原文写的 `:479-489` 与实读差 14 行，**以本行的实读值为准**。`SiteClient.__init__`
   的互斥分支 `:197-224` 实读吻合）
5. `agenerp/routing/config.py` 的 `from_env()` 缺变量时抛的**异常类型**（起草期实读 `RoutingError`）
   与 `agenerp/routing/capabilities.py` 的 `KNOWN_MODEL_PROFILES`
6. `pyproject.toml` 的 `[project].dependencies`（起草期实读**只有 `certifi>=2024.2.2`**）
7. `python3 -m pytest tests/unit -q` 的基线条数（起草期未跑，**开工时实跑并记原文**）
8. `agenerp/site.py` 的 `HTTP_PORT_ENV`（起草期实读 `AGENERP_HTTP_PORT`，`DEFAULT_HTTP_PORT = "8080"`，
   **它是 Frappe 站点的端口，不是本服务的**）与 `credential_from_env()`（`:453`）——
   两者分别是 `D-a-5` 与 Phase 2 判据⑧ 的输入

### 0.1 执行期重取基线的**实读结果**

（执行期填，一条不许留空；与起草期不同的用 ⚠️ 标出）

开工时间 `2026-08-25`，八处逐条实读如下：

| # | 起草期 | **执行期实读** | 吻合 |
|---|---|---|---|
| 1 | — | `git log -1 --format=%H` → **`b557ffd6238ab19b87ef9c9f058abe89d96c214c`**；`git status --porcelain` → **一行 `?? docs/plans/p1-insight/2026-08-25-1159-1-explain-http-service.md`** | ⚠️ **不是"无输出"**，唯一那行**就是本 plan 文件自身**（未 add）。产品代码/判据/文档面**零脏**，照实记、不粉饰 |
| 2 | `7.x` 最大节号 §7.19，预定落 §7.20 | `grep -n '^### 7\.' docs/architecture/module-boundaries.md \| tail -1` → **`2871:### 7.19 …`** ⇒ 最大仍是 **§7.19**，本 plan 落 **§7.20** | ✅ |
| 3 | `explain()` 形参 13 项 | `loop.py:622-666` 实读，形参逐字为 `question / task_class / client / models / requested / config / transport / doctypes / session_id / user / max_turns / executors / immediate` | ✅ 逐字相同 |
| 4 | `client_from_sid()` 在 `:493-503`、docstring 判据引用在 `:499`；`SiteClient.__init__` 互斥分支 `:197-224` | `grep -n "def client_from_sid" agenerp/site.py` → **`493`**；`grep -n "test_explain_service" agenerp/site.py` → **`499`**；互斥分支实读 `:197-224` | ✅ 与"草案评审实读修正"逐字吻合 |
| 5 | `from_env()` 缺变量抛 `RoutingError`；`KNOWN_MODEL_PROFILES` | `agenerp/routing/config.py:68 from_env()` 实读 `raise RoutingError(f"模型端点配置不全，缺：{missing}。…")` —— **指名缺的变量名**；`KNOWN_MODEL_PROFILES` 实读**五个档案**（`qwen3.8-max` / `qwen3.7-plus-2026-05-26` / `qwen3.6-plus` / `qwen-plus` / `qwen3:14b`） | ✅ 异常类型吻合。⚠️ 补一条起草期未写的：**未知任务类目抛的是 `DeclarationError`**（`capabilities.py:123`），它是 `RoutingError` 的**子类**（`errors.py` 逐字）—— 这一条直接影响 `D-a-4` 的 400/502 分格 |
| 6 | `dependencies` 只有 `certifi>=2024.2.2` | `pyproject.toml:14-16` 实读 `dependencies = [ "certifi>=2024.2.2", ]` | ✅ 逐字相同 |
| 7 | 起草期未跑 | `python3 tools/gates/check_expected_red.py` → `门禁 26 项：预期红 0，绿 26，跳过 0` / `✅ 与预期红名单完全一致`，exit **0**；`python3 -m pytest tests/unit -q` → **`697 passed in 2.09s`**，exit **0** | — 基线条数 **697** |
| 8 | `HTTP_PORT_ENV = "AGENERP_HTTP_PORT"` / `DEFAULT_HTTP_PORT = "8080"`；`credential_from_env()` 在 `:453` | `agenerp/site.py:68` → `HTTP_PORT_ENV = "AGENERP_HTTP_PORT"`；`:74` → `DEFAULT_HTTP_PORT = "8080"`；`:453` → `def credential_from_env(variable: str) -> str:` | ✅ 三处逐字吻合 |

**另一条执行期实读（`E-a-1` 的前置）**：`docker compose ps` → **九个容器全部 `Up 27 hours`**，
`frontend` 发布在 `127.0.0.1:18080->8080/tcp` ⇒ **活栈在跑，`E-a-1` 可跑**，
不触发 §7 Phase 1 写死的"不可复现"停机分支。

## 1. Current Baseline

### 1.1 三条卡点已由人拆掉，本 plan 的授权来自这三条 `resolved`

- `STATE.md` §3 `[resolved] 2026-08-25T02:25Z`（两条同文）：原 `[open] 02:10Z` 第一条
  （承载面激活属 L3）与 `[open] 04:05Z`（`sid` 是 `HttpOnly`，接缝需重新裁定）
  **由 D-19 一并解决** —— 承载形态定为**独立进程 + nginx 同源反代，不是 Frappe custom app**。
- `STATE.md` §3 `[resolved] 2026-08-25T02:28Z`：原 `[open] 02:10Z` 第二条（plan 预算 2/2 已满）
  **由人拆行解决** —— `02-WBS.md` §4 P1.8 拆成 **P1.8a / P1.8b** 两行（commit `ec74161`），
  各自有预算。⇒ **工作项 10（P1.8a）今日预算 `0/2`，本 plan 用掉第 1 个。**

### 1.2 `agenerp/explain/` 今天没有任何东西在监听端口

`ls agenerp/explain/` 实读为 `__init__.py` / `gate.py` / `ledger.py` / `loop.py` ——
**四个纯 Python 模块，零 socket、零 `http.server`、零 WSGI**。
`ls agenerp/serve/` → **不存在**（`2026-08-25-0119-1` 的独立关闭审计已实读复核过同一事实）。
D-19 逐字：「侧边栏要能发起解释 → **必须给 `agenerp/explain/` 加一个 HTTP 入口**」。

### 1.3 `sid` 这一层已经建好了，本 plan 不重做

`agenerp/site.py` 已有：`SiteClient(..., sid=...)` 的**互斥**构造分支（同时给 `sid` 与
另两类凭据 → 当场 `SiteError`；空/全空白 `sid` → 当场 `SiteError`，不静默回退）与
`client_from_sid(site, sid, *, transport=None)`（函数体内**一个凭据零件都没有**，
`tests/unit/test_site_client_sid.py` 判据⑧ 用 AST 扫它）。**20 条判据全绿。**

⚠️ **但它测的是 `SiteClient` 这一层，不是服务面**，且**全部 20 条走假传输**——
`client_from_sid()` **从未在活站点上被验证过认得出人**。这条限定是上一份 plan 的
`## Closure` 逐字写下的，本 plan 不改写它、也不假装它已经不成立。

### 1.4 有**两处**指向本 plan 的悬空引用（同一个不存在的文件）

上一份 plan 的关闭审计实读发现并登记为**非阻塞 follow-up**：`client_from_sid()` 的 docstring 指向
`tests/unit/test_explain_service.py` 判据⑩，而该文件不存在。
**草案评审补实读：同一个不存在的文件被引用了两处，不是一处** ——
① `agenerp/site.py:499`（起草期原文写 `:485`，实读差 14 行，以 `:499` 为准）·
② `tests/unit/test_site_client_sid.py:301`（「与 `tests/unit/test_explain_service.py` 的判据⑩
是同一条道理的两侧」）。⚠️ **两处都点名「判据⑩」，而本 plan 的凭据 AST 扫是判据⑧**
（判据⑩ 是「服务面零写方法」）⇒ **只建文件不改编号，两处引用仍然是错的**，
必须文件名与判据编号一起对齐。其触发条件逐字是
「**`sid` 接缝被重新裁定、Phase 3 重开并真的建出 `agenerp/serve/**` 时，由那个 plan 顺手把这行对齐**」。
**本 plan 就是那个 plan** ⇒ 这条按 `Fix` 处理，不是 `Follow-up`（Minimum Rule 14）。

### 1.5 本仓零第三方运行期依赖

`pyproject.toml` 的 `dependencies` 实读**只有 `certifi>=2024.2.2`**，且它进来的理由
写在文件里（D-11 的 CA 根证书坑）。⇒ HTTP 服务只能用标准库
（`http.server` / `socketserver`），**引任何 web 框架都是新增运行期依赖**，
并且会直接把 D-19「代价照实记」那条（零依赖启动门禁的判据面变宽）撑得更大。

### 1.6 「AI 未配置」在本仓是**未配置**，不是错误

`docker-compose.yml` 文件头规则 ② 逐字：「外部能力（LLM 等）缺失是『未配置』状态，
不是错误状态」。`agenerp/routing/config.py:66 from_env()` 实读：三个变量缺任一
→ 抛 `RoutingError` 并**指名缺的是哪个**。而 `route()` 实读是**惰性**取配置
（`resolved = config if config is not None else config_from_env()`，`router.py:76`）
⇒ **进程可以在一个 AI 变量都不配时正常启动**，失败只发生在真去调模型的那一刻。
这正是 P1.8a 验收里那条「零依赖启动门禁须仍绿」能成立的机制。

### 1.7 ① 层不查权限，而本 plan 让调用方变成外部输入

`explain()` 的 docstring 逐字：「⚠️ **① 层不查权限**……字段表是不是当前身份有权看的，
**由调用方负责** —— 这一层不判、也判不了。」
`STATE.md` §3 `[open] 2026-08-25T00:35Z` 第 ① 项登记的就是这件事，
其承接者（上一份 plan 的 `Decision D-下-2`）**随 Phase 3 一起 Deferred，一点没关**。
⇒ **本 plan 一旦让浏览器发起解释，这条就从「将来的风险」变成「今天的入口」**，
必须在本 plan 内裁定（§7 Phase 1 `D-a-3`），不许再往后推。

### 1.8 红线与判据设施的既有形状

- `tools/gates/expected-red.txt` 实读**名单为空**（0 条预期红）。
- `.github/workflows/gates.yml` 的 `gates-l2-live` job 契约逐字是「全部绿、零 red、零 skip」
  ⇒ **一条新建的 `tests/gates/*live*.py` 一旦进仓就必须在 CI 的活栈上是绿的**。
- ⇒ 本 plan **不创建 `tests/gates/**` 下任何文件**（红线 1），按 P1.0a/P1.4/P1.5/P1.6/P1.7
  的既有先例交付**断言体** + 交接说明，由人按路径加载。
- `pyproject.toml` 的 `[tool.ruff]` 把 `tests/gates` `exclude` + `force-exclude` 排除在外。

## 2. Goals

1. **`agenerp/serve/` 存在，并且真的在监听一个端口**：`python3 -m agenerp.serve` 起一个
   标准库 HTTP 服务；判据用**真 socket、真 HTTP 请求**证明，不是「函数签名存在」。
2. **身份只从请求里的 `sid` cookie 来**：服务端拿它调 `frappe.auth.get_logged_user` 解析成用户名；
   解析不出 → **401**，且**绝不回退到环境凭据**（判据要能挡住回退，不只是「正常路径能跑通」）。
3. **「AI 未配置」与「服务坏了」在响应上可区分**：健康端点恒 200；解释端点在缺 LLM 配置时
   回 **503** 并指名缺哪个变量，**不回 200 空回答**。
4. **一次解释的四项 token 账随响应返回**（P1.7 口径：`prompt` / `completion` / `reasoning` / `cached`），
   记账不拦截（D-18）。
5. **① 即时上下文的权限缺口在本 plan 内被裁定并落成代码**，不留给下一个 plan。
6. §1.4 那**两处**悬空引用（`agenerp/site.py:499` · `tests/unit/test_site_client_sid.py:301`）
   与实际交付的判据**文件名和判据编号**同时对齐 —— 只建出文件不算数。

## 3. Non-Goals

1. **不碰 `docker-compose.yml`、不碰 nginx、不向宿主发布任何端口** —— 那是同一工作项第 2 个 plan。
2. **不创建 `tests/gates/**` 下任何文件**（红线 1）；交付断言体 + 交接。
3. **不做 Desk 侧边栏、不做 ⌘K、不写任何前端资源** —— 那是 P1.8b（工作项 11）。
4. **不新增任何第三方依赖**（`pyproject.toml` 的 `dependencies` 一个字不加）。
5. **不做任何写操作** —— ②端只读，服务只暴露读路径；`SiteClient` 的写方法不进服务面。
6. **不做 TLS、不做限流、不做多用户会话池、不做异步/流式回包。**
7. **不改 `agenerp/explain/**` 的任何既有行为**（服务是它的调用方，不是它的改造者）。
8. **不声称满足 `02-WBS.md` §4 P1.8a 的验收命令** —— 那条要活栈与 nginx 同源，属第 2 个 plan。

## 4. Task Route

- Type: `app-layer design change`
- Owner Docs: `docs/architecture/module-boundaries.md`（落点 §7.20，**本 plan 唯一写入的 owner doc**）·
  `docs/masterplan/DECISIONS.md` **D-19（只读，红线 3）** ·
  `docs/design/agents-and-roles.md` §9 风险档（**只读；`No owner-doc update required`** ——
  风险档自评写进 §7.20 而不是改该表，见 Phase 1 `D-a-6`）
- ⚠️ `docs/context/codebase-map.md` 实读**整份仍是模板占位符**（`<path>` / `<YYYY-MM-DD>`），
  它自己的 Update Rule 逐字写着占位符残留时「do not treat the map as authority. Verify with the live repo」
  ⇒ 本 plan 的路由**只以 §0 的实读为准**；该文件**不在本 plan 的写入面内**
  （把它填全是一次跨全仓的独立工作，不是本 plan 的结果面，见 `Deferred But Adjudicated`）
- Skill Selection Basis: 本仓无对应技能条目（`docs/skills/README.md` 无 HTTP 服务面条目），
  各 Phase 一律 `Skill: none`；方法论纪律由本文件 §6 的预注册假设与 §7 的变异自查承担。

## 5. Infrastructure And Config Prereqs

- **无新增基础设施**：服务只在 `127.0.0.1` 上绑一个端口，端口号从环境读、**默认值必须存在**
  （零依赖：不配也能起）。
- **不需要 LLM 凭据即可启动**；判据里凡走到真模型的一律用假传输。
- 活站点探针（§7 Phase 1 的 `E-a-1`）需要栈在跑；**栈不在跑不阻塞本 plan** ——
  按 §7 写死的停机分支记「不可复现」，把该条移交第 2 个 plan，不猜。
- 回滚：本 plan 全部产物是**新增文件** + 两处既有引用的字面修正（§1.4），`git revert` 即可。

### 5.1 见即停清单（起草期写死，执行期不许现编）

遇到下列任一，**当场停下、写进 `STATE.md` §3 needs-human、不试探**：

1. 任何要改 `tests/gates/**` 的冲动（红线 1）
2. 任何要改 `.github/workflows/**` 的冲动（红线 2）
3. 任何 `bench install-app` / `bench new-app` / `bench set-config` / `bench build`
4. 任何往 `docker-compose.yml` 加服务、加挂载、改端口的动作（Non-Goal 1）
5. 任何 `pip install` 新包 / 往 `pyproject.toml` 加依赖（Non-Goal 4）
6. 任何让服务暴露写路径的设计（Non-Goal 5）
7. 任何把真 `sid` 值写进文件、日志、证据、提交信息的动作

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下面每一条在开工前已写死，执行期只填「实测」列，不许回头改预测。**

| # | 预测 | 怎么验 | **执行期实测**（预测原文一个字未改） |
|---|---|---|---|
| H1 | 标准库 `http.server.ThreadingHTTPServer` 绑 `127.0.0.1:0`（端口 0 由内核分配）后，判据能在**同一进程内另起线程**发出真 HTTP 请求并拿到回包 | Phase 2 判据①，真 socket | ✅ **吻合**。`tests/unit/test_explain_service.py` 的 `LiveService` 真起线程 `serve_forever()`，`http.client` 打内核分配的端口：`/health` 200、`/explain` 200 + 答案 + 四项账、404/405 逐格。另判了「内核真的分配了端口」（`service.port != 0`）|
| H2 | `route()` 在 AI 三变量全空时抛的是 **`RoutingError`**（不是 `KeyError` / `TypeError`），消息里**含缺失变量名** | Phase 2 判据⑤，`monkeypatch` 清空环境 | ✅ **吻合**，但**落点比预测更靠前**：服务面**先显式取一次配置**（`config_from_env()`），抛点在进 `route()` **之前** —— 503/502 的分法因此是结构性的，不靠读异常文本猜。三个变量名逐个出现在消息里（判据 `test_c5_unconfigured_llm_is_503_and_names_the_missing_variables`）|
| H3 | `SiteClient.call_method("frappe.auth.get_logged_user")` 在 **sid 有效**时回包形状是 `{"message": "<user>"}`；**sid 无效**时**不是** 200 空包，而是非 2xx ⇒ `SiteError` | Phase 1 `E-a-1` 活站点只读探针；栈不在跑则记「不可复现」并移交第 2 个 plan | ✅ **吻合，且不必走「不可复现」分支**（栈实读 `Up 27 hours`）。有效 `sid` → 200 `{"message":"Administrator"}`，`GET`/`POST` 两种动词同形；伪造 `sid` 与不带 `Cookie` → **均 403**。八行实测见 `docs/analysis/2026-08-25-1159-explain-service-sid-probe.md` |
| H4 | 把服务端的 `client_from_sid` 换成 `client_from_env`（M1），**至少两条**判据变红：AST 面一条 + 行为面一条 | Phase 3 变异自查 | ✅ **吻合且远超**：M1 打红 **16 条**。AST 面两条（`test_c8_the_service_surface_holds_zero_credential_parts` · `test_c8_the_only_way_the_service_builds_a_client_is_the_injected_factory`），行为面十四条（③④⑤⑦⑩ 各族）|
| H5 | 进程在 `AGENERP_LLM_*` 三个变量全空时**能起来**且健康端点回 200 | Phase 2 判据⑥ | ✅ **吻合**。`test_c6_the_service_starts_and_health_is_200_with_no_llm_configured` 在三变量 `monkeypatch.delenv` 后真起进程、真 socket 拿到 200；另加一条 AST 面（`do_GET` 里读不到任何 `AGENERP_LLM_*`、无 `config_from_env`、无 `environ`）|
| H6 | 本 plan 结束时 `pyproject.toml` 的 `dependencies` 与 §0.1 实读**逐字相同** | Phase 3 收口 `git diff -- pyproject.toml` | ✅ **吻合**。`git diff -- pyproject.toml` → **无输出**（该文件一个字未动，全程零第三方依赖）|
| H7 | 新增 `agenerp/**/*.py` 文件数 **= 3**（`agenerp/serve/__init__.py` / `app.py` / `__main__.py`），不多不少 | Phase 3 收口 `git status --porcelain -- agenerp/` | ✅ **吻合，恰好 3**。`git ls-files --others --exclude-standard -- 'agenerp/**/*.py'` → `agenerp/serve/__init__.py` · `agenerp/serve/__main__.py` · `agenerp/serve/app.py`。⚠️ **照实补一条**：`git status --porcelain -- agenerp/` 另有一行 ` M agenerp/site.py` —— 那是 §1.4 那处**悬空引用的字面修正**（docstring 里 判据⑩ → 判据⑧），**不是新增文件**，不改变 H7 的判定 |

⚠️ **H3 是本 plan 唯一依赖外部活体的预测。** 它不吻合或跑不起来**都不阻塞收口** ——
处置在 §7 Phase 1 写死：照实记、把 401 的映射依据降级为「按 `SiteError` 一律 401」并在 §7.20 标注未实证。

## 7. Execution Plan

### Phase 1 — 请求面的形状与身份链（先裁定，后写代码）

Status: completed
Targets: `docs/architecture/module-boundaries.md`（§7.20 新增）
Skill: `none`

- Item Types: `Decision | Explore`
- Prereqs: §0 基线重取完成

- [x] `E-a-1`（Explore）活站点**只读**探针：用一个**故意伪造的** `sid` 打
      `/api/method/frappe.auth.get_logged_user`，记状态码与回包形状；再用一次真登录拿到的
      cookie jar 打同一端点，记形状。**两次都不写任何数据，真 `sid` 一个字节不落盘**
      （落 `docs/analysis/` 时逐位脱敏，并对其前 8 位 grep 全仓确认无命中）。
      栈不在跑 → 记「不可复现」，**不猜**，结论移交第 2 个 plan。
  - Skill: `none`
- [x] `D-a-1`（Decision）**传输栈选标准库 `http.server`**。备选：① 引 `flask`/`fastapi`
      —— 否，Non-Goal 4 且撑大零依赖判据面；② 自己写 socket 循环 —— 否，重造且更易错。
      残余风险照实记：`ThreadingHTTPServer` 每连接一线程，**不是生产级并发形态**，
      本期不假装它是。
  - Skill: `none`
- [x] `D-a-2`（Decision）**端点集合最小化**，两条：
      `GET  <前缀>/health` —— **不认人、不碰 LLM、不碰站点**，恒 200；
      `POST <前缀>/explain` —— 认人、可能碰 LLM。
      **不加第三条**。备选「加一条 `/whoami` 方便调试」→ 否：它是第二个认人面，
      判据要跟着翻倍，而调试价值可由 `/explain` 的 401 分支覆盖。
      前缀字面值在本 Phase 定稿并写进 §7.20（第 2 个 plan 的 nginx `location` 必须与它逐字一致）。
  - Skill: `none`
- [x] `D-a-3`（Decision）**① 即时上下文的权限缺口怎么关**（承接 `STATE.md` §3
      `[open] 2026-08-25T00:35Z` 第 ① 项）。三个备选逐条写进 §7.20：
      **(i)** 请求体直接给字段表 → **否决**，那正是「① 层不查权限」的最坏形态，
      外部输入可把任意字段表送进模型；
      **(ii)** 干脆不接受 ① → 可行但把 P1.8b 的「保留当前单据上下文」堵死；
      **(iii)** 请求体只给 `doctype` + `name`，**字段表由服务端用调用者自己的 `sid` 现取** ⇒
      **权限由 Frappe 判**，与 D-19「权限仍由 Frappe 判」同向。
      **本 plan 选 (iii)** 并落成代码；⚠️ 选定不等于那条 `[open]` 自动消失 ——
      收口时按实际关闭程度在 STATE 追加**事实行**，`[open]` 的处置权仍在人。
  - Skill: `none`
- [x] `D-a-3b`（Decision）**`assemble()` 其余三个入参的出处，逐个点名**（草案评审补：
      `agenerp/context/immediate.py` 的 `assemble()` 实读签名是
      `doctype / name / fields / role / view / actions`，(iii) 只处置了 `fields` 这一个，
      **`role` / `view` / `actions` 三个仍是外部输入，会原样进模型**）。
      逐个写进 §7.20，每个只能落在三格之一：
      **(A)** 服务端用同一个 `sid` 客户端现取（与 (iii) 同向，权限由 Frappe 判）·
      **(B)** 请求体给，但**显式判定为「非特权展示串」**并写明为什么它进模型不构成越权 ·
      **(C)** 服务端写死常量、请求体给了也忽略。
      ⚠️ **`role` 一格不许落 (B) 而不给理由** —— 它的字面就是身份词，
      调用方自称 role 与 `sid` 解析出的人不是同一件事。
      三格各自的选择必须有对应判据（Phase 2 判据⑦）。
  - Skill: `none`
- [x] `D-a-4`（Decision）**失败到状态码的映射表**（写进 §7.20，一格不留白）：
      无 `sid` / 空 `sid` → 401 · `sid` 认不出人（`SiteError`）→ 401 ·
      LLM 未配置（`RoutingError` 且消息指名缺变量）→ 503 · 其它 `RoutingError` → 502 ·
      请求体不成形 → 400 · 未知路径/方法 → 404 / 405。
      **每一格都要有对应判据**，没有判据的格子不许出现在表里。
  - Skill: `none`
- [x] `D-a-5`（Decision）**服务端口的环境变量名，必须与既有的 `AGENERP_HTTP_PORT` 不同**
      （草案评审补：`agenerp/site.py:68` 实读 `HTTP_PORT_ENV = "AGENERP_HTTP_PORT"`、
      `DEFAULT_HTTP_PORT = "8080"`，**那是 Frappe 站点的端口**，证据命令里以
      `AGENERP_HTTP_PORT=18080` 的形式在用）。复用它 = 一个变量同时决定「打谁」和「监听谁」，
      配错时的失败形态是静默的。备选：① 复用 —— 否，理由同上；② 新变量 —— **选它**，
      名字与默认端口在本 Phase 定稿并写进 §7.20（第 2 个 plan 的 nginx `proxy_pass` 要用同一个数）。
      残余风险：默认端口可能与本机别的进程撞，照实记，不发明探测/重试逻辑。
  - Skill: `none`
- [x] `D-a-6`（Decision）**本 plan 的风险档自评**（`docs/design/agents-and-roles.md` §9，**只读**）：
      逐条对照 L0–L3 的定义写进 §7.20 —— 本 plan 不建 DocType、不改权限、不改 Workflow、
      对活站点零写（Non-Goal 5），**故不落 L3**；结论与依据逐字落 §7.20，
      **不改 §9 那张表的任何一行**（`No owner-doc update required`）。
      ⚠️ 自评落在 L3 之外**不等于**「①/② 的判断已经安全」—— 那由 `D-a-3` / `D-a-3b` 各自承担。
  - Skill: `none`

Exit Criteria:

- [x] `E-a-1` 有结果或有「不可复现」的照实记录，二者必居其一
- [x] `D-a-1` · `D-a-2` · `D-a-3` · `D-a-3b` · `D-a-4` · `D-a-5` · `D-a-6` **七条**各有备选与
      残余风险，写进 `module-boundaries.md` **§7.20**；`D-a-3b` 的三格与 `D-a-4` 的每一格
      都能在 Phase 2 指到一条判据
- [x] `docs/logs/2026/08-25.md` 追加一条（日期以执行日实读为准）

### Phase 2 — `agenerp/serve/` 落地 + 离线判据

Status: completed
Targets: `agenerp/serve/__init__.py` · `agenerp/serve/app.py` · `agenerp/serve/__main__.py` ·
`tests/unit/test_explain_service.py` · `tests/unit/serve_fakes.py`
Skill: `none`

- Item Types: `Add | Fix | Proof`（实际分布 5 `Add` / 1 `Fix` / 4 `Proof` ——
  **不满足 Minimum Rule 7 的「80% 同型才可在 Phase 级声明统一类型」，故逐项标注**）
- Prereqs: Phase 1 的**七条** Decision（`D-a-1` · `D-a-2` · `D-a-3` · `D-a-3b` · `D-a-4` ·
  `D-a-5` · `D-a-6`）全部定稿

- [x] `Add` `agenerp/serve/app.py`：请求处理器 + 一个可被判据直接构造的
      `build_server(...)` 工厂（**依赖注入**：站点客户端工厂、模型档案表、传输层
      三者都可从外部传入，否则判据只能靠打补丁，那会让「真实现」与「假实现」难以区分）
- [x] `Add` `agenerp/serve/__main__.py`：`python3 -m agenerp.serve` 起进程，
      绑 `127.0.0.1`，端口从 `D-a-5` 定稿的**新**环境变量读且**有默认值**（不配也能起）；
      **不得读 `AGENERP_HTTP_PORT`**（那是站点端口，`D-a-5`）
- [x] `Add` 身份链：请求 `Cookie` 头 → 取 `sid` → `client_from_sid(site, sid)` →
      `call_method("frappe.auth.get_logged_user")` → 用户名 → 传给 `explain(user=...)`
- [x] `Add` `D-a-3` 选中的 (iii)：请求体只收 `doctype` + `name`，字段表**服务端用同一个
      `sid` 客户端现取**后再组装 `ImmediateContext`；`role` / `view` / `actions` 三个入参
      按 `D-a-3b` 各自定稿的那一格落地（`agenerp/context/immediate.py` 的 `assemble()` 不改，
      Non-Goal 7 同理适用 —— 服务是它的调用方）
- [x] `Add` 响应体带四项 token 账（`prompt` / `completion` / `reasoning` / `cached`），
      **`cached` 不进 `total`**（`§7.17` 的既定口径，本 plan 不改它）
- [x] `Fix` §1.4 的**两处**悬空引用一起对齐到本 plan 真交付的判据文件**与判据编号**：
      ① `agenerp/site.py:499`（`client_from_sid()` docstring）·
      ② `tests/unit/test_site_client_sid.py:301`。
      ⚠️ 两处原文都写「判据⑩」，而本 plan 的凭据 AST 扫是**判据⑧** ⇒ **编号必须一并改**，
      只换文件名仍是错的。改完 `grep -rn "test_explain_service.py" agenerp/ tests/` 逐条复核，
      不得再有指向不存在编号的引用（这是**确认的引用漂移**，按 Minimum Rule 14 不得降级为 follow-up）
- [x] `Proof` 判据①（真 socket）：绑 `127.0.0.1:0`，另起线程发真 HTTP 请求，断言回包
- [x] `Proof` 判据②–④（身份）：无 `sid` → 401 · 坏 `sid`（`SiteError`）→ 401 ·
      **好 `sid` → 200 且传给 `explain()` 的 `user` 等于 `get_logged_user` 回的那个人**
      （断言落在**被调用的参数**上，不落在标志位上）
- [x] `Proof` 判据⑤–⑥（未配置）：清空三个 `AGENERP_LLM_*` → `/health` 200 且进程照常起；
      `POST /explain` → **503** 且消息含缺失变量名
- [x] `Proof` 判据⑦–⑩（越权与泄漏）：
      ⑦ **`assemble()` 六个入参的出处逐个可判**：请求体给字段表 → **被忽略/拒绝**，不进模型；
      `role` / `view` / `actions` 各按 `D-a-3b` 定稿的那一格断言（落 (A) 的断言「取自 `sid` 客户端」、
      落 (C) 的断言「请求体给了也不生效」、落 (B) 的断言「它不参与任何权限判断」）——
      **`D-a-3b` 三格与判据一一对应，没有判据的格子不许存在** ·
      ⑧ **AST 扫 `agenerp/serve/**` 全文**：不得出现 `client_from_env` / `credential_from_env` /
      `ADMIN_PASSWORD_ENV` / `ADMIN_USER_ENV` / `API_KEY_ENV` / `API_SECRET_ENV`，
      且**服务面构造 `SiteClient` 的路径只有注入进来的 `client_from_sid` 工厂一条**
      （草案评审补：只禁 `client_from_env` 挡不住
      `SiteClient(site, admin_password=credential_from_env(...))` 这条等价回退）·
      ⑨ 响应体与日志**不含 `sid` 字面量** ·
      ⑩ 服务面**零写方法**（AST 扫：不得引用 `create_doc` / `submit_doc` / `ensure_doc` /
      `delete_custom_field` / `post_method` 中的写用法）

Exit Criteria:

- [x] 十条判据全绿，且**每一条都指名一个可观测量**（不是「函数存在」）
- [x] `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` → exit 0，
      条数**只增不减**（基线取 §0.1）
- [x] `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → exit 0
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` → exit 0
- [x] `git diff -- pyproject.toml` **无输出**（H6）
- [x] `module-boundaries.md` §7.20 记落点；`docs/logs/` 更新

### Phase 3 — 变异自查 + 断言体 + 交接

Status: completed
Targets: `tests/unit/test_explain_service_body.py`（🔴 断言体）· `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Proof | Add | Follow-up`（4 项：2 `Proof` / 1 `Add`（断言体）/ 1 `Follow-up`）
- Prereqs: Phase 2 全绿

- [x] `Proof` **变异自查 M1–M11，逐条施加一次、记红点、复原**。
      **一个都不许跳过；某条打不红就当场补断言并登记为新编号（Mn+1），不许改预测。**
      （M1–M10 起草期写死，M11 由独立草案评审补，**一并按同一规矩执行**。）
      M1 `client_from_sid` → `client_from_env` · M2 缺 `sid` 时不 401 照常跑 ·
      M3 `SiteError` 被吞掉后继续 · M4 响应账只记 `completion` 不记 `reasoning` ·
      M5 `/health` 读 AI 变量 · M6 未配置时回 200 空回答 · M7 请求体字段表直接透传 ·
      M8 响应回显 `sid` · M9 未知路径回 200 · M10 `user` 从请求体取而不是从 `sid` 解析 ·
      **M11**（草案评审补，直接打判据⑧ 的加严面）把身份链换成
      `SiteClient(site, admin_password=credential_from_env(ADMIN_PASSWORD_ENV))` ——
      **绕开 `client_from_env` 的等价凭据回退**，预测：判据⑧ 打红
- [x] `Add` **`tests/gates/test_explain_service_live.py` 的断言体**落 `tests/unit/test_explain_service_body.py`
      （红线 1：本 plan **不创建** `tests/gates/**`），并写清「人要把它按哪个路径加载、
      加载后跑什么命令、为什么现在还不能加载」（**它要活栈 + nginx 同源，属第 2 个 plan**）
- [x] `Follow-up` 在 `STATE.md` §3 追加：① 本 plan 的证据行；
      ② `[needs-human]` —— 上述 🔴 门禁只能由人按路径加载（`Gates-Change-Approved-By:`）；
      ③ 事实行 —— `[open] 2026-08-25T00:35Z` 第 ① 项由 `D-a-3` **实质关到哪一步**，
      **处置权仍在人，loop 不代改那条的任何一个字**（红线 5）
- [x] `Proof` §6 的 H1–H7 逐条填实测，**不吻合的照实记、预测原文不改**

Exit Criteria:

- [x] M1–M11 逐条有红点记录（补出来的新编号一并记）
- [x] 断言体与交接说明在文件里；`tests/gates/` `git status --porcelain` **无输出**
- [x] H1–H7 七格逐条有实测值
- [x] `docs/logs/` 更新

## Draft Review Record

- Independent draft review iteration 1: `needs revision → 已在本文件内修正，accept`
  （独立草案评审子进程，fresh session，`2026-08-25`，基线 sha `b557ffd`）。
  逐条实读复核了 plan 引用的每一条事实，**结论：授权链成立**
  （`STATE.md` §3 两条 `[resolved] 02:25Z` + 一条 `[resolved] 02:28Z` 实读在文件里；
  `^- \[open\]` 全量扫描**已无** `02:10Z` / `04:05Z` 条目；`02-WBS.md:87` 实读为 P1.8a 独立行；
  `ls agenerp/serve` → 不存在；`tools/gates/expected-red.txt` 实读 0 条；
  `pyproject.toml` 依赖实读只有 `certifi>=2024.2.2`；`router.py` 惰性取配置实读在 `:77`，
  plan 原文写 `:76`，**差 1 行，属 §0 重取范围，不改起草期原文**）。
  **修正的六处（Blocker/Major）**：
  ① §1.4 / Goal 6 的悬空引用位置错了（`site.py:485` 实读在 `:499`），且**漏了第二处**
  `tests/unit/test_site_client_sid.py:301`，两处都点名「判据⑩」而本 plan 的凭据扫是判据⑧
  ⇒ 只建文件不改编号仍是错的 —— `Fix` 项已扩到两处 + 编号 + `grep` 复核；
  ② `assemble()` 实读签名是 `doctype / name / fields / role / view / actions` **六个**，
  原 `D-a-3` 的 (iii) 只处置了 `fields`，`role` / `view` / `actions` 仍是原样进模型的外部输入
  ⇒ 新增 `D-a-3b` 逐个点名出处，判据⑦ 一并扩；
  ③ 判据⑧ 的禁用名单挡不住等价回退
  `SiteClient(site, admin_password=credential_from_env(...))` ⇒ 名单补 `credential_from_env` /
  `ADMIN_USER_ENV`，并加「构造路径只有注入的 `client_from_sid` 一条」，
  变异自查补 **M11** 专打这条；
  ④ 服务端口若复用既有 `AGENERP_HTTP_PORT`（实读 `site.py:68`，站点端口）会静默配错
  ⇒ 新增 `D-a-5` 强制用新变量名；
  ⑤ `docs/design/agents-and-roles.md` §9 被列为 Owner Doc 却无任何一项落到它上
  ⇒ 新增 `D-a-6` 风险档自评 + 显式 `No owner-doc update required`；
  ⑥ `Deferred But Adjudicated` 写「承接者**已存在**」，实读 `ls docs/plans/p1-insight/`
  **没有那个文件** ⇒ 改为「尚未创建，已指名路径与预算格」。
  **另修两处格式项**：Phase 2 的 `Item Types` 声明「10 项里 9 项为 Add」与实际分布
  （5 `Add` / 1 `Fix` / 4 `Proof`）不符且不满足 Minimum Rule 7 的 80% 条件 ⇒ 改为逐项标注；
  §0 由七处补到八处（新增 `HTTP_PORT_ENV` / `credential_from_env` 两个实读输入）。
  **未修正、留给执行期与关闭审计的（Minor）**：`router.py:76` vs `:77` 的行号差
  （§0 已覆盖）；`docs/context/codebase-map.md` 整份占位符（已入 `Deferred But Adjudicated`）。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`module-boundaries.md` §7.20）
- [x] verification has run：`check_expected_red.py && pytest tests/unit -q` ·
      `pytest tests/contracts tests/tools tests/routing tests/context -q` · `ruff check ...` ·
      `git diff -- pyproject.toml`
- [x] scoped verification is not conflated with full verification —— 未跑整仓
      `pytest tests -q -m "not live"` 与 CI 服务端复跑时**逐字写「verification scope limited」**
- [x] no in-scope item downgraded to deferred/follow-up（尤其 §1.4 那**两处**悬空引用，文件名与判据编号都要对齐）
- [x] independent draft review completed and recorded
- [x] text consistency verified
- [x] closure audit was independent —— ⚠️ **原为留白，已由后续一轮补做**：执行期环境不具备
      独立子代理，那一格当时照实空着（执行者自己复跑不是独立审计）。**补做者是独立收口审计者**
      （fresh context、非本 plan 的执行者，基线 sha `06a2d1f`），逐条实读复跑见 `## Closure`
      的「补做记录」。处置同 P1.4 / P1.5 / P1.6 / P1.7 的先例。
- [x] closure evidence exists in files
- [x] 红线自证：`git status --porcelain -- tests/gates/ .github/workflows/ missions/
      docs/masterplan/DECISIONS.md docker-compose.yml` → 无输出

## Deferred But Adjudicated

### 服务的 compose 接线、nginx 同源反代、`02-WBS.md` P1.8a 的验收命令

- Classification: `out-of-scope improvement`（起草期即定界，非执行期现编）
- Why Not Blocking Closure: 它是**同一工作项第 2 个 plan 的全部内容**（Non-Goal 1 / 8）。
  本 plan 交的是「进程与请求面本身」，那是它的硬前置。
- Successor Required: `yes`。承接者**尚未创建**（草案评审实读：`ls docs/plans/p1-insight/`
  里没有这个文件），**已指名的是它的路径与预算格**：
  `docs/plans/p1-insight/2026-08-25-1159-2-explain-service-compose-and-same-origin.md`
  —— 工作项 10（P1.8a）表规 3 预算 `1–2 个 plan` 的**第 2 格**，本 plan 收口后由 mission-driver 起草。
  重开事件：**本 plan 收口**。

### `client_from_sid()` 在活站点上认得出人（H3 若不可复现）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 的十条判据全部离线可判；活体那一半的自然归属是
  第 2 个 plan（它本来就要起栈）。
- Successor Required: `yes`。重开事件：**第 2 个 plan 起栈的那一刻**。

### `docs/context/codebase-map.md` 整份仍是模板占位符

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 它是**全仓性**的（前端/后端/共享/测试/配置五个入口 + 五条常见路由都是
  `<path>`），不是本 plan 造成的漂移，也不是本 plan 的结果面；且该文件自己的 Update Rule 逐字
  规定占位符残留时不得当作权威、以实读为准 ⇒ 本 plan 的路由由 §0 的八处实读承担，**不受它影响**。
- Successor Required: `yes`。重开事件：**有人把它列进一次专门的上下文文档对齐工作**，
  或**某个 plan 因为信了它的占位符而走错路由**（两者任一）。

### 生产级并发形态（连接池 / 超时 / 限流 / TLS）

- Classification: `optimization candidate`
- Why Not Blocking Closure: 本期服务只绑 `127.0.0.1`、不出宿主（Non-Goal 1 / 6）。
- Successor Required: `yes`。重开事件：**出现「服务要对本机之外提供」的具体需求或缺陷**。

## Closure

Status Note: **三个 Phase 全部执行完毕，Plan Status 转 `completed`。** 交付的是
**进程与请求面本身**：`agenerp/serve/` 三个模块（H7 实测**恰好 3** 个新增
`agenerp/**/*.py`）+ `tests/unit/test_explain_service.py`（**59 条**，十条判据族）+
`tests/unit/serve_fakes.py`（认 `sid` 的假站点）+ `tests/unit/test_explain_service_body.py`
（🔴 门禁的**断言体**，含交接说明与**人要做的那一处收严**：skip → fail）。
`module-boundaries.md` **§7.20** 记落点（Phase 1 的七条 Decision + Phase 2 的交付形状 +
Phase 3 的 M1–M11 红点表 + 引用漂移改直）。

**Goal 6 逐字兑现**：§1.4 那**两处**悬空引用（`agenerp/site.py:499` ·
`tests/unit/test_site_client_sid.py:301`）**文件名与判据编号一起对齐**（⑩ → ⑧），
`grep -rn "test_explain_service.py" agenerp/ tests/` 逐条复核过，
不再有指向不存在文件或不存在编号的引用。**没有降级为 follow-up。**

⚠️ **本 plan 明确不声称满足 `02-WBS.md` §4 P1.8a 的验收命令**（Non-Goal 8）——
那要活栈 + nginx 同源，属**第 2 个 plan**。`docs/backlog/p1-insight-roadmap.md`
工作项 10 因此**刻意仍是 `todo`**，并在同一行写明为什么不是漏改。

⚠️ **verification scope limited**：未跑整仓 `pytest tests -q -m "not live"`；
未经 CI 服务端复跑。`GATE_VERIFY` 复跑得到的是 `check_expected_red.py` 与
`pytest tests/unit -q`（**756 条**，含本 plan 的 59 条 + 6 条 `live` 判据 —— 后者在
`-m "not live"` 下被 deselect，因此 CI 的 L1 那一轮看到的是 `756 passed, 0 skipped`）。

Closure Audit Evidence:

- Auditor / Agent: **执行期无** —— 当时环境不具备独立子代理，`closure audit was independent`
  照实留白。下面这组证据是**执行者自己复跑**的，**不得读作独立审计**；
  独立那一轮的复跑另记在本节末尾的「补做记录」。
- Evidence（命令原文 + 退出码 + commit sha）:
  - `python3 tools/gates/check_expected_red.py` → **exit 0**
    （`门禁 26 项：预期红 0，绿 26，跳过 0` / `✅ 与预期红名单完全一致`）
  - `python3 -m pytest tests/unit -q` → **exit 0**（`756 passed, 6 skipped`；
    基线 §0.1 实读 `697 passed` ⇒ **只增不减**）
  - `python3 -m pytest tests/unit -q -m "not live"` → **exit 0**（`756 passed, 6 deselected`）
  - `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → **exit 0**
    （`456 passed, 13 skipped`）
  - `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
    → **exit 0**（`All checks passed!`）
  - `git diff -- pyproject.toml` → **无输出**（H6）
  - `git ls-files --others --exclude-standard -- 'agenerp/**/*.py'` → **3 行**（H7）
  - 红线自证：`git status --porcelain -- tests/gates/ .github/workflows/ missions/
    docs/masterplan/DECISIONS.md docker-compose.yml` → **无输出**；
    `DECISIONS.md` 一个字未改、未新增 `R-x`；`docs/masterplan/STATE.md` **只追加**；
    证据仓 `XM_PATH` 未写入；未生成任何运行时 Server Script
  - commit sha: 实现提交 `18dc4655ffda00c7913deacfb0588b65d505ec09`（`feat(serve): …`）+
    收口提交 `06a2d1f`（`docs(state): …`，STATE §2 的证据行）；基线 `b557ffd`

### 补做记录 · 独立收口审计（2026-08-25，基线 sha `06a2d1f`）

- Auditor / Agent: **独立收口审计者** —— fresh context、**非本 plan 的执行者**，
  只读 plan 与活仓，不改任何产品代码与判据（本次唯一写入是本文件的这一段与那一格勾选）。
- 判定：**approved**。逐条实读复跑如下（命令原文 + 退出码，全部由审计者自己跑，不引执行者的数）:
  - `python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 26 项：预期红 0，绿 26，跳过 0` ·
    `✅ 与预期红名单完全一致`）
  - `python3 -m pytest tests/unit -q` → **exit 0**（`756 passed, 6 skipped`，与 `## Closure` 逐字相同）
  - `python3 -m pytest tests/unit/test_explain_service.py -q` → **exit 0**（`59 passed`，坐实「59 条」）
  - `python3 -m pytest tests/unit/test_explain_service_body.py -q` → **exit 0**（`6 skipped` ——
    断言体够不到活栈时 skip，与文件头交接说明逐字一致，**那 6 条就是 `tests/unit -q` 里的 6 skipped**）
  - `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` → **exit 0**
    （`456 passed, 13 skipped`）
  - `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
    → **exit 0**（`All checks passed!`）
  - `git diff b557ffd..HEAD -- pyproject.toml` → **无输出**（H6 复核成立，零新增第三方依赖）
- **反空壳复核**（不看 `[x]`，只看活码）：`agenerp/serve/app.py` 实读 —— `build_server()` 真造
  `ThreadingHTTPServer` 并可 `serve_forever()`；`handle_explain()` 的身份链
  `_sid_from_cookie` → `client_factory` → `call_method("frappe.auth.get_logged_user")` → `explain(user=…)`
  逐跳有实现；`_immediate_context()` 真用同一个 `sid` 客户端 `GET {RESOURCE_PATH}/…` 现取字段表；
  503/502 的分法在代码里是**结构性**的（先 `deps.config_factory()` 再进 `explain_fn`）。
  **零空函数体、零 `return None` 占位、零吞异常**（`except Exception` 那一处是**显式**回 500
  且不透传异常文本，不是吞掉）。`agenerp/serve/__main__.py` 真起进程并 `serve_forever()`，
  `resolve_port()` 只读 `AGENERP_SERVE_PORT`、**不读** `AGENERP_HTTP_PORT`（`D-a-5` 成立）。
- **Goal 6 复核**：`agenerp/site.py:499` 与 `tests/unit/test_site_client_sid.py:301` 两处实读均已改成
  `tests/unit/test_explain_service.py` **判据⑧**；`grep -rn "test_explain_service" agenerp/ tests/`
  复核，不再有指向不存在文件或不存在编号的引用。**未降级为 follow-up。**
- **红线复核**：`git diff --name-only b557ffd..HEAD` 实读 16 个文件，`tests/gates/**` ·
  `.github/workflows/**` · `missions/**` · `docs/masterplan/DECISIONS.md` · `docker-compose.yml`
  **一个都不在里面**；`git diff b557ffd..HEAD -- docs/masterplan/STATE.md` 的删除行数 **0**
  ⇒ STATE **确为只追加**（红线 5 成立）。`docs/analysis/…-sid-probe.md` 实读**无真 `sid` 落盘**
  （唯一的长十六进制串是**故意伪造**的 `deadbeef…`）。
- **五点一致复核**：`Plan Status: completed` · 三个 Phase `Status: completed` 且执行项与 Exit Criteria
  全 `[x]` · Closure Gates 全 `[x]`（含本次补勾的这一格）· `## Closure` 证据非占位 ·
  `docs/logs/2026/08-25.md` 与 `docs/masterplan/STATE.md` §2 的证据行与本节数字逐字一致 ⇒ **一致**。
- **Deferred 诚实性复核**：四条 `Deferred But Adjudicated` 与三条 `Follow-up` 里
  **没有藏任何在范围内的活缺陷或契约漂移** —— 🔴 门禁只能由人加载是**红线 1 的必然**不是偷懒；
  第 2 个 plan 未创建已在 Non-Goal 1/8 显式定界；`04-RUNBOOK.md` / `budget.json` 那两处是
  **人侧开工前就带着的未提交改动**（`git diff` 内容实读为 `auth-expired` 处置 + 日预算改值，
  与本 plan 的结果面无关），随收口提交进仓已照实记，**不构成隐瞒**。
- ⚠️ **审计者同样确认「verification scope limited」成立且已逐字写明**：整仓
  `pytest tests -q -m "not live"` 与 CI 服务端复跑**本次审计也未跑** ——
  这一格不因审计通过而变成 full green。

Follow-up:

- 🔴 `tests/gates/test_explain_service_live.py` **只能由人按路径加载**
  （`Gates-Change-Approved-By:`），且加载时要把本文件头写明的那一处 **skip → fail** 收严做掉。
  时机是**第 2 个 plan 落地的同一个提交**（在那之前它必然 skip，而 `gates-l2-live` 的契约是零 skip）。
- 第 2 个 plan（compose 接线 + nginx 同源 + P1.8a 验收命令）**尚未创建**，
  路径已指名：`docs/plans/p1-insight/2026-08-25-1159-2-explain-service-compose-and-same-origin.md`。
- ~~**独立收口审计待补**~~ —— **已补做**，见本节「补做记录」；`closure audit was independent` 已由审计者补勾。
- ⚠️ **`docs/masterplan/04-RUNBOOK.md` / `tools/gates/budget.json` / `STATE.md` 在开工时
  就带着人侧的未提交改动**（`auth-expired` 处置固化 + 日预算 10 亿 → 100 亿），
  **本 plan 一个字未动它们**，只是随收口提交一并进仓，照实记在这里。
