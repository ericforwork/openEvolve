"""Normalize LLM-produced YAML (e.g. OpenEvolve temp agents files) before PyYAML parse."""
from __future__ import annotations

import re


def sanitize_agents_yaml_text(text: str) -> str:
    """
    - Strip BOM / normalize newlines
    - If wrapped in ``` / ```yaml fences, keep inner body only
    - Drop leading prose / blank lines until the first top-level `key:` (column 0)
    """
    text = text.lstrip("\ufeff").replace("\r\n", "\n").strip()
    if "```" in text:
        first = re.split(r"```(?:ya?ml)?", text, maxsplit=1, flags=re.IGNORECASE)
        if len(first) > 1:
            rest = first[1].lstrip("\n")
            if "```" in rest:
                text = rest.split("```", 1)[0].strip()
            else:
                text = rest.strip()

    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            continue
        if re.match(r"^[A-Za-z0-9_-]+\s*:", line):
            start = i
            break

    return "\n".join(lines[start:]).strip()
