# ADR-001 — Corpus-first architecture

**Status:** Accepted

## Decision

Build and validate the physical XRD corpus encoder before vector search, classification, learned embeddings, or LLM decision layers.

## Reason

A fast retrieval system built on scientifically invalid representations only accelerates invalid comparisons.

The canonical corpus preserves calibrated physics, masks, support, coverage, uncertainty, and provenance. Future retrieval/index/model layers are derived consumers.

## Consequences

- Vector databases are deferred until pairwise scientific similarity is validated.
- Disease labels do not influence ingestion.
- Re-encoding is versioned.
- Dense index vectors never replace canonical scientific representations.
