# Rubric Checklist

## 1) Transcription and Prompt Generation

- [x] `transcription.txt` generated for each complaint.
- [x] Prompt generated from transcript context and saved to `prompt.txt`.

## 2) Image Generation and Description

- [x] Generated complaint image saved as `generated_image.png`.
- [x] Image description saved as `image_description.txt`.
- [x] Defect localization details saved as `image_analysis.json`.
- [x] Annotated image with bounding boxes saved as `annotated_image.png`.

## 3) Complaint Classification

- [x] Category + subcategory classification implemented using `categories.json`.
- [x] Severity assignment included (`low|medium|high|critical`).
- [x] Classification persisted as `classification.txt` and `classification.json`.

## 4) Solution Integration and Workflow

- [x] Unified orchestrator in `project/main.py`.
- [x] Supports text input, single audio, and batch audio directory.
- [x] Writes full pipeline outputs per complaint.
- [x] Writes run summary `project/output/run_summary.json`.

## Optional Enhancements

- [x] Async orchestration for scalable batch processing.
- [x] Reusable utility modules for cleaner architecture.
- [x] Dry-run mode for integration testing without external API calls.
