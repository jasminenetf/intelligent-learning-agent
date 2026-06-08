# AI Coding 使用说明

## 1. 使用目的

本项目允许使用 AI Coding 工具辅助完成需求分析、代码实现、重构优化、测试脚本编写和交付文档整理。AI Coding 的目标不是替代人工设计，而是提升开发效率，并通过人工审核、lint 和 smoke 回归保证质量。

## 2. 使用范围

AI Coding 主要参与以下环节：

- 需求拆解：根据项目要求文档梳理 P0/P1/P2 长任务。
- 前端开发：完善学习工作台、资源包详情、学习报告、画像中心、多模态资源展示。
- 后端开发：补齐多智能体 trace schema、学习报告 mastery 字段、依赖配置。
- 测试增强：扩展 `scripts/verify_p0_smoke.py`，覆盖 mastery、agent trace、grounding、resource package。
- 文档编写：生成系统设计文档、技术实现文档、演示脚本和答辩材料。

## 3. 人工审核机制

所有 AI 生成或修改的内容均经过人工检查，重点包括：

- 是否符合项目要求。
- 是否与已有代码结构一致。
- 是否存在安全风险或密钥泄露。
- 是否破坏已有接口兼容性。
- 是否能通过 linter 和 smoke 回归。

## 4. 质量控制

项目通过以下方式控制质量：

### 4.1 Lint 检查

对关键文件执行静态检查，例如：

- `frontend-demo/app.js`
- `backend/app/services/agent_graph.py`
- `backend/app/services/learning_report_service.py`
- `scripts/verify_p0_smoke.py`

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

## 5. 安全边界

- 不在代码、文档或提交中写入真实 API Key。
- `.env.example` 仅保留占位配置。
- LLM 配置接口仅允许管理员操作。
- demo endpoint 已禁用，避免依赖虚假演示数据。
- 非法资源下载路径会被拦截。

## 6. AI Coding 贡献总结

AI Coding 在本项目中主要提升了以下方面：

- 加速多智能体和资源包功能的产品化落地。
- 帮助完善学习闭环和展示逻辑。
- 快速补齐 smoke 回归和交付文档。
- 协助发现依赖缺失并补齐 `requirements.txt`。
- 将项目从功能原型推进到比赛成品打磨阶段。

## 7. 人工最终负责

AI Coding 仅作为辅助工具，最终功能设计、代码审查、测试验证、演示材料和提交内容均由开发者人工确认。