import httpx
from opentelemetry.trace import SpanKind

from config import settings
from rag.tracing import (
    EmbeddingAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
    get_tracer,
)


def embed(text: str) -> list[float]:
    with get_tracer().start_as_current_span("embed", kind=SpanKind.CLIENT) as span:
        if span.is_recording():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.EMBEDDING.value)
            span.set_attribute(SpanAttributes.INPUT_VALUE, text)
            span.set_attribute(SpanAttributes.EMBEDDING_MODEL_NAME, settings.embed_model)

        resp = httpx.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.embed_model, "prompt": text},
            timeout=60.0,
        )
        resp.raise_for_status()
        vector = resp.json()["embedding"]

        if span.is_recording():
            span.set_attribute(
                f"{SpanAttributes.EMBEDDING_EMBEDDINGS}.0.{EmbeddingAttributes.EMBEDDING_TEXT}",
                text,
            )
            # Store vector dimension only — the full float array would exceed span size limits
            span.set_attribute(
                f"{SpanAttributes.EMBEDDING_EMBEDDINGS}.0.embedding.dimensions",
                len(vector),
            )

        return vector
