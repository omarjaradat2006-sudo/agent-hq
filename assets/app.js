/* Agent HQ front end. Static: reads data/<team>/state.json + metrics.json, refreshes every 60s. */
(function () {
  const CFG = window.HQ_CONFIG;
  const ROOT = document.documentElement.dataset.root || "./";
  const TEAM = document.documentElement.dataset.team || null; // null = hub
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const NS = "http://www.w3.org/2000/svg";
  const sv = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const safeUrl = u => { try { const p = new URL(u); return /^https?:$/.test(p.protocol) ? p.href : null; } catch { return null; } };
  const STATUS_COLOR = { working: "#6fd3ff", idle: "#a37bff", waiting: "#ffc864", error: "#ff7a8e", off: "#4b4566", ok: "#5fe0a0" };
  const STATUS_TEXT = { working: "Working", idle: "Idle", waiting: "Waiting", error: "Error", off: "Not hired", ok: "Done" };

  function ago(iso) {
    if (!iso) return "never"; const t = new Date(iso).getTime(); if (isNaN(t)) return "—";
    const s = Math.round((Date.now() - t) / 1000);
    if (s < 0) return until(iso);
    if (s < 60) return "just now"; if (s < 3600) return Math.floor(s / 60) + "m ago";
    if (s < 86400) return Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m ago";
    return Math.floor(s / 86400) + "d ago";
  }
  function until(iso) {
    if (!iso) return ""; const s = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
    if (isNaN(s)) return ""; if (s <= 0) return "any minute";
    if (s < 3600) return "in " + Math.ceil(s / 60) + "m"; return "in " + Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m";
  }
  const clock = iso => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); };
  const fmtNum = n => (typeof n === "number" ? (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e4 ? (n / 1e3).toFixed(1) + "K" : n.toLocaleString()) : (n ?? "—"));

  async function getJSON(path) {
    try { const r = await fetch(ROOT + path + "?t=" + Date.now(), { cache: "no-store" }); if (!r.ok) return null; return await r.json(); } catch { return null; }
  }

  /* ---------- Nav ---------- */
  function renderNav() {
    const nav = $("#nav"); if (!nav) return; nav.replaceChildren();
    const a = el("a", null, "HQ"); a.href = ROOT; if (!TEAM) a.setAttribute("aria-current", "page"); nav.append(a);
    CFG.teams.forEach(t => { const l = el("a", null, t.name); l.href = ROOT + t.id + "/"; if (TEAM === t.id) l.setAttribute("aria-current", "page"); nav.append(l); });
  }

  /* ---------- Isometric floor ---------- */
  const TW = 112, TH = 56;
  function iso(cx, cy, x, y, z = 0) { return [cx + (x - y) * TW / 2, cy + (x + y) * TH / 2 - z]; }
  const pts = a => a.map(p => p.join(",")).join(" ");
  const SLOTS = [[-2.6, -0.6], [-0.6, -2.6], [1.8, -2.4], [2.6, -0.2], [2.4, 2.0], [0.2, 2.7], [-2.2, 2.2], [-2.9, 0.9]];

  function drawFloor(svg, center, nodes, wallItems) {
    svg.replaceChildren();
    const W = 980, H = 700, cx = W / 2, cy = 372;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const P = (x, y, z) => iso(cx, cy, x, y, z);
    const defs = sv("defs", {}, svg);
    const g1 = sv("radialGradient", { id: "fglow", cx: "50%", cy: "50%", r: "60%" }, defs);
    sv("stop", { offset: "0%", "stop-color": "#3b2580", "stop-opacity": ".55" }, g1); sv("stop", { offset: "100%", "stop-color": "#0b0914", "stop-opacity": "0" }, g1);
    const blur = sv("filter", { id: "blur", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); sv("feGaussianBlur", { stdDeviation: "6" }, blur);

    const R = 4.2, WH = 120;
    // back walls with research panels
    const wallL = [P(-R, -R, 0), P(-R, R, 0), P(-R, R, WH), P(-R, -R, WH)];
    const wallR = [P(-R, -R, 0), P(R, -R, 0), P(R, -R, WH), P(-R, -R, WH)];
    sv("polygon", { points: pts(wallL), fill: "#120f20", stroke: "#2a2442" }, svg);
    sv("polygon", { points: pts(wallR), fill: "#151226", stroke: "#2a2442" }, svg);
    const items = (wallItems || []).slice(0, 12);
    const PANEL_COLORS = ["#6fd3ff", "#a37bff", "#ffc864", "#ff7ab8", "#5fe0a0"];
    for (let i = 0; i < 12; i++) {
      const onLeft = i < 6, k = onLeft ? i : i - 6;
      const a0 = -R + 0.5 + k * 1.3, a1 = a0 + 1.0;
      const z0 = 28, z1 = 96;
      const poly = onLeft ? [P(-R, a0, z0), P(-R, a1, z0), P(-R, a1, z1), P(-R, a0, z1)] : [P(a0, -R, z0), P(a1, -R, z0), P(a1, -R, z1), P(a0, -R, z1)];
      const it = items[i]; const col = PANEL_COLORS[i % PANEL_COLORS.length];
      const p = sv("polygon", { points: pts(poly), fill: it ? col : "#1d1932", "fill-opacity": it ? ".22" : "1", stroke: it ? col : "#2a2442", "stroke-opacity": it ? ".9" : "1" }, svg);
      if (it) { sv("title", {}, p).textContent = (it.title || "") + (it.metric ? " — " + it.metric : "");
        for (let l = 0; l < 3; l++) { const zz = z1 - 14 - l * 12; const ln = onLeft ? [P(-R, a0 + .15, zz), P(-R, a1 - .15 - l * .2, zz)] : [P(a0 + .15, -R, zz), P(a1 - .15 - l * .2, -R, zz)]; sv("polyline", { points: pts(ln), stroke: col, "stroke-opacity": ".55", "stroke-width": "2" }, svg); } }
    }
    // floor
    sv("ellipse", { cx, cy: P(0, 0, 0)[1], rx: 480, ry: 250, fill: "url(#fglow)" }, svg);
    const floor = [P(-R, -R), P(R, -R), P(R, R), P(-R, R)];
    sv("polygon", { points: pts(floor), fill: "#0e0b1a", stroke: "#a37bff", "stroke-width": "2", "stroke-opacity": ".9" }, svg);
    sv("polygon", { points: pts(floor), fill: "none", stroke: "#a37bff", "stroke-width": "8", "stroke-opacity": ".25", filter: "url(#blur)" }, svg);
    for (let i = -3; i <= 3; i++) {
      sv("line", { x1: P(i, -R)[0], y1: P(i, -R)[1], x2: P(i, R)[0], y2: P(i, R)[1], stroke: "#2a2442", "stroke-width": "1" }, svg);
      sv("line", { x1: P(-R, i)[0], y1: P(-R, i)[1], x2: P(R, i)[0], y2: P(R, i)[1], stroke: "#2a2442", "stroke-width": "1" }, svg);
    }
    // links from center to nodes (L shaped along grid)
    const placed = nodes.slice(0, SLOTS.length).map((n, i) => ({ n, x: SLOTS[i][0], y: SLOTS[i][1] }));
    placed.forEach(({ n, x, y }) => {
      const path = [P(0, 0, 2), P(x, 0, 2), P(x, y, 2)];
      const d = "M" + path.map(p => p.join(",")).join(" L");
      const col = STATUS_COLOR[n.status] || STATUS_COLOR.idle;
      sv("path", { d, fill: "none", stroke: col, "stroke-opacity": n.status === "off" ? ".15" : ".45", "stroke-width": "2" }, svg);
      if (n.status === "working") {
        for (let k = 0; k < 2; k++) {
          const c = sv("circle", { r: "3.5", fill: col }, svg);
          const am = sv("animateMotion", { dur: "2.6s", repeatCount: "indefinite", begin: (k * 1.3) + "s", path: d }, c);
          am.setAttribute("keyPoints", "1;0"); am.setAttribute("keyTimes", "0;1"); am.setAttribute("calcMode", "linear");
        }
      }
    });
    // pods sorted back-to-front
    const all = [{ n: center, x: 0, y: 0, big: true }, ...placed].sort((a, b) => (a.x + a.y) - (b.x + b.y));
    all.forEach(({ n, x, y, big }) => drawPod(svg, P, n, x, y, big));
  }

  function drawPod(svg, P, n, x, y, big) {
    const s = big ? 0.85 : 0.6, h = big ? 22 : 14;
    const col = STATUS_COLOR[n.status] || STATUS_COLOR.idle;
    const g = sv("g", { class: n.status === "working" ? "working" : "" }, svg);
    if (n.href) { g.style.cursor = "pointer"; g.addEventListener("click", () => location.href = n.href); }
    const top = [P(x - s, y - s, h), P(x + s, y - s, h), P(x + s, y + s, h), P(x - s, y + s, h)];
    const left = [P(x - s, y + s, h), P(x + s, y + s, h), P(x + s, y + s, 0), P(x - s, y + s, 0)];
    const right = [P(x + s, y - s, h), P(x + s, y + s, h), P(x + s, y + s, 0), P(x + s, y - s, 0)];
    sv("polygon", { points: pts(left), fill: "#1b1630", stroke: col, "stroke-opacity": ".35" }, g);
    sv("polygon", { points: pts(right), fill: "#231c3d", stroke: col, "stroke-opacity": ".35" }, g);
    sv("polygon", { points: pts(top), fill: "#2b2250", stroke: col, "stroke-width": "1.5" }, g);
    const [tx, ty] = P(x, y, h);
    sv("ellipse", { class: "ring", cx: tx, cy: ty, rx: big ? 46 : 30, ry: big ? 23 : 15, fill: "none", stroke: col, "stroke-width": "2" }, g);
    // screens on the desk
    const scr = big ? 3 : 2;
    for (let i = 0; i < scr; i++) {
      const off = (i - (scr - 1) / 2) * (big ? 0.5 : 0.45);
      const a = P(x + off - 0.18, y - s + 0.12, h), b = P(x + off + 0.18, y - s + 0.12, h);
      const sh = big ? 30 : 22;
      sv("polygon", { points: pts([a, b, [b[0], b[1] - sh], [a[0], a[1] - sh]]), fill: col, "fill-opacity": n.status === "off" ? ".08" : ".28", stroke: col, "stroke-opacity": ".8" }, g);
    }
    // core orb
    const orbY = ty - (big ? 34 : 24);
    sv("circle", { cx: tx, cy: orbY, r: big ? 18 : 11, fill: col, opacity: ".35", filter: "url(#blur)" }, g);
    sv("circle", { class: "pod-core", cx: tx, cy: orbY, r: big ? 9 : 6, fill: col }, g);
    for (let k = 0; k < 3; k++) sv("rect", { class: "beam", x: tx - 1 + (k - 1) * 6, y: orbY - 6, width: 2, height: 8, rx: 1, fill: col, style: `animation-delay:${k * 0.6}s;opacity:0` }, g);
    // label
    const [lx, ly] = P(x, y, 0);
    const name = sv("text", { x: lx, y: ly + (big ? 40 : 30), "text-anchor": "middle", fill: "#efecf8", "font-size": big ? 14 : 12, "font-weight": 600 }, g); name.textContent = n.name;
    const st = sv("text", { x: lx, y: ly + (big ? 57 : 45), "text-anchor": "middle", fill: col, "font-size": 10.5 }, g);
    st.textContent = (STATUS_TEXT[n.status] || n.status || "").toUpperCase();
    sv("title", {}, g).textContent = n.name + " — " + (n.doing || STATUS_TEXT[n.status] || "");
  }

  /* ---------- Shared renderers ---------- */
  function renderLog(list, items) {
    list.replaceChildren();
    if (!items.length) { const li = el("li"); li.append(el("time", null, "")); li.append(el("span", "muted", "No activity yet. The first run will show up here.")); list.append(li); return; }
    items.slice(0, 80).forEach(e => {
      const li = el("li"); const t = el("time", null, clock(e.t)); t.title = new Date(e.t).toLocaleString(); li.append(t);
      const sp = el("span"); if (e.agent) { sp.append(el("b", null, e.agent)); sp.append(document.createTextNode(" ")); } sp.append(document.createTextNode(e.msg || "")); li.append(sp); list.append(li);
    });
  }
  function statusPill(s) { return el("span", "pill s-" + (s || "idle"), STATUS_TEXT[s] || s || "Idle"); }

  /* ---------- Team page ---------- */
  let filter = "pending";
  function issueUrl(action, idea) {
    const title = `${action}: ${idea.id}`;
    const body = `Decision from Agent HQ.\n\nIdea: ${idea.title || ""}\nTeam: ${TEAM}\n\n(Just press "Submit new issue". The agents read this and update the site.)`;
    return `https://github.com/${CFG.repo}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  }
  function renderIdeas(state) {
    const box = $("#ideas"), tabs = $("#tabs"); if (!box) return;
    const ideas = state.ideas || [];
    const S = [["pending", "To review"], ["approved", "Approved"], ["filmed", "Filmed"], ["rejected", "Passed"]];
    tabs.replaceChildren();
    S.forEach(([k, l]) => { const b = el("button", null, l); b.setAttribute("aria-pressed", String(filter === k)); b.append(el("span", "n", String(ideas.filter(i => (i.status || "pending") === k).length))); b.onclick = () => { filter = k; renderIdeas(state); }; tabs.append(b); });
    box.replaceChildren();
    const list = ideas.filter(i => (i.status || "pending") === filter).sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
    if (!list.length) { const e = el("div", "empty"); e.append(el("strong", null, ideas.length ? "Nothing in this list" : "No ideas yet")); e.append(el("span", null, ideas.length ? "Ideas land here when you change their status." : "The copywriter adds ideas with hooks and full scripts after each research run.")); box.append(e); return; }
    list.forEach(i => {
      const c = el("article", "idea"); const top = el("div", "idea-top"); top.append(el("h3", null, i.title || "Untitled"));
      const tags = el("div", "row"); if (i.format) tags.append(el("span", "pill s-idle", i.format)); if (i.score != null) tags.append(el("span", "small", "Fit " + i.score + "/10")); top.append(tags); c.append(top);
      if (i.hook) c.append(el("div", "hook", i.hook)); if (i.why) c.append(el("div", "why", i.why));
      if (i.script) { const d = el("details"); d.append(el("summary", null, "Full script")); d.append(el("div", "script", i.script)); c.append(d); }
      if (Array.isArray(i.sources) && i.sources.length) { const s = el("div", "sources"); s.append(el("span", "muted", "Based on:")); i.sources.forEach(x => { const u = safeUrl(x.url); if (u) { const a = el("a", null, x.title || "source"); a.href = u; a.target = "_blank"; a.rel = "noopener"; s.append(a); } }); c.append(s); }
      const act = el("div", "row"); const st = i.status || "pending";
      const add = (label, action, cls) => { const a = el("a", "btn " + (cls || ""), label); a.href = issueUrl(action, i); a.target = "_blank"; a.rel = "noopener"; act.append(a); };
      if (st === "pending") { add("Approve", "approve", "primary"); add("Pass", "pass"); }
      else if (st === "approved") { add("Mark filmed", "filmed", "primary"); add("Back to review", "review"); }
      else add("Back to review", "review");
      act.append(el("span", "small", "Added " + ago(i.createdAt) + (i.decisionPending ? " · decision received, updating…" : "")));
      c.append(act); box.append(c);
    });
  }
  function renderResearch(state) {
    const box = $("#research"); if (!box) return; box.replaceChildren();
    const items = []; (state.research || []).slice(0, 3).forEach(r => (r.items || []).forEach(x => items.push(x)));
    if (!items.length) { const e = el("div", "empty"); e.append(el("strong", null, "No research yet")); e.append(el("span", null, "Videos in your niche doing unusually well show up here with why they worked.")); box.append(e); return; }
    const w = el("div", "wall");
    items.slice(0, 12).forEach(x => { const s = el("div", "shot"); const u = safeUrl(x.url); const t = el(u ? "a" : "div", "t", x.title || x.creator || "Video"); if (u) { t.href = u; t.target = "_blank"; t.rel = "noopener"; } s.append(t); const m = [x.creator, x.metric].filter(Boolean).join(" · "); if (m) s.append(el("div", "m", m)); if (x.whyItWorks) s.append(el("p", null, x.whyItWorks)); w.append(s); });
    box.append(w);
  }
  function renderMetrics(metrics) {
    const box = $("#metrics"); if (!box) return; box.replaceChildren();
    if (!metrics || metrics.status === "needs_setup" || !(metrics.kpis || []).length) {
      const e = el("div", "empty"); e.append(el("strong", null, metrics && metrics.status === "needs_setup" ? "Waiting for access" : "No stats yet"));
      e.append(el("span", null, (metrics && metrics.message) || "Once your account is connected, the data collector pulls your stats every hour.")); box.append(e); return;
    }
    const k = el("div", "kpis"); metrics.kpis.forEach(m => { const d = el("div", "kpi"); d.append(el("div", "v", fmtNum(m.value))); d.append(el("div", "k", m.label)); if (m.delta != null) { const n = Number(m.delta); d.append(el("div", "d " + (n >= 0 ? "up" : "down"), (n >= 0 ? "+" : "") + fmtNum(n) + (m.deltaLabel ? " " + m.deltaLabel : ""))); } k.append(d); }); box.append(k);
    const vids = metrics.topVideos || [];
    if (vids.length) { const sc = el("div", "scroll"); sc.style.marginTop = "14px"; const t = el("table", "vids"); const hr = el("tr"); ["Video", "Views", "Likes", "Posted"].forEach((h, i) => { const th = el("th", null, h); if (i && i < 3) th.style.textAlign = "right"; hr.append(th); }); t.append(hr);
      vids.slice(0, 10).forEach(v => { const r = el("tr"); const td = el("td"); const u = safeUrl(v.url); const a = el(u ? "a" : "span", null, v.title || "Untitled"); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } td.append(a); r.append(td); r.append(el("td", "n", fmtNum(v.views))); r.append(el("td", "n", fmtNum(v.likes))); r.append(el("td", null, v.published ? new Date(v.published).toLocaleDateString() : "")); t.append(r); });
      sc.append(t); box.append(sc); }
    box.append(el("div", "small", "Collected " + ago(metrics.updatedAt) + (metrics.source ? " · " + metrics.source : "")));
  }
  function renderTrending(metrics) {
    const box = $("#trending"); if (!box) return; box.replaceChildren();
    const tr = (metrics && metrics.trending) || [];
    if (!tr.length) { const e = el("div", "empty"); e.append(el("strong", null, "No trend data yet")); e.append(el("span", null, "The collector fills this with what's trending in your niches.")); box.append(e); return; }
    const w = el("div", "wall"); tr.slice(0, 12).forEach(x => { const s = el("div", "shot"); const u = safeUrl(x.url); const t = el(u ? "a" : "div", "t", x.title); if (u) { t.href = u; t.target = "_blank"; t.rel = "noopener"; } s.append(t); const m = [x.channel, x.views != null ? fmtNum(x.views) + " views" : null, x.age].filter(Boolean).join(" · "); if (m) s.append(el("div", "m", m)); w.append(s); }); box.append(w);
  }
  function renderBrief(state) {
    const box = $("#brief"); if (!box) return; const b = state.brief;
    if (!b) { box.hidden = true; return; } box.hidden = false; box.replaceChildren();
    box.append(el("div", "label", "Chief of Staff · " + (b.date || ago(b.createdAt))));
    box.append(el("h2", null, b.headline || "Today's brief")); if (b.summary) box.append(el("p", "sum", b.summary));
    const cols = el("div", "cols");
    [["Film today", b.filmToday], ["Needs you", b.approvals], ["Heads up", b.notes]].forEach(([t, arr]) => { if (!Array.isArray(arr) || !arr.length) return; const d = el("div"); d.append(el("div", "label", t)); const ul = el("ul"); arr.forEach(x => ul.append(el("li", null, String(x)))); d.append(ul); cols.append(d); });
    if (cols.childElementCount) box.append(cols);
  }
  function renderRoster(agents) {
    const box = $("#roster"); if (!box) return; box.replaceChildren();
    agents.forEach(a => { const c = el("div", "agent"); const r = el("div", "row"); r.style.justifyContent = "space-between"; r.append(el("h3", null, a.name)); r.append(statusPill(a.status)); c.append(r); c.append(el("div", "role", a.role || ""));
      if (a.doing) c.append(el("div", "doing", a.doing));
      c.append(el("div", "when", (a.lastRun ? "Last run " + ago(a.lastRun) : "Hasn't run yet") + (a.nextRun ? " · next " + until(a.nextRun) : ""))); box.append(c); });
  }

  async function loadTeam() {
    const cfg = CFG.teams.find(t => t.id === TEAM);
    const tg = $("#tagline"); if (tg) tg.textContent = cfg.tagline;
    const [state, metrics] = await Promise.all([getJSON(`data/${TEAM}/state.json`), getJSON(`data/${TEAM}/metrics.json`)]);
    const st = state || { agents: [], log: [], ideas: [], research: [] };
    const agents = (st.agents && st.agents.length) ? st.agents : (cfg.agents || []).map(a => ({ ...a, status: "off" }));
    const lead = agents.find(a => a.lead) || agents[0] || { name: cfg.name, status: "idle" };
    const rest = agents.filter(a => a !== lead);
    if (metrics) rest.push({ name: "Data Collector", role: "Pulls stats hourly", status: metrics.status === "needs_setup" ? "waiting" : metrics.status === "error" ? "error" : "ok", doing: metrics.message, lastRun: metrics.updatedAt });
    drawFloor($("#floor"), lead, rest, (st.research || []).flatMap(r => r.items || []));
    const working = agents.filter(a => a.status === "working").length;
    $("#s-working").textContent = working; $("#s-ideas").textContent = (st.ideas || []).filter(i => (i.status || "pending") === "pending").length;
    $("#s-last").textContent = ago(st.updatedAt);
    renderRoster(rest.length ? [lead, ...rest] : [lead]);
    const log = [...(st.log || []), ...((metrics && metrics.log) || []).map(l => ({ ...l, agent: l.agent || "Data Collector" }))].sort((a, b) => (b.t || "").localeCompare(a.t || ""));
    renderLog($("#log"), log);
    renderBrief(st); renderIdeas(st); renderResearch(st); renderMetrics(metrics); renderTrending(metrics);
    $("#liveText").textContent = "Updated " + ago(st.updatedAt);
  }

  /* ---------- Hub ---------- */
  async function loadHub() {
    const states = await Promise.all(CFG.teams.map(t => getJSON(`data/${t.id}/state.json`)));
    const box = $("#companies"); box.replaceChildren();
    const nodes = []; let log = [], working = 0, pending = 0;
    CFG.teams.forEach((t, i) => {
      const s = states[i]; const agents = (s && s.agents) || [];
      const hired = !!(s && s.hired);
      const anyWorking = agents.some(a => a.status === "working"), anyErr = agents.some(a => a.status === "error");
      working += agents.filter(a => a.status === "working").length;
      pending += ((s && s.ideas) || []).filter(x => (x.status || "pending") === "pending").length;
      nodes.push({ name: t.name, status: !hired ? "off" : anyErr ? "error" : anyWorking ? "working" : "idle", href: ROOT + t.id + "/", doing: t.tagline });
      (s && s.log || []).forEach(l => log.push({ ...l, agent: t.name + " · " + (l.agent || "") }));
      const a = el("a", "co"); a.href = ROOT + t.id + "/";
      const r = el("div", "row"); r.style.justifyContent = "space-between"; r.append(el("h3", null, t.name)); r.append(statusPill(!hired ? "off" : anyErr ? "error" : anyWorking ? "working" : "idle")); a.append(r);
      a.append(el("div", "muted", t.tagline));
      const bar = el("div", "bar"); (agents.length ? agents : (t.agents || [])).forEach(ag => { const i2 = el("i", ag.status === "working" ? "w" : ag.status === "ok" ? "o" : ag.status === "error" ? "e" : ""); bar.append(i2); }); a.append(bar);
      a.append(el("div", "small", hired ? ((s.ideas || []).length + " ideas · updated " + ago(s.updatedAt)) : "Not hired yet"));
      box.append(a);
    });
    drawFloor($("#floor"), { name: "Agent HQ", status: working ? "working" : "idle" }, nodes, states.flatMap(s => (s && s.research || []).flatMap(r => r.items || [])));
    $("#s-working").textContent = working; $("#s-ideas").textContent = pending; $("#s-teams").textContent = states.filter(s => s && s.hired).length + "/" + CFG.teams.length;
    log.sort((a, b) => (b.t || "").localeCompare(a.t || "")); renderLog($("#log"), log);
    $("#liveText").textContent = "Live · checks every minute";
  }

  renderNav();
  const load = TEAM ? loadTeam : loadHub;
  load(); setInterval(load, 60000);
})();
