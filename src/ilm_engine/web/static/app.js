"use strict";

/* ILM Engine web UI: upload → live pipeline → human review → results. No build step, no framework. */

const app = document.getElementById("app");
const state = {
  pipeline: null,
  books: [],
  overview: {},
  cleanup: [],
  upload: null,
  reviewer: load("reviewer", { id: "demo-reviewer", role: "editor_reviewer" }),
};

/* ---------- helpers ---------- */

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem("ilm." + key)) ?? fallback; } catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem("ilm." + key, JSON.stringify(value)); } catch { /* private mode */ }
}
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const fmt = (n) => (typeof n === "number" ? n.toLocaleString("en-US") : esc(n ?? "—"));
const label = (s) => String(s ?? "").replace(/_/g, " ");
const ARABIC_RUN = /[\u0600-\u06FF\uFDF0-\uFDFF][\u0600-\u06FF\uFDF0-\uFDFF\u064B-\u065F\s\-()«»،؛.:0-9٠-٩]*/g;
/* Escape, then isolate every Arabic run so it cannot reorder the English around it. */
const bidi = (text) => esc(text).replace(ARABIC_RUN, (run) => {
  const trimmed = run.trimEnd();
  return `<bdi dir="rtl" lang="ar" class="ar-inline">${trimmed}</bdi>${run.slice(trimmed.length)}`;
});
const ar = (text, tag = "span") => `<${tag} class="ar" dir="rtl" lang="ar">${esc(text)}</${tag}>`;

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = response.statusText;
    try { message = (await response.json()).detail || message; } catch { /* not JSON */ }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}

function toast(message, bad = false) {
  const el = document.createElement("div");
  el.className = "toast" + (bad ? " bad" : "");
  el.textContent = message;
  document.getElementById("toasts").append(el);
  setTimeout(() => el.remove(), bad ? 6000 : 3200);
}

function conf(value) {
  if (value == null) return '<span class="muted small">—</span>';
  const color = value >= 0.9 ? "var(--ok)" : value >= 0.75 ? "var(--gold)" : "var(--bad)";
  return `<span class="conf"><i style="--w:${Math.round(value * 100)}%;--c:${color}"></i>${value.toFixed(2)}</span>`;
}

function statusChip(status) {
  const kind = { auto_approved: "ok", approved: "ok", edited: "ok", rejected: "bad", pending_review: "warn", reprocess_requested: "info" }[status] || "";
  return `<span class="chip ${kind}">${esc(label(status))}</span>`;
}

function anchorPage(anchor) {
  return anchor ? anchor.scan_page ?? anchor.page : null;
}

function openScan(pub, page) {
  const dialog = document.getElementById("pdfdialog");
  document.getElementById("pdftitle").textContent = page ? `Scan · page ${page}` : "Scan";
  document.getElementById("pdfframe").src = `/api/books/${encodeURIComponent(pub)}/pdf#page=${page || 1}`;
  dialog.showModal();
}
document.querySelector("#pdfdialog [data-close]").onclick = () => document.getElementById("pdfdialog").close();

function highlight(text, marks) {
  let html = "", position = 0;
  for (const [start, end] of marks) {
    if (start < position) continue;
    html += esc(text.slice(position, start)) + `<mark>${esc(text.slice(start, end))}</mark>`;
    position = end;
  }
  return html + esc(text.slice(position));
}

/* ---------- theme ---------- */

const themeButton = document.getElementById("theme");
function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}
applyTheme(load("theme", null));
themeButton.onclick = () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  const next = dark ? "light" : "dark";
  applyTheme(next);
  save("theme", next);
};

/* ---------- routing ---------- */

const TABS = [
  ["overview", "Overview"],
  ["review", "Human review"],
  ["units", "Knowledge units"],
  ["people", "People & relations"],
  ["graph", "Graph"],
  ["search", "Search"],
  ["downloads", "Downloads"],
];

async function refreshBooks() {
  state.books = await api("/api/books");
  const picker = document.getElementById("bookpicker");
  picker.hidden = state.books.length === 0;
  picker.innerHTML = '<option value="">Processed books…</option>' +
    state.books.map((b) => `<option value="${esc(b.pub_ref)}">${esc(b.title || b.pub_ref)}</option>`).join("");
}
document.getElementById("bookpicker").onchange = (event) => {
  if (event.target.value) location.hash = `#/book/${encodeURIComponent(event.target.value)}/overview`;
};

function renderNav(pub, tab) {
  const nav = document.getElementById("booknav");
  const picker = document.getElementById("bookpicker");
  picker.value = pub || "";
  if (!pub) { nav.innerHTML = ""; return; }
  const pending = state.overview[pub]?.review?.pending_review;
  nav.innerHTML = TABS.map(([key, name]) => {
    const badge = key === "review" && pending ? `<span class="count">${pending}</span>` : "";
    return `<a href="#/book/${encodeURIComponent(pub)}/${key}" class="${key === tab ? "active" : ""}">${name}${badge}</a>`;
  }).join("");
}

async function route() {
  state.cleanup.splice(0).forEach((fn) => fn());
  const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  try {
    if (parts[0] === "run" && parts[1]) {
      renderNav(null);
      await viewRun(parts[1]);
    } else if (parts[0] === "book" && parts[1]) {
      const pub = parts[1], tab = parts[2] || "overview";
      if (!state.overview[pub]) state.overview[pub] = await api(`/api/books/${encodeURIComponent(pub)}/overview`);
      renderNav(pub, tab);
      await VIEWS[tab](pub);
    } else {
      renderNav(null);
      await viewHome();
    }
  } catch (error) {
    app.innerHTML = `<div class="card pad"><h2>Something went wrong</h2><p class="muted">${esc(error.message)}</p><a class="btn" href="#/">Back to start</a></div>`;
  }
  app.focus({ preventScroll: true });
}
window.addEventListener("hashchange", route);

/* ---------- home: upload ---------- */

