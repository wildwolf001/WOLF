# WOLF Team 独立模块搭建方案 v0.6

> **实施状态**: ✅ 全部 8 个 Phase 已完成，45 个 Python 文件，零编译错误
> **实施日期**: 2026-05-26

## 1. 架构：MARVIS 式主 Agent + 六大专项 Agent ✅

```
                        ┌─────────────────────────┐
                        │     🧠 Orchestrator      │
                        │    (主 Agent / 统筹)      │
                        │  - 任务分解与调度          │
                        │  - 结果合成与把关          │
                        │  - 能力路由               │
                        │  - 全局 Blackboard 管理   │
                        └──────────┬──────────────┘
                                   │
          ┌────────────┬───────────┼───────────┬──────────┬────────────┐
          ▼            ▼           ▼           ▼          ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ 📖       │ │ 🔍       │ │ 💡       │ │ 🧪       │ │ 💻       │ │ ✍️        │
    │ 文献     │ │ 分析     │ │ 假设     │ │ 实验     │ │ 代码     │ │ 写作     │
    │ Reader   │ │ Analyst  │ │Hypothesis│ │Experiment│ │  Coder   │ │ Writer   │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 1.1 角色定义

| Agent | 角色 | 输入 | 输出 | 专属能力 |
|-------|------|------|------|---------|
| **Orchestrator** | 主统筹 | 用户任务 | 分解后的子任务 + 最终合成结果 | 任务规划、能力路由、质量把关 |
| **📖 Reader** | 文献阅读 | PDF/URL/搜索词 | 结构化文献摘要、关键发现 | PDF解析、学术搜索、引用提取 |
| **🔍 Analyst** | 研究分析 | 文献摘要集 | 研究空白、趋势、创新方向 | 统计分析、知识图谱、趋势识别 |
| **💡 Hypothesizer** | 假设生成 | 分析结果 | 可验证的研究假设 | 假设推理、因果分析、可行性评估 |
| **🧪 Experimenter** | 实验验证 | 假设 + 数据 | 实验结果、统计分析 | 实验设计、数据处理、可视化 |
| **💻 Coder** | 代码实现 | 算法/方法描述 | 可运行代码 | Python/R、算法实现、API调用 |
| **✍️ Writer** | 论文学术写作 | 所有前期产出 | 结构化论文 (LaTeX/Markdown) | 学术写作、引用管理、格式排版 |

---

## 2. 能力注册机制（不靠 Prompt 约束）✅

### 2.1 核心原则

> **Prompt 只管角色和行为，不管工具。工具通过 API 级别强制过滤。**

**反模式（为什么 prompt 约束不行）：**
```
❌ system_prompt = "你只能用 Bash 和 Read，不能用 Write 和网络..."
   → 加新工具？改所有 Agent 的 prompt
   → LLM 不听话？没办法强制
   → prompt 越长越容易忘
```

**正确模式（API 级别强制）：**
```
✅ Agent Profile 存 tool_whitelist = ["Bash", "Read", "Glob"]
✅ LLM 调用时，tools 参数只传白名单里的工具
✅ LLM 根本不知道其他工具的存在 → 无法调用 → 不需要 prompt 约束
✅ 加新工具 → 注册到 GlobalRegistry → 勾选到 Agent whitelist → 即刻可用
```

### 2.2 工具注册与过滤流程

```
┌─ Global Tool Registry (全局唯一) ──────────────────────────────────┐
│                                                                      │
│  所有工具在这里注册一次:                                              │
│                                                                      │
│  registry.register("Bash",     executor=bash_executor,     schema=...)│
│  registry.register("Read",     executor=read_executor,     schema=...)│
│  registry.register("Write",    executor=write_executor,    schema=...)│
│  registry.register("WebFetch", executor=webfetch_executor, schema=...)│
│  registry.register("arxiv-mcp",executor=arxiv_mcp_exec,    schema=...)│
│  ...                                                                 │
│                                                                      │
│  ★ 新工具只在这里加一次，不碰任何 Agent prompt                        │
└──────────────────────────────────────────────────────────────────────┘

