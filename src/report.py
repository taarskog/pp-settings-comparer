"""Render a self-contained HTML comparison report for Power Platform environment settings.

Public API::

    render_html(data: dict) -> str

The returned document inlines all CSS/JS and bakes the data in as ``const DATA``.
It makes no network requests and uses no storage, so it works from ``file://``.
"""

from __future__ import annotations

import json

__all__ = ["render_html"]


def _embed_json(data: dict) -> str:
    """Serialize *data* so it is safe to place inside a <script> block."""
    text = json.dumps(data, ensure_ascii=False, default=str)
    # No raw "<": it can close the script element or, via "<!--<script>", flip the
    # HTML tokenizer into script-data-escaped state. U+2028/29 are raw newlines in JS.
    return (
        text.replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Environment Settings Comparison</title>
<script>
  (() => {
    let saved = null;
    try { saved = localStorage.getItem("cpTheme"); } catch (e) { /* storage can be blocked */ }
    const search = new URLSearchParams(window.location.search);
    // "scoutTheme" is a legacy alias kept for an external test harness.
    const param = search.get("theme") || search.get("scoutTheme");
    const pref = param || saved || "system";
    const theme =
      pref === "system"
        ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
        : pref;
    document.documentElement.setAttribute("data-theme", theme);
    window.__themePref = pref;
  })();
</script>
<style>
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 24px;
  background: var(--cp-bg);
  color: var(--cp-text);
  font-family: "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.45;
}

.card {
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.14);
}

header.card { position: relative; padding: 20px 24px; margin-bottom: 16px; }
header h1 { margin: 0 0 4px; padding-right: 130px; font-size: 20px; font-weight: 600; }
header .sub { color: var(--cp-text-muted); font-size: 13px; }

.themeswitch {
  position: absolute; top: 18px; right: 20px;
  display: inline-flex; gap: 2px; padding: 3px;
  background: var(--cp-surface-soft);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
}
.themeswitch button {
  display: inline-flex; padding: 5px 8px;
  background: transparent; border: 0; border-radius: 8px;
  color: var(--cp-text-muted);
}
.themeswitch button:hover { background: var(--cp-surface); color: var(--cp-text); }
.themeswitch button[aria-pressed="true"] { background: var(--cp-accent); color: var(--cp-accent-fg); }
.themeswitch svg { display: block; width: 16px; height: 16px; }

.meta { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 14px; }
.meta div { display: flex; flex-direction: column; }
.meta .lbl {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--cp-text-soft);
}
.meta .val { font-size: 14px; font-weight: 600; }
.mono { font-family: Consolas, "Courier New", Courier, monospace; }

.toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 12px 16px; margin-bottom: 12px;
}

input[type="search"], select, button {
  font: inherit;
  color: var(--cp-text);
  background: var(--cp-surface);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  padding: 7px 10px;
}
input[type="search"] { min-width: 260px; flex: 1 1 260px; }
input[type="search"]:focus-visible, select:focus-visible, button:focus-visible {
  outline: 2px solid var(--cp-accent); outline-offset: 1px;
}
button { cursor: pointer; }
button:hover { border-color: var(--cp-border-strong); }
button.on {
  background: var(--cp-accent); border-color: var(--cp-accent); color: var(--cp-accent-fg);
}

.toggle { display: inline-flex; align-items: center; gap: 7px; user-select: none; cursor: pointer; }

.count { margin-left: auto; color: var(--cp-text-muted); font-size: 13px; }

