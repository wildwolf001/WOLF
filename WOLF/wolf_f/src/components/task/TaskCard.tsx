import React from 'react';
import type { Task } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface TaskCardProps {
  task: Task;
}

const priorityColors: Record<string, string> = {
  low: 'text-gray-400',
  medium: 'text-yellow-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
};

export function TaskCard({ task }: TaskCardProps) {
  return (
    <div className="bg-gray-700 rounded-lg p-3 hover:bg-gray-600 transition-colors cursor-pointer">
      <h4 className="font-medium text-sm truncate">{task.title}</h4>
      <p className="text-xs text-gray-400 mt-1 line-clamp-2">{task.description}</p>

      <div className="flex items-center justify-between mt-3">
        <span className={`text-xs ${priorityColors[task.priority]}`}>
          {task.priority}
        </span>
        <span className="text-xs text-gray-500">
          {formatDistanceToNow(task.createdAt, { addSuffix: true })}
        </span>
      </div>

      {task.assigneeRole && (
        <div className="mt-2 pt-2 border-t border-gray-600">
          <span className="text-xs text-gray-400">
            Assigned: {task.assigneeRole}
          </span>
        </div>
      )}
    </div>
  );
}
