# AWS Live Verification — Opportunity Operator

This document defines the first live Strands + Amazon Bedrock verification gate.

## Verified configuration

Official Strands documentation currently shows Amazon Bedrock as the default model provider and supports explicit configuration with:

- model ID: `global.anthropic.claude-sonnet-4-6`
- region: configurable; this project defaults to `us-east-1`
- credentials: standard AWS credential chain

The hackathon requires Strands Agents SDK. Bedrock AgentCore is optional and can improve technical scoring, but this first verification step only proves a real Strands -> Bedrock model turn.

## Credential handling

Do not commit AWS credentials, access keys, session tokens, profiles, or exported credential output.

Use the standard AWS credential chain on the execution host, for example an authenticated AWS CLI profile, workload role, or environment supplied securely outside Git.

## Run

```bash
cd hackathons/aws-agents-for-humans
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AWS_REGION=us-east-1
# Optional override; otherwise the verified default is used.
export AION_AWS_MODEL_ID=global.anthropic.claude-sonnet-4-6

python live_verify.py
```

The harness sends only a controlled hypothetical opportunity fixture. It does not browse, submit applications, contact third parties, move funds, connect wallets, or execute financial actions.

## Pass criteria

A verification is successful only if all of the following are observed from the real execution host:

1. dependencies install successfully;
2. AWS credentials resolve without being printed or committed;
3. Bedrock model access is authorized;
4. Strands invokes the configured Bedrock model;
5. the agent returns a response for the safe fixture;
6. structured output includes `live_verification_success`;
7. relevant CloudTrail/Bedrock or runtime evidence can be captured without exposing secrets.

Do not claim live verification until the script has actually returned success against AWS.

## Common blockers

- AWS credentials are absent or expired;
- the selected account/region lacks Bedrock model access;
- IAM permissions do not allow model invocation;
- the cross-region/global model ID is unavailable under the account's policy or geography;
- network or service-control policies block Bedrock.

If the default model is unavailable, choose another Bedrock model supported by Strands and the hackathon, set `AION_AWS_MODEL_ID`, and document the final model used in the submission.

## Submission evidence to capture after success

- terminal output with secrets removed;
- configured model ID and region;
- architecture diagram showing human -> Opportunity Operator -> Strands -> Amazon Bedrock -> deterministic qualification tool -> persistent ledger -> human review;
- representative structured logs;
- public repository/README instructions;
- <=5-minute demo video.
