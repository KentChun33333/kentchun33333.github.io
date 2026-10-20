"""Web search providers behind the web agent's private search tool (web_research.py), tried in the order of
`web_search_providers`:

- ddgs: in-process metasearch library (bing, brave, duckduckgo, google, ...): no server, no API key.
- searxng: a SearXNG instance's JSON API at `web_search_searxng_url` (settings.yml needs `json` under
  `search.formats`). Skipped while the URL is empty.

A provider that fails or finds nothing hands over to the next one; the answer names the provider that answered
and why earlier ones did not.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from ..config import Settings

TIMELIMITS = ("d", "w", "m", "y")
SEARXNG_TIME_RANGE = {"d": "day", "w": "week", "m": "month", "y": "year"}


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    snippet: str
    published: str = ""


class ProviderError(Exception):
    """This provider cannot answer now; the chain moves on."""


class ProviderSkipped(ProviderError):
    """Not configured (e.g. no SearXNG URL): not worth reporting unless every provider fails."""


def search_ddgs(settings: Settings, query: str, n: int, timelimit: str | None) -> list[WebResult]:
    from ddgs import DDGS                       # lazy: loads a native HTTP client
    from ddgs.exceptions import DDGSException, RatelimitException

    try:
        rows = DDGS(timeout=settings.web_search_timeout).text(query, max_results=n, timelimit=timelimit)
    except RatelimitException:
        raise ProviderError("rate-limited by the search engines") from None
    except DDGSException as e:
        if "No results" in str(e):
            return []
        raise ProviderError(str(e)) from None
    return [WebResult(str(r.get("title") or ""), str(r.get("href") or ""), str(r.get("body") or ""))
            for r in rows if r.get("href")]


def search_searxng(settings: Settings, query: str, n: int, timelimit: str | None) -> list[WebResult]:
    base = settings.web_search_searxng_url.strip().rstrip("/")
    if not base:
        raise ProviderSkipped("web_search_searxng_url is not set")
    params = {"q": query, "format": "json"}
    if timelimit:
        params["time_range"] = SEARXNG_TIME_RANGE[timelimit]
    req = urllib.request.Request(f"{base}/search?{urllib.parse.urlencode(params)}",
                                 headers={"Accept": "application/json", "User-Agent": "kentc-agent"})
    try:
        with urllib.request.urlopen(req, timeout=settings.web_search_timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        hint = " (enable json under search.formats in settings.yml)" if e.code == 403 else ""
        raise ProviderError(f"HTTP {e.code} from {base}{hint}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        reason = getattr(e, "reason", e)
        raise ProviderError(f"cannot reach {base}: {reason}") from None
    except ValueError:
        raise ProviderError(f"{base} did not return JSON") from None
    results = [WebResult(str(r.get("title") or ""), str(r["url"]), str(r.get("content") or ""),
                         str(r.get("publishedDate") or "")[:10])
               for r in data.get("results") or [] if isinstance(r, dict) and r.get("url")]
    if not results and data.get("unresponsive_engines"):
        down = ", ".join(f"{e[0]} ({e[1]})" for e in data["unresponsive_engines"] if len(e) >= 2)
        raise ProviderError(f"no results; engines not answering: {down}")
    return results[:n]


PROVIDERS: dict[str, Callable[[Settings, str, int, str | None], list[WebResult]]] = {
    "ddgs": search_ddgs,
    "searxng": search_searxng,
}


def provider_names(settings: Settings) -> list[str]:
    names = [n for n in re.split(r"[,\s]+", settings.web_search_providers.strip().lower()) if n]
    unknown = [n for n in names if n not in PROVIDERS]
    if unknown or not names:
        raise ValueError(f"web_search_providers: unknown or empty {unknown or names!r}; "
                         f"use a comma-separated list of {', '.join(PROVIDERS)}")
    return names


def web_search(settings: Settings, query: str, n: int, timelimit: str | None
               ) -> tuple[str | None, list[WebResult], list[str]]:
    """-> (provider that answered or None, results, notes on providers that did not).
    Raises ProviderError when no provider could search at all."""
    notes: list[str] = []
    skipped: list[str] = []
    searched = False
    for name in provider_names(settings):
        try:
            results = PROVIDERS[name](settings, query, n, timelimit)
        except ProviderSkipped as e:
            skipped.append(f"{name}: {e}")
            continue
        except ProviderError as e:
            notes.append(f"{name}: {e}")
            continue
        searched = True
        if results:
            return name, results, notes
        notes.append(f"{name}: no results")
    if not searched:
        raise ProviderError("; ".join(notes + skipped) or "no provider configured")
    return None, [], notes
