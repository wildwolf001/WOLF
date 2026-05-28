import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage } from '@/types';
import { memoryApi } from '@/services/api';

export interface LogEntry {
  id: string;
  timestamp: number;
  message: string;
  type: 'log' | 'error' | 'user' | 'done' | 'system';
}

export interface TaskResultEntry {
  task_id: string;
  type: string;
  title: string;
  status: string;
  result: string;
}

export type MemoryType = 'user' | 'feedback' | 'project' | 'reference';

export interface MemoryEntry {
  id: string;
  name: string;
  description: string;
  type: MemoryType;
  content: string;
  why?: string;  // Why this memory is important
  howToApply?: string;  // How to apply this memory
  createdAt: number;
  updatedAt: number;
  lastUsedAt?: number;
  usageCount: number;
}

export interface Session {
  id: string;
  name: string;
  messages: ChatMessage[];
  logs: LogEntry[];
  taskResults: TaskResultEntry[];
  finalReport: string | null;
  memories: MemoryEntry[];
  createdAt: number;
  updatedAt: number;
}

interface SessionStore {
  sessions: Session[];
  currentSessionId: string | null;
  addSession: (name?: string) => Session;
  deleteSession: (id: string) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  getSession: (id: string) => Session | undefined;
  setCurrentSession: (id: string | null) => void;
  addMessageToSession: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => ChatMessage;
  deleteMessageFromSession: (sessionId: string, messageId: string) => void;
  clearSessionMessages: (sessionId: string) => void;
  addLogToSession: (sessionId: string, message: string, type?: LogEntry['type']) => LogEntry;
  clearSessionLogs: (sessionId: string) => void;
  addTaskResultToSession: (sessionId: string, result: TaskResultEntry) => void;
  clearSessionTaskResults: (sessionId: string) => void;
  setFinalReport: (sessionId: string, report: string) => void;
  exportSessions: () => string;
  importSessions: (jsonStr: string) => boolean;
  // Memory management (with API persistence)
  addMemory: (sessionId: string, memory: Omit<MemoryEntry, 'id' | 'createdAt' | 'updatedAt' | 'usageCount'>) => Promise<MemoryEntry>;
  updateMemory: (sessionId: string, memoryId: string, updates: Partial<MemoryEntry>) => Promise<void>;
  deleteMemory: (sessionId: string, memoryId: string) => Promise<void>;
  getMemories: (sessionId: string) => MemoryEntry[];
  useMemory: (sessionId: string, memoryId: string) => Promise<void>;
  clearOldMemories: (sessionId: string, maxAgeMs?: number) => void;
  getRelevantMemories: (sessionId: string, maxCount?: number) => MemoryEntry[];
  loadMemoriesFromAPI: (sessionId: string) => Promise<void>;
}

const createDefaultSession = (): Session => ({
  id: `session-${Date.now()}`,
  name: 'New Conversation',
  messages: [],
  logs: [],
  taskResults: [],
  finalReport: null,
  memories: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
});

