import { useCallback } from 'react';
import { useChatStore } from '@/store';
import { wsService } from '@/services';

export function useChat() {
  const {
    messages,
    isTyping,
    currentSessionId,
    addMessage,
    setMessages,
    setTyping,
    setCurrentSession,
    clearMessages,
  } = useChatStore();

  const sendMessage = useCallback((content: string, agentRole?: string) => {
    const message = {
      sessionId: currentSessionId || 'default',
      agentRole: agentRole || 'user',
      content,
      isUser: !agentRole,
    };
    addMessage(message);

    // Send via WebSocket if agent is specified
    if (agentRole) {
      // Build history from local message store
      const history = messages
        .filter(m => m.isUser || m.agentRole === agentRole)
        .map(m => ({ role: m.isUser ? 'user' : 'assistant', content: m.content }));

      wsService.sendToAgent(agentRole, content, history);
    }
  }, [addMessage, currentSessionId, messages]);

  const loadHistory = useCallback((history: typeof messages) => {
    setMessages(history);
  }, [setMessages]);

  const startSession = useCallback((sessionId: string) => {
    setCurrentSession(sessionId);
    wsService.joinSession(sessionId);
  }, [setCurrentSession]);

  const endSession = useCallback(() => {
    if (currentSessionId) {
      wsService.leaveSession(currentSessionId);
    }
    setCurrentSession(null);
    clearMessages();
  }, [currentSessionId, setCurrentSession, clearMessages]);

  return {
    messages,
    isTyping,
    currentSessionId,
    sendMessage,
    loadHistory,
    startSession,
    endSession,
    setTyping,
  };
}
