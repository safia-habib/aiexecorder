from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "state_eo"

    # Azure OpenAI — used for both embeddings and chat completions
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # OpenTelemetry / OpenInference — all three must be set to enable export
    otlp_endpoint: str = ""
    # Comma-separated key=value pairs, e.g. "Authorization=Api-Token dt0c01.xxx"
    # For Arize Phoenix: "api_key=<key>,space_id=<id>"
    otlp_headers: str = ""
    otlp_service_name: str = "state-ai-eo-explorer"

    model_config = {"env_file": ".env"}


settings = Settings()
