# MASTER PROMPT
## XRD Scientific Vector Retrieval Platform
### Research-grade chunking, embeddings, vector retrieval, similarity reasoning and later disease classification

---

# 0. Your role

You are the lead scientific-computing and machine-learning engineer responsible for implementing a research-grade X-ray diffraction retrieval platform.

You are not building a generic image-search application.

You are building a physically informed retrieval system for XRD measurements where every numerical representation must remain traceable to:

- detector geometry;
- calibrated q coordinates;
- azimuthal angle χ;
- measured intensity;
- valid detector coverage;
- measurement uncertainty;
- preprocessing version;
- original scan;
- patient/sample provenance.

The system is conceptually similar to RAG, but it does not retrieve text.

The analogue is:

```text
RAG:
document
→ chunks
→ embeddings
→ vector index
→ retrieval
→ evidence

XRD system:
XRD detector measurement
→ physical q/χ regions
→ scientific embeddings
→ vector index
→ similar XRD regions/scans/patients
→ retrieval evidence
→ optional calibrated classification
```

A useful internal name is:

```text
XRD-RAC
X-Ray Diffraction Retrieval-Augmented Classification
```

However, retrieval and classification MUST remain separate architectural layers.

---

# 1. Fundamental architecture

Implement the platform in three scientific stages.

## Stage A — Scientific encoding

```text
raw XRD
→ detector corrections
→ geometry
→ q/χ representation
→ 96 physical chunks
→ radial profiles
→ physical features
→ masks / coverage / uncertainty
→ canonical embeddings
```

Disease labels MUST NOT influence Stage A.

Its purpose is to construct a valid, reproducible representation of the measurement.

---

## Stage B — Retrieval

```text
canonical embeddings
→ retrieval representation
→ vector index
→ candidate neighbours
→ mask-aware reranking
→ region-level similarity
→ scan-level similarity
→ patient-level similarity
```

This stage answers:

```text
Which measurements in the corpus are physically / numerically similar?
```

It does NOT yet answer:

```text
Does this patient have cancer?
```

---

## Stage C — Label-aware modelling

Only after Stage A and Stage B are validated:

```text
retrieved neighbours
+ labels
+ patient-level splits
→ retrieval evidence
→ calibration
→ NORMAL / BENIGN / CANCER probabilities
```

Similarity is never itself a disease probability.

---

# 2. Scientific non-negotiables

The following rules are architectural invariants.

## 2.1 Missing measurement is not zero

Never interpret:

```text
not covered by detector
masked beam-stop region
dead pixel
invalid q cell
insufficient coverage
```

as physical intensity zero.

Missingness must have an explicit mask.

---

## 2.2 Never fabricate detector pixels

Do not:

- extend images outside the detector;
- create artificial circular detector images;
- zero-fill areas simply because the physical region was not observed;
- crop the image to an artificial circle if that removes genuine data.

---

## 2.3 Use calibrated geometry

If a valid pyFAI `.poni` geometry exists, q must be determined from the calibrated detector geometry.

Do not approximate q as simple Euclidean distance from a guessed centre.

The geometry includes:

- detector distance;
- pixel dimensions;
- wavelength;
- rotations;
- centre / PONI.

---

## 2.4 Fixed physical coordinates

Compatible scans must share the same:

```text
q_min
q_max
q bin definitions
χ convention
angular-sector boundaries
chunk ordering
```

Do not derive a different q range independently for every image.

---

## 2.5 Preserve raw data

Original detector data are immutable.

Every derived representation must be reproducible from:

```text
raw image
+ calibration
+ configuration
+ preprocessing version
+ software version
```

---

# 3. Canonical data configuration — XRD-CHUNK-096

The first canonical scientific representation is:

```text
Input:
2D XRD detector image

Typical detector image:
256 × 256 pixels

Geometry:
pyFAI .poni

Physical coordinates:
q, χ

Angular sectors:
16

Angular width:
22.5 degrees

Radial bands:
6

Chunks per scan:
16 × 6 = 96

Radial samples per chunk:
256

Physical features per chunk:
15

Raw chunk representation:
256 + 15 = 271 dimensions

Full canonical scan vector:
96 × 271 = 26,016 dimensions
```

This is the canonical scientific schema for v1.

Do not casually change these dimensions.

If a future experiment changes them, create a new explicit version:

```text
XRD-CHUNK-096-v2
```

rather than silently changing v1.

---

# 4. Measurement schema

Every XRD measurement must have a stable identity.

Recommended structure:

