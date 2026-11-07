def split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size has to be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid overlap")
    chunks = []
    start = 0

    while start < len(text):
        chunk_end = min(start + chunk_size, len(text))
        chunks.append(text[start:chunk_end])
        if chunk_end == len(text):
            break
        start = chunk_end - overlap
    return chunks
