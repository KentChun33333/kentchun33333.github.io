/* Progressive enhancement: durable content lives in Git + public catalogue,
   never in browser preferences. No messages, payments, or private data sent. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const announce = text => { $('announcement').textContent = text; };
  const params = new URLSearchParams(location.search);
  const legacyEntries = { '#profile': '/#about', '#research': '/?kind=Research', '#demos': '/?kind=Demo', '#skills': '/?kind=Skill', '#vault': '/?kind=Article', '#monitoring': '/hub/graph/' };
  if (location.pathname === '/' && legacyEntries[location.hash]) location.replace(legacyEntries[location.hash]);
  const setParams = fields => {
    const url = new URL(location.href);
    for (const [key, value] of Object.entries(fields)) value ? url.searchParams.set(key, value) : url.searchParams.delete(key);
    history.replaceState(null, '', url);
  };
  async function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try { await navigator.clipboard.writeText(text); return; } catch (_) { /* fallback below */ }
    }
    const field = document.createElement('textarea');
    field.value = text; field.setAttribute('aria-label', 'Text to copy');
    field.style.position = 'fixed'; field.style.left = '-10000px';
    document.body.append(field); field.select();
    const success = document.execCommand('copy'); field.remove();
    if (!success) throw new Error('Copy unavailable');
  }
  document.querySelectorAll('[data-share]').forEach(button => button.addEventListener('click', async () => {
    try { await copy(location.href); button.textContent = 'Link copied'; announce('Share link copied.'); }
    catch (_) { button.textContent = 'Copy the address from your browser'; announce('Clipboard unavailable. Copy the address from your browser.'); }
  }));

  const search = $('asset-search');
  if (search) {
    const kind = $('asset-kind'), stream = $('asset-stream');
    const cards = [...document.querySelectorAll('[data-asset]')];
    search.value = params.get('q') || '';
    for (const [select, key] of [[kind, 'kind'], [stream, 'stream']]) {
      const value = params.get(key) || '';
      const allowed = key === 'kind' ? ['', 'Article', 'Research', 'Demo', 'Skill', 'Tool', 'Protocol'] : ['', 'Build', 'Research', 'Publish'];
      select.value = allowed.includes(value) ? value : '';
    }
    function filter() {
      const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
      let count = 0;
      cards.forEach(card => {
        const visible = terms.every(t => card.dataset.search.includes(t)) && (!kind.value || card.dataset.kind === kind.value) && (!stream.value || card.dataset.stream === stream.value);
        card.hidden = !visible; if (visible) count++;
      });
      $('result-count').textContent = `${count} of ${cards.length} assets`;
      $('empty-results').hidden = count !== 0;
      document.querySelectorAll('[data-kind-shortcut]').forEach(link => {
        link.setAttribute('aria-pressed', String(link.dataset.kindShortcut === kind.value));
      });
      document.querySelectorAll('[data-stream-shortcut]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.streamShortcut === stream.value)));
      if ($('filter-count')) $('filter-count').textContent = [kind.value, stream.value].filter(Boolean).length || '';
      if ($('filter-results')) $('filter-results').textContent = `${count} matching assets`;
      setParams({ q: search.value.trim(), kind: kind.value, stream: stream.value });
    }
    search.addEventListener('input', filter); kind.addEventListener('change', filter); stream.addEventListener('change', filter);
    document.querySelectorAll('[data-kind-shortcut]').forEach(link => link.addEventListener('click', e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault(); kind.value = link.dataset.kindShortcut; filter();
    }));
    document.querySelectorAll('[data-stream-shortcut]').forEach(button => button.addEventListener('click', () => { stream.value = button.dataset.streamShortcut; filter(); }));
    if ($('filters-reset')) $('filters-reset').addEventListener('click', () => { search.value = ''; kind.value = ''; stream.value = ''; filter(); });
    search.form.addEventListener('submit', e => { e.preventDefault(); filter(); });
    search.form.addEventListener('reset', () => { setTimeout(filter, 0); });
    document.addEventListener('keydown', e => {
      const editing = e.target.closest('input,textarea,select,[contenteditable=true]');
      if (!editing && (e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'))) { e.preventDefault(); search.focus(); }
    });
    filter();
  }

  const graphFocus = $('graph-focus');
  if (graphFocus) {
    // Node text is always assigned through textContent, not untrusted HTML.
    const node = (tag, text, className) => { const el = document.createElement(tag); if (text) el.textContent = text; if (className) el.className = className; return el; };
    fetch('/data/hub/catalog.json').then(response => { if (!response.ok) throw new Error('Catalogue unavailable'); return response.json(); }).then(data => {
      const assets = new Map(data.assets.map(a => [a.id, a]));
      const requested = params.get('asset');
      if ([...graphFocus.options].some(o => o.value === requested)) graphFocus.value = requested;
      function render() {
        const asset = assets.get(graphFocus.value);
        const relations = data.relations.filter(r => r.source === asset.id || r.target === asset.id);
        const canvas = $('graph-canvas'), context = $('graph-context');
        canvas.replaceChildren(); context.replaceChildren();
        const root = node('div', '', 'graph-root'); root.append(node('p', asset.kind.toUpperCase()), node('h2', asset.title), node('p', asset.status)); canvas.append(root);
        const neighbors = node('div', '', 'graph-neighbors');
        context.append(node('p', 'RELATIONSHIP NOTES', 'eyebrow'), node('h2', 'Why these connect'));
        relations.forEach(r => {
          const other = assets.get(r.source === asset.id ? r.target : r.source);
          const label = r.type.replaceAll('_', ' ');
          const link = node('a', '', 'graph-node'); link.href = other.detail_url;
          link.append(node('small', (r.source === asset.id ? 'OUTGOING · ' : 'INCOMING · ') + label), node('strong', other.title)); neighbors.append(link);
          const note = node('article', '', 'graph-context-item'); note.append(node('h3', other.title), node('p', r.basis));
          const explore = node('button', 'Focus this asset →', 'text-button');
          explore.addEventListener('click', () => { graphFocus.value = other.id; render(); graphFocus.focus(); }); note.append(explore); context.append(note);
        });
        canvas.append(neighbors); setParams({ asset: asset.id }); announce(`${asset.title}: ${relations.length} recorded connections.`);
      }
      graphFocus.addEventListener('change', render); render();
    }).catch(() => { $('graph-canvas').textContent = 'The interactive map could not load. All recorded relationships are available below.'; $('graph-context').textContent = 'Try reloading the page, or follow the links in the relationship list.'; });
  }

  function initDrawer(name) {
    const panel = $(name + '-panel'), trigger = $(name + '-trigger');
    if (!panel || !trigger || typeof panel.showModal !== 'function') return null;
    let previousOverflow = '';
    const open = () => {
      if (panel.open) return;
      previousOverflow = document.body.style.overflow;
      panel.showModal(); document.body.style.overflow = 'hidden';
      $(name + '-title').focus();
    };
    trigger.addEventListener('click', e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault(); open();
    });
    $(name + '-close').addEventListener('click', () => panel.close());
    if ($(name + '-apply')) $(name + '-apply').addEventListener('click', () => panel.close());
    panel.addEventListener('close', () => { document.body.style.overflow = previousOverflow; trigger.focus(); });
    panel.addEventListener('click', e => {
      const rect = panel.getBoundingClientRect();
      if (e.target === panel && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) panel.close();
    });
    return open;
  }
  initDrawer('conversation');
  const filtersPanel = $('filters-panel'), filtersTrigger = $('filters-trigger');
  if (filtersPanel && filtersTrigger) {
    const handle = $('filters-resizer');
    let width = 64, dragging = false, dragStart = 0, startWidth = 64;
    const stops = () => {
      const full = Math.min(360, Math.max(160, window.innerWidth - 160));
      return [64, Math.min(240, Math.round(full * .72)), full];
    };
    const applyWidth = value => {
      const sizes = stops(); width = Math.max(64, Math.min(sizes[2], value));
      const rail = width < 112;
      document.body.style.setProperty('--filters-width', width + 'px');
      document.body.setAttribute('data-filter-layout', rail ? 'rail' : 'expanded');
      document.body.setAttribute('data-filter-dragging', String(dragging));
      filtersTrigger.setAttribute('aria-expanded', String(!rail));
      $('filters-close').textContent = rail ? '›' : '‹';
      $('filters-close').setAttribute('aria-label', rail ? 'Expand filters' : 'Collapse to icons');
      if (handle) {
        handle.setAttribute('aria-valuenow', String(Math.round(width)));
        handle.setAttribute('aria-valuemax', String(sizes[2]));
        handle.setAttribute('aria-valuetext', rail ? 'Icons only' : Math.round(width) + ' pixels');
      }
      document.querySelectorAll('[data-panel-stop]').forEach(button => button.setAttribute('aria-pressed', String(sizes[Number(button.dataset.panelStop)] === width)));
    };
    const snap = () => applyWidth(stops().reduce((a,b) => Math.abs(a-width) <= Math.abs(b-width) ? a : b));
    const toggle = () => applyWidth(width < 112 ? stops()[1] : 64);
    filtersTrigger.addEventListener('click', e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault(); toggle();
    });
    $('filters-close').addEventListener('click', toggle);
    $('filters-apply').addEventListener('click', () => { applyWidth(64); if (search) search.focus(); });
    document.querySelectorAll('[data-panel-stop]').forEach(button => button.addEventListener('click', () => applyWidth(stops()[Number(button.dataset.panelStop)])));
    filtersPanel.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.preventDefault(); applyWidth(64); $('filters-close').focus(); }
    });
    if (handle) {
      handle.addEventListener('pointerdown', e => {
        if (e.button !== 0) return;
        e.preventDefault(); dragging = true; dragStart = e.clientX; startWidth = width;
        handle.setPointerCapture(e.pointerId); handle.focus(); applyWidth(width);
      });
      handle.addEventListener('pointermove', e => { if (dragging) applyWidth(startWidth + e.clientX - dragStart); });
      const finish = () => { if (dragging) { dragging = false; snap(); } };
      handle.addEventListener('pointerup', finish); handle.addEventListener('pointercancel', finish); handle.addEventListener('lostpointercapture', finish);
      handle.addEventListener('dblclick', () => applyWidth(stops().find(x => x > width + 1) || 64));
      handle.addEventListener('keydown', e => {
        const sizes = stops(); let next;
        if (e.key === 'ArrowRight') next = sizes.find(x => x > width + 1) || sizes[2];
        else if (e.key === 'ArrowLeft') next = [...sizes].reverse().find(x => x < width - 1) || 64;
        else if (e.key === 'Home') next = 64;
        else if (e.key === 'End') next = sizes[2];
        else return;
        e.preventDefault(); applyWidth(next);
      });
    }
    window.addEventListener('resize', () => { applyWidth(width); snap(); });
    applyWidth(64);
  }
  const openAbout = initDrawer('about');
  if (openAbout && location.hash === '#about') openAbout();
  const trigger = $('conversation-trigger');

  const form = $('brief-form');
  if (form) {
    for (const [id, key] of [['brief-purpose', 'purpose'], ['brief-offer', 'offer'], ['brief-asset', 'asset']]) {
      const select = $(id), requested = params.get(key) || (key === 'asset' && trigger ? trigger.dataset.currentAsset : null);
      if ([...select.options].some(o => o.value === requested)) select.value = requested;
    }
    const brief = () => `Autumn Memo inquiry\nPurpose: ${$('brief-purpose').value}\nAsset: ${$('brief-asset').selectedOptions[0].textContent}${$('brief-asset').value ? '\nAsset link: ' + location.origin + '/hub/assets/' + $('brief-asset').value + '/' : ''}\nEngagement: ${$('brief-offer').selectedOptions[0].textContent}\n\n${$('brief-context').value.trim()}\n\nPrepared from: ${location.origin}/hub/contact/\n`;
    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      try { await copy(brief()); $('brief-status').textContent = 'Brief copied. Nothing was sent. Use the GitHub profile link to find contact information.'; }
      catch (_) { $('brief-status').textContent = 'Clipboard unavailable. Download the brief as text instead.'; }
    });
    $('download-brief').addEventListener('click', () => {
      if (!form.reportValidity()) return;
      const url = URL.createObjectURL(new Blob([brief()], { type: 'text/plain;charset=utf-8' }));
      const link = document.createElement('a'); link.href = url; link.download = 'autumn-memo-inquiry.txt'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000); $('brief-status').textContent = 'Brief downloaded. Nothing was sent or stored on this site.';
    });
  }
})();
