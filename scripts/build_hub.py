#!/usr/bin/env python3
"""Build the public hub without rewriting any original content routes.

Source of truth: hub-src/catalog.json. Derived JSON, HTML and public SQLite
contain only the explicitly public catalogue. No credentials or visitor memory.
"""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://kentchun33333.github.io'
NOW = datetime.now(timezone.utc).isoformat(timespec='seconds')
E = lambda value: escape(str(value), quote=True)
DATA = json.loads((ROOT / 'hub-src/catalog.json').read_text())
ASSETS = DATA['assets']
BY_ID = {a['id']: a for a in ASSETS}
RELATIONS = DATA['relations']
OFFERS = DATA['offers']


class ArticleMedia(HTMLParser):
    """Read only article-body images; exclude badges, tracking and site chrome."""
    def __init__(self):
        super().__init__(); self.depth = 0; self.images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth: self.depth += 1
            elif 'post-content' in attrs.get('class', '').split(): self.depth = 1
        if self.depth and tag == 'img' and attrs.get('src'):
            self.images.append((attrs['src'], attrs.get('alt', '')))

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth: self.depth -= 1


def source_images(a):
    if a['kind'] != 'Article' or not a['path'].endswith('.html'): return []
    parser = ArticleMedia(); parser.feed((ROOT / a['path']).read_text(errors='replace'))
    media, seen = [], set()
    descriptions = {
        '/img/about/image-20210802080500753.png': 'Campus architecture pictured in Kent’s original MIT-CSAIL introduction.',
        '/img/BuyingHouse2021/image-20210802073610105.png': 'Residential towers and landscaped grounds pictured in the home-buying story.',
        '/img/BuyingHouse2021/image-20210802083702087.png': 'Price and location comparison chart from the original home-buying story.'
    }
    for src, alt in parser.images:
        url = urlsplit(urljoin(href(a['path']), src))
        if url.scheme or url.netloc: continue  # External originals stay in the source article.
        p = (ROOT / unquote(url.path).lstrip('/')).resolve()
        if not p.is_relative_to(ROOT) or not p.is_file(): continue
        rel = str(p.relative_to(ROOT)); image_url = href(rel)
        if image_url in seen: continue
        seen.add(image_url)
        if not alt.strip() or re.match(r'^(image[-_]|img[-_]|[0-9])', alt, re.I):
            alt = 'Image from “' + a['title'] + '”'
        media.append({'url':image_url, 'alt':descriptions.get(image_url,alt), 'source_path':a['path'], 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return media


def href(path):
    return '/' + quote(path, safe='/')


def detail(a):
    return '/hub/assets/' + a['id'] + '/'


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def validate():
    assert len(BY_ID) == len(ASSETS), 'Duplicate asset IDs'
    assert len({a['path'] for a in ASSETS}) == len(ASSETS), 'Duplicate canonical paths'
    for a in ASSETS:
        assert a['title'].strip() and a['summary'].strip(), 'Assets need a readable title and summary'
        assert re.fullmatch(r'[a-z0-9_-]+', a['id']), a['id']
        path = (ROOT / a['path']).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), a['path']
        assert not any(part.startswith('.') for part in Path(a['path']).parts)
        assert a['visibility'] == 'public', 'Private records cannot enter public exports'
        a['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        a['url'] = href(a['path'])
        a['detail_url'] = detail(a)
        a['images'] = source_images(a)
    for r in RELATIONS:
        assert r['source'] in BY_ID and r['target'] in BY_ID and r['basis']
        assert r['source'] != r['target']
        assert r['type'] in {'documented_by', 'evaluated_with', 'uses_schema', 'related_topic'}
    assert len({o['id'] for o in OFFERS}) == len(OFFERS)
    for o in OFFERS:
        assert o['state'] in {'inquiry', 'available', 'retired'}
        assert all(i in BY_ID for i in o['asset_ids'])
        if o['state'] == 'available':
            assert o.get('price') and o.get('currency') and o.get('license_url') and o.get('delivery_terms')
            assert urlsplit(o.get('checkout_url', '')).scheme == 'https', 'Available offers require reviewed HTTPS checkout'


def asset_actions(a):
    available = [o for o in OFFERS if a['id'] in o['asset_ids'] and o['state']=='available']
    if available:
        offer=available[0]
        return f'<div class="asset-actions"><a class="button" href="{E(offer["checkout_url"])}">Buy · {E(offer["price"])} {E(offer["currency"])}</a></div>'
    return ''


def card(a, compact=False):
    search = E(' '.join([a['title'], a['summary'], *a['topics']]).lower())
    thumbnail = ''
    if a.get('images'):
        media = a['images'][0]
        thumbnail = f'<a class="card-photo" href="{detail(a)}" aria-label="Read {E(a["title"])}"><img src="{E(media["url"])}" alt="{E(media["alt"])}" loading="lazy" decoding="async"></a>'
    return f'''<article class="asset-card {'compact' if compact else ''}" data-asset data-kind="{E(a['kind'])}" data-stream="{E(a['stream'])}" data-search="{search}">{thumbnail}
      <div class="eyebrow"><span>{E(a['kind'])}</span><span>{E(a['stream'])}</span></div>
      <h3><a href="{detail(a)}">{E(a['title'])}</a></h3><p>{E(a['summary'])}</p>
      <div class="card-bottom"><span class="status">{E(a['status'])}</span><a class="arrow" href="{detail(a)}" aria-label="Explore {E(a['title'])}">↗</a></div>{asset_actions(a)}</article>'''



def conversation_form():
    return '''<form id="brief-form" class="brief-form"><label>Your purpose<select id="brief-purpose"><option>Project inquiry</option><option>Research collaboration</option><option>Technical opportunity</option><option>Asset licensing</option></select></label><label>Related asset<select id="brief-asset"><option value="">General conversation</option>'''+''.join(f'<option value="{a["id"]}">{E(a["title"])}</option>' for a in ASSETS)+'''</select></label><label>Related engagement<select id="brief-offer"><option value="">General conversation</option>'''+''.join(f'<option value="{o["id"]}">{E(o["title"])}</option>' for o in OFFERS)+'''</select></label><label>What would you like to work on?<textarea id="brief-context" rows="6" required placeholder="The problem, your context, desired outcome, and timeline…"></textarea></label><div class="actions"><button class="button" type="submit">Copy inquiry brief</button><button class="text-button" id="download-brief" type="button">Download as text ↓</button></div><p id="brief-status" role="status"></p><p><a href="https://github.com/KentChun33333" target="_blank" rel="noopener">Open Kent’s GitHub profile ↗</a></p></form><noscript><p>The brief builder requires JavaScript. You can still use the GitHub profile link to find contact information.</p></noscript>'''


def page(title, description, body, route='/', active=None, asset=None):
    # Keep the fixed push panel outside the reflowing workspace container.
    sidebar_match = re.search(r'<aside id="filters-panel".*?</aside>', body, re.S)
    filter_sidebar = sidebar_match.group(0) if sidebar_match else ''
    if filter_sidebar: body = body.replace(filter_sidebar, '', 1)
    library_heading = '<a class="header-library-link" href="/">Asset library</a>'
    if filter_sidebar: library_heading = '<h1 class="header-library-title">'+library_heading+'</h1>' 
    about_drawer = '''<dialog id="about-panel" class="conversation-panel" aria-labelledby="about-title"><div class="conversation-heading"><h2 id="about-title" tabindex="-1">About Kent & experience</h2><button type="button" id="about-close" aria-label="Close about panel">×</button></div><div class="about-panel-content"><div><p>I work across AI systems, research, and engineering. Autumn Memo began during my research exchange in Randall Davis’s MIT-CSAIL lab in 2016.</p><p>Explore agent workflow design, evaluation research, and product engineering through the artifacts below, alongside personal stories and illustrated notes.</p><div class="about-links"><a href="/hub/assets/ter/">Agent workflows ↗</a><a href="/hub/assets/gse/">Evaluation research ↗</a><a href="/hub/assets/publisher/">Product engineering ↗</a><a href="/about/">Original background & photos ↗</a></div></div></div></dialog>'''
    current_asset = asset['id'] if asset else ''
    contact_url = '/hub/contact/' + ('?asset='+current_asset if current_asset else '')
    trigger = f'<a class="conversation-trigger" id="conversation-trigger" href="{contact_url}" data-current-asset="{current_asset}" aria-haspopup="dialog" aria-controls="conversation-panel">Start a conversation <span aria-hidden="true">↗</span></a>'
    drawer = '<dialog id="conversation-panel" class="conversation-panel" aria-labelledby="conversation-title"><div class="conversation-heading"><h2 id="conversation-title" tabindex="-1">Start a conversation</h2><button type="button" id="conversation-close" aria-label="Close conversation panel">×</button></div><p class="conversation-description">Tell me what you have in mind. Prepare a brief to copy or download; nothing is sent or stored by this site.</p>'+conversation_form()+'</dialog>'
    if route == '/hub/contact/':
        drawer = ''
        trigger = '<a class="conversation-trigger" href="#brief-form">Start a conversation ↗</a>'
    image = '' if asset else f'<meta property="og:image" content="{ORIGIN}/img/autumn-memo-hub-social.png"><meta name="twitter:image" content="{ORIGIN}/img/autumn-memo-hub-social.png">'
    if asset and asset.get('images'):
        media = asset['images'][0]
        image = f'<meta property="og:image" content="{ORIGIN}{E(media["url"])}"><meta property="og:image:alt" content="{E(media["alt"])}"><meta name="twitter:image" content="{ORIGIN}{E(media["url"])}">'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{E(title)} · Autumn Memo</title><meta name="description" content="{E(description)}"><link rel="canonical" href="{ORIGIN}{route}">
      <meta property="og:title" content="{E(title)} · Autumn Memo"><meta property="og:description" content="{E(description)}"><meta property="og:type" content="{'article' if asset else 'website'}"><meta property="og:url" content="{ORIGIN}{route}">{image}
      <meta name="twitter:card" content="{'summary' if asset else 'summary_large_image'}"><meta name="twitter:title" content="{E(title)} · Autumn Memo"><meta name="twitter:description" content="{E(description)}">
      <meta name="theme-color" content="#f5f4ec"><link rel="stylesheet" href="/css/command-center.css"><script src="/js/command-center.js" defer></script><script src="/js/asset-viewer.js" defer></script><link rel="alternate" type="application/rss+xml" title="Autumn Memo" href="/index.xml"></head>
      <body data-filter-layout="{'rail' if filter_sidebar else 'none'}"><a class="skip" href="#main">Skip to content</a><div class="app-shell"><div class="workspace"><header class="topbar library-topbar">{library_heading}<div class="topbar-links"><a id="about-trigger" class="about-trigger" href="/about/" aria-haspopup="dialog" aria-controls="about-panel">About & experience</a>{trigger}</div></header>
      <main id="main" class="{'collection-main' if route == '/' else ''}">{body}</main><footer><span>Autumn Memo · Kent Chiu</span><div><a href="/archives/">Archives</a><a href="/index.xml">RSS</a><a href="https://github.com/KentChun33333">GitHub</a><a href="/index.legacy-hugo.html">Original homepage</a></div></footer></div></div>{filter_sidebar}{drawer}{about_drawer}<div id="announcement" class="sr-only" role="status" aria-live="polite"></div></body></html>'''



def head(kicker, title, text):
    return f'<div class="page-heading"><p class="eyebrow">{E(kicker)}</p><h1>{E(title)}</h1><p class="lede">{E(text)}</p></div>'


def section(title, items, link=None):
    return f'<section class="section"><div class="section-heading"><h2>{E(title)}</h2>{link or ""}</div><div class="card-grid">{items}</div></section>'


def inline(text, source):
    text = E(text)
    def link(m):
        label, target = m.group(1), m.group(2)
        target = target.replace('&amp;', '&')
        if urlsplit(target).scheme not in ('', 'https', 'http', 'mailto') or target.startswith('//'):
            return label
        resolved = urljoin(href(source), target)
        return f'<a href="{E(resolved)}">{label}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', link, text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def markdown(text, source):
    """Safe, intentionally small reader. Raw HTML is escaped, never executed."""
    out, para, code, list_items = [], [], None, []
    def flush():
        if para:
            out.append('<p>' + inline(' '.join(para), source) + '</p>'); para.clear()
        if list_items:
            out.append('<ul>' + ''.join('<li>' + inline(x, source) + '</li>' for x in list_items) + '</ul>'); list_items.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None: code = []
            else: out.append('<pre><code>' + E('\n'.join(code)) + '</code></pre>'); code = None
        elif code is not None: code.append(line)
        elif re.match(r'^#{1,6} ', line):
            flush(); level = min(len(line) - len(line.lstrip('#')) + 1, 6)
            out.append(f'<h{level}>' + inline(line.lstrip('# '), source) + f'</h{level}>')
        elif re.match(r'^\s*(?:[-*]|\d+\.) ', line):
            if para: flush()
            list_items.append(re.sub(r'^\s*(?:[-*]|\d+\.) ', '', line))
        elif not line.strip(): flush()
        else:
            if list_items: flush()
            para.append(line)
    flush()
    if code is not None: out.append('<pre><code>' + E('\n'.join(code)) + '</code></pre>')
    return ''.join(out)


def build_memory():
    # Inventory existing HTML/Markdown assets without adding them to discovery.
    # Content discovery is explicitly curated; preserved files remain in place.
    previous_path = ROOT / 'data/hub/catalog.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {'assets': []}
    # Only prune previously generated detail pages, never original source files.
    for old in previous['assets']:
        if old['id'] not in BY_ID and re.fullmatch(r'[a-z0-9_-]+', old['id']):
            obsolete = ROOT / 'hub/assets' / old['id'] / 'index.html'
            if obsolete.exists(): obsolete.unlink()
            reader = ROOT / 'data/hub/readers' / (old['id'] + '.html')
            if reader.exists(): reader.unlink()
    inventory = []
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(p.startswith('.') for p in rel.parts) or rel.parts[0] in {'hub', 'hub-src', 'scripts', 'data', 'docs'}: continue
        if not path.is_file() or path.suffix.lower() not in {'.html', '.md'} or len(rel.parts) == 1: continue
        raw = path.read_bytes()
        inventory.append({'path': str(rel), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    conn = sqlite3.connect(ROOT / 'data/hub/memory.sqlite')
    conn.executescript((ROOT / 'hub-src/schema.sql').read_text())
    with conn:
        conn.execute('DELETE FROM offer_assets'); conn.execute('DELETE FROM offers'); conn.execute('DELETE FROM relations'); conn.execute('DELETE FROM asset_media')
        ids = {a['id'] for a in ASSETS}
        for (old_id,) in conn.execute('SELECT id FROM assets').fetchall():
            if old_id not in ids:
                conn.execute('DELETE FROM revisions WHERE asset_id=?', (old_id,))
                conn.execute('DELETE FROM assets WHERE id=?', (old_id,))
        for a in ASSETS:
            values = (a['id'], a['title'], a['kind'], a['stream'], a['path'], a['summary'], a['status'], 'public', json.dumps(a, ensure_ascii=False))
            conn.execute('INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,kind=excluded.kind,stream=excluded.stream,path=excluded.path,summary=excluded.summary,status=excluded.status,metadata_json=excluded.metadata_json', values)
            conn.execute('INSERT OR IGNORE INTO revisions VALUES (?,?,?)', (a['id'], a['sha256'], NOW))
            conn.executemany('INSERT INTO asset_media VALUES (?,?,?,?,?,?)', [(a['id'],m['url'],m['alt'],m['source_path'],m['sha256'],i) for i,m in enumerate(a['images'])])
        conn.executemany('INSERT INTO relations VALUES (?,?,?,?)', [(r['source'],r['type'],r['target'],r['basis']) for r in RELATIONS])
        for o in OFFERS:
            conn.execute('INSERT INTO offers VALUES (?,?,?,?)', (o['id'],o['title'],o['state'],json.dumps(o)))
            conn.executemany('INSERT INTO offer_assets VALUES (?,?)', [(o['id'],x) for x in o['asset_ids']])
        conn.execute('DELETE FROM source_inventory')
        conn.executemany('INSERT INTO source_inventory VALUES (?,?,?)', [(i['path'],i['sha256'],i['bytes']) for i in inventory])
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    conn.execute('PRAGMA optimize'); conn.execute('VACUUM'); conn.close()
    write('data/hub/catalog.json', json.dumps(DATA, ensure_ascii=False, indent=2) + '\n')
    write('data/hub/source-manifest.json', json.dumps({'scope':'Existing nested HTML and Markdown outside hub tooling; preservation inventory, not publication approval.','files': inventory}, indent=2) + '\n')
    return len(inventory)


def build_pages():
    intro = ''
    controls = '''<form id="library-search" class="compact-search" role="search" action="/"><a id="filters-trigger" class="filter-trigger" href="#filters-panel" aria-expanded="false" aria-controls="filters-panel">Asset types <span aria-hidden="true">☰</span><span id="filter-count"></span></a><label class="sr-only" for="asset-search">Search the collection</label><input id="asset-search" name="q" type="search" placeholder="Search research, demos, skills, writing…" autocomplete="off"><input id="asset-kind" type="hidden" name="kind"><input id="asset-stream" type="hidden" name="stream"></form>'''
    types=''.join(f'<button type="button" data-kind-shortcut="{kind}" aria-pressed="false" aria-label="{E(label)}" title="{E(label)}"><span class="type-icon" aria-hidden="true">{dict(Research="◇", Demo="▷", Skill="✦", Article="≡", Tool="⚒", Protocol="☷").get(kind,"▦")}</span><span class="type-label">{label}</span><span class="type-total" title="Total assets in the collection">{sum(1 for a in ASSETS if not kind or a["kind"]==kind)}</span></button>' for kind,label in [('', 'All assets'),('Research','Research'),('Demo','Demos'),('Skill','Skills'),('Article','Writing & blogs'),('Tool','Tools'),('Protocol','Protocols')])
    streams=''.join(f'<button type="button" data-stream-shortcut="{value}" aria-pressed="false">{label}</button>' for value,label in [('', 'All workstreams'),('Build','Build'),('Research','Research'),('Publish','Publish')])
    filters='<aside id="filters-panel" class="filters-panel" aria-labelledby="filters-title"><div class="conversation-heading"><h2 id="filters-title" class="sidebar-brand" tabindex="-1"><a class="brand" href="/" title="Autumn Memo · Kent Chiu"><span class="brand-mark" aria-hidden="true">am<span>↗</span></span><span class="brand-name">AUTUMN MEMO<small>Kent Chiu’s work & ideas</small></span><span class="sr-only">Autumn Memo · asset filters</span></a></h2><button type="button" id="filters-close" aria-label="Expand filters" title="Expand or collapse filters">›</button></div><fieldset class="filter-group asset-type-group" id="asset-type-filters"><legend>Asset type</legend><div class="filter-options asset-type-options">'+types+'</div></fieldset><fieldset class="filter-group"><legend>Workstream</legend><div class="filter-options">'+streams+'</div></fieldset><p id="filter-results" role="status"></p><div class="filter-panel-actions"><button type="button" id="filters-apply" class="button">Show results</button><button type="button" id="filters-reset" class="text-button">Reset all</button></div><div id="filters-resizer" role="separator" tabindex="0" aria-label="Resize asset filters" aria-orientation="vertical" aria-valuemin="64" aria-valuemax="240" aria-valuenow="64" title="Drag to resize. Arrow keys change width; Home shows icons; End expands."></div></aside>'
    priority=['gse','ter','story-autumn-memo','wealth','writing-buyinghouse2021','publisher']
    ordered=[BY_ID[i] for i in priority]+[a for a in ASSETS if a['id'] not in priority]
    library=intro+controls+filters+f'<p id="result-count" role="status">{len(ASSETS)} assets</p><div id="asset-results" class="card-grid">'+''.join(card(a,True) for a in ordered)+'</div><div id="empty-results" class="empty-state" hidden><h2>No matching assets</h2><p>Try a broader search or reset your filters.</p></div><noscript><p>All assets are listed here. Interactive filtering requires JavaScript.</p></noscript>'
    viewer = '<section id="asset-view" hidden aria-labelledby="viewer-title"><div class="viewer-toolbar"><button type="button" id="viewer-back" class="text-button">← Library</button><h2 id="viewer-title" tabindex="-1"></h2><div class="viewer-actions"><button type="button" id="viewer-share" class="text-button">Share</button><a id="viewer-original" target="_blank" rel="noopener">Open original ↗</a></div></div><p id="viewer-status" role="status"></p><div id="viewer-canvas"></div></section>'
    library='<section id="library-view">'+library+'</section>'+viewer
    html=page('Kent Chiu · Asset library' ,'Research, demos, skills, personal stories and illustrated writing by Kent Chiu. Explore an asset or get in touch.',library,'/')
    write('index.html',html)
    write('hub/library/index.html',html)
    # Legacy entry URLs retain a useful destination; source asset URLs are untouched.
    for route,target,label in [('solutions','/','Asset library'),('collaborate','/?kind=Research','Research assets'),('experience','/#about','About Kent & experience'),('stories','/?kind=Article','Writing & blogs')]:
        body=head('ASSET LIBRARY','Everything lives in the collection.','Explore the original work and contact me from any asset.')+f'<a class="button" href="{target}">{label} ↗</a>'
        redirect=page(label,'Explore Kent Chiu’s asset library.',body,'/').replace('<head>',f'<head><meta http-equiv="refresh" content="0;url={target}">',1)
        write('hub/'+route+'/index.html',redirect)
    connected={r[k] for r in RELATIONS for k in ['source','target']}
    graph=head('KNOWLEDGE MAP','Follow the connections, not just the files.','Select an asset to see its immediate connections. Every link includes a stated basis; topic links are editorial, not claims that one system implements another.')+f'''<label class="graph-picker">Explore an asset<select id="graph-focus">{''.join(f'<option value="{a["id"]}">{E(a["title"])}</option>' for a in ASSETS if a['id'] in connected)}</select></label><div class="graph-workspace"><div id="graph-canvas" aria-label="Selected asset and its connected records"></div><aside id="graph-context"></aside></div><section class="section"><h2>All recorded relationships</h2><div class="relationship-list">'''+''.join(f'<article><a href="{detail(BY_ID[r["source"]])}">{E(BY_ID[r["source"]]["title"])}</a><span>{E(r["type"].replace("_"," "))}</span><a href="{detail(BY_ID[r["target"]])}">{E(BY_ID[r["target"]]["title"])}</a><p>{E(r["basis"])}</p></article>' for r in RELATIONS)+'</div></section>'
    write('hub/graph/index.html',page('Knowledge map','Explore evidence-backed and editorial relationships between public assets.',graph,'/hub/graph/'))
    design=head('DESIGN TREE','One durable asset layer. Multiple experiences.','Original files keep their existing homes. A curated catalogue adds meaning and relationships; the web layer offers different ways to use the same work.')+'''<div class="design-tree"><section><span>01 / ORIGINAL SOURCES</span><h2>Preserved content</h2><p>Blogs · Markdown · Research sites · Agentic demos · Skills · Supporting files</p><small>Existing paths remain the source destinations.</small></section><div class="tree-arrow" aria-hidden="true">↓</div><section><span>02 / PUBLIC ASSET MEMORY</span><h2>Catalogue + knowledge graph</h2><p>Stable asset IDs · Source hashes · Types · Topics · Audiences · Maturity · Relationships · Rights · Offers</p><small>Git-backed records → JSON for the web + SQLite for structured queries.</small></section><div class="tree-arrow" aria-hidden="true">↓</div><section><span>03 / WEB EXPERIENCES</span><h2>Choose a purpose</h2><div class="tree-branches"><a href="/">Asset library · research, demos, skills & writing</a><a href="/#about">About Kent & experience</a><a href="/hub/graph/">Follow relationships</a></div></section></div><section class="reading-path"><h2>Memory has different boundaries</h2><p><strong>Public knowledge memory:</strong> the durable catalogue, source fingerprints, and curated connections implemented here.</p><p><strong>Personal visitor memory:</strong> saved collections and cross-device reading progress would require authenticated storage. They are not silently stored in this public catalogue.</p><p><strong>Private operating memory:</strong> client notes, tasks, proposals, and payment entitlements belong in a separate authenticated backend. They must never be committed to this public repository.</p><p><strong>Commercial assets:</strong> selected engagements accept inquiries. Direct sales require approved price, license, delivery terms, and checkout; paid files require protected storage.</p><a href="/docs/hub/architecture.md">Read the architecture document ↗</a> · <a href="/data/hub/catalog.json">Public catalogue JSON ↗</a> · <a href="/data/hub/memory.sqlite" download>Public SQLite catalogue ↓</a></section>'''
    write('hub/design/index.html',page('Design tree','The asset, memory, graph, and web architecture of Autumn Memo.',design,'/hub/design/'))
    contact=head('START A CONVERSATION','Bring a problem, question, or opportunity.','Prepare a brief you can copy or download, then use the contact details available on my GitHub profile. This page does not send or store your message.')+conversation_form()
    write('hub/contact/index.html',page('Start a conversation','Prepare a project, research, technical opportunity, or licensing inquiry.',contact,'/hub/contact/'))
    for a in ASSETS:
        rels=[r for r in RELATIONS if a['id'] in (r['source'],r['target'])]
        related=''
        for r in rels:
            other=BY_ID[r['target'] if r['source']==a['id'] else r['source']]
            related+=f'<li><a href="{detail(other)}">{E(other["title"])}</a><small>{E(r["type"].replace("_"," "))} · {E(r["basis"])}</small></li>'
        body=f'<a class="back-link" href="/hub/library/">← Asset library</a>'+head(a['kind']+' / '+a['stream'],a['title'],a['summary'])+f'''<div class="asset-toolbar"><span class="status">{E(a['status'])}</span><a class="button" href="{a['url']}">{'Open source' if a['path'].endswith('.md') else 'Open original '+a['kind'].lower()} ↗</a><button class="text-button" data-share>Copy share link</button>{asset_actions(a)}</div>'''
        if a['path'].endswith('.md'):
            reader_html='<article class="reader">'+markdown((ROOT/a['path']).read_text(),a['path'])+'</article>'
            write('data/hub/readers/'+a['id']+'.html', reader_html)
            body+=reader_html
        else:
            if a.get('images'):
                body+='<section class="article-gallery" aria-label="Pictures from the original article">'+''.join(f'<figure><a href="{a["url"]}"><img src="{E(m["url"])}" alt="{E(m["alt"])}" loading="lazy" decoding="async"></a><figcaption>Original article image · <a href="{a["url"]}">Read with its full context ↗</a> · <a href="{E(m["url"])}">View full-size image ↗</a></figcaption></figure>' for m in a['images'])+'</section>'
            body+=f'''<section class="reading-path"><h2>{'Explore the interactive artifact' if a['kind'] in ['Demo','Research','Tool'] else 'Read the original article'}</h2><p>The original page retains its layout and interactions. Open it directly for the full experience.</p><a href="{a['url']}">Continue to the original asset ↗</a></section>'''
        if related: body+='<section class="section"><h2>Connected knowledge</h2><ul class="related-list">'+related+'</ul></section>'
        body+=f'<details class="source-details"><summary>Source & reuse information</summary><p>{E(a["rights"])}</p><p>Source: <a href="{a["url"]}">{E(a["path"])}</a></p><p>Asset ID: <code>{a["id"]}</code></p><p>Content fingerprint: <code class="fingerprint">{a["sha256"]}</code></p><p>The fingerprint records source identity, not the date of publication or independent verification of its claims.</p></details>'
        write('hub/assets/'+a['id']+'/index.html',page(a['title'],a['summary'],body,detail(a),active='/',asset=a))


if __name__ == '__main__':
    validate()
    count=build_memory()
    build_pages()
    print(f'Built {len(ASSETS)} asset pages, {len(RELATIONS)} relations, {len(OFFERS)} offers; inventoried {count} source files.')
