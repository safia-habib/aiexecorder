"""Unit tests for ingestion — no external services required."""
from ingestion.chunker import LONG_FIELD_THRESHOLD, chunk_state_record
from ingestion.ingest import EXPECTED_COLUMNS, normalize_state_code


def _row(**overrides) -> dict:
    base = {
        "State": "California",
        "state_code": "CA",
        "Executive Order (Name/Number)": "EO N-12-23",
        "Date Issued": "2023-09-06",
        "Governor": "Gavin Newsom",
        "Main Topics Covered": "AI governance and transparency",
        "Top Items for AI Workloads": "Model explainability",
        "Dynatrace Features for Compliance": "Distributed tracing, log analytics",
        "Bindplane Features for Compliance": "Log collection and routing",
        "Arize Features for Compliance": "Model monitoring and drift detection",
    }
    base.update(overrides)
    return base


# ── schema ──────────────────────────────────────────────────────────────────

def test_expected_columns_complete():
    assert len(EXPECTED_COLUMNS) == 9
    for col in [
        "State",
        "Dynatrace Features for Compliance",
        "Bindplane Features for Compliance",
        "Arize Features for Compliance",
    ]:
        assert col in EXPECTED_COLUMNS


# ── chunker ─────────────────────────────────────────────────────────────────

def test_chunk_produces_full_record():
    chunks = chunk_state_record(_row())
    full = [c for c in chunks if c.chunk_type == "full_record"]
    assert len(full) == 1
    assert "California" in full[0].text
    assert "EO N-12-23" in full[0].text


def test_short_fields_no_extra_chunks():
    chunks = chunk_state_record(_row())
    assert len(chunks) == 1, "Short fields should produce only the full_record chunk"


def test_long_field_produces_extra_chunk():
    long_val = "x" * (LONG_FIELD_THRESHOLD + 1)
    chunks = chunk_state_record(_row(**{"Main Topics Covered": long_val}))
    field_chunks = [c for c in chunks if c.chunk_type == "field"]
    assert len(field_chunks) >= 1
    assert long_val in field_chunks[0].text


def test_full_record_contains_all_sections():
    chunks = chunk_state_record(_row())
    text = chunks[0].text
    for label in [
        "Dynatrace Features",
        "Bindplane Features",
        "Arize Features",
        "Main Topics",
    ]:
        assert label in text, f"Full record chunk should contain '{label}'"


# ── state code normalisation ─────────────────────────────────────────────────

def test_normalize_known_states():
    assert normalize_state_code("California") == "CA"
    assert normalize_state_code("New York") == "NY"
    assert normalize_state_code("Texas") == "TX"
    assert normalize_state_code("Washington") == "WA"


def test_normalize_strips_whitespace():
    assert normalize_state_code("  California  ") == "CA"


def test_normalize_unknown_returns_none():
    assert normalize_state_code("Narnia") is None
    assert normalize_state_code("") is None
