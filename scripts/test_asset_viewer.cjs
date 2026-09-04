const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const catalogue = JSON.parse(fs.readFileSync(path.join(root, 'data/hub/catalog.json')));
const script = fs.readFileSync(path.join(root, 'js/asset-viewer.js'), 'utf8');
class El {
  constructor() { this.hidden=false; this.children=[]; this.events={}; this.dataset={}; this.isConnected=true; this.classList={contains:()=>false}; }
  addEventListener(name, fn) { this.events[name]=fn; }
  setAttribute(name,value) {this[name]=value;}
  removeAttribute(name) {delete this[name];}
  replaceChildren() {this.children=[];this.innerHTML='';}
  append(el) {this.children.push(el);}
  focus() {this.focused=true;}
}
function setup(url) {
  const els=Object.fromEntries(['library-view','asset-view','viewer-canvas','viewer-title','viewer-status','viewer-toolbar','viewer-back','viewer-share','brief-asset','conversation-trigger'].map(k=>[k,new El()]));
  els['asset-view'].hidden=true;
  const events={}, winEvents={}, location=new URL(url);
  const history={state:null,entries:[],pushState(state,_,url){this.state=state;location.href=url;this.entries.push(location.href);},replaceState(state,_,url){this.state=state;location.href=url;}};
  const document={title:'Asset library',body:new El(),activeElement:new El(),getElementById:id=>els[id],createElement:()=>new El(),addEventListener:(name,fn)=>events[name]=fn};
  const window={scrollY:620,scrollTo(_,y){this.scrollY=y;},addEventListener:(name,fn)=>winEvents[name]=fn};
  const fetch=async url=>url==='/data/hub/catalog.json'?{ok:true,json:async()=>catalogue}:{ok:true,text:async()=>'<article class="reader"><h2>Source reader</h2></article>'};
  vm.runInNewContext(script,{document,window,location,history,fetch,URL,URLSearchParams,navigator:{clipboard:{writeText:async()=>{}}}});
  const open=id=>{const link={href:'https://example.org/hub/assets/'+id+'/',target:'',hasAttribute:()=>false,closest:()=>null};let prevented=false;events.click({button:0,target:{closest:()=>link},preventDefault(){prevented=true;}});assert(prevented);};
  return {els,events,winEvents,location,history,window,document,open};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  const app=setup('https://example.org/?kind=Research');app.open('gse');await flush();
  assert.equal(app.location.pathname,'/');assert.equal(app.location.searchParams.get('asset'),'gse');
  assert(app.els['library-view'].hidden && !app.els['asset-view'].hidden && !app.els['viewer-toolbar'].hidden);
  assert.equal(app.els['viewer-canvas'].children[0].src,catalogue.assets.find(a=>a.id==='gse').url);
  assert.equal(app.els['brief-asset'].value,'gse');
  app.els['viewer-canvas'].children[0].events.load();assert.equal(app.els['viewer-status'].textContent,'');
  app.els['viewer-back'].events.click();assert(!app.els['library-view'].hidden && app.els['viewer-toolbar'].hidden);
  assert.equal(app.window.scrollY,620);assert.equal(app.els['viewer-canvas'].children.length,0);
  assert.equal(app.location.searchParams.get('kind'),'Research');assert(!app.location.searchParams.has('asset'));
  app.open('gse-paper');await flush();assert(app.els['viewer-canvas'].innerHTML.includes('Source reader'));
  app.location.href='https://example.org/?kind=Research';app.winEvents.popstate({state:{libraryScroll:620}});assert(!app.els['library-view'].hidden);
  app.location.href='https://example.org/?kind=Research&asset=ter';app.winEvents.popstate({state:{libraryScroll:620}});await flush();assert.equal(app.els['brief-asset'].value,'ter');
  app.events['hub:filters-changed']();assert(!app.els['library-view'].hidden);
  const deep=setup('https://example.org/?asset=gse-paper');await flush();assert(deep.els['viewer-canvas'].innerHTML.includes('Source reader'));
  const invalid=setup('https://example.org/?asset=not-real');await flush();assert.equal(invalid.els['viewer-title'].textContent,'Asset not found');
  const race=setup('https://example.org/');race.open('gse-paper');race.els['viewer-back'].events.click();await flush();assert.equal(race.els['viewer-canvas'].children.length,0);assert(!race.els['library-view'].hidden);
  console.log('Passed in-place HTML/Markdown, shared URLs, Back/Forward, scroll/filter preservation, context, invalid assets, and cancellation of stale loads.');
})().catch(e=>{console.error(e);process.exitCode=1;});
