# WOLF 2.0 改进大纲

> 基于 `E:\ai\ARG\learn\` 全部 84 份文档总结 | 仅涉及 `app/`，不涉及 `app_team`

---

## 改造后完整架构

```
app/
├── vector_store/          ← [新增] RAG 向量检索 + Agentic RAG
│   ├── embedder.py            Embedding 模型封装 (bge-small-zh-v1.5)
│   ├── splitter.py            文本分块 (固定/代码/Markdown三种策略)
│   ├── store.py               ChromaDB CRUD 封装
│   ├── retriever.py           检索器 + 重排序 + 多步推理检索
│   ├── ingest.py              文档摄入流水线 (文件/目录批量索引)
│   ├── tool.py                Agent Tool 注册 (rag_search/ingest/status)
│   ├── kg_builder.py          [Agentic RAG] 自动知识图谱构建器
│   ├── hybrid_retriever.py    [Agentic RAG] 向量+BM25+图 三路RRF融合
│   └── error_book.py          [Agentic RAG] Error Book 自我纠错
│
├── prompt/                 ← [改造] Prompt 工程系统
│   ├── orchestrator.py        统一调度核心
│   ├── layers.py              四层架构 (角色/规则/上下文/输出)
│   ├── template.py            Jinja2 模板引擎
│   ├── versioning.py          语义化版本管理 + diff + rollback
│   ├── ab_test.py             A/B 测试框架
│   ├── assembler.py           [对标CC] 条件化 Prompt 组装
│   ├── compact.py             [对标CC] 上下文压缩 Prompt 子系统
│   ├── cache.py               [对标CC] Section级缓存 (static/session)
│   ├── feature_flags.py       [对标CC] Feature Flag 灰度发布
│   ├── core/schemas.py        数据模型定义
│   ├── core/constants.py      常量定义
│   └── templates/*.j2         可复用 Jinja2 模板
│
├── observability/          ← [新增] LLM 可观测性
│   ├── langfuse_client.py     LangFuse Trace 平台客户端
│   ├── tracker.py             @track_llm_call 装饰器 + StatsAggregator
│   └── cost.py                CostCalculator + 预算预警 + 自动降级
│
├── memory/                 ← [增强] 认知记忆架构
│   ├── cognitive.py           五层记忆层级 + Ebbinghaus 遗忘曲线
│   ├── consolidation.py       SleepConsolidation 睡眠整合引擎
│   ├── scorer.py              四维重要性评分 (recency×freq×surprise×outcome)
│   └── vector_sync.py         记忆-向量库同步桥
│
├── evolution/              ← [新增] 自我进化 (AGP 协议)
│   ├── versioned_artifact.py  版本化工件存储 (Prompt/Skill/Tool)
│   ├── skill_optimizer.py     Skill 自动优化器 (TextualLR + ReflectionMinibatch)
│   ├── tool_evolver.py        Tool 描述自动优化
│   └── rollout_manager.py     灰度发布 + 自动回滚
│
├── skills/                 ← [增强] Skill 系统强化
│   ├── agentskills_loader.py  兼容 agentskills.io 开放标准
│   ├── trainer.py             Skill 自动训练器
│   ├── evaluator.py           留出验证集 + 门控机制
│   └── meta_update.py         跨Skill元分析 + 三级调度
│
├── cache/                  ← [新增] 生产级基础设施
│   └── redis_client.py        Redis (Session/Embedding/RateLimiter/TaskQueue)
│
├── middleware/
│   └── injection_guard.py     [新增] Prompt Injection 防护
│
├── security/
│   └── verifier.py            [新增] AgentFSM 形式化安全验证
│
├── tools/
│   ├── predictive_executor.py [新增] CBR 预测式执行 (MCP-Cosmos 启发)
│   └── definitions/agentic_rag.py [新增] Agentic RAG 工具定义
│
├── mcp/
│   └── a2a_bridge.py          [新增] Google A2A Agent间通信协议
│
├── core/providers/
│   ├── ollama_provider.py     [新增] 本地 Ollama 模型适配
│   └── vllm_provider.py       [新增] vLLM 推理集群适配
│
└── api/
    ├── prompt_routes.py        [新增] Prompt 管理 API (9端点)
    ├── observability.py        [新增] 可观测性 API (4端点)
    └── routes/evolution.py     [新增] 进化系统 API (4端点)
```

---

## 总览

| 模块 | 优先级 | 新建文件 | 修改文件 | 核心前沿技术 |
|------|--------|----------|----------|-------------|
| 一、RAG 向量检索 + Agentic RAG | 🔴 | 10 | 5 | ChromaDB, Kuzu, RRF, LLM-Wiki Error Book |
| 二、Prompt 工程系统 | 🔴 | 16 | 4 | Feature Flag, Compaction, Section Cache, DSPy |
| 三、LLM 可观测性 | 🟡 | 4 | 3 | LangFuse, OpenTelemetry, SWE-bench |
| 四、认知记忆架构 | 🟡 | 4 | 5 | ZenBrain, Ebbinghaus, Sleep Consolidation |
| 五、自我进化系统 | 🟡 | 5 | 2 | AGP (Stanford), SkillOpt (Microsoft), TextualLR |
| 六、Skill 系统强化 | 🟢 | 4 | 2 | Agent Skills 开放标准 (Anthropic), 渐进式披露 |
| 七、生产级基础设施 | 🟢 | 4 | 3 | MAESTRO, Redis, Ollama/vLLM |
| 八、前沿功能探索 | 🔵 | 3 | 1 | MCP-Cosmos (IBM), A2A (Google), AgentFSM |
| **合计** | | **50** | **25** | **20+ 种前沿技术** |

---

## 实施优先级矩阵

```
                    影响力
                中          高
           ┌─────────┬─────────┐
      高   │ 8.前沿   │ 1.RAG   │  ← 立即开始
实         │ 功能     │ 2.Prompt│
施   ├─────────┼─────────┤
难   │ 6.Skill │ 3.观测  │
度   │ 7.生产  │ 4.记忆  │  ← 第二批
      低   │         │ 5.进化  │
           └─────────┴─────────┘
```

**推荐实施顺序**：RAG+Prompt (1-2周) → 观测+记忆 (3-4周) → 进化+Skill (5-6周) → 生产+前沿 (7-8周)

---

## 一、RAG 向量检索 + Agentic RAG 🔴

> **前沿研究**：LLM-Wiki (Tencent, arXiv:2605.25480) — 检索即推理 | Do We Still Need GraphRAG? (arXiv:2604.09666) — Agentic Search 基准 | RRF — Reciprocal Rank Fusion | Kuzu 嵌入式图数据库 | Matryoshka Embedding (arXiv:2205.13147)

### 架构

```
用户提问
    │
    ▼
┌──────────────────────────────────────┐
│  Agent (Tool 选择)                    │
│    ├── grep (关键词)                   │
│    ├── glob (文件名)                   │
│    └── rag_search (语义) ← 新增       │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  app/vector_store/retriever.py       │
│    ├── 向量检索 (ChromaDB)            │
│    ├── BM25 关键词 (rank-bm25)        │
│    ├── 图遍历 (Kuzu) ← Agentic RAG   │
│    └── RRF 融合 → LLM 上下文          │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  存储层                               │
│    ├── ChromaDB (向量)                │
│    ├── Kuzu (知识图谱)                │
│    └── SQLite (Error Book)            │
└──────────────────────────────────────┘
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/vector_store/__init__.py` | 模块入口，`setup_vector_store()` 初始化 ChromaDB + Embedder + 注册 Tool |
| `app/vector_store/embedder.py` | Embedding 模型封装，默认 `BAAI/bge-small-zh-v1.5` (512维)，支持 OpenAI/text-embedding-3-small 后端切换 |
| `app/vector_store/splitter.py` | 三种分块策略：`split_code()` 按函数/类边界、`split_markdown()` 按 ## 标题、`split_generic()` 固定大小 |
| `app/vector_store/store.py` | ChromaDB CRUD 封装：`add()` / `query()` / `remove_by_source()` / `count()`，统一返回 `[{"text","metadata","score"}]` |
| `app/vector_store/retriever.py` | `retrieve()` 向量粗筛 → 关键词重排序 → top-k；`retrieve_as_context()` 格式化为 LLM Prompt 上下文 |
| `app/vector_store/ingest.py` | `ingest_file()` 单文件摄入；`ingest_directory()` 批量目录摄入（排除 node_modules/.git 等），内容 hash 增量更新 |
| `app/vector_store/tool.py` | 注册 3 个 Agent Tool：`rag_search` / `rag_ingest` / `rag_status` |
| `app/vector_store/kg_builder.py` | **Agentic RAG** — AutoKGBuilder：LLM 提取 (实体,关系,实体) 三元组 → Kuzu 图数据库写入 |
| `app/vector_store/hybrid_retriever.py` | **Agentic RAG** — HybridRetriever：向量 + BM25 + 图遍历三路 RRF 融合 |
| `app/vector_store/error_book.py` | **Agentic RAG** — ErrorBook：SQLite 持久化检索错误 + 两阶段修复 (代码级确定性规则 + LLM 级模式分析) |
| `app/tools/definitions/agentic_rag.py` | Agentic RAG 工具参数定义 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/main.py` | lifespan 中 Tool 注册后调用 `setup_vector_store()`；注册 Agentic RAG 工具 |
| `config.json` | 新增 `vector_store` 配置段 (persist_path, embedding_model, chunk_size, chunk_overlap) |
| `app/core/runtime_config.py` | RuntimeConfig 新增 vector_store 相关字段 + 加载逻辑 |
| `requirements.txt` | 追加 `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`, `kuzu`, `rank-bm25` |
| `app/retriever.py` | 新增 `multi_step_retrieve()` 多步推理检索 (search→read→verify→refine, 最多3轮) |

### 性能提升

- Token 消耗：单次对话从 ~200K 降至 ~5K（预先索引，按需检索 → **节省 97%**）
- 复杂查询准确率：知识图谱多跳推理 +30-50%（参考 GraphRAG 基准）
- 检索失败自动修正：Error Book 两阶段修复 → 同类型错误不再重复

---

## 二、Prompt 工程系统 🔴

> **对标参考**：Claude Code (`cc-haha-main/src/constants/prompts.ts` + `systemPromptSections.ts`) — Section级缓存 / Feature Flag / Compaction / 条件化组装 | DSPy (Stanford) — 声明式 Prompt 编程 | SkillOpt (Microsoft 2026) — Textual Learning Rate

### 架构

```
┌──────────────────────────────────────────────────────┐
│              PromptOrchestrator (调度核心)             │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Assembler│  │ Template │  │Versioning│           │
│  │ 条件化组装│  │ Jinja2   │  │ save/load│           │
│  │ (对标CC) │  │ 模板引擎  │  │ /rollback│           │
│  └──────────┘  └──────────┘  └──────────┘           │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ A/B Test │  │ Compact  │  │  Cache   │           │
│  │ 流量分流 │  │ 上下文压缩│  │Section缓存│          │
│  │ 统计检验 │  │ (>80%触发)│  │(对标CC)  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
│                                                      │
│  ┌──────────────────────────────────────────┐       │
│  │        Feature Flag (灰度发布)             │       │
│  │  一致性哈希分流 → 10%→50%→100% 逐级放量    │       │
│  └──────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Section 组装结果 (按条件动态选择)                     │
│                                                      │
│  Static (跨会话复用/cross-org cache):                 │
│    ├── 角色定义 ("You are WOLF...")                   │
│    ├── 通用规则 ("Don't create helpers...")           │
│    ├── 安全指引 + 风险操作清单                         │
│    └── Tool 使用原则 (对标CC: prefer dedicated tools)  │
│                                                      │
│  Dynamic (每轮/每会话重新计算):                        │
│    ├── Tool 列表 + Tool 级行为边界指引 ← 2.1改造      │
│    ├── Skill 元数据索引 (渐进式披露) ← 2.3改造         │
│    ├── 用户上下文 (CLAUDE.md)                         │
│    ├── Git 状态 + 时间戳                               │
│    └── Feature Flag 实验特性 ← 2.4改造                 │
└──────────────────────────────────────────────────────┘
```

### 现状诊断

| # | 问题 | CC 是怎么做的 |
|---|------|--------------|
| 1 | Prompt 硬编码在 Python 源码中 | 分离到独立文件，每个 Tool/Feature 自带 Prompt，通过 Section 机制注入 |
| 2 | 无 Tool 级行为边界指导 | `BashTool/prompt.ts`: "Do NOT use Bash when a dedicated tool exists" |
| 3 | 拼装顺序固定，无场景感知 | `getSessionSpecificGuidanceSection()`: 根据 REPL/Skill/AgentTool 条件化 |
| 4 | Skill 全量注入，无渐进式披露 | 只注入元数据，Agent 需要时才读取完整 SKILL.md |
| 5 | 无版本管理与优化闭环 | Feature Flag 灰度 + A/B 测试量化 |
| 6 | 缓存粒度粗糙 | Section 级缓存 + STATIC_DYNAMIC_BOUNDARY 分离 |

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/prompt/orchestrator.py` | PromptOrchestrator 统一调度核心，协调 assembler/template/versioning/ab_test/compact 各子系统 |
| `app/prompt/assembler.py` | **对标 CC `getSessionSpecificGuidanceSection()`** — 根据 enabled_tools / active_skills / session_mode 条件化组装 Prompt |
| `app/prompt/layers.py` | 四层架构定义：RoleLayer (角色) / RulesLayer (规则) / ContextLayer (上下文) / OutputLayer (输出) |
| `app/prompt/template.py` | Jinja2 模板引擎封装，支持变量/条件/循环/宏，替代裸字符串拼接 |
| `app/prompt/versioning.py` | 语义化版本管理：`save()` / `load()` / `rollback()` / `diff()` / `list_versions()`，JSON 文件 + 索引持久化 |
| `app/prompt/ab_test.py` | A/B 测试框架：流量分流 (随机/hash/canary) + 统计显著性判断 + 效果差异阈值 |
| `app/prompt/compact.py` | **对标 CC `services/compact/prompt.ts`** — CompactManager：检测上下文 >80% → 触发压缩 → "保留架构决策/Bug/实现细节，丢弃冗余工具输出" |
| `app/prompt/cache.py` | **对标 CC `systemPromptSections.ts`** — SectionCache：static 跨会话复用 (global scope) / session 级按需失效 |
| `app/prompt/feature_flags.py` | **对标 CC `feature()` 机制** — 基于 session_id 一致性哈希分流，支持 0-100% 灰度，A/B 实验管理 |
| `app/prompt/core/schemas.py` | 数据模型：LayerType / PromptVersion / ABTestConfig / FeatureFlag / CompactConfig |
| `app/prompt/core/constants.py` | 常量：默认 chunk_size / 半衰期 / 灰度阈值 / 缓存 scope |
| `app/prompt/templates/base.j2` | 基础 Jinja2 模板 |
| `app/prompt/templates/role.j2` | 角色层模板 |
| `app/prompt/templates/rules.j2` | 规则层模板 |
| `app/prompt/templates/context.j2` | 上下文层模板 |
| `app/prompt/templates/output.j2` | 输出层模板 |
| `app/prompt/existing/prompts_compat.py` | `prompts.py` 兼容包装 (渐进式迁移，不破坏现有代码) |
| `app/prompt/existing/sections_compat.py` | `sections.py` 兼容包装 |
| `app/prompt/existing/system_compat.py` | `system.py` 兼容包装 |
| `app/api/prompt_routes.py` | 9个API端点：版本管理 (CRUD+rollback+diff) + A/B测试 (create/status/decide) + 实验特性管理 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/prompt/__init__.py` | 导出新模块，`init_prompt_system()` 初始化所有子系统 |
| `app/prompt/prompts.py` | 现有 Section 函数适配为 LayerProvider 接口 |
| `app/main.py` | lifespan 中调用 `init_prompt_system()` |
| `config.json` | 新增 `prompt_system` + `prompt_experiments` 配置段 |
| `requirements.txt` | 追加 `jinja2>=3.1.0` |

### 性能提升

| 改造点 | 对标 CC | 效果 |
|--------|---------|------|
| Tool 级自描述 Prompt | `tools/*/prompt.ts` | Tool 选择准确率↑，误用率↓ |
| 条件化 Prompt 组装 | `getSessionSpecificGuidanceSection()` | Prompt 长度 -20-40%，幻觉率↓ |
| 渐进式 Skill 披露 | `DISCOVER_SKILLS_TOOL_NAME` | System Prompt Token -50-70% |
| Feature Flag 灰度 | `feature()` | 改坏了 10% 阶段终止，不波及全量 |
| Compaction 子系统 | `services/compact/prompt.ts` | 长会话不爆窗口，信息保留 95%+ |
| Section 级缓存 | `systemPromptSections.ts` | Prompt 构建延迟 -60-80% |
| 版本管理 + A/B 测试 | — | 秒级回滚，数据驱动优化 |

---

## 三、LLM 可观测性 🟡

> **前沿研究**：LangFuse — LLM Trace 标准平台 (2026 主流) | OpenTelemetry for LLMs — 标准化可观测性 | SWE-bench Verified/Atlas/EVO — Agent 评估基准

### 架构

```
LLM 调用
    │
    ▼
