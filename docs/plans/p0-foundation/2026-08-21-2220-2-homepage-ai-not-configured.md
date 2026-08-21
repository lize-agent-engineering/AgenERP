# 2026-08-21-2220-2 首页「AI 能力未配置」降级文案，以及让 CI 真跑 L2

> Plan Status: completed
> Mission: p0-foundation
> Work Item: 8. 零依赖启动进 CI（L2 慢门禁）—— **第二个（也是最后一个）plan：首页降级文案 + CI 真跑 L2**
> Last Reviewed: 2026-08-21
> Source: plan `2026-08-21-1634-2` 的 `Deferred But Adjudicated` 第一条（`Successor Required: yes`）·
>   `STATE.md` §3 P0.7 那条补充事实行逐字登记的「未做、也不由本 plan 做」第 ①
> Related: `2026-08-21-1022-1-zero-dep-boot-compose.md`（compose 落地）·
>   `2026-08-21-1634-2-compose-healthcheck-app-services.md`（healthy 可判定，本 plan 的 successor 契约出处）·
>   `2026-08-21-2220-1-schema-drift-orphan-columns.md`（同批次，执行顺序在前）
> Audit: required

## Current Baseline

以下每一条都是 2026-08-21 起草时在**活站点上实测**得来的。起草基线 sha **`3fed439`**。
⚠️ 起草过程中 HEAD 动过：人在 22:21:59 提交了 `3fed439`，**把 `STATE.md` §3 里最后三条 `[open]` 全部转成 `resolved`**
（实测 `grep -c "^- \[open\]" docs/masterplan/STATE.md` → `0`）。原草案把「CI 那半」排除在外的理由正是
「它卡在一条 §3 的 `[open]` 上」——**那条依据在起草时已经不成立**，草案评审逐字指出。本 plan 已据此把 CI 那半收回范围内。
栈以 `AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` 冷起（exit 0；
按 `system-baseline.md` §14.2 的收窄口径：**六个有探针的服务 healthy，三个 worker 只判 running**，
两个一次性容器 `Exited (0)`）。

**判据侧（红线内，一个字节都不动）**

`tests/gates/test_zero_dep_boot.py::test_homepage_states_ai_disabled_instead_of_crashing` 两条断言：

```
resp = compose_stack.http_get("/")
assert resp.status_code == 200
assert "AI 能力未配置" in resp.text
```

`compose_stack.http_get` 带 `Host: frontend` 头（`tests/gates/conftest.py`）。
该门禁**仍在** `tools/gates/expected-red.txt` 名单内。

**红因由本 plan 起草时在 `3fed439` 上亲自复跑坐实**：

```
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin \
python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line
→ exit 1 ; 1 failed, 2 passed in 0.40s
→ tests/gates/test_zero_dep_boot.py:37: AssertionError: 首页没有说明 AI 能力未配置——用户会以为产品坏了
```

失败原文里逐字带着 `Response(status_code=200, …)`——**这就是「第一条断言已经过」的直接证据**。
同一次运行里 `test_stack_boots_and_all_services_healthy` **是绿的**（`2 passed` 的其中一条）。

**实测：第一条断言今天就已经过，红的只有第二条**

```
curl -s -o /tmp/home.html -w "status=%{http_code} size=%{size_download}\n" \
  -H "Host: frontend" http://127.0.0.1:18080/
→ status=200 size=346536 ; <title>Login</title>
```

首页**既没有崩也没有白屏**，它是 ERPNext 的登录页（`Website Settings.home_page` 为 `None` 时的回退）。
所以本 plan 要补的不是「别崩」，而是「把 AI 能力状态说出来」——这一点起草时必须说穿，
否则执行会照着门禁的 docstring（「而不是 500 或空白」）去修一个并不存在的崩溃。

**实测：Web Page + `Website Settings.home_page` 这条路是通的（起草时已跑通并已还原）**

经 REST 建一条 `Web Page`（`route=agenerp-probe-home`、`published=1`、`content_type=HTML`、
`main_section_html` 含「AI 能力未配置」），再 `PUT Website Settings.home_page` 指向它：

```
curl -H "Host: frontend" http://127.0.0.1:18080/ → status=200，正文含「AI 能力未配置」
```

**门禁的两条断言都会过。** 随后已把 `home_page` 置回空并删掉那条 Web Page，
复验 `<title>Login</title>` 且「AI 能力未配置」出现 0 次——**站点已还原，本轮没有留下站点态**。

**AI 能力在栈里的现状**

`docker-compose.yml:48` 的 `x-ai-env` 锚点注入三个变量，全部空默认值：
`AGENERP_LLM_ENDPOINT` / `AGENERP_LLM_API_KEY` / `AGENERP_LLM_MODEL`。
该锚点被 `<<: *ai_env` 引用**四次**（`:165` backend、`:207` queue-short、`:217` queue-long、`:225` scheduler）——
原草案写「只进 `backend`」是错的，草案评审逐字纠正。
四处都只是 `environment` 注入，**不出现在任何 healthcheck / command 的成败路径上**
（`system-baseline.md` §14 规则 ②，判据是 `tests/unit/test_compose_zero_dep.py`）。
站点侧**没有任何东西读它们**——「AI 未配置」这件事此刻在站点上完全不可见。

仓根有一个 gitignored 的 `.env`，实测内容只有一行 `MISSION_DRIVER_HOME=tools/mission-driver`，
**不含任何 AI 变量**；但 compose 会读它做插值，所以「本机环境能改变门禁结果」这条路是通的
（下面 Phase 1 的 `Decision` ② 必须处理它）。

**compose 侧的既有硬判据（本 plan 改 compose 就必须同时满足，起草时逐条读过）**

`tests/unit/test_compose_zero_dep.py` 会扫原始文本：
每个 `${...}` 必须带 `:-` 默认值、不许 `${VAR:?}`、三个 AI 变量默认值必须是空串、
发布端口必须是字面 `127.0.0.1:` 开头的短语法、镜像 tag 不许浮动、不许顶层 `version:`。

**没有任何 bind mount（这条决定引导逻辑能怎么落盘）**

实测 `grep -n "\./" docker-compose.yml` **零命中**：所有服务只挂命名卷 `sites` / `logs`。
**仓内的脚本对容器不可见**——引导逻辑不能简单地写成 `tools/` 下一个文件然后指望 `bench` 跑得到它。

**CI 侧**

`.github/workflows/gates.yml` 现有 6 个 job：`gates-untouched` / `expected-red-ratchet` /
`gates-l1` / `masterplan-links` / `roadmap-parseable` / `loop-wiring`。**没有任何一个跑 docker**。
`gates-l1` 只 `pip install pytest` 后跑 `python3 tools/gates/check_expected_red.py`（默认环境，L2 恒红）。
默认环境下 `python3 tools/gates/check_expected_red.py` 实测 **exit 0**（「门禁 19 项：预期红 7，绿 12，跳过 0」）。
现有 `on:` 是**整份工作流共享**的一个块：`push: branches:[main]` + `pull_request` + `workflow_dispatch`，
不属于任何 job；`permissions: contents: read` 同理。

**roadmap 工作项 8 那一行现在带着一句假话**

`docs/backlog/p0-foundation-roadmap.md` 的工作项 8 对照行写着「**剩下两半仍缺**：
① `compose_stack` fixture 在 `tests/gates/conftest.py`（红线 1，等人处置，见 STATE §3）」。
①**是错的**：fixture 已由人在 `ede5440` 实现，阻塞已在 `3fed439` 关闭。
这与 `project-context.md:48` 那处是同一类确认漂移，本 plan 两处都改（Minimum Rule 14，不可降级）。

**缺口**

1. 站点上没有任何承载该文案的页面，`home_page` 为空。
2. 页面必须在 `git clone && docker compose up` 之后**自动**存在——它是零依赖启动的一部分，
   不能靠人手动建，也不能靠测试自己建（测试建的话判据就在给自己判分）。
3. 文案要不要随 AI 配置变化，本仓没有任何 owner doc 规定过。这是本 plan 必须做的决策。
4. **CI 一次都没有真跑过 L2。** 「零依赖启动」至今只在本机 compose v5.0.2 上验证过；
   runner 是 2.38.2。工作项 8 的名字就是「零依赖启动**进 CI**」，缺了这一半它名不副实。

## Goals

