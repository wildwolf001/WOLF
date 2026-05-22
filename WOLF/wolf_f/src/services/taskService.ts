import { tasksApi } from './api';
import { wsService } from './websocket';

class TaskService {
  async getAllTasks(params?: { status?: string; page?: number; pageSize?: number }) {
    return tasksApi.getAll(params);
  }

  async getTask(id: string) {
    return tasksApi.getById(id);
  }

  async createTask(task: unknown) {
    const result = await tasksApi.create(task);
    // Notify via WebSocket
    wsService.createTask(task);
    return result;
  }

  async updateTask(id: string, updates: unknown) {
    return tasksApi.update(id, updates);
  }

  async deleteTask(id: string) {
    return tasksApi.delete(id);
  }

  async assignTask(taskId: string, assigneeId: string) {
    return tasksApi.assign(taskId, assigneeId);
  }
}

export const taskService = new TaskService();