┌─ Agent Profile ─────────────────────────────────────────────────────┐
│                                                                      │
│  {                                                                   │
│    "id": "reader",                                                   │
│    "name": "Reader",                                                 │
│    "role_prompt": "你是文献阅读专家。分析论文，提取关键发现。",        │
│                   ↑ 只描述角色，不提具体工具名                         │
│                                                                      │
│    "tool_whitelist": ["Read", "Glob", "Grep", "WebFetch", "arxiv-mcp"],│
│                      ↑ 这是强制过滤——LLM 调用时只传这些工具            │
│                                                                      │
│    "tool_blacklist": ["Write", "Edit"],  ← 明确禁用（可选）           │
│    "sandbox": "docker",                                              │
│    "model": "minimax"                                                │
│  }                                                                   │
└──────────────────────────────────────────────────────────────────────┘

┌─ 运行时过滤 ────────────────────────────────────────────────────────┐
│                                                                      │
│  def get_tools_for_agent(agent_profile):                             │
│      all_tools = GlobalToolRegistry.list_all()                       │
│      return [t for t in all_tools if t.name in agent_profile.tool_whitelist]│
│                                                                      │
│  # LLM 调用                                                            │
│  llm.complete(                                                       │
│      messages=[...],                                                 │
│      tools=get_tools_for_agent(agent_profile)  ← API 级别强制         │
│  )                                                                   │
│                                                                      │
│  → Reader 的 LLM 调用中 tools = [Read, Glob, Grep, WebFetch, arxiv-mcp]│
│  → Bash 不在里面 → LLM 不知道 Bash 的存在 → 无法调用 Bash            │
│  → 不需要在 prompt 里写 "你不能用 Bash"                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 加新工具的完整流程

```
1. 开发新工具 "DataAnalysis"
   → app_team/tools/definitions/data_analysis.py
   → 实现 execute() 方法

2. 注册到全局
   → GlobalToolRegistry.register("DataAnalysis", executor, schema)
   → 一行代码，不改任何 Agent 文件

3. 给需要的 Agent 勾选
   → UI: Reader 的工具列表勾上 ☑ DataAnalysis
   → 或者: Coder 的工具列表勾上 ☑ DataAnalysis
   → Reader 即刻能用，Coder 也能用，其他 Agent 不知道

4. 不需要做的事情:
   ✗ 不需要改 prompt
   ✗ 不需要改 Skills 定义
   ✗ 不需要重启整个系统
```

### 2.4 Orchestrator 路由（基于能力声明而非 prompt）

```python
class CapabilityRouter:
    """根据任务需求匹配 Agent —— 基于注册表查询，不是 prompt"""

    def __init__(self, global_registry: GlobalToolRegistry, agent_registry: AgentRegistry):
        self.tools = global_registry
        self.agents = agent_registry

    def find_agents_with(self, tool_name: str) -> List[Agent]:
        """哪些 Agent 有这个工具？查 whitelist，不靠 prompt"""
        return [a for a in self.agents.list_all()
                if tool_name in a.tool_whitelist]

    def match_task(self, task: Task) -> Agent:
        """根据任务类型找 Agent（任务类型→需要的工具→有该工具的Agent）"""
        required_tool = TASK_TOOL_MAP.get(task.type)  # {"pdf-parse": "arxiv-mcp"}
        candidates = self.find_agents_with(required_tool)
        return candidates[0] if candidates else None

    def compose_pipeline(self, user_task: str) -> Pipeline:
        """分析任务 → 确定需要的工具链 → 匹配有这些工具的 Agent"""
```

---

## 3. RAG 集成 ✅

### 3.1 RAG 的必要性

科研任务的核心数据是**文献、实验数据、领域知识**。不用 RAG：
- 每篇论文塞进上下文 → token 爆炸
- LLM 幻觉引用 → 论文不可信
- 实验结果无法追溯 → 无法复现

### 3.2 Team RAG 架构

