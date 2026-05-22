import { create } from 'zustand';
import type { ChatMessage } from '@/types';

interface ChatStore {
  messages: ChatMessage[];
  isTyping: boolean;
  currentSessionId: string | null;
  // Message history for Cmd/Ctrl+Z and arrow key navigation
  messageHistory: string[];
  historyIndex: number;
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setTyping: (isTyping: boolean) => void;
  setCurrentSession: (sessionId: string | null) => void;
  clearMessages: () => void;
  // History management
  addToHistory: (message: string) => void;
  navigateHistory: (direction: 'up' | 'down') => string;
  resetHistoryIndex: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isTyping: false,
  currentSessionId: null,
  messageHistory: [],
  historyIndex: -1,

  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        },
      ],
    })),

  setMessages: (messages) => set({ messages }),

  setTyping: (isTyping) => set({ isTyping }),

  setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),

  clearMessages: () => set({ messages: [] }),

  addToHistory: (message) =>
    set((state) => ({
      messageHistory: [message, ...state.messageHistory].slice(0, 50), // Keep last 50 messages
      historyIndex: -1,
    })),

  navigateHistory: (direction) => {
    const { messageHistory, historyIndex } = get();
    if (messageHistory.length === 0) return '';

    let newIndex: number;
    if (direction === 'up') {
      newIndex = historyIndex === -1 ? 0 : Math.min(historyIndex + 1, messageHistory.length - 1);
    } else {
      newIndex = historyIndex === -1 ? -1 : Math.max(historyIndex - 1, -1);
    }

    set({ historyIndex: newIndex });
    return newIndex === -1 ? '' : messageHistory[newIndex];
  },

  resetHistoryIndex: () => set({ historyIndex: -1 }),
}));
