"""Text chunking with overlap."""


class TextChunker:
    """Boundary-aware character splitter with overlap.

    Prefers to cut at a paragraph, line, sentence or word boundary within the
    second half of each window. Dependency-free on purpose: fast, deterministic
    tests; swap for a token-aware splitter if chunk sizes must match model limits.
    """

    _SEPARATORS = ("\n\n", "\n", ". ", " ")

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if not 0 <= overlap < chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []
        chunks: list[str] = []
        n = len(text)
        start = 0
        while start < n:
            end = min(start + self.chunk_size, n)
            if end < n:
                window_start = start + self.chunk_size // 2
                for sep in self._SEPARATORS:
                    idx = text.rfind(sep, window_start, end)
                    if idx != -1:
                        end = idx + len(sep)
                        break
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= n:
                break
            start = max(end - self.overlap, start + 1)
        return chunks
