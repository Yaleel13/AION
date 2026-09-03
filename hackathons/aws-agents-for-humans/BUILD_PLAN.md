# AWS Agents for Humans 2026 — AION-Derived Build Plan

## Working project title

**AION Opportunity Operator — Strands Edition**

## Objective

Build a new hackathon project during the contest period that turns a user goal such as "find me legitimate AI work worth pursuing" into a bounded background workflow:

1. discover candidate opportunities;
2. verify official sources;
3. reject scams, upfront-fee offers, speculative trading, and wallet-connect requirements;
4. rank the survivors by expected value, effort, urgency, eligibility, credibility, and fit;
5. prepare an action packet;
6. surface only the decisions that require human review.

This is inspired by AION but should be implemented as a new project using the AWS Strands Agents SDK, with any reused pre-existing concepts or code disclosed.

## Why this fits Agents for Humans

The hackathon emphasizes agents that do useful work end-to-end and reduce repetitive operational burden. This project is designed to run as a professional background agent that continuously turns public opportunity noise into a concise, verified queue.

## Core user story

> I want a trustworthy agent that scouts legitimate revenue/funding opportunities, verifies them, rejects unsafe or low-quality leads, and only interrupts me when something is worth acting on.

## MVP scope

### Agent 1 — Scout
Search configured public sources for hackathons, grants, contracts, paid open-source issues, partnerships, and non-speculative Web3 technical work.

### Agent 2 — Verifier
Require an official or otherwise high-authority source before promoting an opportunity. Reddit/social content is discovery-only.

### Agent 3 — Risk filter
Reject:
- upfront-fee/pay-to-qualify offers;
- wallet-connect requirements solely to enter;
- token-price speculation;
- gambling/trading contests;
- unverifiable payment claims;
- stale/expired opportunities;
- suspicious credential or fund-transfer requests.

### Agent 4 — Ranker
Score:
- expected payout/value;
- effort;
- deadline urgency;
- eligibility;
- credibility;
- technical fit.

### Agent 5 — Briefing / human gate
Produce a compact decision packet with evidence links, risks, deadline, next action, and a recommendation. Do not submit applications or contact third parties without explicit authorization.

## Technical architecture

- **Agent framework:** AWS Strands Agents SDK
- **Model:** Amazon Bedrock, explicitly configured for live verification
- **Runtime:** local first; optionally Bedrock AgentCore / AWS compute if useful for judging
- **State:** persistent opportunity ledger
- **Tools:** public-source retrieval adapters, verifier, scoring tool, dedupe/change detector
- **Interface:** minimal FastAPI human-review surface
- **Observability:** structured logs for discovery, verification, filtering, ranking, escalation, and live verification

## Build sequence

### Phase 1 — skeleton — IMPLEMENTED
- isolated Strands project;
- typed opportunity/evidence/decision models;
- deterministic safety rejection and ranking logic;
- sample scoring tests;
- Strands tool wrapper.

### Phase 2 — qualification pipeline — IMPLEMENTED
- official-source verification gate;
- stable opportunity fingerprinting;
- material-change signature and ledger;
- same-batch dedupe;
- unchanged-result silence behavior;
- mixed-opportunity demo fixtures;
- minimal FastAPI human-review endpoint;
- tests for social-only rejection, dedupe, silence, and material payout changes.

### Phase 3 — scout/verifier foundations — IMPLEMENTED
- read-only public JSON retrieval adapter;
- explicit provenance normalization;
- UTC deadline normalization;
- persistent JSON-backed ledger;
- structured JSON observability;
- restart-persistence tests.

### Phase 4 — AWS live verification — HARNESS READY, EXECUTION PENDING
- explicit Strands `BedrockModel` configuration;
- verified default model example: `global.anthropic.claude-sonnet-4-6`;
- safe `live_verify.py` fixture;
- credential-safe execution instructions;
- live AWS invocation still required on an authenticated AWS execution host;
- optional Bedrock AgentCore deployment after the basic model turn succeeds.

### Phase 5 — submission
- public MIT or Apache-licensed repository as required by the contest;
- architecture diagram;
- strong README and reproducibility instructions;
- <=5-minute demo;
- final Devpost submission.

## Safety boundaries

- No autonomous financial transactions.
- No token purchasing or live trading.
- No sending funds to qualify for work.
- No automatic third-party outreach or application submission.
- No secret/private AION owner data in the hackathon project.
- No AWS credentials in Git.
- No claim of live success without external confirmation.

## Current status

Phases 1-3 are implemented. The Phase 4 live-verification harness is implemented and configured against the current Strands Bedrock provider pattern. The project has **not yet produced a verified live Bedrock success event or AWS deployment**, and no hackathon submission has been filed.
