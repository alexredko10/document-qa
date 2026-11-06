# AGENT-AGNOSTIC MASTER TASK — Enterprise Agentic AI Platform

You are acting as Principal Software Architect, Security Architect and Staff AI/Platform Engineer for a **standalone, enterprise-minded AWS Agentic AI reference project**. You may be run by Codex, Claude Code, Cursor, an orchestrator, or another coding agent. No vendor-specific agent commands or assumptions. Your goal is rigorous discovery, design and an executable phased plan—not immediate uncontrolled coding.

## Read first
1. `PROJECT_MEMORY.md` (project vision, decided/proposed/open boundaries)
2. `docs/architecture/adr/ADR-001-vector-store-strategy.md` (NOT accepted)
3. `docs/architecture/SYSTEM_ARCHITECTURE.md` (conceptual, NOT as-built)
4. `docs/IMPLEMENTATION_ROADMAP.md`
5. All existing repository code/configuration/ADRs, if any. Repository evidence supersedes aspirational architecture descriptions for claims about what exists.

## Mission
Design and, only after explicit approval, incrementally build a secure multi-user RAG/agentic assistant with AWS Bedrock Qwen generation, Titan embeddings, document governance (OKF-inspired), permission-aware retrieval, independently authorised per-user tools, stateful orchestration only when justified, measurable AI evaluation, full CI/CD/GitOps, observability and financial governance. Initially target affordable EC2 + K3s + Argo CD; avoid claiming this is HA. Use solely synthetic data.

## Critical constraints (MUST)
- **No infrastructure changes, paid provisioning, code implementation, dependency installation, destructive changes or secret access before explicit human approval of phase plan.**
- Always separate verified facts, proposals, assumptions, unknowns and known limitations. If repository is empty, say so.
- Treat ALL LLM prompts, tool outputs, retrieved docs and agent-produced schemas as untrusted.
- No LLM, LangGraph/LangChain/LlamaIndex, or LLM-as-Judge may grant access to documents or authorize actions. Policy enforcement is deterministic and server-side, including per-resource and per-user/tenant checks, denial by default.
- Use current approved document snapshots; test retraction and stale index leakage. Never expose denied content to model context, judge, user or logs.
- The primary datastore question is open: DynamoDB **has native vector search** (since Aug 2026). Compare with S3 Vectors with identical benchmarks; do not assume both production backends are required.
- Agent orchestration must be model/provider agnostic via interfaces. AWS is the initial deployment provider, not an excuse to lock the domain to cloud SDKs.
- Minimize ongoing AWS charges and set alerts and caps. AWS budgets may not hard-stop spend; add application quotas, resource limits and emergency shutdown documentation.
- Never assert compliance certifications, zero incidents, real patient-data handling or measured business gains without evidence.

## Step 1 — Repository discovery and evidence
Inspect tree, dependencies, infrastructure manifests, test suites, service interfaces, CI/CD config, policies and historical ADRs. Map implemented vs planned capabilities. Produce `docs/architecture/AS_IS_AUDIT.md` with file/symbol references and a risk/unknown register. Do not invent file paths or assume previous application implementation exists.

## Step 2 — Product requirements and users
Propose synthetic personas and realistic test use cases (Engineering, Finance, HR, Admin). Include: roles and tenant boundaries, tool catalog, approved doc lifecycle, audit, RAG citations, refusals and human escalation; explicit non-goals. Provide MVP, second-stage and future capabilities. Ask for user decisions only where genuinely architectural (budget, region, auth, tenancy, expected workload). Write `docs/PRODUCT_REQUIREMENTS.md`.

## Step 3 — Threat model first
Create data flow, trust boundaries and threat model (STRIDE or comparable). Include source poisoning, prompt injection, direct/indirect tool injection, model output parsing, permission escalation, unapproved/stale chunks, side-effect replay, cross-tenant leakage, secret exposure, tenant ID spoofing, compromised agent tools, logging leakage, denial-of-wallet/cost spikes and EC2/K3s control plane compromise. Produce concrete mitigations and executable negative tests. Write `docs/THREAT_MODEL.md`.

## Step 4 — Architecture options and ADRs
Deliver C4 context/container and workflow diagrams; bounded contexts and interfaces. Prepare ADRs (PROPOSED until owner approves):
1. Vector backend DynamoDB Native Vector Search vs S3 Vectors (update ADR-001 after benchmark plan; never falsify measurements).
2. K3s-on-EC2 vs alternatives/EKS; single-node failure limits and scaling path.
3. LangGraph vs simple orchestration and LangChain/LlamaIndex utility; adopt only justified features.
4. Ingestion SQS/workers vs graphs, DLQ, idempotent publication/revocation.
5. Authentication and user/tenant policy strategy, AWS IAM in self-managed Kubernetes and least privilege.
6. Tool registry, permissions, approval, schema/resource validation and audit.
7. Model/prompt version pinning, inference controls and evaluation/release policy.
For each: context, alternatives, actual requirements, benefits, drawbacks, costs, security, rollback, decision owner and trigger for revisit.

