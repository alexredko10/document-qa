# PROJECT MEMORY — Enterprise Agentic AI Reference Platform

**Version:** 0.1 | **Date:** 2026-11-06 | **Status:** Foundation / design, not implementation
**Project type:** Standalone portfolio/pet project engineered with enterprise discipline.
**Source of truth:** This file + ADRs + verified repository facts. Do not interpret project memory as a claim that software is already implemented.

## 1. Vision
Build an agent-agnostic, production-minded, AWS-hosted Agentic AI / RAG reference platform that demonstrates Senior/Lead/Staff engineering capabilities: secure multi-role tools, controlled knowledge ingestion, reliable orchestration, GitOps, comprehensive testing, LLM evaluation, SRE observability, cost control and architecture governance. **Enterprise-grade engineering without enterprise-grade spending.** It is a learning system and a portfolio demonstration, not a production medical platform. Use synthetic datasets only.

## 2. Guiding principles
- Security, authorisation and data governance are enforced in deterministic application code, never delegated to an LLM or judge.
- Start with a minimal vertical slice, expand by evidence. No framework adoption for its own sake.
- Clear separation: knowledge governance control plane; ingestion/index publication; retrieval/inference data plane; tool policy/execution plane; CI/CD/control plane.
- Design to scale while initially deploying economically on one EC2 instance; one node is **not HA**.
- Every new service/framework requires rationale, an ADR, benchmark where appropriate and rollback strategy.
- Human-owned decisions, AI-assisted implementation, explicit ownership; no autonomous changes to architectural rules to bypass failures.
- Source-level, chunk-level, resource-level and user/tenant-level authorisation; deny by default; validate again immediately before disclosure.
- Separate **decided**, **proposed**, **open**, **verified implemented** and **not yet implemented**. Do not invent production history, costs, tests, certifications, clinical outcomes or capabilities.

## 3. Proposed technology landscape (not all approved)
- AWS infrastructure with Terraform; Linux EC2, K3s (lightweight Kubernetes) initial candidate; Helm, Argo CD GitOps and GitHub Actions CI.
- FastAPI/Python application components (candidate), container images and Kubernetes manifests.
- Bedrock as managed model runtime; evaluate available Qwen models for answer generation/tool-calling and Amazon Titan Text Embeddings V2 for embeddings; pin IDs, region and compatible APIs after verification.
- LangGraph as *candidate* for stateful, branching agent workflows; LangChain/LlamaIndex optional adapters or comparative experiments, not mandatory platform-wide dependencies.
- Standard S3 buckets: originals, approved immutable knowledge snapshots, extracted text/chunk payloads and optionally reports; bucket policies, encryption, lifecycle and provenance.
- DynamoDB for operational data: source catalog, lifecycle, approvals, version metadata, execution metadata, tool policy and audit pointers (exact data model TBD).
- **DynamoDB native vector search vs S3 Vectors undecided**. VectorStore interface and evidence-based benchmark first. They are alternative vector backends, not assumed mandatory duplicates. Native DynamoDB vector search became GA August 2026.
- For ingestion, consider SQS + idempotent worker, DLQ, retries and bounded concurrency. Do not require LangGraph for a deterministic pipeline.
- OpenTelemetry tracing, Prometheus/Grafana for app/runtime metrics, AWS-native logs/alerts where prudent; guard against sensitive values in telemetry.
- Quality: pytest, typing, ruff, coverage, property/contract tests, SAST/dependency/IaC scanning, golden set AI evals, retrieval metrics, security/authorization tests, load tests. Assess mutation testing feasibility and cost.

## 4. Reference bounded contexts / planes
1. Identity/API: authenticated sessions, token verification, user context and request limits.
2. Knowledge governance (OKF-inspired): candidate -> metadata review/approval -> immutable approved snapshot -> extraction -> chunk/embedding -> index publication. Approval never equals automatic indexing.
3. Knowledge pipeline: deterministic text processing, chunk lineage, embedding and index adapter; versioned publication, reprocessing and deletion/revocation.
4. Retrieval: user-authorised scope -> semantic/optional lexical retrieval -> verification against authoritative policy -> reranking -> trusted context assembly -> citations.
5. Agent workflow: intent routing -> permitted RAG or tool path -> model -> validation/evaluation -> response/refusal/escalation. Strongly bounded retries/steps/tokens/time.
6. Tool registry/policy/execution: allowlisted tools, JSON-schema/Pydantic argument validation, resource-level checks, per-role/per-user policies, risk tiers, approval, idempotency, audit, safe output handling. Model output is always untrusted.
7. Observability/FinOps: costs, latency, error budgets, audit, regression signals and operational response.