.envwrap { position: relative; }
.popover {
  position: absolute; top: calc(100% + 6px); left: 0; z-index: 40;
  width: 320px; max-height: 60vh; overflow: auto;
  padding: 12px;
  background: var(--cp-panel-strong);
  backdrop-filter: blur(6px);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  box-shadow: var(--cp-shadow);
}
.popover[hidden] { display: none; }
.popover .row { display: flex; align-items: center; gap: 8px; padding: 5px 4px; border-radius: 0.625rem; }
.popover .row:hover { background: var(--cp-surface-soft); }
.popover label { display: flex; align-items: center; gap: 8px; cursor: pointer; flex: 1; min-width: 0; }
.popover .en { display: block; font-weight: 600; }
.popover .es { display: block; color: var(--cp-text-muted); font-size: 12px; }
.popover .acts { display: flex; gap: 8px; margin-bottom: 8px; }
.popover .acts button { padding: 4px 12px; font-size: 13px; }
.popover .note { margin-bottom: 8px; color: var(--cp-text-soft); font-size: 12px; }
.popover .note[hidden] { display: none; }
.popover .row.inactive .en { color: var(--cp-text-muted); font-weight: 500; }

.tablewrap {
  overflow: auto;
  max-height: calc(100vh - 300px);
  border: 1px solid var(--cp-border);
  border-radius: 16px;
  background: var(--cp-surface);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.14);
}

table { border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; }

thead th {
  position: sticky; top: 0; z-index: 2;
  background: var(--cp-bg-elevated);
  border-bottom: 1px solid var(--cp-border-strong);
  text-align: left; vertical-align: bottom;
  padding: 10px 12px;
  font-size: 13px;
}
thead th.corner {
  left: 0; z-index: 3;
  min-width: 320px; max-width: 320px;
  border-right: 1px solid var(--cp-border-strong);
}
thead th.env { min-width: 170px; }
thead .en { display: block; font-weight: 600; }
thead .es { display: block; color: var(--cp-text-muted); font-size: 11px; font-weight: 400; }
thead .mark {
  display: inline-block; margin-left: 6px; padding: 0 6px;
  border-radius: 999px; font-size: 11px; font-weight: 700; cursor: help;
  color: var(--cp-accent-fg);
}
thead .mark.error { background: var(--cp-danger); }
thead .mark.partial { background: var(--cp-warning); }

tbody th.rowhead {
  position: sticky; left: 0; z-index: 1;
  background: var(--cp-surface);
  border-right: 1px solid var(--cp-border-strong);
  min-width: 320px; max-width: 320px;
  text-align: left; vertical-align: top; font-weight: 400;
  padding: 8px 12px;
  cursor: default;
}
tbody th.rowhead .nm { display: block; font-weight: 600; overflow-wrap: anywhere; }
tbody th.rowhead .ky {
  display: block; color: var(--cp-text-soft); font-size: 11px;
  font-family: Consolas, "Courier New", Courier, monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
tbody td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--cp-border);
  max-width: 320px;
  vertical-align: top;
  overflow-wrap: anywhere;
  vertical-align: top;
}
tbody th.rowhead { border-bottom: 1px solid var(--cp-border); }
tbody tr:hover th.rowhead, tbody tr:hover td { background: var(--cp-surface-soft); }
tbody td.diff { background: var(--cp-highlight); }
tbody tr:hover td.diff { background: var(--cp-accent-soft); }
tbody td.yes { color: var(--cp-success); font-weight: 600; }
tbody td.no { color: var(--cp-text-muted); }
tbody td.none { color: var(--cp-text-soft); }
tbody td.override { box-shadow: inset 3px 0 0 var(--cp-accent); }
tbody tr.diffrow th.rowhead { box-shadow: inset 3px 0 0 var(--cp-accent); }

.empty { padding: 32px; text-align: center; color: var(--cp-text-muted); }

#tip {
  position: fixed; z-index: 90; max-width: 380px; pointer-events: none;
  padding: 10px 12px;
  background: var(--cp-panel-strong);
  color: var(--cp-text);
  border: 1px solid var(--cp-border);
  border-radius: 0.625rem;
  box-shadow: var(--cp-shadow);
  font-size: 13px;
}
#tip[hidden] { display: none; }
#tip .t { font-weight: 600; margin-bottom: 4px; }
#tip .d { color: var(--cp-text-muted); }
#tip .k {
  margin-top: 6px; color: var(--cp-text-soft); font-size: 11px;
  font-family: Consolas, "Courier New", Courier, monospace;
}
</style>
</head>
<body>

