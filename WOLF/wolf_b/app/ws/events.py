from enum import Enum


class WSEventType(str, Enum):
    # Client to Server
    JOIN_SESSION = "join-session"
    LEAVE_SESSION = "leave-session"
    SEND_TO_AGENT = "send-to-agent"
    CREATE_TASK = "create-task"
    AGENT_ACTION = "agent-action"
    PERMISSION_RESPONSE = "permission-response"

    # Server to Client
    AGENT_STATUS = "agent-status"
    NEW_MESSAGE = "new-message"
    TASK_UPDATED = "task-updated"
    AGENT_TYPING = "agent-typing"
    NOTIFICATION = "notification"
    PERMISSION_REQUEST = "permission-request"
