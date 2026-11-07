from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends,Request, Response
from app.llm.openrouter import LLMProviderError
from app.llm.provider import get_llm
from app.llm.base import LLMClient
from app.llm.relevance import has_relevant_context
from app.models.ask import AskRequest, AskResponse, SourceChunk
from app.models.document import DocumentRequest, DocumentResponse
from app.rag.cleaner import clean_text
from app.rag.embedder import embed_text
from app.rag.markdown_chunker import split_markdown
from app.rag.retriever import search_vectors

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.observability.metrics import (
    HTTP_REQUESTS,
    HTTP_DURATION,
    HTTP_IN_FLIGHT,
)
app = FastAPI(title="Document QA Prototype")

MAX_DOCUMENT_BYTES = 1024 * 1024
# Temporary in-memory storage
documents: dict[str, str] = {}
document_chunks: dict[str, list[str]] = {}
document_vectors: dict[str, list[list[float]]] = {}

@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    # Do not instrument Prometheus scrapes.
    if request.url.path == "/metrics":
        return await call_next(request)

    HTTP_IN_FLIGHT.inc()
    start = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    finally:
        elapsed = perf_counter() - start

        # Use the registered route template, never the raw path.
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")

        method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
        HTTP_REQUESTS.labels(
            method=method,
            route=route_name,
            status=str(status_code),
        ).inc()

        HTTP_DURATION.labels(
            method=method,
            route=route_name,
        ).observe(elapsed)

        HTTP_IN_FLIGHT.dec()

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
    vectors = [embed_text(chunk) for chunk in chunks]
    document_id = str(uuid4())

    documents[document_id] = document.text
    document_chunks[document_id] = chunks
    document_vectors[document_id] = vectors

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
    if request.document_id not in document_chunks:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    query_vector = embed_text(request.question)

    results = search_vectors(
        query_vector=query_vector,
        chunks=document_chunks[request.document_id],
        vectors=document_vectors[request.document_id],
        top_k=3,
    )
    if not results:
        return AskResponse(
            answer="I don't know based on the provided document.",
            source_chunks=[],
        )

    try:
        context = [item.text for item in results]
        if not has_relevant_context(request.question, context):
            return AskResponse(
                answer="I don't know based on the provided document.",
                source_chunks=[],
            )
        answer = llm.generate(
            question=request.question,
            context=context,
        )

    except LLMProviderError as exc:
        headers = {}
        if exc.retry_after:
            headers["Retry-After"] = exc.retry_after
        raise HTTPException(
            status_code=503,
            detail="LLM provider unavailable",
            headers=headers,
        ) from exc

    return AskResponse(
        answer=answer,
        source_chunks=[
            SourceChunk(
                index=item.index,
                text=item.text,
                score=item.score,
            )
            for item in results
        ],
    )

@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )