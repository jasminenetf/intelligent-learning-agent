"""Grounding / citation coverage checks for RAG outputs."""

from __future__ import annotations

import re
from typing import Any


_UNSUPPORTED_PATTERNS = [
    r"我猜",
    r"大概",
    r"可能是因为",
    r"没有依据",
    r"无法确定",
    r"也许",
]


def evaluate_grounding(*, answer: str, citations: list[dict[str, Any]] | None, retrieved_chunks: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Return a lightweight grounding report for a generated answer."""
    citations = citations or []
    retrieved_chunks = retrieved_chunks or []
    answer_text = answer or ""

    citation_count = len(citations)
    chunk_count = len(retrieved_chunks)
    unsupported_claims = _find_unsupported_claims(answer_text)

    grounding_score = _calc_grounding_score(answer_text, citation_count, chunk_count, len(unsupported_claims))
    risk_level = _risk_level(grounding_score, unsupported_claims)
    return {
        "grounding_score": grounding_score,
        "citation_count": citation_count,
        "retrieved_chunk_count": chunk_count,
        "unsupported_claims": unsupported_claims,
        "risk_level": risk_level,
        "message": "回答主要基于课程资料生成" if risk_level == "low" else "回答存在一定无依据表述，请谨慎使用",
    }


def _find_unsupported_claims(answer: str) -> list[str]:
    if not answer:
        return []
    found: list[str] = []
    for pattern in _UNSUPPORTED_PATTERNS:
        for m in re.finditer(pattern, answer):
            snippet = answer[max(0, m.start() - 10): min(len(answer), m.end() + 10)]
            if snippet not in found:
                found.append(snippet)
    return found[:5]


def _calc_grounding_score(answer: str, citation_count: int, chunk_count: int, unsupported_count: int) -> float:
    score = 0.35
    if citation_count:
        score += min(0.35, citation_count * 0.08)
    if chunk_count:
        score += min(0.2, chunk_count * 0.02)
    if len(answer) > 120:
        score += 0.08
    if unsupported_count:
        score -= min(0.35, unsupported_count * 0.08)
    return max(0.0, min(1.0, round(score, 2)))


def _risk_level(score: float, unsupported_claims: list[str]) -> str:
    if unsupported_claims and score < 0.7:
        return "medium"
    if score < 0.5:
        return "high"
    if score < 0.75:
        return "medium"
    return "low"
