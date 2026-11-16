(() => {
  'use strict';

  const get = id => document.getElementById(id);
  const format = value => Number(value).toLocaleString();
  const taskId = new URLSearchParams(location.search).get('task') || '';
  const compactNumber = new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: 1});
  const narrow = matchMedia('(max-width: 980px)');
  const layout = get('layout');
  const conversation = get('conversation');
  const prompt = get('prompt');
  const outputFile = get('output-file');
  const outputFrame = get('output-frame');
  const attached = new Set();
  const expanded = new Set(['']);
  const directories = new Map();
  const tabs = ['activity', 'context', 'output'];
  const MAX_UPLOAD = 128 * 1024 * 1024;
  const statusLabels = {ready: 'Ready', running: 'Running', waiting: 'Needs review', done: 'Done',
    failed: 'Needs attention', interrupted: 'Interrupted', pending: 'Queued', skipped: 'Skipped', retrying: 'Retried',
    open: 'Open', closed: 'Closed'};
  const roles = {
    system: 'System instructions', runtime: 'Runtime notice', checkpoint: 'Checkpoint summary',
    requirements: 'Pinned requirements', user: 'User message', assistant: 'Assistant message',
    tool: 'Tool result', schemas: 'Tool definitions'
  };
  let state = {messages: [], compactions: [], busy: false, draft: '', reasoning: '', workspace: 'Workspace'};
  let folder = '';
  let connected = false;
  let pending = false;
  let uploading = false;
  let view = 'current';
  let inspectorTab = 'context';
  let outputs = [];
  let selectedOutput = null;
  let outputRequest = 0;
  let compressionTimer;
  let taskListSignature;
  let taskRequest = 0;
  let profiles;
  let workflowStep;

  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }

  async function api(path, options) {
    const url = ['/api/tasks', '/api/profiles'].includes(path) ? path : taskUrl(path);
    const response = await fetch(url, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed (' + response.status + ').');
    return body;
  }

  function jsonRequest(body) {
    return {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
  }

  function taskUrl(path) {
    if (!taskId) return path;
    return path + (path.includes('?') ? '&' : '?') + 'task=' + encodeURIComponent(taskId);
  }

  function taskLink(id) {
    return id ? '/?task=' + encodeURIComponent(id) : '/';
  }

  function badge(status) {
    const node = element('span', 'task-badge', statusLabels[status] || statusLabels.ready);
    node.dataset.status = status || 'ready';
    return node;
  }

  async function refreshTasks() {
    const request = ++taskRequest;
    try {
      const {entries} = await api('/api/tasks');
      if (request !== taskRequest) return;
      const reviews = entries.filter(task => task.status === 'waiting').length;
      get('review-count').textContent = format(reviews);
      get('review-count').hidden = !reviews;
      get('workspace-toggle').title = reviews ? format(reviews) + ' tasks awaiting review' : '';
      const line = get('task-list-error');
      const missing = !entries.some(task => task.id === taskId);
      line.hidden = !missing;
      if (missing) line.textContent = 'Task unavailable. Select another task.';
      const signature = JSON.stringify(entries);
      if (taskListSignature === signature) return;
      taskListSignature = signature;
      const list = get('task-list');
      const focused = document.activeElement?.dataset.taskLink;
      list.replaceChildren();
      for (const task of entries) {
        const item = element('li');
        const link = element('a', 'task-link');
        link.href = taskLink(task.id);
        link.dataset.taskLink = task.id;
        if (task.id === taskId) link.setAttribute('aria-current', 'page');
        link.append(element('span', 'task-link-title', task.title), badge(task.status));
        item.append(link);
        list.append(item);
        if (focused === task.id) link.focus({preventScroll: true});
      }
    } catch (error) {
      if (request !== taskRequest) return;
      get('task-list-error').textContent = 'Could not load tasks. ' + error.message;
      get('task-list-error').hidden = false;
    }
  }

  function renderTask() {
    if (!state.task?.id) return;
    get('chat-heading').textContent = state.task.title;
    layout.dataset.task = state.task.id;
    document.title = state.task.title + ' · Kent WebIO';
    const close = get('task-close');
    close.hidden = false;
    close.textContent = state.task.closed ? 'Reopen task' : 'Close task';
    const target = get('task-profiles');
    const active = [state.task.persona, ...state.task.skills].filter(Boolean);
    target.replaceChildren(...active.map(name => element('span', 'profile-chip', name)));
    target.hidden = !active.length;
  }

  function panel(name, open) {
    get(name + '-panel').hidden = !open;
    get(name + '-toggle').setAttribute('aria-expanded', String(open));
    layout.classList.toggle('hide-' + name, !open);
    if ((name === 'context' && !open) || (name === 'workspace' && open)) expandOutput(false);
    if (open && narrow.matches) {
      panel(name === 'workspace' ? 'context' : 'workspace', false);
    }
    if (name === 'context' && open && inspectorTab === 'output') renderPreview();
  }

  function expandOutput(expanded) {
    layout.classList.toggle('output-expanded', expanded);
    const button = get('output-expand');
    button.setAttribute('aria-pressed', String(expanded));
    button.textContent = expanded ? 'Collapse' : 'Expand';
  }

  function initInspectorResize() {
    const divider = get('inspector-resize');
    const inspector = get('context-panel');
    const storageKey = 'kent-webio.inspector-width';
    const property = '--inspector-width';
    let drag;

    function bounds() {
      const style = getComputedStyle(layout);
      const pixels = name => parseFloat(style.getPropertyValue(name));
      const min = pixels('--inspector-min');
      const max = Math.max(min, layout.clientWidth - pixels('--left') - pixels('--chat-min'));
      return {min, max};
    }

    function resize(width, {min, max} = bounds()) {
      layout.style.setProperty(property, Math.min(max, Math.max(min, Math.round(width))) + 'px');
    }

    function rememberWidth() {
      try {
        const width = parseInt(layout.style.getPropertyValue(property), 10);
        if (Number.isFinite(width)) localStorage.setItem(storageKey, String(width));
        else localStorage.removeItem(storageKey);
      } catch {
        // The divider still works when browser storage is unavailable.
      }
    }

    try {
      const saved = Number(localStorage.getItem(storageKey));
      if (Number.isSafeInteger(saved) && saved > 0) layout.style.setProperty(property, saved + 'px');
    } catch {
      // Use the CSS default when browser storage is unavailable.
    }

    const observer = new ResizeObserver(() => {
      if (!divider.getClientRects().length) return;
      const {min, max} = bounds();
      const width = Math.round(inspector.getBoundingClientRect().width);
      divider.setAttribute('aria-valuemin', String(min));
      divider.setAttribute('aria-valuemax', String(max));
      divider.setAttribute('aria-valuenow', String(width));
      divider.setAttribute('aria-valuetext', width + ' pixels');
    });
    for (const node of [layout, inspector, get('workspace-panel')]) observer.observe(node);

    divider.addEventListener('pointerdown', event => {
      if (!event.isPrimary || event.button !== 0 || drag) return;
      divider.focus({preventScroll: true});
      divider.setPointerCapture(event.pointerId);
      drag = {id: event.pointerId, x: event.clientX, lastX: event.clientX,
        width: inspector.getBoundingClientRect().width, bounds: bounds()};
      layout.classList.add('resizing-inspector');
    });
    divider.addEventListener('pointermove', event => {
      if (event.pointerId === drag?.id && event.clientX !== drag.lastX) {
        drag.lastX = event.clientX;
        resize(drag.width + drag.x - event.clientX, drag.bounds);
      }
    });
    divider.addEventListener('lostpointercapture', event => {
      if (event.pointerId !== drag?.id) return;
      drag = undefined;
      layout.classList.remove('resizing-inspector');
      rememberWidth();
    });
    divider.addEventListener('dblclick', () => {
      layout.style.removeProperty(property);
      rememberWidth();
    });
    divider.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const range = bounds();
      const width = inspector.getBoundingClientRect().width;
      const sizes = {ArrowLeft: width + 24, ArrowRight: width - 24, Home: range.min, End: range.max};
      resize(sizes[event.key], range);
      rememberWidth();
    });
  }

  function showInspectorTab(name) {
    inspectorTab = name;
    layout.classList.toggle('output-open', name === 'output');
    for (const tab of tabs) {
      const active = name === tab;
      get(tab + '-tab').setAttribute('aria-selected', String(active));
      get(tab + '-tab').tabIndex = active ? 0 : -1;
      get(tab + '-view').hidden = !active;
    }
    if (name === 'output') renderPreview();
    else expandOutput(false);
  }

  function downloadUrl(path) {
    return taskUrl('/api/download?path=' + encodeURIComponent(path));
  }

  function openOutput(path) {
    selectedOutput = path;
    showInspectorTab('output');
    panel('context', true);
    get('output-tab').focus();
    if (!outputs.some(entry => entry.path === path)) {
      get('output-empty').textContent = 'Locating ' + path + '…';
      refreshOutputs();
    }
  }

  function renderPreview(reload = false) {
    if (inspectorTab !== 'output' || get('context-panel').hidden) return;
    const output = selectedOutput ? outputs.find(entry => entry.path === selectedOutput) : outputs[0];
    const download = get('output-download');
    outputFrame.hidden = !output;
    download.hidden = !output;
    get('output-empty').hidden = Boolean(output);
    get('output-expand').disabled = !output;
    if (!output) {
      expandOutput(false);
      outputFrame.removeAttribute('src');
      outputFile.value = '';
      outputFile.removeAttribute('title');
      if (selectedOutput) get('output-empty').textContent = 'HTML file unavailable · ' + selectedOutput;
      return;
    }
    selectedOutput = output.path;
    outputFile.value = output.path;
    outputFile.title = output.path;
    download.href = downloadUrl(output.path);
    const prefix = taskId ? '/tasks/' + encodeURIComponent(taskId) : '';
    const url = prefix + '/preview/' + output.path.split('/').map(encodeURIComponent).join('/') + '?v=' + output.version;
    if (reload || outputFrame.getAttribute('src') !== url) outputFrame.src = url;
  }

  async function refreshOutputs(reload = false) {
    const request = ++outputRequest;
    const errorLine = get('output-error');
    try {
      const result = await api('/api/outputs');
      if (request !== outputRequest) return;
      outputs = result.entries;
      if (selectedOutput && !outputs.some(entry => entry.path === selectedOutput)) {
        selectedOutput = outputs[0]?.path || null;
      }
      outputFile.replaceChildren();
      for (const {path} of outputs) outputFile.add(new Option(path, path));
      if (!outputs.length) outputFile.add(new Option('No HTML files', ''));
      outputFile.disabled = !outputs.length;
      outputFile.value = selectedOutput || outputs[0]?.path || '';
      get('output-count').textContent = format(outputs.length);
      get('output-count').hidden = !outputs.length;
      get('output-empty').textContent = 'Ask Kent to save a slide deck, diagram, or report as HTML, or upload an HTML file.';
      errorLine.hidden = true;
      renderPreview(reload);
    } catch (error) {
      if (request !== outputRequest) return;
      get('output-empty').textContent = 'Refresh to check for HTML files.';
      errorLine.textContent = 'Could not list HTML outputs. ' + error.message;
      errorLine.hidden = false;
    }
  }

  function updateControls() {
    const closed = Boolean(state.task?.closed);
    const busy = !connected || state.busy || pending || uploading;
    const locked = busy || closed;
    const stop = get('stop-button');
    const send = get('send-button');
    stop.hidden = !state.busy;
    stop.disabled = !connected || pending || state.status === 'Stopping';
    send.hidden = state.busy;
    send.disabled = locked || !prompt.value.trim();
    prompt.disabled = closed;
    prompt.placeholder = closed ? 'Task is closed. Reopen it to send messages.' : 'Message Kent…';
    get('upload-button').disabled = locked;
    get('folder-button').disabled = locked;
    get('clear-chat').disabled = locked || !state.messages.length;
    get('compact-button').disabled = locked || !state.context?.entries.some(row => row.role === 'user' || row.role === 'assistant');
    get('workflow-action').disabled = locked;
    get('task-close').disabled = !connected || state.busy || pending || uploading;
    for (const btn of get('file-tree').querySelectorAll('.tree-action[data-mutating]')) {
      btn.disabled = locked;
    }
  }

  function fileFeedback(text, error = false) {
    get('file-feedback').textContent = text;
    get('file-feedback').classList.toggle('error', error);
  }

  function chatFeedback(text, error = false) {
    const line = get('chat-feedback');
    line.textContent = text;
    line.classList.toggle('error', error);
    line.hidden = !text;
  }

  function drawAttachments() {
    const target = get('attachments');
    target.replaceChildren();
    for (const path of attached) {
      const chip = element('span', 'attachment', path);
      const remove = element('button', '', '×');
      remove.type = 'button';
      remove.setAttribute('aria-label', 'Remove ' + path);
      remove.addEventListener('click', () => {
        attached.delete(path);
        drawAttachments();
        renderTree();
      });
      chip.append(remove);
      target.append(chip);
    }
    target.hidden = attached.size === 0;
  }

  function toggleAttachment(path) {
    if (attached.has(path)) attached.delete(path);
    else if (attached.size < 32) attached.add(path);
    else {
      fileFeedback('You can attach up to 32 files to a message.', true);
      return;
    }
    drawAttachments();
    renderTree();
  }

  function folderRow(entry, root = false) {
    const row = element('li');
    const open = expanded.has(entry.path);
    const line = element('div', 'tree-row' + (entry.path === folder ? ' selected-folder' : ''));
    const button = element('button', 'tree-label folder');
    button.type = 'button';
    button.title = root ? 'Select workspace root' : entry.path;
    button.dataset.treeControl = 'folder:' + entry.path;
    button.setAttribute('aria-expanded', String(open));
    button.append(element('span', 'tree-glyph', open ? '▾' : '▸'), element('span', 'filename', entry.name));
    button.addEventListener('click', async () => {
      folder = entry.path;
      if (!root && open) expanded.delete(entry.path);
      else expanded.add(entry.path);
      renderTree();
      if (expanded.has(entry.path)) await refreshTree();
    });
    line.append(button);
    if (!root) {
      const rename = element('button', 'tree-action', '✎');
      rename.type = 'button';
      rename.dataset.mutating = '1';
      rename.dataset.treeControl = 'rename:' + entry.path;
      rename.title = 'Rename ' + entry.name;
      rename.setAttribute('aria-label', rename.title);
      rename.addEventListener('click', () => openRenameDialog(entry));
      const del = element('button', 'tree-action danger', '×');
      del.type = 'button';
      del.dataset.mutating = '1';
      del.dataset.treeControl = 'delete:' + entry.path;
      del.title = 'Delete ' + entry.name;
      del.setAttribute('aria-label', del.title);
      del.addEventListener('click', () => openDeleteDialog(entry));
      line.append(rename, del);
    }
    row.append(line);
    if (open) {
      const list = element('ul');
      const entries = directories.get(entry.path);
      if (!entries?.length) list.append(element('li', 'tree-empty', entries ? 'Empty folder' : 'Loading…'));
      for (const child of entries || []) list.append(child.directory ? folderRow(child) : fileRow(child));
      row.append(list);
    }
    return row;
  }

  function fileRow(entry) {
    const row = element('li', 'tree-row');
    const previewable = /\.html?$/i.test(entry.name);
    const label = element(previewable ? 'button' : 'span', 'tree-label');
    if (previewable) {
      label.type = 'button';
      label.dataset.treeControl = 'preview:' + entry.path;
      label.setAttribute('aria-label', 'Preview ' + entry.name);
      label.title = 'Preview ' + entry.path;
      label.addEventListener('click', () => openOutput(entry.path));
    } else label.title = entry.path + ' · ' + format(entry.bytes) + ' bytes';
    label.append(element('span', 'tree-glyph', '▧'), element('span', 'filename', entry.name));
    const attach = element('button', 'tree-action', attached.has(entry.path) ? '✓' : '+');
    attach.type = 'button';
    attach.dataset.treeControl = 'attach:' + entry.path;
    attach.setAttribute('aria-label', 'Attach ' + entry.name);
    attach.setAttribute('aria-pressed', String(attached.has(entry.path)));
    attach.title = 'Attach to message';
    attach.addEventListener('click', () => toggleAttachment(entry.path));
    const download = element('a', 'tree-action', '↓');
    download.href = downloadUrl(entry.path);
    download.title = 'Download ' + entry.name;
    download.setAttribute('aria-label', download.title);
    const rename = element('button', 'tree-action', '✎');
    rename.type = 'button';
    rename.dataset.mutating = '1';
    rename.dataset.treeControl = 'rename:' + entry.path;
    rename.title = 'Rename ' + entry.name;
    rename.setAttribute('aria-label', rename.title);
    rename.addEventListener('click', () => openRenameDialog(entry));
    const del = element('button', 'tree-action danger', '×');
    del.type = 'button';
    del.dataset.mutating = '1';
    del.dataset.treeControl = 'delete:' + entry.path;
    del.title = 'Delete ' + entry.name;
    del.setAttribute('aria-label', del.title);
    del.addEventListener('click', () => openDeleteDialog(entry));
    row.append(label, attach, download, rename, del);
    return row;
  }

  function renderTree() {
    const tree = get('file-tree');
    const focused = document.activeElement?.dataset.treeControl;
    const root = element('ul');
    root.append(folderRow({name: state.workspace, path: ''}, true));
    tree.replaceChildren(root);
    if (focused) [...tree.querySelectorAll('[data-tree-control]')]
      .find(control => control.dataset.treeControl === focused)?.focus({preventScroll: true});
    get('destination').textContent = folder ? 'Upload to ' + folder + '/' : 'Upload to workspace root';
    updateControls();
  }

  async function refreshTree() {
    await Promise.all([...expanded].map(async path => {
      try {
        const result = await api('/api/files?path=' + encodeURIComponent(path));
        directories.set(path, result.entries);
      } catch (error) {
        directories.delete(path);
        if (path) expanded.delete(path);
        if (folder === path) folder = '';
        fileFeedback(error.message, true);
      }
    }));
    renderTree();
  }

  async function uploadFiles(files) {
    if (!files.length || uploading || state.busy || pending || state.task?.closed) return;
    uploading = true;
    updateControls();
    const destination = folder;
    const problems = [];
    let saved = 0;
    for (const file of files) {
      if (file.size > MAX_UPLOAD) {
        problems.push(file.name + ': exceeds the 128 MiB limit.');
        continue;
      }
      const path = destination ? destination + '/' + file.name : file.name;
      fileFeedback('Uploading ' + file.name + '…');
      try {
        await api('/api/files?path=' + encodeURIComponent(path), {
          method: 'PUT', headers: {'Content-Type': 'application/octet-stream'}, body: file
        });
        saved++;
      } catch (error) {
        problems.push(file.name + ': ' + error.message);
      }
    }
    expanded.add(destination);
    await Promise.all([refreshTree(), refreshOutputs()]);
    const outcome = saved ? format(saved) + (saved === 1 ? ' file uploaded.' : ' files uploaded.') : '';
    fileFeedback([outcome, ...problems].filter(Boolean).join(' '), problems.length > 0);
    uploading = false;
    updateControls();
  }

  function atBottom() {
    return conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight < 100;
  }

  function scrollChat() {
    conversation.scrollTop = conversation.scrollHeight;
  }

  function addMessage(message) {
    const item = element('article', 'message ' + message.role);
    const user = message.role === 'user';
    const header = element('div', 'message-label');
    const avatar = element('span', 'avatar ' + (user ? 'user-avatar' : 'kent-avatar'), user ? 'Y' : 'K');
    avatar.setAttribute('aria-hidden', 'true');
    header.append(avatar, document.createTextNode(user ? 'You' : 'Kent'));
    item.append(header);
    if (message.reasoning) {
      const thinking = element('details', 'thinking');
      thinking.append(element('summary', '', 'Thinking'), element('div', 'thinking-text', message.reasoning));
      item.append(thinking);
    }
    if (message.text) {
      const body = element('div', 'message-text');
      if (message.markdown_html) {
        body.classList.add('formatted-message');
        body.innerHTML = message.markdown_html;
      } else body.textContent = message.text;
      item.append(body);
    }
    if (message.files?.length) {
      const files = element('div', 'message-files');
      for (const path of message.files) files.append(element('span', 'message-file', path));
      item.append(files);
    }
    if (message.outputs?.length) {
      const cards = element('ul', 'deliverables');
      cards.setAttribute('aria-label', 'Deliverables');
      for (const path of message.outputs) {
        const name = path.split('/').pop();
        const card = element('li', 'deliverable');
        const file = element('div', 'deliverable-file');
        const filename = element('strong', '', name);
        filename.title = path;
        file.append(element('span', 'deliverable-format', 'HTML'), filename);
        const actions = element('div', 'deliverable-actions');
        const preview = element('button', 'button deliverable-preview', 'Preview');
        preview.type = 'button';
        preview.setAttribute('aria-label', 'Preview ' + name);
        preview.addEventListener('click', () => openOutput(path));
        const download = element('a', 'quiet deliverable-download', 'Download');
        download.href = downloadUrl(path);
        download.setAttribute('aria-label', 'Download ' + name);
        actions.append(preview, download);
        card.append(file, actions);
        cards.append(card);
      }
      item.append(cards);
    }
    get('messages').append(item);
  }

  function renderThinking() {
    get('live-thinking').hidden = !state.reasoning;
    get('live-thinking-text').textContent = state.reasoning || '';
  }

  function renderElapsed() {
    const seconds = state.busy && state.status_since
      ? Math.max(0, Math.floor(Date.now() / 1000 - state.status_since))
      : null;
    get('activity-elapsed').textContent = seconds === null ? '' :
      seconds < 60 ? seconds + 's' : Math.floor(seconds / 60) + 'm ' + (seconds % 60) + 's';
  }

  function renderChat(stick = false) {
    const review = Boolean(state.workflow?.gate) && !state.busy;
    get('welcome').hidden = state.messages.length > 0 || state.busy || review;
    get('review-card').hidden = !review;
    get('activity').hidden = !state.busy;
    get('reply-draft').textContent = state.draft || '';
    const activityText = get('activity-text');
    const status = state.status || 'Working';
    if (activityText.textContent !== status) activityText.textContent = status;
    const detail = get('activity-detail');
    detail.hidden = !state.status_detail;
    get('activity-detail-text').textContent = state.status_detail || '';
    if (!state.busy) {
      detail.open = false;
      get('live-thinking').open = false;
    }
    renderThinking();
    renderElapsed();
    if (stick) scrollChat();
  }

  function renderMeter() {
    const context = state.context;
    if (!context) return;
    get('meter-heading').textContent = context.scope === 'workflow' ? 'Workflow context' : 'Working context';
    get('model-name').textContent = context.model ? context.provider + ' · ' + context.model : 'KentC Agent';
    const value = get('meter-value');
    value.replaceChildren(document.createTextNode(format(context.tokens) + (context.window ? ' / ' + format(context.window) : ' ')));
    value.append(element('small', '', ' tokens'));
    const percent = context.window ? Math.min(100, context.tokens / context.window * 100) : 0;
    const near = context.threshold != null && context.tokens >= context.threshold;
    const shortcut = get('context-shortcut');
    const usage = '≈ ' + compactNumber.format(context.tokens) + (context.window ? ' / ' + compactNumber.format(context.window) : '');
    get('context-shortcut-usage').textContent = usage;
    shortcut.title = format(context.tokens) + ' estimated tokens' + (context.window
      ? ' of ' + format(context.window) : ' · model window pending');
    shortcut.setAttribute('aria-label', 'Open context details · ' + shortcut.title);
    shortcut.classList.toggle('near', near);
    shortcut.classList.toggle('compacting', state.phase === 'compacting');
    const meter = get('meter');
    meter.setAttribute('aria-valuenow', String(Math.round(percent)));
    meter.setAttribute('aria-valuetext', format(context.tokens) + ' estimated tokens' +
      (context.window ? ' of ' + format(context.window) : ', window pending'));
    meter.classList.toggle('near', near);
    get('meter-fill').style.width = percent + '%';
    get('meter-threshold').hidden = !context.window;
    if (context.window) get('meter-threshold').style.left = Math.min(99.5, context.threshold / context.window * 100) + '%';
    get('remaining').textContent = context.window ? format(Math.max(0, context.window - context.tokens)) : '—';
    get('threshold').textContent = context.threshold === null ? '—' : format(context.threshold);
    get('meter-caption').textContent = context.window
      ? 'Estimated usage · deployment ' + format(context.deployment) + ' · density ×' + context.density
      : 'Model window pending first request';
    const status = get('context-status');
    status.textContent = state.phase === 'compacting' ? 'Compressing' : state.busy ? 'Active' : 'Ready';
    status.className = 'count-badge' + (state.phase === 'compacting' ? ' compacting' : state.busy ? ' working' : '');
    get('compression-progress').hidden = state.phase !== 'compacting';
  }

  function renderEntries() {
    const request = view === 'request';
    const source = request ? state.request : state.context;
    const target = get('entry-list');
    const open = new Set([...target.querySelectorAll('details[open]')].map(node => node.dataset.entry));
    target.replaceChildren();
    get('current-view').setAttribute('aria-pressed', String(!request));
    get('request-view').setAttribute('aria-pressed', String(request));
    const entries = source?.entries || [];
    get('entry-count').textContent = entries.length ? format(entries.length) + ' entries' : '';
    const note = get('inspection-note');
    if (!request) note.textContent = 'Live messages retained for the next turn. Item sizes are estimates.';
    else if (!source) note.textContent = 'Send a message to inspect the model request.';
    else note.textContent = format(source.tokens) + (source.estimated ? ' estimated' : ' reported') +
      ' input tokens · ' + format(source.output) + ' reply budget';
    entries.forEach((entry, index) => {
      const key = view + ':' + index + ':' + entry.role;
      const block = element('details', 'entry ' + entry.role);
      block.dataset.entry = key;
      block.open = open.has(key);
      const heading = element('summary');
      heading.append(element('span', 'entry-label', roles[entry.role] || entry.role),
        element('span', 'entry-tokens', '≈ ' + format(entry.tokens)));
      const preview = entry.preview || '(Empty message)';
      block.append(heading, element('pre', '', preview + (entry.truncated ? '\n… preview clipped' : '')));
      target.append(block);
    });
  }

  function renderCompressions() {
    const target = get('compression-list');
    target.replaceChildren();
    if (!state.compactions.length) {
      target.append(element('p', 'inspection-note', 'No compression events yet.'));
      return;
    }
    for (const change of [...state.compactions].reverse()) {
      const item = element('div', 'compression-item');
      const date = new Date(change.time * 1000);
      item.append(element('span', '', 'Checkpoint ' + change.id + ' · ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})),
        element('strong', '', format(change.before) + ' → ' + format(change.after) + ' tokens'));
      target.append(item);
    }
  }

  function showCompression(change) {
    const notice = get('compression-notice');
    clearTimeout(compressionTimer);
    notice.hidden = !change;
    if (!change) return;
    notice.textContent = 'Context compressed · ' + compactNumber.format(change.before) + ' → ' + compactNumber.format(change.after) + ' tokens';
    notice.title = format(change.before) + ' → ' + format(change.after) + ' estimated tokens';
    compressionTimer = setTimeout(() => { notice.hidden = true; }, 7000);
  }

  function renderFeedback() {
    const text = state.error ? [state.failed_stage, state.error].filter(Boolean).join(' · ') : state.notice;
    chatFeedback(text || '', Boolean(state.error));
  }

  function renderActivity() {
    const status = state.run_state || 'ready';
    const indicator = get('run-status');
    indicator.textContent = statusLabels[status] || statusLabels.ready;
    indicator.className = 'task-badge';
    indicator.dataset.status = status;
    get('activity-dot').hidden = !state.busy;
    const workflow = state.workflow;
    const steps = get('workflow-steps');
    get('workflow-steps-section').hidden = !workflow;
    steps.replaceChildren();
    for (const step of workflow?.steps || []) {
      const item = element('li');
      const title = element('div', 'step-title', step.id.replaceAll('_', ' '));
      if (step.kind === 'ask') title.append(element('span', 'inspection-note', 'Human review'));
      if (step.status === 'waiting' && !state.busy) {
        const review = element('button', 'button step-review', 'Review');
        review.type = 'button';
        review.addEventListener('click', () => get('workflow-action').click());
        item.append(title, review);
      } else item.append(title, badge(step.status));
      steps.append(item);
    }
    const agents = get('delegation-list');
    agents.replaceChildren();
    get('delegation-empty').hidden = Boolean(state.delegations?.length);
    for (const child of state.delegations || []) {
      const item = element('li', 'delegation');
      const header = element('div', 'delegation-title');
      const label = child.agent === 'document' ? 'Document reader' : child.agent;
      header.append(element('strong', '', label), badge(child.status));
      const detail = element('p', 'delegation-source', child.label);
      const note = child.parent === 'main' ? 'Delegated by Kent' : 'Workflow step · ' + child.parent.replaceAll('_', ' ');
      const seconds = child.finished ? Math.max(0, child.finished - child.started).toFixed(1) + 's' : '';
      item.append(header, detail, element('p', 'inspection-note', [note, seconds].filter(Boolean).join(' · ')));
      agents.append(item);
    }
    const timeline = get('timeline-list');
    timeline.replaceChildren();
    get('timeline-empty').hidden = Boolean(state.activity?.length);
    for (const stage of [...(state.activity || [])].reverse()) {
      const time = new Date(stage.time * 1000);
      const item = element('li');
      const label = element('time', '', time.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'}));
      label.dateTime = time.toISOString();
      item.append(label, element('span', '', stage.label));
      timeline.append(item);
    }
  }

  function renderWorkflow() {
    const workflow = state.workflow;
    get('workflow-strip').hidden = !workflow;
    if (!workflow) return;
    get('workflow-name').textContent = workflow.name;
    get('workflow-status').textContent = workflow.gate ? 'Review needed · ' + workflow.gate.step.replaceAll('_', ' ') :
      (statusLabels[workflow.status] || statusLabels.ready);
    const action = get('workflow-action');
    action.hidden = Boolean(workflow.gate) || workflow.status === 'done' || workflow.status === 'running';
    action.textContent = workflow.gate ? 'Review step' : workflow.has_inputs ? 'Resume workflow' : 'Run workflow';
    get('review-card-message').textContent = workflow.gate?.message || '';
  }

  function apply(event) {
    const stick = atBottom();
    if (event.snapshot) {
      const newChat = state.session_id && state.session_id !== event.snapshot.session_id;
      state = event.snapshot;
      if (newChat) {
        view = 'current';
        prompt.value = '';
        resizePrompt();
        attached.clear();
        drawAttachments();
        showCompression();
      }
      get('messages').replaceChildren();
      for (const message of state.messages) addMessage(message);
      renderChat(true);
      renderMeter();
      renderEntries();
      renderCompressions();
      renderTask();
      renderActivity();
      renderWorkflow();
      renderFeedback();
      refreshTasks();
      refreshTree();
      refreshOutputs();
    }
    if (event.patch) {
      const wasBusy = state.busy;
      Object.assign(state, event.patch);
      renderChat(stick);
      if ('phase' in event.patch || 'context' in event.patch || 'busy' in event.patch) renderMeter();
      if ('context' in event.patch || 'request' in event.patch) renderEntries();
      if (['activity', 'delegations', 'workflow', 'run_state'].some(key => key in event.patch)) renderActivity();
      if ('workflow' in event.patch) renderWorkflow();
      if ('task' in event.patch) {
        renderTask();
        refreshTasks();
      }
      if (wasBusy !== state.busy) refreshTasks();
      if ('error' in event.patch || 'notice' in event.patch) renderFeedback();
      if (wasBusy && !state.busy) {
        refreshTree();
        refreshOutputs();
      }
    }
    if (event.message) {
      state.messages.push(event.message);
      addMessage(event.message);
      if (event.message.role === 'assistant') {
        state.draft = '';
        state.reasoning = '';
      }
      renderChat(stick || event.message.role === 'user');
    }
    if (event.delta) {
      state.draft += event.delta;
      get('reply-draft').textContent = state.draft;
      if (stick) scrollChat();
    }
    if (event.reasoning_delta) {
      state.reasoning += event.reasoning_delta;
      renderThinking();
      if (stick) scrollChat();
    }
    if (event.compaction) {
      state.compactions.push(event.compaction);
      state.compactions = state.compactions.slice(-30);
      renderCompressions();
      showCompression(event.compaction);
    }
    if (event.workflow_compaction) showCompression(event.workflow_compaction);
    updateControls();
  }

  async function submitChat(event) {
    event.preventDefault();
    const text = prompt.value.trim();
    if (!text || state.busy || pending || uploading || !connected || state.task?.closed) return;
    const files = [...attached];
    const original = prompt.value;
    pending = true;
    updateControls();
    try {
      await api('/api/chat', jsonRequest({text, files}));
      if (prompt.value === original) {
        prompt.value = '';
        resizePrompt();
      }
      for (const path of files) attached.delete(path);
      drawAttachments();
      renderTree();
    } catch (error) {
      chatFeedback(error.message, true);
    } finally {
      pending = false;
      updateControls();
    }
  }

  function resizePrompt() {
    prompt.style.height = 'auto';
    prompt.style.height = Math.min(160, Math.max(55, prompt.scrollHeight)) + 'px';
  }

  get('composer').addEventListener('submit', submitChat);
  get('stop-button').addEventListener('click', async () => {
    if (!state.busy || pending) return;
    pending = true;
    updateControls();
    try {
      await api('/api/cancel', {method: 'POST'});
    } catch (error) {
      chatFeedback(error.message, true);
    } finally {
      pending = false;
      updateControls();
    }
  });
  prompt.addEventListener('input', () => { resizePrompt(); updateControls(); });
  prompt.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!get('send-button').disabled) get('composer').requestSubmit();
    }
  });
  for (const name of ['workspace', 'context']) {
    get(name + '-toggle').addEventListener('click', () => panel(name, get(name + '-panel').hidden));
    panel(name, !narrow.matches);
  }
  initInspectorResize();
  narrow.addEventListener('change', event => {
    panel('workspace', !event.matches);
    panel('context', !event.matches);
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    if (layout.classList.contains('output-expanded')) {
      expandOutput(false);
      get('output-expand').focus();
    } else if (narrow.matches) {
      panel('workspace', false);
      panel('context', false);
    }
  });

  for (const name of tabs) {
    const tab = get(name + '-tab');
    tab.addEventListener('click', () => showInspectorTab(name));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const index = (tabs.indexOf(name) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      const next = {Home: tabs[0], End: tabs.at(-1)}[event.key] || tabs[index];
      showInspectorTab(next);
      get(next + '-tab').focus();
    });
  }
  if (taskId) showInspectorTab('activity');
  outputFile.addEventListener('change', () => {
    selectedOutput = outputFile.value;
    renderPreview();
  });
  get('output-reload').addEventListener('click', () => refreshOutputs(true));
  get('output-expand').addEventListener('click', () => expandOutput(!layout.classList.contains('output-expanded')));
  get('context-shortcut').addEventListener('click', () => {
    showInspectorTab('context');
    panel('context', true);
    get('context-tab').focus();
  });

  const taskDialog = get('task-dialog');
  get('task-close').addEventListener('click', async () => {
    pending = true;
    updateControls();
    try {
      await api('/api/tasks/status', jsonRequest({closed: !state.task.closed}));
    } catch (error) {
      chatFeedback(error.message, true);
    } finally {
      pending = false;
      updateControls();
    }
  });
  get('new-task').addEventListener('click', async () => {
    get('task-form').reset();
    get('task-error').textContent = '';
    get('task-workflow-description').hidden = true;
    taskDialog.showModal();
    if (profiles) return;
    try {
      profiles = await api('/api/profiles');
      for (const name of profiles.personas) get('task-persona').add(new Option(name, name));
      for (const workflow of profiles.workflows) get('task-workflow').add(new Option(workflow.name, workflow.id));
      const skills = get('task-skills');
      for (const name of profiles.skills) {
        const label = element('label');
        const input = element('input');
        input.type = 'checkbox';
        input.value = name;
        label.append(input, document.createTextNode(name));
        skills.append(label);
      }
      get('profile-skills').hidden = !profiles.skills.length;
    } catch (error) {
      get('task-error').textContent = error.message;
    }
  });
  get('task-workflow').addEventListener('change', event => {
    const detail = profiles?.workflows.find(workflow => workflow.id === event.target.value)?.description;
    get('task-workflow-description').textContent = detail || '';
    get('task-workflow-description').hidden = !detail;
  });
  get('cancel-task').addEventListener('click', () => taskDialog.close());
  get('task-form').addEventListener('submit', async event => {
    event.preventDefault();
    const button = get('create-task');
    if (button.disabled) return;
    button.disabled = true;
    get('task-error').textContent = '';
    try {
      const task = await api('/api/tasks', jsonRequest({
        title: get('task-title').value.trim(), persona: get('task-persona').value,
        workflow: get('task-workflow').value,
        skills: [...get('task-skills').querySelectorAll('input:checked')].map(input => input.value),
      }));
      location.assign(taskLink(task.id));
    } catch (error) {
      get('task-error').textContent = error.message;
      button.disabled = false;
    }
  });

  const workflowDialog = get('workflow-dialog');
  get('review-card-action').addEventListener('click', () => get('workflow-action').click());
  get('workflow-action').addEventListener('click', () => {
    const workflow = state.workflow;
    const gate = workflow.gate;
    workflowStep = gate?.step;
    const title = get('workflow-action').textContent;
    get('workflow-dialog-title').textContent = title;
    get('submit-workflow').textContent = gate ? 'Submit review' : title;
    get('workflow-dialog-description').textContent = gate?.message || workflow.description;
    get('workflow-error').textContent = '';
    const fields = get('workflow-fields');
    fields.replaceChildren();
    if (gate) {
      const label = element('label', '', 'Your decision');
      let input;
      if (gate.options?.length) {
        input = element('select');
        input.add(new Option('Choose a decision', ''));
        for (const option of gate.options) input.add(new Option(option, option));
        input.required = true;
      } else {
        input = element('textarea');
        input.rows = 3;
        input.maxLength = 20000;
      }
      input.id = 'workflow-answer';
      if (gate.default != null) input.value = gate.default;
      label.append(input);
      fields.append(label);
    } else if (!workflow.has_inputs) {
      for (const entry of workflow.inputs) {
        const label = element('label', '', entry.name.replaceAll('_', ' '));
        const input = element('input');
        input.required = entry.required;
        input.value = entry.default;
        input.dataset.input = entry.name;
        label.append(input);
        if (entry.description) label.append(element('span', 'inspection-note', entry.description));
        fields.append(label);
      }
    }
    workflowDialog.showModal();
  });
  get('cancel-workflow').addEventListener('click', () => workflowDialog.close());
  get('workflow-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (pending || state.busy) return;
    pending = true;
    get('submit-workflow').disabled = true;
    updateControls();
    try {
      const inputs = Object.fromEntries([...get('workflow-fields').querySelectorAll('[data-input]')]
        .filter(input => input.value !== '').map(input => [input.dataset.input, input.value]));
      await api('/api/workflow', jsonRequest({inputs, step: workflowStep, answer: get('workflow-answer')?.value}));
      workflowDialog.close();
      if (!narrow.matches) {
        showInspectorTab('activity');
        panel('context', true);
      }
    } catch (error) {
      get('workflow-error').textContent = error.message;
    } finally {
      pending = false;
      get('submit-workflow').disabled = false;
      updateControls();
    }
  });

  get('attach-button').addEventListener('click', () => {
    panel('workspace', true);
    fileFeedback('Use + beside a file to attach it to your message.');
  });
  get('refresh-files').addEventListener('click', () => {
    refreshTree();
    refreshOutputs();
  });
  get('upload-button').addEventListener('click', () => get('file-input').click());
  get('file-input').addEventListener('change', event => {
    uploadFiles([...event.target.files]);
    event.target.value = '';
  });
  const workspace = get('workspace-panel');
  workspace.addEventListener('dragover', event => {
    if (!event.dataTransfer.types.includes('Files')) return;
    event.preventDefault();
    workspace.classList.add('dragging');
  });
  workspace.addEventListener('dragleave', event => {
    if (!workspace.contains(event.relatedTarget)) workspace.classList.remove('dragging');
  });
  workspace.addEventListener('drop', event => {
    event.preventDefault();
    workspace.classList.remove('dragging');
    uploadFiles([...event.dataTransfer.files]);
  });

  const dialog = get('folder-dialog');
  get('folder-button').addEventListener('click', () => {
    get('folder-destination').textContent = folder ? 'Create inside ' + folder + '/' : 'Create at the workspace root';
    get('folder-error').textContent = '';
    get('folder-name').value = '';
    dialog.showModal();
    get('folder-name').focus();
  });
  get('cancel-folder').addEventListener('click', () => dialog.close());
  get('folder-form').addEventListener('submit', async event => {
    event.preventDefault();
    const name = get('folder-name').value.trim();
    if (!name || name.includes('/') || name.includes('\\')) {
      get('folder-error').textContent = 'Enter a single folder name.';
      return;
    }
    try {
      const path = folder ? folder + '/' + name : name;
      await api('/api/folders', jsonRequest({path}));
      expanded.add(folder);
      folder = path;
      expanded.add(path);
      dialog.close();
      await refreshTree();
    } catch (error) {
      get('folder-error').textContent = error.message;
    }
  });

  const renameDialog = get('rename-dialog');
  let renameEntry;
  function openRenameDialog(entry) {
    renameEntry = entry;
    get('rename-source').textContent = 'Current path: ' + entry.path;
    get('rename-name').value = entry.name;
    get('rename-error').textContent = '';
    renameDialog.showModal();
    get('rename-name').focus();
    get('rename-name').select();
  }
  get('cancel-rename').addEventListener('click', () => renameDialog.close());
  get('rename-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!renameEntry || pending) return;
    const name = get('rename-name').value.trim();
    if (!name || name.includes('/') || name.includes('\\')) {
      get('rename-error').textContent = 'Enter a single name without slashes.';
      return;
    }
    const parent = renameEntry.path.includes('/') ? renameEntry.path.slice(0, renameEntry.path.lastIndexOf('/')) : '';
    const destination = parent ? parent + '/' + name : name;
    if (destination === renameEntry.path) {
      renameDialog.close();
      return;
    }
    pending = true;
    get('confirm-rename').disabled = true;
    updateControls();
    try {
      await api('/api/files/rename', jsonRequest({source: renameEntry.path, destination}));
      if (attached.delete(renameEntry.path)) attached.add(destination);
      if (folder === renameEntry.path) folder = destination;
      if (expanded.delete(renameEntry.path)) expanded.add(destination);
      if (selectedOutput === renameEntry.path) selectedOutput = destination;
      drawAttachments();
      renameDialog.close();
      await Promise.all([refreshTree(), refreshOutputs()]);
    } catch (error) {
      get('rename-error').textContent = error.message;
    } finally {
      pending = false;
      get('confirm-rename').disabled = false;
      updateControls();
    }
  });

  const deleteDialog = get('delete-dialog');
  let deleteEntry;
  function openDeleteDialog(entry) {
    deleteEntry = entry;
    get('delete-target').textContent = entry.directory
      ? 'Delete folder "' + entry.path + '" and all of its contents?'
      : 'Delete file "' + entry.path + '"?';
    get('delete-error').textContent = '';
    deleteDialog.showModal();
  }
  get('cancel-delete').addEventListener('click', () => deleteDialog.close());
  get('delete-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!deleteEntry || pending) return;
    pending = true;
    get('confirm-delete').disabled = true;
    updateControls();
    try {
      const query = '/api/files?path=' + encodeURIComponent(deleteEntry.path) + (deleteEntry.directory ? '&recursive=true' : '');
      await api(query, {method: 'DELETE'});
      for (const path of [...attached]) {
        if (path === deleteEntry.path || path.startsWith(deleteEntry.path + '/')) attached.delete(path);
      }
      if (folder === deleteEntry.path || folder.startsWith(deleteEntry.path + '/')) folder = '';
      for (const path of [...expanded]) {
        if (path === deleteEntry.path || path.startsWith(deleteEntry.path + '/')) expanded.delete(path);
      }
      drawAttachments();
      deleteDialog.close();
      await Promise.all([refreshTree(), refreshOutputs()]);
    } catch (error) {
      get('delete-error').textContent = error.message;
    } finally {
      pending = false;
      get('confirm-delete').disabled = false;
      updateControls();
    }
  });
  for (const name of ['current', 'request']) {
    get(name + '-view').addEventListener('click', () => {
      view = name;
      renderEntries();
    });
  }
  const clearDialog = get('clear-chat-dialog');
  let chatToClear;
  get('clear-chat').addEventListener('click', () => {
    chatToClear = state.session_id;
    get('clear-chat-error').textContent = '';
    clearDialog.showModal();
  });
  get('cancel-clear-chat').addEventListener('click', () => clearDialog.close());
  get('clear-chat-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (pending) return;
    pending = true;
    get('confirm-clear-chat').disabled = true;
    updateControls();
    try {
      await api('/api/chat/clear', jsonRequest({session_id: chatToClear}));
      clearDialog.close();
      prompt.focus();
    } catch (error) {
      get('clear-chat-error').textContent = error.message;
    } finally {
      pending = false;
      get('confirm-clear-chat').disabled = false;
      updateControls();
    }
  });
  get('compact-button').addEventListener('click', async () => {
    pending = true;
    updateControls();
    try {
      await api('/api/compact', {method: 'POST'});
    } catch (error) {
      chatFeedback(error.message, true);
    } finally {
      pending = false;
      updateControls();
    }
  });

  const events = new EventSource(taskUrl('/api/events'));
  events.onopen = () => {
    connected = true;
    get('connection').textContent = 'Local workspace';
    get('connection').classList.add('online');
    updateControls();
  };
  events.onmessage = event => apply(JSON.parse(event.data));
  events.onerror = () => {
    connected = false;
    get('connection').textContent = 'Reconnecting';
    get('connection').classList.remove('online');
    updateControls();
  };
  setInterval(renderElapsed, 1000);
  setInterval(() => { if (!document.hidden) refreshTasks(); }, 5000);
  refreshTasks();
  updateControls();
})();
