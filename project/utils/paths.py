from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"
AUDIO_DIR = PROJECT_DIR / "audio"
TEXTUAL_COMPLAINTS_DIR = PROJECT_DIR / "textual_complaints"
CATEGORIES_FILE = PROJECT_DIR / "categories.json"
