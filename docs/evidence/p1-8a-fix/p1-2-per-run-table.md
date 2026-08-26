# P1-2 逐 run 表（同口径 10 个 run，零模型调用取得）

> 取数时刻：2026-08-26 10:10–10:20 +0800，执行者 loop（`2026-08-26-094345-mission-driver`）
> ⚠️ 本表**未照抄 plan 里任何一个数**（`P1-2` 逐字要求），全部现取。
> 命令原文：
> ```
> gh run list --workflow=gates.yml -L 14 --json databaseId,headSha,conclusion,event,status,createdAt
> gh api /repos/lize-agent-engineering/AgenERP/actions/jobs/<job_id>/logs
> gh api /repos/lize-agent-engineering/AgenERP/actions/jobs/<job_id>   # 取 steps 的 started_at/completed_at
> ```

## 0. 口径切分（B1 的切分点未变，计数已现算）

- **同口径**（`e3afd77` 及其之后，AI 变量名已修好、答案面能真调模型）：**10 个 run，3 红 7 绿，连绿 7 次。**
  ⚠️ **plan 第 7 轮记的「3 红 5 绿 / 样本 8」在本轮取数时已过期** —— 新增 `fecbd59`（run `32920159448`）与
  `d69b335`（run `32920289578`）两次绿。**B1 第五次被 CI 追上。**
- **不同口径**（`f09b8f0` … `e3afd77^`，服务恒回 503、不调模型）：13 次红，**本表不与上段混数**。

## 1. 主表

| sha | run id | job id | 结论 | 判定步原文 | 判定步墙钟 | 起栈步墙钟 | `失败取证` 步 |
|---|---|---|---|---|---|---|---|
| `e3afd77` | 32838495432 | 97772598288 | **红** | `门禁 54 项：红 2，绿 52，跳过 0` | 86s | 131s | **该步当时还不存在**（`758b7bc` 才引入，`git log -S"失败取证"` 实证） |
| `758b7bc` | 32839163713 | 97774627334 | **红** | `门禁 54 项：红 1，绿 53，跳过 0` | 76s | 134s | 65s，`1 failed, 25 passed, 28 deselected in 64.49s (0:01:04)` |
| `82a144a` | 32841381171 | 97781428215 | **红** | `门禁 54 项：红 1，绿 53，跳过 0` | 70s | 129s | 81s，`2 failed, 24 passed, 28 deselected in 81.20s (0:01:21)` |
| `7af5493` | 32841842429 | 97782873503 | 绿 | `门禁 54 项：红 0，绿 54，跳过 0` | 35s | 133s | skipped |
| `cc205d6` | 32846332776 | 97796776119 | 绿 | 同上 | 35s | 129s | skipped |
| `f144475` | 32849370852 | 97806423158 | 绿 | 同上 | 35s | 132s | skipped |
| `f924ac6` | 32850335965 | 97809514596 | 绿 | 同上 | 34s | 131s | skipped |
| `7a217a2` | 32853424473 | 97819531021 | 绿 | 同上 | 32s | 124s | skipped |
| `fecbd59` | 32920159448 | 98032018332 | 绿 | 同上 | 32s | 127s | skipped |
| `d69b335` | 32920289578 | 98032396897 | 绿 | 同上 | 30s | 113s | skipped |

## 2. 红的判据名（判定步自己打的名单，逐字）

- `e3afd77`：**两条** —— `test_no_response_through_the_front_ever_echoes_the_sid` · `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`
- `758b7bc`：**一条** —— `test_no_response_through_the_front_ever_echoes_the_sid`
- `82a144a`：**一条** —— `test_no_response_through_the_front_ever_echoes_the_sid`

⇒ **三次红全部落在 B3 指名的「唯二会发真解释」那两条之内，没有第三条判据名出现。**
⇒ 按 `P1-2` 写死的判据：**没有出现「红在 `_request` 之外」的形态**，B3 这条线不被排除。

