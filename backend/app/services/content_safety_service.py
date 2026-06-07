"""Content safety checks for learning Q&A outputs."""

from __future__ import annotations

import re
from typing import Any


_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all above",
    r"system prompt",
    r"developer message",
    r"prompt injection",
    r"绕过.*限制",
    r"忽略.*规则",
]

_SENSITIVE_PATTERNS = [
    r"违法",
    r"作弊",
    r"外挂",
    r"攻击",
    r"木马",
    r"钓鱼",
]


def evaluate_content_safety(*, question: str, answer: str, citations: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Lightweight content safety and injection risk report."""
    citations = citations or []
    text = f"{question or ''}\n{answer or ''}"
    flags: list[str] = []

    if _match_any(_INJECTION_PATTERNS, text):
        flags.append("prompt_injection_risk")
    if _match_any(_SENSITIVE_PATTERNS, text):
        flags.append("sensitive_content_risk")
    if answer and len(citations) == 0 and len(answer) > 80:
        flags.append("high_confidence_without_citation")

    safe = len(flags) == 0
    return {
        "safe": safe,
        "risk_flags": flags,
        "suggestion": "内容安全" if safe else "建议降低风险输出并补充引用依据",
    }


def _match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)
