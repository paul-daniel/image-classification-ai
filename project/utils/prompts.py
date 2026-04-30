from __future__ import annotations

import json
from typing import Any


PROMPT_ENGINEER_SYSTEM = (
    "You are an expert prompt engineer for customer complaint visualization. "
    "Convert complaint text into one precise image-generation prompt for a single realistic product photo. "
    "Prioritize defect visibility, physical plausibility, and inspection-style framing. "
    "Avoid brand logos, text overlays, watermarks, and artistic effects."
)


VISION_ANALYSIS_SYSTEM = (
    "You analyze complaint-related images and identify visible defects. "
    "Always respond as strict JSON with keys: summary, scene_details, defects. "
    "defects must be an array of objects with keys: label, confidence, bbox, evidence. "
    "bbox must be [x, y, width, height] normalized between 0 and 1 with tight, minimal boxes around only the defective region. "
    "Do not box entire product unless the whole product is defective. "
    "confidence is a number from 0 to 1. "
    "Return empty defects if no defect is visible."
)


CLASSIFICATION_SYSTEM = (
    "You are a complaint triage assistant. "
    "Classify complaints into exactly one category and one subcategory using the provided catalog. "
    "Also estimate severity in {low, medium, high, critical} with concise rationale. "
    "Return strict JSON only."
)


def build_image_prompt_user(transcript: str) -> str:
    return (
        "Create one precise image prompt for the complaint below.\n"
        "Requirements:\n"
        "1) Keep it realistic and physically plausible.\n"
        "2) Identify product type and the most important visible defects explicitly.\n"
        "3) Mention exact defect locations on the product (for example handle base, lid hinge, side panel).\n"
        "4) Mention packaging/context clues only if relevant to the complaint.\n"
        "5) Mention camera framing and lighting for inspection clarity (close-up, eye-level, natural indoor light).\n"
        "6) Output 70-120 words, single paragraph, prompt text only.\n"
        "7) Avoid unsafe content and avoid adding readable text in the image.\n\n"
        f"Complaint transcript:\n{transcript.strip()}"
    )


def build_vision_user(image_data_url: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": (
                "Inspect this complaint image carefully. "
                "Provide a concise scene summary, relevant visual details, and precise defect bounding boxes in normalized coordinates. "
                "Boxes must be tight around the defect itself and not include excessive background. "
                "If unsure, lower confidence instead of expanding the box."
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": image_data_url},
        },
    ]


def build_classification_user(
    transcript: str,
    image_summary: str,
    categories: dict[str, Any],
) -> str:
    categories_json = json.dumps(categories, ensure_ascii=True)
    return (
        "Classify the complaint using this categories catalog (JSON):\n"
        f"{categories_json}\n\n"
        "Inputs:\n"
        f"- Transcript: {transcript.strip()}\n"
        f"- Image analysis summary: {image_summary.strip()}\n\n"
        "Output JSON keys: category, subcategory, severity, confidence, rationale."
    )
