"""Build coherent learning resource packages from answer/trace outputs."""

from __future__ import annotations

from typing import Any


def build_resource_package(
    *,
    topic: str,
    resource_suggestions: list[dict[str, Any]] | None,
    agent_traces: list[dict[str, Any]] | None,
    grounding: dict[str, Any] | None,
    safety: dict[str, Any] | None,
    mastery: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize a response into a learning resource package."""
    suggestions = resource_suggestions or []
    traces = agent_traces or []
    grounding = grounding or {}
    safety = safety or {}
    mastery = mastery or {}

    package_items: list[dict[str, Any]] = []
    for s in suggestions:
        package_items.append({
            "type": s.get("type"),
            "title": s.get("title"),
            "reason": s.get("reason"),
        })

    package = {
        "topic": topic,
        "title": topic or "个性化学习资源包",
        "items": package_items,
        "item_count": len(package_items),
        "agent_count": len(traces),
        "grounding_score": grounding.get("grounding_score", 0.0),
        "risk_level": grounding.get("risk_level", "low"),
        "content_safe": bool(safety.get("safe", True)),
        "mastery_snapshot": mastery,
        "summary": grounding.get("message") or "系统已生成个性化学习资源包",
    }
    return package
