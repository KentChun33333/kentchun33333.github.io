// Non-browser interaction checks against the shipped script.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'data/hub/catalog.json')));
const source = fs.readFileSync(path.join(root, 'js/command-center.js'), 'utf8');
class Element {
  constructor(value = '') { this.value = value; this.children = []; this.events = {}; this.options = []; this.hidden = false; this.style = {setProperty(name,value) {this[name]=value;}}; }
  addEventListener(name, fn) { this.events[name] = fn; }
  append(...children) { this.children.push(...children); }
  replaceChildren() { this.children = []; }
  focus() { this.focused = true; }
  get selectedOptions() { return this.options.filter(o => o.value === this.value); }
  setAttribute(name, value) { this[name] = value; }
}
function run(url, elements, cards = [], options = {}) {
  elements.announcement = new Element();
  const location = new URL(url);
  const document = { body: new Element(), getElementById: id => elements[id] || null, querySelectorAll: selector => selector === '[data-asset]' ? cards : (options.controls?.[selector] || []), addEventListener() {}, createElement: () => new Element() };
  const context = { document, location, URL, URLSearchParams, history: { replaceState: (_, __, value) => { location.href = value.href; } }, navigator: options.navigator || {}, window: {innerWidth: 1280, addEventListener() {}, ...(options.window || {})}, setTimeout, fetch: async () => ({ ok: true, json: async () => data }) };
  vm.runInNewContext(source, context);
  return location;
}
async function main() {
  const search = new Element(); search.form = new Element();
  const kind = new Element(); kind.options = ['', ...new Set(data.assets.map(a => a.kind))].map(value => ({ value }));
  const stream = new Element(); stream.options = ['', 'Build', 'Research', 'Publish'].map(value => ({ value }));
  const cards = data.assets.map(a => { const el = new Element(); el.dataset = { kind: a.kind, stream: a.stream, search: [a.title, a.summary, ...a.topics].join(' ').toLowerCase() }; return el; });
  const els = { 'asset-search': search, 'asset-kind': kind, 'asset-stream': stream, 'result-count': new Element(), 'empty-results': new Element() };
  const location = run('https://example.org/hub/library/?kind=Skill&stream=Build', els, cards);
  assert.equal(cards.filter(c => !c.hidden).length, data.assets.filter(a => a.kind === 'Skill' && a.stream === 'Build').length);
  search.value = 'no-such-unfindable-asset'; search.events.input();
  assert.equal(cards.filter(c => !c.hidden).length, 0); assert.equal(els['empty-results'].hidden, false);
  assert.equal(location.searchParams.get('q'), search.value);
  search.value = 'guarded evolution'; kind.value = ''; stream.value = ''; search.events.input();
  assert(cards.filter(c => !c.hidden).length >= 4);
  search.value = ''; search.events.input();
  assert.equal(cards.filter(c => !c.hidden).length, data.assets.length);
  search.value = 'MIT CSAIL'; search.events.input();
  assert(cards.some((c,i) => !c.hidden && data.assets[i].id === 'story-autumn-memo'));
  search.value = 'buying home'; search.events.input();
  assert(cards.some((c,i) => !c.hidden && data.assets[i].id === 'writing-buyinghouse2021'));
  const protocol = new Element(); protocol.dataset = {kindShortcut: 'Protocol'};
  const researchStream = new Element(); researchStream.dataset = {streamShortcut: 'Research'};
  els['filter-count'] = new Element(); els['filter-results'] = new Element(); els['filters-reset'] = new Element();
  run('https://example.org/?kind=Protocol', els, cards, {controls: {'[data-kind-shortcut]':[protocol], '[data-stream-shortcut]':[researchStream]}});
  assert.equal(protocol['aria-pressed'], 'true');
  researchStream.events.click();
  assert.equal(els['filter-count'].textContent, 2);
  assert(cards.filter(c=>!c.hidden).every(c=>c.dataset.kind==='Protocol' && c.dataset.stream==='Research'));
  els['filters-reset'].events.click();
  assert.equal(cards.filter(c=>!c.hidden).length,data.assets.length);
  assert.equal(protocol['aria-pressed'], 'false');
  const focus = new Element('gse'); const ids = new Set(data.relations.flatMap(r => [r.source, r.target]));
  focus.options = [...ids].map(value => ({ value }));
  const graph = { 'graph-focus': focus, 'graph-canvas': new Element(), 'graph-context': new Element() };
  const graphLocation = run('https://example.org/hub/graph/?asset=ter', graph);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(focus.value, 'ter');
  assert.equal(graph['graph-canvas'].children[1].children.length, 2);
  focus.value = 'gse'; focus.events.change();
  assert.equal(graph['graph-canvas'].children[1].children.length, 5);
  assert.equal(graphLocation.searchParams.get('asset'), 'gse');
  const select = pairs => { const el = new Element(pairs[0][0]); el.options = pairs.map(([value,textContent]) => ({value,textContent})); return el; };
  const form = new Element(); form.reportValidity = () => true;
  const briefElements = { 'brief-form': form, 'brief-purpose': select([['Project inquiry','Project inquiry']]), 'brief-offer': select([['','General conversation']]), 'brief-asset': select([['','General conversation'],['gse','Guarded Skill Evolution']]), 'brief-context': new Element('Let us discuss evaluation.'), 'brief-status': new Element(), 'download-brief': new Element() };
  let copied = '';
  run('https://example.org/hub/contact/?asset=gse', briefElements, [], { window: { isSecureContext: true }, navigator: { clipboard: { writeText: async text => { copied = text; } } } });
  assert.equal(briefElements['brief-asset'].value, 'gse');
  await form.events.submit({ preventDefault() {} });
  assert(copied.includes('Asset: Guarded Skill Evolution'));
  assert(copied.includes('https://example.org/hub/assets/gse/'));
  assert(copied.includes('Let us discuss evaluation.'));
  const panel = new Element(); panel.open = false;
  panel.showModal = () => { panel.open = true; };
  panel.close = () => { panel.open = false; panel.events.close(); };
  const trigger = new Element(); trigger.dataset = { currentAsset: 'gse' };
  briefElements['conversation-panel'] = panel; briefElements['conversation-trigger'] = trigger;
  briefElements['conversation-close'] = new Element(); briefElements['conversation-title'] = new Element();
  briefElements['brief-asset'].value = '';
  run('https://example.org/hub/assets/gse/', briefElements);
  assert.equal(briefElements['brief-asset'].value, 'gse');
  let prevented = false;
  trigger.events.click({ preventDefault() { prevented = true; } });
  assert(prevented && panel.open && briefElements['conversation-title'].focused);
  briefElements['conversation-close'].events.click();
  assert(!panel.open && trigger.focused);
  trigger.events.click({ preventDefault() {} });
  assert.equal(briefElements['brief-context'].value, 'Let us discuss evaluation.');
  panel.close();
  for (const name of ['about','filters']) {
    const drawer = new Element(), opener = new Element(), title = new Element();
    drawer.showModal = () => {drawer.open=true;}; drawer.close = () => {drawer.open=false;drawer.events.close();};
    const bits = {[name+'-panel']:drawer,[name+'-trigger']:opener,[name+'-title']:title,[name+'-close']:new Element()};
    if(name==='filters') {bits['filters-apply']=new Element();bits['filters-resizer']=new Element();bits['filters-resizer'].setPointerCapture=()=>{};}
    run('https://example.org/'+(name==='about'?'#about':''),bits);
    if(name==='about') assert(drawer.open && title.focused);
    else {
      const handle=bits['filters-resizer'];
      assert.equal(handle['aria-valuenow'],'64');
      opener.events.click({preventDefault(){}});assert.equal(handle['aria-valuenow'],'240');
      handle.events.keydown({key:'End',preventDefault(){}});assert.equal(handle['aria-valuenow'],'240');
      handle.events.keydown({key:'Home',preventDefault(){}});assert.equal(handle['aria-valuenow'],'64');
      handle.events.pointerdown({button:0,clientX:64,pointerId:1,preventDefault(){}});
      handle.events.pointermove({clientX:270});handle.events.pointerup();assert.equal(handle['aria-valuenow'],'240');
      bits['filters-apply'].events.click();assert.equal(handle['aria-valuenow'],'64');
      opener.events.click({preventDefault(){}});drawer.events.keydown({key:'Escape',preventDefault(){}});assert.equal(opener['aria-expanded'],'false');
    }
  }
  console.log('Passed type/workstream buttons, filter reset, URL restoration, resizable snap rail, keyboard/drag controls, and both right drawers, contact context, focus restoration, and draft retention.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