```
┌─ RAG 层 ──────────────────────────────────────────────────────┐
│                                                                │
│  ┌─ Vector Store (ChromaDB) ──────────────────────────────┐   │
│  │                                                          │   │
│  │  Collection: papers        ← 文献全文 (PDF chunked)      │   │
│  │  Collection: experiments   ← 实验记录 (结构化)           │   │
│  │  Collection: domain_knowledge ← 领域概念/定义/方法       │   │
│  │  Collection: agent_memory  ← Agent 专属记忆              │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ Embedding 服务 ────────────────────────────────────────┐   │
│  │  MiniMax Embedding / text-embedding-3-small              │   │
│  │  或本地 BGE-M3 (离线，无 API 费用)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ 文档处理管线 ──────────────────────────────────────────┐   │
│  │  PDF → pymupdf extract text → chunk (semantic split)     │   │
│  │       → embed → store in papers collection              │   │
│  │  文献更新 → 增量索引 (git commit hook 触发)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ 检索接口 ──────────────────────────────────────────────┐   │
│  │  query → embed → vector search (top-k)                   │   │
│  │       → rerank (cross-encoder) → final top-n             │   │
│  │       → 注入 Agent 的 system prompt                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 每个 Agent 的 RAG 使用

| Agent | RAG 查询内容 | 注入时机 |
|-------|-------------|---------|
| Reader | "相关工作的最新进展" | 阅读论文前，先检索背景知识 |
| Analyst | "该领域的研究空白和趋势" | 分析时检索已有综述和方法 |
| Hypothesizer | "类似问题的已有假设和验证方法" | 生成假设前验证新颖性 |
| Experimenter | "该实验设计的统计方法" | 设计实验时检索最佳实践 |
| Coder | "类似算法的实现" | 写代码前检索现有实现 |
| Writer | "该期刊的格式要求和常用表达" | 写作时参考学术风格 |

---

## 4. 强制隔离：API 级别而非 Prompt 级别 ✅

### 4.1 三层隔离

```
┌─ 隔离层 1: LLM API tools 参数 ─────────────────────────────────────┐
│                                                                      │
│  Reader 的 LLM 调用:                                                  │
│  llm.complete(..., tools=[Read, Glob, Grep, WebFetch, arxiv-mcp])   │
│                                                                      │
│  Coder 的 LLM 调用:                                                   │
│  llm.complete(..., tools=[Read, Write, Edit, Bash, Glob, Grep])     │
│                                                                      │
│  → LLM 根本不知道其他工具的存在                                        │
│  → 这个隔离是 OpenAI function calling 协议级别的，不是 prompt 建议    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ 隔离层 2: ToolExecutor 二次校验 ────────────────────────────────────┐
│                                                                      │
│  async def execute_tool(agent, tool_name, args):                     │
│      if tool_name not in agent.tool_whitelist:                       │
│          raise ForbiddenError(f"{agent.id} cannot use {tool_name}")  │
│      return await GlobalToolRegistry.execute(tool_name, args, agent.sandbox)│
│                                                                      │
│  → 即使 LLM 幻觉出一个不在 tools 参数里的工具名，这里也会拦截          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ 隔离层 3: Sandbox 物理隔离 ────────────────────────────────────────┐
│                                                                      │
│  Reader 的 Bash → 容器 reader-{session}                             │
│  Coder 的 Bash  → 容器 coder-{session}                              │
│                                                                      │
│  → 同样的工具名，在不同的文件系统和网络环境中运行                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 三种资源的统一注册

Tool、Skill、MCP 在注册中心统一管理，但用法不同：

| 资源类型 | 是什么 | 注册到 | 如何分配给 Agent | Agent 如何感知 |
|---------|--------|--------|-----------------|---------------|
| **Tool** | 原子操作 (Bash, Read, Write...) | GlobalToolRegistry | whitelist 勾选 → tools 参数传给 LLM | LLM function calling 中可见 |
| **Skill** | 预定义的 prompt 模板 + 可选的工具链 | SkillRegistry | whitelist 勾选 → 注入 system prompt | system prompt 中的 "可用技能" 段 |
| **MCP** | 外部服务连接 (arxiv, github...) | MCPRegistry | whitelist 勾选 → 同上 | 同上 |

