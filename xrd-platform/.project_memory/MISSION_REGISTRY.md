# Mission Registry

This registry defines what each planned mission owns.

| Mission | Owns | Must not own |
|---|---|---|
| 001 | schema/config/domain contracts | geometry, retrieval, ML |
| 001.5 | XRD-scoped hygiene/CI | legacy formatting, science code |
| 001.6 | source audit/assumptions/license questions | implementation reuse |
| 002 | detector geometry/q/chi | masks, integration, refinement |
| 003 | typed masks/QC | polar integration/features |
| 004 | polar integration/support/coverage | chunk physical features |
| 005 | deterministic 96-chunk profile split | disease labels/features |
| 006 | 15 one-chunk physical features | patient-side/group features |
| 007 | corpus serialization/provenance | ANN/classification |
| 008 | pairwise scientific similarity | disease probability |
| 009 | unsupervised corpus quality maps | label-driven pruning |
| 010 | vector candidate index/retrieval | source-of-truth science |
| 011+ | explicitly authorized modelling research | retroactive corpus mutation |

## Mission rules

- A mission may depend on earlier stable interfaces.
- A mission must not silently pull later roadmap work forward.
- If a needed contract is missing, report the dependency rather than inventing it.
- Major schema changes require a new version or ADR.
