// API Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// WebSocket Events
export interface WSClientEvents {
  'join-session': { sessionId: string };
  'leave-session': { sessionId: string };
  'send-to-agent': { agentId: string; content: string; sessionId?: string };
  'process-request': { message: string; sessionId: string };
  'create-task': { task: unknown };
  'agent-action': { agentId: string; action: string; payload: unknown };
}

export interface WSServerEvents {
  'agent-status': { agentId: string; status: string };
  'new-message': { agentRole?: string; content: string; isUser?: boolean };
  'task-updated': { task: unknown };
  'agent-typing': { agentId: string };
  'notification': { type: string; message: string };
}
