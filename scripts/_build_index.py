import sys
sys.path.insert(0, '.')
from app.core.database import create_db_and_tables, engine
from app.services.rag_service import build_course_index
from sqlmodel import Session

create_db_and_tables()
with Session(engine) as s:
    r = build_course_index(5, s)
    print(f"Indexed: {r}")