<header class="card">
  <div class="themeswitch" role="group" aria-label="Color theme">
    <button type="button" data-theme-pref="light" title="Light theme" aria-label="Light theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>
    <button type="button" data-theme-pref="system" title="Match system theme" aria-label="System theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></button>
    <button type="button" data-theme-pref="dark" title="Dark theme" aria-label="Dark theme"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg></button>
  </div>
  <h1>Environment Settings Comparison</h1>
  <div class="sub">Power Platform tenant configuration matrix</div>
  <div class="meta">
    <div><span class="lbl">Tenant</span><span class="val mono" id="m-tenant"></span></div>
    <div><span class="lbl">Generated (UTC)</span><span class="val" id="m-gen"></span></div>
    <div><span class="lbl">Environments</span><span class="val" id="m-envs"></span></div>
    <div><span class="lbl">Settings</span><span class="val" id="m-settings"></span></div>
  </div>
</header>

<div class="toolbar card">
  <input type="search" id="q" placeholder="Filter by name, key, category or description…" autocomplete="off">
  <select id="cat"><option value="">All categories</option></select>
  <label class="toggle"><input type="checkbox" id="onlydiff"> Only differences</label>
  <span class="envwrap">
    <button type="button" id="envbtn" aria-expanded="false">Environments</button>
    <div class="popover" id="envpop" hidden>
      <div class="acts">
        <button type="button" id="env-active" title="Only environments that are enabled and ready">Active</button>
        <button type="button" id="env-all">All</button>
        <button type="button" id="env-none">None</button>
      </div>
      <div class="note" id="envnote" hidden></div>
      <div id="envlist"></div>
    </div>
  </span>
  <span class="count" id="count"></span>
</div>

<div class="tablewrap">
  <table>
    <thead><tr id="hrow"></tr></thead>
    <tbody id="body"></tbody>
  </table>
  <div class="empty" id="empty" hidden>No settings match the current filters.</div>
</div>

<div id="tip" hidden></div>

<script>
const DATA = __DATA__;

const DASH = "\\u2014";
const YES = new Set(["yes", "true", "on", "enabled", "allowed", "required"]);
const NO = new Set(["no", "false", "off", "disabled", "blocked", "not allowed"]);

const envs = DATA.environments || [];
const settings = DATA.settings || [];
const haystacks = settings.map((s) =>
  (s.name + " " + s.key + " " + (s.category || "") + " " + (s.description || "")).toLowerCase()
);
const hidden = new Set();

const $ = (id) => document.getElementById(id);
const tbody = $("body");
const tip = $("tip");

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ---------- header meta ---------- */
$("m-tenant").textContent = DATA.tenantId || DASH;
$("m-gen").textContent = DATA.generatedUtc || DASH;
$("m-envs").textContent = envs.length;
$("m-settings").textContent = settings.length;

/* ---------- theme (light / system / dark) ---------- */
const media = window.matchMedia("(prefers-color-scheme: dark)");
let themePref = window.__themePref || "system";

function applyTheme() {
  const theme = themePref === "system" ? (media.matches ? "dark" : "light") : themePref;
  document.documentElement.setAttribute("data-theme", theme);
  for (const b of document.querySelectorAll("[data-theme-pref]")) {
    b.setAttribute("aria-pressed", String(b.dataset.themePref === themePref));
  }
}
media.addEventListener("change", () => { if (themePref === "system") applyTheme(); });
document.querySelector(".themeswitch").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-theme-pref]");
  if (!b) return;
  themePref = b.dataset.themePref;
  try { localStorage.setItem("cpTheme", themePref); } catch (e) { /* storage can be blocked */ }
  applyTheme();
});
applyTheme();

