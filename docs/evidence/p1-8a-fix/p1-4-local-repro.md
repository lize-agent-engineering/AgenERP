# P1-4 本机把 B3 单独逼出来

> 2026-08-26 10:31 +0800，本机 `agenerp` 栈（`docker compose ls` ⇒ `running(10)`，已起 17 小时）
> ⚠️ 端口按 plan 写死的本机口径：**`18080`**（`docker port agenerp-frontend-1` ⇒ `8080/tcp -> 127.0.0.1:18080`；
> `8080` 被另一个 compose 项目占着，实测 `curl … :8080/agenerp/health` 回 **500**，`:18080` 回 **200**）。
> ⚠️ **CI 上不设该变量、走默认 8080** ⇒ 复现命令不许照抄。

## 命令原文与退出码

```
$ AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin \
  python3 -m pytest tests/gates/test_explain_service_live.py -q --durations=0 --no-header
......                                                                   [100%]
============================== slowest durations ===============================
1.90s call     tests/gates/test_explain_service_live.py::test_no_response_through_the_front_ever_echoes_the_sid
1.72s call     tests/gates/test_explain_service_live.py::test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to
0.35s call     tests/gates/test_explain_service_live.py::test_caller_claimed_context_is_rejected_through_the_front
0.04s call     tests/gates/test_explain_service_live.py::test_explain_with_a_forged_sid_is_401_and_never_falls_back
0.01s call     tests/gates/test_explain_service_live.py::test_health_is_200_through_the_same_origin_front
(13 durations < 0.005s hidden.  Use -vv to show these durations.)
6 passed in 4.05s
退出码 0
```

⚠️ **跑的是 `tests/gates/` 那份门禁本体（不是宽松副本）** —— 它把断言体里的 `pytest.skip` 换成 `pytest.fail`，
所以「6 passed」意味着**答案面那条真走了 200 分支**（服务若回 503，这一条会红而不是跳过）。
⚠️ **只是运行它，没有改它一个字节**（红线 1）。

## 直接量到的秒数（不是推算）

| 判据 | 本机墙钟 | 含几次真解释 |
|---|---|---|
| `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to` | **1.72s** | 1 次 |
| `test_no_response_through_the_front_ever_echoes_the_sid` | **1.90s** | 1 次（另 3 个请求在调模型前就被 401/400/404 掉） |
| 其余 4 条（不发真解释） | ≤ 0.35s | 0 |
| **整份门禁** | **4.05s** | **2 次** |

**该次运行确实发出了真解释**（而不是被 503 掉）的独立证据：
`test_the_user_…resolves_to` 内含 `total["total"] == total["prompt"] + total["completion"]` 这条成本账断言
（`tests/unit/test_explain_service_body.py:230-231`），它要求回包里有端点自报的 `usage`；
且本机 `agenerp-serve` 容器环境实测 `AGENERP_LLM_BASE_URL` / `AGENERP_LLM_API_KEY` / `AGENERP_LLM_MODEL` **三件套全非空**
（`docker inspect` 取，值未打印）。

## 结论

- **本机不复现。** 两条会发真解释的判据在本机各 **1.7–1.9 秒**跑完，
  离客户端预算 `TIMEOUT = 30` 差着一个数量级。
- 🔴 **按 D-16，这一条只能写成「本机不复现」，不得写成「B3 被证伪」。** 本机与 runner 是两台机器。
- ⚠️ **另有一处必须照实记的混淆项**：本机这一栈已起 17 小时，**本轮没有重跑 `agenerp.seedsite` 的三条装载命令**
  （CI 每次都装），⇒ **本机站点的数据量与 CI 不一定相同**，而解释 loop 的轮数/工具调用数随数据量变。
  ⇒ **本机的 1.7s 不能当作「CI 上也该是 1.7s」的证据**，它只能证明
  「**这条链路本身跑得完，且在数据量较小时非常快**」。
- ⇒ **`P1-4` 原本设想的「本机把 B3 逼出来」没有做到** —— B3 那条长尾在本机一次都没出现。
  **这一格逐字记为「本机未逼出」**，不修饰成别的。

## 额度记账

本次本机运行 = **2 次真解释**，进 `§8`（同一个 DashScope 额度池，`run id` 一列记 `本机`）。