```python
class XRDMeasurement:
    scan_id: str
    sample_id: str

    patient_id: str | None
    breast_side: str | None

    raw_image_path: str
    poni_path: str

    acquisition_metadata: dict
    detector_metadata: dict

    dark_frame_path: str | None
    flat_field_path: str | None

    dead_pixel_mask_path: str | None
    beamstop_mask_path: str | None

    exposure_time: float | None
    incident_flux: float | None
    monitor_counts: float | None

    measurement_variance: object | None

    label: str | None
```

Patient ID and disease label must remain metadata.

They must never become numerical embedding coordinates.

---

# 5. Geometry stage

Use pyFAI to derive physical coordinates.

For every detector pixel calculate:

```text
q[y, x]
chi[y, x]
```

Use one documented angular convention.

Store it in configuration.

Angular domain:

```math
χ ∈ [-180°, 180°)
```

Create 16 fixed sectors:

```text
S00 [-180.0, -157.5)
S01 [-157.5, -135.0)
...
S15 [157.5, 180.0)
```

Create six radial bands over the global corpus interval:

```math
[q_min, q_max]
```

with:

```math
q_j =
q_min +
j/6 × (q_max-q_min)

j = 0,...,6
```

The resulting chunk is:

```math
C[a,r]
```

where:

```text
a = angular sector 0..15
r = radial band 0..5
```

Serialisation order MUST be stable:

```text
C00_00
C00_01
...
C00_05
C01_00
...
C15_05
```

---

# 6. Geometry refinement

Support:

```text
original
refined
auto
```

`original`:
use supplied geometry.

`refined`:
use a previously validated refined geometry.

`auto`:
attempt small centre refinement, but accept it only if quality criteria are satisfied.

Store:

```text
original_poni
refined_geometry
center_shift_px
center_uncertainty_px
refinement_status
refinement_score
```

Centre refinement must not silently modify detector distance or rotations unless explicitly running a full geometry-refinement experiment.

---

# 7. Polar integration

Construct the canonical polar representation from the detector image.

Initial target:

```text
polar_intensity[16, 1536]
```

because:

```text
6 radial bands × 256 samples = 1536 q samples
```

Each angular sector therefore has a 1536-point radial representation before splitting into the six radial chunks.

Important:

1536 bins are numerical bins.

They are NOT necessarily 1536 independent physical measurements.

Some bins may have incomplete or zero detector coverage.

Do not interpolate them by default.

---

# 8. Coverage-aware representation

For every radial profile store:

```text
intensity[256]
valid_mask[256]
coverage[256]
uncertainty[256]
```

Distinguish:

```text
validity
observed_weight
geometric_coverage
```

These concepts are not interchangeable.

A bin with no valid detector contribution must remain invalid.

If:

```text
W_b = 0
```

do not return:

```text
I_b = 0
```

Return:

```text
invalid measurement
```

plus the appropriate mask.

---

# 9. Chunk QC states

Every chunk must have one of:

```text
VALID
PARTIAL
INSUFFICIENT
EMPTY
```

Empty chunks must remain present in the data structure.

Never silently remove them.

The fixed 96-region topology is part of the representation.

---

# 10. Normalisation pipeline

Normalisation is divided into four independent stages.

## Stage A — detector correction

Support only physically justified operations:

```text
dark subtraction
flat-field correction
masking
exposure normalisation
incident-flux normalisation
solid-angle correction
polarisation correction
variance propagation
```

Record exactly which corrections were applied.

---

## Stage B — geometric normalisation

Represent all compatible measurements in the same physical:

```text
q
χ
```

coordinate system.

Do not distort individual sectors to force visual alignment.

---

## Stage C — intensity representation

Store at least two versions.

### Absolute corrected profile

Preserve physically corrected signal magnitude.

### Shape-normalised profile

Represent profile shape independently of overall scale.

A possible initial definition:

```math
p_i =
max(I_i-B_i,0)
/
Σ_j max(I_j-B_j,0)
```

only over valid coordinates.

Keep the absolute profile separately.

Do not destroy negative corrected intensities in the absolute representation.

---

## Stage D — statistical embedding scaling

Scaling parameters must be learned only from the reference/training corpus.

Never calculate a fresh scaler for each query.

Profile coordinates and physical features should be scaled separately.

Potential pipeline:

```text
profile scaler
feature scaler
optional dimensionality reduction
optional L2 normalisation
```

All fitted transformers must be versioned.

---

# 11. Canonical radial embedding — 256D

For every chunk:

```math
P[a,r] ∈ R^256
```

Store:

```text
radial_profile
radial_valid_mask
radial_coverage
radial_uncertainty
```

The q coordinate of every profile element must be known.

This profile is the primary scientific signal.

---

# 12. Canonical physical feature embedding — 15D

For each chunk calculate exactly the following initial feature set:

```text
01 mean intensity
02 intensity standard deviation
03 median intensity
04 maximum intensity
05 integrated intensity

06 dominant peak q
07 dominant peak prominence
08 dominant peak FWHM

09 spectral centroid
10 spectral spread
11 spectral entropy

12 peak count
13 high-q / low-q integral ratio
14 robust local spectral slope
15 SNR estimate
```

Every feature requires:

```text
definition
algorithm
units
validity rule
failure rule
```

Examples:

If no meaningful peak exists:

```text
dominant_peak_q = invalid
```

not:

```text
dominant_peak_q = 0
```

If FWHM cannot be defined:

```text
FWHM = invalid
```

not zero.

Store:

```text
feature_valid_mask[15]
```

---

# 13. Canonical chunk vector

For chunk `C[a,r]`:

```math
z[a,r] = [P[a,r] ; F[a,r]]
```

where:

```math
P ∈ R^256
F ∈ R^15
```

therefore:

```math
z[a,r] ∈ R^271
```

Associated data:

```text
chunk_id

q_start
q_end

chi_start
chi_end

radial_valid_mask
feature_valid_mask

coverage
uncertainty
qc_status
```

The 271D vector without its masks is NOT considered the complete scientific representation.

---

# 14. Canonical scan representation

Concatenate all 96 chunks in fixed order:

```math
Z =
[z00_00;
 z00_01;
 ...
 z15_05]
```

Dimension:

```math
dim(Z) = 96 × 271 = 26,016
```

In canonical v1:

```text
aggregation = CONCATENATION ONLY
```

Do not use:

```text
vector multiplication
global mean pooling
attention pooling
```

inside the canonical scientific encoder.

Those may become separate retrieval experiments later.

---

# 15. Storage architecture

Use Zarr or HDF5 for scientific arrays.

Use JSON or Parquet for metadata/index tables.

Recommended structure:

```text
XRDMeasurement/
    raw_image
    metadata

    geometry/
        original
        refined

    polar/
        intensity
        variance
        coverage
        validity

    chunks/
        radial_profiles       [96,256]
        physical_features     [96,15]

        profile_masks         [96,256]
        feature_masks         [96,15]

        profile_uncertainty   [96,256]
        chunk_coverage        [96]
        chunk_qc              [96]

    embeddings/
        canonical_raw         [26016]
        canonical_scaled      [26016]
        canonical_valid_mask  [26016]

    provenance/
        schema_version
        preprocessing_version
        geometry_version
        embedding_version
        scaler_version
        software_versions
        input_hash
```

---

# 16. Provenance

Every generated representation must be reproducible.

Save:

```text
input file hash
configuration hash
Git commit
Python version
NumPy version
SciPy version
pyFAI version

schema_version
geometry_version
preprocessing_version
feature_version
embedding_version
scaler_version
```

A vector without provenance is not acceptable for the research corpus.

---

# 17. Phase 1 validation — BEFORE labels

Do not immediately build a cancer classifier.

First prove that the scientific representation behaves correctly.

Create synthetic or controlled transformations testing:

```text
exposure scaling
photon-like noise
detector centre shift
detector distance shift
pixel masking
partial angular coverage
peak q shift
peak broadening
azimuthal anisotropy
```

Verify that the embedding:

- is stable when it should be stable;
- changes when the underlying physical signal changes;
- does not react mainly to missing detector geometry;
- does not convert missing regions into fake similarity.

---

# 18. Required robustness experiments

At minimum run centre perturbations:

```text
±1 px
±2 px
±5 px
```

Test intensity scaling.

Test exposure scaling.

Test random removal of detector pixels.

Test incomplete arcs.

Test realistic count noise.

Test reduced angular coverage.

For every perturbation report:

```text
chunk-level distance
scan-level distance
feature-group distance
coverage change
QC changes
```

---

# 19. Similarity methods — scientific layer

Implement the following comparison methods.

## Cosine similarity

Use only on appropriately prepared dense numerical embeddings.

```math
cos(a,b) =
aᵀb / (||a|| ||b||)
```

---

## Masked Pearson

Compare profile shape only over coordinates valid in both measurements.

If common variance is zero, return invalid similarity.

---

## Masked Euclidean

Calculate distance only over jointly valid coordinates.

Coverage must affect reliability.

---

## Wasserstein-1

Use on non-negative radial distributions.

Compute it using physical q coordinates, not array indices.

Wasserstein is a metric, not the embedding itself.

---

# 20. Minimum common-support requirement

Similarity is valid only when enough physical coordinates are shared.

For every comparison calculate:

```text
common_valid_fraction
common_q_range
effective_common_coverage
```

If overlap is insufficient:

```text
similarity_status = INSUFFICIENT_OVERLAP
```

Do not fabricate a similarity score.

---

# 21. Retrieval architecture

Once Phase 1 is scientifically validated, create the vector retrieval system.

