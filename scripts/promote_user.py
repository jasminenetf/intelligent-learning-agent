#!/usr/bin/env python3
"""Promote an existing user to teacher or admin (local demo bootstrap)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.user import VALID_ROLES, User


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote user role for demo setup")
    parser.add_argument("username", help="Existing username")
    parser.add_argument("role", choices=sorted(VALID_ROLES - {"student"}), help="teacher or admin")
    args = parser.parse_args()

    create_db_and_tables()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == args.username)).first()
        if not user:
            print(f"ERROR: user not found: {args.username}")
            return 1
        old = user.role
        user.role = args.role
        session.add(user)
        session.commit()
        print(f"OK: {args.username} {old} -> {args.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