export const useSessionStore = create<SessionStore>()(
  persist(
    (set, get) => ({
      sessions: [createDefaultSession()],
      currentSessionId: null,

      addSession: (name?: string) => {
        const session: Session = {
          ...createDefaultSession(),
          name: name || `Conversation ${get().sessions.length + 1}`,
        };
        set((state) => ({
          sessions: [session, ...state.sessions],
        }));
        return session;
      },

      deleteSession: (id: string) => {
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
        }));
      },

      updateSession: (id: string, updates: Partial<Session>) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id ? { ...s, ...updates, updatedAt: Date.now() } : s
          ),
        }));
      },

      getSession: (id: string) => {
        return get().sessions.find((s) => s.id === id);
      },

      setCurrentSession: (id: string | null) => {
        set({ currentSessionId: id });
      },

      addMessageToSession: (sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
        const newMessage: ChatMessage = {
          ...message,
          id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        };

        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, messages: [...(s.messages || []), newMessage], updatedAt: Date.now() }
              : s
          ),
        }));

        return newMessage;
      },

      deleteMessageFromSession: (sessionId: string, messageId: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, messages: s.messages.filter((m) => m.id !== messageId), updatedAt: Date.now() }
              : s
          ),
        }));
      },

      clearSessionMessages: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, messages: [], updatedAt: Date.now() } : s
          ),
        }));
      },

      addLogToSession: (sessionId: string, message: string, type: LogEntry['type'] = 'log') => {
        const logEntry: LogEntry = {
          id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
          message,
          type,
        };

        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, logs: [...(s.logs || []), logEntry], updatedAt: Date.now() }
              : s
          ),
        }));

        return logEntry;
      },

      clearSessionLogs: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, logs: [], updatedAt: Date.now() } : s
          ),
        }));
      },

      addTaskResultToSession: (sessionId: string, result: TaskResultEntry) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, taskResults: [...(s.taskResults || []), result], updatedAt: Date.now() }
              : s
          ),
        }));
      },

      clearSessionTaskResults: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, taskResults: [], updatedAt: Date.now() } : s
          ),
        }));
      },

      setFinalReport: (sessionId: string, report: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, finalReport: report, updatedAt: Date.now() } : s
          ),
        }));
      },

      // Export all sessions to JSON
      exportSessions: () => {
        const { sessions } = get();
        return JSON.stringify(sessions, null, 2);
      },

      // Import sessions from JSON
      importSessions: (jsonStr: string) => {
        try {
          const imported = JSON.parse(jsonStr) as Session[];
          if (!Array.isArray(imported)) {
            throw new Error('Invalid format');
          }
          set((state) => ({
            sessions: [...imported, ...state.sessions],
          }));
          return true;
        } catch {
          return false;
        }
      },

      // Memory management methods (with API persistence)
      addMemory: async (sessionId: string, memory: Omit<MemoryEntry, 'id' | 'createdAt' | 'updatedAt' | 'usageCount'>) => {
        const now = Date.now();
        const newMemory: MemoryEntry = {
          ...memory,
          id: `memory-${now}-${Math.random().toString(36).substr(2, 9)}`,
          createdAt: now,
          updatedAt: now,
          usageCount: 0,
        };

        // Update local store first
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, memories: [...(s.memories || []), newMemory], updatedAt: now }
              : s
          ),
        }));

        // Sync to API
        try {
          await memoryApi.create(sessionId, {
            name: memory.name,
            description: memory.description,
            type: memory.type,
            content: memory.content,
            why: memory.why,
            howToApply: memory.howToApply,
          });
        } catch (error) {
          console.error('Failed to sync memory to API:', error);
        }

        return newMemory;
      },

      updateMemory: async (sessionId: string, memoryId: string, updates: Partial<MemoryEntry>) => {
        // Update local store first
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  memories: s.memories.map((m) =>
                    m.id === memoryId ? { ...m, ...updates, updatedAt: Date.now() } : m
                  ),
                  updatedAt: Date.now(),
                }
              : s
          ),
        }));

        // Sync to API
        try {
          await memoryApi.update(sessionId, memoryId, {
            name: updates.name,
            description: updates.description,
            type: updates.type,
            content: updates.content,
            why: updates.why,
            howToApply: updates.howToApply,
          });
        } catch (error) {
          console.error('Failed to sync memory update to API:', error);
        }
      },

      deleteMemory: async (sessionId: string, memoryId: string) => {
        // Update local store first
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, memories: s.memories.filter((m) => m.id !== memoryId), updatedAt: Date.now() }
              : s
          ),
        }));

        // Sync to API
        try {
          await memoryApi.delete(sessionId, memoryId);
        } catch (error) {
          console.error('Failed to sync memory deletion to API:', error);
        }
      },

      getMemories: (sessionId: string) => {
        const session = get().sessions.find((s) => s.id === sessionId);
        return session?.memories || [];
      },

      useMemory: async (sessionId: string, memoryId: string) => {
        // Update local store first
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  memories: s.memories.map((m) =>
                    m.id === memoryId
                      ? { ...m, usageCount: m.usageCount + 1, lastUsedAt: Date.now() }
                      : m
                  ),
                  updatedAt: Date.now(),
                }
              : s
          ),
        }));

        // Sync to API
        try {
          await memoryApi.use(sessionId, memoryId);
        } catch (error) {
          console.error('Failed to sync memory usage to API:', error);
        }
      },

      loadMemoriesFromAPI: async (sessionId: string) => {
        try {
          const response = await memoryApi.getAll(sessionId);
          const data = response as any;
          const apiMemoriesData = Array.isArray(data.memories) ? data.memories : [];
          const apiMemories: MemoryEntry[] = apiMemoriesData.map((m: any) => ({
            id: m.id,
            name: m.name,
            description: m.description || '',
            type: m.type,
            content: m.content,
            why: m.why || '',
            howToApply: m.howToApply || '',
            createdAt: new Date(m.createdAt).getTime(),
            updatedAt: new Date(m.updatedAt).getTime(),
            lastUsedAt: m.lastUsedAt ? new Date(m.lastUsedAt).getTime() : undefined,
            usageCount: m.usageCount || 0,
          }));

          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId
                ? { ...s, memories: apiMemories, updatedAt: Date.now() }
                : s
            ),
          }));
        } catch (error) {
          console.error('Failed to load memories from API:', error);
        }
      },

      clearOldMemories: (sessionId: string, maxAgeMs: number = 7 * 24 * 60 * 60 * 1000) => {
        // Default: clear memories older than 7 days
        const cutoff = Date.now() - maxAgeMs;
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  memories: s.memories.filter((m) => m.createdAt > cutoff || m.usageCount > 0),
                  updatedAt: Date.now(),
                }
              : s
          ),
        }));
      },

      getRelevantMemories: (sessionId: string, maxCount: number = 5) => {
        const memories = get().getMemories(sessionId);
        // Sort by: usageCount (desc), lastUsedAt (desc), updatedAt (desc)
        const sorted = [...memories].sort((a, b) => {
          const aScore = (a.usageCount || 0) * 1000 + (a.lastUsedAt || 0) + a.updatedAt;
          const bScore = (b.usageCount || 0) * 1000 + (b.lastUsedAt || 0) + b.updatedAt;
          return bScore - aScore;
        });
        return sorted.slice(0, maxCount);
      },
    }),
    {
      name: 'wolf-sessions',
    }
  )
);