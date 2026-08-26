# P3-2 / P3-3 —— 离线判据与变异自查（`D-26` 那次拆分的守卫）

> 产出者：loop（任务 `2026-08-26-094345-mission-driver`，Phase 3）。
> 基线：`BASE_3 = 182ef2a`（人落地 `D-26` 的那个提交，即本 plan 的**修复提交**）。
> ⚠️ **本轮 loop 对 `tests/unit/test_explain_service_body.py` 一个字节未改**（红线 1）——
> 修法是**人**在 `182ef2a` 落的，带 `Gates-Change-Approved-By: lize`。

## 1. P3-1：修法本身（loop 未落地，人已落地）

| | |
|---|---|
| 修复提交 | `182ef2a1c42f08c02fb432f385cfa9edfaf0bfe2` · author `lize <lize-agent-engineering@users.noreply.github.com>` · `2026-08-26 10:59:28 +0800` |
| 裁定 | `docs/masterplan/DECISIONS.md` `D-26` —— **「30 是测试便利值，不是产品承诺」**，改法逐字「**拆成两个预算，不是把 30 调大**」 |
| 落点 | `tests/unit/test_explain_service_body.py`：`TIMEOUT = 30` → `CHEAP_TIMEOUT = 30`（`:116`）+ `EXPLAIN_TIMEOUT = 180`（`:120`）；`_request()` 增 `timeout=CHEAP_TIMEOUT` 形参（`:139`）并把它传给 `HTTPConnection`（`:146`）；四个调用点改用长预算 |
| 它凭什么修掉 `P1-8` 那句机制陈述 | 机制陈述的承重成分逐字是「**当其中任意一次的服务端墙钟超过断言体写死的客户端预算 `TIMEOUT = 30` 时**，客户端在等回包处抛 `TimeoutError`」。`P1-3` 实测：真解释中位数 1.7–13s、长尾 > 30s（上界未测出）；服务端**没坏**（算完仍写 `200`，因对端已断开抛 `BrokenPipeError`，次数逐次相等）。⇒ 把**真解释那几发**的客户端预算抬到 180s，长尾就不再被误判成故障，**而便宜请求的 30s 判别力原样保留**。 |
| 残余风险（照实记，不粉饰） | **「为什么某一次会落到 30 秒之外」仍未查明**（`P1-8` 自己点明的那一格）。本修法让**正确性判据**不再被延迟长尾误判，**长尾本身还在**。`D-26` 的「翻案条件」②逐字写死：若长尾成因查明后表明 180s 仍不够，**说明问题不在预算，不要再调大**。 |

## 2. P3-2：离线判据

新增 `tests/unit/test_explain_service_timeout_budgets.py`（**6 条**，全部离线、零网络、零 docker）。
⚠️ **不在 `tests/gates/`**（红线 1），也**不改**断言体本身 —— 它**按路径把断言体加载进来**再驱动，
加载器与 `tests/unit/explain_fakes.py` 的 `load_repo_module` 是同一个。

| 判据 | 形态 | 它挡住什么 |
|---|---|---|
| `test_the_two_budgets_are_separate_and_the_merged_name_is_gone` | 常量 + **反向存在性** | 两个预算各自在、方向正确、`CHEAP_TIMEOUT ≤ 30`、`EXPLAIN_TIMEOUT ≥ 120`，**且合并回去的 `TIMEOUT` 这个名字必须不存在** |
| `test_the_budget_actually_reaches_the_socket` | **行为**（记录型假 `HTTPConnection`） | 「`timeout=` 是个被吞掉的形参」——**改成空壳** |
| `test_the_call_that_waits_on_the_model_gets_the_long_budget` | **行为**（真跑断言体那条「真 `sid` → 200」） | 真解释那一发被改回短预算；**同一次跑里对照**登录/认人仍是短预算 ⇒ 「整份文件一起放宽」在本条上分得开 |
| `test_the_sid_echo_loop_picks_its_budget_per_request` | **行为**（真跑 `echoes_the_sid` 那个循环） | 「为了少写一行就把整个循环放宽」——健康检查与 404 跟着拿 180s |
| `test_the_recorder_itself_would_notice_a_wrong_budget` | **自反** | 假连接自己不记录时上面三条恒绿 |
| `test_the_body_still_loads_from_its_pinned_path` | 存在性 | 源文件没了就是红，不是少跑几条判据 |

