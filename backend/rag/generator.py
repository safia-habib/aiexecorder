import json
from typing import Generator

import httpx
from opentelemetry.trace import SpanKind

from config import settings
from rag.tracing import (
    MessageAttributes,
    OpenInferenceSpanKindValues,
    SpanAttributes,
    get_tracer,
)

SYSTEM_PROMPT = (
    "You are an expert on state AI executive orders and compliance technology. "
    "Answer the user's question based ONLY on the provided context about the state's executive order. "
    "If the context does not contain enough information to answer, say so clearly. "
    "Do not invent policy details not present in the context."
)


def generate_stream(context: str, question: str) -> Generator[str, None, None]:
    prompt = (
        f"Context about the state's AI executive order:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer based strictly on the above context:"
    )

    with get_tracer().start_as_current_span("llm_generate", kind=SpanKind.CLIENT) as span:
        if span.is_recording():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            span.set_attribute(SpanAttributes.LLM_MODEL_NAME, settings.llm_model)
            span.set_attribute(SpanAttributes.INPUT_VALUE, question)
            # System message
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_ROLE}", "system")
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_CONTENT}", SYSTEM_PROMPT)
            # User message (includes full RAG context)
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.1.{MessageAttributes.MESSAGE_ROLE}", "user")
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.1.{MessageAttributes.MESSAGE_CONTENT}", prompt)

        tokens: list[str] = []

        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if not data.get("done"):
                            token = data.get("response", "")
                            if token:
                                tokens.append(token)
                                yield token

        if span.is_recording():
            full_answer = "".join(tokens)
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, full_answer)
            span.set_attribute(f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_ROLE}", "assistant")
            span.set_attribute(f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_CONTENT}", full_answer)
