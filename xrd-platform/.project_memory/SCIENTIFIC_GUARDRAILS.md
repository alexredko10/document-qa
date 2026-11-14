# Scientific Guardrails

These rules are mandatory for all XRD implementation missions.

## Geometry

- Production geometry uses full calibrated detector geometry, preferably pyFAI.
- Do not compute q using only Euclidean pixel radius when `.poni` geometry is available.
- PONI is the point of normal incidence, not automatically the direct-beam intersection for a tilted detector.
- Verify detector shape, axis orientation, binning, pixel size, wavelength, rotations, and q units.
- A claimed `512x726` detector versus an example `Ash512x768` calibration is an unresolved compatibility question until verified.
- Do not resize a larger detector to 256x256 to fit the canonical representation.

## q / chi convention

Canonical v1 uses:

- full angular domain `[-180 deg, 180 deg)`;
- 16 equal angular sectors;
- 6 non-overlapping physical-q bands;
- 256 q samples per band;
- sector-major, band-minor ordering.

Equivalent physical regions must map to the same chunk IDs across scans.

## Canonical dimensions

- sectors: 16
- radial bands: 6
- chunks: 96
- profile length: 256
- physical features: 15
- chunk payload: 271
- scan payload: 26,016

These are an experimental schema contract, not a claim that 26,016 independent physical measurements exist.

## Masks

A future reason-coded mask system should distinguish, where evidence supports it:

- NONFINITE
- DEAD_PIXEL
- HOT_PIXEL
- KNOWN_DETECTOR_DEFECT
- SATURATED
- DIRECT_BEAM_CORE
- BEAM_HALO_SUSPECT
- USER_EXCLUDED
- GEOMETRICALLY_UNOBSERVED
- VALID

Do not detect saturation from an arbitrary global threshold such as intensity > 500.

Do not treat bright real Bragg peaks as defective pixels merely because they are bright.

Do not remove all low-q/SAXS data because some low-q pixels are contaminated.

## Signal, support, coverage, uncertainty

Keep these concepts distinct.

`signal` is measured/corrected intensity.

`support` describes observed contributor weight or evidence.

`coverage` describes explicitly defined geometric/physical coverage relative to a documented reference.

`uncertainty` is only produced when the detector/statistical model justifies it.

pyFAI count/normalization fields are not automatically geometric coverage.

Do not apply Poisson uncertainty blindly to arbitrary postprocessed ADU/background-subtracted signals.

## Intensity handling

- Preserve corrected absolute representation.
- Negative corrected residuals can be physically meaningful after background subtraction.
- Do not globally clip negatives in the absolute representation.
- Nonnegative transforms are allowed only for explicitly defined probability/mass operations.
- Do not silently smooth profiles.
- Any smoothing experiment is versioned and evaluated for peak attenuation/broadening.

## Interpolation

Never fabricate values outside actual q support.

`np.interp` boundary extrapolation is not acceptable for unsupported physical q regions.

Compare only common supported q ranges or preserve missingness explicitly.

## Wasserstein

Wasserstein-1 is a pairwise similarity/distance metric, not a standalone chunk embedding unless a reference distribution is explicitly defined.

For nonuniform q bins, distinguish:

- sample mass;
- intensity density.

If intensity is a density, mass generally requires bin-width weighting.

Units, support, normalization, and negative-baseline handling must be explicit.

## Historical constants

The following are legacy experiment-specific candidates, not universal defaults:

- q = 14 peak assumptions
- q windows around 6.7
- ROI [2,23], [7.5,23], etc.
- Savitzky-Golay window 11
- raw gate 0.6
- bright-pixel threshold 500
- SNR 18 dB

They may exist only in a clearly labelled legacy/reproduction context until scientifically justified for this project.

## Clinical interpretation

Similarity is not disease probability.

Water/Fat is not automatically cancer-specific.

Breast density, inflammation, oedema, fibrosis, instrument/batch, and coverage can confound future disease analyses.

No current corpus code may present a clinical diagnostic claim.
