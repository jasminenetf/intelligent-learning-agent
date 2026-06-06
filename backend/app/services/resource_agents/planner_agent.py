"""Planner agent: decide resource mix and difficulty from profile + topic."""

from typing import Any


def plan(
    course_id: int,
    topic: str,
    student_profile: Any,
    resource_types: list[str],
    goal: str | None = None,
    difficulty: str = "auto",
) -> dict:
    weak_points: list[str] = []
    if getattr(student_profile, "weak_points", None):
        try:
            import json
            raw = student_profile.weak_points
            weak_points = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        except Exception:
            weak_points = []

    knowledge = getattr(student_profile, "knowledge_level", None) or "intermediate"
    if difficulty == "auto":
        if knowledge == "beginner":
            difficulty = "easy"
        elif knowledge == "advanced":
            difficulty = "hard"
        else:
            difficulty = "medium"

    return {
        "course_id": course_id,
        "topic": topic,
        "goal": goal or getattr(student_profile, "learning_goal", None) or "课程掌握",
        "difficulty": difficulty,
        "resource_types": resource_types,
        "priority_points": weak_points[:5],
        "strategy": "retrieve -> generate -> verify",
        "agents": ["planner", "retriever", "content", "mindmap", "exercise", "verifier"],
    }
