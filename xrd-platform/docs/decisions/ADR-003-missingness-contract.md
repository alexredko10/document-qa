# ADR-003 — Missingness and validity contract

**Status:** Accepted

## Decision

Validity masks are authoritative.

For profile/feature numerical slots:

- valid (`mask=True`) -> finite value required;
- invalid (`mask=False`) -> fill value is not scientifically meaningful and may be zero or NaN.

Measured zero is therefore distinct from missing zero-filled storage.

## Reason

Scientific validity is a state of the measurement, not a property inferred from a numeric sentinel.

## Consequence

Any storage/index adapter that fills missing coordinates must preserve sidecar validity and must never present imputation as observation.