┌──────────────────────────────────────┐
│  @track_llm_call 装饰器 (AOP 注入)    │
│    ├── 记录: model/tokens/latency/cost│
│    ├── Trace: 发送到 LangFuse         │
│    └── Stats: 写入 StatsAggregator    │
└──────────────────────────────────────┘
    │
    ├───────────────────────────────────┐
    ▼                                   ▼
┌──────────────────┐    ┌──────────────────────┐
│  LangFuse        │    │  CostCalculator      │
│  (Trace 平台)     │    │  - 日/月预算追踪      │
│  - 调用链可视化    │    │  - 80% 预警阈值       │
│  - 按 Provider/   │    │  - 超限自动降级模型    │
│    Model/Session  │    │  - 成本优化建议        │
│    聚合分析        │    └──────────────────────┘
└──────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  前端 Dashboard (wolf_f)              │
│    ├── TokenUsageChart (折线图)       │
│    ├── CostBreakdown (饼图/Provider)  │
│    ├── ModelPerformance (表)          │
│    └── RecentCalls (实时日志)         │
└──────────────────────────────────────┘
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/observability/__init__.py` | 模块入口，`setup_observability()` 初始化 LangFuse + Tracker + CostCalculator |
| `app/observability/langfuse_client.py` | LangFuse API 客户端：Trace 创建/查询/统计，支持降级到本地内存 |
| `app/observability/tracker.py` | `@track_llm_call` 装饰器 (同步+异步) + StatsAggregator 滑动窗口 (2000条) |
| `app/observability/cost.py` | CostCalculator：日/月预算上限 + 80% 预警 + 自动降级模型切换 |
| `app/api/observability.py` | 4个API端点：stats / traces / cost/projection / alert/config |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/services/llm_service.py` | `complete()` 和 `stream_complete()` 添加 `@track_llm_call` 装饰器 |
| `app/main.py` | lifespan 中注册 observability 路由 + 初始化可观测性模块 |
| `config.json` | 新增 `observability` 配置段 (langfuse 连接 + budget 预算) |
| `requirements.txt` | 追加 `langfuse>=2.0.0` |

