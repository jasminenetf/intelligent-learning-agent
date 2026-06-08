"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.analytics import router as analytics_router
from app.api.app import router as app_router
from app.api.auth import router as auth_router
from app.api.avatar import router as avatar_router
from app.api.courses import router as courses_router
from app.api.health import router as health_router
from app.api.learning_sessions import router as sessions_router
from app.api.ocr import router as ocr_router
from app.api.openai_compat import router as openai_router
from app.api.profiles import router as profiles_router
from app.api.qa import router as qa_router
from app.api.rag import router as rag_router
from app.api.resources import router as resources_router
from app.api.settings import router as settings_router
from app.api.version import router as version_router
from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="智学·多智能体",
    description="面向高校与培训场景的智能学习工作台，支持课程管理、知识库问答、画像构建、学习路径与资源生成。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(version_router)
app.include_router(openai_router)
app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(rag_router)
app.include_router(qa_router)
app.include_router(profiles_router)
app.include_router(resources_router)
app.include_router(agent_router)
app.include_router(ocr_router)
app.include_router(settings_router)
app.include_router(analytics_router)
app.include_router(app_router)
app.include_router(sessions_router)
app.include_router(avatar_router)
