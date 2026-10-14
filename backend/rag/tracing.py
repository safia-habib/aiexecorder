"""Central tracer factory and OpenInference semantic-convention re-exports.

Import get_tracer() and the semconv symbols from here so every RAG module
uses a consistent tracer name and a single import point for attribute keys.
"""

from opentelemetry import trace

from openinference.semconv.trace import (
    DocumentAttributes,
    EmbeddingAttributes,
    MessageAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
)

_TRACER_NAME = "state-ai-eo-explorer"


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(_TRACER_NAME)


__all__ = [
    "get_tracer",
    "DocumentAttributes",
    "EmbeddingAttributes",
    "MessageAttributes",
    "OpenInferenceSpanKindValues",
    "SpanAttributes",
]