### 性能提升

- 自动采集所有 LLM 调用 Trace → 按 Provider/Model/Session 聚合 → **淘汰低效模型，月成本 -20-40%**
- 日预算超限自动降级到低成本模型防爆单
- 前端仪表板 30 秒自动刷新

---

## 四、认知记忆架构 🟡

> **前沿研究**：ZenBrain (arXiv:2604.23878) — 7层认知记忆 + Ebbinghaus 遗忘 | CogniFold (arXiv:2605.13438) — 主动记忆 | SuperLocalMemory V3.3 (arXiv:2604.04514) — 生物遗忘 | SCG-MEM (arXiv:2604.20117) — Schema 约束生成 | Claude Code Auto Dream — Sleep Consolidation 生产实践

### 架构

```
记忆生命周期:
  
  用户反馈 / Agent 行为
    │
    ▼
┌──────────────────────────────────────┐
│  [Working Memory]  当前会话上下文      │  ← 会话窗口内
│        │ Ebbinghaus 衰减              │
│        ▼                              │
│  [Short-Term]  SQLite + 文件系统       │  ← 最近 N 天，权重随时间衰减
│        │ Sleep Consolidation (6h)     │
│        ▼                              │
│  [Episodic]  ChromaDB 向量库           │  ← 长期向量化记忆
│        │ 模式提取                     │
│        ▼                              │
│  [Semantic]  知识图谱 (Kuzu)           │  ← 抽象规则 / 实体关系
│        │ 元认知                       │
│        ▼                              │
│  [Procedural] 有效工作流模板            │  ← Skill / 操作序列
└──────────────────────────────────────┘

重要性评分 = Recency(25%) × Frequency(25%) × BayesianSurprise(25%) × Outcome(25%)
遗忘曲线 = 初始权重 × e^(-t/半衰期)
  半衰期: user=30天 | feedback=90天 | project=7天 | reference=60天
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/memory/cognitive.py` | CognitiveMemoryLayer 五层枚举 + EbbinghausDecay 衰减引擎 (R=e^(-t/T)，按记忆类型设置不同半衰期) |
| `app/memory/consolidation.py` | SleepConsolidation 睡眠整合引擎：后台定时任务 (默认6小时间隔)，聚类相似短期记忆→合并为精炼长期知识 |
| `app/memory/scorer.py` | MemoryScorer 四维评分器：recency (最近使用) × frequency (检索频率) × bayesian_surprise (与已有记忆的矛盾度) × outcome (关联任务成功/失败) |
| `app/memory/vector_sync.py` | MemoryVectorSync 同步桥：`write_memory()` 时自动生成 Embedding → ChromaDB，检索时语义搜索优先 + TF-Jaccard fallback |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/memory/types.py` | MemoryEntry 新增：`review_count`, `strength_boost`, `importance_score`, `cognitive_layer` |
| `app/memory/__init__.py` | 导出认知增强模块 |
| `app/memory/management.py` | 新增 `get_importance_scores()` / `prune_by_importance()` / `record_memory_usage()` |
| `app/memory/memory_tools.py` | 新增 `register_cognitive_tools()`，注册 MemoryImportance / MemoryConsolidate / MemoryDecay |
| `app/memory/directory.py` | `write_memory()` 末尾调用 `sync_memory_on_write()` hook 同步到向量库 |
| `app/main.py` | lifespan 中初始化 SleepConsolidation 后台任务 + 注册认知工具 |

### 性能提升

- 重要记忆自动提升权重 → Agent 优先回忆有效经验
- 低分记忆自动清理 → **存储 -60%，保留 95%+ 有用信息**（参考 ZenBrain 实测数据）
- Sleep Consolidation → 相似记忆合并为精炼知识，减少碎片化
- 语义检索替代关键词匹配 → 记忆召回率显著提升

---

## 五、自我进化系统 🟡

> **前沿研究**：AGP — Autogenesis Protocol (Stanford, arXiv:2604.15034) — Agent 资源版本化+可审计回滚 | SkillOpt (Microsoft 2026) — Textual Learning Rate + Reflection Minibatch | Mimosa Framework (arXiv:2603.28986) — 自进化多Agent科学发现

### 架构

```
Skill/Tool 执行轨迹
    │
    ▼