**关键**：三种资源的隔离机制完全一样——Agent Profile 里的 whitelist 是唯一真相。

### 4.3 创建 Agent 时的配置界面

```
┌─ Agent: Reader ───────────────────────────────────────────────┐
│                                                                │
│  Role Prompt:                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 你是学术文献阅读专家。你的职责:                              │ │
│  │ 1. 解析 PDF 论文，提取核心贡献、方法、实验结果              │ │
│  │ 2. 生成结构化摘要（方法、发现、局限、引用）                 │ │
│  │ 3. 提取引用并关联已有文献库                                 │ │
│  │                                                          │ │
│  │ ★ prompt 里不提任何具体工具名，只描述角色                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Tool Whitelist (API 级别强制):                                │
│  ┌─ 全局工具 ────────────────────────────────────────────┐   │
│  │ ☑ Read        ☑ Glob      ☑ Grep      ☑ WebFetch    │   │
│  │ ☐ Write       ☐ Edit      ☐ Bash                    │   │
│  │ ☑ arxiv-mcp   ☑ scholar-mcp  ☐ python-mcp           │   │
│  │ [↻ Refresh Tools]                                     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  Skill Whitelist:                                              │
│  ┌─ 可用 Skills ─────────────────────────────────────────┐   │
│  │ ☑ pdf-parse        ☑ paper-summarize                  │   │
│  │ ☑ citation-extract  ☐ experiment-design               │   │
│  │ [↻ Refresh Skills]                                     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ★ 新工具/Skill 出现 → 刷新列表 → 勾选 → 即刻生效               │
│  ★ 不修改 prompt                                               │
└────────────────────────────────────────────────────────────────┘
```

### 4.4 "加新工具"的全流程（零 prompt 修改）

```
1. 开发: app_team/tools/definitions/data_analysis.py
2. 注册: GlobalToolRegistry.register("DataAnalysis", ...)
3. UI: 所有 Agent 配置页出现 ☐ DataAnalysis
4. 勾选: Reader ☑ DataAnalysis, Coder ☑ DataAnalysis
5. 生效: Reader 和 Coder 的 LLM 调用中 tools=[..., DataAnalysis]
6. 不需要: ✗改prompt ✗改skills ✗重启
```

---

## 5. Agent 自我学习与进化系统 ✅

### 5.1 学习的闭环

```
Agent 第 N 次执行任务
  │
  ├─ 1. 任务开始: 加载 Agent 专属记忆 → 注入 system prompt
  │     "你在过去的 23 次审查中，最常见的发现是: 硬编码密钥(3次)、SQL注入(2次)"
  │     "用户偏好: 使用 podman 而非 Docker"
  │     "本项目: FastAPI + JWT + PostgreSQL"
  │
  ├─ 2. 任务执行: Agent 带着记忆工作
  │
  ├─ 3. 收到反馈: Orchestrator 汇总 Reviewer 的 review + Tester 的结果
  │     {
  │       "approved": false,
  │       "issues": [{"file": "auth.py:47", "severity": "CRITICAL", "desc": "硬编码密钥"}],
  │       "test_results": {"passed": 8, "failed": 2}
  │     }
  │
  ├─ 4. LLM 提取经验 (Learning Extraction):
  │     prompt = f"Agent {agent_id} 执行了任务: {task_summary}。反馈: {feedback}。
  │               与已有记忆对比: {existing_memories}。
  │               从这次经验中提取值得保留的新记忆，去重后返回。"
  │     → 返回: [
  │         {type: "feedback", content: "检查 auth.py 时务必扫描环境变量和硬编码密钥"},
  │         {type: "project", content: "FastAPI 项目中 jwt secret 必须从环境变量读取"}
  │       ]
  │
  ├─ 5. 写入 Agent 专属记忆
  │     → memory/agents/reviewer/feedback/2026-05-26-hardcoded-secret.md
  │     → memory/agents/reviewer/project/fastapi-jwt-security.md
  │     → memory/agents/reviewer/meta/stats.json (更新指标)
  │
  ├─ 6. 记忆压缩 (达到阈值时触发):
  │     feedback/ 目录下 > 5 条同类记忆 → LLM 合并为一条精炼规则
  │     "在 Python Web 项目中，必须检查: 1)硬编码密钥 2)SQL注入 3)CSRF..."
  │
  └─ 7. 更新 Agent 指标
        total_tasks += 1, success_rate 重算, avg_score 更新
        specialties 可能新增: ["FastAPI安全审查"]
```

