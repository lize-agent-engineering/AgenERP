# P1-6 复跑记录（同一 sha 原样重跑）

> 裁判规则 3：**复跑优先于分析。复跑不出来就记「不可复现」，不许猜根因。**
> 目标 sha：**`82a144a`**（run `32841381171`，原始 attempt 1 为 `failure`）
> ⚠️ **§8 记账：本节两次重跑一律标注「取证用，预期红」，与「本该绿却红了」分开计。**
> ⚠️ **重跑口径**：`gh run rerun` 产生的是**同一 run id 下的新 attempt**，不是新 run
> ⇒ **本节三个 attempt 一律不得计入 P3-6 那三次验收。**

## 命令原文与退出码

```
$ gh run rerun 32841381171 --failed --repo lize-agent-engineering/AgenERP     # 2026-08-26T02:19:50Z
（无输出，exit 0）
$ gh run rerun 32841381171 --repo lize-agent-engineering/AgenERP             # 2026-08-26T02:25:08Z
（无输出，exit 0）
```

## 三个 attempt 的逐次结果（同一 sha `82a144a`，三路径零 diff）

| attempt | 触发 | `gates-l2-live` job | 判定步原文 | 判定步墙钟 | 红的判据名 |
|---|---|---|---|---|---|
| 1（原始） | `push` 2026-08-25T11:15:29Z | `97781428215` **failure** | `门禁 54 项：红 1，绿 53，跳过 0` | **70s** | `test_no_response_through_the_front_ever_echoes_the_sid` |
| 1 的 `失败取证` 步（同一 job 内、同一个栈、约 1 分钟后原样重跑 26 条 live 门禁） | — | — | `2 failed, 24 passed, 28 deselected in 81.20s` | 81s | **两条都红**（多出 `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`） |
| **2** | `gh run rerun --failed` 2026-08-26T02:19:50Z | `98038161648` **success** | `门禁 54 项：红 0，绿 54，跳过 0` | **33s** | 无 |
| **3** | `gh run rerun` 2026-08-26T02:25:08Z | `98039087598` **success** | `门禁 54 项：红 0，绿 54，跳过 0` | **23s** | 无 |

## 结论（照实写，不修饰）

1. **红没有复现。** 同一 sha 原样重跑 **2 次，2 次全绿**。
   ⇒ 按裁判规则 3，**「`82a144a` 那次红」在本轮复跑下逐字记为「不可复现」。**
2. **但「间歇」这件事本身被复跑坐实了，而且是在两个层级上：**
   - **attempt 之间**：同一 sha、三路径零 diff，attempt 1 红、attempt 2/3 绿。
   - **单个 job 内部**：attempt 1 的判定步红 **1** 条，约 1 分钟后 `失败取证` 步在**同一个栈上**
     原样重跑同一批门禁，红的是 **2** 条。⇒ **同栈、同代码、相隔 1 分钟，结果不同。**
3. **判定步墙钟在同一 sha 上的跨度是 23s → 70s（3 倍）**，而门禁项数一次没变（`54 项` × 3）
   ⇒ **变的不是「跑了多少判据」，是「每次真解释等了多久」。**（与 `p1-3` 的推算一致。）
4. **attempt 3 的 ps 指纹与红 attempt 同形**：`backend` `CREATED 2 minutes ago` / `Up 46 seconds`，
   `websocket` `Up 2 minutes`，`db` `Up 2 minutes` ⇒ **绿 attempt 上同样有那个差值**
   —— 这是「方向 ③ 不足以单独解释红」在**同一 sha** 上的又一次实证。

## 额度记账

- attempt 2：绿 run ⇒ **2 次真解释**（`失败取证` 步 `skipped`，未翻倍）。
- attempt 3：绿 run ⇒ **2 次真解释**。
- **本节合计 4 次真解释**，两次都**预期红而实际绿** —— 照实记，不改预测（`predictions.md` §5b 那格不吻合）。
