/* TER Agentic Studio front end.
   Page 1: stage documents (context required, doc evidence optional), pick data pulls, and track cases.
   Page 2: review the context/doc agents' output and the data pulls, flag wrong values, add documents - all
   asynchronous; the report can be asked for at any time and starts when the pending jobs finish.
   Page 3: the report agent's TER report: request documents, refine into new versions, approve, export.
   Every view is rebuilt from the API (src/kentc_studio/api/); nothing is simulated. */
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
  const S = { cases: [], health: null, current: null, detail: null, page: 1, version: null, insightFilter: 'all',
    openForms: new Set(), work: { id: null, after: 0, timer: null, tick: 0 }, extrasPicked: null };

  // ---------------------------------------------------------------- staging lanes (reusable)
  const LANES = {
    context: { title: 'CONTEXT', tag: 'REQUIRED', hint: 'Trigger e-mails, customer explanations, case notes → context agent' },
    doc: { title: 'EVIDENCE', tag: 'OPTIONAL', hint: 'Invoices, contracts, B/L, customs, statements → doc agent (key values)' },
  };

  class Stager {
    constructor(el, { compact = false, contextRequired = true, onChange = () => {} } = {}) {
      Object.assign(this, { el, compact, contextRequired, onChange, files: [], sample: false });
      el.innerHTML = Object.entries(LANES).map(([role, l]) => `
        <div class="lane" data-role="${role}">
          <div class="lane-head"><b>${l.title}</b><span class="chip ${role === 'context' && contextRequired ? 'ready' : ''}">${role === 'context' && !contextRequired ? 'OPTIONAL' : l.tag}</span></div>
          <div class="dropzone ${compact ? 'small' : ''}"><span>${esc(l.hint)}</span>
            <button type="button" class="btn secondary small">Choose files</button><input type="file" multiple hidden></div>
          <div class="docs"></div>
        </div>`).join('');
      $$('.lane', el).forEach(lane => {
        const role = lane.dataset.role, dz = $('.dropzone', lane), input = $('input', lane);
        $('button', dz).onclick = () => input.click();
        input.onchange = () => { this.add(input.files, role); input.value = ''; };
        ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.add('drag'); }));
        ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.remove('drag'); }));
        dz.addEventListener('drop', e => this.add(e.dataTransfer.files, role));
      });
      this.render();
    }
    add(list, role) {
      for (const f of list) {
        if (isVideo(f.name)) { toast(`${f.name}: video input is not supported`, true); continue; }
        if (isLegacy(f.name)) { toast(`${f.name}: save it as .docx / .xlsx / .pptx first`, true); continue; }
        this.files = this.files.filter(x => x.file.name !== f.name);
        this.files.push({ file: f, role });
      }
      this.render();
    }
    clear() { this.files = []; this.sample = false; this.render(); }
    count(role) { return this.files.filter(f => f.role === role).length; }
    render() {
      for (const role of Object.keys(LANES)) {
        const box = $(`.lane[data-role="${role}"] .docs`, this.el);
        const chips = this.files.map((f, i) => ({ f, i })).filter(x => x.f.role === role).map(({ f, i }) =>
          `<span class="doc-chip"><em>${esc((f.file.name.split('.').pop() || '').toUpperCase())}</em>${esc(f.file.name)}
            <button type="button" data-move="${i}" title="Move to the other lane">⇄</button><button type="button" data-rm="${i}" title="Remove">×</button></span>`);
        if (this.sample) chips.unshift(`<span class="doc-chip sample"><em>SAMPLE</em>${role === 'context' ? 'customer e-mail (with contract attached)' : 'KYC, invoice, B/L, customs, statement'}</span>`);
        box.innerHTML = chips.join('');
      }
      $$('[data-rm]', this.el).forEach(b => (b.onclick = () => { this.files.splice(+b.dataset.rm, 1); this.render(); }));
      $$('[data-move]', this.el).forEach(b => (b.onclick = () => { const f = this.files[+b.dataset.move]; f.role = f.role === 'doc' ? 'context' : 'doc'; this.render(); }));
      this.onChange(this);
    }
    formData(fd = new FormData()) {
      this.files.forEach(f => { fd.append('files', f.file, f.file.name); fd.append('roles', f.role); });
      return fd;
    }
  }

  // ---------------------------------------------------------------- pages
  function show(page) {
    S.page = page;
    $$('.page').forEach(p => p.classList.toggle('active', p.id === `page${page}`));
    $$('.journey-step').forEach(j => { const n = +j.dataset.page; j.classList.toggle('active', n === page); j.classList.toggle('done', n < page); });
    $('#backBtn').hidden = page === 1;
    if (page === 1) { S.current = null; S.detail = null; S.openForms.clear(); history.replaceState(null, '', '#'); }
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
    if (!S.detail) return toast('Open a case from the queue first.');
    n === 2 ? renderPage2(S.detail) : renderPage3(S.detail);
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
      $('#sampleBtn').hidden = !h.sample;
    } catch {
      $('#modelPill').className = 'pill bad';
      $('#modelPill').lastElementChild.textContent = 'server offline';
    }
  }

  // ---------------------------------------------------------------- page 1: intake
  // data pulls on Page 1: pre-ticked from the trigger text until the analyst changes a tick
  const pullPick = { picked: new Set(), touched: false };
  function updateStageCount(st) {
    const c = st.count('context') + (st.sample ? 1 : 0), d = st.count('doc') + (st.sample ? 5 : 0), q = pullPick.picked.size;
    const pulls = `${q} data pull${q === 1 ? '' : 's'}`;
    $('#stageCount').innerHTML = c || d ? `${c} context · ${d} evidence staged · ${pulls}${c ? '' : ' — <b style="color:var(--red)">add a context document</b>'}` : `Nothing staged.${q ? ` ${pulls} ticked.` : ''}`;
  }
  const intake = new Stager($('#intakeLanes'), { onChange: updateStageCount });
  function renderIntakePulls() {
    const box = $('#intakePulls'), list = arr(S.health && S.health.data_pulls);
    if (!list.length) { box.innerHTML = ''; return updateStageCount(intake); }
    const trig = String($('#caseForm').trigger.value || '').toLowerCase();
    if (!pullPick.touched) pullPick.picked = new Set(list.filter(p => p.default || arr(p.triggers).some(t => trig.includes(String(t).toLowerCase()))).map(p => p.name));
    box.innerHTML = `<div class="lane"><div class="lane-head"><b>DATA PULLS</b><span class="chip pending">NO MODEL · RUN IN PARALLEL</span></div>
      <p class="caption" style="margin:0 0 8px">SQL on ${esc([...new Set(list.map(p => p.database))].join(', '))} with the CIF and review period above. Results appear on Page 2; the report waits for them.</p>
      <div class="pull-list">${list.map(p => `<label class="extra"><input type="checkbox" data-pull="${esc(p.name)}" ${pullPick.picked.has(p.name) ? 'checked' : ''}>
        <span><b>${esc(p.label)}</b><small>${esc(p.description)}</small></span></label>`).join('')}</div></div>`;
    $$('[data-pull]', box).forEach(c => (c.onchange = () => {
      pullPick.touched = true;
      c.checked ? pullPick.picked.add(c.dataset.pull) : pullPick.picked.delete(c.dataset.pull);
      updateStageCount(intake);
    }));
    updateStageCount(intake);
  }
  $('#caseForm').trigger.addEventListener('input', renderIntakePulls);
  $('#sampleBtn').onclick = () => { intake.sample = true; intake.render(); };

  function nextCaseId() {
    const base = 'TER-2026-';
    const used = S.cases.map(c => c.id).filter(id => id.startsWith(base)).map(id => parseInt(id.slice(base.length), 10)).filter(Number.isFinite);
    return `${base}${String(used.length ? Math.max(...used) + 1 : 418).padStart(5, '0')}`;
  }
  function fillDefaults() {
    const f = $('#caseForm');
    f.cif.value = 'CIF-8842197';
    f.case_id.value = nextCaseId();
    f.customer.value = 'Orchid Meridian Trading';
    f.start_date.value = '2026-07-01';
    f.lookback_date.value = '2026-04-01';
    f.review_scope.value = 'Import activity and connected transactions';
    f.trigger.value = 'Police intelligence: the Singapore account of UBO Tan Wei Ming may be compromised. The ML trigger model flagged a trade anomaly on recent import payments.';
  }

  $('#caseForm').onsubmit = async e => {
    e.preventDefault();
    if (!intake.count('context') && !intake.sample) return toast('Stage at least one context document (or use the sample bundle).', true);
    const fd = intake.formData(new FormData(e.target));
    fd.append('use_sample', intake.sample ? 'true' : 'false');
    const hasPulls = arr(S.health && S.health.data_pulls).length > 0;
    if (hasPulls) { fd.append('pulls_selected', 'true'); pullPick.picked.forEach(n => fd.append('pulls', n)); }
    const btn = $('#submitCase');
    btn.disabled = true; btn.textContent = 'Uploading…';
    try {
      const c = await api('/api/cases', { method: 'POST', body: fd });
      const q = hasPulls ? pullPick.picked.size : 0;
      toast(`${c.id}: ${c.documents} documents uploaded · parsing${q ? ` and ${q} data pull(s)` : ''} started`);
      intake.clear();
      pullPick.touched = false;
      $('#newCasePanel').open = false;
      $('#intakeSummary').textContent = `last submitted ${c.id} · open for another case`;
      await refreshQueue(c.id);
      $('#caseForm').case_id.value = nextCaseId();
      renderIntakePulls();
    } catch (err) { toast(err.message, true); }
    finally { btn.disabled = false; btn.textContent = 'Upload & start parsing →'; }
  };
  $('#newCasePanel').addEventListener('toggle', () => { if ($('#newCasePanel').open) $('#intakeSummary').textContent = ''; });

  // ---------------------------------------------------------------- page 1: queue
  const REC = { 'PENDING REVIEW': 'pending', 'REQUEST DOCUMENTS': 'extra', 'FURTHER INVESTIGATION': 'extra', AGREE: 'approved',
    APPROVED: 'approved', ERROR: 'error', 'IN PROGRESS': 'progress', REGENERATE: 'ready' };

  function rowHtml(c, fresh) {
    const live = c.status === 'running' || c.status === 'queued';
    const sub = live ? `${c.documents} docs · ${clock(c.elapsed)} agent time` : c.versions ? `${c.versions} report version(s)` : `${c.documents} documents`;
    const work = `<button class="work-btn" data-work="${esc(c.id)}">${live ? '<span class="spinner"></span>' : '<span class="stage-dot"></span>'}${esc(c.stage || 'Agent work')}</button>`;
    let act = '';
    if (c.page) act += `<button class="btn ${!live && c.status !== 'approved' ? '' : 'secondary'} small" data-open="${esc(c.id)}">${!live && c.status === 'ready' ? 'Review →' : 'Detail'}</button>`;
    if (live) act += ` <button class="btn secondary small" data-stop="${esc(c.id)}">Stop</button>`;
    if (c.status === 'failed') act += ` <button class="btn dark small" data-retry="${esc(c.id)}">Retry</button>`;
    if (c.status === 'approved') act += ` <a class="btn secondary small" href="/api/cases/${enc(c.id)}/export.zip">ZIP</a>`;
    return `<tr class="${fresh ? 'fresh' : ''}">
      <td><span class="case-id">${esc(c.id)}</span><span class="case-sub">${esc(when(c.created))}</span></td>
      <td class="mono">${esc(c.cif)}</td><td>${esc(c.customer || '—')}</td>
      <td><span class="status ${esc(c.status)}"><i></i><div>${esc(c.label)}<small>${esc(sub)}</small></div></span></td>
      <td><span class="chip ${REC[c.recommendation] || ''}">${esc(c.recommendation)}</span></td>
      <td>${work}</td><td><div class="actions">${act}</div></td></tr>`;
  }
  function renderQueue(freshId) {
    const q = $('#cifSearch').value.trim().toLowerCase();
    const rows = S.cases.filter(c => !q || c.cif.toLowerCase().includes(q) || c.id.toLowerCase().includes(q));
    $('#queueBody').innerHTML = rows.length ? rows.map(c => rowHtml(c, c.id === freshId)).join('')
      : `<tr><td colspan="7" class="empty">${S.cases.length ? 'No case matches this search.' : 'No cases yet. Stage documents above - the sample bundle is a quick start.'}</td></tr>`;
  }
  $('#cifSearch').oninput = () => renderQueue();
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
        if (p && p.label !== c.label && !['running', 'queued'].includes(c.status)) toast(`${c.id}: ${c.label}`);
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

  const docLink = (d, name) => `<a href="/api/cases/${enc(d.id)}/docs/${enc(name)}" target="_blank" rel="noopener">${esc(name)}</a>`;
  const linkify = (d, s) => {
    s = String(s ?? '');
    const hit = arr(d.docs).find(x => s.includes(x.name));
    return hit ? esc(s).replace(esc(hit.name), docLink(d, hit.name)) : esc(s);
  };
  const strip = (el, items) => (el.innerHTML = items.map(([k, v]) => `<div><span>${esc(k)}</span><b title="${esc(v)}">${esc(v)}</b></div>`).join(''));
  const STATUS_ICON = { queued: '⏳', running: '<span class="spinner"></span>', done: '✓', failed: '✕', stopped: '■', staged: '·' };
  const jobState = s => `<span class="jstate ${esc(s)}">${STATUS_ICON[s] || '·'} ${esc(s)}</span>`;

  function renderJobs(d) {
    const items = arr(d.jobs).slice(-12).reverse().map(j => `<li class="${esc(j.status)}"><span>${STATUS_ICON[j.status] || '·'}</span>
      <div><b>${esc(j.label)}</b><small>${esc(j.role === 'query' ? `data pull${Object.keys(obj(obj(j.params).params)).length ? ` · ${Object.entries(obj(j.params.params)).map(([k, v]) => `${k}=${v}`).join(', ')}` : ''}` : j.params && j.params.feedback ? 'with analyst feedback' : j.params && j.params.instruction ? `revision: ${j.params.instruction}` : j.role)}${j.error ? ` · ${esc(j.error)}` : ''}</small></div>
      <time>${j.finished && j.started ? clock(j.finished - j.started) : j.status === 'running' && j.started ? clock(Date.now() / 1000 - j.started) : ''}</time></li>`).join('');
    $('#jobList2').innerHTML = items || '<li class="muted">No jobs yet.</li>';
  }

  // ---------------------------------------------------------------- page 2
  const more = new Stager($('#moreLanes'), { compact: true, contextRequired: false,
    onChange: st => { $('#uploadMore').disabled = !st.files.length; } });
  $('#uploadMore').onclick = async () => {
    const fd = more.formData();
    $('#uploadMore').disabled = true;
    try {
      const r = await api(`/api/cases/${enc(S.current)}/documents`, { method: 'POST', body: fd });
      toast(`${r.added.length} document(s) uploaded · extraction queued`);
      more.clear(); refreshDetail(true);
    } catch (e) { toast(e.message, true); $('#uploadMore').disabled = false; }
  };

  function flatInsights(d) {
    const rows = [];
    for (const doc of arr(d.docs)) {
      if (doc.role !== 'doc' || !doc.extraction) continue;
      for (const kv of arr(doc.extraction.key_values)) {
        const flags = arr(doc.corrections).filter(c => c.field === kv.field);
        rows.push({ doc: doc.name, status: doc.status, ...obj(kv), flags });
      }
    }
    return rows;
  }

  function renderPage2(d, scroll = true) {
    const ctxDocs = arr(d.docs).filter(x => x.role === 'context'), evDocs = arr(d.docs).filter(x => x.role === 'doc');
    strip($('#strip2'), [['Case', d.id], ['CIF', d.cif], ['Customer', d.customer || '—'],
      ['Documents', `${ctxDocs.length} context · ${evDocs.length} evidence`], ['Status', d.label]]);
    renderReady(d);

    // context summary
    const c = obj(d.context);
    const cbusy = ['queued', 'running'].includes(d.context_status);
    $('#contextMeta').innerHTML = cbusy ? `<span class="spinner"></span> CONTEXT AGENT ${esc(d.context_status.toUpperCase())}` : d.context ? `UPDATED ${esc(when(c.updated))}` : '';
    $('#contextBody').innerHTML = !d.context ? `<div class="placeholder">${cbusy ? 'The context agent is summarising the context documents…' : d.context_status === 'failed' ? `Context agent failed: ${esc(d.context_error)}` : 'No context summary yet.'}</div>` : `
      <div class="trigger-head"><span class="chip ready">${esc(c.trigger_type || 'TRIGGER')}</span><span class="muted">${esc(txt(c.trigger_source))}</span></div>
      <ul class="bullets">
        <li><b>Trigger event</b>${esc(txt(c.trigger_event))}</li>
        <li><b>Profile deviation</b>${esc(txt(c.profile_deviation))}</li>
        <li><b>Customer explanation</b>${esc(txt(c.customer_explanation) || 'None provided')}</li>
        <li><b>Routing rationale</b>${esc(txt(c.routing_rationale))}</li>
      </ul>
      <div class="two-col">
        <div><h3 style="margin-top:14px">MATCHED PARTIES</h3><div class="party-list">${arr(c.matched_parties).map(p => `<span class="party"><b>${esc(obj(p).name || txt(p))}</b>${esc(obj(p).role || '')}</span>`).join('') || '<span class="muted">—</span>'}</div></div>
        <div><h3 style="margin-top:14px">INITIAL EVIDENCE GAPS</h3><ul class="bullets">${arr(c.evidence_gaps).map(g => `<li>${esc(txt(g))}</li>`).join('') || '<li>None.</li>'}</ul></div>
      </div>
      <p class="caption" style="margin-top:10px">No risk conclusion is made at trigger stage.</p>`;
    const ctxForm = $('#contextBody');
    ctxForm.insertAdjacentHTML('beforeend', `<div class="inline-form" data-form="context">
      <label>Feedback to the context agent <small>(${ctxDocs.map(x => esc(x.name)).join(', ') || 'no context documents'})</small></label>
      <div class="row"><textarea class="input" rows="2" placeholder="e.g. the matched person is the UBO, not a former director; the alert date is 13 Aug"></textarea><button class="btn dark small">Re-summarise</button></div></div>`);
    const cf = $('[data-form="context"]', ctxForm);
    $('button', cf).onclick = () => sendFeedback({ target: 'context', note: $('textarea', cf).value }, $('button', cf));
    trackTyping(cf, 'context');

    renderData(d);

    // insights
    const rows = flatInsights(d);
    const low = rows.filter(r => num(r.confidence) < 80), flagged = rows.filter(r => r.flags.length);
    $('#insightMeta').textContent = `${rows.length} VALUES · ${low.length} LOW CONFIDENCE · ${flagged.length} FLAGGED`;
    $$('#insightFilter .seg').forEach(b => b.classList.toggle('active', b.dataset.filter === S.insightFilter));
    const shown = S.insightFilter === 'low' ? low : S.insightFilter === 'flagged' ? flagged : rows;
    const parsing = evDocs.filter(x => ['queued', 'running'].includes(x.status));
    $('#insights').innerHTML = `<div class="insight-head"><span>Field · document</span><span>Extracted value</span><span>Confidence</span><span>Location</span><span></span></div>` +
      parsing.map(x => `<div class="insight-row pending"><div class="fname">${esc(x.name)}</div><div class="muted"><span class="spinner"></span> doc agent ${esc(x.status)}…</div><div></div><div></div><div></div></div>`).join('') +
      (shown.length ? shown.map((r, i) => {
        const conf = Math.max(0, Math.min(100, num(r.confidence) || 0));
        const fl = r.flags[r.flags.length - 1];
        const key = `kv:${r.doc}:${r.field}`;
        return `<div class="insight-row ${conf < 80 ? 'low' : ''} ${fl ? 'edited' : ''}">
          <div class="fname">${esc(r.field)}<small class="docname">${esc(r.doc)}</small>${fl ? `<small>${r.status === 'done' ? 'ANALYST FEEDBACK APPLIED' : 'RE-EXTRACTING'}</small>` : ''}</div>
          <div class="val">${esc(txt(r.value))}${fl && fl.analyst_value ? `<div class="analyst">Analyst: ${esc(fl.analyst_value)}</div>` : ''}</div>
          <div class="conf"><b>${conf}%</b><div class="bar ${conf < 70 ? 'lowc' : conf < 85 ? 'mid' : ''}"><i style="width:${conf}%"></i></div></div>
          <div class="src">${esc(r.location || '')}</div>
          <div><button class="btn secondary small" data-flag="${i}" title="This value looks wrong">Flag</button></div>
          ${S.openForms.has(key) ? flagForm(i, r) : ''}</div>`;
      }).join('') : `<div class="empty">${rows.length ? 'No values in this filter.' : parsing.length ? '' : 'No key values extracted yet.'}</div>`);
    $$('#insights [data-flag]').forEach(b => (b.onclick = () => {
      const r = shown[+b.dataset.flag], key = `kv:${r.doc}:${r.field}`;
      S.openForms.has(key) ? S.openForms.delete(key) : S.openForms.add(key);
      renderPage2(S.detail, false);
    }));
    $$('#insights [data-send-flag]').forEach(b => (b.onclick = () => {
      const r = shown[+b.dataset.sendFlag], f = b.closest('.inline-form');
      sendFeedback({ target: r.doc, field: r.field, value: $('[name=value]', f).value, note: $('[name=note]', f).value }, b, `kv:${r.doc}:${r.field}`);
    }));
    $$('#insights [data-cancel]').forEach(b => (b.onclick = () => { S.openForms.delete(b.dataset.cancel); renderPage2(S.detail, false); }));

    // documents
    $('#docMeta').textContent = `${arr(d.docs).length} FILES · ${evDocs.reduce((n, x) => n + arr(obj(x.extraction).anomalies).length, 0)} ANOMALIES`;
    $('#docGrid').innerHTML = arr(d.docs).map((x, i) => {
      const e = obj(x.extraction), key = `doc:${x.name}`;
      const kvs = arr(e.key_values).slice(0, 10), an = arr(e.anomalies);
      return `<article class="doc-card"><header><div><b>${docLink(d, x.name)}</b><small>${esc(e.document_type || (x.role === 'context' ? 'context document' : ''))}${e.reference ? ` · ${esc(e.reference)}` : ''}</small></div>
          <span class="chip ${x.role === 'context' ? 'pending' : ''}">${x.role === 'context' ? 'CONTEXT' : 'EVIDENCE'}</span></header>
        <div class="doc-state">${x.role === 'context' ? '<span class="muted">Summarised by the context agent (Trigger Context)</span>' : jobState(x.status)}${x.error ? ` <span class="flag">${esc(x.error)}</span>` : ''}</div>
        ${e.summary ? `<p class="doc-summary">${esc(txt(e.summary))}</p>` : ''}
        ${kvs.length ? `<dl>${kvs.map(k => `<dt>${esc(obj(k).field)}</dt><dd>${esc(txt(obj(k).value))}</dd>`).join('')}</dl>` : ''}
        ${an.length ? `<div class="anomalies">${an.map(a => `<div class="flag">${esc(txt(a))}</div>`).join('')}</div>` : ''}
        ${arr(x.corrections).length ? `<div class="corrections">${arr(x.corrections).map(cc => `<div>✎ ${esc(cc.field ? `${cc.field}: ` : '')}${esc(cc.analyst_value || cc.note)}</div>`).join('')}</div>` : ''}
        <footer>${S.openForms.has(key) ? `<div class="inline-form" data-docform="${i}"><textarea class="input" rows="2" placeholder="What did the agent miss or get wrong in this document?"></textarea>
            <div class="row"><button class="btn dark small" data-redo="${i}">Re-extract with note</button><button class="btn secondary small" data-cancel="${esc(key)}">Cancel</button></div></div>`
          : `<button class="btn link" data-docnote="${i}">${x.role === 'context' ? 'Note for the context agent' : 'Re-extract with a note'}</button>`}</footer></article>`;
    }).join('') || '<div class="placeholder">No documents.</div>';
    $$('#docGrid [data-docnote]').forEach(b => (b.onclick = () => { S.openForms.add(`doc:${arr(d.docs)[+b.dataset.docnote].name}`); renderPage2(S.detail, false); }));
    $$('#docGrid [data-redo]').forEach(b => (b.onclick = () => {
      const x = arr(d.docs)[+b.dataset.redo];
      sendFeedback({ target: x.name, note: $('textarea', b.closest('.inline-form')).value }, b, `doc:${x.name}`);
    }));
    $$('#docGrid [data-cancel]').forEach(b => (b.onclick = () => { S.openForms.delete(b.dataset.cancel); renderPage2(S.detail, false); }));

    renderJobs(d);
    renderExtras($('#extraList2'), d);
    const pending = arr(d.jobs).filter(j => BUSY(j.status) && ['doc', 'context', 'query'].includes(j.role)).length;
    $('#genHint2').textContent = pending ? `${pending} extraction / data job(s) still running - ask now and the report agent starts when they finish.` : d.reports.length ? `Latest: v${d.reports[d.reports.length - 1].version}${d.stale ? ' (out of date)' : ''}.` : '';
    $('#genReport2').textContent = pending ? 'Generate TER report when ready →' : d.reports.length ? `Regenerate TER report (v${d.reports.length + 1}) →` : 'Generate TER report →';
    if (scroll) show(2);
  }

  // ---------------------------------------------------------------- page 2: readiness and data pulls
  const shortProgress = s => String(s || '').replace(/^querying [^·]*·\s*/, '');
  function renderReady(d) {
    const ev = arr(d.docs).filter(x => x.role === 'doc'), evBusy = ev.filter(x => BUSY(x.status)).length;
    const data = arr(d.data).filter(p => p.status), dBusy = data.filter(p => BUSY(p.status));
    const run = dBusy.find(p => p.status === 'running'), cs = d.context_status;
    const item = (label, state, text) => `<div class="ready ${state}"><i>${state === 'busy' ? '<span class="spinner"></span>' : state === 'ok' ? '✓' : state === 'bad' ? '✕' : '·'}</i><span>${esc(label)}</span><b>${esc(text)}</b></div>`;
    const n = evBusy + dBusy.length + (BUSY(cs) ? 1 : 0);
    $('#ready2').innerHTML = [
      BUSY(cs) ? item('Context', 'busy', 'summarising') : d.context ? item('Context', 'ok', 'ready') : item('Context', cs === 'failed' ? 'bad' : '', cs === 'failed' ? 'failed' : 'none'),
      item('Documents', evBusy ? 'busy' : ev.some(x => x.status === 'failed') ? 'bad' : ev.length ? 'ok' : '', ev.length ? `${ev.length - evBusy}/${ev.length} done` : 'none'),
      item('Data', dBusy.length ? 'busy' : data.some(p => p.status === 'failed') ? 'bad' : data.length ? 'ok' : '', data.length ? `${data.length - dBusy.length}/${data.length} done${run ? ` · ${run.label} ${shortProgress(run.progress)}` : ''}` : 'none'),
    ].join('') + `<div class="ready-note">${n ? `${n} job(s) running. Review what is here; the TER report can be asked for now and starts when they finish.` : 'All inputs are in: ready for the TER report.'}</div>`;
  }

  const miniTable = (title, cols, rows) => `<div class="mini">${title ? `<b>${esc(title)}</b>` : ''}<div class="table-wrap"><table class="grid mini-grid">
    <thead><tr>${arr(cols).map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
    <tbody>${arr(rows).map(r => `<tr>${arr(r).map(v => `<td>${esc(v)}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${arr(cols).length || 1}" class="empty">No rows.</td></tr>`}</tbody></table></div></div>`;

  function dataCard(d, p, i) {
    const r = obj(p.result), live = BUSY(p.status), key = `data:${p.name}`, kv = arr(r.key_values);
    const dated = arr(p.binds).some(b => b === 'lookback_date' || b === 'start_date');
    const params = Object.entries(obj(r.params)).map(([k, v]) => `${k}=${v}`).join(' · ');
    const shown = { ...obj(r.params), ...obj(p.params) };
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
        : `<button class="btn ${p.result ? 'secondary' : 'dark'} small" data-pull-run="${i}">${p.result ? 'Re-run' : 'Run'}</button>${dated ? ` <button class="btn link" data-pull-edit="${i}">Change period</button>` : ''}`}
        ${p.result ? `<a class="btn link" href="/api/cases/${enc(d.id)}/data/${enc(p.name)}">CSV</a>` : ''}</footer>
      ${S.openForms.has(key) && !live ? `<div class="inline-form"><div class="row">
        <label>From <input class="input" type="date" name="lookback_date" value="${esc(shown.lookback_date || d.lookback_date)}"></label>
        <label>To <input class="input" type="date" name="start_date" value="${esc(shown.start_date || d.start_date)}"></label>
        <button class="btn dark small" data-pull-send="${i}">Run for this period</button><button class="btn secondary small" data-cancel="${esc(key)}">Cancel</button></div></div>` : ''}
    </article>`;
  }

  function renderData(d) {
    const grid = $('#dataGrid'), list = arr(d.data);
    const busy = list.filter(p => BUSY(p.status)).length, done = list.filter(p => p.result).length;
    $('#dataMeta').innerHTML = busy ? `<span class="spinner"></span> ${busy} RUNNING · ${done} DONE` : `${done} OF ${list.length} PULLED`;
    grid.innerHTML = list.map((p, i) => dataCard(d, p, i)).join('') || '<div class="placeholder">No data pulls configured (studio.yaml → data_pulls).</div>';
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
      const p = list[+b.dataset.pullSend], params = { ...obj(p.params) };
      $$('input[name]', b.closest('.inline-form')).forEach(x => { if (x.value) params[x.name] = x.value; });
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

  function flagForm(i, r) {
    return `<div class="inline-form flag-form"><div class="row">
      <input class="input" name="value" placeholder="Correct value (if you know it)">
      <input class="input" name="note" placeholder="What is wrong? e.g. amount is per carton, not the total">
      <button class="btn dark small" data-send-flag="${i}">Send to doc agent</button><button class="btn secondary small" data-cancel="kv:${esc(r.doc)}:${esc(r.field)}">Cancel</button></div></div>`;
  }

  function trackTyping(form, key) {
    const t = $('textarea', form);
    t.addEventListener('input', () => (t.value ? S.openForms.add(key) : S.openForms.delete(key)));
  }

  async function sendFeedback(body, btn, formKey) {
    if (!String(body.note || '').trim() && !String(body.value || '').trim()) return toast('Say what is wrong first.', true);
    btn.disabled = true;
    try {
      await post(`/api/cases/${enc(S.current)}/feedback`, body);
      toast(body.target === 'context' ? 'Context agent re-summarising with your feedback' : `${body.target}: re-extraction queued`);
      if (formKey) S.openForms.delete(formKey);
      S.openForms.delete('context');
      refreshDetail(true);
    } catch (e) { toast(e.message, true); btn.disabled = false; }
  }

  $$('#insightFilter .seg').forEach(b => (b.onclick = () => { S.insightFilter = b.dataset.filter; renderPage2(S.detail, false); }));

  function renderExtras(el, d) {
    const ex = obj(d.extras);
    if (S.extrasPicked === null) S.extrasPicked = new Set(Object.entries(ex).filter(([, v]) => v.default).map(([k]) => k));
    el.innerHTML = Object.keys(ex).length ? Object.entries(ex).map(([k, v]) => `<label class="extra"><input type="checkbox" data-extra="${esc(k)}" ${S.extrasPicked.has(k) ? 'checked' : ''}>
      <span><b>${esc(v.label)}</b><small>${esc(v.remote ? 'external agent' : 'local agent')}${v.status ? ` · last run ${esc(v.status)}` : ''}</small></span></label>`).join('')
      : '<p class="caption">No extra agents configured (studio.yaml).</p>';
    $$('[data-extra]', el).forEach(c => (c.onchange = () => (c.checked ? S.extrasPicked.add(c.dataset.extra) : S.extrasPicked.delete(c.dataset.extra))));
  }

  async function requestReport(instruction = '') {
    try {
      await post(`/api/cases/${enc(S.current)}/report`, { extras: [...(S.extrasPicked || [])], instruction });
      toast(instruction ? 'Revision queued - the report agent is on it' : 'TER report queued');
      S.version = null;
      await refreshDetail(true);
      renderPage3(S.detail);
    } catch (e) { toast(e.message, true); }
  }
  $('#genReport2').onclick = () => requestReport();

  // ---------------------------------------------------------------- page 3
  const scoreColor = s => (s >= 85 ? 'var(--red)' : s >= 70 ? 'var(--amber)' : '#9aa0a6');

  function renderPage3(d, scroll = true) {
    const reports = arr(d.reports);
    const reportJobs = arr(d.jobs).filter(j => j.role === 'report' || j.role === 'extra');
    const busy = reportJobs.filter(j => ['queued', 'running'].includes(j.status));
    if (S.version === null || !reports.some(r => r.version === S.version)) S.version = reports.length ? reports[reports.length - 1].version : null;
    const rep = reports.find(r => r.version === S.version);
    const r = obj(rep && rep.data);
    const latest = reports.length && S.version === reports[reports.length - 1].version;

    $('#versionSel').innerHTML = reports.map(x => `<option value="${x.version}" ${x.version === S.version ? 'selected' : ''}>v${x.version}${d.approved && d.approved.version === x.version ? ' · approved' : ''}</option>`).join('') || '<option>—</option>';
    $('#versionSel').disabled = !reports.length;
    $('#p3Title').textContent = rep ? `TER report v${rep.version}${d.approved && d.approved.version === rep.version ? ' · approved' : ''}` : 'Trigger Event Report';
    strip($('#strip3'), [['Case', d.id], ['Customer', d.customer || txt(obj(r.background).entity) || '—'],
      ['Confidence', Number.isFinite(num(r.confidence)) ? `${Math.round(num(r.confidence))}%` : '—'],
      ['Key risks', String(arr(r.key_risks).length)], ['Versions', String(reports.length)]]);

    const banner = $('#staleBanner');
    if (busy.length) {
      const run = busy.find(j => j.status === 'running');
      const inputs = arr(d.jobs).filter(j => BUSY(j.status) && ['doc', 'context', 'query'].includes(j.role)).length;
      banner.hidden = false;
      banner.className = 'banner working';
      banner.innerHTML = `<span class="spinner"></span><div><b>${esc(run ? run.label : 'Report jobs queued')}</b> ${run && run.params.instruction ? `revising: “${esc(run.params.instruction)}”` : run ? 'drafting the next version' : inputs ? `waiting for ${inputs} extraction / data job(s)` : `waiting for ${busy.length} job(s)`}
        <small>${d.live && d.live.text ? esc(d.live.text.slice(-220)) : 'You can keep working - the page updates when it is ready.'}</small></div><button class="btn secondary small" data-open-work>Watch</button>`;
    } else if (d.stale && latest) {
      banner.hidden = false;
      banner.className = 'banner';
      banner.innerHTML = `<div><b>New evidence or corrections since v${rep.version}.</b> The report does not include them yet.</div><button class="btn small" id="regenBtn">Regenerate v${reports.length + 1}</button>`;
      $('#regenBtn').onclick = () => requestReport();
    } else banner.hidden = true;

    $('#reportView').innerHTML = rep ? reportHtml(d, rep, r) : `<div class="placeholder">${busy.length ? 'The report agent is drafting the first version…' : 'No report yet. Generate it from Page 2 or below.'}</div>`;
    renderNext(d, rep, r, busy.length > 0);
    if (scroll) show(3);
  }
  $('#versionSel').onchange = e => { S.version = +e.target.value; renderPage3(S.detail, false); };

  function reportHtml(d, rep, r) {
    const trig = obj(r.trigger), bg = obj(r.background), rec = obj(r.recommendation);
    const risks = [...arr(r.key_risks)].sort((a, b) => num(b.score) - num(a.score));
    return `<div class="report">
      <div class="report-head"><div><span class="eyebrow">Trigger Event Report · CONFIDENTIAL</span><h1>${esc(r.title || d.customer || d.id)}</h1>
        <p class="muted">${esc(r.typology || '')}</p></div>
        <div class="report-meta"><span>${esc(d.id)}</span><span>${esc(d.cif)}</span><span>v${rep.version} · ${esc(when(rep.created))}</span></div></div>
      ${rep.instruction ? `<div class="fold-note">Revision instruction: ${esc(rep.instruction)}${r.changes ? ` <br><b>Changes:</b> ${esc(txt(r.changes))}` : ''}</div>` : ''}
      <h2>Executive narrative</h2><p>${esc(txt(r.executive_narrative))}</p>
      <h2>Trigger</h2><div class="kv">
        <div><span>Trigger type</span><b>${esc(txt(trig.type) || '—')}</b></div><div><span>Trigger event</span><b>${esc(txt(trig.event) || '—')}</b></div>
        <div><span>Primary discrepancy</span><b>${esc(txt(trig.primary_discrepancy) || '—')}</b></div><div><span>Context gap</span><b>${esc(txt(trig.context_gap) || '—')}</b></div></div>
      <h2>Background</h2><div class="kv">${[['Entity', bg.entity], ['Nature of business', bg.nature_of_business], ['Accounts', bg.accounts], ['Directors / UBO', bg.owners_directors], ['Expected activity', bg.expected_activity], ['Major counterparty', bg.major_counterparty]]
        .map(([k, v]) => `<div><span>${k}</span><b>${linkify(d, txt(v)) || '—'}</b></div>`).join('')}</div>
      <h2>Review</h2><h3>KYC review</h3><p>${linkify(d, txt(r.kyc_review))}</p>
      <h3>Transaction review</h3><div class="table-wrap"><table class="grid"><thead><tr><th>Date</th><th>From</th><th>To</th><th>Amount</th><th>Review result</th></tr></thead>
        <tbody>${arr(r.transactions).map(t => `<tr><td class="mono">${esc(obj(t).date)}</td><td>${esc(obj(t).from)}</td><td>${esc(obj(t).to)}</td><td class="mono">${esc(obj(t).amount)}</td><td>${esc(obj(t).result)}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">—</td></tr>'}</tbody></table></div>
      <h2>Justification and key risks</h2><div class="risk-list">${risks.map((k, i) => {
        const s = Math.max(0, Math.min(100, num(k.score) || 0));
        return `<article class="risk"><div class="score" style="--v:${s};--c:${scoreColor(s)}"><b>${s}</b></div><div>
          <div class="kicker">${esc(k.id || `KR-0${i + 1}`)} · KEY RISK</div><h4>${esc(k.title)}</h4><p>${esc(txt(k.reason))}</p>
          ${k.evidence ? `<div class="evidence"><b>EVIDENCE</b>${linkify(d, txt(k.evidence))}</div>` : ''}${k.gap ? `<div class="gap"><b>GAP</b>${esc(txt(k.gap))}</div>` : ''}</div></article>`;
      }).join('') || '<p class="muted">No key risks.</p>'}</div>
      <h2>Recommended next step</h2><div class="rec-card ${/further/i.test(rec.next_step || '') ? '' : 'agree'}"><span>${esc((rec.next_step || '—').toUpperCase())}</span><b>${esc(rec.scope || '')}</b><p>${esc(txt(rec.rationale))}</p></div>
    </div>`;
  }

  function renderNext(d, rep, r, busy) {
    const body = $('#nextBody');
    const rec = obj(r.recommendation);
    const reqs = arr(r.document_requests), qs = arr(r.open_questions);
    const approvedThis = d.approved && rep && d.approved.version === rep.version;
    body.innerHTML = `
      ${rep ? `<div class="rec-card ${/further/i.test(rec.next_step || '') ? '' : 'agree'}"><span>AGENT SUGGESTS</span><b>${esc(rec.next_step || '—')}</b><p>${esc(reqs.length ? `Request ${reqs.length} document(s) from the client to close the gaps.` : rec.scope || '')}</p></div>` : ''}
      <section><h3>1 · REQUEST FROM THE CLIENT</h3>
        ${reqs.length ? `<ul class="req-list">${reqs.map((q, i) => `<li><div><b>${esc(obj(q).document || txt(q))}</b><small>${esc(obj(q).reason || '')}</small></div>
          <label class="btn secondary small">Upload<input type="file" multiple hidden data-req="${i}"></label></li>`).join('')}</ul>` : '<p class="caption">No documents requested by the agent.</p>'}
        <label class="btn secondary small" style="margin-top:8px">Upload other evidence<input type="file" multiple hidden data-req="other"></label>
        <p class="caption">Uploads go to the doc agent; Page 2 opens while they are extracted, then regenerate the report.</p></section>
      <section><h3>2 · REFINE THE REPORT</h3>
        ${qs.length ? `<div class="q-chips">${qs.map((q, i) => `<button class="q-chip" data-q="${i}" title="Add to the instruction">${esc(txt(q))}</button>`).join('')}</div>` : ''}
        <textarea class="input" id="instruction" rows="4" placeholder="e.g. clarify whether the 301,760 payment matches the invoice; shorten the narrative; explain KR-02 evidence"></textarea>
        <button class="btn dark" id="reviseBtn" style="width:100%;margin-top:8px" ${rep && !busy ? '' : 'disabled'}>Revise → v${arr(d.reports).length + 1}</button></section>
      <section><h3>3 · EXTRA AGENTS</h3><div class="extra-list" id="extraList3"></div>
        <button class="btn secondary" id="regenNow" style="width:100%;margin-top:8px" ${busy ? 'disabled' : ''}>${rep ? 'Regenerate from current evidence' : 'Generate TER report'}</button></section>
      <section><h3>4 · APPROVE</h3>
        <div class="btn-row"><button class="btn green" id="approveBtn" ${rep && !approvedThis && !busy ? '' : 'disabled'}>${approvedThis ? `v${rep.version} approved` : rep ? `Approve v${rep.version}` : 'Approve'}</button>
          <a class="btn secondary" href="/api/cases/${enc(d.id)}/export.zip">Case ZIP</a></div>
        <button class="btn link" id="printBtn" style="margin-top:6px">Print / save as PDF</button>
        ${d.stale && rep ? '<p class="caption" style="color:var(--amber)">This version predates the latest evidence.</p>' : ''}</section>
      <section><h3>VERSIONS</h3><ul class="job-list">${arr(d.reports).slice().reverse().map(v => `<li class="done"><span>${d.approved && d.approved.version === v.version ? '✓' : 'v'}</span>
        <div><b>v${v.version} · ${esc(when(v.created))}</b><small>${esc(v.instruction ? `revision: ${v.instruction}` : `new draft${arr(v.extras).length ? ` with ${v.extras.join(', ')}` : ''}`)}</small></div></li>`).join('') || '<li class="muted">None yet.</li>'}</ul></section>`;
    renderExtras($('#extraList3'), d);
    const ins = $('#instruction');
    ins.addEventListener('input', () => (ins.value ? S.openForms.add('instruction') : S.openForms.delete('instruction')));
    $$('[data-q]', body).forEach(b => (b.onclick = () => { ins.value = (ins.value ? `${ins.value}\n` : '') + `Clarify: ${b.textContent}`; S.openForms.add('instruction'); ins.focus(); }));
    $('#reviseBtn').onclick = () => {
      if (!ins.value.trim()) return toast('Write what to change or clarify.', true);
      S.openForms.delete('instruction');
      requestReport(ins.value.trim());
    };
    $('#regenNow').onclick = () => requestReport();
    $('#approveBtn').onclick = async () => {
      try { await post(`/api/cases/${enc(d.id)}/approve`, { version: rep.version }); toast(`v${rep.version} approved`); refreshDetail(true); }
      catch (e) { toast(e.message, true); }
    };
    $('#printBtn').onclick = () => window.print();
    $$('[data-req]', body).forEach(inp => (inp.onchange = async () => {
      if (!inp.files.length) return;
      const fd = new FormData();
      for (const f of inp.files) {
        if (isVideo(f.name) || isLegacy(f.name)) { toast(`${f.name}: unsupported format`, true); return; }
        fd.append('files', f, f.name); fd.append('roles', 'doc');
      }
      try {
        const res = await api(`/api/cases/${enc(d.id)}/documents`, { method: 'POST', body: fd });
        toast(`${res.added.join(', ')} uploaded · doc agent extracting`);
        await refreshDetail(true);
        renderPage2(S.detail);
      } catch (e) { toast(e.message, true); }
    }));
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
      $('#awStop').hidden = !['running', 'queued'].includes(r.view.status);
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
    await refreshHealth();
    await refreshQueue();
    fillDefaults();
    renderIntakePulls();
    if (S.cases.length) $('#newCasePanel').open = false;
    const m = location.hash.match(/^#case\/([^/]+)(?:\/(\d))?$/);
    if (m) openCase(decodeURIComponent(m[1]), m[2] ? +m[2] : undefined).catch(e => toast(e.message, true));
    setInterval(refreshQueue, 2000);
    setInterval(refreshHealth, 8000);
    setInterval(() => { if (S.current && S.detail && arr(S.detail.jobs).some(j => ['queued', 'running'].includes(j.status))) refreshDetail(); }, 4000);
  }
  boot();
})();
