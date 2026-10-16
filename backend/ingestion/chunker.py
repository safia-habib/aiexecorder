from dataclasses import dataclass

LONG_FIELD_THRESHOLD = 400


@dataclass
class Chunk:
    state_code: str
    state: str
    text: str
    chunk_type: str  # "full_record" | "field"


def chunk_state_record(row: dict) -> list[Chunk]:
    state = str(row["State"])
    state_code = str(row["state_code"])
    eo_name = str(row.get("Executive Order (Name/Number)", ""))

    full_text = "\n".join([
        f"State: {state}",
        f"Executive Order: {eo_name}",
        f"Date Issued: {row.get('Date Issued', '')}",
        f"Governor: {row.get('Governor', '')}",
        f"Main Topics Covered: {row.get('Main Topics Covered', '')}",
        f"Top Items for AI Workloads: {row.get('Top Items for AI Workloads', '')}",
        f"Dynatrace Features for Compliance: {row.get('Dynatrace Features for Compliance', '')}",
        f"Bindplane Features for Compliance: {row.get('Bindplane Features for Compliance', '')}",
        f"Arize Features for Compliance: {row.get('Arize Features for Compliance', '')}",
    ])

    chunks = [Chunk(state_code=state_code, state=state, text=full_text, chunk_type="full_record")]

    for field_name, label in [
        ("Main Topics Covered", "Main Topics"),
        ("Top Items for AI Workloads", "AI Workload Items"),
        ("Dynatrace Features for Compliance", "Dynatrace Features"),
        ("Bindplane Features for Compliance", "Bindplane Features"),
        ("Arize Features for Compliance", "Arize Features"),
    ]:
        value = str(row.get(field_name, ""))
        if len(value) > LONG_FIELD_THRESHOLD:
            field_text = f"State: {state}\n{label} (from EO {eo_name}):\n{value}"
            chunks.append(Chunk(state_code=state_code, state=state, text=field_text, chunk_type="field"))

    return chunks
