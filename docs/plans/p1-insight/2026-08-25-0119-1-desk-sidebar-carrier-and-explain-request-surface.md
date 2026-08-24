# P1.8 下半 · 承载面落地 + 解释请求面 + ⌘K（**激活由人批，本 plan 不激活**）

> Plan Status: deferred
>
> **Phase 1–2 已落地并全绿；Phase 3 / 4 / 5 由 Phase 1 的 H1 实测整体转 `Deferred But Adjudicated`。**
> ⚠️ **状态行本身只写 `deferred` 一个词** —— 起草期把定界写在同一行括号里，
> `tools/mission-driver/src/plan-check.mjs` 的 `PLAN_STATUS_RE` 因此把状态读成 `unknown`
> （该正则要求状态词后到行尾无其它字符）。2026-08-25 关闭审计把定界移到下一行，**状态语义一个字未变**。
>
> ⚠️ **不是 `completed`，也不是 `cancelled`。** `completed` 要求每个 phase 的 Exit Criteria 全 `[x]`，
> 而 Phase 3 / 4 / 5 一格都没做；把它写成 `completed` 就是伪造证据。
> 按 `docs/plans/00-plan-authoring-and-execution-guide.md` 的状态表，`deferred` 的定义逐字是
> 「the plan no longer owns live closure in its original form」—— 本 plan 的原始形态
> （承载面落地 + 解释请求面 + ⌘K）**确实不再由它拥有**，重开事件见 §11 第一条。
> Mission: p1-insight
> Work Item: 10. Agent 侧边栏嵌 Desk（P1.8）
> Last Reviewed: 2026-08-25
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 10 · `docs/masterplan/02-WBS.md` §4 P1.8 行 ·
> 上半 plan [`2026-08-24-2311-2-desk-embed-carrier-decision.md`](./2026-08-24-2311-2-desk-embed-carrier-decision.md)
> 的 **D1 / D2 / D3** 三条裁定（本 plan 的输入契约）
> Related: [`2026-08-24-2311-1-immediate-context-into-explain-loop.md`](./2026-08-24-2311-1-immediate-context-into-explain-loop.md)（① 即时上下文接进循环。
> **本 plan 继承它 §11 第二条**（① 档上下文预算，合取条件今天只满足一半）；
> **§11 第三条**（① 档权限校验）的重开事件**由本 plan 触发**，处置见 §7 Phase 3 的 `Decision D-下-2`）
> Audit: required

## 0. 执行前必做：重取基线

