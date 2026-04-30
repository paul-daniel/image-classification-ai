from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Iterable

import requests


AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"}
TEXT_EXTENSIONS = {".txt"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def image_file_to_data_url(path: Path) -> str:
    mime = "image/png"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"

    image_bytes = path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def save_generated_image(result: Any, destination: Path, timeout: int = 30) -> Path:
    ensure_dir(destination.parent)

    payload = result.model_dump() if hasattr(result, "model_dump") else result
    data = payload.get("data", []) if isinstance(payload, dict) else []
    if not data:
        raise ValueError("Image generation response did not include image data.")

    first = data[0]
    image_b64 = first.get("b64_json") if isinstance(first, dict) else None
    image_url = first.get("url") if isinstance(first, dict) else None

    if image_b64:
        destination.write_bytes(base64.b64decode(image_b64))
        return destination

    if image_url:
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return destination

    raise ValueError("Unsupported image generation response format. Expected b64_json or url.")


def list_audio_files(audio_dir: Path) -> list[Path]:
    if not audio_dir.exists():
        return []

    audio_files: Iterable[Path] = (p for p in audio_dir.iterdir() if p.is_file())
    return sorted([p for p in audio_files if p.suffix.lower() in AUDIO_EXTENSIONS])


def list_text_files(text_dir: Path) -> list[Path]:
    if not text_dir.exists():
        return []

    text_files: Iterable[Path] = (p for p in text_dir.iterdir() if p.is_file())
    return sorted([p for p in text_files if p.suffix.lower() in TEXT_EXTENSIONS])


def slugify_filename(value: str) -> str:
    clean = []
    for ch in value.lower():
        if ch.isalnum():
            clean.append(ch)
        elif ch in {" ", "-", "_"}:
            clean.append("-")

    out = "".join(clean).strip("-")
    while "--" in out:
        out = out.replace("--", "-")

    return out or "complaint"
