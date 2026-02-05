import os
import sqlite3
from pathlib import Path

from ..db import DB_PATH


def _get_pyterrier():
    try:
        import pyterrier as pt

        if not pt.started():
            pt.init()
        return pt
    except Exception:
        return None


def _index_path() -> str | None:
    env_path = os.getenv("TERRIER_INDEX")
    if env_path:
        return env_path
    default_path = Path(__file__).resolve().parents[2] / "data" / "terrier_index"
    return str(default_path)


def terrier_ready() -> bool:
    pt = _get_pyterrier()
    if not pt:
        return False
    index_path = _index_path()
    if not index_path:
        return False
    if not Path(index_path).exists():
        return False
    try:
        pt.IndexFactory.of(index_path)
        return True
    except Exception:
        return False


def _fetch_docs(doc_ids: list[str]) -> dict[str, dict]:
    if not doc_ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(doc_ids))
    query = (
        "SELECT id, source, url, title, text, timestamp, tickers "
        "FROM docs WHERE id IN (" + placeholders + ")"
    )
    rows = cur.execute(query, doc_ids).fetchall()
    conn.close()
    return {
        str(r[0]): {
            "id": r[0],
            "source": r[1],
            "url": r[2],
            "title": r[3],
            "text": r[4],
            "timestamp": r[5],
            "tickers": r[6],
        }
        for r in rows
    }


def search_sparse(q: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
    if not terrier_ready():
        raise RuntimeError(
            "Terrier no está listo. Verificá TERRIER_INDEX y la instalación de pyterrier."
        )
    pt = _get_pyterrier()
    index = pt.IndexFactory.of(_index_path())
    wmodel = os.getenv("TERRIER_WMODEL", "BM25")
    retr = pt.BatchRetrieve(index, wmodel=wmodel)
    res = retr.search(q)
    if res is None or res.empty:
        return []
    df = res.sort_values(by="score", ascending=False).head(limit)
    docnos = [str(x) for x in df["docno"].tolist()]
    meta_map = _fetch_docs(docnos)
    hits: list[dict] = []
    for _, row in df.iterrows():
        docno = str(row["docno"])
        meta = meta_map.get(docno, {"id": int(docno) if docno.isdigit() else docno})
        hit = {
            **meta,
            "score": float(row.get("score", 0.0)),
        }
        hits.append(hit)
    if filters:
        if "ticker" in filters:
            ticker = str(filters["ticker"]).upper()
            hits = [h for h in hits if ticker in str(h.get("tickers", "")).upper()]
        if "source" in filters:
            hits = [h for h in hits if h.get("source") == filters["source"]]
    return hits[:limit]


def index_documents(_: list[dict]) -> dict:
    return {
        "status": "skipped",
        "reason": "Terrier requiere indexación offline; use un pipeline de indexación separado.",
    }