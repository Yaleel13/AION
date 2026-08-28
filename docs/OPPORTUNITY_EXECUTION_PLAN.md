# AION Opportunity Execution Plan

Date: 2026-08-28

This document converts current verified funding and hackathon opportunities into a concrete execution order for AION.

## Priority 1 — Google All Things Agentic Hackathon

Deadline: August 31, 2026 at 5:00 PM PT.

Recommended category: **Taskmaster**.

Why AION fits:
- AION already has durable state, scheduled/background operations, controlled autonomy, audit trails, approval gates, an owner UI, and a revenue/opportunity discovery path.
- The Taskmaster category explicitly rewards completion of a multi-step workflow rather than simple chat.
- AION's strongest submission story is an autonomous opportunity workflow: discover legitimate paid opportunities, score them, reject scams/speculation, persist qualified opportunities, and surface only high-value items for owner review.

Mandatory Google requirements still to satisfy for an eligible submission:
1. Gemini 3.5 or newer through Gemini API or Vertex AI.
2. At least one Google agent framework: Google ADK, GenAI SDK, Antigravity SDK, or GenKit.
3. At least one Google Cloud infrastructure service such as Cloud Run, Cloud SQL, Firestore, GKE, or Pub/Sub.
4. Hosted project URL.
5. Repository with reproducible spin-up instructions.
6. Architecture diagram.
7. Demo video no longer than 4 minutes, including visible proof that the backend is running on Google Cloud.

Execution scope:
- Do **not** rewrite AION.
- Add a narrow Google-compatible adapter around the existing opportunity workflow.
- Prefer Gemini + Google GenAI SDK + Cloud Run as the smallest migration surface.
- Keep Supabase/Postgres and the production AION path intact unless the hackathon adapter requires otherwise.
- Demonstrate a complete workflow: ingest -> verify -> rank -> persist -> owner notification/review.
- Preserve AION safety policy: no live trading, wallet connection, funding requests, token purchases, or automatic outbound contact.

Judging emphasis to optimize for:
- Operational utility and autonomous execution.
- Clear state management and failure tolerance.
- Scoped tools and security boundaries.
- Reproducible documentation and architecture clarity.

## Priority 2 — OpenAI WebMCP Challenge

Deadline: September 3, 2026 at 1:00 PM PT.

A new application is not required; adding WebMCP support to an existing app is explicitly allowed.

Recommended AION concept: **AION Opportunity Review as an agent-native website surface**.

Expose a small set of safe, useful WebMCP tools rather than the entire owner system. Candidate tools:
- `list_opportunities`: return qualified opportunities already collected by AION.
- `get_opportunity`: show evidence, payout/value, deadline, credibility, risk, and fit.
- `rank_opportunities`: rank a bounded set using AION's scoring policy.
- `prepare_review`: create a non-destructive owner review summary.

Do not expose:
- owner secrets or private memory,
- arbitrary repository writes,
- unrestricted outbound messaging,
- wallet or transaction actions,
- internal system prompts.

Submission requirements verified from the challenge site include a project description, working live app, code repository, and demo video. Testing is supported in ChatGPT's in-app browser or Chrome with WebMCP enabled.

Judging optimization:
- usefulness,
- originality,
- execution,
- thoughtful WebMCP usage,
- quality of the human-agent experience.

## Priority 3 — Sentient Foundation Open Source AGI Grant

Status: rolling; no cohort deadline published.

The program states $42M committed and offers a grants/public-goods track with no equity, lockups, or claim on the work.

Do not open-source the entire private owner agent. Prepare a narrow reusable public-good component after the two deadline-driven hackathons.

Best candidate: **AION Safe Opportunity Evaluator** — a provider-neutral library that:
- classifies paid gigs, bounties/grants, partnerships, and Web3 paid work,
- rejects price speculation and unsafe wallet/funding requests,
- scores credibility, fit, urgency, effort, and expected value,
- records evidence and uncertainty,
- supports human approval before outbound action.

For a credible grant application, the open-source component should have a clean standalone README, permissive license decision, tests, example fixtures, and a public roadmap.

## Current AION evidence

The repository already contains a general opportunity engine test suite and revenue discovery logic covering paid gigs, grants/bounties, partnerships, and Web3 paid work while separating crypto market chatter from legitimate paid work. The owner UI also contains an opportunity-review component.

## Execution order

1. Google compatibility slice and Cloud Run proof.
2. Google submission assets: README setup, architecture diagram, <=4 minute demo, Devpost description.
3. WebMCP safe tool surface added to the existing AION web experience.
4. WebMCP demo and submission assets.
5. Extract and harden the open-source-safe opportunity evaluator.
6. Submit Sentient grant application.

## Guardrails

- No purchase or payment to qualify for an opportunity.
- Reddit is discovery-only until independently verified.
- No generic token speculation, gambling, or pump activity.
- No wallet-connect requests or sending funds.
- No automatic contact or application submission without explicit owner approval.
- Never expose AION owner secrets, private memory, API keys, or hidden prompts in a public submission.
