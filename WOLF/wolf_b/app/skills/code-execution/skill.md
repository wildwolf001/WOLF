# Code Execution Skill

## Description
安全执行代码的能力，支持Python和JavaScript

## Capabilities
- Python代码执行
- JavaScript代码执行
- 代码验证和沙箱隔离

## Usage
当用户需要执行代码来验证想法、运行计算或测试算法时使用。

## Features
- **沙箱隔离**: 代码在隔离环境中执行
- **超时保护**: 执行时间限制30秒
- **危险检测**: 阻止危险操作
- **结果返回**: 返回执行输出和错误

## Safety Rules
❌ 禁止:
- 导入os, sys, subprocess等系统模块
- 文件操作
- 网络请求
- 无限循环

✅ 允许:
- math, json, datetime等标准库
- 算法和数据结构
- 数学计算

## Examples
```python
# 计算斐波那契数列
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

[fib(i) for i in range(10)]
```

## Tool
- `execute_code(code, language="python")`: 执行代码