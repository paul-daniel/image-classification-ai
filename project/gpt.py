from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

try:
    from .utils.clients import build_azure_openai_client
    from .utils.config import load_pipeline_config
    from .utils.io import read_json
    from .utils.parsing import extract_json
    from .utils.prompts import (
        CLASSIFICATION_SYSTEM,
        PROMPT_ENGINEER_SYSTEM,
        build_classification_user,
        build_image_prompt_user,
    )
except ImportError:  # pragma: no cover
    from utils.clients import build_azure_openai_client
    from utils.config import load_pipeline_config
    from utils.io import read_json
    from utils.parsing import extract_json
    from utils.prompts import (
        CLASSIFICATION_SYSTEM,
        PROMPT_ENGINEER_SYSTEM,
        build_classification_user,
        build_image_prompt_user,
    )


def generate_image_prompt(transcript: str) -> str:
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    config = load_pipeline_config().conversation
    client = build_azure_openai_client(config)

    response = client.chat.completions.create(
        model=config.deployment,
        messages=[
            {"role": "system", "content": PROMPT_ENGINEER_SYSTEM},
            {"role": "user", "content": build_image_prompt_user(transcript)},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Prompt generation model returned empty output.")
    return content.strip()


def classify_with_gpt(
    transcript: str,
    image_summary: str,
    categories_catalog: dict[str, Any],
) -> dict[str, Any]:
    config = load_pipeline_config().conversation
    client = build_azure_openai_client(config)

    response = client.chat.completions.create(
        model=config.deployment,
        messages=[
            {"role": "system", "content": CLASSIFICATION_SYSTEM},
            {
                "role": "user",
                "content": build_classification_user(
                    transcript=transcript,
                    image_summary=image_summary,
                    categories=categories_catalog,
                ),
            },
        ],
    )

    content = response.choices[0].message.content or "{}"
    payload = extract_json(content)
    if not isinstance(payload, dict):
        raise ValueError("Classification output must be a JSON object.")

    payload.setdefault("category", "Unknown")
    payload.setdefault("subcategory", "Unknown")
    payload.setdefault("severity", "medium")
    payload.setdefault("confidence", 0.0)
    payload.setdefault("rationale", "No rationale provided.")
    return payload


def load_categories(categories_path: str | Path) -> dict[str, Any]:
    path = Path(categories_path)
    if not path.exists():
        raise FileNotFoundError(f"Categories file not found: {path}")
    catalog = read_json(path)
    if not isinstance(catalog, dict):
        raise ValueError("categories.json must contain a JSON object.")
    return catalog


async def generate_image_prompt_async(transcript: str) -> str:
    return await asyncio.to_thread(generate_image_prompt, transcript)


async def classify_with_gpt_async(
    transcript: str,
    image_summary: str,
    categories_catalog: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(
        classify_with_gpt,
        transcript,
        image_summary,
        categories_catalog,
    )


def main() -> None:
    print("Use this module via project/main.py for full pipeline execution.")


if __name__ == "__main__":
    main()