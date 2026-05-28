// Agent Types
export type AgentRole =
  | 'main'          // Main Agent (Claude Code style)
  | 'pm'           // Project Manager
  | 'research'     // Research Agent
  | 'ml'           // ML Engineer
  | 'developer'     // Full-Stack Developer
  | 'writer'        // Technical Writer
  | 'data'          // Data Engineer
  | 'review'        // Review Agent
  | 'devops';       // DevOps Agent

export type AgentStatus =
  | 'idle'
  | 'analyzing'
  | 'working'
  | 'waiting'
  | 'error'
  | 'completed';

export interface AgentConfig {
  id: string;
  role: AgentRole;
  name: string;
  description: string;
  systemPrompt: string;
  status: AgentStatus;
  currentTask?: string;
  capabilities: string[];
  llmProvider?: string;
  model?: string;
}

export interface AgentMessage {
  id: string;
  from: AgentRole;
  to: AgentRole | 'broadcast';
  type: 'task' | 'result' | 'question' | 'approval' | 'rejection' | 'status' | 'progress' | 'broadcast';
  content: string;
  attachments?: Attachment[];
  metadata?: Record<string, unknown>;
  timestamp: number;
  taskId?: string;
  sessionId?: string;
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  url?: string;
  content?: string;
}

// Agent State
export interface AgentState {
  agents: Map<string, AgentConfig>;
  activeAgent: string | null;
  agentMessages: Map<string, AgentMessage[]>;
}
