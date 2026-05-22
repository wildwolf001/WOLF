import React, { useState } from 'react';
import { useTask } from '@/hooks';
import { TaskCard } from './TaskCard';
import { TaskCreate } from './TaskCreate';
import type { TaskStatus } from '@/types';

const columns: { id: TaskStatus; label: string }[] = [
  { id: 'pending', label: 'Pending' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'completed', label: 'Completed' },
  { id: 'blocked', label: 'Blocked' },
];

export function TaskBoard() {
  const { tasks } = useTask();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-vscode-text">Task Board</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="px-3 py-1.5 bg-vscode-accent hover:bg-vscode-accent/80 text-white text-xs rounded-sm font-medium transition-colors"
        >
          + New Task
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {columns.map((column) => {
          const columnTasks = tasks.filter((t) => t.status === column.id);
          return (
            <div key={column.id} className="bg-vscode-bg-light rounded-sm border border-vscode-border">
              <div className="flex items-center justify-between mb-3 px-3 py-2 border-b border-vscode-border">
                <h3 className="font-medium text-xs text-vscode-text">{column.label}</h3>
                <span className="text-xs text-vscode-text-dim bg-vscode-bg-hover px-1.5 py-0.5 rounded-sm">
                  {columnTasks.length}
                </span>
              </div>
              <div className="space-y-2 p-2">
                {columnTasks.map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
                {columnTasks.length === 0 && (
                  <p className="text-xs text-vscode-text-dim text-center py-4">
                    No tasks
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {showCreate && <TaskCreate onClose={() => setShowCreate(false)} />}
    </div>
  );
}