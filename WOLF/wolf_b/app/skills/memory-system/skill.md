# Memory System Skill

## Description
记忆系统技能，管理会话记忆和上下文

## Capabilities
- 保存用户偏好记忆
- 保存项目相关记忆
- 保存反馈和改进记忆
- 记忆检索和使用

## Architecture
```
memory/
├── MEMORY.md          # 索引文件（最多200行）
├── user_role.md       # 用户角色偏好
├── feedback_*.md      # 反馈记忆
├── project_*.md      # 项目记忆
└── reference_*.md     # 参考记忆
```

## Usage
当需要记住用户偏好、项目上下文或长期信息时使用此技能。

## Memory Types
1. **User Memory** (`user_*.md`): 用户角色、偏好、协作方式
2. **Feedback Memory** (`feedback_*.md`): 反馈记录和改进
3. **Project Memory** (`project_*.md`): 项目特定信息
4. **Reference Memory** (`reference_*.md`): 外部系统引用

## Tool
- `memory_service.save_memory(session_id, memory_type, content)`: 保存记忆
- `memory_service.get_memory(session_id)`: 获取记忆
- `context_service.get_full_context()`: 获取完整上下文

## Notes
- MEMORY.md 最多200行，超出自动截断
- 每次保存自动更新索引
- 支持按类型检索记忆