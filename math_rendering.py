"""Normalize model math for Streamlit/KaTeX, while preserving literal code."""
from __future__ import annotations

import re

# Protect fenced code (including an unfinished fence) and inline code first.
_CODE = re.compile(r"(?m)^ {0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n"
                   r"[\s\S]*?(?:^ {0,3}(?P=fence)[ \t]*(?:\n|$)|\Z)"
                   r"|(?<!`)(?P<inline>`+)(?!`)[^\n]+?(?P=inline)(?!`)")
_MATHY = re.compile(r"\\(?:frac|sqrt|sum|prod|int|log|ln|left|right|theta|Theta|Omega|omega|"
                    r"alpha|beta|gamma|delta|epsilon|infty|leq|geq|neq|in|notin|subseteq|"
                    r"mathbb|mathcal|mathrm|text|cdot|times|begin|end)(?![a-zA-Z])|\^|"
                    r"\bf_?\d*\s*\([^()\n]*\)\s*=")


def _delimiters(text: str) -> str:
    text = re.sub(r"\\\[(.*?)\\\]", lambda m: "\n\n$$\n" + m[1].strip() + "\n$$\n\n", text, flags=re.S)
    return re.sub(r"\\\((.*?)\\\)", lambda m: "$" + m[1] + "$", text, flags=re.S)


def fix_math(text: str) -> str:
    parts, end = [], 0
    for match in _CODE.finditer(text):
        parts.append(_delimiters(text[end:match.start()]))
        token = match[0]
        if match.group("inline") == "`":
            inner = token[1:-1]
            if inner.startswith(r"\(") and inner.endswith(r"\)"):
                token = "$" + inner[2:-2] + "$"
            elif _MATHY.search(inner) and not any(c in inner for c in ('"', "'", ';', '$')):
                token = "$" + inner + "$"
        parts.append(token)
        end = match.end()
    parts.append(_delimiters(text[end:]))
    return "".join(parts)
