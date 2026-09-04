/* Progressive enhancement: durable content lives in Git + public catalogue,
   never in browser preferences. No messages, payments, or private data sent. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const announce = text => { $('announcement').textContent = text; };
  const params = new URLSearchParams(location.search);
  const legacyEntries = { '#profile': '/hub/experience/', '#research': '/hub/solutions/#research', '#demos': '/hub/library/?kind=Demo', '#skills': '/hub/library/?kind=Skill', '#vault': '/hub/library/?kind=Article', '#monitoring': '/hub/graph/' };
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
      select.value = [...select.options].some(o => o.value === value) ? value : '';
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
      setParams({ q: search.value.trim(), kind: kind.value, stream: stream.value });
    }
    search.addEventListener('input', filter); kind.addEventListener('change', filter); stream.addEventListener('change', filter);
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

  const form = $('brief-form');
  if (form) {
    for (const [id, key] of [['brief-purpose', 'purpose'], ['brief-offer', 'offer']]) {
      const select = $(id), requested = params.get(key);
      if ([...select.options].some(o => o.value === requested)) select.value = requested;
    }
    const brief = () => `Autumn Memo inquiry\nPurpose: ${$('brief-purpose').value}\nEngagement: ${$('brief-offer').selectedOptions[0].textContent}\n\n${$('brief-context').value.trim()}\n\nPrepared from: ${location.origin}/hub/contact/\n`;
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
