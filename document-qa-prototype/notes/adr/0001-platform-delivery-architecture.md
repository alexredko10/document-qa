# ADR-0001: Platform Delivery Architecture for Document QA

- **Date:** 2026-11-07
- **Status:** Accepted as a target architecture; implementation pending
- **Scope:** `document-qa-prototype` learning notes and the future `document-qa` deployment
- **Decision owners:** Project maintainers

## Context

The exercise is primarily a **platform engineering** evaluation: package, deploy, operate, observe, and reliably deliver a small LLM-backed document Q&A service on Kubernetes. RAG is the example workload, not the sole deliverable.

The Git repository contains **two project directories, not two Git branches**:

- `document-qa-prototype/` — learning and validating a minimal application, retrieval logic, and LLM integration.
- `document-qa/` — the deployable service and platform artifacts (Docker, Helm, CRD/operator, observability, CI/CD, infrastructure).

Decisions documented here do **not** mean that all components are already implemented.

## Decisions

### 1. Application baseline and LLM

- Finish `POST /ask` with a JSON **answer and source chunks**. Return a clear "I don't know" when the provided document does not support an answer.
- Introduce a small `LLMClient` contract with two implementations:
  - `StubLLM` — deterministic, offline/no-key implementation to exercise the entire API path. It is **not** a real language model.
  - `OpenRouterLLM` — real model provider configured via environment variables; never commit API keys.
- Cover successful retrieval/answering, unsupported questions, invalid input, provider timeouts, rate limits, and unavailable providers with tests.
- Preserve current prototype retrieval experiments (Markdown cleaning/chunking, simple hashed vectors, BM25) as baseline measurements. Avoid additional RAG tuning until delivery requirements are met.
- Do not depend on agent frameworks. Autonomous agents and Amazon S3 Vectors are **deferred**, not required by the exercise. DynamoDB is not part of this design.

### 2. Source control and container registry

- GitHub is the source of truth for code, Helm configurations, and GitOps deployment manifests.
- Use **GitHub Container Registry (GHCR)** for application container images instead of ECR or Docker Hub in the initial implementation.
- CI publishes images after tests and security checks using short-lived `GITHUB_TOKEN` with minimum `packages: write` permissions; **no AWS credentials in application CI/CD**.
- Never deploy the mutable `latest` tag. Publish a commit-derived tag such as `sha-<full-git-sha>`; pin the **image digest (`sha256:...`)** in the deployed GitOps configuration where practical. Retain the association between Git revision, image digest, and deployment revision for rollbacks.
- Make the package public for anonymous pull in the demo, or explicitly configure Kubernetes registry credentials if private.

### 3. CI quality gates

- On pull requests: run Python lint (`ruff`), unit/integration tests (`pytest`), Helm validation, and security checks.
- Integrate **SonarQube Cloud (formerly SonarCloud)** for static analysis/SAST and a Quality Gate, subject to project/plan configuration. Do not treat it as a replacement for dependency or image vulnerability scans.
- Run **Trivy** for container/dependency vulnerabilities. Define a documented policy for which findings block a build.
- On approved `main` changes: build and publish a Linux **ARM64** container image to GHCR; do not publish deployable images on untrusted PRs.
- Separate CI image publishing from GitOps deployment configuration updates. Prefer a reviewed pull request that updates the pinned image digest.

### 4. Runtime and infrastructure

- Target **AWS EC2 Graviton ARM64**, initially `t4g.large` (2 vCPU, 8 GiB RAM), **Ubuntu Server 24.04 ARM64**, and a single-node **K3s** cluster.
- Provision EC2, IAM instance profile, networking/security groups, and bootstrap using **Terraform**; keep infrastructure credentials outside application CI. Clean up using `terraform destroy` and verify removal of chargeable resources.
- Start with a local k3d deployment using the **same Helm chart** before provisioning EC2. Keep separate `values-dev.yaml` and `values-prod.yaml` rather than changing templates between environments.
- A single-node K3s demo is **not highly available** and is not a claim of production SLA readiness.
- Verify that all third-party container images (Argo CD, Cloudflare, monitoring) support Linux ARM64 and that resource consumption fits the EC2 instance.
- Prefer AWS Systems Manager for administrative access; avoid exposing SSH or the Kubernetes API publicly.

