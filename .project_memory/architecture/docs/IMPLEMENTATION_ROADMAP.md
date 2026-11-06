# IMPLEMENTATION ROADMAP — gates, not a big-bang implementation

Every phase requires an explicit human-approved plan, small PRs, tests and updated project memory showing evidence. Check AWS availability, pricing and SDK capabilities in selected region before provisioning.

| Phase | Deliverable | Exit gate |
|---|---|---|
| 0 — Discovery & design | Requirements, C4, threat model, storage/framework ADRs, budget, IAM and deployment decision | Owner approves scope and trade-offs |
| 1 — IaC/GitOps | Terraform, AWS budget alerts, one EC2 K3s, Argo CD, CI and rollback runbook | Reproducible secure deployment, no publicly exposed admin consoles |
| 2 — Knowledge governance | Source catalogue, approval gate, S3 immutable approved snapshots, version/audit lineage | Unapproved or revoked knowledge cannot be published |
| 3 — Retrieval | Chunking, Titan embeddings, VectorStore interface, dual-backend benchmark, authorised RAG Qwen | Security & retrieval golden datasets pass, one backend selected |
| 4 — Tool orchestration | Agent workflow, per-user registry, schema/policy, approvals, idempotency, bounded agent loops | Forbidden operations cannot execute, including adversarial cases |
| 5 — AI evaluation | Golden datasets, deterministic tests, calibrated judge, release quality policy | Reproducible quality and no-leak regression suites |
| 6 — SRE/FinOps | Traces, dashboards, alerting, budgets, backup/recovery, cost per successful answer | Operational runbook + actual measured KPIs |
| 7 — Scale/portfolio demo | Traffic tests, failure injection, EKS/multi-node migration ADR, architecture case study | Evidence, documented limitations, recorded demo |

## Prioritisation
Build a **secure thin vertical slice** before maximum framework exploration: authenticate one user -> approve one synthetic document -> index -> retrieve authorised chunks -> Bedrock response + citations -> audit and measure. Then add Finance vs HR negative auth test, then tools and approval. Framework comparison can occur as controlled branch experiments; avoid introducing all frameworks simultaneously.

## Documentation hygiene
Each task must list: objective, decision scope, non-goals, touched files, acceptance criteria, tests, cost impact, threat impact, rollbacks, evidence and open questions. Done is not equivalent to merged or agent-claimed success. Record test commands and observed output.

## Delivery cadence: GRILL ME timeboxes
Execute the roadmap as discrete <=4-hour vertical slices rather than one end-to-end multi-agent run. The execution contract and precise 240-minute breakdown live in `agent/GRILL_ME_4H_TASK.md`. Each slice requires a narrow story, clear non-goals, positive/negative tests and a final memory update. Deploy may mean local container smoke validation unless live AWS was explicitly approved. Security architecture and irreversible side effects remain human-reviewed.
