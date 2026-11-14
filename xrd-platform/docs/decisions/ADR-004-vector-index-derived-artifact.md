# ADR-004 — Vector index is a derived artifact

**Status:** Accepted

## Decision

FAISS/Qdrant/pgvector or another ANN/index backend is not the canonical scientific corpus.

## Architecture

```text
canonical scientific representation
    -> versioned dense index adapter
    -> vector index
    -> candidate retrieval
    -> canonical mask-aware reranking
```

## Consequences

- Index vectors can be regenerated.
- Index imputation/scaling is versioned separately.
- Similarity returned by an ANN index is not disease probability.
- Scientific comparisons may reject candidates with insufficient common support even if ANN distance is small.
