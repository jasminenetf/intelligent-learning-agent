#!/usr/bin/env python3
"""Import the full 高数上 PDF as a real demo course for RAG demonstrations."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, select  # noqa: E402

from app.core.database import create_db_and_tables, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.course_file import CourseFile  # noqa: E402
from app.models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from app.models.knowledge_mastery import KnowledgeMastery  # noqa: E402
from app.models.learning_analytics import AuditLog, LearningProgress, ResourceBookmark  # noqa: E402
from app.models.quiz_attempt import QuizAttempt  # noqa: E402
from app.models.student_profile import StudentProfile  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rag_service import build_course_index  # noqa: E402

DEFAULT_PDF = Path(r"C:\Users\zhang\Desktop\高数上.pdf")
PDF_PATH = Path(os.environ.get("GAOSHU_PDF_PATH", str(DEFAULT_PDF)))
COURSE_NAME = os.environ.get("GAOSHU_COURSE_NAME", "高等数学上册 - 真实教材演示课程")
TEACHER_USERNAME = os.environ.get("GAOSHU_TEACHER_USERNAME", "demo_teacher")
STUDENT_USERNAME = os.environ.get("GAOSHU_STUDENT_USERNAME", "demo_student")
DEMO_PASSWORD = os.environ.get("GAOSHU_DEMO_PASSWORD", "demo_pass_12345")
CHUNK_MAX_CHARS = int(os.environ.get("GAOSHU_CHUNK_MAX_CHARS", "900"))
CHUNK_OVERLAP_CHARS = int(os.environ.get("GAOSHU_CHUNK_OVERLAP_CHARS", "120"))
ENABLE_OCR = os.environ.get("GAOSHU_OCR", "0").lower() in {"1", "true", "yes", "on"}
OCR_LANG = os.environ.get("GAOSHU_OCR_LANG", "chi_sim")
OCR_DPI = int(os.environ.get("GAOSHU_OCR_DPI", "180"))
MAX_PAGES = int(os.environ.get("GAOSHU_MAX_PAGES", "0"))
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
LOCAL_TESSDATA = ROOT / ".local" / "tessdata"


def _require_pdf_lib():
    try:
        import fitz  # type: ignore
        return fitz
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing PDF dependency pymupdf. Install backend dependencies with: "
            "python -m pip install -r backend/requirements.txt"
        ) from exc


def _get_or_create_user(session: Session, username: str, role: str) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=role,
            is_active=True,
        )
    else:
        user.role = role
        user.is_active = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _get_or_create_course(session: Session, teacher: User) -> Course:
    course = session.exec(select(Course).where(Course.name == COURSE_NAME)).first()
    description = "真实《高等数学上册》PDF 教材导入课程，用于展示 PDF 知识库、RAG 引用、讲义/导图/练习题生成和学习报告闭环。"
    if not course:
        course = Course(name=COURSE_NAME, description=description, teacher_id=int(teacher.id or 0))
    else:
        course.description = description
        course.teacher_id = int(teacher.id or course.teacher_id)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_text(text: str, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    text = _normalize_text(text)
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(para):
                piece = para[start : start + max_chars].strip()
                if piece:
                    chunks.append(piece)
                if start + max_chars >= len(para):
                    break
                start += max(1, max_chars - overlap)
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())
    return chunks


def _require_ocr_libs():
    try:
        from PIL import Image  # noqa: F401
        import pytesseract  # type: ignore
        return pytesseract
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "OCR requires Pillow and pytesseract. Install with: python -m pip install -r backend/requirements.txt"
        ) from exc


def _configure_tesseract(pytesseract) -> None:
    if TESSERACT_CMD and Path(TESSERACT_CMD).exists():
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    if LOCAL_TESSDATA.exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(LOCAL_TESSDATA))


def _ocr_page(page, page_index: int) -> str:
    pytesseract = _require_ocr_libs()
    _configure_tesseract(pytesseract)
    zoom = OCR_DPI / 72
    matrix = page.parent.__class__.Matrix(zoom, zoom) if False else None
    # PyMuPDF exposes Matrix on fitz, not on document; import lazily to keep text-only path simple.
    import fitz  # type: ignore
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    from PIL import Image
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    try:
        return pytesseract.image_to_string(image, lang=OCR_LANG) or ""
    except Exception as exc:
        raise SystemExit(
            f"OCR failed on page {page_index}: {exc}\n"
            "If Chinese OCR data is missing, set TESSDATA_PREFIX to the folder containing chi_sim.traineddata."
        ) from exc


def _extract_pdf_chunks(pdf_path: Path) -> tuple[int, list[dict]]:
    fitz = _require_pdf_lib()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    chunks: list[dict] = []
    with fitz.open(str(pdf_path)) as doc:
        page_count = len(doc)
        limit = page_count if MAX_PAGES <= 0 else min(page_count, MAX_PAGES)
        for page_index in range(1, limit + 1):
            page = doc[page_index - 1]
            text = page.get_text("text") or ""
            if not _normalize_text(text) and ENABLE_OCR:
                text = _ocr_page(page, page_index)
            page_chunks = [c for c in _split_text(text) if len(c) >= 30]
            for local_idx, chunk in enumerate(page_chunks):
                chunks.append(
                    {
                        "content": chunk,
                        "source": pdf_path.name,
                        "page_number": page_index,
                        "local_index": local_idx,
                    }
                )
            if page_index % 10 == 0 or page_index == limit:
                print(f"processed_pages={page_index}/{limit} chunks={len(chunks)} ocr={'on' if ENABLE_OCR else 'off'}")
    return page_count, chunks


def _seed_course_file_and_chunks(session: Session, course: Course, teacher: User, pdf_path: Path, chunks: list[dict]) -> None:
    file_row = session.exec(
        select(CourseFile).where(
            CourseFile.course_id == course.id,
            CourseFile.original_filename == pdf_path.name,
        )
    ).first()
    if not file_row:
        file_row = CourseFile(
            course_id=int(course.id or 0),
            uploader_id=int(teacher.id or 0),
            original_filename=pdf_path.name,
            stored_path=str(pdf_path),
            content_type="application/pdf",
            file_ext=".pdf",
            file_size=pdf_path.stat().st_size,
            status="processed",
        )
    else:
        file_row.stored_path = str(pdf_path)
        file_row.file_size = pdf_path.stat().st_size
        file_row.status = "processed"
        file_row.error_message = None
    session.add(file_row)
    session.commit()
    session.refresh(file_row)

    old_chunks = session.exec(
        select(KnowledgeChunk).where(
            KnowledgeChunk.course_id == course.id,
            KnowledgeChunk.file_id == file_row.id,
        )
    ).all()
    for row in old_chunks:
        session.delete(row)
    session.commit()

    for idx, chunk in enumerate(chunks):
        content = chunk["content"].strip()
        session.add(
            KnowledgeChunk(
                course_id=int(course.id or 0),
                file_id=int(file_row.id or 0),
                chunk_index=idx,
                content=content,
                source=chunk.get("source") or pdf_path.name,
                page_number=chunk.get("page_number"),
                token_count=max(1, len(content) // 2),
            )
        )
        if idx and idx % 500 == 0:
            session.commit()
    session.commit()


def _seed_gaoshu_learning_data(session: Session, student: User, course: Course) -> None:
    weak_points = ["函数极限", "导数几何意义", "洛必达法则", "不定积分", "定积分应用"]
    profile = session.exec(select(StudentProfile).where(StudentProfile.user_id == student.id)).first()
    if not profile:
        profile = StudentProfile(user_id=int(student.id or 0))
    profile.major = profile.major or "数学与应用数学 / 工科基础课"
    profile.learning_goal = "复习高等数学上册，重点掌握极限、导数、微分中值定理和积分方法"
    profile.knowledge_level = "intermediate"
    profile.cognitive_style = "logical"
    profile.weak_points = json.dumps(weak_points, ensure_ascii=False)
    profile.pace_preference = "moderate"
    profile.learning_stage = "review"
    profile.resource_preference = json.dumps(["lecture_doc", "mindmap", "quiz", "ppt"], ensure_ascii=False)
    profile.motivation = "准备期末复习，希望结合教材例题理解概念和方法"
    profile.emotion_tendency = "对极限证明和积分技巧容易混淆，需要步骤化讲解"
    profile.raw_evidence = "真实高数教材导入后初始化画像：学生希望围绕极限、导数和积分进行复习。"
    profile.profile_source = "gaoshu_pdf_seed"
    profile.profile_confidence = max(float(profile.profile_confidence or 0), 0.82)
    profile.last_extracted_at = datetime.now(timezone.utc)
    profile.updated_at = datetime.now(timezone.utc)
    session.add(profile)

    progress = session.exec(
        select(LearningProgress).where(
            LearningProgress.user_id == student.id,
            LearningProgress.course_id == course.id,
        )
    ).first()
    if not progress:
        progress = LearningProgress(user_id=int(student.id or 0), course_id=int(course.id or 0))
    progress.completed_lessons = 5
    progress.total_lessons = 12
    progress.completed_rate = 5 / 12
    progress.weak_points = json.dumps(weak_points[:4], ensure_ascii=False)
    progress.next_recommendation = "优先复习函数极限和导数几何意义，再用洛必达法则与积分题进行巩固。"
    progress.updated_at = datetime.now(timezone.utc)
    session.add(progress)

    attempts = [
        ("函数极限", "若函数在某点附近有定义，极限存在是否要求函数在该点有定义？", "要求", "不要求", False, "极限只关注自变量趋近该点时函数值的趋势，不要求该点函数值存在。"),
        ("导数", "导数的几何意义是什么？", "切线斜率", "切线斜率", True, "导数表示函数图像在该点切线的斜率。"),
        ("不定积分", "不定积分结果是否只差一个常数？", "是", "是", True, "同一函数的所有原函数之间相差常数 C。"),
    ]
    existing = session.exec(
        select(QuizAttempt).where(
            QuizAttempt.user_id == student.id,
            QuizAttempt.course_id == course.id,
        )
    ).all()
    existing_keys = {(a.question_text, a.knowledge_point) for a in existing}
    for kp, question, selected, correct, ok, explanation in attempts:
        if (question, kp) in existing_keys:
            continue
        session.add(
            QuizAttempt(
                user_id=int(student.id or 0),
                course_id=int(course.id or 0),
                topic="高等数学上册复习",
                question_text=question,
                selected_answer=selected,
                correct_answer=correct,
                is_correct=ok,
                knowledge_point=kp,
                explanation=explanation,
            )
        )

    mastery_items = [
        ("函数极限", 0.42, 3, 1, 2, "复习极限定义与左右极限，并完成基础判断题。"),
        ("导数几何意义", 0.68, 2, 2, 0, "结合图像理解切线斜率和瞬时变化率。"),
        ("洛必达法则", 0.35, 2, 0, 2, "先识别 0/0 和 ∞/∞ 型，再练习适用条件。"),
        ("不定积分", 0.58, 3, 2, 1, "整理基本积分公式并练习换元法。"),
    ]
    for kp, score, attempts_count, correct_count, wrong_count, action in mastery_items:
        row = session.exec(
            select(KnowledgeMastery).where(
                KnowledgeMastery.user_id == student.id,
                KnowledgeMastery.course_id == course.id,
                KnowledgeMastery.knowledge_point == kp,
            )
        ).first()
        if not row:
            row = KnowledgeMastery(user_id=int(student.id or 0), course_id=int(course.id or 0), knowledge_point=kp)
        row.mastery_score = score
        row.attempt_count = attempts_count
        row.correct_count = correct_count
        row.wrong_count = wrong_count
        row.recommended_action = action
        row.last_practiced_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        session.add(row)

    bookmark_id = f"gaoshu-course-{course.id}-review-package"
    bookmark = session.exec(
        select(ResourceBookmark).where(
            ResourceBookmark.user_id == student.id,
            ResourceBookmark.resource_id == bookmark_id,
        )
    ).first()
    if not bookmark:
        session.add(
            ResourceBookmark(
                user_id=int(student.id or 0),
                resource_id=bookmark_id,
                title="高数上册极限与导数复习资源包",
                shared_token="demo-gaoshu-review-package",
            )
        )
    session.add(
        AuditLog(
            user_id=int(student.id or 0),
            action="gaoshu_pdf_seed",
            target_type="course",
            target_id=str(course.id),
            detail="导入整本高数上 PDF 教材并初始化高数复习画像、错题和掌握度",
        )
    )
    session.commit()


def main() -> int:
    create_db_and_tables()
    print(f"Importing PDF: {PDF_PATH}")
    page_count, chunks = _extract_pdf_chunks(PDF_PATH)
    if not chunks:
        raise SystemExit("No usable text chunks extracted from PDF")

    with Session(engine) as session:
        teacher = _get_or_create_user(session, TEACHER_USERNAME, "teacher")
        student = _get_or_create_user(session, STUDENT_USERNAME, "student")
        course = _get_or_create_course(session, teacher)
        _seed_course_file_and_chunks(session, course, teacher, PDF_PATH, chunks)
        _seed_gaoshu_learning_data(session, student, course)
        index_result = build_course_index(int(course.id or 0), session)

    print("=== Gaoshu PDF Seeded ===")
    print(f"course_name={COURSE_NAME}")
    print(f"course_id={course.id}")
    print(f"student_username={STUDENT_USERNAME}")
    print(f"student_password={DEMO_PASSWORD}")
    print(f"pages={page_count}")
    print(f"chunks={len(chunks)}")
    print("rag_index=" + json.dumps(index_result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