┌──────────────────────────────────────┐
│  ReflectionMinibatch                 │
│  (积累 20 条失败轨迹 → 批量分析)       │
│        │                             │
│        ▼                             │
│  SkillOptimizer / ToolEvolver        │
│  (TextualLR 控制修改幅度)             │
│        │                             │
│        ▼                             │
│  生成优化版本 (v1.0.1 → v1.1.0)      │
│        │                             │
│        ▼                             │
│  RolloutManager                      │
│  DRAFT → CANARY(10%) → PARTIAL(50%)  │
│        │              │              │
│        │         ┌────┘              │
│        ▼         ▼                   │
│   FULL_RELEASE  ROLLED_BACK          │
│   (成功率↑)     (成功率↓10%)          │
└──────────────────────────────────────┘
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/evolution/__init__.py` | 包入口，`setup_evolution_system()` 初始化所有子系统 + 注册 API |
| `app/evolution/versioned_artifact.py` | VersionedArtifact 数据类 (semver+score+changelog) + ArtifactStore JSON 文件持久化，支持 save/load/rollback/diff/list_versions |
| `app/evolution/skill_optimizer.py` | SkillOptimizer：ReflectionMinibatch (积累20条失败轨迹) → 共性分析 → TextualLR 控制修改幅度 (0.001~0.3) → 生成优化版本 |
| `app/evolution/tool_evolver.py` | ToolDescOptimizer + ToolUsageAnalyzer (分析调用频率/成功率/参数错误) + MissingToolDetector (检测需求缺口) |
| `app/evolution/rollout_manager.py` | RolloutManager 灰度发布状态机：DRAFT→CANARY(10%)→PARTIAL(50%)→FULL_RELEASE / ROLLED_BACK，综合评分 (success_rate 40% + satisfaction 30% + efficiency 20% + latency 10%)，自动回滚阈值 10% |
| `app/api/routes/evolution.py` | 4个API端点：status / rollout / evaluate / rollback |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/main.py` | lifespan 中初始化 evolution 系统 + 注册路由 |