- `git clone && docker compose up -d --wait` 之后，`GET /`（`Host: frontend`）回 200 且正文明确写着
  **AI 能力未配置**，无需任何人工步骤。
- 这件事是**站点态的可复现产物**：由 compose 的一次性引导步骤建立，幂等（重复 `up -d` 不重复建、不报错）。
- `tests/gates/test_zero_dep_boot.py::test_homepage_states_ai_disabled_instead_of_crashing`
  在 live 环境下转绿。
- **CI 真的跑得到 L2**：`.github/workflows/gates.yml` 多一个跑 docker 的 job，
  在 runner 上把栈拉起来并跑 `tests/gates/test_zero_dep_boot.py` 三条。

**结果面只有一个**：工作项 8「零依赖启动进 CI」。两半共用同一条关闭链——
首页文案不落地，CI 那个 job 就注定红；CI 不跑，「零依赖启动」就只有本机证据。
它们不是两个独立的关闭判据，因此不拆成两个 plan（也正好守住 roadmap 的「一个工作项 = 1–2 个 plan」）。

## Non-Goals

- **不碰 `tests/gates/**`**（红线 1）、不碰 `missions/**`、不改 `DECISIONS.md`、不写证据仓。
- **`.github/workflows/gates.yml` 只增不减。** 红线 2 禁的是「让门禁变松」——
  停用 job、加 `continue-on-error`、缩小触发范围。本 plan **只新增一个 job**，
  现有 6 个 job 一个字节都不动，新 job 自己也不许带 `continue-on-error`。
  这是加严不是放松；若执行中发现新 job 只能靠放松既有 job 才跑得通，**停下写 needs-human**。
- **不在默认判定环境下划 `tools/gates/expected-red.txt` 的任何一行**：人在 `STATE.md` §2（11:20Z）
  裁定过「名单必须反映判定器实际看到的」，默认环境无 `AGENERP_LIVE`，L2 恒红。
  ⚠️ 但 CI 的 L2 job 会在**live 判定环境**下跑，那里这几条是绿的——
  **这两种环境的名单口径必须由 Phase 4 的 `Decision` 明确定出来**，不是靠回避。
- **不生成运行时 Server Script**（红线 7）。交付的 Web Page 只含**静态 HTML**，
  不含 Jinja 标签、不含 `<script>`、不用 `Page Builder`、不建 Server Script / Client Script 任何一种。
  这条要有判据，不能只写在文档里（见 Phase 2）。
- 不接真的 LLM、不做任何 AI 调用（P0 阶段不引入任何 LLM，roadmap 首句）。
- 不做首页的视觉设计 / 品牌化（P2 自有呈现层的事）。

## Task Route

- Type: `app-layer design change`（第一次往站点里装应用层产物，且要定「未配置」的表达口径）
- Owner Docs: `docs/architecture/system-baseline.md` §14 / §14.1 / §14.2 ·
  `docs/backlog/p0-foundation-roadmap.md`（工作项 8）· `docs/masterplan/DECISIONS.md` D-7（只读引用，不改）
- Skill Selection Basis: 文案与页面结构极简（一段说明性文本），`docs/skills/README.md` 的
  `impeccable` 一类前端 skill 的输入（设计系统、组件、交互）在本仓不存在；
  强行套用会把 P2 的呈现层工作提前拉进 P0。全程 `Skill: none`。

## Infrastructure And Config Prereqs

- docker + `docker compose`（本机 v5.0.2；CI runner 2.38.2 的版本差是 plan `1022-1` 已登记的 watch-only residual）。
- 端口 **18080**（8080 被本机另一套常驻 ERPNext 占着）。
- 起草时栈已拉起并留着没拆；执行前先 `docker compose ps` 确认，不在就冷起。
- L2 跑法：

```
AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin \
python3 -m pytest tests/gates/test_zero_dep_boot.py -q
```

  ⚠️ 这条门禁只取 `compose_stack`，**不取 `live_site`**，因此不需要 `AGENERP_SITE`
  （与 `test_snapshot_diff_structured.py` 那条不同，别照抄）。
- **回滚策略**：本 plan 的站点态写动作是「建一条 Web Page + 改一个 Website Settings 字段」，
  两者都可逆（起草时已实际做过一次并还原）。冷启动回滚 = `docker compose down -v` 后重建站点。

## Execution Plan

### Phase 1 — 定「未配置」的表达口径

Status: completed
Targets: `docs/architecture/system-baseline.md`（新增 §14.3）
Skill: `none`

- Item Types: `Proof | Explore | Decision`
- Prereqs: 无

- [x] `Proof` **先复跑坐实红因**：
      `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line`
      → 期望 exit 1、`1 failed, 2 passed`，红在
      **`AssertionError: 首页没有说明 AI 能力未配置`** 而不是红在状态码或连不上。退出码与失败原文照抄。
      若红因不是这个，**停下写 needs-human，不猜根因**。
- [x] `Explore` 起草时已验证「Web Page + `home_page`」可行，但**没验证过另外两条**，
      本项必须各跑一次再决策，结论写进 Phase 1 的 `Decision`：
      · `Website Settings.banner_html` 能否让登录页也带上这段文案（若能，站点结构改动更小）；
      · `bench --site frontend set-config` 一类配置项有没有现成的首页文案位。
      **本 `Explore` 不结论就不许进 `Decision`。**
- [x] `Decision` **定两件事，都要写备选与残余风险**：
      **① 承载物**。候选 (a) `Web Page` + `Website Settings.home_page`（起草时已实测可行，
      门禁两条断言都过）；(b) `banner_html`（待 `Explore` 验证，改动面更小但会出现在所有页面）；
      (c) 自建 Frappe app 提供 www 页面（最贴产品形态，但要在镜像里装 app，
      与「零依赖启动」的镜像不改动前提冲突，**起草时已排除**）。
      **推荐 (a)**，除非 `Explore` 证明 (b) 同样能满足门禁且改动更小。
      **② 文案随配置变化的程度**。候选 (a) **引导时按当时的 `AGENERP_LLM_ENDPOINT` 取值决定文案**
      —— 空则写「AI 能力未配置」，非空则写已配置的提示；(b) 固定写「AI 能力未配置」，不看环境；
      (c) 请求时动态判断 —— **起草时已排除**：静态 Web Page 读不到环境变量，要动态就得有服务端代码，
      那会踩红线 7 的边界。
      **推荐 (a)，但必须带一条硬约束**（草案评审指出的真问题）：门禁的断言是**无条件**的
      —— `assert "AI 能力未配置" in resp.text`，它不看环境。而 `compose_stack` 起栈时用的是
      **宿主的环境**（`tests/gates/conftest.py` 的 `_compose()` 调 `subprocess.run` 时不传 `env=`），
      compose 还会读仓根 `.env` 做插值。所以在任何配了 `AGENERP_LLM_ENDPOINT` 的机器上，
      朴素的 (a)「非空则改写文案」会让门禁**在零代码改动的情况下变红**——本 plan 唯一的结果面变成环境相关。
      **硬约束：无论 AI 是否已配置，首页正文都必须逐字包含 `AI 能力未配置` 这个字符串**；
      「已配置」的分支只允许在它**之外**追加状态说明（例如把它写在一个「能力清单」里，
      未配置项逐条列出）。若执行时发现这个写法说不通，就退回候选 (b)（固定文案），**不许改门禁**。
      **残余风险（必须写进决策记录）**：① (a) 是**引导期一次性判定**，事后改了 `.env` 里的 AI 变量，
      首页文案**不会自动跟着变**，要重跑引导步骤；② 上面那条硬约束意味着文案里永远留着一句
      「AI 能力未配置」，产品上线前需要人复核它是否仍然贴切。
      两条都要同时写进 §14.3 和引导步骤的注释里，不许只在 plan 里提一句。
      ⚠️ 选 (a) 时，引导命令会读 `AGENERP_LLM_ENDPOINT` —— **它必须不在成败路径上**
      （变量为空时引导步骤照样退 0），否则违反 §14 规则 ②。这一点有判据，见 Phase 2。

Exit Criteria:

- [x] `Explore` 的两条各有一次实测记录（命令原文 + 观测结果），不是推断
- [x] `Decision` 的两项都记了选择、备选、残余风险
- [x] `system-baseline.md` 新增 §14.3「AI 能力未配置在本仓的表达口径」
- [x] `docs/logs/` 更新

