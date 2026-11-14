# Agent Workflow

## Roles

### Orchestrator

Owns scientific/architectural direction, mission decomposition, acceptance decisions, and review prompts.

### Implementation Agent

Implements one narrow mission.

It must:

- read mandatory project memory;
- inspect existing code before editing;
- make the smallest sufficient change;
- run mission-specific tests;
- report assumptions and deferred work;
- never manage Git state.

### Independent Review Agent

Did not implement the mission.

It must:

- independently inspect source and tests;
- assume the implementation report may be incomplete or wrong;
- verify scientific and engineering contracts;
- avoid source edits;
- avoid mutating tools on the owner's working tree;
- never repair Git/working-tree state.

### Independent Scientific Validation Agent

Used only when a mission contains substantial numerical/physical risk.

It focuses on:

- physical formulas;
- units;
- independent numerical oracles;
- detector conventions;
- uncertainty semantics;
- edge cases.

It should not redesign the software unless a scientific defect requires a correction.

## Mission cycle

```text
orchestrator defines narrow mission
        |
implementation agent
        |
implementation report + tests
        |
independent reviewer
        |
orchestrator verdict
        |
small repair if required
        |
targeted verification
        |
mission CLOSED
```

Complex scientific missions may add an independent scientific validation step before closure.

## Scope discipline

One mission should primarily modify one conceptual layer.

Do not combine:

- geometry + masks + integration + features;
- storage + retrieval + classification;
- scientific implementation + frontend;
- legacy cleanup + new XRD development.

## Legacy-code safety

Treat:

- `document-qa-prototype/`
- `document-qa/`

as read-only unless the mission explicitly names a specific integration file.

## Change reports

Every implementation report should include:

- exact files changed;
- design decisions;
- exact test commands/results;
- assumptions;
- deferred items;
- unrelated repository state observed but not touched.

Every review report should include:

- verdict;
- findings with severity;
- independent test result;
- scope verification;
- explicit statement that Git/legacy state was not repaired.
