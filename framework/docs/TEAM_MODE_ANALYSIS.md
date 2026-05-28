# WOLF Team 模式当前实现分析

## 1. 发布任务后的完整流程

```
用户输入 → Frontend TeamRun.tsx
  │
  ├─ handleRun() 创建 EventSource
  │   GET /api/stream/team?task=...&agents=coder,reviewer&pattern=auto&budget=50000
  │
  ▼
Backend routes.py: team_stream()
  │
  ├─ 创建 TeamOrchestrator()
  │
  ▼
TeamOrchestrator.run(task, agent_ids, pattern, budget)
  │
  ├─ Step 1: 加载 Agent Profiles
  │     for aid in agent_ids:
  │       profile = registry.get(aid)   ← 从 team_agents.json 读取
  │     → agents = {"coder": AgentProfile, "reviewer": AgentProfile, ...}
  │
  ├─ Step 2: 选编排模式
  │     if pattern != "auto":
  │       mode = pattern          ← 用户指定的
  │     else:
  │       mode = matcher.match(task)   ← 规则引擎匹配
  │     → yield {"type": "orchestration", "pattern": "maker-checker"}
  │
  ├─ Step 3: 创建 PatternExecutor(self._run_single_agent)
  │     ▸ _run_single_agent 是闭包，持有 self = TeamOrchestrator
  │
  ├─ Step 4: 执行编排
  │     PatternExecutor.execute(pattern, agents, task, board, guard)
  │        │
  │        ▼ (假设匹配到 maker-checker)
  │     _maker_checker(agents, task, board, guard)
  │        │
  │        ├─ maker  = agents["coder"]         ← 硬编码 key 查找
  │        ├─ checker = agents["reviewer"]     ← 硬编码 key 查找
  │        │
  │        ├─ Round 1:
  │        │   ├─ maker_result = await _run_agent(coder, task, board)
  │        │   │     │
  │        │   │     ├─ system_prompt = coder.system_prompt + board.snapshot()
  │        │   │     ├─ tools = tool_registry.get_tools_for_agent(coder.tools)
  │        │   │     ├─ llm = LLMService(provider=coder.model or default)
  │        │   │     ├─ result = await llm.complete(messages, tools, max_tokens=4096)
  │        │   │     ├─ while tool_calls and turn < max_turns:
  │        │   │     │    ├─ 执行工具: _execute_tool_call(name, args)
  │        │   │     │    │     ├─ Bash → subprocess.run(cmd, shell=True)
  │        │   │     │    │     ├─ Read → open(path).read()
  │        │   │     │    │     ├─ Write → open(path, 'w').write()
  │        │   │     │    │     ├─ Glob → glob.glob(pattern)
  │        │   │     │    │     └─ Grep → return {"matches": []}  ← 空实现!
  │        │   │     │    └─ llm.complete(msgs + tool_results, tools)
  │        │   │     └─ return {"output": content, "approved": ...}
  │        │   │
  │        │   ├─ checker_result = await _run_agent(checker, "Review: " + maker_output, board)
  │        │   ├─ if approved → return TeamResult(success=True)
  │        │   └─ if not approved → task += feedback → Round 2
  │        │
  │        └─ Max 3 rounds, then fail
  │
  ├─ Step 5: 返回结果
  │     yield {"type": "team_complete", "success": ..., "output": ..., ...}
  │
  ▼
Frontend TeamRun.tsx
  ├─ es.addEventListener("orchestration", ...)
  ├─ es.addEventListener("team_complete", ...)
  └─ 展示结果
```

---

## 2. 每个子系统的逐项分析

### 2.1 工具调用

**现状**：Team 有自己的 `TeamToolRegistry`，但工具实现是 `_execute_tool_call()` 里的简略版本。

**具体问题**：

| 工具 | 问题 |
|------|------|
| Bash | `shell=True` + `cwd` 指向 Team 模块内部拼出的 temp 路径，路径计算依赖 `__file__`，可能不对。无 sandbox 支持 |
| Read | 用相对路径读文件，cwd 未知，大概率读不到 |
| Write | 默认路径 `/tmp/out.txt` 在 Windows 上不存在，写文件可能失败 |
| Grep | **空实现**，永远返回 `{"matches": []}` |
| Glob | 在未知 cwd 下搜索，结果不可预测 |

