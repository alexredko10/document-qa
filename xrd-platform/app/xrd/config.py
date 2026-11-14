"""Authoritative chunk-topology configuration (AGENT_SPEC §3, §5, §13, §14)."""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ChunkId:
    """Chunk C[a, r]; field order makes sorting match the canonical serialisation."""

    sector: int
    band: int

    def __str__(self) -> str:
        return f"C{self.sector:02d}_{self.band:02d}"


@dataclass(frozen=True, kw_only=True)
class XRDChunkConfig:
    version: str
    n_sectors: int
    n_radial_bands: int
    radial_samples: int
    n_features: int
    chi_min_deg: float
    chi_max_deg: float

    def __post_init__(self) -> None:
        for name in ("n_sectors", "n_radial_bands", "radial_samples", "n_features"):
            value = getattr(self, name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive int, got {value!r}")
        if self.chi_max_deg - self.chi_min_deg != 360.0:
            raise ValueError(
                f"chi domain [{self.chi_min_deg}, {self.chi_max_deg}) must span 360 degrees"
            )

    @property
    def sector_width_deg(self) -> float:
        return (self.chi_max_deg - self.chi_min_deg) / self.n_sectors

    @property
    def n_chunks(self) -> int:
        return self.n_sectors * self.n_radial_bands

    @property
    def chunk_dim(self) -> int:
        return self.radial_samples + self.n_features

    @property
    def scan_dim(self) -> int:
        return self.n_chunks * self.chunk_dim

    def chunk_ids(self) -> tuple[ChunkId, ...]:
        """Canonical serialisation order: sector-major, radial band minor."""
        return tuple(
            ChunkId(sector=a, band=r)
            for a in range(self.n_sectors)
            for r in range(self.n_radial_bands)
        )

    def sector_bounds(self, sector: int) -> tuple[float, float]:
        """Half-open χ interval [start, end) in degrees."""
        if not 0 <= sector < self.n_sectors:
            raise ValueError(f"sector {sector} out of range 0..{self.n_sectors - 1}")
        start = self.chi_min_deg + sector * self.sector_width_deg
        return start, start + self.sector_width_deg


XRD_CHUNK_096_V1 = XRDChunkConfig(
    version="XRD-CHUNK-096-v1",
    n_sectors=16,
    n_radial_bands=6,
    radial_samples=256,
    n_features=15,
    chi_min_deg=-180.0,
    chi_max_deg=180.0,
)
