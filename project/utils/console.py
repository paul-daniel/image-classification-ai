"""Lightweight console formatting and timed step tracking."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

_RESET = "\033[0m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_BOLD = "\033[1m"


def _supports_color() -> bool:
    return os.getenv("NO_COLOR") is None


def _color(text: str, code: str) -> str:
    if not _supports_color():
        return text
    return f"{code}{text}{_RESET}"


def info(complaint_id: str, message: str) -> None:
    print(f"[{complaint_id}] {_color('[....]', _CYAN)} {message}", flush=True)


def ok(complaint_id: str, message: str) -> None:
    print(f"[{complaint_id}] {_color('[ OK ]', _GREEN)} {message}", flush=True)


def warn(complaint_id: str, message: str) -> None:
    print(f"[{complaint_id}] {_color('[WARN]', _YELLOW)} {message}", flush=True)


def error(complaint_id: str, message: str) -> None:
    print(f"[{complaint_id}] {_color('[ERR ]', _RED)} {message}", flush=True)


async def run_step(
    *,
    complaint_id: str,
    step_name: str,
    task: Awaitable[Any],
    timeout_seconds: int,
) -> Any:
    """Run one async step with timeout and standard console events."""
    info(complaint_id, f"{step_name} started")
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(task, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        error(complaint_id, f"{step_name} timed out after {timeout_seconds}s")
        raise TimeoutError(
            f"[{complaint_id}] {step_name} timed out after {timeout_seconds}s"
        ) from exc

    elapsed = time.perf_counter() - started
    ok(complaint_id, f"{step_name} completed in {elapsed:.1f}s")
    return result


def show_prompt(complaint_id: str, prompt: str, max_chars: int = 220) -> None:
    """Print a trimmed prompt preview for traceability."""
    snippet = prompt.strip().replace("\n", " ")
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 3] + "..."
    print(
        f"[{complaint_id}] {_color(_BOLD + 'Prompt:' + _RESET, _BLUE)} {snippet}",
        flush=True,
    )


def show_artifact(complaint_id: str, label: str, path: str | Path) -> None:
    """Print a generated artifact path."""
    path_text = str(path)
    print(
        f"[{complaint_id}] {_color(label + ':', _BLUE)} {_color(path_text, _CYAN)}",
        flush=True,
    )


def show_result(complaint_id: str, classification: dict[str, Any]) -> None:
    """Print a compact, human-readable classification summary."""
    category = str(classification.get("category", "Unknown"))
    subcategory = str(classification.get("subcategory", "Unknown"))
    severity = str(classification.get("severity", "medium"))
    confidence = classification.get("confidence", 0.0)

    print(
        f"[{complaint_id}] {_color('Classification:', _BLUE)} "
        f"{_color(category, _GREEN)} / {_color(subcategory, _GREEN)} | "
        f"severity={_color(severity, _YELLOW)} | confidence={confidence}",
        flush=True,
    )
