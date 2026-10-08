from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from config import settings
from rag.embedder import embed

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def retrieve(state_code: str, question: str, top_k: int = 3) -> list[str]:
    query_vec = embed(question)
    results = get_client().search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vec,
        query_filter=Filter(
            must=[FieldCondition(key="state_code", match=MatchValue(value=state_code.upper()))]
        ),
        limit=top_k,
    )
    return [r.payload["text"] for r in results]