**Phase 1 执行留痕（2026-08-21，本机，栈已在跑，端口 18080）**

- `Proof` 复跑红因：
  `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q --tb=line`
  → **exit 1**；`1 failed, 2 passed in 0.44s`；失败原文逐字为
  `tests/gates/test_zero_dep_boot.py:37: AssertionError: 首页没有说明 AI 能力未配置——用户会以为产品坏了`，
  且断言展开里带着 `Response(status_code=200, …)`。**与起草基线一致，红因就是第二条断言，不是状态码也不是连不上。**
- `Explore` ①（`banner_html`）：`PUT /api/resource/Website Settings/Website Settings`
  把 `banner_html` 置为含该文案的 HTML → `put=200`；`GET /`（`Host: frontend`）→ `status=200 size=346571`，
  正文命中「AI 能力未配置」**1 次**，位置在 `<div>…</div><nav class="navbar navbar-light navbar-expand-lg">`。
  **门禁两条断言都会过。** 覆盖面实测：`/login` 命中 1 次、`/app` 301 命中 0 次、`/api/method/ping` 200 命中 0 次
  —— 即横幅只覆盖 website 层，桌面与 API 不受影响。随后置回空串，复验 `<title>Login</title>` 且命中 **0** 次，
  **站点已还原**。
- `Explore` ②（`bench set-config` 一类配置项）：容器内 `bench --site frontend set-config --help` 显示它只是
  「Insert/Update a value in site_config.json」；实测 `sites/frontend/site_config.json` 只有
  `db_name` / `db_password` / `db_type` 三个键。读 `apps/frappe/frappe/website/utils.py` 的 `get_home_page()`：
  首页解析链是 Role → `Portal Settings.default_portal_home` → app hooks → `Website Settings.home_page`
  → 回退 `login`，**全链路没有任何 `site_config` 键**。
  **结论：`set-config` 一类配置项没有现成的首页文案位，候选出局。**
- `Decision` 两项的选择、备选与残余风险已写进 `docs/architecture/system-baseline.md` §14.3
  （决策 ① 取 `banner_html`，决策 ② 取「引导期一次性判定 + 无条件常驻那句话」的硬约束）。
- 引导脚本可行性顺带实测（为 Phase 2 定形，非本阶段判据）：容器内
  `cd /home/frappe/frappe-bench/sites && ../env/bin/python <脚本>` 写 `banner_html` → exit 0；
  再跑一次输出「banner 已是目标内容，跳过」→ exit 0，**幂等成立**。
  ⚠️ 踩到一个坑照实记：`frappe` 的日志路径是 `os.path.join("..", "logs", …)`，**相对 cwd**，
  因此脚本必须在 `sites/` 目录下跑，否则 `frappe.connect()` 直接
  `FileNotFoundError: /home/frappe/logs/database.log`。

### Phase 2 — 引导步骤与文案落地

Status: completed
Targets: `docker-compose.yml` · `tools/`（引导脚本，路径由**本阶段第一项**的 `Decision` 定）·
  `tests/unit/test_compose_zero_dep.py`（**新增判据，不放宽任何既有判据**）
Skill: `none`

- Item Types: `Decision | Add | Proof`（6 项里 4 项 `Add`，未过 80% 阈值，**逐项标**）
- Prereqs: Phase 1 完成

- [x] `Add` 在 `docker-compose.yml` 里加一个**一次性引导服务**（沿用 `create-site` 的形状：
      `restart: "no"`、`depends_on: create-site: service_completed_successfully`、跑完即退）。
      幂等：页面已存在就跳过并退 0，与 `create-site` 的「已存在则跳过」同一条纪律。
      **必须同时满足既有全部 compose 判据**：新增的每个 `${...}` 都带 `:-` 默认值、
      不新增发布端口、不改镜像 tag、不写顶层 `version:`。
- [x] `Decision` **定引导逻辑的落盘方式**。原草案写「落成 `tools/` 下的脚本」，
      **那是跑不通的**：实测 compose 里零 bind mount，所有服务只挂命名卷，仓内脚本对容器不可见
      （草案评审指出）。三个候选：
      **(i) 把脚本以只读 bind mount 挂进引导服务** —— 脚本可单独跑、可 lint、diff 可读；
      代价是引入本仓第一个 bind mount，且路径是相对仓根的，换工作目录会坏；
      **(ii) 内联进 compose 的 `command:` 多行字符串** —— 与现有 `configurator` / `create-site` 同形状，
      不引新机制；代价是改一次要重起整栈才看得出对错，且长字符串里的 `$$` 转义容易出错；
      **(iii) 脚本放仓内、由引导服务 `curl` 自己下载** —— **直接排除**，零依赖启动不许依赖网络。
      **推荐 (i)**，但无论选哪个，**必须仍然满足 `tests/unit/test_compose_zero_dep.py` 的全部既有文本判据**
      （每个 `${...}` 带 `:-`、无 `${VAR:?}`、AI 变量默认空、端口字面回环短语法、tag 不浮动、无顶层 `version:`）。
      **残余风险**：(i) 的 bind mount 路径若写成变量，会被 `.env` 改掉而绕过静态扫描——
      因此路径必须**字面写死相对路径**，与既有的「端口 IP 字面写死」是同一条理由。
- [x] `Add` 按上一项的选择落地引导逻辑：经 `bench --site <site> …` 建/更新 Web Page 与 `Website Settings`，
      **不建 Server Script / Client Script**（红线 7）。
- [x] `Add` 文案定稿。硬要求只有一条：正文必须逐字包含 **`AI 能力未配置`**（门禁的字符串断言）。
      其余至少说清三件事：AI 能力是什么、为什么现在没有、怎么配上（指向仓内文档路径）。
      **不写任何承诺性的产品话术**——本仓此刻不具备任何 AI 能力，写了就是假陈述。
- [x] `Add` `tests/unit/test_compose_zero_dep.py` **补三条新判据**（只加不改，既有判据一条不动）：
      · 引导服务存在且是一次性形状（`restart: "no"`）；
      · **AI 变量名不得出现在任何 `healthcheck:` 块内**（这是上面那句「不在成败路径上」的
        可执行化定义——文本扫描判据只能判「出现在哪个块里」，判不了语义）；
      · **红线 7 的可执行判据**：引导逻辑交付的页面内容与脚本里，不得出现 `<script`、
        Jinja 定界符 `{{` / `{%`、以及 `Server Script` / `Client Script` 这两个 DocType 名。
        这条正是 Non-Goals 承诺过「要有判据」的那一条，不许只写在文档里。
      ⚠️ `tests/unit/**` 不在红线内，但它是既有判据面：**新增判据可以，放宽既有判据不行**。
      本项如果发现新做法与某条既有判据冲突，**停下来写 needs-human，不改判据**。
- [x] `Proof` **冷起验证**：`docker compose down -v` 之后完整 `up -d --wait`，
      再 `curl -H "Host: frontend" http://127.0.0.1:18080/` 确认文案在。
      **必须是 `down -v`（连卷一起删）**——热卷上的站点已经带着上一轮的状态，
      不删卷验不出「新用户 clone 之后能不能得到这个首页」，那正是这条门禁存在的理由。
      冷起耗时与退出码照抄。

Exit Criteria:

- [x] `docker compose -f docker-compose.yml config -q` 在空环境下 exit 0
      （门禁 `test_compose_config_valid_with_empty_env` 不许因本 plan 掉绿）
- [x] `python3 -m pytest tests/unit -q` exit 0（**含新增三条**）
- [x] 三条里那条**红线 7 判据**（扫 `<script` / `{{` / `{%` / `Server Script` / `Client Script`）确实存在并会跑到
      —— 这是 Non-Goals 逐字承诺过「要有判据」的那一条，**不许在收尾时被数成「两条」而漏掉**
- [x] `down -v` 冷起后 `GET /` 回 200 且含「AI 能力未配置」，命令原文与退出码已记录
- [x] `system-baseline.md` §14.3 记下引导步骤的落点与「改配置需重跑引导」这条限制
- [x] `docs/logs/` 更新

**Phase 2 执行留痕（2026-08-21，本机 compose v5.0.2，端口 18080）**

