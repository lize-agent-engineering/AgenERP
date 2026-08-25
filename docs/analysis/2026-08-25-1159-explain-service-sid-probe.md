# 探测记录 · 服务端拿浏览器 `sid` 认人这条链，在活站点上走不走得通（P1.8a 第 1 个 plan `E-a-1`）

> Plan: [`docs/plans/p1-insight/2026-08-25-1159-1-explain-http-service.md`](../plans/p1-insight/2026-08-25-1159-1-explain-http-service.md) Phase 1 `E-a-1`
> Date: 2026-08-25
> 基线 sha: `b557ffd6238ab19b87ef9c9f058abe89d96c214c`
> 站点: `frontend` @ `http://127.0.0.1:18080`（`docker compose ps` 实读九容器全部 `Up 27 hours`）
> **本记录里零 `sid` 真值。** 真 `sid` 全程只存在于探针进程的内存里，**一个字节没落盘**：
> 探针脚本本身写在 `/tmp` 且跑完即删，`sid` 从未被 `print`、未被写文件、未进任何命令行参数。
> 落盘前做过**反向自证**（见文末「零落盘自证」一节）。
> **本次探测零写操作**：三条 `GET` + 两条 `POST`，`POST` 只有 `/api/method/login` 与
> `/api/method/frappe.auth.get_logged_user`（后者是只读白名单方法）。

## 结论先行（四句）

1. **H3 吻合，并且是在本 plan 真正要走的那条代码路径上吻合的。**
   有效 `sid` 下 `frappe.auth.get_logged_user` 回 **HTTP 200** `{"message":"Administrator"}`，
   **`GET` 与 `POST` 两种方法都回同一个形状** —— 后者才是 `SiteClient.call_method()` 实际发的动词
   （`site.py:312` 逐字 `POST /api/method/<dotted.path>`）。
2. **无效 `sid` 与完全不带 `Cookie` 都回 HTTP 403，不是「200 + Guest」，也不是 200 空包。**
   ⇒ 经 `SiteClient._request()` 的非 2xx 分支变成 `SiteError`
   ⇒ 服务面把 `SiteError` 一律映射成 **401** 这件事**有实测支撑**，不是推测。
3. **两种失败在回包上可分辨，但服务面不打算分辨**：伪造 `sid` 的回包多一个 `"session_expired":1`，
   完全不带 `Cookie` 的没有。**本 plan 不使用这个差别**（见「一条被否决的诱惑」）。
4. **同一个 `sid` 客户端读得到单据**：`GET /api/resource/Item?limit_page_length=1` 回 **200**
   `{"data":[{"name":"HRD-ASSY-SVC"}]}` ⇒ `D-a-3` 选项 (iii)「字段表由服务端用调用者自己的
   `sid` 现取」在活站点上**是可行的**，不是纸面设计。

## 逐条实测

命令原文：一个 `/tmp` 下的 `python3` 探针（标准库 `urllib` + `http.cookiejar`，
与产品代码 `agenerp/site.py` 用的是同一套标准库），跑完 `rm -f` 删除。
所有请求带 `Host: frontend`（compose 栈按 Host 分站）。

| # | 输入 | 方法 · 路径 | 状态码 | 回包（前 200 字节） |
|---|---|---|---|---|
| a | 伪造 `sid=deadbeefdeadbeefdeadbeefdeadbeef` | `GET /api/method/frappe.auth.get_logged_user` | **403** | `{"session_expired":1,"exception":"frappe.exceptions.PermissionError: … Function <strong>frappe.auth.get_logged_user</strong> is not whitelisted.…"}` |
| b | 完全不带 `Cookie` | `GET /api/method/frappe.auth.get_logged_user` | **403** | `{"exception":"frappe.exceptions.PermissionError: … Login to access …"}`（**无 `session_expired`**）|
| c | `POST /api/method/login`（`Administrator`）| `POST /api/method/login` | **200** | cookie jar 里拿到 `sid`，**长度 56**（值不记录）|
| d | 有效 `sid`（走 cookie jar 自动带） | `GET /api/method/frappe.auth.get_logged_user` | **200** | `{"message":"Administrator"}` |
| e | 有效 `sid`（**显式 `Cookie: sid=…` 头**，与 `SiteClient._headers()` 的形态逐字相同） | `GET /api/method/frappe.auth.get_logged_user` | **200** | `{"message":"Administrator"}` |
| f | 有效 `sid`，**`POST`**（`call_method()` 实际用的动词） | `POST /api/method/frappe.auth.get_logged_user` | **200** | `{"message":"Administrator"}` |
| g | 伪造 `sid`，**`POST`** | `POST /api/method/frappe.auth.get_logged_user` | **403** | `{"session_expired":1,…}` |
| h | 有效 `sid` | `GET /api/resource/Item?limit_page_length=1` | **200** | `{"data":[{"name":"HRD-ASSY-SVC"}]}` |

**e 与 d 同形**这一条是要点：`SiteClient` 在 `sid` 模式下**只发一个 `Cookie: sid=…` 头**
（`site.py:415-425` 的 `_headers()` 逐字：给了 `sid` 就 `return`，**不再拼 `Authorization`**），
它与浏览器自带 cookie 走的是同一条服务端路径。

## 一条被否决的诱惑：拿 `session_expired` 分辨两种失败

回包差别（a 有 `"session_expired":1`，b 没有）**真实存在**，但服务面**不用它**，三条理由：

1. 它是 Frappe 的内部字段，不是本仓能控制的契约面 —— 今天有不代表下个 patch 版本还有；
2. 服务面已经在**请求解析那一层**分辨了这两件事：**根本没有 `sid`** 走的是本地分支
   （压根不打站点），**`sid` 认不出人**才会打到站点。两者本来就不需要靠回包区分；
3. 分辨出来之后**处置相同**（都是 401 + 一句固定文案）。给一个不改变行为的差别写解析代码，
   等于给将来的漂移留一个没有判据保护的面。

⇒ `D-a-4` 的映射表里两格都是 **401**，理由记在 §7.20。

## 一条实测出来的边界，照实记

**回包里 `Function … is not whitelisted` 这句话是误导性的**：`frappe.auth.get_logged_user`
**是**白名单方法，403 的真实原因是 Guest 身份不被允许调它。Frappe 把两类拒绝拼进了同一句文案。
⇒ **服务面绝不把这句站点原文透传给浏览器**（它会把「你没登录」说成「服务端方法名配错了」），
401 一律回本仓自己的固定文案。这一条同时也是判据⑨（响应体不含 `sid`、不透传站点原文）的一半理由。

## 零落盘自证

探针跑完后另跑一个**只在内存里**取 `sid` 前 8 位的自证脚本，对全仓与 `/tmp` 各 `grep -rIl` 一次：

```
GREP_HITS= 0      # /Users/lize/Claude/Projects/AgenERP 全仓，0 个文件命中
TMP_HITS=  0      # /tmp 全目录，0 个文件命中
```

自证脚本自己也 `rm -f` 删掉了（`ls` 复核：两份探针脚本均 `No such file or directory`）。
⚠️ **这条自证能证的与不能证的**：它证「那次会话的 `sid` 没有落在这两处磁盘上」；
它**不能**证「历史上任何 `sid` 都没落过盘」—— 后者不是一次 grep 能给的结论，本记录不提出那个主张。
