# 系统架构图与流程图

> 全部使用 Mermaid 语法，答辩/报告可直接渲染

---

## 1. 系统总体架构图

```mermaid
graph TB
    subgraph Frontend["前端层"]
        FE[frontend-demo<br/>HTML+CSS+JS]
        LC[LobeChat<br/>可选兼容]
    end

    subgraph API["FastAPI 后端 :8000"]
        AUTH[Auth API<br/>JWT 登录/注册]
        PROF[Profile API<br/>8维画像]
        OCR[OCR API<br/>OCR→RAG]
        RAG[RAG API<br/>检索/索引]
        RES[Resource API<br/>5类资源生成]
        OAI[OpenAI-compat<br/>/v1/models/chat]
        ADMIN[SQLAdmin<br/>/admin]
        VFY[Verifier<br/>防幻觉]
    end

    subgraph Data["数据层"]
        SQL[(SQLite<br/>4张表)]
        CHROMA[(ChromaDB<br/>向量索引)]
    end

    subgraph AI["AI 层"]
        DS[DeepSeek API<br/>真LLM]
        ST[sentence-transformers<br/>真Embedding]
        MU[PyMuPDF<br/>文档解析]
        PP[python-pptx<br/>PPT生成]
    end

    FE --> AUTH
    FE --> PROF
    FE --> RAG
    FE --> RES
    FE --> OAI
    LC --> OAI
    AUTH --> SQL
    PROF --> DS
    PROF --> SQL
    OCR --> MU
    OCR --> SQL
    OCR --> CHROMA
    RAG --> CHROMA
    RAG --> ST
    RES --> DS
    RES --> RAG
    RES --> PP
```

**说明**: 前端通过 Bearer Token 访问所有 API。LobeChat 可选接入 /v1 兼容接口。资源生成链路：Profile+RAG → DeepSeek → JSON → 渲染器。

---

## 2. 数据流图

```mermaid
flowchart LR
    PDF[教材 PDF] --> PARSE[PyMuPDF 解析]
    IMG[扫描版 PDF] --> OCR_ENGINE[Tesseract OCR]
    OCR_ENGINE --> TEXT[OCR 文本]
    PARSE --> TEXT2[文档文本]
    TEXT --> CHUNK[chunker 切块<br/>800字符/块]
    TEXT2 --> CHUNK
    CHUNK --> SQL[SQLite<br/>knowledge_chunks]
    CHUNK --> EMBED[sentence-transformers<br/>向量嵌入]
    EMBED --> CHROMA[ChromaDB<br/>向量索引]
    CHROMA --> RAG_SEARCH[RAG 检索]
    SQL --> RAG_SEARCH
    RAG_SEARCH --> PROMPT[Prompt Builder<br/>topic+profile+context]
    PROMPT --> DS[DeepSeek API]
    DS --> PARSE_JSON[JSON 清洗+解析]
    PARSE_JSON --> RENDER[渲染器]
    RENDER --> OUT[5类资源输出]
```

**说明**: 文字型 PDF 经 PyMuPDF 解析，扫描版需 Tesseract OCR。文本切块后同时写入 SQLite(元数据)和 ChromaDB(向量)。RAG 检索时优先向量相似度，前端展示引用来源。

---

## 3. 多智能体流程图

```mermaid
flowchart TD
    Q[学生提问] --> SUP[supervisor<br/>任务分解]
    SUP --> PROF_NODE[profile_agent<br/>画像更新]
    PROF_NODE --> PROFILE[(8维画像)]
    SUP --> RAG_NODE[rag_agent<br/>课程检索]
    RAG_NODE --> CHROMA_DB[(ChromaDB)]
    RAG_NODE --> CHUNKS[检索结果 chunks]
    SUP --> LEC_NODE[resource_agent<br/>内容生成]
    LEC_NODE --> DS_API[DeepSeek API]
    DS_API --> DRAFT[初稿答案]
    SUP --> VFY_NODE[verifier<br/>防幻觉校验]
    DRAFT --> VFY_NODE
    CHUNKS --> VFY_NODE
    VFY_NODE --> FINAL[最终回答<br/>+ citations<br/>+ agent_trace]
```

**说明**: LangGraph 多 Agent 工作流。supervisor 调度各子 Agent，profile_agent 维护画像，rag_agent 检索课程资料，resource_agent 调用 DeepSeek 生成内容，verifier 校验答案与资料一致性并标注引用来源。

---

## 4. 资源生成流程图

```mermaid
flowchart TD
    START([输入: topic + course_id + user]) --> PROF[get_or_create_profile<br/>8维画像]
    PROF --> RAG_RET[search_course<br/>RAG 检索 top_k=8]
    RAG_RET --> CHUNKS{有资料?}
    CHUNKS -- 无 --> ERR[返回错误]
    CHUNKS -- 有 --> BUILD_PROMPT[构建 Prompt<br/>topic + context + profile]
    BUILD_PROMPT --> CALL_DS{DeepSeek<br/>可用?}
    CALL_DS -- 是 --> DS_GEN[DeepSeek 生成 JSON]
    CALL_DS -- 否/Mock --> FALLBACK[fallback_template]
    DS_GEN --> CLEAN[_clean_json<br/>去围栏+修复尾逗号]
    CLEAN --> PARSE{JSON<br/>合法?}
    PARSE -- 否 --> FALLBACK
    PARSE -- 是 --> RENDER[渲染器]
    RENDER --> MINDMAP[mindmap → Mermaid]
    RENDER --> LECTURE[lecture_doc → Markdown]
    RENDER --> QUIZ[quiz → 题目卡片]
    RENDER --> PPT_OUT[ppt → PPTX bytes]
    RENDER --> PLAN[study_plan → 步骤卡片]
    MINDMAP --> META[标记 generated_by=deepseek<br/>fallback_used=false]
    LECTURE --> META
    QUIZ --> META
    PPT_OUT --> META
    PLAN --> META
    FALLBACK --> META_FB[标记 generated_by=fallback_template<br/>fallback_used=true]
    META --> RESP[ResourcePackResponse]
    META_FB --> RESP
```

**说明**: 统一生成管线。优先真 LLM，失败或 Mock 时 fallback 到模板。每个资源标记 generated_by 和 fallback_used，前端可据此展示生成来源。
