# XRD Project Memory

This directory is the stable operational memory for agents working on `xrd-platform/`.

Agents must not rely on chat history as the source of truth. They must read the project documents before changing code.

## Mandatory reading order

For every implementation mission:

1. `.agents/skills/project-workflow/SKILL.md`
2. `xrd-platform/.project_memory/AGENT_SPEC.md`
3. `xrd-platform/.project_memory/PROJECT_CONSTITUTION.md`
4. `xrd-platform/.project_memory/ROADMAP.md`
5. `xrd-platform/.project_memory/PROJECT_STATE.md`
6. the mission-specific files explicitly named by the orchestrator
7. `xrd-platform/.project_memory/IMPLEMENTATION_AGENT_BASE.md`

For every independent review:

1. `.agents/skills/project-workflow/SKILL.md`
2. `xrd-platform/.project_memory/AGENT_SPEC.md`
3. `xrd-platform/.project_memory/PROJECT_CONSTITUTION.md`
4. `xrd-platform/.project_memory/ROADMAP.md`
5. `xrd-platform/.project_memory/PROJECT_STATE.md`
6. `xrd-platform/.project_memory/INDEPENDENT_REVIEW_AGENT_BASE.md`
7. the implementation and tests being reviewed

## Precedence

If documents conflict, use this order:

1. Explicit current mission instructions from the orchestrator
2. `AGENT_SPEC.md`
3. `PROJECT_CONSTITUTION.md`
4. accepted ADRs in `xrd-platform/docs/decisions/`
5. `SCIENTIFIC_GUARDRAILS.md`
6. `ROADMAP.md`
7. supporting audit/reference documents

An agent must not silently resolve a scientific conflict. Report it.

## Project phase

The current phase is **corpus preparation and scientific validation**.

It is not a disease-classification project yet.

The immediate target is a reproducible physical XRD encoding pipeline satisfying `XRD-CHUNK-096-v1`.
