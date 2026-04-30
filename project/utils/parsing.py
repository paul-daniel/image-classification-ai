from __future__ import annotations

import json
import re
from typing import Any


_JSON_BLOCK_PATTERN = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str) -> Any:
    stripped = text.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    match = _JSON_BLOCK_PATTERN.search(stripped)
    if not match:
        raise ValueError("Model output did not contain valid JSON.")

    return json.loads(match.group(0))