**与 Solo 的差距**：Solo 的 Bash/Read/Write 工具经过长期调试，有 working_dir、base_path、sandbox 包装。Team 的工具是重新手写的简化版，缺少所有这些。

### 2.2 任务编排

**现状**：`PatternExecutor` 有 5 种模式，但都有严重问题。

| 模式 | 核心问题 |
|------|---------|
| maker-checker | 通过 `agents.get("coder")` 硬编码查找 agent。如果用户选了 id 不为 "coder" 的 agent 当 maker，根本找不到。checker 同理 |
| sequential | 遍历 `list(agents.values())`，按字典序执行。用户选 agent 的顺序被忽略。每个 agent 的输出混入下一个 agent 的输入，5 个 agent 后上下文已经是一坨浆糊 |
| map-reduce | `_decompose_task()` 用正则按换行/编号拆分任务。如果用户的自然语言描述没有编号 → 拆不出 → 退化为单任务 → 和没拆一样 |
| consensus | 依赖 `review.get("approved", False)` ，但 agent 返回的 `approved` 字段是检查输出中是否包含 "CRITICAL" 字符串，完全不靠谱 |
| hierarchical | Planner 的输出用 `_decompose_task()` 拆分，同样是正则拆分，不可靠 |

**致命缺陷**：所有模式都假设 agent 的 `id` 符合约定（"coder"、"reviewer"、"planner"）。用户自定义的 agent 除非恰好叫这些名字，否则编排逻辑会崩溃。

### 2.3 每个 Agent 的工作方式

**现状**：`_run_single_agent()` 是一个独立 LLM 调用循环。

```
Agent 收到任务
  → 调用 LLM (system_prompt + task)
  → LLM 可能返回 tool_calls
  → 执行工具（最多 2 个并行）
  → 把工具结果送回 LLM
  → 循环，直到没有 tool_calls 或超过 max_turns
  → 返回最终文本输出
```

**问题**：

1. **Agent 是瞎子** — 它的 system_prompt 只有 `profile.system_prompt + board.snapshot()`。Board snapshot 只是一行行 `✅ [task-id] title` 的文本。Agent 看不到其他 agent 的实际输出内容，只知道标题。

2. **没有真正的工具链** — 工具执行是同步 subprocess，没有流式输出，没有超时后的 partial result。Agent 调 Bash 跑测试，等 60 秒，然后一次性拿到全部输出。

3. **`approved` 判断荒谬** — 返回值是 `"CRITICAL" not in output.upper()`。这意味着只要输出里不包含大写的 CRITICAL 就算通过。实际 LLM 输出可能包含 "no critical issues found" — 这也算不通过，因为包含了 CRITICAL。

4. **单轮 LLM 对话** — Agent 没有上下文记忆。每轮都是一次全新的 LLM 调用，看不到之前轮次的思考过程。

### 2.4 记忆系统

**现状**：**完全缺失**。

Agent Profile 有 `memory_dir` 字段，但从未被写入或读取。设计文档中描述的"Agent 专属记忆"（每次执行后提取经验）没有实现。

Agent 每次执行都是一张白纸，学不到任何东西。

### 2.5 Agent 间通信

**现状**：仅通过 Blackboard 的文本快照。

```
通信方式 1: Blackboard.snapshot()
  → 生成文本 "## Team Blackboard Snapshot\n✅ [task-1] Implement auth\n🔄 [task-2] Write tests"
  → 注入每个 agent 的 system_prompt
  
通信方式 2: 模式内的数据传递
  → maker-checker: checker 收到 "Review this output: {maker_output[:2000]}"
  → sequential: 下一个 agent 收到 "Previous output:\n{prev[:2000]}\n\nContinue with: {task}"
  → hierarchical: reviewer 收到 "Integrate and review:\n{combined}"
```

**问题**：