async function viewHome() {
  await refreshBooks();
  app.innerHTML = `
    <section class="hero">
      <div>
        <span class="chip accent">Step 1 · Upload</span>
        <h1 style="margin-top:12px">Turn a digitized book into a traceable knowledge layer</h1>
        <p class="lead">Upload the book's structured JSON (and its scan PDF). The engine extracts metadata, structure,
        footnotes, citations, biographical entries, people and relationships, and points every fact back to the exact
        source text. The original is never modified.</p>
        <ol class="journey">
          <li><span><b>Upload</b> the book JSON and, optionally, the scan PDF.</span></li>
          <li><span><b>Watch</b> the 21-step pipeline run, phase by phase.</span></li>
          <li><span><b>Review</b> what the engine is unsure about, with the source passage highlighted.</span></li>
          <li><span><b>Explore</b> the results: entries, people, relationships, graph, search and exports.</span></li>
        </ol>
      </div>
      <form class="card pad stack" id="upload">
        <h2>New book</h2>
        <label class="drop" id="drop-json">
          <span class="icon">📄</span>
          <b data-name>Drop the book JSON here</b>
          <span class="muted small" data-hint>or click to choose · required</span>
          <input type="file" name="book" accept=".json,application/json">
        </label>
        <label class="drop" id="drop-pdf">
          <span class="icon">🖼️</span>
          <b data-name>Drop the scan PDF here</b>
          <span class="muted small" data-hint>optional · used for page links in review</span>
          <input type="file" name="pdf" accept=".pdf,application/pdf">
        </label>
        <label class="toggle"><input type="checkbox" name="fresh" checked> Fresh run <span class="muted small">(re-run every step, ignore the cache)</span></label>
        <label class="toggle"><input type="checkbox" name="pace" checked> Presentation pace <span class="muted small">(slow the animation down to follow each step)</span></label>
        <button class="btn primary big" type="submit" disabled>Start processing →</button>
      </form>
    </section>
    <section style="margin-top:40px" class="stack">
      <div class="spread"><h2>Processed books</h2><span class="muted small">${state.books.length} in the output folder</span></div>
      ${state.books.length ? `<div class="books">${state.books.map(bookCard).join("")}</div>` : '<div class="card empty">No book processed yet. Upload one above.</div>'}
    </section>`;

  const form = document.getElementById("upload");
  const files = { book: null, pdf: null };
  function pickFor(key, file) {
    if (!file) return;
    const zone = document.getElementById(key === "book" ? "drop-json" : "drop-pdf");
    files[key] = file;
    zone.classList.add("filled");
    zone.querySelector("[data-name]").textContent = file.name;
    zone.querySelector("[data-hint]").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · click to change`;
    form.querySelector("button[type=submit]").disabled = !files.book;
  }
  for (const [id, key] of [["drop-json", "book"], ["drop-pdf", "pdf"]]) {
    const zone = document.getElementById(id);
    const input = zone.querySelector("input");
    input.onchange = () => pickFor(key, input.files[0]);
    zone.ondragover = (event) => { event.preventDefault(); zone.classList.add("over"); };
    zone.ondragleave = () => zone.classList.remove("over");
    zone.ondrop = (event) => {
      event.preventDefault();
      zone.classList.remove("over");
      const dropped = [...event.dataTransfer.files];
      pickFor("book", dropped.find((f) => f.name.toLowerCase().endsWith(".json")));
      pickFor("pdf", dropped.find((f) => f.name.toLowerCase().endsWith(".pdf")));
    };
  }

  form.onsubmit = async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    button.textContent = "Uploading…";
    const body = new FormData();
    body.append("book", files.book);
    if (files.pdf) body.append("pdf", files.pdf);
    body.append("fresh", form.fresh.checked ? "true" : "false");
    try {
      const { job_id } = await api("/api/runs", { method: "POST", body });
      state.upload = { name: files.book.name, pdf: files.pdf?.name, pace: form.pace.checked };
      location.hash = `#/run/${job_id}`;
    } catch (error) {
      toast(error.message, true);
      button.disabled = false;
      button.textContent = "Start processing →";
    }
  };
}

function bookCard(book) {
  const pub = encodeURIComponent(book.pub_ref);
  return `<article class="card book-card">
    ${book.title ? ar(book.title, "div") : ""}
    <span class="mono muted">${esc(book.pub_ref)}</span>
    <span class="muted small">${book.finished_at ? "Processed " + new Date(book.finished_at).toLocaleString() : ""}</span>
    <div class="row" style="margin-top:6px">
      <a class="btn primary" href="#/book/${pub}/overview">Results</a>
      <a class="btn" href="#/book/${pub}/review">Review</a>
    </div>
  </article>`;
}

/* ---------- run: animated pipeline ---------- */

const COUNTERS = [
  ["pages", "Pages"], ["blocks", "Blocks"], ["sections", "Sections"],
  ["annotations", "Footnotes"], ["citations", "Citations"], ["units", "Entries"],
  ["entities", "People"], ["relationships", "Relations"], ["review_items", "To review"],
];

