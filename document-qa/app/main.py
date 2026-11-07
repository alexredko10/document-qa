"""FastAPI app factory: lifespan wiring, middleware, router registration."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.api import ask, documents, health, sessions
from app.config import EMBEDDING_DIM, Provider, Settings, StoreBackend, get_settings
from app.deps import Services
from app.llm.base import LLMClient
from app.llm.bedrock import BedrockLLM
from app.llm.mock import MockLLM
from app.prompts import PromptRegistry
from app.rag.chunker import TextChunker
from app.rag.embedder import BedrockTitanEmbedder, Embedder, HashingMockEmbedder
from app.rag.pipeline import SYSTEM_PROMPT, USER_PROMPT, RagPipeline
from app.store.base import DocumentStore
from app.store.memory import InMemoryStore
from app.store.postgres import PostgresStore, run_migrations

# JSON envelope overhead allowed on top of the document limit.
BODY_OVERHEAD_BYTES = 64 * 1024


def _make_store(s: Settings) -> DocumentStore:
    if s.store_backend is StoreBackend.POSTGRES:
        return PostgresStore(s.database_url, s.db_pool_min_size, s.db_pool_max_size)
    return InMemoryStore()


def _make_embedder(s: Settings) -> Embedder:
    if s.embedder_provider is Provider.BEDROCK:
        return BedrockTitanEmbedder(s.aws_region, s.bedrock_embed_model_id, s.embed_concurrency)
    return HashingMockEmbedder()


def _make_llm(s: Settings) -> LLMClient:
    if s.llm_provider is Provider.BEDROCK:
        return BedrockLLM(s.aws_region, s.bedrock_llm_model_id, s.bedrock_max_tokens)
    return MockLLM()


async def build_services(s: Settings) -> Services:
    """Wire components and fail fast on misconfiguration (before taking traffic)."""
    embedder = _make_embedder(s)
    if embedder.dimension != EMBEDDING_DIM:
        raise RuntimeError(
            f"Embedder dimension {embedder.dimension} != schema dimension {EMBEDDING_DIM}"
        )
    prompts = PromptRegistry(s.prompts_dir)
    prompts.require(SYSTEM_PROMPT, USER_PROMPT)

    if s.store_backend is StoreBackend.POSTGRES and s.run_migrations:
        await run_migrations(s.database_url, s.migrations_dir)
    store = _make_store(s)
    await store.open()

    llm = _make_llm(s)
    return Services(
        settings=s,
        store=store,
        embedder=embedder,
        llm=llm,
        prompts=prompts,
        chunker=TextChunker(s.chunk_size, s.chunk_overlap),
        pipeline=RagPipeline(
            store, embedder, llm, prompts, top_k=s.retrieval_top_k, min_score=s.retrieval_min_score
        ),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        services = await build_services(settings)
        app.state.services = services
        try:
            yield
        finally:
            await services.store.close()

    app = FastAPI(title="Document Q&A Service", version="0.1.0", lifespan=lifespan)

    body_limit = settings.max_document_bytes + BODY_OVERHEAD_BYTES

    @app.middleware("http")
    async def limit_body_size(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Reject oversized bodies before they are read into memory. Handlers still
        enforce the exact byte limits; Traefik enforces the same ceiling at the edge."""
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > body_limit:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds the limit of {body_limit} bytes."},
            )
        return await call_next(request)

    for module in (health, documents, ask, sessions):
        app.include_router(module.router)
    return app


app = create_app()