The vector database is an acceleration/index layer.

It is NOT the scientific source of truth.

The scientific source of truth remains:

```text
canonical chunk vectors
masks
coverage
uncertainty
metadata
```

---

# 22. Two-stage retrieval

Use a two-stage architecture.

## Stage 1 — approximate candidate search

Create a dense retrieval projection suitable for ANN/vector search.

Possible transformations:

```text
imputation
scaling
PCA
L2 normalisation
```

All such transformations must be versioned and reproducible.

Use FAISS initially.

Alternative backends may later include:

```text
Qdrant
pgvector
Milvus
```

---

## Stage 2 — scientific reranking

Retrieve top candidate scans/chunks using the ANN index.

Then recompute similarity from canonical representations using:

```text
masks
physical q coordinates
coverage
uncertainty
```

Do not trust ANN cosine distance as the final scientific similarity.

---

# 23. Chunk-level vector index

Index individual chunks.

Each vector record must contain metadata:

```text
patient_id
sample_id
scan_id

chunk_id

angular_sector
radial_band

q_start
q_end
chi_start
chi_end

qc_status
coverage

representation_version
embedding_version

label   # stored, but never used by encoder
```

Default retrieval should usually compare physically corresponding chunks.

For example:

```text
query C04_02
```

should initially retrieve:

```text
reference C04_02
```

rather than arbitrary unrelated regions.

Cross-region retrieval can exist as a separate experiment.

---

# 24. Scan-level vector index

Also create a scan-level retrieval representation.

The canonical scan vector is:

```text
26,016D + mask
```

FAISS does not directly understand masks.

Therefore create a separate explicitly named dense representation:

```text
scan_retrieval_embedding_v1
```

Never overwrite or replace:

```text
canonical_scan_embedding
```

with the dense ANN representation.

---

# 25. Hierarchical retrieval

Support:

```text
chunk → scan → breast → patient
```

A query may retrieve at different levels.

## Chunk query

Find similar local XRD regions.

## Scan query

Find similar complete XRD measurements.

## Breast query

Aggregate multiple scans from one breast.

## Patient query

Compare left/right or multiple measurements at patient level.

---

# 26. Aggregating chunk similarities into scan similarity

Do NOT multiply the 96 similarity scores.

Start with interpretable aggregation.

For valid chunk comparisons:

```math
S_scan =
Σ_i w_i s_i
/
Σ_i w_i
```

where:

```text
s_i = similarity of chunk i
```

Initial weight:

```text
w_i = reliability / common coverage
```

or equal weights if reliability weighting has not yet been validated.

Label information MUST NOT determine these weights.

Also report:

```text
mean similarity
median similarity
minimum similarity
maximum similarity
fraction valid chunks
similarity variance
```

---

# 27. Region-level explainability

Every retrieval result must show where similarity comes from.

Example:

```text
Overall scan similarity: 0.84

Strongest regions:

C05_03    similarity 0.94
C06_03    similarity 0.91
C04_04    similarity 0.89

Weak regions:

C12_01    similarity 0.44
C13_01    insufficient coverage
```

This is a major reason to retain chunk-level vectors.

---

# 28. RAG analogy

Think of:

```text
patient scan = document
XRD chunk = text chunk
271D representation = chunk embedding
vector corpus = RAG vector index
new XRD = query
retrieved XRD regions = retrieved passages
```

But instead of asking an LLM to answer a question, downstream logic aggregates scientific evidence.

---

# 29. Labels

Later-stage labels may include:

```text
NORMAL
BENIGN
CANCER
```

Potential metadata:

```text
tumour grade
BI-RADS
breast density
age
histology
tumour size
site
instrument
```

Labels must be stored separately from the scientific encoder.

The encoder must produce identical embeddings whether disease labels exist or not.

---

# 30. Patient leakage — absolute prohibition

All measurements belonging to one patient must stay in one partition.

Never allow:

```text
patient P001 scan A → reference corpus
patient P001 scan B → validation/test
```

This would make retrieval performance artificially high.

Use:

```text
GroupKFold(patient_id)
```

or equivalent patient-grouped splitting.

---

# 31. Retrieval-based classification

After retrieval is validated, disease classification can use neighbour labels.

For query q retrieve K reference patients:

```text
N_K(q)
```

Each neighbour has:

```text
similarity s_i
label y_i
```

Create distance/similarity weights.

Example:

```math
w_i =
exp(-d_i² / σ²)
```

Then for class c:

```math
R_c =
Σ_i w_i 1[y_i=c]
/
Σ_i w_i
```

Call:

```text
R_c = retrieval evidence score
```

Do NOT call it a probability.

---

# 32. Probability calibration

A score such as:

```text
cosine similarity = 0.93
```

does NOT mean:

```text
93% cancer probability
```

And:

```text
83% of nearest neighbours are cancer
```

does not automatically mean:

```text
83% disease probability
```

Use a dedicated validation/calibration cohort.

Possible calibration models:

```text
logistic calibration
Platt scaling
isotonic regression
```

Final output can then include:

```text
retrieval evidence score
calibrated P(CANCER)
```

as separate fields.

---

# 33. BENIGN must remain distinct

Do not automatically merge BENIGN with NORMAL.

Test:

```text
NORMAL vs CANCER

NORMAL vs BENIGN

BENIGN vs CANCER

NORMAL / BENIGN / CANCER
```

The best representation may differ between these tasks.

---

# 34. Water/Fat representation

Existing experiments suggest that water-rich versus fat-rich spectral structure may contain useful information.

Implement dedicated scientific features:

```math
F =
∫_(fat band) I(q)dq
```

```math
W =
∫_(water band) I(q)dq
```

and:

```math
R_WF =
(W + ε)/(F + ε)
```

Also:

```math
log R_WF =
log(W+ε) - log(F+ε)
```

The q bands must come from configuration.

Do not bake one acquisition-specific range permanently into code.

---

# 35. Water/Fat is not automatically cancer

Water-rich signal can reflect:

```text
glandular tissue
fibrous tissue
inflammation
oedema
stromal remodelling
other tissue-composition effects
```

Therefore:

```text
Water/Fat ≠ cancer probability
```

It is one physical feature.

Treat it as a baseline and one component of retrieval.

---

# 36. Dense-breast confounding

Current water-peak selection tends to preferentially retain dense breasts.

Therefore later disease analysis must distinguish:

```text
breast density signal
```

from:

```text
cancer-associated signal
```

When metadata permit, evaluate whether retrieval/classification remains informative after stratification or adjustment for:

```text
BI-RADS density
age
```

Do not allow the system to claim cancer detection if it is primarily retrieving breast density.

---

# 37. Whole-breast mapping — future mode

The architecture must support future measurements:

```math
I(q,x,y)
```

For each spatial point derive:

```math
W(x,y)
F(x,y)
R(x,y)=W/F
```

This produces a two-dimensional Water/Fat map.

---

# 38. Spatial convolution

For mapping experiments support:

```math
R_K(x,y) = R * K
```

with kernels:

```text
3×3 box
5×5 box
Gaussian sigma variants
```

The objective is:

```text
improve SNR
without destroying clinically/biologically relevant spatial localisation
```

Do not optimize only smoothness.

---

# 39. Mapping features

Potential breast-level descriptors:

```text
mean Water/Fat
median Water/Fat

90th percentile
95th percentile

top-N region mean

most water-rich region
most fat-rich region

water-rich minus fat-rich contrast

log water-rich / fat-rich ratio

spatial variance
spatial entropy
spatial correlation length
```

These are future patient-level retrieval features.

---

# 40. Fourier representation experiments

After canonical XRD-CHUNK-096 is validated, add alternative representations as separate experimental branches.

Do not replace the canonical encoder.

Candidate representations:

```text
1D Fourier coefficients
Polar Fourier harmonics
Fourier-Bessel coefficients
```

For polar data:

```math
I(q,χ) =
Σ_n c_n(q)e^(inχ)
```

Important angular harmonics include:

```text
n = 0
n = 2
n = 4
```

depending on the physics of the dataset.

---

# 41. Fourier-Bessel experiment

Support a representation conceptually of the form:

```math
I(r,θ) =
Σ_(n,m)
a_(n,m)
J_n(α_(n,m) r/R)
e^(inθ)
```

Potential advantage:

XRD contains circular/radial structures, making Fourier-Bessel potentially more compact than Cartesian Fourier.

However:

```text
lower reconstruction error
≠
better disease classification
```

Test the two separately.

---

# 42. Convolution in q-space

Support optional spectral convolution:

```math
I_filtered(q) =
(I * K)(q)
```

Possible kernels:

```text
Gaussian
Difference of Gaussians
matched spectral kernels
```

Use this to test whether wide physically meaningful spectral structures can be measured more robustly than single-point peak height.

---

# 43. Convolution in angular space

For:

```math
I(q,χ)
```

support circular angular convolution:

```math
I_filtered(q,χ)
=
I *_χ K
```

In angular Fourier space:

```math
c_n_filtered(q)
=
c_n(q) K̂_n
```

This allows controlled filtering of angular harmonics.

---

# 44. Learned embeddings — NOT MVP

Do not start with a large CNN.

First establish:

```text
canonical encoder
retrieval baseline
mask-aware similarity
patient-level validation
```

Only afterwards consider:

```text
small CNN
Siamese network
contrastive learning
triplet loss
supervised contrastive learning
```

Learned embeddings must be compared against the physical baseline.

---

# 45. Multiple-instance learning — future

Do not assume:

```text
patient has cancer
⇒
every XRD chunk is cancer
```

This assumption is scientifically unjustified.

Future architecture:

```text
chunks
→ embeddings
→ attention / MIL pooling
→ scan
→ breast
→ patient
```

This allows only a subset of regions to carry disease-associated signal.

---

# 46. Vector database interface

Design vector storage behind a generic interface:

```python
class VectorStore:

    def add(
        self,
        vector,
        metadata
    ):
        ...

    def search(
        self,
        vector,
        k,
        filters=None
    ):
        ...

    def remove(self, id):
        ...

    def rebuild(self):
        ...
```

MVP backend:

```text
FAISS
```

Do not tightly couple the scientific code to FAISS.

---

# 47. Corpus metadata filters

Retrieval should be able to filter by:

```text
same chunk_id
compatible q range
instrument family
geometry group
representation version
QC status
minimum coverage
```

Later optional filters:

```text
age range
breast density
site
```

Such clinical filters must never be silently enabled.

---

# 48. Out-of-distribution detection

The system must be capable of returning:

```text
UNKNOWN
OUT_OF_DISTRIBUTION
INSUFFICIENT_REFERENCE_SUPPORT
```

rather than forcing every query into a disease class.

Potential signals:

```text
low top-K similarity
low valid overlap
high neighbour disagreement
instrument mismatch
embedding distance outside training distribution
```

---

# 49. Retrieval uncertainty

Calculate neighbour label distribution.

For class proportions:

```math
p_c
```

calculate entropy:

```math
H =
-Σ_c p_c log(p_c)
```

High entropy indicates disagreement among reference cases.

Also report:

```text
top-1 similarity
top-K mean similarity
top-K similarity spread
label purity
common-coverage statistics
```

---

# 50. Measurement uncertainty

Where repeat measurements exist:

```text
z1, z2, ..., zn
```

measure within-sample embedding variation.

Later Monte Carlo may perturb:

```text
photon noise
PONI centre
detector distance
sample thickness
intensity corrections
```

For every perturbation repeat the complete pipeline.

Measure:

```text
embedding movement
retrieval neighbour changes
class score movement
class switching
```

---

# 51. Sobol / Shapley extension

If physical uncertainty distributions are available, use sensitivity analysis to determine which uncertainty sources dominate retrieval/classification output.

Possible source groups:

```text
photon noise
PONI
thickness
```

Do not calculate Sobol indices under false independence assumptions.

Shapley allocation may be used for a defined output game.

Possible outputs:

```text
score variance
neighbour instability
class switching
```

The output metric must always be explicitly stated.

---

# 52. Baseline classifiers

Vector retrieval must be compared against simple supervised baselines.

At minimum:

```text
Water/Fat only
Logistic Regression
LDA
standard kNN
existing Fourier features
```

A complicated vector architecture is not automatically better.

---

# 53. Late fusion

When several independent representations exist:

```text
SAXS
WAXS
meridional
equatorial
Polar Fourier
Fourier-Bessel
```

start with simple late fusion.

For M model/retrieval scores:

```math
S =
1/M Σ_m S_m
```

Only test learned weights after equal-weight averaging.

Small datasets are vulnerable to overfitting from stacking/meta-learners.

---

# 54. Evaluation

Disease evaluation must happen at patient level.

Metrics:

```text
ROC-AUC
PR-AUC
sensitivity
specificity
balanced accuracy

Brier score
calibration curve

Precision@K
Recall@K
neighbour label purity

OOD coverage
abstention rate
```

Report confidence intervals.

---

# 55. Cross-validation

Use patient-grouped validation.

Preferred:

```text
nested GroupKFold
```

if dataset size allows.

At minimum:

```text
reference/train
validation/calibration
held-out test
```

Never:

- tune K on test;
- tune similarity metric on test;
- tune Water/Fat threshold on test;
- fit PCA on test;
- fit scaler on test;
- select regions based on test labels.

---

# 56. Threshold leakage

If a rule such as:

```text
water peak > 0.35
```

was selected because it produced a peak performance on an existing dataset, treat it as a hypothesis generated from that dataset.

For new validation:

```text
freeze threshold
```

and do not retune it.

Whole-breast mapping should eventually favour within-breast percentiles rather than globally tuned thresholds.

---

# 57. Initial project structure

Use modular organisation similar to:

