// Reader for index.html: loads topics/<slug>.html into #view without a page reload.
// Supports two top-level tabs ("agent" for kentc_agent, "breezeman" for Breezeman).
// Routes: "" / "#tab=agent" / "#tab=breezeman" (home), "#slug", "#slug/anchor".
(() => {
  'use strict';
  const allTopics = window.KENTC_TOPICS, bySlug = new Map(allTopics.map(topic => [topic.slug, topic]));
  const {escape, pager, mount, sidebar, filter, trackStickyHeight, tabOf, topicsForTab, loadTab, saveTab, renderTabsBar} = window.KentcDocs;
  const view = document.getElementById('view'), sideNav = document.getElementById('sideNav');
  const outline = document.getElementById('outline'), search = document.getElementById('search');
  const homeTitle = document.title;
  const cache = new Map();
  let activeTab = loadTab();
  let current = null, spy = null;

  const topicUrl = slug => new URL(`topics/${slug}.html`, location.href);
  const groupsFor = tab => topicsForTab(tab).reduce((map, topic) => map.set(topic.group, [...(map.get(topic.group) || []), topic]), new Map());

  // ---------- loading ----------
  function rewrite(article, base) {
    article.querySelectorAll('[href],[src]').forEach(el => {
      const attr = el.hasAttribute('href') ? 'href' : 'src', value = el.getAttribute(attr);
      if (value.startsWith('#')) { el.setAttribute(attr, `#${base.slug}/${value.slice(1)}`); return; }
      const url = new URL(value, base.url);
      const own = url.pathname.match(/\/topics\/([\w-]+)\.html$/);
      if (own && url.origin === location.origin && bySlug.has(own[1])) el.setAttribute(attr, `#${own[1]}${url.hash ? '/' + url.hash.slice(1) : ''}`);
      else el.setAttribute(attr, url.href);
    });
    return article;
  }
  function load(slug) {
    if (!cache.has(slug)) {
      const url = topicUrl(slug);
      cache.set(slug, fetch(url).then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.text(); })
        .then(text => {
          const article = new DOMParser().parseFromString(text, 'text/html').querySelector('article.topic');
          if (!article) throw new Error('topic page has no article.topic');
          return rewrite(article, {slug, url});
        })
        .catch(error => { cache.delete(slug); throw error; }));
    }
    return cache.get(slug);
  }
  const prefetch = slug => { if (bySlug.has(slug)) load(slug).catch(() => {}); };

  // ---------- tabs, sidebar and home ----------
  function setTab(tab, {navigateHome = false} = {}) {
    if (tab !== 'agent' && tab !== 'breezeman') tab = 'agent';
    activeTab = tab;
    saveTab(activeTab);
    renderTabsBar(activeTab, {
      onSelect: nextTab => {
        if (nextTab === activeTab && !current) return;
        setTab(nextTab, {navigateHome: true});
      }
    });
    renderSidebar();
    markCurrent();
    if (navigateHome) {
      const targetHash = `#tab=${activeTab}`;
      if (location.hash === targetHash) showHome();
      else location.hash = targetHash;
    }
  }

  const renderSidebar = () => sidebar(sideNav, {href: slug => `topics/${slug}.html`, home: `#tab=${activeTab}`, activeTab});

  function renderHome() {
    const tplId = activeTab === 'breezeman' ? 'homeTpl-breezeman' : 'homeTpl-agent';
    const tpl = document.getElementById(tplId).content.cloneNode(true);
    tpl.querySelector('#topicIndex').insertAdjacentHTML('beforeend', [...groupsFor(activeTab)].map(([group, list]) =>
      `<div class="index-group"><h3>${escape(group)}</h3><div class="topic-grid">${list.map(topic =>
        `<a class="topic-card" href="topics/${topic.slug}.html" data-slug="${topic.slug}" data-search="${escape(`${topic.num} ${topic.nav} ${topic.kicker} ${topic.title} ${topic.problem}`.toLowerCase())}"><span class="num">${escape(topic.num)} · ${escape(topic.nav)}</span><b>${escape(topic.title)}</b><em>問題：${escape(topic.problem)}</em></a>`).join('')}</div></div>`).join(''));
    view.replaceChildren(tpl);
    filter(search.value);
  }

  // ---------- topic view ----------
  function renderOutline(article) {
    spy?.disconnect();
    const heads = [...article.querySelectorAll('h3[id]')].filter(h => !h.closest('.step-panel, details'));
    if (!heads.length) { outline.replaceChildren(); return; }
    outline.innerHTML = `<h2>本頁內容</h2><ol>${heads.map(h => `<li><a href="#${current}/${h.id}" data-anchor="${h.id}">${escape(h.textContent.trim())}</a></li>`).join('')}</ol>`;
    const links = new Map([...outline.querySelectorAll('a')].map(a => [a.dataset.anchor, a]));
    spy = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      links.forEach(a => a.classList.remove('active'));
      links.get(visible.target.id)?.classList.add('active');
    }, {rootMargin: '-70px 0px -65% 0px'});
    heads.forEach(h => spy.observe(h));
  }
  function scrollToAnchor(anchor, behavior = 'instant') {
    const target = anchor && document.getElementById(anchor);
    if (target) target.scrollIntoView({block: 'start', behavior});
    else window.scrollTo({top: 0, behavior});
  }
  async function showTopic(slug, anchor) {
    const topic = bySlug.get(slug);
    const topicTab = tabOf(slug);
    if (topicTab !== activeTab) setTab(topicTab, {navigateHome: false});
    if (current === slug && view.querySelector('.view-topic')) { scrollToAnchor(anchor, 'smooth'); return; }
    current = slug;
    document.body.classList.remove('is-home');
    markCurrent();
    view.innerHTML = '<div class="loading" aria-label="載入中"><i></i><i></i><i></i><i></i></div>';
    let article;
    try { article = (await load(slug)).cloneNode(true); }
    catch { location.replace(topicUrl(slug).href + (anchor ? `#${anchor}` : '')); return; }
    if (current !== slug) return;
    article.className = 'topic view-topic enter';
    const crumbs = document.createElement('p');
    crumbs.className = 'crumbs';
    const tabLabel = activeTab === 'breezeman' ? 'Breezeman' : 'kentc_agent';
    crumbs.innerHTML = `<a href="#tab=${activeTab}" data-home>${escape(tabLabel)}</a><span>›</span><span>${escape(topic.group)}</span><span>›</span><span>${escape(topic.num)} · ${escape(topic.nav)}</span><span style="margin-left:auto"><a href="topics/${slug}.html" title="以獨立頁面開啟（可直接分享）">獨立頁面 ↗</a></span>`;
    const nav = document.createElement('nav');
    nav.className = 'pager'; nav.setAttribute('aria-label', '上一篇與下一篇');
    nav.innerHTML = pager(slug, target => `#${target}`);
    view.replaceChildren(crumbs, article, nav);
    mount(article, slug);
    renderOutline(article);
    document.title = `${topic.num} · ${topic.nav}｜${tabLabel} 核心方法論`;
    scrollToAnchor(anchor);
    const heading = article.querySelector('h2');
    if (!anchor && heading) { heading.setAttribute('tabindex', '-1'); heading.focus({preventScroll: true}); }
    const tabTopics = topicsForTab(activeTab);
    const at = tabTopics.indexOf(topic);
    prefetch(tabTopics[at + 1]?.slug);
  }
  function showHome() {
    current = null; spy?.disconnect(); outline.replaceChildren();
    document.body.classList.add('is-home');
    markCurrent(); renderHome();
    document.title = activeTab === 'breezeman' ? 'Breezeman｜長程排程、全域記憶與 Studio 整合' : homeTitle;
    window.scrollTo({top: 0, behavior: 'instant'});
  }
  const markCurrent = () => window.KentcDocs.markCurrent(sideNav, current);

  // ---------- routing ----------
  async function findAnchor(id) {
    const auto = id.match(/^([\w-]+)-\d+$/);
    if (auto && bySlug.has(auto[1])) return auto[1];
    for (const topic of allTopics) {
      try { if ((await load(topic.slug)).querySelector(`#${CSS.escape(id)}`)) return topic.slug; } catch { return null; }
    }
    return null;
  }
  async function route() {
    const hash = decodeURIComponent(location.hash.slice(1));
    if (!hash) return showHome();
    if (hash.startsWith('tab=')) {
      const nextTab = hash.slice(4);
      if (nextTab === 'agent' || nextTab === 'breezeman') {
        if (nextTab !== activeTab) setTab(nextTab, {navigateHome: false});
      }
      return showHome();
    }
    const [head, ...rest] = hash.split('/'), anchor = rest.join('/');
    if (bySlug.has(head)) return showTopic(head, anchor);
    const slug = await findAnchor(head);
    if (slug) { history.replaceState(null, '', `#${slug}/${head}`); return showTopic(slug, head); }
    history.replaceState(null, '', location.pathname + location.search);
    showHome();
  }

  // ---------- search, keyboard, progress ----------
  search.addEventListener('input', () => filter(search.value));
  search.addEventListener('keydown', event => {
    if (event.key === 'Enter') { const first = sideNav.querySelector('.side-link[data-slug]:not([hidden])'); if (first) { location.hash = first.dataset.slug; search.blur(); } }
    if (event.key === 'Escape') { search.value = ''; filter(''); search.blur(); }
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-slug], a[data-home]');
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    const hash = link.hasAttribute('data-home') ? `#tab=${activeTab}` : `#${link.dataset.slug}`;
    if (location.hash === hash) route(); else location.hash = hash;
  });
  document.addEventListener('pointerover', event => { const link = event.target.closest('a[data-slug]'); if (link) prefetch(link.dataset.slug); });
  document.addEventListener('keydown', event => {
    if (event.target.closest('input, select, textarea, [contenteditable]') || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === '/') { event.preventDefault(); search.focus(); return; }
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    const tabTopics = topicsForTab(activeTab);
    const at = current ? tabTopics.findIndex(topic => topic.slug === current) : -1;
    const next = event.key === 'ArrowRight' ? tabTopics[at + 1] : tabTopics[at - 1];
    if (next) location.hash = next.slug; else if (event.key === 'ArrowLeft' && current) location.hash = `#tab=${activeTab}`;
  });
  const bar = document.getElementById('progress');
  const progress = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = `${max > 0 ? Math.min(100, scrollY / max * 100) : 0}%`;
  };
  addEventListener('scroll', progress, {passive: true});
  addEventListener('resize', progress);
  addEventListener('hashchange', route);

  search.value = '';
  setTab(activeTab, {navigateHome: false});
  trackStickyHeight();
  route().then(progress);
})();
