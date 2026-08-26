# `tests/gates` 与 `tests/tools` 同进程跑会互相污染环境 —— 整仓 `pytest tests -q -m "not live"` 因此 12 error

> Status: `deferred`（**登记，不处置**；处置需要人排期）
> Created: 2026-08-26
> 由 plan `docs/plans/p1-insight/2026-08-25-1118-1-gates-l2-live-intermittent-red.md` 的收口步产出
> ⚠️ 本条**不在**那个 plan 的 `Goals` 里（它的范围是 `frontend` 起栈时序缺陷），
> 是跑 `Closure Gates` 第 4 条那句「整仓验证」时撞见的，**已在该 plan 的
> `Deferred But Adjudicated` 逐字登记，不是静默丢弃**

## 事实（2026-08-26 在 `main` @ `f3ff580` 上实跑，不是推理）

| # | 命令 | 输出 |
|---|---|---|
| 1 | `python3 -m pytest tests -q -m "not live"` | `1301 passed, 33 deselected, **12 errors**` |
| 2 | `python3 -m pytest tests/tools/test_live_conformance.py -q -m "not live"` | `12 skipped` —— **单独跑是 skip，符合该文件头部逐字写的「无凭据 / 无站点时 skip」** |
| 3 | `python3 -m pytest tests/contracts tests/tools -q -m "not live"` | `232 passed, 12 skipped` —— 不触发 |
| 4 | `python3 -m pytest tests/unit tests/tools -q -m "not live"` | `888 passed, 12 skipped, 6 deselected` —— 不触发 |
| 5 | `python3 -m pytest tests/gates tests/tools -q -m "not live"` | `109 passed, 26 deselected, **12 errors**` —— **触发** |

⇒ **触发条件锁定在「`tests/gates` 与 `tests/tools` 进同一个 pytest 进程」。**

12 个 error 全在 `tests/tools/test_live_conformance.py`，报文逐字：

```
Failed: 没有活站点：设置 AGENERP_SITE 与站点凭据后重跑
—— 在门禁里这是**红**，不是跳过。
```

## 未查明的一格（不许猜根因）

**具体是哪个 fixture / 哪一行把站点相关的环境留在了进程环境里，本轮没查。**
方向（**是方向不是结论**）：`tests/tools/test_live_conformance.py` 的 skip 判定走 `agenerp.site.client_from_env`，
它读 `AGENERP_SITE`；而 `tests/gates/**` 里有门禁会设置站点环境。**未经证实，不得当结论用。**

## 为什么此刻不阻塞

- **CI 从不触发它**：`.github/workflows/gates.yml:570-584` 把 `tests/unit` / `tests/contracts` / `tests/tools` / `tests/routing`
  **逐目录分开跑**，`tests/gates` 走的是 `tools/gates/check_expected_red.py` 另一条路
  ⇒ 这两个目录从未进过同一个 pytest 进程。
- 门禁判据本身不受影响（`check_expected_red.py` → `门禁 28 项：预期红 0，绿 28，跳过 0`，exit 0）。

## 代价（照实说，不淡化）

任何人手跑整仓 `pytest tests -q -m "not live"` 会看到 12 个 error，**看起来像仓库坏了，其实是测试间环境泄漏**。
这让「整仓一把跑」这条最直觉的自检手段失效 —— 而它恰恰是新人和外部审计员最可能先跑的那一条。

## 重开事件

**任何人把「整仓一把跑」写进某条验收命令时，这一条立刻从 `deferred` 变成阻塞项。**
