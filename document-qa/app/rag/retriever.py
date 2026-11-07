"""Similarity helpers shared by store backends that rank in-process."""

from collections.abc import Sequence

import numpy as np


def cosine_scores(query: Sequence[float], matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of `query` against each row of `matrix`."""
    q = np.asarray(query, dtype=np.float32)
    q_norm = float(np.linalg.norm(q)) or 1e-9
    row_norms = np.linalg.norm(matrix, axis=1)
    row_norms[row_norms == 0] = 1e-9
    scores: np.ndarray = (matrix @ q) / (row_norms * q_norm)
    return scores
