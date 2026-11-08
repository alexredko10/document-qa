# QA prototype Helm chart

This chart deploys the `document-qa-prototype` image.

- One replica only: documents/vectors are kept in process memory. Every Pod restart loses uploaded documents. It is NOT a durable or highly available application.
- Image is pinned by GHCR digest, not `latest`. The AWS values contain the GitOps digest; other values must set `image.digest`.
- `values-dev.yaml`: `stub`, works without credentials.
- `values-prod.yaml`: `openrouter`, references Kubernetes Secret `qa-openrouter` (`OPENROUTER_API_KEY` key). The Secret must be created out-of-band; do not commit secrets.
- No public ingress is created by this chart. Use authorized private access or `kubectl port-forward` for a smoke test.
- `Recreate` strategy avoids overlapping copies of the in-memory service during upgrades but creates downtime and loses all document data.
- Readiness/liveness check only `/healthz`, not upstream LLM health. Prometheus metrics, structured logs and optional Tempo tracing provide application observability.

Local chart lint, with the actual GHCR image digest:

```bash
helm lint ./document-qa-prototype/deploy/charts/qa-prototype \
  -f ./document-qa-prototype/deploy/charts/qa-prototype/values-dev.yaml \
  --set-string image.digest="$DIGEST"
```

Embedding configuration is independent of generation: `embedding.provider` defaults to `hash` and `embedding.model` defaults to `openai/text-embedding-3-small`. Selecting `embedding.provider=openrouter` references the existing `llm.openRouterSecretName` / `OPENROUTER_API_KEY` Secret even when `llm.provider=stub`. No Secret is created by this chart. Changing embedding provider or model requires re-uploading in-memory documents; see the prototype README for cost, privacy and retention limitations.
