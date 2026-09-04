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


def card(a, compact=False):
    search = E(' '.join([a['title'], a['summary'], *a['topics']]).lower())
    thumbnail = ''
    if a.get('images'):
        media = a['images'][0]
        thumbnail = f'<a class="card-photo" href="{detail(a)}" aria-label="Read {E(a["title"])}"><img src="{E(media["url"])}" alt="{E(media["alt"])}" loading="lazy" decoding="async"></a>'
    return f'''<article class="asset-card {'compact' if compact else ''}" data-asset data-kind="{E(a['kind'])}" data-stream="{E(a['stream'])}" data-search="{search}">{thumbnail}
      <div class="eyebrow"><span>{E(a['kind'])}</span><span>{E(a['stream'])}</span></div>
      <h3><a href="{detail(a)}">{E(a['title'])}</a></h3><p>{E(a['summary'])}</p>
      <div class="card-bottom"><span class="status">{E(a['status'])}</span><a class="arrow" href="{detail(a)}" aria-label="Explore {E(a['title'])}">↗</a></div></article>'''


NAV = [('Overview', '/'), ('Work with me', '/hub/solutions/'), ('Experience', '/hub/experience/'), ('Writing & photos', '/hub/stories/'), ('Asset library', '/hub/library/'), ('Knowledge map', '/hub/graph/')]