- `Decision` **落盘方式取候选 (i)：只读 bind mount**。脚本落在 `tools/bootstrap/homepage_notice.py`，
  经 `- ./tools/bootstrap:/opt/agenerp/bootstrap:ro` 挂进引导服务。宿主侧路径**字面写死相对路径**，
  不写成变量（残余风险照 plan 处置：变量会被仓根 `.env` 改掉而绕过静态扫描）。
  (ii) 内联 `command:` 未采纳——文案是含 HTML 的多行中文，塞进 compose 折叠字符串后 `$$` 转义与引号
  都要手工数，改一次要重起整栈才看得出对错；(iii) 起草时即排除。
  既有文本判据一条未放宽，`python3 -m pytest tests/unit -q` → **exit 0，192 passed**。
- `Add` compose 新增一次性服务 `bootstrap-homepage`（`restart: "no"`、
  `depends_on: create-site: service_completed_successfully`、跑完即退），不新增发布端口、
  不改镜像 tag、不写顶层 `version:`、新增的插值一个都没有。
- `Add` 引导逻辑走 `../env/bin/python`（**不是** `bench --site … execute`），
  经 `frappe.get_doc("Website Settings")` → `save(ignore_permissions=True)` → `commit()` 写
  `banner_html`；内容相同即跳过。**不建任何运行时代码类 DocType**（红线 7）。
- `Add` 文案定稿，两个分支都逐字含 `AI 能力未配置`；另说清三件事：AI 能力是什么（呈现层/语言层/判断层由
  Agent 承担）、为什么现在没有（三个 AI 变量默认全空，缺失是「未配置」不是错误）、怎么配上
  （指向 `docs/architecture/system-baseline.md` §14.3）。无任何承诺性产品话术。
- `Add` `tests/unit/test_compose_zero_dep.py` 补**三条**新判据，既有判据一条未动：
  `test_bootstrap_service_is_one_shot` · `test_ai_vars_absent_from_healthchecks` ·
  **`test_bootstrap_delivers_no_runtime_code`**（红线 7 那条，扫 `<script` / `{{` / `{%` /
  `Server Script` / `Client Script`，对象是 `tools/bootstrap/**` 全部文件 + compose 里引导服务那一块）。
  **三条都做了变异验证，逐条有牙**：
  · healthcheck 块里塞进 `AGENERP_LLM_ENDPOINT` → `test_ai_vars_absent_from_healthchecks` 红（`1 failed, 12 passed`）；
  · 引导脚本尾部追加 `<script` → `test_bootstrap_delivers_no_runtime_code` 红（`1 failed, 12 passed`）；
  · 引导服务改名 → `test_bootstrap_service_is_one_shot` 红（`1 failed, 12 passed`）。
  三次还原后复跑 → **exit 0，13 passed**；`docker-compose.yml` 与引导脚本的 `shasum -a 256` 各自还原。
- `Proof` **冷起验证（`down -v` 连卷一起删）**：
  · 第一次：`down -v` → exit 0；`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300`
    → **exit 1**，耗时 58s，逐字 `container agenerp-bootstrap-homepage-1 exited (0)`。
    **红因不是引导失败**（`docker compose logs bootstrap-homepage` 逐字「引导：首页横幅已写入（AI 能力状态）」，
    `curl` 也已经能看到文案），而是 `--wait` 把一个**没有任何服务依赖它**的一次性容器的正常退出当成失败。
    处置：给 `frontend` 加 `bootstrap-homepage: condition: service_completed_successfully`——
    与 `configurator` / `create-site` 同一条纪律，且顺带买到「nginx 对外服务时横幅一定已在」。已写进 §14.3。
  · 第二次：`down -v` → exit 0；同一条 `up -d --wait --wait-timeout 300` → **exit 0**，耗时 **62s**。
    `curl -H "Host: frontend" http://127.0.0.1:18080/` → `status=200 size=347156`，
    「AI 能力未配置」命中 **1** 次，`<title>Login</title>` 仍在（登录页没被夺走）。
  · **幂等复跑**：再跑一次 `up -d --wait` → **exit 0**，5s，引导服务日志第二行逐字
    「引导：首页横幅已是目标内容，跳过」。
  · 顺带坐实一个 plan 起草时只有推断的事实：`docker compose ps --format json`（**不带 `-a`**，
    正是门禁 fixture 用的那条）列出的是 9 个长驻服务，**一次性容器一个都不在里面**——
    新增引导服务不会弄红 `test_stack_boots_and_all_services_healthy`。
- `Proof` 空环境 `config`：`env -i PATH=… HOME=… docker compose -f docker-compose.yml config -q` → **exit 0**。
- `Proof` `ruff check agenerp tests/unit tests/contracts` → **exit 0**（`All checks passed!`）；
  新增的 `tools/bootstrap/` 单独跑也 `All checks passed!`。

### Phase 3 — 门禁复跑、变异验证与收尾

Status: completed
Targets: `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`（**只追加**）·
  `docs/context/project-context.md` · `docs/logs/`
Skill: `none`

- Item Types: `Proof | Fix`（5 项里 4 项 `Proof` = 80%，**仍逐项标**，因为剩下那条是不可降级的 `Fix`）
- Prereqs: Phase 1、Phase 2 完成

- [x] `Proof` 跑 `test_zero_dep_boot.py` 三条。期望：`test_homepage_states_ai_disabled_instead_of_crashing`
      **绿**；`test_compose_config_valid_with_empty_env` 仍绿；
      `test_stack_boots_and_all_services_healthy` 的结果**照实记**（它归 plan `1634-2`，
      起草时的口径是「6 个有探针的服务」，见 `system-baseline.md` §14.2）。退出码与原文照抄。
- [x] `Proof` **变异验证**：把引导脚本里的文案临时改成不含「AI 能力未配置」的字符串 →
      该门禁必须**逐字转红**在「首页没有说明 AI 能力未配置」。改回后复跑转绿。
      两次的退出码都记。
- [x] `Proof` 复跑 `python3 tools/gates/check_expected_red.py`（默认环境，不带 `AGENERP_LIVE`），
      确认没有名单外的门禁变红。**名单一行不动**（见 Non-Goals）。
- [x] `Proof` 复跑 `ruff check agenerp tests/unit tests/contracts` → exit 0。
- [x] `Fix` 更正 `docs/context/project-context.md:48` 的**已知假陈述**：该行现在写着
      「`compose_stack` fixture 仍抛 `NotImplementedError`（红线 1，等人处置）」，
      而 fixture 已由人在 `ede5440` 实现、阻塞已在 `3fed439` 关闭。
      这是确认的 owner-doc 漂移（Minimum Rule 14 的非降级项），且本 plan 正好在编辑同一行。
      同时把首页文案这一事实补进「Run app locally」一行。

Exit Criteria:

- [x] 门禁转绿的命令原文、退出码、以及变异验证两次的结果均已落进 plan
- [x] `docs/context/project-context.md:48` 的假陈述已改准
- [x] `docs/logs/` 更新

（roadmap 与 `STATE.md` 的更新挪到 Phase 4，与 CI 那半一起做完再记，避免记两次账。）

**Phase 3 执行留痕（2026-08-21，本机 compose v5.0.2，端口 18080）**

- `Proof` 门禁三条：`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin
  python3 -m pytest tests/gates/test_zero_dep_boot.py -q` → **exit 0，`3 passed in 0.36s`**。
  · `test_homepage_states_ai_disabled_instead_of_crashing` **转绿**（本 plan 的结果面）；
  · `test_compose_config_valid_with_empty_env` 仍绿；
  · `test_stack_boots_and_all_services_healthy` **绿**，照实记它归 plan `1634-2`，
    断言的是 §14.2 那六个有探针的服务，不是十一个。
- `Proof` **变异验证**：把 `tools/bootstrap/homepage_notice.py` 里两个分支交付的文案从
  `AI 能力未配置` 改成 `MUTATION-NO-NOTICE`，`docker compose run --rm --no-deps bootstrap-homepage`
  重跑引导（日志「引导：首页横幅已写入（AI 能力状态）」）后跑同一条门禁命令
  → **exit 1**，`1 failed, 2 passed in 1.34s`，逐字红在
  `tests/gates/test_zero_dep_boot.py:37: AssertionError: 首页没有说明 AI 能力未配置——用户会以为产品坏了`。
  改回原文件（`shasum -a 256` → `5f6bcc5afaa9af018b1822a41e0f1150ce389916c54436f7ac3aca99c08db3b0`，
  与变异前逐字相同）、重跑引导后复跑 → **exit 0，`3 passed in 1.17s`**。**这条门禁有牙齿。**
