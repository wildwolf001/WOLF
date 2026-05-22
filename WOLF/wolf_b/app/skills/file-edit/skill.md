# File Edit Skill

## Description
文件编辑技能，提供安全的文件读写和修改能力

## Capabilities
- 文件读取（支持大文件分片读取）
- 文件写入
- 文件内容替换
- 目录操作

## Usage
当用户需要读取、创建或修改文件时使用。

## Features
- **安全路径检查**: 防止路径遍历攻击
- **大文件支持**: 超过1MB的文件自动截断
- **原子操作**: 写入前先写临时文件再重命名
- **权限验证**: 检查操作权限

## Tools
- `tools_service.read(path, offset=0, limit=500)`: 读取文件
- `tools_service.write(path, content, append=False)`: 写入文件
- `tools_service.edit(path, old_string, new_string)`: 编辑文件
- `tools_service.list_directory(path)`: 列出目录

## Safety Rules
✅ 允许操作:
- 读取工作目录下的文件
- 写入到工作目录
- 创建新文件

❌ 禁止操作:
- 路径遍历 (`../etc/passwd`)
- 系统目录 (`C:\Windows`, `/etc`)
- 敏感文件

## Examples
- "读取 `README.md` 的前100行"
- "将文件中的 `foo` 替换为 `bar`"
- "列出当前目录下的所有Python文件"