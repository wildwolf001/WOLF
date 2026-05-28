# WOLF 2.0 — AI Agent 编程平台

自研的多智能体 AI 编程助手平台。从零实现 Agent 调度引擎、混合 RAG 检索、认知记忆系统、Prompt 工程化、自我进化及形式化安全验证。

> **23,600+ 行 Python · React + TypeScript 前端 · Docker 沙箱隔离 · 8 种 LLM Provider 统一接入**
>
|------|------|----------|
| RRF 融合 | 经典 IR |
| Kuzu 图数据库 | Kuzu Team | 
| ZenBrain 7-Layer Memory | 
| Ebbinghaus 遗忘曲线 | 
| AGP 自进化协议 | 
| SkillOpt TextualLR | Microsoft 2026 |
| Agent Skills 标准 |
| MAESTRO | Ben Gurion Univ. | 
| MCP-Cosmos | 
| Google A2A | Google 2025 |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│  wolf_f (React 18 + Vite + Zustand + Tailwind)          │
│  Dashboard · TaskCenter · Memory · Git · Observability  │
└──────────────────────┬──────────────────────────────────┘
                       │ SSE / WebSocket / Hybrid Transport
┌──────────────────────┴──────────────────────────────────┐
│  wolf_b2 (FastAPI + asyncio)                            │
│                                                         │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │ Agent   │ │  Query   │ │  Prompt   │ │  Memory   │ │
│  │ Engine  │ │  Engine  │ │  System   │ │  System   │ │
│  └─────────┘ └──────────┘ └───────────┘ └───────────┘ │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │  RAG    │ │ Evolution│ │ Observable│ │ Security  │ │
│  │ System  │ │ System   │ │ System    │ │ System    │ │
│  └─────────┘ └──────────┘ └───────────┘ └───────────┘ │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │  MCP    │ │ Workflow │ │  Sandbox  │ │  Skills   │ │
│  │  Bridge │ │ Engine   │ │  (Docker) │ │  Loader   │ │
│  └─────────┘ └──────────┘ └───────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 核心特性

### Agent 多智能体调度引擎
主 Agent 通过 AgentTool 动态派生子 Agent，支持前后台并行执行、DAG 任务依赖编排、超时熔断与自动重试。Agent 能力通过 Tool 白名单在 API 级别强制约束，不依赖 Prompt 软约束。

### 混合 RAG 检索系统
Vector (ChromaDB + BGE Embedding) + BM25 稀疏关键词 + 知识图谱 (Kuzu 图数据库，多跳遍历) 三路独立召回，通过 **RRF (Reciprocal Rank Fusion, k=60)** 进行倒数秩融合排序。文档入库时自动抽取实体关系构建知识图谱。

### 五层认知记忆系统
- **Working Memory** — 当前会话上下文窗口
- **Short-term** — SQLite 短期存储，最近 N 天
- **Episodic** — 向量库长期索引
- **Semantic** — 知识图谱抽象规则
- **Procedural** — 高频工作流模板

基于 **Ebbinghaus 遗忘曲线** 对记忆进行时变权重衰减，半衰期按类型差异化设定（用户画像 30 天 / 项目上下文 7 天 / 操作反馈 90 天）。会话结束后自动触发记忆萃取，经由规则引擎 + LLM 双阶段 pipeline 提取值得持久化的信息。

### Prompt 工程化 & A/B 实验
- 条件化 Prompt 组装器 — 根据 Agent 当前启用的 Tool/Skill/会话模式动态注入分层的 System Prompt
- A/B 测试框架 — MD5 一致性哈希分流 + DRAFT → CANARY (10%) → PARTIAL (50%) → FULL_RELEASE 四阶段灰度发布 + 效果下降 >10% 自动回滚
- Section 级缓存 — GLOBAL 层跨会话复用，SESSION 层按需组合

### 自我进化系统 (AGP 协议)
参考 Stanford AGP 协议设计进化 pipeline：
- **SkillOptimizer** — TextualLR + ReflectionMinibatch 算法，累积 20 条轨迹后触发反思优化
- **ToolDescOptimizer** — 自动检测成功率 <70% 的工具描述缺陷并补充反例
- **RolloutManager** — 灰度发布状态机，金丝雀评分低于基线 90% 自动回滚

### AgentFSM 形式化安全验证
基于 MAESTRO 框架，将 Agent 行为建模为 6 状态有限机（IDLE → THINKING → EXECUTING_TOOL → WAITING_CONFIRMATION → RESPONDING → IDLE），定义 14 组合法状态转移与 30 条时序逻辑安全属性，拦截非法状态跳转。

