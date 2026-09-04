#!/usr/bin/env python3
"""Contract checks and isolated build integration; no production fixtures."""
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from asset_discovery import discover_assets

ROOT = Path(__file__).resolve().parents[1]

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'hub-src').mkdir(); (self.root / 'ai-research-insights').mkdir()
        shutil.copy(ROOT / 'hub-src/discovery.json', self.root / 'hub-src/discovery.json')
        self.record = json.loads((ROOT / 'docs/hub/asset-metadata.example.json').read_text())
    def write(self, record=None, filename='new.html'):
        path = self.root / 'ai-research-insights' / filename
        path.write_text('<html><head><script type="application/json" id="asset-metadata">' + json.dumps(record or self.record) + '</script></head><body>Preserve this artifact.</body></html>')
        return path
    def test_opt_in_and_source_preservation(self):
        path = self.write(); before = path.read_bytes()
        (path.parent / 'legacy.html').write_text('<html>Unmarked</html>')
        result = discover_assets(self.root, [])
        self.assertEqual(len(result), 1); self.assertEqual(result[0]['path'], 'ai-research-insights/new.html')
        self.assertEqual(before, path.read_bytes())
        record = copy.deepcopy(self.record); record['visibility'] = 'unlisted'; self.write(record)
        self.assertEqual(discover_assets(self.root, []), [])
    def test_invalid_and_duplicate_metadata(self):
        for field, value in [('id','../bad'), ('kind','Unknown'), ('topics','not a list'), ('dates',{'added':{'at':'2026-09-04','source':'note'}})]:
            with self.subTest(field=field):
                record = copy.deepcopy(self.record); record[field] = value; self.write(record)
                with self.assertRaises(ValueError): discover_assets(self.root, [])
        record = copy.deepcopy(self.record); del record['summary']; self.write(record)
        with self.assertRaises(ValueError): discover_assets(self.root, [])
        self.write(); self.write(filename='duplicate.html')
        with self.assertRaises(ValueError): discover_assets(self.root, [])
    def test_curated_precedence_and_path_conflict(self):
        self.write(); curated = dict(self.record, path='ai-research-insights/new.html', title='Editorial title')
        self.assertEqual(discover_assets(self.root, [curated]), [])
        curated['id'] = 'other'
        with self.assertRaises(ValueError): discover_assets(self.root, [curated])
    def test_date_normalization(self):
        self.record['dates'] = {'added':{'at':'2026-09-04T09:00:00+08:00','source':'editorial: verified upload'}}
        self.write()
        self.assertEqual(discover_assets(self.root, [])[0]['dates']['added']['at'], '2026-09-04T01:00:00+00:00')
    def test_isolated_build(self):
        shutil.copytree(ROOT / 'scripts', self.root / 'scripts')
        for name in ['catalog.json', 'schema.sql']:
            shutil.copy(ROOT / 'hub-src' / name, self.root / 'hub-src' / name)
        catalogue = json.loads((ROOT / 'hub-src/catalog.json').read_text())
        for asset in catalogue['assets']:
            source = self.root / asset['path']; source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / asset['path'], source)
        (self.root / 'data/hub').mkdir(parents=True)
        path = self.write(); before = path.read_bytes()
        result = subprocess.run([sys.executable, str(self.root / 'scripts/build_hub.py')], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        assets = json.loads((self.root / 'data/hub/catalog.json').read_text())['assets']
        self.assertIn(self.record['id'], [a['id'] for a in assets])
        self.assertIn('/hub/assets/' + self.record['id'] + '/', (self.root / 'index.html').read_text())
        self.assertTrue((self.root / 'hub/assets' / self.record['id'] / 'index.html').is_file())
        with sqlite3.connect(self.root / 'data/hub/memory.sqlite') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM assets WHERE id=?', (self.record['id'],)).fetchone()[0], 1)
        self.assertEqual(before, path.read_bytes())

if __name__ == '__main__': unittest.main()
