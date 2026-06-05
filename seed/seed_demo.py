#!/usr/bin/env python3
"""
Seed demo data for Intelligent Learning Agent.
Creates demo user, course, and knowledge base.
Run from project root: python seed/seed_demo.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

# Import app components
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.course import Course
from app.models.course_file import CourseFile
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.chunker import split_text_to_chunks

ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = ROOT / "seed" / "demo_knowledge.txt"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123456"
DEMO_COURSE_NAME = "高等数学上"
DEMO_COURSE_DESC = "高等数学上 Demo 示例课程（极限、导数、积分核心知识）"


def seed():
    print("创建数据库表...")
    create_db_and_tables()

    with Session(engine) as session:
        # ── 1. Demo teacher user ──────────────────────────────────────
        user = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
        if not user:
            user = User(
                username=DEMO_USERNAME,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                role="teacher",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"  创建演示用户: {DEMO_USERNAME} / {DEMO_PASSWORD} (role=teacher, id={user.id})")
        else:
            print(f"  演示用户已存在: {DEMO_USERNAME} (id={user.id})")

        uid = int(user.id) if user.id else 1

        # ── 2. Demo course ────────────────────────────────────────────
        course = session.exec(
            select(Course).where(Course.name == DEMO_COURSE_NAME)
        ).first()
        if not course:
            course = Course(
                name=DEMO_COURSE_NAME,
                description=DEMO_COURSE_DESC,
                teacher_id=uid,
            )
            session.add(course)
            session.commit()
            session.refresh(course)
            print(f"  创建演示课程: {DEMO_COURSE_NAME} (id={course.id})")
        else:
            print(f"  演示课程已存在: {DEMO_COURSE_NAME} (id={course.id})")

        cid = int(course.id) if course.id else 2

        # ── 3. Check existing chunks ──────────────────────────────────
        existing = session.exec(
            select(KnowledgeChunk).where(KnowledgeChunk.course_id == cid)
        ).all()
        if existing:
            print(f"  知识库已有 {len(existing)} 个 chunks，跳过解析")
        elif SEED_FILE.exists():
            # Create a virtual file entry
            cf = CourseFile(
                course_id=cid,
                uploader_id=uid,
                original_filename="高数上_demo_knowledge.txt",
                stored_path=str(ROOT / "data" / "raw" / "2" / "高数上_demo_knowledge.txt"),
                content_type="text/plain",
                file_ext=".txt",
                file_size=SEED_FILE.stat().st_size,
                status="parsed",
            )
            session.add(cf)
            session.commit()
            session.refresh(cf)
            fid = int(cf.id) if cf.id else 1

            # Read and chunk
            text = SEED_FILE.read_text(encoding="utf-8")
            chunks = split_text_to_chunks(text, chunk_size=800, chunk_overlap=120)
            now = datetime.now(timezone.utc)

            for i, ch_text in enumerate(chunks):
                kc = KnowledgeChunk(
                    course_id=cid,
                    file_id=fid,
                    chunk_index=i,
                    content=ch_text.strip(),
                    source="高数上_demo_knowledge.txt",
                    page_number=None,
                    token_count=len(ch_text),
                    created_at=now,
                )
                session.add(kc)

            session.commit()
            print(f"  解析知识库: {len(chunks)} chunks (来自 seed/demo_knowledge.txt)")

            # ── 4. Build ChromaDB index ────────────────────────────────
            print("  构建向量索引(ChromaDB)...")
            try:
                from app.services.rag_service import build_course_index
                result = build_course_index(cid, session)
                if "error" in result:
                    print(f"  ⚠ 向量索引构建失败: {result['error']}")
                    print(f"    启动应用后可在此页面构建: http://127.0.0.1:5173 → 知识库")
                else:
                    print(f"  向量索引构建完成: {result.get('vector_count', '?')} vectors")
            except Exception as e:
                print(f"  ⚠ 向量索引构建跳过: {e}")
                print(f"    这是正常的（首次安装需要启动后端后手动构建）")
                print(f"    启动后用 API 调用: POST /api/ocr/build-rag/course/{cid}")
        else:
            print(f"  ⚠ 种子数据文件未找到: {SEED_FILE}")

        print(f"\n✅ 演示数据初始化完成!")
        print(f"   用户: {DEMO_USERNAME} / {DEMO_PASSWORD}")
        print(f"   课程: {DEMO_COURSE_NAME} (id={cid})")


if __name__ == "__main__":
    # Set working directory to project root so config finds .env
    os.chdir(ROOT)
    seed()
