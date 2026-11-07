from pathlib import Path

from app.rag.bm25 import bm25_search
from app.rag.cleaner import clean_text
from app.rag.embedder import embed_text
from app.rag.markdown_chunker import split_markdown
from app.rag.retriever import search_vectors, cosine_similarity

raw = Path("data/deployment.md").read_text(encoding="utf-8")
cleaned = clean_text(raw)

chunks = split_markdown(cleaned, chunk_size=800, overlap=120)
vectors = [embed_text(chunk) for chunk in chunks]

print(f"Raw characters: {len(raw)}")
print(f"Cleaned characters: {len(cleaned)}")
print(f"Chunks: {len(chunks)}")

question = "How does a Deployment perform a rolling update?"

results = search_vectors(
    query_vector=embed_text(question),
    chunks=chunks,
    vectors=vectors,
    top_k=3,
)

for result in results:
    print(f"\nChunk #{result.index}, similarity={result.score:.3f}")
    print(result.text[:500])

print("\n--- Keyword baseline ---")

keywords = [
    "rolling update",
    "RollingUpdate",
    "maxSurge",
]

for keyword in keywords:
    matches = [
        index
        for index, chunk in enumerate(chunks)
        if keyword.lower() in chunk.lower()
    ]

    print(f"{keyword}: {matches[:15]}")


query_vector = embed_text(question)

ranked = sorted(
    [
        (index, cosine_similarity(query_vector, vector))
        for index, vector in enumerate(vectors)
    ],
    key=lambda item: item[1],
    reverse=True,
)

print("\n--- Relevant chunk ranking ---")

for chunk_id in [22, 69, 77, 78, 79, 80]:
    for rank, (index, score) in enumerate(ranked, start=1):
        if index == chunk_id:
            print(
                f"Chunk #{index}: rank={rank}, "
                f"similarity={score:.3f}"
            )
            print(chunks[index][:350])
            print("-" * 50)
            break


print("\n--- BM25 Search ---")

bm25_results = bm25_search(
    query=question,
    chunks=chunks,
    top_k=5,
)

for result in bm25_results:
    print(
        f"\nChunk #{result.index}, "
        f"BM25 score={result.score:.3f}"
    )
    print(result.text[:500])