def page(title, description, body, route='/', active=None, asset=None):
    nav = ''.join('<a href="{}" {}>{}</a>'.format(url, 'aria-current="page"' if url == (active or route) else '', label) for label, url in NAV)
    image = '' if asset else f'<meta property="og:image" content="{ORIGIN}/img/autumn-memo-hub-social.png"><meta name="twitter:image" content="{ORIGIN}/img/autumn-memo-hub-social.png">'
    if asset and asset.get('images'):
        media = asset['images'][0]
        image = f'<meta property="og:image" content="{ORIGIN}{E(media["url"])}"><meta property="og:image:alt" content="{E(media["alt"])}"><meta name="twitter:image" content="{ORIGIN}{E(media["url"])}">'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{E(title)} · Autumn Memo</title><meta name="description" content="{E(description)}"><link rel="canonical" href="{ORIGIN}{route}">
      <meta property="og:title" content="{E(title)} · Autumn Memo"><meta property="og:description" content="{E(description)}"><meta property="og:type" content="{'article' if asset else 'website'}"><meta property="og:url" content="{ORIGIN}{route}">{image}
      <meta name="twitter:card" content="{'summary' if asset else 'summary_large_image'}"><meta name="twitter:title" content="{E(title)} · Autumn Memo"><meta name="twitter:description" content="{E(description)}">
      <meta name="theme-color" content="#f5f4ec"><link rel="stylesheet" href="/css/command-center.css"><script src="/js/command-center.js" defer></script><link rel="alternate" type="application/rss+xml" title="Autumn Memo" href="/index.xml"></head>
      <body><a class="skip" href="#main">Skip to content</a><div class="app-shell"><aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">am<span>↗</span></span><span>AUTUMN MEMO<small>Kent Chiu’s work & ideas</small></span></a>
      <p class="nav-label">YOUR ENTRY POINT</p><nav aria-label="Primary">{nav}</nav><div class="sidebar-bottom"><a href="/hub/design/">How this workspace connects ↗</a><a href="/post/">Original blog archive ↗</a><a href="/about/">About Kent ↗</a><span>Research. Build. Share.</span></div></aside>
      <div class="workspace"><header class="topbar"><span>PERSONAL COMMAND CENTER <span class="topbar-divider">/</span> PUBLIC WORKSPACE</span><a href="/hub/contact/">Start a conversation ↗</a></header>
      <main id="main">{body}</main><footer><span>Autumn Memo · Kent Chiu</span><div><a href="/archives/">Archives</a><a href="/index.xml">RSS</a><a href="https://github.com/KentChun33333">GitHub</a><a href="/index.legacy-hugo.html">Original homepage</a></div></footer></div></div><div id="announcement" class="sr-only" role="status" aria-live="polite"></div></body></html>'''


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
    hero = '''<div class="intro-row"><div><p class="eyebrow">ONE BODY OF WORK. MANY WAYS IN.</p><h1>Ideas into systems.<br><em>Find your way in.</em></h1><p class="lede">I’m Kent Chiu. Explore the research, working prototypes, and reusable knowledge behind my AI and engineering work.</p></div><a class="focus-note" href="/hub/assets/gse/"><span class="eyebrow">FEATURED RESEARCH QUESTION</span><strong>How should agents<br>learn to improve?</strong><span>Explore Guarded Skill Evolution ↗</span></a></div>'''
    entries = '''<section class="entry-strip entries-three" aria-label="Choose your purpose"><a href="/hub/solutions/"><span>01 / CONNECT</span><strong>Work with me ↗</strong><small>Projects, research & collaboration</small></a><a href="/hub/experience/"><span>02 / EVALUATE</span><strong>Explore my work ↗</strong><small>Systems, decisions & source material</small></a><a href="/hub/library/"><span>03 / LEARN</span><strong>Follow an idea ↗</strong><small>Writing, skills & interactive research</small></a></section>'''
    featured = section('Selected work', ''.join(card(BY_ID[i]) for i in ['gse','ter','wealth']), '<a href="/hub/library/">Explore all assets ↗</a>')
    streams = section('Follow a workstream', ''.join(f'<a class="stream-card" href="/hub/library/?stream={name}"><span class="eyebrow">{n:02d} / WORKSTREAM</span><h3>{name} <span>↗</span></h3><p>{desc}</p><small>{sum(a["stream"]==name for a in ASSETS)} curated assets</small></a>' for n,(name,desc) in enumerate([('Build','Agent workflows, tools, and reusable skill definitions.'),('Research','Proposals, protocols, and interactive explainers.'),('Publish','Engineering notes and the original writing archive.')],1)))
    connective = '''<section class="connection-banner"><div><p class="eyebrow">THE THREAD BETWEEN THE WORK</p><h2>Read the idea. Explore the system.<br>Inspect the evidence.</h2><p>Every asset has a stable home. The knowledge map connects related work and explains each relationship.</p></div><a class="button" href="/hub/graph/">Explore the knowledge map ↗</a></section>'''
    stories = '<section class="section"><div class="section-heading"><div><p class="eyebrow">LIFE BEHIND THE WORK</p><h2>Stories, places & personal notes</h2></div><a href="/hub/stories/">All writing & photos ↗</a></div><div class="story-grid">'+''.join(card(BY_ID[i]) for i in ['story-autumn-memo','writing-buyinghouse2021'])+'</div></section>'
    write('index.html', page('Kent Chiu · Research, systems & knowledge', 'Explore Kent Chiu’s research, interactive systems, writing, and opportunities to work together.', hero+entries+featured+stories+connective+streams))
    writing = head('WRITING & PHOTOS', 'The stories behind the systems.', 'Research beginnings, a home in Singapore, personal experiences, and years of engineering notes. Original articles, pictures, and charts stay together.')+'<div class="story-grid">'+''.join(card(BY_ID[i]) for i in ['story-autumn-memo','writing-buyinghouse2021'])+'</div>'+section('From the writing archive', ''.join(card(a, True) for a in ASSETS if a['kind']=='Article' and a['id'] not in ['story-autumn-memo','writing-buyinghouse2021']), '<a href="/hub/library/?kind=Article">Search all writing ↗</a>')
    write('hub/stories/index.html',page('Writing & photos','Personal stories, MIT-CSAIL beginnings, home-buying experiences, and illustrated engineering notes.',writing,'/hub/stories/'))
    # Build all static entry points; search is a progressive enhancement.
    controls = f'''<form class="library-controls" role="search" action="/hub/library/"><label class="search-label">Search the collection<input id="asset-search" name="q" type="search" placeholder="Try memory, evaluation, or finance…" autocomplete="off"></label><label>Asset type<select id="asset-kind" name="kind"><option value="">All types</option>{''.join(f'<option>{E(k)}</option>' for k in sorted({a['kind'] for a in ASSETS}))}</select></label><label>Workstream<select id="asset-stream" name="stream"><option value="">All streams</option><option>Build</option><option>Research</option><option>Publish</option></select></label><button type="reset" class="text-button">Reset</button></form>'''
    library = head('ASSET LIBRARY', 'One collection. Many directions.', 'Search research, demos, skills, and writing. Every entry connects to the preserved original source.')+controls+f'<p id="result-count" role="status">{len(ASSETS)} assets</p><div id="asset-results" class="card-grid">'+''.join(card(a,True) for a in ASSETS)+'</div><div id="empty-results" class="empty-state" hidden><h2>No matching assets</h2><p>Try a broader search or reset your filters.</p></div><noscript><p>All assets are listed below. Interactive filtering requires JavaScript.</p></noscript>'
    write('hub/library/index.html',page('Asset library','Browse research, demos, tools, writing, and reusable skills.',library,'/hub/library/'))
    offers = ''
    for o in OFFERS:
        terms = '<p class="muted">Scope and pricing by agreement. This is an inquiry, not a purchase.</p>'
        action = f'<a class="button" href="/hub/contact/?offer={o["id"]}">Discuss this engagement ↗</a>'
        if o['state']=='retired': action='<p>Not currently offered.</p>'
        elif o['state']=='available':
            terms=f'<p>{E(o["price"])} {E(o["currency"])} · <a href="{E(o["license_url"])}">License terms</a></p><p>{E(o["delivery_terms"])}</p>'
            action=f'<a class="button" href="{E(o["checkout_url"])}">Buy asset ↗</a>'
        offers += f'<article class="offer-card"><span class="eyebrow">{E(o["state"])} / ENGAGEMENT</span><h2>{E(o["title"])}</h2><p>{E(o["summary"])}</p><h3>Scope to agree</h3><ul>'+''.join(f'<li>{E(x)}</li>' for x in o['deliverables'])+'</ul><div class="evidence-links">'+''.join(f'<a href="{detail(BY_ID[i])}">{E(BY_ID[i]["title"])} ↗</a>' for i in o['asset_ids'])+'</div>'+terms+action+'</article>'
    collaboration = '''<section class="reading-path"><p class="eyebrow">START HERE / GUARDED SKILL EVOLUTION</p><h2>From a research question to an evaluation design.</h2><ol>'''+''.join(f'<li><a href="{detail(BY_ID[i])}">{E(BY_ID[i]["title"])} ↗</a></li>' for i in ['gse','gse-paper','gse-experiment-protocol','gse-benchmark-schema'])+'''</ol><p>Potential collaboration: critique the protocol, propose evaluation tasks, or discuss an independent implementation. Simulator values are illustrative; they are not completed experimental findings.</p><a class="button" href="/hub/contact/?purpose=Research%20collaboration">Propose a collaboration ↗</a></section>'''
    intro=head('WORK WITH ME','Build something useful. Explore a good question.','Bring a business problem, a research idea, or a technical challenge. Explore the work below and choose how we could work together.')
    choices='<div class="collaboration-choices"><a href="#projects"><strong>Start a project ↓</strong><span>Prototypes, architecture reviews, and scoped engagements.</span></a><a href="#research"><strong>Research together ↓</strong><span>Shared questions, evaluation designs, and experiments.</span></a></div>'
    projects='<section class="section" id="projects"><div class="section-heading"><h2>Projects & engagements</h2></div><div class="offer-grid">'+offers+'</div></section>'
    research='<section class="section" id="research"><div class="section-heading"><h2>Research collaboration</h2><a href="/hub/library/?kind=Research">Explore all research ↗</a></div><p class="lede">Inspect a proposal, critique the method, or suggest an experiment we could investigate together.</p>'+collaboration+'</section>'
    solutions=intro+choices+projects+research
    write('hub/solutions/index.html',page('Work with me','Discuss projects, AI systems engagements, and research collaboration with Kent Chiu.',solutions,'/hub/solutions/'))
    redirect_body=head('WORK WITH ME','Research and projects, together.','Research collaboration is now part of Work with me.')+'<a class="button" href="/hub/solutions/#research">Explore research collaboration ↗</a>'
    redirect=page('Research collaboration','Research collaboration is now part of Work with me.',redirect_body,'/hub/solutions/',active='/hub/solutions/').replace('<head>','<head><meta http-equiv="refresh" content="0;url=/hub/solutions/#research">',1)
    write('hub/collaborate/index.html',redirect)
    experience=head('EXPERIENCE & CAPABILITIES','Inspect the work behind the introduction.','Kent Chiu · AI systems, research, and engineering. Autumn Memo began during a research exchange in Randall Davis’s MIT-CSAIL lab.')+'''<section class="reading-path"><h2>Explore by capability</h2><p>This collection demonstrates areas of work through public artifacts. Project maturity is shown individually.</p><div class="capability-grid"><div><h3>Agent workflow design</h3><p>Coordination, document workflows, and human review.</p><a href="/hub/assets/ter/">Inspect the operations studio ↗</a></div><div><h3>Evaluation & research</h3><p>Hypotheses, regression controls, and evaluation design.</p><a href="/hub/assets/gse/">Inspect Guarded Skill Evolution ↗</a></div><div><h3>Product engineering</h3><p>Focused browser utilities and interactive systems.</p><a href="/hub/assets/publisher/">Inspect the ZIP Publisher ↗</a></div></div><a class="button" href="/about/">Read my background ↗</a> <a class="text-button" href="/hub/contact/?purpose=Technical%20opportunity">Discuss an opportunity ↗</a></section>'''+section('Selected engineering artifacts',''.join(card(BY_ID[i]) for i in ['ter','wealth','publisher']))
    write('hub/experience/index.html',page('Experience','Explore Kent Chiu’s technical work and background through public artifacts.',experience,'/hub/experience/'))
    connected={r[k] for r in RELATIONS for k in ['source','target']}
    graph=head('KNOWLEDGE MAP','Follow the connections, not just the files.','Select an asset to see its immediate connections. Every link includes a stated basis; topic links are editorial, not claims that one system implements another.')+f'''<label class="graph-picker">Explore an asset<select id="graph-focus">{''.join(f'<option value="{a["id"]}">{E(a["title"])}</option>' for a in ASSETS if a['id'] in connected)}</select></label><div class="graph-workspace"><div id="graph-canvas" aria-label="Selected asset and its connected records"></div><aside id="graph-context"></aside></div><section class="section"><h2>All recorded relationships</h2><div class="relationship-list">'''+''.join(f'<article><a href="{detail(BY_ID[r["source"]])}">{E(BY_ID[r["source"]]["title"])}</a><span>{E(r["type"].replace("_"," "))}</span><a href="{detail(BY_ID[r["target"]])}">{E(BY_ID[r["target"]]["title"])}</a><p>{E(r["basis"])}</p></article>' for r in RELATIONS)+'</div></section>'
    write('hub/graph/index.html',page('Knowledge map','Explore evidence-backed and editorial relationships between public assets.',graph,'/hub/graph/'))
    design=head('DESIGN TREE','One durable asset layer. Multiple experiences.','Original files keep their existing homes. A curated catalogue adds meaning and relationships; the web layer offers different ways to use the same work.')+'''<div class="design-tree"><section><span>01 / ORIGINAL SOURCES</span><h2>Preserved content</h2><p>Blogs · Markdown · Research sites · Agentic demos · Skills · Supporting files</p><small>Existing paths remain the source destinations.</small></section><div class="tree-arrow" aria-hidden="true">↓</div><section><span>02 / PUBLIC ASSET MEMORY</span><h2>Catalogue + knowledge graph</h2><p>Stable asset IDs · Source hashes · Types · Topics · Audiences · Maturity · Relationships · Rights · Offers</p><small>Git-backed records → JSON for the web + SQLite for structured queries.</small></section><div class="tree-arrow" aria-hidden="true">↓</div><section><span>03 / WEB EXPERIENCES</span><h2>Choose a purpose</h2><div class="tree-branches"><a href="/hub/solutions/">Work with me · projects & research</a><a href="/hub/experience/">Evaluate experience</a><a href="/hub/library/">Read & explore</a><a href="/hub/graph/">Follow relationships</a></div></section></div><section class="reading-path"><h2>Memory has different boundaries</h2><p><strong>Public knowledge memory:</strong> the durable catalogue, source fingerprints, and curated connections implemented here.</p><p><strong>Personal visitor memory:</strong> saved collections and cross-device reading progress would require authenticated storage. They are not silently stored in this public catalogue.</p><p><strong>Private operating memory:</strong> client notes, tasks, proposals, and payment entitlements belong in a separate authenticated backend. They must never be committed to this public repository.</p><p><strong>Commercial assets:</strong> selected engagements accept inquiries. Direct sales require approved price, license, delivery terms, and checkout; paid files require protected storage.</p><a href="/docs/hub/architecture.md">Read the architecture document ↗</a> · <a href="/data/hub/catalog.json">Public catalogue JSON ↗</a> · <a href="/data/hub/memory.sqlite" download>Public SQLite catalogue ↓</a></section>'''
    write('hub/design/index.html',page('Design tree','The asset, memory, graph, and web architecture of Autumn Memo.',design,'/hub/design/'))
    contact=head('START A CONVERSATION','Bring a problem, question, or opportunity.','Prepare a brief you can copy or download, then use the contact details available on my GitHub profile. This page does not send or store your message.')+'''<form id="brief-form" class="brief-form"><label>Your purpose<select id="brief-purpose"><option>Project inquiry</option><option>Research collaboration</option><option>Technical opportunity</option><option>Asset licensing</option></select></label><label>Related engagement<select id="brief-offer"><option value="">General conversation</option>'''+''.join(f'<option value="{o["id"]}">{E(o["title"])}</option>' for o in OFFERS)+'''</select></label><label>What would you like to work on?<textarea id="brief-context" rows="6" required placeholder="The problem, your context, desired outcome, and timeline…"></textarea></label><div class="actions"><button class="button" type="submit">Copy inquiry brief</button><button class="text-button" id="download-brief" type="button">Download as text ↓</button></div><p id="brief-status" role="status"></p><p><a href="https://github.com/KentChun33333" target="_blank" rel="noopener">Open Kent’s GitHub profile ↗</a></p></form><noscript><p>The brief builder requires JavaScript. You can still use the GitHub profile link to find contact information.</p></noscript>'''
    write('hub/contact/index.html',page('Start a conversation','Prepare a project, research, technical opportunity, or licensing inquiry.',contact,'/hub/contact/'))
    for a in ASSETS:
        rels=[r for r in RELATIONS if a['id'] in (r['source'],r['target'])]
        related=''
        for r in rels:
            other=BY_ID[r['target'] if r['source']==a['id'] else r['source']]
            related+=f'<li><a href="{detail(other)}">{E(other["title"])}</a><small>{E(r["type"].replace("_"," "))} · {E(r["basis"])}</small></li>'
        body=f'<a class="back-link" href="/hub/library/">← Asset library</a>'+head(a['kind']+' / '+a['stream'],a['title'],a['summary'])+f'''<div class="asset-toolbar"><span class="status">{E(a['status'])}</span><a class="button" href="{a['url']}">{'Open source' if a['path'].endswith('.md') else 'Open original '+a['kind'].lower()} ↗</a><button class="text-button" data-share>Copy share link</button><a href="/hub/contact/?purpose=Asset%20licensing">Discuss reuse ↗</a></div>'''
        if a['path'].endswith('.md'):
            body+='<article class="reader">'+markdown((ROOT/a['path']).read_text(),a['path'])+'</article>'
        else:
            if a.get('images'):
                body+='<section class="article-gallery" aria-label="Pictures from the original article">'+''.join(f'<figure><a href="{a["url"]}"><img src="{E(m["url"])}" alt="{E(m["alt"])}" loading="lazy" decoding="async"></a><figcaption>Original article image · <a href="{a["url"]}">Read with its full context ↗</a> · <a href="{E(m["url"])}">View full-size image ↗</a></figcaption></figure>' for m in a['images'])+'</section>'
            body+=f'''<section class="reading-path"><h2>{'Explore the interactive artifact' if a['kind'] in ['Demo','Research','Tool'] else 'Read the original article'}</h2><p>The original page retains its layout and interactions. Open it directly for the full experience.</p><a href="{a['url']}">Continue to the original asset ↗</a></section>'''
        if related: body+='<section class="section"><h2>Connected knowledge</h2><ul class="related-list">'+related+'</ul></section>'
        body+=f'<details class="source-details"><summary>Source & reuse information</summary><p>{E(a["rights"])}</p><p>Source: <a href="{a["url"]}">{E(a["path"])}</a></p><p>Asset ID: <code>{a["id"]}</code></p><p>Content fingerprint: <code class="fingerprint">{a["sha256"]}</code></p><p>The fingerprint records source identity, not the date of publication or independent verification of its claims.</p></details>'
        write('hub/assets/'+a['id']+'/index.html',page(a['title'],a['summary'],body,detail(a),active='/hub/library/',asset=a))


if __name__ == '__main__':
    validate()
    count=build_memory()
    build_pages()
    print(f'Built {len(ASSETS)} asset pages, {len(RELATIONS)} relations, {len(OFFERS)} offers; inventoried {count} source files.')
