#!/usr/bin/env python3
"""Record first-add commit timestamps as upload proxies; no filesystem dates.
Run with --write to update the authoritative catalogue; default is preview.
Git does not expose historical remote push/deployment timestamps.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'hub-src/catalog.json'
    data = json.loads(path.read_text())
    changed = 0
    for asset in data['assets']:
        rows = subprocess.check_output(['git', 'log', '--diff-filter=A', '--format=%cI%x09%H', '--', asset['path']], cwd=ROOT, text=True).splitlines()
        if not rows:
            print('No first-add commit; retaining date:', asset['id'])
            continue
        timestamp, commit = rows[-1].split('\t')
        record = {'at': datetime.fromisoformat(timestamp).astimezone(timezone.utc).isoformat(timespec='seconds'), 'source': 'git-first-add:' + commit + ':' + asset['path']}
        dates = asset.setdefault('dates', {})
        # Explicit editorial dates take precedence over Git-derived estimates.
        existing = dates.get('added', {})
        if existing and not existing.get('source', '').startswith(('git:', 'git-first-add:')):
            continue
        if existing != record:
            dates['added'] = record
            changed += 1
            print(asset['id'], record['at'])
    if args.write:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f'{changed} upload records ' + ('updated' if args.write else 'would change'))

if __name__ == '__main__':
    main()
