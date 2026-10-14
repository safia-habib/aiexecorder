from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "state_eo"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "llama3.1:8b"

    # OpenTelemetry / OpenInference — all three must be set to enable export
    otlp_endpoint: str = ""
    # Comma-separated key=value pairs, e.g. "Authorization=Api-Token dt0c01.xxx"
    # For Arize Phoenix: "api_key=<key>,space_id=<id>"
    otlp_headers: str = ""
    otlp_service_name: str = "state-ai-eo-explorer"

    model_config = {"env_file": ".env"}


settings = Settings()
