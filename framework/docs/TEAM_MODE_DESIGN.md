# WOLF 2.0 多 Agent 协作设计方案 v4

## 1. 设计原则

1. **编排是结构，不是 prompt** — 不靠 LLM 猜，用确定的规则选模式
2. **集中式 + 分层** — 一个 Orchestrator 管理一切，五层架构
3. **Agent 有记忆** — 每个 Agent 从执行中学习，越用越好
4. **收敛是强制保证** — 不靠运气，超时/死循环/冲突都有硬性兜底

## 2. 总体架构：五层集中式

取 HAWK 的分层设计，加上集中式编排。

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: User Layer                                         │
│   用户输入、反馈、Agent Profile 配置                          │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Workflow Layer                                     │
│   模式匹配引擎: 根据任务类型选编排模式                          │
│   Pipeline 定义: 阶段、Agent 角色、Gate 条件                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Operation Layer (TeamOrchestrator)                 │
│   任务分解 → 分配 → 调度 → 结果聚合                           │
│   所有 Agent 的注册、启动、监控、终止                          │
│   Blackboard 读写、ConvergenceGuard 检查                     │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Agent Layer                                        │
│   Agent 实例 = Profile + Memory + LocalAgentTask            │
│   每个 Agent 独立运行，通过 Blackboard 通信                   │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Resource Layer                                     │
│   工具 (Bash/Read/Write/...)、Sandbox、Git、Memory Store     │
└─────────────────────────────────────────────────────────────┘
```

Layer 3 是核心——**所有编排逻辑在这层**。Layer 4 决定"用什么模式"，Layer 3 执行。

## 3. 编排模式的选择规则

**不是 LLM 选，是确定性规则 + 用户覆盖。**

### 3.1 任务类型自动匹配

```python
PATTERN_RULES = [
    # (条件, 模式, 说明)
    (TaskHas("implement|build|create|写|实现|开发"), "maker-checker",
     "代码生成类 → Maker-Checker (生成→审查→修复)"),
    
    (TaskHas("research|analyze|调查|分析|review|审查") & IsIndependent(),
     "map-reduce", "独立分析类 → MapReduce (并行→聚合)"),
    
    (TaskHas("design|设计|架构") & NeedsImplementation(),
     "sequential", "设计+实现 → Sequential (设计→实现→测试)"),
    
    (TaskHas("security|安全|audit|审计|risk|风险"),
     "consensus", "高风险评估 → Consensus (多 Agent 投票)"),
    
    (ComplexityScore() > 7,
     "hierarchical", "高复杂度 → Hierarchical (Planner→专业Agent→Reviewer)"),
    
    # 默认
    (Always(), "maker-checker", "默认 Maker-Checker"),
]
```

用户可在 UI 中覆盖：
```
┌─ Orchestration ───────────────────────────┐
│  Auto-detected: Maker-Checker             │
│  Override: [Maker-Checker ▾]             │
│  Max iterations: [3]                      │
│  Token budget: [50000]                    │
└───────────────────────────────────────────┘
```

### 3.2 五种模式在 WOLF 中的实现

#### (1) Maker-Checker（默认，代码生成首选）

```
Round 1:
  Coder ──生成代码──▶ Reviewer ──审查──▶ 发现问题 × 3
  Reviewer ──反馈──▶ Coder ──修复──▶ Reviewer ──审查──▶ 通过 ✓
                                                          │
Convergence: 最多 3 轮。同一问题出现 2 次 → 升级用户      │
                                                          ▼
                                                    Tester 跑测试
```

**何时用**: "实现 X"、"写一个 Y"、"修复 Z bug"
**优势**: 质量保证，迭代收敛
**成本**: 每轮 2 次 LLM 调用（Coder + Reviewer），最多 3 轮 = 最多 6 次

#### (2) MapReduce（独立分析首选）

```
          ┌─ Researcher-1: 分析 auth.py ─┐
Orchestrator ─┼─ Researcher-2: 分析 models.py ─┼─▶ Aggregator ──▶ Report
          └─ Researcher-3: 分析 views.py ─┘
                 ↑ 并行，互不依赖
```

**何时用**: "审查所有 Python 文件"、"分析整个项目的安全漏洞"
**优势**: 并行，速度 = 最慢的子任务
**前置条件**: 任务可分解为独立子任务（由 Orchestrator 分解，不是 LLM）

#### (3) Sequential（有明确依赖时）

```
Planner ──▶ Coder ──▶ Reviewer ──▶ Tester
  │            │          │           │
  设计文档    依赖设计    依赖代码    依赖审查通过
  Gate: ✓     Gate: ✓    Gate: ✓    Gate: ✓
```

**何时用**: "先设计再实现然后测试"——依赖链明确
**阶段间传递**: 结构化数据（task_list JSON），不是自然语言

#### (4) Consensus（高风险决策）

```
          ┌─ Reviewer-1 (MiniMax): "Line 47: 硬编码密钥 — CRITICAL"
