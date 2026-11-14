# Project State

This file is intentionally small. Update it only after the orchestrator closes a mission.

## Current stable state

- Mission 001 — Canonical schema foundation: **CLOSED**
- Mission 001.5 — Project hygiene: **PENDING FINAL INDEPENDENT APPROVAL**
- Mission 001.6 — Source reuse/scientific assumptions audit: **NOT STARTED**
- Mission 002 — Geometry/detector compatibility: **NOT STARTED**

## Current scientific contract

`XRD-CHUNK-096-v1`

- 16 angular sectors
- 6 radial bands
- 96 chunks
- 256 radial profile coordinates/chunk
- 15 physical features/chunk
- 271 numerical coordinates/chunk
- 26,016 numerical coordinates/scan
- masks are authoritative
- valid profile/feature values are finite

## Current exclusions

Not yet authorized:

- clinical classification
- disease probability
- vector database as source of truth
- learned embeddings
- CNN/Siamese/MIL
- label-driven feature pruning
- LLM decision making

## Immediate next gate

Close Mission 001.5 through independent non-mutating review.

Then perform Mission 001.6 before significant legacy-code reuse in geometry/integration.