/* ---------- category dropdown ---------- */
const cats = [...new Set(settings.map((s) => s.category).filter(Boolean))].sort();
for (const c of cats) {
  const o = document.createElement("option");
  o.value = c;
  o.textContent = c;
  $("cat").appendChild(o);
}

/* ---------- environment popover ---------- */
// Environments that are not running are hidden on load - their values are stale or absent.
const INACTIVE_STATES = new Set(
  ["disabled", "adminmode", "suspended", "deleting", "deleted", "failed", "notspecified"]
);
const activeIds = new Set();
const isActive = (e) => !INACTIVE_STATES.has(String(e.state || "").toLowerCase().replace(/\\s+/g, ""));

const envlist = $("envlist");
for (const e of envs) {
  const active = isActive(e);
  if (active) activeIds.add(e.id);
  else hidden.add(e.id);
  const row = document.createElement("div");
  row.className = active ? "row" : "row inactive";
  const secondary = [e.type, e.region, e.state].filter(Boolean).join(" \\u00b7 ");
  row.innerHTML =
    '<label><input type="checkbox" data-env="' + esc(e.id) + '"' + (active ? " checked" : "") + ">" +
    '<span><span class="en">' + esc(e.name) + "<\\/span>" +
    '<span class="es">' + esc(secondary) + "<\\/span><\\/span><\\/label>";
  envlist.appendChild(row);
}

const inactiveCount = envs.length - activeIds.size;
if (inactiveCount) {
  $("envnote").textContent =
    inactiveCount + " inactive environment" + (inactiveCount === 1 ? "" : "s") + " hidden by default.";
  $("envnote").hidden = false;
}

envlist.addEventListener("change", (ev) => {
  const cb = ev.target.closest("input[data-env]");
  if (!cb) return;
  if (cb.checked) hidden.delete(cb.dataset.env);
  else hidden.add(cb.dataset.env);
  render();
});

function apply(keep) {
  hidden.clear();
  for (const cb of envlist.querySelectorAll("input[data-env]")) {
    cb.checked = keep(cb.dataset.env);
    if (!cb.checked) hidden.add(cb.dataset.env);
  }
  render();
}
$("env-active").addEventListener("click", () => apply((id) => activeIds.has(id)));
$("env-all").addEventListener("click", () => apply(() => true));
$("env-none").addEventListener("click", () => apply(() => false));

$("envbtn").addEventListener("click", (ev) => {
  ev.stopPropagation();
  const pop = $("envpop");
  pop.hidden = !pop.hidden;
  $("envbtn").setAttribute("aria-expanded", String(!pop.hidden));
});
document.addEventListener("click", (ev) => {
  const pop = $("envpop");
  if (!pop.hidden && !pop.contains(ev.target) && ev.target !== $("envbtn")) pop.hidden = true;
});

/* ---------- filters ---------- */
let query = "";
let timer = 0;
$("q").addEventListener("input", (ev) => {
  const v = ev.target.value.trim().toLowerCase();
  clearTimeout(timer);
  timer = setTimeout(() => { query = v; render(); }, 150);
});
$("cat").addEventListener("change", render);
$("onlydiff").addEventListener("change", render);

/* ---------- rendering ---------- */
function visibleEnvs() {
  return envs.filter((e) => !hidden.has(e.id));
}

function matches(i) {
  return !query || haystacks[i].includes(query);
}

function valueClass(v, display) {
  if (v == null) return "none";
  const d = String(display).toLowerCase();
  if (v.raw === true || YES.has(d)) return "yes";
  if (v.raw === false || NO.has(d)) return "no";
  return "";
}

function renderHead(vis) {
  let html = '<th class="corner">Setting<\\/th>';
  for (const e of vis) {
    const secondary = [e.type, e.region].filter(Boolean).join(" \\u00b7 ");
    let mark = "";
    if (e.status && e.status !== "ok") {
      const msg = e.statusMessage || (e.status === "error" ? "No access" : "Partial data");
      mark = '<span class="mark ' + esc(e.status) + '" title="' + esc(msg) + '">!<\\/span>';
    }
    html +=
      '<th class="env"><span class="en">' + esc(e.name) + mark + "<\\/span>" +
      '<span class="es">' + esc(secondary) + "<\\/span><\\/th>";
  }
  $("hrow").innerHTML = html;
}

