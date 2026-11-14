import dataclasses

import numpy as np
import pytest

from app.xrd.config import XRD_CHUNK_096_V1 as V1, ChunkId
from app.xrd.schema import ChunkQCStatus, XRDChunkEncoding, XRDEncoding


def test_v1_has_96_unique_chunk_ids_in_canonical_order():
    ids = [str(c) for c in V1.chunk_ids()]
    expected = [f"C{a:02d}_{r:02d}" for a in range(16) for r in range(6)]
    assert ids == expected
    assert len(ids) == 96 == len(set(ids))
    assert ids[0] == "C00_00" and ids[-1] == "C15_05"
    assert ids[:7] == ["C00_00", "C00_01", "C00_02", "C00_03", "C00_04", "C00_05", "C01_00"]
    assert list(V1.chunk_ids()) == sorted(V1.chunk_ids())
    assert V1.chunk_ids() == V1.chunk_ids()


def test_v1_dimensions():
    assert V1.version == "XRD-CHUNK-096-v1"
    assert V1.chunk_dim == 271
    assert V1.scan_dim == 26_016


def test_sectors_tile_full_chi_domain_without_overlap():
    bounds = [V1.sector_bounds(a) for a in range(V1.n_sectors)]
    assert V1.sector_width_deg == 22.5
    assert bounds[0] == (-180.0, -157.5)
    assert bounds[-1] == (157.5, 180.0)
    for (start, end), (next_start, _) in zip(bounds, bounds[1:]):
        assert end - start == 22.5
        assert end == next_start  # half-open intervals: contiguous, no overlap
    with pytest.raises(ValueError):
        V1.sector_bounds(16)


def test_qc_states():
    assert {s.name for s in ChunkQCStatus} == {"VALID", "PARTIAL", "INSUFFICIENT", "EMPTY"}


def test_counts_are_not_limited_by_id_formatting():
    cfg = dataclasses.replace(V1, n_sectors=120, n_radial_bands=150)
    assert cfg.n_chunks == 18_000


@pytest.mark.parametrize(
    "change",
    [{"n_sectors": 0}, {"n_radial_bands": -1}, {"radial_samples": 25.6}, {"chi_max_deg": 170.0}],
)
def test_inconsistent_config_fails(change):
    with pytest.raises(ValueError):
        dataclasses.replace(V1, **change)


def _chunk(cid: ChunkId, valid_radial: np.ndarray, valid_features: np.ndarray) -> XRDChunkEncoding:
    chi = V1.sector_bounds(cid.sector)
    return XRDChunkEncoding(
        chunk_id=cid,
        q_start=1.0 + cid.band,
        q_end=2.0 + cid.band,
        chi_start_deg=chi[0],
        chi_end_deg=chi[1],
        radial_profile=np.zeros(valid_radial.shape),
        radial_valid_mask=valid_radial,
        radial_coverage=valid_radial.astype(float),
        radial_uncertainty=np.full(valid_radial.shape, 0.1),
        features=np.zeros(valid_features.shape),
        feature_valid_mask=valid_features,
        qc_status=ChunkQCStatus.PARTIAL,
    )


def test_masks_are_independent_of_values():
    valid = np.arange(V1.radial_samples) < 100
    feats = np.ones(V1.n_features, dtype=bool)
    feats[5] = False  # e.g. dominant peak q undefined
    chunk = _chunk(ChunkId(0, 0), valid, feats)
    # Same value 0.0: a measured physical zero vs. a non-measurement, decided only by the mask.
    assert chunk.radial_profile[0] == chunk.radial_profile[200] == 0.0
    assert chunk.radial_valid_mask[0] and not chunk.radial_valid_mask[200]
    assert chunk.features[4] == chunk.features[5] == 0.0
    assert chunk.feature_valid_mask[4] and not chunk.feature_valid_mask[5]


@pytest.mark.parametrize("values_field, mask_field", [
    ("radial_profile", "radial_valid_mask"),
    ("features", "feature_valid_mask"),
])
@pytest.mark.parametrize("fill, valid, accepted", [
    (0.0, True, True),    # valid physical zero
    (0.0, False, True),   # zero used as fill for a missing slot
    (np.nan, False, True),  # NaN used as fill for a missing slot
    (np.nan, True, False),  # a valid measurement must be finite
])
def test_mask_is_authoritative(values_field, mask_field, fill, valid, accepted):
    chunk = _chunk(ChunkId(0, 0), np.ones(V1.radial_samples, dtype=bool), np.ones(V1.n_features, dtype=bool))
    values = getattr(chunk, values_field).copy()
    mask = getattr(chunk, mask_field).copy()
    values[0], mask[0] = fill, valid
    if not accepted:
        with pytest.raises(ValueError):
            dataclasses.replace(chunk, **{values_field: values, mask_field: mask})
        return
    out = dataclasses.replace(chunk, **{values_field: values, mask_field: mask})
    assert getattr(out, mask_field)[0] == valid


def test_mask_must_be_bool():
    chunk = _chunk(ChunkId(0, 0), np.ones(V1.radial_samples, dtype=bool), np.ones(V1.n_features, dtype=bool))
    with pytest.raises(ValueError):
        dataclasses.replace(chunk, radial_valid_mask=chunk.radial_valid_mask.astype(float))


def test_scan_encoding_requires_full_canonical_topology():
    empty = np.zeros(V1.radial_samples, dtype=bool)
    no_feats = np.zeros(V1.n_features, dtype=bool)
    chunks = tuple(_chunk(cid, empty, no_feats) for cid in V1.chunk_ids())
    enc = XRDEncoding(scan_id="s1", config=V1, chunks=chunks)
    assert len(enc.chunks) == V1.n_chunks
    with pytest.raises(ValueError):  # dropping an empty chunk is not allowed
        XRDEncoding(scan_id="s1", config=V1, chunks=chunks[:-1])
    with pytest.raises(ValueError):  # order is part of the representation
        XRDEncoding(scan_id="s1", config=V1, chunks=chunks[::-1])
