"""Deterministic 'I don't know' guard: refuse when no chunk passes the threshold.

The guard runs before the LLM is called, so a refusal never depends on the model
following its instructions, and costs no tokens.
"""

from app.store.base import ScoredChunk

DONT_KNOW = "I don't know based on the provided document."


def trusted_evidence(hits: list[ScoredChunk], min_score: float) -> list[ScoredChunk]:
    """Keep only chunks similar enough to count as evidence for an answer."""
    return [h for h in hits if h.score >= min_score]
