/* Agentic Studio front end: one asynchronous three-page loop for every app of studio.yaml (GET /api/apps).
   Page 1: pick an app, fill its fields, stage files in its lanes, tick its data pulls; the case table tracks every
           case and marks a report version you have not opened yet (NEW).
   Page 2: verify the insight agents' results, flag facts or leave notes (that agent runs again), add files, ask
           for the report at any time.
   Page 3: the report (report framework + the app's view) with the agent's suggested next steps, and a slide-out
           prompt panel: one prompt → one new version, asynchronously (back to the case table until it is in).
   Agent results render through the app's views with a fixed set of blocks (renderBlocks); agents never write
   HTML. Every view is rebuilt from the API (src/kentc_studio/api/); nothing is simulated. */
(() => {
  'use strict';

  // ---------------------------------------------------------------- helpers
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const arr = v => (Array.isArray(v) ? v : []);
  const obj = v => (v && typeof v === 'object' && !Array.isArray(v) ? v : {});
  const txt = v => (Array.isArray(v) ? v.map(txt).filter(Boolean).join('; ') : v && typeof v === 'object' ? Object.values(v).map(txt).filter(Boolean).join(' · ') : String(v ?? ''));
  const num = v => (typeof v === 'number' ? v : parseFloat(String(v ?? '').replace(/[^0-9.\-]/g, '')));
  const get = (data, path) => String(path).split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), data);
  const humanize = k => { const s = String(k).split('.').pop().replace(/_/g, ' ').trim(); return s.charAt(0).toUpperCase() + s.slice(1); };
  const clock = s => { s = Math.max(0, Math.round(s || 0)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}:${String(x).padStart(2, '0')}`; };
  const when = t => (t ? new Date(t * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '');
  const hhmmss = t => new Date(t * 1000).toLocaleTimeString([], { hour12: false });
  const enc = encodeURIComponent;
  const isVideo = n => /\.(mp4|mov|m4v|mkv|webm|avi|mpg|mpeg|wmv|flv|3gp)$/i.test(n);
  const isLegacy = n => /\.(doc|xls|ppt)$/i.test(n);
  const BUSY = s => ['queued', 'running'].includes(s);

  let token = sessionStorage.getItem('kentc-studio-token') || '';
  async function api(path, opts = {}, retried = false) {
    const headers = new Headers(opts.headers || {});
    if (token) headers.set('x-api-token', token);
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401 && !retried) {
      const entered = prompt('Studio API token');
      if (entered) {
        token = entered;
        sessionStorage.setItem('kentc-studio-token', token);
        return api(path, opts, true);
      }
    }
    let body = null;
    try { body = await res.json(); } catch { /* no JSON */ }
    if (!res.ok) throw new Error((body && (body.detail || body.error)) || `${res.status} ${res.statusText}`);
    return body;
  }
  const post = (path, data) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });

  let toastTimer;
  function toast(msg, err = false) {
    const t = $('#toast');
    t.textContent = msg;
    t.className = `toast show${err ? ' err' : ''}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.className = 'toast'), err ? 6000 : 3200);
  }

  // ---------------------------------------------------------------- state
  const S = { apps: {}, appOrder: [], intakeApp: null, cases: [], health: null, current: null, detail: null, page: 1,
    version: null, factFilter: 'all', openForms: new Set(), work: { id: null, after: 0, timer: null, tick: 0 }, extrasPicked: null };
  const appOf = d => S.apps[d && d.app] || null;

  // versions the analyst has opened, per case: the case table marks newer ones NEW
  const SEEN_KEY = 'kentc-studio-seen';
  const seen = JSON.parse(localStorage.getItem(SEEN_KEY) || '{}');
  const seenKey = c => `${c.id}@${c.created}`;                  // a recreated case with the same id starts unseen
  const markSeen = (c, v) => { if ((seen[seenKey(c)] || 0) < v) { seen[seenKey(c)] = v; localStorage.setItem(SEEN_KEY, JSON.stringify(seen)); } };

  // ---------------------------------------------------------------- blocks: the one renderer of agent results
  const BLOCK_KINDS = ['text', 'kv', 'table', 'list', 'chips', 'cards', 'facts'];
  const scoreColor = s => (s >= 85 ? 'var(--red)' : s >= 70 ? 'var(--amber)' : '#9aa0a6');
  const docLink = (d, name) => `<a href="/api/cases/${enc(d.id)}/docs/${enc(name)}" target="_blank" rel="noopener">${esc(name)}</a>`;
  const linkify = (d, s) => {
    s = String(s ?? '');
    const hit = d ? arr(d.docs).find(x => s.includes(x.name)) : null;
    return hit ? esc(s).replace(esc(hit.name), docLink(d, hit.name)) : esc(s);
  };
  function tableColumns(block, rows) {
    const cols = block.columns;
    if (cols && !Array.isArray(cols) && typeof cols === 'object') return Object.entries(cols);
    const keys = Array.isArray(cols) && cols.length ? cols : Object.keys(obj(rows.find(r => r && typeof r === 'object')));
    return keys.map(k => [k, humanize(k)]);
  }
  /* view: [{<kind>: path, title?, options}]; ctx: {d (case detail, for file links), h ('h2'|'h3'), facts ('skip'|'dl')} */
  function renderBlocks(view, data, ctx = {}) {
    const h = ctx.h || 'h3', d = ctx.d;
    return arr(view).map(block => {
      const kind = BLOCK_KINDS.find(k => k in block);
      if (!kind) return '';
      const path = block[kind];
      if (kind === 'facts' && ctx.facts === 'skip') return '';
      const title = block.title ? `<${h} class="blk-title">${esc(block.title)}</${h}>` : '';
      const labels = obj(block.labels);
      if (kind === 'kv') {
        const pairs = Array.isArray(path) ? path.map(p => [labels[p] || humanize(p), get(data, p)])
          : Object.entries(obj(get(data, path))).map(([k, v]) => [labels[k] || humanize(k), v]);
        const shown = pairs.filter(([, v]) => txt(v) !== '');
        return shown.length ? `${title}<div class="kv">${shown.map(([k, v]) => `<div><span>${esc(k)}</span><b>${linkify(d, txt(v))}</b></div>`).join('')}</div>` : '';
      }
      const value = get(data, path);
      if (kind === 'text') {
        const paras = (Array.isArray(value) ? value : [value]).map(txt).filter(Boolean);
        return paras.length ? `${title}${paras.map(p => `<p class="blk-text">${linkify(d, p)}</p>`).join('')}` : '';
      }
      const rows = arr(value);
      if (!rows.length) return title ? `${title}<p class="muted blk-empty">—</p>` : '';
      if (kind === 'list') return `${title}<ul class="bullets">${rows.map(x => `<li>${linkify(d, txt(x))}</li>`).join('')}</ul>`;
      if (kind === 'chips') return `${title}<div class="party-list">${rows.map(x => {
        const vals = x && typeof x === 'object' ? Object.values(x).map(txt).filter(Boolean) : [txt(x)];
        return `<span class="party"><b>${esc(vals[0] || '')}</b>${esc(vals.slice(1).join(' · '))}</span>`;
      }).join('')}</div>`;
      if (kind === 'table') {
        const cols = tableColumns(block, rows);
        return `${title}<div class="table-wrap"><table class="grid"><thead><tr>${cols.map(([, l]) => `<th>${esc(l)}</th>`).join('')}</tr></thead>
          <tbody>${rows.map(r => `<tr>${cols.map(([k]) => `<td>${linkify(d, txt(obj(r)[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      }
      if (kind === 'facts') {
        const shown = rows.filter(r => r && typeof r === 'object').slice(0, 8);
        return `${title}<dl class="facts-dl">${shown.map(r => `<dt>${esc(r.field)}</dt><dd>${esc(txt(r.value))}</dd>`).join('')}</dl>${rows.length > shown.length ? `<p class="caption">+${rows.length - shown.length} more in Facts to verify</p>` : ''}`;
      }
      // cards
      const items = rows.filter(r => r && typeof r === 'object');
      if (block.score) items.sort((a, b) => (num(b[block.score]) || 0) - (num(a[block.score]) || 0));
      return `${title}<div class="risk-list">${items.map(r => {
        const s = block.score ? Math.max(0, Math.min(100, num(r[block.score]) || 0)) : null;
        return `<article class="risk ${s === null ? 'noscore' : ''}">${s === null ? '' : `<div class="score" style="--v:${s};--c:${scoreColor(s)}"><b>${s}</b></div>`}<div>
          ${block.kicker ? `<div class="kicker">${esc(txt(r[block.kicker]))}</div>` : ''}${block.head ? `<h4>${esc(txt(r[block.head]))}</h4>` : ''}
          ${block.body ? `<p>${linkify(d, txt(r[block.body]))}</p>` : ''}
          ${arr(block.notes).filter(n => txt(r[n])).map(n => `<div class="evidence"><b>${esc(humanize(n).toUpperCase())}</b>${linkify(d, txt(r[n]))}</div>`).join('')}</div></article>`;
      }).join('')}</div>`;
    }).join('');
  }
  // flaggable rows of an agent result: its view's `facts` blocks
  const factsOf = (view, result) => arr(view).filter(b => 'facts' in b).flatMap(b => arr(get(result, b.facts)).filter(r => r && typeof r === 'object'));

  // ---------------------------------------------------------------- staging lanes (reusable)
  class Stager {
    constructor(el, { compact = false, onChange = () => {} } = {}) {
      Object.assign(this, { el, compact, onChange, lanes: [], files: [], sample: false });
    }
    setLanes(lanes, { optional = false } = {}) {
      Object.assign(this, { lanes, optional, files: [], sample: false });
      this.el.innerHTML = lanes.map(l => `
        <div class="lane" data-lane="${esc(l.name)}">
          <div class="lane-head"><b>${esc((l.label || l.name).toUpperCase())}</b><span class="chip ${l.required && !optional ? 'ready' : ''}">${l.required && !optional ? 'REQUIRED' : 'OPTIONAL'}</span>
            <small class="muted">${esc(l.agent_label ? `${l.agent_label}${l.per === 'lane' ? ' · whole lane' : ' · per file'}` : 'read by the report agent')}</small></div>
          <div class="dropzone ${this.compact ? 'small' : ''}"><span>${esc(l.hint || '')}</span>
            <button type="button" class="btn secondary small">Choose files</button><input type="file" multiple hidden></div>
          <div class="docs"></div>
        </div>`).join('');
      $$('.lane', this.el).forEach(laneEl => {
        const lane = laneEl.dataset.lane, dz = $('.dropzone', laneEl), input = $('input', laneEl);
        $('button', dz).onclick = () => input.click();
        input.onchange = () => { this.add(input.files, lane); input.value = ''; };
        ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.add('drag'); }));
        ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.remove('drag'); }));
        dz.addEventListener('drop', e => this.add(e.dataTransfer.files, lane));
      });
      this.render();
    }
    add(list, lane) {
      for (const f of list) {
        if (isVideo(f.name)) { toast(`${f.name}: video input is not supported`, true); continue; }
        if (isLegacy(f.name)) { toast(`${f.name}: save it as .docx / .xlsx / .pptx first`, true); continue; }
        this.files = this.files.filter(x => x.file.name !== f.name);
        this.files.push({ file: f, lane });
      }
      this.render();
    }
    clear() { this.files = []; this.sample = false; this.render(); }
    count(lane) { return this.files.filter(f => f.lane === lane).length; }
    missing() { return this.sample ? [] : this.lanes.filter(l => l.required && !this.optional && !this.count(l.name)); }
    render() {
      for (const l of this.lanes) {
        const box = $(`.lane[data-lane="${CSS.escape(l.name)}"] .docs`, this.el);
        const chips = this.files.map((f, i) => ({ f, i })).filter(x => x.f.lane === l.name).map(({ f, i }) =>
          `<span class="doc-chip"><em>${esc((f.file.name.split('.').pop() || '').toUpperCase())}</em>${esc(f.file.name)}
            ${this.lanes.length > 1 ? `<button type="button" data-move="${i}" title="Move to the next lane">⇄</button>` : ''}<button type="button" data-rm="${i}" title="Remove">×</button></span>`);
        if (this.sample) chips.unshift('<span class="doc-chip sample"><em>SAMPLE</em>sample bundle files for this lane</span>');
        box.innerHTML = chips.join('');
      }
      $$('[data-rm]', this.el).forEach(b => (b.onclick = () => { this.files.splice(+b.dataset.rm, 1); this.render(); }));
      $$('[data-move]', this.el).forEach(b => (b.onclick = () => {
        const f = this.files[+b.dataset.move], i = this.lanes.findIndex(l => l.name === f.lane);
        f.lane = this.lanes[(i + 1) % this.lanes.length].name;
        this.render();
      }));
      this.onChange(this);
    }
    formData(fd = new FormData()) {
      this.files.forEach(f => { fd.append('files', f.file, f.file.name); fd.append('lanes', f.lane); });
      return fd;
    }
  }

  // ---------------------------------------------------------------- pages
  function show(page) {
    S.page = page;
    $$('.page').forEach(p => p.classList.toggle('active', p.id === `page${page}`));
    $$('.journey-step').forEach(j => { const n = +j.dataset.page; j.classList.toggle('active', n === page); j.classList.toggle('done', n < page); });
    $('#backBtn').hidden = page === 1;
    if (page === 1) { S.current = null; S.detail = null; S.openForms.clear(); history.replaceState(null, '', '#'); renderQueue(); }
    else history.replaceState(null, '', `#case/${enc(S.current)}/${page}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  $('#backBtn').onclick = () => show(1);
  $$('.journey-step').forEach(j => (j.onclick = () => goto(+j.dataset.page)));
  document.addEventListener('click', e => {
    const g = e.target.closest('[data-goto]');
    if (g) goto(+g.dataset.goto);
    if (e.target.closest('[data-open-work]') && S.current) openWork(S.current);
  });
  function goto(n) {
    if (n === 1) return show(1);
    if (!S.detail) return toast('Open a case from the case table first.');
    n === 2 ? renderPage2(S.detail) : renderPage3(S.detail);
  }
  const strip = (el, items) => (el.innerHTML = items.map(([k, v]) => `<div><span>${esc(k)}</span><b title="${esc(v)}">${esc(v)}</b></div>`).join(''));
  const columnFields = (app, fields) => arr(app && app.fields).filter(f => f.column && obj(fields)[f.name]).map(f => [f.label || humanize(f.name), fields[f.name]]);
  function caseStrip(el, d, last) {
    const app = appOf(d), cols = columnFields(app, d.fields);
    strip(el, [['Case', d.id], ['App', d.app_title], cols[0] || ['Documents', String(arr(d.docs).length)], cols[1] || ['Status', d.label], last]);
  }

  // ---------------------------------------------------------------- health
  async function refreshHealth() {
    try {
      const h = await api('/api/health');
      S.health = h;
      const m = $('#modelPill');
      m.className = `pill ${h.model.online ? 'ok' : 'bad'}`;
      m.lastElementChild.textContent = h.model.online ? `${h.model.id} · ${Math.round(h.model.context / 1000)}k` : 'model offline';
      m.title = h.model.online ? `LLM server online · workspace ${h.workspace}` : h.model.error;
      const q = $('#queuePill');
      q.className = `pill ${h.running.length ? 'busy' : 'ok'}`;
      q.lastElementChild.textContent = h.running.length ? `${h.running[0].case} · ${h.running[0].label}${h.queued ? ` · +${h.queued}` : ''}` : h.queued ? `${h.queued} jobs queued` : 'agents idle';
    } catch {
      $('#modelPill').className = 'pill bad';
      $('#modelPill').lastElementChild.textContent = 'server offline';
    }
  }

  // ---------------------------------------------------------------- page 1: intake
  const pullPick = { picked: new Set(), touched: false };
  const intake = new Stager($('#intakeLanes'), { onChange: updateStageCount });
  function fieldValues() {
    const out = {};
    $$('[data-field]', $('#fieldGrid')).forEach(x => (out[x.dataset.field] = x.value));
    return out;
  }
  function updateStageCount(st) {
    const app = S.apps[S.intakeApp];
    if (!app) return;
    const parts = app.lanes.map(l => `${st.count(l.name)}${st.sample ? '+' : ''} ${(l.label || l.name).toLowerCase()}`);
    const q = pullPick.picked.size, miss = st.missing();
    $('#stageCount').innerHTML = `${esc(parts.join(' · '))}${app.pulls.length ? ` · ${q} data pull${q === 1 ? '' : 's'}` : ''}${miss.length ? ` — <b style="color:var(--red)">add a file to ${esc(miss.map(l => l.label || l.name).join(', '))}</b>` : ''}`;
  }
  function renderIntakePulls() {
    const app = S.apps[S.intakeApp], box = $('#intakePulls'), list = arr(app && app.pulls);
    if (!list.length) { box.innerHTML = ''; return updateStageCount(intake); }
    const words = Object.values(fieldValues()).join(' ').toLowerCase();
    if (!pullPick.touched) pullPick.picked = new Set(list.filter(p => p.default || arr(p.triggers).some(t => words.includes(String(t).toLowerCase()))).map(p => p.name));
    box.innerHTML = `<div class="lane"><div class="lane-head"><b>DATA PULLS</b><span class="chip pending">NO MODEL · RUN IN PARALLEL</span></div>
      <p class="caption" style="margin:0 0 8px">SQL on ${esc([...new Set(list.map(p => p.database))].join(', '))} with the fields on the left. Results appear on Page 2; the report waits for them.</p>
      <div class="pull-list">${list.map(p => `<label class="extra"><input type="checkbox" data-pull="${esc(p.name)}" ${pullPick.picked.has(p.name) ? 'checked' : ''}>
        <span><b>${esc(p.label)}</b><small>${esc(p.description)}</small></span></label>`).join('')}</div></div>`;
    $$('[data-pull]', box).forEach(c => (c.onchange = () => {
      pullPick.touched = true;
      c.checked ? pullPick.picked.add(c.dataset.pull) : pullPick.picked.delete(c.dataset.pull);
      updateStageCount(intake);
    }));
    updateStageCount(intake);
  }
  function nextCaseId(prefix) {
    const used = S.cases.map(c => c.id).filter(id => id.startsWith(prefix)).map(id => parseInt(id.slice(prefix.length), 10)).filter(Number.isFinite);
    return `${prefix}${String(used.length ? Math.max(...used) + 1 : 1).padStart(5, '0')}`;
  }
  function fieldInput(f) {
    const id = `f-${f.name}`, common = `class="input" id="${id}" data-field="${esc(f.name)}" ${f.required ? 'required' : ''}`;
    const input = f.type === 'textarea' ? `<textarea ${common} rows="3">${esc(f.default)}</textarea>`
      : f.type === 'select' ? `<select ${common}>${arr(f.options).map(o => `<option ${o === f.default ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`
        : `<input ${common} type="${f.type === 'date' ? 'date' : 'text'}" value="${esc(f.default)}">`;
    return `<div class="field ${f.wide || f.type === 'textarea' ? 'wide' : ''}"><label for="${id}">${esc(f.label || humanize(f.name))}${f.required || f.type === 'select' ? '' : ' <small class="muted">(optional)</small>'}</label>${input}</div>`;
  }
  function pickApp(name) {
    const app = S.apps[name];
    if (!app) return;
    S.intakeApp = name;
    $$('#appPick .seg').forEach(b => b.classList.toggle('active', b.dataset.app === name));
    $('#fieldsTitle').textContent = app.title.toUpperCase();
    $('#appDescription').textContent = app.description;
    $('#fieldGrid').innerHTML = `<div class="field"><label for="f-case-id">${esc(app.case.label)}</label><input class="input" id="f-case-id" name="case_id" required value="${esc(nextCaseId(app.case.prefix))}"></div>` +
      app.fields.map(fieldInput).join('');
    $$('[data-field]', $('#fieldGrid')).forEach(x => x.addEventListener('input', renderIntakePulls));
    $('#sampleBtn').hidden = !app.sample;
    pullPick.touched = false;
    intake.setLanes(app.lanes);
    renderIntakePulls();
  }
  function renderAppPick() {
    $('#appPick').innerHTML = S.appOrder.length > 1 ? S.appOrder.map(n => `<button type="button" class="seg" data-app="${esc(n)}" role="tab" title="${esc(S.apps[n].description)}">${esc(S.apps[n].title)}</button>`).join('') : '';
    $$('#appPick .seg').forEach(b => (b.onclick = () => pickApp(b.dataset.app)));
  }
  $('#sampleBtn').onclick = () => { intake.sample = true; intake.render(); };

  $('#caseForm').onsubmit = async e => {
    e.preventDefault();
    const app = S.apps[S.intakeApp], miss = intake.missing();
    if (miss.length) return toast(`Stage at least one file in ${miss.map(l => l.label || l.name).join(', ')} (or use the sample bundle).`, true);
    const fd = intake.formData(new FormData());
    fd.append('app', app.name);
    fd.append('case_id', $('#f-case-id').value);
    fd.append('fields', JSON.stringify(fieldValues()));
    fd.append('use_sample', intake.sample ? 'true' : 'false');
    if (app.pulls.length) { fd.append('pulls_selected', 'true'); pullPick.picked.forEach(n => fd.append('pulls', n)); }
    const btn = $('#submitCase');
    btn.disabled = true; btn.textContent = 'Uploading…';
    try {
      const c = await api('/api/cases', { method: 'POST', body: fd });
      const q = app.pulls.length ? pullPick.picked.size : 0;
      toast(`${c.id}: ${c.documents} files uploaded · agents started${q ? ` with ${q} data pull(s)` : ''}`);
      $('#newCasePanel').open = false;
      $('#intakeSummary').textContent = `last submitted ${c.id} · open for another case`;
      await refreshQueue(c.id);
      pickApp(app.name);
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = 'Upload & start →'; }
  };
  $('#newCasePanel').addEventListener('toggle', () => { if ($('#newCasePanel').open) $('#intakeSummary').textContent = ''; });

  // ---------------------------------------------------------------- page 1: case table
  const REC = { 'PENDING REVIEW': 'pending', APPROVED: 'approved', ERROR: 'error', 'IN PROGRESS': 'progress', REGENERATE: 'ready' };
  const TONE = { ok: 'approved', warn: 'extra', bad: 'error', info: 'pending' };
  function rowHtml(c, fresh) {
    const live = c.status === 'running' || c.status === 'queued';
    const fresh3 = c.versions > (seen[seenKey(c)] || 0);
    const sub = live ? `${c.documents} files · ${clock(c.elapsed)} agent time` : c.versions ? `${c.versions} report version(s)` : `${c.documents} files`;
    const work = `<button class="work-btn" data-work="${esc(c.id)}">${live ? '<span class="spinner"></span>' : '<span class="stage-dot"></span>'}${esc(c.stage || 'Agent work')}</button>`;
    const subject = columnFields(S.apps[c.app], c.fields).map(([, v]) => v);
    let act = '';
    if (c.page) act += `<button class="btn ${!live && c.status !== 'approved' ? '' : 'secondary'} small" data-open="${esc(c.id)}">${!live && c.status === 'ready' ? (fresh3 ? `Open v${c.versions} →` : 'Review →') : 'Detail'}</button>`;
    if (live) act += ` <button class="btn secondary small" data-stop="${esc(c.id)}">Stop</button>`;
    if (c.status === 'failed') act += ` <button class="btn dark small" data-retry="${esc(c.id)}">Retry</button>`;
    if (c.status === 'approved') act += ` <a class="btn secondary small" href="/api/cases/${enc(c.id)}/export.zip">ZIP</a>`;
    return `<tr class="${fresh ? 'fresh' : ''}">
      <td><span class="case-id">${esc(c.id)}</span><span class="case-sub">${esc(when(c.created))}</span></td>
      <td><span class="chip">${esc(c.app_title)}</span></td>
      <td class="subject" title="${esc(subject.join(' · '))}"><b>${esc(subject[0] || '—')}</b><small>${esc(subject.slice(1).join(' · '))}</small></td>
      <td><span class="status ${esc(c.status)}"><i></i><div>${esc(c.label)}${fresh3 ? ` <span class="chip new">NEW v${c.versions}</span>` : ''}<small>${esc(sub)}</small></div></span></td>
      <td><span class="chip ${TONE[c.tone] || REC[c.recommendation] || ''}">${esc(c.recommendation)}</span></td>
      <td>${work}</td><td><div class="actions">${act}</div></td></tr>`;
  }
  function renderQueue(freshId) {
    const q = $('#caseSearch').value.trim().toLowerCase();
    const rows = S.cases.filter(c => !q || c.id.toLowerCase().includes(q) || Object.values(obj(c.fields)).some(v => String(v).toLowerCase().includes(q)));
    $('#queueBody').innerHTML = rows.length ? rows.map(c => rowHtml(c, c.id === freshId)).join('')
      : `<tr><td colspan="7" class="empty">${S.cases.length ? 'No case matches this search.' : 'No cases yet. Start one above - the sample bundle is a quick start.'}</td></tr>`;
  }
  $('#caseSearch').oninput = () => renderQueue();
  $('#queueBody').addEventListener('click', async e => {
    const b = e.target.closest('button');
    if (!b) return;
    try {
      if (b.dataset.open) await openCase(b.dataset.open);
      else if (b.dataset.work) openWork(b.dataset.work);
      else if (b.dataset.stop) { await post(`/api/cases/${enc(b.dataset.stop)}/stop`); toast(`Stopping ${b.dataset.stop}…`); }
      else if (b.dataset.retry) { await post(`/api/cases/${enc(b.dataset.retry)}/retry`); toast(`${b.dataset.retry}: failed jobs queued again`); }
      refreshQueue();
    } catch (err) { toast(err.message, true); }
  });

  async function refreshQueue(freshId) {
    try {
      const prev = Object.fromEntries(S.cases.map(c => [c.id, c]));
      S.cases = await api('/api/cases');
      for (const c of S.cases) {
        const p = prev[c.id];
        if (p && p.label !== c.label && !BUSY(c.status)) toast(`${c.id}: ${c.label}`);
      }
      if (S.page === 1) renderQueue(freshId);
      if (S.current) {
        const c = S.cases.find(x => x.id === S.current), p = prev[S.current];
        if (c && (!p || c.updated !== p.updated)) refreshDetail();
      }
    } catch { /* shown by the health pill */ }
  }

  // ---------------------------------------------------------------- case detail
  async function openCase(id, page) {
    const d = await api(`/api/cases/${enc(id)}`);
    S.current = id; S.detail = d; S.version = null; S.openForms.clear(); S.extrasPicked = null;
    const target = page || d.page || 2;
    target === 3 ? renderPage3(d) : renderPage2(d);
  }
  const busyTyping = () => {
    const a = document.activeElement;
    return (a && a.matches('textarea, input[type=text], input:not([type])') && a.closest('.page.active') && a.value) || S.openForms.size > 0;
  };
  async function refreshDetail(force = false) {
    if (!S.current) return;
    try {
      const d = await api(`/api/cases/${enc(S.current)}`);
      if (!S.current || d.id !== S.current) return;
      S.detail = d;
      if (!force && busyTyping()) { renderJobs(d); return; }        // never wipe what the analyst is typing
      S.page === 2 ? renderPage2(d, false) : S.page === 3 ? renderPage3(d, false) : null;
    } catch { /* keep the last view */ }
  }

  const STATUS_ICON = { queued: '⏳', running: '<span class="spinner"></span>', done: '✓', failed: '✕', stopped: '■', staged: '·', stored: '·' };
  const jobState = s => `<span class="jstate ${esc(s)}">${STATUS_ICON[s] || '·'} ${esc(s)}</span>`;

  function renderJobs(d) {
    const items = arr(d.jobs).slice(-12).reverse().map(j => `<li class="${esc(j.status)}"><span>${STATUS_ICON[j.status] || '·'}</span>
      <div><b>${esc(j.label)}</b><small>${esc(j.role === 'query' ? `data pull${Object.keys(obj(obj(j.params).params)).length ? ` · ${Object.entries(obj(j.params.params)).map(([k, v]) => `${k}=${v}`).join(', ')}` : ''}` : j.params && j.params.feedback ? 'with analyst feedback' : j.params && j.params.instruction ? `prompt: ${j.params.instruction}` : j.role)}${j.error ? ` · ${esc(j.error)}` : ''}</small></div>
      <time>${j.finished && j.started ? clock(j.finished - j.started) : j.status === 'running' && j.started ? clock(Date.now() / 1000 - j.started) : ''}</time></li>`).join('');
    $('#jobList2').innerHTML = items || '<li class="muted">No jobs yet.</li>';
  }

  // ---------------------------------------------------------------- page 2
  let moreApp = null;
  const more = new Stager($('#moreLanes'), { compact: true, onChange: st => { $('#uploadMore').disabled = !st.files.length; } });
  $('#uploadMore').onclick = async () => {
    const fd = more.formData();
    $('#uploadMore').disabled = true;
    try {
      const r = await api(`/api/cases/${enc(S.current)}/documents`, { method: 'POST', body: fd });
      toast(`${r.added.length} file(s) uploaded · agents queued`);
      more.clear(); refreshDetail(true);
    } catch (e) { toast(e.message, true); $('#uploadMore').disabled = false; }
  };

  // every flaggable row: per-file agents' facts, then per-lane agents' facts
  function flatFacts(d, app) {
    const rows = [];
    for (const doc of arr(d.docs)) {
      const agent = obj(app.agents[doc.agent]);
      if (doc.per !== 'file' || !doc.insight) continue;
      for (const f of factsOf(agent.view, doc.insight.result)) rows.push({ target: doc.name, where: doc.name, status: doc.status, ...f, flags: arr(doc.corrections).filter(c => c.field === f.field) });
    }
    for (const ln of arr(d.lanes)) {
      if (!ln.insight) continue;
      const target = `lane:${ln.name}`;
      for (const f of factsOf(obj(app.agents[ln.agent]).view, ln.insight.result)) rows.push({ target, where: ln.label || ln.name, status: ln.status, ...f, flags: arr(ln.corrections).filter(c => c.field === f.field) });
    }
    return rows;
  }

  function noteForm(key, label, placeholder, button) {
    return `<div class="inline-form" data-note="${esc(key)}"><label>${label}</label>
      <div class="row"><textarea class="input" rows="2" placeholder="${esc(placeholder)}"></textarea><button class="btn dark small" data-send-note="${esc(key)}">${esc(button)}</button></div></div>`;
  }

  function renderPage2(d, scroll = true) {
    const app = appOf(d);
    if (!app) return toast(`App ${d.app} is not configured`, true);
    if (moreApp !== app.name) { more.setLanes(app.lanes, { optional: true }); moreApp = app.name; }
    $('#p2Eyebrow').textContent = `Page 2 · ${app.title} · verify insights`;
    caseStrip($('#strip2'), d, ['Status', d.label]);
    renderReady(d, app);

    // per-lane agents: one fold each
    $('#laneFolds').innerHTML = arr(d.lanes).map(ln => {
      const busy = BUSY(ln.status), res = obj(ln.insight), key = `lane:${ln.name}`;
      return `<details class="card fold" open><summary>${esc((ln.label || ln.name).toUpperCase())} · ${esc(ln.agent_label)} <span class="summary-meta">${busy ? `<span class="spinner"></span> ${esc(ln.status.toUpperCase())}` : ln.insight ? `UPDATED ${esc(when(res.updated))}` : ''}</span></summary>
        <div class="fold-body">${ln.insight ? renderBlocks(obj(app.agents[ln.agent]).view, res.result, { d, facts: 'skip' })
          : `<div class="placeholder">${busy ? `${esc(ln.agent_label)} is reading ${esc(arr(ln.files).join(', '))}…` : ln.status === 'failed' ? `${esc(ln.agent_label)} failed: ${esc(ln.error)}` : 'No result yet.'}</div>`}
          ${arr(ln.corrections).length ? `<div class="corrections">${arr(ln.corrections).map(c => `<div>✎ ${esc(c.field ? `${c.field}: ` : '')}${esc(c.analyst_value || c.note)}</div>`).join('')}</div>` : ''}
          ${noteForm(key, `Note for the ${esc(ln.agent_label)} <small>(${esc(arr(ln.files).join(', ') || 'no files')})</small>`, 'e.g. the matched person is the UBO, not a former director', 'Run again with note')}</div></details>`;
    }).join('');
    bindNotes($('#laneFolds'));

    $('#dataFold').hidden = !app.pulls.length;
    if (app.pulls.length) renderData(d, app);

    // facts to verify
    const rows = flatFacts(d, app);
    const low = rows.filter(r => num(r.confidence) < 80), flagged = rows.filter(r => r.flags.length);
    $('#factsFold').hidden = !rows.length && !arr(d.docs).some(x => x.per === 'file');
    $('#factMeta').textContent = `${rows.length} VALUES · ${low.length} LOW CONFIDENCE · ${flagged.length} FLAGGED`;
    $$('#factFilter .seg').forEach(b => b.classList.toggle('active', b.dataset.filter === S.factFilter));
    const shown = S.factFilter === 'low' ? low : S.factFilter === 'flagged' ? flagged : rows;
    const reading = arr(d.docs).filter(x => x.per === 'file' && BUSY(x.status));
    $('#facts').innerHTML = `<div class="insight-head"><span>Field · source</span><span>Value</span><span>Confidence</span><span>Location</span><span></span></div>` +
      reading.map(x => `<div class="insight-row pending"><div class="fname">${esc(x.name)}</div><div class="muted"><span class="spinner"></span> agent ${esc(x.status)}…</div><div></div><div></div><div></div></div>`).join('') +
      (shown.length ? shown.map((r, i) => {
        const conf = Math.max(0, Math.min(100, num(r.confidence) || 0));
        const fl = r.flags[r.flags.length - 1];
        const key = `kv:${r.target}:${r.field}`;
        return `<div class="insight-row ${conf < 80 ? 'low' : ''} ${fl ? 'edited' : ''}">
          <div class="fname">${esc(r.field)}<small class="docname">${esc(r.where)}</small>${fl ? `<small>${r.status === 'done' ? 'ANALYST FEEDBACK APPLIED' : 'RE-READING'}</small>` : ''}</div>
          <div class="val">${esc(txt(r.value))}${fl && fl.analyst_value ? `<div class="analyst">Analyst: ${esc(fl.analyst_value)}</div>` : ''}</div>
          <div class="conf"><b>${conf}%</b><div class="bar ${conf < 70 ? 'lowc' : conf < 85 ? 'mid' : ''}"><i style="width:${conf}%"></i></div></div>
          <div class="src">${esc(r.location || '')}</div>
          <div><button class="btn secondary small" data-flag="${i}" title="This value looks wrong">Flag</button></div>
          ${S.openForms.has(key) ? flagForm(i, key) : ''}</div>`;
      }).join('') : `<div class="empty">${rows.length ? 'No values in this filter.' : reading.length ? '' : 'No values to verify yet.'}</div>`);
    $$('#facts [data-flag]').forEach(b => (b.onclick = () => {
      const r = shown[+b.dataset.flag], key = `kv:${r.target}:${r.field}`;
      S.openForms.has(key) ? S.openForms.delete(key) : S.openForms.add(key);
      renderPage2(S.detail, false);
    }));
    $$('#facts [data-send-flag]').forEach(b => (b.onclick = () => {
      const r = shown[+b.dataset.sendFlag], f = b.closest('.inline-form');
      sendFeedback({ target: r.target, field: r.field, value: $('[name=value]', f).value, note: $('[name=note]', f).value }, b, `kv:${r.target}:${r.field}`);
    }));
    $$('#facts [data-cancel]').forEach(b => (b.onclick = () => { S.openForms.delete(b.dataset.cancel); renderPage2(S.detail, false); }));

    // files
    $('#docMeta').textContent = `${arr(d.docs).length} FILES`;
    $('#docGrid').innerHTML = arr(d.docs).map(x => {
      const lane = app.lanes.find(l => l.name === x.lane) || {}, res = obj(x.insight), key = `doc:${x.name}`;
      const state = x.per === 'file' ? jobState(x.status) : x.per === 'lane' ? `<span class="muted">Read with the ${esc(lane.label || x.lane)} lane by the ${esc(lane.agent_label)}</span>` : '<span class="muted">Read by the report agent</span>';
      return `<article class="doc-card"><header><div><b>${docLink(d, x.name)}</b><small>${esc(when(x.uploaded))}</small></div>
          <span class="chip ${x.per === 'lane' ? 'pending' : ''}">${esc((lane.label || x.lane).toUpperCase())}</span></header>
        <div class="doc-state">${state}${x.error ? ` <span class="flag">${esc(x.error)}</span>` : ''}</div>
        ${x.insight ? `<div class="doc-body">${renderBlocks(obj(app.agents[x.agent]).view, res.result, { d, facts: 'dl' })}</div>` : ''}
        ${arr(x.corrections).length ? `<div class="corrections">${arr(x.corrections).map(cc => `<div>✎ ${esc(cc.field ? `${cc.field}: ` : '')}${esc(cc.analyst_value || cc.note)}</div>`).join('')}</div>` : ''}
        ${x.per ? `<footer>${noteForm(key, 'Note for the agent', 'What did the agent miss or get wrong in this file?', 'Run again with note')}</footer>` : ''}</article>`;
    }).join('') || '<div class="placeholder">No files.</div>';
    bindNotes($('#docGrid'));

    renderJobs(d);
    renderExtras($('#extraList2'), d);
    const pending = arr(d.jobs).filter(j => BUSY(j.status) && ['insight', 'query'].includes(j.role)).length;
    const name = app.report.name;
    $('#reportHead2').textContent = name.toUpperCase();
    $('#toReport2').textContent = `${name} →`;
    $('#genHint2').textContent = (pending ? `${pending} insight / data job(s) still running - ask now and the ${app.report.label.toLowerCase()} starts when they finish. ` : d.reports.length ? `Latest: v${d.reports[d.reports.length - 1].version}${d.stale ? ' (out of date)' : ''}. ` : '') +
      'It runs in the background: you go back to the case table, which shows when the version is ready.';
    $('#genReport2').textContent = pending ? `Generate ${name} when ready →` : d.reports.length ? `Regenerate ${name} (v${d.reports.length + 1}) →` : `Generate ${name} →`;
    if (scroll) show(2);
  }

  function bindNotes(root) {
    $$('[data-note] textarea', root).forEach(t => {
      const key = t.closest('[data-note]').dataset.note;
      t.addEventListener('input', () => (t.value ? S.openForms.add(`note:${key}`) : S.openForms.delete(`note:${key}`)));
    });
    $$('[data-send-note]', root).forEach(b => (b.onclick = () => {
      const key = b.dataset.sendNote, target = key.startsWith('doc:') ? key.slice(4) : key;
      sendFeedback({ target, note: $('textarea', b.closest('.inline-form')).value }, b, `note:${key}`);
    }));
  }

  // ---------------------------------------------------------------- page 2: readiness and data pulls
  const shortProgress = s => String(s || '').replace(/^querying [^·]*·\s*/, '');
  function renderReady(d, app) {
    const item = (label, state, text) => `<div class="ready ${state}"><i>${state === 'busy' ? '<span class="spinner"></span>' : state === 'ok' ? '✓' : state === 'bad' ? '✕' : '·'}</i><span>${esc(label)}</span><b>${esc(text)}</b></div>`;
    const items = [];
    let n = 0;
    for (const lane of app.lanes.filter(l => l.agent)) {
      if (lane.per === 'lane') {
        const ln = arr(d.lanes).find(x => x.name === lane.name) || {};
        if (BUSY(ln.status)) n++;
        items.push(BUSY(ln.status) ? item(lane.label, 'busy', 'reading') : ln.insight ? item(lane.label, 'ok', 'ready') : item(lane.label, ln.status === 'failed' ? 'bad' : '', ln.status === 'failed' ? 'failed' : 'none'));
      } else {
        const files = arr(d.docs).filter(x => x.lane === lane.name), busy = files.filter(x => BUSY(x.status)).length;
        n += busy;
        items.push(item(lane.label, busy ? 'busy' : files.some(x => x.status === 'failed') ? 'bad' : files.length ? 'ok' : '', files.length ? `${files.length - busy}/${files.length} done` : 'none'));
      }
    }
    if (app.pulls.length) {
      const data = arr(d.data).filter(p => p.status), dBusy = data.filter(p => BUSY(p.status)), run = dBusy.find(p => p.status === 'running');
      n += dBusy.length;
      items.push(item('Data', dBusy.length ? 'busy' : data.some(p => p.status === 'failed') ? 'bad' : data.length ? 'ok' : '', data.length ? `${data.length - dBusy.length}/${data.length} done${run ? ` · ${run.label} ${shortProgress(run.progress)}` : ''}` : 'none'));
    }
    $('#ready2').innerHTML = items.join('') + `<div class="ready-note">${n ? `${n} job(s) running. Review what is here; the ${esc(app.report.name)} can be asked for now and starts when they finish.` : `All inputs are in: ready for the ${esc(app.report.name)}.`}</div>`;
  }

  const miniTable = (title, cols, rows) => `<div class="mini">${title ? `<b>${esc(title)}</b>` : ''}<div class="table-wrap"><table class="grid mini-grid">
    <thead><tr>${arr(cols).map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
    <tbody>${arr(rows).map(r => `<tr>${arr(r).map(v => `<td>${esc(v)}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${arr(cols).length || 1}" class="empty">No rows.</td></tr>`}</tbody></table></div></div>`;

  function dataCard(d, app, p, i) {
    const r = obj(p.result), live = BUSY(p.status), key = `data:${p.name}`, kv = arr(r.key_values);
    const params = Object.entries(obj(r.params)).map(([k, v]) => `${k}=${v}`).join(' · ');
    const shown = { ...obj(r.params), ...obj(p.params) };
    const fieldOf = b => app.fields.find(f => f.name === b) || { name: b };
    return `<article class="data-card ${p.result || live ? '' : 'idle'}">
      <header><div><b>${esc(p.label)}</b><small>${esc(p.database)} · ${esc(p.description)}</small></div>${p.status ? jobState(p.status) : '<span class="jstate">not run</span>'}</header>
      ${live ? `<div class="data-progress"><span class="spinner"></span> ${esc(p.status === 'queued' ? 'queued' : p.progress || 'querying…')}</div>` : ''}
      ${p.error && !live ? `<div class="data-progress"><span class="flag">${esc(p.error)}</span></div>` : ''}
      ${p.result ? `<div class="data-params mono">${esc(params)} · ${esc(String(r.rows))} rows${r.truncated ? ` (capped at ${esc(String(r.row_cap))})` : ''} · ${esc(when(r.updated))}</div>
        ${kv.filter(k => !k.columns).length ? `<dl>${kv.filter(k => !k.columns).map(k => `<dt>${esc(k.field)}</dt><dd>${esc(k.value)}</dd>`).join('')}</dl>` : ''}
        ${kv.filter(k => k.columns).map(k => miniTable(k.field, k.columns, k.rows)).join('')}
        <details class="data-more"><summary>Rows (first ${arr(r.preview).length} of ${esc(String(r.rows))})</summary>${miniTable('', r.columns, r.preview)}</details>
        <details class="data-more"><summary>SQL</summary><pre>${esc(r.sql)}</pre></details>` : ''}
      <footer>${live ? `<button class="btn secondary small" data-pull-stop="${esc(p.job)}">Cancel</button>`
        : `<button class="btn ${p.result ? 'secondary' : 'dark'} small" data-pull-run="${i}">${p.result ? 'Re-run' : 'Run'}</button>${arr(p.binds).length ? ` <button class="btn link" data-pull-edit="${i}">Change parameters</button>` : ''}`}
        ${p.result ? `<a class="btn link" href="/api/cases/${enc(d.id)}/data/${enc(p.name)}">CSV</a>` : ''}</footer>
      ${S.openForms.has(key) && !live ? `<div class="inline-form"><div class="row">
        ${arr(p.binds).map(b => { const f = fieldOf(b); return `<label>${esc(f.label || humanize(b))} <input class="input" type="${f.type === 'date' ? 'date' : 'text'}" name="${esc(b)}" value="${esc(shown[b] ?? obj(d.fields)[b] ?? '')}"></label>`; }).join('')}
        <button class="btn dark small" data-pull-send="${i}">Run with these</button><button class="btn secondary small" data-cancel="${esc(key)}">Cancel</button></div></div>` : ''}
    </article>`;
  }

  function renderData(d, app) {
    const grid = $('#dataGrid'), list = arr(d.data);
    const busy = list.filter(p => BUSY(p.status)).length, done = list.filter(p => p.result).length;
    $('#dataMeta').innerHTML = busy ? `<span class="spinner"></span> ${busy} RUNNING · ${done} DONE` : `${done} OF ${list.length} PULLED`;
    grid.innerHTML = list.map((p, i) => dataCard(d, app, p, i)).join('');
    $$('[data-pull-run]', grid).forEach(b => (b.onclick = () => { const p = list[+b.dataset.pullRun]; runPull({ pull: p.name, params: obj(p.params) }, b); }));
    $$('[data-pull-stop]', grid).forEach(b => (b.onclick = async () => {
      b.disabled = true;
      try { await post(`/api/cases/${enc(d.id)}/jobs/${enc(b.dataset.pullStop)}/stop`); toast('Cancelling the data pull…'); refreshDetail(true); }
      catch (e) { toast(e.message, true); b.disabled = false; }
    }));
    $$('[data-pull-edit]', grid).forEach(b => (b.onclick = () => {
      const k = `data:${list[+b.dataset.pullEdit].name}`;
      S.openForms.has(k) ? S.openForms.delete(k) : S.openForms.add(k);
      renderPage2(S.detail, false);
    }));
    $$('[data-pull-send]', grid).forEach(b => (b.onclick = () => {
      const p = list[+b.dataset.pullSend], params = {};
      $$('input[name]', b.closest('.inline-form')).forEach(x => { if (x.value && x.value !== obj(d.fields)[x.name]) params[x.name] = x.value; });
      S.openForms.delete(`data:${p.name}`);
      runPull({ pull: p.name, params }, b);
    }));
    $$('[data-cancel]', grid).forEach(b => (b.onclick = () => { S.openForms.delete(b.dataset.cancel); renderPage2(S.detail, false); }));
  }

  async function runPull(body, btn) {
    btn.disabled = true;
    try { await post(`/api/cases/${enc(S.current)}/data`, body); toast(`${body.pull}: data pull queued - it runs alongside the agents`); refreshDetail(true); }
    catch (e) { toast(e.message, true); btn.disabled = false; }
  }

  function flagForm(i, key) {
    return `<div class="inline-form flag-form"><div class="row">
      <input class="input" name="value" placeholder="Correct value (if you know it)">
      <input class="input" name="note" placeholder="What is wrong? e.g. amount is per carton, not the total">
      <button class="btn dark small" data-send-flag="${i}">Send to the agent</button><button class="btn secondary small" data-cancel="${esc(key)}">Cancel</button></div></div>`;
  }

  async function sendFeedback(body, btn, formKey) {
    if (!String(body.note || '').trim() && !String(body.value || '').trim()) return toast('Say what is wrong first.', true);
    btn.disabled = true;
    try {
      await post(`/api/cases/${enc(S.current)}/feedback`, body);
      toast(`${body.target.replace(/^lane:/, '')}: the agent runs again with your note`);
      if (formKey) S.openForms.delete(formKey);
      refreshDetail(true);
    } catch (e) { toast(e.message, true); btn.disabled = false; }
  }

  $$('#factFilter .seg').forEach(b => (b.onclick = () => { S.factFilter = b.dataset.filter; renderPage2(S.detail, false); }));

  function renderExtras(el, d) {
    const ex = obj(d.extras);
    if (S.extrasPicked === null) S.extrasPicked = new Set(Object.entries(ex).filter(([, v]) => v.default).map(([k]) => k));
    el.innerHTML = Object.keys(ex).length ? Object.entries(ex).map(([k, v]) => `<label class="extra"><input type="checkbox" data-extra="${esc(k)}" ${S.extrasPicked.has(k) ? 'checked' : ''}>
      <span><b>${esc(v.label)}</b><small>${esc(v.remote ? 'external agent' : 'local agent')}${v.status ? ` · last run ${esc(v.status)}` : ''}</small></span></label>`).join('')
      : '<p class="caption">No extra agents for this app.</p>';
    $$('[data-extra]', el).forEach(c => (c.onchange = () => (c.checked ? S.extrasPicked.add(c.dataset.extra) : S.extrasPicked.delete(c.dataset.extra))));
  }

  /* Every report request is asynchronous: queue it and go back to the case table, which shows NEW vN when the
     version is in. A prompt revises the report only; extra agents run with a generation from Page 2. */
  async function requestReport(instruction = '') {
    const app = appOf(S.detail), id = S.current;
    try {
      await post(`/api/cases/${enc(id)}/report`, { extras: instruction ? [] : [...(S.extrasPicked || [])], instruction });
      toast(`${id}: ${instruction ? 'prompt' : app.report.name} queued - the case table shows when the new version is in`);
      show(1);
      refreshQueue();
    } catch (e) { toast(e.message, true); }
  }
  $('#genReport2').onclick = () => requestReport();

  // ---------------------------------------------------------------- page 3: the report, its next steps, the prompt panel
  const PROMPT_KEY = 'kentc-studio-prompt-open';
  function setPromptOpen(open) {
    localStorage.setItem(PROMPT_KEY, open ? '1' : '0');
    $('#page3 .review-layout').classList.toggle('prompt-closed', !open);
    $('#promptPanel').classList.toggle('closed', !open);
    $('#promptToggle').setAttribute('aria-expanded', String(open));
    $('#promptToggle').title = open ? 'Hide the prompt panel' : 'Open the prompt panel';
  }
  $('#promptToggle').onclick = () => setPromptOpen($('#promptPanel').classList.contains('closed'));
  setPromptOpen(localStorage.getItem(PROMPT_KEY) !== '0');

  function renderPage3(d, scroll = true) {
    const app = appOf(d);
    if (!app) return toast(`App ${d.app} is not configured`, true);
    const rep3 = app.report, reports = arr(d.reports);
    const busy = arr(d.jobs).filter(j => ['report', 'extra'].includes(j.role) && BUSY(j.status));
    const last = reports.length ? reports[reports.length - 1].version : null;
    if (S.version === null || !reports.some(r => r.version === S.version)) S.version = last;
    const rep = reports.find(r => r.version === S.version);
    const r = obj(rep && rep.data);
    if (last) markSeen(d, last);                    // the analyst has the latest version in front of them

    $('#journey3').textContent = rep3.name;
    $('#p3Eyebrow').textContent = `Page 3 · ${app.title} · ${rep3.name}`;
    $('#versionSel').innerHTML = reports.map(x => `<option value="${x.version}" ${x.version === S.version ? 'selected' : ''}>v${x.version}${d.approved && d.approved.version === x.version ? ' · approved' : ''}</option>`).join('') || '<option>—</option>';
    $('#versionSel').disabled = !reports.length;
    $('#p3Title').textContent = rep ? `${rep3.name} v${rep.version}${d.approved && d.approved.version === rep.version ? ' · approved' : ''}` : rep3.name;
    caseStrip($('#strip3'), d, ['Verdict', r.verdict ? txt(r.verdict) : '—']);
    const approvedThis = d.approved && rep && d.approved.version === rep.version;
    $('#approveBtn').disabled = !rep || approvedThis || busy.length > 0;
    $('#approveBtn').textContent = approvedThis ? `v${rep.version} approved` : rep ? `Approve v${rep.version}` : 'Approve';
    $('#zipLink').href = `/api/cases/${enc(d.id)}/export.zip`;

    const banner = $('#staleBanner');
    if (busy.length) {
      const run = busy.find(j => j.status === 'running');
      const inputs = arr(d.jobs).filter(j => BUSY(j.status) && ['insight', 'query'].includes(j.role)).length;
      banner.hidden = false;
      banner.className = 'banner working';
      banner.innerHTML = `<span class="spinner"></span><div><b>${esc(run ? run.label : `${rep3.name} jobs queued`)}</b> ${run && run.params.instruction ? `working on the prompt: “${esc(run.params.instruction)}”` : run ? 'drafting the next version' : inputs ? `waiting for ${inputs} insight / data job(s)` : `waiting for ${busy.length} job(s)`}
        <small>${d.live && d.live.text ? esc(d.live.text.slice(-220)) : 'It runs in the background - the case table shows when the version is ready.'}</small></div><button class="btn secondary small" data-open-work>Watch</button>`;
    } else if (d.stale && rep && rep.version === last) {
      banner.hidden = false;
      banner.className = 'banner';
      banner.innerHTML = `<div><b>New evidence or corrections since v${rep.version}.</b> The report does not include them yet.</div><button class="btn small" id="regenBtn">Regenerate v${reports.length + 1}</button>`;
      $('#regenBtn').onclick = () => requestReport();
    } else banner.hidden = true;

    $('#reportView').innerHTML = rep ? reportHtml(d, app, rep, r) : `<div class="placeholder">${busy.length ? `The ${esc(rep3.label.toLowerCase())} is drafting the first version - the case table shows when it is ready.` : 'No version yet. Generate it from Page 2.'}</div>`;
    if (rep) bindNextSteps(d, app, r);
    renderPrompt(d, app, busy.length > 0);
    if (scroll) show(3);
  }
  $('#versionSel').onchange = e => { S.version = +e.target.value; renderPage3(S.detail, false); };
  $('#approveBtn').onclick = async () => {
    const d = S.detail;
    try { await post(`/api/cases/${enc(d.id)}/approve`, { version: S.version }); toast(`v${S.version} approved`); refreshDetail(true); }
    catch (e) { toast(e.message, true); }
  };
  $('#printBtn').onclick = () => window.print();

  function reportHtml(d, app, rep, r) {
    const tone = obj(app.report.verdicts)[Object.keys(obj(app.report.verdicts)).find(k => k.toLowerCase() === String(r.verdict || '').toLowerCase())] || 'info';
    return `<div class="report">
      <div class="report-head"><div><span class="eyebrow">${esc(app.report.name)} · ${esc(app.title)}</span><h1>${esc(r.title || d.id)}</h1>
        ${r.verdict ? `<span class="chip ${TONE[tone] || ''}">${esc(String(r.verdict).toUpperCase())}</span>` : ''}</div>
        <div class="report-meta"><span>${esc(d.id)}</span><span>v${rep.version} · ${esc(when(rep.created))}</span></div></div>
      ${rep.instruction ? `<div class="fold-note"><b>Prompt:</b> ${esc(rep.instruction)}${r.reply ? `<br><b>Reply:</b> ${esc(txt(r.reply))}` : ''}</div>` : ''}
      ${renderBlocks(app.report.view, r, { d, h: 'h2', facts: 'skip' })}
      ${nextStepsHtml(app, r)}
    </div>`;
  }

  // requested documents go to the lane read file by file (evidence), else the first lane with an agent
  const requestLane = app => app.lanes.find(l => l.per === 'file') || app.lanes.find(l => l.agent) || app.lanes[0];

  /* The agent's suggestions, on the report itself: documents to request (upload → Page 2 to review them) and
     open questions (each can start a prompt). */
  function nextStepsHtml(app, r) {
    const reqs = arr(r.requests), qs = arr(r.questions), lane = requestLane(app);
    return `<section class="next-steps"><h2>Suggested next steps</h2>
      <h3>Request from the client</h3>
      ${reqs.length ? `<ul class="req-list">${reqs.map((q, i) => `<li><div><b>${esc(obj(q).document || txt(q))}</b><small>${esc(obj(q).reason || '')}</small></div>
        <label class="btn secondary small no-print">Upload<input type="file" multiple hidden data-req="${i}"></label></li>`).join('')}</ul>` : '<p class="caption">No documents requested.</p>'}
      <div class="req-other no-print"><label class="btn secondary small">Upload other files<input type="file" multiple hidden data-req="other"></label>
        <span class="caption">Uploads go to the ${esc(lane.label || lane.name)} lane and open Page 2 to review what the agents read; regenerate from there.</span></div>
      ${qs.length ? `<h3>Open questions</h3><ul class="q-list">${qs.map((q, i) => `<li><span>${esc(txt(q))}</span><button type="button" class="btn link no-print" data-q="${i}">Use as prompt</button></li>`).join('')}</ul>` : ''}
    </section>`;
  }

  function bindNextSteps(d, app, r) {
    const view = $('#reportView'), lane = requestLane(app).name;
    $$('[data-q]', view).forEach(b => (b.onclick = () => {
      setPromptOpen(true);
      const p = $('#prompt');
      if (p.disabled) return toast('Wait for the running version to finish.', true);
      p.value = (p.value ? `${p.value}\n` : '') + `Clarify: ${txt(arr(r.questions)[+b.dataset.q])}`;
      S.openForms.add('prompt');
      p.focus();
    }));
    $$('[data-req]', view).forEach(inp => (inp.onchange = async () => {
      if (!inp.files.length) return;
      const fd = new FormData();
      for (const f of inp.files) {
        if (isVideo(f.name) || isLegacy(f.name)) { toast(`${f.name}: unsupported format`, true); return; }
        fd.append('files', f, f.name); fd.append('lanes', lane);
      }
      try {
        const res = await api(`/api/cases/${enc(d.id)}/documents`, { method: 'POST', body: fd });
        toast(`${res.added.join(', ')} uploaded · review them on Page 2 while the agents read`);
        await refreshDetail(true);
        renderPage2(S.detail);
      } catch (e) { toast(e.message, true); }
    }));
  }

  /* The prompt panel only takes a prompt: one prompt → one new version, asynchronously. */
  function renderPrompt(d, app, busy) {
    const reports = arr(d.reports), last = reports.length ? reports[reports.length - 1].version : 0;
    const can = last > 0 && !busy, keep = $('#prompt') ? $('#prompt').value : '';
    $('#promptBody').innerHTML = `
      <p class="caption">${can ? `Tell the ${esc(app.report.label.toLowerCase())} what to change or explain. It revises v${last} into <b>v${last + 1}</b> in the background: you go back to the case table, and the row shows <span class="chip new">NEW v${last + 1}</span> when it is ready.`
        : busy ? 'A version is being written. Open it from the case table when it is ready, then prompt again.' : 'Generate the first version from Page 2, then prompt here.'}</p>
      <textarea class="input" id="prompt" rows="9" ${can ? '' : 'disabled'} placeholder="e.g. explain the evidence for the top risk; shorten the narrative; correct the counterparty name"></textarea>
      <button class="btn dark" id="sendPrompt" ${can ? '' : 'disabled'}>Send prompt → v${last + 1}</button>`;
    const p = $('#prompt');
    p.value = can ? keep : '';
    p.addEventListener('input', () => (p.value ? S.openForms.add('prompt') : S.openForms.delete('prompt')));
    $('#sendPrompt').onclick = () => {
      if (!p.value.trim()) return toast('Write what to change or explain first.', true);
      S.openForms.delete('prompt');
      requestReport(p.value.trim());
    };
  }

  // ---------------------------------------------------------------- agent work panel
  const ICON = { status: '·', tool: '⚙', result: '↳', error: '✕', start: '▶', done: '✓', queued: '⏳', compaction: '◆' };
  function openWork(id) {
    const W = S.work;
    clearInterval(W.timer);
    Object.assign(W, { id, after: 0, tick: 0 });
    $('#awTitle').textContent = id;
    $('#awFeed').innerHTML = '';
    $('#awLive').hidden = true;
    $('#agentWork').classList.add('open');
    $('#workBackdrop').classList.add('open');
    pollWork(true);
    W.timer = setInterval(pollWork, 1300);
  }
  function closeWork() {
    clearInterval(S.work.timer);
    S.work.id = null;
    $('#agentWork').classList.remove('open');
    $('#workBackdrop').classList.remove('open');
  }
  $('#awClose').onclick = closeWork;
  $('#workBackdrop').onclick = closeWork;
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeWork(); });
  $('#awStop').onclick = async () => { try { await post(`/api/cases/${enc(S.work.id)}/stop`); toast('Stopping at the next agent event…'); } catch (e) { toast(e.message, true); } };

  async function pollWork(full = false) {
    const W = S.work, id = W.id;
    if (!id) return;
    try {
      if (full || W.tick++ % 3 === 0) {
        const d = await api(`/api/cases/${enc(id)}`);
        if (W.id !== id) return;
        $('#awJobs').innerHTML = arr(d.jobs).slice(-8).reverse().map(j => `<li class="${esc(j.status)}"><span>${STATUS_ICON[j.status] || '·'}</span><div><b>${esc(j.label)}</b><small>${esc(j.status)}${j.error ? ` · ${esc(j.error)}` : ''}</small></div>
          <time>${j.started ? clock((j.finished || Date.now() / 1000) - j.started) : ''}</time></li>`).join('') || '<li>No jobs.</li>';
      }
      const r = await api(`/api/cases/${enc(id)}/events?after=${W.after}`);
      if (W.id !== id) return;
      $('#awStage').textContent = `AGENT WORK · ${(r.view.stage || r.view.status).toUpperCase()}`;
      $('#awStatus').textContent = r.view.label;
      $('#awStop').hidden = !BUSY(r.view.status);
      const feed = $('#awFeed');
      const nearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 60;
      feed.insertAdjacentHTML('beforeend', r.events.map(ev => `<div class="ev ${esc(ev.kind)}"><time>${hhmmss(ev.time)}</time><span class="k">${ICON[ev.kind] || '·'}</span>
        <div class="txt"><span class="who">${esc(ev.agent)}</span>${esc(ev.text)}</div></div>`).join(''));
      if (r.events.length) W.after = r.events[r.events.length - 1].seq;
      if (nearBottom || full) feed.scrollTop = feed.scrollHeight;
      const live = $('#awLive');
      if (r.live && r.live.text && r.view.status === 'running') {
        live.hidden = false;
        live.className = `live ${r.live.kind === 'reasoning' ? 'reasoning' : ''}`;
        live.innerHTML = `<span class="lbl">${esc(r.live.agent)} · ${r.live.kind === 'reasoning' ? 'THINKING' : 'WRITING'}${r.tokens && r.tokens.window ? ` · CONTEXT ${Math.round(r.tokens.used / 1000)}k / ${Math.round(r.tokens.window / 1000)}k` : ''}</span>${esc(r.live.text.slice(-900))}`;
        live.scrollTop = live.scrollHeight;
      } else live.hidden = true;
    } catch { /* keep polling */ }
  }

  // ---------------------------------------------------------------- boot
  async function boot() {
    const apps = await api('/api/apps');
    S.appOrder = apps.map(a => a.name);
    S.apps = Object.fromEntries(apps.map(a => [a.name, a]));
    $('#brandCopy').textContent = `Agentic Studio · ${apps.map(a => a.title).join(' · ')}`;
    await refreshHealth();
    await refreshQueue();
    renderAppPick();
    pickApp(S.appOrder[0]);
    if (S.cases.length) $('#newCasePanel').open = false;
    const m = location.hash.match(/^#case\/([^/]+)(?:\/(\d))?$/);
    if (m) openCase(decodeURIComponent(m[1]), m[2] ? +m[2] : undefined).catch(e => toast(e.message, true));
    setInterval(refreshQueue, 2000);
    setInterval(refreshHealth, 8000);
    setInterval(() => { if (S.current && S.detail && arr(S.detail.jobs).some(j => BUSY(j.status))) refreshDetail(); }, 4000);
  }
  boot().catch(e => toast(`Studio failed to start: ${e.message}`, true));
})();
