# Scientific Validation Strategy

## Principle

Shape/order tests are necessary but insufficient.

Each numerical/physical mission should include an independent oracle whenever practical.

## Geometry

Test:

- unrotated synthetic detector geometry;
- tilted geometry;
- beam centre inside, edge, and outside image;
- q unit conversion;
- chi sign/orientation and +/-180 seam;
- image-shape mismatch.

Do not validate geometry only by comparing one pyFAI call to another wrapper around the same call.

## Masks/QC

Test:

- NaN/nonfinite;
- known bad pixel;
- synthetic saturation using explicit detector bound;
- bright but legitimate ring/spot;
- direct-beam core vs suspected halo;
- geometric unobserved region.

## Polar integration

Test:

- constant field;
- analytic/synthetic rings at known q;
- anisotropic arcs in known sectors;
- partial detector coverage;
- masked pixels;
- empty bins;
- axis order and bin edges.

## Features

Use analytic or synthetic profiles for:

- mean/integral;
- Gaussian peak q and FWHM;
- centroid/spread;
- entropy;
- high/low ratio;
- slope;
- peak count;
- invalid/no-peak cases.

Tolerance must reflect physical/numerical resolution, not arbitrary exact equality.

## Similarity

Wasserstein examples:

- identical distributions -> 0;
- delta peaks -> |qa-qb|;
- nonuniform q bins;
- empty/disjoint support;
- negative baseline conversion policy.

Cross-check numerical results against an independent formula or trusted library reference.

## Real-data acceptance

Synthetic success does not equal scientific validation.

When available, include:

- calibrant;
- background/water reference;
- actual 256x256 scan;
- larger detector scan;
- repeated measurements;
- cross-session/cross-detector samples.

## Visualization

Scientific QA should eventually show:

- raw detector image;
- mask overlay with reason codes;
- calibrated q/chi view;
- 16x6 coverage/status map;
- selected 256D profiles with q axes;
- feature values/availability;
- geometry refinement before/after if implemented.
