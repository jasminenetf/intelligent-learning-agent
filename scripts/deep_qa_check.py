"""Deep QA gate for the competition demo.

This script is intentionally local and lightweight:
- no real LLM call is required;
- it assumes the demo backend is already running on 127.0.0.1:8010;
- it checks the current high-value P0/P1 learning loop.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("DEEP_QA_BASE", "http://127.0.0.1:8010").rstrip("/")
QUESTION = "我不懂函数极限，讲清定义、常见误区，并给一个例题"
RESOURCE_TYPES = ["mindmap", "quiz", "lecture_doc", "study_plan", "ppt"]


class QaFailure(RuntimeError):
    pass


def run_cmd(args: list[str], timeout: int = 90) -> str:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=False,
    )
    if proc.returncode != 0:
        raise QaFailure(f"command failed: {' '.join(args)}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip()


def request_json(path: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise QaFailure(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise QaFailure(f"{method} {path} failed: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QaFailure(f"{method} {path} returned non-json: {raw[:200]}") from exc


def request_text(path: str, timeout: int = 30) -> str:
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise QaFailure(f"download {path} failed: {exc}") from exc


def unwrap(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("ok") is True and isinstance(data.get("data"), dict):
        return data["data"]
    return data


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise QaFailure(message)


def check_syntax() -> None:
    run_cmd([sys.executable, "-m", "py_compile", "backend/app/demo_main.py"])
    run_cmd(["node", "--check", "frontend-demo/app.js"])
    print("[PASS] syntax checks")


def check_p0_smoke() -> None:
    env = os.environ.copy()
    env["P0_SMOKE_BASE"] = BASE
    proc = subprocess.run(
        [sys.executable, "scripts/verify_p0_smoke.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=90,
        env=env,
    )
    if proc.returncode != 0 or "ALL CHECKS PASSED" not in proc.stdout:
        raise QaFailure(f"P0 smoke failed\n{proc.stdout}\n{proc.stderr}")
    print("[PASS] P0 smoke")


def check_learning_loop() -> list[dict[str, Any]]:
    ask = unwrap(
        request_json(
            "/api/app/ask",
            "POST",
            {"course_id": 1, "question": QUESTION},
            timeout=20,
        )
    )
    items = (ask.get("resource_package") or {}).get("items") or []
    types = {item.get("type") for item in items}
    missing = [typ for typ in RESOURCE_TYPES if typ not in types]
    assert_true(not missing, f"ask resource package missing types: {missing}")
    assert_true((ask.get("student_profile") or {}).get("profile_version", 0) >= 1, "profile did not update after ask")
    assert_true(len(ask.get("agent_traces") or ask.get("agent_trace") or []) >= 4, "agent trace is too weak")
    assert_true((ask.get("grounding") or {}).get("risk_level") == "low", "grounding risk should be low")

    generated: list[dict[str, Any]] = []
    for typ in RESOURCE_TYPES:
        res = unwrap(
            request_json(
                "/api/app/generate",
                "POST",
                {"course_id": 1, "resource_type": typ, "topic": "函数极限的定义"},
                timeout=20,
            )
        )
        assert_true(res.get("download_url"), f"{typ} missing download_url")
        assert_true((res.get("verifier") or {}).get("status") == "passed", f"{typ} verifier not passed")
        assert_true((res.get("context") or {}).get("chapter"), f"{typ} missing chapter context")
        if typ == "mindmap":
            assert_true(bool(res.get("tree")), "mindmap missing readable tree")
        if typ == "quiz":
            assert_true(len(res.get("items") or []) >= 3, "quiz should contain at least 3 items")
            assert_true(all(q.get("explanation") for q in res.get("items") or []), "quiz explanations missing")
        if typ == "study_plan":
            steps = ((res.get("study_plan") or {}).get("steps") or [])
            assert_true(len(steps) >= 4, "study plan should contain at least 4 steps")
            assert_true(all(step.get("check_standard") for step in steps), "study plan missing check standards")
        if typ == "ppt":
            assert_true((res.get("slide_count") or 0) >= 6, "ppt markdown deck should contain enough slides")
        generated.append(res)

    wrong = request_json(
        "/api/app/quiz/submit",
        "POST",
        {
            "course_id": 1,
            "topic": "函数极限",
            "question_text": "极限存在是否要求函数在该点有定义？",
            "selected_answer": "要求",
            "correct_answer": "不要求",
            "is_correct": False,
            "knowledge_point": "函数极限",
            "explanation": "极限研究趋近过程，不要求该点函数值存在。",
        },
        timeout=10,
    )
    assert_true((wrong.get("mastery") or {}).get("mastery_score") == 0.48, "wrong answer mastery not updated")
    assert_true((wrong.get("detailed_feedback") or {}).get("correct_logic"), "wrong answer detailed feedback missing")
    print("[PASS] ask -> resources -> quiz feedback loop")
    return generated


def check_downloads(resources: list[dict[str, Any]]) -> None:
    for res in resources:
        text = request_text(str(res["download_url"]), timeout=10)
        typ = res.get("resource_type") or res.get("type")
        assert_true("Verifier" in text, f"{typ} download missing verifier section")
        assert_true("高数上.pdf" in text or "高等数学上册" in text, f"{typ} download missing course evidence")
        if typ == "ppt":
            assert_true("教学版文字课件" in text, "ppt markdown download missing teaching deck marker")
        if typ == "mindmap":
            assert_true("可读知识结构" in text, "mindmap download missing readable structure")
    print("[PASS] resource downloads")


def check_secret_hygiene() -> None:
    allow_files = {
        "README.md",
        ".env.example",
        "backend/.env.example",
        "docs/final/模型与配置说明.md",
        "docs/final/朋友下载运行说明.md",
    }
    suspicious: list[str] = []
    patterns = [
        re.compile(r"(?i)(api[_-]?key|api[_-]?password|secret)\s*=\s*['\"]?([A-Za-z0-9_\-:]{16,})"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in allow_files:
            continue
        if any(part in {".git", ".venv", "venv", "__pycache__", "node_modules", "data", ".local"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".js", ".css", ".md", ".txt", ".bat", ".sh", ".yml", ".yaml", ".json", ".example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = match.group(match.lastindex or 0)
                if "your" in value.lower() or "mock" in value.lower() or "example" in value.lower():
                    continue
                suspicious.append(f"{rel}: {match.group(0)[:80]}")
    assert_true(not suspicious, "possible secrets found:\n" + "\n".join(suspicious[:20]))
    print("[PASS] secret hygiene")


def main() -> int:
    print(f"=== Deep QA Check ({BASE}) ===")
    try:
        health = request_json("/health", timeout=5)
        assert_true(health.get("ok") is True, "backend health not ok")
        check_syntax()
        check_p0_smoke()
        resources = check_learning_loop()
        check_downloads(resources)
        check_secret_hygiene()
    except QaFailure as exc:
        print(f"[FAIL] {exc}")
        return 1
    print("=== DEEP QA PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