async function viewRun(jobId) {
  state.pipeline = state.pipeline || (await api("/api/pipeline"));
  const upload = state.upload || { name: "uploaded book", pace: true };
  const phases = [];
  for (const step of state.pipeline) {
    let phase = phases.find((p) => p.name === step.phase);
    if (!phase) phases.push((phase = { name: step.phase, steps: [] }));
    phase.steps.push(step);
  }
  const total = state.pipeline.length;
  app.innerHTML = `
    <div class="run-head">
      <div class="spread">
        <div>
          <span class="chip accent">Step 2 · Processing</span>
          <h1 style="margin-top:10px">Processing <span class="mono" style="font-size:.8em">${esc(upload.name)}</span></h1>
          <p class="muted" id="run-status">Starting the pipeline…</p>
        </div>
        <div class="row">
          <span class="chip" id="run-clock">0.0 s</span>
          <label class="toggle small"><input type="checkbox" id="pace" ${upload.pace ? "checked" : ""}> Presentation pace</label>
        </div>
      </div>
      <div class="progress"><span id="run-bar"></span></div>
      <div id="run-banner"></div>
    </div>
    <div class="run-layout">
      <div class="phases">
        ${phases.map((phase, i) => `
          <section class="card phase" data-phase="${i}">
            <div class="phase-title">${esc(phase.name)}</div>
            ${phase.steps.map((s) => `
              <div class="step pending" data-step="${esc(s.name)}">
                <div class="dot">${s.index}</div>
                <div>
                  <div class="step-title">${esc(s.title)}</div>
                  <div class="step-doing">${esc(s.doing)}</div>
                  <div class="step-out"></div>
                </div>
                <div class="step-time"></div>
              </div>`).join("")}
          </section>`).join("")}
      </div>
      <aside class="side">
        <div class="card">
          <div class="spread" style="padding:14px 14px 0"><h3>Live counters</h3><span class="muted small" id="run-count">0 / ${total}</span></div>
          <div class="counters">${COUNTERS.map(([key, name]) => `<div class="counter" data-counter="${key}"><b>0</b><span>${name}</span></div>`).join("")}</div>
        </div>
        <div>
          <h3 style="margin-bottom:8px">Pipeline log</h3>
          <div class="console" id="console" aria-live="off"></div>
        </div>
      </aside>
    </div>`;

  const pace = document.getElementById("pace");
  const consoleEl = document.getElementById("console");
  const started = performance.now();
  const clock = setInterval(() => {
    document.getElementById("run-clock").textContent = `${((performance.now() - started) / 1000).toFixed(1)} s`;
  }, 100);
  let currentPhase = null, finishedCount = 0, closed = false;
  const stepPhase = Object.fromEntries(phases.flatMap((p, i) => p.steps.map((s) => [s.name, i])));
  const byName = Object.fromEntries(state.pipeline.map((s) => [s.name, s]));

  const log = (text, cls = "") => {
    const line = document.createElement("div");
    if (cls) line.className = cls;
    line.innerHTML = bidi(text);
    consoleEl.append(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
  };
  const tag = (i) => `Pipeline_${String(i).padStart(2, "0")}/${total}`;
  const counter = (key, value) => {
    const el = document.querySelector(`[data-counter="${key}"]`);
    if (!el) return;
    const b = el.querySelector("b");
    const from = Number(b.dataset.value || 0);
    b.dataset.value = value;
    el.classList.add("bump");
    setTimeout(() => el.classList.remove("bump"), 700);
    const t0 = performance.now(), duration = pace.checked ? 600 : 150;
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration);
      b.textContent = Math.round(from + (value - from) * (1 - Math.pow(1 - p, 3))).toLocaleString("en-US");
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  const handlers = {
    step_started(ev) {
      const el = document.querySelector(`[data-step="${ev.name}"]`);
      const phaseIndex = stepPhase[ev.name];
      if (phaseIndex !== currentPhase) {
        document.querySelectorAll(".phase.active").forEach((p) => { p.classList.remove("active"); p.classList.add("complete"); });
        currentPhase = phaseIndex;
        log(`━━ ${phases[phaseIndex].name} ━━`, "phase-line");
      }
      document.querySelector(`[data-phase="${phaseIndex}"]`).classList.add("active");
      el.className = "step running";
      el.querySelector(".dot").innerHTML = "•••";
      el.scrollIntoView({ behavior: pace.checked ? "smooth" : "auto", block: "center" });
      document.getElementById("run-status").textContent = `Step ${ev.index} of ${ev.total}: ${byName[ev.name].title}. ${byName[ev.name].doing}…`;
      log(`${tag(ev.index)} ▶ ${byName[ev.name].title}: ${byName[ev.name].doing}...`);
    },
    step_finished(ev) {
      const el = document.querySelector(`[data-step="${ev.name}"]`);
      el.className = `step ${ev.status}`;
      el.querySelector(".dot").textContent = { ran: "✓", cached: "↺", failed: "✕", skipped: "–" }[ev.status] || "✓";
      el.querySelector(".step-time").textContent = `${ev.duration_ms} ms`;
      const cached = ev.status === "cached" ? " (from cache)" : "";
      el.querySelector(".step-out").innerHTML = ev.status === "failed"
        ? `<div class="step-summary">Step failed</div>`
        : `<div class="step-summary">${bidi(ev.summary)}${cached}</div>`;
      finishedCount = ev.index;
      document.getElementById("run-bar").style.width = `${(ev.index / ev.total) * 100}%`;
      document.getElementById("run-count").textContent = `${ev.index} / ${ev.total}`;
      for (const [key, value] of Object.entries(ev.counts || {})) counter(key, value);
      const next = state.pipeline[ev.index];
      const mark = ev.status === "failed" ? "✗" : ev.status === "cached" ? "↺" : "✓";
      const cls = ev.status === "failed" ? "fail" : ev.status === "cached" ? "cached" : "ok";
      log(`${tag(ev.index)} ${mark} ${ev.summary || ev.status}${cached} [${ev.duration_ms} ms].${next ? ` Moving to ${next.title} →` : " Done."}`, cls);
    },
    async done(ev) {
      clearInterval(clock);
      document.querySelectorAll(".phase.active").forEach((p) => { p.classList.remove("active"); p.classList.add("complete"); });
      delete state.overview[ev.pub_ref];
      const overview = (state.overview[ev.pub_ref] = await api(`/api/books/${encodeURIComponent(ev.pub_ref)}/overview`));
      const s = overview.stats;
      const evaluation = ev.evaluation
        ? ` Checked against the editor's printed index: precision <b>${ev.evaluation.precision.toFixed(2)}</b>, recall <b>${ev.evaluation.recall.toFixed(2)}</b>.`
        : "";
      document.getElementById("run-status").textContent = `Finished all ${total} steps in ${document.getElementById("run-clock").textContent}.`;
      document.getElementById("run-banner").innerHTML = `
        <div class="banner ok">
          <div class="grow">
            <h2>✓ Enrichment complete</h2>
            <div>${fmt(s.units)} entries, ${fmt(s.entities)} people, ${fmt(s.relationships)} relationships and ${fmt(s.citations)} citations, every one linked to its source.
            ${fmt(s.review_items)} items need a human decision.${evaluation}</div>
          </div>
          <a class="btn primary big" href="#/book/${encodeURIComponent(ev.pub_ref)}/review">Start human review →</a>
          <a class="btn big" href="#/book/${encodeURIComponent(ev.pub_ref)}/overview">See results</a>
        </div>`;
      log(`Finished ${total} steps. Output: output/${ev.pub_ref}/`, "ok");
      window.scrollTo({ top: 0, behavior: "smooth" });
      refreshBooks();
    },
    failed(ev) {
      clearInterval(clock);
      document.getElementById("run-status").textContent = "The run stopped.";
      document.getElementById("run-banner").innerHTML = `
        <div class="banner bad"><div class="grow"><h2>The pipeline stopped</h2><div class="mono">${esc(ev.error)}</div>
        <div class="small" style="margin-top:6px">Nothing is guessed: an unknown source format stops the run instead of producing wrong data.</div></div>
        <a class="btn" href="#/">Try another file</a></div>`;
      log(`✗ ${ev.error}`, "fail");
    },
  };

  const queue = [];
  let playing = false;
  async function play() {
    if (playing) return;
    playing = true;
    while (queue.length && !closed) {
      const ev = queue.shift();
      await handlers[ev.type]?.(ev);
      const slow = pace.checked;
      if (ev.type === "step_started") await sleep(slow ? 650 : 60);
      if (ev.type === "step_finished") await sleep(slow ? 220 : 25);
    }
    playing = false;
  }
  const source = new EventSource(`/api/runs/${encodeURIComponent(jobId)}/events`);
  source.onmessage = (message) => {
    const ev = JSON.parse(message.data);
    if (ev.type === "done" || ev.type === "failed") source.close();
    queue.push(ev);
    play();
  };
  source.onerror = () => {
    source.close();
    if (!finishedCount && !queue.length) handlers.failed({ error: "Lost the connection to the run (was the server restarted?)" });
  };
  state.cleanup.push(() => { closed = true; source.close(); clearInterval(clock); });
}

/* ---------- book: overview ---------- */

const ORIGIN_COLORS = {
  author_text: "var(--accent)", transmission_isnad: "var(--gold)", editor_text: "#8b5cf6", editor_footnote: "#94a3b8", ai_generated: "var(--bad)",
};
const ORIGIN_LABELS = {
  author_text: "Author's text", transmission_isnad: "Chain of transmission (isnad)", editor_text: "Editor's text", editor_footnote: "Editor's footnotes", ai_generated: "AI generated",
};

function metaValue(field) {
  const value = field?.value;
  if (value == null) return '<span class="muted">not found</span>';
  if (typeof value === "object") {
    if (value.genre) return esc(value.genre) + (value.sub_type ? ` <span class="muted">· ${esc(value.sub_type)}</span>` : "");
    const name = value.name || value.as_source || JSON.stringify(value);
    const death = value.death_hijri ? ` <span class="muted small">(d. ${value.death_hijri} AH)</span>` : "";
    return ar(name) + death;
  }
  return /[؀-ۿ]/.test(String(value)) ? ar(value) : esc(value);
}

async function viewOverview(pub) {
  const o = state.overview[pub];
  const m = o.metadata, s = o.stats;
  const totalOrigins = Object.values(o.origins).reduce((a, b) => a + b, 0) || 1;
  const valTotal = Object.values(o.validation).reduce((a, b) => a + b, 0) || 1;
  const reviewTotal = Object.values(o.review).reduce((a, b) => a + b, 0);
  const decided = reviewTotal - (o.review.pending_review || 0);
  const ev = o.evaluation;
  const fields = ["title", "author", "editor", "publisher", "edition", "year_hijri", "category", "genre_primary", "language"];
  app.innerHTML = `
    <div class="stack">
      <div class="card pad book-hero">
        <div>
          <span class="chip accent">Results</span>
          ${m.title?.value ? ar(m.title.value, "div").replace('class="ar"', 'class="ar title"') : `<h1>${esc(pub)}</h1>`}
          <div class="row muted small">
            ${m.author?.value ? `<span>${metaValue(m.author)}</span>` : ""}
            ${m.genre_primary?.value ? `<span class="chip">${metaValue(m.genre_primary)}</span>` : ""}
            <span class="mono">${esc(pub)}</span>
          </div>
        </div>
        <div class="row">
          <a class="btn primary" href="#/book/${encodeURIComponent(pub)}/review">Review ${o.review.pending_review || 0} pending</a>
          <a class="btn" href="/api/books/${encodeURIComponent(pub)}/files/enrichment.json">Download enrichment.json</a>
        </div>
      </div>

      <div class="tiles">
        ${[["pages", "Pages"], ["blocks", "Text blocks"], ["sections", "Sections"], ["units", "Biographical entries"], ["entities", "People"], ["relationships", "Relationships"], ["citations", "Citations"], ["annotations", "Footnotes"], ["review_items", "Review items"]]
          .map(([k, name]) => `<div class="card tile"><b>${fmt(s[k])}</b><span>${name}</span></div>`).join("")}
      </div>

      <div class="three">
        <div class="card pad stack">
          <h3>Accuracy</h3>
          ${ev ? `
            <div class="metric"><b>${ev.precision.toFixed(2)}</b><span class="muted">precision</span></div>
            <div class="metric"><b>${ev.recall.toFixed(2)}</b><span class="muted">recall</span></div>
            <p class="muted small">${ev.matched}/${ev.gold?.entries ?? ev.matched} entries match the editor's printed index of narrators.</p>`
            : '<p class="muted small">No gold sample for this book. Accuracy is measured against a hand-checked index when one exists.</p>'}
        </div>
        <div class="card pad stack">
          <h3>Integrity</h3>
          <div class="row"><span class="chip ok">✓ Originals unchanged</span></div>
          <p class="small">${fmt(o.integrity?.anchors_checked)} source anchors re-verified against the original text in this run.</p>
          <p class="muted small mono">run ${esc(o.manifest.run_id)}<br>code ${esc(o.manifest.code_version)}</p>
        </div>
        <div class="card pad stack">
          <h3>Human review</h3>
          <div class="metric"><b>${decided}</b><span class="muted">of ${reviewTotal} decided</span></div>
          <div class="progress"><span style="width:${reviewTotal ? (decided / reviewTotal) * 100 : 0}%"></span></div>
          <p class="muted small">Sensitive items (hadith grading, prophetic attribution…) can only be approved by a scholar reviewer.</p>
        </div>
      </div>

      <div class="two">
        <div class="card pad">
          <h3>Who is speaking? <span class="muted small">(every block is labelled)</span></h3>
          <div class="bar" style="margin-top:12px">${Object.entries(o.origins).map(([k, v]) => `<span title="${esc(ORIGIN_LABELS[k] || k)}: ${v}" style="width:${(v / totalOrigins) * 100}%;background:${ORIGIN_COLORS[k] || "var(--muted)"}"></span>`).join("")}</div>
          <div class="legend">${Object.entries(o.origins).map(([k, v]) => `<span><i style="background:${ORIGIN_COLORS[k] || "var(--muted)"}"></i>${esc(ORIGIN_LABELS[k] || k)} · ${v}</span>`).join("")}</div>
        </div>
        <div class="card pad">
          <h3>Validation <span class="muted small">(evidence + confidence for every record)</span></h3>
          <div class="bar" style="margin-top:12px">${Object.entries(o.validation).map(([k, v]) => `<span title="${esc(label(k))}: ${v}" style="width:${(v / valTotal) * 100}%;background:${k === "auto_approved" ? "var(--ok)" : "var(--gold)"}"></span>`).join("")}</div>
          <div class="legend">${Object.entries(o.validation).map(([k, v]) => `<span><i style="background:${k === "auto_approved" ? "var(--ok)" : "var(--gold)"}"></i>${esc(label(k))} · ${v}</span>`).join("")}</div>
        </div>
      </div>

      <div class="card pad">
        <h3 style="margin-bottom:10px">Bibliographic metadata <span class="muted small">(each value with its origin, confidence and source)</span></h3>
        <table>
          <thead><tr><th>Field</th><th>Value</th><th>Origin</th><th>Confidence</th><th>Sources</th></tr></thead>
          <tbody>${fields.filter((f) => m[f]).map((f) => `
            <tr>
              <td>${esc(label(f))}</td>
              <td>${metaValue(m[f])}${m[f].conflicts?.length ? `<div class="small muted">also seen: ${m[f].conflicts.map((c) => ar(typeof c.value === "object" ? JSON.stringify(c.value) : c.value)).join(", ")}</div>` : ""}</td>
              <td><span class="chip">${esc(label(m[f].origin))}</span></td>
              <td>${conf(m[f].confidence)}</td>
              <td class="small">${(m[f].sources || []).map((src) => {
                const a = src.anchors?.[0];
                return a ? `<button class="chip" data-page="${anchorPage(a)}">book p.${a.page}</button>` : `<span class="chip">${esc(label(src.kind))}</span>`;
              }).join(" ")}</td>
            </tr>`).join("")}</tbody>
        </table>
        ${m.missing_fields?.length ? `<p class="muted small">Not found in the book: ${m.missing_fields.map(esc).join(", ")}</p>` : ""}
      </div>
    </div>`;
  app.querySelectorAll("[data-page]").forEach((b) => (b.onclick = () => openScan(pub, b.dataset.page)));
}

/* ---------- book: human review ---------- */

const REASONS = {
  sensitive: ["Sensitive", "bad"], discrepancy: ["Discrepancy", "warn"], low_confidence: ["Low confidence", "warn"],
  needs_llm: ["Needs model", "info"], structural_issue: ["Structure", ""],
};

function itemTitle(item, names) {
  const v = item.proposed_value || {};
  switch (item.target_kind) {
    case "relationship":
      return `${names[v.subject_entity_id] || "?"} · ${label(v.type)} · ${names[v.object_entity_id] || "?"}`;
    case "unit":
      return `Entry #${v.entry_no ?? "?"} · ${v.payload?.person?.surface || ""}`;
    case "fact":
      return `Fact: ${label(v.predicate)} = ${v.object}`;
    case "citation":
      return `Citation: ${v.title_raw || ""} ${v.locators?.[0]?.raw || ""}`;
    case "annotation":
      return `Cross-reference “${v.anchor?.quote || ""}” (${label(v.kind)})`;
    default:
      return `${label(item.target_kind)} · ${item.target_id}`;
  }
}

