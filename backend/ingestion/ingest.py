#!/usr/bin/env python3
"""
Ingestion script: reads state_ai_eo_source.xlsx → chunks → embeds → upserts to Qdrant.

Usage (from the repo root):
    cd backend
    python -m ingestion.ingest [--data-path ../data/state_ai_eo_source.xlsx] [--recreate]

Options:
    --data-path   Path to the source spreadsheet (default: ../data/state_ai_eo_source.xlsx)
    --recreate    Drop and recreate the Qdrant collection before ingesting
"""
import argparse
import sys
import uuid
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from ingestion.chunker import chunk_state_record
from rag.embedder import embed
from states_registry import STATE_CODES

EXPECTED_COLUMNS = [
    "State",
    "Executive Order (Name/Number)",
    "Date Issued",
    "Governor",
    "Main Topics Covered",
    "Top Items for AI Workloads",
    "Dynatrace Features for Compliance",
    "Bindplane Features for Compliance",
    "Arize Features for Compliance",
]


def normalize_state_code(state_name: str) -> str | None:
    if not state_name:
        return None
    return STATE_CODES.get(state_name.strip())


def _fmt_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value) if value else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest state AI EO spreadsheet into Qdrant.")
    parser.add_argument("--data-path", default="../data/state_ai_eo_source.xlsx")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting.",
    )
    args = parser.parse_args()

    print(f"Reading {args.data_path} …")
    df = pd.read_excel(args.data_path)

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Spreadsheet is missing expected columns: {missing_cols}")

    df["state_code"] = df["State"].map(normalize_state_code)
    unresolved = df[df["state_code"].isna()]["State"].tolist()
    if unresolved:
        print(f"WARNING: Could not resolve state codes for {unresolved} — skipping these rows.")
    df = df[df["state_code"].notna()].copy()
    print(f"Loaded {len(df)} row(s) with recognised state names.")

    client = QdrantClient(url=settings.qdrant_url)

    print("Probing embedding dimension …")
    sample_vec = embed("state AI executive order compliance")
    dim = len(sample_vec)
    print(f"  Dimension: {dim}")

    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing and args.recreate:
        client.delete_collection(settings.qdrant_collection)
        print(f"Dropped collection '{settings.qdrant_collection}'.")
        existing.discard(settings.qdrant_collection)

    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"Created collection '{settings.qdrant_collection}'.")
    else:
        print(f"Collection '{settings.qdrant_collection}' exists — upserting into it.")

    points: list[PointStruct] = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        chunks = chunk_state_record(row_dict)
        for chunk in chunks:
            vec = embed(chunk.text)
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={
                        "state": chunk.state,
                        "state_code": chunk.state_code,
                        "chunk_type": chunk.chunk_type,
                        "text": chunk.text,
                        "eo_name": str(row_dict.get("Executive Order (Name/Number)", "")),
                        "date_issued": _fmt_date(row_dict.get("Date Issued")),
                        "governor": str(row_dict.get("Governor", "")),
                        "main_topics": str(row_dict.get("Main Topics Covered", "")),
                        "top_items": str(row_dict.get("Top Items for AI Workloads", "")),
                        "dynatrace_features": str(row_dict.get("Dynatrace Features for Compliance", "")),
                        "bindplane_features": str(row_dict.get("Bindplane Features for Compliance", "")),
                        "arize_features": str(row_dict.get("Arize Features for Compliance", "")),
                    },
                )
            )
        print(f"  [{row_dict['state_code']}] {row_dict['State']} → {len(chunks)} chunk(s)")

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    print(f"\nDone. Ingested {len(df)} state(s), {len(points)} total chunk(s) into Qdrant.")


if __name__ == "__main__":
    main()
