# P1-8 机制陈述

> 要求：一句话说清「什么条件下会红」，且这句话的**每个成分都能指回上面某一格的数字**。

## 机制陈述

> **一轮 `gates-l2-live` 恰好发出 2 次真解释；当其中任意一次的服务端墙钟超过断言体写死的客户端预算
> `TIMEOUT = 30` 秒时，客户端在等回包处抛 `TimeoutError`，那一条判据红 ——
> 而服务端并没有坏：它随后仍把解释算完并去写 `200`，因对端已断开而抛 `BrokenPipeError`。
> 红是「这一次解释落在了 30 秒之外的长尾」，不是「连不上」、不是「服务没起来」、也不是「容器重启了」。**

## 逐个成分指回数字

| 成分 | 指回哪一格 |
|---|---|
| 「一轮恰好发 2 次真解释」 | `tests/unit/test_explain_service_body.py:212`（`resolves_to`，1 次）与 `:246`（`echoes_the_sid` 循环里的第 3 个请求，1 次）；同循环 `:247` 的 `{"role": …}` 在调模型**之前**就被 400（`:253` 那条判据正是判这个）。本轮独立复读 `grep -n "EXPLAIN_PATH\|def test_"` 确认，全文件只有这 2 处会走到模型 |
| 「客户端预算 30 秒」 | `tests/unit/test_explain_service_body.py:99` `TIMEOUT = 30` → `:125` 交给 `http.client.HTTPConnection(host, port, timeout=TIMEOUT)` |
| 「抛 `TimeoutError`，在等回包处」 | `758b7bc` 与 `82a144a` 两次红的 traceback **逐字相同**：`socket.py:718` `recv_into` ← `http/client.py:298` `readline` ← `:337` `getresponse()`。⇒ `conn.request()` 已成功、连接已建立 |
| 「服务端仍算完并去写 200」 | 同两次红的 `agenerp-serve` 日志：`app.py:329 do_POST → self._respond(200, payload)` → `app.py:377 self.wfile.write(body)` → `BrokenPipeError: [Errno 32] Broken pipe`；对端 `172.18.0.10` 是 compose 网内的 frontend(nginx) |
| 「次数对得上」 | `758b7bc`：`BrokenPipeError` **1 次** ↔ `失败取证` `1 failed`；`82a144a`：**2 次** ↔ `2 failed` |
| 「长尾」 | 真解释墙钟实测跨度：**本机 1.72s / 1.90s**（`--durations=0` 直接量到）· CI 绿 run 推算 **≈3–6s**（上界可证 < 17.5s）· CI 红 run 里成功那次推算 **≈13.3s** · 红那次 **> 30s**（客户端上限，上界未测出） |
| 「同一份代码既红又绿」 | 同口径 10 个 sha 逐对 `git diff --stat -- agenerp/ docker-compose.yml tools/nginx/` **9 对全空**；同一 sha `82a144a` 三个 attempt：红 / 绿 / 绿 |
| 「判定步墙钟随之摆动，而项数不变」 | 同一 sha `82a144a`：**70s（红）→ 33s（绿）→ 23s（绿）**，判定步原文一直是 `门禁 54 项` |
| 「不是连不上」 | 抛点是 `recv_into` 不是 `connect`；且 `BrokenPipeError` 证明请求确实到达了 `agenerp-serve` |
| 「不是服务没起来 / 起栈时序」 | `agenerp-serve` 与 `backend` 是 `create-site` 同一道闸上的平级容器，10 个 run 的 `Up` 值逐次相同；红的形态也不是 502（`resolver` 失败该有的形态） |
| 「不是容器重启」 | CI 10/10 run 的 backend 日志各只有**一套** `Linking fresh assets` + `Starting gunicorn`；本机 13 个容器 `RestartCount` **全 0**；`Up` < `CREATED` 的那组恰好等于（传递地）等 `create-site` 的那组，`websocket` 不在其中且实测无差值 |

## 🔴 这句话里**没有**的一格（必须写出来，不许含糊）

**「为什么某一次会落到 30 秒之外」本轮未查明。**

- 两条可能的来源本轮**分不开**：① **端点侧延迟尖峰**；② **解释 loop 自身的轮数/工具调用数在某些输入下变多**。
- 分开它需要**单次解释的耗时与 token 账**，而：`agenerp/serve/` 没有耗时日志（B6 实读）·
  junit 报告未作为 artifact 上传（`gh api …/artifacts` ⇒ `total_count = 0`）·
  给 CI 加探针要改 `.github/workflows/gates.yml`（红线 2 的判断题，`P2-1 (B)`，Phase 1 明令不做）。
- ⚠️ **裁判规则 3：不许猜根因。** 上面两条是**候选**，不是结论。

⇒ **这一格的缺失直接约束 Phase 2**：按 `P2-1 (H)` 与 `P3-6 绑定 5` 的既有规矩，
**任何「绕开长尾」而不解释长尾的修法都不算修掉了缺陷。**

## 三条具名方向的处置（Phase 1 Exit Criteria 要求三选一，不许留空）

| 方向 | 处置 | 依据 |
|---|---|---|
| **① B3 回包超时** | **坐实（作为失败形态）** | 两次红逐字相同的 `recv_into` 抛点 + 服务端 `BrokenPipeError` + 墙钟分布。⚠️ **但 B3 原来所依赖的前提「解释系统性地慢」被证伪** —— 中位数 1.7–13s ≪ 30s |
| **② 起栈时序（`depends_on`）** | **排除** | `agenerp-serve`/`backend` 平级同闸、10 run `Up` 值逐次相同；红的形态不是 502 也不是连接失败 |
| **③ B7 重启窗口** | **排除** | 按 `P1-2` 写死判据：绿 run 同样出现该差值（10/10）⇒ 不足以单独解释红；另三条证据显示**根本没发生重启** |
| **④ 第四种机制** | **无（说明查过哪些）** | `p1-6b` 逐条：端点侧长尾（落在 ① 内部）· runner 网络（无）· nginx resolver 窗口（无）· OOM（日志侧无证据）· 名单漂移（无） |

## B7 那处分歧的处置（Exit Criteria 单列的一条）

人写「断言逐字 `timed out`，**是连不上**，不是 502」；B2 实读的抛点是 `recv_into`（连接已建立）。

**处置：`没对上` —— 两侧数据都给出，人的那一半不成立。**

- 人的一侧依据的是**断言消息的字面**：`127.0.0.1:8080 够不到（timed out）—— 同源前端没在跑`。
  **那句是 `except OSError` 分支的固定文案**（`test_explain_service_body.py:133`），**不是运行时观测**。
- loop 这一侧依据的是 traceback 抛点与服务端日志：连接建立成功、请求送达、服务端算完写 200 时才 `EPIPE`。
- ⇒ **「连不上」不成立；正确的表述是「连上了，但回包没在 30 秒内到」。**
- ⚠️ **这不是人写错了就完事** —— 被误导的是**断言消息本身**，而它在 `tests/gates/**` 判据正文里（红线 1，loop 无权改）。
  该条已在 plan 的 `Deferred But Adjudicated` 登记，重开事件是「人裁定停机分支 A 时顺带处置这一句文案」。
  **本轮实测给它补上了一条新证据：这句文案已经第二次把取证带偏了**（第一次带偏了 WBS 行的命名，第二次带偏了人的归因）。