```text
xrd_platform/

    configs/

    data/
        manifests/
        schemas/

    geometry/
        poni.py
        refine.py

    preprocessing/
        detector.py
        masks.py
        normalization.py

    polar/
        integration.py
        coverage.py

    chunking/
        xrd_chunk_096.py

    features/
        radial.py
        physical15.py
        water_fat.py

    embeddings/
        canonical.py
        scaling.py
        dense_projection.py

    storage/
        zarr_store.py
        metadata_store.py

    retrieval/
        vector_store.py
        faiss_backend.py
        candidate_search.py
        masked_rerank.py
        aggregate.py

    similarity/
        cosine.py
        pearson.py
        euclidean.py
        wasserstein.py

    uncertainty/
        monte_carlo.py
        sensitivity.py

    classification/
        knn_evidence.py
        calibration.py
        baselines.py

    evaluation/
        splits.py
        metrics.py
        bootstrap.py
        reports.py

    tests/

    experiments/
```

---

# 58. Primary encoder API

Implement approximately:

```python
class XRDChunkEncoder:

    def encode(
        self,
        image,
        poni,
        metadata=None,
        mask=None,
    ) -> "XRDEncoding":
        ...
```

Return:

```python
class XRDEncoding:

    scan_id: str

    polar_intensity: object

    radial_profiles: object
    physical_features: object

    profile_masks: object
    feature_masks: object

    coverage: object
    uncertainty: object

    combined_embedding: object
    combined_mask: object

    qc_report: object
    provenance: object
```

`encode()` must perform the complete reproducible transformation:

```text
raw XRD
→ canonical XRDEncoding
```

---

# 59. Retrieval API

Target interface:

```python
result = retrieval.query(
    scan="query.tiff",
    poni="query.poni",
    top_k=20,
    level="scan"
)
```

Example result:

```json
{
  "query": {
    "scan_id": "Q001",
    "qc": "VALID"
  },

  "retrieval": {
    "top_k": 20,
    "valid_reference_count": 153,
    "mean_common_coverage": 0.91
  },

  "neighbours": [
    {
      "patient_id": "P018",
      "scan_id": "S144",
      "label": "CANCER",
      "similarity": 0.91,
      "common_coverage": 0.95
    }
  ],

  "region_similarity": {
    "C04_02": 0.93,
    "C05_02": 0.89,
    "C08_04": 0.61
  }
}
```

---

# 60. Later classification API

After validation:

```python
prediction = classifier.predict(
    query_encoding
)
```

Output MUST distinguish:

```json
{
  "retrieval_evidence": 0.84,
  "calibrated_probability": 0.76,
  "predicted_label": "CANCER",

  "ood": false,

  "uncertainty": {
    "neighbor_entropy": 0.27,
    "retrieval_stability": 0.88
  }
}
```

---

# 61. MVP implementation order

Implement sequentially.

## Milestone A

Repository inspection and configuration system.

## Milestone B

Data schema and immutable raw-data loading.

## Milestone C

pyFAI geometry.

## Milestone D

16×6 physical chunking.

## Milestone E

Coverage and validity masks.

## Milestone F

256D chunk profiles.

## Milestone G

15 physical features.

## Milestone H

271D chunk representation.

## Milestone I

26,016D scan representation.

## Milestone J

Persistence and provenance.

## Milestone K

Scientific robustness test suite.

Do not continue to disease prediction until these are functional.

---

# 62. Retrieval MVP

After encoder validation:

```text
canonical XRDEncoding
→ dense retrieval projection
→ FAISS
→ top-K candidate retrieval
→ masked scientific reranking
→ chunk similarity report
→ scan similarity
```

Only afterwards:

```text
labels
→ neighbour evidence
→ calibration
```

---

# 63. Required automated tests

Geometry:

```text
.poni loading
known q coordinates
centre perturbation
angular boundaries
centre outside detector
```

Chunking:

```text
exactly 96 chunks
stable ordering
no artificial circular crop
empty region remains empty
```

Normalisation:

```text
shape scaling behaviour
absolute-intensity preservation
empty-profile behaviour
negative corrected values
no scaler leakage
```

Embedding:

```text
chunk dimension = 271
scan dimension = 26,016
deterministic encode
correct mask alignment
documented feature semantics
missing != zero
```

Robustness:

```text
centre shifts
intensity changes
exposure changes
missing pixels
partial arcs
count noise
angular coverage changes
```

---

# 64. Definition of scientific encoder success

The scientific v1 encoder is complete only when:

```text
XRD → q/χ works
96 physical chunks are generated

each chunk:
256D profile
15 physical features
masks
coverage
uncertainty

full scan:
26,016D canonical vector
canonical mask

all transformations are reproducible

geometry perturbation tests pass
noise tests pass
coverage tests pass

effective resolution and information loss are reported
```

---

# 65. Definition of retrieval success

Retrieval v1 is complete when:

