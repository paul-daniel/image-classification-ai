"""Main orchestrator for complaint processing.

This module coordinates transcription/text intake, prompt generation, image
generation, vision analysis, annotation, and final classification.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

try:
    from .dalle import generate_image_async
    from .gpt import classify_with_gpt_async, generate_image_prompt_async, load_categories
    from .utils.console import info, run_step, show_artifact, show_prompt, show_result
    from .utils.io import list_audio_files, list_text_files, slugify_filename, write_json, write_text
    from .utils.paths import AUDIO_DIR, CATEGORIES_FILE, OUTPUT_DIR, TEXTUAL_COMPLAINTS_DIR
    from .vision import analyze_and_annotate_image_async
    from .whisper import transcribe_audio_async
except ImportError:  # pragma: no cover
    from dalle import generate_image_async
    from gpt import classify_with_gpt_async, generate_image_prompt_async, load_categories
    from utils.console import info, run_step, show_artifact, show_prompt, show_result
    from utils.io import list_audio_files, list_text_files, slugify_filename, write_json, write_text
    from utils.paths import AUDIO_DIR, CATEGORIES_FILE, OUTPUT_DIR, TEXTUAL_COMPLAINTS_DIR
    from vision import analyze_and_annotate_image_async
    from whisper import transcribe_audio_async


def _create_placeholder_image(path: Path) -> None:
    """Create a deterministic placeholder image used in dry-run mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1024, 1024), color=(245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle([(220, 280), (820, 760)], outline="red", width=6)
    draw.text((240, 240), "Dry-run placeholder defect image", fill="black")
    image.save(path)


def _safe_stem(path: Path) -> str:
    """Return a filesystem-safe identifier derived from a filename stem."""
    clean = "".join(ch if ch.isalnum() else "-" for ch in path.stem.lower())
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-") or "complaint"


def _signal_id_from_text(text: str) -> str:
    """Build a stable output folder id from the first words of text input."""
    words = text.strip().split()
    snippet = " ".join(words[:14])
    slug = slugify_filename(snippet)[:80].strip("-")
    return slug or "text-complaint"


def _read_text_file(path: Path) -> str:
    """Read and validate a plain-text complaint file."""
    if not path.exists():
        raise FileNotFoundError(f"Text complaint file not found: {path}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Text complaint file is empty: {path}")

    return content


def _validate_args(args: argparse.Namespace) -> None:
    """Validate CLI combinations to keep execution mode unambiguous."""
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1.")
    if args.step_timeout < 1:
        raise ValueError("--step-timeout must be at least 1 second.")

    single_input_flags = [bool(args.audio), bool(args.text), bool(args.text_file)]
    if sum(single_input_flags) > 1:
        raise ValueError("Use only one of --audio, --text, or --text-file at a time.")

    if any(single_input_flags) and (args.audio_dir or args.text_dir):
        raise ValueError(
            "Do not combine single-input flags (--audio/--text/--text-file) "
            "with batch flags (--audio-dir/--text-dir)."
        )


async def _run_dry_pipeline(
    *,
    complaint_id: str,
    prompt_file: Path,
    image_file: Path,
    image_description_file: Path,
    defects_file: Path,
    annotated_file: Path,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Generate deterministic placeholder artifacts for dry-run mode."""
    image_prompt = (
        "A realistic product defect scene in an e-commerce context, with clear focus on the issue."
    )
    write_text(prompt_file, image_prompt + "\n")
    show_prompt(complaint_id, image_prompt)

    info(complaint_id, "Image generation skipped in dry-run")
    _create_placeholder_image(image_file)
    show_artifact(complaint_id, "Image", image_file)

    analysis: dict[str, Any] = {
        "summary": "A damaged parcel with visible denting on the product box.",
        "scene_details": [
            "Cardboard package on doorstep",
            "Visible crush marks on one side",
        ],
        "defects": [
            {
                "label": "package damage",
                "confidence": 0.88,
                "bbox": [0.22, 0.27, 0.58, 0.47],
                "evidence": "Visible dent and crease lines",
            }
        ],
    }
    write_json(defects_file, analysis)
    write_text(image_description_file, analysis["summary"] + "\n")

    _create_placeholder_image(annotated_file)
    show_artifact(complaint_id, "Annotated image", annotated_file)

    classification: dict[str, Any] = {
        "category": "Logistics",
        "subcategory": "Damaged Delivery",
        "severity": "high",
        "confidence": 0.8,
        "rationale": "Visible damage likely affects usability and customer trust.",
    }
    info(complaint_id, "Vision analysis and classification skipped in dry-run")

    return image_prompt, analysis, classification


async def _run_real_pipeline(
    *,
    complaint_id: str,
    transcript: str,
    categories: dict[str, Any],
    image_quality: str,
    step_timeout: int,
    prompt_file: Path,
    image_file: Path,
    image_description_file: Path,
    defects_file: Path,
    annotated_file: Path,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Execute model-backed prompt, image, vision, and classification stages."""
    image_prompt = await run_step(
        complaint_id=complaint_id,
        step_name="Prompt generation",
        task=generate_image_prompt_async(transcript),
        timeout_seconds=step_timeout,
    )
    write_text(prompt_file, image_prompt + "\n")
    show_prompt(complaint_id, image_prompt)

    await run_step(
        complaint_id=complaint_id,
        step_name="Image generation",
        task=generate_image_async(image_prompt, image_file, quality=image_quality),
        timeout_seconds=step_timeout,
    )
    show_artifact(complaint_id, "Image", image_file)

    analysis = await run_step(
        complaint_id=complaint_id,
        step_name="Vision analysis + annotation",
        task=analyze_and_annotate_image_async(
            image_file,
            description_path=image_description_file,
            annotation_output_path=annotated_file,
            defects_json_path=defects_file,
        ),
        timeout_seconds=step_timeout,
    )
    show_artifact(complaint_id, "Annotated image", annotated_file)

    classification = await run_step(
        complaint_id=complaint_id,
        step_name="Complaint classification",
        task=classify_with_gpt_async(
            transcript,
            str(analysis.get("summary", "")),
            categories,
        ),
        timeout_seconds=step_timeout,
    )

    return image_prompt, analysis, classification


async def process_complaint(
    *,
    complaint_id: str,
    output_root: Path,
    categories: dict[str, Any],
    audio_path: Path | None = None,
    text: str | None = None,
    language: str = "en",
    image_quality: str = "medium",
    step_timeout: int = 120,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process one complaint and persist all rubric-required artifacts."""
    output_dir = output_root / complaint_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Standard output contract for downstream review and submission checks.
    transcription_file = output_dir / "transcription.txt"
    prompt_file = output_dir / "prompt.txt"
    image_file = output_dir / "generated_image.png"
    image_description_file = output_dir / "image_description.txt"
    defects_file = output_dir / "image_analysis.json"
    annotated_file = output_dir / "annotated_image.png"
    classification_json_file = output_dir / "classification.json"
    classification_text_file = output_dir / "classification.txt"

    if audio_path:
        source_audio = Path(audio_path)
        if not source_audio.exists():
            raise FileNotFoundError(f"Audio file not found: {source_audio}")

        copied_audio_file = output_dir / source_audio.name
        if source_audio.resolve() != copied_audio_file.resolve():
            shutil.copy2(source_audio, copied_audio_file)
        show_artifact(complaint_id, "Input audio", copied_audio_file)

    if text and text.strip():
        transcript = text.strip()
        info(complaint_id, "Using provided text input")
    elif audio_path:
        transcript = await run_step(
            complaint_id=complaint_id,
            step_name="Transcription",
            task=transcribe_audio_async(audio_path, language=language),
            timeout_seconds=step_timeout,
        )
    else:
        raise ValueError("Either text or audio_path must be provided.")

    write_text(transcription_file, transcript + "\n")

    if dry_run:
        _, _, classification = await _run_dry_pipeline(
            complaint_id=complaint_id,
            prompt_file=prompt_file,
            image_file=image_file,
            image_description_file=image_description_file,
            defects_file=defects_file,
            annotated_file=annotated_file,
        )
    else:
        _, _, classification = await _run_real_pipeline(
            complaint_id=complaint_id,
            transcript=transcript,
            categories=categories,
            image_quality=image_quality,
            step_timeout=step_timeout,
            prompt_file=prompt_file,
            image_file=image_file,
            image_description_file=image_description_file,
            defects_file=defects_file,
            annotated_file=annotated_file,
        )

    write_json(classification_json_file, classification)
    write_text(
        classification_text_file,
        (
            f"Category: {classification.get('category', 'Unknown')}\n"
            f"Subcategory: {classification.get('subcategory', 'Unknown')}\n"
            f"Severity: {classification.get('severity', 'medium')}\n"
            f"Confidence: {classification.get('confidence', 0.0)}\n"
            f"Rationale: {classification.get('rationale', '')}\n"
        ),
    )
    show_result(complaint_id, classification)

    return {
        "complaint_id": complaint_id,
        "output_dir": str(output_dir),
        "category": classification.get("category", "Unknown"),
        "subcategory": classification.get("subcategory", "Unknown"),
        "severity": classification.get("severity", "medium"),
    }


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for single and batch complaint processing."""
    parser = argparse.ArgumentParser(description="Customer complaint classification pipeline")
    parser.add_argument("--audio", type=str, default=None, help="Path to one complaint audio file")
    parser.add_argument("--text", type=str, default=None, help="Raw complaint text input")
    parser.add_argument("--text-file", type=str, default=None, help="Path to one text complaint file (.txt)")
    parser.add_argument(
        "--audio-dir",
        type=str,
        default=None,
        help="Directory containing audio files for batch processing",
    )
    parser.add_argument(
        "--text-dir",
        type=str,
        default=None,
        help="Directory containing text complaint files (.txt) for batch processing",
    )
    parser.add_argument("--language", type=str, default="en", help="Speech-to-text language hint")
    parser.add_argument(
        "--image-quality",
        type=str,
        choices=["low", "medium", "high"],
        default="medium",
        help="Image generation quality (lower is cheaper)",
    )
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--concurrency", type=int, default=3, help="Batch concurrency")
    parser.add_argument(
        "--step-timeout",
        type=int,
        default=120,
        help="Per-step timeout in seconds for model calls",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without external API calls")
    return parser


async def run(args: argparse.Namespace) -> None:
    """Execute pipeline based on validated CLI arguments."""
    _validate_args(args)

    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    categories = load_categories(CATEGORIES_FILE)

    tasks: list[asyncio.Task[dict[str, Any]]] = []

    if args.text or args.audio or args.text_file:
        text_content = None
        complaint_id = ""

        if args.text_file:
            text_path = Path(args.text_file)
            text_content = _read_text_file(text_path)
            complaint_id = _safe_stem(text_path)
        elif args.text:
            text_content = args.text
            complaint_id = _signal_id_from_text(args.text)
        else:
            complaint_id = _safe_stem(Path(args.audio))

        audio_path = Path(args.audio) if args.audio else None
        tasks.append(
            asyncio.create_task(
                process_complaint(
                    complaint_id=complaint_id,
                    output_root=output_root,
                    categories=categories,
                    audio_path=audio_path,
                    text=text_content,
                    language=args.language,
                    image_quality=args.image_quality,
                    step_timeout=args.step_timeout,
                    dry_run=args.dry_run,
                )
            )
        )
    else:
        audio_dir = Path(args.audio_dir) if args.audio_dir else AUDIO_DIR
        text_dir = Path(args.text_dir) if args.text_dir else TEXTUAL_COMPLAINTS_DIR

        audio_files = list_audio_files(audio_dir)
        text_files = list_text_files(text_dir)

        if not audio_files and not text_files:
            raise ValueError(
                "No input provided. Use --audio, --text, --text-file, or place files in "
                "project/audio/ or project/textual_complaints/."
            )

        semaphore = asyncio.Semaphore(max(1, int(args.concurrency)))

        async def _bounded_process(file_path: Path) -> dict[str, Any]:
            async with semaphore:
                return await process_complaint(
                    complaint_id=_safe_stem(file_path),
                    output_root=output_root,
                    categories=categories,
                    audio_path=file_path,
                    text=None,
                    language=args.language,
                    image_quality=args.image_quality,
                    step_timeout=args.step_timeout,
                    dry_run=args.dry_run,
                )

        for audio_file in audio_files:
            tasks.append(asyncio.create_task(_bounded_process(audio_file)))

        async def _bounded_text_process(file_path: Path) -> dict[str, Any]:
            async with semaphore:
                return await process_complaint(
                    complaint_id=_safe_stem(file_path),
                    output_root=output_root,
                    categories=categories,
                    audio_path=None,
                    text=_read_text_file(file_path),
                    language=args.language,
                    image_quality=args.image_quality,
                    step_timeout=args.step_timeout,
                    dry_run=args.dry_run,
                )

        for text_file in text_files:
            tasks.append(asyncio.create_task(_bounded_text_process(text_file)))

    results = await asyncio.gather(*tasks)
    summary = {"processed": len(results), "results": results}
    write_json(output_root / "run_summary.json", summary)

    print(f"Processed {len(results)} complaint(s).")
    print(f"Summary: {output_root / 'run_summary.json'}")


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
