# AI Coding 使用说明

## 1. 使用目的

本项目允许使用 AI Coding 工具辅助完成需求分析、代码实现、重构优化、测试脚本编写和交付文档整理。AI Coding 的目标不是替代人工设计，而是提升开发效率，并通过人工审核、lint 和 smoke 回归保证质量。

## 2. 使用范围

AI Coding 主要参与以下环节：

- 需求拆解：根据项目要求文档梳理 P0/P1/P2 长任务。
- 前端开发：完善《高数上》学习工作台、可读思维导图、练习题反馈、学习画像、学习路径和资源下载。
- 后端开发：补齐 Demo 聚合 API、自动五类资源包、多智能体 trace、grounding、防幻觉字段和 Mock fallback。
- 测试增强：扩展 `scripts/verify_p0_smoke.py`，新增 `scripts/deep_qa_check.py`，覆盖自动资源包、下载、错题反馈和敏感信息扫描。
- 文档编写：生成系统设计文档、技术实现文档、演示脚本、答辩 PPT 大纲和比赛评分点映射。

## 3. 人工审核机制

所有 AI 生成或修改的内容均经过人工检查，重点包括：

- 是否符合项目要求。
- 是否与已有代码结构一致。
- 是否存在安全风险或密钥泄露。
- 是否破坏已有接口兼容性。
- 是否能通过语法检查、smoke、deep QA 和敏感信息扫描。
- 是否遵守额度节省原则：默认 Mock/fallback 调试，真实 Spark 只做必要连通性验证。

## 4. 质量控制

项目通过以下方式控制质量：

### 4.1 静态检查

对关键文件执行静态检查，例如：

- `frontend-demo/app.js`
- `backend/app/demo_main.py`
- `scripts/verify_p0_smoke.py`
- `scripts/deep_qa_check.py`

当前检查结果为无 linter 错误。

### 4.2 P0 Smoke 回归

启动后端后运行：

```bash
python scripts/verify_p0_smoke.py
```

或指定临时端口：

```bash
P0_SMOKE_BASE=http://127.0.0.1:8010 python scripts/verify_p0_smoke.py
```

已验证通过：

```text
=== ALL CHECKS PASSED ===
```

### 4.3 Deep QA 回归

答辩前运行：

```bash
python scripts/deep_qa_check.py
```

该脚本默认不调用真实 Spark，覆盖：

- 后端与前端语法检查
- P0 smoke
- 固定《高数上》问题的问答和五类自动资源
- 思维导图可读树、练习题、讲义、学习路径、Markdown PPT
- 资源下载中的教材依据、Verifier 和生成来源
- 测验选错后的原地详细解析
- 常见敏感信息扫描

### 4.4 GitHub Actions

仓库包含 `.github/workflows/static-qa.yml`，每次 push / pull request 自动执行：

- Python 语法检查
- 前端 JS 语法检查
- 敏感信息扫描

CI 不启动真实模型，也不读取本地 `.env`，用于控制 GitHub 仓库基础质量。

## 5. 安全边界

- 不在代码、文档或提交中写入真实 API Key。
- `.env.example` 仅保留占位配置。
- LLM 配置接口在答辩 Demo 中免登录开放，但只写入本机环境配置，不提交到仓库。
- 真实 Spark API Key 不用于自动化测试；本地调试默认使用 Mock/fallback。
- 旧 demo endpoint 已禁用，避免依赖虚假演示数据。
- 非法资源下载路径会被拦截。

## 6. AI Coding 贡献总结

AI Coding 在本项目中主要提升了以下方面：

- 加速多智能体和资源包功能的产品化落地。
- 帮助完善学习闭环和展示逻辑。
- 快速补齐 smoke、deep QA、GitHub Actions 和交付文档。
- 协助发现依赖缺失并补齐 `requirements.txt`。
- 将项目从功能原型推进到比赛成品打磨阶段。

## 7. 人工最终负责

AI Coding 仅作为辅助工具，最终功能设计、代码审查、测试验证、演示材料和提交内容均由开发者人工确认。
