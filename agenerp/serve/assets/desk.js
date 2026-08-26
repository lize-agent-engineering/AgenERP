/* AgenERP · Desk ⌘K 侧边栏（plan 2026-08-25-1743-1 · 落点 module-boundaries.md §7.23）
 *
 * 由 agenerp/serve/app.py 的 ASSET_PATH 路由发出（不认人、不接受路径参数），
 * 经 nginx 那一跳同源送到 Desk 页面：tools/nginx/frappe.conf.template 的 AgenERP 哨兵段。
 *
 * 三条硬约束写在 §7.23，改这份文件之前先读它：
 *   1. 建 DOM 只走 textContent / createTextNode —— HTML 注入那一族 sink 在判据里是零命中。
 *   2. 渲染只取 user / answer / accepted / cost 四个已知键与状态码本身，
 *      整份响应体不进 DOM（sid 是 HttpOnly，别自己造一个绕过它的显示面）。
 *   3. 状态机是「开放枚举 + 兜底」。兜底态在任何时候都不许删 ——
 *      真实的 500（app.py 的 except Exception）与 504（proxy_read_timeout）封闭枚举接不住。
 */
(function () {
	"use strict";

	var MARK = {
		name: "agenerp-desk",
		version: "0.2.0",
		plan: "2026-08-25-1743-1",
	};

	// 只读 —— 页面上别的脚本改不动它，判「注入是否到位」时看到的就是本仓发出的那份。
	// ⚠️ 面板的可变状态挂在下面的 `state` 上，**不要为了挂状态把这个标记解冻**。
	try {
		Object.defineProperty(window, "agenerpDesk", {
			value: Object.freeze(MARK),
			writable: false,
			configurable: false,
			enumerable: true,
		});
	} catch (err) {
		// 已经挂过（例如注入了两次）：不抢、不覆盖，让「恰好 1 次」的失败可见。
		return;
	}

	var EXPLAIN_PATH = "/agenerp/explain";
	var TASK_CLASS = "explain";
	var PANEL_ID = "agenerp-desk-panel";

	// 面板侧可分辨的状态码。**十种来源折成九个码**：服务端八种 + 反代两种，
	// 而两个 502（服务端「上游模型坏了」/ 反代「agenerp-serve 不在」）在面板上必然合并 ——
	// 想分开只能靠嗅响应体，那撞上「响应体不进渲染面」那条禁令。合并是正确行为。
	// ⚠️ 这是**开放**枚举：没命中的码走 renderFallback，不是走空白。
	var CODE_TEXT = {
		400: "请求不合法（400）——服务端没收下这次提问",
		401: "未认到人（401）——站点不认这个会话",
		403: "当前身份取不到这张单据的字段表（403）",
		404: "这个路径服务不认（404）",
		405: "方法不对（405）",
		500: "服务内部出错（500）",
		502: "上游坏了，或解释服务不在（502）",
		503: "模型未配置（503）",
		504: "等太久，被反代掐断了（504）",
	};

	var state = {
		open: false,
		busy: false,
		lastFocus: null,
		root: null,
		input: null,
		output: null,
		hint: null,
	};

	function el(tag, cls, text) {
		var node = document.createElement(tag);
		if (cls) {
			node.className = cls;
		}
		if (text !== undefined && text !== null) {
			node.textContent = String(text);
		}
		return node;
	}

	function clear(node) {
		while (node.firstChild) {
			node.removeChild(node.firstChild);
		}
	}

	/* 当前单据上下文。优先级由 plan 的 H4 写死：URL 路径 > frappe.get_route() > cur_frm.doc。
	 *
	 * ⚠️ URL 只给「哪两段」，它给不出另外两件（实读见 §7.23.2）：
	 *   - slug 不是 doctype 名（`sales-order` 的真名是 `Sales Order`），原样发出去服务端必然取不到字段表；
	 *   - `/app/setup-wizard/0` 与 `/app/user/Administrator` 形状完全相同，URL 分不出页面路由与单据路由。
	 * 这两件由 Frappe 自己的 `frappe.router.routes`（slug → {doctype}）回答。
	 * 表拿不到、或 slug 不在表里 ⇒ 落到下一顺位；全都没有就是「无单据上下文」，
	 * 请求体一个键都不带（app.py 的 parse_request 要求 doctype 与 name 同时给或同时不给）。
	 */
	function doctypeForSlug(slug) {
		try {
			var routes = window.frappe && frappe.router && frappe.router.routes;
			if (!routes) {
				return null;
			}
			var hit = routes[slug];
			if (hit && hit.doctype) {
				return hit.doctype;
			}
		} catch (err) {
			return null;
		}
		return null;
	}

	function contextFromUrl() {
		var path = window.location && window.location.pathname;
		if (!path) {
			return null;
		}
		var segs = path.replace(/^\/app\/?/, "").split("/").filter(Boolean);
		if (segs.length < 2) {
			return null;
		}
		var doctype = doctypeForSlug(decodeURIComponent(segs[0]));
		if (!doctype) {
			return null;
		}
		return { doctype: doctype, name: decodeURIComponent(segs[1]) };
	}

	function contextFromRoute() {
		try {
			var route = frappe.get_route();
			if (route && route.length >= 3 && route[0] === "Form" && route[1] && route[2]) {
				return { doctype: String(route[1]), name: String(route[2]) };
			}
		} catch (err) {
			return null;
		}
		return null;
	}

	function contextFromForm() {
		try {
			var doc = window.cur_frm && cur_frm.doc;
			if (doc && doc.doctype && doc.name) {
				return { doctype: String(doc.doctype), name: String(doc.name) };
			}
		} catch (err) {
			return null;
		}
		return null;
	}

	function currentContext() {
		return contextFromUrl() || contextFromRoute() || contextFromForm() || null;
	}

	function buildPanel() {
		var root = el("aside", "agenerp-desk-panel");
		root.id = PANEL_ID;
		root.setAttribute("role", "dialog");
		root.setAttribute("aria-label", "AgenERP 解释");
		root.style.cssText =
			"position:fixed;top:0;right:0;width:380px;max-width:92vw;height:100%;" +
			"z-index:2147483000;background:#fff;border-left:1px solid #d1d8dd;" +
			"box-shadow:-2px 0 12px rgba(0,0,0,.12);display:flex;flex-direction:column;" +
			"padding:16px;gap:10px;font-size:13px;line-height:1.6;overflow:auto;";

		var title = el("div", "agenerp-desk-title", "AgenERP 解释");
		title.style.cssText = "font-weight:600;font-size:14px;";

		var hint = el("div", "agenerp-desk-hint", "");
		hint.style.cssText = "color:#8d99a6;";

		var input = el("textarea", "agenerp-desk-input");
		input.setAttribute("rows", "3");
		input.setAttribute("placeholder", "问一句关于当前单据的话，回车发送");
		input.style.cssText =
			"width:100%;box-sizing:border-box;padding:8px;border:1px solid #d1d8dd;border-radius:4px;font:inherit;";

		var send = el("button", "agenerp-desk-send", "发送");
		send.setAttribute("type", "button");
		send.style.cssText =
			"align-self:flex-start;padding:6px 14px;border:1px solid #d1d8dd;border-radius:4px;" +
			"background:#f4f5f6;cursor:pointer;font:inherit;";

		var output = el("div", "agenerp-desk-output");
		output.setAttribute("aria-live", "polite");
		output.style.cssText = "white-space:pre-wrap;word-break:break-word;";

		root.appendChild(title);
		root.appendChild(hint);
		root.appendChild(input);
		root.appendChild(send);
		root.appendChild(output);

		state.root = root;
		state.input = input;
		state.output = output;
		state.hint = hint;

		send.addEventListener("click", function () {
			ask();
		});
		input.addEventListener("keydown", function (event) {
			if (event.key === "Enter" && !event.shiftKey) {
				event.preventDefault();
				ask();
			}
		});

		document.body.appendChild(root);
		return root;
	}

	function describeContext() {
		var ctx = currentContext();
		if (!ctx) {
			return "当前不在单据页 —— 这次提问不带单据上下文";
		}
		return "当前单据：" + ctx.doctype + " / " + ctx.name;
	}

	/* ---- 渲染：每一态都非空、可分辨、含状态码字面量；一条都不通向空白或永久 spinner ---- */

	function say(text) {
		clear(state.output);
		state.output.appendChild(el("div", "agenerp-desk-line", text));
	}

	function renderPending() {
		// ⚠️ 这不是「永久 spinner」：ask() 的每一条出路（成功 / 失败 / 网络层抛）都会覆盖它。
		say("正在问……（还没有回音）");
	}

	function renderOk(data) {
		clear(state.output);
		// ⚠️ 这一行里的 `200` 不是装饰：判据要求十种态**各含自己那个码的字面量**，
		// 否则「答案面」与别的态在可见文本上分不出来（answer 的内容是模型给的，不受控）。
		state.output.appendChild(el("div", "agenerp-desk-status", "答出来了（200）"));
		var answer = data && typeof data.answer === "string" ? data.answer : "";
		state.output.appendChild(el("div", "agenerp-desk-answer", answer || "服务回了空回答"));
		var who = data && data.user ? String(data.user) : "";
		if (who) {
			state.output.appendChild(el("div", "agenerp-desk-user", "回答给：" + who));
		}
		if (data && data.accepted === false) {
			state.output.appendChild(el("div", "agenerp-desk-accepted", "未被判定为可接受"));
		}
		var cost = data && data.cost;
		if (cost) {
			state.output.appendChild(
				el("div", "agenerp-desk-cost", "本次开销：calls " + cost.calls + " · total " + cost.total)
			);
		}
	}

	function renderCode(status, detail) {
		var head = CODE_TEXT[status];
		if (!head) {
			renderFallback(status);
			return;
		}
		clear(state.output);
		state.output.appendChild(el("div", "agenerp-desk-status", head));
		if (detail) {
			state.output.appendChild(el("div", "agenerp-desk-detail", String(detail)));
		}
	}

	/* 兜底态。**任何时候都不许删** —— 服务端会长出新码，而封闭枚举接不住新码。
	 * ⚠️ 它只渲染状态码 + 一句固定文案，**一个字节都不碰响应体**：
	 * 真 nginx 502 / 504 回的是默认 HTML 不是 JSON，在这里假设响应体形状就会抛，
	 * 抛出去就是一个空白面板 —— 而所有打桩判据仍然全绿。
	 */
	function renderFallback(status) {
		say("未预期的响应（" + status + "）——服务回了一个面板还不认识的码");
	}

	function renderTransportFailure(reason) {
		say("请求没能发出去（" + reason + "）");
	}

	/* 只从响应里取 §1.3 那四个已知键。解析失败不抛给调用方，回 null 由调用方走码分支。 */
	function readKnownKeys(payload) {
		if (!payload || typeof payload !== "object") {
			return null;
		}
		return {
			user: payload.user,
			answer: payload.answer,
			accepted: payload.accepted,
			cost: payload.cost,
		};
	}

	function ask() {
		if (state.busy) {
			return;
		}
		var question = (state.input.value || "").trim();
		if (!question) {
			say("先写一句要问的话");
			return;
		}
		state.busy = true;
		renderPending();

		// 请求体只放这四个键。fields / role / view / actions / user 是越权向量，
		// 服务端对它们一律 400 —— 带上就是必然 400，而那种 400 在界面上和「问题不合法」长得一样。
		var body = { question: question, task_class: TASK_CLASS };
		var ctx = currentContext();
		if (ctx) {
			body.doctype = ctx.doctype;
			body.name = ctx.name;
		}

		var status = 0;
		fetch(EXPLAIN_PATH, {
			method: "POST",
			credentials: "same-origin",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		})
			.then(function (response) {
				status = response.status;
				return response.text().then(
					function (raw) {
						return raw;
					},
					function () {
						return "";
					}
				);
			})
			.then(function (raw) {
				var payload = null;
				try {
					payload = JSON.parse(raw);
				} catch (err) {
					payload = null;
				}
				if (status === 200) {
					var known = readKnownKeys(payload);
					if (known) {
						renderOk(known);
					} else {
						renderFallback(status);
					}
					return;
				}
				var detail = payload && typeof payload.error === "string" ? payload.error : "";
				renderCode(status, detail);
			})
			.catch(function (err) {
				renderTransportFailure(err && err.message ? err.message : "网络层失败");
			})
			.then(function () {
				state.busy = false;
			});
	}

	/* ---- 唤起 / 关闭 / 焦点归还 ---- */

	function open() {
		if (state.open) {
			return;
		}
		state.lastFocus = document.activeElement;
		if (!state.root) {
			buildPanel();
		}
		state.root.style.display = "flex";
		state.hint.textContent = describeContext();
		state.open = true;
		state.input.focus();
	}

	function close() {
		if (!state.open) {
			return;
		}
		state.root.style.display = "none";
		state.open = false;
		var back = state.lastFocus;
		state.lastFocus = null;
		// 元素可能已经不在文档里了（Desk 是 SPA，路由一换就重建）——不还就是了，不抛。
		if (back && typeof back.focus === "function" && document.contains(back)) {
			back.focus();
		}
	}

	function toggle() {
		if (state.open) {
			close();
		} else {
			open();
		}
	}

	// ⌘K / Ctrl+K 唤起与关闭；Esc 关闭。
	// H3 实测：Frappe v15 的 frappe.ui.keys.handlers 里没有 "k"（awesomebar 走 ctrl+g），
	// 真按下去 defaultPrevented=false ⇒ 这个键位没被占，不抢任何既有绑定。
	document.addEventListener(
		"keydown",
		function (event) {
			if (event.key === "Escape" && state.open) {
				event.preventDefault();
				close();
				return;
			}
			if ((event.metaKey || event.ctrlKey) && !event.shiftKey && !event.altKey) {
				var key = event.key ? String(event.key).toLowerCase() : "";
				if (key === "k") {
					event.preventDefault();
					toggle();
				}
			}
		},
		true
	);

	console.log("[agenerp] desk.js " + MARK.version + " loaded (plan " + MARK.plan + ")");
})();
