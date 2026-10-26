/* Agent HQ — game-style floor. Static site: reads data/<team>/state.json + metrics.json, refreshes every 60s. */
(function () {
  const CFG = window.HQ_CONFIG;
  const ROOT = document.documentElement.dataset.root || "./";
  const START = document.documentElement.dataset.team || (location.hash || "").slice(1) || null;
  const NS = "http://www.w3.org/2000/svg";
  const $ = s => document.querySelector(s);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  const sv = (t, a = {}, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  const safeUrl = u => { try { const p = new URL(u); return /^https?:$/.test(p.protocol) ? p.href : null; } catch { return null; } };
  const SC = { working: "#6fd3ff", ok: "#5fe0a0", idle: "#a37bff", waiting: "#ffc864", error: "#ff7a8e", off: "#4b4566" };
  const ST = { working: "Working", ok: "Done", idle: "Idle", waiting: "Waiting", error: "Error", off: "Not hired" };
  const fmt = n => typeof n === "number" ? (Math.abs(n) >= 1e6 ? (n / 1e6).toFixed(1) + "M" : Math.abs(n) >= 1e4 ? (n / 1e3).toFixed(1) + "K" : n.toLocaleString()) : (n ?? "—");
  function ago(iso) { if (!iso) return "never"; const t = Date.parse(iso); if (isNaN(t)) return "—"; const s = Math.round((Date.now() - t) / 1000);
    if (s < 0) return until(iso); if (s < 60) return "just now"; if (s < 3600) return Math.floor(s / 60) + "m ago"; if (s < 86400) return Math.floor(s / 3600) + "h ago"; return Math.floor(s / 86400) + "d ago"; }
  function until(iso) { if (!iso) return ""; const s = Math.round((Date.parse(iso) - Date.now()) / 1000); if (isNaN(s)) return ""; if (s <= 0) return "any minute";
    if (s < 3600) return "in " + Math.ceil(s / 60) + "m"; if (s < 86400) return "in " + Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m"; return "in " + Math.floor(s / 86400) + "d"; }
  const clock = iso => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); };
  async function getJSON(p) { try { const r = await fetch(ROOT + p + "?t=" + Date.now(), { cache: "no-store" }); return r.ok ? await r.json() : null; } catch { return null; } }
  function toast(t) { let x = $(".toast"); if (!x) { x = el("div", "toast"); document.body.append(x); } x.textContent = t; x.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => x.hidden = true, 2200); }

  /* ---------------- model ---------------- */
  let M = null, raw = "";
  async function load() {
    const res = await Promise.all(CFG.teams.map(async t => [t.id, await getJSON(`data/${t.id}/state.json`), t.virtual ? null : await getJSON(`data/${t.id}/metrics.json`)]));
    const sig = JSON.stringify(res); if (sig === raw) return false; raw = sig;
    const teams = {};
    res.forEach(([id, st, mt]) => {
      const cfg = CFG.teams.find(t => t.id === id); const s = st || {}; const hired = !!s.hired;
      const byId = {}; (s.agents || []).forEach(a => byId[a.id] = a);
      const agents = cfg.agents.map(a => {
        let live = byId[a.id] || {};
        if (a.id === "collector") live = mt ? { status: mt.status === "needs_setup" ? "waiting" : mt.status === "error" ? "error" : "ok", doing: mt.message, lastRun: mt.updatedAt, nextRun: nextHour() } : { status: "off" };
        const status = (!hired && a.id !== "collector") ? "off" : (live.status || "idle");
        return { ...a, status, doing: live.doing || "", lastRun: live.lastRun, nextRun: live.nextRun };
      });
      const log = [...(s.log || []), ...((mt && mt.log) || []).map(l => ({ ...l, agent: l.agent || "Data Collector" }))].sort((a, b) => (b.t || "").localeCompare(a.t || ""));
      teams[id] = { cfg, hired, state: s, metrics: mt, agents, log };
    });
    M = { teams };
    return true;
  }
  function nextHour() { const d = new Date(); d.setUTCMinutes(7, 0, 0); if (d < new Date()) d.setUTCHours(d.getUTCHours() + 1); return d.toISOString(); }

  /* ---------------- world ---------------- */
  const TW = 104, TH = 52, S = 4, G = 1.4, WALL = 120;
  const P = (x, y, z = 0) => [(x - y) * TW / 2, (x + y) * TH / 2 - z];
  const pts = a => a.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  const roomOrigin = t => [t.cfg.grid[0] * (S + G), t.cfg.grid[1] * (S + G)];
  const SLOTSET = { 3: [[0.4, 0.4], [2.75, 0.35], [0.35, 2.75]], 4: [[0.2, 0.2], [2.8, 0.3], [0.3, 2.8], [2.3, 2.3]], 5: [[0.2, 0.2], [2.8, 0.3], [0.3, 2.8], [2.8, 2.0], [1.9, 2.8]], 6: [[0.15, 0.15], [1.55, 0.15], [2.9, 0.4], [0.2, 2.85], [1.6, 2.9], [2.9, 1.9]] };
  const W0 = { x0: -1.2, y0: -1.2, x1: 3 * S + 2 * G + 1.2, y1: 2 * S + G + 1.2 };
  let svg, worldBox, roomBoxes = {};

  function buildWorld() {
    svg = $("#world"); svg.replaceChildren();
    const defs = sv("defs", {}, svg);
    const bl = sv("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); sv("feGaussianBlur", { stdDeviation: "5" }, bl);
    const fg = sv("radialGradient", { id: "fl", cx: "50%", cy: "50%", r: "60%" }, defs);
    sv("stop", { offset: "0", "stop-color": "#2a1d5c", "stop-opacity": ".9" }, fg); sv("stop", { offset: "1", "stop-color": "#0c0a16", "stop-opacity": "1" }, fg);
    const L = sv("g", {}, svg), F = sv("g", {}, svg), O = sv("g", {}, svg), T = sv("g", {}, svg);
    const { x0, y0, x1, y1 } = W0;
    // walls with research screens
    sv("polygon", { points: pts([P(x0, y0), P(x0, y1), P(x0, y1, WALL), P(x0, y0, WALL)]), fill: "#110e1f", stroke: "#2a2442" }, L);
    sv("polygon", { points: pts([P(x0, y0), P(x1, y0), P(x1, y0, WALL), P(x0, y0, WALL)]), fill: "#151227", stroke: "#2a2442" }, L);
    sv("polyline", { points: pts([P(x0, y1, WALL), P(x0, y0, WALL), P(x1, y0, WALL)]), fill: "none", stroke: "#a37bff", "stroke-width": 2, "stroke-opacity": .7 }, L);
    const shots = []; Object.values(M.teams).forEach(t => (t.state.research || []).slice(0, 2).forEach(r => (r.items || []).forEach(it => shots.push({ it, t }))));
    (((M.teams.tiktok || {}).metrics || {}).trending || []).slice(0, 4).forEach(it => shots.push({ it, t: M.teams.tiktok, trend: true }));
    (((M.teams.youtube || {}).metrics || {}).trending || []).slice(0, 4).forEach(it => shots.push({ it, t: M.teams.youtube, trend: true }));
    const nL = 7, nR = 11, spanL = (y1 - y0) / nL, spanR = (x1 - x0) / nR;
    for (let i = 0; i < nL + nR; i++) {
      const left = i < nL, k = left ? i : i - nL, span = left ? spanL : spanR, a0 = (left ? y0 : x0) + k * span + span * .14, a1 = a0 + span * .72;
      const z0 = 26, z1 = 96, s = shots[i];
      const poly = left ? [P(x0, a0, z0), P(x0, a1, z0), P(x0, a1, z1), P(x0, a0, z1)] : [P(a0, y0, z0), P(a1, y0, z0), P(a1, y0, z1), P(a0, y0, z1)];
      const col = s ? s.t.cfg.color : "#2a2442";
      const g = sv("g", s ? { class: "room", tabindex: 0 } : {}, L);
      sv("polygon", { points: pts(poly), fill: s ? col : "#1b1730", "fill-opacity": s ? .16 : 1, stroke: col, "stroke-opacity": s ? .9 : 1 }, g);
      if (s) {
        for (let l = 0; l < 4; l++) { const zz = z1 - 14 - l * 13, w = [.85, .7, .78, .5][l]; const ln = left ? [P(x0, a0 + .1, zz), P(x0, a0 + .1 + (a1 - a0 - .2) * w, zz)] : [P(a0 + .1, y0, zz), P(a0 + .1 + (a1 - a0 - .2) * w, y0, zz)];
          sv("polyline", { points: pts(ln), stroke: col, "stroke-opacity": .6, "stroke-width": 2.2, "stroke-linecap": "round" }, g); }
        sv("title", {}, g).textContent = (s.trend ? "Trending: " : "Research: ") + (s.it.title || "") + (s.it.metric ? " — " + s.it.metric : s.it.age ? " — " + s.it.age : "");
        g.addEventListener("click", e => { e.stopPropagation(); focusTeam(s.t.cfg.id, s.trend ? "trending" : "research"); });
      }
    }
    // floor
    const floor = sv("polygon", { points: pts([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]), fill: "url(#fl)", stroke: "#a37bff", "stroke-width": 2 }, L);
    sv("polygon", { points: pts([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)]), fill: "none", stroke: "#a37bff", "stroke-width": 10, "stroke-opacity": .25, filter: "url(#glow)" }, L);
    for (let x = Math.ceil(x0); x <= x1; x++) sv("line", { x1: P(x, y0)[0], y1: P(x, y0)[1], x2: P(x, y1)[0], y2: P(x, y1)[1], stroke: "#231d3b" }, L);
    for (let y = Math.ceil(y0); y <= y1; y++) sv("line", { x1: P(x0, y)[0], y1: P(x0, y)[1], x2: P(x1, y)[0], y2: P(x1, y)[1], stroke: "#231d3b" }, L);
    floor.addEventListener("click", () => { if (!dragMoved) zoomOut(); });

    // rooms
    const hq = M.teams.hq; const [hx, hy] = roomOrigin(hq);
    const objs = [];
    const order = Object.values(M.teams).sort((a, b) => (a.cfg.grid[0] + a.cfg.grid[1]) - (b.cfg.grid[0] + b.cfg.grid[1]));
    order.forEach(t => {
      const [ox, oy] = roomOrigin(t), c = t.cfg.color, on = t.hired || t.cfg.virtual;
      const g = sv("g", { class: "room", tabindex: 0, role: "button", "aria-label": t.cfg.name }, F);
      const slab = 7;
      sv("polygon", { points: pts([P(ox, oy + S, slab), P(ox + S, oy + S, slab), P(ox + S, oy + S), P(ox, oy + S)]), fill: "#1a1530" }, g);
      sv("polygon", { points: pts([P(ox + S, oy, slab), P(ox + S, oy + S, slab), P(ox + S, oy + S), P(ox + S, oy)]), fill: "#211a3c" }, g);
      sv("polygon", { class: "floor", points: pts([P(ox, oy, slab), P(ox + S, oy, slab), P(ox + S, oy + S, slab), P(ox, oy + S, slab)]), fill: c, "fill-opacity": on ? .12 : .04, stroke: c, "stroke-width": 2, "stroke-opacity": on ? .95 : .35 }, g);
      if (on) sv("polygon", { points: pts([P(ox, oy, slab), P(ox + S, oy, slab), P(ox + S, oy + S, slab), P(ox, oy + S, slab)]), fill: "none", stroke: c, "stroke-width": 8, "stroke-opacity": .22, filter: "url(#glow)" }, g);
      for (let i = 1; i < S; i++) { sv("line", { x1: P(ox + i, oy, slab)[0], y1: P(ox + i, oy, slab)[1], x2: P(ox + i, oy + S, slab)[0], y2: P(ox + i, oy + S, slab)[1], stroke: c, "stroke-opacity": .08 }, g);
        sv("line", { x1: P(ox, oy + i, slab)[0], y1: P(ox, oy + i, slab)[1], x2: P(ox + S, oy + i, slab)[0], y2: P(ox + S, oy + i, slab)[1], stroke: c, "stroke-opacity": .08 }, g); }
      g.addEventListener("click", e => { e.stopPropagation(); if (!dragMoved) focusTeam(t.cfg.id); });
      g.addEventListener("keydown", e => { if (e.key === "Enter") focusTeam(t.cfg.id); });
      // data path to HQ
      if (!t.cfg.virtual) {
        const [cx, cy] = [ox + S / 2, oy + S / 2], [tx, ty] = [hx + S / 2, hy + S / 2];
        const d = "M" + [P(cx, cy, slab), P(tx, cy, slab), P(tx, ty, slab)].map(p => p.join(",")).join(" L");
        sv("path", { d, fill: "none", stroke: c, "stroke-opacity": on ? .28 : .08, "stroke-width": 2, "stroke-dasharray": "6 6" }, O);
        if (t.agents.some(a => a.status === "working") || (on && t.agents.some(a => a.id === "collector" && a.status === "ok"))) {
          for (let k = 0; k < 2; k++) { const p = sv("circle", { r: 3.5, fill: c }, O); const am = sv("animateMotion", { dur: (3 + k) + "s", repeatCount: "indefinite", begin: k * 1.4 + "s", path: d }, p); }
        }
      }
      // desks + bots
      t.agents.forEach((a, i) => {
        const big = t.cfg.virtual;
        const set = SLOTSET[t.agents.length] || SLOTSET[5]; const [sx, sy] = big ? [1.4, 1.1] : set[i % set.length];
        objs.push({ depth: ox + sx + oy + sy + .3, draw: () => drawDesk(O, ox + sx, oy + sy, slab, c, a, big) });
        objs.push({ depth: ox + sx + oy + sy + 1.3, draw: () => drawBot(O, t, a, P(ox + sx + .45, oy + sy + .95, slab), big) });
      });
      if (t.cfg.virtual) objs.push({ depth: ox + oy + 5, draw: () => drawHolo(O, P(ox + 2.6, oy + 2.8, slab), c) });
      // label (top layer)
      const [lx, ly] = P(ox + S, oy + S, 0); const lab = sv("g", { class: "room-label", transform: `translate(${lx - 6},${ly + 14})` }, T);
      const name = t.cfg.name.toUpperCase(); const w = name.length * 8.4 + 30;
      sv("rect", { x: -w / 2, y: -13, width: w, height: 26, rx: 13, fill: "#0e0c17", stroke: c, "stroke-opacity": on ? .9 : .4 }, lab);
      sv("circle", { cx: -w / 2 + 13, cy: 0, r: 4, fill: on ? (t.agents.some(a => a.status === "working") ? SC.working : t.agents.some(a => a.status === "error") ? SC.error : c) : SC.off }, lab);
      const tx2 = sv("text", { x: -w / 2 + 23, y: 4.5, fill: on ? "#f1eefb" : "#6b6489", "font-size": 12.5, "font-weight": 600, "font-family": "IBM Plex Mono, monospace", "letter-spacing": ".06em" }, lab); tx2.textContent = name;
      // bbox for camera
      const corners = [P(ox, oy, slab + 90), P(ox + S, oy), P(ox + S, oy + S), P(ox, oy + S), P(ox + S, oy + S, -40)];
      roomBoxes[t.cfg.id] = bbox(corners);
    });
    objs.sort((a, b) => a.depth - b.depth).forEach(o => o.draw());
    // sparks
    for (let i = 0; i < 18; i++) { const x = x0 + Math.random() * (x1 - x0), y = y0 + Math.random() * (y1 - y0); const [px, py] = P(x, y, 10);
      sv("circle", { class: "spark", cx: px, cy: py, r: 1.6, fill: i % 2 ? "#6fd3ff" : "#a37bff", style: `animation-delay:${(Math.random() * 6).toFixed(2)}s` }, O); }
    worldBox = bbox([P(x0, y0, WALL + 10), P(x1, y0), P(x1, y1), P(x0, y1), P(x0, y1, WALL)]);
    worldBox.y1 += 30;
  }
  function bbox(ps) { const xs = ps.map(p => p[0]), ys = ps.map(p => p[1]); return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }; }

  let clipN = 0;
  function drawDesk(O, x, y, z, c, a, big) {
    const w = big ? 1.2 : .9, d = .45, h = 15;
    const top = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)];
    sv("polygon", { points: pts([P(x, y + d, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x, y + d, z)]), fill: "#1d1735" }, O);
    sv("polygon", { points: pts([P(x + w, y, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x + w, y, z)]), fill: "#251e44" }, O);
    sv("polygon", { points: pts(top), fill: "#322a5c", stroke: c, "stroke-opacity": .35 }, O);
    const n = big ? 3 : 1;
    for (let i = 0; i < n; i++) {
      const [mx, my] = P(x + w * (i + .5) / n, y + .12, z + h); const mw = big ? 26 : 30, mh = 20, id = "clip" + (++clipN);
      const cp = sv("clipPath", { id }, O); sv("rect", { x: mx - mw / 2, y: my - mh - 4, width: mw, height: mh, rx: 3 }, cp);
      sv("rect", { x: mx - mw / 2 - 1.5, y: my - mh - 5.5, width: mw + 3, height: mh + 3, rx: 4, fill: "#0b0918", stroke: c, "stroke-opacity": .7 }, O);
      sv("rect", { x: mx - 1.5, y: my - 4, width: 3, height: 5, fill: "#3a3160" }, O);
      const g = sv("g", { "clip-path": `url(#${id})` }, O);
      sv("rect", { x: mx - mw / 2, y: my - mh - 4, width: mw, height: mh, fill: c, "fill-opacity": a.status === "off" ? .05 : .18 }, g);
      if (a.status !== "off") { const lines = sv("g", { class: a.status === "working" ? "screen-line" : "" }, g);
        for (let l = 0; l < 6; l++) sv("rect", { x: mx - mw / 2 + 4, y: my - mh + l * 6, width: (mw - 8) * [.9, .6, .75, .5, .85, .4][l], height: 2, rx: 1, fill: c, "fill-opacity": .8 }, lines); }
    }
  }
  function drawBot(O, t, a, [x, y], big) {
    const c = t.cfg.color, st = a.status, k = big ? 1.35 : 1;
    const g = sv("g", { class: `bot ${st}`, transform: `translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${k})`, tabindex: 0, role: "button", "aria-label": `${a.name}: ${ST[st] || st}` }, O);
    sv("ellipse", { cx: 0, cy: 0, rx: 14, ry: 5.5, fill: "#000", opacity: .45 }, g);
    if (st === "working") sv("ellipse", { class: "ring", cx: 0, cy: 0, rx: 15, ry: 6, fill: "none", stroke: SC.working, "stroke-width": 2 }, g);
    const wan = sv("g", { class: st === "idle" || st === "ok" ? "wander" : "", style: `animation-delay:-${(Math.random() * 14).toFixed(1)}s` }, g);
    const b = sv("g", { class: "bot-anim", style: `animation-delay:-${(Math.random() * 3).toFixed(2)}s` }, wan);
    sv("rect", { x: -8, y: -9, width: 5, height: 9, rx: 2, fill: "#2a2350" }, b); sv("rect", { x: 3, y: -9, width: 5, height: 9, rx: 2, fill: "#2a2350" }, b);
    sv("rect", { class: "arm-l", x: -17.5, y: -31, width: 5, height: 15, rx: 2.5, fill: c, "fill-opacity": .85 }, b);
    sv("rect", { class: "arm-r", x: 12.5, y: -31, width: 5, height: 15, rx: 2.5, fill: c, "fill-opacity": .85 }, b);
    sv("rect", { class: "bot-body", x: -12.5, y: -35, width: 25, height: 27, rx: 9, fill: "#2a2350", stroke: c, "stroke-width": 1.6 }, b);
    sv("circle", { cx: 0, cy: -21, r: 3.2, fill: SC[st] || c }, b);
    const h = sv("g", { class: "bot-head" }, b);
    sv("line", { x1: 0, y1: -54, x2: 0, y2: -62, stroke: c, "stroke-width": 1.6 }, h);
    sv("circle", { class: "antenna-ball", cx: 0, cy: -64, r: 3, fill: SC[st] || c }, h);
    sv("rect", { x: -12, y: -55, width: 24, height: 18, rx: 7, fill: "#372d6b", stroke: c, "stroke-width": 1.6 }, h);
    sv("rect", { x: -8.5, y: -51, width: 17, height: 9, rx: 4.5, fill: "#0b0918" }, h);
    sv("circle", { class: "eye", cx: -4, cy: -46.5, r: 2, fill: st === "off" ? "#4b4566" : c }, h);
    sv("circle", { class: "eye", cx: 4, cy: -46.5, r: 2, fill: st === "off" ? "#4b4566" : c }, h);
    sv("title", {}, g).textContent = `${a.name} — ${a.doing || ST[st] || ""}`;
    g.addEventListener("click", e => { e.stopPropagation(); if (!dragMoved) focusTeam(t.cfg.id, tabForKind(t, a.kind), a.id); });
    g.addEventListener("keydown", e => { if (e.key === "Enter") focusTeam(t.cfg.id, tabForKind(t, a.kind), a.id); });
  }
  function drawHolo(O, [x, y], c) {
    const g = sv("g", { transform: `translate(${x},${y})` }, O);
    sv("ellipse", { cx: 0, cy: 0, rx: 30, ry: 12, fill: c, "fill-opacity": .25, stroke: c }, g);
    sv("ellipse", { class: "ring", cx: 0, cy: 0, rx: 30, ry: 12, fill: "none", stroke: c, "stroke-width": 2 }, g);
    sv("polygon", { points: "-16,0 16,0 6,-60 -6,-60", fill: c, "fill-opacity": .12 }, g);
    sv("circle", { cx: 0, cy: -70, r: 22, fill: c, opacity: .35, filter: "url(#glow)" }, g);
    sv("circle", { class: "antenna-ball", cx: 0, cy: -70, r: 12, fill: c }, g);
    sv("circle", { cx: 0, cy: -70, r: 19, fill: "none", stroke: c, "stroke-width": 1.5, "stroke-dasharray": "4 5" }, g);
  }

  /* ---------------- camera ---------------- */
  let vb = null, anim = null, focused = null, dragMoved = false;
  function panelInsets() {
    const open = $("#panel").classList.contains("open"); const mobile = innerWidth <= 760;
    return { top: mobile ? 120 : 86, bottom: 100 + (open && mobile ? innerHeight * .6 - 90 : 0), right: open && !mobile ? Math.min(470, innerWidth) : 0, left: 0 };
  }
  function fitBox(b, pad = .9) {
    const W = svg.clientWidth, H = svg.clientHeight, ins = panelInsets();
    const aw = Math.max(80, W - ins.left - ins.right), ah = Math.max(80, H - ins.top - ins.bottom);
    const bw = b.x1 - b.x0, bh = b.y1 - b.y0, s = Math.min(aw / bw, ah / bh) * pad;
    const cx = (b.x0 + b.x1) / 2, cy = (b.y0 + b.y1) / 2;
    const ax = ins.left + aw / 2, ay = ins.top + ah / 2;
    return { x: cx - ax / s, y: cy - ay / s, w: W / s, h: H / s };
  }
  function setVB(v) { vb = v; svg.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`); }
  function animateTo(t, ms = 750) {
    if (!vb || matchMedia("(prefers-reduced-motion: reduce)").matches) return setVB(t);
    cancelAnimationFrame(anim); const f = { ...vb }, t0 = performance.now();
    const step = now => { const p = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - p, 3);
      setVB({ x: f.x + (t.x - f.x) * e, y: f.y + (t.y - f.y) * e, w: f.w + (t.w - f.w) * e, h: f.h + (t.h - f.h) * e }); if (p < 1) anim = requestAnimationFrame(step); };
    anim = requestAnimationFrame(step);
  }
  function zoomOut() { focused = null; closePanel(); setTimeout(() => animateTo(fitBox(worldBox, .96)), 10); syncTeambar(); if (location.hash) history.replaceState(null, "", location.pathname); }
  function enablePanZoom() {
    let start = null;
    svg.addEventListener("pointerdown", e => { start = { x: e.clientX, y: e.clientY, vb: { ...vb } }; dragMoved = false; });
    addEventListener("pointermove", e => { if (!start) return; const dx = e.clientX - start.x, dy = e.clientY - start.y; if (Math.abs(dx) + Math.abs(dy) > 6) { dragMoved = true; svg.classList.add("dragging"); }
      if (!dragMoved) return; const s = vb.w / svg.clientWidth; setVB({ ...start.vb, x: start.vb.x - dx * s, y: start.vb.y - dy * s }); });
    addEventListener("pointerup", () => { start = null; svg.classList.remove("dragging"); setTimeout(() => dragMoved = false, 0); });
    svg.addEventListener("wheel", e => { e.preventDefault(); const r = svg.getBoundingClientRect(); const k = Math.exp(e.deltaY * .0012);
      const mx = vb.x + (e.clientX - r.left) / r.width * vb.w, my = vb.y + (e.clientY - r.top) / r.height * vb.h;
      const w = Math.min(Math.max(vb.w * k, 300), 6000), h = w * vb.h / vb.w; setVB({ x: mx - (mx - vb.x) * w / vb.w, y: my - (my - vb.y) * h / vb.h, w, h }); }, { passive: false });
    addEventListener("resize", () => { if (focused) animateTo(fitBox(roomBoxes[focused]), 200); else animateTo(fitBox(worldBox, .96), 200); });
    addEventListener("keydown", e => { if (e.key === "Escape") zoomOut(); });
  }

  /* ---------------- panel ---------------- */
  let tab = "overview", agentSel = null, ideaFilter = "pending", statSel = null;
  function tabForKind(t, kind) { return ["stats", "research", "ideas", "review", "competitors"].includes(kind) ? kind : "overview"; }
  function focusTeam(id, tb, agentId) {
    if (!M.teams[id]) return; focused = id; tab = tb || "overview"; agentSel = agentId || null; statSel = null; ideaFilter = id === "youtube" ? "approved" : "pending";
    $("#panel").classList.add("open"); renderPanel(); syncTeambar();
    requestAnimationFrame(() => animateTo(fitBox(roomBoxes[id], .74)));
    history.replaceState(null, "", "#" + id);
  }
  function closePanel() { $("#panel").classList.remove("open"); }
  function syncTeambar() { document.querySelectorAll(".teambar button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.id === focused))); $("#back").hidden = !focused; }

  function tabsFor(t) {
    if (t.cfg.virtual) return [["overview", "Brief"], ["activity", "Activity"]];
    const out = [["overview", "Overview"], ["ideas", t.cfg.ideaWord || "Ideas"]];
    if (t.metrics) out.push(["stats", "Stats"]);
    if (t.metrics && (t.metrics.trending || []).length) out.push(["trending", "Trending"]);
    if (t.cfg.id === "youtube") out.splice(1, 0, ["lineup", "Today's lineup"]), out.splice(3, 0, ["shots", "Footage"]);
    if (t.cfg.id === "tiktok" || t.cfg.id === "youtube") out.splice(out.findIndex(x => x[0] === "ideas") + 1, 0, ["review", "Review"]);
    if (t.cfg.id === "linkedai" || t.cfg.id === "growth") out.splice(2, 0, ["competitors", "Competitors"]);
    out.push(["research", "Research"], ["activity", "Activity"]);
    return out;
  }
  function renderPanel() {
    const t = M.teams[focused]; if (!t) return; const p = $("#panel"); p.style.setProperty("--tc", t.cfg.color); p.replaceChildren();
    const ph = el("div", "ph"); const top = el("div", "ph-top"); const tt = el("div");
    tt.append(el("div", "label", t.cfg.virtual ? "Agent HQ" : (t.hired ? "Company floor" : "Not hired yet")));
    const h = el("h2", null, t.cfg.name); h.style.color = t.cfg.color; tt.append(h); tt.append(el("div", "tag", t.cfg.tagline));
    const x = el("button", "xbtn", "×"); x.setAttribute("aria-label", "Close and zoom out"); x.onclick = zoomOut; top.append(tt, x); ph.append(top);
    const tabs = el("div", "tabs"); tabs.setAttribute("role", "tablist");
    tabsFor(t).forEach(([k, l]) => { const b = el("button", null, l); b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(tab === k));
      if (k === "ideas") b.append(el("span", "n", String((t.state.ideas || []).filter(i => t.cfg.id === "youtube" ? ["pending", "approved"].includes(effectiveStatus(i).status) : effectiveStatus(i).status === "pending").length)));
      if (k === "shots") b.append(el("span", "n", String((t.state.footage || []).filter(f => f.status === "ready").length)));
      b.onclick = () => { tab = k; renderPanel(); }; tabs.append(b); });
    ph.append(tabs); p.append(ph);
    const body = el("div", "pb"); p.append(body);
    ({ overview: vOverview, ideas: vIdeas, review: vReview, competitors: vCompetitors, lineup: vLineup, shots: vShots, stats: vStats, trending: vTrending, research: vResearch, activity: vActivity }[tab] || vOverview)(t, body);
  }
  function pill(s) { return el("span", "pill s-" + (s || "idle"), ST[s] || s || "Idle"); }
  function empty(title, text) { const e = el("div", "empty"); e.append(el("strong", null, title)); e.append(el("span", null, text)); return e; }
  function agentCard(t, a) {
    const c = el("div", "card agentcard"); const r = el("div", "row between"); const nm = el("div"); nm.append(el("h3", null, a.name)); nm.append(el("div", "muted", a.role));
    r.append(nm, pill(a.status)); c.append(r);
    if (a.doing) c.append(el("div", null, a.doing));
    c.append(el("div", "small", (a.lastRun ? "Last run " + ago(a.lastRun) : "Hasn't run yet") + (a.nextRun ? " · next " + until(a.nextRun) : "")));
    const k = tabForKind(t, a.kind); if (k !== "overview") { const b = el("button", "btn primary", { stats: "See the stats", research: "See what they found", review: "See the review", competitors: "See the competitors" }[k] || "See what they wrote"); b.onclick = () => { tab = k; renderPanel(); }; c.append(b); }
    return c;
  }
  function vOverview(t, body) {
    if (agentSel) { const a = t.agents.find(x => x.id === agentSel); if (a) body.append(agentCard(t, a)); }
    const b = t.state.brief;
    if (b) { const c = el("div", "card brief"); c.append(el("div", "label", (t.cfg.virtual ? "Chief of Staff · " : "Brief · ") + (b.date || ago(b.createdAt))));
      c.append(el("h3", null, b.headline || "Today's brief")); if (b.summary) c.append(el("div", "why", b.summary));
      [["Film today", b.filmToday], ["Needs you", b.approvals], ["Heads up", b.notes]].forEach(([l, arr]) => { if (!Array.isArray(arr) || !arr.length) return; c.append(el("div", "label", l)); const ul = el("ul"); arr.forEach(i => ul.append(el("li", null, String(i)))); c.append(ul); });
      body.append(c); }
    else if (t.cfg.virtual) body.append(empty("No brief yet", "The Chief of Staff writes one every day before noon."));
    if (!t.hired && !t.cfg.virtual) body.append(empty("This team hasn't started yet", "Its first run fills this floor with research and ideas."));
    if (t.metrics && (t.metrics.kpis || []).length) { const k = el("div", "kpis"); t.metrics.kpis.slice(0, 4).forEach(m => k.append(kpi(m))); body.append(k); }
    body.append(el("div", "label", t.cfg.virtual ? "On duty" : "The team"));
    const ro = el("div", "roster");
    t.agents.forEach(a => { const b2 = el("button", "mini-agent"); const av = el("span", "av"); av.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><rect x="4" y="5" width="12" height="9" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="8" cy="9.5" r="1.2" fill="currentColor"/><circle cx="12" cy="9.5" r="1.2" fill="currentColor"/><line x1="10" y1="5" x2="10" y2="2.5" stroke="currentColor" stroke-width="1.6"/></svg>'; av.style.color = t.cfg.color;
      const mid = el("span"); mid.append(el("div", "nm", a.name)); mid.append(el("div", "dg", a.doing || a.role)); b2.append(av, mid, pill(a.status));
      b2.onclick = () => { agentSel = a.id; tab = "overview"; renderPanel(); }; ro.append(b2); });
    body.append(ro);
    if (t.cfg.virtual) { body.append(el("div", "label", "Teams")); const ro2 = el("div", "roster");
      Object.values(M.teams).filter(x => !x.cfg.virtual).forEach(x => { const b3 = el("button", "mini-agent"); const av = el("span", "av"); av.style.background = x.cfg.color + "33"; av.append(el("span", null, ""));
        const w = x.agents.filter(a => a.status === "working").length; const mid = el("span"); mid.append(el("div", "nm", x.cfg.name)); mid.append(el("div", "dg", x.hired ? ((x.state.ideas || []).filter(i => (i.status || "pending") === "pending").length + " to review · updated " + ago(x.state.updatedAt)) : "Not hired yet"));
        b3.append(av, mid, pill(!x.hired ? "off" : w ? "working" : "idle")); b3.onclick = () => focusTeam(x.cfg.id); ro2.append(b3); });
      body.append(ro2); }
  }
  function kpi(m) { const d = el("div", "kpi"); d.append(el("div", "v", fmt(m.value))); d.append(el("div", "k", m.label.replace(/^.* · /, ""))); if (m.delta != null && m.delta !== 0) { const n = Number(m.delta); d.append(el("div", "d " + (n >= 0 ? "up" : "down"), (n >= 0 ? "+" : "") + fmt(n) + " " + (m.deltaLabel || ""))); } return d; }
  function issueUrl(action, t, idea) {
    const body = `Decision from Agent HQ.\n\nIdea: ${idea.title || ""}\nTeam: ${t.cfg.id}\n\n(Just press "Submit new issue". The agents read this and update the site.)`;
    return `https://github.com/${CFG.repo}/issues/new?title=${encodeURIComponent(action + ": " + idea.id)}&body=${encodeURIComponent(body)}`;
  }
  /* one-click decisions: a GitHub token kept only in this browser */
  const LS = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} } };
  const ACTION_STATUS = { approve: "approved", pass: "rejected", filmed: "filmed", review: "pending" };
  function localDecisions() { try { return JSON.parse(LS.get("hq.decisions") || "{}"); } catch { return {}; } }
  function saveDecision(id, status) { const d = localDecisions(); d[id] = { status, at: Date.now() }; LS.set("hq.decisions", JSON.stringify(d)); }
  function effectiveStatus(i) { const d = localDecisions()[i.id]; const real = i.status || "pending";
    if (d && d.status !== real && Date.now() - d.at < 3 * 86400e3) return { status: d.status, queued: true }; return { status: real, queued: false }; }
  async function decide(action, t, idea, btns) {
    const tok = LS.get("hq.ghToken");
    if (!tok) { window.open(issueUrl(action, t, idea), "_blank", "noopener"); toast("Press Create on GitHub. Tip: connect GitHub once for one-click decisions."); return; }
    btns.forEach(b => b.disabled = true);
    try {
      const r = await fetch(`https://api.github.com/repos/${CFG.repo}/issues`, { method: "POST",
        headers: { Authorization: "Bearer " + tok, Accept: "application/vnd.github+json", "Content-Type": "application/json" },
        body: JSON.stringify({ title: `${action}: ${idea.id}`, body: `Decision from Agent HQ.\n\nIdea: ${idea.title || ""}\nTeam: ${t.cfg.id}` }) });
      if (r.status === 401 || r.status === 403) { LS.set("hq.ghToken", null); throw new Error("token"); }
      if (!r.ok) throw new Error("http " + r.status);
      saveDecision(idea.id, ACTION_STATUS[action]);
      toast({ approve: "Approved", pass: "Passed", filmed: "Marked done", review: "Moved back to review" }[action] + ". The team picks it up on its next run.");
      renderPanel();
    } catch (e) { btns.forEach(b => b.disabled = false); toast(e.message === "token" ? "GitHub didn't accept the token. Connect it again." : "Couldn't reach GitHub. Try again."); }
  }
  function connectCard(body) {
    if (LS.get("hq.ghToken")) return;
    const c = el("details", "card"); c.append(el("summary", null, "Make Approve and Pass one click"));
    const w = el("div"); w.style.display = "grid"; w.style.gap = "8px"; w.style.marginTop = "8px";
    w.append(el("div", "why", "Right now each decision opens GitHub. Paste a GitHub token once and they happen instantly. It's saved only in this browser."));
    const steps = el("ol"); steps.style.margin = "0"; steps.style.paddingLeft = "18px"; steps.style.fontSize = "13px";
    ["Open github.com/settings/personal-access-tokens/new", "Name it Agent HQ, set Expiration to 1 year", "Repository access: Only select repositories → agent-hq", "Permissions → Issues → Read and write, then Generate token", "Copy it and paste it below"].forEach(x => steps.append(el("li", null, x)));
    w.append(steps);
    const inp = el("input"); inp.type = "password"; inp.id = "ghtok"; inp.placeholder = "github_pat_…"; inp.autocomplete = "off";
    Object.assign(inp.style, { background: "var(--bg2)", border: "1px solid var(--line2)", borderRadius: "9px", padding: "9px 11px", color: "var(--fg)", font: "13px var(--f-mono)" });
    const sv2 = el("button", "btn primary", "Connect"); sv2.onclick = () => { const v = inp.value.trim(); if (!/^(github_pat_|ghp_)/.test(v)) { toast("That doesn't look like a GitHub token."); return; } LS.set("hq.ghToken", v); toast("Connected. Decisions are one click now."); renderPanel(); };
    w.append(inp, sv2); c.append(w); body.append(c);
  }
  function makeItPrompt(t, i) {
    const f = (i.format || "").toLowerCase(); const skill = f.includes("ambient") ? "ambient-escape-videos" : "bounce-theory-videos";
    return `Use the ${skill} skill. Include this Agent HQ idea in today's batch (id ${i.id}):\n\nTitle: ${i.title}\nHook: ${i.hook || ""}\nFormat: ${i.format || ""}\n\nProduction notes:\n${i.script || ""}`;
  }
  function vIdeas(t, body) {
    const ideas = t.state.ideas || []; const S2 = [["pending", "To review"], ["approved", t.cfg.id === "youtube" ? "Up next" : "Approved"], ["filmed", t.cfg.id === "opps" ? "Started" : "Done"], ["rejected", "Passed"]];
    const sub = el("div", "subtabs"); S2.forEach(([k, l]) => { const b = el("button", null, `${l} ${ideas.filter(i => effectiveStatus(i).status === k).length}`); b.setAttribute("aria-pressed", String(ideaFilter === k)); b.onclick = () => { ideaFilter = k; renderPanel(); }; sub.append(b); });
    body.append(sub);
    const list = ideas.filter(i => effectiveStatus(i).status === ideaFilter).sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
    if (!list.length) { body.append(empty(ideas.length ? "Nothing in this list" : "Nothing yet", ideas.length ? "Ideas move here when you change their status." : "The team adds new ideas after each run.")); return; }
    list.forEach(i => { const c = el("article", "card"); const r = el("div", "row between"); r.append(el("h3", null, i.title || "Untitled"));
      const tg = el("div", "row"); if (i.format) tg.append(el("span", "pill s-idle", i.format)); if (i.score != null) tg.append(el("span", "small", "Fit " + i.score + "/10")); r.append(tg); c.append(r);
      if (i.hook) c.append(el("div", "hook", i.hook)); if (i.why) c.append(el("div", "why", i.why));
      if (i.onScreen) c.append(el("div", "small", "On screen: " + i.onScreen));
      if (Array.isArray(i.scenes) && i.scenes.length) { const d = el("details"); d.open = false; d.append(el("summary", null, `Scenes (${i.scenes.length}${i.length ? " · ~" + i.length + "s" : ""}${i.hookFamily ? " · " + i.hookFamily : ""})`));
        const w = el("div"); w.style.display = "grid"; w.style.gap = "10px"; w.style.marginTop = "8px";
        i.scenes.forEach((sc, n) => { const b = el("div"); b.style.borderLeft = "2px solid var(--line2)"; b.style.paddingLeft = "10px";
          b.append(el("div", "label", `Scene ${n + 1} · ${sc.label || ""}${sc.time ? " · " + sc.time : ""}`)); b.append(el("div", null, sc.line || "")); if (sc.delivery) b.append(el("div", "small", sc.delivery)); w.append(b); });
        if (Array.isArray(i.hooksToTest) && i.hooksToTest.length) { w.append(el("div", "label", "Hooks to test")); const ul = el("ul"); ul.style.margin = "0"; ul.style.paddingLeft = "18px"; i.hooksToTest.forEach(h => ul.append(el("li", null, h))); w.append(ul); }
        if (i.caption) { w.append(el("div", "label", "Caption")); w.append(el("div", "small", i.caption)); }
        d.append(w); c.append(d); }
      else if (i.script) { const d = el("details"); d.append(el("summary", null, t.cfg.id === "opps" ? "How to do it" : t.cfg.id === "youtube" ? "Production notes" : "Full script")); d.append(el("div", "script", i.script)); c.append(d); }
      if (Array.isArray(i.sources) && i.sources.length) { const s = el("div", "sources"); i.sources.forEach(x => { const u = safeUrl(x.url); if (u) { const a = el("a", null, "↗ " + (x.title || "source")); a.href = u; a.target = "_blank"; a.rel = "noopener"; s.append(a); } }); c.append(s); }
      const act = el("div", "row"); const { status: st, queued } = effectiveStatus(i); const btns = [];
      const add = (l, a, cls) => { const b = el("button", "btn " + (cls || ""), l); b.onclick = () => decide(a, t, i, btns); btns.push(b); act.append(b); };
      if (queued) act.append(el("span", "pill s-waiting", "Sent · applies next run"));
      else if (st === "pending") { add("Approve", "approve", "primary"); add("Pass", "pass"); }
      else if (st === "approved") { add(t.cfg.id === "tiktok" || t.cfg.id === "youtube" ? (t.cfg.id === "youtube" ? "Mark made" : "Mark filmed") : "Mark done", "filmed", "primary"); add("Back to review", "review"); }
      else add("Back to review", "review");
      if (t.cfg.id === "youtube" && !queued && (st === "pending" || st === "approved")) { const m = el("button", "btn", "Copy 'make it' prompt"); m.onclick = async () => { const txt = makeItPrompt(t, i); try { await navigator.clipboard.writeText(txt); toast("Copied. Paste it into Claude to make this video."); } catch { const ta = el("textarea"); ta.value = txt; ta.style.width = "100%"; ta.rows = 5; c.append(ta); ta.select(); toast("Select and copy the text below."); } }; act.append(m); }
      act.append(el("span", "small", ago(i.createdAt))); c.append(act); body.append(c); });
    connectCard(body);
  }
  function vReview(t, body) {
    const r = t.state.review;
    if (!r) { body.append(empty("No review yet", "The Performance Reviewer compares your best and worst recent videos on its next run and says why.")); return; }
    const top = el("div", "card brief"); top.append(el("div", "label", "Performance review · " + (r.date || ago(r.createdAt))));
    if (r.headline) top.append(el("h3", null, r.headline)); if (r.summary) top.append(el("div", "why", r.summary)); body.append(top);
    const list = (title, arr, cls) => { if (!Array.isArray(arr) || !arr.length) return; const c = el("div", "card"); c.append(el("div", "label", title));
      arr.forEach(v => { const s = el("div", "shot"); const u = safeUrl(v.url); const a = el(u ? "a" : "div", "t", v.title || ""); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } s.append(a);
        const m = [v.channel, v.views != null ? fmt(v.views) + " views" : null, v.avgViewPct != null ? v.avgViewPct + "% watched" : null, v.vsAvg].filter(Boolean).join(" · "); if (m) { const mm = el("div", "m", m); if (cls) mm.style.color = cls; s.append(mm); }
        if (v.why) s.append(el("p", null, v.why)); c.append(s); }); body.append(c); };
    list("What worked", r.winners, "var(--good)"); list("What didn't", r.losers, "var(--bad)");
    const bullets = (title, arr) => { if (!Array.isArray(arr) || !arr.length) return; const c = el("div", "card brief"); c.append(el("div", "label", title)); const ul = el("ul"); arr.forEach(x => ul.append(el("li", null, typeof x === "string" ? x : (x.text || JSON.stringify(x))))); c.append(ul); body.append(c); };
    bullets("Patterns", r.patterns); bullets("Do more of", r.doMore); bullets("Stop doing", r.stopDoing); bullets("Suggested skill updates", r.skillSuggestions);
  }
  function vCompetitors(t, body) {
    const cs = t.state.competitors || [];
    if (!cs.length) { body.append(empty("No competitor intel yet", "Competitor Watch fills this with what your competitors post, how many views they get, how they advertise and how they grew.")); return; }
    if (t.state.competitorsUpdated) body.append(el("div", "small", "Updated " + ago(t.state.competitorsUpdated)));
    cs.forEach(x => { const c = el("div", "card"); const r = el("div", "row between"); const u = safeUrl(x.url); const h = el(u ? "a" : "h3", u ? "t" : null, x.name || "Competitor");
      if (u) { h.href = u; h.target = "_blank"; h.rel = "noopener"; h.style.fontWeight = "600"; h.style.fontSize = "16px"; h.style.color = "var(--fg)"; } r.append(h); if (x.price) r.append(el("span", "pill s-idle", x.price)); c.append(r);
      if (x.oneLiner) c.append(el("div", "why", x.oneLiner));
      const sec = (label, txt) => { if (!txt) return; c.append(el("div", "label", label)); c.append(el("div", null, txt)); };
      sec("How they grew", x.howTheyGrew); sec("Ad strategy", x.adStrategy); sec("Content strategy", x.contentStrategy);
      if (Array.isArray(x.topContent) && x.topContent.length) { c.append(el("div", "label", "Their top content")); x.topContent.forEach(v => { const s = el("div", "shot"); const uu = safeUrl(v.url); const a = el(uu ? "a" : "div", "t", v.title || v.platform || "Post"); if (uu) { a.href = uu; a.target = "_blank"; a.rel = "noopener"; } s.append(a);
        const m = [v.platform, v.views != null ? (typeof v.views === "number" ? fmt(v.views) : v.views) + " views" : null, v.date].filter(Boolean).join(" · "); if (m) s.append(el("div", "m", m)); if (v.whyItWorked) s.append(el("p", null, v.whyItWorked)); c.append(s); }); }
      if (Array.isArray(x.ads) && x.ads.length) { c.append(el("div", "label", "Ads running")); x.ads.forEach(v => { const s = el("div", "shot"); const uu = safeUrl(v.url); const a = el(uu ? "a" : "div", "t", v.hook || v.title || "Ad"); if (uu) { a.href = uu; a.target = "_blank"; a.rel = "noopener"; } s.append(a); const m = [v.platform, v.running].filter(Boolean).join(" · "); if (m) s.append(el("div", "m", m)); if (v.notes) s.append(el("p", null, v.notes)); c.append(s); }); }
      if (x.lessonForUs) { const l = el("div", "hook", x.lessonForUs); c.append(l); }
      body.append(c); });
  }
  function vLineup(t, body) {
    const L = t.state.lineup; const sub0 = L && L.channels ? Object.keys(L.channels) : [];
    if (!sub0.length) { body.append(empty("No lineup yet", "Every morning the team plans all 17 videos for each channel: 15 Shorts and 2 long videos.")); return; }
    statSel = sub0.includes(statSel) ? statSel : sub0[0];
    const sub = el("div", "subtabs"); sub0.forEach(ch => { const b = el("button", null, `${ch} ${(L.channels[ch] || []).length}`); b.setAttribute("aria-pressed", String(statSel === ch)); b.onclick = () => { statSel = ch; renderPanel(); }; sub.append(b); }); body.append(sub);
    body.append(el("div", "small", "Planned " + (L.date || ago(L.createdAt)) + " · say “make today's batch” to Claude and it builds these"));
    const c = el("div", "card"); (L.channels[statSel] || []).forEach(v => { const r = el("div", "vid");
      const tt = el("span", "t", (v.slot || "") + "  " + (v.title || "")); tt.title = v.title || ""; r.append(tt, el("span", "n", v.kind || ""));
      r.append(el("span", "m", [v.format, v.note].filter(Boolean).join(" · ")), el("span", "m", [v.newIdea ? "★ new" : "", v.footage ? "🎞 " + v.footage : ""].filter(Boolean).join("  "))); c.append(r); });
    body.append(c);
  }
  function vShots(t, body) {
    const ft = t.state.footage || [];
    const intro = el("div", "card"); intro.append(el("h3", null, "Free stock footage"));
    intro.append(el("div", "why", "The team picks the clips each lineup needs. GitHub then finds and downloads them from Pexels (or Pixabay) automatically, so your batch has them ready. You don't film anything."));
    body.append(intro);
    if (!ft.length) { body.append(empty("No footage requested yet", "The YouTube team lists the clips it needs with each morning's lineup.")); return; }
    const label = { ready: ["ok", "Downloaded"], wanted: ["waiting", "Finding"], needs_key: ["waiting", "Needs Pixabay key"], not_found: ["error", "No match"], error: ["error", "Failed"] };
    if (ft.some(f => f.status === "needs_key")) body.append(empty("One-time setup", "Get a free API key at pixabay.com/api/docs (it shows next to “key” when you are logged in) and add it in GitHub Secrets as PIXABAY_API_KEY. Then the clips download by themselves."));
    ft.forEach(f => { const k = el("div", "card"); const r = el("div", "row between"); r.append(el("h3", null, f.query || f.file)); const [cls, txt] = label[f.status || "wanted"] || ["idle", f.status]; r.append(el("span", "pill s-" + cls, txt)); k.append(r);
      const meta = [f.file, f.for ? "for " + f.for : null, f.seconds ? f.seconds + "s" : null, f.size, f.mb ? f.mb + " MB" : null].filter(Boolean).join(" · "); k.append(el("div", "small", meta));
      if (f.credit) { const row = el("div", "sources"); const u = safeUrl(f.page); const a = el(u ? "a" : "span", null, (u ? "↗ " : "") + f.credit); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } row.append(a); k.append(row); }
      if (f.note && f.status !== "ready") k.append(el("div", "why", f.note));
      body.append(k); });
  }
  function barChart(vals, labels, color) {
    const W = 420, H = 150, pl = 34, pb = 22, pt = 14, n = vals.length, max = Math.max(1, ...vals);
    const nice = Math.pow(10, Math.floor(Math.log10(max))); const top = Math.ceil(max / nice) * nice;
    const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${W} ${H}`); s.setAttribute("class", "chart"); s.setAttribute("role", "img");
    s.setAttribute("aria-label", "Views per video: " + vals.join(", "));
    [0, .5, 1].forEach(f => { const y = pt + (H - pt - pb) * (1 - f); sv("line", { x1: pl, x2: W, y1: y, y2: y, stroke: "#2a2442" }, s); const tx = sv("text", { x: pl - 6, y: y + 4, "text-anchor": "end", fill: "#6b6489", "font-size": 10 }, s); tx.textContent = fmt(Math.round(top * f)); });
    const bw = (W - pl - 6) / n;
    vals.forEach((v, i) => { const h = (H - pt - pb) * v / top, x = pl + 4 + i * bw, y = H - pb - h; const last = i === n - 1;
      sv("rect", { x, y, width: Math.max(3, bw - 6), height: Math.max(1, h), rx: 3, fill: color, "fill-opacity": last ? 1 : .55 }, s);
      const lt = sv("text", { x: x + (bw - 6) / 2, y: H - 7, "text-anchor": "middle", fill: "#6b6489", "font-size": 9.5 }, s); lt.textContent = labels[i] || ""; });
    return s;
  }
  function vStats(t, body) {
    const m = t.metrics || {}; if (m.status === "needs_setup" || !(m.kpis || []).length) { body.append(empty("Waiting for access", m.message || "Connect the account to see stats.")); return; }
    let kpis = m.kpis, vids = m.topVideos || [];
    const groups = [...new Set(kpis.map(k => k.label.includes(" · ") ? k.label.split(" · ")[0] : ""))].filter(Boolean);
    if (groups.length > 1) { statSel = statSel || groups[0]; const sub = el("div", "subtabs"); groups.forEach(gn => { const b = el("button", null, gn); b.setAttribute("aria-pressed", String(statSel === gn)); b.onclick = () => { statSel = gn; renderPanel(); }; sub.append(b); }); body.append(sub);
      kpis = kpis.filter(k => k.label.startsWith(statSel + " · ")); vids = vids.filter(v => (v.title || "").startsWith("[" + statSel + "]")).map(v => ({ ...v, title: v.title.replace(/^\[[^\]]+\]\s*/, "") })); }
    const k = el("div", "kpis"); kpis.forEach(x => k.append(kpi(x))); body.append(k);
    const recent = vids.slice(0, 10).reverse();
    if (recent.length > 1) { const c = el("div", "card"); c.append(el("div", "label", `Views on your last ${recent.length} videos (oldest → newest)`));
      c.append(barChart(recent.map(v => v.views || 0), recent.map(v => v.published ? new Date(v.published).toLocaleDateString([], { month: "numeric", day: "numeric" }) : ""), t.cfg.color));
      const avg = Math.round(recent.reduce((a, v) => a + (v.views || 0), 0) / recent.length); c.append(el("div", "small", `Average ${fmt(avg)} views · best ${fmt(Math.max(...recent.map(v => v.views || 0)))}`)); body.append(c); }
    if (vids.length) { const c = el("div", "card"); c.append(el("div", "label", "Recent videos"));
      vids.slice(0, 15).forEach(v => { const r = el("div", "vid"); const u = safeUrl(v.url); const a = el(u ? "a" : "span", "t", v.title || "Untitled"); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } r.append(a, el("span", "n", fmt(v.views) + " views"));
        r.append(el("span", "m", v.published ? new Date(v.published).toLocaleDateString() : ""), el("span", "m", (v.likes != null ? fmt(v.likes) + " likes" : ""))); c.append(r); }); body.append(c); }
    body.append(el("div", "small", "Collected " + ago(m.updatedAt) + " · refreshes hourly"));
  }
  function vTrending(t, body) {
    const tr = (t.metrics || {}).trending || []; if (t.metrics && t.metrics.trendingAt) body.append(el("div", "small", "Scanned " + ago(t.metrics.trendingAt) + " · ranked by how far each video beats its channel's normal views"));
    const c = el("div", "card"); tr.slice(0, 15).forEach(x => { const s = el("div", "shot"); const u = safeUrl(x.url); const a = el(u ? "a" : "div", "t", x.title); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } s.append(a);
      s.append(el("div", "m", [x.channel, x.views != null ? fmt(x.views) + " views" : null, x.age].filter(Boolean).join(" · "))); c.append(s); }); body.append(c);
  }
  function vResearch(t, body) {
    const rs = t.state.research || []; if (!rs.length) { body.append(empty("No research yet", "The team's research shows up here after its first run.")); return; }
    rs.slice(0, 7).forEach(r => { const c = el("div", "card"); c.append(el("div", "label", r.date || ago(r.createdAt)));
      (r.items || []).forEach(x => { const s = el("div", "shot"); const u = safeUrl(x.url); const a = el(u ? "a" : "div", "t", x.title || x.creator || "Finding"); if (u) { a.href = u; a.target = "_blank"; a.rel = "noopener"; } s.append(a);
        const m = [x.creator, x.metric].filter(Boolean).join(" · "); if (m) s.append(el("div", "m", m)); if (x.whyItWorks) s.append(el("p", null, x.whyItWorks)); c.append(s); }); body.append(c); });
  }
  function vActivity(t, body) {
    let log = t.log; if (t.cfg.virtual) log = Object.values(M.teams).flatMap(x => x.log.map(l => ({ ...l, agent: (x.cfg.virtual ? "" : x.cfg.name + " · ") + (l.agent || ""), color: x.cfg.color }))).sort((a, b) => (b.t || "").localeCompare(a.t || ""));
    if (!log.length) { body.append(empty("No activity yet", "Every step the agents take shows up here.")); return; }
    const c = el("div", "card"); const ul = el("ul", "log");
    log.slice(0, 80).forEach(e => { const li = el("li"); const tm = el("time", null, clock(e.t)); tm.title = new Date(e.t).toLocaleString(); li.append(tm);
      const sp = el("span"); if (e.agent) { const b = el("b", null, e.agent + " "); b.style.color = e.color || t.cfg.color; sp.append(b); } sp.append(document.createTextNode(e.msg || "")); li.append(sp); ul.append(li); });
    c.append(ul); body.append(c);
  }

  /* ---------------- HUD ---------------- */
  function renderHUD() {
    const all = Object.values(M.teams); const working = all.reduce((n, t) => n + t.agents.filter(a => a.status === "working").length, 0);
    const pending = all.reduce((n, t) => n + (t.state.ideas || []).filter(i => (i.status || "pending") === "pending").length, 0);
    const tk = (M.teams.tiktok.metrics || {}).kpis || []; const fol = tk.find(k => k.label === "Followers");
    const yk = (M.teams.youtube.metrics || {}).kpis || []; const subs = yk.filter(k => /subscribers$/.test(k.label)).reduce((n, k) => n + (k.value || 0), 0);
    const chips = $("#chips"); chips.replaceChildren();
    const chip = (v, k, d) => { const c = el("div", "chip"); c.append(el("div", "v", v)); c.append(el("div", "k", k)); if (d) c.append(d); chips.append(c); };
    chip(String(working), "Working now"); chip(String(pending), "Ideas to review");
    if (fol) chip(fmt(fol.value), "TikTok followers", fol.delta ? el("div", "d " + (fol.delta >= 0 ? "up" : "down"), (fol.delta >= 0 ? "+" : "") + fol.delta) : null);
    if (subs) chip(fmt(subs), "YouTube subs");
    $("#liveText").textContent = "Live · " + all.filter(t => t.hired && !t.cfg.virtual).length + " of 5 teams hired";
    const bar = $("#teambar"); bar.replaceChildren();
    CFG.teams.forEach(c => { const t = M.teams[c.id]; const b = el("button"); b.dataset.id = c.id; const sw = el("span", "sw"); sw.style.background = c.color; b.append(sw, document.createTextNode(c.virtual ? "HQ" : c.name));
      if (t.agents.some(a => a.status === "working")) b.append(el("span", "live")); b.onclick = () => focusTeam(c.id); bar.append(b); });
    syncTeambar();
    const tr = $("#tickerTrack"); tr.replaceChildren();
    const items = all.flatMap(t => t.log.slice(0, 6).map(l => ({ ...l, team: t }))).sort((a, b) => (b.t || "").localeCompare(a.t || "")).slice(0, 24);
    (items.length ? items : [{ msg: "Waiting for the first agent run…", team: M.teams.hq }]).forEach(i => { const s = el("span"); const b = el("b", null, (i.team.cfg.virtual ? "" : i.team.cfg.name + " · ") + (i.agent || "") + "  "); b.style.color = i.team.cfg.color; s.append(b, document.createTextNode((i.msg || "") + (i.t ? "  · " + ago(i.t) : ""))); tr.append(s); });
  }

  /* ---------------- boot ---------------- */
  async function refresh(first) {
    const changed = await load(); if (!M) return;
    if (changed || first) { buildWorld(); renderHUD(); if (focused) renderPanel(); if (first) { setVB(fitBox(worldBox, .96)); if (START && M.teams[START]) setTimeout(() => focusTeam(START), 500); } else if (focused) setVB(vb); else setVB(fitBox(worldBox, .96)); }
  }
  $("#back").onclick = zoomOut;
  refresh(true).then(enablePanZoom);
  setInterval(refresh, 60000);
})();
