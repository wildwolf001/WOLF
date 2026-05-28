import { create } from 'zustand';
import type { Task, TaskCreate, TaskStatus } from '@/types';

interface TaskStore {
  tasks: Task[];
  selectedTask: Task | null;
  backgroundTasks: Map<string, BackgroundTask>;
  addTask: (task: TaskCreate) => Task;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  setSelectedTask: (task: Task | null) => void;
  getTasksByStatus: (status: TaskStatus) => Task[];
  getTasksByAssignee: (assigneeId: string) => Task[];
  // Background task management
  addBackgroundTask: (task: BackgroundTask) => void;
  updateBackgroundTask: (id: string, updates: Partial<BackgroundTask>) => void;
  removeBackgroundTask: (id: string) => void;
  getBackgroundTask: (id: string) => BackgroundTask | undefined;
  getBackgroundTasks: () => BackgroundTask[];
}

export interface BackgroundTask {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  createdAt: number;
  updatedAt: number;
  startedAt?: number;
  completedAt?: number;
  result?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  selectedTask: null,
  backgroundTasks: new Map(),

  addTask: (taskCreate) => {
    const task: Task = {
      id: `task-${Date.now()}`,
      ...taskCreate,
      status: 'pending',
      createdBy: 'user',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      dependencies: taskCreate.dependencies || [],
      subtasks: [],
    };
    set((state) => ({ tasks: [...state.tasks, task] }));
    return task;
  },

  updateTask: (id, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, ...updates, updatedAt: Date.now() } : t
      ),
    })),

  deleteTask: (id) =>
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
      selectedTask: state.selectedTask?.id === id ? null : state.selectedTask,
    })),

  setSelectedTask: (task) => set({ selectedTask: task }),

  getTasksByStatus: (status) => get().tasks.filter((t) => t.status === status),

  getTasksByAssignee: (assigneeId) =>
    get().tasks.filter((t) => t.assigneeId === assigneeId),

  // Background task management
  addBackgroundTask: (task) =>
    set((state) => {
      const newMap = new Map(state.backgroundTasks);
      newMap.set(task.id, task);
      return { backgroundTasks: newMap };
    }),

  updateBackgroundTask: (id, updates) =>
    set((state) => {
      const newMap = new Map(state.backgroundTasks);
      const existing = newMap.get(id);
      if (existing) {
        newMap.set(id, { ...existing, ...updates, updatedAt: Date.now() });
      }
      return { backgroundTasks: newMap };
    }),

  removeBackgroundTask: (id) =>
    set((state) => {
      const newMap = new Map(state.backgroundTasks);
      newMap.delete(id);
      return { backgroundTasks: newMap };
    }),

  getBackgroundTask: (id) => get().backgroundTasks.get(id),

  getBackgroundTasks: () => Array.from(get().backgroundTasks.values()),
}));
