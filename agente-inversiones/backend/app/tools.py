"""Wrappers de herramientas para el agente (LangGraph/LangChain)."""
from .clients.search_backend import get_search_backend
from .db import get_conn


def tool_search_sparse(query: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
    backend = get_search_backend()
    return backend.search_sparse(query, filters=filters, limit=limit)


def tool_get_digest(ticker: str, date: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, content FROM digests WHERE ticker=? AND date=?", (ticker.upper(), date))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "content": row[1]}


def tool_upsert_docs(docs: list[dict]) -> dict:
    # insert into SQLite
    conn = get_conn()
    cur = conn.cursor()
    for it in docs:
        tickers = it.get("tickers", [])
        if isinstance(tickers, list):
            tickers_str = ",".join([t.upper() for t in tickers])
        else:
            tickers_str = str(tickers)
        cur.execute(
            "INSERT OR IGNORE INTO docs (source, url, title, text, timestamp, tickers) VALUES (?,?,?,?,?,?)",
            (it.get("source"), it.get("url"), it.get("title"), it.get("text"), it.get("timestamp"), tickers_str),
        )
    conn.commit()
    conn.close()
    # publish to search backend if supported
    backend = get_search_backend()
    if backend.supports_indexing:
        return backend.index_documents(docs)
    return {"status": "skipped", "reason": f"Backend '{backend.name}' no soporta indexación online."}


def tool_get_portfolio() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ticker, quantity, entry_price, entry_date FROM portfolio ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "ticker": r[1], "quantity": r[2], "entry_price": r[3], "entry_date": r[4]}
        for r in rows
    ]


def tool_set_portfolio(items: list[dict]) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM portfolio")
    for it in items:
        cur.execute(
            "INSERT INTO portfolio (ticker, quantity, entry_price, entry_date) VALUES (?,?,?,?)",
            (it["ticker"].upper(), float(it["quantity"]), float(it["entry_price"]), it["entry_date"]),
        )
    conn.commit()
    conn.close()
    return {"count": len(items)}
