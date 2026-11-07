"""Embedders: deterministic mock and Bedrock Titan v2.

`embed` is synchronous (boto3 is); callers run it via asyncio.to_thread so the
event loop never blocks on network I/O.
"""

import hashlib
import json
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from app.config import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Without stop-word removal, function words alone give unrelated texts a cosine of
# ~0.2, which defeats the "I don't know" guard in mock mode.
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "did", "do", "does",
        "for", "from", "has", "have", "how", "in", "is", "it", "its", "of", "on", "or",
        "that", "the", "this", "to", "was", "were", "what", "when", "where", "which",
        "who", "why", "will", "with",
    }
)  # fmt: skip


class Embedder(ABC):
    model_id: str = "unknown"

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingMockEmbedder(Embedder):
    """Deterministic bag-of-words hashing: texts sharing content words score high.

    Not semantic, but good enough for the end-to-end flow (including the
    "I don't know" guard) to behave plausibly without an API key.
    """

    model_id = "mock-hashing"

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            v = np.zeros(self._dim, dtype=np.float32)
            for token in _TOKEN_RE.findall(text.lower()):
                if token in _STOPWORDS:
                    continue
                digest = hashlib.md5(token.encode("utf-8"), usedforsecurity=False).digest()
                v[int.from_bytes(digest[:4], "big") % self._dim] += 1.0
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v /= norm
            out.append(v.tolist())
        return out


class BedrockTitanEmbedder(Embedder):
    """Titan Text Embeddings v2. One API call per text, fanned out over a bounded
    thread pool: a 1 MiB document is ~1,300 chunks, which is minutes sequentially."""

    def __init__(self, region: str, model_id: str, concurrency: int = 8) -> None:
        import boto3

        self._client: Any = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id
        self._concurrency = concurrency

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM

    def _embed_one(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": EMBEDDING_DIM, "normalize": True})
        resp = self._client.invoke_model(modelId=self.model_id, body=body)
        embedding: list[float] = json.loads(resp["body"].read())["embedding"]
        return embedding

    def embed(self, texts: list[str]) -> list[list[float]]:
        if len(texts) == 1:
            return [self._embed_one(texts[0])]
        with ThreadPoolExecutor(max_workers=self._concurrency) as pool:
            return list(pool.map(self._embed_one, texts))