function proposedView(item, names) {
  const v = item.proposed_value;
  if (v == null) return '<p class="muted small">No value is proposed: the issue below needs a person to look at the source.</p>';
  if (item.target_kind === "relationship") {
    return `<div class="relation">${ar(names[v.subject_entity_id] || v.subject_entity_id)}<span class="arrow">${esc(label(v.type))}</span>${ar(names[v.object_entity_id] || v.object_entity_id)}</div>
      <dl class="kv" style="margin-top:12px">
        <dt>Assertion</dt><dd>${v.assertion === "inferred" ? '<span class="chip warn">inferred: not written in the text</span>' : '<span class="chip ok">stated in the text</span>'}</dd>
        <dt>Origin</dt><dd>${esc(label(v.origin))}</dd>
        ${v.attrs?.kind ? `<dt>Kind</dt><dd>${esc(v.attrs.kind)}</dd>` : ""}
      </dl>`;
  }
  const rows = Object.entries(v).filter(([k, x]) => x != null && typeof x !== "object" && k !== "review_status" && !k.endsWith("_id"));
  const nested = [];
  if (v.payload?.person?.surface) nested.push(["person", ar(v.payload.person.surface)]);
  if (v.payload?.nasab?.length) nested.push(["nasab", ar(v.payload.nasab.join(" بن "))]);
  if (v.anchor?.quote) nested.push(["quote", ar(v.anchor.quote)]);
  if (v.locators?.length) nested.push(["locator", esc(v.locators.map((l) => l.raw).join(", "))]);
  return `<dl class="kv">
      ${nested.map(([k, x]) => `<dt>${esc(label(k))}</dt><dd>${x}</dd>`).join("")}
      ${rows.map(([k, x]) => `<dt>${esc(label(k))}</dt><dd>${/[؀-ۿ]/.test(String(x)) ? ar(x) : esc(x)}</dd>`).join("")}
    </dl>`;
}

