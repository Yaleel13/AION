# Google All Things Agentic — Submission Pack

## Project name

Opportunity Navigator

## Recommended category

Taskmaster

## One-line description

A safe Google ADK agent that helps technical builders compare legitimate earning and funding opportunities, ranks them with a deterministic scoring tool, and clearly separates verified evidence from uncertainty before a human decides what to pursue.

## Submission description

Opportunity Navigator is a new hackathon project inspired by AION's broader opportunity-discovery concepts but implemented as an isolated Google-native agent for this event. It runs on Google Agent Development Kit, uses Gemini, exposes a deterministic `score_opportunity` tool, and is packaged for Google Cloud Run.

The agent is designed for a practical multi-step workflow: a user supplies candidate opportunities such as hackathons, grants, funded bounties, freelance or contract work, partnerships, referral programs, or legitimate Web3 developer work. The agent reviews the available evidence, distinguishes verified facts from inference, invokes deterministic scoring when enough information is available, and returns a ranked shortlist with the remaining evidence required before the user should act.

The scoring tool evaluates expected value, effort, credibility, technical fit, deadline urgency, and eligibility. This keeps the final ranking understandable and reproducible rather than relying entirely on free-form model judgment.

Safety is part of the product design. Opportunity Navigator does not speculate on token prices, gamble, connect wallets, send funds, buy tokens, pay qualification fees, contact third parties automatically, or submit applications automatically. Social and community posts are treated only as discovery leads until independently verified against an official source.

The project demonstrates how an agent can do more than chat: it coordinates model reasoning, a bounded deterministic tool, explicit safety policy, and a hosted cloud runtime to complete a useful decision workflow while keeping the final action with the human.

## What was built during the hackathon

- A new isolated Google ADK agent project.
- Gemini-backed opportunity evaluation instructions and workflow.
- A deterministic opportunity scoring tool.
- FastAPI/ADK serving entrypoint.
- Cloud Run container/deployment configuration.
- Safety tests for high-quality vs. low-quality opportunities.
- Architecture and reproducible deployment documentation.

## Pre-existing work disclosure

AION existed before this hackathon and inspired the opportunity-discovery concept. The Google hackathon project in this directory is intentionally isolated and does not claim AION's pre-existing production runtime, private memory, or existing application infrastructure as newly created hackathon work.

## Suggested judge test

Ask the deployed agent to compare three opportunities with different payout, effort, deadline, eligibility, credibility, and technical-fit profiles. Include one weak or suspicious opportunity. The expected result is a concise ranking, use of deterministic scoring where sufficient evidence exists, explicit uncertainty, and rejection or deprioritization of unsafe or low-credibility paths.

## Evidence that must be attached before submission

Deployment status (Aug 31, 2026):

- [x] Cloud Run URL: https://opportunity-navigator-554734366722.us-central1.run.app
- [x] Revision deployed: opportunity-navigator-00006-bjw
- [x] Service status: ACTIVE and serving 100% traffic
- [x] Service logs confirm: "Uvicorn running on http://0.0.0.0:8080"
- [ ] Public `/health` response: Blocked by organization policy on current Google account
- [x] Authenticated `/health` access via gcloud returns `200 OK`
- [x] Demo video: Will show Cloud Run console, logs proving FastAPI is running, and code architecture
- [x] Real Gemini turn executed through Google ADK using authenticated Cloud Run access; public invocation remains blocked by organization policy.
- [x] Cloud Run request/log evidence captured from the active service revision
- [x] Final project ID: **agent-aion**
- [x] Final region: **us-central1**
- [x] Architecture diagram: [ARCHITECTURE.md](./ARCHITECTURE.md) included in submission assets
- [ ] Demo video of 4 minutes or less
- [x] Repository URL: https://github.com/yalee/AION
- [x] Reproducible setup instructions: [README.md](./README.md) and [DEPLOY_TODAY.md](./DEPLOY_TODAY.md)

**Build Status**: Service deployed and serving traffic on the correct Cloud Run revision.
**Build Logs**: https://console.cloud.google.com/cloud-build/builds;region=us-central1/880a7cc5-5438-4aa4-b7a0-6df2d2aa7a59?project=554734366722
**Access Note**: Google Cloud organization policy is currently blocking public invocation for this project. The service is active, but unauthenticated browser/client access is restricted by policy rather than application code.

## Repository

Use the public AION repository and point judges directly to `hackathons/google-agentic-opportunity-navigator/` so the hackathon-specific implementation is clear.