### 5. GitOps and external access

- Install **Argo CD** as the GitOps controller. It watches a Git path containing Helm/Kubernetes desired state and reconciles the K3s cluster.
- GitHub Actions builds and publishes; **Argo CD deploys**. Avoid granting the application CI pipeline cluster-admin credentials or using direct `kubectl apply` as the steady-state deployment mechanism.
- Use **Cloudflare Tunnel** for outbound-only connectivity to selected endpoints, with **Cloudflare Access** protecting the Argo CD UI. Do not publicly expose the Argo CD dashboard by raw IP without access controls.
- Keep tunnel credentials, OpenRouter API keys, and other secrets out of Git/Helm values. Refer to Kubernetes Secrets supplied via a documented secret delivery mechanism (e.g., External Secrets Operator), with access scoped to what each component needs.

### 6. Operations required by the exercise

- Expose request/latency/LLM token and cost metrics; use structured, request-correlated logs without document or secret content by default.
- Instrument LLM calls for duration, outcome, and token usage; make content capture opt-in and protected because prompts/documents may contain sensitive material.
- Define at least two measurable SLOs (e.g., availability and latency), alert rules, and short on-call runbook steps.
- Handle model timeouts, rate limits, and upstream failures predictably; return controlled HTTP errors and expose those failures in telemetry.
- Supply a validated `DocumentQAService` CRD plus an example, and either a working reconciliation controller or a clearly documented reconciliation design, as permitted by the exercise.

## Planned delivery sequence

1. **Finish the prototype API:** `/ask`, `StubLLM`, OpenRouter adapter, source chunks, "I don't know", resilience tests.
2. **Promote the minimal working service** into `document-qa/`; produce a non-root Linux ARM64 Docker image.
3. **Deploy locally:** Helm chart, dev/prod values, readiness/liveness probes, secret references, k3d smoke test.
4. **Build CI:** tests, Ruff, SonarQube Cloud, Trivy, ARM64 image publication to GHCR with commit tag and captured digest.
5. **Provision EC2/K3s:** Terraform, least-privilege IAM, SSM, deployment and runtime validation.
6. **Add GitOps:** Argo CD sync from Git; protect chosen endpoints with Cloudflare Tunnel + Access.
7. **Demonstrate operations:** CRD/reconciliation, metrics, traces, logs, two SLOs with alerts and runbooks, LLM failure drill.

## Acceptance evidence

- A reviewer can run the service **locally without an LLM API key** and observe an answer plus source chunks.
- Unsupported questions do not generate fabricated document-based answers.
- An HTTP request through the service can be tested with both a stub and a real provider (when configured), including provider failure scenarios.
- A tested **ARM64** image can be traced to its Git commit and digest; no `latest` is required to deploy or roll back.
- Helm deploys the service to k3d and K3s; Argo CD shows the desired application as synced/healthy after reconciliation.
- CI requires no AWS credential to build/publish the application. Infrastructure authentication is documented separately.
- An operator can find relevant metrics/logs/traces, investigate alerts, and follow the runbook.

## Trade-offs and open items

- GHCR simplifies GitHub-hosted CI, but registry package visibility and permissions need one-time setup.
- Graviton reduces expected runtime cost for supported workloads but requires ARM64-compatible images, dependencies, and CI runners.
- Argo CD, Cloudflare Tunnel, and monitoring consume resources on a single `t4g.large`; measure memory/CPU before adding more services.
- Image digest update automation may initially be manual/PR-based; full automation is not necessary for the first demo.
- A real LLM's answer quality is not fully demonstrated by stub tests; end-to-end provider tests must be separately and explicitly identified.
- The prototype's in-memory document/vector state is not persistent or multi-replica safe; document this limitation for the first Kubernetes demo and address it only if time allows.

## Next immediate action

Return to the unfinished **LLM work in `document-qa-prototype`**. Complete `POST /ask` + `LLMClient` + `StubLLM` and test the offline API path **before** starting Docker/CI/CD implementation.
