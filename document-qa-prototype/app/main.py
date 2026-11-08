import logging
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.llm.metadata import metadata_context
from app.llm.openrouter import LLMProviderError
from app.llm.provider import get_llm
from app.llm.relevance import has_relevant_context
from app.models.ask import AskRequest, AskResponse, SourceChunk, LLMMetadata, RetrievalMetadata
from app.models.document import DocumentRequest, DocumentResponse
from app.observability import tracing
from app.observability.logging import log_event, request_id, request_id_context
from app.observability.metrics import (
    HTTP_REQUESTS,
    HTTP_DURATION,
    HTTP_IN_FLIGHT,
)
from app.rag.cleaner import clean_text
from app.rag.embedding_provider import EmbeddingError, get_embedding_provider, validate_vectors
from app.rag.markdown_chunker import split_markdown
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.llm.base import ContextFreeUnavailable, LLMClient
from app.rag.embedder import embed_text
from app.rag.retriever import search_vectors

app = FastAPI(title="Document QA Prototype")
tracing.configure_tracing()

MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_SEMANTIC_CHUNKS = 256
# Temporary in-memory storage
# Process-local state requires one replica until documents and vectors use shared storage.
documents: dict[str, str] = {}
document_chunks: dict[str, list[str]] = {}
document_vectors: dict[str, list[list[float]]] = {}
document_embedding_config: dict[str, tuple[str, str, int]] = {}


# Centralize request correlation, metrics and tracing across HTTP routes.
@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    correlation_id = request_id(request.headers.get("X-Request-ID"))
    token = request_id_context.set(correlation_id)
    path = request.url.path
    scrape = path == "/metrics"
    quiet = path in {"/metrics", "/healthz"}
    method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD",
                                                  "OPTIONS"} else "OTHER"
    start = perf_counter()
    status_code = 500
    failed = False
    if not scrape:
        HTTP_IN_FLIGHT.inc()
    with tracing.get_tracer().start_as_current_span(
        "http.request",
        attributes={"http.request.method": method},
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            try:
                response = await call_next(request)
                status_code = response.status_code
            except Exception:
                failed = True
                response = PlainTextResponse("Internal Server Error", status_code=500)
            response.headers["X-Request-ID"] = correlation_id
            return response
        finally:
            elapsed = perf_counter() - start
            # Route templates and bounded methods avoid labels for individual request paths.
            route = request.scope.get("route")
            route_name = getattr(route, "path", "unmatched")
            span.set_attribute("http.route", route_name)
            span.set_attribute("http.response.status_code", status_code)
            if failed or status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            try:
                if not scrape:
                    HTTP_REQUESTS.labels(method=method, route=route_name, status=str(status_code)).inc()
                    HTTP_DURATION.labels(method=method, route=route_name).observe(elapsed)
                    HTTP_IN_FLIGHT.dec()
                if failed:
                    log_event("http_request_failed", level=logging.ERROR, method=method,
                              route=route_name, reason="unexpected_error")
                if not quiet:
                    log_event("http_request_completed", method=method, route=route_name,
                              status_code=status_code, duration_ms=round(elapsed * 1000, 3))
            finally:
                request_id_context.reset(token)


DEMO_DIR = Path(__file__).resolve().parent / "demo"


@app.get("/demo", include_in_schema=False)
def demo():
    return FileResponse(DEMO_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/demo/{asset}", include_in_schema=False)
def demo_asset(asset: str):
    if asset not in {"console.css", "console.js"}:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(DEMO_DIR / asset)


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentResponse,
          status_code=201, )
def create_document(document: DocumentRequest) -> DocumentResponse | HTTPException:
    size = len(document.text.encode("utf-8"))
    if size > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Document exceeds 1 MiB",
        )
    cleaned_text = clean_text(document.text)

    chunks = split_markdown(
        cleaned_text,
        chunk_size=800,
        overlap=120,
    )
    if not chunks:
        raise HTTPException(status_code=422, detail="Document has no indexable content")
    try:
        provider = get_embedding_provider()
        if provider.provider == 'openrouter' and len(chunks) > MAX_SEMANTIC_CHUNKS:
            raise HTTPException(status_code=413, detail="Document exceeds the 256-chunk semantic indexing limit")
        vectors = validate_vectors(provider.embed(chunks, 'document'), len(chunks), allow_zero=provider.provider == 'hash')
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail="Embedding provider unavailable") from exc
    document_id = str(uuid4())

    # Store only after all embeddings validate, avoiding partially indexed documents.
    documents[document_id] = document.text
    document_vectors[document_id] = vectors
    document_embedding_config[document_id] = (provider.provider, provider.model, len(vectors[0]))
    document_chunks[document_id] = chunks

    return DocumentResponse(
        document_id=document_id,
        status="accepted",
        text=document.text,
    )


