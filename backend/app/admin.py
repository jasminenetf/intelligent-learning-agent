"""SQLAdmin management panel.

Mounts at /admin when ADMIN_ENABLED=true (env var).
Provides CRUD views for users, courses, course_files, knowledge_chunks.

Security note: No auth currently. In production, either set ADMIN_ENABLED=false
or add middleware/auth (e.g. BasicAuth, OAuth2) before exposing /admin.
"""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from app.core.config import settings
from app.core.database import engine
from app.models import Course, CourseFile, KnowledgeChunk, StudentProfile, User


# ── Model Views ──────────────────────────────────────────────────────────────

class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.username,
        User.email,
        User.role,
        User.is_active,
        User.created_at,
    ]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.username, User.role, User.created_at]
    can_create = True
    can_edit = True
    can_delete = True
    can_export = False
    name = "用户"
    name_plural = "用户管理"


class CourseAdmin(ModelView, model=Course):
    column_list = [
        Course.id,
        Course.name,
        Course.description,
        Course.teacher_id,
        Course.created_at,
    ]
    column_searchable_list = [Course.name, Course.description]
    column_sortable_list = [Course.id, Course.name, Course.created_at]
    can_create = True
    can_edit = True
    can_delete = True
    name = "课程"
    name_plural = "课程管理"


class CourseFileAdmin(ModelView, model=CourseFile):
    column_list = [
        CourseFile.id,
        CourseFile.course_id,
        CourseFile.uploader_id,
        CourseFile.original_filename,
        CourseFile.file_ext,
        CourseFile.file_size,
        CourseFile.status,
        CourseFile.created_at,
    ]
    column_searchable_list = [CourseFile.original_filename]
    column_sortable_list = [
        CourseFile.id,
        CourseFile.course_id,
        CourseFile.file_size,
        CourseFile.status,
        CourseFile.created_at,
    ]
    can_create = True
    can_edit = True
    can_delete = True
    name = "课程文件"
    name_plural = "课程文件管理"


class KnowledgeChunkAdmin(ModelView, model=KnowledgeChunk):
    # content is too long — exclude from list, show summary fields only
    column_list = [
        KnowledgeChunk.id,
        KnowledgeChunk.course_id,
        KnowledgeChunk.file_id,
        KnowledgeChunk.chunk_index,
        KnowledgeChunk.source,
        KnowledgeChunk.page_number,
        KnowledgeChunk.token_count,
        KnowledgeChunk.created_at,
    ]
    column_searchable_list = [KnowledgeChunk.source]
    column_sortable_list = [
        KnowledgeChunk.id,
        KnowledgeChunk.course_id,
        KnowledgeChunk.chunk_index,
        KnowledgeChunk.created_at,
    ]
    can_create = False   # chunks are auto-generated, not manually created
    can_edit = False     # content integrity — edit via re-upload instead
    can_delete = True
    name = "知识块"
    name_plural = "知识块管理"


class StudentProfileAdmin(ModelView, model=StudentProfile):
    column_list = [
        StudentProfile.id, StudentProfile.user_id,
        StudentProfile.major, StudentProfile.knowledge_level,
        StudentProfile.cognitive_style, StudentProfile.pace_preference,
        StudentProfile.meta_learning_level, StudentProfile.updated_at,
    ]
    column_searchable_list = [StudentProfile.major]
    can_create = True; can_edit = True; can_delete = True
    name = "学生画像"; name_plural = "学生画像管理"


# ── Admin setup ───────────────────────────────────────────────────────────────

_admin: Admin | None = None


def setup_admin(app) -> Admin | None:
    """Mount SQLAdmin on the FastAPI app if ADMIN_ENABLED=true."""
    global _admin

    if not settings.ADMIN_ENABLED:
        return None

    _admin = Admin(
        app,
        engine,
        title="智能学习Agent — 管理后台",
        base_url="/admin",
    )
    _admin.add_view(UserAdmin)
    _admin.add_view(CourseAdmin)
    _admin.add_view(CourseFileAdmin)
    _admin.add_view(KnowledgeChunkAdmin)
    _admin.add_view(StudentProfileAdmin)
    return _admin
