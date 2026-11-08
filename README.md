# Document QA — Platform Engineering Take-Home

The working prototype uploads text documents into memory and answers questions using retrieved chunks. It supports a deterministic stub and hash embedding baseline, plus optional OpenRouter generation and embeddings. A demo console provides RAG comparison and request metadata.

## Navigate the repository

- [Working application and local run instructions](document-qa-prototype/README.md)
- [Prototype Helm chart](document-qa-prototype/deploy/charts/qa-prototype/README.md)
- [AWS infrastructure](document-qa/infra/terraform/README.md)
- [Observability, SLOs and alerts](document-qa/deploy/grafana/README.md) and [logging and tracing](document-qa/deploy/logging/README.md)
- [Local k6 benchmark](document-qa-prototype/README.md#local-k6-benchmark--8-november-2026)
- [Custom Resource API and reconciliation design](document-qa-prototype/deploy/custom-resource/RECONCILIATION.md)

`document-qa-prototype/` contains the working application and chart. `document-qa/deploy/argocd/`, `document-qa/deploy/grafana/`, `document-qa/deploy/logging/`, and `document-qa/infra/terraform/` contain the working platform infrastructure. `document-qa/app/`, `document-qa/operator/`, and the placeholder `qa-operator` and `qa-service` charts are unfinished experimental scaffolding and are not part of the delivered runtime.

Implemented features include document ingestion and retrieval, a demo console, Helm and Argo CD configuration, Prometheus metrics and alerts, structured logs, and tracing with Tempo.

## Limitations

Documents and vectors are in memory and are lost on restart. The prototype uses one replica; it does not provide high availability, durable storage, production authentication, or production-grade scaling. The Custom Resource is a design only: no controller is implemented or deployed. The local k6 result measures the stub/hash workload, not real provider latency or AWS capacity.