⚠️ **同一 job 内的一次天然复跑，必须照实记**：`82a144a` 的**判定步**打的是「红 1」，
而约 1 分钟后 `失败取证` 步把同一批 live 门禁在**同一个栈上原样重跑**，结果是 **2 failed**
（多出 `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`）。
⇒ **同 sha、同栈、相隔 1 分钟，红的条数不同** —— 间歇性在单个 job 内部就已被实测到。
（`758b7bc` 的同一对比是 1 红 → 1 红，红的是同一条。）

## 3. traceback 的异常类型与抛点（不是那句写死的中文文案）

`758b7bc` 与 `82a144a` 两次的抛点**逐字相同**：

```
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/http/client.py:337:
>       line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/http/client.py:298:
>               return self._sock.recv_into(b)
E               TimeoutError: timed out
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/socket.py:718: TimeoutError
```

⇒ **异常类型 `TimeoutError`，抛点 `socket.py:718` 的 `recv_into`，上游帧是 `http/client.py:298` 的 `readline`
（再上游 `:337` 是 `getresponse()` 读状态行）。**
⇒ **`conn.request()` 已经成功、TCP 连接已建立、请求已发出**，超时发生在**等回包**那一段。
⇒ 断言消息印的那句「`127.0.0.1:8080` 够不到（timed out）—— 同源前端没在跑」是
`except OSError` 分支的**固定文案**（`tests/unit/test_explain_service_body.py:133`），**与实际形态不符**。
**B2 的实读在两次红上都复现了。**

## 4. 🔴 服务端侧的对应证据（本轮新取，plan 前七轮均无）

`失败取证` 步尾部 `docker compose logs agenerp-serve --tail 60` 在**两次红上都打出了同一形状的服务端异常**：

```
Exception occurred during processing of request from ('172.18.0.10', 44618)
Traceback (most recent call last):
  ...
  File "/opt/agenerp/agenerp/serve/app.py", line 329, in do_POST
    self._respond(200, payload)
  File "/opt/agenerp/agenerp/serve/app.py", line 377, in _respond
    self.wfile.write(body)
  ...
BrokenPipeError: [Errno 32] Broken pipe
```

- `758b7bc`：该块出现 **1 次**，该次 `失败取证` 是 **1 failed**。
- `82a144a`：该块出现 **2 次**，该次 `失败取证` 是 **2 failed**。
- `172.18.0.10` 是 compose 网络内的 **frontend（nginx）** 容器地址，即 `agenerp-serve` 的上游客户端。

⇒ **服务端把解释算完了、正在写 `200` 的响应体，而客户端已经先走了。**
⇒ 与客户端侧 `TimeoutError`（等回包超时）**对上同一条时间线**：
判据体 `TIMEOUT = 30` 到点 → pytest 断开 → nginx 随之断上游 → `agenerp-serve` 写 200 时 `EPIPE`。
⇒ **红的形态不是「连不上」，也不是「服务没算出来」，是「算得比 30 秒慢」。**

## 5. 🔴 ps 重启指纹（B7 那一格，`if: always()`，红绿 run 都有，零模型调用）

`取证 —— 服务状态` 步的 `docker compose ps`，按服务记 `CREATED` 与 `STATUS` 的 `Up`：

| 服务 | `e3afd77` **红** | `758b7bc` **红** | `82a144a` **红** | `7af5493` 绿 | `d69b335` 绿 |
|---|---|---|---|---|---|
| db | 3m ago / Up 3m | 4m / Up 4m | 4m / Up 4m | 2m / Up 2m | 2m / Up 2m |
| redis-cache | 3m / Up 3m | 4m / Up 4m | 4m / Up 4m | 2m / Up 2m | 2m / Up 2m |
| redis-queue | 3m / Up 3m | 4m / Up 4m | 4m / Up 4m | 2m / Up 2m | 2m / Up 2m |
| websocket | 3m / **Up 3m** | 4m / **Up 3m** | 4m / **Up 4m** | 2m / **Up 2m** | 2m / **Up ~1m** |
| backend | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / Up ~1m | 2m / Up 55s |
| agenerp-serve | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / Up ~1m | 2m / Up 55s |
| queue-long | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / Up ~1m | 2m / Up 55s |
| queue-short | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / Up ~1m | 2m / Up 55s |
| scheduler | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / Up ~1m | 2m / Up 55s |
| frontend | 3m / Up ~1m | 4m / Up 2m | 4m / Up 2m | 2m / **Up 56s** | 2m / Up 49s |

