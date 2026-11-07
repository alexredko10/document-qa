"""Bedrock Converse client (Qwen), run off the event loop.

Credentials come from the default boto3 chain: the EC2 instance profile on k3s,
or AWS_PROFILE locally. Timeouts, retries and the circuit breaker are added in
app/llm/resilience.py (stage 3).
"""

import asyncio
from typing import Any

from app.llm.base import LLMClient, LLMResponse


class BedrockLLM(LLMClient):
    def __init__(self, region: str, model_id: str, max_tokens: int = 512) -> None:
        import boto3

        self._client: Any = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id
        self._max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> LLMResponse:
        # boto3 is synchronous: a worker thread keeps one slow call from
        # stalling every other in-flight request on this pod.
        resp = await asyncio.to_thread(
            self._client.converse,
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": self._max_tokens},
        )
        blocks = resp["output"]["message"]["content"]
        text = "".join(b.get("text", "") for b in blocks).strip()
        usage = resp.get("usage", {})
        return LLMResponse(
            text=text,
            input_tokens=int(usage.get("inputTokens", 0)),
            output_tokens=int(usage.get("outputTokens", 0)),
        )
