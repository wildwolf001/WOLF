import React, { useState } from 'react';
import { useTask } from '@/hooks';
import type { TaskType, TaskPriority } from '@/types';

interface TaskCreateProps {
  onClose: () => void;
}

const taskTypes: { value: TaskType; label: string }[] = [
  { value: 'research', label: 'Research' },
  { value: 'model_development', label: 'Model Development' },
  { value: 'coding', label: 'Coding' },
  { value: 'writing', label: 'Writing' },
  { value: 'data', label: 'Data' },
  { value: 'deployment', label: 'Deployment' },
  { value: 'review', label: 'Review' },
  { value: 'management', label: 'Management' },
];

const priorities: { value: TaskPriority; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

export function TaskCreate({ onClose }: TaskCreateProps) {
  const { createTask } = useTask();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<TaskType>('research');
  const [priority, setPriority] = useState<TaskPriority>('medium');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    await createTask({ title, description, type, priority });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-md p-6">
        <h2 className="text-lg font-medium mb-4">Create New Task</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-primary-500 focus:outline-none"
              placeholder="Task title"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-primary-500 focus:outline-none resize-none"
              rows={3}
              placeholder="Task description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as TaskType)}
                className="w-full px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-primary-500 focus:outline-none"
              >
                {taskTypes.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 bg-gray-700 rounded-lg border border-gray-600 focus:border-primary-500 focus:outline-none"
              >
                {priorities.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm font-medium transition-colors"
            >
              Create Task
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
