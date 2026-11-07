# document-qa

AI Document Q&A service on Kubernetes: RAG + tool-calling agent, Helm, CRD/operator, observability.

## Quickstart
```bash
make install && make test && make run
```

## Layout
| Path | Purpose |
|---|---|
| `app/` | FastAPI service (api, store, rag, agent, llm, obs, prompts) |
| `migrations/` | Postgres schema |
| `operator/` | Kopf operator for DocumentQAService |
| `deploy/` | Helm charts, example CR, Argo CD apps |
| `infra/` | CloudFormation bootstrap + Terraform for AWS |
| `tests/` | pytest suite |
