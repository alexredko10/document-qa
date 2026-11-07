import os
from functools import lru_cache

from app.llm.base import LLMClient
from app.llm.stub import StubLLM
from app.llm.openrouter import OpenRouterLLM


@lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "stub")

    if provider == "stub":
        return StubLLM()

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

        return OpenRouterLLM(
            api_key=api_key,
            model=model,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")