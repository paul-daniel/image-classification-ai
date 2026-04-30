"""Speech-to-text helpers for complaint audio intake."""

from __future__ import annotations

import asyncio
from pathlib import Path

try:
    from .utils.clients import build_azure_openai_client
    from .utils.config import load_pipeline_config
except ImportError:  # pragma: no cover
    from utils.clients import build_azure_openai_client
    from utils.config import load_pipeline_config


def transcribe_audio(audio_path: str | Path, *, language: str = "en") -> str:
    """Transcribe one audio file and return plain text."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    config = load_pipeline_config().speech
    client = build_azure_openai_client(config)

    with path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=config.deployment,
            file=audio_file,
            language=language,
        )

    text = getattr(result, "text", None)
    if not text:
        raise ValueError("Speech-to-text response did not contain transcription text.")

    return text.strip()


async def transcribe_audio_async(audio_path: str | Path, *, language: str = "en") -> str:
    """Async wrapper around transcribe_audio."""
    return await asyncio.to_thread(transcribe_audio, audio_path, language=language)


def main() -> None:
    sample = Path(__file__).resolve().parent / "audio" / "sample.wav"
    if not sample.exists():
        print("No sample audio found in project/audio/. Add a file and run through main.py.")
        return

    print(transcribe_audio(sample))


if __name__ == "__main__":
    main()