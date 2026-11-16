// Teaching widgets and shared topic helpers. Standalone topic pages mount themselves; the reader
// (index.html, shell.js) calls KentcDocs.mount for each topic it loads. Widgets are local simulations only.
(() => {
  'use strict';
  const fmt = value => Math.round(value).toLocaleString('zh-TW');
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const budget = w => ({reserve:Math.min(16384,Math.floor(w/4)),keep:Math.min(20000,Math.floor(w/3)),margin:Math.max(256,Math.floor(w/20)),result:Math.min(3000,Math.floor(w/20)),turn:Math.min(12000,Math.floor(w/5)),digest:Math.min(1500,Math.floor(w/40))});

  // W and O carry over between the context and document topics within a browser session.
  const WO_KEY = 'kentc-docs-wo';
  const loadWO = () => {
    try { const v = JSON.parse(sessionStorage.getItem(WO_KEY)); if (v && Number.isSafeInteger(v.W) && Number.isSafeInteger(v.O)) return v; } catch {}
    return {W: 15536, O: 8192};
  };
  const saveWO = (W, O) => { try { sessionStorage.setItem(WO_KEY, JSON.stringify({W, O})); } catch {} };

  const scoped = root => {
    const $ = selector => root.querySelector(selector);
    return {
      $,
      integer(id, min, max = 2000000) {
        const field = $(id), value = Number(field.value);
        const valid = field.value.trim() !== '' && Number.isSafeInteger(value) && value >= min && value <= max;
        field.setAttribute('aria-invalid', String(!valid));
        return valid ? value : null;
      },
      verdict(id, tone, text) { const el = $(id); el.className = 'verdict ' + tone; el.textContent = text; },
      kv(id, rows) { $(id).innerHTML = rows.map(([label, value]) => `<div><span>${escape(label)}</span><b>${escape(typeof value === 'number' ? fmt(value) : value)}</b></div>`).join(''); }
    };
  };

  const STEPS = [
    ['準備上下文','Agent._call → _try_compact / room',['OpenAI 已重新偵測部署；Qwen 使用內建 60k 或明確覆寫值。本輪依能力快照計算 W。','計數由伺服器 usage 與經 density 校準的新訊息估算構成。','超過門檻先壓縮；回覆空間太少時嘗試強制壓縮。']],
    ['呼叫模型','LLMClient.chat',['送出系統提示、有效上下文與工具 schema；同一 client 的主代理、子代理及 Qwen 備援共享 TPM 估算與冷卻。','429 尊重 Retry-After 並有限等待；上下文超限仍由預算／壓縮處理。','串流 delta 是暫時顯示，不是已接受證據；Qwen 開始串流後不在傳輸層重播或切換。']],
    ['驗證後保存','Agent._call → Session.append',['先拒絕截斷、中斷串流與無效工具 JSON；結構化結果另檢查 JSON、schema 與 checks。','有限次乾淨重試不帶入被拒輸出；文件重試另開新 session，使用原始證據。','通過後才保存回覆、usage 與工具呼叫；無工具呼叫時回傳答案，否則繼續執行工具。']],
    ['執行工具','Agent._execute → _tool',['依序處理呼叫，先檢查 JSON、必要欄位與 schema 宣告的基本型別。','錯誤型別回傳可修正的工具錯誤，不讓 content=123 進入 write。','ctx.operation 指向目前工具；文件子代理與外存結果可回連到來源操作。']],
    ['整理結果','bigcontext.route_turn → Agent._settle',['一般路徑先按 file / result / turn 三道規則決定外存內容。','完整結果或原檔參照留在工作區，主上下文接收摘要與再讀取路徑。','已完成的工具不因結果路由失敗而重新執行。']],
    ['配對與繼續','Agent._persist_result / _repair / _end',['每個已保存的工具呼叫補齊一個結果；部分已保存的批次不重複附加。','取消或例外時直接修復配對，可能保留尚未路由的原始結果，不假裝正常路由已完成。','追蹤紀錄收尾；一般工具回合繼續下一個 operation，或因上限／取消／錯誤停止。']]
  ];
  function mountLoop(root) {
    const {$} = scoped(root), buttons = $('#stepBtns');
    if (!buttons) return;
    const show = index => {
      [...buttons.children].forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
      const [title, fn, items] = STEPS[index];
      $('#stepPanel').innerHTML = `<h3>${index+1}．${title}</h3><div class="fn">${escape(fn)}</div><ul>${items.map(item => `<li>${escape(item)}</li>`).join('')}</ul>`;
    };
    STEPS.forEach(([title], index) => { const button = document.createElement('button'); button.type = 'button'; button.className = 'btn'; button.textContent = `${index+1} ${title}`; button.onclick = () => show(index); buttons.appendChild(button); });
    show(0);
  }

  const LABEL = {text:'文字／程式檔',page:'分頁讀取',pdf:'PDF／影像',office:'Office／郵件／CSV',bash:'命令輸出'};
  const PRESETS = {small:[['bash',300],['text',200],['bash',150]],mixed:[['text',23700],['pdf',5600],['office',900],['bash',1100],['text',400]],batch:[['page',2900],['page',2900],['page',2900],['page',2900],['page',2900]]};
  function mountBudget(root) {
    const {$, integer, verdict, kv} = scoped(root);
    if (!$('#wInput')) return;
    let {W, O} = loadWO();
    let rows = PRESETS.mixed.map(row => [...row]);
    $('#wInput').value = W; $('#outputInput').value = O;

    function renderRouter() {
      if ($('#wInput').getAttribute('aria-invalid') === 'true' || $('#outputInput').getAttribute('aria-invalid') === 'true') return;
      const lim = budget(W), digestOf = t => Math.min(lim.digest, Math.round(150 + t * .03));
      const out = rows.map(([type, requested]) => ({type, requested, t: type === 'page' ? Math.min(requested, lim.result) : requested, rule: '', by: '', ctx: type === 'page' ? Math.min(requested, lim.result) : requested}));
      const store = (row, rule) => Object.assign(row, {rule, by: ['pdf','office'].includes(row.type) ? '文件子代理' : '規則摘要', ctx: digestOf(row.t)});
      out.forEach(row => { if (row.type === 'pdf' || (['text','office'].includes(row.type) && row.t > lim.result)) store(row, 'file'); });
      out.forEach(row => { if (!row.rule && row.t > lim.result) store(row, 'result'); });
      const sum = () => out.reduce((total, row) => total + row.ctx, 0);
      while (sum() > lim.turn) { const movable = out.filter(row => !row.rule && row.ctx > lim.digest); if (!movable.length) break; store(movable.reduce((a, b) => a.ctx >= b.ctx ? a : b), 'turn'); }
      $('#rBody').innerHTML = out.map((row, index) => `<tr><td>${LABEL[row.type]}${row.type === 'page' && row.requested > row.t ? '<br><small>分頁量已依門檻縮小</small>' : ''}</td><td>${fmt(row.t)}</td><td>${row.rule ? `<span class="tag ${row.rule === 'turn' ? 'violet' : 'red'}">${row.rule}</span>` : '原文'}</td><td>${row.by || '不產生摘要'}</td><td>${fmt(row.ctx)}</td><td><button type="button" class="btn" data-rm="${index}" aria-label="移除第 ${index+1} 筆結果">移除</button></td></tr>`).join('') || '<tr><td colspan="6">尚無結果。可新增一筆，或選擇上方教學情境。</td></tr>';
      $('#rBody').querySelectorAll('[data-rm]').forEach(button => { button.onclick = () => { rows.splice(Number(button.dataset.rm), 1); renderRouter(); }; });
      const total = sum(), raw = out.reduce((value, row) => value + row.t, 0), stored = out.filter(row => row.rule).length;
      verdict('#rVerdict', total > lim.turn ? 'warn' : 'ok', `單筆門檻 ${fmt(lim.result)}；本輪預算 ${fmt(lim.turn)}；示意摘要上限 ${fmt(lim.digest)}。${fmt(raw)} tokens → 約 ${fmt(total)} 進入上下文，${stored} 筆外存。${total > lim.turn ? '仍超過預算：沒有可再縮減的候選，下一次請求仍可能需要壓縮或超限處理。' : '這是路由示意，不是主上下文總量。'}`);
    }

    function renderBudget() {
      const w = integer('#wInput', 1024), o = integer('#outputInput', 512);
      if (w === null || o === null) {
        $('#budgetKV').replaceChildren(); $('#budgetBar').replaceChildren(); $('#rBody').replaceChildren();
        verdict('#budgetVerdict', 'bad', '請輸入有效整數：W 為 1,024～2,000,000；O 為 512～2,000,000。這是教學元件的輸入範圍，不是伺服器能力範圍。');
        verdict('#rVerdict', 'bad', '請先修正上方 W 或 O，避免以舊參數誤讀路由示意。'); return;
      }
      W = w; O = o; saveWO(W, O);
      const range = $('#ctxRange'); range.max = Math.floor(W * 1.2);
      const count = Number(range.value), b = budget(W), threshold = W - b.reserve, room = W - count - b.margin;
      $('#ctxVal').textContent = fmt(count);
      $('#budgetBar').innerHTML = `<div style="width:${threshold/W*100}%;background:var(--blue)">${fmt(threshold)}</div><div style="width:${b.reserve/W*100}%;background:var(--red)">${fmt(b.reserve)}</div><span class="marker" style="left:calc(${Math.min(count/W*100,100)}% - 2px)"></span>`;
      kv('#budgetKV', [['壓縮保留量 R',b.reserve],['超過此值先壓縮',threshold],['最近訊息保留目標 K',b.keep],['安全餘裕 M',b.margin],['壓縮前回覆空間 room',room],['壓縮前初步 max_tokens',Math.max(512,Math.min(O,room))],['單筆結果門檻',b.result],['本輪結果預算',b.turn]]);
      if (count > threshold) verdict('#budgetVerdict', 'warn', `${fmt(count)} > ${fmt(threshold)}：先嘗試壓縮舊對話，保留最近約 ${fmt(b.keep)} tokens 與結構化摘要。上列是壓縮前數值，不能當成壓縮後請求的保證。`);
      else if (room < 1024) verdict('#budgetVerdict', 'bad', `room = ${fmt(room)}，低於 1,024：嘗試強制壓縮；不能宣稱目前輸入與回覆都放得下。`);
      else verdict('#budgetVerdict', 'ok', `依此估算尚有空間：初步請求 max_tokens = ${fmt(Math.max(512,Math.min(O,room)))}。這是估算，不是伺服器已接受；實際仍以部署回覆與 usage 校準。`);
      renderRouter();
    }

    $('#wPreset').onchange = () => { $('#wInput').value = $('#wPreset').value; $('#ctxRange').value = Math.min(Number($('#ctxRange').value), Math.floor(Number($('#wPreset').value) * .6)); renderBudget(); };
    $('#wInput').oninput = renderBudget; $('#outputInput').oninput = renderBudget; $('#ctxRange').oninput = renderBudget;
    root.querySelectorAll('[data-preset]').forEach(button => { button.onclick = () => { rows = PRESETS[button.dataset.preset].map(row => [...row]); renderRouter(); }; });
    $('#rClear').onclick = () => { rows = []; renderRouter(); };
    $('#rAdd').onclick = () => { const value = integer('#rTok', 1); if (value === null) { verdict('#rVerdict', 'bad', '新增結果須為 1～2,000,000 的整數 token 估算。'); return; } rows.push([$('#rType').value, value]); renderRouter(); };
    renderBudget();
  }

  function mountDocument(root) {
    const {$, integer, verdict, kv} = scoped(root);
    if (!$('#docUser')) return;
    const saved = loadWO();
    $('#docW').value = saved.W; $('#docO').value = saved.O;
    function render() {
      const W = integer('#docW', 1024), O = integer('#docO', 512), user = integer('#docUser', 1), field = $('#docDensity'), density = Number(field.value);
      const valid = field.value.trim() !== '' && Number.isFinite(density) && density >= 1 && density <= 3;
      field.setAttribute('aria-invalid', String(!valid));
      if (W === null || O === null || user === null || !valid) { $('#docKV').replaceChildren(); verdict('#docVerdict', 'bad', '請輸入有效整數：W 為 1,024～2,000,000、O 為 512～2,000,000、user ≥ 1，density 為 1～3。'); return; }
      saveWO(W, O);
      const b = budget(W), output = Math.min(O, Math.floor(W/2)), reserve = Math.max(Math.max(output,1024) + b.margin, b.reserve), input = W - reserve;
      const prompt = Math.ceil((100 + user) * density), expansion = Math.ceil(user * density * 1.25), transcribe = $('#docMode').value === 'transcribe';
      kv('#docKV', [['規劃用輸入預算',input],['規劃用輸出保留量',output],['示意完整提示估算',prompt],['示意轉錄輸出需求',expansion]]);
      const problems = [];
      if (prompt > input) problems.push(`提示 ${fmt(prompt)} 超過輸入預算 ${fmt(input)}`);
      if (user > 12000) problems.push('user 超過 12,000 的分塊策略上限');
      if (transcribe && expansion > output) problems.push(`轉錄需求 ${fmt(expansion)} 超過輸出保留量 ${fmt(output)}`);
      verdict('#docVerdict', problems.length ? 'warn' : 'ok', problems.length ? `此候選塊不適合直接送出：${problems.join('；')}。文字需再分塊；若單張影像或合併材料仍放不下，程式會明確報錯。` : '此候選塊符合示意的 token 條件；實際還需估算完整提示、檢查影像張數，並確認模型回覆正常完成。');
    }
    ['#docW', '#docO', '#docUser', '#docDensity'].forEach(id => { $(id).oninput = render; });
    $('#docMode').onchange = render;
    render();
  }

  const WF = [
    ['extract','擷取證據','read, bash','讀取來源、列出事實與位置。模型不應將推論偽裝成原文。','工具結果經上下文路由後，仍由同一個主 Agent 繼續。'],
    ['check','核對數值','read, bash','回讀重要原句與數字；用命令計算而不是心算。','需要新證據時才追加讀取，不重送整份歷史。'],
    ['review','人類審閱','ask','等待真實使用者確認或提出修正；沒有回答就停止等待恢復。','審閱內容進入工作流程狀態與對話，不由模型冒充批准。'],
    ['brief','保存摘要','tools: []','只使用已取得的材料撰稿，保留矛盾與不確定性。','Runner 以 output 保存 reports/brief.md；不是模型自行獲得寫檔工具。']
  ];
  function mountWorkflow(root) {
    const {$} = scoped(root), timeline = $('#timeline');
    if (!timeline) return;
    const show = index => {
      [...timeline.children].forEach((button, i) => button.setAttribute('aria-pressed', String(index === i)));
      const [id, title, tools, action, result] = WF[index];
      $('#wfPanel').innerHTML = `<h3>${index+1}．${title}</h3><div class="fn">${escape(id)} · ${escape(tools)}</div><ul><li>${escape(action)}</li><li>${escape(result)}</li></ul>`;
    };
    WF.forEach(([id, title, tools], index) => { const button = document.createElement('button'); button.type = 'button'; button.className = 'btn'; button.innerHTML = `${index+1}．${title}<small>${escape(id)} · ${escape(tools)}</small>`; button.onclick = () => show(index); timeline.appendChild(button); });
    show(0);
  }

  // Every h3 gets a stable id so the reader's outline and #slug/anchor links can target it.
  function anchorHeadings(root, slug) {
    root.querySelectorAll('h3').forEach((heading, index) => { if (!heading.id) heading.id = `${slug}-${index + 1}`; });
  }

  function pager(slug, hrefFor) {
    const topics = window.KENTC_TOPICS || [], at = topics.findIndex(topic => topic.slug === slug);
    const link = (topic, rel, label) => topic
      ? `<a class="pager-link ${rel}" rel="${rel}" href="${hrefFor(topic.slug)}" data-slug="${topic.slug}"><small>${label}</small><b>${escape(topic.num)} · ${escape(topic.nav)}</b><span>${escape(topic.title)}</span></a>`
      : '<span></span>';
    return at < 0 ? '' : link(topics[at - 1], 'prev', '← 上一篇') + link(topics[at + 1], 'next', '下一篇 →');
  }

  // ---------- topic sidebar: the same panel on the reader and on every standalone topic page ----------
  const searchText = topic => `${topic.num} ${topic.nav} ${topic.kicker} ${topic.title} ${topic.problem}`.toLowerCase();
  function sidebar(nav, {href, home}) {
    const topics = window.KENTC_TOPICS || [];
    const groups = topics.reduce((map, topic) => map.set(topic.group, [...(map.get(topic.group) || []), topic]), new Map());
    const link = topic => `<a class="side-link" href="${href(topic.slug)}" data-slug="${topic.slug}" data-search="${escape(searchText(topic))}"><span class="num">${escape(topic.num)}</span><span>${escape(topic.nav)}</span></a>`;
    nav.innerHTML = `<a class="side-link home" href="${home}" data-home><span class="num">◆</span><span>首頁 · 全部主題</span></a>` +
      [...groups].map(([group, list]) => `<div class="side-group"><h2>${escape(group)}</h2>${list.map(link).join('')}</div>`).join('') +
      '<p class="side-empty" hidden>沒有符合的主題</p><p class="kbd-hint"><kbd>←</kbd> <kbd>→</kbd> 切換主題 · <kbd>/</kbd> 搜尋</p>';
  }
  function markCurrent(nav, slug) {
    let active = null;
    nav.querySelectorAll('.side-link').forEach(a => {
      const on = slug ? a.dataset.slug === slug : a.hasAttribute('data-home');
      if (on) { a.setAttribute('aria-current', 'page'); active = a; } else a.removeAttribute('aria-current');
    });
    // In the narrow horizontal strip, keep the current topic in view without moving the page.
    const strip = nav.closest('.sidebar');
    if (active && strip && strip.scrollWidth > strip.clientWidth) strip.scrollLeft = active.offsetLeft - (strip.clientWidth - active.offsetWidth) / 2;
  }
  // Filters every sidebar link and home card by the search text; empty groups are hidden.
  function filter(query) {
    query = query.trim().toLowerCase();
    let shown = 0;
    document.querySelectorAll('.side-link[data-slug], .topic-card').forEach(el => {
      const hit = !query || el.dataset.search.includes(query);
      el.hidden = !hit; if (hit && el.classList.contains('side-link')) shown++;
    });
    document.querySelectorAll('.side-group').forEach(group => { group.hidden = !group.querySelector('.side-link:not([hidden])'); });
    document.querySelectorAll('.index-group').forEach(group => { group.hidden = !group.querySelector('.topic-card:not([hidden])'); });
    const empty = document.querySelector('.side-empty');
    if (empty) empty.hidden = shown > 0;
  }
  // Sticky header (and, on narrow screens, the topic strip) height, for sticky offsets and anchor scrolling.
  function trackStickyHeight() {
    const header = document.querySelector('.top'), strip = document.querySelector('.sidebar');
    const update = () => {
      const rail = strip && getComputedStyle(strip).display !== 'none' && matchMedia('(max-width:640px)').matches ? strip.offsetHeight : 0;
      document.documentElement.style.setProperty('--header-h', `${header.offsetHeight}px`);
      document.documentElement.style.setProperty('--sticky-h', `${header.offsetHeight + rail}px`);
    };
    new ResizeObserver(update).observe(header);
    if (strip) new ResizeObserver(update).observe(strip);
    addEventListener('resize', update);
    update();
  }

  function mount(root, slug) {
    anchorHeadings(root, slug);
    mountLoop(root); mountBudget(root); mountDocument(root); mountWorkflow(root);
  }

  window.KentcDocs = {mount, pager, escape, sidebar, markCurrent, filter, trackStickyHeight};

  if (document.body.classList.contains('topic-page')) {
    const main = document.getElementById('topic'), slug = main.dataset.slug, nav = document.getElementById('sideNav');
    const search = document.getElementById('search'), topics = window.KENTC_TOPICS || [];
    sidebar(nav, {href: target => `${target}.html`, home: '../index.html'});
    trackStickyHeight();
    markCurrent(nav, slug);
    mount(main, slug);
    const pagerNav = main.querySelector('[data-pager]');
    if (pagerNav) pagerNav.innerHTML = pager(slug, target => `${target}.html`);
    if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
    search.value = '';
    search.addEventListener('input', () => filter(search.value));
    search.addEventListener('keydown', event => {
      if (event.key === 'Enter') { const first = nav.querySelector('.side-link[data-slug]:not([hidden])'); if (first) location.href = first.href; }
      if (event.key === 'Escape') { search.value = ''; filter(''); search.blur(); }
    });
    document.addEventListener('keydown', event => {
      if (event.target.closest('input, select, textarea, [contenteditable]') || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === '/') { event.preventDefault(); search.focus(); return; }
      const at = topics.findIndex(topic => topic.slug === slug);
      const next = event.key === 'ArrowRight' ? topics[at + 1] : event.key === 'ArrowLeft' ? topics[at - 1] : null;
      if (next) location.href = `${next.slug}.html`;
    });
  }
})();
