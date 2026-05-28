"""
Integration Tests for WOLF 2.0
Tests the core functionality of the backend
"""
import sys
sys.path.insert(0, '.')

import asyncio


def test_tools():
    """Test tool registration and execution"""
    from app.tools import register_all_tools
    from app.tools.registry import tool_registry

    register_all_tools()
    tools = tool_registry.list_tools()

    assert len(tools) >= 7, f"Expected at least 7 tools, got {len(tools)}"
    print(f"  [OK] {len(tools)} tools registered")

    # Test getting a tool
    bash_tool = tool_registry.get('Bash')
    assert bash_tool is not None, "Bash tool not found"
    print("  [OK] Tool registry working")


def test_query_engine():
    """Test query engine basic functionality"""
    from app.query.engine import QueryEngine, Message
    from app.query.config import QueryConfig

    config = QueryConfig(max_turns=3)

    async def mock_llm(messages, tools, config):
        return {"content": "Hello!", "tool_calls": []}

    async def run():
        engine = QueryEngine(".", llm_provider=mock_llm)
        messages = [Message(role="user", content="Hi")]

        events = []
        async for event in engine.query(messages, "You are helpful", []):
            events.append(event)
            if len(events) > 10:
                break

        return events

    events = asyncio.run(run())
    assert len(events) > 0, "No events generated"
    print(f"  [OK] Query engine generated {len(events)} events")


def test_task_system():
    """Test task system"""
    from app.tasks.base import TaskType, TaskStatus

    assert TaskType.LOCAL_BASH is not None
    assert TaskStatus.PENDING is not None
    print("  [OK] Task types and statuses defined")


def test_workflow():
    """Test workflow engine"""
    from app.workflow.engine import WorkflowDefinition, WorkflowStep

    step = WorkflowStep(
        id="step1",
        name="Test Step",
        action="test",
        args={}
    )

    workflow = WorkflowDefinition(
        id="wf1",
        name="Test Workflow",
        description="Test",
        steps=[step]
    )

    assert workflow.id == "wf1"
    assert len(workflow.steps) == 1
    print("  [OK] Workflow engine working")


def test_transports():
    """Test transport implementations"""
    from app.transports.base import BaseTransport, StreamEvent

    event = StreamEvent("test", {"data": "value"})
    assert event.type == "test"
    print("  [OK] Stream event working")

    from app.transports.sse_transport import SSETransport

    sse = SSETransport("http://localhost")
    assert sse is not None
    print("  [OK] SSE transport created")


def test_mcp():
    """Test MCP client and server"""
    from app.mcp import MCPClient, MCPServer, MCPTool

    client = MCPClient()
    assert client is not None
    print("  [OK] MCP client created")

    server = MCPServer("test-server")
    assert server is not None
    print("  [OK] MCP server created")

    tool = MCPTool(
        name="test-tool",
        description="A test tool",
        input_schema={"type": "object"},
        server_name="test"
    )
    assert tool.name == "test-tool"
    print("  [OK] MCP tool created")


def test_database():
    """Test database models"""
    from app.db.models.task import TaskModel
    from app.db.models.session import SessionModel
    from app.db.models.message import MessageModel

    task = TaskModel(
        id="task1",
        session_id="sess1",
        title="Test",
        status="pending",
        created_at=1234567890.0
    )
    assert task.id == "task1"
    print("  [OK] Task model created")

    session = SessionModel(
        id="sess1",
        workspace_id="ws1",
        user_id="user1",
        created_at=1234567890.0,
        last_active=1234567890.0
    )
    assert session.id == "sess1"
    print("  [OK] Session model created")


def test_services():
    """Test service components"""
    from app.services.tools.orchestration import get_tool_orchestrator
    from app.tools.registry import tool_registry

    orchestrator = get_tool_orchestrator(tool_registry)
    assert orchestrator is not None
    print("  [OK] Tool orchestrator working")


def main():
    """Run all integration tests"""
    print("=" * 50)
    print("WOLF 2.0 Integration Tests")
    print("=" * 50)
    print()

    tests = [
        ("Tools", test_tools),
        ("Query Engine", test_query_engine),
        ("Task System", test_task_system),
        ("Workflow", test_workflow),
        ("Transports", test_transports),
        ("MCP", test_mcp),
        ("Database", test_database),
        ("Services", test_services),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"Testing {name}...")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] FAILED: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)