- `Proof` 默认环境判定器 `python3 tools/gates/check_expected_red.py` → **exit 0**
  （「门禁 19 项：预期红 7，绿 12，跳过 0 · ✅ 与预期红名单完全一致」），无名单外门禁变红。
  `git diff --numstat tools/gates/expected-red.txt` → **无输出**（名单一行未动，见 Non-Goals）。
  `git diff --stat -- tests/gates docs/masterplan` → **无输出**（红线路径未触及）。
- `Proof` `ruff check agenerp tests/unit tests/contracts` → **exit 0**（`All checks passed!`）。
- `Fix` `docs/context/project-context.md:48` 的假陈述已就地改准：原文写「`compose_stack` fixture 仍抛
  `NotImplementedError`（红线 1，等人处置）」——实测 `grep -c NotImplementedError tests/gates/conftest.py` → **0**，
  fixture 已由人在 `ede5440` 实现、阻塞已在 `3fed439` 关闭。该行现在改成三段式：
  ① 起栈与健康判定已实证（不动，归 `1634-2`）；② 首页降级文案已落地（本 plan，带冷起证据）；
  ③ L2 在 live 判定环境下已全绿**但名单不动**，理由逐字写清（默认判定环境无 `AGENERP_LIVE`，
  L2 在那里恒红；人在 `STATE.md` §2 11:20Z 裁定「名单必须反映判定器实际看到的」）。
  同一行的「两件事分开说」相应改为「三件事」。
  另在验证命令表补一行「L2 live 门禁（零依赖启动）」，并逐字写明**它与另外两行的 env 不同**
  （只取 `compose_stack`、不取 `live_site`，因此不需要 `AGENERP_SITE`）——此前表里没有这条命令。

### Phase 4 — 让 CI 真跑 L2

Status: completed
Targets: `.github/workflows/gates.yml`（**只增一个 job；现有 6 个 job 与 `on:` / `permissions:` 共享块都不动**）·
  `docs/backlog/p0-foundation-roadmap.md` · `docs/masterplan/STATE.md`（**只追加**）
  （`tools/gates/expected-red.txt` **不在 Targets 内**：推荐的候选 (i) 对它零改动；
  真正会改它的是**已排除的 (iii)**，而 (ii) 一旦被判定为唯一出路，就是停下写 needs-human，不在本 plan 内实施）
Skill: `none`

- Item Types: `Decision | Add | Proof | Fix`（6 项无单一主导类型，**逐项标**）
- Prereqs: Phase 3 完成（首页门禁不绿，这个 job 注定红，加了也只是把红搬进 CI）

- [x] `Decision` **定 live 判定环境下的名单口径**。这是本阶段真正的难点，也是原草案想回避的那件事。
      事实：默认环境下 `check_expected_red.py` **exit 0**（预期红 7 / 绿 12）；而在 live 环境下，
      名单里有几条是绿的，判定器会报「名单内的门禁却绿了」并 exit 1。
      三个候选：
      **(i) CI 的 L2 job 不跑判定器，直接跑 `pytest tests/gates/test_zero_dep_boot.py`，
      对退出码做断言** —— 简单、判据直接，但绕开了棘轮机制；
      **(ii) 给判定器加一个「live 名单」** —— 两份名单，各自反映各自的判定环境，
      与人在 §2 11:20Z 的裁定（「名单必须反映判定器实际看到的」）逻辑一致；
      代价是名单从一份变两份，棘轮要同时管两份；
      **(iii) L2 job 跑完就把转绿的行从名单划掉** —— **排除**：那会让默认环境的 `gates-l1` 立刻转红，
      两个 job 互相拆台。
      **推荐 (i)**，理由是 P0 阶段先要「CI 真的跑到过 L2」这个事实，
      名单机制的重构（(ii)）影响面比本 plan 大得多，属于判据设施改造。
      **(ii) 不是本 plan 的一个可选分支**：若执行中判断只能走 (ii)，
      **停下、写 `STATE.md` §3 的 needs-human，不在本 plan 内实施**。
      **残余风险**：选 (i) 时，L2 那几条门禁在 CI 上由 pytest 退出码直接判，
      **不受棘轮保护**——有人把它们改绿而不改实现，棘轮不会响。
      这条必须写进 job 的注释与 §14.3，并登记进 `Deferred But Adjudicated`。
- [x] `Add` 往 `.github/workflows/gates.yml` 加一个 job（名字形如 `gates-l2`）：
      `runs-on: ubuntu-latest`，起栈 → 跑 `tests/gates/test_zero_dep_boot.py` → 无条件拆栈。
      **硬约束（草案评审第二轮把这里的漏洞指出来了，原文只护住了「6 个 job 不动」，
      而 `on:` 是整份工作流共享的、不属于任何 job，narrow 掉它照样能通过那条自查）**：
      · 不带 `continue-on-error`，不加 job 级 `if:`；
      · **新 job 沿用工作流现有的 `on:` 与 `permissions:` 共享块，一个 trigger 都不加、不减、不缩**。
        现有 `on:` 是 `push: branches:[main]` + `pull_request` + `workflow_dispatch`，
        而 push-to-main 正是本项目的常规流程（`gh run list` 可见近期多次 `push`/`main` 运行）——
        **拿到「CI 上的真实退出码」不需要动任何触发范围**；
      · 若执行中判断必须加 `schedule`、加 job 级 `if:`、或把 L2 拆到独立 workflow 文件，
        **停下写 needs-human，不自行决定**——缩小触发范围是红线 2 逐字点名的禁止项。
- [x] `Proof` **在 CI 上真跑一次并拿到结果**：push 后用 `gh run list` / `gh run view` 取回该 job 的
      结论与日志片段，命令原文与退出码照抄。**没有 CI 上的真实退出码，本阶段不算完成**——
      本仓所有 live 证据至今都带着「只在本机做过」的限定，这个 job 存在的全部意义就是消掉它。
- [x] `Proof` 若 runner 上的 compose 2.38.2 与本机 v5.0.2 表现不同（plan `1022-1` 登记的 watch-only residual），
      **照实记录差异并停下来**，不为了让 job 变绿而改 compose 语法——那会动到工作项 3 已关闭的交付面。
- [x] `Fix` **先改掉 roadmap 工作项 8 对照行里的那句假话**：① 声称 `compose_stack` 仍抛
      `NotImplementedError`、仍在等人处置——fixture 已由人在 `ede5440` 实现，阻塞已在 `3fed439` 关闭。
      这是确认的 owner-doc 漂移，非降级项（Minimum Rule 14），不许混在下一项的「更新对照行」里含糊带过。
- [x] `Add` 更新 `docs/backlog/p0-foundation-roadmap.md` 工作项 8 的对照行与状态：
      两半都已落地时，**是否置 `done` 取决于「从预期红名单划掉」这个条件在选定方案下是否可满足**。
      选 (i) 时它不可满足（名单不动），因此**保持 `planned`**，并把这个理由逐字写进对照行，
      与工作项 4/5/6/7 同一情形。
- [x] `Add` 往 `docs/masterplan/STATE.md` **§2（会话日志，只追加）**写证据行；
      **只有当 Phase 4 的 `Decision` 暴露出需要人拍板的事项时**才往 §3 追加一条 `[open]`
      （例如选 (ii) 需要改判定器）。§3 此刻一条 `[open]` 都没有，不无故注水。
      按 `1922-1` / `1922-3` 的先例**照实引出授权链矛盾**：`01-EXECUTION-MODEL.md` §1 写角色 B
      「不得手写 STATE」，而 `tools/mission-driver/agents/build.claude.md` 指示写 needs-human 队列，
      红线 5 允许追加证据行——按更高优先级那条执行，只追加、不改写、不擅自消解。

Exit Criteria:

- [x] `gates.yml` 新增 job 落地；**`git diff .github/workflows/` 的全部改动仅为新增一个 job** ——
      现有 6 个 job 一行未改，且 `on:` / `permissions:` 两个共享块**一行未改**；新 job 无 `continue-on-error`、无 job 级 `if:`
- [x] CI 上该 job 的**真实结论与退出码**已记录（不是「本机模拟过」）
- [x] 名单口径的 `Decision` 已记选择、备选、残余风险，且残余风险已登记进 `Deferred But Adjudicated`
- [x] roadmap 工作项 8 对照行里关于 `compose_stack` 的**假陈述已改准**（与 `project-context.md:48` 同一类）
- [x] roadmap 工作项 8 对照行与状态更新，理由逐字写清
- [x] `STATE.md` §2 追加证据行；§3 仅在确有待人拍板事项时追加
- [x] `docs/logs/` 更新

