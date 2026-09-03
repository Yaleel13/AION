from __future__ import annotations

import os

from strands.models import BedrockModel


DEFAULT_MODEL_ID = "global.anthropic.claude-sonnet-4-6"
DEFAULT_REGION = "us-east-1"


def build_bedrock_model() -> BedrockModel:
    """Return the explicit Bedrock model configuration for live verification.

    Credentials are intentionally resolved through the standard AWS credential
    chain and are never stored in this repository.
    """
    return BedrockModel(
        model_id=os.getenv("AION_AWS_MODEL_ID", DEFAULT_MODEL_ID),
        region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION)),
        temperature=0.2,
        max_tokens=1200,
    )
