/* Persistent library shell. Original HTML runs in its own frame; Markdown
   readers are generated, escaped fragments. Original URLs remain available. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const library = $('library-view'), viewer = $('asset-view');
  if (!library || !viewer) return;
  const canvas = $('viewer-canvas'), title = $('viewer-title'), status = $('viewer-status');
  const toolbar = $('viewer-toolbar');
  let request = 0, current = null, libraryScroll = 0, returnFocus = null, catalogue;
  const sourceAssets = new Map();
  const baseTitle = document.title;
  const getCatalogue = () => catalogue || (catalogue = fetch('/data/hub/catalog.json').then(r => {
    if (!r.ok) throw new Error('Catalogue unavailable');
    return r.json();
  }).then(data => {
    data.assets.forEach(a => {
      sourceAssets.set(a.url, a.id);
      if (a.url.endsWith('/index.html')) sourceAssets.set(a.url.slice(0, -10), a.id);
    });
    return data;
  }).catch(error => { catalogue = null; throw error; }));
  function setContext(id) {
    if ($('brief-asset')) $('brief-asset').value = id || '';
    if ($('conversation-trigger')) $('conversation-trigger').dataset.currentAsset = id || '';
  }
  function setRoute(id) {
    const url = new URL(location.href);
    if (id) url.searchParams.set('asset', id); else url.searchParams.delete('asset');
    history.pushState({ libraryScroll }, '', url);
  }
  function showLibrary(push = true) {
    request++;
    if (push && new URLSearchParams(location.search).has('asset')) setRoute(null);
    current = null; canvas.replaceChildren(); viewer.hidden = true; toolbar.hidden = true; library.hidden = false;
    document.body.removeAttribute('data-asset-open'); document.title = baseTitle; setContext(null);
    window.scrollTo(0, libraryScroll);
    if (returnFocus && returnFocus.isConnected) returnFocus.focus({ preventScroll: true });
  }
  function fail(text, retry) {
    status.textContent = text;
    if (retry) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'text-button'; button.textContent = 'Retry';
      button.addEventListener('click', retry); canvas.append(button);
    }
  }
  async function showAsset(id, push = true) {
    if (viewer.hidden) {
      libraryScroll = window.scrollY;
      returnFocus = document.activeElement;
      history.replaceState({ ...(history.state || {}), libraryScroll }, '', location.href);
    }
    if (push) setRoute(id);
    const ticket = ++request;
    library.hidden = true; viewer.hidden = false; toolbar.hidden = false; canvas.replaceChildren();
    title.textContent = 'Opening asset…'; status.textContent = 'Loading…';
    document.body.setAttribute('data-asset-open', 'true');
    window.scrollTo(0, 0);
    try {
      const data = await getCatalogue();
      if (ticket !== request) return;
      const asset = data.assets.find(a => a.id === id);
      if (!asset) { title.textContent = 'Asset not found'; status.textContent = 'Return to the library to choose an asset.'; return; }
      current = asset; title.textContent = asset.title; document.title = asset.title + ' · Autumn Memo';
      title.title = asset.title; if ($('viewer-asset-mark')) $('viewer-asset-mark').title = asset.title; setContext(asset.id); title.focus({ preventScroll: true });
      if (asset.path.endsWith('.md')) {
        const response = await fetch('/data/hub/readers/' + asset.id + '.html');
        if (!response.ok) throw new Error('Reader unavailable');
        const html = await response.text();
        if (ticket !== request) return;
        // Only the build-generated, escaped reader fragment is inserted here.
        canvas.innerHTML = html; status.textContent = '';
      } else {
        const frame = document.createElement('iframe'); frame.className = 'asset-frame'; frame.title = asset.title;
        // Same-origin storage is needed by existing trusted demos. Top navigation
        // is withheld; external popups/downloads remain user-initiated capabilities.
        frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-downloads allow-popups allow-popups-to-escape-sandbox');
        frame.addEventListener('load', () => { if (ticket === request) status.textContent = ''; });
        frame.addEventListener('error', () => { if (ticket === request) fail('The embedded page could not load.', () => showAsset(asset.id, false)); });
        frame.src = asset.url; canvas.append(frame);
      }
    } catch (_) {
      if (ticket === request) fail('This asset could not load. Your library is still available.', () => showAsset(id, false));
    }
  }
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button > 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const link = e.target.closest('a[href]');
    if (!link || link.target === '_blank' || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin) return;
    const match = url.pathname.match(/^\/hub\/assets\/([a-z0-9_-]+)\/(?:index\.html)?$/);
    if (match) { e.preventDefault(); showAsset(match[1]); }
    else if (!viewer.hidden && link.closest('#viewer-canvas') && sourceAssets.has(url.pathname)) { e.preventDefault(); showAsset(sourceAssets.get(url.pathname)); }
    else if (link.classList.contains('header-library-link') && !viewer.hidden) { e.preventDefault(); showLibrary(); }
  });
  $('viewer-back').addEventListener('click', () => showLibrary());
  $('viewer-share').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(location.href); status.textContent = 'Link copied.'; }
    catch (_) { status.textContent = 'Copy the address from your browser to share this asset.'; }
  });
  document.addEventListener('hub:filters-changed', () => { if (!viewer.hidden) showLibrary(); });
  window.addEventListener('popstate', e => {
    const id = new URLSearchParams(location.search).get('asset');
    if (e.state && Number.isFinite(e.state.libraryScroll)) libraryScroll = e.state.libraryScroll;
    if (id) showAsset(id, false); else showLibrary(false);
  });
  const initial = new URLSearchParams(location.search).get('asset');
  if (initial) showAsset(initial, false);
})();