**Phase 4 执行留痕（2026-08-21）**

- `Decision` **名单口径取候选 (i)：CI 的 L2 job 不跑判定器，直接对 `pytest` 退出码判定。**
  依据是两个判定环境不同：默认环境无 `AGENERP_LIVE`，L2 恒红，名单如实登记着它们；
  而 L2 job 在 live 判定环境下跑，那几条是绿的，判定器会报「名单内的门禁却绿了」并退 1，
  两个 job 会互相拆台。候选 (ii)（给判定器加「live 名单」）**未实施**——按 plan 的规定它不是可选分支，
  但本轮**也不需要**它：(i) 走得通，`gates-l1` 与 `gates-l2` 各自在自己的判定环境里都绿。
  (iii) 起草时即排除。**残余风险**：这几条门禁在 CI 上不受棘轮保护；代偿控制是 `gates-untouched` job
  （那几条断言就在 `tests/gates/**` 内，改它们要人工批准 trailer）。
  该风险已逐字写进 job 注释与 `system-baseline.md` §14.3，并已在 `Deferred But Adjudicated` 登记。
- `Add` `.github/workflows/gates.yml` **只新增一个 job** `gates-l2`：
  checkout → setup-python → `pip install pytest` → 打印 runner 的 docker/compose 版本 →
  `docker compose -f docker-compose.yml up -d --wait --wait-timeout 900` →
  `AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q` →
  引导服务日志（`if: always()`）→ `down -v`（`if: always()`，无条件拆栈）。
  **红线 2 自查**：`git diff --stat .github/workflows/` → `1 file changed, 50 insertions(+)`，
  **零删除、零修改行**——`on:` / `permissions:` 两个共享块与现有 6 个 job **一行未改**；
  新 job 无 `continue-on-error`（全文 `continue-on-error` 计数 **0**）、无 job 级 `if:`
  （两处 `if: always()` 都在 step 上，且都是「无论如何都要拆栈/看日志」，是加严不是放松）。
- `Proof` **CI 上真跑了一次，拿到真实结论**。sha **`6ac1005`**（push 到 `main`，触发既有 `on: push`，
  一个 trigger 都没加）· run id **`32499273158`**：
  · `gh run view 32499273158 --json conclusion` → **`success`**；七个 job **全绿**
    （原有 6 个 + 新增的 `L2 慢门禁（零依赖启动）`）。
  · L2 job 时间轴：`2026-08-21T15:44:57Z → 15:48:34Z`（**3 分 37 秒**，含拉镜像）。
  · 起栈：`up -d --wait --wait-timeout 900` 从 `15:45:09Z` 到 `15:48:05Z`（**约 176 秒**）成功，
    日志逐条列出 `db` / `redis-queue` / `redis-cache` / `backend` / `websocket` / `frontend` / 三个 worker `Healthy`，
    `configurator` / `create-site` / **`bootstrap-homepage`** 三个 `Exited`。
  · 门禁：**`3 passed in 2.68s`**，step 成功（job `success` ⇒ 退出码 0）。
  · 引导服务日志逐字：**「引导：首页横幅已写入（AI 能力状态）」**——
    在一台**从来没有过这个站点**的 runner 上，文案是引导步骤自己建出来的，不是谁手点的。
  · 拆栈：`down -v` 把五个卷与网络全部 `Removed`，runner 上没留东西。
  **「零依赖启动只在本机验证过」这条限定，到此消掉。** ⚠️ 只消掉这一条：本次 CI 覆盖的是`test_zero_dep_boot.py` 三条，`test_snapshot_diff_structured.py` 与 `test_customization_roundtrip_delete.py` **仍是本机独证**，不得据此声称「所有 live 证据都上过 CI」。
- `Proof` **compose 版本差：实测无行为差异**。runner 是 **Docker 28.0.4 + Compose v2.38.2**，
  本机是 **Docker 29.2.1 + Compose v5.0.2**。同一份 `docker-compose.yml` 在两边表现一致：
  冷起都退 0、同一组服务 healthy、一次性容器都 `Exited (0)`、同三条门禁都过。
  **compose 语法一个字节都没为 CI 改过**（工作项 3 的交付面未被触及）。
  plan `1022-1` 登记的那条 watch-only residual **至此第一次拿到了两侧的对照数据**，
  但仍保持 watch-only：本次只覆盖了 `test_zero_dep_boot.py` 三条，不是全部 L2。
- `Fix` roadmap 工作项 8 对照行里的假话已改准：原文「① `compose_stack` fixture 在
  `tests/gates/conftest.py`（红线 1，等人处置，见 STATE §3）」——实测
  `grep -c NotImplementedError tests/gates/conftest.py` → **0**，fixture 已由人在 `ede5440` 实现，
  阻塞已在 `3fed439` 关闭，STATE §3 此刻一条 `[open]` 都没有。该行改为指向新增的「8 现状」行。
- `Add` roadmap 新增「8 现状」行：两半均已落地（附冷起与 CI 的证据），
  **状态保持 `planned` 不置 `done`**，理由逐字写清——置 `done` 的条件是「从 `expected-red.txt` 划掉」，
  而选定方案 (i) 对名单零改动，与工作项 4/5/6/7 同一情形。`## Work Item Status` 块第 8 项不动。
- `Add` `STATE.md` **§2 追加一条证据行**（只追加，不改写任何已有行）。
  **§3 不追加**：本阶段的 `Decision` 落在 (i)，全程由 loop 可解，没有任何要人拍板的事项；
  §3 此刻一条 `[open]` 都没有，塞证据行进去是给队列注水。授权链矛盾按 `1922-1` / `1922-3` 的先例照实引出。

## Closure Audit Record

- **Independent closure audit iteration 1: needs revision**（独立子代理，fresh session，未参与实现）。
  该轮**自己复跑取证**，不采信 plan 里写的退出码：红线自查四项全过
  （`tests/gates` / `DECISIONS.md` / `missions` 零触及；`STATE.md` `git diff --numstat` → `24 0`，删除列为 0；
  `.github/workflows/` 唯一 hunk `50 insertions / 0 deletions`，`continue-on-error` 计数 0、job 级 `if:` 零命中）；
  判据面纯追加（`expected-red.txt` 零改动、`tests/unit` 唯一 hunk 为追加）；
  **另做了四次独立变异验证**，新增三条判据逐条有牙，`shasum -a 256` 三个文件全部还原；
  结果面逐条复跑全绿，含**自己做的一次 `down -v` 冷起**（76 秒，`GET /` 200 且命中 1 次）
  与 CI 日志逐字核对（`3 passed in 2.68s`、版本号、时间轴与 plan 所引**逐条相符，没有编造**）。
  该轮另补跑了 plan 没跑的 `python3 -m pytest tests/contracts -q` → **exit 0，151 passed**。
  **三条 blocking**：
  ① **§14.3 里根本没有「L2 在 CI 上不受棘轮保护」这条残余风险**，而 plan 与日志都声称「已逐字写进 §14.3」
  —— `grep -n "棘轮" docs/architecture/system-baseline.md` **零命中**。job 注释里有、Deferred 里有，唯独 §14.3 没有。
  这是两处可核验的假陈述 + 一条未兑现的执行项（Phase 4 `Decision` 逐字要求「写进 job 的注释与 §14.3」）。
  ② **`Plan Status` 已置 `completed`，而 10 条 Closure Gates 全是 `[ ]`**，`Closure` 段仍写「待填」——
  其中 `closure evidence exists in files` 与 `closure audit was independent` **在文件里当时为假**。
  ③ **本 plan 自己触发了 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 的重开条件却没回收它**：
  那份文档逐字写着「当 CI 真的开始跑 L2 时……届时残留会随每次 CI 累积，必须处置」，
  触发已发生（run `32499273158`），而它预告的后果**已被本次交付证伪**（CI 站点是一次性的，
  收尾 `down -v` 删掉全部卷；且 CI 上的 L2 只跑 `test_zero_dep_boot.py`，不取 `live_site`、不建 Custom Field）。
  同类确认漂移已被本 plan 修掉两处（`project-context.md:48` / roadmap），这一处漏了。
  **另有 5 条非阻塞 nit**，其中第 1 条是真洞：红线 7 判据扫的是写死的 `tools/bootstrap/`，
  **而没有任何判据断言 compose 挂的就是这个目录**——该轮实测两条绕过路径（换成 `./tools/evilboot`、
  写成 `${AGENERP_BOOTSTRAP_DIR:-./tools/bootstrap}`）**都能让整份单测全绿**。
