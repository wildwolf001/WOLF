/**
 * AgentFactory - DEPRECATED
 *
 * Multi-agent collaboration has been disabled.
 * Single-agent direct execution mode is now used.
 *
 * @deprecated Use MainAgent with single-agent direct execution instead
 */
import type { AgentRole, AgentConfig } from '@/types';

const agentConfigs: Record<AgentRole, Partial<AgentConfig>> = {
  main: {
    name: 'Main Agent',
    capabilities: ['coordination', 'execution', 'analysis', 'exploration'],
  },
  pm: {
    name: 'PM Agent',
    capabilities: ['task-management', 'coordination', 'planning'],
  },
  research: {
    name: 'Research Agent',
    capabilities: ['web-search', 'paper-analysis', 'knowledge-synthesis'],
  },
  ml: {
    name: 'ML Engineer Agent',
    capabilities: ['model-design', 'training', 'optimization'],
  },
  developer: {
    name: 'Developer Agent',
    capabilities: ['frontend', 'backend', 'database'],
  },
  writer: {
    name: 'Writer Agent',
    capabilities: ['paper-writing', 'documentation'],
  },
  data: {
    name: 'Data Agent',
    capabilities: ['data-collection', 'data-cleaning', 'annotation'],
  },
  review: {
    name: 'Review Agent',
    capabilities: ['paper-review', 'quality-control'],
  },
  devops: {
    name: 'DevOps Agent',
    capabilities: ['containerization', 'ci-cd', 'monitoring'],
  },
};

export function createAgent(role: AgentRole, customConfig?: Partial<AgentConfig>): never {
  throw new Error('Multi-agent collaboration is disabled. Use single-agent direct execution mode.');
}

export function getAvailableRoles(): AgentRole[] {
  return ['pm', 'research', 'ml', 'developer', 'writer', 'data', 'review', 'devops'];
}