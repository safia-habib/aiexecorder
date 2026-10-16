import logging

from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from config import settings
from states_registry import ALL_STATES

logger = logging.getLogger(__name__)
router = APIRouter()

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def _all_full_records() -> dict[str, dict]:
    """Fetch all full_record chunks from Qdrant.

    Returns an empty dict (rather than raising) when Qdrant is unreachable or
    the collection doesn't exist yet — e.g. before ingestion has been run.
    """
    try:
        records, _ = get_client().scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="chunk_type", match=MatchValue(value="full_record"))]
            ),
            limit=200,
            with_payload=True,
        )
        return {r.payload["state_code"]: r.payload for r in records}
    except Exception as exc:
        logger.warning("Could not fetch EO records from Qdrant: %s", exc)
        return {}


@router.get("/states")
def list_states():
    eo_map = _all_full_records()
    states = []
    for code, name in sorted(ALL_STATES.items(), key=lambda x: x[1]):
        payload = eo_map.get(code)
        if payload:
            states.append({
                "state": name,
                "state_code": code,
                "has_eo": True,
                "eo_name": payload.get("eo_name"),
                "governor": payload.get("governor"),
                "date_issued": payload.get("date_issued"),
            })
        else:
            states.append({
                "state": name,
                "state_code": code,
                "has_eo": False,
                "eo_name": None,
                "governor": None,
                "date_issued": None,
            })
    return {"states": states}


@router.get("/states/{state_code}/eo")
def get_state_eo(state_code: str):
    code = state_code.upper()
    if code not in ALL_STATES:
        raise HTTPException(status_code=404, detail=f"Unknown state code: {code}")

    try:
        records, _ = get_client().scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="state_code", match=MatchValue(value=code)),
                    FieldCondition(key="chunk_type", match=MatchValue(value="full_record")),
                ]
            ),
            limit=1,
            with_payload=True,
        )
    except Exception as exc:
        logger.warning("Could not fetch EO record for %s from Qdrant: %s", code, exc)
        return {
            "state": ALL_STATES[code],
            "state_code": code,
            "has_eo": False,
            "message": "EO data is not available right now. Qdrant may still be starting or ingestion has not been run.",
        }

    if not records:
        return {
            "state": ALL_STATES[code],
            "state_code": code,
            "has_eo": False,
            "message": f"No AI executive order on file for {ALL_STATES[code]}.",
        }

    p = records[0].payload
    return {
        "state": ALL_STATES[code],
        "state_code": code,
        "has_eo": True,
        "eo_name": p.get("eo_name"),
        "date_issued": p.get("date_issued"),
        "governor": p.get("governor"),
        "main_topics": p.get("main_topics"),
        "top_items_for_ai_workloads": p.get("top_items"),
        "dynatrace_features": p.get("dynatrace_features"),
        "bindplane_features": p.get("bindplane_features"),
        "arize_features": p.get("arize_features"),
    }
