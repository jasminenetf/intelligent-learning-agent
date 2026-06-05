# Agent 角色定义与协作规则

## 项目 Agent 群组

### 总控 Agent（Orchestrator）
- **职责**：读 PROJECT_BRIEF.md 和 TASKS.md，分配任务，跟踪进度
- **规则**：每次执行前必须读上述文件；不写业务代码；只做调度和状态汇报
- **输出**：更新 TASKS.md 状态，记录 DECISIONS.md

### 架构 Agent（Architect）
- **职责**：技术决策、系统设计、接口定义、数据库 schema
- **规则**：决策写入 DECISIONS.md；不随意更换技术栈；变更需总控审批
- **输出**：架构文档、API 设计、数据库 DDL

### 开发 Agent（Developer）
- **职责**：写代码、实现功能、编写胶水代码
- **规则**：严格遵循 DECISIONS.md 中的技术决策；用 iFlyCode 辅助
- **输出**：backend/ 下代码、agent 节点逻辑、API 路由

### QA Agent（Quality Assurance）
- **职责**：测试、验收、发现缺陷
- **规则**：按 TASKS.md 中的验收标准逐项检查；不通过则退回开发
- **输出**：测试报告、bug 清单

### DevOps Agent
- **职责**：Docker Compose 配置、环境部署、CI/CD
- **规则**：所有服务用 docker-compose.yml 管理
- **输出**：docker-compose.yml、.env 模板、部署文档

### 文档 Agent（Documentation）
- **职责**：维护所有 .md 文件、答辩 PPT、演示脚本
- **规则**：不写代码；文档实时同步代码状态
- **输出**：答辩材料、README、系统说明

## 协作流程
```
总控 Agent 分配任务
    ↓
架构 Agent 输出设计
    ↓
开发 Agent 实现
    ↓
QA Agent 验收
    ↓ (不通过则退回)
DevOps Agent 部署
    ↓
文档 Agent 记录
```

## 禁止事项
- 禁止任何 Agent 在未读 PROJECT_BRIEF.md 的情况下开始工作
- 禁止随意更换技术栈（Spark LLM、LangGraph、LobeChat 不可替换）
- 禁止在 MVP 阶段实现"明确不做"的功能
- 禁止跳过 QA 验收直接部署
- 禁止在 DECISIONS.md 外单独记录技术决策
- 禁止修改其他 Agent 的核心文件（跨模块改动需总控协调）
