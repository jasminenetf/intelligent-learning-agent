"""Verifier agent: score and normalize generated resources."""

from typing import Any


def verify(resources: list[dict], evidence: dict, student_profile: Any) -> list[dict]:
    chunk_count = int(evidence.get("chunk_count") or 0)
    verified: list[dict] = []
    for item in resources:
        score = float(item.get("quality_score") or 0.0)
        if chunk_count > 0:
            score = max(score, 0.88)
        else:
            score = max(score, 0.75)
        if not item.get("title"):
            score -= 0.1
        if not item.get("content") and not item.get("download_url"):
            score -= 0.15
        score = max(0.0, min(1.0, score))
        item = dict(item)
        item["quality_score"] = round(score, 2)
        item.setdefault("generated_by", ["planner", "retriever", "generator", "verifier"])
        verified.append(item)
    return verified
