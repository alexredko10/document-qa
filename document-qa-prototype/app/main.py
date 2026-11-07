from uuid import uuid4
from app.rag.chunker import split_text
from fastapi import FastAPI, HTTPException
from app.models.document import DocumentRequest, DocumentResponse
from app.rag.embedder import embed_text

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
    chunks = split_text(document.text)
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
