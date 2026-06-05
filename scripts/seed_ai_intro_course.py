#!/usr/bin/env python3
"""Seed AI Introduction course into the database.

Usage:
  cd /home/zhang/projects/intelligent-learning-agent
  python3 scripts/seed_ai_intro_course.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.core.database import create_db_and_tables, engine
from app.core.config import settings
from app.models.course import Course
from app.models.course_file import CourseFile
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.user import User
from app.services.chunker import split_text_to_chunks
from sqlmodel import Session, select
from datetime import datetime, timezone

COURSE_NAME = "人工智能导论"
COURSE_DESC = "人工智能导论课程，涵盖机器学习基础、过拟合与正则化、神经网络等核心主题"
MD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "course_materials", "ai_intro", "人工智能导论.md")


def main():
    # Ensure DB exists
    create_db_and_tables()

    with Session(engine) as session:
        # ── 1. Find or create demo teacher ──
        demo_user = session.exec(select(User).where(User.username == "demo")).first()
        if not demo_user:
            print("ERROR: demo user not found. Run demo-init first.")
            sys.exit(1)
        teacher_id = int(demo_user.id) if demo_user.id else 1
        print(f"[1] Demo teacher: id={teacher_id}")

        # ── 2. Read course content ──
        if not os.path.exists(MD_PATH):
            print(f"ERROR: Course markdown not found at {MD_PATH}")
            sys.exit(1)
        with open(MD_PATH, "r", encoding="utf-8") as f:
            full_text = f.read()
        print(f"[2] Read course content: {len(full_text)} chars")

        # ── 3. Find or create course ──
        course = session.exec(select(Course).where(Course.name == COURSE_NAME)).first()
        created_course = False
        if course:
            print(f"[3] Course exists: id={course.id}")
            # Delete old chunks and file entries for re-seeding
            old_files = session.exec(
                select(CourseFile).where(CourseFile.course_id == course.id)
            ).all()
            for f_entry in old_files:
                session.exec(
                    select(KnowledgeChunk).where(KnowledgeChunk.file_id == f_entry.id)
                )
                # Delete chunks manually
                old_chunks = session.exec(
                    select(KnowledgeChunk).where(KnowledgeChunk.file_id == f_entry.id)
                ).all()
                for c in old_chunks:
                    session.delete(c)
                session.delete(f_entry)
            session.commit()
            print(f"    Cleaned old chunks and files")
        else:
            course = Course(
                name=COURSE_NAME,
                description=COURSE_DESC,
                teacher_id=teacher_id,
            )
            session.add(course)
            session.commit()
            session.refresh(course)
            created_course = True
            print(f"[3] Course created: id={course.id}")
        course_id = int(course.id) if course.id else 0

        # ── 4. Create CourseFile ──
        file_entry = CourseFile(
            course_id=course_id,
            uploader_id=teacher_id,
            original_filename="人工智能导论.md",
            stored_path="docs/course_materials/ai_intro/",
            content_type="text/markdown",
            file_ext=".md",
            file_size=len(full_text.encode("utf-8")),
            status="processed",
        )
        session.add(file_entry)
        session.commit()
        session.refresh(file_entry)
        file_id = int(file_entry.id) if file_entry.id else 0
        print(f"[4] CourseFile created: id={file_id}")

        # ── 5. Generate chunks ──
        chunks = split_text_to_chunks(full_text, chunk_size=600, chunk_overlap=100)
        print(f"[5] Chunking: {len(chunks)} chunks generated")

        chunk_count = 0
        for idx, chunk_text in enumerate(chunks):
            if not chunk_text.strip():
                continue
            session.add(KnowledgeChunk(
                course_id=course_id,
                file_id=file_id,
                chunk_index=idx,
                content=chunk_text,
                source="ai_intro_course",
                page_number=None,
            ))
            chunk_count += 1
        session.commit()
        print(f"    Inserted {chunk_count} chunks into SQLite")

        # ── 6. Build ChromaDB index ──
        indexed = 0
        try:
            from app.services.rag_service import build_course_index
            result = build_course_index(course_id, session)
            indexed = result.get("indexed_chunks", 0)
            print(f"[6] ChromaDB indexed: {indexed} vectors")
        except Exception as e:
            print(f"[6] ChromaDB indexing skipped: {e}")

        # ── 7. Summary ──
        print(f"\n{'='*50}")
        print(f" AI Intro Course Seed Complete")
        print(f"{'='*50}")
        print(f"  course_id:     {course_id}")
        print(f"  course_name:   {COURSE_NAME}")
        print(f"  files:         1")
        print(f"  chunks:        {chunk_count}")
        print(f"  indexed:       {indexed}")
        print(f"  created:       {created_course}")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()
