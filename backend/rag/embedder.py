from openai import AzureOpenAI
from opentelemetry.trace import SpanKind

from config import settings
from rag.tracing import (
    EmbeddingAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
    get_tracer,
)

_client: AzureOpenAI | None = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    return _client


def embed(text: str) -> list[float]:
    with get_tracer().start_as_current_span("embed", kind=SpanKind.CLIENT) as span:
        if span.is_recording():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.EMBEDDING.value)
            span.set_attribute(SpanAttributes.INPUT_VALUE, text)
            span.set_attribute(SpanAttributes.EMBEDDING_MODEL_NAME, settings.azure_openai_embedding_deployment)

        response = _get_client().embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=text,
        )
        vector = response.data[0].embedding

        if span.is_recording():
            span.set_attribute(
                f"{SpanAttributes.EMBEDDING_EMBEDDINGS}.0.{EmbeddingAttributes.EMBEDDING_TEXT}",
                text,
            )
            span.set_attribute(
                f"{SpanAttributes.EMBEDDING_EMBEDDINGS}.0.embedding.dimensions",
                len(vector),
            )

        return vector
