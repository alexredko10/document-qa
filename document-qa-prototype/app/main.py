from uuid import uuid4

from fastapi import FastAPI, HTTPException

from app.models.ask import AskRequest, AskResponse, SourceChunk
from app.models.document import DocumentRequest, DocumentResponse
from app.rag.cleaner import clean_text
from app.rag.embedder import embed_text
from app.rag.markdown_chunker import split_markdown
from app.rag.retriever import search_vectors

app = FastAPI(title="Document QA Prototype")

MAX_DOCUMENT_BYTES = 1024 * 1024
# Temporary in-memory storage
documents: dict[str, str] = {}
document_chunks: dict[str, list[str]] = {}
document_vectors: dict[str, list[list[float]]] = {}


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
def ask(request: AskRequest) -> AskResponse:

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

    return AskResponse(
        answer=None,
        source_chunks=[
            SourceChunk(
                index=result.index,
                text=result.text,
                score=result.score,
            )
            for result in results
        ],
    )