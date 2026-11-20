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

  // ---------- 2-tab helpers (kentc_agent vs Breezeman) ----------
  const TAB_KEY = 'kentc-docs-tab';
  const tabsList = () => window.KENTC_TABS || [
    {id: 'agent', label: 'kentc_agent', short: '單任務引擎'},
    {id: 'breezeman', label: 'Breezeman', short: '長程常駐與記憶'}
  ];
  const tabOf = slug => (window.KENTC_TOPICS || []).find(t => t.slug === slug)?.tab || 'agent';
  const topicsForTab = tab => (window.KENTC_TOPICS || []).filter(t => (t.tab || 'agent') === tab);
  const loadTab = () => {
    try { const v = sessionStorage.getItem(TAB_KEY); if (v && tabsList().some(t => t.id === v)) return v; } catch {}
    return 'agent';
  };
  const saveTab = tab => { try { sessionStorage.setItem(TAB_KEY, tab); } catch {} };

  function renderTabsBar(activeTab, {onSelect, hrefForTab} = {}) {
    const topIn = document.querySelector('.top-in');
    if (!topIn) return null;
    let bar = topIn.querySelector('#docTabs');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'docTabs';
      bar.className = 'doc-tabs';
      bar.setAttribute('role', 'tablist');
      bar.setAttribute('aria-label', '文件分頁');
      const search = topIn.querySelector('.search');
      topIn.insertBefore(bar, search || null);
    }
    bar.innerHTML = tabsList().map(t => {
      const selected = t.id === activeTab;
      if (hrefForTab) {
        return `<a class="tab-btn" role="tab" data-tab="${t.id}" aria-selected="${selected}" href="${hrefForTab(t.id)}">${escape(t.label)} <small>${escape(t.short)}</small></a>`;
      }
      return `<button type="button" class="tab-btn" role="tab" data-tab="${t.id}" aria-selected="${selected}">${escape(t.label)} <small>${escape(t.short)}</small></button>`;
    }).join('');
    if (onSelect) {
      bar.querySelectorAll('[data-tab]').forEach(btn => {
        btn.addEventListener('click', () => onSelect(btn.dataset.tab));
      });
    }
    return bar;
  }

  function pager(slug, hrefFor) {
    const tab = tabOf(slug);
    const topics = topicsForTab(tab), at = topics.findIndex(topic => topic.slug === slug);
    const link = (topic, rel, label) => topic
      ? `<a class="pager-link ${rel}" rel="${rel}" href="${hrefFor(topic.slug)}" data-slug="${topic.slug}"><small>${label}</small><b>${escape(topic.num)} · ${escape(topic.nav)}</b><span>${escape(topic.title)}</span></a>`
      : '<span></span>';
    return at < 0 ? '' : link(topics[at - 1], 'prev', '← 上一篇') + link(topics[at + 1], 'next', '下一篇 →');
  }

  // ---------- topic sidebar: the same panel on the reader and on every standalone topic page ----------
  const searchText = topic => `${topic.num} ${topic.nav} ${topic.kicker} ${topic.title} ${topic.problem} ${topic.tab || ''}`.toLowerCase();
  function sidebar(nav, {href, home, activeTab = 'agent'}) {
    const topics = topicsForTab(activeTab);
    const tabMeta = tabsList().find(t => t.id === activeTab);
    const groups = topics.reduce((map, topic) => map.set(topic.group, [...(map.get(topic.group) || []), topic]), new Map());
    const link = topic => `<a class="side-link" href="${href(topic.slug)}" data-slug="${topic.slug}" data-tab="${topic.tab || 'agent'}" data-search="${escape(searchText(topic))}"><span class="num">${escape(topic.num)}</span><span>${escape(topic.nav)}</span></a>`;
    nav.innerHTML = `<a class="side-link home" href="${home}" data-home><span class="num">◆</span><span>${escape(tabMeta ? tabMeta.label : '首頁')} · 總覽</span></a>` +
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

  const LSM_STEPS = [
    {
      label: '1. 初次寫入',
      op: 'CREATE', opClass: '',
      pct: 22, barClass: '', l0Tokens: '1,100 / 5,000 tokens',
      l0State: 'is-active', l1State: '', l2State: '',
      l0: '# api.md（活頭）\n- port = 8000（未驗證，來源：turn 4）\n- auth = bearer token',
      l1: '_index.md：\n- api.md（活躍活頭）',
      l2: '（尚無冷封存分片）',
      what: '任務剛開始，第一次壓縮建立主題筆記 api.md，直接寫進 L0 熱層，並在 L1 索引登記。',
      why: '筆記還很小，不需要封存；主代理之後 read api.md 一次就能看到完整現況。'
    },
    {
      label: '2. 正常 MERGE',
      op: 'MERGE', opClass: '',
      pct: 36, barClass: '', l0Tokens: '1,800 / 5,000 tokens',
      l0State: 'is-active', l1State: '', l2State: '',
      l0: '# api.md（活頭 · 已去重整理）\n- port = 9000（已驗證，取代舊值 8000）\n- auth = bearer token（已確認）\n- timeout = 30s（來源：turn 18）',
      l1: '_index.md：\n- api.md（活躍活頭）',
      l2: '（尚無冷封存分片）',
      what: '新回合把 port 改成 9000。因為「舊筆記 + 新更新 ≤ 門檻 T」，系統呼叫 MERGE，在 L0 原地整合、去重並標明取代關係。',
      why: '這就是為什麼需要 MERGE：把零散重複的對話整理成「單一乾淨現行版」，之後讀起來省 token 又不會誤用舊值 8000。'
    },
    {
      label: '3. 長程累積超限',
      op: 'OVERFLOW > T', opClass: 'warn',
      pct: 100, barClass: 'over', l0Tokens: '5,600 / 5,000 tokens（超過門檻 T！）',
      l0State: 'is-warn', l1State: '', l2State: '',
      l0: '# api.md（活頭 · 跨週累積 40+ 條獨立事實與除錯紀錄）\n- port = 9000 ...\n- retry 策略 v1 → v2 → v3 ...\n- 歷次 502 / 429 錯誤碼與對應 trace ...\n+ [本輪新事實 800 tokens]  ⚠ 合併後將撞爆輸出上限！',
      l1: '_index.md：\n- api.md（活躍活頭）',
      l2: '（尚未封存）',
      what: '任務跑了好幾天，無法刪掉的獨立事實越積越多。此時「既有筆記 + 本輪更新 > 門檻 T_topic」，若硬做原地 MERGE 會被輸出上限截斷而失敗。',
      why: '單靠 MERGE 撐不住無限長程任務——這正是觸發 LSM「Seal & Roll」的瞬間。'
    },
    {
      label: '4. SEAL 封存 L2',
      op: 'SEAL', opClass: 'seal',
      pct: 100, barClass: 'over', l0Tokens: '準備封存舊版快照 → L2',
      l0State: '', l1State: 'is-active', l2State: 'is-seal',
      l0: '# api.md（舊版完整內容待捲動...）',
      l1: '_index.md：\n- api.md（活躍活頭）\n- api-era-001.md（🔒 不可變冷分片，EXTRACT 自動忽略）',
      l2: '🔒 api-era-001.md（SHA-256 鎖定 · 永不改寫）\n原封不動保存第 1～3 步累積的完整 40+ 條歷史紀錄與來源證據',
      what: '系統先把舊版 api.md 一字不漏地寫進 L2 冷層命名為 api-era-001.md，並更新 L1 索引登記這個冷分片。',
      why: '「零靜默刪改」：所有歷史證據與除錯細節完整保留在硬碟上供日後查核，而且未來壓縮不會再去重寫這份冷檔。'
    },
    {
      label: '5. ROLL 瘦身 L0',
      op: 'ROLL', opClass: 'roll',
      pct: 24, barClass: 'slim', l0Tokens: '1,200 / 5,000 tokens（活頭瘦身完成！）',
      l0State: 'is-seal', l1State: '', l2State: '',
      l0: '# api.md（精簡新活頭）\n> 歷史完整紀錄已封存於：api-era-001.md（按需 read/rg）\n- 現行狀態：port=9000, retry v3, timeout=30s\n- 未解問題：429 限流調優中\n- 本輪新事實：已加入指數退避',
      l1: '_index.md：\n- api.md（活躍活頭）\n- api-era-001.md（🔒 冷分片指標）',
      l2: '🔒 api-era-001.md（靜置於磁碟，不佔用 L0 活頭預算）',
      what: '呼叫 ROLL_TOPIC，把「現行活躍狀態 + 本輪新事實 + 冷檔指標」蒸餾成一份全新的輕量 api.md 放回 L0。',
      why: '活頭體積瞬間從 5,600 降回 1,200 tokens，永遠保持在輸出上限內，平時讀取快、精準、不爆窗。'
    },
    {
      label: '6. 回到正常 MERGE',
      op: 'MERGE', opClass: '',
      pct: 34, barClass: '', l0Tokens: '1,700 / 5,000 tokens',
      l0State: 'is-active', l1State: '', l2State: '',
      l0: '# api.md（活頭 · 繼續安全 MERGE）\n> 歷史完整紀錄已封存於：api-era-001.md\n- 現行狀態：port=9000, retry v3, timeout=30s\n- 本輪更新：429 限流已通過壓測 ✓',
      l1: '_index.md：\n- api.md（活躍活頭）\n- api-era-001.md（🔒 冷分片指標）',
      l2: '🔒 api-era-001.md（需要查上週細節時，代理才用 read/rg 去翻）',
      what: '因為 L0 活頭已經瘦身，後續新回合又可以安全地做原地 MERGE；等未來再次超過門檻 T，再封存成 api-era-002.md。',
      why: '循環運作：MERGE 維持平常讀取乾淨，Seal & Roll 保證長程永不膨脹失控。'
    }
  ];

  function mountLSM(root) {
    const {$} = scoped(root), host = $('#lsmSim');
    if (!host) return;
    let idx = 0, timer = null;
    const btns = $('#lsmStepBtns'), playBtn = $('#lsmPlayBtn');
    const stopPlay = () => { if (timer) { clearInterval(timer); timer = null; } if (playBtn) playBtn.textContent = '▶ 自動播放'; };
    const render = i => {
      idx = (i + LSM_STEPS.length) % LSM_STEPS.length;
      const s = LSM_STEPS[idx];
      [...btns.children].forEach((b, bi) => b.setAttribute('aria-pressed', String(bi === idx)));
      $('#lsmL0Box').className = 'lsm-tier ' + s.l0State;
      $('#lsmL1Box').className = 'lsm-tier ' + s.l1State;
      $('#lsmL2Box').className = 'lsm-tier ' + s.l2State;
      const fill = $('#lsmMeterFill');
      fill.style.width = `${s.pct}%`;
      fill.className = 'lsm-meter-fill ' + s.barClass;
      $('#lsmTokens').textContent = s.l0Tokens;
      $('#lsmL0Code').textContent = s.l0;
      $('#lsmL1Code').textContent = s.l1;
      $('#lsmL2Code').textContent = s.l2;
      $('#lsmExplain').innerHTML = `<span class="lsm-op ${s.opClass}">${escape(s.op)}</span><b>發生了什麼：</b>${escape(s.what)}<br><b>為什麼：</b>${escape(s.why)}`;
    };
    LSM_STEPS.forEach((s, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'btn'; b.textContent = s.label;
      b.onclick = () => { stopPlay(); render(i); };
      btns.appendChild(b);
    });
    if (playBtn) {
      playBtn.onclick = () => {
        if (timer) { stopPlay(); return; }
        playBtn.textContent = '⏸ 暫停播放';
        render(idx === LSM_STEPS.length - 1 ? 0 : idx + 1);
        timer = setInterval(() => {
          if (idx === LSM_STEPS.length - 1) { stopPlay(); return; }
          render(idx + 1);
        }, 2600);
      };
    }
    render(0);
  }

  function mount(root, slug) {
    anchorHeadings(root, slug);
    mountLoop(root); mountBudget(root); mountDocument(root); mountWorkflow(root); mountLSM(root);
  }

  window.KentcDocs = {mount, pager, escape, sidebar, markCurrent, filter, trackStickyHeight, tabsList, tabOf, topicsForTab, loadTab, saveTab, renderTabsBar};

  if (document.body.classList.contains('topic-page')) {
    const main = document.getElementById('topic'), slug = main.dataset.slug, nav = document.getElementById('sideNav');
    const search = document.getElementById('search');
    const activeTab = tabOf(slug);
    saveTab(activeTab);
    const topics = topicsForTab(activeTab);
    renderTabsBar(activeTab, {
      hrefForTab: tab => `../index.html#tab=${tab}`
    });
    sidebar(nav, {href: target => `${target}.html`, home: `../index.html#tab=${activeTab}`, activeTab});
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
