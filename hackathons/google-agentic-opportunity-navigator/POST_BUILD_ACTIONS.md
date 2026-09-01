# WHEN BUILD COMPLETES ✅

The terminal will show output like this:

```
✓ Service [opportunity-navigator] revision [opportunity-navigator-00001-xyz] has been deployed and is serving 100% of traffic.
Service URL: https://opportunity-navigator-xxxxx-uc.a.run.app
```

## Immediate Actions (5 minutes)

### 1. Save the URL
Copy the Service URL and keep it handy. You'll need it for the demo.

### 2. Test Health Check
```bash
curl https://YOUR_SERVICE_URL/health
```

Should return:
```json
{
  "status": "ok",
  "project": "opportunity-navigator",
  "framework": "google-adk",
  "model": "gemini-3.7-flash"
}
```

### 3. Update Submission Document
Edit SUBMISSION.md and README.md with your Cloud Run URL:
- Replace `YOUR_URL` with the actual URL
- Save files

## Record Demo Video (20-30 minutes)

Follow `DEMO.md` runbook exactly:

**0:00–0:55** — Problem, promise, architecture  
**0:55–1:20** — Proof of Cloud Run in Google Cloud Console  
**1:20–2:45** — Live agent conversation  
**2:45–3:15** — Show Cloud Run logs/request evidence  
**3:15–3:40** — Close statement  

**TOTAL: ≤4 minutes, stop before 4:00**

### Testing agent before demo
Quick test with your URL:
```bash
curl -X POST https://YOUR_SERVICE_URL/agents/opportunity_navigator/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Compare A) hackathon $10k 12h 5day, strong fit; B) bounty $1.5k 8h no deadline; C) crypto social post with wallet + upfront token purchase."
      }
    ]
  }'
```

Expected: Agent reasoning + scoring + rejection of unsafe opportunity.

## Submit to Devpost (5 minutes before deadline)

1. Go to [Google All Things Agentic on Devpost](https://devpost.com/)
2. Fill out submission:
   - **Project name**: Opportunity Navigator
   - **Category**: Taskmaster
   - **Repository**: https://github.com/yalee/AION/tree/main/hackathons/google-agentic-opportunity-navigator
   - **Description**: From SUBMISSION.md
   - **Demo video**: Upload or link
   - **Cloud Run URL**: Your deployed service URL

3. **Click SUBMIT** before 5:00 PM PT

---

**Timeline**: 
- Now: Build completing (10-15 min remaining)
- 1:30-2:15 PM PT: Demo video recording
- 4:45-5:00 PM PT: Final submission

You're on track! 🚀