@app.get("/documents/{document_id}")
def document(document_id: str) -> DocumentResponse:
    if document_id not in documents:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )
    text = documents[document_id]
    return DocumentResponse(
        document_id=document_id,
        status="Document in the storage",
        text=text,
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest,
        llm: LLMClient = Depends(get_llm)) -> AskResponse:
    log_event("ask_request_received", context_mode="rag" if request.use_context else "no_rag")
    results = []
    retrieval = None
    if request.use_context:
        if request.document_id not in document_chunks:
            raise HTTPException(status_code=404, detail="Document not found")
        started = perf_counter()
        # Vectors must share a provider, model and dimensions to be comparable.
        stored_provider, stored_model, dimensions = document_embedding_config[request.document_id]
        try:
            provider = get_embedding_provider()
            if (provider.provider, provider.model) != (stored_provider, stored_model):
                raise EmbeddingError('incompatible_model')
            query_vector = validate_vectors(provider.embed([request.question], 'query'), 1, allow_zero=provider.provider == 'hash')[0]
            if len(query_vector) != dimensions:
                raise EmbeddingError('incompatible_dimensions')
        except EmbeddingError as exc:
            raise HTTPException(status_code=503, detail="Embedding provider unavailable or incompatible; re-upload the document if configuration changed") from exc
        with tracing.get_tracer().start_as_current_span(
            "vector.retrieval", record_exception=False, set_status_on_exception=False
        ) as span:
            try:
                results = search_vectors(
                    query_vector=query_vector,
                    chunks=document_chunks[request.document_id],
                    vectors=document_vectors[request.document_id],
                    top_k=3,
                    positive_only=stored_provider == 'hash',
                )
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                raise
        retrieval = RetrievalMetadata(embedding_provider=stored_provider, embedding_model=stored_model,
                                      retrieval_duration_ms=round((perf_counter() - started) * 1000, 3))
        context = [item.text for item in results]
        # Hash embeddings capture word overlap rather than semantic similarity.
        if not results or (stored_provider == "hash" and not has_relevant_context(request.question, context)):
            return AskResponse(answer="I don't know based on the provided document.",
                               source_chunks=[], llm=LLMMetadata(), use_context=True, retrieval=retrieval)

    try:
        metadata = {}
        token = metadata_context.set(metadata)
        try:
            if request.use_context:
                answer = llm.generate(question=request.question, context=context)
            else:
                answer = llm.generate_without_context(question=request.question)
        finally:
            metadata_context.reset(token)
    except ContextFreeUnavailable as exc:
        raise HTTPException(status_code=501, detail="Context-free answers require a real generative provider; StubLLM does not support this mode.") from exc
    except LLMProviderError as exc:
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = exc.retry_after
        raise HTTPException(status_code=503, detail="LLM provider unavailable", headers=headers) from exc

    return AskResponse(
        answer=answer,
        llm=LLMMetadata(**metadata),
        use_context=request.use_context,
        retrieval=retrieval,
        source_chunks=[SourceChunk(index=item.index, text=item.text, score=item.score) for item in results],
    )

@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