### 性能提升

- Skill 自动检测性能下降 → 分析失败轨迹 → 生成优化 → 灰度验证 → 全量或回滚
- **Skill 成功率持续收敛至 85%+**
- Tool 描述持续优化 → Agent 选择正确 Tool 的概率上升

---

## 六、Skill 系统强化 🟢

> **前沿研究**：Agent Skills 开放标准 (Anthropic 2025.10, agentskills.io) — 三层渐进式披露 | Claude Code Skills — 生产实践 | SkillOpt (Microsoft 2026) — TextualLR + 留出验证集

### 架构

```
启动时:
  扫描 bundled/ + user/ + project/ Skill 目录
    │
    ▼
  agentskills_loader.py → 解析 SKILL.md (YAML frontmatter + Markdown)
    │
    ▼
  System Prompt 中仅注入元数据索引:
    "可用: /pdf(处理PDF), /commit(创建提交), ..."
    │
    ▼
  运行时 (渐进式披露):
    Layer 1: 元数据 (name + description) → 始终在 System Prompt
    Layer 2: 用户触发 → Agent 读取 SKILL.md 全文 → 注入上下文
    Layer 3: SKILL.md 引用 references/ → Agent 按需深入读取
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/skills/agentskills_loader.py` | 兼容 agentskills.io 开放标准：解析 YAML frontmatter (name/description/tags/tests/metadata)，支持 `references/` 目录渐进式加载 |
| `app/skills/trainer.py` | SkillTrainer：轨迹缓冲 SQLite → ReflectionEngine 反思 → TextualOptimizer 文本优化器 (TextualLR 控制修改幅度) |
| `app/skills/evaluator.py` | SkillEvaluator：80/20 留出验证集 + 门控机制 (优化后准确率 >= 优化前 才准发布) + 三大指标 (成功率/Token消耗/质量) |
| `app/skills/meta_update.py` | MetaUpdater：跨 Skill 模式分析 + OptimizationScheduler 三级调度 (daily 高频轻量 / weekly 全量评估 / monthly 元更新) |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/skills/__init__.py` | 新增导出 + `build_progressive_prompt()` (渐进式披露：只注入活跃 Skill 全文，其余仅索引) |
| `app/main.py` | lifespan 中初始化 Skill 训练系统 |

### 性能提升

- 渐进式披露：System Prompt Token **-50-70%**（不再全量注入 Skill 内容）
- 留出验证集门控：效果下降的优化版本**自动拦截**，不上线
- 跨 Skill 元分析：发现通用改进模式 → 批量优化

---

## 七、生产级基础设施 🟢

> **前沿研究**：MAESTRO 框架 — MCP 环境下 16 种攻击类别防御 (95.7% 拦截率) | Ollama — 本地模型零 API 成本部署 | vLLM — PagedAttention 高性能推理 | Semantic Cache (GPTCache) — Embedding 缓存

### 架构

```
请求 → ┌──────────────────────┐
       │  InjectionGuard      │ ← 检测 Prompt Injection (8组规则)
       │  (block/warn/log)    │
       └──────────────────────┘
                │
       ┌──────────────────────┐
       │  RateLimiter (Redis) │ ← 滑动窗口限流
       └──────────────────────┘
                │
       ┌──────────────────────┐
       │  PermissionManager   │ ← 四级权限检查
       │  READ_ONLY/NETWORK   │
       │  /WRITE/SHELL        │
       └──────────────────────┘
                │
       ┌──────────────────────┐
       │  Cache Layer (Redis) │ ← Session/Embedding/TaskQueue
       └──────────────────────┘
                │
       ┌──────────────────────┐
       │  LLM Provider Router │ ← Ollama(本地) / vLLM / API
       └──────────────────────┘
