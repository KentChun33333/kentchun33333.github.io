(() => {
  'use strict';

  const get = id => document.getElementById(id);
  const format = value => Math.round(value).toLocaleString('zh-TW');
  const svgNS = 'http://www.w3.org/2000/svg';
  const nodeWidth = 252;
  const nodeHeight = 116;
  const source = file => '../src/kentc_agent/' + file;
  let budget;
  let current = 'window';
  let selected = null;
  let guided = false;

  const diagrams = {
    window: {
      kind: '額度關係', title: '部署上限如何變成工作額度', height: 540,
      description: '箭頭表示數值依賴。R 是壓縮策略，K 是保留目標，兩者會影響同一份歷史。主路徑可從 D 讀到 W 與 R。',
      route: ['deployment', 'window', 'reserve'],
      lanes: [[28, 28, '部署與設定'], [385, 28, '主代理工作視窗'], [750, 18, '有效保留策略']],
      nodes: [
        {id: 'deployment', x: 28, y: 80, code: 'D / DEPLOYMENT', title: '部署上下文上限',
          value: b => format(b.D), subtitle: () => '由模型部署回報或明確設定',
          detail: () => '這是目前模型部署的容量。主代理工作視窗與文件子代理都會參考它。工作上限只能在這個容量內選擇。',
          formula: 'D = llm.info().context_window', file: 'agent/budget.py'},
        {id: 'setting', x: 28, y: 270, code: 'B / CONFIGURATION', title: '設定的工作上限',
          value: b => b.B === 0 ? '沿用 D' : format(b.B), subtitle: () => 'context_budget_tokens',
          detail: () => '這是你指定給主代理的工作上限。設為 0 時採用部署上限，設為正數時和 D 取較小值。',
          formula: '--context-budget-tokens B', file: 'agent/budget.py'},
        {id: 'window', x: 385, y: 175, code: 'W / WORKING WINDOW', title: '實際工作視窗',
          value: b => format(b.W), subtitle: () => '部署與設定共同決定',
          detail: b => '本輪工作視窗為 ' + format(b.W) + ' tokens。壓縮策略與安全餘裕依這個 W 計算。文件解析子代理另採部署容量 D。',
          formula: 'B > 0 ? min(D, B) : D', file: 'agent/budget.py'},
        {id: 'reserve', x: 750, y: 35, tone: 'amber', code: 'R / RESERVE', title: '壓縮 buffer',
          value: b => format(b.R), subtitle: b => '一般壓縮門檻 ' + format(b.W - b.R),
          detail: b => 'R 受設定上限與 W 的四分之一共同限制。T 加上狀態提示預留 F，超過 ' + format(b.W - b.R) + ' 時嘗試壓縮。',
          formula: 'R = min(reserve_tokens, floor(W / 4))', file: 'agent/budget.py'},
        {id: 'recent', x: 750, y: 205, code: 'K / RECENT HISTORY', title: '近期保留目標',
          value: b => format(b.K), subtitle: () => '保留較近的訊息與工具配對',
          detail: () => '壓縮會從最新訊息往回找保留範圍，再移到合法切點。K 是挑選目標，實際保留量會受到訊息大小、切點與強制壓縮影響。',
          formula: 'K = min(keep_recent_tokens, floor(W / 3))', file: 'agent/budget.py'},
        {id: 'margin', x: 750, y: 375, tone: 'amber', code: 'M / SAFETY MARGIN', title: '請求安全餘裕',
          value: b => format(b.M), subtitle: () => '工作視窗的 5%，最低 256',
          detail: () => '在計算回覆空間與完整請求預檢時，都會扣掉安全餘裕。它為 token 估算誤差留出空間。',
          formula: 'M = max(256, floor(W / 20))', file: 'agent/budget.py'}
      ],
      edges: [
        {from: 'deployment', to: 'window'},
        {from: 'setting', to: 'window'},
        {from: 'window', to: 'reserve'},
        {from: 'window', to: 'recent'},
        {from: 'window', to: 'margin'}
      ]
    },
    capacity: {
      kind: '動態預算', title: '用量增加，回覆與工具額度怎麼變', height: 480,
      description: 'T 已包含本輪密度校準的估算。room 再扣除 M 與 F，回覆與工具額度各自套用上限。主路徑從 T 走到工具額度 A。',
      route: ['used', 'room', 'tools'],
      lanes: [[28, 28, '當輪容量與用量'], [385, 28, '剩餘空間'], [750, 28, '回覆與工具']],
      nodes: [
        {id: 'window', x: 28, y: 70, code: 'W / CAPACITY', title: '主代理工作視窗',
          value: b => format(b.W), subtitle: () => '本輪上下文可用的總範圍',
          detail: () => '同一個 W 用來計算歷史壓縮門檻和請求餘裕。剩餘空間還要考慮目前用量與狀態提示。',
          formula: 'W = B > 0 ? min(D, B) : D', file: 'agent/budget.py'},
        {id: 'used', x: 28, y: 290, code: 'T / CURRENT CONTEXT', title: '當輪上下文估算',
          value: b => format(b.T), subtitle: b => '另預留狀態提示 F = ' + format(b.F),
          detail: () => 'T 使用最近可用的 usage 作錨點，再加上後續訊息的估算。移動下方用量滑桿，可以觀察 room、回覆與工具門檻的變化。',
          formula: 'T = counted + ceil(estimated × density)', file: 'adapters/session.py'},
        {id: 'room', x: 385, y: 180, code: 'ROOM / REPLY SPACE', title: '回覆可用空間',
          value: b => format(b.room), subtitle: b => '扣除 M ' + format(b.M) + ' 與 F ' + format(b.F),
          detail: b => '目前 room 為 ' + format(b.room) + '。低於 1,024 tokens 時先嘗試強制壓縮。完整請求還會以 Q 再檢查一次。',
          formula: 'room = W − T − M − F', file: 'agent/budget.py'},
        {id: 'reply', x: 750, y: 70, tone: 'green', code: 'MODEL / OUTPUT', title: '候選回覆額度',
          value: b => b.reply === 0 ? '需先恢復' : format(b.reply), subtitle: b => '設定輸出上限 O = ' + format(b.O),
          detail: () => '回覆額度同時考慮 max_output_tokens、room 與完整請求預檢。伺服器仍可能回報更小的可用額度，觸發縮減或壓縮。',
          formula: '候選值受 O、room、W − Q − M 共同限制', file: 'agent/loop.py'},
        {id: 'tools', x: 750, y: 290, code: 'A / TOOL ALLOWANCE', title: '工具結果分配',
          value: b => format(b.A), subtitle: b => '單筆 ' + format(b.single) + ' · 整批 ' + format(b.batch),
          detail: b => '工具分配 A 會再套用單筆與批次上限。此刻工具摘要額度為 ' + format(b.brief) + '，成功寫入參數的外存門檻為 ' + format(b.write) + ' tokens。A 的最低值為 128，送出仍需通過預檢。',
          formula: 'A = max(128, room − R)', file: 'context/bigcontext.py'}
      ],
      edges: [
        {from: 'window', to: 'room'},
        {from: 'used', to: 'room'},
        {from: 'room', to: 'reply'},
        {from: 'room', to: 'tools'}
      ]
    },
    write: {
      kind: '工具呼叫流程', title: '長文件寫入成功後，正文如何移出上下文', height: 630,
      description: '第一次生成要帶完整參數。成功且超過門檻時，先保存原參數再替換 live history。呼叫 ID 與工具結果繼續配對。',
      route: ['generated', 'execute', 'gate', 'archive', 'shortcut', 'next'],
      lanes: [[28, 28, '本輪生成與執行'], [750, 237, '參數存檔'], [28, 237, '後續請求']],
      nodes: [
        {id: 'generated', x: 28, y: 65, code: '01 / GENERATE', title: '模型生成完整參數',
          value: () => 'write / edit', subtitle: () => '正文佔用本輪輸出額度',
          detail: () => '模型先產生含正文的完整 JSON。回覆截斷或參數 JSON 不完整時，會先拒絕並有限次重試。尚未通過驗證的寫入呼叫不會執行。',
          formula: '完整 tool arguments → 回覆驗證', file: 'agent/loop.py'},
        {id: 'execute', x: 385, y: 65, code: '02 / EXECUTE', title: '執行寫入或編輯',
          value: () => '工具回傳', subtitle: () => '正文先寫入目標檔案',
          detail: () => '內建 write 或 edit 以原始參數執行。工具回傳與呼叫配對保存後，程式才考慮縮短參數。',
          formula: '執行工具 → 保存工具結果', file: 'agent/executor.py'},
        {id: 'gate', x: 750, y: 65, tone: 'amber', code: '03 / CHECK', title: '成功且參數超限？',
          value: b => '> ' + format(b.write), subtitle: () => '門檻按當時剩餘空間計算',
          detail: b => '只處理成功的內建 write 或 edit。圖上本輪門檻是 ' + format(b.write) + ' tokens，執行成功後會依當時空間再判斷。失敗、小參數或存檔失敗時保留原參數。',
          formula: '成功且大小 > max(512, 單筆工具結果門檻)', file: 'agent/executor.py'},
        {id: 'archive', x: 750, y: 270, tone: 'violet', code: '04 / ARCHIVE', title: '保存原始參數',
          value: () => 'arguments', subtitle: () => '原始 JSON + 索引 ID + 來源',
          detail: () => '原始參數逐字寫入工作區，索引記錄訊息 ID、呼叫 ID 和工具名。原始 session 訊息也仍在 append-only log 中。目標檔日後被改動時，仍能核對當次參數。',
          formula: 'memory.archive(kind="arguments")', file: 'agent/executor.py'},
        {id: 'shortcut', x: 385, y: 270, tone: 'green', code: '05 / SHORTCUT', title: '換成歷史捷徑',
          value: () => '路徑 + ID', subtitle: () => '替換正文，保存工具配對',
          detail: () => '有效對話保留目標路徑與呼叫 ID，把大型正文換成存檔參照。session 另寫入替換事件，重新載入時會還原相同捷徑。',
          formula: 'Session.replace_tool_arguments()', file: 'adapters/session.py'},
        {id: 'next', x: 28, y: 270, tone: 'green', code: '06 / CONTINUE', title: '下一輪只帶捷徑',
          value: () => '按需回讀', subtitle: () => '目前正文讀目標檔，原參數查索引',
          detail: () => '模型可按需讀取目標檔或原始參數存檔。後續壓縮接收到的工具呼叫也使用捷徑，減少重送大型正文。',
          formula: '下一輪 context → 簡短參照', file: 'agent/loop.py'},
        {id: 'original', x: 385, y: 470, tone: 'red', code: 'FALLBACK / KEEP', title: '保留原參數',
          value: () => '仍可修正', subtitle: () => '寫入失敗、小參數或存檔失敗',
          detail: () => '未符合縮短條件時，原參數留在有效對話。成功寫入後若參數存檔遇到 I/O 錯誤，會回報狀態並繼續使用原參數。',
          formula: '跳過參數替換', file: 'agent/executor.py'}
      ],
      edges: [
        {from: 'generated', to: 'execute'},
        {from: 'execute', to: 'gate'},
        {from: 'gate', to: 'archive', fromSide: 'bottom', toSide: 'top', label: [900, 225, '成功且超限']},
        {from: 'archive', to: 'shortcut', fromSide: 'left', toSide: 'right'},
        {from: 'shortcut', to: 'next', fromSide: 'left', toSide: 'right'},
        {from: 'gate', to: 'original', toSide: 'right', via: [[1060, 123], [1060, 528]], label: [828, 510, '未符合縮短條件']},
        {from: 'original', to: 'next', fromSide: 'left', toSide: 'right', via: [[330, 528], [330, 328]]}
      ]
    },
    history: {
      kind: '歷史資料流', title: '壓縮、原文與下一輪上下文的關係', height: 630,
      description: '歷史先存檔，再交給模型寫 checkpoint。近期訊息與有效的固定要求另外帶入下一輪，精確資料透過索引回讀。',
      route: ['history', 'cut', 'archive', 'summarizer', 'checkpoint', 'next'],
      lanes: [[28, 28, '有效對話'], [750, 237, '摘要呼叫'], [28, 437, '另外保留的資訊']],
      nodes: [
        {id: 'history', x: 28, y: 65, code: '01 / LIVE HISTORY', title: '對話累積到門檻',
          value: b => format(b.W - b.R), subtitle: () => 'T + F 超過時嘗試一般壓縮',
          detail: () => '每次主模型請求前檢查容量。一般壓縮、低回覆空間的強制壓縮、完整請求預檢與伺服器超限，都可能進入恢復流程。',
          formula: 'T + F > W − R', file: 'agent/loop.py'},
        {id: 'cut', x: 385, y: 65, tone: 'amber', code: '02 / BOUNDARY', title: '找合法切點',
          value: b => 'K ' + format(b.K), subtitle: () => '維持工具呼叫與結果配對',
          detail: () => '從最新訊息往回估算，切在 user 或 assistant 訊息。K 是近期保留目標，強制壓縮時可能改用更靠後的合法切點。',
          formula: 'find_cut(messages, K / density)', file: 'context/compaction.py'},
        {id: 'archive', x: 750, y: 65, tone: 'violet', code: '03 / PRESERVE', title: '先保存被移出的歷史',
          value: () => 'history', subtitle: () => '舊訊息 + 上一份 checkpoint',
          detail: () => '在生成摘要之前存檔。若工具參數或結果已有外存捷徑，歷史存檔保留這些捷徑，原文可再沿索引取回。',
          formula: 'memory.archive(kind="history")', file: 'agent/budget.py'},
        {id: 'summarizer', x: 750, y: 270, code: '04 / SUMMARIZE', title: '模型更新 checkpoint',
          value: b => format(b.summary) + ' tokens', subtitle: () => '長歷史分批折疊進摘要',
          detail: () => '模型使用固定章節整理目標、要求、完成條件、進度、證據、決策與下一步。單筆工具結果在摘要輸入中最多保留開頭 2,000 字元。截斷或空白回覆會再試一次。',
          formula: 'min(floor(0.8 × R), max_output_tokens)', file: 'context/compaction.py'},
        {id: 'checkpoint', x: 385, y: 270, tone: 'green', code: '05 / CHECKPOINT', title: '提交新摘要',
          value: b => format(b.words) + ' words', subtitle: () => '提示中的字數目標',
          detail: () => '摘要有內容且未因長度截斷，才提交 compaction 事件並移出舊訊息。章節與字數由寫作提示要求，仍須沿原文驗證細節。',
          formula: 'Session.compact(summary, first_kept, ...)', file: 'adapters/session.py'},
        {id: 'next', x: 28, y: 270, tone: 'green', code: '06 / NEXT REQUEST', title: '重建下一輪請求',
          value: () => '摘要 + 近期', subtitle: () => '加上狀態提示與有效固定要求',
          detail: () => '系統提示、最新 checkpoint、近期訊息與有效的固定要求構成下一輪內容。runtime 狀態顯示索引路徑與最近三筆記錄，細節按需回讀。',
          formula: 'runtime notice + Session.context()', file: 'agent/loop.py'},
        {id: 'recent', x: 28, y: 470, code: 'RETAIN / CURRENT', title: '近期訊息與固定要求',
          value: () => '保留原文', subtitle: () => '要求可由 /require 明確固定',
          detail: () => '近期訊息留在有效對話。使用者明確固定的要求另外存入 session 事件，每輪帶入。第一則一般 prompt 仍遵循一般歷史壓縮規則。',
          formula: 'summary + active requirements + live messages', file: 'adapters/session.py'},
        {id: 'index', x: 750, y: 470, tone: 'violet', code: 'RECOVER / WORKSPACE', title: '工作區索引與原文',
          value: () => 'index.md', subtitle: () => '工具結果、原參數、歷史與證據',
          detail: () => '索引是可重建的目錄，列出每份原文快照的 ID 和路徑。模型可按行或字元回讀，重開同一 session 時仍能使用。',
          formula: '.kentc-agent/memory/<session>/index.md', file: 'context/memory.py'}
      ],
      edges: [
        {from: 'history', to: 'cut'},
        {from: 'cut', to: 'archive'},
        {from: 'archive', to: 'summarizer', fromSide: 'bottom', toSide: 'top'},
        {from: 'summarizer', to: 'checkpoint', fromSide: 'left', toSide: 'right'},
        {from: 'checkpoint', to: 'next', fromSide: 'left', toSide: 'right'},
        {from: 'recent', to: 'next', fromSide: 'top', toSide: 'bottom'},
        {from: 'index', to: 'next', fromSide: 'left', toSide: 'bottom',
          via: [[330, 528], [330, 425], [154, 425]], label: [450, 510, '需要細節時回讀']}
      ]
    }
  };

  function svgElement(tag, attributes = {}, text) {
    const element = document.createElementNS(svgNS, tag);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function port(node, side) {
    const x = node.x;
    const y = node.y;
    if (side === 'top') return [x + nodeWidth / 2, y];
    if (side === 'bottom') return [x + nodeWidth / 2, y + nodeHeight];
    if (side === 'left') return [x, y + nodeHeight / 2];
    return [x + nodeWidth, y + nodeHeight / 2];
  }

  function edgePath(edge, nodes) {
    const start = port(nodes.get(edge.from), edge.fromSide || 'right');
    const end = port(nodes.get(edge.to), edge.toSide || 'left');
    let middle = edge.via || [];
    if (!edge.via && start[0] !== end[0] && start[1] !== end[1]) {
      const x = (start[0] + end[0]) / 2;
      middle = [[x, start[1]], [x, end[1]]];
    }
    return [start, ...middle, end].map(([x, y], index) => (index === 0 ? 'M ' : 'L ') + x + ' ' + y).join(' ');
  }

  function inspect(diagram) {
    const node = diagram.nodes.find(item => item.id === selected);
    const step = diagram.route.indexOf(selected);
    get('diagram-position').textContent = selected === null ? '全圖' : step < 0 ? '支線節點' : (step + 1) + ' / ' + diagram.route.length;
    get('diagram-previous').disabled = step <= 0;
    get('diagram-next').disabled = step === diagram.route.length - 1;
    get('diagram-node-label').textContent = node ? node.code : '圖解導讀';
    get('diagram-node-title').textContent = node ? node.title : '選節點，或沿主要路徑閱讀';
    get('diagram-node-detail').textContent = node ? node.detail(budget) : diagram.description;
    get('diagram-node-formula').hidden = !node;
    get('diagram-node-source').hidden = !node;
    if (node) {
      get('diagram-node-formula').textContent = node.formula;
      get('diagram-node-source').href = source(node.file);
      get('diagram-node-source').textContent = '查看實作 · ' + node.file;
    }
  }

  function selectNode(id, journey = false) {
    selected = id;
    guided = journey;
    draw();
    if (id) {
      const node = diagrams[current].nodes.find(item => item.id === id);
      const canvas = get('diagram-canvas');
      const svg = canvas.querySelector('svg');
      const ratio = svg.getBoundingClientRect().width / 1120;
      canvas.scrollLeft = (node.x + nodeWidth / 2) * ratio - canvas.clientWidth / 2;
    }
  }

  function draw() {
    if (!budget || !budget.valid) return;
    const diagram = diagrams[current];
    get('diagram-kind').textContent = diagram.kind;
    get('diagram-title').textContent = diagram.title;
    get('diagram-description').textContent = diagram.description;
    get('diagram-live').textContent = 'W ' + format(budget.W) + ' · T ' + format(budget.T);
    const nodes = new Map(diagram.nodes.map(node => [node.id, node]));
    const relevant = new Set(selected ? [selected] : []);
    const routeEdges = new Set();
    if (selected && guided) {
      const index = diagram.route.indexOf(selected);
      for (let i = 0; i <= index; i++) {
        relevant.add(diagram.route[i]);
        if (i > 0) routeEdges.add(diagram.route[i - 1] + '~' + diagram.route[i]);
      }
    } else if (selected) {
      for (const edge of diagram.edges) {
        if (edge.from === selected || edge.to === selected) {
          relevant.add(edge.from);
          relevant.add(edge.to);
          routeEdges.add(edge.from + '~' + edge.to);
        }
      }
    }

    const svg = svgElement('svg', {
      viewBox: '0 0 1120 ' + diagram.height, role: 'group', 'aria-labelledby': 'map-title map-description'
    });
    svg.append(svgElement('title', {id: 'map-title'}, diagram.title));
    svg.append(svgElement('desc', {id: 'map-description'}, diagram.description));
    const defs = svgElement('defs');
    for (const [id, color] of [['arrow-normal', '#8d9ba7'], ['arrow-active', '#245db2']]) {
      const marker = svgElement('marker', {id, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: 'auto', markerUnits: 'userSpaceOnUse'});
      marker.append(svgElement('path', {d: 'M 0 0 L 8 4 L 0 8 Z', fill: color}));
      defs.append(marker);
    }
    svg.append(defs);
    for (const [x, y, text] of diagram.lanes) svg.append(svgElement('text', {x, y, class: 'diagram-lane'}, text));

    for (const edge of diagram.edges) {
      const active = routeEdges.has(edge.from + '~' + edge.to);
      const dimmed = selected && !active;
      svg.append(svgElement('path', {
        d: edgePath(edge, nodes),
        class: 'diagram-edge' + (active ? ' active' : '') + (dimmed ? ' dimmed' : ''),
        'marker-end': 'url(#' + (active ? 'arrow-active' : 'arrow-normal') + ')',
        'data-edge': edge.from + '~' + edge.to
      }));
      if (edge.label) {
        const [x, y, text] = edge.label;
        svg.append(svgElement('text', {x, y, class: 'diagram-edge-label' + (dimmed ? ' dimmed' : '')}, text));
      }
    }

    for (const node of diagram.nodes) {
      const value = node.value(budget);
      const group = svgElement('g', {
        class: 'diagram-node ' + (node.tone || 'blue') +
          (selected === node.id ? ' selected' : '') + (selected && !relevant.has(node.id) ? ' dimmed' : ''),
        transform: 'translate(' + node.x + ' ' + node.y + ')', tabindex: 0, role: 'button',
        'aria-label': node.title + '，' + value, 'aria-pressed': String(selected === node.id), 'data-node': node.id
      });
      group.append(svgElement('rect', {width: nodeWidth, height: nodeHeight, rx: 11, class: 'node-body'}));
      group.append(svgElement('rect', {x: 12, y: 12, width: 228, height: 20, rx: 4, class: 'node-cap'}));
      group.append(svgElement('text', {x: 20, y: 26, class: 'node-code'}, node.code));
      group.append(svgElement('text', {x: 18, y: 53, class: 'node-title'}, node.title));
      group.append(svgElement('text', {x: 18, y: 82, class: 'node-value'}, value));
      group.append(svgElement('text', {x: 18, y: 104, class: 'node-subtitle'}, node.subtitle(budget)));
      group.addEventListener('click', () => selectNode(node.id));
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectNode(node.id);
          get('diagram-canvas').querySelector('[data-node="' + node.id + '"]').focus({preventScroll: true});
        }
      });
      svg.append(group);
    }
    svg.style.width = Number(get('diagram-zoom').value) * 100 + '%';
    get('diagram-canvas').replaceChildren(svg);
    inspect(diagram);
  }

  function switchDiagram(name) {
    current = name;
    selected = null;
    guided = false;
    for (const tab of document.querySelectorAll('[data-diagram]')) {
      const active = tab.dataset.diagram === name;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    }
    get('diagram-panel').setAttribute('aria-labelledby', 'tab-' + name);
    get('diagram-canvas').scrollLeft = 0;
    draw();
  }

  const tabs = [...document.querySelectorAll('[data-diagram]')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => switchDiagram(tab.dataset.diagram));
    tab.addEventListener('keydown', event => {
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else return;
      event.preventDefault();
      switchDiagram(tabs[next].dataset.diagram);
      tabs[next].focus();
    });
  });
  get('diagram-reset').addEventListener('click', () => selectNode(null));
  get('diagram-next').addEventListener('click', () => {
    const route = diagrams[current].route;
    selectNode(route[Math.min(route.indexOf(selected) + 1, route.length - 1)], true);
  });
  get('diagram-previous').addEventListener('click', () => {
    const route = diagrams[current].route;
    selectNode(route[Math.max(0, route.indexOf(selected) - 1)], true);
  });
  get('diagram-zoom').addEventListener('change', draw);
  document.addEventListener('budget:update', event => {
    budget = event.detail;
    get('diagram-invalid').hidden = budget.valid;
    get('diagram-content').hidden = !budget.valid;
    for (const id of ['diagram-next', 'diagram-previous', 'diagram-reset', 'diagram-zoom']) get(id).disabled = !budget.valid;
    draw();
  });
})();
