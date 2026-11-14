# ADR-002 — XRD-CHUNK-096-v1

**Status:** Accepted experimental schema

## Decision

Use a fixed baseline representation:

- 16 full-circle angular sectors;
- 6 non-overlapping physical-q bands;
- 256 radial samples per band;
- 15 physical features per chunk;
- 96 chunks;
- 271 numerical coordinates/chunk;
- 26,016 coordinates/scan;
- sector-major, band-minor order.

## Important limitation

This is an experimental encoding format, not a proof of optimal discretization.

256 samples/band are output coordinates, not necessarily independent physical measurements.

Partial/unobserved regions remain represented through masks rather than fabricated signal.

## Change policy

A materially different layout requires a new schema version and compatibility decision.
