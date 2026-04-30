# Architecture Notes

## High-Level Flow

1. Input intake:
- Audio complaint (`--audio` or batch `--audio-dir`)
- Direct text complaint (`--text`)

2. Speech-to-text:
- `project/whisper.py` transcribes complaint audio.

3. Prompt engineering:
- `project/gpt.py` creates a visual prompt from transcript context.

4. Image generation:
- `project/dalle.py` generates a complaint depiction image.

5. Vision analysis:
- `project/vision.py` extracts scene summary and defect bounding boxes.

6. Annotation:
- `project/vision.py` overlays bounding boxes and labels using PIL.

7. Classification:
- `project/gpt.py` assigns category, subcategory, and severity using `project/categories.json`.

8. Output persistence:
- Artifacts per complaint are stored under `project/output/<complaint-id>/`.
- Batch summary is written to `project/output/run_summary.json`.

## Async Design

`project/main.py` uses `asyncio` to orchestrate complaint processing.

- Single complaint: sequential model stages, non-blocking wrappers for each network-bound module.
- Batch mode: bounded concurrency with an async semaphore to process multiple audio files in parallel.

## Reusable Utility Layer

`project/utils/` centralizes:

- Configuration and `.env` loading (`config.py`)
- Azure OpenAI client factory (`clients.py`)
- File and JSON helpers (`io.py`)
- Prompt templates (`prompts.py`)
- Structured JSON extraction (`parsing.py`)
- Shared path constants (`paths.py`)

This keeps model modules concise and easier to test or swap.

## Model Flexibility

The pipeline does not hardcode specific model IDs.

- If your endpoint includes `/openai/deployments/<name>/...`, deployment names and `api-version` are auto-detected.
- Optional env overrides are supported via `*_MODEL_DEPLOYMENT` and `*_MODEL_API_VERSION`.

This supports replacing baseline models with newer deployments without code changes.
