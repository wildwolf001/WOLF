import { useCallback } from 'react';
import { useTaskStore } from '@/store';
import { taskService } from '@/services';
import type { TaskCreate, TaskStatus } from '@/types';

export function useTask() {
  const {
    tasks,
    selectedTask,
    addTask,
    updateTask,
    deleteTask,
    setSelectedTask,
    getTasksByStatus,
    getTasksByAssignee,
  } = useTaskStore();

  const createTask = useCallback(async (task: TaskCreate) => {
    const newTask = addTask(task);
    try {
      await taskService.createTask(newTask);
    } catch (error) {
      console.error('Failed to create task on server:', error);
    }
    return newTask;
  }, [addTask]);

  const updateTaskStatus = useCallback(async (id: string, status: TaskStatus) => {
    updateTask(id, { status });
    try {
      await taskService.updateTask(id, { status });
    } catch (error) {
      console.error('Failed to update task on server:', error);
    }
  }, [updateTask]);

  const removeTask = useCallback(async (id: string) => {
    deleteTask(id);
    try {
      await taskService.deleteTask(id);
    } catch (error) {
      console.error('Failed to delete task on server:', error);
    }
  }, [deleteTask]);

  const assignTask = useCallback(async (taskId: string, assigneeId: string) => {
    updateTask(taskId, { assigneeId, status: 'in_progress' });
    try {
      await taskService.assignTask(taskId, assigneeId);
    } catch (error) {
      console.error('Failed to assign task on server:', error);
    }
  }, [updateTask]);

  return {
    tasks,
    selectedTask,
    createTask,
    updateTask,
    updateTaskStatus,
    removeTask,
    assignTask,
    setSelectedTask,
    getTasksByStatus,
    getTasksByAssignee,
  };
}
