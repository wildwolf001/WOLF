# Scheduler Skill

## Description
任务调度技能，用于创建和管理定时任务

## Capabilities
- Cron表达式调度
- 间隔任务调度
- 单次任务执行
- 任务持久化

## Usage
当用户需要创建定时任务、周期性工作或自动化工作流时使用。

## Cron Expression Format
```
分 时 日 月 周
*  *  *  *  *
│  │  │  │  │
│  │  │  │  └── 星期 (0-6, 0=周日)
│  │  │  └───── 月份 (1-12)
│  │  └──────── 日期 (1-31)
│  └─────────── 小时 (0-23)
└──────────────── 分钟 (0-59)
```

## Examples
- `"0 9 * * *"` - 每天9点执行
- `"30 14 * * 1-5"` - 工作日下午2:30执行
- `"0 */2 * * *"` - 每2小时执行

## Tool
- `scheduler_service.create_cron_job(name, prompt, cron_expression)`: 创建Cron任务
- `scheduler_service.create_interval_job(name, prompt, interval_seconds)`: 创建间隔任务
- `scheduler_service.list_jobs()`: 列出所有任务
- `scheduler_service.delete_job(job_id)`: 删除任务

## Notes
- 任务默认持久化到文件
- 调度器在后台运行
- 可以暂停和恢复任务