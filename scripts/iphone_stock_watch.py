#!/usr/bin/env python3
"""Singapore iPhone Duo authorised-channel watcher (stdlib, macOS).

Run: python3 scripts/iphone_stock_watch.py check
Schedule every 15 minutes: python3 scripts/iphone_stock_watch.py install
Status: python3 scripts/iphone_stock_watch.py status
Stop: python3 scripts/iphone_stock_watch.py uninstall

State, append-only history and alert links live in ~/Library/Application Support/
iPhoneDuoWatch. The LaunchAgent runs while this user is logged in; sleeping/offline
machines cannot check. It stops fetching after 2026-10-30 23:59 Singapore time.
Alerts mean a stock signal, NOT a booked unit or guaranteed delivery. Apple pickup
uses central Singapore postcode 238801, not the user's address. HTTP/challenge
failures stay UNKNOWN/ERROR; no CAPTCHA bypass, purchase, reservation or payment.

Verified live: iStudio's eight Shopify SKUs and Best Denki's eight product cards.
Apple fulfilment returned HTTP 541 during setup; it is retried each cycle but
cannot currently provide automated Apple pickup coverage. Telco JS-only stock
may remain UNKNOWN. No generic launch date or shipping policy triggers a stock
alert. Candidate/contradictory offer changes alert once per observed transition.
macOS notification submission is logged; visible delivery depends on permissions
and Focus settings. Run test-notification to submit a labelled non-stock test.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SG = ZoneInfo('Asia/Singapore')
ROOT = Path.home() / 'Library/Application Support/iPhoneDuoWatch'
LABEL = 'com.kentchiu.iphone-duo-watch'
PLIST = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
DEADLINE = datetime(2026, 10, 30, 23, 59, 59, tzinfo=SG)
APPLE = 'https://www.apple.com/sg/shop/buy-iphone/iphone-duo'
STUDIO = 'https://www.istudiosg.com/products/iphone-duo-mk2d4x-a'
BEST = 'https://www.bestdenki.com.sg/it-mobile/apple/iphone/iphone-duo.html'
PAGES = {
    'Gain City': 'https://www.gaincity.com/iphone-duo',
    'Singtel (plan required)': 'https://shop.singtel.com/phones/apple-iphone-duo',
    'StarHub (eligibility/plan restrictions)': 'https://www.starhub.com/personal/mobile/apple/iphone-duo.html',
    'M1 (reservation is not stock)': 'https://www.m1.com.sg/apple-iphone/iphone-duo',
}
HOSTS = {'www.apple.com', 'www.istudiosg.com', 'www.bestdenki.com.sg',
         'www.gaincity.com', 'shop.singtel.com', 'www.starhub.com', 'www.m1.com.sg'}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.words = []
        self.ld = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
            if tag == 'script' and attrs.get('type') == 'application/ld+json':
                self.script = ''

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            if self.script is not None:
                try:
                    self.ld.append(json.loads(self.script))
                except ValueError:
                    pass
                self.script = None
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if self.script is not None:
            self.script += data
        if not self.skip:
            self.words.append(data)

    @property
    def text(self):
        return ' '.join(' '.join(self.words).split())


def fetch(url):
    if urlparse(url).hostname not in HOSTS:
        raise ValueError('Non-authorised host rejected')
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; iPhoneDuoStockWatch/1.0)',
                                'Accept-Language': 'en-SG,en;q=0.9'})
    with urlopen(req, timeout=25) as response:
        if urlparse(response.url).hostname not in HOSTS:
            raise ValueError('Unexpected redirect host')
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Response too large')
        text = raw.decode('utf-8')
        if re.search(r'<title>[^<]*(access denied|just a moment|captcha)', text, re.I):
            raise ValueError('Challenge page; availability unknown')
        return text


def result(seller, url, status, evidence, sku='all/unspecified'):
    return dict(seller=seller, sku=sku, url=url, status=status, evidence=evidence,
                delivery='UNCONFIRMED — verify collection/delivery by 30 October')


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def product_signals(raw):
    page = Page()
    page.feed(raw)
    statuses = []
    for root in page.ld:
        for obj in walk(root):
            kind = obj.get('@type', [])
            if isinstance(kind, str):
                kind = [kind]
            if 'Product' not in kind or not re.search(r'iphone\s+duo', obj.get('name', ''), re.I):
                continue
            # Only offers belonging to this exact product, never other page products.
            states = {str(o['availability']).rsplit('/', 1)[-1]
                      for o in walk(obj.get('offers', [])) if 'availability' in o}
            if states:
                statuses.append((obj['name'], states))
    return page, statuses


def generic(seller, url):
    raw = fetch(url)
    page, signals = product_signals(raw)
    rows = []
    for name, states in signals:
        positive = 'InStock' in states
        negative = bool(states & {'OutOfStock', 'PreOrder', 'BackOrder', 'SoldOut'})
        status = 'CONFLICT' if positive and negative else 'CANDIDATE' if positive else 'UNAVAILABLE'
        rows.append(result(seller, url, status, 'Product offer: ' + ', '.join(sorted(states)), name))
    if rows:
        return rows
    # Negative copy is not evidence of a particular variant. Never infer stock from
    # launch dates, add-to-cart text, generic free delivery or page changes.
    matches = re.findall(r'.{0,70}(?:stocks are fully reserved|out of stock|backorder|reserve now|next available inventory).{0,100}', page.text, re.I)
    return [result(seller, url, 'UNKNOWN', ' | '.join(matches[:3]) or 'No machine-readable SKU availability; manual check needed')]


def studio():
    raw = fetch(STUDIO)
    handles = sorted(set(re.findall(r'iphone-duo-mk2[a-z0-9]+-a', raw)))
    if len(handles) != 8:
        raise ValueError(f'Expected eight Duo product handles, discovered {len(handles)}')
    rows = []
    for handle in handles:
        url = 'https://www.istudiosg.com/products/' + handle
        data = json.loads(fetch(url + '.js'))
        if not re.search(r'iphone\s+duo', data.get('title', ''), re.I):
            raise ValueError('Unexpected iStudio product')
        available = data.get('available')
        status = 'CANDIDATE' if available is True else 'UNAVAILABLE' if available is False else 'UNKNOWN'
        rows.append(result('iStudio', url, status, f'Shopify available={available}; shipping date not provided', data['title']))
    return rows


def best():
    raw = fetch(BEST)
    cards = re.findall(r'<li\b[^>]*class="[^"]*product-item[^"]*"[^>]*>(.*?)</li>', raw, re.S)
    rows = []
    for card in cards:
        page = Page()
        page.feed(card)
        if not re.search(r'iphone\s+duo', page.text, re.I):
            continue
        links = re.findall(r'href="([^"]+)"', card)
        url = next((u for u in links if 'mk2' in u.lower()), BEST)
        negative = bool(re.search(r'out of stock|sold out|notify me', page.text, re.I))
        positive = bool(re.search(r'\bin stock\b|add to cart', page.text, re.I))
        status = 'CONFLICT' if positive and negative else 'UNAVAILABLE' if negative else 'CANDIDATE' if positive else 'UNKNOWN'
        rows.append(result('Best Denki', unescape(url), status, page.text[:500], page.text.split('$')[0].strip()))
    if len(rows) != 8:
        raise ValueError(f'Expected eight Best Denki variants, parsed {len(rows)}')
    return rows


def apple():
    raw = fetch(APPLE)
    parts = sorted(set(re.findall(r'"partNumber"\s*:\s*"(MK2[A-Z0-9]+X/A)"', raw)))
    if len(parts) != 8:
        raise ValueError(f'Expected eight Apple Duo parts, discovered {len(parts)}')
    params = {'fae': 'true', 'pl': 'true', 'location': '238801'}
    params.update({f'parts.{i}': part for i, part in enumerate(parts)})
    api = 'https://www.apple.com/sg/shop/fulfillment-messages?' + urlencode(params)
    data = json.loads(fetch(api))
    rows = []
    for obj in walk(data):
        for part in parts:
            entry = obj.get(part)
            if not isinstance(entry, dict):
                continue
            display = entry.get('pickupDisplay')
            if display is None:
                continue
            evidence = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            status = 'CANDIDATE' if display == 'available' else 'UNAVAILABLE' if display in ('unavailable', 'ineligible') else 'UNKNOWN'
            rows.append(result('Apple pickup', APPLE, status, evidence, part))
    if not rows:
        return [result('Apple', APPLE, 'UNKNOWN', 'Fulfilment returned no recognised pickup availability; manual check needed')]
    return rows


def safe_check(name, url, fn):
    try:
        return fn()
    except Exception as exc:
        return [result(name, url, 'ERROR', f'{type(exc).__name__}: {exc}')]


def notification(title, message):
    # argv avoids interpolating retailer text into AppleScript source.
    source = 'on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"\nend run'
    done = subprocess.run(['/usr/bin/osascript', '-e', source, title, message], capture_output=True, text=True)
    return {'submitted': done.returncode == 0, 'error': done.stderr.strip(),
            'note': 'Submission does not prove visible delivery; macOS notification permissions/Focus apply.'}


def run_check(notify=True):
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'check.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another check is running; skipped.')
            return
        now = datetime.now(SG)
        if now > DEADLINE:
            print('Travel deadline passed; no network requests made.')
            return
        state_path = ROOT / 'latest.json'
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        jobs = [('Apple', APPLE, apple), ('iStudio', STUDIO, studio), ('Best Denki', BEST, best)]
        jobs += [(name, url, lambda n=name, u=url: generic(n, u)) for name, url in PAGES.items()]
        with ThreadPoolExecutor(max_workers=4) as pool:
            batches = list(pool.map(lambda job: safe_check(*job), jobs))
        rows = [row for batch in batches for row in batch]
        old = {(r['seller'], r['sku'], r['url']): r for r in previous.get('results', [])}
        alerts = []
        for row in rows:
            prior = old.get((row['seller'], row['sku'], row['url']), {})
            if row['status'] in ('CANDIDATE', 'CONFLICT') and (prior.get('status'), prior.get('evidence')) != (row['status'], row['evidence']):
                alerts.append(row)
        errors = [r for r in rows if r['status'] == 'ERROR']
        old_errors = {(r['seller'], r['evidence']) for r in previous.get('results', []) if r['status'] == 'ERROR'}
        new_errors = [r for r in errors if (r['seller'], r['evidence']) not in old_errors]
        report = {'checked_at': now.isoformat(), 'deadline': DEADLINE.isoformat(), 'results': rows,
                  'alerts': alerts, 'notifications': []}
        if notify and alerts:
            report['notifications'].append(notification('iPhone Duo：正規渠道庫存訊號', '; '.join(r['seller'] + ' ' + r['sku'] for r in alerts)[:220] + '。交貨未確認；請查看監察結果。'))
        if notify and new_errors:
            report['notifications'].append(notification('iPhone Duo：部分渠道無法檢查', ', '.join(r['seller'] for r in new_errors) + '；不是缺貨結論，請手動查看。'))
        text = json.dumps(report, ensure_ascii=False, indent=2)
        temporary = ROOT / 'latest.tmp'
        temporary.write_text(text)
        temporary.replace(state_path)
        with (ROOT / 'history.jsonl').open('a') as history:
            history.write(json.dumps(report, ensure_ascii=False) + '\n')
        if alerts:
            with (ROOT / 'alerts.txt').open('a') as output:
                for row in alerts:
                    output.write(f"{now.isoformat()} {row['seller']} {row['sku']} {row['status']}\n{row['url']}\n{row['delivery']}\n\n")
        print(text, flush=True)


def schedule(install):
    domain = f'gui/{os.getuid()}'
    if not install:
        if PLIST.exists():
            subprocess.run(['/bin/launchctl', 'bootout', domain, str(PLIST)], check=False)
            PLIST.unlink()
        print('Schedule removed; history retained at', ROOT)
        return
    ROOT.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    config = {'Label': LABEL, 'ProgramArguments': [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), 'check'],
              'StartInterval': 900, 'RunAtLoad': True, 'ProcessType': 'Background',
              'StandardOutPath': str(ROOT / 'launchd.log'), 'StandardErrorPath': str(ROOT / 'launchd-error.log')}
    if PLIST.exists():
        subprocess.run(['/bin/launchctl', 'bootout', domain, str(PLIST)], check=False)
    PLIST.write_bytes(plistlib.dumps(config))
    subprocess.run(['/bin/launchctl', 'bootstrap', domain, str(PLIST)], check=True)
    print('Installed:', PLIST, '\nEvery 900 seconds while logged in; deadline:', DEADLINE.isoformat())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['check', 'install', 'uninstall', 'status', 'test-notification'])
    parser.add_argument('--no-notify', action='store_true')
    args = parser.parse_args()
    if args.command == 'check':
        run_check(notify=not args.no_notify)
    elif args.command in ('install', 'uninstall'):
        schedule(args.command == 'install')
    elif args.command == 'test-notification':
        print(json.dumps(notification('iPhone Duo 監察測試', '這是通知測試，不是有貨通知。'), ensure_ascii=False))
    else:
        path = ROOT / 'latest.json'
        print(path.read_text() if path.exists() else 'No completed check yet.')
        subprocess.run(['/bin/launchctl', 'print', f'gui/{os.getuid()}/{LABEL}'], check=False)


if __name__ == '__main__':
    main()