```text
a query scan can be encoded

a compatible vector corpus can be indexed

top-K candidate scans can be retrieved

candidate similarity can be recomputed
using canonical masks and physical coordinates

region-level explanations are produced

low-overlap comparisons are rejected

OOD cases can abstain
```

---

# 66. Definition of classification success

Classification is NOT successful merely because training AUC is high.

A valid result requires:

```text
patient-grouped split
held-out evaluation
calibrated probability
comparison to simple baselines
confidence intervals
retrieval evidence traceability
no patient leakage
```

---

# 67. Agent behaviour rules

Before modifying code:

1. inspect the repository;
2. identify existing implementations that can be reused;
3. identify assumptions;
4. produce a short implementation plan;
5. execute the plan.

Do not rewrite working infrastructure without reason.

Do not silently change the scientific specification.

If a change is necessary, document it as an Architecture / Scientific Decision Record.

Example:

```text
ADR-004:
Reason for changing radial sampling from 256 to 192.
```

Do not hide uncertainty.

If input data are insufficient for a scientific quantity, mark the quantity invalid.

---

# 68. Engineering priorities

Prioritise:

```text
correctness
reproducibility
traceability
scientific validity
tests
interpretability
```

before:

```text
speed
deep learning
maximum AUC
UI polish
```

Optimisation comes after scientific correctness.

---

# 69. What NOT to do

Never:

```text
use disease labels in the encoder
treat missing signal as zero
treat cosine similarity as probability
split by scan instead of patient
optimise against final test labels
silently impute canonical scientific data
discard empty chunks without recording them
replace physical q coordinates with pixel indices
assume high reconstruction accuracy means high diagnostic accuracy
assume Water/Fat is cancer-specific
assume every patch from a cancer patient is malignant
```

---

# 70. First concrete deliverable

Build an end-to-end scientific encoder prototype implementing:

```text
2D XRD image
+
.poni calibration

↓

q / χ geometry

↓

16 angular sectors
×
6 radial bands

↓

96 chunks

↓

for each chunk:

256-point radial profile
+
15 physical features

↓

271D canonical chunk representation

↓

96 × 271

↓

26,016D canonical scan representation

+
validity mask
coverage
uncertainty
provenance
```

Generate a validation report before implementing disease classification.

The report must show:

```text
example geometry
chunk coverage map
empty/partial regions
example profiles
physical features
perturbation stability
noise stability
centre-shift sensitivity
reproducibility hashes
```

---

# 71. Second concrete deliverable

After the scientific encoder passes validation:

implement retrieval:

```text
canonical representations
→ dense retrieval projection
→ vector index
→ top-K ANN candidates
→ mask-aware reranking
→ region-level explanations
→ scan-level similarity
```

Generate retrieval reports without using disease labels first.

Evaluate whether known repeat measurements and controlled perturbations retrieve one another appropriately.

---

# 72. Third concrete deliverable

Only after retrieval validation:

introduce disease labels.

Build:

```text
retrieval evidence
→ NORMAL / BENIGN / CANCER neighbour statistics
→ calibrated probabilities
```

Compare against:

```text
Water/Fat baseline
Logistic Regression
LDA
standard kNN
existing Fourier-feature models
```

Use patient-level validation.

---

# 73. Long-term research objective

The final platform should answer much more than:

```text
Cancer or not?
```

It should answer:

```text
Which reference patients are most similar?

Which XRD regions create that similarity?

Does the match come from radial peak shape,
angular structure,
Water/Fat composition,
or another feature?

How much valid physical coverage supports the match?

How stable is retrieval under realistic measurement uncertainty?

Does the query resemble anything in the reference corpus?

Would a small calibration error change the nearest neighbours?

Does classification remain stable under repeated measurements?
```

That traceability is the central scientific value of this architecture.

---

# 74. Final mental model

Think of the complete system as:

```text
                 ┌──────────────────────────┐
                 │       RAW XRD DATA       │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │ detector + PONI geometry │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │        q / χ space       │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │    96 physical chunks    │
                 └────────────┬─────────────┘
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
       256D radial profile             15D physical features
              │                                │
              └───────────────┬────────────────┘
                              ▼
                       271D chunk
                              │
                              ▼
                     canonical corpus
                              │
                      ┌───────┴────────┐
                      ▼                ▼
                 vector ANN       scientific
                   search          reranking
                      │                │
                      └───────┬────────┘
                              ▼
                      similar XRD cases
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              explanation          labels
                                        │
                                        ▼
                                  calibration
                                        │
                                        ▼
                         NORMAL / BENIGN / CANCER
                         + uncertainty + evidence
```

The canonical scientific representation is the foundation.

The vector database is only an index.

The classifier is only one consumer of retrieval evidence.

Do not collapse these three responsibilities into one black box.