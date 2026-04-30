"""Image-generation helpers for complaint visualization."""

from __future__ import annotations

import asyncio
from pathlib import Path

try:
    from .utils.clients import build_azure_openai_client
    from .utils.config import load_pipeline_config
    from .utils.io import save_generated_image
except ImportError:  # pragma: no cover
    from utils.clients import build_azure_openai_client
    from utils.config import load_pipeline_config
    from utils.io import save_generated_image


def generate_image(
    prompt: str,
    output_path: str | Path,
    *,
    size: str = "1024x1024",
    quality: str = "medium",
    n: int = 1,
) -> Path:
    """Generate and persist a complaint image from a prompt."""
    if not prompt.strip():
        raise ValueError("Image prompt cannot be empty.")

    config = load_pipeline_config().image
    client = build_azure_openai_client(config)

    result = client.images.generate(
        model=config.deployment,
        prompt=prompt,
        n=n,
        size=size,
        quality=quality,
    )

    path = Path(output_path)
    return save_generated_image(result, path)


async def generate_image_async(
    prompt: str,
    output_path: str | Path,
    *,
    size: str = "1024x1024",
    quality: str = "medium",
    n: int = 1,
) -> Path:
    """Async wrapper around generate_image."""
    return await asyncio.to_thread(
        generate_image,
        prompt,
        output_path,
        size=size,
        quality=quality,
        n=n,
    )


def main() -> None:
    print("Use this module via project/main.py for full pipeline execution.")


if __name__ == "__main__":
    main()