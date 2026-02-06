from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Field(default=Path("./data"))
    model_path: Path | None = Field(default=Path("/mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf"))
    llm_backend: str = Field(default="local", description="local|openai")
    openai_model: str = Field(default="text-embedding-3-small")
    openai_api_key: str | None = None

    chroma_path: Path = Field(default=Path("./data/vectordb"))
    collection_name: str = Field(default="annotations")

    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)
    top_k: int = Field(default=5)

    queue_backend: str = Field(default="kafka", description="kafka|sqs|none")
    kafka_bootstrap: str = Field(default="localhost:9092")
    kafka_topic: str = Field(default="annotations")

    sqs_queue_url: str | None = None
    aws_region: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = "RAG_"


settings = Settings()
