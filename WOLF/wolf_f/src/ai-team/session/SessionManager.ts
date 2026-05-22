import type { ChatMessage } from '@/types';

export interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
  context: Map<string, unknown>;
}

export class SessionManager {
  private sessions: Map<string, Session> = new Map();
  private activeSessionId: string | null = null;

  createSession(title: string): Session {
    const session: Session = {
      id: `session-${Date.now()}`,
      title,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      context: new Map(),
    };
    this.sessions.set(session.id, session);
    this.activeSessionId = session.id;
    return session;
  }

  getSession(id: string): Session | undefined {
    return this.sessions.get(id);
  }

  getAllSessions(): Session[] {
    return Array.from(this.sessions.values());
  }

  getActiveSession(): Session | undefined {
    if (!this.activeSessionId) return undefined;
    return this.sessions.get(this.activeSessionId);
  }

  setActiveSession(id: string): void {
    if (this.sessions.has(id)) {
      this.activeSessionId = id;
    }
  }

  addMessage(sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>): ChatMessage {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error('Session not found');
    }

    const newMessage: ChatMessage = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
    };

    session.messages.push(newMessage);
    session.updatedAt = Date.now();
    return newMessage;
  }

  setContext(sessionId: string, key: string, value: unknown): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.context.set(key, value);
      session.updatedAt = Date.now();
    }
  }

  getContext(sessionId: string, key: string): unknown | undefined {
    const session = this.sessions.get(sessionId);
    return session?.context.get(key);
  }

  deleteSession(id: string): boolean {
    if (this.activeSessionId === id) {
      this.activeSessionId = null;
    }
    return this.sessions.delete(id);
  }
}

export const sessionManager = new SessionManager();
