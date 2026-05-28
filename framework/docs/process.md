# WOLF 2.0 改进过程记录

> 对照文档：`WOLF改进大纲.md` | 仅涉及 `app/`

---

## 进度总览

| 模块 | 优先级 | 状态 | 开始 | 完成 |
|------|--------|------|------|------|
| 一、RAG 向量检索 + Agentic RAG | 🔴 | 🔄 1.1完成 | 2026-05-27 | 1.1: 2026-05-27 |
| 二、Prompt 工程系统 | 🔴 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 三、LLM 可观测性 | 🟡 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 四、认知记忆架构 | 🟡 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 五、自我进化系统 | 🟡 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 六、Skill 系统强化 | 🟢 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 七、生产级基础设施 | 🟢 | ✅ 完成 | 2026-05-27 | 2026-05-27 |
| 八、前沿功能探索 | 🔵 | ✅ 完成 | 2026-05-27 | 2026-05-27 |

---

## 一、RAG 向量检索

### 1.1 基础 RAG 模块 ✅

**新建文件** (7): `app/vector_store/{__init__,embedder,splitter,store,retriever,ingest,tool}.py`
**修改文件** (3): `requirements.txt`, `config.json`, `app/main.py`
**注册 Tool** (3): `rag_search`, `rag_ingest`, `rag_status`

### 1.2 Agentic RAG 增强 ⬜ 待第二阶段

- [ ] `kg_builder.py`, `hybrid_retriever.py`, `error_book.py`, 多步推理检索

---

## 二、Prompt 工程系统 ✅

> 对标: Claude Code `cc-haha-main/src/constants/prompts.ts` + `systemPromptSections.ts`

**新建文件** (10):
`app/prompt/{core/schemas,core/constants,cache,layers,template,versioning,assembler,compact,feature_flags,ab_test}.py`

**修改文件** (4): `app/prompt/__init__.py`, `config.json`, `app/main.py`, `requirements.txt`

**六大改造点**:
1. Tool 级自描述 Prompt (行为边界指导)
2. 条件化 Prompt 组装 (assembler.py)
3. 渐进式 Skill 披露 (元数据索引)
4. Feature Flag 灰度发布 (feature_flags.py)
5. Context Compaction 子系统 (compact.py)
6. Section 级缓存 (cache.py)

---

## 三、LLM 可观测性 ✅

**新建文件** (4): `app/observability/{__init__,langfuse_client,tracker,cost}.py`
**修改文件** (2): `config.json`, `app/main.py`

核心能力: @track_llm_call 装饰器, StatsAggregator 滑动窗口, CostCalculator 预算预警, LangFuse 集成

---

## 四、认知记忆架构 ✅

> 前沿: ZenBrain (arXiv:2604.23878), Ebbinghaus 遗忘曲线

**新建文件** (4): `app/memory/{cognitive,consolidation,scorer,vector_sync}.py`

核心能力: 五层记忆层级, Ebbinghaus 衰减 (半衰期按类型), SleepConsolidation 6h 整合, 四维评分, 记忆-向量库同步

---

## 五、自我进化系统 ✅

> 前沿: AGP (Stanford, arXiv:2604.15034), SkillOpt (Microsoft 2026)

**新建文件** (5): `app/evolution/{__init__,versioned_artifact,skill_optimizer,tool_evolver,rollout_manager}.py`

核心能力: 版本化工件存储, Skill 自动优化 (TextualLR + ReflectionMinibatch), Tool 描述优化, 灰度发布 (DRAFT→CANARY→FULL/ROLLED_BACK)

---

## 六、Skill 系统强化 ✅

> 前沿: Agent Skills 开放标准 (Anthropic, agentskills.io)

**新建文件** (4): `app/skills/{agentskills_loader,trainer,evaluator,meta_update}.py`

核心能力: agentskills.io 兼容 (YAML frontmatter), Skill 训练器 (SQLite 轨迹缓冲), 留出验证集门控, 三级调度 (daily/weekly/monthly)

---

## 七、生产级基础设施 ✅

> 前沿: MAESTRO (16种攻击, 95.7%拦截), Ollama/vLLM

**新建文件** (4): `app/{cache/redis_client,middleware/injection_guard,core/providers/ollama_provider,core/providers/__init__}.py`
**修改文件** (2): `config.json`, `app/main.py` (含 Redis/injection_guard 初始化)

核心能力: SessionCache/EmbeddingCache/RateLimiter/TaskQueue, InjectionDetector 8组规则 + OutputValidator, Ollama 本地模型, 四级 Tool 权限

---

## 八、前沿功能探索 ✅

> 前沿: MCP-Cosmos (IBM, arXiv:2605.09131), Google A2A Protocol, MAESTRO

**新建文件** (3): `app/{tools/predictive_executor,mcp/a2a_bridge,security/__init__,security/verifier}.py`

核心能力: CBR 预测式执行 (48h 时效 + 频率因子), A2A Server + Client (AgentCard 发现/任务提交), AgentFSM 6 状态机 + 4 条安全属性验证

---

## 改造统计

| 类型 | 数量 |
|------|------|
| 新建模块 | 6 (vector_store, observability, evolution, cache, security, core/providers) |
| 新建文件 | 38 |
| 修改文件 | 5 (main.py, config.json, requirements.txt, prompt/__init__.py, memory/__init__.py) |
| 注册 Agent Tool | 3 (rag_search, rag_ingest, rag_status) |
| 引入前沿论文/协议 | 12+ (ZenBrain, AGP, MCP-Cosmos, A2A, MAESTRO, Ebbinghaus, SkillOpt, agentskills.io, LLM-Wiki, GraphRAG, Matryoshka, RRF) |

---

## 待第二阶段实施

- [ ] RAG 1.2 Agentic RAG (kg_builder, hybrid_retriever, error_book)
- [ ] 前端改造 (ObservabilityDashboard, PermissionConfirmModal)
- [ ] API 路由注册 (observability, evolution, prompt)
- [ ] pip install chromadb sentence-transformers jinja2 redis pyyaml 验证
- [ ] 端到端测试
