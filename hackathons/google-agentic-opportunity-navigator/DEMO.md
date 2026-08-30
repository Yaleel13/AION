# Opportunity Navigator Demo Runbook

Target length: 3:00–3:40. Hard stop before 4:00.

## 0:00–0:25 — Problem and promise

Show the project title and say:

“Opportunity Navigator helps technical builders compare legitimate ways to earn or secure funding without turning opportunity discovery into speculation or unsafe automation. It uses Google ADK, Gemini, a deterministic scoring tool, and Google Cloud Run.”

## 0:25–0:55 — Architecture

Show `ARCHITECTURE.md` and briefly trace:

User → Cloud Run → Google ADK → Gemini → `score_opportunity` → response.

Call out the explicit safety boundary: no wallets, funds, token purchases, gambling, or autonomous outreach.

## 0:55–1:20 — Prove Google Cloud runtime

Show the Cloud Run service in Google Cloud Console, including service name, region, and active revision. Open the deployed `/health` endpoint and show a successful response.

Do not substitute a local server or Vercel deployment for this evidence.

## 1:20–2:45 — Live agent workflow

Use a prompt similar to:

“Compare these three opportunities for a technical builder and tell me which one deserves attention first. Use the scoring tool when enough evidence is available. Distinguish facts from assumptions and tell me what still needs verification.

A. Verified AI hackathon: $10,000 prize, 12 hours estimated effort, deadline in 5 days, strong eligibility and technical fit, official organizer page.
B. Paid open-source issue: $1,500 bounty, 8 hours estimated effort, no urgent deadline, official repository and maintainer confirmation.
C. Crypto opportunity from a social post promising a large return but requiring a wallet connection and an upfront token purchase.”

Expected demonstration:

- Gemini/ADK reasons over the three opportunities.
- The scoring tool is used for legitimate candidates with enough evidence.
- The suspicious crypto path is rejected or explicitly treated as unsafe rather than ranked as an earning opportunity.
- The answer identifies missing evidence and leaves the final decision to the human.

## 2:45–3:15 — Show backend evidence

Show Cloud Run request/log evidence for the live turn. Make it visually clear that the request hit the Google-hosted backend.

## 3:15–3:40 — Close

Say:

“Opportunity Navigator demonstrates an agent completing a bounded decision workflow: reason, verify uncertainty, invoke deterministic scoring, enforce safety boundaries, and return a prioritized human-review result. The hackathon implementation is isolated from the pre-existing AION runtime and was built specifically for this event.”

## Recording checklist

- [ ] Cloud Run service/revision visible
- [ ] Hosted `/health` response visible
- [ ] Live ADK/Gemini agent turn visible
- [ ] Deterministic ranking/tool behavior visible
- [ ] Unsafe wallet/upfront-payment candidate rejected
- [ ] Cloud Run request/log evidence visible
- [ ] Architecture visible
- [ ] Runtime under 4:00
- [ ] No API keys, tokens, environment secrets, owner credentials, or private AION data visible
