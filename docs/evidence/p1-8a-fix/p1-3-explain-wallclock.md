# P1-3 一次真实解释在 runner 上要多久（B6 那格空白）

> 取数：2026-08-26，零模型调用（全部由已有 run 的日志与 step 时间戳反解）
> 命令原文：`gh api /repos/lize-agent-engineering/AgenERP/actions/jobs/<job_id>` 取 `steps[].started_at/completed_at`
> ⚠️ **本节给出的是「推算秒数」，不是探针直接量到的秒数。** 推算的算式、输入与假设全部写在下面，可复核可推翻。
> ⚠️ **没有走「加探针」那条路** —— 那要改 `.github/workflows/gates.yml`（红线 2 的判断题，`P2-1 (B)`），Phase 1 明令不做。

## 1. 直接观测到的量（无推算）

**判定步（`python3 tools/gates/check_expected_red.py`，跑全部 54 项，`pytest tests/gates -q --tb=no`，实读该脚本 `:73-81` 确认是单进程顺序跑、无 xdist）的墙钟：**

| run | 结论 | 判定步墙钟 |
|---|---|---|
| `e3afd77` | 红 2 | **86s** |
| `758b7bc` | 红 1 | **76s** |
| `82a144a` | 红 1 | **70s** |
| `7af5493` | 绿 | **35s** |
| `cc205d6` | 绿 | **35s** |
| `f144475` | 绿 | **35s** |
| `f924ac6` | 绿 | **34s** |
| `7a217a2` | 绿 | **32s** |
| `fecbd59` | 绿 | **32s** |
| `d69b335` | 绿 | **30s** |

**`失败取证` 步里 pytest 自己打的汇总行（只跑 26 条 live 门禁）：**

- `758b7bc`：`1 failed, 25 passed, 28 deselected in 64.49s (0:01:04)`
- `82a144a`：`2 failed, 24 passed, 28 deselected in 81.20s (0:01:21)`

## 2. 推算（算式写死，假设写死）

**假设**（两条，都可推翻）：
- ① 一次超时的判据恰好消耗 `TIMEOUT = 30` 秒（客户端上限，`tests/unit/test_explain_service_body.py:99`）；
- ② 同一份 26 条 live 门禁里，**非解释**那 24 条的耗时在两次 `失败取证` 之间大致相同。

设 `A` = 24 条非解释 live 门禁的合计耗时，`E` = **一次成功的真解释**耗时。

```
82a144a： 30 + 30 + A = 81.20   ⇒  A = 21.20s
758b7bc： 30 +  E + A = 64.49   ⇒  E = 64.49 - 30 - 21.20 = 13.29s
```

⇒ **`758b7bc` 那一轮里，成功的那次真解释 ≈ 13.3 秒；同一轮里另一次 > 30 秒（被客户端掐断）。**

**绿 run 的上界（不依赖假设②）**：判定步整段（54 项，含 **2 次**成功真解释）最短 **30s**、最长 **35s**
⇒ **单次成功真解释在绿 run 上必然 < 17.5 秒，且两次相加 < 35 秒。**
把 `A = 21.20s` 代进去（此时依赖假设②）⇒ 2 次解释 + 28 条非 live 门禁 ≈ **9–14s** ⇒ **单次 ≈ 3–6 秒**。

## 3. 结论（P1-3 要求的那个秒数）

> **一次真实解释在 runner 上的墙钟不是一个数，是一条尾巴很长的分布：
> 绿 run 上单次 ≈ 3–6 秒（上界可证 < 17.5 秒）；红 run 上成功那次 ≈ 13.3 秒；
> 而红的那次 > 30 秒 —— 且服务端事后仍算完了（见下）。**

🔴 **这一条直接推翻了 B3 那条方向所依赖的前提**：
`tools/nginx/frappe.conf.template:71-77` 的注释写 `proxy_read_timeout 300` 的理由是
「单次解释实测 9.7 万–12.8 万 token」，读起来像「解释系统性地很慢，30 秒当然不够」。
**实测不是这样：绝大多数解释在 3–13 秒内跑完，30 秒的客户端预算在中位数上绰绰有余。**
红的不是「解释慢」，是**「偶尔有一次落在 30 秒之外的长尾」**。

## 4. 红那次的下界证据：服务端把它算完了

`失败取证` 步尾部的 `agenerp-serve` 容器日志，在 `758b7bc`（1 次）与 `82a144a`（2 次）上都打出：

```
File "/opt/agenerp/agenerp/serve/app.py", line 329, in do_POST
  self._respond(200, payload)
File "/opt/agenerp/agenerp/serve/app.py", line 377, in _respond
  self.wfile.write(body)
BrokenPipeError: [Errno 32] Broken pipe
```

⇒ **服务端走到了 `_respond(200, payload)`** —— 解释算完了、`payload` 也拼好了，
只是往回写时对端已断。**`BrokenPipeError` 的次数与该次 `失败取证` 的 `failed` 条数逐次相等（1↔1，2↔2）。**
⇒ **红那次的真解释耗时 > 30 秒，但有限**（服务端没有吊死，也没有 OOM／崩溃）。
⚠️ **超出多少，本轮量不出来** —— 服务端日志无时间戳，junit 报告未作为 artifact 上传
（`gh api .../artifacts` ⇒ `total_count = 0`），而加时间戳/传 artifact 都要改 `.github/`。
**这一格逐字记为「下界 > 30s，上界未测出」。**
