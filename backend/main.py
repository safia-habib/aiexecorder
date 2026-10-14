import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import ask, states

app = FastAPI(title="State AI EO Explorer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(states.router, prefix="/api")
app.include_router(ask.router, prefix="/api")


@app.get("/api/health")
def health():
    ollama_ok = False
    qdrant_ok = False
    try:
        httpx.get(f"{settings.ollama_url}/api/tags", timeout=3.0).raise_for_status()
        ollama_ok = True
    except Exception:
        pass
    try:
        # Qdrant readiness endpoint
        httpx.get(f"{settings.qdrant_url}/readyz", timeout=3.0).raise_for_status()
        qdrant_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if (ollama_ok and qdrant_ok) else "degraded",
        "ollama": "reachable" if ollama_ok else "unreachable",
        "qdrant": "reachable" if qdrant_ok else "unreachable",
    }


def _parse_otlp_headers(raw: str) -> dict[str, str]:
    """Parse 'key1=value1,key2=value2' into a dict for the OTLP exporter."""
    if not raw.strip():
        return {}
    return dict(pair.split("=", 1) for pair in raw.split(",") if "=" in pair)


def _setup_otel() -> None:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.resource import ResourceAttributes

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.otlp_service_name,
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otlp_endpoint,
                headers=_parse_otlp_headers(settings.otlp_headers),
            )
        )
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


if settings.otlp_endpoint:
    _setup_otel()
