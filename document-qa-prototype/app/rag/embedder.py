import hashlib
import math
import re


def embed_text(text: str, dimensions: int = 128) -> list[float]:
    """
    Creates a deterministic, normalized vector using word hashing.
    Counts word occurrences, but does not capture semantic meaning.
    """
    if dimensions <= 0:
        raise ValueError("dimensions couldn't be negative")

    vector = [0.0] * dimensions
    tokens = re.findall(r"\w+", text.lower())
    for token in tokens:
        token_hash = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(token_hash[:8], "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(x * x for x in vector))

    if norm == 0:
        return vector
    return [x / norm for x in vector]