## 5. Security invariants (non-negotiable)
- Authentication and tenant identity come from trusted server-side context, not LLM-generated arguments or prompt text.
- Tool invocation = explicit policy decision based on principal, action, resource, context and approval. Disallowed or unknown tool/field is rejected. No broad generic shell/network tools by default.
- Never reveal denied document contents to the model, reranker, judge or logs. Use access-scoped retrieval filters *plus* authoritative re-authorisation per document/chunk before sending to model and before returning data.
- Approved sources and immutable snapshots govern publishable content; stale/revoked/unapproved data must be excluded, with tested revocation semantics.
- Prompt injection is untrusted content. No retrieved text may redefine system instructions, authorisations or tool policy.
- Judge is for quality evaluation, not authoritative access/security approval. It cannot override deterministic policy.
- Synthetic HR/Finance/Engineering/medical-style datasets; do not use real patient records or personally identifiable data.
- TLS, encryption at rest, least privilege, workload identity strategy for self-managed K3s, secrets never committed to Git, audit events without secrets, network ingress restrictions, backups and documented recovery.
- Tool calls may have irreversible side effects: risk categories, human approval, replay/idempotency protections and bounded execution.

## 6. Test and evaluation philosophy
- Unit tests: policy engine, schema validation, state transitions, indexing contracts, retry limits and citation matching.
- Contract/integration tests: AWS adapters with test accounts and controlled fixtures; verify real Bedrock API and vector operations separately from mocked tests.
- RAG evaluation: Recall@k, nDCG/MRR where relevant, answer correctness, faithfulness/groundedness, citation validity, abstention and escalation.
- Agent/tool evaluation: tool-selection correctness, argument validity, permission denial, prohibited-call execution count, number of steps, cost and failure recovery.
- Security: horizontal/vertical privilege escalation, prompt injection, cross-role/tenant leakage, malformed tool args, toxic documents, unsafe outputs, revocation race conditions.
- Operational: P50/P95 latency, tokens/input-output per request, total invocation count, costs per successful answer, cache hit rate, error rate, task completion, human escalation, CI duration and incidents.
- Judge: calibrate against human-labelled reference examples. Offline or sampled online, not necessarily each request. Deterministic security always first.
- CI blocking: formatting/lint/types, unit and architecture/policy tests, critical security and RAG regression thresholds; heavier LLM judge/load/mutation tests scheduled or gated as justified.

## 7. Candidate end-to-end demonstrations
1. Finance user retrieves an approved finance policy/document with valid citations, audit trail, model/version/token costs.
2. Same user requests HR record or forbidden tool: deterministic denial with no unauthorised retrieval/model exposure.
3. A document is changed or revoked: previous approved snapshot lineage remains auditable; retrieval excludes revoked publication.
4. Model version/candidate changes: offline regression comparison of answer quality, latency and cost; controlled promotion/rollback.
5. Source upload -> approval -> snapshot -> chunk -> embed -> index -> verify -> publish, with failure, retry and DLQ examples.
6. GitHub Actions CI -> Argo CD deployment -> health check -> rollback and recovery exercise.

## 8. Delivery phases and exit criteria
**Phase 0 — Foundation:** requirements, baseline ADRs, threat model, C4/data flow diagrams, cost envelope, current-state audit if repo exists. Exit: explicit architectural decisions and open questions.
**Phase 1 — Infrastructure:** Terraform account-bound environment, budget alerts, EC2 K3s, Argo CD, image registry, secure access, CI. Exit: repeatable provision/deploy/recover and no public admin UI.
**Phase 2 — Governance:** source registry, approval, immutable S3 snapshots, metadata/access rules. Exit: unapproved content never eligible for publication.
**Phase 3 — RAG:** chunk/embedding/index adapters, DynamoDB-vs-S3 vector benchmark, authorised retrieval, Bedrock Qwen. Exit: golden-set retrieval and no-leak tests pass.
**Phase 4 — Agent tools:** LangGraph candidate, registry/policy, per-user tool grants, schema validation, approvals, bounded execution. Exit: negative authorization matrix passes.
**Phase 5 — AI quality:** judge evaluation, retrieval/answer/tool metrics, adversarial suites and release gates. Exit: reproducible regression evaluation.
**Phase 6 — SRE/FinOps:** telemetry, dashboards, budgets, alerts, incidents, backup/recovery. Exit: measured cost and SLO evidence.
**Phase 7 — Scale experiments:** load/chaos, worker scaling, tenancy, multi-node/EKS migration ADR. Exit: evidence-based limitations and roadmap.

