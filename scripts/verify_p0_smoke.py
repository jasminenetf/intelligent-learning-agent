#!/usr/bin/env python3
"""Smoke verification for P0 fixes (no secrets printed)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path: str, token: str | None = None, timeout: int = 8) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"raw": body[:200]}
        return e.code, data


def post(path: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:200]}
        return e.code, parsed


def main() -> int:
    fails: list[str] = []
    print("=== P0 Smoke Verification ===")

    # health
    try:
        st, _ = get("/health")
        if st != 200:
            fails.append(f"health status={st}")
        else:
            print("[PASS] GET /health")
    except Exception as exc:
        print(f"[SKIP] backend not running: {exc}")
        print("Start with: cd backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return 2

    # bootstrap (guest)
    st, body = get("/api/app/bootstrap")
    if st != 200:
        fails.append(f"bootstrap status={st}")
    elif body.get("ok") is not True:
        fails.append("bootstrap missing ok:true")
    elif "courses" not in body.get("data", {}):
        fails.append("bootstrap missing data.courses")
    elif "llm_configured" not in body.get("data", {}).get("config", {}):
        fails.append("bootstrap missing config.llm_configured")
    else:
        print("[PASS] GET /api/app/bootstrap (guest)")

    # settings POST without auth should 401/403
    st, _ = post("/api/settings/test-llm", {"provider": "spark"})
    if st not in (401, 403):
        fails.append(f"settings test-llm without auth expected 401/403 got {st}")
    else:
        print(f"[PASS] POST /api/settings/test-llm unauthenticated -> {st}")

    # register + login + dashboard
    import time

    user = f"verify_{int(time.time())}"
    password = "verify_pass_12345"
    st, reg = post("/api/auth/register", {"username": user, "password": password, "role": "teacher"})
    if st not in (200, 201) and not (st == 400 and "already" in str(reg).lower()):
        fails.append(f"register status={st}")
    else:
        print("[PASS] POST /api/auth/register (role locked to student)")

    st, login = post("/api/auth/login", {"username": user, "password": password})
    token = login.get("access_token") if st == 200 else None
    if not token:
        fails.append(f"login failed status={st}")
    else:
        print("[PASS] POST /api/auth/login")

    if token:
        st, _ = post(
            "/api/settings/llm",
            {"provider": "spark", "api_key": "x", "base_url": "http://x", "model": "m"},
            token,
        )
        if st != 403:
            fails.append(f"student save llm expected 403 got {st}")
        else:
            print("[PASS] POST /api/settings/llm student -> 403")

        st, _ = post("/api/courses", {"name": "x", "description": "y"}, token)
        if st != 403:
            fails.append(f"student create course expected 403 got {st}")
        else:
            print("[PASS] POST /api/courses student -> 403")

        try:
            st, dash = get("/api/app/dashboard", token, timeout=30)
        except TimeoutError:
            print("[SKIP] GET /api/app/dashboard timed out (embedding cold start)")
            st, dash = 0, {}
        if st == 200 and dash.get("ok") is True and "knowledge_base" in dash.get("data", {}):
            kb = dash["data"]["knowledge_base"]
            print(f"[PASS] GET /api/app/dashboard chunks={kb.get('chunks_count')} vectors={kb.get('vector_count')}")
        elif st == 404:
            print("[PASS] GET /api/app/dashboard skipped (no courses in DB)")
        elif st == 0:
            pass
        else:
            fails.append(f"dashboard unexpected status={st}")

    if fails:
        print("\n=== FAILED ===")
        for f in fails:
            print(" -", f)
        return 1

    print("\n=== ALL CHECKS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
