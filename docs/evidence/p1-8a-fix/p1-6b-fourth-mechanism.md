# P1-6b 第四种机制存不存在 + 「为什么会重启」

> 取数：2026-08-26，零模型调用。
> ⚠️ 按 plan 第 7 轮改正：**「重启窗口」已升为具名方向 ③，不占本条的第三/第四机制名额**，
> 本条要查的是「**既非 B3 回包超时、既非起栈时序、也非 B7 重启窗口的第四种机制**」。

## 1. 同口径 sha 之间，产品代码有没有变

命令原文（逐对）：`git diff --stat <prev> <next> -- agenerp/ docker-compose.yml tools/nginx/`

| 对 | 三路径改动 |
|---|---|
| `e3afd77` → `758b7bc` | **零** |
| `758b7bc` → `82a144a` | **零** |
| `82a144a` → `7af5493` | **零** |
| `7af5493` → `cc205d6` | **零** |
| `cc205d6` → `f144475` | **零** |
| `f144475` → `f924ac6` | **零** |
| `f924ac6` → `7a217a2` | **零** |
| `7a217a2` → `fecbd59` | **零** |
| `fecbd59` → `d69b335` | **零** |

⇒ **同口径 10 个 sha 之间，`agenerp/` / `docker-compose.yml` / `tools/nginx/` 一个字节没变，
而结果是 3 红 7 绿。**⇒ **「同一份产品代码既红又绿」在本窗口内坐实。**
（⚠️ 这**不等于**「与代码无关」—— 只等于「红绿的差别不由这三路径的 diff 解释」。）

**不同口径那段单独查**（`f09b8f0` … `e3afd77^`，服务恒回 503）：三路径合计
`5 files changed, 408 insertions(+), 3 deletions(-)`（含 `tools/nginx/frappe.conf.template` 新增 213 行）。
**该段的结论不与上表混数。**
另记一格：`e3afd77^` → `e3afd77` 动的是 `.github/workflows/gates.yml`(+41/-13) 与 `docker-compose.yml`(+10) ——
即人修好 `AGENERP_LLM_BASE_URL` 变量名那一次，**这正是切分点本身**。

## 2. 逐条枚举：第四种机制

| 候选 | 查了没 | 结论与依据 |
|---|---|---|
| **端点侧延迟尖峰** | **查了** | **有支持证据，但它落在方向 ① 内部，不是第四种机制。** 依据：三路径零 diff（上表）⇒ 模型调用是这 10 个 run 之间唯一的外部变量；且真解释墙钟实测跨度 ≈3s → >30s（`p1-3`）。⚠️ **「长尾来自端点，还是来自解释 loop 自己的轮数/工具调用数」本轮分不开** —— 分开它需要回包里的 `cost` 账或耗时日志，`agenerp/serve/` 没有耗时日志（B6），junit 也没作为 artifact 上传（`gh api .../artifacts` ⇒ `total_count = 0`）。**记为方向 ① 内的一格未查明。** |
| **runner 网络** | **查了** | **无异常证据。** 依据：三次红的抛点都是 `recv_into`（TCP 已建立、请求已发出）；同一次 `失败取证` 里另有 24–25 条 live 判据**同时全过**，其中大量打 `127.0.0.1:8080`；且服务端在同一时刻正常处理并写出了 200（`BrokenPipeError` 栈帧在 `_respond(200, payload)` 之后）。 |
| **nginx `resolver … valid=10s` 重解析窗口** | **查了** | **无。** 依据：`tools/nginx/frappe.conf.template:70` 的 `resolver 127.0.0.11 valid=10s`，其失败形态是**该 location 回 502**（同处注释逐字写死）。实测三次红**没有一次是 502**，全是客户端 `TimeoutError`；且 `BrokenPipeError` 证明请求**确实到达了 `agenerp-serve`** ⇒ 名字解析成功。 |
| **OOM / 容器被杀** | **查了** | **日志侧无证据**（按人自己的标注读，不写成「已排除」）。人侧 `grep -inE "oom|killed|exit code 137|signal 9"` 全日志零命中；本轮补两条：10 个 run 的 backend 日志各只有 7 行、无异常退出；本机 13 个容器 `RestartCount` 全 `0`。⚠️ **零命中不等于没发生。** |
| **`expected-red.txt` 名单漂移** | **查了** | **无。** 10 个 run 的判定步逐字都是 `门禁 54 项`，项数一次没变；红的判据名全部落在 B3 指名那两条内。 |

⇒ **本条结论：`无（说明查过哪些）`。**
**没有找到一条既非 B3、非起栈时序、非重启窗口的具名第四机制。**
⚠️ 明确声明：**本条没有拿「重启窗口」交差**（plan 第 7 轮逐字禁止）。

## 3. 「为什么会重启」这一格

⚠️ **本轮的实测把这一格的**前提**推翻了**（`p1-5` §②③ 与 `p1-2` §5.2）：
CI 全部 10 个 run 的 backend 日志各只有**一套**启动序列，本机 `RestartCount` 全为 `0`，
而 `Up` < `CREATED` 的那一组容器**恰好等于（传递地）等 `create-site` 的那一组**。
⇒ **「整组 frappe 容器重启过一次」在本轮证据下不成立**，因此「为什么会重启」这个问题**没有对象**。

**但仍按 `P1-6b` 的要求逐条给「查了—有/无」，不整条略过**：

| 候选成因 | 查了没 | 结论 |
|---|---|---|
| entrypoint 的 `Linking fresh assets to volume...` 触发重启 | **查了** | **无。** 该行在每个 run 的 backend 日志里只出现 **1 次**，且**紧接着**就是同一次 `Starting gunicorn` ⇒ 它是**首次启动**的一步，不是重启的痕迹。 |
| compose `restart: on-failure` 策略被触发 | **查了** | **无。** 策略确实是 `on-failure`（`docker-compose.yml:40` 等），但本机 `RestartCount` 全 `0` ⇒ 该策略本轮从未生效。 |
| healthcheck 抖动导致容器被判死 | **查了** | **无。** `restart: on-failure` 不因 healthcheck 失败而重启容器（healthcheck 只影响 `depends_on: service_healthy` 与 `--wait`）；本机 `FailingStreak` 全 `0`。 |
| runner 资源（CPU/内存）压力 | **没查 —— 说明为什么** | CI 上没有资源采样步，取它要改 `.github/workflows/gates.yml`（红线 2 的判断题，`P2-1 (B)`），**Phase 1 明令不做**。⇒ 逐字记为「**没查**」，不记为「无」。 |

⚠️ **不许据此猜根因**（裁判规则 3、人自己的标注）：上表给的是「这四条各自有没有证据」，不是「重启的原因是 X」。
