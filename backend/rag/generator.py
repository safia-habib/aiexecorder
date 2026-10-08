import json
from typing import Generator

import httpx

from config import settings

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
                            yield token