### 5.2 记忆存储结构

```
wolf_data/team_memory/agents/{agent_id}/
  ├── identity.json              ← Agent 身份快照 (指标、版本)
  ├── feedback/                  ← 从用户纠正中学到的
  │   ├── check-sql-injection.md
  │   ├── use-podman-not-docker.md
  │   └── hardcoded-secret-check.md
  ├── project/                   ← 项目上下文
  │   ├── fastapi-jwt-project.md
  │   └── common-auth-patterns.md
  ├── experience/                ← 从成功/失败案例中学到的
  │   ├── success-pattern-a.md
  │   └── failure-pattern-b.md
  ├── meta/
  │   ├── stats.json             ← {total_tasks, success_rate, avg_score, specialties, ...}
  │   └── evolution.json         ← 版本历史 (每次显著改进记录)
  └── compressed/                ← 合并压缩后的精炼记忆
      └── python-web-security-rules.md
```

### 5.3 Agent 能力树的动态扩展

```
Agent 创建时 (v1):
  └─ 基础能力 (profile 中定义的 skills)

执行 10 次后 (v2):
  ├─ 基础能力
  ├─ 从反馈中学会的: SQL注入检查、硬编码密钥检测  ← 自动添加
  └─ 从成功中总结的: 最优代码审查顺序               ← 自动添加

执行 50 次后 (v3):
  ├─ 基础能力
  ├─ 反馈学会的: 8 条
  ├─ 成功模式: 5 条
  ├─ 项目特化: FastAPI安全模式、JWT最佳实践        ← 自动提取
  └─ 用户偏好: podman > docker, 类型注解必须          ← 自动学习
```

能力树不是预设的，是**长出来的**。用户在 UI 中看到 Agent 的能力树随时间扩展：

```
Agent: code-reviewer ⭐4.2  47 tasks
  ├─ 🔍 基础审查 (built-in)
  ├─ 🔍 SQL注入检测 (learned, task #3)
  ├─ 🔍 硬编码密钥检测 (learned, task #1)
  ├─ 📊 FastAPI安全 (learned, task #12)
  └─ 📊 CSRF检查 (learned, task #28)
```

### 5.4 跨 Agent 知识共享

Agent 学到的经验不仅自己用，还可以**共享给同类型 Agent**：

```
Reader-1 学会: "这篇论文的引用格式是 APA 7th"
  → 写入 team_memory/shared/apa-citation.md
  → Reader-2, Writer 下次执行时自动加载这条共享记忆

但是 Coder 不需要这段记忆 → Agent 启动时只注入自己 role 相关的共享记忆
```

共享规则：
- 同角色 Agent 自动共享所有项目级和用户级记忆
- 不同角色 Agent 只共享 user 级记忆（偏好、风格）
- Agent 专属的 feedback 级记忆不共享（那是个人经验）

### 5.5 持续学习 vs 灾难性遗忘

```
防止灾难性遗忘的机制:

1. 记忆不是无限累加 → max 20 条主动记忆
2. 达到 20 条 → 触发压缩: LLM 将相似记忆合并为精炼规则
3. 压缩保留最重要的，丢弃过时的:
   - 最近 30 天内使用过的 → 保留
   - 最近 90 天未使用 → 归档到 compressed/
   - 项目已删除/变更的记忆 → 标记 obsolete

4. Agent 可以"重置学习" → 清空 feedback/ 和 experience/，保留 built-in skills
```