function render() {
  const vis = visibleEnvs();
  const onlyDiff = $("onlydiff").checked;
  const cat = $("cat").value;
  renderHead(vis);

  const parts = [];
  let shown = 0;

  for (let i = 0; i < settings.length; i++) {
    const s = settings[i];
    if (cat && s.category !== cat) continue;
    if (!matches(i)) continue;

    // Cells with no value are ignored entirely: a row differs only when the values
    // that do exist disagree, and "common" is the majority among those.
    const displays = new Array(vis.length);
    const counts = new Map();
    let common = null;
    let best = -1;
    for (let c = 0; c < vis.length; c++) {
      const v = s.values ? s.values[vis[c].id] : null;
      const d = v ? String(v.display) : DASH;
      displays[c] = d;
      if (!v) continue;
      const n = (counts.get(d) || 0) + 1;
      counts.set(d, n);
      if (n > best) { best = n; common = d; }
    }
    const differs = counts.size > 1;
    if (onlyDiff && !differs) continue;
    shown++;

    let cells = "";
    for (let c = 0; c < vis.length; c++) {
      const v = s.values ? s.values[vis[c].id] : null;
      const d = displays[c];
      let cls = valueClass(v, d);
      if (differs && v && d !== common) cls += " diff";
      if (v && v.source === "override") cls += " override";
      cells += '<td class="' + cls.trim() + '">' + esc(d) + "<\\/td>";
    }

    parts.push(
      '<tr data-i="' + i + '"' + (differs ? ' class="diffrow"' : "") + ">" +
      '<th class="rowhead" scope="row"><span class="nm">' + esc(s.name) + "<\\/span>" +
      '<span class="ky">' + esc(s.key) + "<\\/span><\\/th>" + cells + "<\\/tr>"
    );
  }

  const tpl = document.createElement("template");
  tpl.innerHTML = parts.join("");
  tbody.replaceChildren(tpl.content);

  $("empty").hidden = shown > 0;
  $("count").textContent =
    "Showing " + shown + " of " + settings.length + " settings \\u00b7 " +
    vis.length + " of " + envs.length + " environments";
  hideTip();
}

/* ---------- tooltip (delegated) ---------- */
let tipRow = null;

function hideTip() {
  tip.hidden = true;
  tipRow = null;
}

function placeTip(x, y) {
  const pad = 14;
  const r = tip.getBoundingClientRect();
  let left = x + pad;
  let top = y + pad;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - pad;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - pad;
  tip.style.left = Math.max(8, left) + "px";
  tip.style.top = Math.max(8, top) + "px";
}

tbody.addEventListener("mousemove", (ev) => {
  const th = ev.target.closest("th.rowhead");
  const row = th ? th.parentElement : null;
  if (!row) { if (!tip.hidden) hideTip(); return; }

  if (row !== tipRow) {
    const s = settings[Number(row.dataset.i)];
    if (!s || !s.description) { hideTip(); return; }
    tip.innerHTML =
      '<div class="t">' + esc(s.name) + "<\\/div>" +
      '<div class="d">' + esc(s.description) + "<\\/div>" +
      '<div class="k">' + esc(s.key) + "<\\/div>";
    tip.hidden = false;
    tipRow = row;
  }
  if (!tip.hidden) placeTip(ev.clientX, ev.clientY);
});
tbody.addEventListener("mouseleave", hideTip);
document.querySelector(".tablewrap").addEventListener("scroll", hideTip, { passive: true });

render();
</script>
</body>
</html>
"""


def render_html(data: dict) -> str:
    """Return a complete, self-contained HTML report document for *data*."""
    return _TEMPLATE.replace("__DATA__", _embed_json(data))
