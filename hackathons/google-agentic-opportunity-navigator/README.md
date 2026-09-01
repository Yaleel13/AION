# Opportunity Navigator — Google All Things Agentic Hackathon

A new, isolated hackathon project inspired by AION's opportunity-discovery concept. It does **not** reuse AION's production runtime. The project uses Google Agent Development Kit (ADK), Gemini 3.7 Flash, FastAPI, and is packaged for Cloud Run.

## Submission assets

- [Architecture](./ARCHITECTURE.md)
- [Submission copy and evidence checklist](./SUBMISSION.md)
- [Demo runbook](./DEMO.md)

## What it does

Opportunity Navigator helps a technical builder compare legitimate opportunities such as:

- hackathons and grants
- funded bounties and paid open-source issues
- freelance and contract work
- partnerships and referral programs
- legitimate Web3/crypto developer work

It ranks opportunities by expected value, effort, urgency, eligibility, credibility, and fit.

## Safety boundaries

The agent does not:

- speculate on token prices
- gamble
- connect wallets
- send funds
- buy tokens
- pay upfront qualification fees
- contact third parties automatically
- submit applications automatically

Social posts and Reddit are discovery leads only until independently verified.

## Local run

```bash
cd hackathons/google-agentic-opportunity-navigator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY="your-key"
uvicorn main:app --host 0.0.0.0 --port 8080
```

Health check:

```bash
curl http://localhost:8080/health
```

ADK exposes its standard agent API endpoints from the same FastAPI application.

## Cloud Run

Deployment details:

- **Project**: agent-aion
- **Region**: us-central1
- **Service**: opportunity-navigator
- **Status**: DEPLOYED
- **Public URL**: https://opportunity-navigator-554734366722.us-central1.run.app
- **Build**: https://console.cloud.google.com/cloud-build/builds;region=us-central1/880a7cc5-5438-4aa4-b7a0-6df2d2aa7a59?project=554734366722
- **Access note**: The Cloud Run service is live, but the current Google organization policy blocks public unauthenticated invocation. The service can be reached by authenticated GCP clients, and the deployment is now attached to the correct hackathon service.

To deploy from this directory (if needed for future redeployment):

```bash
gcloud run deploy opportunity-navigator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  "--set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=agent-aion,GOOGLE_CLOUD_LOCATION=global"
```

For production, prefer Vertex AI credentials/service identity rather than baking API keys into the image.

## Hackathon disclosure

This project was created specifically for the 2026 Google All Things Agentic Hackathon. It is inspired by concepts developed in the pre-existing AION repository, particularly safe opportunity discovery and human-controlled monetization workflows. It does not claim the pre-existing AION runtime as newly created hackathon work.

## Submission evidence still required

Before submission:

1. Deploy this project to Google Cloud Run.
2. Verify a real Gemini 3.7 Flash turn through ADK on the deployed service.
3. Capture Cloud Run and request logs showing the Google-hosted backend.
4. Include the architecture diagram in the submission.
5. Record a <=4 minute demo using the provided runbook.
6. Add the final hosted URL and reproducible deployment notes here.
