"""Ingesta de fuentes externas: RSS y Yahoo Finance por ticker.
Normaliza documentos y los publica vía tool_upsert_docs.
"""
from typing import List, Tuple
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
    # MarketWatch Top Stories
    "https://feeds.marketwatch.com/marketwatch/topstories/",
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


def ingest_rss(feeds: List[str] | None = None) -> dict:
    feeds = feeds or DEFAULT_FEEDS
    portfolio = _get_portfolio_tickers()
    docs = []
    for feed in feeds:
        parsed = feedparser.parse(feed)
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
