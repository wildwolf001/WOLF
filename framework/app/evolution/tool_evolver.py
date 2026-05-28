"""Tool 描述自动优化 — ToolUsageAnalyzer + ToolDescOptimizer"""
from typing import Dict, List, Optional


class ToolUsageAnalyzer:
    """Tool 调用日志分析器"""

    def __init__(self):
        self._logs: List[dict] = []

    def log_call(self, tool_name: str, success: bool, error: str = "", params: dict = None):
        self._logs.append({
            "tool": tool_name, "success": success, "error": error, "params": params or {}
        })

    def analyze(self) -> dict:
        """分析 Tool 使用情况"""
        by_tool = {}
        for log in self._logs:
            name = log["tool"]
            if name not in by_tool:
                by_tool[name] = {"calls": 0, "successes": 0, "errors": [], "param_issues": []}
            by_tool[name]["calls"] += 1
            if log["success"]:
                by_tool[name]["successes"] += 1
            if log.get("error"):
                by_tool[name]["errors"].append(log["error"])
        for name in by_tool:
            s = by_tool[name]
            s["success_rate"] = round(s["successes"] / s["calls"], 3) if s["calls"] > 0 else 0
            s["needs_desc_improvement"] = s["success_rate"] < 0.7
        return by_tool


class ToolDescOptimizer:
    """Tool 描述优化器"""

    def __init__(self, analyzer: ToolUsageAnalyzer = None):
        self._analyzer = analyzer or ToolUsageAnalyzer()

    def analyze_missing_tools(self, agent_requests: List[str], existing_tools: set) -> List[str]:
        """检测 Agent 需要的但缺失的 Tool"""
        missing = []
        for req in agent_requests:
            req_lower = req.lower()
            if not any(t in req_lower for t in existing_tools):
                missing.append(req)
        return missing

    def improve_description(self, tool_name: str, current_desc: str, analysis: dict) -> str:
        """改进 Tool 描述"""
        stats = analysis.get(tool_name, {})
        success_rate = stats.get("success_rate", 1.0)
        common_errors = stats.get("errors", [])

        improved = current_desc
        if success_rate < 0.7 and common_errors:
            improved += "\n\n⚠ Common mistakes to avoid:\n"
            for err in set(common_errors)[:3]:
                improved += f"- {err}\n"
        return improved
