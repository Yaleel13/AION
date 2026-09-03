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
- **Model:** Amazon Bedrock-supported model selected for cost/quality after verifying contest eligibility
- **Runtime:** local first; optionally Bedrock AgentCore / AWS compute if useful for judging
- **State:** lightweight durable opportunity ledger
- **Tools:** web/source retrieval adapters, verifier, scoring tool, dedupe/change detector
- **Interface:** minimal web or CLI dashboard showing only qualified opportunities and human-action gates
- **Observability:** structured logs for discovery, verification, filtering, ranking, and escalation

## Judging strategy

### Technical implementation
Show multiple Strands agents/tools cooperating on a real task, with clear error handling and durable state.

### Product experience
Make the demo obvious: noisy public opportunities in -> small verified queue out.

### Real-world impact
Demonstrate time saved and false-positive reduction rather than claiming unmeasured revenue.

### Originality
Differentiate through evidence-first qualification, explicit scam/safety filtering, and human-controlled execution.

## Demo scenario

1. User says: "Find legitimate ways my AI/automation skills could earn money this month."
2. Scout ingests a mixed set containing:
   - valid hackathon;
   - real paid contract;
   - stale bounty;
   - Reddit rumor with no official source;
   - wallet-connect promo;
   - token speculation post.
3. Verifier independently confirms official sources.
4. Risk filter removes unsafe/low-quality items and explains why.
5. Ranker scores remaining opportunities.
6. Agent surfaces the top two with deadlines and action packets.
7. User approves one for application preparation; no external submission is made automatically.

## Safety boundaries

- No autonomous financial transactions.
- No token purchasing or live trading.
- No sending funds to qualify for work.
- No automatic third-party outreach or application submission.
- No secret/private AION owner data in the hackathon project.
- No claim of success without external confirmation.

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

### Phase 3 — real scout/verifier adapters — NEXT
- add real public-source retrieval adapters;
- normalize official-source evidence into Opportunity objects;
- add source freshness and deadline parsing;
- persist the ledger instead of keeping it process-local;
- add structured logging / observability.

### Phase 4 — AWS deployment/evidence
- choose and verify qualifying Bedrock model configuration;
- run a real Strands/Bedrock turn;
- optionally deploy on Bedrock AgentCore / AWS compute where useful for judging;
- capture architecture diagram and logs;
- verify end-to-end run;
- document reused pre-existing concepts/components.

### Phase 5 — submission
- public MIT or Apache-licensed repository as required by the contest;
- strong README and reproducibility instructions;
- <=5-minute demo;
- final Devpost submission.

## External gates

Before claiming submission readiness, verify:
- current AWS contest rules and eligible Strands/Bedrock configuration;
- AWS promotional credit availability;
- public-repository/license requirement;
- exact deadline and submission fields;
- deployed URL if deployment is included in judging.

## Current status

Phases 1 and 2 are implemented on the hackathon branch. The project has not yet been executed against a live Bedrock model or deployed to AWS. No hackathon submission has been filed.
