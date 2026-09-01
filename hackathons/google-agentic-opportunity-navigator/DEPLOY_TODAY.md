# CRITICAL PATH: Cloud Run Deployment — Aug 31

**Deadline**: 5:00 PM PT today  
**Status**: Code ready, deployment in progress

## Prerequisites (if not already set up)

```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

## Deploy to Cloud Run

From the `hackathons/google-agentic-opportunity-navigator/` directory:

```bash
# Deploy with Vertex AI authentication (preferred for production)
gcloud run deploy opportunity-navigator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),GOOGLE_CLOUD_LOCATION=global \
  --timeout=3600 \
  --memory=512Mi \
  --cpu=1
```

**If Vertex AI fails**, fall back to direct Google AI API key:

```bash
gcloud run deploy opportunity-navigator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_API_KEY \
  --timeout=3600 \
  --memory=512Mi \
  --cpu=1
```

## Verify Deployment

The `gcloud run deploy` command will output a public URL. Save it.

```bash
# Health check (replace URL)
curl https://opportunity-navigator-xxxxx-uc.a.run.app/health
```

Expected response:
```json
{
  "status": "ok",
  "project": "opportunity-navigator",
  "framework": "google-adk",
  "model": "gemini-3.7-flash"
}
```

If this succeeds, **the deployment is live**.

## Quick Demo Test

Use the Cloud Run URL to test a live agent turn before recording:

```bash
curl -X POST https://opportunity-navigator-xxxxx-uc.a.run.app/agents/opportunity_navigator/messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Compare these opportunities: (A) hackathon $10k, 12h, 5 days, high fit. (B) bounty $1.5k, 8h, no deadline. (C) crypto post requiring wallet + upfront token purchase."
      }
    ]
  }'
```

This confirms Gemini is responding through ADK.

## Demo Recording

Use the `DEMO.md` runbook with the actual Cloud Run URL:
- 0:00–0:25: Problem & promise
- 0:25–0:55: Architecture (show ARCHITECTURE.md)
- 0:55–1:20: Cloud Run Console proof + `/health` response
- 1:20–2:45: Live agent workflow (use the test prompt above)
- 2:45–3:15: Cloud Run logs/requests
- 3:15–3:40: Close

**Max 4 minutes. Stop before 4:00.**

## Before 5 PM PT Submission

Collect these files in the hackathon directory:

1. **Deployed URL** — update `README.md` and `SUBMISSION.md` with the public Cloud Run URL
2. **Demo video** — name it `DEMO_VIDEO.mp4` or note platform URL
3. **Architecture diagram** — already in `ARCHITECTURE.md`
4. **Project ID & region** — add to submission notes
5. **Evidence checklist** — verify all items in `SUBMISSION.md`

## Devpost Submission

Go to [Devpost Google All Things Agentic](https://devpost.com/) and:

1. Link this repository: `https://github.com/yalee/AION/tree/main/hackathons/google-agentic-opportunity-navigator`
2. Paste submission description from `SUBMISSION.md`
3. Upload or link demo video
4. Include the live Cloud Run URL
5. **Submit before 5:00 PM PT**

---

## Troubleshooting

### Deployment hangs or fails

Check build logs:
```bash
gcloud builds log --limit=50
```

If the image build fails, verify `requirements.txt` is correct and the Dockerfile syntax is valid.

### Health check fails (401/403)

- Verify `GOOGLE_API_KEY` is set and valid, OR
- Verify Vertex AI is enabled and service account has `aiplatform.resourceReader` role

### Agent endpoint not responding

```bash
# Check Cloud Run logs
gcloud run logs read opportunity-navigator --limit=50
```

If logs show import errors, the Google ADK or dependencies may not have installed correctly. Rebuild and redeploy.

### Video length problem

If your demo is running long, prioritize:
1. Architecture (fastest)
2. Proof of Cloud Run (essential)
3. Agent turn + unsafe candidate rejection (core demo)
4. Logs (fast)

---

## Success Criteria

- ✅ Cloud Run deployment is live and public
- ✅ `/health` returns 200 OK
- ✅ Agent accepts a message and returns a Gemini response
- ✅ Demo video is ≤4 minutes
- ✅ Submission arrives before 5:00 PM PT

Good luck! 🚀
