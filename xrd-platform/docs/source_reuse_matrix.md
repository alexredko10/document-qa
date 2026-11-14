# Source Reuse Matrix

This file is initialized from the scientific library audit and must be refined against the actual mounted source before code reuse.

Decision vocabulary:

`REUSE_AS_IS | ADAPT | IDEA_ONLY | REJECT | DEFER`

| Source | Candidate | Current decision | Main reason / risk | Required before implementation |
|---|---|---|---|---|
| XRD-preprocessing | `azimuthal.py` pyFAI integration | ADAPT | Useful integration pattern but insufficient coverage/uncertainty semantics | Inspect exact version/API; independent geometry/integration tests |
| XRD-preprocessing | `gfrm.py`, `h5.py` readers | ADAPT | Potential raw transport layer; detector-specific assumptions | Format/license audit, raw preservation tests |
| XRD-preprocessing | row-511 masking | REJECT as generic default | Detector-specific historical behaviour | Evidence tied to detector family |
| XRD-preprocessing | `faulty_pixels.py` bright threshold | REJECT as generic default | Fixed 500 threshold can erase real peaks | Detector full-well/saturation metadata |
| XRD-preprocessing | PONI-based beam-centre approximation | REJECT general use | Invalid under general tilt | Use verified pyFAI geometry |
| XRD-preprocessing | normalization windows | DEFER / experiment-specific | Historical q windows/hardcodes | Explicit scientific justification |
| XRD-preprocessing | SNR/QC/config interfaces | IDEA_ONLY / ADAPT | Structure useful, noise model must be verified | Detector statistics audit |
| Bremen | cosine distance | IDEA_ONLY | Simple formula; must become mask/common-support aware | Independent implementation/tests |
| Bremen | Wasserstein-1 | IDEA_ONLY | Useful pairwise metric; mass semantics ambiguous on nonuniform q | Physical-bin-width tests; SciPy/analytic reference |
| Bremen | weighted RMS | IDEA_ONLY | Useful for repeats, not single-scan uncertainty | Define replicate semantics |
| Bremen | "mahalanobis" | IDEA_ONLY with rename | Diagonal standardized distance, not full Mahalanobis | Accurate name/formula |
| Bremen | q-grid interpolation strategy | REJECT as-is | Boundary extrapolation/missingness risks | Fixed physical grid + masks |
| Bremen | Savitzky-Golay window 11 | DEFER | Points not physical q width; may broaden peaks | Ablation with physical-q width |
| Bremen | q=14 / ROI/gate constants | REJECT generic use | Historical experiment-specific values | Legacy-only reproduction namespace |
| Bremen | historical 15 features | REJECT for chunk encoder | Requires multiple LEFT/RIGHT profiles | Future isolated patient-level adapter |
| Aramina | profile Wasserstein | IDEA_ONLY | Duplicate pairwise concept | One tested production implementation only |
| Aramina | symmetry LEFT/RIGHT | DEFER | Patient/breast-level, not scan chunk | Future experiment |
| Aramina | previous-model logit aggregation | REJECT for corpus encoder | Model-output leakage into physical representation | Future downstream modelling only |
| Aramina | age / age_available | REJECT for physical embedding | Demographic, not XRD physics | Future controlled patient-level model only |
| Aramina | unavailable -> zero | REJECT | Missingness can look identical | Explicit masks/status |
| Aramina | out-of-range `np.interp` | REJECT | Fabricates unsupported q values | Common support only |

## Licensing note

The audit reports no LICENSE in the supplied source trees.

Until permission/license is established:

- do not directly copy non-trivial implementation code;
- independently implement public mathematical formulas;
- preserve provenance in documentation;
- flag licensing as unresolved.