### LLM 可观测性 & 成本治理
- LangFuse 全链路追踪 (Trace → Span → Generation)，不可用自动降级本地内存
- Token 预算管理 — 按会话配额 + 日级预算 (100 万 Token/天) + 80% 阈值预警
- 统一接入 8 种 LLM Provider：MiniMax / DeepSeek / OpenAI / Anthropic / Qwen / Zhipu / Moonshot / Ollama

### MCP & A2A 协议支持
实现 Model Context Protocol 客户端/服务端和 Google A2A Agent 间通信协议，支持 Agent Card 服务发现、任务状态追踪与取消。

### Docker 沙箱隔离
Agent 生成的代码/命令在独立容器中验证执行，项目目录只读挂载，仅 temp 目录可读写，限制网络与系统调用。

---

## 项目结构

```
WOLF2.0/
├── wolf_b2/                    # 后端 (FastAPI + Python)
│   ├── app/
│   │   ├── api/                # REST + WebSocket routes
│   │   ├── bridge/             # 前后端桥接 (SessionRunner, REPL)
│   │   ├── commands/           # 内置命令 (read/write/edit/commit/...)
│   │   ├── compact/            # 上下文压缩 (Reactive/Snip)
│   │   ├── core/               # 配置、Provider (Ollama/vLLM)
│   │   ├── evolution/          # 自我进化 (AGP 协议)
│   │   ├── harness/            # Tool 注册与权限管理
│   │   ├── memory/             # 五层认知记忆
│   │   ├── middleware/         # Auth / Prompt Injection Guard
│   │   ├── mcp/                # MCP + A2A Bridge
│   │   ├── observability/      # LangFuse + Token Budget
│   │   ├── prompt/             # Prompt 工程 (组装/缓存/A/B/版本)
│   │   ├── query/              # 查询引擎 (Token Budget + Stop Hooks)
│   │   ├── sandbox/            # Docker 沙箱
│   │   ├── security/           # AgentFSM 形式化验证
│   │   ├── skills/             # Skill 加载/训练/评估
│   │   ├── tools/              # 工具系统 (Bash/Read/Write/Agent/...)
│   │   ├── transports/         # SSE / WebSocket / Hybrid
│   │   ├── vector_store/       # RAG (ChromaDB + BM25 + 知识图谱)
│   │   └── workflow/           # 工作流引擎
│   ├── docs/                   # 设计文档
│   ├── config.json             # 系统配置
│   └── requirements.txt
│
├── wolf_f/                     # 前端 (React + TypeScript + Vite)
│   └── src/
│       ├── components/         # AgentWorkflow, UnifiedInput, BackendLogs
│       ├── pages/              # Dashboard, TaskCenter, Memory, Git, Settings
│       ├── hooks/              # useAgent, useChat, useTask, useWebSocket
│       ├── services/           # API Service 层
│       └── store/              # Zustand 状态管理
│
└── AI学习路线与前沿方向报告.md
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+ (前端开发)
- Docker (可选，用于沙箱隔离)
- Redis (可选，用于缓存加速)

### 1. 后端启动

```bash
cd wolf_b2

# 创建虚拟环境
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (可选，config.json 已包含默认配置)
cp .env.example .env

# 启动服务
python -m app.main
# 服务运行在 http://localhost:8080
```

### 2. 前端启动

```bash
cd wolf_f

npm install
npm run dev
# 开发服务器运行在 http://localhost:5173
```

### 3. Docker 部署

```bash
cd wolf_b2
docker build -t wolf-backend .
docker run -p 8000:8000 wolf-backend
```

---

## 配置说明

核心配置在 `wolf_b2/config.json`：

| 配置项 | 说明 |
|--------|------|
| `providers` | LLM Provider 配置 (MiniMax/DeepSeek/OpenAI/Anthropic/...) |
| `vector_store` | 向量数据库 (ChromaDB) + Embedding 模型 + 分块策略 |
| `agentic_rag` | 知识图谱构建 + 混合检索 + Error Book 纠错 |
| `prompt_experiments` | A/B 测试 + Feature Flag 灰度 |
| `observability` | LangFuse 追踪 + 成本预算 |
| `redis` | Redis 缓存 (可选) |

默认使用 MiniMax-M2.7 模型，可通过 `current_provider` 切换或设置环境变量 `LLM_PROVIDER`。

---


---

## License

MIT
