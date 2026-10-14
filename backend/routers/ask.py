import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from opentelemetry.trace import SpanKind
from pydantic import BaseModel

from rag.generator import generate_stream
from rag.retriever import retrieve
from rag.tracing import OpenInferenceSpanKindValues, SpanAttributes, get_tracer
from states_registry import ALL_STATES

router = APIRouter()


class AskRequest(BaseModel):
    state_code: str
    question: str


@router.post("/ask")
def ask(req: AskRequest):
    code = req.state_code.upper()
    if code not in ALL_STATES:
        raise HTTPException(status_code=400, detail=f"Unknown state code: {code}")

    def _stream():
        with get_tracer().start_as_current_span("rag_chain", kind=SpanKind.SERVER) as span:
            if span.is_recording():
                span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.CHAIN.value)
                span.set_attribute(SpanAttributes.INPUT_VALUE, req.question)
                span.set_attribute("chain.state_code", code)
                span.set_attribute("chain.state_name", ALL_STATES[code])

            chunks = retrieve(code, req.question)

            if not chunks:
                msg = (
                    f"No executive order data is on file for {ALL_STATES[code]}. "
                    "I cannot answer this question."
                )
                if span.is_recording():
                    span.set_attribute(SpanAttributes.OUTPUT_VALUE, msg)
                yield f"event: done\ndata: {json.dumps({'full_answer': msg})}\n\n"
                return

            context = "\n\n---\n\n".join(chunks)
            full: list[str] = []

            for token in generate_stream(context, req.question):
                full.append(token)
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

            full_answer = "".join(full)
            if span.is_recording():
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, full_answer)
            yield f"event: done\ndata: {json.dumps({'full_answer': full_answer})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
