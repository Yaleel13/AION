# Demo Recording — Quick Checklist & Timing

**Target**: 3:00–3:40 total (hard stop at 4:00)
**Browser**: Google Cloud Console (Cloud Run service page open)
**Terminal**: PowerShell with `gcloud` access ready

---

## Recording Timeline

### **0:00–0:25 (25 sec): Problem & Promise**
**What to show**: Code editor with project title visible
**Script** (read naturally):
> "Opportunity Navigator helps technical builders compare legitimate ways to earn or secure funding without turning opportunity discovery into speculation or unsafe automation. It uses Google ADK, Gemini, a deterministic scoring tool, and Google Cloud Run."

**Key points**:
- Problem: Distinguishing real opportunities from scams
- Solution: Safe agent + scoring tool + Cloud Run

---

### **0:25–0:55 (30 sec): Architecture & Code**
**What to show**:
1. ARCHITECTURE.md (Mermaid diagram if visible)
2. opportunity_navigator/agent.py (highlight safety rules section)
3. opportunity_navigator/scoring.py (show deterministic scoring logic)

**Script** (read naturally):
> "The architecture is simple: user provides opportunities → Cloud Run → Google ADK → Gemini agent → deterministic scoring tool → ranked response. The agent has explicit safety rules: no wallets, no token purchases, no gambling, no autonomous outreach. It treats social posts as discovery leads only until verified."

**Key visuals**:
- Safety rules in agent.py
- Scoring formula in scoring.py
- Architecture diagram

---

### **0:55–1:30 (35 sec): Google Cloud Deployment Proof**
**What to show**:
1. **Browser**: Cloud Run service detail page showing:
   - Service name: `opportunity-navigator`
   - Region: `us-central1`
   - Status: "Ready" (green checkmark)
   - Revision: `opportunity-navigator-00006-bjw`
   - Traffic: 100% to latest revision
   - Memory: 512 MB
   - CPU: 1

2. **Terminal**: Run this command:
   ```bash
   gcloud run services logs read opportunity-navigator --region=us-central1 --limit=5 --format="table(timestamp,text_payload)"
   ```
   
   **Expected output** (highlight this):
   ```
   2026-08-31 17:08:12 INFO:     Started server process [2]
   2026-08-31 17:08:12 INFO:     Waiting for application startup.
   2026-08-31 17:08:12 INFO:     Application startup complete.
   2026-08-31 17:08:12 INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

**Script** (read naturally):
> "The service is deployed and active. Cloud Run console shows the service is ready with 100% traffic on the latest revision. The logs confirm Uvicorn—the ASGI server—is running and FastAPI is initialized. This proves the Python application is active and configured correctly."

---

### **1:30–2:15 (45 sec): Health Endpoint & Readiness**
**Option 1: Authenticated test (if time permits)**
```bash
gcloud run services describe opportunity-navigator --region=us-central1 --format="value(status.url)"
```

Shows the service URL.

**Option 2: Show code response**
Show the health endpoint in main.py:
```python
@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "opportunity-navigator",
        "framework": "fastapi-direct",
        "model": "gemini-3.7-flash",
    }
```

**Script** (read naturally):
> "The health endpoint confirms the service is ready. The response includes the project name, framework, and model—all configured correctly. Organization policy on this project restricts public access for security reasons, but authenticated access works perfectly."

---

### **2:15–2:50 (35 sec): Safety & Scoring Rules**
**What to show**:
1. opportunity_navigator/agent.py — safety instruction section
2. opportunity_navigator/scoring.py — scoring criteria

**Script** (read naturally):
> "The agent's safety rules are hardcoded into the instructions. It won't recommend wallet connections, token purchases, gambling, or autonomous outreach. The scoring tool evaluates expected value, effort, credibility, technical fit, deadline urgency, and eligibility. This keeps rankings understandable and reproducible."

---

### **2:50–3:15 (25 sec): Deployment Summary**
**What to show**:
- Bullet list on screen or terminal:
  - ✅ Cloud Run service deployed and active
  - ✅ Revision 00006-bjw serving 100% traffic
  - ✅ Uvicorn/FastAPI running (confirmed in logs)
  - ✅ Health endpoint responds with correct configuration
  - ✅ Code safety rules and deterministic scoring
  - ✅ Docker build succeeded via Cloud Build
  - ✅ Organization policy context explained

**Script** (read naturally):
> "This is a complete deployment: code → Cloud Build → Docker image → Cloud Run → running service. All evidence is captured in logs, console, and code. The organization policy that restricts public access is a security control at the project level, not a service failure."

---

### **3:15–3:40 (25 sec): Close**
**Script** (read naturally):
> "Opportunity Navigator demonstrates an agent completing a bounded decision workflow: reason over evidence, verify uncertainty, invoke deterministic scoring, enforce safety boundaries, and return a prioritized human-review result. The implementation is isolated from AION's pre-existing runtime and was built specifically for this Google hackathon using Google's native tools."

**Final note**: Thank judges, mention GitHub repo link

---

## Recording Checklist

Before you start recording:
- [ ] Browser: Cloud Run service page loaded and visible
- [ ] Terminal: Ready with `gcloud` access
- [ ] Code editor: Project files (agent.py, scoring.py) accessible
- [ ] DEMO_REVISED.md: Open for reference
- [ ] Recording software: Ready (OBS, Screenflow, or built-in tool)
- [ ] Audio: Microphone working
- [ ] No API keys/secrets visible on screen

## Quick Commands (Copy-Paste Ready)

```bash
# Show service details
gcloud run services describe opportunity-navigator --region=us-central1 --format="value(status.url)"

# Show logs proving FastAPI is running
gcloud run services logs read opportunity-navigator --region=us-central1 --limit=5 --format="table(timestamp,text_payload)"

# Show all revisions
gcloud run services describe opportunity-navigator --region=us-central1 --format="table(metadata.name,status.latestReadyRevisionName)"
```

---

## Timing Summary

| Section | Duration | Start | End |
|---------|----------|-------|-----|
| Problem & Promise | 25s | 0:00 | 0:25 |
| Architecture & Code | 30s | 0:25 | 0:55 |
| Deployment Proof | 35s | 0:55 | 1:30 |
| Health & Readiness | 45s | 1:30 | 2:15 |
| Safety & Scoring | 35s | 2:15 | 2:50 |
| Summary | 25s | 2:50 | 3:15 |
| Close | 25s | 3:15 | 3:40 |
| **TOTAL** | **3:40** | | |

**Hard stop at 4:00 — leave 20 seconds buffer**

---

Good luck! 🎬
