import { agentsApi } from './api';
import { wsService } from './websocket';
import type { AgentRole } from '@/types';

class AgentService {
  async getAllAgents() {
    return agentsApi.getAll();
  }

  async getAgent(id: string) {
    return agentsApi.getById(id);
  }

  async getAgentStatus(id: string) {
    return agentsApi.getStatus(id);
  }

  async sendMessage(agentId: string, content: string) {
    // Send via WebSocket for real-time response
    wsService.sendToAgent(agentId, content);
  }

  async getHistory(agentId: string) {
    return agentsApi.getHistory(agentId);
  }

  assignTaskToAgent(task: unknown, agentRole: AgentRole) {
    // This would typically be handled by the PM agent
    const message = `New task assigned: ${JSON.stringify(task)}`;
    wsService.sendToAgent(agentRole, message);
  }
}

export const agentService = new AgentService();
