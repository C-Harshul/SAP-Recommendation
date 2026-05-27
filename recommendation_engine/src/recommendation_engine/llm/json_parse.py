"""Parse and repair JSON from LLM responses (fenced, truncated, or malformed)."""

from __future__ import annotations

import json
import re


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fence:
        return fence.group(1).strip()
    return stripped


def _close_open_brackets(text: str) -> str:
    """Append `}`, `]`, etc. for responses cut off mid-structure."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}":
            if stack and stack[-1] == "}":
                stack.pop()
        elif ch in "]":
            if stack and stack[-1] == "]":
                stack.pop()

    trimmed = text.rstrip()
    # Drop trailing comma or incomplete key (e.g. `"sentiment": "negative",`)
    while trimmed:
        try:
            json.loads(trimmed + "".join(reversed(stack)))
            return trimmed + "".join(reversed(stack))
        except json.JSONDecodeError:
            pass
        if trimmed.endswith(","):
            trimmed = trimmed[:-1].rstrip()
            continue
        # Truncate after last complete object in an array
        last_obj = trimmed.rfind("}")
        if last_obj > 0:
            trimmed = trimmed[: last_obj + 1]
            stack = []
            in_string = False
            escape = False
            for ch in trimmed:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    stack.append("}")
                elif ch == "[":
                    stack.append("]")
                elif ch in "}":
                    if stack and stack[-1] == "}":
                        stack.pop()
                elif ch in "]":
                    if stack and stack[-1] == "]":
                        stack.pop()
            continue
        break

    return trimmed + "".join(reversed(stack))


def _salvage_ideas_objects(text: str) -> dict | None:
    """Extract complete `{...}` objects from a truncated `ideas` array."""
    match = re.search(r'"ideas"\s*:\s*\[', text)
    if not match:
        return None
    chunk = text[match.end() :]
    objects: list[dict] = []
    depth = 0
    start_idx: int | None = None
    in_string = False
    escape = False
    for i, ch in enumerate(chunk):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start_idx is not None:
                fragment = chunk[start_idx : i + 1]
                try:
                    obj = json.loads(fragment)
                    if isinstance(obj, dict) and obj.get("pain_point") and obj.get("evidence_quotes"):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start_idx = None
    if objects:
        return {"ideas": objects}
    return None


def parse_json_response(text: str) -> dict | list:
    """Parse JSON with repairs for common Gemini truncation / fence issues."""
    base = _strip_fences(text)
    candidates = [base]

    salvaged = _salvage_ideas_objects(base)
    if salvaged:
        candidates.insert(0, json.dumps(salvaged))

    candidates.append(_close_open_brackets(base))

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

    if salvaged:
        return salvaged

    raise last_error or json.JSONDecodeError("Could not parse JSON", text, 0)
