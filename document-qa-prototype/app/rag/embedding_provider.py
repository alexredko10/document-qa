"""Embedding providers and bounded request observability."""
import math
import os
from time import perf_counter
from typing import Protocol

import httpx
from prometheus_client import Counter, Histogram

from app.observability.logging import log_event, model_id
from app.rag.embedder import embed_text

EMBEDDING_REQUESTS = Counter('embedding_requests_total', 'Embedding requests by provider and outcome', ['provider', 'outcome'])
EMBEDDING_DURATION = Histogram('embedding_request_duration_seconds', 'Embedding request duration', ['provider'])
EMBEDDING_TOKENS = Counter('embedding_tokens_total', 'Provider-reported embedding input tokens', ['provider'])
URL = 'https://openrouter.ai/api/v1/embeddings'
BATCH_SIZE = 32


class EmbeddingError(Exception):
    def __init__(self, reason='error'):
        self.reason = reason
        super().__init__(reason)


class EmbeddingProvider(Protocol):
    provider: str
    model: str

    def embed(self, texts: list[str], operation: str) -> list[list[float]]: ...


def validate_vectors(vectors, count, *, allow_zero=False):
    if not isinstance(vectors, list) or len(vectors) != count or not vectors:
        raise EmbeddingError('invalid_response')
    result = []
    dimension = None
    for vector in vectors:
        if not isinstance(vector, list) or not vector or (dimension is not None and len(vector) != dimension):
            raise EmbeddingError('invalid_response')
        dimension = len(vector)
        converted = []
        for value in vector:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise EmbeddingError('invalid_response')
            try:
                value = float(value)
            except (OverflowError, ValueError):
                raise EmbeddingError('invalid_response') from None
            if not math.isfinite(value):
                raise EmbeddingError('invalid_response')
            converted.append(value)
        if not allow_zero and not any(converted):
            raise EmbeddingError('invalid_response')
        result.append(converted)
    return result


def instrument(provider, operation, fn):
    start = perf_counter()
    outcome = 'success'
    reason = None
    try:
        return fn()
    except EmbeddingError as exc:
        outcome = exc.reason if exc.reason in {'timeout', 'rate_limited'} else 'error'
        reason = exc.reason if exc.reason in {'timeout', 'rate_limited', 'invalid_response', 'configuration_error'} else 'error'
        raise
    except Exception as exc:
        outcome = 'error'
        reason = 'error'
        raise EmbeddingError('error') from exc
    finally:
        elapsed = perf_counter() - start
        EMBEDDING_REQUESTS.labels(provider.provider, outcome).inc()
        EMBEDDING_DURATION.labels(provider.provider).observe(elapsed)
        fields = {'provider': provider.provider, 'model': model_id(provider.provider, provider),
                  'operation': operation, 'outcome': outcome, 'duration_ms': round(elapsed * 1000, 3)}
        if reason is not None:
            fields['reason'] = reason
        log_event('embedding_request_completed', **fields)


class HashEmbeddings:
    provider = 'hash'
    model = 'sha256-word-hash-128'

    def embed(self, texts: list[str], operation: str) -> list[list[float]]:
        return instrument(self, operation, lambda: validate_vectors([embed_text(text) for text in texts], len(texts), allow_zero=True))


class OpenRouterEmbeddings:
    provider = 'openrouter'

    def __init__(self, api_key: str, model: str = 'openai/text-embedding-3-small', client: httpx.Client | None = None):
        self.api_key = api_key
        self.model = model
        self.client = client

    def embed(self, texts: list[str], operation: str) -> list[list[float]]:
        if not texts:
            raise EmbeddingError('invalid_response')
        vectors = []
        for offset in range(0, len(texts), BATCH_SIZE):
            batch = texts[offset:offset + BATCH_SIZE]
            def fetch_batch():
                batch_vectors = self._batch(batch, operation)
                if vectors and len(batch_vectors[0]) != len(vectors[0]):
                    raise EmbeddingError('invalid_response')
                return batch_vectors
            vectors.extend(instrument(self, operation, fetch_batch))
        return validate_vectors(vectors, len(texts))

    def _batch(self, texts, operation):
        if not self.api_key or not self.model:
            raise EmbeddingError('configuration_error')
        try:
            if self.client is not None:
                response = self.client.post(URL, headers={'Authorization': f'Bearer {self.api_key}'}, json={'model': self.model, 'input': texts}, timeout=20.0)
            else:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(URL, headers={'Authorization': f'Bearer {self.api_key}'}, json={'model': self.model, 'input': texts})
        except httpx.TimeoutException as exc:
            raise EmbeddingError('timeout') from exc
        except httpx.RequestError as exc:
            raise EmbeddingError('error') from exc
        if response.status_code == 429:
            raise EmbeddingError('rate_limited')
        if response.status_code >= 400:
            raise EmbeddingError('error')
        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingError('invalid_response') from exc
        if not isinstance(data, dict):
            raise EmbeddingError('invalid_response')
        usage = data.get('usage')
        if isinstance(usage, dict):
            tokens = usage.get('prompt_tokens')
            if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0:
                EMBEDDING_TOKENS.labels(self.provider).inc(tokens)
                log_event('embedding_usage_reported', provider=self.provider,
                          model=model_id(self.provider, self), operation=operation, input_tokens=tokens)
        # OpenRouter may omit the provider prefix for this specific model.
        returned_model = data.get('model')
        model_matches = returned_model == self.model or (
            self.model == 'openai/text-embedding-3-small'
            and returned_model == 'text-embedding-3-small'
        )
        if not model_matches or not isinstance(data.get('data'), list) or len(data['data']) != len(texts):
            raise EmbeddingError('invalid_response')
        ordered = [None] * len(texts)
        for item in data['data']:
            if not isinstance(item, dict):
                raise EmbeddingError('invalid_response')
            index = item.get('index')
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(texts) or ordered[index] is not None:
                raise EmbeddingError('invalid_response')
            ordered[index] = item.get('embedding')
        return validate_vectors(ordered, len(texts))


def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv('EMBEDDING_PROVIDER', 'hash')
    if provider == 'hash':
        return HashEmbeddings()
    if provider == 'openrouter':
        return OpenRouterEmbeddings(os.getenv('OPENROUTER_API_KEY', ''), os.getenv('OPENROUTER_EMBEDDING_MODEL', 'openai/text-embedding-3-small'))
    raise EmbeddingError('configuration_error')