1. Blackboard 快照只有标题和状态，Agent 看不到其他 Agent 的**实际产出**
2. 输出截断到 2000 字符，复杂输出被腰斩
3. 没有结构化的 Agent 间消息。Agent A 想对 Agent B 说"你那个 auth.py 第 47 行有问题" — 没有这个能力
4. Blackboard 没有事件通知机制。Agent A 完成了，Agent B 不知道，只能等编排器调度

---

## 3. 异常处理

**现状**：有多层 try/except，但每一层都是吃掉异常继续。

```python
# orchestrator.py:142
except Exception as e:
    return {"output": f"[Agent error: {e}]", "approved": False}

# orchestrator.py:173
except Exception:
    break  # 静默退出工具循环

# orchestrator.py:118
except Exception as e:
    yield {"type": "team_complete", "success": False, "errors": [str(e)]}
```

**问题**：

1. 第一层：Agent LLM 调用失败 → 返回错误字符串冒充输出 → 后续 agent 把这个当正常输出处理
2. 第二层：工具调用失败 → 静默 break → Agent 返回半成品
3. 第三层：编排器异常 → 仅返回错误信息 → 前端显示 "Team Failed" 但没有诊断信息

**缺失的异常处理**：

- 没有 propagation（编排器不知道 agent 内部发生了什么）
- 没有降级策略（agent A 失败 → 换 agent B 重试 → 不需要）
- 没有 partial result（失败了连已完成的输出都丢了）
- 没有日志（异常在 `except` 中消失，没有记录到 log）

---

## 4. 收敛保障

**现状**：`ConvergenceGuard` 定义了四层兜底，但实际调用不完整。

| 层级 | 定义 | 实际调用 |
|------|------|---------|
| Layer 1: 模式级 | `check_retries()` + `record_retry()` | maker-checker 调了 `record_retry`，但 `check_retries` 从未被检查 |
| Layer 2: Agent 级 | `check_idle()` | **从未被调用** |
| Layer 3: 反馈级 | `detect_loop()` | maker-checker 调了，其他模式没调 |
| Layer 4: 资源级 | `check_budget()` | **从未被调用** |

预算设置了 `50000`，但执行过程中没有任何地方检查剩余预算。Agent 可以无限制烧 token。

---

## 5. 评测打分

| 维度 | 分数 | 评语 |
|------|------|------|
| 工具调用 | ⭐⭐ | 6 个工具有 5 个有严重实现问题 |
| 任务编排 | ⭐⭐ | 5 种模式都依赖硬编码 agent id，通用性为零 |
| Agent 执行 | ⭐⭐⭐ | 基本 LLM 调用链可用，但 approved 判断可笑 |
| 记忆系统 | ⭐ | 字段存在，代码零实现 |
| Agent 通信 | ⭐⭐ | 仅文本快照，截断 2000 字符，无事件通知 |
| 异常处理 | ⭐⭐ | 有 try/except 但吃掉所有异常无日志 |
| 收敛保障 | ⭐ | 定义四层，实际上只用了半层 |
| Token 预算 | ⭐ | 设置了但从未检查 |
| 综合 | ⭐⭐ | 骨架完整，细节全缺，不可用于生产 |

---

## 6. 改进路径

### 优先级排序

**P0 — 让 Agent 能正确执行（1-2 天）**
- 修 `_execute_tool_call()`：正确的 cwd，Grep 真实实现，Write 用项目路径
- 修 `approved` 判断：LLM 显式输出 `{"approved": true/false, "issues": [...]}` JSON
- 修模式匹配：不硬编码 agent id，改用 `agent_type` 字段匹配角色

**P1 — 让编排真正工作（2-3 天）**
- 实现真正的预算检查（每次 LLM 调用后扣减）
- 让 `ConvergenceGuard` 全部生效
- 加 partial result 返回

**P2 — 让 Agent 之间有意义的通信（3-5 天）**
- `_run_single_agent` 不返回到编排器再分发，而是通过 Blackboard 发布/订阅
- Agent 完成 → 写 Blackboard → 其他 Agent 的 system prompt 自动包含
- Blackboard 加事件通知 → 依赖满足后自动触发下游 Agent

**P3 — Agent 记忆（5-7 天）**
- 每次 Agent 执行后调用 LLM extraction
- 写入 Agent 专属记忆目录
- 下次启动注入
