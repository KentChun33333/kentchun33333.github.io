(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const fmt = value => Math.round(value).toLocaleString('zh-TW');
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const integer = (id, min, max = 2000000) => {
    const field = $(id), value = Number(field.value);
    const valid = field.value.trim() !== '' && Number.isSafeInteger(value) && value >= min && value <= max;
    field.setAttribute('aria-invalid', String(!valid));
    return valid ? value : null;
  };
  const showVerdict = (id, tone, text) => { const el = $(id); el.className = 'verdict ' + tone; el.textContent = text; };
  const renderKV = (id, rows) => { $(id).innerHTML = rows.map(([label, value]) => `<div><span>${escape(label)}</span><b>${escape(typeof value === 'number' ? fmt(value) : value)}</b></div>`).join(''); };
  const budget = w => ({reserve:Math.min(16384,Math.floor(w/4)),keep:Math.min(20000,Math.floor(w/3)),margin:Math.max(256,Math.floor(w/20)),result:Math.min(3000,Math.floor(w/20)),turn:Math.min(12000,Math.floor(w/5)),digest:Math.min(1500,Math.floor(w/40))});
  let W = 15536, O = 8192;
  const STEPS = [
    ['準備上下文','Agent._call → _try_compact / room',['先前已重新偵測部署；本輪用該能力快照計算 W。','計數由伺服器 usage 與經 density 校準的新訊息估算構成。','超過門檻先壓縮；回覆空間太少時嘗試強制壓縮。']],
    ['呼叫模型','LLMClient.chat',['送出系統提示、目前有效上下文，以及本步驟的工具 schema。','輸出請求受 O 與剩餘空間限制；超限時重新偵測，再依伺服器數字調整或壓縮。','僅有思考、沒有可用內容時，主迴圈允許再試一次。']],
    ['保存回覆','Session.append / Agent.last_finish',['保存 assistant 回覆、推理欄位與工具呼叫；usage 用於後續估算。','沒有工具呼叫時回傳答案；length 會標示截斷，不冒充正常完成。','有工具呼叫時繼續處理；中斷修復涵蓋這之後的執行與結果整理。']],
    ['執行工具','Agent._execute → _tool',['依序處理呼叫，先檢查 JSON、必要欄位與 schema 宣告的基本型別。','錯誤型別回傳可修正的工具錯誤，不讓 content=123 進入 write。','ctx.operation 指向目前工具；文件子代理與外存結果可回連到來源操作。']],
    ['整理結果','bigcontext.route_turn → Agent._settle',['一般路徑先按 file / result / turn 三道規則決定外存內容。','完整結果或原檔參照留在工作區，主上下文接收摘要與再讀取路徑。','已完成的工具不因結果路由失敗而重新執行。']],
    ['配對與繼續','Agent._persist_result / _repair / _end',['每個已保存的工具呼叫補齊一個結果；部分已保存的批次不重複附加。','取消或例外時直接修復配對，可能保留尚未路由的原始結果，不假裝正常路由已完成。','追蹤紀錄收尾；一般工具回合繼續下一個 operation，或因上限／取消／錯誤停止。']]
  ];
  const stepButtons = $('#stepBtns');
  function showStep(index) {
    [...stepButtons.children].forEach((button,i) => button.setAttribute('aria-pressed', String(i === index)));
    const [title,fn,items] = STEPS[index];
    $('#stepPanel').innerHTML = `<h3>${index+1}．${title}</h3><div class="fn">${escape(fn)}</div><ul>${items.map(item=>`<li>${escape(item)}</li>`).join('')}</ul>`;
  }
  STEPS.forEach(([title],index) => { const button=document.createElement('button'); button.type='button'; button.className='btn'; button.textContent=`${index+1} ${title}`; button.onclick=()=>showStep(index); stepButtons.appendChild(button); });
  showStep(0);

  function renderBudget() {
    const w=integer('#wInput',1024), o=integer('#outputInput',512);
    if (w===null || o===null) {
      $('#budgetKV').replaceChildren(); $('#budgetBar').replaceChildren(); $('#docKV').replaceChildren();
      showVerdict('#budgetVerdict','bad','請輸入有效整數：W 為 1,024～2,000,000；O 為 512～2,000,000。這是教學元件的輸入範圍，不是伺服器能力範圍。');
      showVerdict('#docVerdict','bad','請先修正上方視窗或輸出參數，文件示意暫停更新。');
      $('#rBody').replaceChildren(); showVerdict('#rVerdict','bad','請先修正上方 W 或 O，避免以舊參數誤讀路由示意。'); return;
    }
    W=w; O=o;
    const range=$('#ctxRange'); range.max=Math.floor(W*1.2); const count=Number(range.value), b=budget(W), threshold=W-b.reserve, room=W-count-b.margin;
    $('#ctxVal').textContent=fmt(count);
    $('#budgetBar').innerHTML=`<div style="width:${threshold/W*100}%;background:var(--blue)">${fmt(threshold)}</div><div style="width:${b.reserve/W*100}%;background:var(--red)">${fmt(b.reserve)}</div><span class="marker" style="left:calc(${Math.min(count/W*100,100)}% - 2px)"></span>`;
    renderKV('#budgetKV',[['壓縮保留量 R',b.reserve],['超過此值先壓縮',threshold],['最近訊息保留目標 K',b.keep],['安全餘裕 M',b.margin],['壓縮前回覆空間 room',room],['壓縮前初步 max_tokens',Math.max(512,Math.min(O,room))],['單筆結果門檻',b.result],['本輪結果預算',b.turn]]);
    if(count>threshold) showVerdict('#budgetVerdict','warn',`${fmt(count)} > ${fmt(threshold)}：先嘗試壓縮舊對話，保留最近約 ${fmt(b.keep)} tokens 與結構化摘要。上列是壓縮前數值，不能當成壓縮後請求的保證。`);
    else if(room<1024) showVerdict('#budgetVerdict','bad',`room = ${fmt(room)}，低於 1,024：嘗試強制壓縮；不能宣稱目前輸入與回覆都放得下。`);
    else showVerdict('#budgetVerdict','ok',`依此估算尚有空間：初步請求 max_tokens = ${fmt(Math.max(512,Math.min(O,room)))}。這是估算，不是伺服器已接受；實際仍以部署回覆與 usage 校準。`);
    renderRouter(); renderDocument();
  }
  $('#wPreset').onchange=()=>{ $('#wInput').value=$('#wPreset').value; $('#ctxRange').value=Math.min(Number($('#ctxRange').value),Math.floor(Number($('#wPreset').value)*.6)); renderBudget(); };
  $('#wInput').oninput=renderBudget; $('#outputInput').oninput=renderBudget; $('#ctxRange').oninput=renderBudget;

  const LABEL={text:'文字／程式檔',page:'分頁讀取',pdf:'PDF／影像',office:'Office／郵件／CSV',bash:'命令輸出'};
  const PRESETS={small:[['bash',300],['text',200],['bash',150]],mixed:[['text',23700],['pdf',5600],['office',900],['bash',1100],['text',400]],batch:[['page',2900],['page',2900],['page',2900],['page',2900],['page',2900]]};
  let rows=PRESETS.mixed.map(row=>[...row]);
  function renderRouter() {
    if($('#wInput').getAttribute('aria-invalid')==='true' || $('#outputInput').getAttribute('aria-invalid')==='true') return;
    const lim=budget(W), digestOf=t=>Math.min(lim.digest,Math.round(150+t*.03));
    const out=rows.map(([type,requested])=>({type,requested,t:type==='page'?Math.min(requested,lim.result):requested,rule:'',by:'',ctx:type==='page'?Math.min(requested,lim.result):requested}));
    const store=(row,rule)=>Object.assign(row,{rule,by:['pdf','office'].includes(row.type)?'文件子代理':'規則摘要',ctx:digestOf(row.t)});
    out.forEach(row=>{if(row.type==='pdf'||(['text','office'].includes(row.type)&&row.t>lim.result))store(row,'file');});
    out.forEach(row=>{if(!row.rule&&row.t>lim.result)store(row,'result');});
    const sum=()=>out.reduce((total,row)=>total+row.ctx,0);
    while(sum()>lim.turn){const movable=out.filter(row=>!row.rule&&row.ctx>lim.digest);if(!movable.length)break;store(movable.reduce((a,b)=>a.ctx>=b.ctx?a:b),'turn');}
    $('#rBody').innerHTML=out.map((row,index)=>`<tr><td>${LABEL[row.type]}${row.type==='page'&&row.requested>row.t?'<br><small>分頁量已依門檻縮小</small>':''}</td><td>${fmt(row.t)}</td><td>${row.rule?`<span class="tag ${row.rule==='turn'?'violet':'red'}">${row.rule}</span>`:'原文'}</td><td>${row.by||'不產生摘要'}</td><td>${fmt(row.ctx)}</td><td><button type="button" class="btn" data-rm="${index}" aria-label="移除第 ${index+1} 筆結果">移除</button></td></tr>`).join('')||'<tr><td colspan="6">尚無結果。可新增一筆，或選擇上方教學情境。</td></tr>';
    $('#rBody').querySelectorAll('[data-rm]').forEach(button=>{button.onclick=()=>{rows.splice(Number(button.dataset.rm),1);renderRouter();};});
    const total=sum(), raw=out.reduce((value,row)=>value+row.t,0), stored=out.filter(row=>row.rule).length;
    showVerdict('#rVerdict',total>lim.turn?'warn':'ok',`單筆門檻 ${fmt(lim.result)}；本輪預算 ${fmt(lim.turn)}；示意摘要上限 ${fmt(lim.digest)}。${fmt(raw)} tokens → 約 ${fmt(total)} 進入上下文，${stored} 筆外存。${total>lim.turn?'仍超過預算：沒有可再縮減的候選，下一次請求仍可能需要壓縮或超限處理。':'這是路由示意，不是主上下文總量。'}`);
  }
  document.querySelectorAll('[data-preset]').forEach(button=>{button.onclick=()=>{rows=PRESETS[button.dataset.preset].map(row=>[...row]);renderRouter();};});
  $('#rClear').onclick=()=>{rows=[];renderRouter();};
  $('#rAdd').onclick=()=>{const value=integer('#rTok',1);if(value===null){showVerdict('#rVerdict','bad','新增結果須為 1～2,000,000 的整數 token 估算。');return;}rows.push([$('#rType').value,value]);renderRouter();};

  function renderDocument() {
    if($('#wInput').getAttribute('aria-invalid')==='true'||$('#outputInput').getAttribute('aria-invalid')==='true')return;
    const user=integer('#docUser',1), field=$('#docDensity'), density=Number(field.value);
    const valid=field.value.trim()!==''&&Number.isFinite(density)&&density>=1&&density<=3;
    field.setAttribute('aria-invalid',String(!valid));
    if(user===null||!valid){$('#docKV').replaceChildren();showVerdict('#docVerdict','bad','請輸入有效 user 整數及 1～3 的 density。');return;}
    const b=budget(W), output=Math.min(O,Math.floor(W/2)), reserve=Math.max(Math.max(output,1024)+b.margin,b.reserve), input=W-reserve;
    const prompt=Math.ceil((100+user)*density), expansion=Math.ceil(user*density*1.25), transcribe=$('#docMode').value==='transcribe';
    renderKV('#docKV',[['規劃用輸入預算',input],['規劃用輸出保留量',output],['示意完整提示估算',prompt],['示意轉錄輸出需求',expansion]]);
    const problems=[];if(prompt>input)problems.push(`提示 ${fmt(prompt)} 超過輸入預算 ${fmt(input)}`);if(user>12000)problems.push('user 超過 12,000 的分塊策略上限');if(transcribe&&expansion>output)problems.push(`轉錄需求 ${fmt(expansion)} 超過輸出保留量 ${fmt(output)}`);
    showVerdict('#docVerdict',problems.length?'warn':'ok',problems.length?`此候選塊不適合直接送出：${problems.join('；')}。文字需再分塊；若單張影像或合併材料仍放不下，程式會明確報錯。`:'此候選塊符合示意的 token 條件；實際還需估算完整提示、檢查影像張數，並確認模型回覆正常完成。');
  }
  $('#docUser').oninput=renderDocument; $('#docDensity').oninput=renderDocument; $('#docMode').onchange=renderDocument;
  const WF=[
    ['extract','擷取證據','read, bash','讀取來源、列出事實與位置。模型不應將推論偽裝成原文。','工具結果經上下文路由後，仍由同一個主 Agent 繼續。'],
    ['check','核對數值','read, bash','回讀重要原句與數字；用命令計算而不是心算。','需要新證據時才追加讀取，不重送整份歷史。'],
    ['review','人類審閱','ask','等待真實使用者確認或提出修正；沒有回答就停止等待恢復。','審閱內容進入工作流程狀態與對話，不由模型冒充批准。'],
    ['brief','保存摘要','tools: []','只使用已取得的材料撰稿，保留矛盾與不確定性。','Runner 以 output 保存 reports/brief.md；不是模型自行獲得寫檔工具。']
  ];
  function showWorkflow(index){[...$('#timeline').children].forEach((button,i)=>button.setAttribute('aria-pressed',String(index===i)));const [id,title,tools,action,result]=WF[index];$('#wfPanel').innerHTML=`<h3>${index+1}．${title}</h3><div class="fn">${escape(id)} · ${escape(tools)}</div><ul><li>${escape(action)}</li><li>${escape(result)}</li></ul>`;}
  WF.forEach(([id,title,tools],index)=>{const button=document.createElement('button');button.type='button';button.className='btn';button.innerHTML=`${index+1}．${title}<small>${escape(id)} · ${escape(tools)}</small>`;button.onclick=()=>showWorkflow(index);$('#timeline').appendChild(button);});
  showWorkflow(0);renderBudget();
})();
