"""Vision analysis and image annotation utilities."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from .utils.clients import build_azure_openai_client
    from .utils.config import load_pipeline_config
    from .utils.io import image_file_to_data_url, write_json
    from .utils.parsing import extract_json
    from .utils.prompts import VISION_ANALYSIS_SYSTEM, build_vision_user
except ImportError:  # pragma: no cover
    from utils.clients import build_azure_openai_client
    from utils.config import load_pipeline_config
    from utils.io import image_file_to_data_url, write_json
    from utils.parsing import extract_json
    from utils.prompts import VISION_ANALYSIS_SYSTEM, build_vision_user


def describe_image(image_path: str | Path) -> dict[str, Any]:
    """Analyze an image and return structured defect metadata."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    config = load_pipeline_config().conversation
    client = build_azure_openai_client(config)
    image_data_url = image_file_to_data_url(path)

    response = client.chat.completions.create(
        model=config.deployment,
        messages=[
            {"role": "system", "content": VISION_ANALYSIS_SYSTEM},
            {"role": "user", "content": build_vision_user(image_data_url)},
        ],
    )

    content = response.choices[0].message.content or "{}"
    payload = extract_json(content)

    if not isinstance(payload, dict):
        raise ValueError("Vision response JSON must be an object.")

    payload.setdefault("summary", "")
    payload.setdefault("scene_details", [])
    payload.setdefault("defects", [])
    return payload


def annotate_image(
    image_path: str | Path,
    defects: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """Draw defect bounding boxes and labels on an image."""
    src = Path(image_path)
    dst = Path(output_path)

    with Image.open(src).convert("RGB") as image:
        width, height = image.size
        drawer = ImageDraw.Draw(image)
        line_width = max(3, width // 300)
        font_size = max(16, width // 42)

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        palette = [
            (255, 64, 64),
            (0, 196, 255),
            (255, 196, 0),
            (64, 224, 128),
            (224, 128, 255),
        ]

        for idx, defect in enumerate(defects):
            bbox = defect.get("bbox", [])
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue

            # Convert normalized bbox coordinates into pixel coordinates.
            x, y, w, h = bbox
            left = max(0, min(width - 1, int(float(x) * width)))
            top = max(0, min(height - 1, int(float(y) * height)))
            right = max(left + 1, min(width, int(float(x + w) * width)))
            bottom = max(top + 1, min(height, int(float(y + h) * height)))

            color = palette[idx % len(palette)]
            drawer.rectangle([(left, top), (right, bottom)], outline=color, width=line_width)

            label = defect.get("label", "defect")
            confidence = defect.get("confidence", "")
            if isinstance(confidence, (int, float)):
                conf_text = f"{confidence:.2f}"
            else:
                conf_text = str(confidence).strip()

            caption = f"{idx + 1}. {label} ({conf_text})" if conf_text else f"{idx + 1}. {label}"
            text_left = left + 2
            text_top = max(0, top - font_size - 12)

            text_bbox = drawer.textbbox((text_left, text_top), caption, font=font)
            bg_left = max(0, text_bbox[0] - 6)
            bg_top = max(0, text_bbox[1] - 4)
            bg_right = min(width, text_bbox[2] + 6)
            bg_bottom = min(height, text_bbox[3] + 4)

            drawer.rectangle([(bg_left, bg_top), (bg_right, bg_bottom)], fill=color)
            drawer.text((text_left, text_top), caption, fill="black", font=font)

        dst.parent.mkdir(parents=True, exist_ok=True)
        image.save(dst)

    return dst


def analyze_and_annotate_image(
    image_path: str | Path,
    *,
    description_path: str | Path,
    annotation_output_path: str | Path,
    defects_json_path: str | Path,
) -> dict[str, Any]:
    """Run vision analysis and persist JSON, summary text, and annotation image."""
    analysis = describe_image(image_path)
    defects = analysis.get("defects", [])

    write_json(Path(defects_json_path), analysis)
    annotate_image(image_path, defects if isinstance(defects, list) else [], annotation_output_path)

    summary_text = analysis.get("summary", "")
    Path(description_path).parent.mkdir(parents=True, exist_ok=True)
    Path(description_path).write_text(summary_text, encoding="utf-8")

    return analysis


async def describe_image_async(image_path: str | Path) -> dict[str, Any]:
    """Async wrapper around describe_image."""
    return await asyncio.to_thread(describe_image, image_path)


async def analyze_and_annotate_image_async(
    image_path: str | Path,
    *,
    description_path: str | Path,
    annotation_output_path: str | Path,
    defects_json_path: str | Path,
) -> dict[str, Any]:
    """Async wrapper around analyze_and_annotate_image."""
    return await asyncio.to_thread(
        analyze_and_annotate_image,
        image_path,
        description_path=description_path,
        annotation_output_path=annotation_output_path,
        defects_json_path=defects_json_path,
    )


def main() -> None:
    print("Use this module via project/main.py for full pipeline execution.")


if __name__ == "__main__":
    main()