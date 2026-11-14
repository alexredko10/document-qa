# XRD Project Constitution

## 1. Mission

Build a research-grade XRD corpus preparation platform that converts raw, physically calibrated area-detector measurements into reproducible, mask-aware, uncertainty-aware scientific representations.

The first stable release contract is:

`XRD-CHUNK-096-v1`

The platform must support future retrieval, modelling, and scientific analysis without forcing those future tasks into the current encoder.

## 2. Corpus-first architecture

Current scope:

```text
RAW XRD + calibration + metadata
    -> QC and typed masks
    -> validated geometry
    -> q / chi coordinates
    -> polar signal/support/coverage
    -> 96 physical chunks
    -> 256D radial profile + 15D physical features per chunk
    -> canonical 26,016D scan representation + masks
    -> provenance + quality reports
    -> validated scientific corpus
```

Future, explicitly out of current scope:

```text
vector ANN index
retrieval classifier
clinical probabilities
CNN / Siamese / MIL
LLM decision layer
```

These may consume the corpus later. They must not redefine the corpus retrospectively without a version change.

## 3. Scientific source of truth

The source of truth is not a vector database.

The source of truth is:

- raw measurement reference/hash;
- original calibration;
- detector/acquisition metadata;
- masks and reason codes;
- physical q/chi coordinates;
- canonical profiles/features;
- validity/support/coverage;
- uncertainty when scientifically justified;
- processing configuration and provenance.

Dense index vectors are derived artifacts.

## 4. Raw-first rule

Never overwrite raw measurements, original `.poni`, masks, or original metadata.

Derived data must be reproducible from immutable inputs plus versioned configuration/code.

## 5. Missingness rule

Measured zero and missing/unobserved are different scientific states.

Validity masks are authoritative.

For profile/features:

- `mask=True` means the value is scientifically available and must be finite.
- `mask=False` means the numerical slot is not a valid observation; its fill value is not scientifically meaningful.

Do not infer validity from a numeric sentinel.

## 6. No invented physics

Never invent:

- detector dimensions;
- pixel size;
- wavelength;
- saturation level;
- q range;
- allowed centre drift;
- SNR threshold;
- peak threshold;
- beam-halo radius;
- normalization reference window.

Unknown values remain unknown.

Synthetic fixtures must be labelled synthetic.

## 7. No label leakage

Disease labels, patient age, side, previous model logits, or clinical outcomes must not enter the physical chunk encoder.

Any future supervised transformation must be fitted only on an appropriate reference/training partition.

## 8. Existing product isolation

`document-qa-prototype/` and `document-qa/` are existing product areas.

They are effectively read-only unless a mission explicitly names a narrow integration file.

No opportunistic cleanup, formatting, modernization, or refactoring of legacy code.

## 9. Agent boundaries

Implementation agents implement only the current mission.

Independent review agents do not implement the mission they review.

The human repository owner alone controls Git history, staging, commits, branches, pushes, PRs, merges, tags, restore/reset/cleanup, and worktrees.

## 10. Definition of scientific progress

Passing tests is necessary but not sufficient.

A scientific component is accepted only when:

- units and coordinate conventions are explicit;
- missingness is preserved;
- assumptions are documented;
- physically meaningful negative/zero values are handled correctly;
- synthetic/golden oracles challenge the implementation;
- an independent reviewer validates the result;
- unresolved unknowns remain visible rather than being guessed.
