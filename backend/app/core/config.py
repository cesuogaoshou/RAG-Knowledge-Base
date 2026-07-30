from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_title: str = "RAG Knowledge Base API"
    app_version: str = "0.1.0"

    upload_dir: Path = Field(default=BACKEND_DIR / "data" / "uploads", alias="RAG_UPLOAD_DIR")
    vector_store_dir: Path = Field(default=BACKEND_DIR / "data" / "chroma_db", alias="RAG_VECTOR_STORE_DIR")
    metadata_store_path: Path = Field(default=BACKEND_DIR / "data" / "documents.json", alias="RAG_METADATA_STORE_PATH")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"],
        alias="RAG_CORS_ORIGINS",
    )
    cors_methods: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["GET", "POST", "DELETE", "OPTIONS"],
        alias="RAG_CORS_METHODS",
    )

    chunk_size: int = Field(default=800, alias="RAG_CHUNK_SIZE", ge=1)
    chunk_overlap: int = Field(default=120, alias="RAG_CHUNK_OVERLAP", ge=0)
    default_top_k: int = Field(default=5, alias="RAG_DEFAULT_TOP_K", ge=1, le=20)
    min_relevance_score: float = Field(default=0.5, alias="RAG_MIN_RELEVANCE_SCORE", ge=0.0)

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/chat/completions",
        alias="DEEPSEEK_BASE_URL",
    )
    deepseek_timeout_seconds: float = Field(default=30.0, alias="DEEPSEEK_TIMEOUT_SECONDS", gt=0.0)

    @field_validator("cors_origins", "cors_methods", mode="before")
    @classmethod
    def _split_comma_separated_values(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
