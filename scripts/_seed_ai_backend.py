#!/usr/bin/env python3
"""Seed AI Intro course (run from backend dir)."""
import sys
sys.path.insert(0, '.')

from app.core.database import create_db_and_tables, engine
from app.models.course import Course
from app.models.course_file import CourseFile
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.user import User
from app.services.chunker import split_text_to_chunks
from sqlmodel import Session, select

N = '人工智能导论'
create_db_and_tables()
with Session(engine) as s:
    u = s.exec(select(User).where(User.username == 'demo')).first()
    tid = int(u.id) if u and u.id else 3
    txt = open('../docs/course_materials/ai_intro/人工智能导论.md').read()
    print(f'Content: {len(txt)} chars')

    c = s.exec(select(Course).where(Course.name == N)).first()
    if not c:
        c = Course(name=N, description='AI导论', teacher_id=tid)
        s.add(c); s.commit(); s.refresh(c)
        print(f'Created course: id={c.id}')
    else:
        print(f'Found course: id={c.id}')
    cid = int(c.id) if c.id else 0

    # Clean old
    for f in s.exec(select(CourseFile).where(CourseFile.course_id == cid)).all():
        for oc in s.exec(select(KnowledgeChunk).where(KnowledgeChunk.file_id == f.id)).all():
            s.delete(oc)
        s.delete(f)
    s.commit()

    fe = CourseFile(course_id=cid, uploader_id=tid, original_filename='人工智能导论.md',
                    stored_path='docs/course_materials/ai_intro/', content_type='text/markdown',
                    file_ext='.md', file_size=len(txt.encode()), status='processed')
    s.add(fe); s.commit(); s.refresh(fe)
    fid = int(fe.id) if fe.id else 0

    chunks = [c for c in split_text_to_chunks(txt, 600, 100) if c.strip()]
    for i, ch in enumerate(chunks):
        s.add(KnowledgeChunk(course_id=cid, file_id=fid, chunk_index=i, content=ch, source='ai_intro_course'))
    s.commit()
    print(f'Chunks: {len(chunks)}')

    try:
        from app.services.rag_service import build_course_index
        r = build_course_index(cid, s)
        print(f'Indexed: {r.get("indexed_chunks", 0)}')
    except Exception as e:
        print(f'Index skip: {e}')

    print(f'\nDONE: course_id={cid}, chunks={len(chunks)}')
