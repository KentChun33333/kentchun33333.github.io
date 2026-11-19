"""Free public data sources with an on-disk cache. No API keys required."""

from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import requests

CACHE = Path(__file__).parent / "cache"
MAX_AGE_SECONDS = 12 * 3600
UA = {"User-Agent": "Mozilla/5.0 (sg-crisis-monitor)"}

FRED_SERIES = ["BAA10Y", "STLFSI4", "NFCI", "VIXCLS", "T10Y2Y", "DEXSIUS", "DEXHKUS", "DTB4WK", "DTB3"]
YAHOO_TICKERS = ["^STI", "D05.SI", "O39.SI", "U11.SI", "^VIX", "^VIX3M", "SPY", "RSP", "^SOX"]


def _cached(name: str, fetch, refresh: bool) -> pd.DataFrame:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{name}.csv"
    if not refresh and path.exists() and time.time() - path.stat().st_mtime < MAX_AGE_SECONDS:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    try:
        df = fetch()
    except Exception as exc:  # network failure: fall back to stale cache if any
        if path.exists():
            print(f"  ! {name}: fetch failed ({exc}); using stale cache")
            return pd.read_csv(path, index_col=0, parse_dates=True)
        raise
    df.to_csv(path)
    return df


def fred(series_id: str, refresh: bool = False) -> pd.Series:
    def fetch():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True, na_values=".")
        df.columns = [series_id]
        return df

    return _cached(f"fred_{series_id}", fetch, refresh)[series_id].dropna()


def yahoo(ticker: str, refresh: bool = False) -> pd.Series:
    """Daily adjusted close (dividend-adjusted where Yahoo provides it)."""

    def fetch():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"period1": 315532800, "period2": int(time.time()), "interval": "1d", "events": "div,split"}
        r = requests.get(url, params=params, headers=UA, timeout=60)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        ind = res["indicators"]
        px = ind["adjclose"][0]["adjclose"] if "adjclose" in ind else ind["quote"][0]["close"]
        idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
        df = pd.DataFrame({"close": px}, index=idx)
        return df[~df.index.duplicated(keep="last")]

    safe = ticker.replace("^", "IDX_").replace(".", "_")
    return _cached(f"yahoo_{safe}", fetch, refresh)["close"].dropna()


def ofr_fsi(refresh: bool = False) -> pd.DataFrame:
    def fetch():
        r = requests.get("https://www.financialresearch.gov/financial-stress-index/data/fsi.csv", headers=UA, timeout=60)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True)

    return _cached("ofr_fsi", fetch, refresh)


def hkma_liquidity(refresh: bool = False) -> pd.DataFrame:
    """HKMA daily interbank liquidity: HIBOR fixings + aggregate balance (HK$ mn)."""

    def fetch():
        base = "https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity"
        rows, offset = [], 0
        while True:
            params = {"pagesize": 1000, "offset": offset, "sortby": "end_of_date", "sortorder": "asc"}
            for attempt in range(3):  # HKMA's WAF answers 405 when requests come too fast
                r = requests.get(base, params=params, headers=UA, timeout=60)
                if r.status_code not in (405, 429):
                    break
                time.sleep(10 * (attempt + 1))
            r.raise_for_status()
            time.sleep(2)
            recs = r.json()["result"]["records"]
            rows += recs
            if len(recs) < 1000:
                break
            offset += 1000
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df.pop("end_of_date"))
        return df[["hibor_overnight", "hibor_fixing_1m", "closing_balance"]].apply(pd.to_numeric, errors="coerce")

    return _cached("hkma_liquidity", fetch, refresh)


def _empty(columns: list[str] | None) -> pd.Series | pd.DataFrame:
    idx = pd.DatetimeIndex([])
    return pd.Series(dtype=float, index=idx) if columns is None else pd.DataFrame(columns=columns, index=idx, dtype=float)


def load_all(refresh: bool = False) -> tuple[dict, list[str]]:
    """Every source is optional: a failed download with no cache yields an empty series,
    and the composite is computed from whatever components remain."""
    jobs = [(s, "fred ", lambda s=s: fred(s, refresh), None) for s in FRED_SERIES]
    jobs += [(t, "yahoo", lambda t=t: yahoo(t, refresh), None) for t in YAHOO_TICKERS]
    jobs += [("OFR", "ofr  ", lambda: ofr_fsi(refresh), ["OFR FSI", "Funding"])]
    jobs += [("HKMA", "hkma ", lambda: hkma_liquidity(refresh), ["hibor_overnight", "hibor_fixing_1m", "closing_balance"])]
    out, missing = {}, []
    for key, src, fn, cols in jobs:
        print(f"  {src} {key}")
        try:
            out[key] = fn()
        except Exception as exc:
            print(f"  ! {key}: unavailable ({exc}); excluded from this run")
            out[key], missing = _empty(cols), missing + [key]
    return out, missing
