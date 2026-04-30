from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


_DEPLOYMENT_PATTERN = re.compile(r"/openai/deployments/([^/]+)")


@dataclass(frozen=True)
class DeploymentConfig:
    endpoint: str
    api_key: str
    api_version: str
    deployment: str


@dataclass(frozen=True)
class PipelineConfig:
    speech: DeploymentConfig
    image: DeploymentConfig
    conversation: DeploymentConfig


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _parse_deployment_endpoint(raw_endpoint: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not raw_endpoint:
        return None, None, None

    parsed = urlparse(raw_endpoint)
    if not parsed.scheme or not parsed.netloc:
        return raw_endpoint.rstrip("/"), None, None

    base_endpoint = f"{parsed.scheme}://{parsed.netloc}"

    deployment = None
    match = _DEPLOYMENT_PATTERN.search(parsed.path)
    if match:
        deployment = match.group(1)

    query = parse_qs(parsed.query)
    api_version = query.get("api-version", [None])[0]

    return base_endpoint, deployment, api_version


def _load_dotenv_if_present() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    dotenv_path = root_dir / ".env"

    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key and key not in os.environ:
            os.environ[key] = value


def _build_config(
    *,
    endpoint_env: str,
    key_env: str,
    deployment_env: str,
    api_version_env: str,
    version_env: str,
    fallback_api_version: str,
    fallback_deployment: str,
) -> DeploymentConfig:
    raw_endpoint = _first_non_empty(os.getenv(endpoint_env), os.getenv("AZURE_OPENAI_ENDPOINT"))
    base_endpoint, parsed_deployment, parsed_api_version = _parse_deployment_endpoint(raw_endpoint)

    api_key = _first_non_empty(os.getenv(key_env), os.getenv("AZURE_OPENAI_API_KEY"))
    if not api_key:
        raise ValueError(
            f"Missing API key for {endpoint_env}. Set {key_env} or AZURE_OPENAI_API_KEY."
        )

    endpoint = _first_non_empty(base_endpoint, os.getenv("AZURE_OPENAI_ENDPOINT"))
    if not endpoint:
        raise ValueError(
            f"Missing endpoint. Set {endpoint_env} with a full endpoint URL or AZURE_OPENAI_ENDPOINT."
        )

    deployment = _first_non_empty(
        os.getenv(deployment_env),
        parsed_deployment,
        os.getenv("DEPLOYMENT_NAME"),
        fallback_deployment,
    )

    api_version = _first_non_empty(
        os.getenv(api_version_env),
        parsed_api_version,
        os.getenv(version_env),
        os.getenv("OPENAI_API_VERSION"),
        fallback_api_version,
    )

    if not deployment:
        raise ValueError(
            f"Missing deployment name. Set {deployment_env} or use an endpoint containing /deployments/<name>."
        )

    if not api_version:
        raise ValueError(
            f"Missing API version. Set {api_version_env} or include api-version in {endpoint_env}."
        )

    return DeploymentConfig(
        endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        deployment=deployment,
    )


def load_pipeline_config() -> PipelineConfig:
    _load_dotenv_if_present()

    speech = _build_config(
        endpoint_env="SPEECH_TO_TEXT_MODEL_ENDPOINT",
        key_env="SPEECH_TO_TEXT_MODEL_KEY",
        deployment_env="SPEECH_TO_TEXT_MODEL_DEPLOYMENT",
        api_version_env="SPEECH_TO_TEXT_MODEL_API_VERSION",
        version_env="SPEECH_TO_TEXT_MODEL_VERSION",
        fallback_api_version="2025-03-01-preview",
        fallback_deployment="gpt-4o-transcribe",
    )

    image = _build_config(
        endpoint_env="IMAGE_GENERATION_MODEL_ENDPOINT",
        key_env="IMAGE_GENERATION_MODEL_KEY",
        deployment_env="IMAGE_GENERATION_MODEL_DEPLOYMENT",
        api_version_env="IMAGE_GENERATION_MODEL_API_VERSION",
        version_env="IMAGE_GENERATION_MODEL_VERSION",
        fallback_api_version="2025-04-01-preview",
        fallback_deployment="gpt-image-2",
    )

    conversation = _build_config(
        endpoint_env="CONVERSATION_MODEL_ENDPOINT",
        key_env="CONVERSATION_MODEL_KEY",
        deployment_env="CONVERSATION_MODEL_DEPLOYMENT",
        api_version_env="CONVERSATION_MODEL_API_VERSION",
        version_env="CONVERSATION_MODEL_VERSION",
        fallback_api_version="2025-03-01-preview",
        fallback_deployment="gpt-5-mini",
    )

    return PipelineConfig(speech=speech, image=image, conversation=conversation)