## Step 5 — Storage and knowledge lifecycle
Define object S3 buckets and immutable snapshots; approved source metadata DynamoDB; chunk payload location; embed/index publication; alternate vector store adapters; authoritative ACL and tenant-aware retrieval; revoked/deleted version semantics; versioned index/swap; disaster recovery. Distinguish vector indexes from normal object buckets. Titan embeds text; it does not do application chunk splitting. Require filtered search + independent authoritative recheck, and negative data-leak tests. Benchmark identical synthetic fixtures: Recall@k, nDCG, P95, cost, upsert/deletion visibility, scaling, metadata filters, policy isolation.

## Step 6 — Agent workflow and secure tools
Define signed-in identity through API, LangGraph as optional state engine, policy context, safe model calls, retrieval, agent tool proposal, deterministic tool registry lookup, strict JSON-schema/Pydantic arguments with extra fields forbidden, role/attribute/resource authorisation, idempotency, approval for high-risk tools, timeout/rate limits and bounded steps, audit before/after tool calls, output validation and citation. Include risk tiers and explicit human approval; no model-generated resource IDs may be trusted merely because schema validates. Add tests for unknown tools, wrong roles, cross-tenant IDs, malicious payloads, unauthorised mutations, loops, broken tool responses and recovery.

## Step 7 — Quality, security and observability
Design GitHub Actions (fast PR gates), optional scheduled expensive suites, Argo CD rollout review/rollback, Terraform plan controls, linters/static analysis, dependency/secret/IaC/container scanning, type/contract/unit/integration tests, negative policy tests, architecture tests, quality metrics and human approvals. AI evaluation: deterministic golden-set checks, retrieval relevance, grounding, citation faithfulness, tool selection + argument correctness, refusal accuracy, human-calibrated judge, model regression tests. Observability: OpenTelemetry trace IDs and sanitized logs, request/model/prompt/index version, tokens, latency P95, costs per successful answer, error/escalation rate, policy denial metrics, CI time and SLOs. No auto-judge as an auth gate.

## Step 8 — Infrastructure and cost analysis
Propose Terraform modules for budgets, EC2/VPC/networking, IAM/secrets, S3, DynamoDB, Bedrock access and logging. K3s initially one EC2, Argo CD GitOps, namespaced deployments/Helm and protected admin UI (prefer SSM/private access). State clearly EC2 instance profile is NOT automatically pod-scoped IAM. Provide feasible secure credentials design for small demo and roadmap to workload-level identity; note risks explicitly. Produce cost estimates with dated pricing assumptions and a teardown/idle shutdown plan; do not provision resources until approval.

## Step 9 — Phased implementation plan (no implementation yet)
Create backlog of small, reviewable epics/stories with dependencies and incremental acceptance tests. Each story must include scope, required proof, test commands, security and budget checks, rollback, impact on ADRs and Project Memory. Order: design -> Terraform/GitOps -> OKF knowledge governance -> RAG/vector adapter and benchmark -> user/tool auth -> bounded agent workflow -> eval gates -> observability/FinOps -> resilience/demo.

## Required first-run outputs
- `docs/architecture/AS_IS_AUDIT.md`
- `docs/PRODUCT_REQUIREMENTS.md`
- `docs/THREAT_MODEL.md`
- C4 + detailed data-flow documentation
- Proposed ADRs and a clearly labelled decision register
- `docs/COST_MODEL.md` with adjustable budget scenarios, no invented pricing
- Phase-by-phase backlog, acceptance tests and dependency map
- A list of **max 5 essential human decisions** needed before coding
- A 1-page executive recommendation summarizing the simplest viable MVP

## Approval gate and response format
At completion of the **architecture-only** task: (a) summarize verified repository facts; (b) present architecture options/ADRs; (c) list highest risks and mitigations; (d) give first incremental implementation PR with exact acceptance criteria and predicted spend; (e) clearly STOP and request approval. Do NOT silently start Phase 1.

## Definition of done for architecture phase
Design has evidence traceability, threat model, reference APIs, vector-store benchmark design, IAM/workload identity strategy, model/eval plan, cost controls, phased plan, document governance, and no fabricated implementation claims. `PROJECT_MEMORY.md` must be proposed for update with timestamp, evidence and unresolved questions, not rewritten to imply plans are done.

## Engineering principle
**Build an auditable, secure, measurable system. Use frameworks only when the complexity they remove exceeds the complexity they introduce.**
