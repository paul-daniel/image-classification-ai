from __future__ import annotations

from openai import AzureOpenAI

from .config import DeploymentConfig


def build_azure_openai_client(config: DeploymentConfig) -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=config.endpoint,
        api_key=config.api_key,
        api_version=config.api_version,
    )
