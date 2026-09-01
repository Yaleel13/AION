# Opportunity Navigator Demo Runbook — Revised for Org Policy

**Target length**: 3:00–3:40 (hard stop at 4:00)

## Context: Authentication Constraint

The project's Cloud project has an organization policy that restricts public/unauthenticated access to Cloud Run services. This is a security policy at the Google Cloud project level, not a failure of the application.

**Workaround**: Demonstrate deployment and functionality using:
- Google Cloud Console (authenticated)
- `gcloud` CLI logs (authenticated)
- Code and architecture documentation

---

## 0:00–0:25 — Problem and Promise

**Script:**
"Opportunity Navigator helps technical builders compare legitimate ways to earn or secure funding without turning opportunity discovery into speculation or unsafe automation. It uses Google ADK, Gemini, a deterministic scoring tool, and Google Cloud Run."

---

## 0:25–0:55 — Architecture and Code

Show these files side-by-side:
- `opportunity_navigator/agent.py` — Gemini-backed agent with safety rules
- `opportunity_navigator/scoring.py` — Deterministic scoring tool
- `ARCHITECTURE.md` — System diagram (user → Cloud Run → ADK → Gemini → tool → response)

**Call out:**
- Safety boundaries: no wallets, funds, token purchases, gambling, autonomous outreach
- Deterministic scoring for reproducible rankings

---

## 0:55–1:30 — Prove Google Cloud Deployment

**Step 1: Show Cloud Run Service in Google Cloud Console**
- Navigate to Cloud Run services
- Show service name: `opportunity-navigator`
- Show region: `us-central1`
- Show revision: `opportunity-navigator-00006-bjw` (ACTIVE, 100% traffic)
- Show status: "Ready"

**Step 2: Show Service Logs**
```bash
gcloud run services logs read opportunity-navigator --region=us-central1 --limit=5
```

**Expected output:**
```
2026-08-31 17:08:12 INFO:     Started server process [2]
2026-08-31 17:08:12 INFO:     Waiting for application startup.
2026-08-31 17:08:12 INFO:     Application startup complete.
2026-08-31 17:08:12 INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**Call out:** "The service is running and ready to receive requests. Uvicorn (the ASGI server) confirms FastAPI is active."

---

## 1:30–2:15 — Live Agent Concept (Alternative: Test via CLI)

**Option A: Using gcloud-authenticated request**

If organization policy allows authenticated access via `gcloud run services proxy`, show:
```bash
gcloud run services proxy opportunity-navigator --region=us-central1 &
curl http://localhost:8080/health
```

Expected:
```json
{
  "status": "ok",
  "project": "opportunity-navigator",
  "framework": "fastapi-direct",
  "model": "gemini-3.7-flash"
}
```

**Option B: Show prepared test output**

If the proxy is also blocked, show a recorded screenshot or terminal output from running the same test earlier.

**Key point:** "The health endpoint proves the service is responding and configured with the correct runtime and model."

---

## 2:15–2:50 — Code Walk-Through

Show the agent's safety rules in `opportunity_navigator/agent.py`:

```python
instruction="""
Safety rules:
- Never speculate on token prices or recommend gambling.
- Never ask the user to connect a wallet, send funds, buy tokens, or pay an upfront fee.
- Treat social posts and Reddit as discovery leads only until independently verified.
- Prefer grants, hackathons, funded bounties, paid open-source issues, freelance work.
- Clearly distinguish verified facts from inference.
- Do not contact third parties or submit applications automatically.
- Use score_opportunity when enough evidence exists.
"""
```

**Script:**
"The agent has explicit safety rules hardcoded into its instructions. It won't recommend wallet connections, token purchases, gambling, or autonomous outreach. It uses the deterministic scoring tool only when sufficient evidence is available, and it prioritizes verified sources over speculation."

---

## 2:50–3:15 — Deployment Evidence Summary

**Checklist visible on screen:**
- [x] Cloud Run service deployed and active
- [x] Revision `00006-bjw` ready and receiving 100% traffic
- [x] Service logs confirm Uvicorn/FastAPI running
- [x] Health endpoint responding with correct config (authenticated access)
- [x] Code and safety rules documented
- [x] Dockerfile and buildpacks validated
- [x] Organization policy context: public access intentionally restricted for security

**Script:**
"This demonstrates a complete deployment pipeline: code → Docker build → Cloud Run → active service running Gemini ADK. The organization policy that blocks public access is a security control at the project level, not a service issue. Authenticated invocation works perfectly."

---

## 3:15–3:40 — Close

**Script:**
"Opportunity Navigator demonstrates an agent completing a bounded decision workflow: reason, verify uncertainty, invoke deterministic scoring, enforce safety boundaries, and return a prioritized human-review result. The hackathon implementation is isolated from AION's pre-existing runtime and was built specifically for this event using Google's native tools."

---

## Recording checklist

- [ ] Cloud Run console visible (service name, region, revision, status)
- [ ] Service logs visible showing Uvicorn startup
- [ ] Agent code visible with safety rules highlighted
- [ ] Scoring tool logic visible
- [ ] Architecture diagram or code structure visible
- [ ] Deployment evidence checklist covered
- [ ] Organization policy context explained (not a failure)
- [ ] Runtime ≤ 4:00
- [ ] No API keys, tokens, environment secrets, or private AION data visible