Task ─────┼─ Reviewer-2 (DeepSeek): "Line 47: 硬编码密钥 — CRITICAL"
          └─ Reviewer-3 (MiniMax):  "Looks fine, but check line 89"

              ↓ Voting: 2/3 say CRITICAL → accepted as CRITICAL
```

**何时用**: "评估这个架构方案"、"判断这个安全漏洞是否真实"
**投票规则**: 多数决（≥2/3）。1/3 → 升级用户。全票通过 → 自动接受
**关键**: 必须用不同模型或不同 prompt，保证多样性

#### (5) Hierarchical（高复杂度任务）

```
                   Planner
                      │
            ┌─────────┼─────────┐
            ▼         ▼         ▼
         Coder-A   Coder-B   Researcher
        (后端API)  (前端UI)  (技术调研)
            │         │         │
            └─────────┼─────────┘
                      ▼
                  Integrator
                      │
                      ▼
                  Reviewer
```

**何时用**: 复杂度 > 阈值（文件数 > 10、跨领域 > 2）
**层级深度**: 最多 2 层（Planner → Workers → Reviewer）

## 4. 状态管理：集中式 Blackboard + 事件日志

### 4.1 Blackboard 数据结构

```python
@dataclass
class Blackboard:
    tasks: Dict[str, TaskState]        # task_id → 当前状态
    ownership: Dict[str, str]          # task_id → agent_id (互斥锁)
    outputs: Dict[str, Any]            # task_id → 产出
    stage: str                         # 当前阶段
    errors: List[ErrorEntry]           # 错误日志
    token_budget: TokenBudget          # 预算追踪

    # 每个 key 有历史版本（事件溯源），方便调试
    history: Dict[str, List[Entry]]
```

### 4.2 互斥锁保证任务不冲突

```python
class TaskOwnership:
    def acquire(self, task_id: str, agent_id: str) -> bool:
        """原子操作：检查+锁定"""
        if task_id in self._owners:
            return False
        self._owners[task_id] = agent_id
        return True
    
    def release(self, task_id: str, agent_id: str):
        """只有 owner 能释放"""
        if self._owners.get(task_id) == agent_id:
            del self._owners[task_id]
```

这消除了"两个 agent 抢同一个任务"的问题——不是靠 LLM prompt 约束，是代码强制。

## 5. 收敛保障

### 5.1 四层兜底

```
Layer 1: 模式级收敛
  Maker-Checker: 最多 3 轮
  Consensus: 最多 3 个 reviewer
  Hierarchical: 最多 2 层

Layer 2: Agent 级收敛
  单 Agent 超时: max_seconds (默认 300s)
  单 Agent 空转: 连续 3 轮无工具调用 → 终止
  单 Agent 轮次: max_turns (配置在 Profile 中)

Layer 3: 反馈级收敛
  同一 task 被同一原因 reject > 2 次 → 不再重试 → 升级用户
  feedback_history 记录每次 reject 的原因摘要
  hamming_distance < 阈值 → 判定为"相同原因"

Layer 4: 资源级收敛
  Token 超预算 → 终止当前阶段 → 聚合已有结果
  并发 Agent 数 > 上限 → 排队
```

### 5.2 升级路径

```
Agent 内部重试失败 → Orchestrator 收到 ConvergenceError
  → 尝试降级: 换一个 Agent 或换模型
  → 降级也失败 → 升级给用户:
      "Task 'implement auth.py' failed after 3 attempts.
       Issue: hardcoded secret keeps appearing.
       Options: [Skip this task] [Give more instructions] [Abort all]"
```

## 6. Agent 自我学习

### 6.1 两阶段学习

```
Phase 1: 即时学习（单次执行内）
  同一个 task 被 reject → Agent 收到 reviewer 反馈
  → 不是重新生成，是带着反馈修正
  → 反馈写入 Blackboard → Agent 下一轮看到

Phase 2: 长期学习（跨执行）
  每次 Agent 任务完成 → LLM Extraction 提炼记忆
  → 写入 agent 专属记忆目录
  → 下次该 Agent 启动时，注入相关记忆
```

### 6.2 记忆结构

```
wolf_data/memory/agents/code-reviewer/
  feedback/
    总是检查sql注入.md          ← 用户反复强调的
    更关注类型安全.md            ← 用户偏好
  project/
    fastapi_jwt项目.md          ← 项目上下文
    auth_py的3个常见问题.md      ← 从执行经验中提取
  user/
    安全标准owasp_top10.md      ← 用户标准
  meta/
    stats.json                  ← 统计: 执行次数、评分、常见问题
