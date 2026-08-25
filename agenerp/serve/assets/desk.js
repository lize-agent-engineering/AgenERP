/* AgenERP · Desk 注入接缝的自证脚本（plan 2026-08-25-1615-1 · 落点 module-boundaries.md §7.22）
 *
 * 这是本仓第一段会被浏览器执行的 JS。它**只证明自己到了**，不做别的：
 * 不注册快捷键、不发任何请求、不碰 DOM（⌘K 侧边栏是工作项 11 第 2 个 plan 的面）。
 *
 * 由 agenerp/serve/app.py 的 ASSET_PATH 路由发出（不认人、不接受路径参数），
 * 经 nginx 那一跳同源送到 Desk 页面：tools/nginx/frappe.conf.template 的 AgenERP 哨兵段。
 */
(function () {
	"use strict";

	var MARK = {
		name: "agenerp-desk",
		version: "0.1.0",
		plan: "2026-08-25-1615-1",
	};

	// 只读 —— 页面上别的脚本改不动它，判「注入是否到位」时看到的就是本仓发出的那份。
	try {
		Object.defineProperty(window, "agenerpDesk", {
			value: Object.freeze(MARK),
			writable: false,
			configurable: false,
			enumerable: true,
		});
	} catch (err) {
		// 已经挂过（例如注入了两次）：不抢、不覆盖，让 H7 那格「恰好 1 次」的失败可见。
		return;
	}

	console.log("[agenerp] desk.js " + MARK.version + " loaded (plan " + MARK.plan + ")");
})();
