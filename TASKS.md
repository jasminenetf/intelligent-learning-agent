# 任务清单（更新至 2026-06-08）

## ✅ 已完成
- 项目控制层 (AGENTS/PROJECT_BRIEF/TASKS/DECISIONS/RUNBOOK)
- FastAPI 后端骨架
- 课程管理 + 文件上传
- PDF/DOCX/TXT 文档解析
- OCR-W2 (OCR→RAG 检索管道)
- ChromaDB 向量库
- RAG 搜索 + Q&A
- LangGraph 5Agent 多智能体
- 多类资源生成: mindmap/lecture_doc/quiz/ppt/study_plan/reading/video_script
- OpenAI-compatible API
- Embedding 服务: hash_mock / sentence-transformers 可切换
- LLM 服务: Spark / DeepSeek / Mock fallback
- 6维学生画像
- 资源生成去Mock化
- 流式问答 (SSE)
- 静态前端 Demo 工作台 (`frontend-demo/`)
- 学习会话、错题本、掌握度、学习报告、资源中心
- P0 smoke 验证脚本 (`scripts/verify_p0_smoke.py`)
- Playwright 前端 E2E 冒烟测试
- 一键启动脚本默认启动免登录 Demo 后端
- 所有功能入口本地 Demo 模式无登录/权限限制
- API 设置页支持打开后直接填写 Spark/DeepSeek Key
- OSS_LICENSES.md

## 🔄 P1 进行中
- 答辩前材料准备
- Spark 主引擎配置与连接验证
- 控制文件与当前实现持续对齐
- Demo 数据与演示流程固化
- 一键启动后的真实 API Key 联调

## ⬜ 后续 P2/P3
- 正式注册/登录、角色权限与 Admin 认证加固
- pytest 单元/集成测试补齐
- Docker Compose 完整编排
- SQLAdmin 管理后台按需恢复/加固
- generated_file_storage 持久化到对象存储或稳定目录
- Tesseract 安装 (扫描PDF OCR)
- LobeChat / Presenton 如需展示再作为可选集成，不作为当前答辩主链路

## 🎯 答辩前必须完成
- [x] 前端 Demo 页面
- [ ] 答辩 PPT
- [x] 演示脚本/流程初稿
- [ ] Spark 连接实测
- [ ] P0 smoke 在答辩机器上通过
