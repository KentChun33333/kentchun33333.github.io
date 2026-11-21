/* Breezeman: chat over kentc-agent. One WebSocket per open chat (/ws/<key>); REST for tree, uploads, chats,
   transcript and context. No build step. */
(() => {
  'use strict';

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTok = n => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n || 0));
  const fmtSize = n => (n == null ? '' : n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1048576).toFixed(1)} MB`);
  const clock = t => new Date(t * 1000).toLocaleTimeString([], { hour12: false });
  const ago = t => {
    const s = Date.now() / 1000 - t;
    return s < 60 ? 'just now' : s < 3600 ? `${Math.floor(s / 60)}m ago` : s < 86400 ? `${Math.floor(s / 3600)}h ago` : new Date(t * 1000).toLocaleDateString();
  };
  const oneLine = (s, n = 120) => { const t = String(s || '').replace(/\s+/g, ' ').trim(); return t.length > n ? `${t.slice(0, n)}…` : t; };
  const pretty = v => { try { return typeof v === 'string' ? JSON.stringify(JSON.parse(v), null, 2) : JSON.stringify(v, null, 2); } catch { return String(v); } };
  const argLine = args => {
    if (typeof args === 'string') { try { args = JSON.parse(args); } catch { return oneLine(args, 90); } }
    if (!args || typeof args !== 'object') return String(args ?? '');
    const first = args.command ?? args.path ?? args.query ?? args.url ?? Object.values(args)[0];
    return oneLine(typeof first === 'string' ? first : JSON.stringify(first ?? ''), 90);
  };
  const SUB_AGENTS = ['document', 'subagent', 'web', 'web-screen'];

  // ---------------------------------------------------------------- API
  const params = new URLSearchParams(location.search);
  let token = params.get('token') || sessionStorage.getItem('kentc-breezeman-token') || '';
  if (params.get('token')) {
    sessionStorage.setItem('kentc-breezeman-token', token);
    history.replaceState(null, '', location.pathname + location.hash);
  }
  async function api(path, opts = {}, retried = false) {
    const headers = new Headers(opts.headers || {});
    if (token) headers.set('x-api-token', token);
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401 && !retried) {
      const entered = prompt('Breezeman API token');
      if (entered) {
        token = entered;
        sessionStorage.setItem('kentc-breezeman-token', token);
        return api(path, opts, true);
      }
    }
    const body = res.headers.get('content-type')?.includes('json') ? await res.json() : await res.text();
    if (!res.ok) {
      const err = new Error(typeof body === 'object' ? body.detail || res.statusText : body || res.statusText);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  let toastTimer;
  function toast(msg, err = false) {
    const t = $('#toast');
    t.textContent = msg;
    t.className = `toast show${err ? ' err' : ''}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = 'toast'; }, err ? 5200 : 2600);
  }

  // ---------------------------------------------------------------- markdown (escaped first: model text never becomes HTML)
  function inline(s) {
    const codes = [];
    s = s.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
    s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>')
      .replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[i]}</code>`);
  }
  const LIST = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
  const TABLE_RULE = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;
  const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => inline(c.trim()));
  function blocks(lines) {
    const out = [];
    let i = 0;
    const isBlockStart = l => /^\s*```/.test(l) || /^#{1,6}\s/.test(l) || /^\s*&gt;/.test(l) || LIST.test(l);
    while (i < lines.length) {
      const l = lines[i];
      let m;
      if (/^\s*```/.test(l)) {
        const lang = l.replace(/^\s*```/, '').trim().toLowerCase();
        const buf = [];
        i++;
        while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) buf.push(lines[i++]);
        i++;
        const previewBtn = (lang === 'html' || lang === 'htm') ? '<button class="preview-html" type="button">preview</button>' : '';
        out.push(`<pre><div class="pre-actions">${previewBtn}<button class="copy" type="button">copy</button></div><code>${buf.join('\n')}</code></pre>`);
      } else if (!l.trim()) {
        i++;
      } else if ((m = l.match(/^(#{1,6})\s+(.*)$/))) {
        const n = Math.min(4, m[1].length);
        out.push(`<h${n}>${inline(m[2])}</h${n}>`);
        i++;
      } else if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(l)) {
        out.push('<hr>');
        i++;
      } else if (/^\s*&gt;/.test(l)) {
        const buf = [];
        while (i < lines.length && /^\s*&gt;/.test(lines[i])) buf.push(lines[i++].replace(/^\s*&gt;\s?/, ''));
        out.push(`<blockquote>${blocks(buf)}</blockquote>`);
      } else if (l.includes('|') && i + 1 < lines.length && TABLE_RULE.test(lines[i + 1])) {
        const head = cells(l);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
        out.push(`<table><thead><tr>${head.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${
          rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
      } else if ((m = l.match(LIST))) {
        const ordered = /\d/.test(m[2]);
        const items = [];
        while (i < lines.length && (m = lines[i].match(LIST))) {
          const depth = Math.floor(m[1].replace(/\t/g, '  ').length / 2);
          let text = m[3];
          i++;
          while (i < lines.length && lines[i].trim() && !LIST.test(lines[i]) && !isBlockStart(lines[i]) && /^\s+/.test(lines[i])) text += ` ${lines[i++].trim()}`;
          items.push(`<li${depth ? ` style="margin-left:${depth * 16}px"` : ''}>${inline(text)}</li>`);
        }
        out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`);
      } else {
        const buf = [];
        while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i]) &&
               !(lines[i].includes('|') && i + 1 < lines.length && TABLE_RULE.test(lines[i + 1]))) buf.push(inline(lines[i++]));
        out.push(`<p>${buf.join('<br>')}</p>`);
      }
    }
    return out.join('');
  }
  const md = src => blocks(esc(src).split('\n'));
  document.addEventListener('click', e => {
    const copyBtn = e.target.closest('pre .copy');
    if (copyBtn) {
      const code = copyBtn.closest('pre')?.querySelector('code')?.textContent ?? '';
      navigator.clipboard?.writeText(code).then(() => toast('Copied'));
      return;
    }
    const pvBtn = e.target.closest('pre .preview-html');
    if (pvBtn) {
      const html = pvBtn.closest('pre')?.querySelector('code')?.textContent ?? '';
      showHtmlDialog('HTML output', fmtSize(html.length), html);
    }
  });

  // ---------------------------------------------------------------- state
  const S = {
    key: null, ws: null, wsWanted: false, retry: 0, busy: null, seq: 0, tokens: 0, window: 0,
    attachments: [], selectedDir: '', openDirs: new Set(JSON.parse(localStorage.getItem('breezeman-open-dirs') || '[]')),
    block: null, lastUserText: null, chats: [], tasks: [], studios: [], activeTaskId: null, activeStudioId: null, ctx: null, ctxStale: true, unread: 0,
    pending: {}, lastFeed: null, liveFilter: 'all', ctxFilter: 'all', runStart: 0, skill: null, skills: null,
  };

  // ---------------------------------------------------------------- panels
  function setPanel(side, open) {
    const panel = side === 'left' ? $('#leftPanel') : $('#rightPanel');
    panel.classList.toggle('closed', !open);
    $('#shell').classList.toggle(`${side}-closed`, !open);
    localStorage.setItem(`breezeman-${side}`, open ? '1' : '0');
    const fold = side === 'left' ? $('#leftFold') : $('#rightFold');
    fold.textContent = side === 'left' ? (open ? '«' : '»') : (open ? '»' : '«');
    if (side === 'right' && open) { clearUnread(); if (activeTab() === 'context' && S.ctxStale) loadContext(); }
  }
  const panelOpen = side => !(side === 'left' ? $('#leftPanel') : $('#rightPanel')).classList.contains('closed');
  $('#leftFold').onclick = () => setPanel('left', !panelOpen('left'));
  $('#rightFold').onclick = () => setPanel('right', !panelOpen('right'));
  $$('.rail-label').forEach(r => { r.onclick = () => setPanel(r.closest('.side').id === 'leftPanel' ? 'left' : 'right', true); });

  const activeTab = () => $('.tab.active').dataset.tab;
  function showTab(tab) {
    $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    $('#liveTab').hidden = tab !== 'live';
    $('#contextTab').hidden = tab !== 'context';
    $('#skillsTab').hidden = tab !== 'skills';
    $('#scheduleTab').hidden = tab !== 'schedule';
    if (tab === 'live') clearUnread();
    if (tab === 'context' && S.ctxStale) loadContext();
    if (tab === 'skills') loadSkills();
    if (tab === 'schedule') renderSchedule();
  }
  $$('.tab').forEach(t => { t.onclick = () => showTab(t.dataset.tab); });
  function bumpUnread() {
    if (panelOpen('right') && activeTab() === 'live') return;
    S.unread++;
    $('#liveBadge').hidden = false;
    $('#liveBadge').textContent = S.unread > 99 ? '99+' : S.unread;
  }
  function clearUnread() { if (activeTab() !== 'live') return; S.unread = 0; $('#liveBadge').hidden = true; }
  setPanel('left', localStorage.getItem('breezeman-left') !== '0');
  setPanel('right', localStorage.getItem('breezeman-right') !== '0');

  // ---------------------------------------------------------------- health
  async function health() {
    const pill = $('#modelPill');
    try {
      const h = await api('/api/health');
      $('#wsName').textContent = h.workspace;
      $('#wsName').title = h.workspace;
      if (h.model.online) {
        pill.className = 'pill ok';
        pill.lastElementChild.textContent = `${h.model.id} · ${fmtTok(h.model.context)}`;
        pill.title = 'LLM server online';
        if (!S.window) { S.window = h.model.context; meter(); }
      } else {
        pill.className = 'pill bad';
        pill.lastElementChild.textContent = 'model offline';
        pill.title = h.model.error;
      }
    } catch (e) {
      pill.className = 'pill bad';
      pill.lastElementChild.textContent = 'server unreachable';
      pill.title = e.message;
    }
  }

  // ---------------------------------------------------------------- task manager
  const taskQuery = (prefix = '?') => (
    S.activeStudioId ? `${prefix}task=${encodeURIComponent('studio:' + S.activeStudioId)}`
    : S.activeTaskId ? `${prefix}task=${encodeURIComponent(S.activeTaskId)}` : ''
  );
  function syncWorkspaceHeader(task) {
    const label = $('#wsLabel');
    if (label) label.textContent = task ? `WORKSPACE · ${task.folder}` : 'WORKSPACE';
  }
  function renderTasks() {
    const tbody = $('#taskList');
    if (!S.tasks.length && !S.studios.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="task-empty">No tasks yet. Click <b>+ Task</b> or <b>+ Studio</b> to start.</td></tr>';
      return;
    }
    const studioRows = S.studios.map(st => {
      const current = st.id === S.activeStudioId;
      return `<tr class="studio-row${current ? ' current' : ''}" data-studio-id="${esc(st.id)}" title="${esc(st.name)} (${esc(st.folder)})">
        <td><div class="task-name"><span class="studio-pill">STUDIO</span><span>${esc(st.name)}</span></div></td>
        <td><span class="studio-count">${st.cases} case${st.cases === 1 ? '' : 's'}</span></td>
        <td></td>
      </tr>`;
    }).join('');
    const taskRows = S.tasks.map(t => {
      const current = !S.activeStudioId && (t.id === S.activeTaskId || t.chat_key === S.key);
      const schedOn = !!t.schedule?.enabled;
      const status = schedOn ? 'active' : t.status;
      const schedTitle = schedOn ? `Scheduled every ${t.schedule.interval_min}m` : 'Set schedule for this task';
      return `<tr class="task-row${current ? ' current' : ''}" data-id="${esc(t.id)}" title="${esc(t.name)} (${esc(t.folder)})">
        <td><div class="task-name">${t.busy ? '<i class="task-busy" title="Agent running"></i>' : ''}<span>${esc(t.name)}</span></div></td>
        <td><select class="task-status ${esc(status)}" data-id="${esc(t.id)}" aria-label="Task status">
          <option value="open"${status === 'open' ? ' selected' : ''}>open</option>
          <option value="active"${status === 'active' ? ' selected' : ''}>active</option>
          <option value="done"${status === 'done' ? ' selected' : ''}>done</option>
        </select></td>
        <td><button class="task-sched${schedOn ? ' on' : ''}" type="button" data-id="${esc(t.id)}" title="${esc(schedTitle)}">⏱</button><button class="task-del" type="button" data-id="${esc(t.id)}" title="Remove task from list (keeps folder)">×</button></td>
      </tr>`;
    }).join('');
    tbody.innerHTML = studioRows + taskRows;
  }
  function openStudio(st) {
    closeDreamStage();
    closePromptLoopStage();
    $('#shell').classList.add('studio-mode');
    const changed = S.activeStudioId !== st.id;
    S.activeStudioId = st.id;
    S.activeTaskId = null;
    syncWorkspaceHeader({ folder: st.folder });
    if (changed) {
      setTarget('');
      renderTree();
    }
    $('#studioStageName').textContent = st.name;
    $('#studioStageFolder').textContent = st.folder;
    $('#studioOpenTab').href = st.url;
    if ($('#studioFrame').getAttribute('src') !== st.url) $('#studioFrame').setAttribute('src', st.url);
    $('#studioStage').hidden = false;
    $('#messages').hidden = true;
    $('#composer').hidden = true;
    renderTasks();
  }
  function closeStudio() {
    if (!S.activeStudioId && $('#studioStage').hidden) return;
    S.activeStudioId = null;
    $('#shell').classList.remove('studio-mode');
    $('#studioStage').hidden = true;
    $('#messages').hidden = false;
    $('#composer').hidden = false;
    const match = S.tasks.find(t => t.chat_key === S.key);
    S.activeTaskId = match ? match.id : null;
    syncWorkspaceHeader(match || null);
    setTarget('');
    renderTree();
  }
  async function refreshStudios() {
    try { S.studios = await api('/api/studios'); } catch { return; }
    renderTasks();
  }
  async function refreshTasks() {
    try { S.tasks = await api('/api/tasks'); } catch { return; }
    const match = S.tasks.find(t => t.chat_key === S.key);
    const prev = S.activeTaskId;
    S.activeTaskId = match ? match.id : null;
    syncWorkspaceHeader(match || null);
    if (prev !== S.activeTaskId) { setTarget(''); renderTree(); }
    renderTasks();
    renderSchedule();
  }
  async function selectTask(task) {
    closeStudio();
    closeDreamStage();
    closePromptLoopStage();
    const changed = S.activeTaskId !== task.id;
    S.activeTaskId = task.id;
    syncWorkspaceHeader(task);
    if (changed) {
      S.attachments = [];
      renderAttachments();
      setTarget('');
      renderTree();
    }
    renderTasks();
    renderSchedule();
    if (task.chat_key && task.chat_key !== S.key) await openChat(task.chat_key);
  }
  $('#newTaskBtn').onclick = () => {
    $('#studioForm').hidden = true;
    const form = $('#taskForm');
    form.hidden = !form.hidden;
    if (!form.hidden) $('#taskNameInput').focus();
  };
  $('#newStudioBtn').onclick = async () => {
    $('#taskForm').hidden = true;
    const form = $('#studioForm');
    form.hidden = !form.hidden;
    if (!form.hidden) {
      try {
        const list = await api('/api/studios/templates');
        $('#studioTemplateSelect').innerHTML = list.map(t => `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join('');
      } catch { /* keep defaults */ }
      $('#studioNameInput').focus();
    }
  };
  $('#studioCancelBtn').onclick = () => { $('#studioForm').reset(); $('#studioForm').hidden = true; };
  $('#studioForm').onsubmit = async e => {
    e.preventDefault();
    const name = $('#studioNameInput').value.trim();
    const folder = $('#studioFolderInput').value.trim();
    const template = $('#studioTemplateSelect').value;
    if (!name) return;
    try {
      const st = await api('/api/studios', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, folder, template }),
      });
      $('#studioForm').reset();
      $('#studioForm').hidden = true;
      await refreshStudios();
      renderTree();
      openStudio(st);
      toast(`Studio “${st.name}” created (${st.folder})`);
    } catch (err) { toast(err.message, true); }
  };
  $('#studioBackChat').onclick = () => { closeStudio(); renderTasks(); };
  $('#taskCancelBtn').onclick = () => { $('#taskForm').reset(); $('#taskForm').hidden = true; };
  $('#taskForm').onsubmit = async e => {
    e.preventDefault();
    const name = $('#taskNameInput').value.trim();
    const folder = $('#taskFolderInput').value.trim();
    if (!name) return;
    try {
      const task = await api('/api/tasks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, folder }),
      });
      $('#taskForm').reset();
      $('#taskForm').hidden = true;
      await refreshTasks();
      await refreshChats();
      await selectTask(task);
      toast(`Task “${task.name}” created (${task.folder})`);
    } catch (err) { toast(err.message, true); }
  };
  let schedMode = 'prompt';
  let plActiveName = '';
  const PL_STARTER_YAML = `name: custom-loop
version: 2
description: Custom PromptLoop FSM workflow (100% fresh per state).

inputs:
  goal: {required: true, description: "task goal"}

runtime:
  max_cycles: 10
  max_retries_per_state: 3
  no_progress_limit: 2

tools: [read, write, edit, bash]
entry: plan

states:
  plan:
    macro_phase: PLAN
    tools: [read, bash]
    prompt: "Plan the work for: {{ inputs.goal }}"
    routes:
      default: execute

  execute:
    macro_phase: EXECUTE
    prompt: |
      Plan:
      {{ steps.plan.output }}
      Execute the plan and save key output to reports/result.md.
    output: reports/result.md
    routes:
      default: exit_gate

  exit_gate:
    macro_phase: EXIT
    gate: true
    validators:
      - name: result_written
        file_exists: reports/result.md
    routes:
      passed: DONE
      failed: execute
`;

  async function loadWorkflows() {
    try {
      S.workflows = await api('/api/workflows');
    } catch {
      S.workflows = S.workflows || [];
    }
    if (!$('#scheduleTab').hidden) renderSchedule();
    if (!$('#promptloopStage').hidden) renderPromptLoopList();
  }

  function setSchedMode(mode) {
    schedMode = mode === 'workflow' ? 'workflow' : 'prompt';
    $$('#schedModeRow .seg').forEach(b => b.classList.toggle('active', b.dataset.mode === schedMode));
    $('#schedPromptBox').hidden = schedMode !== 'prompt';
    $('#schedWorkflowBox').hidden = schedMode !== 'workflow';
    $('#schedRunWfBtn').hidden = schedMode !== 'workflow';
    $('#schedPromptLabel').textContent = schedMode === 'workflow'
      ? 'Additional prompt / task instructions (optional)'
      : 'Prompt for this task';
    $('#schedPrompt').placeholder = schedMode === 'workflow'
      ? 'Optional extra instructions injected into every PromptLoop state…'
      : "What should the agent do on each scheduled run in this task's workspace?";
  }

  function renderScheduleWorkflowInputs(wfName, savedInputs = {}) {
    const wf = (S.workflows || []).find(w => w.name === wfName);
    const statesEl = $('#schedWorkflowStates');
    const box = $('#schedWorkflowInputs');
    if (!wf) {
      statesEl.textContent = wfName ? `Custom path: ${wfName}` : 'Pick a PromptLoop YAML';
      box.innerHTML = '';
      return;
    }
    statesEl.textContent = `${wf.states.join(' → ')} (${wf.source})`;
    const entries = Object.entries(wf.inputs || {});
    if (!entries.length) {
      box.innerHTML = '<div class="caption muted">No inputs required for this workflow.</div>';
      return;
    }
    box.innerHTML = entries.map(([k, spec]) => {
      const val = savedInputs && savedInputs[k] !== undefined ? savedInputs[k] : (spec.default ?? '');
      const req = spec.required ? ' *' : '';
      const ph = spec.description || (spec.default != null ? `default: ${spec.default}` : '');
      return `<label class="sched-field">
        <span class="caption mono">${esc(k)}${req}</span>
        <input class="input mono" data-wf-input="${esc(k)}" type="text" value="${esc(String(val))}" placeholder="${esc(ph)}"${spec.required ? ' data-req="1"' : ''}>
      </label>`;
    }).join('');
  }

  function readScheduleWorkflowInputs() {
    const out = {};
    $$('#schedWorkflowInputs [data-wf-input]').forEach(el => {
      const val = el.value.trim();
      if (val !== '') out[el.dataset.wfInput] = val;
    });
    return out;
  }

  function renderSchedule() {
    const task = S.tasks.find(t => t.id === S.activeTaskId);
    $('#schedDot').hidden = !task?.schedule?.enabled;
    $('#schedEmpty').hidden = !!task;
    $('#taskSchedForm').hidden = !task;
    if (!task) return;
    if (!S.skills) loadSkills();
    if (!S.workflows) loadWorkflows();
    const sel = $('#schedSkill');
    const wanted = task.schedule?.skill || '';
    sel.innerHTML = '<option value="">(keep chat skill)</option>' +
      (S.skills || []).map(s => `<option value="${esc(s.name)}" title="${esc(s.description || '')}">${esc(s.name)}</option>`).join('');
    sel.value = wanted;

    const wfSel = $('#schedWorkflow');
    const wantedWf = task.schedule?.workflow || '';
    const wfs = S.workflows || [];
    wfSel.innerHTML = '<option value="">(select PromptLoop YAML)</option>' +
      wfs.map(w => `<option value="${esc(w.name)}">${esc(w.name)} (${w.states.length} states · ${w.source})</option>`).join('');
    if (wantedWf && !wfs.some(w => w.name === wantedWf)) {
      wfSel.insertAdjacentHTML('beforeend', `<option value="${esc(wantedWf)}">${esc(wantedWf)}</option>`);
    }
    wfSel.value = wantedWf;

    setSchedMode(wantedWf ? 'workflow' : 'prompt');
    renderScheduleWorkflowInputs(wantedWf, task.schedule?.inputs || {});

    $('#schedTitle').textContent = task.name;
    $('#schedFolder').textContent = task.folder;
    $('#schedEnabled').checked = !!task.schedule?.enabled;
    $('#schedInterval').value = task.schedule?.interval_min || 60;
    $('#schedPrompt').value = task.schedule?.prompt || '';
    const parts = [];
    if (task.schedule?.last_status) parts.push(`status: ${task.schedule.last_status}`);
    if (task.schedule?.last_run) parts.push(`last: ${clock(task.schedule.last_run)}`);
    if (task.schedule?.enabled && task.schedule?.next_run) parts.push(`next: ${clock(task.schedule.next_run)}`);
    if (task.schedule?.consecutive_errors) parts.push(`errors: ${task.schedule.consecutive_errors}`);
    if (task.schedule?.last_error) parts.push(`err: ${task.schedule.last_error}`);
    $('#schedMeta').textContent = parts.join(' · ') || 'Not scheduled yet';

    const canResume = task.schedule?.last_status === 'waiting_human' || task.schedule?.last_status === 'paused';
    $('#schedResumeBox').hidden = !canResume;
  }

  const inPromptLoopMode = () => !$('#promptloopStage').hidden;
  function openPromptLoopStage() {
    closeStudio();
    closeDreamStage();
    $('#shell').classList.add('promptloop-mode');
    $('#promptloopStage').hidden = false;
    $('#messages').hidden = true;
    $('#composer').hidden = true;
    const btn = $('#promptloopBtn');
    btn.classList.add('active');
    btn.firstElementChild.textContent = '← Back to Chat';
    loadWorkflows().then(() => {
      if (!plActiveName && S.workflows?.length) selectPromptLoop(S.workflows[0].name);
    });
  }
  function closePromptLoopStage() {
    if ($('#promptloopStage').hidden) return;
    $('#shell').classList.remove('promptloop-mode');
    $('#promptloopStage').hidden = true;
    const btn = $('#promptloopBtn');
    btn.classList.remove('active');
    btn.firstElementChild.textContent = 'PromptLoops';
    if ($('#studioStage').hidden && $('#dreamStage').hidden) {
      $('#messages').hidden = false;
      $('#composer').hidden = false;
    }
  }
  function renderPromptLoopList() {
    const list = $('#plList');
    const wfs = S.workflows || [];
    if (!wfs.length) {
      list.innerHTML = '<div class="placeholder">No PromptLoop YAMLs found. Click + New PromptLoop.</div>';
      return;
    }
    list.innerHTML = wfs.map(w => `
      <button class="dream-node-row${w.name === plActiveName ? ' pl-row-active' : ''}" type="button" data-wf="${esc(w.name)}">
        <div class="dream-node-top">
          <span class="dream-node-title">
            <span class="dream-type-badge ${w.source === 'workspace' ? 'pattern' : 'fact'}">${esc(w.source)}</span>
            <strong class="mono">${esc(w.name)}</strong>
          </span>
          <span class="caption mono muted">${w.states.length} states</span>
        </div>
        <div class="caption mono muted">${esc(w.states.join(' → '))}</div>
      </button>
    `).join('');
  }
  async function selectPromptLoop(name) {
    plActiveName = name;
    renderPromptLoopList();
    $('#plStatusMsg').textContent = 'Loading…';
    try {
      const wf = await api(`/api/workflows/${encodeURIComponent(name)}`);
      $('#plEditorTitle').textContent = wf.name;
      $('#plEditorSource').textContent = `${wf.source} · ${wf.path}`;
      $('#plNameInput').value = wf.name;
      $('#plYamlInput').value = wf.content;
      $('#plStatesPreview').textContent = `entry: ${wf.entry} · states: ${wf.states.join(' → ')}`;
      $('#plDeleteBtn').hidden = wf.source !== 'workspace';
      $('#plStatusMsg').textContent = wf.source === 'bundled'
        ? 'Bundled default (saving creates a workspace override in workflows/)'
        : 'Workspace workflow (editable)';
    } catch (err) {
      $('#plStatusMsg').textContent = err.message;
      toast(err.message, true);
    }
  }
  function startNewPromptLoop() {
    plActiveName = '';
    renderPromptLoopList();
    $('#plEditorTitle').textContent = 'New PromptLoop YAML';
    $('#plEditorSource').textContent = 'workflows/<name>.yaml';
    $('#plNameInput').value = 'custom-loop';
    $('#plYamlInput').value = PL_STARTER_YAML;
    $('#plStatesPreview').textContent = 'entry: plan · states: plan → execute → exit_gate';
    $('#plDeleteBtn').hidden = true;
    $('#plStatusMsg').textContent = 'Edit YAML and click Validate & Save.';
    $('#plNameInput').focus();
  }

  let dreamTrack = '';
  const inDreamMode = () => !$('#dreamStage').hidden;
  function openDreamStage() {
    closeStudio();
    closePromptLoopStage();
    $('#shell').classList.add('dream-mode');
    $('#dreamStage').hidden = false;
    $('#messages').hidden = true;
    $('#composer').hidden = true;
    const btn = $('#dreamBtn');
    btn.classList.add('active');
    btn.lastElementChild.textContent = '← Back to Chat';
    btn.title = 'Return to Chat';
    renderTree();
    loadDream();
    loadDreamNodes();
  }
  function closeDreamStage() {
    if ($('#dreamStage').hidden) return;
    $('#shell').classList.remove('dream-mode');
    $('#dreamStage').hidden = true;
    const btn = $('#dreamBtn');
    btn.classList.remove('active');
    btn.lastElementChild.textContent = 'Dreaming';
    btn.title = 'User-level Memory & Dreaming Scheduler';
    if ($('#studioStage').hidden) {
      $('#messages').hidden = false;
      $('#composer').hidden = false;
    }
    renderTree();
  }
  function renderDream(d) {
    if (!d) return;
    const btn = $('#dreamBtn');
    btn.classList.toggle('on', !!d.enabled);
    btn.classList.toggle('busy', !!d.busy);
    $('#dreamEnabled').checked = !!d.enabled;
    $('#dreamInterval').value = d.interval_min || 60;
    const c = d.counts || {};
    const v = d.volumes || {};
    const items = [
      ['fact', 'Facts', c.fact || 0, v.fact || 0],
      ['pattern', 'Patterns', c.pattern || 0, v.pattern || 0],
      ['sim', 'SIM', c.sim || 0, v.sim || 0],
      ['archived', 'Archived', c.archived || 0, v.archived || 0],
    ];
    const totalNodes = items.reduce((a, x) => a + x[2], 0);
    const totalBytes = items.reduce((a, x) => a + x[3], 0);
    $('#dreamTotalVol').textContent = `${totalNodes} nodes · ${fmtSize(totalBytes)}`;
    $('#dreamVolumeBar').innerHTML = totalBytes
      ? items.filter(x => x[3] > 0).map(([k, lbl, , bytes]) =>
          `<div class="dream-vol-seg ${k}" style="width:${Math.max(3, (bytes / totalBytes) * 100)}%" title="${lbl}: ${fmtSize(bytes)}"></div>`
        ).join('')
      : '';
    $('#dreamCounts').innerHTML = items.map(([k, lbl, cnt, bytes]) =>
      `<div class="dream-vol-item"><span class="lbl"><i class="${k}"></i>${lbl}</span><span class="val">${cnt}</span><span class="mono caption muted">${fmtSize(bytes)}</span></div>`
    ).join('');
    $('#dreamIndexBtn').hidden = !d.index_exists;
    const runBtn = $('#dreamRunBtn');
    runBtn.disabled = !!d.busy;
    runBtn.textContent = d.busy ? 'Dreaming…' : 'Run now';
    const meta = [];
    if (d.last_run) meta.push(`last: ${clock(d.last_run)}`);
    if (d.enabled && d.next_run) meta.push(`next: ${clock(d.next_run)}`);
    if (d.last_summary) {
      const s = d.last_summary;
      meta.push(`+${s.created || 0} ~${s.updated || 0} sup:${s.superseded || 0} arch:${s.archived || 0}`);
    }
    if (d.last_error) meta.push(`err: ${d.last_error}`);
    $('#dreamMeta').textContent = meta.join(' · ') || 'Not dreamed yet';
  }
  async function loadDreamNodes() {
    const q = ($('#dreamSearch').value || '').trim();
    const archived = dreamTrack === 'archived';
    const qs = new URLSearchParams({ q, track: dreamTrack, archived: String(archived) });
    try {
      const nodes = await api(`/api/dream/nodes?${qs.toString()}`);
      const list = $('#dreamNodeList');
      if (!nodes.length) {
        list.innerHTML = `<div class="placeholder">${q ? 'No matching memory nodes.' : 'No memory nodes yet. Click “Run now” to distill sessions.'}</div>`;
        return;
      }
      list.innerHTML = nodes.map(n => `
        <button class="dream-node-row" type="button" data-path="${esc(n.rel_path)}">
          <div class="dream-node-top">
            <span class="dream-node-title">
              <span class="dream-type-badge ${esc(n.type)}">${esc(n.type)}</span>
              <strong class="mono">${esc(n.id)}</strong>
            </span>
            <span class="mono caption muted">${esc(n.status)} · ${esc(n.updated_at)} · ${fmtSize(n.size)}</span>
          </div>
          <div class="dream-node-summary">${esc(n.summary)}</div>
        </button>`).join('');
    } catch (err) { toast(err.message, true); }
  }
  async function loadDream() {
    try { renderDream(await api('/api/dream')); }
    catch (err) { toast(err.message, true); }
  }
  $('#dreamSchedForm').onsubmit = async e => {
    e.preventDefault();
    const enabled = $('#dreamEnabled').checked;
    const interval_min = Number($('#dreamInterval').value);
    try {
      const d = await api('/api/dream', {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, interval_min }),
      });
      renderDream(d);
      toast(d.enabled ? `Dreaming scheduled every ${d.interval_min}m` : 'Dreaming schedule paused');
    } catch (err) { toast(err.message, true); }
  };
  $('#dreamRunBtn').onclick = async () => {
    const btn = $('#dreamRunBtn');
    btn.disabled = true;
    btn.textContent = 'Dreaming…';
    try {
      const res = await api('/api/dream/run', { method: 'POST' });
      renderDream(res.status);
      loadDreamNodes();
      renderTree();
      const r = res.report || {};
      toast(`Dreamed ${r.sessions_processed || 0} session(s): +${r.created || 0} ~${r.updated || 0}`);
    } catch (err) {
      toast(err.message, true);
      loadDream();
    }
  };
  $('#dreamIndexBtn').onclick = () => openPreview('memory/INDEX.md', true);
  $('#dreamBackChat').onclick = closeDreamStage;
  $('#dreamSearch').oninput = () => loadDreamNodes();
  $('#dreamFilters').addEventListener('click', e => {
    const btn = e.target.closest('[data-track]');
    if (!btn) return;
    dreamTrack = btn.dataset.track || '';
    $$('#dreamFilters .seg').forEach(b => b.classList.toggle('active', b === btn));
    loadDreamNodes();
  });
  $('#dreamNodeList').addEventListener('click', e => {
    const row = e.target.closest('.dream-node-row');
    if (row) openPreview(`memory/${row.dataset.path}`, true);
  });
  $('#promptloopBtn').onclick = () => (inPromptLoopMode() ? closePromptLoopStage() : openPromptLoopStage());
  $('#plBackChat').onclick = closePromptLoopStage;
  $('#plNewBtn').onclick = startNewPromptLoop;
  $('#plRefreshBtn').onclick = () => loadWorkflows();
  $('#plList').addEventListener('click', e => {
    const row = e.target.closest('.dream-node-row');
    if (row?.dataset.wf) selectPromptLoop(row.dataset.wf);
  });
  $('#plEditorForm').onsubmit = async e => {
    e.preventDefault();
    const name = $('#plNameInput').value.trim();
    const content = $('#plYamlInput').value;
    $('#plStatusMsg').textContent = 'Validating…';
    try {
      const saved = await api(`/api/workflows/${encodeURIComponent(name)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      plActiveName = saved.name;
      await loadWorkflows();
      await selectPromptLoop(saved.name);
      toast(`PromptLoop “${saved.name}” validated & saved`);
    } catch (err) {
      $('#plStatusMsg').textContent = `Validation error: ${err.message}`;
      toast(err.message, true);
    }
  };
  $('#plDeleteBtn').onclick = async () => {
    const name = $('#plNameInput').value.trim();
    if (!name) return;
    try {
      await api(`/api/workflows/${encodeURIComponent(name)}`, { method: 'DELETE' });
      plActiveName = '';
      await loadWorkflows();
      if (S.workflows?.length) selectPromptLoop(S.workflows[0].name);
      else startNewPromptLoop();
      toast(`Deleted workspace workflow “${name}”`);
    } catch (err) { toast(err.message, true); }
  };

  $('#schedModeRow').addEventListener('click', e => {
    const btn = e.target.closest('.seg');
    if (!btn) return;
    setSchedMode(btn.dataset.mode);
  });
  $('#schedWorkflow').onchange = () => {
    const task = S.tasks.find(t => t.id === S.activeTaskId);
    renderScheduleWorkflowInputs($('#schedWorkflow').value, task?.schedule?.inputs || {});
  };
  $('#schedManageWfBtn').onclick = () => openPromptLoopStage();

  $('#schedRunWfBtn').onclick = async () => {
    if (!S.activeTaskId) return;
    const workflow = $('#schedWorkflow').value;
    if (!workflow) { toast('Select a PromptLoop workflow first', true); return; }
    const inputs = readScheduleWorkflowInputs();
    const prompt = $('#schedPrompt').value.trim();
    try {
      await api(`/api/tasks/${encodeURIComponent(S.activeTaskId)}/workflow/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow, inputs, prompt }),
      });
      showTab('live');
      toast(`Started PromptLoop “${workflow}”`);
    } catch (err) { toast(err.message, true); }
  };

  $('#schedResumeBtn').onclick = async () => {
    if (!S.activeTaskId) return;
    const answers = {};
    ($('#schedResumeAnswers').value || '').split('\n').forEach(line => {
      const idx = line.indexOf('=');
      if (idx > 0) answers[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    });
    try {
      await api(`/api/tasks/${encodeURIComponent(S.activeTaskId)}/workflow/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume: 'latest', answers }),
      });
      $('#schedResumeAnswers').value = '';
      showTab('live');
      toast('Resumed paused PromptLoop workflow');
    } catch (err) { toast(err.message, true); }
  };

  $('#taskSchedForm').onsubmit = async e => {
    e.preventDefault();
    if (!S.activeTaskId) return;
    const enabled = $('#schedEnabled').checked;
    const interval_min = Number($('#schedInterval').value);
    const payload = schedMode === 'workflow'
      ? { enabled, interval_min, prompt: $('#schedPrompt').value.trim(), workflow: $('#schedWorkflow').value || null, inputs: readScheduleWorkflowInputs() }
      : { enabled, interval_min, prompt: $('#schedPrompt').value.trim(), workflow: null, inputs: {}, skill: $('#schedSkill').value || null };
    try {
      const updated = await api(`/api/tasks/${encodeURIComponent(S.activeTaskId)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schedule: payload }),
      });
      await refreshTasks();
      renderSchedule();
      toast(updated.schedule?.enabled ? `Scheduled every ${updated.schedule.interval_min}m` : 'Schedule saved (paused)');
    } catch (err) { toast(err.message, true); }
  };

  $('#taskList').addEventListener('click', async e => {
    if (e.target.closest('.task-status')) return;
    const sched = e.target.closest('.task-sched');
    if (sched) {
      e.stopPropagation();
      const task = S.tasks.find(t => t.id === sched.dataset.id);
      if (task) {
        await selectTask(task);
        setPanel('right', true);
        showTab('schedule');
        $('#schedPrompt').focus();
      }
      return;
    }
    const del = e.target.closest('.task-del');
    if (del) {
      e.stopPropagation();
      try {
        await api(`/api/tasks/${encodeURIComponent(del.dataset.id)}`, { method: 'DELETE' });
        if (S.activeTaskId === del.dataset.id) S.activeTaskId = null;
        await refreshTasks();
      } catch (err) { toast(err.message, true); }
      return;
    }
    const srow = e.target.closest('.studio-row');
    if (srow) {
      const st = S.studios.find(x => x.id === srow.dataset.studioId);
      if (st) openStudio(st);
      return;
    }
    const row = e.target.closest('.task-row');
    if (!row) return;
    const task = S.tasks.find(t => t.id === row.dataset.id);
    if (task) await selectTask(task);
  });
  $('#taskList').addEventListener('change', async e => {
    const sel = e.target.closest('.task-status');
    if (!sel) return;
    try {
      await api(`/api/tasks/${encodeURIComponent(sel.dataset.id)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: sel.value }),
      });
      await refreshTasks();
    } catch (err) { toast(err.message, true); await refreshTasks(); }
  });

  // ---------------------------------------------------------------- workspace tree
  const EXT = { pdf: 'pdf', doc: 'doc', docx: 'doc', ppt: 'doc', pptx: 'doc', xls: 'xls', xlsx: 'xls', csv: 'xls', png: 'img', jpg: 'img', jpeg: 'img',
    gif: 'img', webp: 'img', md: 'txt', txt: 'txt', json: 'txt', yaml: 'txt', yml: 'txt', py: 'txt', js: 'txt', html: 'txt', eml: 'doc', msg: 'doc' };
  const extOf = name => (name.includes('.') ? name.split('.').pop().toLowerCase() : '');
  function saveOpenDirs() { localStorage.setItem('breezeman-open-dirs', JSON.stringify([...S.openDirs])); }

  async function renderDir(path, container) {
    let entries;
    try {
      const tq = inDreamMode() ? '' : taskQuery('&');
      entries = await api(`/api/tree?path=${encodeURIComponent(path)}${tq}`);
    } catch (e) {
      S.openDirs.delete(path);
      saveOpenDirs();
      container.innerHTML = `<div class="caption">${esc(e.message)}</div>`;
      return;
    }
    container.innerHTML = '';
    if (!entries.length && !path) container.innerHTML = '<div class="placeholder">The workspace is empty. Drop files here.</div>';
    for (const e of entries) {
      const row = document.createElement('div');
      const ext = extOf(e.name);
      row.className = `node ${e.dir ? 'dir' : 'file'}${e.dir && S.openDirs.has(e.path) ? ' open' : ''}${e.dir && e.path === S.selectedDir ? ' selected' : ''}`;
      row.dataset.path = e.path;
      row.setAttribute('role', 'treeitem');
      row.draggable = !e.dir;
      row.title = e.path;
      row.innerHTML = e.dir
        ? `<span class="chev">▶</span><span class="ico">▰</span><span class="nm">${esc(e.name)}</span>`
        : `<span class="chev"></span><span class="ico ${EXT[ext] || ''}">${esc((ext || 'file').slice(0, 4).toUpperCase())}</span><span class="nm">${esc(e.name)}</span><span class="sz">${fmtSize(e.size)}</span><button class="att" type="button" title="Attach to the next message">+ attach</button>`;
      container.append(row);
      if (e.dir) {
        const kids = document.createElement('div');
        kids.className = 'children';
        kids.hidden = !S.openDirs.has(e.path);
        container.append(kids);
        if (!kids.hidden) renderDir(e.path, kids);
      }
    }
  }
  const renderTree = () => {
    const label = $('#wsLabel');
    if (inDreamMode()) {
      if (label) label.textContent = 'MEMORY · memory/';
      return renderDir('memory', $('#tree'));
    }
    const task = S.tasks.find(t => t.id === S.activeTaskId);
    const st = S.studios.find(s => s.id === S.activeStudioId);
    if (label) label.textContent = st ? `WORKSPACE · ${st.folder}` : (task ? `WORKSPACE · ${task.folder}` : 'WORKSPACE');
    return renderDir('', $('#tree'));
  };
  function setTarget(dir) {
    S.selectedDir = dir;
    $$('#tree .node.dir').forEach(n => n.classList.toggle('selected', n.dataset.path === dir));
    const el = $('#uploadTarget');
    el.hidden = !dir;
    if (dir) {
      const task = S.tasks.find(t => t.id === S.activeTaskId);
      el.textContent = `upload to: ${task ? `${task.folder}/` : '/'}${dir}`;
    } else {
      el.textContent = '';
    }
  }
  $('#tree').addEventListener('click', e => {
    const row = e.target.closest('.node');
    if (!row) return;
    const path = row.dataset.path;
    if (e.target.closest('.att')) { attach(path); return; }
    if (row.classList.contains('dir')) {
      const kids = row.nextElementSibling;
      const open = kids.hidden;
      kids.hidden = !open;
      row.classList.toggle('open', open);
      if (open) { S.openDirs.add(path); renderDir(path, kids); } else S.openDirs.delete(path);
      saveOpenDirs();
      setTarget(open ? path : path.split('/').slice(0, -1).join('/'));
    } else openPreview(path);
  });
  $('#tree').addEventListener('dragstart', e => {
    const row = e.target.closest('.node.file');
    if (row) e.dataTransfer.setData('text/x-breezeman-path', row.dataset.path);
  });
  $('#treeRefresh').onclick = renderTree;

  async function upload(files, folder = S.selectedDir) {
    files = [...files];
    if (!files.length) return [];
    const form = new FormData();
    form.append('folder', folder);
    if (S.activeTaskId) form.append('task', S.activeTaskId);
    files.forEach(f => form.append('files', f, f.name));
    toast(`Uploading ${files.length} file${files.length > 1 ? 's' : ''}…`);
    try {
      const r = await api('/api/upload', { method: 'POST', body: form });
      toast(`Uploaded ${r.saved.join(', ')}`);
      if (folder) { S.openDirs.add(folder); saveOpenDirs(); }
      renderTree();
      return r.saved;
    } catch (e) {
      toast(`Upload failed: ${e.message}`, true);
      return [];
    }
  }
  $('#uploadInput').onchange = e => { upload(e.target.files); e.target.value = ''; };
  const zone = $('#treeZone');
  const hasFiles = e => [...(e.dataTransfer?.types || [])].includes('Files');
  zone.addEventListener('dragover', e => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    zone.classList.add('drag');
    $$('#tree .node.drop').forEach(n => n.classList.remove('drop'));
    e.target.closest('.node.dir')?.classList.add('drop');
  });
  zone.addEventListener('dragleave', e => { if (!zone.contains(e.relatedTarget)) { zone.classList.remove('drag'); $$('#tree .node.drop').forEach(n => n.classList.remove('drop')); } });
  zone.addEventListener('drop', e => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    zone.classList.remove('drag');
    const dir = e.target.closest('.node.dir');
    $$('#tree .node.drop').forEach(n => n.classList.remove('drop'));
    upload(e.dataTransfer.files, dir ? dir.dataset.path : S.selectedDir);
  });

  // preview
  let previewPath = null;
  let previewHtml = null;
  function renderPreviewHtml(mode) {
    const body = $('#pvBody');
    $$('#pvTabs .seg').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
    if (mode === 'render') {
      body.classList.add('html-mode');
      body.innerHTML = '';
      const frame = document.createElement('iframe');
      frame.className = 'html-frame';
      frame.sandbox = 'allow-scripts';
      frame.srcdoc = previewHtml ?? '';
      body.append(frame);
    } else {
      body.classList.remove('html-mode');
      body.innerHTML = `<pre>${esc(previewHtml ?? '')}</pre>`;
    }
  }
  async function openPreview(path, rootOnly = false) {
    try {
      const tq = (rootOnly || inDreamMode()) ? '' : taskQuery('&');
      const f = await api(`/api/file?path=${encodeURIComponent(path)}${tq}`);
      if (!f.binary && (f.ext === '.html' || f.ext === '.htm')) {
        const html = f.truncated ? await api(`/api/file/raw?path=${encodeURIComponent(path)}${tq}`) : f.text;
        showHtmlDialog(f.path, fmtSize(f.size), html, path);
        return;
      }
      showDialog(f.path, `${fmtSize(f.size)}${f.truncated ? ' · preview truncated' : ''}`,
        f.binary ? `<div class="placeholder">${esc(f.ext || 'binary')} file · ${fmtSize(f.size)}<br>No text preview. Attach it: the agent reads PDFs, Office files, images and e-mail through its document sub-agent.</div>`
          : f.ext === '.md' ? `<div class="md">${md(f.text)}</div>` : `<pre>${esc(f.text)}</pre>`, path);
    } catch (e) { toast(e.message, true); }
  }
  function showHtmlDialog(title, meta, html, attachPath = null) {
    previewPath = attachPath;
    previewHtml = html;
    $('#pvName').textContent = title;
    $('#pvMeta').textContent = meta;
    $('#pvTabs').hidden = false;
    $('#pvAttach').hidden = !attachPath;
    $('#preview').classList.add('is-html');
    renderPreviewHtml('render');
    $('#preview').showModal();
  }
  function showDialog(title, meta, html, attachPath = null) {
    previewPath = attachPath;
    previewHtml = null;
    $('#pvName').textContent = title;
    $('#pvMeta').textContent = meta;
    $('#pvTabs').hidden = true;
    $('#preview').classList.remove('is-html');
    $('#pvBody').classList.remove('html-mode');
    $('#pvBody').innerHTML = html;
    $('#pvAttach').hidden = !attachPath;
    $('#preview').showModal();
  }
  $('#pvTabs').onclick = e => {
    const b = e.target.closest('button[data-mode]');
    if (b && previewHtml != null) renderPreviewHtml(b.dataset.mode);
  };
  $('#pvClose').onclick = () => $('#preview').close();
  $('#preview').addEventListener('click', e => { if (e.target === $('#preview')) $('#preview').close(); });
  $('#pvAttach').onclick = () => { if (previewPath) attach(previewPath); $('#preview').close(); };

  // ---------------------------------------------------------------- composer
  function attach(path) {
    if (!S.attachments.includes(path)) S.attachments.push(path);
    renderAttachments();
    $('#prompt').focus();
  }
  function renderAttachments() {
    $('#attachRow').innerHTML = S.attachments.map((p, i) =>
      `<span class="doc-chip" title="${esc(p)}"><em>${esc((extOf(p) || 'file').slice(0, 4).toUpperCase())}</em>${esc(p.split('/').pop())}<button type="button" data-i="${i}" aria-label="Remove">×</button></span>`).join('');
  }
  $('#attachRow').onclick = e => {
    const b = e.target.closest('button[data-i]');
    if (b) { S.attachments.splice(Number(b.dataset.i), 1); renderAttachments(); }
  };
  const prompt_ = $('#prompt');
  const autosize = () => { prompt_.style.height = 'auto'; prompt_.style.height = `${Math.min(240, prompt_.scrollHeight)}px`; };
  prompt_.addEventListener('input', autosize);
  prompt_.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('#composer').requestSubmit(); }
  });
  $('#composer').addEventListener('submit', e => {
    e.preventDefault();
    const text = prompt_.value.trim();
    if (!text) return;
    if (S.busy) { toast('The agent is still working; stop it or wait.', true); return; }
    if (!send({ type: 'chat', text, attachments: S.attachments })) return;
    prompt_.value = '';
    autosize();
    S.attachments = [];
    renderAttachments();
  });
  $('#stopBtn').onclick = () => send({ type: 'stop' });
  $('#compactBtn').onclick = () => {
    if (S.busy) { toast('Wait for the current run to finish.', true); return; }
    const focus = prompt('Compact older history into topic notes. Optional focus:', '');
    if (focus !== null) send({ type: 'compact', focus });
  };
  $('#suggestions').onclick = e => {
    const b = e.target.closest('.seg');
    if (b) { prompt_.value = b.textContent; autosize(); prompt_.focus(); }
  };
  const composer = $('#composer');
  composer.addEventListener('dragover', e => { e.preventDefault(); $('.composer-box').style.borderColor = 'var(--red)'; });
  composer.addEventListener('dragleave', () => { $('.composer-box').style.borderColor = ''; });
  composer.addEventListener('drop', async e => {
    e.preventDefault();
    $('.composer-box').style.borderColor = '';
    const path = e.dataTransfer.getData('text/x-breezeman-path');
    if (path) { attach(path); return; }
    if (hasFiles(e)) (await upload(e.dataTransfer.files)).forEach(attach);
  });

  function setBusy(kind) {
    S.busy = kind || null;
    $('#stopBtn').hidden = !S.busy;
    $('#sendBtn').hidden = !!S.busy;
    $('#compactBtn').disabled = !!S.busy;
    renderSkills();
    connState();
  }
  function meter() {
    const pct = S.window ? Math.min(100, (100 * S.tokens) / S.window) : 0;
    const bar = $('#meterBar');
    bar.style.width = `${pct}%`;
    bar.className = pct > 85 ? 'hot' : pct > 65 ? 'warn' : '';
    $('#meterText').textContent = S.window ? `context ${fmtTok(S.tokens)} / ${fmtTok(S.window)} (${pct.toFixed(0)}%)` : 'context –';
  }

  // ---------------------------------------------------------------- chat view
  const messages = $('#messages');
  const nearBottom = el => el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  const scrollChat = (force = false) => { if (force || nearBottom(messages)) messages.scrollTop = messages.scrollHeight; };
  function clearChat() {
    messages.querySelectorAll('.msg, .divider').forEach(n => n.remove());
    $('#emptyState').hidden = false;
    S.block = null;
  }
  function addUser(text, attachments = []) {
    $('#emptyState').hidden = true;
    const el = document.createElement('div');
    el.className = 'msg user';
    const long = text.length > 1200 || text.split('\n').length > 16;
    el.innerHTML = `${attachments.length ? `<div class="att-chips">${attachments.map(p => `<span class="doc-chip"><em>${esc((extOf(p) || 'file').slice(0, 4).toUpperCase())}</em>${esc(p.split('/').pop())}</span>`).join('')}</div>` : ''}<div class="bubble${long ? ' long' : ''}">${esc(text)}</div>`;
    if (long) el.querySelector('.bubble').onclick = ev => ev.currentTarget.classList.add('expanded');
    messages.append(el);
    scrollChat(true);
  }
  function addDivider(text, err = false) {
    $('#emptyState').hidden = true;
    const d = document.createElement('div');
    d.className = `divider${err ? ' err' : ''}`;
    d.textContent = text;
    messages.append(d);
    scrollChat();
  }
  function newBlock(live) {
    $('#emptyState').hidden = true;
    const el = document.createElement('div');
    el.className = 'msg agent';
    el.innerHTML = `<div class="avatar">B</div><div class="agent-body"><div class="meta"><span>AGENT</span><span class="state"></span></div><div class="work"></div><div class="md answer"></div></div>`;
    messages.append(el);
    const b = { el, work: el.querySelector('.work'), answer: el.querySelector('.answer'), state: el.querySelector('.state'), text: '',
      chipRow: null, chips: [], byId: {}, live, raf: 0 };
    if (live) setState(b, '<span class="spinner"></span> working…');
    scrollChat(true);
    return b;
  }
  function setState(b, html, err = false) { b.state.innerHTML = html; b.state.classList.toggle('err', err); }
  function addChip(b, name, args, id) {
    if (!b.chipRow || b.work.lastElementChild !== b.chipRow) {
      b.chipRow = document.createElement('div');
      b.chipRow.className = 'chip-row';
      b.work.append(b.chipRow);
    }
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'tool-chip';
    chip.innerHTML = `<span class="st"><span class="spinner"></span></span><b>${esc(name)}</b><span>${esc(argLine(args))}</span>`;
    const rec = { el: chip, name, args, result: null, error: false };
    chip.onclick = () => showDialog(`${name}`, rec.error ? 'tool call · error' : 'tool call',
      `<h4 class="mono">arguments</h4><pre>${esc(pretty(rec.args))}</pre><h4 class="mono">result</h4><pre>${esc(rec.result ?? '(running…)')}</pre>`);
    b.chipRow.append(chip);
    b.chips.push(rec);
    if (id) b.byId[id] = rec;
    return rec;
  }
  function endChip(rec, result, error) {
    rec.result = result;
    rec.error = error;
    rec.el.classList.add(error ? 'err' : 'ok');
    rec.el.querySelector('.st').textContent = error ? '✗' : '✓';
  }
  function renderAnswer(b, final = false) {
    b.raf = 0;
    b.answer.innerHTML = md(b.text) + (final ? '' : '<span class="cursor"></span>');
    scrollChat();
  }
  function flushNote(b) {
    if (!b.text.trim()) { b.text = ''; return; }
    const n = document.createElement('div');
    n.className = 'note md';
    n.innerHTML = md(b.text);
    b.work.append(n);
    b.text = '';
    b.answer.innerHTML = '';
  }

  // events of a live run, in the chat (main agent only; sub-agents show on the right)
  function chatEvent(ev) {
    if (ev.type === 'run_start') {
      // replaying a running chat: the transcript may already hold this prompt (it ends the journaled user message)
      const dup = S.replaying && S.lastUserText != null && S.lastUserText.endsWith(ev.text);
      if (dup) {         // the replay rebuilds this run's journaled turns: drop their transcript rendering
        const users = $$('.msg.user', messages);
        let n = users[users.length - 1]?.nextElementSibling;
        while (n) { const next = n.nextElementSibling; n.remove(); n = next; }
      } else if (ev.run !== 'compact') addUser(ev.text, ev.attachments || []);
      S.block = newBlock(true);
      if (ev.run === 'compact') setState(S.block, '<span class="spinner"></span> compacting history into topic notes…');
      S.runStart = ev.t;
      return;
    }
    if (ev.type === 'compaction' && ev.agent === 'main') { addDivider(`CONTEXT COMPACTED · ${fmtTok(ev.before)} → ${fmtTok(ev.after)}`); return; }
    const b = S.block;
    if (!b) return;
    const elapsed = () => (ev.t && S.runStart ? ` · ${(ev.t - S.runStart).toFixed(1)}s` : '');
    switch (ev.type) {
      case 'delta':
        if (ev.agent !== 'main') { setState(b, `<span class="spinner"></span> ${esc(ev.agent)} sub-agent working…`); break; }
        if (ev.kind === 'reasoning') setState(b, '<span class="spinner"></span> thinking…');   // the text itself is on the Live panel
        else if (ev.kind === 'content') {
          b.text += ev.text;
          setState(b, '<span class="spinner"></span> writing…');
          if (!b.raf) b.raf = requestAnimationFrame(() => renderAnswer(b));
        }
        scrollChat();
        break;
      case 'tool_start':
        if (ev.agent !== 'main') break;
        flushNote(b);
        b.pending = addChip(b, ev.name, ev.args);
        setState(b, `<span class="spinner"></span> running ${esc(ev.name)}…`);
        scrollChat();
        break;
      case 'tool_end':
        if (ev.agent === 'main' && b.pending) { endChip(b.pending, ev.result + (ev.chars > ev.result.length ? `\n… (${ev.chars} characters; preview cut)` : ''), ev.error); b.pending = null; }
        break;
      case 'done':
        if (b.raf) cancelAnimationFrame(b.raf);
        b.text = ev.answer || b.text;
        renderAnswer(b, true);
        setState(b, ev.stopped === 'max_turns' ? `stopped at the model-call limit${elapsed()}` : `done${elapsed()}`, ev.stopped === 'max_turns');
        S.block = null;
        break;
      case 'compacted':
        b.el.remove();
        addDivider(ev.compacted ? 'HISTORY COMPACTED INTO TOPIC NOTES' : 'NOTHING TO COMPACT');
        S.block = null;
        break;
      case 'aborted':
        if (b.raf) cancelAnimationFrame(b.raf);
        if (b.text) renderAnswer(b, true);
        setState(b, `stopped by you${elapsed()}`, true);
        b.chips.filter(c => c.result === null).forEach(c => endChip(c, 'Aborted by the user.', true));
        S.block = null;
        break;
      case 'error':
        if (ev.run) {
          if (b.raf) cancelAnimationFrame(b.raf);
          if (b.text) renderAnswer(b, true);
          setState(b, `error: ${esc(ev.message)}`, true);
          S.block = null;
        }
        break;
      case 'stopping':
        setState(b, '<span class="spinner"></span> stopping…', true);
        break;
      default:
    }
  }

  // the journal as a conversation
  function renderTranscript(items) {
    clearChat();
    let b = null;
    for (const m of items) {
      if (m.role === 'user') { addUser(m.content, m.attachments || []); b = null; }
      else if (m.role === 'compaction') { addDivider('CONTEXT COMPACTED · EARLIER TURNS NOW IN TOPIC NOTES'); }
      else if (m.role === 'assistant') {
        b = b || newBlock(false);
        if (m.tool_calls?.length) {
          if (m.content) { b.text = m.content; flushNote(b); }
          m.tool_calls.forEach(c => addChip(b, c.name, c.arguments, c.id));
        } else if (m.content) { b.text = m.content; renderAnswer(b, true); }
      } else if (m.role === 'tool' && b) {
        const rec = b.byId[m.tool_call_id];
        if (rec) endChip(rec, m.content, /^(Error|\[Aborted)/.test(m.content) || m.content.startsWith('Aborted by the user'));
      }
    }
    if (b) b.chips.filter(c => c.result === null).forEach(c => endChip(c, '(no result recorded)', true));
    scrollChat(true);
    return items.filter(m => m.role === 'user').pop()?.content ?? null;
  }

  // ---------------------------------------------------------------- live panel
  const feed = $('#feed');
  const liveBody = $('#liveTab');
  const KIND = { thinking: 'thinking', writing: 'thinking', tool: 'tool', big: 'tool', status: 'status', compaction: 'status', error: 'status', run: 'status', done: 'status' };
  function feedCard(cls, ev, what, inner = '') {
    $('#feedEmpty')?.remove();
    const pin = nearBottom(liveBody);
    const el = document.createElement('div');
    el.className = `ev ${cls}`;
    el.dataset.k = KIND[cls] || 'status';
    const who = ev.agent ? `<span class="who${SUB_AGENTS.includes(ev.agent) ? ' sub' : ''}">${esc(ev.agent)}</span>` : '';
    el.innerHTML = `<div class="ev-head"><time>${ev.t ? clock(ev.t) : ''}</time>${who}<span class="what">${what}</span><span class="dur"></span></div>${inner}`;
    applyFilter(el);
    feed.append(el);
    while (feed.children.length > 1500) feed.firstElementChild.remove();
    if (pin) liveBody.scrollTop = liveBody.scrollHeight;
    if (cls === 'tool' || cls === 'thinking' || cls === 'error') bumpUnread();
    return el;
  }
  function applyFilter(el) { el.classList.toggle('hide', S.liveFilter !== 'all' && el.dataset.k !== S.liveFilter); }
  $('#liveFilters').onclick = e => {
    const b = e.target.closest('.seg');
    if (!b) return;
    S.liveFilter = b.dataset.f;
    $$('#liveFilters .seg').forEach(s => s.classList.toggle('active', s === b));
    $$('.ev', feed).forEach(applyFilter);
  };
  $('#liveClear').onclick = () => { feed.innerHTML = ''; S.lastFeed = null; };

  function feedEvent(ev) {
    const last = S.lastFeed;
    if (ev.type === 'delta') {
      if (ev.kind === 'tool') return;
      const cls = ev.kind === 'reasoning' ? 'thinking' : 'writing';
      if (last && last.cls === cls && last.agent === ev.agent && feed.contains(last.el)) {
        const t = last.el.querySelector('.txt');
        t.textContent += ev.text;
        if (t.textContent.length > 60000) t.textContent = `…${t.textContent.slice(-50000)}`;
        t.scrollTop = t.scrollHeight;
        if (nearBottom(liveBody)) liveBody.scrollTop = liveBody.scrollHeight;
        return;
      }
      const el = feedCard(cls, ev, cls === 'thinking' ? 'THINKING' : 'WRITING', '<div class="txt"></div>');
      el.querySelector('.txt').textContent = ev.text;
      S.lastFeed = { cls, agent: ev.agent, el };
      return;
    }
    S.lastFeed = null;
    switch (ev.type) {
      case 'run_start':
        feedCard('run', ev, `RUN · ${esc(oneLine(ev.text, 60))}`);
        S.pending = {};
        break;
      case 'tool_start': {
        const el = feedCard('tool', ev, `<span class="spinner"></span> ${esc(ev.name)}`,
          `<pre>${esc(pretty(ev.args))}</pre>`);
        (S.pending[ev.agent] ||= []).push({ el, name: ev.name, t: ev.t });
        break;
      }
      case 'tool_end': {
        const list = S.pending[ev.agent] || [];
        const i = list.findIndex(p => p.name === ev.name);
        const p = i >= 0 ? list.splice(i, 1)[0] : { el: feedCard('tool', ev, esc(ev.name)), t: ev.t };
        p.el.classList.toggle('err', ev.error);
        p.el.querySelector('.what').innerHTML = `${ev.error ? '✗' : '✓'} ${esc(ev.name)}`;
        p.el.querySelector('.dur').textContent = `${(ev.t - p.t).toFixed(1)}s · ${fmtTok(ev.chars)} ch`;
        const det = document.createElement('details');
        det.open = ev.error;
        det.innerHTML = `<summary>RESULT${ev.chars > ev.result.length ? ` (first ${ev.result.length} of ${ev.chars} characters)` : ''}</summary><pre>${esc(ev.result)}</pre>`;
        p.el.append(det);
        break;
      }
      case 'compaction':
        feedCard('compaction', ev, `◆ context compacted · ${fmtTok(ev.before)} → ${fmtTok(ev.after)} tokens`);
        break;
      case 'big_result': {
        const r = ev.routed || {};
        feedCard('big', ev, `⇢ ${esc(ev.tool)} result stored · ${fmtTok(r.tokens)} tokens → digest ${fmtTok(ev.shown)}`,
          `<pre>${esc(`digest by ${r.by || '?'} · ${r.rule || ''}\n${r.folder || ''}`)}</pre>`);
        break;
      }
      case 'status':
        feedCard('status', ev, esc(ev.text));
        break;
      case 'turn_end':
        if (ev.agent === 'main') { S.tokens = ev.tokens; S.window = ev.window || S.window; meter(); }
        break;
      case 'done':
        feedCard('done', ev, `✓ DONE${ev.stopped ? ` · ${esc(ev.stopped)}` : ''} · context ${fmtTok(ev.tokens)}`);
        break;
      case 'compacted':
        feedCard('done', ev, ev.compacted ? '✓ COMPACTED' : 'nothing to compact');
        break;
      case 'aborted':
        feedCard('error', ev, '■ STOPPED BY USER');
        break;
      case 'stopping':
        feedCard('status', ev, 'stop requested · ends at the next token or tool call');
        break;
      case 'skill':
        feedCard('status', ev, ev.skill ? `◇ skill loaded · ${esc(ev.skill)}` : '◇ skill removed');
        break;
      case 'error':
        if (ev.run) feedCard('error', ev, `ERROR · ${esc(ev.message)}`);
        break;
      default:
    }
  }

  // ---------------------------------------------------------------- context panel
  const approxTok = s => Math.ceil(String(s || '').length / 4);
  function contextItems(c) {
    const items = [{ group: 'system', role: 'system', title: 'System prompt', text: c.system }];
    if (c.persona) items.push({ group: 'system', role: 'system', title: 'Persona', text: c.persona });
    if (c.instructions) items.push({ group: 'system', role: 'system', title: c.skill ? `Skill · ${c.skill}` : 'Instructions', text: c.instructions });
    if (c.checkpoint) items.push({ group: 'memory', role: 'memory', title: 'Checkpoint (compacted history)', text: c.checkpoint });
    c.topics.forEach(t => items.push({ group: 'memory', role: 'memory', title: `topic · ${t.slug}`, text: t.text }));
    if (c.topics_error) items.push({ group: 'memory', role: 'memory', title: 'topic notes unavailable', text: c.topics_error });
    c.messages.forEach((m, i) => {
      const calls = (m.tool_calls || []).map(t => `→ ${t.name}(${t.arguments})`).join('\n');
      const text = [m.reasoning ? `[thinking]\n${m.reasoning}` : '', m.content, calls].filter(Boolean).join('\n\n');
      const title = m.content ? oneLine(m.content, 90) : calls ? oneLine(calls, 90) : m.reasoning ? '(thinking only)' : '(empty)';
      items.push({ group: 'messages', role: m.role, title: `#${i + 1} ${title}`, text });
    });
    c.tools.forEach(t => items.push({ group: 'tools', role: 'def', title: t.name, text: `${t.description}\n\n${JSON.stringify(t.parameters, null, 2)}` }));
    return items;
  }
  async function loadContext() {
    if (!S.key) return;
    try {
      const c = await api(`/api/chats/${encodeURIComponent(S.key)}/context`);
      if (c.key !== S.key) return;
      S.ctx = { ...c, items: contextItems(c) };
      S.ctxStale = false;
      S.tokens = c.tokens;
      if (c.window) S.window = c.window;
      meter();
      renderContext();
    } catch (e) { $('#ctxList').innerHTML = `<div class="placeholder">${esc(e.message)}</div>`; }
  }
  const countHits = (text, q) => { if (!q) return 0; const t = text.toLowerCase(); let n = 0; let i = t.indexOf(q); while (i >= 0) { n++; i = t.indexOf(q, i + q.length); } return n; };
  function highlight(text, q) {
    if (!q) return esc(text);
    const t = text.toLowerCase();
    let out = ''; let from = 0; let i = t.indexOf(q);
    while (i >= 0) { out += `${esc(text.slice(from, i))}<mark>${esc(text.slice(i, i + q.length))}</mark>`; from = i + q.length; i = t.indexOf(q, from); }
    return out + esc(text.slice(from));
  }
  const GROUPS = { system: 'SYSTEM', memory: 'MEMORY · CHECKPOINT & TOPIC NOTES', messages: 'LIVE MESSAGES', tools: 'TOOLS' };
  function renderContext() {
    const c = S.ctx;
    if (!c) return;
    const q = $('#ctxSearch').value.trim().toLowerCase();
    const list = $('#ctxList');
    list.innerHTML = '';
    let shown = 0; let hits = 0; let group = null; let autoOpen = 3;
    for (const it of c.items) {
      if (S.ctxFilter !== 'all' && it.group !== S.ctxFilter) continue;
      const n = countHits(`${it.title}\n${it.text}`, q);
      if (q && !n) continue;
      if (it.group !== group) {
        group = it.group;
        const h = document.createElement('div');
        h.className = 'ctx-group';
        h.textContent = GROUPS[group];
        list.append(h);
      }
      shown++;
      hits += n;
      const d = document.createElement('details');
      d.className = 'ctx-item';
      d.innerHTML = `<summary><span class="role ${esc(it.role)}">${esc(it.role === 'def' ? 'tool' : it.role)}</span><span class="ttl">${highlight(it.title, q)}</span>${n ? `<span class="hits">${n}</span>` : ''}<span class="tok">~${fmtTok(approxTok(it.text))}</span></summary><div class="body"></div>`;
      const fill = () => { if (!d.dataset.filled) { d.querySelector('.body').innerHTML = highlight(it.text || '(empty)', q); d.dataset.filled = '1'; } };
      d.addEventListener('toggle', () => { if (d.open) fill(); });
      if (q && autoOpen > 0) { d.open = true; fill(); autoOpen--; }
      list.append(d);
    }
    if (!shown) list.innerHTML = `<div class="placeholder">${q ? `No match for “${esc(q)}”.` : 'Nothing in this view yet.'}</div>`;
    const total = c.items.length;
    $('#ctxSummary').innerHTML = q
      ? `<b>${hits}</b> match${hits === 1 ? '' : 'es'} in <b>${shown}</b> of ${total} items · Enter jumps to the next`
      : `<b>${total}</b> items · <b>${fmtTok(c.tokens)}</b> / ${fmtTok(c.window)} tokens · ${c.messages.length} live messages · ${c.topics.length} topic notes · session <span class="mono">${esc(c.session_id)}</span>`;
    markIndex = -1;
  }
  let ctxTimer;
  let markIndex = -1;
  $('#ctxActions').addEventListener('click', async e => {
    const btn = e.target.closest('[data-clear]');
    if (!btn || !S.key) return;
    const scope = btn.dataset.clear;
    const label = scope === 'all' ? 'live messages and checkpoint' : scope;
    if (!confirm(`Clear ${label} from live context? (Session journal on disk is preserved.)`)) return;
    try {
      const c = await api(`/api/chats/${encodeURIComponent(S.key)}/context/clear`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope }),
      });
      S.ctx = { ...c, items: contextItems(c) };
      S.ctxStale = false;
      S.tokens = c.tokens;
      if (c.window) S.window = c.window;
      meter();
      renderContext();
      toast(`Cleared ${label} (${fmtTok(c.tokens)} tokens remaining)`);
    } catch (err) { toast(err.message, true); }
  });
  $('#ctxSearch').addEventListener('input', () => { clearTimeout(ctxTimer); ctxTimer = setTimeout(renderContext, 140); });
  $('#ctxSearch').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    // open every matching item on demand so all marks exist, then step through them
    $$('#ctxList .ctx-item').forEach(d => { if (!d.open && d.querySelector('.hits')) d.open = true; });
    const marks = $$('#ctxList .body mark');
    if (!marks.length) return;
    marks[markIndex]?.classList.remove('cur');
    markIndex = (markIndex + (e.shiftKey ? -1 : 1) + marks.length) % marks.length;
    marks[markIndex].classList.add('cur');
    marks[markIndex].scrollIntoView({ block: 'center', behavior: 'smooth' });
  });
  $('#ctxFilters').onclick = e => {
    const b = e.target.closest('.seg');
    if (!b) return;
    S.ctxFilter = b.dataset.f;
    $$('#ctxFilters .seg').forEach(s => s.classList.toggle('active', s === b));
    renderContext();
  };
  $('#ctxRefresh').onclick = loadContext;
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      setPanel('right', true);
      showTab('context');
      $('#ctxSearch').focus();
      $('#ctxSearch').select();
    } else if (e.key === 'Escape' && !$('#chatMenu').hidden) closeMenu();
  });
  function contextChanged() {
    S.ctxStale = true;
    if (panelOpen('right') && activeTab() === 'context') loadContext();
  }

  // ---------------------------------------------------------------- skill panel (one skill per chat)
  async function loadSkills() {
    try { S.skills = await api('/api/skills'); } catch (e) { $('#skillList').innerHTML = `<div class="placeholder">${esc(e.message)}</div>`; return; }
    renderSkills();
    renderSchedule();
  }
  function renderSkills() {
    $('#skillDot').hidden = !S.skill;
    if (!S.skills) return;
    const opts = [{ name: null, description: 'No skill: base prompt, AGENTS.md and persona only.' }, ...S.skills];
    $('#skillList').innerHTML = opts.map(o => {
      const on = (o.name || null) === (S.skill || null);
      return `<button class="skill-opt${on ? ' on' : ''}" role="radio" aria-checked="${on}" data-name="${esc(o.name || '')}"${S.busy ? ' disabled title="The agent is running; change the skill when it is idle"' : ''}>`
        + `<span class="radio" aria-hidden="true"></span><b>${esc(o.name || 'None')}</b><small>${esc(o.description || '')}</small></button>`;
    }).join('') + (S.skills.length ? '' : '<div class="placeholder">The skill library has no &lt;name&gt;.md files.</div>');
  }
  $('#skillList').onclick = async e => {
    const b = e.target.closest('.skill-opt');
    if (!b || b.disabled || !S.key) return;
    const name = b.dataset.name || null;
    if (name === S.skill) return;
    try {
      const r = await api(`/api/chats/${encodeURIComponent(S.key)}/skill`, {
        method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name }) });
      S.skill = r.skill;
      renderSkills();
      contextChanged();
      toast(r.skill ? `Skill “${r.skill}” loaded for this chat` : 'Skill removed from this chat');
    } catch (err) { toast(err.message, true); }
  };

  // ---------------------------------------------------------------- socket
  function connState() {
    const c = $('#connState');
    const open = S.ws && S.ws.readyState === WebSocket.OPEN;
    c.className = `conn ${!open ? 'bad' : S.busy ? 'busy' : 'ok'}`;
    c.lastElementChild.textContent = !open ? 'reconnecting…' : S.busy ? `agent ${S.busy === 'compact' ? 'compacting' : 'working'}` : 'agent ready';
  }
  function send(msg) {
    if (!S.ws || S.ws.readyState !== WebSocket.OPEN) { toast('Not connected to the agent yet.', true); return false; }
    S.ws.send(JSON.stringify(msg));
    return true;
  }
  function connect(key) {
    if (S.ws) { S.wsWanted = false; S.ws.close(); }
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(key)}${token ? `?token=${encodeURIComponent(token)}` : ''}`);
    S.ws = ws;
    S.wsWanted = true;
    ws.onopen = () => { S.retry = 0; connState(); };
    ws.onmessage = m => {
      if (ws !== S.ws) return;
      const ev = JSON.parse(m.data);
      if (ev.type === 'hello') { hello(ev); return; }
      if (ev.seq && ev.seq <= S.seq) return;
      if (ev.seq) S.seq = ev.seq;
      handle(ev);
    };
    ws.onclose = e => {
      if (ws !== S.ws) return;
      connState();
      if (e.code === 4404) { toast('That chat no longer exists; starting a new one.', true); newChat(); return; }
      if (S.wsWanted) setTimeout(() => { if (ws === S.ws) openChat(key, { reconnect: true }); }, Math.min(10000, 800 * 2 ** S.retry++));
    };
  }
  function hello(h) {
    S.seq = h.seq;
    S.skill = h.skill || null;
    renderSkills();
    S.tokens = h.tokens || S.tokens;
    S.window = h.window || S.window;
    meter();
    feed.innerHTML = '';
    S.lastFeed = null;
    S.pending = {};
    // a running chat: rebuild its live block from the buffered events of the current run
    const lastRun = h.busy ? h.activity.map(e => e.type).lastIndexOf('run_start') : -1;
    S.replaying = true;
    h.activity.forEach((ev, i) => { feedEvent(ev); if (lastRun >= 0 && i >= lastRun) chatEvent(ev); });
    S.replaying = false;
    S.lastUserText = null;
    if (!h.activity.length) feed.innerHTML = '<div class="placeholder" id="feedEmpty">Agent activity appears here: thinking, tool calls, compaction, sub-agents.</div>';
    S.unread = 0;
    $('#liveBadge').hidden = true;
    setBusy(h.busy);
  }
  function handle(ev) {
    feedEvent(ev);
    chatEvent(ev);
    if (ev.type === 'run_start') { setBusy(ev.run); refreshTasks(); }
    if (['done', 'aborted', 'compacted'].includes(ev.type) || (ev.type === 'error' && ev.run)) {
      setBusy(null);
      if (ev.tokens != null) { S.tokens = ev.tokens; meter(); }
      contextChanged();
      renderTree();      // the agent may have created or changed files
      refreshChats();
  refreshTasks();
  loadDream();
  refreshStudios();
      refreshTasks();
    }
    if (ev.type === 'error' && !ev.run) toast(ev.message, true);
    if (ev.type === 'error' && ev.run) toast(`Agent error: ${ev.message}`, true);
    if (ev.type === 'compaction' || ev.type === 'tool_end') S.ctxStale = true;
    if (ev.type === 'skill') { S.skill = ev.skill || null; renderSkills(); contextChanged(); }
  }

  // ---------------------------------------------------------------- chats
  async function openChat(key, { reconnect = false } = {}) {
    let items;
    try {
      items = await api(`/api/chats/${encodeURIComponent(key)}/transcript`);
    } catch (e) {
      if (e.status === 404 && !reconnect) { await newChat(); return; }
      if (reconnect) { setTimeout(() => openChat(key, { reconnect: true }), Math.min(10000, 800 * 2 ** S.retry++)); connState(); return; }
      toast(e.message, true);
      return;
    }
    S.key = key;
    S.seq = 0;
    localStorage.setItem('breezeman-chat', key);
    if (location.hash !== `#${key}`) history.replaceState(null, '', `#${key}`);
    S.lastUserText = renderTranscript(items);
    S.ctx = null;
    S.ctxStale = true;
    $('#ctxList').innerHTML = '';
    $('#ctxSummary').textContent = '';
    if (!reconnect) { S.tokens = 0; meter(); }
    connect(key);
    contextChanged();
    updateTitle();
    const task = S.tasks.find(t => t.chat_key === key);
    const prev = S.activeTaskId;
    S.activeTaskId = task ? task.id : null;
    syncWorkspaceHeader(task || null);
    if (prev !== S.activeTaskId) {
      S.attachments = [];
      renderAttachments();
      setTarget('');
      renderTree();
    }
    renderTasks();
    renderSchedule();
    if (!reconnect) prompt_.focus();
  }
  async function newChat() {
    closeStudio();
    closeDreamStage();
    closePromptLoopStage();
    try {
      const { key } = await api('/api/chats', { method: 'POST' });
      await openChat(key);
      await refreshChats();
    } catch (e) { toast(e.message, true); }
  }
  $('#dreamBtn').onclick = () => ($('#dreamStage').hidden ? openDreamStage() : closeDreamStage());
  async function refreshChats() {
    try { S.chats = await api('/api/chats'); } catch { return; }
    updateTitle();
    if (!$('#chatMenu').hidden) renderChatList();
  }
  function updateTitle() {
    const c = S.chats.find(x => x.key === S.key);
    const title = c?.title || 'New chat';
    $('#chatTitle').textContent = title;
    document.title = `${title} · Breezeman`;
  }
  function renderChatList() {
    const q = $('#chatFilter').value.trim().toLowerCase();
    const rows = S.chats.filter(c => !q || `${c.title} ${c.key}`.toLowerCase().includes(q));
    $('#chatList').innerHTML = rows.length ? rows.map(c =>
      `<button class="chat-item${c.key === S.key ? ' current' : ''}" data-key="${esc(c.key)}" role="option"><b>${esc(c.title || 'New chat')}</b><small>${esc(ago(c.updated))} · ${c.messages} messages · ${esc(c.key)}</small>${c.busy ? '<span class="tag">● RUNNING</span>' : ''}</button>`).join('')
      : '<div class="placeholder">No chats match.</div>';
  }
  function closeMenu() { $('#chatMenu').hidden = true; $('#chatPickerBtn').setAttribute('aria-expanded', 'false'); }
  $('#chatPickerBtn').onclick = async () => {
    const menu = $('#chatMenu');
    if (!menu.hidden) { closeMenu(); return; }
    menu.hidden = false;
    $('#chatPickerBtn').setAttribute('aria-expanded', 'true');
    $('#chatFilter').value = '';
    renderChatList();
    $('#chatFilter').focus();
    await refreshChats();
  };
  $('#chatFilter').addEventListener('input', renderChatList);
  $('#chatList').onclick = e => {
    const b = e.target.closest('.chat-item');
    if (!b) return;
    closeMenu();
    if (b.dataset.key !== S.key) openChat(b.dataset.key);
  };
  document.addEventListener('click', e => { if (!$('#chatMenu').hidden && !e.target.closest('#chatPicker')) closeMenu(); });
  window.addEventListener('hashchange', () => {
    const key = decodeURIComponent(location.hash.slice(1));
    if (key && key !== S.key) openChat(key);
  });

  // ---------------------------------------------------------------- start
  setTarget('');
  renderTree();
  health();
  setInterval(health, 30000);
  refreshChats();
  refreshTasks();
  loadDream();
  refreshStudios();
  const initial = decodeURIComponent(location.hash.slice(1)) || localStorage.getItem('breezeman-chat');
  if (initial) openChat(initial); else newChat();
})();