（`cc205d6` / `f144475` / `f924ac6` / `7a217a2` / `fecbd59` 五个绿 run 的形状与 `7af5493` / `d69b335` **完全同形**，
逐 run 原文见 `p1-2-raw/`。）

### 5.1 按 `P1-2` **写死的判据**读

判据原文：「**红 run 普遍出现 frappe 系容器 `Up` 远小于 `CREATED`、而绿 run 不出现** ⇒ 「重启窗口」**坐实**；
**绿 run 同样出现** ⇒ 重启确实发生但**不足以单独解释红**」。

**实测结果：绿 run 同样出现，且 10 个 run 无一例外、形状一致。**
⇒ **按判据的第二支：这一格不足以单独解释红。方向 ③ 不坐实。**

### 5.2 🔴 而且这个差值**不是重启**（本轮另取的两条证据，超出原判据的范围，照实记）

- **证据 a（CI 侧）**：`取证 —— backend 日志`（`if: always()`，`--tail 200`）在**全部 10 个 run 上**都只有 **7 行**，
  其中 `Linking fresh assets to volume...` **1 次**、`Starting gunicorn` **1 次**。
  容器重启后 `docker compose logs` 仍保留重启前的输出 ⇒ **真重启过就会看到两套启动序列，实测只有一套。**
- **证据 b（本机侧，`docker inspect` 实取，零模型调用）**：本机 `agenerp` 栈 13 个容器
  **`RestartCount` 全为 `0`**，而 `Created` → `StartedAt` 的差正好复刻 CI 那个形状：
  `db`/`redis-*` +0.4s · `configurator` +6s · `create-site`/`websocket` +9s ·
  `backend`/`queue-long`/`queue-short`/`scheduler`/`bootstrap-homepage` **+57s** · `frontend` **+62s**。
- **证据 c（compose 图，实读）**：`x-backend-defaults` 锚点（`docker-compose.yml:38-51`）给
  `backend` / `queue-short` / `queue-long` / `scheduler` 都挂了
  `create-site: condition: service_completed_successfully`；`agenerp-serve:331-333` 同样只等 `create-site`；
  `frontend:374-386` 等 `backend`+`websocket`+`bootstrap-homepage`；而 `websocket:243-245` **只等 `configurator`**。
  ⇒ **`Up` 落后于 `CREATED` 的那一组，恰好就是（传递地）等 `create-site` 的那一组**，
  `websocket` 不在其中 —— 这正是实测里 `websocket` 没有差值的原因。

⇒ **`docker compose up` 是「先把全部容器 create 出来，再按依赖次序 start」**，
`CREATED` 与 `Up` 的差 = **等 `create-site` 建站的那段时间**，不是一次重启。

🔴 **因此 B7 ② 那条人写的推断「整组 frappe 容器在起栈约 2 分钟后集体重启过一次」，
在本轮取到的三条证据下不成立。**
⚠️ **这不是「人写错了所以不用管」** —— 人给的那份 ps 原文是真的、也是本 plan 眼下最便宜的一格证据来源；
被证伪的只有「`Up` < `CREATED` ⇒ 重启」这一步**读法**。
⚠️ 按 D-16，证据 b 是本机数据、**不能外推到 runner**；承重的是证据 a（CI 侧）与证据 c（compose 图），
证据 b 只是把「差值 = 启动次序」这个读法在一个可 `inspect` 的环境里做实。