```

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/cache/redis_client.py` | RedisClient 连接池 (最大20连接) + SessionCache (1h TTL) + EmbeddingCache (24h TTL, SHA256键) + RateLimiter (incr+expire滑动窗口) + TaskQueue (rpush/blpop) |
| `app/middleware/injection_guard.py` | InjectionDetector (8组 SUSPICIOUS_PATTERNS: system_override/jailbreak/code_exec/data_leak) + 风险评分 (高危+0.3) + 三级动作 (>=0.8 block / >=0.4 warn / else log) + OutputValidator (API Key/Token/私钥检测→[REDACTED]) |
| `app/core/providers/ollama_provider.py` | Ollama 本地模型 Provider 适配 (qwen2.5-coder:7b, 8K 上下文) |
| `app/core/providers/vllm_provider.py` | vLLM 推理集群 Provider 适配 (Qwen2.5-14B-Instruct, OpenAI API 兼容格式) |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/tools/registry.py` | 新增 ToolPermissionLevel 四级枚举 (READ_ONLY→NETWORK_READ→WRITE→SHELL) + PermissionManager + SessionPermissionMode (RESTRICTED/TRUSTED/OBSERVE_ONLY)，requires_confirmation 检查 |
| `config.json` | 新增 redis / harness / budget / ollama / vllm 配置段 |
| `app/main.py` | lifespan 中初始化 Redis + 注册 Injection Guard + 设置 harness 参数 |
| `requirements.txt` | 追加 `redis>=5.0.0`, `hiredis` |

### 性能提升

- Embedding 24h 缓存 → **Embedding 计算减少 80%**
- Injection 攻击拦截率 **>95%**（参考 MAESTRO 实测 95.7%）
- RESTRICTED 模式零 Bash 权限 → 安全事件减少
- 本地模型处理简单任务 → **API 成本 -30-50%**

---

## 八、前沿功能探索 🔵

> **前沿研究**：MCP-Cosmos (IBM, arXiv:2605.09131) — World Model 预测式执行 + BYOWM | Google A2A Protocol — Agent-to-Agent 通信标准 | ACP (arXiv:2602.15055) — 去中心化身份+语义意图映射 | AGP (arXiv:2604.15034) — 协议栈顶层 | MAESTRO — 30 时序逻辑属性形式化验证

### 新建文件

| 文件 | 作用 |
|------|------|
| `app/tools/predictive_executor.py` | **MCP-Cosmos 启发** — PredictiveToolExecutor：CBR 案例推理 (SHA256 匹配历史 → 置信度计算 (48h时效衰减+频率因子) → 预测跳过实际执行)，确定性工具分类，写操作后缓存失效 |
| `app/mcp/a2a_bridge.py` | **Google A2A 协议** — A2AServer (FastAPI 路由: /a2a/agent-card 发现 + /a2a/tasks 创建 + 状态查询 + 取消) + A2AClient (aiohttp 异步调用) + AgentCard + TaskStatusMachine (SUBMITTED→WORKING→COMPLETED/FAILED/CANCELED) |
| `app/security/verifier.py` | **MAESTRO 启发** — AgentFSM 有限状态机 (6状态: IDLE/THINKING/EXECUTING_TOOL/WAITING_CONFIRMATION/RESPONDING/ERROR) + 4 条 SafetyProperty 实时检测 (拒绝后不执行/读写隔离/高危必须确认/Tool调用次数<=50) |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `app/main.py` | lifespan 中初始化预测执行器 + A2A Bridge + 安全验证器；Tool 执行路径接入预测检查和状态验证 |

### 性能提升

- 确定性 Tool (Read/Glob/Grep) 缓存命中 → **延迟 -60-80%**
- WOLF 可被其他 Agent 发现和调用 → Agent 协作生态
- 非法状态转移实时拦截 → 安全性增强

---

## 技术-论文映射速查

| 前沿技术 | 来源/论文 | arXiv ID | 应用于 WOLF 模块 |
|----------|----------|----------|-----------------|
| LLM-Wiki Error Book | Tencent 2026 | 2605.25480 | `vector_store/error_book.py` |
| Do We Still Need GraphRAG? | 2026 | 2604.09666 | `vector_store/hybrid_retriever.py` |
| RRF 融合 | 经典 IR 算法 | — | `vector_store/hybrid_retriever.py` |
| Kuzu 图数据库 | Kuzu Team 2024 | — | `vector_store/kg_builder.py` |
| Matryoshka Embedding | OpenAI 2024 | 2205.13147 | `vector_store/embedder.py` |
| ZenBrain 7-Layer Memory | 2026 | 2604.23878 | `memory/cognitive.py` |
| Ebbinghaus 遗忘曲线 | H. Ebbinghaus 1885 | — | `memory/cognitive.py` |
| Sleep Consolidation | Claude Code Auto Dream | — | `memory/consolidation.py` |
| CogniFold 主动记忆 | 2026 | 2605.13438 | `memory/scorer.py` |
| SCG-MEM Schema 约束 | 2026 | 2604.20117 | `memory/scorer.py` |
| AGP 自我进化协议 | Stanford 2026 | 2604.15034 | `evolution/versioned_artifact.py` |
| SkillOpt TextualLR | Microsoft 2026 | — | `evolution/skill_optimizer.py` |
| Agent Skills 开放标准 | Anthropic 2025 | agentskills.io | `skills/agentskills_loader.py` |
| Claude Code Prompt 架构 | Anthropic 2025 | cc-haha-main | `prompt/assembler.py` + `cache.py` + `compact.py` |
| DSPy | Stanford 2024 | — | `prompt/template.py` |
| LangFuse | LangFuse Team | — | `observability/langfuse_client.py` |
| SWE-bench | Princeton 2024 | — | `observability/tracker.py` |
| MAESTRO | Ben Gurion Univ. | — | `middleware/injection_guard.py` |
| MCP-Cosmos World Model | IBM 2026 | 2605.09131 | `tools/predictive_executor.py` |
| Google A2A | Google 2025 | — | `mcp/a2a_bridge.py` |
| ACP 统一通信协议 | 2026 | 2602.15055 | `mcp/a2a_bridge.py` |
| 时序逻辑形式化验证 | 2025 | 2510.14133 | `security/verifier.py` |
