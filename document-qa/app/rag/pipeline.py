"""Retrieve-then-answer pipeline (stage 1). Stage 2 replaces the single LLM call
with a bounded tool-calling loop; the guard and the result shape stay the same."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from app.llm.base import LLMClient
from app.prompts import PromptRegistry
from app.rag.embedder import Embedder
from app.rag.guard import DONT_KNOW, trusted_evidence
from app.store.base import DocumentStore, Message, ScoredChunk

SYSTEM_PROMPT = "answer_system"
USER_PROMPT = "answer_user"


@dataclass(frozen=True)
class PipelineResult:
    answer: str
    sources: list[ScoredChunk]
    model_id: str | None
    prompt_version: str | None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def grounded(self) -> bool:
        return bool(self.sources)


def _format_history(messages: Sequence[Message]) -> str:
    if not messages:
        return "(none)"
    return "\n".join(f"{m.role.value.capitalize()}: {m.content}" for m in messages)


def _format_context(chunks: Sequence[ScoredChunk]) -> str:
    return "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(chunks, start=1))


class RagPipeline:
    def __init__(
        self,
        store: DocumentStore,
        embedder: Embedder,
        llm: LLMClient,
        prompts: PromptRegistry,
        *,
        top_k: int,
        min_score: float,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._llm = llm
        self._prompts = prompts
        self._top_k = top_k
        self._min_score = min_score

    async def answer(
        self,
        question: str,
        history: Sequence[Message],
        document_ids: Sequence[str] | None,
    ) -> PipelineResult:
        # Retrieval uses the question alone. Follow-ups such as "tell me more"
        # retrieve poorly; the stage-2 agent fixes this by letting the model
        # write its own search query via the search_chunks tool.
        query_embedding = (await asyncio.to_thread(self._embedder.embed, [question]))[0]
        hits = await self._store.search(query_embedding, self._top_k, document_ids)
        evidence = trusted_evidence(hits, self._min_score)
        if not evidence:
            return PipelineResult(answer=DONT_KNOW, sources=[], model_id=None, prompt_version=None)

        system = self._prompts.get(SYSTEM_PROMPT).render()
        user = self._prompts.get(USER_PROMPT).render(
            context=_format_context(evidence),
            history=_format_history(history),
            question=question,
        )
        response = await self._llm.complete(system, user)
        # The model may still decline after reading the evidence; report that as a
        # refusal so `grounded` and `sources` never claim support that wasn't used.
        refused = response.text.strip().strip('"') == DONT_KNOW
        return PipelineResult(
            answer=DONT_KNOW if refused else response.text,
            sources=[] if refused else evidence,
            model_id=self._llm.model_id,
            prompt_version=self._prompts.version_of(SYSTEM_PROMPT, USER_PROMPT),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