⚠️ **逐字回应 `P3-2` 那两条硬约束**：
① **不判「调得通」** —— 「`_request()` 能跑完」掏空之后照样成立；判的是**预算有没有真的到达 `HTTPConnection`**、
以及**哪个调用点拿到了哪一个预算**。
② **不是「两边读同一个常量再比」**（工作项 11 的 M5 窟窿）—— 6 条里 **3 条真的把断言体那几个函数跑起来**，
预算是从假连接**录下来的观测值**，不是从模块里读出来的同一个常量。

## 3. P3-3：变异自查（**7 条逐条打红，0 条打不红**）

⚠️ **变异施加在一份仓外副本上**（`/tmp/p18a-mut/mutant_body.py`），
经 `-p mutplugin` 把 `load_repo_module` 指向副本 —— **仓内的断言体从头到尾没有被写过一次**（红线 1）。

```
M1 合并回一个 TIMEOUT                   exit=1  打红 ✅  4 failed, 2 passed
M2 timeout= 是被吞掉的空壳形参          exit=1  打红 ✅  4 failed, 2 passed
M3 真解释那一发改回短预算               exit=1  打红 ✅  1 failed, 5 passed
M4 便宜请求的预算被放宽到 180           exit=1  打红 ✅  1 failed, 5 passed
M5 长预算只从 30 挪到 31                exit=1  打红 ✅  1 failed, 5 passed
M6 echoes 循环整体放宽                  exit=1  打红 ✅  1 failed, 5 passed
M7 timeout= 形参整个删掉                exit=1  打红 ✅  4 failed, 2 passed
```

**复原自证**（本轮从未写过它，仍逐字核 `sha256`）：

```
$ shasum -a 256 tests/unit/test_explain_service_body.py
52727509979112bc759ad5c79c086c27f5bd0c3f015aab876ece234de11fd45c
$ shasum -a 256 -c /tmp/p18a-mut/body.sha256
tests/unit/test_explain_service_body.py: OK
RESTORED OK
$ git status --porcelain -- tests/unit/test_explain_service_body.py tests/gates/ .github/
（无输出）
```

## 4. 一处**照实记下来但本轮不修**的不吻合

`D-26` 的「哪几处用长预算」一格**逐字**列了三处（真 `sid` 的解释调用 + `echoes_the_sid` 循环里
`path == EXPLAIN_PATH` 的两条），并**逐字**把「伪造 `sid`（401 挡下）」「非法参数（400 挡下）」留在短预算。

**而落地的代码里有第四处也用了长预算**：`test_explain_without_any_cookie_is_401_through_the_same_origin_front`
（`tests/unit/test_explain_service_body.py:201`）—— 没带 cookie，同样在 **401** 就被挡下、**根本到不了模型**。
按 `D-26` 自己那条理由（「到不了模型的保持短预算，因为它们卡住就是真故障」）**它该是短预算**。

⚠️ **loop 两条路都无权**：改代码要动断言体（**红线 1**），改说明要动 `DECISIONS.md`（**红线 3**）。
⇒ **既不修，也不写进判据**（写进去会让 `tests/unit` 当场红，而唯一的复绿路径在红线内）。
已登记在 plan `2026-08-25-1118-1` 的 `Deferred But Adjudicated`，重开事件写在那里。
**代价照实说**：那一发的短预算判别力丢了 —— 若同源前端在「无 cookie 401」这条路上真卡住，
门禁要 180 秒才失败退出，而不是 30 秒。**这不影响正确性判定，只影响失败时的反馈速度。**

## 5. P3-5：未触发

**本轮未改 `docker-compose.yml`、未改 `tools/nginx/**`** ⇒ `P3-5` 冷起自证与
`pytest tests/unit/test_compose_zero_dep.py` 两条**有条件命令未触发**。
自证：`git diff --name-only 182ef2a..HEAD -- docker-compose.yml tools/nginx/` → 无输出。
