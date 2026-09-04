#!/usr/bin/env python3
"""Validate generated routes, data integrity, source fingerprints and safety gates."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import importlib.util
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT/'data/hub/catalog.json').read_text())
builder_origin = 'https://kentchun33333.github.io'


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]; self.ids=set(); self.meta={}; self.canonical=None
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, 'Duplicate HTML ID: '+attrs['id']
            self.ids.add(attrs['id'])
        for attr in ['href','src']:
            if attrs.get(attr): self.refs.append(attrs[attr])
        if tag=='meta': self.meta[attrs.get('property',attrs.get('name',''))]=attrs.get('content')
        if tag=='link' and attrs.get('rel')=='canonical': self.canonical=attrs.get('href')


pages=[ROOT/'index.html', *sorted((ROOT/'hub').rglob('index.html'))]
failures=[]
for p in pages:
    parsed=Page(); parsed.feed(p.read_text())
    for ref in parsed.refs:
        url=urlsplit(ref)
        if url.scheme or url.netloc: continue
        target=(ROOT/unquote(url.path).lstrip('/')) if url.path.startswith('/') else p.parent/unquote(url.path)
        if not url.path: target=p
        if target.is_dir(): target=target/'index.html'
        # Original Markdown may link to absent historical targets; preserve and
        # report these separately, without treating existing source gaps as edits.
        if not target.exists(): failures.append((str(p.relative_to(ROOT)),ref))
    assert parsed.canonical, p
    assert parsed.meta.get('og:title') and parsed.meta.get('og:description'), p
    assert parsed.meta.get('twitter:title') and parsed.meta.get('twitter:description'), p
    if '/assets/' in str(p):
        asset=next(a for a in data['assets'] if a['id']==p.parent.name)
        assert parsed.meta['og:description']==asset['summary'], p
        assert parsed.meta['og:title']==asset['title']+' · Autumn Memo', p
        if asset.get('images'):
            assert parsed.meta.get('og:image')==builder_origin+asset['images'][0]['url'], 'Use the original article image for sharing'
        else:
            assert 'og:image' not in parsed.meta, 'Detail page must not inherit unrelated homepage image'

conn=sqlite3.connect(ROOT/'data/hub/memory.sqlite')
assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert not conn.execute('PRAGMA foreign_key_check').fetchall()
assert conn.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==len(data['assets'])
for a in data['assets']:
    assert hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest()==a['sha256'], a['path']
    if a['path'].endswith('.md'):
        reader = ROOT/'data/hub/readers'/(a['id']+'.html')
        assert reader.is_file() and '<article class="reader">' in reader.read_text(), a['id']
    assert conn.execute('SELECT 1 FROM revisions WHERE asset_id=? AND sha256=?',(a['id'],a['sha256'])).fetchone()
    for media in a.get('images', []):
        path=ROOT/unquote(media['url']).lstrip('/')
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==media['sha256']
        assert conn.execute('SELECT sha256 FROM asset_media WHERE asset_id=? AND url=?',(a['id'],media['url'])).fetchone()[0]==media['sha256']
assert conn.execute('SELECT COUNT(*) FROM offer_assets').fetchone()[0]==sum(len(o['asset_ids']) for o in data['offers'])
assert conn.execute('SELECT COUNT(*) FROM asset_media').fetchone()[0]==sum(len(a.get('images',[])) for a in data['assets'])
conn.close()

spec=importlib.util.spec_from_file_location('build_hub',ROOT/'scripts/build_hub.py')
builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
unsafe=builder.markdown('<script>alert(1)</script>\n\n[bad](javascript:alert)\n\n[good](https://example.org)','skills/example/SKILL.md')
assert '<script>' not in unsafe and 'href="javascript:' not in unsafe
assert 'href="https://example.org"' in unsafe
assert 'href="/skills/example/reference.md"' in builder.markdown('[relative](reference.md)','skills/example/SKILL.md')
builder.ASSETS[0]['visibility']='private'
try: builder.validate(); raise RuntimeError('Private publication was not blocked')
except AssertionError: pass
builder.ASSETS[0]['visibility']='public'
builder.OFFERS[0]['state']='available'
try: builder.validate(); raise RuntimeError('Incomplete checkout was not blocked')
except AssertionError: pass

source_link_gaps=[f for f in failures if '/assets/' in f[0] and f[1].startswith('/skills/')]
other=[f for f in failures if f not in source_link_gaps]
print(f'Validated {len(pages)} pages, {len(data["assets"])} assets, database integrity, source fingerprints, safe reader, and publication/checkout gates.')
if source_link_gaps:
    print('Existing skill source references without local targets:')
    for source,ref in source_link_gaps: print(' ',source,'->',ref)
assert not other, 'Unresolved generated links: '+repr(other)
print('Generated hub navigation resolves. No browser visual test was run.')