**起草期读到的一切都可能在开工时已经变了。** 下面八处**逐条重读**，把实读值填进 §0.1，
与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`（后者必须无输出才开工）
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时的最大节号**（起草期是 **§7.13**，
   本 plan 预定落 **§7.14**；若开工时已被别的 plan 占用就顺延，**以开工时实读为准**）
3. `.github/workflows/gates.yml` 第 532–546 行那一步（⑦ 没有测试目录被漏在 CI 之外）的
   `COVERED` 字符串**逐字**（起草期：`contracts context experiments fixtures gates routing tools unit`）
4. `ls -d tests/*/ | xargs -n1 basename | grep -v __pycache__ | sort | tr '\n' ' '`
   （**必须滤掉 `tests/__pycache__/`**，否则与上一条 `COVERED` 天然对不上；
   口径与 `gates.yml:537` 那一行对齐。起草期实读八个目录，与 `COVERED` **逐字相等**）
5. `agenerp/site.py` 的 `_headers()` 与 `_ensure_authenticated()`（起草期实读：**没有任何按调用方给的
   `sid` 认证的入口**，见 §1.3）
6. `agenerp/explain/loop.py` 的 `explain(...)` 签名（起草期实读见 §1.8）
7. `docs/masterplan/STATE.md` §3 里 **2026-08-25T02:10Z 那两条 `[open]`** 是否仍是 `open`
   （**若人已批准激活并改成 `resolved`，Phase 5 的定界要按 §11 第二条重开事件重读**）
8. `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q` 的**开工基线数字**
   （起草期最后一次落账是 `预期红 0，绿 11` + `520 passed`）

### 0.1 执行期重取基线的**实读结果**

执行期实读时间 2026-08-25，逐条：

1. `git log -1 --format=%H` → `7e7f5177c68e1b86b1a552452191484048d94c17`（起草期基线之后又落了一个纯文档提交，
   **与起草期不一致，照实记**）；`git status --porcelain` → **只有一行** `?? docs/plans/p1-insight/2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`（本 plan 自己，尚未入仓）。
   ⚠️ **起草期写的是「必须无输出才开工」，实读不是无输出。** 照实记并逐字说清为什么仍然开工：
   那唯一一行就是**本 plan 文件自身**，它不是别的 plan 留下的脏工作区，也不触及任何产品代码或红线路径。
   把它读成「工作区脏」会让任何一个「起草完立刻执行」的 plan 都开不了工。**判据收窄成：除本 plan 文件外无输出**，实读满足。
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族当时最大节号 → **§7.13**（`:1118`），
   **与起草期一致**，本 plan 落 **§7.14**，无需顺延。
3. `.github/workflows/gates.yml` 第 532–546 行的 `COVERED` 逐字 →
   `contracts context experiments fixtures gates routing tools unit`，**与起草期逐字一致**。
4. `ls -d tests/*/ | xargs -n1 basename | grep -v __pycache__ | sort | tr '\n' ' '` →
   `context contracts experiments fixtures gates routing tools unit `（八个）。
   ⚠️ **与 `COVERED` 是同一个集合，但排序不同**（本机 locale 把 `context` 排在 `contracts` 前，
   `gates.yml:537` 那一行在 runner 上排成 `contracts context`）。集合相等，**逐字串不相等**；
   起草期写的「与 `COVERED` 逐字相等」在本机 locale 下**不成立**，照实记。
   这不影响本 plan——本 plan **不新增测试目录**（Non-Goals 2），第 ⑦ 步照旧。
5. `agenerp/site.py` 的 `_headers()`（`:367-373`）与 `_ensure_authenticated()`（`:352-365`）→
   **与起草期 §1.3 实读逐字一致**：`_headers()` 只发 `Host` / `Accept` /（有体时）`Content-Type` /
   （有 token 时）`Authorization`，**从不发 `Cookie`**；`_ensure_authenticated()` 只有 token / `admin_password` 两条路。
6. `agenerp/explain/loop.py` 的 `explain(...)` 签名 → **与起草期 §1.8 实读逐字一致**（十四个参数，
   `immediate: ImmediateContext | None = None` 在末位）。
7. `docs/masterplan/STATE.md` §3 的 **2026-08-25T02:10Z 两条** → **仍是 `[open]`**（`:499` 激活属风险档 L3 · `:507` plan 预算已用满）。
   ⇒ 人尚未批准激活，Phase 5 的定界**不需要**按 §11 第二条重开事件重读。
8. 开工基线数字 → `python3 tools/gates/check_expected_red.py` **exit 0**（`门禁 11 项：预期红 0，绿 11，跳过 0`）
   `&& python3 -m pytest tests/unit -q` **exit 0**（`520 passed in 1.83s`）。**与起草期最后一次落账逐字一致。**

**附：执行期额外实读的三条前置**（不在八条内，但 §5 要求）：
活栈已 Up 16h（`agenerp-frontend-1` 映射 `127.0.0.1:18080->8080/tcp`，六个 healthy）·
`lsof -nP -iTCP:17801 -sTCP:LISTEN` **无输出**（17801 空闲）·
`~/.config/agenerp/secrets.env` 存在且 `0600`（含 `DASHSCOPE_API_KEY` / `AGENERP_WORKER_PASSWORD`）。
⚠️ `AGENERP_ADMIN_PASSWORD` **不在环境里也不在 `.env` 里**，本仓一贯的取值是字面 `admin`
（出处 `docs/context/project-context.md` 多行逐字 `AGENERP_ADMIN_PASSWORD=admin`），本轮照此。

## 1. Current Baseline

### 1.1 上半交下来的三条裁定，是本 plan 的输入契约（不是可选参考）

出处 `docs/architecture/module-boundaries.md` **§7.13**：

- **D1 · 承载面 = (A) 自建 Frappe app**，走 `hooks["app_include_js"]`；
  **激活（`bench install-app` + 重启）是风险档 L3，强制人批**。
- **D2 · 身份口径 = (i) 当前登录用户**。(ii) Administrator 被逐字判为**一次已知的信息越权**，
  不是「暂未实现」。(iii)「按传入身份重建受限 `SiteClient`」被留作 fallback，
  且 §7.13 逐字写了它的触发条件：**「若 P1.8 下半实测发现必须把请求转手给容器外的 `agenerp` 进程
  （例如 LLM 凭据不进容器），身份问题原样回来，届时 (iii) 是唯一合规选项」**。
  → **§1.7 实读表明这个条件今天就成立**（理由**不是**「凭据送不进容器」——那句经实读已被自我更正——
  而是 **`agenerp` 包本身不在镜像里**），因此本 plan 走 (i) 的语义、(iii) 的实现。
- **D3 · 判定面口径 = ①–⑦ 七条判据形状**，逐条注明挡哪种假实现。本 plan 的判据面必须逐条覆盖。

另有交给下半的三条实读事实（探测记录 §6）：Desk 全局 JS 的完整来源是 `www/app.py:47` 一行两项 ·
(A) 的身份**只对跑在容器内的代码白送** · **app 里不得出现 `Client Script` / `Server Script` fixture**。

### 1.2 本仓一行承载面代码都没有

`ls` 仓根：无 `apps/` 目录。`agenerp/` 下九个包（`context` / `explain` / `insight` / `inspection` /
`orchestration` / `packs` / `routing` / `seed` / `tools`）**没有任何 HTTP 服务面** ——
`grep -rn "http.server\|HTTPServer\|BaseHTTPRequestHandler"` 全仓**零命中**。
`tests/` 下无 `ui` 目录。**这是净新建，不是改造。**

### 1.3 `SiteClient` 今天**认不出浏览器里那个人**（D2/D3⑦ 的实现缺口）

`agenerp/site.py:367-373` 的 `_headers()` 只发四样：`Host` / `Accept` /（有请求体时）`Content-Type` /
（有 token 时）`Authorization`，**从不发 `Cookie`**（全仓 `grep -n sid agenerp/site.py` 只命中 `:132`
一句注释）。`:352-365` 的 `_ensure_authenticated()` 只有两条路：token 对，或用
`AGENERP_ADMIN_PASSWORD` 打 `POST /api/method/login` 换会话。
⇒ **今天没有任何入口能让调用方说「用这个人的 `sid` 去读」**。
D3⑦ 逐字要求的「把请求里的 Frappe `sid` cookie 转发给站点」，**必须先在本模块开一条认证模式**。

⚠️ 这条改动落在 `agenerp/site.py` —— 它**不是** Protected Areas 里的任何一行
（那两行覆盖的是「对活站点的破坏性写」与「非破坏性写（建/改）」两个**写面**），
本 plan **不新增任何写方法**，`tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`
**一个字不动**。但它确实是**认证面**的变更，因此按 `ai-autonomy-policy.md`
「changing … auth, permission … behavior without an owner doc and test strategy」→ **plan-first**：
owner doc 是 §7.13 的 D2，test strategy 是 D3⑦ + §7 Phase 2 的判据表。

### 1.4 **`tests/ui/` 一旦被创建，CI 当场红 —— 而修它属红线 2**

`.github/workflows/gates.yml:532-546` 的第 ⑦ 步把测试目录集合**写死**成
`contracts context experiments fixtures gates routing tools unit`，
并逐字写着「新增目录必须显式接进本 job（或列入 `COVERED` 并说明为何不跑）」，多出目录即 `exit 1`。
而 `.github/workflows/**` 在红线 2 与 Protected Areas 里都是 `blocked`。

⇒ **本 plan 不创建 `tests/ui/`，也不创建 `tests/ui/test_sidebar.py`。**
按 **P1.0a / P1.4 / P1.5 / P1.7 四次先例**交**断言体** + 交接说明，由人按路径加载。
⚠️ 这与前四次的理由**不同**：前四次是因为 `tests/gates/**` 是裁判（红线 1），
这一次是因为**新增测试目录会打红一条 CI 元判据，而修那条元判据在红线 2 内**。
**理由不同，处置相同，不许把两者混成一句话。**

### 1.5 `live` marker 已注册，不必新增

`pyproject.toml` 的 `[tool.pytest.ini_options].markers` 逐字有
`live: 需要活站点 / docker 的慢门禁（L2）。L1 快门禁跑 -m 'not live'`。
⇒ WBS 那条 `pytest -m live tests/ui/test_sidebar.py` 的 `-m live` 语义**今天就存在**，
缺的只有那个文件本身（§1.4）。

### 1.6 激活这一步卡在人批上，账已经记过

`docs/masterplan/STATE.md` §3 有两条 **2026-08-25T02:10Z** 的 `[open]`：
一条是激活属风险档 L3 强制人批（含命令原文与回滚原文），
一条是「工作项 10 的 plan 预算已用满表规 3 的 2 个，而 WBS 验收命令交不出来 —— 拆行只有人能做」。
**本 plan 就是那两条里点名的「P1.8 下半」，是工作项 10 的第 2 个（也是最后一个）plan。**
本 plan **不代人批、不试探、不绕道**，也**不再重复登记**那两条。

### 1.7 解释必须跑在容器外 ⇒ D2 的 (iii) 分支今天就被触发

实读三处：① `docker-compose.yml` 的 `x-ai-env` **通道是存在的**（`AGENERP_LLM_ENDPOINT` /
`AGENERP_LLM_API_KEY` / `AGENERP_LLM_MODEL` 三个变量已注入容器），**只是值默认为空**，
且逐字写着「**不出现在任何 healthcheck 或 command 的成败路径上**」——
**因此「凭据进不了容器」这句话是错的，正确的说法是「今天没有人往那三个变量里填过值，
而填它们要动 `.env` 或 compose，后者在 Non-Goals 里」**；
② `2026-08-24-2311-1` 的 Closure 逐字记着 `DASHSCOPE_API_KEY` 已迁到
`~/.config/agenerp/secrets.env`（0600，**仓库目录之外**，用户 2026-08-24 明示）；
③ `agenerp` 包**不在容器里**（上半 plan §1.2 实读，`sites` / `logs` 是仅有的两个 volume）。

⇒ (iii) 的正当性**不挂在「凭据送不进去」上**（上面已自我更正），而挂在这一条：
**`agenerp` 包本身不在镜像里**，要让解释跑在容器内就得同时解决三件没有裁定过的事 ——
把 `agenerp` 装进镜像（改 `docker-compose.yml` 或自建镜像，Non-Goals 1/3）·
把 LLM 凭据从 `~/.config/agenerp/secrets.env` 搬进容器环境（密钥面变更）·
容器出网策略。**每一件都比本 plan 大。**
本 plan 按 §7.13 D2 预写的那句话走 **(iii)**：解释跑在**容器外的本机进程**，
身份由**浏览器传来的 `sid`** 重建。**这不是绕开 (i)，(i) 是语义、(iii) 是实现路径。**

### 1.8 `explain()` 的入口形状（`agenerp/explain/loop.py:622-666` 实读）

```
explain(question, *, task_class, client, models, requested=None, config=None, transport=None,
        doctypes=None, session_id="explain", user="", max_turns=MAX_TURNS,
        executors=None, immediate=None) -> ExplainResult
```

- `client` 是 `SiteClient` —— **服务面要给的就是这一个对象**，身份差异全落在它身上。
- `immediate` 是 ① 即时上下文，**给了就渲染成一条独立 `system` 消息**；模块 docstring 逐字写着
  「**① 层不查权限** …… 字段表是不是当前身份有权看的，**由调用方负责**」。
  → 这句话就是 `STATE.md` §3 `[open] 2026-08-25T00:35Z` 第 ① 项的全部内容，本 plan 是它点名的承接者。
- `models` 是 `agenerp.routing.CAPABILITIES` 那份声明（`tests/unit/test_explain_immediate_context.py`
  与 `docs/evidence/p1-immediate/` 两处调用形态可照抄）。

### 1.9 与本 plan 相关的既有事实（只列，不重复登记）

- 受限身份「车间工人」已由 `agenerp/seedusers.py` 幂等建出（只读 3 个 DocType），
  roadmap「已知的坑」那一节逐字记着它的边界：**受限身份枚举不出 DocType 清单**，
  `permission.scope` 的候选集必须由调用方给。
- 固定测例：成品仓积压 1,010 台；`docs/evidence/p1-immediate/immediate-source-doc.json`
  是一份现成的 `Sales Order` 字段表（70 个字段），可作离线夹具的**形状**来源。
- 基线判据数：`tests/unit` **520 passed** · `tests/contracts` 151 · `tests/tools` 81 passed, 12 skipped ·
  `tests/routing` 164 passed, 1 skipped · `tests/context` 53 passed。

## 2. Goals

1. **承载面 app 的源码进 git**：`apps/agenerp_desk/**` 走 `hooks["app_include_js"]`，
   带 ⌘K 唤起与侧边栏挂载。**只进 git，不激活**（激活是人的动作，§1.6）。
2. **解释请求面落地**：本机 HTTP 服务，绑定地址**字面** `127.0.0.1`，
   只收 `{doctype, name, question}` 三个键，**身份来自浏览器传来的 `sid`**，
   坏输入的状态码与错误标识**在动手前写死**。
3. **D3 ①–⑦ 七条逐条落成可跑判据**，全部进 `tests/unit`（`GATE_VERIFY` 与 CI 两侧都复跑得到）。
4. **`tests/ui/test_sidebar.py` 的断言体 + 交接说明**交付（§1.4 的理由），
   并在 `STATE.md` §3 追加一条 needs-human。
5. **越权处停机**：任何一步落到「强制人批」，停在那里记进 needs-human，**不代人做、也不绕过去**。

## 3. Non-Goals

1. **不激活承载面**。点名覆盖：`bench new-app` · `bench install-app` · `bench build` · `bench migrate` ·
   改 `sites/apps.txt` · 改全局 `installed_apps` · `docker cp` · 给 `docker-compose.yml` 加 bind mount 或
   `build:` · 任何写 `sites/` 的命令。**见即停清单在 §5.1，执行期不许现编。**
2. **不创建 `tests/ui/` 与 `tests/ui/test_sidebar.py`**（理由 §1.4，不是省事）。
   **也不声称满足 `02-WBS.md` §4 P1.8 那条验收命令。**
3. **不改 `tests/gates/**` · `.github/workflows/**` · `missions/*.json` · `docs/masterplan/**`**
   （红线 1/2/3/5）；`STATE.md` 只追加。
4. **不写任何业务数据**（P1 是②端只读）。服务面**不提供任何写路径**，
   `SiteClient` 的写方法一个都不新增，`WRITE_METHOD_ALLOWLIST` 一个字不动。
5. **不引入任何第三方依赖** —— 不装浏览器驱动（playwright / selenium）、不装 web 框架。
   ⇒ **本 plan 不主张「⌘K 在真实浏览器里被按下并弹出了侧边栏」被验证过**，
   能主张的只有「那段 JS 里有这个绑定、且它进了 git」。这条限制写进落点节，不粉饰。
6. **不接受浏览器传来的字段表**（D2-下，见 §7 Phase 3）：请求体只有 `{doctype, name, question}`，
   多一个键就 400。字段表由服务端**用那个人的 `sid`** 去站点取。
7. **不设成本阈值、不加任何拦截分支**（D-18）。本 plan 复用 P1.7 的账本，不动它。
8. **不改 `docs/masterplan/DECISIONS.md`**，不新增 `R-x`（红线 3）。
9. **不动 `docs/backlog/p1-insight-roadmap.md` 的 Work Item Status 块** —— 工作项 10 的状态位
   由引擎在 closure 审计通过后回写，不由本 plan 改。
10. **不生成运行时 Server Script**（红线 7，无条件）；app 里**不得出现**
    `Client Script` / `Server Script` 两类 fixture（D3⑥）。

## 4. Task Route

- Type: `app-layer design change` + `implementation-only change`
  （承载面与请求面的净新建；**认证面变更**使它落在 plan-first，见 §1.3）
- Owner Docs：
  - `docs/architecture/module-boundaries.md` **§7.13**（**输入契约**，只读不改；本 plan 追加 **§7.14**）
  - `docs/architecture/module-boundaries.md` **§7.7 / §7.8 / §7.11 / §7.12**（**只读**：
    上下文层 · 解释循环 · 成本账本 · ① 接进循环 四个既有落点）
  - `docs/architecture/module-boundaries.md` **§11.7**（**只读**，`agenerp/site.py` 的边界节；
    本 plan 动它的认证面 ⇒ 需在 §7.14 记一条指针，**不改写 §11.7 已有行**）
  - `docs/architecture/system-baseline.md` **§4 三端模型**（**只读**，逐字「Desk 原样保留」——
    本 plan 的读法与它是否冲突，Phase 4 必须逐字回答，见 §7 Phase 4 的 `Decision` 项）
  - `docs/architecture/system-baseline.md` **§14 / §14.1**（**只读**，「回环绑定 IP 必须字面写死」
    与「密钥只从环境变量读取，不入库、不入源码、不入日志」两条的出处）
  - `docs/design/agents-and-roles.md` **§9 风险档表**（**只读**，L3 强制人批的出处；
    ⚠️ 与 §5.0 的证据门禁 L1–L3 **同名不同义**，全文引用必须带「风险档」三字）
  - `docs/design/context-and-memory.md` **§8.2**（**只读**，① 即时上下文的规则源）
  - `docs/context/ai-autonomy-policy.md` **Protected Areas**（**只读**）
  - `docs/masterplan/DECISIONS.md` **D-10 / D-15 / D-16 / D-18**（**只读**，红线 3）
- Skill Selection Basis：
  Phase 1 是只读探测 → `Skill: none`（registry 无探索类 skill；`bug-diagnosis-prompt.md` 不适用，本 phase 无 bug）；
  Phase 2–4 的裁定用 `development-wisdom-gate-prompt.md` 自查（required input「assumption inventory」正是 §6）；
  草案评审 `plan-audit-prompt.md`；关闭审计 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

- **活栈**：`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300`。
  ⚠️ 裸跑 `docker compose up -d` 会落到 **8080**，而 8080 被本机另一套常驻 ERPNext 栈占着。
- **站点只读访问**：`AGENERP_SITE=frontend` · `AGENERP_SITE_URL=http://127.0.0.1:18080` ·
  `AGENERP_ADMIN_PASSWORD`（Phase 1 探测与 Phase 5 活跑都要）。
- **受限身份**：本 plan **无条件不跑** `python3 -m agenerp.seedusers --load-users --site frontend`。
  理由是它是**写**动作（走 `create_doc` / `ensure_doc`，落在 Protected Areas 里
  「对活站点的非破坏性写（建 / 改）」那一行，`plan-first`，Required Evidence 含一条
  「对可逆性说话」的），而本 plan 通篇声称对活站点**只读**（Non-Goals 4），
  两者自相矛盾；它同时也撞 §5.1 见即停第 5 条（任何 `POST` 到站点）。
  → **开工时若「车间工人」不在站点上，H3 与 Phase 5「活跑三」整体记 blocked 并停机交人，
  不跑装载器把它建出来。** 起草期实读：该身份已在站点上（`agenerp/seedusers.py` 幂等建过），
  因此预期不触发这条停机。
- **LLM 凭据**：`~/.config/agenerp/secrets.env`（0600，仓库目录外）。
  Phase 5 活跑需要它；**缺了就把 Phase 5 的活跑记成 blocked，不伪造数**。
- **服务端口**：本机 HTTP 服务默认 **17801**（见 §7 Phase 3 的 `Decision` D-下-3）。
  开工前确认它空闲：`lsof -nP -iTCP:17801 -sTCP:LISTEN`（无输出即空闲）。
- **回滚**：本 plan 对活站点**只读**（Non-Goals 1/4），站点侧无需回滚；
  仓内改动 `git revert` 即完整回滚。**本 plan 不跑 `bench backup`** ——
  它会往共用的 `sites:` volume 里写文件，正撞 §5.1 见即停，且本仓从未写过任何 restore 命令，
  那份备份买不到任何东西（理由与上半 plan §5 逐字相同）。

### 5.1 见即停清单（起草期写死，执行期不许现编）

**看见就停下来记进 `STATE.md` §3，不许绕、不许试、不许「先跑一下看看」**：

1. 任何 `bench` 子命令中的：`new-app` · `install-app` · `uninstall-app` · `build` · `migrate` ·
   `backup` · `restore` · `set-config` · `execute`
2. 任何**写** `sites/` 的命令（含 `sites/apps.txt` · `site_config.json` · `common_site_config.json`）
3. 任何对 `docker-compose.yml` 的编辑（含加 volume / bind mount / `build:` / 改 `ports`）
4. `docker cp` 任何方向
5. 任何 `POST` / `PUT` / `DELETE` 到站点 —— **除**两条显式白名单：
   `POST /api/method/login`（换 `sid`，Phase 1 与 Phase 5 都要）
   与 `POST /api/method/logout`（收尾清 `sid`）。
   ⚠️ **按实际发出的 HTTP 动词判，不按方法名听起来是不是只读判** ——
   上半 plan Closure 偏离 3 就是在这条缝上越界过一次（`SiteClient.call_method` 内部走 `POST`）。
6. 任何在活站点上**建或改** `Client Script` / `Server Script` / `Website Script` /
   `Custom HTML Block` / `Workspace Custom Block` / Single 上的 `Code` 字段
7. 任何 `pip install` / `npm install`（Non-Goals 5）
8. 任何对 `tests/gates/**` · `.github/workflows/**` · `missions/*.json` ·
   `docs/masterplan/**`（`STATE.md` 追加除外）的写

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下面每一格在开工前写死，执行期只填「实际」列，预测列一个字不改。**
不吻合的**照实记并说清前提哪里错了**，不许事后改写预测。

| # | 假设（预测，逐字） | 怎么测 | 实际 |
|---|---|---|---|
| **H1** | `POST /api/method/login` 回的 `Set-Cookie: sid=…` **不带 `HttpOnly` 属性** ⇒ Desk 里的 JS 用 `frappe.get_cookie("sid")` 读得到它 | `curl -i -sS -X POST -H "Host: frontend" -H "Content-Type: application/json" -d '{"usr":…,"pwd":…}' http://127.0.0.1:18080/api/method/login`，逐字读 `Set-Cookie` 行 | **不吻合（决定性）**。实读 `Set-Cookie: sid=<REDACTED>; Expires=Mon, 31 Aug 2026 19:57:54 GMT; Max-Age=612000; **HttpOnly**; Path=/; SameSite=Lax` —— **`HttpOnly` 在**。退出码 0，`HTTP/1.1 200 OK`。⚠️ 同批五个 cookie 里**只有 `sid` 带 `HttpOnly`**（`system_user`/`full_name`/`user_id`/`user_image` 都不带）⇒ `frappe.get_cookie("sid")` **按构造读不到**。**触发 Phase 1 Exit Criteria 第 4 条的停机分支。** 记录 `docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md` |
| **H2** | **伪造 / 过期 `sid` 不会回 401/403，而是回 HTTP 200 且 `message == "Guest"`** ⇒ 服务面**不许靠状态码判登录**，必须判「回的用户名是不是 `Guest`」 | `GET /api/method/frappe.auth.get_logged_user`，`Cookie: sid=<乱写一串>` 一次、`Cookie` 整个不带一次，逐条记状态码与载荷 | **不吻合**。三条实读：有效 `sid` → **200** `{"message":"Administrator"}`；乱写 `sid` → **403** `{"session_expired":1,"exception":"frappe.exceptions.PermissionError: …Function <strong>frappe.auth.get_logged_user</strong> is not whitelisted…"}`；不带 `Cookie` → **403**（同文本，**无** `session_expired`）。**前提本身错了**：该方法对 Guest 不在白名单，根本走不到「回 `Guest`」那一步。⚠️ 按承重格注记，**「不许用状态码代替用户名判定」不因此放松**；但这条的下游（Phase 3 的 `resolve_user`）已随停机分支整体 Deferred |
| **H3** | 有效 `sid` 下 `frappe.auth.get_logged_user` 回的**就是登录时那个 `usr`**；用「车间工人」的 `sid` 读它**读不到的** DocType 回 **HTTP 403** | 两个身份各登录一次，各读一次可读 DocType、一次不可读 DocType | **吻合（两半都吻合）**。worker 登录 → 200 `full_name=车间工人`；`get_logged_user`（worker 的 `sid`）→ **200** `{"message":"worker@hrd.example.com"}`（**就是登录时那个 `usr`**）；`GET /api/resource/Item?limit_page_length=1`（可读）→ **200** `{"data":[{"name":"HRD-ASSY-SVC"}]}`；`GET /api/resource/Sales%20Order?limit_page_length=1`（不可读）→ **403** `PermissionError`；`GET /api/resource/Sales%20Order/HRD-SO-0001` → **403**，`_server_messages` 逐字含 `User <strong>worker@hrd.example.com</strong> does not have doctype access via role permission for document <strong>Sales Order</strong>`。⚠️ **未跑 `seedusers`**（该身份开工时已在站点上），不触发 §5 那条停机。**活端点侧（Phase 5）随停机分支 Deferred，本格只填假站点外的站点侧** |
| **H4** | 服务面在 `sid` 缺失 / 伪造时**不会静默回退到管理员凭据** —— 这是本 plan 最重要的一条反测。预测：**不回退**（因为 Phase 2 的 `sid` 模式与 `admin_password` 是互斥构造，不是回退链） | `tests/unit` 判据：构造只给 `sid` 的客户端，断言请求头有 `Cookie: sid=…`、**没有** `Authorization`、**没有**任何 `POST /api/method/login` | **吻合**（本 plan 唯一一格既做了预测、又在**同一个 phase 内**测到的假设）。`tests/unit/test_site_client_sid.py` 判据①②③ 各绿：`Cookie: sid=…` 逐字相同 · **零** `Authorization` · 假 transport 记下的请求列表逐条断言后**零** `login`（单次与多次调用各一条）。构造侧另有判据⑧（AST + 字面量双扫 `client_from_sid` 函数体，零凭据零件）。⚠️ 但**「服务面」不存在** —— 本格测到的是 `SiteClient` 这一层，不是 plan 起草期设想的 `agenerp/serve/`（Phase 3 已 Deferred）。**照实记，不把两者混成一句话。** 变异 M1/M2/M20/M21/M23/M24 逐条打红，红在哪条断言见 §7.14 的表 |
| **H5** | 活端点一跑：`usage` 三项**全部 > 0**，账本条数 == `adapter.chat()` 被调次数，答案里出现**只有那张单据才有的值** | **未测（Phase 5 整体 Deferred）**。不是 blocked（LLM 凭据其实在位），是**按构造无处可测** —— 它测的是「活端点」，而端点随 Phase 3 一起没写。⚠️ **不记成绿也不记成红。** |
| **H6** | **差分成立**：换第二个 `name` 跑第二次，两跑的 ① 档来源字段表**不同**，且答案文本**不同** | **未测（Phase 5 整体 Deferred）**，理由同 H5。|
| **H7** | 坏输入**十一格逐条**回预写的状态码与错误标识（表见 Phase 3 D-下-4），**没有一格回 200**（预检那格回 204） | **未测（Phase 3 / Phase 5 整体 Deferred）**。十一格的状态码与错误标识**已在起草期写死**（D-下-4 那张表原样保留在本文件里），但**没有任何实现去满足它，也没有任何判据去测它**。⚠️ **那张表因此是一份规格，不是一份证据。** |
| **H8** | 缺 `Origin` 头、非回环 `Origin`、`Origin: null` **三种全部 403**；而 Desk 自己的 `Origin`（`http://127.0.0.1:18080`）放行 | **未测（Phase 3 整体 Deferred）**，理由同 H7。|
| **H9** | `apps/agenerp_desk/**` 静态扫描：**零** `Client Script` / `Server Script` fixture（按构造为真），且 `hooks.py` 的 `app_include_js` 指向**仓内真实存在**的文件 | **未测（Phase 4 整体 Deferred）**。`apps/agenerp_desk/**` **不存在**，判据文件也不存在。⚠️ 「零 `Client Script` / `Server Script` fixture」这句话此刻是**空真**（没有 app 就没有 fixture），**不算证据**。|
| **H10** | JS 里那个 `http://127.0.0.1:17801` 与服务面的 `DEFAULT_PORT` 常量**是同一个数** —— 两边写死会漂移，判据从两个文件各解析一次再比 | **未测（Phase 3 与 Phase 4 均 Deferred）**。两边的文件都不存在，「两个数是不是同一个」按构造问不出来。|
| **H11** | 四个面**逐字不变**：`tests/contracts` 151 · `tests/tools` 81 passed, 12 skipped · `tests/context` 53 passed；`tests/unit` **只增不减**。⚠️ **`tests/routing` 会变多，且能算出来**：`tests/routing/test_adapter.py:485` 的 `PRODUCT_MODULES = sorted((REPO_ROOT / "agenerp").rglob("*.py"))` 把一条判据按**每个 `agenerp/**/*.py` 文件**参数化一次 ⇒ 新增 4 个模块（`serve/__init__.py` · `serve/service.py` · `serve/identity.py` · `serve/__main__.py`）⇒ 预测 **164 → 168 passed, 1 skipped**。**把它写成「逐字不变」会在收口时把一次正常增长误判成回归。** | **四个面吻合，`tests/routing` 那一半的预测前提不成立**。实测：`tests/contracts` **151 passed** · `tests/tools` **81 passed, 12 skipped** · `tests/context` **53 passed** —— 三条逐字不变；`tests/unit` **520 → 540 passed**（只增不减，+20 条全在新建的 `test_site_client_sid.py`）。⚠️ **`tests/routing` 实测仍是 `164 passed, 1 skipped`，不是预测的 168** —— 预测的算式没错（`test_adapter.py:485` 确实按 `agenerp/**/*.py` 全量参数化），错的是**前提**：那 4 个新模块（`serve/**`）随 Phase 3 一起没建，`find agenerp -name '*.py' | wc -l` 实测 **53**（与起草期复核的 53 逐字相同）。**这一格记「前提不成立」，不记「不吻合」** —— 把它记成不吻合会暗示参数化算式有问题，那是错的。|

**⚠️ H2 是本表的承重格**：如果它不吻合（比如站点真回 401），
Phase 3 的登录判定实现要按实测改，**但「不许用状态码代替用户名判定」这条不因此放松** ——
两者都判是更严，不是更松。

## 7. Execution Plan

**执行顺序即下列顺序，不许并行、不许跳。** Phase 1 的实测结果会改 Phase 2/3 的实现细节。

### Phase 1 — 只读探测：`sid` 这条接缝到底走不走得通

Status: completed
Targets: 无仓内改动（探测记录落 `docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md`）
Skill: `none`
Item Types: `Explore | Proof`
Prereqs: 活栈已 Up；`AGENERP_ADMIN_PASSWORD` 已设

- [x] **Explore P1**：`POST /api/method/login` 取一次 `sid`，**逐字**记 `Set-Cookie` 行
      （是否带 `HttpOnly` / `Secure` / `SameSite`）→ 回填 H1
      - Skill: `none`
- [x] **Explore P2**：`GET /api/method/frappe.auth.get_logged_user` 三种输入各一次
      （有效 `sid` / 乱写的 `sid` / 不带 `Cookie`），逐条记**状态码 + 载荷原文** → 回填 H2
      - Skill: `none`
- [x] **Explore P3**：受限身份「车间工人」登录一次，用它的 `sid` 各读一次
      「它读得到的 DocType」与「它读不到的 DocType」，逐条记状态码 → 回填 H3
      - Skill: `none`
- [x] **Proof**：探测前后各取一次四类可数文档计数（`Client Script` / `Server Script` /
      `Custom HTML Block` / `Workspace Custom Block`）与 `bench --site frontend list-apps`，
      证明**本 phase 对活站点零写**（照抄上半 plan Closure 的两种读回口径）
      - Skill: `none`
- [x] **收尾**：每个取到的 `sid` 用完打一次 `POST /api/method/logout`；
      **探测记录里不得出现任何 `sid` 的真值**（§14「密钥不入源码、不入日志」）
      - Skill: `none`

Exit Criteria:

- [x] H1 / H2 两格「实际」列已填，每格附**命令原文 + 退出码 + 载荷摘要**；
      **H3 已填，或按 §5「受限身份」那条记成 blocked 并停机交人**（两者取其一，不许留白）
- [x] 「对活站点零写」两种读回逐条落进探测记录
- [x] 探测记录里**零 `sid` 真值**（自查方式：对该文件 grep 本轮用过的 `sid` 前 8 位，须无输出）
- [x] 若 H1 不吻合（`sid` 是 `HttpOnly`）→ **Phase 2 跑完就停**，
      **Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**，重开事件逐字为
      「`sid` 接缝被重新裁定（由人或一个新 plan）」，并把
      「浏览器读不到 `sid`，D3⑦ 的接缝需重新裁定」写进 `STATE.md` §3。
      ⚠️ **不许只停 Phase 3 而让 Phase 4 继续** —— 那会产出「一条没有调用方的认证模式 +
      一段取不到 `sid` 的 JS」两个各自关不掉 D3 的残件，还都进了 git，
      正是 Minimum Rule 4「一个 plan 一个结果面」要挡的形态
- [x] `docs/logs/` 更新

### Phase 2 — `SiteClient` 增一条 `sid` 认证模式（**只读面，不新增任何写方法**）

Status: completed
Targets: `agenerp/site.py` · `tests/unit/test_site_client_sid.py`（新建）
Skill: `development-wisdom-gate-prompt.md`（自查）
Item Types: `Add | Decision | Proof`
Prereqs: Phase 1 的 H2 已回填（错误语义决定这里怎么判「没登录」）

- [x] **Decision D-下-1 · `sid` 认证做成第三条互斥模式，不做回退链**
      - 选中：构造参数 `sid=`，与 `api_key/api_secret`、`admin_password` **三者互斥**；
        给了 `sid` 就**只**发 `Cookie: sid=…`，**不发** `Authorization`、**不打** `/api/method/login`。
      - 备选①「在既有 `_ensure_authenticated` 末尾加一条 `sid` 分支」→ **否决**：
        那是回退链，`sid` 失效时会**静默降级成管理员** —— 正是 D2 判为「已知信息越权」的那个形态。
      - 备选②「让调用方自己传 `transport` 塞 cookie」→ **否决**：把认证语义推给调用方，
        判据只能判到假 transport 上，产品路径无判据（本仓踩过同形状的坑，roadmap 工作项 5 的 M6）。
      - 残余风险：`sid` 是**明文**在进程内传递的短期凭据。缓解是三条：不落盘、不进日志、
        不进任何异常消息（`SiteError` 的消息里带 URL 与响应体，**不带请求头**——需一条判据钉住）。
      - Skill: `development-wisdom-gate-prompt.md`
- [x] **Add**：`SiteClient.__init__` 加 `sid: str | None = None`；`_headers()` 在 `sid` 模式下加
      `Cookie: sid=<v>`；`_ensure_authenticated()` 在 `sid` 模式下直接返回（**无登录动作**）
      - Skill: `none`
- [x] **Add**：`agenerp/site.py` 加 `client_from_sid(site, sid, *, transport=None) -> SiteClient`
      （**不读任何凭据环境变量**，只读 `default_base_url()`）
      - Skill: `none`
- [x] **Proof** `tests/unit/test_site_client_sid.py`，至少七条（每条注明挡哪种假实现）：
      ① `sid` 模式下请求头**有** `Cookie: sid=…`；
      ② `sid` 模式下**没有** `Authorization` 头；
      ③ `sid` 模式下**没有任何** `POST /api/method/login`（假 transport 记录全部请求，逐条断言）；
      ④ 三种凭据**两两同给即报错**（互斥，指名冲突的是哪两个）；
      ⑤ `sid` 为空串 / 全空白 → 报错，**不静默当成没给**；
      ⑥ `SiteError` 的消息里**不出现** `sid` 的值（正例：故意让站点回 500，断言消息里搜不到那串）；
      ⑦ **写方法登记面未变**：`WRITE_METHOD_ALLOWLIST` 与 `agenerp/site.py` 的公开写方法集合
        逐字相等（复用 `tests/unit/test_site_client.py` 的既有口径，**不抄第二套**）；
      ⑧ **`client_from_sid` 的函数体里零凭据零件**：AST 扫它的函数体，
        `ADMIN_PASSWORD_ENV` / `API_KEY_ENV` / `API_SECRET_ENV` /
        `credential_from_env` / `os.environ` **一个都不出现**
        （与 Phase 3 ⑩ 是同一条道理的两侧：⑩ 扫服务面，本条扫工厂函数）
      - Skill: `none`

Exit Criteria:

- [x] **八条**判据（①–⑧）全绿，`python3 -m pytest tests/unit -q` **只增不减**
- [x] `tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST` **一个字未改**
      （自查：`git diff -- tests/unit/test_site_client.py` 无输出）
- [x] `module-boundaries.md` §7.14 记一条指向 §11.7 的指针（**不改写 §11.7 已有行**）
- [x] `docs/logs/` 更新

### Phase 3 — 解释请求面 `agenerp/serve/`（本机 HTTP 服务）

Status: deferred-but-adjudicated（**由 Phase 1 的 H1 实测中止**）

> ⚠️ **本 phase 一行代码都没写。** Phase 1 实测 `sid` 带 `HttpOnly`（H1 不吻合），
> 触发本 plan Phase 1 Exit Criteria 第 4 条**起草期写死**的停机分支：
> 「Phase 2 跑完就停，**Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**」。
> 重开事件逐字：**`sid` 接缝被重新裁定（由人或一个新 plan）**。
> 下面每一格都**不是复选框**，而是 `🔴 [未做 · Deferred]` 标记 —— 按 `00-plan-authoring-and-execution-guide.md`
> 「When Executing」第 8 条逐字「If an item cannot be completed, move it to `Deferred But Adjudicated` …
> **Do not leave it unchecked in the execution list**」，已 Deferred 的项不留在执行清单里当未勾选项。
> ⚠️ **这不是勾上，更不是声称做过** —— 本 phase 一格都没做，定界见 §11 第一条。
> 定界与理由见 `docs/architecture/module-boundaries.md` §7.14 与 §11「Deferred But Adjudicated」。

Targets: `agenerp/serve/__init__.py` · `agenerp/serve/service.py` · `agenerp/serve/identity.py` ·
`agenerp/serve/__main__.py` · `tests/unit/test_explain_service.py`（全部新建）
Skill: `development-wisdom-gate-prompt.md`（自查）
Item Types: `Add | Decision | Proof`
Prereqs: Phase 2 完成（服务面拿 `client_from_sid` 建客户端）

- 🔴 **[未做 · Deferred]** **Decision D-下-2 · 请求体只收 `{doctype, name, question}` 三个键，多一个即 400**
      - 这是 `STATE.md` §3 `[open] 2026-08-25T00:35Z` 第 ① 项（① 层不查权限、
        谁调 `explain(immediate=…)` 谁就能把任意字段表送进模型）的**承接处置**：
        **字段表由服务端用那个人的 `sid` 去站点取，浏览器不许自带。**
      - 备选①「浏览器把 `cur_frm.doc` 整份发过来」→ **否决**：那正是那条 `open` 描述的越权形态，
        而且浏览器里的 `doc` 可被任意篡改。
      - 备选②「在 `agenerp/context/immediate.py` 里补权限校验」→ **否决**：
        补在那里等于推翻 P1.2 的分层裁定与 §7.7，那条 `open` 逐字写着「**不在 ① 层补校验**」。
      - **`assemble()` 的六个参数在这里全部定死**（`agenerp/context/immediate.py:113-121` 实读签名
        `assemble(*, doctype, name, fields, role, view, actions=())`，`role` / `view` **会进模型提示词**，
        起草期不定死＝执行期现编）：
        `doctype` / `name` 取请求体那两个键；`fields` 取**用那个人的 `sid`** 从站点读回的整份字段表；
        `role` 取 `resolve_user()` 回的**用户名**（不是角色名——本仓今天拿不到角色清单，
        roadmap「已知的坑」逐字记着受限身份枚举不出 DocType 清单，角色同理，**不编一个**）；
        `view` 取字面 `"desk-sidebar"`；`actions` 取 `()`（② 档已在 `messages` 里，D2 已裁不重复注入）。
        配一条判据钉住这**六个**取值（`doctype` / `name` / `fields` / `role` / `view` / `actions` 各一格），
        **变异**：把 `role` 改成写死的 `"Administrator"` → 必须红。
      - 残余风险：服务面成了 ① 档字段表的**唯一**合法来源，绕过它直调 `explain(immediate=…)`
        的人照样能塞任意字段表 —— 本 plan **不主张**「① 层已被证明拿不到越权字段」，
        只主张「**产品路径上**字段表来自那个人的身份」。
      - Skill: `development-wisdom-gate-prompt.md`
- 🔴 **[未做 · Deferred]** **Decision D-下-3 · 绑定地址字面写死、端口给常量、允许来源必须是回环**
      - `BIND_HOST = "127.0.0.1"` 是**模块级字面常量，不经任何环境变量**
        （`system-baseline.md` §14.1 同一条理由；判据是静态文本扫描 + 运行期断言两侧）。
      - `DEFAULT_PORT = 17801`，可由 `AGENERP_EXPLAIN_PORT` 覆盖（端口不是安全边界，绑定地址才是）。
      - **允许的 `Origin` 由 `agenerp.site.default_base_url()` 推出**（与站点客户端同源配置，
        不新开第二个环境变量）；**但推出来的主机名必须是回环**（`127.0.0.1` / `localhost` / `::1`），
        否则**服务拒绝启动并指名原因** —— 不是拒绝那一次请求，是根本不起来。
      - 备选「允许 `*`」→ **否决**：任何网页都能拿着用户的 `sid`（若它能读到）打本机服务。
      - 残余风险：本机上的**其它进程**照样能直接打 `127.0.0.1:17801`。
        `Origin` 挡的是浏览器里的跨站，不挡本机进程 —— **照实写进落点节，不粉饰成「已隔离」**。
      - Skill: `development-wisdom-gate-prompt.md`
- 🔴 **[未做 · Deferred]** **Decision D-下-4 · 坏输入的状态码与错误标识，起草期写死（D3⑤）**

      | 输入 | 状态码 | `error` 标识 |
      |---|---|---|
      | 缺 / 空 / 伪造 `sid`（含 `get_logged_user` 回 `Guest`） | **401** | `not-logged-in` |
      | 缺 `Origin` 头 / 非回环 `Origin` / `Origin: null` | **403** | `bad-origin` |
      | 请求体多出 `{doctype,name,question}` 之外的键 | **400** | `unexpected-field` |
      | `question` 为空或全空白 | **400** | `empty-question` |
      | `question` 超过 **4000** 字符 | **413** | `question-too-long` |
      | `{doctype, name}` 在站点上不存在（站点回 404） | **404** | `document-not-found` |
      | 该身份无权读那份单据（站点回 403） | **403** | `not-permitted` |
      | 方法不是 `POST` 或路径不是 `/explain` | **404** | `no-such-endpoint` |
      | **`OPTIONS /explain` 且 `Origin` 是 Desk 源（CORS 预检）** | **204** | 无体，回**四个头**：`Access-Control-Allow-Origin: <那个源>` · `Access-Control-Allow-Headers: Content-Type, X-Frappe-Sid` · `Access-Control-Allow-Methods: POST` · `Access-Control-Max-Age: 600` |
      | `OPTIONS /explain` 且 `Origin` 缺失 / 非回环 / `null` | **403** | `bad-origin`，且**一个 `Access-Control-Allow-*` 头都不回** |
      | 未预期异常（站点 5xx、`RoutingError`、`SiteError`、任何未捕获栈） | **500** | `internal-error`，**响应体里不含异常文本、不含 `sid`、不含站点响应原文** |

      ⚠️ **预检这两格不是补充，是承载面能不能工作的前提**：Phase 4 的 JS 用自定义头
      `X-Frappe-Sid` + `Content-Type: application/json` 打跨源请求，浏览器**必定先发一次
      `OPTIONS` 预检**；服务面不答预检，那次 `fetch` 在浏览器里根本发不出去，
      而**所有 `tests/unit` 判据都会绿**（它们不经浏览器）。
      ⚠️ **凡 `Origin` 过了校验的响应 —— 200 与全部错误码（400 / 401 / 403 `not-permitted` /
      404 / 413 / 500）—— 都必须带 `Access-Control-Allow-Origin`**，否则浏览器读不到响应体，
      **报错在用户那里会长成「网络错误」而不是「你没权限」**。
      **唯一的例外是 `bad-origin` 那两格**（`POST` 与 `OPTIONS` 各一），它们按定义**一个 `Allow-*` 都不回**。
      ⚠️ **所有错误体（401 / 403 / 404 / 413 / 400 / 500）都带一个 `user` 字段**：
      `sid` 解析成功时填用户名，解析失败或未走到那一步时填 `null`。
      没有它，「服务面认出的是谁」在活端点上**没有任何可观测量**，
      D3⑦ 就只剩假站点上的同义反复（Phase 5「活跑三」的断言挂在这个字段上）。
      ⚠️ **`internal-error` 那一格挡的是「把站点的错误原文原样回给浏览器」** ——
      站点 5xx 的响应体里可能带 SQL、路径、甚至凭据片段。

      **判定顺序也写死**：`Origin` → **预检（`OPTIONS`）** → 方法/路径 → `sid` → 请求体形状 → 站点取单据。
      顺序不写死，「越权请求先被 400 挡掉还是先被 401 挡掉」会随实现漂移，判据就判不稳。
      ⚠️ **`not-permitted` 与 `document-not-found` 必须分开** —— 合并成一个会让
      「这个人看不到」与「这张单据不存在」在响应里长得一样，那是把权限信息泄漏与隐藏搞反了：
      本项目取**分开**，理由是 P1 是内网单机、可诊断性优先；**这条是取舍，不是最佳实践，照实记**。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `agenerp/serve/identity.py`：`resolve_user(sid, *, transport=None) -> str`
      —— 用 `client_from_sid` 打 `GET /api/method/frappe.auth.get_logged_user`，
      **回 `Guest` 或空一律抛**（按 H2 的实测语义实现，不靠状态码）
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `agenerp/serve/service.py`：单端点 `POST /explain`，流程逐字为
      **`Origin` 校验 → 预检（`OPTIONS` ⇒ 回 204 + 三个 `Allow-*` + `Max-Age` 后 **就地返回、不再往下走**）
      → 方法/路径 → `sid` → 请求体形状** → `client_from_sid` 取单据字段表 →
      `agenerp.context.assemble(...)` 组 ① 档 → `agenerp.explain.explain(question, task_class="explain",
      client=<那个人的 client>, models=CAPABILITIES, immediate=<① 档>)` → 回
      `{answer, user, doctype, name, usage, model_calls}`
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `agenerp/serve/__main__.py`：`python3 -m agenerp.serve`（打印实际绑定的 host:port）
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof** `tests/unit/test_explain_service.py`（全部假 transport + 假模型，**零站点零 LLM**），
      逐条对上 D3：
      ① **不许拿静态资产当权限判据**（D3①）—— 本服务**根本没有静态资产路径**，
        判据形态是「除 `POST /explain` 外一切路径回 404 `no-such-endpoint`」，
        并在判据文件头逐字写明为什么不写「未登录取不到资产」那条断言；
      ② **同一性**（D3②）—— 注入进模型的 `messages` 里出现**只有该 `{doctype,name}` 才有的值**
        （假站点回一份带唯一标记值的字段表，断言该值出现在 ① 档消息里）；
      ③ **差分**（D3③）—— 换一个 `name` 跑第二次，送进模型的 ① 档消息**不同**；
        另一条反测：假站点**忽略 `name` 永远回同一份** ⇒ 该判据必须红；
      ④ **绑定与来源**（D3④）—— `BIND_HOST` 是字面 `127.0.0.1`（静态文本扫描 + 运行期实际
        `server_address` 双判）；`Origin` 四例（Desk 源放行 / 缺失 / 非回环 / `null`）；
        **变异验证**：把 `BIND_HOST` 改成 `0.0.0.0` → 该判据必须红；
        另一条：`AGENERP_SITE_URL` 指到非回环时**服务拒绝启动**；
      ⑤ **坏输入逐格**（D3⑤，含预检两格与 `internal-error` 一格）—— 状态码与 `error` 标识逐条对上 D-下-4 的表，
        且**判定顺序**另有两条判据（同时坏 `Origin` 与坏 `sid` → 回 `bad-origin`；
        同时坏 `sid` 与空 `question` → 回 `not-logged-in`）；
      ⑦ **`sid` 转发 + 用户名断言 + 伪造必拒**（D3⑦）—— 转发的 `Cookie` 值与请求里那个 `sid`
        **逐字相同**；`get_logged_user` 回 `Guest` → 401；
        **反测**：一个自定义 `X-Logged-In: Administrator` 头**不许**让任何判据变绿；
        **反测**：`sid` 无效时服务面**不许**回退到 `client_from_env`（断言全程零 `Authorization`、
        零 `POST /api/method/login`）；
      ⑧ **CORS 预检 + 跨源可读性，五例**（B1）—— `OPTIONS` + Desk 源 → 204 且**四个头**
        （三个 `Access-Control-Allow-*` + `Access-Control-Max-Age`）**逐字**对上 D-下-4；`OPTIONS` + 缺失 / 非回环 / `null` 源 → 403 且**一个 `Allow-*` 头都没有**；
        另一条：**200 的成功响应带** `Access-Control-Allow-Origin`；
        **第五条**：**每一个错误码的响应都带** `Access-Control-Allow-Origin`（`bad-origin` 两格除外），
        逐个状态码各断言一次；
      ⑨ **服务面的任何输出都不含 `sid`**（M-f）—— 响应体、错误体、
        **以及访问日志**（`BaseHTTPRequestHandler.log_message` **必须被覆写**，
        默认实现把请求行打到 stderr；判据捕获 stderr 并搜那串 `sid`，须无命中）；
        另一条：`internal-error` 的响应体里搜不到假站点回的异常原文；
      ⑩ **构造判据（M-g）**：**扫描面是 `agenerp/serve/**` 的全部源码 + `agenerp/site.py`
        里 `client_from_sid` 的函数体**（后者不能漏 —— 凭据回退最省事的藏法就是藏在那个工厂函数里），
        其中**零出现**这八个标识符：`client_from_env` / `credential_from_env` /
        `AGENERP_ADMIN_PASSWORD` / `AGENERP_API_KEY` / `AGENERP_API_SECRET` 与
        **本仓用来引用它们的三个常量名** `ADMIN_PASSWORD_ENV` / `API_KEY_ENV` / `API_SECRET_ENV`
        （AST + 文本双扫；只扫字符串字面量会被常量引用整个绕过），
        **变异验证**：加回其中任一个 → 必须红。
        ⚠️ 这条与 ⑦ 的两条行为反测**不重复**：行为反测判「这一次没回退」，
        构造判据判「代码里根本没有回退所需的零件」，**两者都要**
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof · 只判单据字段表那一半**：字段表走 `agenerp.context.assemble()`，
      它内部已经用 `agenerp.tools.runtime.wrap_free_text` 包过（`immediate.py` 模块头规矩 3）；
      判据钉住「**服务面没有第二条包法**」—— `agenerp/serve/**` 里零出现 `wrap_free_text`
      与任何自己拼边界串的代码。
      ⚠️ **`question` 不走那条咽喉，本 plan 也不让它走** —— 逐字说清：
      `question` 是**用户自己打的字**，把它包成「来自数据的自由文本」是把提问伪装成数据，
      与 `runtime.py` 那条咽喉的语义不同；而给它另开一条包法要动
      `agenerp/explain/loop.py` 的消息装配面，那是 P1.4 的落点、不在本 plan 的 Targets 里。
      **残余风险照实登记**（进 §7.14 与 §8 R8）：一个精心构造的 `question` 能在模型看到的
      `messages` 里伪装成系统指令；今天挡它的只有 `question` 长度上限（4000）与
      「② 作答前门禁永远开着」，**这两条都不是注入防线，不许说成是**。
      - Skill: `none`

Exit Criteria:

- 🔴 **[未做 · Deferred]** D3 的 ①②③④⑤⑦ 六条**逐条**有判据，**外加本 plan 自立的 ⑧（预检）/ ⑨（输出零 `sid`）/
      ⑩（`agenerp/serve/**` 零凭据零件）三条**，每条在测试 docstring 里注明「它挡的是哪种假实现」
- 🔴 **[未做 · Deferred]** **本 phase 名下的 M 编号逐条施加一次并复跑**：**M3–M11 · M15–M19 · M22 · M25–M29**
      —— **全部必须打红**，未打红的**就地补断言并登记为新的 M 编号**
- 🔴 **[未做 · Deferred]** `python3 -m pytest tests/unit -q` 只增不减；`ruff check agenerp tests/unit …` exit 0
- 🔴 **[未做 · Deferred]** `module-boundaries.md` §7.14 落地（含 D-下-1/2/3/4 与被否决的备选、残余风险），
      并**逐字登记**「**外部输入的 `question` 未经边界标记**」这条残余
      及其重开事件（**当出现第二个非本仓的调用方，或当 `question` 开始被落盘/转发时**）
- 🔴 **[未做 · Deferred]** `docs/logs/` 更新

### Phase 4 — 承载面 app 源码进 git + ⌘K（**不激活**）

Status: deferred-but-adjudicated（**由 Phase 1 的 H1 实测中止**）

> ⚠️ **本 phase 一行代码都没写。** Phase 1 实测 `sid` 带 `HttpOnly`（H1 不吻合），
> 触发本 plan Phase 1 Exit Criteria 第 4 条**起草期写死**的停机分支：
> 「Phase 2 跑完就停，**Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**」。
> 重开事件逐字：**`sid` 接缝被重新裁定（由人或一个新 plan）**。
> 下面每一格都**不是复选框**，而是 `🔴 [未做 · Deferred]` 标记 —— 按 `00-plan-authoring-and-execution-guide.md`
> 「When Executing」第 8 条逐字「If an item cannot be completed, move it to `Deferred But Adjudicated` …
> **Do not leave it unchecked in the execution list**」，已 Deferred 的项不留在执行清单里当未勾选项。
> ⚠️ **这不是勾上，更不是声称做过** —— 本 phase 一格都没做，定界见 §11 第一条。
> 定界与理由见 `docs/architecture/module-boundaries.md` §7.14 与 §11「Deferred But Adjudicated」。

Targets: `apps/agenerp_desk/**`（新建）· `tests/unit/test_desk_app_package.py`（新建）
Skill: `development-wisdom-gate-prompt.md`（自查）
Item Types: `Add | Decision | Proof`
Prereqs: Phase 3 完成（JS 要打的地址与协议由 Phase 3 定死）

- 🔴 **[未做 · Deferred]** **Decision D-下-5 · 「Desk 原样保留」怎么读**
      - `system-baseline.md` §4 三端模型逐字「① 系统管理端 …… 载体 **Desk 原样保留**」。
        本 plan 的读法：侧边栏是**经官方 `app_include_js` 钩子的叠加层**，
        **不改 Desk 的任何页面、表单、DocType、权限、Workflow**；Desk 自身行为一字未变。
      - 备选读法「任何往 Desk 加东西都违反它」→ **否决**：那样 P1.8 这一行 WBS 本身就自相矛盾
        （WBS §4 P1.8 逐字要求「Agent 侧边栏**嵌 Desk**」），且 D-10 已把
        「代码进 git + `install-app` + 重启」这扇门判为**构建期**、正当。
      - 处置：**只在 §7.14 记这次重读，不改写 §4 任何一行**（`docs/architecture/` 非红线，
        但改「三端模型」这种骨架句属产品口径变更，应由人拍板 —— 本 plan 不代改）。
      - 残余风险：若人读 §4 为「一个像素都不许加」，本 plan 的承载面选型作废、回到 D1 的翻案条件①。
      - Skill: `development-wisdom-gate-prompt.md`
- 🔴 **[未做 · Deferred]** **Add** 最小 Frappe app 骨架，**只放跑得起来所必需的文件**：
      `apps/agenerp_desk/setup.py`（或 `pyproject.toml`）· `apps/agenerp_desk/requirements.txt`（空）·
      `apps/agenerp_desk/agenerp_desk/__init__.py`（`__version__`）·
      `apps/agenerp_desk/agenerp_desk/hooks.py`（`app_name` / `app_include_js`）·
      `apps/agenerp_desk/agenerp_desk/modules.txt` · `apps/agenerp_desk/agenerp_desk/patches.txt`（空）·
      `apps/agenerp_desk/agenerp_desk/public/js/agenerp_sidebar.js` ·
      `apps/agenerp_desk/README.md`（**第一行逐字写明：本目录不是 bench 的 `apps/`，
      本仓从未把它装进任何站点**；其后写激活命令与回滚命令原文，并指向 `STATE.md` §3 那条 `[open]`）
      - ⚠️ **零 DocType、零 fixture、零 `hooks` 里的服务端钩子**（不挂 `doc_events` /
        `scheduler_events` / `override_whitelisted_methods`）——
        app 里**唯一**的东西是一个前端 JS 与它的注册。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `agenerp_sidebar.js`：
      ① ⌘K（macOS `metaKey`）/ Ctrl+K（其它平台）唤起，且**在输入框内不劫持**；
      ② 从 `frappe.get_route()` / `cur_frm` 取 `{doctype, name}`，**取不到就提示「请在单据页上使用」
      并不发请求**（不发一个空 `{doctype,name}` 让服务端去 404）；
      ③ 用 `frappe.get_cookie("sid")` 取 `sid`，放进 `X-Frappe-Sid` 头（**不是 cookie** ——
      跨端口的 cookie 行为不在本 plan 的实测范围内，显式头是可判定的）；
      ④ `fetch("http://127.0.0.1:17801/explain", {method:"POST", headers:{"Content-Type":"application/json", …}})`
      —— 自定义头 + JSON 类型**强制预检**，配 Phase 3 的 `Origin` 校验；
      ⑤ 把答案渲染进一个侧边浮层，**不改 Desk 任何既有 DOM 节点**（只 append 一个自有容器）。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof** `tests/unit/test_desk_app_package.py`（**纯静态扫描，零站点、零浏览器**）：
      ① **D3⑥**：递归扫 `apps/agenerp_desk/**`，**没有任何** `.json` 的 `doctype` 字段等于
        `Client Script` / `Server Script`，`hooks.py` 里**没有** `fixtures` 声明；
        **变异验证**：塞一个 `client_script` fixture 进去 → 该判据必须红；
      ② `hooks.py` 的 `app_include_js` 每一项都指向 `apps/agenerp_desk/**` 下**真实存在**的文件；
      ③ **H10 跨文件一致性**：从 JS 里解析出的 URL 与 `agenerp/serve/service.py` 的
        `BIND_HOST` / `DEFAULT_PORT` **逐字相同**；**变异验证**：改任一侧的端口 → 必须红；
      ④ JS 里**出现** ⌘K 的绑定（`metaKey`/`ctrlKey` + `"k"`）且**不出现** `0.0.0.0`；
      ⑤ JS 里**不出现**任何硬编码凭据（扫 `password` / `api_key` / `secret` / `token` 字面量）；
      ⑥ app 的 `hooks.py` 里**不出现**服务端钩子键（`doc_events` / `scheduler_events` /
        `override_whitelisted_methods` / `on_session_creation`）——**变异验证**：加一个 → 必须红
      - Skill: `none`

Exit Criteria:

- 🔴 **[未做 · Deferred]** app 源码进 git，**且站点上一个字都没装**（自查：`bench --site frontend list-apps` 前后一致，
      `sites/apps.txt` 未被写；两条都是**只读**命令）
- 🔴 **[未做 · Deferred]** 六条判据全绿，三条变异逐条打红
- 🔴 **[未做 · Deferred]** `apps/agenerp_desk/README.md` 里激活命令与回滚命令**逐字**照抄 `STATE.md` §3
      `[open] 2026-08-25T02:10Z` 第一条（**不重新编一套**）
- 🔴 **[未做 · Deferred]** `python3 -m pytest tests/unit -q` 只增不减
- 🔴 **[未做 · Deferred]** `docs/logs/` 更新

### Phase 5 — 活跑 + `tests/ui/test_sidebar.py` 断言体 + 交接

Status: deferred-but-adjudicated（**由 Phase 1 的 H1 实测中止**）

> ⚠️ **本 phase 一行代码都没写。** Phase 1 实测 `sid` 带 `HttpOnly`（H1 不吻合），
> 触发本 plan Phase 1 Exit Criteria 第 4 条**起草期写死**的停机分支：
> 「Phase 2 跑完就停，**Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**」。
> 重开事件逐字：**`sid` 接缝被重新裁定（由人或一个新 plan）**。
> 下面每一格都**不是复选框**，而是 `🔴 [未做 · Deferred]` 标记 —— 按 `00-plan-authoring-and-execution-guide.md`
> 「When Executing」第 8 条逐字「If an item cannot be completed, move it to `Deferred But Adjudicated` …
> **Do not leave it unchecked in the execution list**」，已 Deferred 的项不留在执行清单里当未勾选项。
> ⚠️ **这不是勾上，更不是声称做过** —— 本 phase 一格都没做，定界见 §11 第一条。
> 定界与理由见 `docs/architecture/module-boundaries.md` §7.14 与 §11「Deferred But Adjudicated」。

Targets: `tests/unit/test_sidebar_body.py`（新建，🔴 断言体）· `docs/evidence/p1-sidebar/`（新建）·
`docs/architecture/module-boundaries.md` §7.14 · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/2026/08-25.md`
Skill: `none`
Item Types: `Proof | Follow-up`
Prereqs（**逐项拆开，不是一个大前置**）：
Phase 3、Phase 4 完成 · **活跑一 / 活跑二需要 LLM 凭据**（缺了就把这两跑记成 blocked，不伪造数）·
**活跑三与「坏输入活打」不需要 LLM 凭据**（它们在到达 `explain()` 之前就返回了），
因此**即使 LLM 凭据缺席，这两项照跑照记**

- 🔴 **[未做 · Deferred]** **Proof · 活跑一**（Administrator 的**真 `sid`**，经服务面走完整条路）：
      起 `python3 -m agenerp.serve` → 用 Phase 1 那条 `login` 换 `sid` →
      `curl -X POST http://127.0.0.1:17801/explain -H "Origin: http://127.0.0.1:18080"
      -H "X-Frappe-Sid: …" -d '{"doctype":"Sales Order","name":"<固定测例单号>","question":"<题>"}'`
      → 轨迹落 `docs/evidence/p1-sidebar/live-run-01.json` → 回填 **H5**
      - ⚠️ **一跑不是分布**，且**不与 `p1-explain/` 45,195 · `p1-cost/` 58,579 ·
        `p1-immediate/` 任何数作优劣比较**（D-16）。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof · 活跑二**（同题、**只换 `name`**）→ 回填 **H6**（差分，D3③ 的活端点侧）
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof · 活跑三**（受限身份「车间工人」的真 `sid`，**只打到身份这一层**，
      不跑完整解释）：对它**读不到**的 DocType 发一次 → 回 **403 `not-permitted`**，
      且**响应体里的 `user` 字段就是那个工人的用户名** → 回填 **H3** 的活端点侧。
      ⚠️ 为此 D-下-4 的 401 / 403 / 404 三类错误体**都要带 `user` 字段**
      （`sid` 解析成功时填用户名，失败时填 `null`）—— 否则「服务面认出的是谁」在活端点上
      **没有任何可观测量**，D3⑦ 的真证据就只剩假站点上的同义反复
      - ⚠️ 只打身份层是**刻意**的：跑第二次完整解释是纯成本，本 plan 没有成本工作（D-18/D-16）。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof · 坏输入活打**：D-下-4 那张表的**十一格逐条**各打一次真请求，逐条记状态码与
      `error` 标识（**外加 `Access-Control-Allow-Origin` 在不在**）→ 回填 **H7**。
      两格的打法起草期先写清：**预检两格**用 `curl -X OPTIONS -H "Origin: …"`；
      **`internal-error` 那格**用「把 `AGENERP_SITE_URL` 临时指到一个不存在的端口」制造站点侧失败
      （**不改任何产品代码**），断言回 500 `internal-error` 且体内搜不到站点异常原文。
      ⚠️ **这一格的 `curl` 必须把 `Origin` 同步改成那个新 base url** —— 按 D-下-3，
      允许的 `Origin` 是从 `default_base_url()` 推出来的，不改就会先撞 `bad-origin` 403、
      **根本走不到 500**（这也是「`Origin` 与站点基址同源配置」这个设计的一处已知代价，照实记）
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `tests/unit/test_sidebar_body.py` —— WBS §4 P1.8 那条验收件的**断言体**，分两节：
      **§A 承载面注入**（需 app 已激活：`GET /app` 的 HTML 里出现本 app 的 bundle 路径，
      且该 bundle 取回的 JS 里出现 ⌘K 绑定与那个 `127.0.0.1:17801`）·
      **§B 解释端点**（服务面起着时：真 `sid` → 200 且答案里有单据唯一值；伪造 `sid` → 401）。
      文件头写**加载片段与交接说明**，逐字含三条先例提醒：
      ① **basename 必须与目标文件不同**（`tests/` 无 `__init__.py`，同名 basename 会让
        `pytest` 整轮 `import file mismatch`）；
      ② 加载器**必须先注册进 `sys.modules` 再 `exec_module`**
        （`tests/unit/explain_fakes.py` 的 `load_repo_module` 可直接照抄）；
      ③ **§A 在 app 未激活时按构造为红** —— 人加载它之前必须先处置激活那条 `[open]`。
      - ⚠️ **本 plan 不创建 `tests/ui/`**（§1.4），也**不声称** WBS §4 P1.8 的验收已满足。
      - ⚠️ 本文件自身在 `tests/unit` 下**必须全绿**：§A/§B 的断言体是**函数**，
        不在 `tests/unit` 这一轮被调用（只被人加载的那份门禁调用），
        判据形态照抄 `tests/unit/test_explain_cost_accounting_body.py` 的 §A/§B 分节口径。
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Add** `docs/evidence/p1-sidebar/README.md`：三跑的口径、**没证明什么**、
      逐字「**这是每种一跑，不是分布**」「**⌘K 在真实浏览器里的行为本 plan 没有任何证据**」
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Follow-up**：`STATE.md` §3 **追加**一条 needs-human（**只追加**，红线 5），逐条含：
      ① `tests/ui/test_sidebar.py` 与 CI 第 ⑦ 步的 `COVERED` 需人一并处置（§1.4 的双重理由）；
      ② 断言体已交付在 `tests/unit/test_sidebar_body.py`，加载片段与三条提醒在文件头；
      ③ 激活那条 `[open] 2026-08-25T02:10Z` **不因本 plan 落地而消失**，本 plan 不代人处置；
      ④ 本 plan 的三跑口径与「没证明什么」；
      ⑤ **本行只追加，不改写本节任何已有行**
      - Skill: `none`
- 🔴 **[未做 · Deferred]** **Proof · 变异自查 M1–M29**（见下表），逐条施加→复跑→还原，**逐条记红在哪条断言上**；
      有绿的就地补断言并登记为新 M 编号
      - Skill: `none`

#### 变异自查清单（起草期写死）

| # | 变异 | 预期打红的判据 |
|---|---|---|
| M1 | `_headers()` 不发 `Cookie` | Phase 2 ① |
| M2 | `sid` 模式下仍打 `/api/method/login` | Phase 2 ③ |
| M3 | `sid` 无效时回退 `client_from_env` | Phase 3 ⑦ 反测 |
| M4 | `resolve_user` 只看状态码、不看 `Guest` | Phase 3 ⑦ |
| M5 | `BIND_HOST` 改成 `0.0.0.0` | Phase 3 ④ 静态 + 运行期两条 |
| M6 | `Origin` 校验整段删掉 | Phase 3 ④ 四例 |
| M7 | `Origin` 校验放行 `*` | Phase 3 ④ 非回环那例 |
| M8 | 服务面忽略 `name`，永远取同一份单据 | Phase 3 ③ 差分 |
| M9 | 请求体多余键**静默忽略**而不是 400 | Phase 3 ⑤ `unexpected-field` |
| M10 | `not-permitted` 与 `document-not-found` 合并成一个码 | Phase 3 ⑤ 两格 |
| M11 | `question` 长度上限取消 | Phase 3 ⑤ `question-too-long` |
| M12 | app 里塞一个 `client_script` fixture | Phase 4 ① |
| M13 | JS 的端口改掉、服务面不改 | Phase 4 ③ 跨文件一致性 |
| M14 | `hooks.py` 加一个 `doc_events` | Phase 4 ⑥ |
| M15 | 删掉 `OPTIONS` 分支（不答预检） | Phase 3 ⑧ 第一例 |
| M16 | 预检对非回环 `Origin` 也回 `Allow-*` 头 | Phase 3 ⑧ 第二组 |
| M17 | 把站点的异常原文原样塞进 500 的响应体 | Phase 3 ⑨ 第二条 |
| M18 | 不覆写 `log_message`（用默认实现） | Phase 3 ⑨ 访问日志那条 |
| M19 | 在 `agenerp/serve/` 里 import 一次 `client_from_env` | Phase 3 ⑩ |
| M20 | `client_from_sid` 也读一次 `AGENERP_ADMIN_PASSWORD` 当兜底 | **Phase 2 ⑧** + Phase 3 ⑩ |
| M21 | `SiteError` 的消息里带上请求头 | Phase 2 ⑥ |
| M22 | 服务面对 `AGENERP_SITE_URL` 指到非回环时**照常启动** | Phase 3 ④ 拒绝启动那条 |
| M23 | `sid` 为空串时静默当成"没给"而不是报错 | Phase 2 ⑤ |
| M24 | 给 `SiteClient` 加一个未登记的公开写方法 | Phase 2 ⑦（登记面判据） |
| M25 | `assemble(role=...)` 写死成 `"Administrator"` | Phase 3 D-下-2 的取值判据 |
| M26 | 把判定顺序里的 `Origin` 与 `sid` 对调 | Phase 3 ⑤ 的两条顺序判据 |
| M27 | catch-all 路径（`GET /`、`POST /anything`）回 200 而不是 404 | Phase 3 ① |
| M28 | `empty-question` 分支删掉（空问题照样往下走） | Phase 3 ⑤ `empty-question` |
| M29 | 只给 200 加 `Access-Control-Allow-Origin`，错误码不加 | Phase 3 ⑧ 第五条 |

Exit Criteria:

- 🔴 **[未做 · Deferred]** H1–H11 十一格「实际」列**逐条**已填，预测列**一个字未改**
- 🔴 **[未做 · Deferred]** M1–M29 逐条有红/绿记录，且**逐条指名是哪一条断言红的**；无一条留在绿
- 🔴 **[未做 · Deferred]** **六条**验证命令逐条跑过并记退出码（§10）
- 🔴 **[未做 · Deferred]** `module-boundaries.md` §7.14 落地；`docs/evidence/p1-sidebar/` 落盘
- 🔴 **[未做 · Deferred]** `STATE.md` §3 只追加（判据：逐行子序列检查，**不用 `grep '^-[^-]'`** ——
      那条 grep 对「删掉一整条 bullet」是盲的，`2026-08-24-2311-1` 的 Closure 已实证）
- 🔴 **[未做 · Deferred]** `docs/logs/2026/08-25.md` 更新

## 8. 风险

- **R1 · 本 plan 交不出 WBS §4 P1.8 的验收命令。** 那条命令是
  `pytest -m live tests/ui/test_sidebar.py` 退 0，它同时要求**两件本 plan 做不到的事**：
  ① app 已激活（风险档 L3 强制人批，`STATE.md` §3 `[open] 2026-08-25T02:10Z`）；
  ② `tests/ui/` 存在（会打红 CI 第 ⑦ 步，修它属红线 2）。
  ⚠️ **这一条刻意不写成 §6 的假设** —— 「本 plan 不跑激活 ⇒ 交不出退出码」是本 plan 自己的
  Non-Goals 1 的同义反复，**恒真、判不出真假**，放进假设表会稀释那张表的证伪力。
  **处置：照实说，不粉饰、不改判据、不改 WBS。** 本 plan 的 Closure 逐字声明
  「未创建 `tests/ui/test_sidebar.py`、未声称满足那条验收」，交接见 Phase 5。
  ⚠️ 这也意味着**工作项 10 在 2 个 plan 内交不出 WBS 验收** —— 那笔账
  `STATE.md` §3 已记（两个出口都只有人能选：批准激活，或在 `02-WBS.md` 拆行），
  **本 plan 不重复登记、也不代人选**。
- **R2 · 承载面从未被真正装过。** D1 的残余风险第一条原样继承：
  H2b 的「不发 DDL」是**读源码**得出的，不是实测；真装那一次可能撞上读不出来的东西。
  本 plan 交付的 app 是**零 DocType、零 fixture、零服务端钩子**，把那次撞上的面积压到最小，
  但**压小不等于测过**。⚠️ 另照实指一句（**不重复登记**，出处 `STATE.md` §3 `[open] 2026-08-25T02:10Z`
  第一条）：`install-app` **确实还会写** `Module Def` / `Installed Applications` / `Portal Settings` /
  `Patch Log` / `Scheduled Job Type` / 全局 `installed_apps` 多类行，而**本仓没有删除任意站点文档的手段**
  ⇒ **回滚只能由人在 Desk 里手删，或 `docker compose down -v` 冷起丢掉整站数据**。
- **R3 · `sid` 是明文短期凭据，在浏览器 → 本机服务 → 站点之间传三段。**
  缓解：不落盘、不进日志、不进异常消息（Phase 2 判据⑥ 钉住第三条）。
  **不缓解的**：本机上的其它进程能直接打 `127.0.0.1:17801`；`Origin` 挡浏览器跨站，不挡本机进程。
  照实写进 §7.14，**不说成「已隔离」**。
- **R4 · ⌘K 的真实浏览器行为本 plan 没有任何证据。** Non-Goals 5 已定界（不引浏览器驱动）。
  能主张的只有「那段 JS 里有这个绑定、它进了 git、它的地址与服务面一致」。
  **重开事件**：人批准激活之后的第一次真人试用，或引入浏览器驱动的 plan。
- **R5 · `agenerp/site.py` 是全仓最热的模块之一。** 本 plan 动它的**认证面**。
  缓解：改动只加一条互斥模式、不碰既有两条路径；`tests/unit/test_site_client.py` 与
  `tests/contracts` / `tests/tools` / `tests/context` **四个面逐字不变**是 Exit Criteria（H11）。
  ⚠️ **`tests/routing` 不在「逐字不变」之列** —— 它按 `agenerp/**/*.py` 全量参数化
  （`tests/routing/test_adapter.py:485`），新增 4 个模块必然 164 → 168，**那是正常增长不是回归**。
- **R6 · D2 的 (i) 与 (iii) 之争在本 plan 被读成「语义 vs 实现」。**
  若评审或人认为这是把 (ii) 从后门放回来，**停机交人**：判别方式是**三条合取** ——
  Phase 3 的两条**行为反测**（`sid` 失效不许回退管理员 · 全程零 `Authorization` 零 `login`）
  **加** Phase 3 的**构造判据 ⑩** 与 Phase 2 的 **⑧**（代码里根本没有回退所需的零件）。
  行为反测判「这一次没回退」，构造判据判「压根回退不了」，**两种都要**。
  **三条都绿，才不是 (ii)；任一条红，就是。**
- **R7 · 本 plan 面积大（五个 phase、四个新模块 + 一个新 app）。**
  但它只有**一个结果面**：「浏览器里对当前单据发起一次解释」。
  拆成两个 plan 会撞 `02-WBS.md` 表规 3（一个工作项 1–2 个 plan，工作项 10 已用满），
  **拆行只有人能做**。→ 处置是**分阶段可停**：Phase 1 的 H1 不吻合就**停在 Phase 2 结束、Phase 3/4/5 整体转 Deferred**
  （逐字见 Phase 1 Exit Criteria 第 4 条，**不许只停 Phase 3 而让 Phase 4 继续**）；
  Phase 5 活跑 blocked 就照实记 blocked，**不伪造数**。

- **R8 · 外部输入的 `question` 不经任何边界标记。** 实读：`agenerp/context/immediate.py:123`
  的 `wrap_free_text` **只包 `fields`**；`agenerp/explain/loop.py:356` 把 `question` **原样**
  `append` 进 `messages`。本 plan 之后它第一次变成**浏览器来的外部输入**。
  **本 plan 不改这一点**（改法要动 P1.4 的消息装配面，不在 Targets 里），也**不假装它被包过**（B4）。
  今天挡它的只有 4000 字符上限与「② 作答前门禁永远开着」，**这两条都不是注入防线**。
  重开事件：**出现第二个非本仓的调用方，或 `question` 开始被落盘 / 转发。**

## 9. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理 `a24ba58161a2dc060`，
  fresh session，不带起草上下文）because 四条 BLOCKING：
  **B1** 跨源预检（CORS preflight）全篇未处置——JS 用自定义头 + JSON 类型必定触发 `OPTIONS` 预检，
  而 D-下-4 把 `OPTIONS /explain` 判进 `no-such-endpoint`（404，无 `Allow-*` 头）⇒
  浏览器一次 `POST` 都发不出去，**而所有 `tests/unit` 判据照样全绿**（它们不经浏览器）；
  **B2** H11 的「`tests/routing` 164 逐字不变」按构造为假——`tests/routing/test_adapter.py:485`
  按 `agenerp/**/*.py` 全量参数化，新增 4 个模块必然 164 → 168；
  **B3** Phase 1 的停机分支「Phase 2/4 可继续」与 Phase 4 自己的 Prereqs（「Phase 3 完成」）直接冲突，
  且会产出两个各自关不掉 D3 的残件；
  **B4**「`question` 与字段表两处都走 `wrap_free_text`」是假的——`immediate.py:123` 只包 `fields`，
  `loop.py:356` 把 `question` 原样入 `messages`。
  另七条 MAJOR（预检变异缺口 · 缺 `internal-error` 那一格 · §5 的 `seedusers` 与 §5.1 自撞 ·
  Phase 5 前置把不需要 LLM 的两跑绑死 · §1.7 把 (iii) 的理由读松了一格 ·
  变异清单 M1–M14 只覆盖 Phase 2 七条判据里的两条 · 缺「`agenerp/serve/**` 零凭据零件」的构造判据）
  与六条 MINOR。
- Independent draft review iteration 2: **needs revision（1 BLOCKING + 4 MAJOR + 5 MINOR，全部是同一个形状：
  「改了判定表/判据，没改与之配套的实现规格、Exit Criteria、计数引用和风险节」）**
  （同一独立子代理 `a24ba58161a2dc060`，fresh 上下文重读全文）after 上述 BLOCKING 四条 +
  MAJOR 七条 + MINOR 六条**逐条已改**：加预检两格与 `Access-Control-Max-Age` 并把预检写进判定顺序 ·
  加 `internal-error` 与全部错误体的 `user` 字段 · H11 改成「四个面逐字不变 + `tests/routing` 164 → 168」·
  Phase 1 停机分支改成「Phase 3/4/5 整体转 Deferred」· `question` 那条 Proof 改成只判字段表并新立 R8 ·
  `seedusers` 改成无条件不跑 · Phase 5 前置逐项拆开 · §1.7 自我更正 ·
  变异清单 M1–M14 扩到 **M1–M29** · 新增 Phase 3 判据 ⑧/⑨/⑩（预检四例 / 输出零 `sid` 含 `log_message` /
  `agenerp/serve/**` 零凭据零件）· D-下-2 钉死 `assemble()` 六个参数的取值 · 删掉恒真的 H12 · 六条 MINOR 逐条改
- Independent draft review iteration 2 的十条修订**逐条已改**：
  **BLOCKING** `service.py` 的「流程逐字为」补上 `OPTIONS` 预检那一步并写明「就地返回、不再往下走」
  （此前判定顺序改了、实现规格没改 —— 同一件事两个落点只改一个）·
  **MAJOR** R7 残留的「停在 Phase 2/4」改准 · Phase 3 Exit Criteria 补 ⑧/⑨/⑩ 三条判据、
  「四条变异」改成本 phase 名下的 M 编号逐条（M3–M11 · M15–M19 · M22 · M25–M29）·
  「凡 `Origin` 过校验的响应都带 `Access-Control-Allow-Origin`（`bad-origin` 两格例外）」+ Proof ⑧ 第五条 + **M29** ·
  ⑩ 的扫描面扩到 `client_from_sid` 函数体、黑名单补三个常量标识符、Phase 2 补判据 ⑧、M20 改指它 ·
  **MINOR** 「坏输入四类/八格」→「十一格逐条」并写清预检两格与 `internal-error` 那格怎么活打 ·
  §1.7 节标题不再断言「凭据不在容器里」、§1.1 指向更正后的理由 · R6 的判别方式改成「两条行为反测 + 构造判据」三条合取 ·
  「三个头」→「四个头」、「五个取值」→「六个」、R8 移到 R7 之后 · Phase 1 Exit Criteria 允许 H3 记 blocked。
  改完按评审建议做了一次机械自查：对 `Phase 2/4` / `八格` / `坏输入四类` / `四条变异` / `两条反测` /
  `三个头` / `五个取值` 七个串各 grep 一次，**除 Draft Review Record 里对评审意见的引述外零残留**。
- Independent draft review iteration 3: **acceptable as-is**（同一独立子代理 `a24ba58161a2dc060`，
  重读全部 869 行，**并独立复跑了起草者的七串机械自查，未采信起草者的结果**）——
  **零 BLOCKING、零 MAJOR**；四条 BLOCKING 与十一条 MAJOR 全部关闭，无新引入的矛盾。
  审计器逐条验到实处的五点（不是「看有没有那句话」）：`service.py` 的六步流程与判定顺序**逐字同构**
  且写了「就地返回、不再往下走」· Proof ⑧ 第五条**正确把 `bad-origin` 两格排除在外**
  （一刀切给所有响应加 `Allow-Origin` 会把坏来源放进来）· Proof ⑩ 与 Phase 2 ⑧ 列的八个标识符
  经 `agenerp/site.py:55-61` / `:402` / `:414` 复核**全部真实存在** · §10 ④⑤ 给每条写了预期数与理由 ·
  `tests/routing` 164 → 168 的算式经**实测复核**（`agenerp/**/*.py` 53 + 4 = 57 ⇒ 165 → 169 collected）。
  **三条 MINOR 已随本次回填一并改掉**：§10「五条命令」→「六条」· Phase 2 Exit Criteria「七条判据」→「八条」·
  Phase 5「`internal-error` 活打」补上「`curl` 的 `Origin` 必须同步改成那个新 base url，
  否则先撞 `bad-origin` 403 走不到 500」。
  审计器同时记了一条**不必改的观察**：Phase 2 的 Exit Criteria 未像 Phase 3 那样枚举本 phase 名下的
  M 编号（M1/M2/M20/M21/M23/M24），但 Phase 5 的「M1–M29 逐条有红/绿记录」是完整兜底，不构成缺口。
  → **共识达成，`Plan Status` 由 `draft` 转 `active`。**


## 10. Closure Gates

- [x] **in-scope behavior is complete —— 按停机后的范围读，且逐字说清范围被谁缩小的**：
      Phase 1（只读探测）与 Phase 2（`sid` 互斥认证模式 + 20 条判据）**全部落地并全绿**；
      Phase 3 / 4 / 5 **整体转 `Deferred But Adjudicated`**（§11 第一条），由 **Phase 1 Exit Criteria 第 4 条
      起草期写死的停机分支**触发，**不是执行期缩范围**。
      ⚠️ **本 plan 因此不主张 P1.8 已交付。**
- [x] relevant docs are aligned（`module-boundaries.md` §7.14 落地；§11.7 / §7.13 / `system-baseline.md` §4
      **只补指针不改写**；`docs/logs/2026/08-25.md` 有条目）
      —— 自证：`git diff --numstat docs/architecture/module-boundaries.md` → **`121  0`**（纯插入，删除列为 0）；
      `git status --porcelain -- docs/architecture/system-baseline.md` → **无输出**。
      ⚠️ **`D-下-5`（「Desk 原样保留」怎么读）未做** —— 它是 Phase 4 的 Decision，随 Phase 4 一起 Deferred；
      §7.14 因此**没有**记那次重读，`system-baseline.md` §4 也一个字未动。
- [x] verification has run —— **六条命令逐条记原文与退出码**（结果见下方逐条注，
      完整表在 `docs/logs/2026/08-25.md` 本轮条目）：
      ① `python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q`
      → **exit 0**（`门禁 11 项：预期红 0，绿 11，跳过 0` + 520 → **540 passed**，只增不减）
      ② `python3 -m pytest tests/contracts -q` → **exit 0**（`151 passed`，逐字不变）
      ③ `python3 -m pytest tests/tools -q` → **exit 0**（`81 passed, 12 skipped`，逐字不变）
      ④ `python3 -m pytest tests/routing -q` → **exit 0**（**实测 `164 passed, 1 skipped`，不是预期的 168**）
      ⚠️ **H11 的算式没错，错的是前提**：那 4 个 `agenerp/serve/**` 模块随 Phase 3 一起没建，
      `find agenerp -name "*.py" | wc -l` 实测 **53**（与起草期复核值逐字相同）。**不记「不吻合」，记「前提不成立」。**
      ⑤ `python3 -m pytest tests/context -q` → **exit 0**（`53 passed`，逐字不变 —— 本 plan 一个字不改 `agenerp/context/**`）
      ⑥ `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
      → **exit 0**（`All checks passed!`）。⚠️ ⑥ 的作用域**不含 `apps/`** —— 本轮 `apps/` **根本不存在**（Phase 4 Deferred）
- [x] scoped verification is not conflated with full verification ——
      **verification scope limited**：未跑 `pytest tests -q -m "not live"`，未过 CI 服务端复跑，
      `tests/gates` 的 live 语义不在本轮范围内。**六条命令的绿不等于全绿。**
- [x] **no in-scope item downgraded to deferred/follow-up —— 这一格必须逐字读清楚，不许含糊**：
      Phase 3 / 4 / 5 **确实**被整体转成 `Deferred But Adjudicated`，
      但那**不是执行期把做不动的东西降级**，而是**起草期就写死的分支被实测触发**
      （Phase 1 Exit Criteria 第 4 条，逐字含「不许只停 Phase 3 而让 Phase 4 继续」）。
      判别方式：重开事件是**起草期原文**（「`sid` 接缝被重新裁定」），不是执行期现编的措辞。
      Phase 1 / Phase 2 名下**零降级**，两个 phase 的 Exit Criteria 全 `[x]`。
- [x] independent draft review completed and recorded（§9，三轮，第三轮 `acceptable as-is`）
- [x] text consistency verified: status, phases, gates, and log all agree ——
      `Plan Status: deferred` · Phase 1/2 `completed` 且全 `[x]` · Phase 3/4/5 `deferred-but-adjudicated`
      且 36 格**全部是 `🔴 [未做 · Deferred]` 非复选框标记、零 `[x]`**
      （2026-08-25 关闭审计按 guide「When Executing」第 8 条把它们移出执行清单的复选框形态，
      **改的是记法不是结论** —— 勾成 `[x]` 才是伪造，本 plan 一格都没勾）· §10 本节 · `docs/logs/2026/08-25.md` 与
      `docs/masterplan/STATE.md` `2026-08-25T04:05Z` 两处口径**逐字一致**（都写「被实测中止」，不写「已交付」）。
- [x] **closure audit was independent —— 2026-08-25 由独立关闭审计子代理补做，非自证**。
      ⚠️ **审计的对象是「本 plan 停在 `deferred` 这件事成不成立」，不是「`completed` 成不成立」** ——
      本 plan 未主张 `completed`，独立审计**没有**、也**不许**把它改成 `completed`。
      审计器实读复核的四点与它的实读值见 `## Closure` 的 `Closure Audit Evidence`。
      起草期这一格原文是「本轮未做，照实留 `[ ]`」，现由那次审计**如实翻绿**。
- [x] closure evidence exists in files —— `docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md`（探测记录，零 `sid` 真值）·
      `docs/architecture/module-boundaries.md` §7.14 · `tests/unit/test_site_client_sid.py`（20 条）·
      `docs/logs/2026/08-25.md` · `docs/masterplan/STATE.md` `2026-08-25T04:05Z` 两条（纯追加）
- [x] **红线自证**：`git status --porcelain -- tests/gates/ .github/workflows/ missions/
      docs/masterplan/DECISIONS.md docker-compose.yml` → **无输出**；
      `docs/masterplan/STATE.md` 逐行子序列检查「只增不改」→ `git diff --numstat` 实测 **`21  0`**（删除列为 0）；
      `ls tests/ui` → **不存在**；`bench --site frontend list-apps` 探测前后**逐字一致**
- [x] **逐字声明**：本 plan **未创建** `tests/ui/test_sidebar.py`，
      **未声称**满足 `02-WBS.md` §4 P1.8 那条验收命令，**一次都没跑** `bench install-app`。
      ⚠️ **本轮还要多声明三条**（范围比起草期设想的更窄）：**未创建** `apps/agenerp_desk/**` ·
      **未创建** `agenerp/serve/**` · **未交付** `tests/unit/test_sidebar_body.py` 那份断言体。

## 11. Deferred But Adjudicated

### 🔴 Phase 3 / 4 / 5 整体：解释请求面 · 承载面 app + ⌘K · 活跑与断言体

- Classification: `blocked by a falsified design premise`（**本轮新增，执行期触发**）
- **触发它的是实测，不是判断**：Phase 1 实测 `POST /api/method/login` 回的
  `Set-Cookie: sid=…` **带 `HttpOnly`**（§6 **H1 预测「不带」**）。同批五个 cookie 里
  **只有 `sid` 带**（`system_user` / `full_name` / `user_id` / `user_image` 四个都不带）——
  这不是「Frappe 不设 `HttpOnly`」，是**它专门只对 `sid` 设**。
  ⇒ Phase 4 的 JS 用 `frappe.get_cookie("sid")` **按构造取不到值**，
  **D3⑦ 那条「浏览器读 `sid` → 放进 `X-Frappe-Sid` 头 → 转发给本机服务」的接缝不成立。**
- Why Not Blocking Closure: 处置**是起草期写死的**，不是执行期现编 ——
  Phase 1 Exit Criteria 第 4 条逐字：「Phase 2 跑完就停，**Phase 3 / 4 / 5 整体转
  `Deferred But Adjudicated`**」，并逐字禁止「只停 Phase 3 而让 Phase 4 继续」
  （那会产出「一条没有调用方的认证模式 + 一段取不到 `sid` 的 JS」两个各自关不掉 D3 的残件，
  还都进了 git —— 正是 Minimum Rule 4「一个 plan 一个结果面」要挡的形态）。
- Successor Required: `yes`。**重开事件逐字（起草期原文，未被下游改松）**：
  **`sid` 接缝被重新裁定（由人或一个新 plan）。**
  已记进 `docs/masterplan/STATE.md` §3 `[open] 2026-08-25T04:05Z`（只追加）。
- **重开后可直接复用的**：`agenerp/site.py` 的 `sid` 互斥认证模式与 `client_from_sid()`
  （20 条判据全绿，六条变异 M1/M2/M20/M21/M23/M24 逐条打红）。
  ⚠️ **它测的是 `SiteClient` 这一层，不是「服务面」** —— 服务面一行代码都没有；
  ⚠️ 它也**没有**在活站点上被验证过认得出人（全部 20 条走假传输）。
- **残余风险，照实登记，不预选方案**：本 plan **不替那次重新裁定挑接缝**。
  探测记录里那句「`sid` 只对自己设 `HttpOnly`」是**事实**，不是「所以应该改用 X」的论据 ——
  **本仓今天没有对任何替代接缝做过实测**，列一份候选清单等于把没测过的东西伪装成选项。
- ⚠️ **`Decision D-下-2` 随本条一起 Deferred，因此 `STATE.md` §3 `[open] 2026-08-25T00:35Z` 第 ① 项
  （① 层不查权限）本轮一点没关，仍然完全敞着。** 本 plan 是它点名的承接者，但没接上，照实记。
- ⚠️ **`Decision D-下-5`（「Desk 原样保留」怎么读）也随之未做** ——
  §7.14 因此**没有**记那次重读，`system-baseline.md` §4 一个字未动。

### 承载面的激活与 WBS 验收命令

- Classification: `watch-only residual`
- Why Not Blocking Closure: 越权动作只有人能做（风险档 L3，`STATE.md` §3 `[open] 2026-08-25T02:10Z`）。
  本 plan 把激活之外的一切都做完，激活那一步**面积压到最小**（零 DocType、零 fixture、零服务端钩子）。
- Successor Required: `yes`。重开事件：**人在 `STATE.md` §3 把那条 `open` 改成 `resolved`**
  （或人在 `02-WBS.md` 把 P1.8 拆行）。届时要做的三件事已写在
  `apps/agenerp_desk/README.md`：装 app → 加载 `tests/ui/test_sidebar.py` → 跑 WBS 那条命令。

### ⌘K 的真实浏览器行为

- Classification: `watch-only residual`
- Why Not Blocking Closure: 引浏览器驱动要装第三方依赖（Non-Goals 5），
  且在 app 未激活时**装了也没得跑**。
- Successor Required: `yes`。重开事件：**app 激活之后**，且出现一条需要判断
  「真实浏览器里按下 ⌘K 之后发生了什么」的具体缺陷或需求。

### ① 档的上下文预算与裁剪接入点

- Classification: `optimization candidate`（从 `2026-08-24-2311-1` §11 第二条**继承**）
- Why Not Blocking Closure: 那条的重开事件是**两个都要满足**：
  ① 承载面出现真实调用方（**本 plan 满足了这一半**）；
  ② P1.7 Deferred「成本的多次采样与分布」产出过一次实测分布（**今天仍未满足**）。
  D3 已裁定不发明数字（D-16）。
- Successor Required: `yes`。重开事件：**②那一半也满足的那一刻**。
  ⚠️ 继承来的触发条件**不许被下游改松**：本 plan 没有把它改写成更晚的条件。
  残余风险照实登记：**一张超大单据能把上下文撑爆，本仓不会抛一个说得清的异常。**

### 归因文本 / 答案质量的判据

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 判自由文本要先跑通 `tests/unit/test_answer_judging_fixture.py`
  的 24 条人工标注（roadmap 那一节逐字）。本 plan 判的是**结构化事实**
  （状态码 / 身份 / 同一性 / 差分），**不判答案对不对** —— 那一节明确不适用于结构化事实。
- Successor Required: `no`。重开事件：出现一条要判「侧边栏答得对不对」的工作项。

## Closure

Status Note: **本 plan 停在 `deferred`，不是 `completed`。**

Phase 1（只读探测）与 Phase 2（`sid` 互斥认证模式 + `client_from_sid()` + 20 条判据）
**已落地并全绿**；Phase 3 / 4 / 5 **整体转 `Deferred But Adjudicated`**（§11 第一条），
触发者是 Phase 1 的 **H1 实测不吻合**（`sid` 带 `HttpOnly`），处置依据是**起草期写死**的停机分支。

**本 plan 未交付 P1.8 本体**，逐条：无 `agenerp/serve/**` · 无 `apps/agenerp_desk/**` ·
无 ⌘K · 无侧边栏 UI · 无 `tests/ui/test_sidebar.py` · 无 `tests/unit/test_sidebar_body.py` ·
无 `docs/evidence/p1-sidebar/`。**`bench install-app` 一次没跑，`ls tests/ui` 不存在。**
**未声称满足 `02-WBS.md` §4 P1.8 的验收命令。**

六条验证命令**逐条 exit 0**（原文与输出见 §10 与 `docs/logs/2026/08-25.md`），
`tests/unit` **520 → 540 passed**（只增不减）。**verification scope limited**：
未跑 `pytest tests -q -m "not live"`，未过 CI 服务端复跑。

⚠️ **执行期两处偏离起草期原文，均已在 §10 / §7.14 / `STATE.md` 三处逐字记过**：
① 判据④「三种凭据两两互斥」**取窄成「`sid` ⊥ 另两者」**（起草期原文会打红 21 条既有判据，
与同一 plan 的 Exit Criteria「`test_site_client.py` 一个字未改」和 R5「不碰既有两条路径」直接相撞）；
② **H11 的 `tests/routing` 164 → 168 未发生**（前提不成立，不是算式错）。

Closure Audit Evidence:

- Auditor / Agent: **独立关闭审计子代理**（mission-driver `2026-08-24-203159-mission-driver` 的
  closure-audit 步，fresh session，**不带执行期上下文**，2026-08-25）。
  **审计标的逐字：「本 plan 停在 `deferred` 是否成立」**，不是「`completed` 是否成立」——
  审计器**未**把 `Plan Status` 改成 `completed`，因为 Phase 3/4/5 确实一格没做。
  审计器**未采信 plan 自报的任何数字**，逐条实跑复核（命令原文 + 退出码）：
  - **落地面实读**：`agenerp/site.py:197/203/208/224/385/405-406` 的 `sid` 互斥模式与 `:479-489`
    的 `client_from_sid()` **在仓里**；`python3 -m pytest tests/unit/test_site_client_sid.py -q`
    → **exit 0**（`20 passed`，与 plan 自报的 20 条逐字相同）。
  - **未落地面实读（反向证伪，四条各一次 `ls`）**：`agenerp/serve/` · `apps/` · `tests/ui/` ·
    `docs/evidence/p1-sidebar/` · `tests/unit/test_sidebar_body.py` · `tests/unit/test_explain_service.py`
    → **全部 `No such file or directory`**。⇒ Closure 里「未交付 P1.8 本体」那一串**逐条为真**，
    Phase 3/4/5 的 Deferred **不是把做过的东西说成没做，也不是把没做的说成做过**。
  - **六条验证命令独立复跑**：`python3 tools/gates/check_expected_red.py` → **exit 0** ·
    `python3 -m pytest tests/unit -q` → **`540 passed`** ·
    `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q`
    → **`449 passed, 13 skipped`**（= 151 + 81 + 164 + 53，skipped = 12 + 1，与 §10 ②③④⑤ 逐字相符）·
    `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
    → **`All checks passed!`**。
  - **红线自证独立复跑**：`git status --porcelain -- tests/gates/ .github/workflows/ missions/
    docs/masterplan/DECISIONS.md docker-compose.yml` → **无输出**；
    `git log --oneline -5 -- tests/gates .github/workflows docs/masterplan/DECISIONS.md`
    最近一次提交是 `6b07889`，**早于本 plan 的两个落地 sha（`5b675a3` / `7e7f517`）** ⇒ 本 plan 未动裁判面。
  - **审计器本轮改了三处，逐条都是「记法」不是「结论」**：
    ① 状态行的定界移出同一行（`PLAN_STATUS_RE` 此前把状态读成 `unknown`）；
    ② Phase 3/4/5 的 36 个 `- [ ]` 改成 `- 🔴 **[未做 · Deferred]**` 非复选框标记 ——
    依据是 guide「When Executing」第 8 条逐字「Do not leave it unchecked in the execution list」，
    **一格都没被勾成 `[x]`**；③ 本节与上面那条 Closure Gate 的回填。
  - **审计器实读到、但判为不阻塞关闭的一条**：`agenerp/site.py:485` 的 docstring 指向
    `tests/unit/test_explain_service.py` 判据⑩，而该文件随 Phase 3 一起不存在 ⇒ 那是一条**指向未来的悬空引用**。
    不阻塞的理由：它在 docstring 里，**不进任何运行路径、不进任何判据**，且 §11 第一条已逐字登记
    「重开后可直接复用的是 `SiteClient` 这一层，服务面一行代码都没有」。**已作为非阻塞 follow-up 登记在下方。**
  - **审计结论**：`deferred` 成立。**不批准 `completed`** —— 批它就是伪造 Phase 3/4/5 的证据。
- Evidence: 本轮的可复跑证据在文件里 ——
  `docs/analysis/2026-08-25-0119-desk-sid-identity-probe.md`（探测记录，**零 `sid` 真值**，
  已对两个 `sid` 的前 8 位各 grep 一次全仓无命中）·
  `docs/architecture/module-boundaries.md` §7.14（121 insertions / **0 deletions**）·
  `tests/unit/test_site_client_sid.py`（20 条，含六条变异的红点逐条记名）·
  `docs/masterplan/STATE.md` `2026-08-25T04:05Z` 证据行 + `[open]` 各一条（**21 insertions / 0 deletions**）。

Follow-up:

- **`agenerp/site.py:485` docstring 里的悬空引用**（关闭审计实读发现）：该行指向
  `tests/unit/test_explain_service.py` 判据⑩，而该文件随 Phase 3 一起未建。
  **非阻塞的判据**：它只在 docstring 里，**不进运行路径、不进任何判据**，改它一个字都不改行为。
  **触发条件（促成它进范围）**：`sid` 接缝被重新裁定、Phase 3 重开并真的建出 `agenerp/serve/**` 时，
  由那个 plan 顺手把这行对齐；**若那次裁定否掉了整个服务面，则改成删掉这句引用。**
- 除上一条外**无其它非阻塞 follow-up**。本轮真正的未竟项是 §11 第一条那个 `Deferred But Adjudicated`，
  它**是阻塞项**（阻塞 P1.8 本体），因此**不放在这里** —— 确认的缺陷与阻塞项不得伪装成 follow-up。
