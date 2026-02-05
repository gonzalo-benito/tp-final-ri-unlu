import os
import hashlib
from uuid import uuid4
from meilisearch import Client

MEILI_HOST = os.getenv("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_API_KEY = os.getenv("MEILI_API_KEY", "")
INDEX_NAME = os.getenv("MEILI_INDEX", "docs")

_client = None
_index = None

def meili_ready() -> bool:
    global _client, _index
    try:
        if _client is None:
            _client = Client(MEILI_HOST, MEILI_API_KEY if MEILI_API_KEY else None)
        # ensure index exists
        if _index is None:
            try:
                _index = _client.get_index(INDEX_NAME)
            except Exception:
                _index = _client.create_index(INDEX_NAME, {"primaryKey": "id"})
        return True
    except Exception:
        return False

def index_documents(docs: list[dict]) -> dict:
    """docs items should include at least: id, title, text, source, timestamp, tickers"""
    meili_ready()
    for d in docs:
        # ensure id present (derive from url/title)
        if not d.get("id"):
            base = d.get("url") or d.get("title") or str(uuid4())
            d["id"] = hashlib.sha1(base.encode("utf-8")).hexdigest()
        # explode tickers for filtering
        if isinstance(d.get("tickers"), str):
            d["tickers"] = [t.strip().upper() for t in d["tickers"].split(",") if t.strip()]
    task = _index.add_documents(docs)
    return {"task": task}

def search_sparse(q: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
    meili_ready()
    filter_expr = []
    if filters:
        if "ticker" in filters:
            filter_expr.append(f"tickers = {filters['ticker'].upper()}")
        if "source" in filters:
            filter_expr.append(f"source = '{filters['source']}'")
        # since can be used client-side to post-filter by timestamp
    options = {"limit": limit}
    if filter_expr:
        options["filter"] = filter_expr
    res = _index.search(q, options)
    hits = res.get("hits", [])
    return hits
