"""
Tools API Router - 统一的文件操作工具API
"""
from fastapi import APIRouter
from app.tools.file_read_tool import router as file_read_router
from app.tools.file_write_tool import router as file_write_router
from app.tools.file_edit_tool import router as file_edit_router
from app.tools.grep_tool import router as grep_router
from app.tools.glob_tool import router as glob_router
from app.tools.bash_tool import router as bash_router
from app.tools.task_tools import router as task_router
from app.tools.task_output_tools import router as task_output_router
from app.tools.agent_tool import router as agent_router
from app.tools.team_tool import router as team_router
from app.tools.config_tool import router as config_router
from app.tools.repl_tool import router as repl_router
from app.tools.sleep_tool import router as sleep_router
from app.tools.mcp_tool import router as mcp_router
from app.tools.powershell_tool import router as powershell_router
from app.tools.list_tool import router as list_router
from app.tools.info_tool import router as info_router
from app.tools.ask_question_tool import router as ask_question_router
from app.tools.schedule_tool import router as schedule_router
from app.tools.synthetic_tool import router as synthetic_router
from app.tools.todo_tool import router as todo_router

# 创建主路由
router = APIRouter(tags=["tools"])

# 注册子路由
router.include_router(file_read_router, prefix="/file")
router.include_router(file_write_router, prefix="/file")
router.include_router(file_edit_router, prefix="/file")
router.include_router(grep_router, prefix="/search")
router.include_router(glob_router, prefix="/find")
router.include_router(bash_router, prefix="/shell")
router.include_router(task_router, prefix="/tasks")
router.include_router(task_output_router, prefix="/tasks")
router.include_router(agent_router, prefix="/agents")
router.include_router(team_router, prefix="/teams")
router.include_router(config_router, prefix="/config")
router.include_router(repl_router, prefix="/repl")
router.include_router(sleep_router, prefix="/util")
router.include_router(mcp_router, prefix="/mcp")
router.include_router(powershell_router, prefix="/shell")
router.include_router(list_router, prefix="/fs")
router.include_router(info_router, prefix="/fs")
router.include_router(ask_question_router, prefix="/util")
router.include_router(schedule_router, prefix="/schedule")
router.include_router(synthetic_router, prefix="/synthetic")
router.include_router(todo_router, prefix="/todos")