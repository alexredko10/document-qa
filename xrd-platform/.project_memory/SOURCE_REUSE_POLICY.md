# Source and Legacy Library Reuse Policy

The project has access to prior XRD code/libraries, but prior existence is not scientific validation or permission to copy.

## Decision vocabulary

Every candidate function/module receives exactly one decision:

- `REUSE_AS_IS`
- `ADAPT`
- `IDEA_ONLY`
- `REJECT`
- `DEFER`

## Required evidence for reuse

Record:

- source repository/archive;
- path and line/function;
- actual formula/algorithm;
- original data assumptions;
- hardcoded thresholds/windows;
- units;
- output semantics;
- missing-data behaviour;
- detector assumptions;
- scientific evidence/reference;
- licensing/permission status;
- independent conformance test;
- final decision.

## Current high-level decisions

### XRD-preprocessing

Potential use:

- detector/raw readers: audit then adapt/reuse;
- pyFAI integration patterns: adapt and independently validate;
- QC/config structure: idea/adapt.

Do not inherit automatically:

- bright pixel threshold 500;
- row-511 masking;
- q normalization windows;
- SNR thresholds;
- fixed q ROI;
- save/drop policies.

### Bremen feature library

The historical "15 features" are not the project's 15 per-chunk physical features.

They depend on multiple LEFT/RIGHT profiles and are patient/group comparison statistics.

Useful ideas for later similarity/evaluation:

- cosine;
- Wasserstein-1;
- replicate-weighted RMS;
- peak-window comparison;
- common-q comparison.

Historical peak/ROI/gate constants are not generic defaults.

### Aramina feature library

Do not place age, age availability, previous-model logits, or LEFT/RIGHT patient symmetry features inside the physical chunk embedding.

Useful only as future patient-level experimental reference.

Avoid legacy behaviours that:

- interpolate outside real q support;
- convert unavailable to zero;
- imply valid metrics when data are insufficient.

## Licensing

If no license/permission can be established, do not transplant non-trivial source code.

Reimplement public mathematical formulas independently and cite the conceptual source in documentation where appropriate.
