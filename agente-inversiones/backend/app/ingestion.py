"""Ingesta de fuentes externas: RSS y Yahoo Finance por ticker.
Normaliza documentos y los publica vía tool_upsert_docs.
"""
from typing import List, Tuple
import os
import re
import time
import feedparser
from datetime import datetime, timezone

import yfinance as yf

from .db import get_conn
from .tools import tool_upsert_docs


DEFAULT_FEEDS = [
    # Reuters Business
    "https://feeds.reuters.com/reuters/businessNews",
    # CNBC Top News
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    # MarketWatch Top Stories
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    # SEC EDGAR (current filings)
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&count=40&output=atom",
]


def _get_portfolio_tickers() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT UPPER(ticker) FROM portfolio")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def _extract_source(url: str) -> str:
    try:
        host = re.sub(r"^https?://", "", url).split("/")[0]
        return host
    except Exception:
        return "unknown"


def _entry_timestamp(entry) -> str:
    # feedparser provides 'published_parsed' or 'updated_parsed'
    dt = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


def _detect_tickers(text: str, portfolio_tickers: List[str]) -> List[str]:
    if not text:
        return []
    upper = text.upper()
    found: List[str] = []
    for t in portfolio_tickers:
        # evitemos falsos positivos muy cortos; exigir longitud >= 3
        if len(t) >= 3 and t in upper:
            found.append(t)
    # remover duplicados
    return sorted(list(set(found)))


def _extra_feeds() -> List[str]:
    raw = os.getenv("EXTRA_FEEDS", "")
    return [f.strip() for f in raw.split(",") if f.strip()]


def _parse_feed(url: str):
    if "sec.gov" in url:
        user_agent = os.getenv("SEC_USER_AGENT", "tp-final-ri-unlu/1.0 contacto@ejemplo.com")
        return feedparser.parse(url, request_headers={"User-Agent": user_agent})
    return feedparser.parse(url)


def ingest_rss(feeds: List[str] | None = None) -> dict:
    feeds = feeds or DEFAULT_FEEDS
    feeds = [*feeds, *_extra_feeds()]
    portfolio = _get_portfolio_tickers()
    docs = []
    for feed in feeds:
        parsed = _parse_feed(feed)
        for entry in parsed.entries:
            url = getattr(entry, "link", None) or getattr(entry, "id", None) or ""
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            text = f"{title}\n\n{summary}".strip()
            tickers = _detect_tickers(text, portfolio)
            if not tickers:
                continue  # sólo indexamos si menciona algún ticker del portfolio
            docs.append(
                {
                    "source": _extract_source(url),
                    "url": url,
                    "title": title,
                    "text": summary or title,
                    "timestamp": _entry_timestamp(entry),
                    "tickers": tickers,
                }
            )
    if docs:
        tool_upsert_docs(docs)
    return {"feeds": len(feeds), "docs_indexed": len(docs)}


def ingest_yahoo_finance_by_ticker() -> dict:
    """Consulta titulares RSS de Yahoo Finance por cada ticker del portfolio.
    Nota: algunos feeds pueden fallar; se continúa best-effort.
    """
    portfolio = _get_portfolio_tickers()
    docs = []
    for t in portfolio:
        feed_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US"
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            url = getattr(entry, "link", None) or getattr(entry, "id", None) or ""
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            text = f"{title}\n\n{summary}".strip()
            docs.append(
                {
                    "source": _extract_source(url),
                    "url": url,
                    "title": title,
                    "text": summary or title,
                    "timestamp": _entry_timestamp(entry),
                    "tickers": [t],
                }
            )
    if docs:
        tool_upsert_docs(docs)
    return {"tickers": len(portfolio), "docs_indexed": len(docs)}


def _gdelt_query_for_portfolio(tickers: List[str]) -> str | None:
    if not tickers:
        return None
    return " OR ".join([t for t in tickers])


def _parse_gdelt_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # Example: 20250205T171516Z
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def ingest_gdelt_docs(query: str | None = None) -> dict:
    if os.getenv("GDELT_ENABLED", "0").lower() not in {"1", "true", "yes"}:
        return {"docs_indexed": 0, "reason": "disabled"}

    portfolio = _get_portfolio_tickers()
    query = query or _gdelt_query_for_portfolio(portfolio)
    if not query:
        return {"docs_indexed": 0, "reason": "no_query"}

    url = os.getenv("GDELT_DOC_API_URL", "https://api.gdeltproject.org/api/v2/doc/doc")
    mode = os.getenv("GDELT_MODE", "ArtList")
    maxrecords = int(os.getenv("GDELT_MAXRECORDS", "50"))
    params = {
        "query": query,
        "mode": mode,
        "format": "json",
        "maxrecords": maxrecords,
    }

    try:
        import requests

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {"docs_indexed": 0, "reason": "request_failed"}

    docs = []
    for item in data.get("articles", []):
        title = item.get("title", "")
        url_item = item.get("url", "")
        source = item.get("domain") or _extract_source(url_item)
        timestamp = _parse_gdelt_date(item.get("seendate"))
        text = title
        tickers = _detect_tickers(title, portfolio)
        if not tickers:
            continue
        docs.append(
            {
                "source": source,
                "url": url_item,
                "title": title,
                "text": text,
                "timestamp": timestamp,
                "tickers": tickers,
            }
        )
    if docs:
        tool_upsert_docs(docs)
    return {"docs_indexed": len(docs), "query": query}


def fetch_prices(tickers: List[str]) -> List[Tuple[str, float, float]]:
    """Obtiene precio de cierre actual y anterior para cada ticker.
    Devuelve lista de (ticker, close_prev, close_last).
    """
    results: List[Tuple[str, float, float]] = []
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="5d")
            if hist is None or hist.empty or len(hist["Close"]) < 2:
                continue
            close_prev = float(hist["Close"].iloc[-2])
            close_last = float(hist["Close"].iloc[-1])
            results.append((t, close_prev, close_last))
        except Exception:
            continue
    return results