## 9. Decisions and unresolved questions
**Decided as project principles:** separate standalone reference platform; agent-agnostic repo/task instructions; synthetic data; first architecture and ADRs, then implementation; deterministic security and human-controlled decisions; controlled knowledge provenance; testability and cost visibility.
**Proposed (not yet accepted):** FastAPI, K3s EC2, Argo CD, Terraform, Qwen/Titan through Bedrock, LangGraph, SQS workers, DynamoDB metadata, OpenTelemetry, specific test/eval frameworks.
**OPEN ADR-001:** DynamoDB Native Vector Search vs S3 Vectors vs other options, benchmark same embeddings/dataset/search policies.
**OPEN:** AWS region/account budget, traffic profile, authentication provider, tenancy model, role/tool catalogue, exact deployment topology, model IDs/quotas, required SLOs, document formats, revocation strategy and running-cost ceiling.
**Implementation status:** UNKNOWN; no source repository supplied in this task. Do not claim code or infrastructure exists.

## 10. Architecture change protocol
For each proposed major change: document business/technical need -> identify trade-offs -> security impact -> benchmark/test plan -> ADR -> explicit human approval -> incremental implementation -> verification -> project-memory update. Update memory only with verified facts and include dates and evidence. ADRs override aspirational plans on their topic; existing code must be inspected before claims.

## 11. Starter documents
- `docs/architecture/adr/ADR-001-vector-store-strategy.md` (proposed)
- `docs/architecture/SYSTEM_ARCHITECTURE.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `agent/AGENT_TASK.md`

## 12. Research references (checked 2026-11-06)
- DynamoDB vector search GA: https://aws.amazon.com/about-aws/whats-new/2026/08/amazon-dynamodb-vector-search/
- DynamoDB vector implementation: https://aws.amazon.com/blogs/database/build-semantic-search-with-native-vector-support-in-amazon-dynamodb/
- S3 Vectors: https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html
- S3 metadata prefiltering: https://aws.amazon.com/about-aws/whats-new/2026/09/s3-vectors-introduces-metadata-pre-filtering/
- Qwen on Bedrock: https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-qwen.html

## 13. GRILL ME — four-hour execution protocol (added 2026-11-06)
**Status: DECIDED workflow principle, not a statement that any feature is implemented.**
- Adopt **GRILL ME** as the agent-agnostic short-session delivery workflow. "Metadata Enrichment / Grill Me" is the initial requirements-challenge gate: clarify actors, sensitive data, provenance, permissions, acceptance/denial criteria and non-goals before implementation.
- Stages: Metadata Enrichment → Research → Design → Design QA → Planning → Coder → Implementation QA → Pre-Commit Reviewer → Deploy/Delivery Validation. Review occurs before deploy even when a source template enumerates it after deploy.
- Total hard timebox **240 minutes**: 15 / 20 / 25 / 10 / 10 / 95 / 35 / 10 / 20. See `agent/GRILL_ME_4H_TASK.md` for runnable instructions.
- **One small vertical slice per session**, not the entire enterprise platform. Design QA is a short threat/architecture checklist; planning is compact; expensive evaluation and full infra are separately scheduled. Stop feature work after minute 170 to preserve test/review time.
- No live AWS or billable resource provisioning without explicit permission. Initial session should work locally using synthetic fixtures/mocks unless infrastructure deployment is specifically approved and selected as the story.
- Preserve deterministic security tests and acceptance criteria; simplification must remove ceremony, **not safety controls**.
- At session end, update only verified implementation facts with evidence/test results, and list deferred work. Record any unresolved decisions as OPEN.
