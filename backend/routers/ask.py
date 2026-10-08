import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag.generator import generate_stream
from rag.retriever import retrieve
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

    chunks = retrieve(code, req.question)

    if not chunks:
        def _empty():
            msg = (
                f"No executive order data is on file for {ALL_STATES[code]}. "
                "I cannot answer this question."
            )
            yield f"event: done\ndata: {json.dumps({'full_answer': msg})}\n\n"

        return StreamingResponse(_empty(), media_type="text/event-stream")

    context = "\n\n---\n\n".join(chunks)

    def _stream():
        full: list[str] = []
        for token in generate_stream(context, req.question):
            full.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        yield f"event: done\ndata: {json.dumps({'full_answer': ''.join(full)})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
