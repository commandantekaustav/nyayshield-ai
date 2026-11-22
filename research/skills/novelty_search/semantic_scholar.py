"""Free-tier Semantic Scholar Graph API & arXiv API targeted search wrapper.

Fetches only compact metadata (title, year, citationCount, short abstract, url).
Never scrapes full HTML pages. Hard cap: max 2 queries per run.
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

import requests

S2_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_ENDPOINT = "http://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 8


def search_semantic_scholar(
    query: str,
    limit: int = 2,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Query Semantic Scholar Graph API for compact paper metadata."""
    params = {
        "query": query.strip()[:160],
        "limit": max(1, min(limit, 5)),
        "fields": "title,year,citationCount,abstract,url",
    }
    resp = requests.get(S2_ENDPOINT, params=params, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    results: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        abstract = (item.get("abstract") or "").strip()
        results.append(
            {
                "source": "semantic_scholar",
                "title": (item.get("title") or "").strip(),
                "year": item.get("year"),
                "citationCount": item.get("citationCount", 0),
                "abstract": abstract[:300],
                "url": item.get("url", ""),
            }
        )
    return results


def search_arxiv(
    query: str,
    limit: int = 2,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Fallback query to arXiv Atom API for compact metadata."""
    encoded = urllib.parse.quote(query.strip()[:160])
    url = f"{ARXIV_ENDPOINT}?search_query=all:{encoded}&start=0&max_results={max(1, min(limit, 5))}"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:4]
        link = entry.findtext("atom:id", default="", namespaces=ns) or ""
        results.append(
            {
                "source": "arxiv",
                "title": " ".join(title.split()),
                "year": int(published) if published.isdigit() else None,
                "citationCount": 0,
                "abstract": " ".join(summary.split())[:300],
                "url": link.strip(),
            }
        )
    return results


def targeted_search(query: str, limit: int = 2) -> list[dict[str, Any]]:
    """Try Semantic Scholar first, falling back to arXiv, and returning [] if offline."""
    if not query.strip():
        return []
    try:
        hits = search_semantic_scholar(query, limit=limit)
        if hits:
            return hits
    except Exception:
        pass
    try:
        return search_arxiv(query, limit=limit)
    except Exception:
        return []
