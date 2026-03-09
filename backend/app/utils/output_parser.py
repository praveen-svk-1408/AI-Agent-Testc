"""
Robust JSON output parser for local LLMs (Llama, etc.).

Handles common issues with local model output:
- Markdown code fences (```json ... ```)
- JavaScript-style comments (// ...)
- Trailing text after JSON
- Leading/trailing whitespace
"""

import re
import json
import logging
from typing import Type, TypeVar

from langchain_core.output_parsers import BaseOutputParser
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def clean_llm_json(text: str) -> str:
    """Extract and clean JSON from LLM output that may contain markdown fences, comments, etc."""
    # Strip leading/trailing whitespace
    text = text.strip()

    # Extract content from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Remove single-line comments (// ...) — but not inside strings
    # Simple approach: remove lines that are only comments, and trailing comments
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Remove trailing // comments (not inside strings)
        # Find // that's not inside a quoted string
        in_string = False
        escape = False
        comment_pos = None
        for i, ch in enumerate(line):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
            elif ch == "/" and not in_string and i + 1 < len(line) and line[i + 1] == "/":
                comment_pos = i
                break
        if comment_pos is not None:
            line = line[:comment_pos].rstrip()
        if line.strip():  # Keep non-empty lines
            cleaned_lines.append(line)
        elif cleaned_lines:  # Keep blank lines in middle
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


class RobustPydanticOutputParser(BaseOutputParser[T]):
    """Output parser that handles messy LLM JSON output and parses into a Pydantic model."""

    pydantic_model: Type[T]

    class Config:
        arbitrary_types_allowed = True

    def get_format_instructions(self) -> str:
        schema = self.pydantic_model.model_json_schema()
        # Simplify: just show the expected fields
        fields_desc = []
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for name, prop in props.items():
            type_str = prop.get("type", "any")
            if "items" in prop:
                item_type = prop["items"].get("type", "object")
                type_str = f"array of {item_type}s"
            req = " (required)" if name in required else " (optional)"
            desc = prop.get("description", "")
            fields_desc.append(f'  "{name}": {type_str}{req} - {desc}' if desc else f'  "{name}": {type_str}{req}')

        return (
            "You must respond with ONLY valid JSON, no additional text, no markdown code fences, no comments.\n"
            "The JSON object must have these fields:\n"
            "{\n" + ",\n".join(fields_desc) + "\n}"
        )

    def parse(self, text: str) -> T:
        # If it's an AIMessage, get the content
        if hasattr(text, "content"):
            text = text.content

        cleaned = clean_llm_json(str(text))

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse failed, attempting to extract JSON object: %s", str(e))
            # Try to find a JSON object in the text
            obj_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", cleaned, re.DOTALL)
            if obj_match:
                try:
                    data = json.loads(obj_match.group())
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Could not parse JSON from LLM output. Cleaned text:\n{cleaned[:500]}"
                    )
            else:
                raise ValueError(
                    f"No JSON object found in LLM output. Cleaned text:\n{cleaned[:500]}"
                )

        return self.pydantic_model.model_validate(data)
