/**
 * TaskManager - DEPRECATED
 *
 * Multi-agent collaboration has been disabled.
 * Single-agent direct execution mode is now used.
 *
 * @deprecated Use MainAgent with single-agent direct execution instead
 */
import type { Task, TaskCreate, TaskType, AgentRole } from '@/types';

export class TaskManager {
  private tasks: Map<string, Task> = new Map();
  private taskQueue: string[] = [];

  createTask(taskCreate: TaskCreate): never {
    throw new Error('Multi-agent task management is disabled. Use single-agent direct execution mode.');
  }

  getTask(id: string): Task | undefined {
    return undefined;
  }

  getAllTasks(): Task[] {
    return [];
  }

  getTasksByStatus(status: Task['status']): Task[] {
    return [];
  }

  getTasksByAssignee(assigneeId: string): Task[] {
    return [];
  }

  updateTask(id: string, updates: Partial<Task>): Task | undefined {
    return undefined;
  }

  deleteTask(id: string): boolean {
    return false;
  }

  assignTask(taskId: string, assigneeId: string): Task | undefined {
    return undefined;
  }

  completeTask(taskId: string): Task | undefined {
    return undefined;
  }

  getNextTask(): Task | undefined {
    return undefined;
  }

  getTaskCount(): { pending: number; inProgress: number; completed: number; blocked: number } {
    return { pending: 0, inProgress: 0, completed: 0, blocked: 0 };
  }
}

export const taskManager = new TaskManager();

export function getAgentForTaskType(taskType: TaskType): AgentRole {
  const mapping: Record<TaskType, AgentRole> = {
    research: 'research',
    model_development: 'ml',
    coding: 'developer',
    writing: 'writer',
    data: 'data',
    deployment: 'devops',
    review: 'review',
    management: 'pm',
  };
  return mapping[taskType] || 'pm';
}