### 5.6 学习效果量化

```
code-reviewer 学习曲线:
  执行次数  |  成功率  |  avg_turns  |  specialties
  ──────────────────────────────────────────────────
  1-5      |  60%     |  4.2        |  []
  6-15     |  75%     |  3.1        |  [SQL注入, 硬编码密钥]
  16-30    |  85%     |  2.5        |  [FastAPI安全, CSRF]
  31-47    |  92%     |  2.0        |  [OWASP-Top10, 类型安全]

观测指标:
  - 成功率上升 32%
  - 平均 turn 数下降 52%（更快完成任务）
  - 审查覆盖范围从 2 类扩展到 6 类
```

---

## 6. 以"科研论文产出"为例的完整流程 ✅

### 6.1 启动

```
用户输入:
  "分析这3篇关于抗衰老的论文(paper1.pdf, paper2.pdf, paper3.pdf)，
   找出当前研究空白和创新方向，提出可验证的假设，
   设计实验验证，最后写一篇综述论文"

Orchestrator 分析 → 构建 Pipeline
```

### 6.2 流水线执行

```
Phase 1: 📖 Reader (3个并行实例)
  ├─ Reader-1 → paper1.pdf → 结构化摘要
  ├─ Reader-2 → paper2.pdf → 结构化摘要
  └─ Reader-3 → paper3.pdf → 结构化摘要
  ↓
  输入到 RAG: "抗衰老领域最新进展" → 补充背景知识
  ↓
  输出: 3份结构化文献摘要 (方法、发现、局限)

Phase 2: 🔍 Analyst (1个实例)
  ├─ 输入: 3份摘要 + RAG检索的领域趋势
  ├─ 分析: 共性方法、矛盾发现、研究空白
  └─ 输出: 分析报告

Phase 3: 💡 Hypothesizer (1个实例)
  ├─ 输入: 分析报告 + RAG验证新颖性
  ├─ 生成: 2-3个可验证假设
  ├─ 评估: 每个假设的可行性、新颖性、影响力
  └─ 输出: 假设清单 + 验证方案

Phase 4: 🧪 Experimenter + 💻 Coder (并行)
  ├─ Experimenter: 设计实验方案 → 确定统计方法
  ├─ Coder: 实现算法 → 跑数据 → 生成图表
  └─ 输出: 实验结果 + 代码 + 图表

Phase 5: ✍️ Writer (1个实例)
  ├─ 输入: 所有前期产出
  ├─ 写作: 引言→方法→结果→讨论→结论
  ├─ 格式: LaTeX + 参考文献 (BibTeX)
  └─ 输出: 完整论文 draft

Phase 6: 🧠 Orchestrator 最终审查
  ├─ 检查: 逻辑连贯、引用正确、图表规范
  ├─ 可选的 Reviewer Agent 交叉检查
  └─ 输出: 最终论文
```

### 6.3 每个 Agent 的工作状态（前端显示）

