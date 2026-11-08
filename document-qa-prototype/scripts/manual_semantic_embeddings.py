"""Opt-in external smoke test using only synthetic text; may incur provider charges."""
import os

from app.rag.embedding_provider import EmbeddingError, OpenRouterEmbeddings
from app.rag.retriever import search_vectors


def main():
    if os.getenv('RUN_OPENROUTER_EMBEDDING_TEST') != '1' or not os.getenv('OPENROUTER_API_KEY'):
        raise SystemExit('Set RUN_OPENROUTER_EMBEDDING_TEST=1 and OPENROUTER_API_KEY to opt in.')
    provider = OpenRouterEmbeddings(os.environ['OPENROUTER_API_KEY'], os.getenv('OPENROUTER_EMBEDDING_MODEL', 'openai/text-embedding-3-small'))
    documents = ['Dogs are playful companions.', 'The train departed from the station.']
    try:
        vectors = provider.embed(documents, 'document')
        query = provider.embed(['A puppy is a friendly pet.'], 'query')[0]
    except EmbeddingError:
        raise SystemExit('Embedding provider unavailable or returned invalid data.') from None
    if len(query) != len(vectors[0]):
        raise SystemExit('Embedding dimensions are incompatible.')
    results = search_vectors(query, documents, vectors, positive_only=False)
    scores = {result.index: result.score for result in results}
    if 0 not in scores or 1 not in scores or scores[0] <= scores[1]:
        raise SystemExit('Semantic ranking check failed: the dog document did not rank above the train document.')
    print(f'Semantic ranking check passed: dogs={scores[0]:.4f}, train={scores[1]:.4f}')


if __name__ == '__main__':
    main()
