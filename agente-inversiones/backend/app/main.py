from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db, get_conn
from .models import PortfolioItem, Digest, DocItem
import os
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_W_SENT = float(os.getenv("W_SENT", "0.5"))
DEFAULT_W_RECENCY = float(os.getenv("W_RECENCY", "0.3"))
DEFAULT_W_AUTH = float(os.getenv("W_AUTH", "0.2"))

def _configure_logging() -> None:
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"
    handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.setLevel(logging.INFO)
        root.addHandler(handler)

app = FastAPI(title="Agente de Inversiones - Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_configure_logging()
init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

# Portfolio endpoints
@app.get("/portfolio")
def list_portfolio():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, quantity, entry_price, entry_date FROM portfolio ORDER BY id")
    items = [
        {"id": r[0], "ticker": r[1], "quantity": r[2], "entry_price": r[3], "entry_date": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return items

@app.post("/portfolio")
def add_portfolio(item: PortfolioItem):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO portfolio (ticker, quantity, entry_price, entry_date) VALUES (?,?,?,?)",
        (item.ticker.upper(), item.quantity, item.entry_price, item.entry_date),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    backend = get_search_backend()
    if backend.name == "terrier":
        try:
            reindex = build_index(_default_db_path(), _default_index_path(), overwrite=True)
            logger.info("Terrier reindex after portfolio add: %s", reindex)
        except Exception as exc:
            logger.exception("Terrier reindex failed after portfolio add: %s", exc)
    return {"id": new_id}

@app.delete("/portfolio/{item_id}")
def delete_portfolio(item_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM portfolio WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"deleted": item_id}

# Digests (LLM summaries) endpoints
@app.get("/digests/{ticker}/{date}")
def get_digest(ticker: str, date: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, ticker, date, content FROM digests WHERE ticker=? AND date=?",
        (ticker.upper(), date),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Digest not found")
    return {"id": row[0], "ticker": row[1], "date": row[2], "content": row[3]}

@app.post("/digests")
def upsert_digest(d: Digest):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO digests (ticker, date, content) VALUES (?,?,?) ON CONFLICT(ticker, date) DO UPDATE SET content=excluded.content",
        (d.ticker.upper(), d.date, d.content),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

# Docs (news/posts) endpoints
@app.post("/docs")
def add_docs(items: list[DocItem]):
    conn = get_conn()
    cur = conn.cursor()
    for it in items:
        cur.execute(
            "INSERT OR IGNORE INTO docs (source, url, title, text, timestamp, tickers) VALUES (?,?,?,?,?,?)",
            (it.source, it.url, it.title, it.text, it.timestamp, ",".join([t.upper() for t in it.tickers])),
        )
    conn.commit()
    conn.close()
    return {"inserted": len(items)}

@app.get("/alerts")
def list_alerts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, type, score, created_at FROM alerts ORDER BY created_at DESC LIMIT 100")
    items = [
        {"id": r[0], "ticker": r[1], "type": r[2], "score": r[3], "created_at": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()
    return items

# Search: backend configurable (Meilisearch/Terrier)
from .clients.search_backend import get_search_backend
from .ingestion import ingest_rss, ingest_yahoo_finance_by_ticker, ingest_gdelt_docs
from .terrier_index import build_index, _default_db_path, _default_index_path
from .alerts import run_price_drop_alerts
from .signals import run_news_signals, run_volume_signals, aggregate_recommendation_for_ticker
from .ranking import hybrid_score

@app.get("/search")
def search(
    q: str,
    ticker: str | None = None,
    since: str | None = None,
    source: str | None = None,
    limit: int = 10,
    w_sent: float = DEFAULT_W_SENT,
    w_recency: float = DEFAULT_W_RECENCY,
    w_auth: float = DEFAULT_W_AUTH,
):
    backend = get_search_backend()
    if not backend.ready():
        logger.error("Search backend '%s' not available", backend.name)
        raise HTTPException(status_code=503, detail=f"Search backend '{backend.name}' not available")
    filters = {}
    if ticker:
        filters["ticker"] = ticker.upper()
    if since:
        filters["since"] = since
    if source:
        filters["source"] = source
    results = backend.search_sparse(q, filters=filters, limit=limit)
    # Re-ranking híbrido usando peso posicional como proxy de BM25
    rescored = []
    for idx, hit in enumerate(results):
        bm25_pos_weight = max(0.5, 1.0 - 0.05 * idx)
        score, details = hybrid_score(
            title=hit.get("title", ""),
            text=hit.get("text", ""),
            source=hit.get("source", ""),
            url=hit.get("url", ""),
            timestamp=hit.get("timestamp", ""),
            bm25_pos_weight=bm25_pos_weight,
            w_sent=w_sent,
            w_recency=w_recency,
            w_auth=w_auth,
        )
        h = dict(hit)
        h["score"] = score
        h["score_details"] = details
        h["rank_pos"] = idx + 1
        rescored.append(h)
    rescored.sort(key=lambda x: x["score"], reverse=True)
    return {"q": q, "filters": filters, "results": rescored}


# Ingesta: ejecutar fetch de RSS y Yahoo Finance por ticker
@app.post("/ingest/news")
def ingest_news():
    backend = get_search_backend()
    if backend.supports_indexing and not backend.ready():
        logger.error("Search backend '%s' not available for ingest", backend.name)
        raise HTTPException(status_code=503, detail=f"Search backend '{backend.name}' not available")
    r1 = ingest_rss()
    r2 = ingest_yahoo_finance_by_ticker()
    r3 = ingest_gdelt_docs()
    reindex = None
    if backend.name == "terrier":
        try:
            reindex = build_index(_default_db_path(), _default_index_path(), overwrite=True)
            logger.info("Terrier reindex after ingest: %s", reindex)
        except Exception as exc:
            logger.exception("Terrier reindex failed after ingest: %s", exc)
    logger.info("Ingested news rss=%s yahoo=%s gdelt=%s", r1, r2, r3)
    return {"rss": r1, "yahoo": r2, "gdelt": r3, "reindex": reindex}


# Ingesta de precios y generación de alertas por caída porcentual
@app.post("/ingest/prices")
def ingest_prices(threshold: float = 3.0):
    res = run_price_drop_alerts(threshold_pct=threshold)
    return {"threshold_pct": threshold, **res}


# Ejecutar chequeo de alertas (alias)
@app.post("/alerts/run")
def alerts_run(threshold: float = 3.0):
    res = run_price_drop_alerts(threshold_pct=threshold)
    return {"threshold_pct": threshold, **res}


# Señales preventivas desde noticias
@app.post("/signals/run/news")
def signals_run_news(threshold: float = 0.6, window_hours: float = 72.0):
    res = run_news_signals(sentiment_threshold=threshold, window_hours=window_hours)
    return {"threshold": threshold, "window_hours": window_hours, **res}


@app.get("/signals")
def list_signals(ticker: str | None = None, limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    if ticker:
        cur.execute(
            "SELECT id, ticker, type, score, direction, doc_url, details, created_at FROM signals WHERE ticker=? ORDER BY created_at DESC LIMIT ?",
            (ticker.upper(), limit),
        )
    else:
        cur.execute(
            "SELECT id, ticker, type, score, direction, doc_url, details, created_at FROM signals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "ticker": r[1],
            "type": r[2],
            "score": r[3],
            "direction": r[4],
            "doc_url": r[5],
            "details": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]

# Señales de volumen
@app.post("/signals/run/volume")
def signals_run_volume(avg_days: int = 20, multiplier: float = 2.0):
    res = run_volume_signals(avg_days=avg_days, multiplier=multiplier)
    return {"avg_days": avg_days, "multiplier": multiplier, **res}


# Recomendación agregada por ticker
@app.get("/recommendation/{ticker}")
def recommendation(ticker: str, window_hours: float = 72.0):
    res = aggregate_recommendation_for_ticker(ticker, window_hours=window_hours)
    return res
