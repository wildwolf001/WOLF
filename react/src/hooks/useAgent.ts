import { useCallback } from 'react';
import { useAgentStore } from '@/store';
import { agentService } from '@/services';
import type { AgentRole } from '@/types';

export function useAgent() {
  const { agents, activeAgent, setActiveAgent, updateAgentStatus } = useAgentStore();

  const sendMessage = useCallback(async (agentId: string, content: string) => {
    await agentService.sendMessage(agentId, content);
  }, []);

  const selectAgent = useCallback((agentId: string | null) => {
    setActiveAgent(agentId);
  }, [setActiveAgent]);

  const getAgentByRole = useCallback((role: AgentRole) => {
    return agents.find((a) => a.role === role);
  }, [agents]);

  const getAllAgents = useCallback(() => {
    return agents;
  }, [agents]);

  return {
    agents,
    activeAgent,
    sendMessage,
    selectAgent,
    getAgentByRole,
    getAllAgents,
    updateAgentStatus,
  };
}
