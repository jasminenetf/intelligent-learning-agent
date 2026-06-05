# 答辩 PPT 大纲

> 建议 15 页，每页含核心讲解点、配图建议、演讲提示

---

## P1 · 封面

**内容**: 高等教育个性化学习资源多智能体系统 / 团队名称 / 日期

**演讲**: "各位评委好，我们的项目是高等教育个性化学习资源多智能体系统。它基于 DeepSeek 真大模型，为大学生提供个性化学习资源自动生成服务。"

---

## P2 · 赛题背景与痛点

**核心点**:
- 高校学生基础差异大，同一课堂难兼顾所有学生
- 教师手动准备个性化资源（思维导图/讲义/测验/PPT）耗时巨大
- 学生不知道自己的知识短板，缺乏个性化学习路径
- 传统静态课件无法动态反映学生画像变化

**建议配图**: 痛点对比图（传统 vs 智能）

**演讲**: "当前高等教育面临四个核心痛点：学生差异大、资源准备难、知识盲区不清晰、课件无法动态适应。"

---

## P3 · 项目目标

**核心点**:
1. 上传课程资料 → 自动构建知识库
2. 自然语言交互 → 提取 8 维学生画像
3. OCR+RAG 检索 → DeepSeek 生成 5 类个性化资源
4. 画像驱动学习路径规划
5. PPTX 一键下载

**建议配图**: 系统功能一览图

---

## P4 · 总体架构

**架构分层**:
```
前端 Demo (HTML+CSS+JS)
  ↓ CORS + Bearer Token
FastAPI 后端 (25 paths / 30 routes)
  ├── Auth (JWT)
  ├── Profile API (8维画像)
  ├── OCR API (OCR→RAG)
  ├── RAG API (ChromaDB 检索)
  ├── Resource API (5类生成)
  ├── OpenAI-compatible API (/v1/models, /v1/chat)
  └── SQLAdmin (/admin)
      ↓
数据层: SQLite + ChromaDB
AI层: DeepSeek LLM + sentence-transformers
```

**建议配图**: Mermaid 架构图

---

## P5 · 核心技术路线

**数据流**: 教材/PDF → PyMuPDF 解析 → 文本清洗 → chunker 切块 → sentence-transformers 向量化 → ChromaDB 入库 → RAG 检索 → DeepSeek 生成 → 资源输出

**关键指标**:
- 25 API 端点，30 路由方法
- 4 张数据库表，8 维画像字段
- 5 类资源全部 DeepSeek 生成

---

## P6 · 多智能体协作设计

**Agent 链路**:
```
User Query → supervisor (协调)
  ├── profile_agent (画像更新)
  ├── rag_agent (课程检索)
  ├── resource_agent (资源生成)
  └── verifier (防幻觉校验)
     → answer + citations + agent_trace
```

**核心机制**: agent_trace 透明展示每一步调用，citations 标注引用来源

**建议配图**: Agent 流程图

---

## P7 · 学生画像设计（8维）

| 维度 | 字段 | 示例 |
|------|------|------|
| 知识水平 | knowledge_level | beginner |
| 认知风格 | cognitive_style | conceptual |
| 学习节奏 | pace_preference | slow |
| 知识薄弱点 | weak_points | ["导数","极限"] |
| 资源偏好 | resource_preference | ["mindmap","quiz"] |
| 专业 | major | 计算机 |
| 学习目标 | learning_goal | 考研备考 |
| 元学习 | meta_learning_level | medium |

**提取方式**: 自然语言 → DeepSeek LLM + 正则规则 fallback

---

## P8 · RAG 防幻觉机制

**防幻觉策略**:
1. 所有回答基于 ChromaDB 检索的课程资料
2. 每句话标注引用来源（chunk_id、source、page_number）
3. 无相关资料时明确告知学生"当前知识库缺少此内容"
4. OCR 来源 chunk 以 "ocr:" 前缀标记，区分来源可信度

**建议配图**: RAG 问答截图（含引用）

---

## P9 · 五类资源生成

| 资源 | 输出格式 | 生成方式 | rendered示例 |
|------|---------|---------|-------------|
| mindmap | Mermaid | DeepSeek→JSON→Mermaid | 思维导图 |
| lecture_doc | Markdown | DeepSeek→JSON→MD | 课程讲义 |
| quiz | JSON | DeepSeek→JSON→卡片 | 选择题+解析 |
| ppt | PPTX | DeepSeek→JSON→python-pptx | 8页课件 |
| study_plan | JSON | DeepSeek→JSON→步骤卡片 | 学习路径 |

**关键指标**: generated_by=deepseek, fallback_used=false

---

## P10 · 学习路径规划

**生成流程**: 学生画像 + course_id + topic → RAG 检索 → DeepSeek → JSON → 步骤卡片

**输出**: steps(按学习顺序,预计时间,推荐资源类型,练习建议) + recommended_topics + next_action

**个性化**: 薄弱点多安排练习，偏好可视化多安排 mindmap

---

## P11 · 前端 Demo 展示

**演示流程**:
1. 登录 → Token 自动填入
2. 检查系统状态 → 显示 is_mock=false
3. 提取画像 → 8 维字段
4. RAG 问答 → 回答+引用
5. 生成 mindmap → Mermaid 渲染
6. 生成 quiz → 题目卡片
7. 生成 ppt → 下载按钮
8. 生成 study_plan → 学习路径

**建议配图**: 前端截图 4-6 张

---

## P12 · 系统创新点

1. **多智能体协同**: supervisor 调度 + profile/rag/resource/verifier
2. **画像驱动生成**: 8 维画像个性化 5 类资源内容
3. **Agentic RAG 防幻觉**: 检索+验证+引用闭环
4. **OCR→RAG 链路**: 扫描版教材也可检索
5. **OpenAI 兼容**: /v1/models + /v1/chat 可直接对接 LobeChat

---

## P13 · 开源生态与协议

**技术栈**:
- FastAPI / SQLModel / SQLite — 后端
- ChromaDB — 向量存储
- LangGraph — 多 Agent 编排
- DeepSeek API — 真 LLM
- sentence-transformers — 真 Embedding
- PyMuPDF / python-pptx — 文档处理
- SQLAdmin — 管理后台
- Mermaid — 思维导图渲染
- LobeChat — 可选前端

**协议**: 各组件均为 MIT/Apache 2.0 开源协议，OSS_LICENSES.md 已记录

---

## P14 · 测试与演示结果

| 指标 | 值 |
|------|-----|
| API 端点 | 25 paths / 30 routes |
| LLM | DeepSeek-chat, is_mock=false |
| Embedding | sentence-transformers, is_mock=false |
| 5类资源 | generated_by=deepseek, fallback=false |
| 前端 | 登录/画像/问答/资源/下载 全部通过 |
| OCR | PyMuPDF 可用，Tesseract 待安装 |

---

## P15 · 总结与展望

**已完成**:
- 完整后端 + 前端 Demo 闭环
- DeepSeek 真 LLM + 真 Embedding
- 画像→资源→路径 个性化链路
- OCR→RAG→检索 知识库闭环

**待完善**:
- Tesseract OCR 安装（扫描版教材）
- 自动测试
- 生产环境安全加固

**扩展方向**: 语音交互、学习效果评估、视频/图解生成
