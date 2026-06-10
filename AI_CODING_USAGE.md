# AI Coding 使用说明

## 使用范围

本项目使用 AI Coding 辅助完成需求拆解、代码修复、测试脚本、文档和答辩材料整理。最终代码、演示路径和提交材料由人工验收负责。

## 参与内容

- 前端：学习助手工作台、自动资源展示、可读思维导图、错题原地解析、学习画像、学习报告、设置页状态展示。
- 后端：FastAPI Demo 聚合接口、Spark/DeepSeek/Mock fallback、五类资源生成、基础可信度字段、资源下载、错题闭环。
- 测试：`verify_p0_smoke.py`、`deep_qa_check.py`、Playwright E2E。
- 文档：README、RUNBOOK、答辩 PPT、7 分钟演示脚本、提交清单。

## 人工审核点

- 不把 Mock/fallback/hash_mock 包装成真实模型或真实 RAG 效果。
- 不把基础 Verifier 包装成外部事实核查。
- 不伪造 page_number、chunk_id 或 citation。
- 不提交真实密钥、`.env`、日志、数据库、Chroma 或大文件。
- 每轮修改后运行最小验证。

## 额度节省原则

- 默认使用 Mock/fallback 和本地测试。
- 真实 Spark 只用于必要的单次连接验证。
- 自动化测试不调用真实 Spark，不读取真实 `.env` 密钥。

## 当前质量门禁

- Python 语法检查
- 前端 JS 语法检查
- pytest 后端测试
- P0 smoke
- deep QA
- Playwright E2E
- 敏感信息扫描

## 声明

AI Coding 是辅助开发工具，不替代人工设计、代码审查、密钥安全和最终提交验收。
