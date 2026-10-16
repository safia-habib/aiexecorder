"""Central tracer factory and OpenInference semantic-convention re-exports.

Import get_tracer() and the semconv symbols from here so every RAG module
uses a consistent tracer name and a single import point for attribute keys.

If the openinference-semantic-conventions package is not installed the stubs
below supply the correct string values so spans are still correctly attributed
and the app starts without error.
"""

from opentelemetry import trace

_TRACER_NAME = "state-ai-eo-explorer"


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(_TRACER_NAME)


try:
    from openinference.semconv.trace import (  # type: ignore[import]
        DocumentAttributes,
        EmbeddingAttributes,
        MessageAttributes,
        OpenInferenceSpanKindValues,
        SpanAttributes,
    )
except ImportError:
    # Fallback string constants matching the OpenInference semantic convention
    # spec — attribute keys are identical so spans are still correctly tagged.
    class SpanAttributes:  # type: ignore[no-redef]
        OPENINFERENCE_SPAN_KIND = "openinference.span.kind"
        INPUT_VALUE = "input.value"
        OUTPUT_VALUE = "output.value"
        LLM_MODEL_NAME = "llm.model_name"
        LLM_INPUT_MESSAGES = "llm.input_messages"
        LLM_OUTPUT_MESSAGES = "llm.output_messages"
        EMBEDDING_MODEL_NAME = "embedding.model_name"
        EMBEDDING_EMBEDDINGS = "embedding.embeddings"
        RETRIEVAL_DOCUMENTS = "retrieval.documents"

    class MessageAttributes:  # type: ignore[no-redef]
        MESSAGE_ROLE = "message.role"
        MESSAGE_CONTENT = "message.content"

    class DocumentAttributes:  # type: ignore[no-redef]
        DOCUMENT_CONTENT = "document.content"
        DOCUMENT_METADATA = "document.metadata"

    class EmbeddingAttributes:  # type: ignore[no-redef]
        EMBEDDING_TEXT = "embedding.text"
        EMBEDDING_VECTOR = "embedding.vector"

    class _SpanKindValue:
        def __init__(self, v: str) -> None:
            self.value = v

    class OpenInferenceSpanKindValues:  # type: ignore[no-redef]
        CHAIN = _SpanKindValue("CHAIN")
        LLM = _SpanKindValue("LLM")
        RETRIEVER = _SpanKindValue("RETRIEVER")
        EMBEDDING = _SpanKindValue("EMBEDDING")


__all__ = [
    "get_tracer",
    "DocumentAttributes",
    "EmbeddingAttributes",
    "MessageAttributes",
    "OpenInferenceSpanKindValues",
    "SpanAttributes",
]
