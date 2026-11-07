"""Service container and FastAPI dependency providers."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.llm.base import LLMClient
from app.prompts import PromptRegistry
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.pipeline import RagPipeline
from app.store.base import DocumentStore


@dataclass
class Services:
    settings: Settings
    store: DocumentStore
    embedder: Embedder
    llm: LLMClient
    prompts: PromptRegistry
    chunker: TextChunker
    pipeline: RagPipeline


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]
