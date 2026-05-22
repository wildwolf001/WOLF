import type { AgentRole, AgentStatus, AgentMessage } from '@/types';

export interface BaseAgent {
  id: string;
  role: AgentRole;
  name: string;
  status: AgentStatus;
  currentTask?: string;
  systemPrompt: string;
}

export interface Agent extends BaseAgent {
  receive(message: AgentMessage): Promise<void>;
  send(to: AgentRole | 'broadcast', content: string, type: AgentMessage['type']): Promise<void>;
  execute(task: unknown): Promise<string>;
}

export type AgentFactory = (role: AgentRole, config?: Partial<BaseAgent>) => Agent;
