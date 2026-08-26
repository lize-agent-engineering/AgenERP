# P1-5 「起栈时序」这条方向：证实还是排除

> 取数：2026-08-26，零模型调用。
> 分工按 plan 第 7 轮改正后的写法：**「重启是否发生」在 CI 上取**（`P1-2` §5，`gates.yml:349-351` 现成那步）；
> **`RestartCount` / `StartedAt` / `Health.Status` 的精确值在本机取**。
> ⚠️ **未改 `.github/workflows/gates.yml`**（`P2-1 (B)` 那条路本轮不走，红线 2 一个字不放宽）。

## ① `agenerp-serve` 是不是真在 `backend` 之前起？

**实读 `docker-compose.yml`**：

- `x-backend-defaults`（`:38-51`，`backend` / `queue-short` / `queue-long` / `scheduler` 共用）
  ⇒ `configurator: service_completed_successfully` + `create-site: service_completed_successfully`
- `agenerp-serve`（`:331-333`）⇒ **只**等 `create-site: service_completed_successfully`
- `frontend`（`:374-386`）⇒ 等 `backend`(healthy) + `websocket`(healthy) + `bootstrap-homepage`(completed)
- `websocket`（`:243-245`）⇒ **只**等 `configurator`

⇒ **`agenerp-serve` 与 `backend` 是同一道闸（`create-site` 建站完成）上的两个平级容器**，
不存在「`agenerp-serve` 先于 `backend`」这回事 —— **`depends_on` 的字面差异（缺 `backend` 那一格）在实际启动次序上不产生先后。**

**CI 侧实测印证**（`P1-2` §5 那张表）：**全部 10 个 run 里，`agenerp-serve` 与 `backend` 的 `Up N` 逐次完全相同**
（红 run `Up 2 minutes` / `Up 2 minutes`，绿 run `Up 55 seconds` / `Up 55 seconds`，等等）。

⇒ **人写的那条「已知线索」的后半句（`agenerp-serve.depends_on` 缺 `backend`）文本为真，但它不产生时序后果。**
（前半句已由人自己在 `7a217a2` 撤销，B4 也独立实读过。）

## ② ③ `RestartCount` / `StartedAt` / `Health.Status`（本机实取）

命令原文：

```
for c in $(docker ps -a --filter "name=^agenerp-" --format '{{.Names}}' | sort); do
  docker inspect "$c" --format '{{.Name}}|Created={{.Created}}|StartedAt={{.State.StartedAt}}|RestartCount={{.RestartCount}}|Health={{if .State.Health}}{{.State.Health.Status}}|FailStreak={{.State.Health.FailingStreak}}{{else}}none{{end}}|RestartPolicy={{.HostConfig.RestartPolicy.Name}}'
done
```

输出逐字（2026-08-26 10:17 +0800，本机 `agenerp` 栈，`docker compose ls` ⇒ `running(10)`）：

| 容器 | Created | StartedAt | Created→Started | RestartCount | Health |
|---|---|---|---|---|---|
| db | 09:18:26.373 | 09:18:26.797 | **+0.4s** | **0** | healthy |
| redis-cache | 09:18:26.373 | 09:18:26.800 | **+0.4s** | **0** | healthy |
| redis-queue | 09:18:26.374 | 09:18:26.799 | **+0.4s** | **0** | healthy |
| configurator | 09:18:26.462 | 09:18:32.511 | +6.0s | **0** | none |
| create-site | 09:18:26.579 | 09:18:35.613 | +9.0s | **0** | none |
| websocket | 09:18:26.580 | 09:18:35.611 | **+9.0s** | **0** | healthy |
| backend | 09:18:26.656 | 09:19:23.234 | **+56.6s** | **0** | healthy |
| bootstrap-homepage | 09:18:26.656 | 09:19:23.254 | +56.6s | **0** | none |
| queue-long | 09:18:26.666 | 09:19:23.248 | +56.6s | **0** | none |
| queue-short | 09:18:26.664 | 09:19:23.245 | +56.6s | **0** | none |
| scheduler | 09:18:26.664 | 09:19:23.254 | +56.6s | **0** | none |
| frontend | 09:18:26.744 | 09:19:28.960 | **+62.2s** | **0** | healthy |
| agenerp-serve | 10:39:54.505 | 10:39:55.847 | +1.3s | **0** | healthy |

（⚠️ `agenerp-serve` 的 `Created` 晚于其余容器 —— 该容器在本机被单独重建过一次，与本 plan 无关；
它的 `RestartCount` 同样是 `0`。）

**读法**：
- **`RestartCount` 全为 `0`** ⇒ 本机这一栈**从未有过任何一次容器重启**。
- 而 `Created → StartedAt` 的差**恰好复刻了 CI 上那个「`Up` 远小于 `CREATED`」的形状**：
  等 `create-site` 的那一组 **+57s**，`frontend` 再多等 backend healthy **+62s**，`db`/`redis`/`websocket` 几乎为 0。

⇒ **`docker compose up` 的语义是「先把全部容器 create 出来，再按依赖次序 start」**，
`CREATED` 与 `Up` 的差 = **等上游依赖那段时间**，**不是一次重启**。

⚠️ **按 D-16，本机数据不能外推到 runner。** 它能做的只有一件事：
**证伪「`Up` < `CREATED` ⇒ 一定发生过重启」这个读法**（在一个 `RestartCount` 可直接读的环境里，
同样的形状对应 `RestartCount = 0`）。
**承重的 runner 侧证据是另外两条**：CI 全部 10 个 run 的 backend 日志都**只有一套**
`Linking fresh assets to volume...` + `Starting gunicorn`（重启会留下两套）；以及 compose 依赖图本身。

## 结论

- **方向 ②「起栈时序（`depends_on`）」：排除。**
  依据：`agenerp-serve` 与 `backend` 平级同闸、10 个 run 的 `Up` 值逐次相同；
  且红的形态是**连接已建立后等回包超时**（`recv_into`），不是「服务还没起来」应有的连接失败或 502。
- **方向 ③「B7 重启窗口」：不坐实。**
  依据两条，逐条独立：
  ① 按 `P1-2` **写死的判据**：绿 run 与红 run **同样**出现该差值（10/10 同形）⇒ 按判据第二支，**不足以单独解释红**；
  ② 超出原判据范围的三条新证据（CI backend 日志单套启动序列 · 本机 `RestartCount = 0` · compose 依赖图）
  指向**根本没有发生重启**，那个差值是启动次序。
- ⚠️ **③ 的第二条不等于「人取的证据没用」** —— 人给的 ps 原文是真的、且是本 plan 唯一零额度的证据入口；
  被证伪的只有「`Up` < `CREATED` ⇒ 重启」这一步**读法**。
