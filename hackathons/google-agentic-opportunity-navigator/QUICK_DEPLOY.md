# Quick Reference: Google Hackathon Deployment

**TODAY - Aug 31, 2026**  
**Deadline**: 5:00 PM PT  
**Status**: Code ready, deploy now

## 1-Minute Setup
```bash
cd hackathons/google-agentic-opportunity-navigator
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Deploy (3-4 minutes)
```bash
gcloud run deploy opportunity-navigator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  "--set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),GOOGLE_CLOUD_LOCATION=global" \
  --timeout=3600 \
  --memory=512Mi \
  --cpu=1
```

Save the URL from output (e.g., `https://opportunity-navigator-xxxxx-uc.a.run.app`)

## Test (1 minute)
```bash
curl https://YOUR_URL/health
```

Should return `{"status": "ok", ...}`

## Record Demo (20-30 minutes)
Follow `DEMO.md` with your URL. Keep it ≤4 minutes.

## Submit (5 minutes)
1. Devpost: Link repository + description
2. Upload demo video
3. Add Cloud Run URL
4. **Submit before 5:00 PM PT**

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `gcloud: command not found` | Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) |
| Health check 401/403 | Set `GOOGLE_API_KEY` env var or enable Vertex AI |
| Build times out | Increase `--timeout=3600` or check build logs: `gcloud builds log --limit=50` |
| Can't record video | Use quicktime (Mac), OBS (Linux/Windows), or Chrome screen capture |

---

**See full guide**: `DEPLOY_TODAY.md`  
**See implementation status**: `IMPLEMENTATION_STATUS.md`  
**See covenant principles**: `/memories/repo/AION_PRIVATE_COVENANT.md`