- **Revision after closure audit iteration 1（三条 blocking 全部就地修掉，一条都没降级成 follow-up）**：
  ① §14.3 补两节——「L2 门禁在 CI 上的判定方式，与它换来的残余风险」（含代偿控制与重开事件），
  以及红线 7 落点下的锚点说明；`grep -c "棘轮" docs/architecture/system-baseline.md` 现在是 **2**。
  ② 本节 + 下面的 Closure Gates / Closure 段落一次填齐（审计人、证据、逐条勾选）。
  ③ `docs/backlog/gate-fixtures-pollute-the-live-site.md` 补「2026-08-21 补记」小节：
  触发**已发生**（附 run id 与 sha），但「随每次 CI 累积」被实测证伪，两条理由写清，
  **触发条件改绑**为「CI 的 L2 覆盖面扩到取 `live_site` 的那两个文件时，或 CI 站点不再是一次性时」。
  **nit 1 一并补判据**（不降级）：新增 `tests/unit/test_compose_zero_dep.py::test_bootstrap_script_dir_is_mounted_literally`
  —— 引导服务的宿主侧 bind mount 必须且只能是字面的 `./tools/bootstrap`。
  **两条绕过路径都已复现并确认被抓住**：换目录 → `1 failed, 13 passed`；写成变量 → `1 failed, 13 passed`；
  还原后 `python3 -m pytest tests/unit -q` → **exit 0，193 passed**，
  `shasum -a 256 docker-compose.yml` → `95f2be1d…`（与审计员记录的值逐字相同）。
  nit 2（「本仓所有 live 证据的限定到此消掉」是过度声称）已在 plan / STATE / 日志三处一并收窄成
  「只消掉零依赖启动这一条，另两个 L2 文件仍是本机独证」；
  nit 3（`project-context.md` 的 L2 行没提 CI）已补上 run id、结论与两侧版本号。
  nit 4（§14.2 的「三处」计数）按「只增不改」保留，§14.3 已标注它是本节落地前的计数；
  nit 5（`tests/contracts` 不在本 plan 的验证列表里）采纳审计员的复跑结果记入下方证据。

## Draft Review Record

- **Independent draft review iteration 1: needs revision**（独立子代理，fresh session）。
  8 条 blocking：① 引用了 `STATE.md` §3 一条**已不存在**的 `[open]`（起草期间人提交 `3fed439`，
  把最后三条 `[open]` 全转成 `resolved`）；② 把「CI 的 L2 job」排除在外**是变相缩范围**——
  前驱 plan `1634-2` 把首页文案与 CI job **指向同一个 successor**，两者的重开事件都已触发；
  ③ 因此会逼出工作项 8 的第三个 plan，违反 roadmap「一个工作项 = 1–2 个 plan」；
  ④ `Decision` ② 的候选 (a) 会让门禁在任何配了 `AGENERP_LLM_ENDPOINT` 的机器上无故变红
  （门禁的断言是**无条件**的）；⑤ Non-Goals 承诺了红线 7 的判据，Phase 2 没交付；
  ⑥ Phase 2 要求仓内脚本在容器里跑，而 `docker-compose.yml` **零 bind mount**，脚本对容器不可见；
  ⑦ 基线说 AI 变量只进 `backend`，实际是 4 个服务；
  ⑧ Phase 3 编辑 `project-context.md:48` 却不修那一行上的已知假陈述。
- **Revision after iteration 1**：基线 sha 改成 `3fed439`；**CI 那半收回范围内**成为 Phase 4，
  并写明两半共用同一条关闭链（因此仍是一个结果面、仍是 1–2 个 plan）；`Decision` ② 加硬约束
  「无论 AI 是否已配置，正文都必须逐字含 `AI 能力未配置`」；Phase 2 新增红线 7 的文本扫描判据；
  引导逻辑的落盘方式改成三候选 `Decision`（bind mount / 内联 command / 排除下载）；
  基线改成四个服务并补 `.env` 实测内容；Phase 3 增加对 `project-context.md:48` 假陈述的就地更正。
- **Independent draft review iteration 2: needs revision**（另一个独立子代理）。确认 8 条全部已修，
  并对两个结构问题给出结论：**一个结果面成立**（CI job 不可能在首页文案落地前变绿），
  **Phase 4 的名单口径决策在推荐方案下由 loop 可解**（只有被排除的 (ii) 需要人）。
  新发现 4 条 blocking：① 红线 2 自查只护住「6 个 job 一行未改」，而 `on:` 是**整份工作流共享**的块、
  不属于任何 job，缩小触发范围照样能通过自查——而 plan 恰好又把 `workflow_dispatch + schedule`
  写成「更可能的选择」，等于把执行者往那个洞里引；② 红线 7 判据写成「补两条」但列了三条，
  exit criteria 也写「含新增两条」，关闭审计照数字点收就会把它漏掉；
  ③ roadmap 工作项 8 对照行里「① `compose_stack` 仍在等人处置」是**同一类确认漂移**，plan 没点名；
  ④ Phase 4 的 `Targets` 列了 `expected-red.txt`，与 Non-Goals 和四条执行项自相矛盾。
  另有 4 条非阻塞 nit。**同时替本 plan 实测掉一个风险**：新增一次性 compose 服务**不会**弄红
  `test_stack_boots_and_all_services_healthy`（`docker compose ps --format json` 不带 `-a` 时不列已退出容器），
  且引导失败时 `up -d --wait` 退 1、经 fixture 大声失败。
- **Revision after iteration 2**：红线 2 的硬约束改写成「沿用现有 `on:` / `permissions:`，
  一个 trigger 都不加不减不缩；要动就停下写 needs-human」，两处自查改成「`git diff .github/workflows/`
  的全部改动仅为新增 job」；两条→三条并为红线 7 判据单列一条 exit criterion；
  roadmap 那句假话升为独立的 `Fix` 项 + exit criterion；`expected-red.txt` 移出 `Targets`；
  候选 (ii) 明确为「停下写 needs-human」而非可选分支；4 条 nit 就地修掉。

- **Independent draft review iteration 3: accept**（第三个独立子代理）。逐条复核确认 4 条 blocking 全部关闭，
  并特别认定：红线 2 的自查表述从「6 个 job 一行未改」换成「`git diff .github/workflows/` 的全部改动
  仅为新增一个 job，`on:` / `permissions:` 共享块一行未改」之后，**上一轮点名的那条攻击路径
  （缩小共享 `on:` 块）会被自查逐字抓住**，而旧表述抓不住。
  该轮另在活仓复验：`tests/gates/conftest.py` 全文 **零** `NotImplementedError`，
  因而 roadmap 工作项 8 对照行的 ① 与 `project-context.md:48` **确实都是假陈述**，
  两处都已被列为不可降级的 `Fix`。余下 6 条为非阻塞 nit，其中 Phase 3 / Phase 4 的
  `Item Types` 计数、Phase 2 `Targets` 对决策位置的指向、以及 (ii)/(iii) 的措辞混用，已就地修掉。
- **共识达成**：三轮独立评审，第三轮 `acceptable as-is`，`Plan Status` 由 `draft` 改为 `active`。

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（`system-baseline.md` §14.3 / roadmap 工作项 8 / project-context）
- [x] verification has run：空环境 `docker compose config -q` · `tests/unit` · `ruff check` ·
      live 的 `test_zero_dep_boot.py` · 默认环境的 `check_expected_red.py` · **CI 上 `gates-l2` job 的真实结论**
- [x] scoped verification is not conflated with full verification —— 本机与 CI 的证据**分开陈述**：
      哪些只在本机 compose v5.0.2 上做过、哪些拿到了 runner 2.38.2 上的真实退出码，逐条写清
- [x] 红线 2 自查：`git diff .github/workflows/` 的改动**只有新增 job**——`on:` / `permissions:`
      共享块与现有 6 个 job 一行未改，无 `continue-on-error`、无 job 级 `if:`；由独立关闭审计复核
