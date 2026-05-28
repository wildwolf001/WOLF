"""
Git Commit Command - Git提交命令
"""
from typing import Dict, Any
from ..registry import Command, CommandType

commit_command = Command(
    name="commit",
    description="Commit changes to git",
    command_type=CommandType.SLASH,
    source="builtin",
    progress_message="Creating commit",
    aliases=["ci"],
)

async def get_commit_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    """获取commit命令的提示"""
    return """
Please commit the current changes to git.

Steps:
1. Review the changes (git status, git diff)
2. Stage the files (git add)
3. Create a commit with a meaningful message

If the user has provided a commit message, use it.
Otherwise, create a descriptive commit message following conventional commits format.
"""
