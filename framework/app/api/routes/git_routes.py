"""
Git Route — Visual git management for WOLF sessions
"""
import os
import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException

from ...utils.logging import get_logger

router = APIRouter()
logger = get_logger("git")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _git(*args) -> subprocess.CompletedProcess:
    """Run a git command from project root"""
    return subprocess.run(
        ["git"] + list(args),
        cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=30
    )


def _check_git_available() -> bool:
    """Check if git is available and repo exists"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _ensure_repo():
    """Init git repo if not exists"""
    if not _check_git_available():
        _git("init")
        _git("add", "-A")
        _git("commit", "-m", "Initial commit (WOLF auto-init)")


@router.get("/git/status")
async def git_status(branch: Optional[str] = None) -> dict:
    """Get git status — current branch, changes, ahead/behind"""
    _ensure_repo()

    # Current branch
    branch_result = _git("rev-parse", "--abbrev-ref", "HEAD")
    current_branch = branch_result.stdout.strip()

    # Status
    status_result = _git("status", "--porcelain")
    changed = [l for l in status_result.stdout.strip().split('\n') if l]
    staged = [l for l in changed if l[0] != ' ']
    unstaged = [l for l in changed if l[1] != ' ']
    untracked = [l for l in changed if l.startswith('??')]

    # Ahead/behind vs main
    ahead = 0
    behind = 0
    try:
        count = _git("rev-list", "--count", f"main..{current_branch}")
        ahead = int(count.stdout.strip())
        count = _git("rev-list", "--count", f"{current_branch}..main")
        behind = int(count.stdout.strip())
    except Exception:
        pass

    # Stats
    stat_result = _git("diff", "--shortstat", "main..." + current_branch)
    stat_text = stat_result.stdout.strip()

    return {
        "current_branch": current_branch,
        "has_changes": len(changed) > 0,
        "changed_count": len(changed),
        "staged_count": len(staged),
        "unstaged_count": len(unstaged),
        "untracked_count": len(untracked),
        "ahead": ahead,
        "behind": behind,
        "stat": stat_text,
        "git_available": _check_git_available()
    }


@router.get("/git/branches")
async def git_branches() -> dict:
    """List all branches"""
    _ensure_repo()

    # Get branches
    branch_result = _git("branch", "-a")
    current_result = _git("rev-parse", "--abbrev-ref", "HEAD")
    current_branch = current_result.stdout.strip()

    branches = []
    for line in branch_result.stdout.strip().split('\n'):
        name = line.strip().lstrip('*').strip()
        # Skip HEAD refs
        if '->' in name or not name:
            continue
        # Clean remote refs
        remote = name.startswith('remotes/')
        if remote:
            name = name.replace('remotes/origin/', '')
        is_active = name == current_branch
        is_wolf = name.startswith('wolf/')

        # Get commit count for this branch
        commits = 0
        try:
            count = _git("rev-list", "--count", name)
            commits = int(count.stdout.strip())
        except Exception:
            pass

        branches.append({
            "name": name,
            "active": is_active,
            "remote": remote,
            "wolf_session": is_wolf,
            "commits": commits
        })

    return {
        "branches": branches,
        "current_branch": current_branch
    }


@router.get("/git/log")
async def git_log(branch: Optional[str] = None, limit: int = 30) -> dict:
    """Get commit history"""
    _ensure_repo()

    target = branch or "HEAD"
    result = _git(
        "log", target,
        f"-{limit}",
        "--format=%H|%h|%s|%an|%ai"
    )
    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|', 4)
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0],
                "short_hash": parts[1],
                "message": parts[2],
                "author": parts[3],
                "date": parts[4]
            })

    return {"commits": commits, "branch": target}


@router.get("/git/diff")
async def git_diff(commit: str, parent: Optional[str] = None) -> dict:
    """Get diff for a commit"""
    _ensure_repo()

    if parent:
        result = _git("diff", parent, commit)
    else:
        result = _git("show", commit, "--format=")

    # Get changed files
    files_result = _git("diff", "--name-status", f"{commit}~1", commit)
    files = []
    for line in files_result.stdout.strip().split('\n'):
        if line:
            parts = line.split('\t', 1)
            status = parts[0] if parts else 'M'
            filename = parts[1] if len(parts) > 1 else ''
            files.append({"status": status, "file": filename})

    # Stats
    stat_result = _git("show", commit, "--stat", "--format=")
    stat_text = stat_result.stdout.strip()

    return {
        "commit": commit,
        "diff": result.stdout[:50000],  # Limit diff size
        "files": files,
        "stat": stat_text.split('\n')[-2] if stat_text else ""
    }


@router.post("/git/rollback")
async def git_rollback(commit: str = None, mode: str = "soft") -> dict:
    """Rollback to a commit. mode: soft (keep changes), hard (discard changes)"""
    _ensure_repo()

    if commit:
        git_mode = "--hard" if mode == "hard" else "--soft"
        result = _git("reset", git_mode, commit)
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=f"Reset failed: {result.stderr}")
    else:
        # Rollback last commit
        _git("reset", "--soft", "HEAD~1")

    current = _git("rev-parse", "--short", "HEAD")
    return {
        "status": "ok",
        "rolled_back": True,
        "mode": mode,
        "current_commit": current.stdout.strip()
    }


@router.post("/git/accept")
async def git_accept(branch: str = None) -> dict:
    """Accept changes — merge branch to main"""
    _ensure_repo()

    current = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    if not branch:
        branch = current

    if branch == "main":
        return {"status": "skipped", "message": "Already on main"}

    # Save current state
    _git("add", "-A")
    _git("commit", "-m", f"Finalize: {branch}")

    # Switch to main and merge
    _git("checkout", "main")
    merge = _git("merge", branch, "--no-edit")

    if merge.returncode != 0:
        # Conflict — abort and report
        _git("merge", "--abort")
        return {"status": "conflict", "message": "Merge conflict detected. Resolve manually.", "detail": merge.stderr[:500]}

    return {"status": "ok", "merged": branch, "into": "main"}


@router.post("/git/discard")
async def git_discard(branch: str = None) -> dict:
    """Discard a wolf session branch"""
    _ensure_repo()

    if not branch:
        current = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        branch = current

    if branch == "main":
        raise HTTPException(status_code=400, detail="Cannot discard main branch")

    # Switch to main first
    _git("checkout", "main")

    # Force delete the branch
    result = _git("branch", "-D", branch)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Failed to discard: {result.stderr}")

    return {"status": "ok", "discarded": branch}


@router.post("/git/switch")
async def git_switch(branch: str) -> dict:
    """Switch to a different branch"""
    _ensure_repo()

    # Auto-commit current changes
    current = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    status = _git("status", "--porcelain").stdout.strip()
    if status:
        _git("add", "-A")
        _git("commit", "-m", f"Auto-commit before switch to {branch}")

    # Switch
    result = _git("checkout", branch)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Switch failed: {result.stderr}")

    return {"status": "ok", "current_branch": branch}


@router.post("/git/commit")
async def git_commit(message: str = "Auto commit") -> dict:
    """Manual commit current changes"""
    _ensure_repo()

    status = _git("status", "--porcelain").stdout.strip()
    if not status:
        return {"status": "skipped", "message": "Nothing to commit"}

    _git("add", "-A")
    result = _git("commit", "-m", message)

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Commit failed: {result.stderr}")

    current = _git("rev-parse", "--short", "HEAD")
    return {
        "status": "ok",
        "message": message,
        "commit": current.stdout.strip(),
        "files_changed": len(status.split('\n'))
    }
