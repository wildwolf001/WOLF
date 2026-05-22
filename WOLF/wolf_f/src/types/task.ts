// Task Types
export type TaskType =
  | 'research'
  | 'model_development'
  | 'coding'
  | 'writing'
  | 'data'
  | 'deployment'
  | 'review'
  | 'management';

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'blocked'
  | 'cancelled';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Task {
  id: string;
  title: string;
  description: string;
  type: TaskType;
  status: TaskStatus;
  priority: TaskPriority;
  assigneeId?: string;
  assigneeRole?: string;
  parentId?: string;
  createdBy: string;
  createdAt: number;
  updatedAt: number;
  completedAt?: number;
  dependencies: string[];
  subtasks: string[];
  metadata?: Record<string, unknown>;
}

export interface TaskCreate {
  title: string;
  description: string;
  type: TaskType;
  priority: TaskPriority;
  assigneeRole?: string;
  dependencies?: string[];
}