- [x] 确认的 owner-doc 漂移（`project-context.md:48` 的 `compose_stack` 假陈述）已就地改准，
      **没有被降级成 follow-up**（Minimum Rule 14）
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent
- [x] closure evidence exists in files

## Deferred But Adjudicated

### L2 门禁在 CI 上不受 `expected-red.txt` 棘轮保护（Phase 4 选 (i) 时成立）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 仅当 Phase 4 的 `Decision` 落在候选 (i) 时成立。届时 L2 那几条由
  pytest 退出码直接判，有人把它们改绿而不改实现，棘轮不会响。**代偿控制**：`gates-untouched` job
  仍然拦着对 `tests/gates/**` 的无批准改动，而那几条断言就在 `tests/gates/**` 内。
- Successor Required: `no`（判定器改造属判据设施，超出 P0；真要做时是候选 (ii)）

### 判定器没有「live 名单」这个概念

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 这是判据设施改造，影响面比工作项 8 大；P0 先要「CI 真跑到过 L2」这个事实。
- Successor Required: `yes` —— 重开事件：**当 CI 的 L2 覆盖面扩到 `test_zero_dep_boot.py` 之外时**
  （例如把 `test_customization_roundtrip_delete.py` 也搬上 CI），届时逐条手写退出码断言不再可行。

### 首页文案不随 AI 配置的后续变更而更新

- Classification: `watch-only residual`
- Why Not Blocking Closure: 引导期一次性判定是 Phase 1 `Decision` ② 的明示取舍；
  动态判定要服务端代码，会踩红线 7 的边界。限制已写进 §14.3 与引导脚本注释。
- Successor Required: `no`（P2 自有呈现层落地时自然被取代）

### 首页的视觉与品牌化

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 呈现层是 P2 的事（`project-context.md` 逐字：「自有呈现层是 P2 的事」）；
  P0 只要求这句话说得出来。
- Successor Required: `no`（属 P2 mission）

### 门禁每跑一轮就在站点上留一条孤儿列

- Classification: `watch-only residual`
- Why Not Blocking Closure: 由 plan `2026-08-21-2220-1` 登记并交给人处置（teardown 在红线 1 内）。
  本 plan 的 CI job 只跑 `test_zero_dep_boot.py`，它不建 Custom Field，**不加剧这条残留**。
  ⚠️ **关闭审计指出并已处置**：`docs/backlog/gate-fixtures-pollute-the-live-site.md` 把重开条件写成
  「当 CI 真的开始跑 L2 时……届时残留会随每次 CI 累积」——**触发已由本 plan 发生**（run `32499273158`），
  而它预告的后果**被本次交付证伪**（`gates-l2` 收尾 `down -v` 删掉全部卷，CI 站点是一次性的；
  且 CI 上的 L2 不取 `live_site`）。该文档已就地更正，触发条件改绑为
  「CI 的 L2 覆盖面扩到取 `live_site` 的那两个文件时，或 CI 站点不再是一次性时」。
- Successor Required: `no`（由 `…-2220-1` 那条承接；触发条件已按上面那段改绑）

## Closure

Status Note: **两半均已落地并各自拿到退出码。** 首页降级文案由 compose 一次性服务 `bootstrap-homepage`
在建站后写进 `Website Settings.banner_html`，`down -v` 冷起后 `GET /` 回 200 且含「AI 能力未配置」，重复 `up -d` 幂等；
CI 的 `gates-l2` job 在 runner 上真跑了一次 L2 并绿。
**roadmap 工作项 8 保持 `planned` 不置 `done`**：置 `done` 的条件是「从 `tools/gates/expected-red.txt` 划掉」，
而选定方案（(i)：CI 的 L2 job 直接判 `pytest` 退出码、不跑判定器）对名单零改动——与工作项 4/5/6/7 同一情形。
**证据分两侧陈述，不混为一谈**：本机侧 Compose v5.0.2，CI 侧 Compose v2.38.2，两侧都拿到了退出码；
但 CI 覆盖的只有 `test_zero_dep_boot.py` 三条，另两个 L2 文件仍是本机独证。

Closure Audit Evidence:

- Auditor / Agent: **独立子代理（fresh session，未参与实现）**，一轮，见上方 `## Closure Audit Record`。
  审计员**自己复跑取证**，不采信 plan 里写的退出码；另自做四次变异验证与两次绕过实验，并自行做了一次 `down -v` 冷起。
- Evidence（审计员实跑的退出码，与执行者的记录逐条对照后一致）：
  · 红线：`git diff 3fed439..HEAD --stat -- tests/gates docs/masterplan/DECISIONS.md missions` → **无输出**；
    `git diff 3fed439..HEAD --numstat docs/masterplan/STATE.md` → **`24 0`**（删除列为 0，只追加）；
    `git diff 3fed439..HEAD -- .github/workflows/` → 唯一 hunk **`50 insertions / 0 deletions`**，
    `grep -c continue-on-error` → **0**，job 级 `if:` → **零命中**；
    `grep -rn "Server Script\|Client Script" tools/bootstrap/ docker-compose.yml` → **exit 1（零命中）**。
  · 判据：`git diff 3fed439..HEAD -- tools/gates/expected-red.txt` → **无输出**；
    `… -- tests/unit/test_compose_zero_dep.py` → 唯一 hunk **纯追加**。
  · 变异（审计员自做）：服务改名 / 删 `restart: "no"` / AI 变量进探针 / 脚本加脚本标签 →
    各自 `1 failed, 12 passed` 且红对了地方；三个文件 `shasum -a 256` 全部还原。
  · 绕过实验（审计员自做，**发现真洞**）：换挂载目录、把挂载写成变量 → 当时**都 `13 passed`**；
    补上 `::test_bootstrap_script_dir_is_mounted_literally` 后复现两条 → 各自 `1 failed, 13 passed`。
  · 结果面：`check_expected_red.py` → **0**；`pytest tests/unit -q` → **0**（补判据后 **193 passed**）；
    `pytest tests/contracts -q` → **0，151 passed**；`ruff check agenerp tests/unit tests/contracts` → **0**；
    `env -i … docker compose config -q` → **0**。
  · 冷起（审计员自做）：`down -v` → **0**；`up -d --wait --wait-timeout 300` → **0（76 秒）**；
    `curl -H "Host: frontend" http://127.0.0.1:18080/` → **200**，命中 **1** 次，`<title>Login</title>` 仍在；
    冷起后 live 门禁 → **0，`3 passed in 0.46s`**；幂等复跑 → **0**，引导日志「已是目标内容，跳过」。
  · CI（审计员逐字核对日志）：`gh run view 32499273158` → `conclusion=success`，`headSha=6ac1005a…`，**7 个 job 全绿**；
    `gates-l2` `15:44:57Z → 15:48:34Z`，门禁 step 逐字 **`3 passed in 2.68s`**，
    引导日志逐字「引导：首页横幅已写入（AI 能力状态）」，runner `28.0.4` / `Compose v2.38.2`。
    **plan 引的时间、通过数、版本号与日志逐条相符。**
- **修完之后的第二次 CI 复跑**（关闭审计的改动自己也上了 CI）：sha `bd32959`，run **`32501003150`**，`conclusion=success`，**七个 job 全绿**，含新增判据后的 `gates-l1` 与再跑一遍的 `gates-l2`。
- 审计轮次结论：iteration 1 `needs revision`（3 blocking + 5 nit）→ **三条 blocking 与 nit 1 全部就地修掉，
  一条都没有降级成 follow-up**；处置明细见 `## Closure Audit Record` 的 revision 段。

Follow-up:

- 无。**确认的缺陷没有出现在这里**：关闭审计提出的三条 blocking 与 nit 1（红线 7 判据的锚点可绕过）
  全部在本 plan 内就地修掉并复验；nit 2 / 3 为措辞与文档漂移，同样就地改准；
  nit 4（§14.2 的「三处」站点名计数）按红线外文档的「只增不改」纪律保留，§14.3 已标注它是本节落地前的计数；
  nit 5（`tests/contracts` 不在本 plan 的验证列表里）由审计员补跑并记入上方证据。
  余下的取舍与他人所有权项在 `## Deferred But Adjudicated`，其中「门禁每跑一轮留一条孤儿列」那条的
  承接文档 `docs/backlog/gate-fixtures-pollute-the-live-site.md` 已由本 plan 更正触发条件。
