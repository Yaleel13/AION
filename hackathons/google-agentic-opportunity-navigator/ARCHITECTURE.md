# Opportunity Navigator Architecture

```mermaid
flowchart LR
    U[User / Judge] --> CR[Google Cloud Run\nFastAPI service]
    CR --> ADK[Google Agent Development Kit\nOpportunity Navigator agent]
    ADK --> GM[Gemini via Vertex AI]
    ADK --> ST[Deterministic scoring tool\nscore_opportunity]
    ST --> ADK
    GM --> ADK
    ADK --> CR
    CR --> U

    E[Opportunity evidence\nHackathons · grants · bounties · contracts] -. reviewed as input .-> ADK
    G[Safety guardrails\nNo wallet connection\nNo funds or token purchases\nNo autonomous outreach] -. constrain .-> ADK
```

## Request flow

1. A user sends an opportunity-comparison request to the Cloud Run-hosted FastAPI application.
2. Google ADK routes the request to the `opportunity_navigator` agent.
3. Gemini reasons over the supplied evidence and decides when deterministic scoring is appropriate.
4. The `score_opportunity` tool evaluates expected value, effort, credibility, fit, urgency, and eligibility.
5. The agent returns a concise ranking plus any evidence still required before the user should pursue an opportunity.

## Security and safety boundaries

- The hackathon project is isolated from AION's production owner runtime and private memory.
- No owner credentials, private prompts, or AION production secrets are required by the demo agent.
- No wallet connection, token purchase, live trading, gambling, payment, or sending funds is supported.
- The agent does not contact third parties or submit applications automatically.
- Social and community posts are treated as discovery leads until independently verified by an official source.
