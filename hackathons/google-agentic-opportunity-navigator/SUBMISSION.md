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

Do not mark these complete until they have been verified on the real Google Cloud deployment:

- [ ] Public or judge-accessible Cloud Run URL
- [ ] Successful `/health` response from Cloud Run
- [ ] Real Gemini turn executed through Google ADK on the deployed service
- [ ] Cloud Run request/log evidence for that turn
- [ ] Final project ID and region recorded in deployment notes
- [ ] Architecture diagram included in submission assets
- [ ] Demo video of 4 minutes or less
- [ ] Repository URL and reproducible setup instructions

## Repository

Use the public AION repository and point judges directly to `hackathons/google-agentic-opportunity-navigator/` so the hackathon-specific implementation is clear.
