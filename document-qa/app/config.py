"""Settings loaded from environment (pydantic-settings). No secrets in code."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The pgvector column is declared as vector(1024) in migrations/001_init.sql.
# Titan Text Embeddings v2 at dimensions=1024 and the mock embedder both match it.
EMBEDDING_DIM = 1024

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPTS_DIR = PACKAGE_DIR / "prompts"
DEFAULT_MIGRATIONS_DIR = PACKAGE_DIR.parent / "migrations"


class StoreBackend(StrEnum):
    MEMORY = "memory"
    POSTGRES = "postgres"


class Provider(StrEnum):
    MOCK = "mock"
    BEDROCK = "bedrock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- backends ---
    store_backend: StoreBackend = StoreBackend.MEMORY
    llm_provider: Provider = Provider.MOCK
    embedder_provider: Provider = Provider.MOCK

    # --- postgres (DATABASE_URL is injected from a Kubernetes Secret, never from the chart) ---
    database_url: str = "postgresql://qa:qa@localhost:5432/qa"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    run_migrations: bool = True
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR

    # --- corpus governance ---
    # When false, uploaded documents stay "pending" and are invisible to /ask until approved.
    auto_approve: bool = True

    # --- input limits (documented in README, enforced with 413) ---
    max_document_bytes: int = Field(default=1_048_576, gt=0)
    max_question_bytes: int = Field(default=2048, gt=0)

    # --- chunking / retrieval ---
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)
    retrieval_top_k: int = Field(default=4, gt=0, le=50)
    # Below this cosine similarity a chunk is not trusted as evidence.
    # Calibrate per embedder: mock hashing scores and Titan v2 scores live in different ranges.
    retrieval_min_score: float = 0.05
    history_messages: int = Field(default=6, ge=0)

    # --- prompts ---
    prompts_dir: Path = DEFAULT_PROMPTS_DIR

    # --- AWS / Bedrock (unused in mock mode; credentials come from the instance profile) ---
    aws_region: str = "eu-west-1"
    bedrock_llm_model_id: str = "qwen.qwen3-32b-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    bedrock_max_tokens: int = 512
    embed_concurrency: int = Field(default=8, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