```

### 6.3 记忆的使用

Agent 启动时，system_prompt 构建 = 用户定义的 prompt + 注入的记忆上下文：

```python
def build_agent_prompt(profile: AgentProfile, task: str) -> str:
    parts = [profile.system_prompt]
    
    # 注入相关记忆（最多 5 条，按相关性排序）
    memories = profile.get_relevant_memories(task, limit=5)
    if memories:
        parts.append("\n## What you've learned from past work")
        for m in memories:
            parts.append(f"- {m.summary}")
    
    # 注入当前 Blackboard 状态
    parts.append(f"\n## Current state")
    parts.append(f"- Other agents working on: {blackboard.active_tasks()}")
    parts.append(f"- Your task: {task}")
    
    return "\n".join(parts)
```

## 7. 前端设计

### 7.1 Agent 工作台（档案编辑器）

```
┌─ Agents ────────────────────────┬─ Edit: code-reviewer ──────────────┐
│                                 │                                     │
│ [+ New Agent]                   │ Name: [Code Reviewer_____________]  │
│                                 │ Type: [verification ▾]              │
│ 📋 Planner        ⭐8.2  5次   │                                     │
│ 💻 Coder          ⭐7.8 12次   │ System Prompt:                      │
│ 🔍 Code Reviewer  ⭐9.1 23次   │ ┌────────────────────────────────┐ │
│ 🧪 Tester         ⭐6.5  3次   │ │ You are a senior code reviewer │ │
│ 🛡️ Security Audit ⭐8.0  8次   │ │ ...                            │ │
│                                 │ └────────────────────────────────┘ │
│ ───────────────────────         │                                     │
│ Quick Actions:                  │ Tools: ☑Read ☑Grep ☑Glob ☑Bash    │
│ [▶ Test Run]                    │        ☐Write ☐Edit ☐Agent         │
│ [📋 Duplicate]                  │                                     │
│ [🗑️ Delete]                     │ Model: [MiniMax-M2.7 ▾]            │
│                                 │ Max Turns: [5]  Timeout: [120s]    │
│                                 │ Sandbox: [auto ▾]                  │
│                                 │                                     │
│                                 │ Supported Patterns:                 │
│                                 │ ☑ Maker-Checker  ☑ Consensus        │
│                                 │ ☐ MapReduce       ☐ Sequential      │
│                                 │                                     │
│                                 │ Learning Memory (23 tasks, ⭐9.1):  │
│                                 │ 📁 feedback/ (3 files)              │
│                                 │ 📁 project/  (2 files)              │
│                                 │ 📁 user/     (1 file)               │
│                                 │ [📂 Browse] [📊 Stats]              │
│                                 │                                     │
│                                 │ [💾 Save] [▶ Test Run]              │
└─────────────────────────────────┴─────────────────────────────────────┘
```

### 7.2 Team Run 界面

```
┌─ Team Run ──────────────────────────────────────────────────────────┐
│                                                                      │
│  Task: [Implement authentication for FastAPI app...]                 │
│                                                                      │
│  Pattern: Auto-detected → Maker-Checker  [Override ▾]               │
│  Agents:  Coder [💻Coder ▾]  Reviewer [🔍Code Reviewer ▾]           │
│           [+ Add Agent]                                              │
│                                                                      │
│  Budget: [50000 tokens ▾]     Max Iterations: [3]                   │
│                                                                      │
│  ┌─ Progress ───────────────────────────────────────────────────┐   │
│  │  Round 1/3 ●○○                                               │   │
│  │  ┌─ 💻 Coder ─────────────────────────────────────────────┐  │   │
│  │  │ ✅ Generated auth.py (120 lines)                        │  │   │
│  │  │ ✅ Generated test_auth.py (45 lines)                    │  │   │
│  │  │ ✅ 8/8 tests pass                                       │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │  ┌─ 🔍 Code Reviewer ─────────────────────────────────────┐  │   │
│  │  │ ❌ Issue 1: Line 47 hardcoded secret [CRITICAL]         │  │   │
│  │  │ ❌ Issue 2: Missing SQL injection check [WARNING]       │  │   │
│  │  │ → Sent feedback to Coder                                │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                               │   │
│  │  Round 2/3 ●●○                                               │   │
│  │  ┌─ 💻 Coder ─────────────────────────────────────────────┐  │   │
│  │  │ ✅ Fixed: secret → env var                              │  │   │
│  │  │ ✅ Added: SQL injection validation                      │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │  ┌─ 🔍 Code Reviewer ─────────────────────────────────────┐  │   │
│  │  │ ✅ All issues resolved                                  │  │   │
│  │  │ ✅ 10/10 tests pass                                     │  │   │
│  │  │ → APPROVED ✓                                            │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                               │   │
│  │  ✓ Converged in 2 rounds                                     │   │
│  │  Token: 14,230 / 50,000 | Time: 4min 12s                     │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─ Input ────────────────────────────────────────────────────────┐  │
│  │  [Describe your project...                                ]    │  │
│  │                                                   [▶ Execute]  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## 8. 后端实现

