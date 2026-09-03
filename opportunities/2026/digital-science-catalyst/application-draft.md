# Digital Science Catalyst Grant 2026 — Application Draft

## Working project title

**AION Research Provenance Engine — Agentic Workflows You Can Trust**

## One-line proposition

A research agent that plans and executes multi-step investigations while preserving source provenance, separating evidence from inference, requiring human approval for consequential actions, and producing an auditable record of what it did and why.

## Why this fits the 2026 Catalyst theme

Digital Science's 2026 theme is **Agentic Workflows You Can Trust**. The official program emphasizes autonomous, multi-step research workflows with provenance, governance, accountability, and visible working rather than single-prompt generation.

This proposal intentionally narrows AION to a public research-workflow component rather than presenting the entire private personal-agent system as the grant project.

## Problem

Research work increasingly involves many loosely connected steps: finding candidate sources, checking source authority and recency, extracting claims, comparing conflicting evidence, recording citations, identifying uncertainty, synthesizing findings, and deciding what requires expert review.

General-purpose AI can accelerate these steps, but adoption in institutional research settings is constrained by trust. A useful agent must make it possible to determine:

- what source supported each important claim;
- which conclusions are direct evidence versus inference;
- what the agent attempted, changed, or declined to do;
- where uncertainty or conflicting evidence remains;
- which actions required human approval;
- whether a result can be reproduced or independently checked.

## Proposed solution

The AION Research Provenance Engine is a bounded agentic workflow that turns a research objective into an auditable investigation.

### Workflow

1. **Objective decomposition** — break the research request into explicit questions and success criteria.
2. **Source discovery** — identify candidate sources and record their origin, date, authority, and retrieval context.
3. **Evidence extraction** — capture claim-level evidence linked to its source rather than only storing a final summary.
4. **Verification** — compare claims across sources, flag conflicts, stale information, missing evidence, and unsupported assertions.
5. **Reasoned synthesis** — distinguish verified facts, inference, recommendation, and uncertainty.
6. **Human checkpoints** — stop for approval before consequential external actions, publication, or use of sensitive/private data.
7. **Audit receipt** — produce a machine-readable and human-readable record of sources, decisions, tool calls, confidence, approvals, and unresolved questions.

## Trust architecture

The project will treat trust as an architectural property rather than a tone or disclaimer.

### Provenance

Each material claim is linked to source metadata and the evidence used to support it. Source authority and freshness are stored separately from the generated conclusion.

### Governance

Actions are classified by consequence. Read-only research can proceed autonomously within scope; publishing, sending, modifying external systems, financial activity, credential use, or other consequential actions require explicit authorization.

### Accountability

The agent records its workflow state, tool calls, evidence transitions, approval events, and terminal outcome. It must not report an action as completed unless the relevant system confirms completion.

### Uncertainty and refusal

The agent exposes unresolved conflicts and missing evidence rather than filling gaps with plausible text. When a requested action falls outside approved scope, the system should stop or escalate instead of improvising authority.

## Current state

AION already contains experimental foundations relevant to this proposal, including durable storage, agent orchestration, controlled-autonomy patterns, opportunity/evidence review workflows, and owner-facing approval concepts. This application should not claim that the research-provenance product is complete. The Catalyst-funded work would extract, harden, evaluate, and document a focused research component suitable for public or institutional use.

## What the grant would fund

### Work package 1 — Provenance data model

Design claim/source/action/approval records with explicit relationships and supersession history.

### Work package 2 — Research workflow engine

Implement decomposition, source collection, evidence extraction, cross-source verification, synthesis, and escalation.

### Work package 3 — Trust and governance controls

Implement bounded permissions, approval checkpoints, prompt-injection-resistant treatment of retrieved content, and auditable action receipts.

### Work package 4 — Evaluation

Create an evaluation set that measures citation correctness, unsupported-claim rate, conflict detection, source freshness handling, approval-boundary compliance, and reproducibility.

### Work package 5 — Demonstrator

Deliver a working demonstrator showing an end-to-end research task from question to evidence graph to reviewed synthesis and audit receipt.

## Proposed measurable outcomes

Targets to refine before submission:

- citation-to-claim support accuracy;
- unsupported material claim rate;
- percentage of conflicting-source cases correctly surfaced;
- percentage of consequential actions correctly routed to approval;
- successful reproduction of an investigation from its audit receipt;
- median researcher time saved on a defined benchmark workflow.

No numerical performance claims should be entered in the application until measured.

## Users

Initial target users are research-intensive teams that need AI acceleration without losing traceability: research organizations, innovation teams, grant/funding analysts, knowledge-management teams, and technical due-diligence workflows.

## Differentiation

The proposed system is not positioned as another chat interface. Its differentiation is the combination of:

- multi-step autonomous research;
- claim-level provenance;
- evidence/inference separation;
- explicit action governance;
- human approval at consequential boundaries;
- reproducible audit receipts;
- evaluation of trust behavior, not only answer quality.

## Commercial / sustainability path

A public or open core can establish the provenance and evaluation standard, while deployment, connectors, institutional policy configuration, private data integrations, hosted operations, and workflow customization can support a commercial services or SaaS layer.

This section should be adjusted to the Catalyst application form's precise commercialization questions.

## Requested award

**Up to £25,000 equity-free**, allocated primarily to focused engineering, evaluation, demonstration, documentation, and user validation.

A detailed budget should be finalized only after the application form's eligible-cost fields are confirmed.

## 90-day execution outline

### Days 1–30
- freeze research workflow scope;
- implement provenance schema;
- define evaluation tasks and trust metrics;
- build minimal source/evidence ingestion pipeline.

### Days 31–60
- implement verification and synthesis stages;
- add approval/governance controls;
- implement audit receipt and replayable investigation record;
- run internal evaluations.

### Days 61–90
- harden UI/API demonstrator;
- test with representative research workflows;
- document limitations and failure cases;
- prepare public demonstration and grant progress report.

## Evidence still needed before submission

- Exact Catalyst application questions and word limits.
- One concise demonstration scenario grounded in a real research workflow.
- Measured baseline or prototype evidence; do not invent metrics.
- Named project lead / applicant identity and organization structure as required by the form.
- Final budget.
- Any public repository or demo URL we choose to disclose.
- Explicit description of what is pre-existing AION work versus grant-funded new work.

## Source verification

Verified on 2026-09-03 from Digital Science's official 2026 Catalyst announcement:

- applications opened September 1, 2026;
- deadline October 5, 2026 at 5 PM BST / 12 PM EDT;
- up to £25,000 equity-free;
- global eligibility for individuals, startups, and research teams;
- prototype, working product, or well-formed concept can qualify;
- 2026 focus is trustworthy agentic research workflows with provenance, governance, and accountability.
