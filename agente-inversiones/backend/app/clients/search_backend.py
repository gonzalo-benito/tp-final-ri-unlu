import os

from .meilisearch_client import meili_ready, search_sparse as meili_search, index_documents as meili_index
from .terrier_client import terrier_ready, search_sparse as terrier_search, index_documents as terrier_index


class SearchBackend:
    name: str = "base"
    supports_indexing: bool = False

    def ready(self) -> bool:
        return False

    def search_sparse(self, q: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
        raise NotImplementedError

    def index_documents(self, docs: list[dict]) -> dict:
        return {"status": "skipped"}


class MeilisearchBackend(SearchBackend):
    name = "meilisearch"
    supports_indexing = True

    def ready(self) -> bool:
        return meili_ready()

    def search_sparse(self, q: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
        return meili_search(q, filters=filters, limit=limit)

    def index_documents(self, docs: list[dict]) -> dict:
        return meili_index(docs)


class TerrierBackend(SearchBackend):
    name = "terrier"
    supports_indexing = False

    def ready(self) -> bool:
        return terrier_ready()

    def search_sparse(self, q: str, filters: dict | None = None, limit: int = 10) -> list[dict]:
        return terrier_search(q, filters=filters, limit=limit)

    def index_documents(self, docs: list[dict]) -> dict:
        return terrier_index(docs)


_BACKEND = None


def get_search_backend() -> SearchBackend:
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    name = os.getenv("SEARCH_BACKEND", "terrier").lower().strip()
    if name == "terrier":
        _BACKEND = TerrierBackend()
    else:
        _BACKEND = MeilisearchBackend()
    return _BACKEND