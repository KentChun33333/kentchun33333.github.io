(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const format = value => Math.round(value).toLocaleString('zh-TW');
  const form = byId('budget-form');
  const integerFields = [
    'deployment', 'working', 'reserve', 'recent', 'output', 'result', 'turn', 'digest'
  ];

  function number(id, optional = false) {
    const field = byId(id);
    if (optional && field.value.trim() === '') {
      field.setAttribute('aria-invalid', 'false');
      return null;
    }
    const value = Number(field.value);
    const integral = integerFields.includes(id) || id === 'prompt';
    const valid = field.value.trim() !== '' && field.validity.valid &&
      Number.isFinite(value) && (!integral || Number.isSafeInteger(value));
    field.setAttribute('aria-invalid', String(!valid));
    return valid ? value : undefined;
  }

  function drawValues(id, values, definitions = false) {
    const container = byId(id);
    container.replaceChildren();
    for (const [label, value] of values) {
      const item = document.createElement('div');
      const name = document.createElement(definitions ? 'dt' : 'span');
      const content = document.createElement(definitions ? 'dd' : 'b');
      name.textContent = label;
      content.textContent = typeof value === 'number' ? format(value) : value;
      item.append(name, content);
      container.append(item);
    }
  }

  function drawLimits(rows) {
    const body = byId('limits-body');
    body.replaceChildren();
    for (const [key, label, kind, setting, value, formula, unit = 'tokens'] of rows) {
      const row = document.createElement('tr');
      row.dataset.limit = key;
      const name = document.createElement('th');
      name.scope = 'row';
      name.textContent = label;
      const tag = document.createElement('span');
      tag.className = 'limit-kind';
      tag.textContent = kind;
      name.append(tag);
      const cap = document.createElement('td');
      cap.dataset.label = '設定或邊界';
      cap.textContent = setting;
      const result = document.createElement('td');
      result.className = 'limit-value';
      result.dataset.label = '本輪有效值';
      result.dataset.value = value;
      result.textContent = format(value) + ' ' + unit;
      const rule = document.createElement('td');
      const code = document.createElement('code');
      code.textContent = formula;
      rule.append(code);
      row.append(name, cap, result, rule);
      body.append(row);
    }
  }

  function render() {
    const values = {};
    for (const id of [...integerFields, 'density']) values[id] = number(id);
    values.prompt = number('prompt', true);
    const invalid = Object.values(values).some(value => value === undefined);
    byId('validation').hidden = !invalid;
    byId('results').hidden = invalid;
    byId('limits').hidden = invalid;
    if (invalid) {
      byId('validation').textContent = '請依欄位範圍輸入有效數字，token 額度使用整數。';
      document.dispatchEvent(new CustomEvent('budget:update', {detail: {valid: false}}));
      return;
    }

    const {deployment: D, working: B, density, reserve, recent, output: O, result, turn, digest} = values;
    const W = B > 0 ? Math.min(D, B) : D;
    const usage = byId('usage');
    usage.max = Math.ceil(W * 1.2);
    const T = Number(usage.value);
    byId('usage-value').textContent = format(T) + ' tokens';
    const R = Math.min(reserve, Math.floor(W / 4));
    const K = Math.min(recent, Math.floor(W / 3));
    const M = Math.max(256, Math.floor(W / 20));
    const F = Math.ceil(512 * density);
    const room = W - T - M - F;
    const A = Math.max(128, room - R);
    const single = Math.min(result, Math.floor(D / 20), Math.max(64, Math.floor(A / 4)));
    const batch = Math.min(turn, Math.floor(D / 5), A);
    const brief = Math.min(digest, Math.floor(D / 40), Math.max(32, Math.floor(A / 8)));
    const write = Math.max(512, single);
    const input = Math.max(512, Math.min(turn, Math.floor(W / 5)));
    const summary = Math.min(Math.floor(0.8 * R), O);
    const words = Math.floor(Math.max(300, Math.min(4000, Math.floor(W / 16))) * 3 / 4);
    const Q = values.prompt === null ? T + F : values.prompt;
    const available = W - Q - M;
    const reply = available < 512 ? 0 : Math.min(Math.max(512, Math.min(O, room)), available);

    drawValues('summary', [
      ['有效工作視窗 W', W], ['壓縮 buffer R', R], ['壓縮門檻 W − R', W - R], ['近期保留目標 K', K]
    ]);
    byId('threshold-track').style.width = ((W - R) / W * 100) + '%';
    byId('usage-marker').style.left = 'calc(' + Math.min(100, (T + F) / W * 100) + '% - 3px)';

    const decision = byId('decision');
    if (available < 512) {
      decision.className = 'verdict bad';
      decision.textContent = '本輪完整請求估算 Q = ' + format(Q) + '，扣除安全餘裕後剩 ' +
        format(available) + ' tokens。送出前需要壓縮並重算，仍不足時會在本機報超限。';
    } else if (room < 1024) {
      decision.className = 'verdict warn';
      decision.textContent = '回覆空間 room = ' + format(room) + '，低於 1,024。程式會先嘗試強制壓縮。';
    } else if (T + F > W - R) {
      decision.className = 'verdict warn';
      decision.textContent = 'T + F = ' + format(T + F) + '，超過一般壓縮門檻 ' +
        format(W - R) + '。程式會先嘗試壓縮歷史。';
    } else {
      decision.className = 'verdict ok';
      decision.textContent = 'T + F = ' + format(T + F) + '，位於一般壓縮門檻內。當輪候選回覆額度為 ' +
        format(reply) + ' tokens，還會受伺服器回報的限制影響。';
    }

    drawValues('capacity', [
      ['回覆空間 room', room],
      ['完整請求估算 Q', Q],
      ['送出前候選回覆', available < 512 ? '需先恢復' : format(reply) + ' tokens'],
      ['工具結果可分配額度 A', A],
      ['單筆工具結果門檻', single],
      ['成功寫入參數門檻', write]
    ], true);

    const docOutput = Math.min(O, Math.floor(D / 2));
    const docMargin = Math.max(256, Math.floor(D / 20));
    const docReserve = Math.max(Math.max(docOutput, 1024) + docMargin, Math.min(reserve, Math.floor(D / 4)));
    drawValues('document', [
      ['獨立部署視窗', D],
      ['輸出額度', docOutput],
      ['文件輸入 envelope', D - docReserve],
      ['doc_chunk_tokens 預設上限', 12000]
    ], true);

    drawLimits([
      ['window', '工作視窗 W', '隨部署與工作設定', B === 0 ? 'B = 0，沿用 D' : 'B = ' + format(B),
        W, 'B > 0 ? min(D, B) : D'],
      ['reserve', '壓縮 buffer R', '隨視窗縮放，有上限', format(reserve),
        R, 'min(reserve_tokens, floor(W / 4))'],
      ['threshold', '壓縮門檻', '觸發時比較 T + F', 'T + F 超過時嘗試壓縮',
        W - R, 'W − R'],
      ['recent', '近期保留目標 K', '隨視窗縮放，有上限', format(recent),
        K, 'min(keep_recent_tokens, floor(W / 3))'],
      ['margin', '安全餘裕 M', '視窗的 5%，最低 256', '最低 256',
        M, 'max(256, floor(W / 20))'],
      ['feedback', '狀態提示預留 F', '隨 density 變動', '基準 512',
        F, 'ceil(512 × density)'],
      ['reply', '送出前候選回覆', '依 room 與 Q 調整', format(O),
        reply, '若 W − Q − M ≥ 512，取 min(max(512, min(O, room)), W − Q − M)'],
      ['available', '工具結果分配 A', '依剩餘空間', '最低 128',
        A, 'max(128, room − R)'],
      ['single', '單筆工具結果', '部署比例與剩餘空間共同限制', format(result),
        single, 'min(big_result_tokens, floor(D / 20), max(64, floor(A / 4)))'],
      ['batch', '本輪工具結果合計', '部署比例與剩餘空間共同限制', format(turn),
        batch, 'min(big_turn_tokens, floor(D / 5), A)'],
      ['digest', '工具結果摘要額度', '部署比例與剩餘空間共同限制', format(digest),
        brief, 'min(big_digest_tokens, floor(D / 40), max(32, floor(A / 8)))'],
      ['write', '成功 write/edit 參數外存', '成功後再判斷，最低 512', '單筆結果門檻與 512 取較大值',
        write, 'max(512, 單筆工具結果門檻)'],
      ['input', '大型 user 文字外存', '隨工作視窗，有上限與下限', format(turn) + ' / 最低 512',
        input, 'max(512, min(big_turn_tokens, floor(W / 5)))'],
      ['summary', '歷史摘要輸出上限', '由 R 與輸出設定決定', format(O),
        summary, 'min(floor(0.8 × R), max_output_tokens)'],
      ['words', 'checkpoint 字數目標', '寫入摘要提示的目標', '依視窗計算',
        words, 'floor(3 × clamp(floor(W / 16), 300, 4000) / 4)', 'words']
    ]);
    document.dispatchEvent(new CustomEvent('budget:update', {detail: {
      valid: true, D, B, W, T, R, K, M, F, room, A, O, reply, single, batch, brief, write, input, summary, words
    }}));
  }

  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', render);
  byId('scenario').addEventListener('change', event => {
    const scenarios = {
      normal: [60000, 24000],
      near: [60000, 44500],
      small: [12000, 6000],
      large: [120000, 24000]
    };
    const scenario = event.target.value;
    const [working, usage] = scenarios[scenario];
    form.reset();
    byId('scenario').value = scenario;
    byId('working').value = working;
    byId('usage').max = Math.ceil(working * 1.2);
    byId('usage').value = usage;
    render();
  });
  render();
})();
