# Enterprise Agentic AI Platform — architecture starter

This archive is a **repository-ready starting kit**, not an existing or deployed application.

1. Read `PROJECT_MEMORY.md` as the project-level long-term context.
2. Read `docs/architecture/adr/ADR-001-vector-store-strategy.md`: choice is PROPOSED, not approved.
3. Read `docs/architecture/SYSTEM_ARCHITECTURE.md` and `docs/IMPLEMENTATION_ROADMAP.md`.
4. Copy/paste `agent/AGENT_TASK.md` into any coding agent or ask that agent to read the file and follow the approval gates.
5. Place all files in a project repository (or relevant existing repo). With no repository provided, no actual project state can be audited here.
6. First agent run is **architecture-only**; no AWS provisioning or code changes without human approval.

Project memory here means a **versioned Markdown file in Git**, not ChatGPT account memory.

## Timeboxed execution: 
Use `agent/GRILL_ME_4H_TASK.md` when requesting **one concrete, runnable feature in a single four-hour session**. It specifies Metadata Enrichment → Research → Design → Design QA → Planning → Coding → QA → Pre-Commit Review → Delivery, with strict time budgets and security checks. This does not replace the long-term architecture roadmap or authorise AWS deployment.
