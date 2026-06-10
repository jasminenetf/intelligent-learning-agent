# 任务清单（更新至 2026-06-10）

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
- 深度 QA 验证脚本 (`scripts/deep_qa_check.py`)
- Playwright 前端 E2E 冒烟测试
- 一键启动脚本默认启动免登录 Demo 后端
- 所有功能入口本地 Demo 模式无登录/权限限制
- API 设置页支持打开后直接填写 Spark/DeepSeek Key
- 《高数上》提问后自动生成导图、练习、讲义、学习路径、Markdown PPT
- 思维导图默认可读知识树，保留 Mermaid 备份和全屏查看
- 测验答错后原地详细讲解，并写入错题本和学习画像
- 学习画像展示 6 个维度、证据来源和置信度
- 资源下载统一输出稳定可打开的 Markdown 文本
- OSS_LICENSES.md

## 🔄 P1 进行中
- 答辩前材料准备
- Spark 主引擎配置与连接验证
- 控制文件与当前实现持续对齐
- Demo 数据与演示流程固化
- 一键启动后的真实 API Key 联调
- 答辩 PPT 正式文件制作

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
- [ ] P0 smoke + deep QA 在答辩机器上通过

## 🔧 深度检验修复长任务清单（2026-06-08）

详单见 `docs/deep-qa-fix-plan.md`。

### P0 正常使用必修
- [x] 统一启动入口和端口：Windows / Linux / WSL 都应匹配 `frontend-demo` 默认 API Base。
- [x] 修正 `README.md`、`RUNBOOK.md`、`frontend-demo/README.md` 的手动启动说明，避免 `8000/app.main` 与 `8010/app.demo_main` 混用。
- [x] 修正 `install.bat` / `install.sh` 安装后提示，明确下一步启动 `启动智能学习Agent.bat` 或 `scripts/start_app.sh`。
- [x] 一键启动脚本增加 `/health` 自检和失败提示。
- [x] 复跑语法检查、P0 smoke、资源生成交互验证。

### P1 可用性增强
- [ ] 正式后端资源生成和复习计划改为异步任务或增加明确进度提示，避免 25-40 秒等待误判为卡死。
- [x] 补齐后端 pytest，避免 `no tests ran`。
- [ ] 补齐 Playwright E2E 依赖安装/CI 说明，避免 `playwright` 命令不存在。
- [ ] 清理 LangGraph `RunnableConfig` 类型警告。
- [x] 优化学习路径入口，在侧边栏或助手预览区明确展示。
- [x] 规范 `.env.example`，去重 Spark 字段并默认关闭 Admin。
- [x] demo 下载格式按资源类型输出为 Markdown 文本，PPT 改为 Markdown 教学版。
- [ ] `.pptx` 生成作为 P2 可选增强，不进入答辩稳定主链路。
