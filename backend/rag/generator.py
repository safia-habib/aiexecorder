from typing import Generator

from openai import AzureOpenAI
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


def generate_stream(context: str, question: str) -> Generator[str, None, None]:
    user_message = (
        f"Context about the state's AI executive order:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer based strictly on the above context:"
    )

    with get_tracer().start_as_current_span("llm_generate", kind=SpanKind.CLIENT) as span:
        if span.is_recording():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)
            span.set_attribute(SpanAttributes.LLM_MODEL_NAME, settings.azure_openai_deployment)
            span.set_attribute(SpanAttributes.INPUT_VALUE, question)
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_ROLE}", "system")
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_CONTENT}", SYSTEM_PROMPT)
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.1.{MessageAttributes.MESSAGE_ROLE}", "user")
            span.set_attribute(f"{SpanAttributes.LLM_INPUT_MESSAGES}.1.{MessageAttributes.MESSAGE_CONTENT}", user_message)

        tokens: list[str] = []

        stream = _get_client().chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                tokens.append(token)
                yield token

        if span.is_recording():
            full_answer = "".join(tokens)
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, full_answer)
            span.set_attribute(f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_ROLE}", "assistant")
            span.set_attribute(f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_CONTENT}", full_answer)
