from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "state_eo"
    embed_model: str = "nomic-embed-text"
    llm_model: str = "llama3.1:8b"
    otlp_endpoint: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
