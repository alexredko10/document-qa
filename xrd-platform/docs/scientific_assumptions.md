# Scientific Assumptions Registry

Status vocabulary:

- `VERIFIED`
- `HYPOTHESIS`
- `LEGACY`
- `UNKNOWN`

This document must be updated from evidence as the project progresses.

| Topic | Status | Current statement | Required evidence / next action |
|---|---|---|---|
| XRD-CHUNK-096 dimensions | VERIFIED contract | 16 sectors x 6 bands x (256+15) = 26,016 | Schema tests |
| 16x6 is optimal | HYPOTHESIS | It is a frozen experimental comparison format, not proven optimal | Later ablation/reconstruction/retrieval study |
| q unit | TARGET: nm^-1 | Canonical target is explicit physical q, normally `q_nm^-1` | Mission 002 verify pyFAI output/config |
| chi convention | TARGET | `[-180,180)` with fixed orientation | Mission 002 independent axis/sign tests |
| q range | UNKNOWN | Must be common/configured for compatible corpus | Verify real cohort geometry before Mission 004 |
| 256x256 detector | OBSERVED context | Common image shape exists | Verify actual detector metadata |
| 512x726 detector | UNKNOWN | Mentioned target shape | Verify raw files/detector metadata |
| Ash512x768 calibration | OBSERVED legacy example | Example `.poni` names this detector | Resolve mismatch before cross-detector use |
| detector saturation threshold | UNKNOWN | Must come from detector/ADC metadata | Mission 003 |
| direct-beam halo radius | UNKNOWN | Detector/experiment specific | Mission 003 |
| PONI equals beam centre | REJECTED general assumption | Not true in general for tilted geometry | Mission 002 full geometry tests |
| WAXS more informative | HYPOTHESIS | May carry desired structure | No ingestion crop; evaluate later |
| low-q/SAXS can be discarded | REJECTED | Preserve usable low-q data | Typed masks only |
| photon Poisson noise model | UNKNOWN | Valid only for appropriate detector units/stats | Mission 004 uncertainty audit |
| Water/Fat cancer specificity | HYPOTHESIS / not established | Water-rich signal is not unique to cancer | Future controlled clinical analysis |
| Bremen 15 = chunk physical 15 | REJECTED | Bremen features are multi-profile/patient comparison statistics | Keep separate |
| Aramina age/logit as physical embedding | REJECTED | Not physical scan features | Future patient-level experiment only |
| cosine similarity = probability | REJECTED | Similarity is not disease probability | Future calibration required |