```
┌─ Team: 抗衰老研究综述 ───────────────────────────────────────────────┐
│                                                                       │
│  Pipeline: Reader×3 → Analyst → Hypothesizer → Experiment+Coder → Writer │
│  Phase: 4/6 · Token: 45,230/100,000 · Elapsed: 12min                   │
│                                                                       │
│  ✅ 📖 Reader-1  Done     paper1.pdf → 摘要 (2,340 tokens)             │
│  ✅ 📖 Reader-2  Done     paper2.pdf → 摘要 (1,890 tokens)             │
│  ✅ 📖 Reader-3  Done     paper3.pdf → 摘要 (2,100 tokens)             │
│  ✅ 🔍 Analyst   Done     3空白 + 2趋势方向 (3,450 tokens)             │
│  ✅ 💡 Hypothesizer Done  3假设 [细胞自噬, mTOR, NAD+] (4,120 tokens)  │
│                                                                       │
│  🔄 🧪 Experimenter Working ───────────────────────────────────────  │
│  │  Turn 4/8 · Tool: Bash (Rscript analysis.R)                      │
│  │  Experiment: mTOR inhibition on senescent cells                   │
│  │  Progress: ████████████░░░░░░░░ 60%                              │
│  └──────────────────────────────────────────────────────────────────  │
│                                                                       │
│  🔄 💻 Coder Working ──────────────────────────────────────────────  │
│  │  Turn 6/10 · Tool: Write (mtor_model.py)                         │
│  │  Model accuracy: 0.87 → 0.91 (improving)                          │
│  │  Progress: ████████████████░░░░ 75%                               │
│  └──────────────────────────────────────────────────────────────────  │
│                                                                       │
│  ⏳ ✍️ Writer   Queued   等待实验 + 代码完成...                        │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 7. 完整目录结构 ✅

```
app_team/
  __init__.py
  main.py

  config/
    __init__.py
    settings.py                    ← TeamSettings (独立配置)
    runtime.py

  core/
    __init__.py
    types.py                       ← AgentType, TaskType, PipelineStage
    errors.py
    events.py                      ← SSE 事件类型

  # ── 能力注册中心 ──
  capability/
    __init__.py
    registry.py                    ← CapabilityRegistry (全局能力注册表)
    router.py                      ← CapabilityRouter (任务→Agent匹配)
    declaration.py                 ← AgentCapability (每个Agent的能力声明)

  # ── Agent 系统 ──
  agent/
    __init__.py
    profile.py                     ← AgentProfile + AgentRegistry (CRUD)
    identity.py                    ← AgentIdentity (持久化实体)
    runner.py                      ← AgentRunner (启动Agent执行)
    lifecycle.py                   ← AgentLifecycle
    guardrails.py                  ← Guardrails (行为约束)

  # ── 沙箱 ──
  sandbox/
    __init__.py
    manager.py                     ← SandboxPool (容器池)
    docker.py                      ← DockerSandbox
    host.py                        ← HostSandbox (fallback)

  # ── 记忆系统 ──
  memory/
    __init__.py
    store.py                       ← AgentMemoryStore
    extraction.py                  ← 经验提取
    injection.py                   ← 记忆注入 prompt

  # ── RAG 系统 ──
  rag/
    __init__.py
    vectordb.py                    ← ChromaDB 管理
    embedding.py                   ← Embedding 服务封装
    ingestion.py                   ← 文档摄入 (PDF→chunk→embed→store)
    retrieval.py                   ← 检索 + rerank
    collections.py                 ← Collection 管理

  # ── 编排系统 ──
  orchestration/
    __init__.py
    orchestrator.py                ← TeamOrchestrator
    pipeline.py                    ← Pipeline 构建 + 执行
    stage.py                       ← PipelineStage (单个阶段的执行)
    blackboard.py                  ← Blackboard
    convergence.py                 ← ConvergenceGuard

  # ── Skills 系统 ──
  skills/
    __init__.py
    registry.py                    ← SkillRegistry (Agent级别的Skill注册)
    loader.py                      ← SkillLoader (从文件加载Skill定义)
    trigger.py                     ← SkillTrigger (自动触发逻辑)
    definitions/                   ← Skill 定义文件
      reader/pdf_parse.md
      reader/citation_extract.md
      analyst/trend_detect.md
      writer/paper_format.md
      ...

  # ── 工具系统 ──
  tools/
    __init__.py
    registry.py                    ← ToolRegistry (Agent级别的工具注册)
    executor.py                    ← ToolExecutor
    schemas.py
    definitions/
      __init__.py
      bash.py / read.py / write.py / edit.py / glob.py / grep.py

  # ── MCP 系统 ──
  mcp/
    __init__.py
    manager.py                     ← MCPManager (Agent级别的MCP连接管理)
    client.py                      ← MCPClient
    registry.py                    ← MCPRegistry

  # ── 执行引擎 ──
  engine/
    __init__.py
    query_engine.py                ← TeamQueryEngine
    context.py                     ← ContextBuilder
    token_budget.py

  # ── 流式输出 ──
  streaming/
    __init__.py
    multiplexer.py                 ← SSEMultiplexer

  # ── API 层 ──
  api/
    __init__.py
    agents.py                      ← Agent CRUD
    run.py                         ← Team Run SSE
    pipeline.py                    ← Pipeline 状态查询
    rag.py                         ← RAG 管理 (文档上传/索引)
    metrics.py

  # ── 存储 ──
  storage/
    __init__.py
    agent_store.py
    memory_store.py
    metrics_store.py
