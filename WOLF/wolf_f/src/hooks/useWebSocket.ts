import { useEffect, useCallback } from 'react';
import { wsService } from '@/services';
import { useAgentStore, useChatStore } from '@/store';

export function useWebSocket() {
  const { updateAgentStatus } = useAgentStore();
  const { addMessage, setTyping } = useChatStore();

  const handleAgentStatus = useCallback((data: { agentId: string; status: string }) => {
    updateAgentStatus(data.agentId, data.status as 'idle' | 'working' | 'error');
  }, [updateAgentStatus]);

  const handleNewMessage = useCallback((data: { agentRole?: string; content: string; isUser?: boolean }) => {
    addMessage({
      sessionId: 'default',
      agentRole: data.agentRole || 'pm',
      content: data.content,
      isUser: data.isUser || false,
    });
    setTyping(false);
  }, [addMessage, setTyping]);

  const handleAgentTyping = useCallback(() => {
    setTyping(true);
  }, [setTyping]);

  useEffect(() => {
    // Connect to backend WebSocket
    wsService.connect();

    // Set up event handlers
    wsService.on('agent-status', handleAgentStatus);
    wsService.on('new-message', handleNewMessage);
    wsService.on('agent-typing', handleAgentTyping);

    // Join default session
    wsService.joinSession('default');

    return () => {
      wsService.off('agent-status', handleAgentStatus);
      wsService.off('new-message', handleNewMessage);
      wsService.off('agent-typing', handleAgentTyping);
      wsService.leaveSession('default');
    };
  }, [handleAgentStatus, handleNewMessage, handleAgentTyping]);

  const sendMessage = useCallback((agentId: string, content: string) => {
    setTyping(true);
    wsService.sendToAgent(agentId, content);
  }, [setTyping]);

  return {
    isConnected: wsService.isConnected(),
    sendMessage,
  };
}