### 8.1 模块结构

```
app/agent_profiles/
  __init__.py, registry.py, storage.py, routes.py
  → Agent Profile CRUD + 记忆关联

app/orchestration/
  __init__.py
  orchestrator.py    → TeamOrchestrator (Layer 3 核心)
  patterns.py        → 5 种模式的确定性地实现
  blackboard.py      → 集中式状态 + 任务互斥
  convergence.py     → 四层收敛保障
  matcher.py         → 任务类型 → 模式匹配 (规则引擎)
```

### 8.2 核心类关系

```
TeamOrchestrator (单例)
  ├─ PatternMatcher: 规则匹配选模式
  ├─ Blackboard: 状态管理 + 互斥锁
  ├─ ConvergenceGuard: 多层兜底
  └─ AgentRegistry: Agent Profile 注册表
        └─ AgentInstance (每次 run 创建):
              ├─ AgentProfile (静态配置)
              ├─ AgentMemory (动态学习)
              └─ LocalAgentTask (复用已有基础设施)
```

### 8.3 模式执行器

```python
class PatternExecutor:
    """五种模式的确定性地实现 —— 不是 LLM prompt，是代码"""
    
    async def execute_maker_checker(self, maker, checker, task, board, guard):
        """Maker-Checker: 生成→验证循环，最多 MAX_RETRIES 轮"""
        for round_num in range(1, MAX_RETRIES + 1):
            # Step 1: Maker 生成
            result = await maker.run(task, board)
            guard.check_idle(maker.id, result.turns_without_tools)
            
            # Step 2: Checker 验证
            review = await checker.run(f"Review: {result.output}", board)
            guard.check_idle(checker.id, review.turns_without_tools)
            
            if review.approved:
                return TeamResult(success=True, rounds=round_num, output=result.output)
            
            # Step 3: 检查循环
            if guard.detect_loop(task.id, review.issues):
                raise ConvergenceError("Same issue detected twice, needs human")
            
            # Step 4: 反馈修正
            task.add_feedback(review.issues)
        
        raise MaxRetriesExceeded(f"Failed after {MAX_RETRIES} rounds")
    
    async def execute_map_reduce(self, researchers, aggregator, task, board, guard):
        """MapReduce: 并行分解→独立执行→聚合"""
        subtasks = task.decompose()  # 确定性分解，不是 LLM
        
        # Map: 并行执行
        results = await asyncio.gather(*[
            researcher.run(subtask, board)
            for researcher, subtask in zip(researchers, subtasks)
        ])
        
        # Reduce: 聚合
        return await aggregator.run(results, board)
    
    # ... Sequential, Consensus, Hierarchical 同理
```

### 8.4 收敛检查伪代码

```python
class ConvergenceGuard:
    def detect_loop(self, task_id: str, issues: List[Issue]) -> bool:
        """同一问题出现 ≥2 次 → 死循环"""
    
    def check_idle(self, agent_id: str, turns_without_tools: int) -> bool:
        """连续 3 轮没调工具 → 空转"""
    
    def check_budget(self, used: int, limit: int) -> bool:
        """超预算 → 终止当前阶段"""
    
    def check_ownership(self, task_id: str, agent_id: str) -> bool:
        """任务已被别的 agent 认领 → 冲突"""
```

## 9. Token 预算

```
总预算 (用户可配，默认 50k):
  Orchestrator:     固定 10% (调度逻辑不变，开销小)
  Maker/Worker:     60% (核心工作)
  Checker/Reviewer: 20% (审查比生成便宜)
  Aggregator:       10% (汇总开销小)
  
  → 每个 Agent 启动前检查剩余预算
  → 不足时跳过非关键 Agent，降级为简化流程
```

## 10. 实施计划

### Phase 1: Agent Profile CRUD
- `agent_profiles/` 模块
- UI 编辑器
- 记忆关联（读写 `agents/{id}/` 目录）

### Phase 2: Blackboard + ConvergenceGuard
- 集中式状态管理
- 任务互斥锁
- 循环检测 + 空转检测

### Phase 3: PatternExecutor
- Maker-Checker（默认，最优先实现）
- MapReduce
- Sequential / Consensus / Hierarchical

### Phase 4: Team Run UI
- Agent 选择 + Pattern 选择
- 实时进度展示
- Token 预算显示

---

## 11. 与 Solo 1+N 的共存

```
Solo 模式（不改）:
  主 LLM 自由 spawn agent → 灵活但无收敛保证

Team 模式（新增）:
  确定性的编排引擎 → 有保证但约束更多

用户按需切换。两个模式共享:
  - Agent Profile 注册表
  - 工具注册表
  - Sandbox / Git / Memory
  - LocalAgentTask 执行体
```
