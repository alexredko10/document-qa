"""Scientific data contracts for the canonical encoder output (AGENT_SPEC §4, §8–§14).

The validity mask is authoritative: values in invalid slots carry no meaning
(any fill, e.g. 0.0 or NaN) and validity is never inferred from numbers.
Valid slots must hold finite values.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from app.xrd.config import ChunkId, XRDChunkConfig


class ChunkQCStatus(Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    EMPTY = "EMPTY"


@dataclass(frozen=True, kw_only=True)
class XRDMeasurement:
    """Stable identity and provenance of one raw measurement. Labels/patient IDs stay metadata."""

    scan_id: str
    sample_id: str
    raw_image_path: str
    poni_path: str
    patient_id: str | None = None
    breast_side: str | None = None
    acquisition_metadata: dict[str, Any] = field(default_factory=dict)
    detector_metadata: dict[str, Any] = field(default_factory=dict)
    dark_frame_path: str | None = None
    flat_field_path: str | None = None
    dead_pixel_mask_path: str | None = None
    beamstop_mask_path: str | None = None
    exposure_time: float | None = None
    incident_flux: float | None = None
    monitor_counts: float | None = None
    measurement_variance: object | None = None
    label: str | None = None


def _check_masked(name: str, values: np.ndarray, mask: np.ndarray) -> None:
    if values.ndim != 1 or values.shape != mask.shape:
        raise ValueError(f"{name}: values {values.shape} and mask {mask.shape} must be equal 1-D shapes")
    if mask.dtype != np.bool_:
        raise ValueError(f"{name}: mask must be bool, got {mask.dtype}")
    if not np.isfinite(values[mask]).all():
        raise ValueError(f"{name}: values must be finite where the mask is True")


@dataclass(frozen=True, kw_only=True)
class XRDChunkEncoding:
    chunk_id: ChunkId
    q_start: float
    q_end: float
    chi_start_deg: float
    chi_end_deg: float
    radial_profile: np.ndarray
    radial_valid_mask: np.ndarray
    radial_coverage: np.ndarray
    radial_uncertainty: np.ndarray
    features: np.ndarray
    feature_valid_mask: np.ndarray
    qc_status: ChunkQCStatus

    def __post_init__(self) -> None:
        _check_masked("radial_profile", self.radial_profile, self.radial_valid_mask)
        _check_masked("features", self.features, self.feature_valid_mask)
        for name in ("radial_coverage", "radial_uncertainty"):
            if getattr(self, name).shape != self.radial_profile.shape:
                raise ValueError(f"{name} must match radial_profile shape {self.radial_profile.shape}")
        if not self.q_start < self.q_end:
            raise ValueError(f"q_start {self.q_start} must be < q_end {self.q_end}")


@dataclass(frozen=True, kw_only=True)
class XRDEncoding:
    """All chunks of one scan in canonical order; empty chunks stay present (§9)."""

    scan_id: str
    config: XRDChunkConfig
    chunks: tuple[XRDChunkEncoding, ...]

    def __post_init__(self) -> None:
        ids = tuple(c.chunk_id for c in self.chunks)
        if ids != self.config.chunk_ids():
            raise ValueError(f"chunks must be exactly {self.config.n_chunks} chunks in canonical order")
        for c in self.chunks:
            if c.radial_profile.shape != (self.config.radial_samples,):
                raise ValueError(f"{c.chunk_id}: expected {self.config.radial_samples} radial samples")
            if c.features.shape != (self.config.n_features,):
                raise ValueError(f"{c.chunk_id}: expected {self.config.n_features} features")
            if (c.chi_start_deg, c.chi_end_deg) != self.config.sector_bounds(c.chunk_id.sector):
                raise ValueError(f"{c.chunk_id}: chi bounds do not match the configured sector")
