"""
Fallback Output Parser.

When the Strands Agent fails to call the structured output tool (e.g. returns
raw JSON text instead), this parser extracts and validates structured output
from the agent's text response.

Ported from: backend/app/utils/output_parser.py (RobustPydanticOutputParser core logic).
"""

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_from_text(text: str, model: type[T]) -> T:
    """Parse a Pydantic model from LLM text output (fallback when tool calling fails).

    Handles: markdown fences, JS-style comments, trailing text after JSON,
    string-to-list coercion for common fields.
    """
    cleaned = clean_llm_json(text)
    data = json.loads(cleaned)
    data = _coerce_schema_types(data, model)
    return model(**data)


def clean_llm_json(raw: str) -> str:
    """Clean LLM output to extract valid JSON."""
    text = raw.strip()

    # Remove markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Remove JS-style single-line comments
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)

    # Remove JS-style block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # Find the outermost JSON object or array
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        # Unbalanced — return from start to end
        return text[start:]

    return text


def _coerce_schema_types(data: dict, model: type[BaseModel]) -> dict:
    """Coerce common type mismatches (e.g. string → list) based on the Pydantic schema."""
    if not isinstance(data, dict):
        return data

    schema = model.model_json_schema()
    properties = schema.get("properties", {})

    for key, prop in properties.items():
        if key not in data:
            continue
        value = data[key]

        # String → list coercion
        prop_type = prop.get("type")
        if prop_type == "array" and isinstance(value, str):
            # Try JSON parse first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    data[key] = parsed
                    continue
            except (json.JSONDecodeError, ValueError):
                pass
            # Split by newlines or commas
            if "\n" in value:
                data[key] = [line.strip().lstrip("- ") for line in value.strip().split("\n") if line.strip()]
            elif "," in value:
                data[key] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                data[key] = [value] if value else []

    return data
