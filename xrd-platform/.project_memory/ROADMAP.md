# XRD Platform Roadmap

## Guiding dependency chain

```text
scientific contract
    -> source/assumption audit
    -> geometry
    -> typed masks/QC
    -> polar integration/support/coverage
    -> canonical chunks
    -> physical features
    -> canonical corpus/storage
    -> validated pairwise similarity
    -> corpus quality maps
    -> vector index/retrieval
    -> future models
```

Do not invert this dependency order.

---

## Mission 001 — Canonical schema foundation

**Status:** CLOSED

Deliverables:

- v1 configuration;
- `ChunkId`;
- `ChunkQCStatus`;
- measurement/chunk/scan domain contracts;
- exact 96/271/26016 invariants;
- authoritative validity masks;
- finite values required when valid.

Gate:

- deterministic schema tests;
- no geometry/retrieval/ML leakage.

---

## Mission 001.5 — Project hygiene

**Status:** PENDING FINAL INDEPENDENT APPROVAL

Deliverables:

- XRD-scoped pre-commit;
- XRD-only CI test job;
- no production Docker/deployment behaviour changes.

Gate:

- hooks cannot mutate legacy Document QA areas;
- independent non-mutating review passes.

---

## Mission 001.6 — Source reuse and scientific assumptions audit

**Priority:** BLOCKING BEFORE SUBSTANTIAL PHYSICS REUSE

Deliverables:

- `docs/source_reuse_matrix.md` completed with concrete audited functions;
- `docs/scientific_assumptions.md` updated from template to actual project evidence;
- dependency/version inventory;
- license/permission questions;
- explicit approved reuse list.

Important:

This mission may inspect prior archives/libraries, but it does not implement their algorithms.

Gate:

- independent reviewer approves reuse boundaries;
- no blind copying;
- unknown detector/acquisition facts remain unknown.

---

## Mission 002 — Geometry and detector compatibility foundation

Goal:

```text
image shape + verified .poni
    -> physical q[y,x]
    -> chi[y,x]
    -> geometry metadata/provenance
```

Deliverables:

- pyFAI geometry adapter;
- detector/image-shape compatibility validation;
- explicit q units;
- verified chi convention;
- original geometry preservation;
- known synthetic unrotated and tilted geometry tests;
- edge/outside beam-centre cases;
- unresolved 512x726 vs 512x768 reported rather than guessed.

Not included:

- automatic centre refinement;
- masking policy;
- polar integration.

Gate:

- independent geometry oracle reproduces q/chi cases;
- axis/sign/unit convention documented.

---

## Mission 003 — Typed mask and QC subsystem

Goal:

Preserve reasons for unusable/uncertain detector information.

Deliverables:

- reason-coded mask representation;
- explicit adapter to pyFAI exclusion mask;
- nonfinite/dead/hot/saturated/direct-beam/halo/geometric-unobserved semantics;
- QC summary;
- detector-specific saturation contract without arbitrary universal threshold.

Gate:

- synthetic saturated spot masked;
- equally bright legitimate physical signal is not automatically rejected;
- missing is never converted to measured zero.

---

## Mission 004 — Polar integration, support, coverage, uncertainty

Goal:

```text
raw/corrected detector signal + geometry + masks
    -> calibrated I(q,chi)
```

Baseline target:

- 16 azimuth bins;
- 1536 radial bins;
- fixed physical q range supplied by verified config.

Deliverables:

- pyFAI version-verified adapter;
- q/chi bin edges;
- polar signal;
- validity;
- contributor/support information;
- separately defined geometric coverage;
- uncertainty only when scientifically justified.

Gate:

- shape/axis convention independently tested;
- empty bins remain missing;
- count/normalization/coverage are not conflated;
- constant-field/ring synthetic oracles pass.

---

## Mission 005 — Canonical 96-chunk radial profiles

Goal:

Split `(16,1536)` polar representation into `96 x 256`.

Deliverables:

- stable sector-major/band-minor mapping;
- chunk q/chi edges;
- per-bin signal/mask/support/coverage/uncertainty;
- chunk QC status framework;
- no chunk deletion.

Gate:

- exact mapping;
- partial/unobserved chunks preserved;
- seam/boundary tests pass.

---

## Mission 006 — 15 per-chunk physical features

Implement the frozen project feature contract:

1. intensity mean
2. intensity std
3. intensity median
4. reliable maximum
5. integrated intensity
6. dominant peak q
7. dominant peak prominence
8. dominant peak FWHM
9. spectral centroid q
10. spectral spread q
11. spectral entropy
12. peak count
13. high/low q integral ratio
14. robust spectral slope
15. SNR estimate

Deliverables for every feature:

- exact formula;
- units;
- validity conditions;
- numerical guards;
- tests with analytic/synthetic profiles.

Gate:

- features operate on one chunk of one scan;
- unavailable feature != numeric zero;
- no Bremen patient-level feature substitution.

---

## Mission 007 — Canonical scan embedding, provenance, and corpus serialization

Goal:

Produce reproducible raw scientific corpus artifacts.

Deliverables:

- `chunk_raw_embedding [96,271]`;
- chunk validity;
- `scan_raw_embedding [26016]`;
- scan validity;
- provenance/version hashes;
- Zarr/HDF5/appropriate array storage decision;
- metadata manifest;
- round-trip tests.

Separate:

- canonical scientific representation;
- optional dense index representation.

Gate:

- save/load round trip preserves mask meaning;
- exact encoding is reproducible from raw+config+calibration+version.

---

## Mission 008 — Scientific similarity benchmark

This is an evaluation layer, not a classifier.

Deliverables:

- masked Pearson;
- masked cosine;
- masked L2/RMSE;
- physically defined Wasserstein-1;
- overlap/support diagnostics.

Required W1 tests include:

- identical profiles -> zero;
- delta peaks -> physical separation;
- nonuniform q bins;
- empty/disjoint support;
- negative baseline conversion policy;
- duplicate-q policy.

Gate:

- numerical results cross-checked against independent analytic/SciPy references;
- distances are not called disease probabilities.

---

## Mission 009 — Corpus quality and information maps

Without disease labels, generate `16 x 6` maps for:

- coverage;
- saturation/contamination;
- repeatability where available;
- SNR/uncertainty;
- geometry sensitivity;
- peak preservation;
- instrument/batch association diagnostics.

Do not permanently prune chunks based on variability.

Gate:

- measurement quality is separated from between-sample variability.

---

## Mission 010 — Vector retrieval index

Only after Missions 002-009 have stable contracts.

Goal:

Use dense derived index vectors to accelerate candidate search.

Architecture:

```text
canonical corpus
    -> versioned dense index adapter
    -> ANN/vector index
    -> candidates
    -> canonical mask-aware reranking
```

The vector index is not the scientific source of truth.

Gate:

- retrieval of known repeats/controlled perturbations is scientifically sensible;
- ANN result can be traced back to canonical representations.

---

## Mission 011+ — Future modelling research

Possible future branches:

- weighted kNN retrieval evidence;
- calibrated probabilities;
- logistic/LDA baselines;
- learned embeddings;
- Siamese/contrastive learning;
- MIL;
- breast/patient hierarchy;
- LLM explanation layer.

These are not authorized merely because they appear in the roadmap.

Each requires a new explicit mission and validation design.
