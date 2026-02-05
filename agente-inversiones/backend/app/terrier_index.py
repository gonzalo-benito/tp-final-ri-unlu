import argparse
import sqlite3
import shutil
from pathlib import Path


def _default_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "app.db"


def _default_index_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "terrier_index"


def _build_docs(rows: list[tuple]) -> list[dict]:
    docs: list[dict] = []
    for row in rows:
        doc_id, title, text, url, source, timestamp, tickers = row
        title = title or ""
        text = text or ""
        combined = f"{title}\n\n{text}".strip()
        if not combined:
            continue
        docs.append(
            {
                "docno": str(doc_id),
                "text": combined,
                "title": title,
                "url": url or "",
                "source": source or "",
                "timestamp": timestamp or "",
                "tickers": tickers or "",
            }
        )
    return docs


def build_index(db_path: Path, index_path: Path, overwrite: bool = False, limit: int | None = None) -> dict:
    try:
        import pyterrier as pt
    except Exception as exc:
        raise RuntimeError("python-terrier no está instalado") from exc

    if not pt.started():
        pt.init()

    index_path.mkdir(parents=True, exist_ok=True)
    if any(index_path.iterdir()) and not overwrite:
        return {"status": "skipped", "reason": "index_exists", "index": str(index_path)}

    if overwrite:
        shutil.rmtree(index_path, ignore_errors=True)
        index_path.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    query = "SELECT id, title, text, url, source, timestamp, tickers FROM docs ORDER BY id"
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()
    docs_iter = _build_docs(rows)

    indexer = pt.IterDictIndexer(
        str(index_path),
        meta={
            "docno": 32,
            "title": 512,
            "url": 2048,
            "source": 64,
            "timestamp": 64,
            "tickers": 256,
        },
        stemmer="porter",
        stopwords="english",
    )
    indexer.index(docs_iter)
    conn.close()
    return {"status": "ok", "index": str(index_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Construye índice Terrier desde SQLite")
    parser.add_argument("--db", default=str(_default_db_path()))
    parser.add_argument("--index", default=str(_default_index_path()))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    result = build_index(Path(args.db), Path(args.index), overwrite=args.overwrite, limit=args.limit)
    print(result)


if __name__ == "__main__":
    main()