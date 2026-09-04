"""Opt-in HTML discovery. Standard library only; never writes source assets."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class Metadata(HTMLParser):
    def __init__(self, marker):
        super().__init__(); self.marker = marker; self.blocks = []; self.active = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('id') == self.marker:
            if attrs.get('type') != 'application/json':
                raise ValueError('Asset metadata must use type=application/json')
            self.blocks.append(''); self.active = True
    def handle_data(self, data):
        if self.active: self.blocks[-1] += data
    def handle_endtag(self, tag):
        if tag == 'script': self.active = False


def validate_record(record, config):
    if not isinstance(record, dict) or record.get('schema_version') != 1:
        raise ValueError('Expected asset metadata schema_version=1')
    missing = set(config['required']) - record.keys()
    if missing: raise ValueError('Missing metadata: ' + ', '.join(sorted(missing)))
    allowed = set(config['required']) | {'schema_version', 'audiences', 'featured'}
    if record.keys() - allowed: raise ValueError('Unknown metadata fields: ' + ', '.join(sorted(record.keys() - allowed)))
    for key in ['id', 'title', 'summary', 'kind', 'stream', 'status', 'visibility', 'rights']:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(key + ' must be nonempty text')
    if not re.fullmatch(r'[a-z0-9_-]+', record['id']): raise ValueError('Invalid asset ID')
    if record['kind'] not in config['kinds'] or record['stream'] not in config['streams']:
        raise ValueError('Unknown kind or stream')
    if record['visibility'] not in ['public', 'unlisted']: raise ValueError('Use public or unlisted visibility')
    for key in ['topics', 'audiences']:
        value = record.get(key, [])
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            raise ValueError(key + ' must be an array of nonempty strings')
    if 'featured' in record and not isinstance(record['featured'], bool): raise ValueError('featured must be boolean')
    if not isinstance(record['dates'], dict): raise ValueError('dates must be an object')
    for kind, date in record['dates'].items():
        if kind not in ['published', 'added'] or not isinstance(date, dict): raise ValueError('Unknown date kind')
        if set(date) != {'at', 'source'} or not isinstance(date['source'], str) or not date['source'].strip():
            raise ValueError('Date needs at and source evidence')
        dt = datetime.fromisoformat(date['at'].replace('Z', '+00:00'))
        if dt.tzinfo is None: raise ValueError('Date needs timezone')
        date['at'] = dt.astimezone(timezone.utc).isoformat(timespec='seconds')


def discover_assets(root, curated, config_path=None):
    root = Path(root).resolve()
    config = json.loads((config_path or root / 'hub-src/discovery.json').read_text())
    if config.get('schema_version') != 1: raise ValueError('Unknown discovery config version')
    candidates = set()
    for folder in config['roots']:
        directory = (root / folder).resolve()
        if not directory.is_relative_to(root) or directory == root:
            raise ValueError('Discovery root must be a repository subdirectory')
        if directory.is_dir():
            for path in directory.rglob('*.html'):
                if path.is_symlink() or not path.resolve().is_relative_to(root): continue
                if any(part.startswith('.') for part in path.relative_to(root).parts): continue
                candidates.add(path)
    by_id = {a['id']: a for a in curated}; by_path = {a['path']: a for a in curated}
    found = []
    for path in sorted(candidates):
        relative = path.relative_to(root).as_posix()
        try:
            parser = Metadata(config['metadata_id']); parser.feed(path.read_text(encoding='utf-8'))
            if not parser.blocks: continue
            if len(parser.blocks) != 1: raise ValueError('Exactly one metadata block required')
            record = json.loads(parser.blocks[0]); validate_record(record, config)
            existing_id, existing_path = by_id.get(record['id']), by_path.get(relative)
            if existing_id is not None or existing_path is not None:
                if existing_id is existing_path and existing_id in curated:
                    # Central editorial records own existing listings; embedded data
                    # cannot silently change their visibility, dates, or identity.
                    continue
                raise ValueError('Duplicate or conflicting asset ID/path')
            if record['visibility'] == 'unlisted':
                by_id[record['id']] = record; by_path[relative] = record
                continue
            record.pop('schema_version')
            record.update(path=relative, audiences=record.get('audiences', []), featured=record.get('featured', False))
            found.append(record); by_id[record['id']] = record; by_path[relative] = record
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ValueError(relative + ': ' + str(exc)) from exc
    return found