```

---

## 8. 工具/Skills/MCP 注册与隔离流程 ✅

```
┌─ 全局注册（只做一次）──────────────────────────────────────────────┐
│                                                                      │
│  GlobalToolRegistry.register("DataAnalysis", executor, schema)       │
│  SkillRegistry.register("paper-review", skill_template)              │
│  MCPRegistry.register("arxiv-mcp", mcp_server_config)                │
│                                                                      │
│  ★ 新资源只在这里加一次                                               │
└──────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Agent 配置（用户操作）─────────────────────────────────────────────┐
│                                                                      │
│  Agent "Reader":                                                     │
│    role_prompt = "你是文献阅读专家..."    ← 只管角色，不提工具名       │
│    tool_whitelist = [Read, Glob, Grep, WebFetch, arxiv-mcp]          │
│    skill_whitelist = [pdf-parse, paper-summarize, citation-extract]  │
│                                                                      │
│  Agent "Coder":                                                      │
│    role_prompt = "你是代码实现专家..."    ← 只管角色                  │
│    tool_whitelist = [Read, Write, Edit, Bash, Glob, Grep]            │
│    skill_whitelist = [code-generate, unit-test]                      │
│                                                                      │
│  ★ Reader 和 Coder 的 whitelist 完全独立                              │
└──────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ 运行时强制（代码自动处理）──────────────────────────────────────────┐
│                                                                      │
│  当 Orchestrator 启动 Reader:                                        │
│                                                                      │
│  # Step 1: 从 whitelist 构建 tools 参数                              │
│  tools = [t.schema for t in GlobalToolRegistry.all()                 │
│           if t.name in reader.tool_whitelist]                        │
│  # → [Read.schema, Glob.schema, Grep.schema, WebFetch.schema,       │
│  #    arxiv-mcp.schema]                                              │
│                                                                      │
│  # Step 2: 注入 Skill 模板到 system_prompt                           │
│  skills_prompt = "\n".join(s.template for s in SkillRegistry.all()   │
│                           if s.name in reader.skill_whitelist)       │
│  system_prompt = reader.role_prompt + skills_prompt                  │
│                                                                      │
│  # Step 3: LLM 调用 —— 只传白名单工具                                │
│  result = await llm.complete(                                        │
│      system=system_prompt,                                           │
│      messages=[...],                                                 │
│      tools=tools  ← API 级别强制，Reader 的 LLM 只看到这5个工具       │
│  )                                                                   │
│                                                                      │
│  # Step 4: 工具执行时二次校验                                        │
│  async def execute(agent, tool_name, args):                           │
│      if tool_name not in agent.tool_whitelist:  ← 代码强制           │
│          return error("Forbidden")                                   │
│      return await tool.executor(args, agent.sandbox)                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```



## 9. 需要确认的议题

1. **RAG 的 Embedding 模型**: 本地 BGE-M3（免费离线）vs MiniMax Embedding API（方便但有成本）？
2. **文献 PDF 解析**: 用 pymupdf + 自定义 chunker，还是接现有的开源工具（如 paper-qa）？
3. **MCP 服务器是预配置还是用户自定义？** arxiv-mcp 这种科研常用的可以内置
4. **Team 和 Solo 共享 LLM API key 还是独立 .env.team？**
5. **前端需不需要"Skills 编辑器"？** 即用户可以给 Agent 写新的 Skill 定义文件