async function viewReview(pub) {
  const data = await api(`/api/books/${encodeURIComponent(pub)}/review`);
  const items = data.items;
  const filters = load("reviewFilters", { reason: "all", status: "pending", kind: "all" });
  let selected = null, editing = false;
  const kinds = [...new Set(items.map((i) => i.target_kind))].sort();

  const visible = () => items.filter((i) =>
    (filters.reason === "all" || i.reason.includes(filters.reason)) &&
    (filters.kind === "all" || i.target_kind === filters.kind) &&
    (filters.status === "all" || (filters.status === "pending" ? i.status === "pending_review" : i.status !== "pending_review")));

  app.innerHTML = `
    <div class="review-top">
      <div class="spread">
        <div>
          <span class="chip accent">Step 3 · Human verification</span>
          <h1 style="margin-top:10px">Review what the engine is unsure about</h1>
          <p class="muted">Each item shows why it is here, what the engine proposes and the exact source passage. Decisions are audited and approved items become training data.</p>
        </div>
        <div class="card pad row" style="padding:12px 14px">
          <label class="small muted">Reviewer <input type="text" id="rv-id" value="${esc(state.reviewer.id)}" style="width:140px"></label>
          <label class="small muted">Role
            <select id="rv-role">
              <option value="editor_reviewer">Editor reviewer</option>
              <option value="scholar_reviewer">Scholar reviewer</option>
            </select>
          </label>
        </div>
      </div>
      <div class="spread">
        <div class="row" id="reason-chips">
          ${[["all", "All"], ...Object.entries(REASONS).map(([k, [n]]) => [k, n])].map(([k, n]) => {
            const count = k === "all" ? items.length : items.filter((i) => i.reason.includes(k)).length;
            return `<button class="chip ${filters.reason === k ? "on" : ""}" data-reason="${k}">${esc(n)} · ${count}</button>`;
          }).join("")}
        </div>
        <div class="row">
          <select id="f-kind"><option value="all">All kinds</option>${kinds.map((k) => `<option value="${k}">${esc(label(k))}</option>`).join("")}</select>
          <select id="f-status"><option value="pending">Pending</option><option value="decided">Decided</option><option value="all">All statuses</option></select>
        </div>
      </div>
      <div class="row small"><div class="progress" style="flex:1"><span id="rv-bar"></span></div><span id="rv-progress" class="muted"></span></div>
    </div>
    <div class="review-layout">
      <div class="card queue" id="queue"></div>
      <div class="card detail" id="detail"></div>
    </div>`;

  const role = document.getElementById("rv-role");
  role.value = state.reviewer.role;
  role.onchange = () => { state.reviewer.role = role.value; save("reviewer", state.reviewer); renderDetail(); };
  document.getElementById("rv-id").onchange = (e) => { state.reviewer.id = e.target.value.trim() || "demo-reviewer"; save("reviewer", state.reviewer); };
  const kindSelect = document.getElementById("f-kind"), statusSelect = document.getElementById("f-status");
  kindSelect.value = filters.kind;
  statusSelect.value = filters.status;
  const refilter = () => { save("reviewFilters", filters); selected = null; renderQueue(); };
  kindSelect.onchange = () => { filters.kind = kindSelect.value; refilter(); };
  statusSelect.onchange = () => { filters.status = statusSelect.value; refilter(); };
  document.querySelectorAll("[data-reason]").forEach((chip) => (chip.onclick = () => {
    filters.reason = chip.dataset.reason;
    document.querySelectorAll("[data-reason]").forEach((c) => c.classList.toggle("on", c === chip));
    refilter();
  }));

  function renderProgress() {
    const done = items.filter((i) => i.status !== "pending_review").length;
    document.getElementById("rv-bar").style.width = `${(done / items.length) * 100}%`;
    document.getElementById("rv-progress").textContent = `${done} of ${items.length} decided`;
    if (state.overview[pub]) {
      state.overview[pub].review = items.reduce((acc, i) => ((acc[i.status] = (acc[i.status] || 0) + 1), acc), {});
      renderNav(pub, "review");
    }
  }

  function renderQueue() {
    const list = visible();
    if (!selected || !list.includes(selected)) selected = list[0] || null;
    const queue = document.getElementById("queue");
    queue.innerHTML = list.length ? list.map((item) => `
      <button class="qitem ${item === selected ? "sel" : ""} ${item.status !== "pending_review" ? "done" : ""}" data-id="${item.review_id}">
        <div class="row" style="gap:6px">
          <span class="chip">${esc(label(item.target_kind))}</span>
          ${item.reason.map((r) => `<span class="chip ${REASONS[r]?.[1] || ""}">${esc(REASONS[r]?.[0] || r)}</span>`).join("")}
          ${item.status !== "pending_review" ? statusChip(item.status) : ""}
        </div>
        <div class="qtitle">${bidi(itemTitle(item, data.names))}</div>
        <div class="row small muted" style="gap:10px">${conf(item.confidence)} ${item.anchors[0] ? `<span>p.${item.anchors[0].page}</span>` : ""}</div>
      </button>`).join("") : '<div class="empty">Nothing here. 🎉<br><span class="small">Change the filters to see other items.</span></div>';
    queue.querySelectorAll(".qitem").forEach((el) => (el.onclick = () => {
      selected = items.find((i) => i.review_id === el.dataset.id);
      editing = false;
      renderQueue();
    }));
    queue.querySelector(".sel")?.scrollIntoView({ block: "nearest" });
    renderDetail();
    renderProgress();
  }

  function renderDetail() {
    const detail = document.getElementById("detail");
    const item = selected;
    if (!item) { detail.innerHTML = '<div class="empty">Select an item.</div>'; return; }
    const locked = item.sensitive.length && state.reviewer.role !== "scholar_reviewer";
    const page = item.pdf?.scan_page ?? item.pdf?.page ?? anchorPage(item.anchors[0]);
    detail.innerHTML = `
      <div class="pad stack">
        <div class="spread">
          <div class="row" style="gap:6px">${item.reason.map((r) => `<span class="chip ${REASONS[r]?.[1] || ""}">${esc(REASONS[r]?.[0] || r)}</span>`).join("")}
            <span class="chip">${esc(label(item.target_kind))}</span> ${statusChip(item.status)}</div>
          <span class="mono muted small">${esc(item.review_id)}</span>
        </div>
        <h2>${bidi(itemTitle(item, data.names))}</h2>
        ${item.sensitive.length ? `<div class="lock">🔒 Sensitive: ${item.sensitive.map(label).map(esc).join(", ")}. Only a <b>scholar reviewer</b> can decide this item.${locked ? " Switch the role above to continue." : ""}</div>` : ""}
        <div>
          <h3 style="margin-bottom:6px">Why it is here</h3>
          ${item.issues.length ? item.issues.map((id) => data.issues[id]).filter(Boolean).map((iss) => `<div class="small">• <span class="mono">${esc(iss.code)}</span>: ${esc(iss.message)}</div>`).join("") : `<div class="small">• ${item.reason.map((r) => esc(REASONS[r]?.[0] || r)).join(", ")}${item.confidence != null ? ` (confidence ${item.confidence.toFixed(2)})` : ""}</div>`}
        </div>
        <div>
          <h3 style="margin-bottom:8px">What the engine proposes</h3>
          ${proposedView(item, data.names)}
          ${item.proposed_value != null ? `<details style="margin-top:8px"><summary>Raw JSON</summary><pre class="json">${esc(JSON.stringify(item.proposed_value, null, 2))}</pre></details>` : ""}
        </div>
        <div>
          <div class="spread" style="margin-bottom:8px"><h3>Source evidence</h3>
            ${page && state.overview[pub]?.has_pdf ? `<button class="btn" id="open-scan">Open scan page ${page}</button>` : ""}</div>
          ${item.context.length ? item.context.map((c) => `
            <div class="evidence" style="margin-bottom:8px">
              <div class="mono muted small">${esc(c.block_id)} · book page ${c.page}</div>
              <div class="ar" dir="rtl" lang="ar">${highlight(c.text, c.marks)}</div>
            </div>`).join("") : '<p class="muted small">No source passage attached.</p>'}
        </div>
        ${editing ? `
          <div class="stack">
            <h3>Corrected value</h3>
            <textarea id="edit-value" rows="10">${esc(JSON.stringify(item.proposed_value, null, 2))}</textarea>
          </div>` : ""}
        <label class="small muted" style="display:block">Note for the audit trail (optional)
          <input type="text" id="reason" style="width:100%;margin-top:4px" placeholder="e.g. checked against the scan">
        </label>
      </div>
      <div class="actions">
        ${editing
          ? `<button class="btn ok" data-act="edited" ${locked ? "disabled" : ""}>Save correction</button><button class="btn" data-act="cancel">Cancel</button>`
          : `<button class="btn ok" data-act="approved" ${locked ? "disabled" : ""}>✓ Approve <kbd>A</kbd></button>
             <button class="btn bad" data-act="rejected" ${locked ? "disabled" : ""}>✕ Reject <kbd>R</kbd></button>
             <button class="btn" data-act="edit" ${locked || item.proposed_value == null ? "disabled" : ""}>✎ Edit <kbd>E</kbd></button>
             <button class="btn" data-act="reprocess_requested" ${locked ? "disabled" : ""}>↻ Reprocess</button>
             <span class="muted small" style="margin-inline-start:auto;align-self:center"><kbd>J</kbd>/<kbd>K</kbd> next / previous</span>`}
      </div>`;
    document.getElementById("open-scan")?.addEventListener("click", () => openScan(pub, page));
    detail.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => act(b.dataset.act)));
  }

  async function act(action) {
    const item = selected;
    if (!item) return;
    if (action === "edit") { editing = true; renderDetail(); document.getElementById("edit-value")?.focus(); return; }
    if (action === "cancel") { editing = false; renderDetail(); return; }
    let newValue = null;
    if (action === "edited") {
      try { newValue = JSON.parse(document.getElementById("edit-value").value); } catch (error) { toast("The corrected value is not valid JSON: " + error.message, true); return; }
    }
    try {
      const result = await api(`/api/books/${encodeURIComponent(pub)}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          review_id: item.review_id, decision: action, new_value: newValue,
          reason: document.getElementById("reason")?.value || null,
          reviewer_id: state.reviewer.id, reviewer_role: state.reviewer.role,
        }),
      });
      item.status = { approved: "approved", rejected: "rejected", edited: "edited", reprocess_requested: "reprocess_requested" }[action];
      toast(`${label(action)[0].toUpperCase() + label(action).slice(1)} · audit recorded${result.training_examples ? " · 1 training example exported" : ""}`);
      editing = false;
      const list = visible();
      const next = list.find((i) => i.status === "pending_review" && i !== item) || null;
      selected = filters.status === "pending" ? next : item;
      renderQueue();
    } catch (error) {
      toast(error.message, true);
    }
  }

  function move(step) {
    const list = visible();
    const index = list.indexOf(selected);
    const next = list[Math.min(list.length - 1, Math.max(0, index + step))];
    if (next) { selected = next; editing = false; renderQueue(); }
  }
  const onKey = (event) => {
    if (event.target.closest("input, textarea, select") || event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === "j") move(1);
    else if (key === "k") move(-1);
    else if (key === "a") act("approved");
    else if (key === "r") act("rejected");
    else if (key === "e") act("edit");
    else return;
    event.preventDefault();
  };
  document.addEventListener("keydown", onKey);
  state.cleanup.push(() => document.removeEventListener("keydown", onKey));
  renderQueue();
}

/* ---------- book: knowledge units ---------- */

async function records(pub, kind) {
  return api(`/api/books/${encodeURIComponent(pub)}/records/${kind}`);
}

async function viewUnits(pub) {
  const [units, entities] = await Promise.all([records(pub, "knowledge_units"), records(pub, "entities")]);
  const names = Object.fromEntries(entities.map((e) => [e.entity_id, e.canonical_name]));
  units.sort((a, b) => (a.entry_no ?? 1e9) - (b.entry_no ?? 1e9));
  let open = null;
  app.innerHTML = `
    <div class="stack">
      <div class="spread">
        <div><h1>Knowledge units</h1><p class="muted">${units.length} biographical entries, each anchored to its exact place in the book.</p></div>
        <input type="search" id="u-filter" placeholder="Filter by name or number…" style="width:280px">
      </div>
      <div class="card"><table>
        <thead><tr><th>#</th><th>Person</th><th>Type</th><th>Page</th><th>Facts</th><th>Confidence</th><th>Status</th></tr></thead>
        <tbody id="u-rows"></tbody>
      </table></div>
    </div>`;
  const rows = document.getElementById("u-rows");
  const subject = (u) => names[u.subject_entity_id] || u.payload?.person?.surface || "";
  function render() {
    const q = document.getElementById("u-filter").value.trim();
    rows.innerHTML = units.filter((u) => !q || String(u.entry_no) === q || subject(u).includes(q)).map((u) => {
      const a = u.anchors[0];
      const row = `<tr class="clickable" data-id="${u.unit_id}">
        <td>${u.entry_no ?? "—"}</td><td>${ar(subject(u))}</td><td><span class="chip">${esc(label(u.sub_type || u.unit_type))}</span></td>
        <td>${a ? a.page : "—"}</td><td>${u.facts.length}</td><td>${conf(u.confidence)}</td><td>${statusChip(u.review_status)}</td></tr>`;
      if (open !== u.unit_id) return row;
      const p = u.payload || {};
      return row + `<tr><td colspan="7" style="background:var(--surface-2)">
        <div class="stack" style="padding:6px 4px">
          ${u.anchors.slice(0, 2).map((x) => `<div class="evidence" style="background:var(--surface)"><div class="mono muted small">${esc(x.block_id)} · page ${x.page}</div>${ar(x.quote, "div")}</div>`).join("")}
          <dl class="kv">
            ${p.person?.ism ? `<dt>Ism</dt><dd>${ar(p.person.ism)}</dd>` : ""}
            ${p.kunya ? `<dt>Kunya</dt><dd>${ar(p.kunya)}</dd>` : ""}
            ${p.nasab?.length ? `<dt>Nasab</dt><dd>${ar(p.nasab.join(" بن "))}</dd>` : ""}
            ${p.section_subject ? `<dt>Family of</dt><dd>${ar(p.section_subject)}</dd>` : ""}
            ${p.person?.gender ? `<dt>Gender</dt><dd>${p.person.gender === "f" ? "female" : "male"}</dd>` : ""}
            ${u.facts.length ? `<dt>Facts</dt><dd>${u.facts.map((f) => `<span class="chip">${esc(label(f.predicate))}${f.object !== true ? ": " + esc(f.object) : ""}</span>`).join(" ")}</dd>` : ""}
            <dt>Origin</dt><dd>${esc(label(u.origin))} · extracted by ${esc(u.provenance?.method)}</dd>
          </dl>
          ${state.overview[pub]?.has_pdf && a ? `<div><button class="btn" data-page="${anchorPage(a)}">Open scan page ${anchorPage(a)}</button></div>` : ""}
        </div></td></tr>`;
    }).join("");
    rows.querySelectorAll("tr.clickable").forEach((tr) => (tr.onclick = () => { open = open === tr.dataset.id ? null : tr.dataset.id; render(); }));
    rows.querySelectorAll("[data-page]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); openScan(pub, b.dataset.page); }));
  }
  document.getElementById("u-filter").oninput = render;
  render();
}

/* ---------- book: people and relationships ---------- */

/* How each relationship reads from the subject's side and from the object's side. */
const RELATION = {
  sibling_of: ["sibling of", "sibling of"],
  child_of: ["child of", "parent of"],
  mother_is: ["mother is", "mother of"],
};

async function viewPeople(pub) {
  const [entities, relationships] = await Promise.all([records(pub, "entities"), records(pub, "relationships")]);
  const byId = Object.fromEntries(entities.map((e) => [e.entity_id, e]));
  const related = {};
  for (const r of relationships) {
    (related[r.subject_entity_id] ||= []).push(r);
    (related[r.object_entity_id] ||= []).push(r);
  }
  const people = entities.slice().sort((a, b) => (related[b.entity_id]?.length || 0) - (related[a.entity_id]?.length || 0));
  let selected = people[0];
  app.innerHTML = `
    <div class="stack">
      <div class="spread">
        <div><h1>People & relationships</h1><p class="muted">${entities.length} people and ${relationships.length} family relationships. Inferred relationships are always sent to review.</p></div>
        <input type="search" id="p-filter" placeholder="Filter people…" style="width:260px">
      </div>
      <div class="split">
        <div class="card list" id="p-list"></div>
        <div class="card pad" id="p-detail"></div>
      </div>
    </div>`;
  function renderList() {
    const q = document.getElementById("p-filter").value.trim();
    const list = document.getElementById("p-list");
    list.innerHTML = people.filter((p) => !q || p.canonical_name.includes(q) || p.aliases.some((a) => a.includes(q))).map((p) => `
      <button data-id="${p.entity_id}" class="${p === selected ? "sel" : ""}">${ar(p.canonical_name)}<span class="chip">${related[p.entity_id]?.length || 0}</span></button>`).join("");
    list.querySelectorAll("button").forEach((b) => (b.onclick = () => { selected = byId[b.dataset.id]; renderList(); renderDetail(); }));
  }
  function renderDetail() {
    const p = selected, rels = related[p.entity_id] || [];
    document.getElementById("p-detail").innerHTML = `
      <div class="stack">
        <div>${ar(p.canonical_name, "h2")}</div>
        <div class="row">
          <span class="chip">${p.gender === "f" ? "female" : p.gender === "m" ? "male" : "gender unknown"}</span>
          ${p.roles.map((r) => `<span class="chip">${esc(label(r))}</span>`).join("")}
          ${statusChip(p.review_status)} ${conf(p.confidence)}
        </div>
        ${p.aliases.length ? `<div class="small"><span class="muted">Also written as: </span>${p.aliases.map((a) => ar(a)).join(" · ")}</div>` : ""}
        <h3>Relationships</h3>
        ${rels.length ? `<table><tbody>${rels.map((r) => {
          const other = r.subject_entity_id === p.entity_id ? r.object_entity_id : r.subject_entity_id;
          const direction = r.subject_entity_id === p.entity_id ? RELATION[r.type]?.[0] || label(r.type) : RELATION[r.type]?.[1] || `inverse of ${label(r.type)}`;
          const ev = r.evidence?.[0];
          return `<tr>
            <td style="width:30%"><a href="#" data-goto="${other}">${ar(byId[other]?.canonical_name || other)}</a></td>
            <td><span class="chip accent">${esc(direction)}</span> ${r.assertion === "inferred" ? '<span class="chip warn">inferred</span>' : '<span class="chip ok">stated</span>'}
              ${ev ? `<div class="small" style="margin-top:6px">${ar(ev.quote)} <span class="muted">· p.${ev.page}</span></div>` : ""}</td>
            <td>${statusChip(r.review_status)}</td></tr>`;
        }).join("")}</tbody></table>` : '<p class="muted small">No relationships recorded.</p>'}
      </div>`;
    document.querySelectorAll("[data-goto]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); selected = byId[a.dataset.goto]; renderList(); renderDetail(); }));
  }
  document.getElementById("p-filter").oninput = renderList;
  renderList();
  renderDetail();
}

/* ---------- book: graph, search, downloads ---------- */

async function viewGraph(pub) {
  app.innerHTML = `
    <div class="stack">
      <div class="spread"><div><h1>Knowledge graph</h1><p class="muted">People, family relationships and cited works. Drag to explore; the same graph exports to Neo4j (graph.cypher).</p></div>
      <a class="btn" target="_blank" rel="noopener" href="/api/books/${encodeURIComponent(pub)}/files/graph.html">Open full screen ↗</a></div>
      <iframe class="graph-frame card" src="/api/books/${encodeURIComponent(pub)}/files/graph.html" title="Knowledge graph"></iframe>
    </div>`;
}

async function viewSearch(pub) {
  app.innerHTML = `
    <div class="stack">
      <div><h1>Search</h1><p class="muted">Arabic-aware search: diacritics, letter variants and honorifics are normalized, so «الدارقطني» also finds «الدَّارَقُطْنِيّ».</p></div>
      <form class="row" id="s-form">
        <input type="search" id="s-q" class="ar" dir="rtl" placeholder="ابحث…" style="flex:1;min-width:220px;font-size:1.1rem">
        <button class="btn primary" type="submit">Search</button>
      </form>
      <div class="row small" id="s-examples"><span class="muted">Try:</span>
        ${["الدارقطني", "عائشة", "أبي بكر", "الإصابة"].map((q) => `<button class="chip" data-q="${q}">${ar(q)}</button>`).join("")}</div>
      <div id="s-results"></div>
    </div>`;
  const input = document.getElementById("s-q");
  async function run(q) {
    if (!q) return;
    const results = document.getElementById("s-results");
    results.innerHTML = '<div class="empty">Searching…</div>';
    const hits = await api(`/api/books/${encodeURIComponent(pub)}/search?q=${encodeURIComponent(q)}&limit=25`);
    results.innerHTML = hits.length ? `<div class="card">${hits.map((h) => `
      <div class="hit">
        <div class="row small" style="gap:8px"><span class="chip accent">${esc(h.kind)}</span>
          ${h.anchor?.page ? `<span class="muted">page ${h.anchor.page} · ${esc(h.anchor.block_id)}</span>` : ""}
          <span class="muted mono" style="margin-inline-start:auto">score ${h.score}</span>
          ${state.overview[pub]?.has_pdf && h.anchor?.page ? `<button class="chip" data-page="${anchorPage(h.anchor)}">scan ↗</button>` : ""}</div>
        ${ar(h.text || "", "div")}
      </div>`).join("")}</div>` : '<div class="card empty">No results.</div>';
    results.querySelectorAll("[data-page]").forEach((b) => (b.onclick = () => openScan(pub, b.dataset.page)));
  }
  document.getElementById("s-form").onsubmit = (e) => { e.preventDefault(); run(input.value.trim()); };
  document.querySelectorAll("[data-q]").forEach((b) => (b.onclick = () => { input.value = b.dataset.q; run(b.dataset.q); }));
  input.focus();
}

const FILE_INFO = {
  "enrichment.json": "Everything in one validated document (the main deliverable)",
  "metadata.json": "Bibliographic record with provenance per field",
  "document_report.json": "Counts, gaps and quality checks",
  "structure.json": "Sections, TOC alignment and page index",
  "origin_map.json": "Who is speaking in every block",
  "annotations.json": "Footnotes linked to their markers",
  "citations.json": "Cited works and internal cross-references",
  "related_works.json": "The book's family of related works",
  "knowledge_units.json": "Biographical entries with facts",
  "entities.json": "People, with aliases and roles",
  "relationships.json": "Family relationships with evidence",
  "validation_report.json": "Evidence and confidence for every record",
  "review_queue.json": "Items for human review and their status",
  "review_decisions.json": "Decisions made by reviewers",
  "review_audit.jsonl": "Audit trail of every decision",
  "training_examples.jsonl": "Approved items exported as training data",
  "run_manifest.json": "Run ID, versions and every input/output hash",
  "eval_report.json": "Precision and recall against the printed index",
  "graph.html": "Interactive knowledge graph",
  "graph.cypher": "Neo4j import script",
  "enrichment.db": "SQLite copy of the enrichment",
};

async function viewDownloads(pub) {
  delete state.overview[pub];
  const o = (state.overview[pub] = await api(`/api/books/${encodeURIComponent(pub)}/overview`));
  app.innerHTML = `
    <div class="stack">
      <div><h1>Downloads</h1><p class="muted">The enrichment layer, stored separately from the untouched original. Every file is listed with its hash in run_manifest.json.</p></div>
      <div class="files">${o.files.map((f) => `
        <a class="card file" href="/api/books/${encodeURIComponent(pub)}/files/${f.name}" ${f.name === "graph.html" ? 'target="_blank" rel="noopener"' : ""}>
          <span class="ext">${esc(f.name.split(".").pop())}</span>
          <span><b style="color:var(--ink)">${esc(f.name)}</b><br><span class="muted small">${esc(FILE_INFO[f.name] || "")}</span><br><span class="muted small">${(f.bytes / 1024).toFixed(1)} KB</span></span>
        </a>`).join("")}</div>
    </div>`;
}

const VIEWS = {
  overview: viewOverview,
  review: viewReview,
  units: viewUnits,
  people: viewPeople,
  graph: viewGraph,
  search: viewSearch,
  downloads: viewDownloads,
};

route();
