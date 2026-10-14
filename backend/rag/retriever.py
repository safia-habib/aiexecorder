import json

from opentelemetry.trace import SpanKind
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from config import settings
from rag.embedder import embed
from rag.tracing import (
    DocumentAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
    get_tracer,
)

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def retrieve(state_code: str, question: str, top_k: int = 3) -> list[str]:
    with get_tracer().start_as_current_span("retrieve", kind=SpanKind.CLIENT) as span:
        if span.is_recording():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.RETRIEVER.value)
            span.set_attribute(SpanAttributes.INPUT_VALUE, question)
            span.set_attribute("retriever.state_code", state_code.upper())
            span.set_attribute("retriever.top_k", top_k)
            span.set_attribute("retriever.collection", settings.qdrant_collection)

        query_vec = embed(question)
        results = get_client().search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vec,
            query_filter=Filter(
                must=[FieldCondition(key="state_code", match=MatchValue(value=state_code.upper()))]
            ),
            limit=top_k,
        )

        texts = [r.payload["text"] for r in results]

        if span.is_recording():
            for i, (result, text) in enumerate(zip(results, texts)):
                prefix = f"{SpanAttributes.RETRIEVAL_DOCUMENTS}.{i}"
                span.set_attribute(f"{prefix}.{DocumentAttributes.DOCUMENT_CONTENT}", text)
                span.set_attribute(
                    f"{prefix}.{DocumentAttributes.DOCUMENT_METADATA}",
                    json.dumps({
                        "state_code": result.payload.get("state_code"),
                        "chunk_type": result.payload.get("chunk_type"),
                        "score": result.score,
                    }),
                )
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(texts))

        return texts
