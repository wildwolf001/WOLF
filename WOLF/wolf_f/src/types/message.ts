// Message Types
export type MessageType =
  | 'task'
  | 'result'
  | 'question'
  | 'approval'
  | 'rejection'
  | 'status'
  | 'progress'
  | 'broadcast';

export interface ChatMessage {
  id: string;
  sessionId: string;
  agentRole: string;
  content: string;
  timestamp: number;
  isUser: boolean;
  attachments?: import('./agent').Attachment[];
}

// Re-export Attachment from agent to avoid duplication
export type { Attachment } from './agent';
