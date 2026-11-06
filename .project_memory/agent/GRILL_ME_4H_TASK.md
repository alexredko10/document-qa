# GRILL ME — 4-HOUR AGENT-AGNOSTIC DELIVERY TASK

**Workflow version:** 1.0 | **Timebox:** 240 minutes total | **Execution:** one narrowly scoped vertical slice per session
**Compatibility:** Codex / Claude Code / Cursor / local orchestration / any coding agent. No agent-specific commands.

## Mission
Deliver ONE small, testable increment of the Enterprise Agentic AI Reference Platform in <=4 hours. Follow the ordered GRILL ME workflow: Metadata Enrichment → Research → Design → Design QA → Planning → Coder → Implementation QA → Pre-Commit Reviewer → Deploy/Delivery Validation. Preserve enterprise thinking without trying to build the enterprise platform in one session.

## Must-read context
- `PROJECT_MEMORY.md`: decisions versus proposals, non-negotiable security, target architecture.
- `docs/architecture/adr/ADR-001-vector-store-strategy.md`: S3 Vectors preferred first candidate; DynamoDB vector search comparative option; status proposed.
- `docs/architecture/SYSTEM_ARCHITECTURE.md`, `docs/IMPLEMENTATION_ROADMAP.md`.
- Existing code, tests, workflows, decisions; repo evidence overrides aspirational docs.

## Session input (fill before starting)
- Feature / single user story: <ONE STORY>
- User & business problem: <WHO / WHY>
- Acceptance criteria (max 3): <MEASURABLE>
- Explicit non-goals: <OUT OF SCOPE>
- Available environment & permissions: <LOCAL / SANDBOX / AWS APPROVED?>
- Timebox: 240 minutes absolute, including tests/review/docs.

If the story is not specified, propose 2-3 small candidates and recommend the smallest, but do not start arbitrary infrastructure changes. For the first session without a codebase, recommend: **synthetic corpus → deterministic metadata enrichment → authorised retrieval interface (mock vector adapter) → deny-by-default tests**, with no live AWS provisioning. Prefer demonstrating secure boundaries over installing many frameworks.

## 4-hour schedule (hard budget)
| Stage | Minutes | Expected output |
|---|---:|---|
| 0. Metadata Enrichment / Grill Me | 15 | Clarify story, actors, permissions, data classification, examples, assumptions, acceptance tests, risk; challenge weak requirements |
| 1. Research | 20 | Inspect repo and official docs if available; verify SDK/tool capabilities; state unknowns; no broad survey |
| 2. Design | 25 | One-page design, data flow, interfaces, security boundary, trade-off, smallest viable scope |
| 3. Design QA | 10 | Adversarial review: access bypass, data leakage, missing acceptance criteria, cost, overengineering |
| 4. Planning | 10 | 3-6 coding steps, exact file targets, tests and rollback |
| 5. Coder | 95 | Implement thin end-to-end slice with tests, avoid unrelated refactors |
| 6. Implementation QA | 35 | Unit/negative tests, lint/type checks, integration via mocks, verify acceptance criteria, report gaps |
| 7. Pre-Commit Reviewer | 10 | Inspect diff, secrets, unused dependencies, architecture/security rules, docs, commit readiness |
| 8. Deploy / Delivery Validation | 20 | Local container/smoke validation by default; live AWS only with explicit prior approval and credentials; update memory |
| **TOTAL** | **240** | **Deliver one demonstrable increment** |

**Note:** Pre-commit review is intentionally **before** deployment. Even if a naming template lists it last, actual execution must respect this safety dependency. If doing a remote deployment, validate plan and blast radius beforehand and require explicit approval.

## How to shorten without losing engineering discipline
- Combine Research + Design in a shared evidence pass; keep distinct outputs only if needed.
- Design QA = a 10-minute checklist review, not a separate autonomous agent or long meeting.
- Planning = compact checklist, not a large BMAD package.
- One coding agent, one focused independent QA pass; do not build a multi-agent mesh for a small story.
- Reuse existing linters/tests/CI. No new SonarCloud/Argo CD/Terraform stack unless the selected story is specifically infrastructure.
- Run quick deterministic tests locally; postpone full load, DAST, mutation suites and extensive LLM Judge experiments to scheduled backlog items.
- Mock Bedrock and vector backends in quick tests; one live integration smoke test only when approved, affordable, and available.
- Use the minimum adapter interfaces needed for future migration; no abstraction explosion.
- No continuous agent debate. Max one Design QA feedback loop and one Implementation QA fix loop.
- Stop adding features at minute 170; reserve last 70 minutes for QA/review/delivery.

## Metadata Enrichment / GRILL ME gate
Before coding, challenge the story with these questions. Answer from available context; ask the human only for a genuinely blocking choice.
1. Who is the principal? How is identity verified (not supplied by LLM)?
2. What resource is requested, with tenant/role/security labels?
3. What exact success and deny cases must work?
4. What is trusted/untrusted: user input, documents, LLM-generated tool arguments?
5. What is the authoritative source of policy and approved document state?
6. What is the smallest runnable demonstration and how will we measure it?
7. Which external services cost money? What can be mocked?
8. What is NOT being implemented in this four-hour session?
Output: concise `SESSION_BRIEF.md` or PR description (<=1 page).

## Non-negotiable quality/security
- Default deny, validate tool name and argument schema; enforce role, tenant and resource authorisation server-side.
- Never permit an LLM, Judge, LangGraph, or retrieved document to grant access or bypass guardrails.
- No real patient/HR/finance PII; use synthetic fixtures. No credentials in logs/commits.
- Tests must include at least one allowed and one denied path. For tool features, test invalid tool name, malformed arguments and cross-role/resource access.
- Preserve approved-source provenance and chunk authorisation when the story involves knowledge.
- No AWS provisioning or paid deployments without explicit authorisation; budgets/alarms are not spending hard caps.
- Be honest about implementation status, measured metrics and test coverage.

## Deliverables at end of session
1. A runnable minimal increment (or a clearly documented blocker, not a claim of success).
2. Tests/commands executed, their results, and known omissions.
3. Short architecture rationale and list of files changed.
4. Security assumptions, failing/negative-path evidence, cost implications.
5. Updated `PROJECT_MEMORY.md` with *verified completed work* and open questions; never mark proposed features implemented.
6. A five-minute demo script and next recommended smallest story.

## Timebox escalation
- By 60 min: design approved/assumptions explicit; if blocked, select narrower scope.
- By 120 min: skeleton working; otherwise cut optional frameworks and integrations.
- By 170 min: feature freeze; tests and verification only.
- At 240 min: STOP; deliver honest status and next steps. Never silently exceed the timebox.

## First task suggestion for a new empty repository
**Story:** A secure retrieval stub using synthetic Finance and HR documents.
- Metadata enrichment: assign source_id, tenant_id, department, status, version, sensitivity and permitted roles to fixtures.
- Design: document/chunk lineage and `VectorStore` contract; mock embeddings/search with fixed results; no Bedrock dependency yet.
- Code: authorised retrieval service that excludes unapproved documents and denies Finance→HR content even when mock retrieval returns it.
- QA: positive Finance access, negative HR access, missing/invalid labels, unapproved document, revoke semantics if feasible.
- Demo: same query under two distinct server-verified principals; log decision metadata without content leakage.
- Explicitly defer: K3s, Argo CD, model routing, live Bedrock, LLM Judge, vector-store performance benchmark, admin UI.

## Closing principle
**Make one small, secure, measurable change within four hours. Architecture ambition belongs in the roadmap; implementation scope belongs in the timebox.**
