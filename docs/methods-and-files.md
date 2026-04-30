# Methods and Files Guide

This guide explains what was added, where it lives, and how each method participates in the end-to-end workflow.

## Core Workflow Files

### project/main.py

Purpose:
- Async pipeline orchestrator and CLI entry point.

Key methods:
- `process_complaint(...)`
  - Orchestrates one complaint from input to final classification artifacts.
  - Inputs: text or audio, categories, language, image quality, dry-run mode.
  - Outputs: all complaint artifacts under `project/output/<complaint-id>/`.
- `build_parser()`
  - CLI options for single/batch mode and runtime controls.
- `run(args)`
  - Handles single-input or bounded-concurrency batch execution.
- `main()`
  - Parses args and runs async event loop.

Notable runtime options:
- `--image-quality {low,medium,high}` with default `medium` to reduce costs.
- `--dry-run` to validate the file pipeline without API calls.

### project/whisper.py

Purpose:
- Speech-to-text transcription.

Key methods:
- `transcribe_audio(audio_path, language="en")`
  - Calls Azure OpenAI transcription deployment.
  - Returns transcript text.
- `transcribe_audio_async(...)`
  - Async wrapper using `asyncio.to_thread`.

### project/dalle.py

Purpose:
- Complaint image generation.

Key methods:
- `generate_image(prompt, output_path, size="1024x1024", quality="medium", n=1)`
  - Calls image generation deployment.
  - Saves first generated image to disk.
- `generate_image_async(...)`
  - Async wrapper using `asyncio.to_thread`.

Cost-related change:
- Default quality changed from `high` to `medium`.

### project/vision.py

Purpose:
- Image analysis, defect localization, and annotation.

Key methods:
- `describe_image(image_path)`
  - Uses multimodal chat analysis and expects strict JSON.
  - Returns summary, scene details, and normalized defect bounding boxes.
- `annotate_image(image_path, defects, output_path)`
  - Draws bounding boxes and labels using PIL.
- `analyze_and_annotate_image(...)`
  - Convenience function to run analysis + persist JSON/description + save annotation.
- Async wrappers:
  - `describe_image_async(...)`
  - `analyze_and_annotate_image_async(...)`

### project/gpt.py

Purpose:
- Prompt engineering and complaint classification.

Key methods:
- `generate_image_prompt(transcript)`
  - Produces a concise complaint visualization prompt.
- `classify_with_gpt(transcript, image_summary, categories_catalog)`
  - Returns JSON with category, subcategory, severity, confidence, rationale.
- `load_categories(categories_path)`
  - Loads and validates categories metadata.
- Async wrappers:
  - `generate_image_prompt_async(...)`
  - `classify_with_gpt_async(...)`

### project/categories.json

Purpose:
- Classification metadata for category and subcategory routing.
- Includes severity guidance for low/medium/high/critical.

## Shared Utility Layer

### project/utils/config.py

Purpose:
- Loads `.env` values.
- Parses deployment name and API version from full Azure endpoint URLs.
- Produces strongly typed configs for speech, image, and conversation models.

Main method:
- `load_pipeline_config()`

### project/utils/clients.py

Purpose:
- Creates Azure OpenAI client instances from typed config.

Main method:
- `build_azure_openai_client(config)`

### project/utils/io.py

Purpose:
- File and JSON helpers, image save helpers, audio file discovery.

Main methods:
- `write_text`, `write_json`, `read_json`
- `save_generated_image` (supports base64 and URL responses)
- `image_file_to_data_url`
- `list_audio_files`

### project/utils/prompts.py

Purpose:
- System prompt repertoire and prompt-builder methods for each model stage.

Main methods:
- `build_image_prompt_user(...)`
- `build_vision_user(...)`
- `build_classification_user(...)`

### project/utils/parsing.py

Purpose:
- Robust extraction of structured JSON from model responses.

Main method:
- `extract_json(text)`

### project/utils/paths.py

Purpose:
- Shared constants for key project paths.

Constants:
- `PROJECT_DIR`, `OUTPUT_DIR`, `AUDIO_DIR`, `CATEGORIES_FILE`

## Added Documentation Files

- `docs/architecture.md`: high-level architecture and async design.
- `docs/rubric-checklist.md`: direct rubric-to-artifact mapping.
- `docs/methods-and-files.md`: this implementation guide.

## Artifact Contract

Per complaint folder (`project/output/<complaint-id>/`):
- `transcription.txt`
- `prompt.txt`
- `generated_image.png`
- `image_description.txt`
- `image_analysis.json`
- `annotated_image.png`
- `classification.json`
- `classification.txt`

Run-level summary:
- `project/output/run_summary.json`
