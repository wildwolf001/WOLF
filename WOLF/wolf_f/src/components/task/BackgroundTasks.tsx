import React from 'react';
import { useTaskStore, type BackgroundTask } from '@/store/taskStore';
import clsx from 'clsx';

const statusColors: Record<BackgroundTask['status'], string> = {
  pending: 'bg-vscode-yellow',
  running: 'bg-vscode-blue animate-pulse',
  completed: 'bg-vscode-green',
  failed: 'bg-vscode-red',
  cancelled: 'bg-vscode-text-dim',
};

const statusLabels: Record<BackgroundTask['status'], string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export function BackgroundTasks() {
  const {
    backgroundTasks,
    updateBackgroundTask,
    removeBackgroundTask,
    getBackgroundTasks,
  } = useTaskStore();

  const tasks = getBackgroundTasks();

  const handleCancel = (taskId: string) => {
    updateBackgroundTask(taskId, {
      status: 'cancelled',
      completedAt: Date.now(),
    });
  };

  const handleRetry = (task: BackgroundTask) => {
    updateBackgroundTask(task.id, {
      status: 'pending',
      error: undefined,
      progress: 0,
    });
  };

  const handleRemove = (taskId: string) => {
    removeBackgroundTask(taskId);
  };

  const handleClearCompleted = () => {
    tasks
      .filter(t => t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled')
      .forEach(t => removeBackgroundTask(t.id));
  };

  if (tasks.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="text-4xl mb-4">⚡</div>
          <div className="text-vscode-text mb-2">No Background Tasks</div>
          <div className="text-xs text-vscode-text-dim max-w-xs">
            Long-running tasks will appear here. Tasks include file processing, model training, and large research operations.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-vscode-text">
          Background Tasks ({tasks.length})
        </h2>
        {tasks.some(t => ['completed', 'failed', 'cancelled'].includes(t.status)) && (
          <button
            onClick={handleClearCompleted}
            className="px-3 py-1 text-xs text-vscode-text-dim hover:text-vscode-text"
          >
            Clear Completed
          </button>
        )}
      </div>

      <div className="space-y-3">
        {tasks.map(task => (
          <div
            key={task.id}
            className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className={clsx('w-3 h-3 rounded-full', statusColors[task.status])} />
                <div>
                  <div className="text-sm text-vscode-text font-medium">{task.name}</div>
                  {task.description && (
                    <div className="text-xs text-vscode-text-dim">{task.description}</div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-vscode-text-dim capitalize">
                  {statusLabels[task.status]}
                </span>
                {task.status === 'failed' && (
                  <button
                    onClick={() => handleRetry(task)}
                    className="px-2 py-1 text-xs text-vscode-accent hover:bg-vscode-accent/20 rounded"
                  >
                    Retry
                  </button>
                )}
                {['pending', 'running'].includes(task.status) && (
                  <button
                    onClick={() => handleCancel(task.id)}
                    className="px-2 py-1 text-xs text-vscode-red hover:bg-vscode-red/20 rounded"
                  >
                    Cancel
                  </button>
                )}
                {['completed', 'failed', 'cancelled'].includes(task.status) && (
                  <button
                    onClick={() => handleRemove(task.id)}
                    className="px-2 py-1 text-xs text-vscode-text-dim hover:text-vscode-text"
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {(task.status === 'pending' || task.status === 'running') && (
              <div className="mb-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-vscode-text-dim">Progress</span>
                  <span className="text-vscode-text">{task.progress}%</span>
                </div>
                <div className="h-1.5 bg-vscode-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-vscode-accent transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error message */}
            {task.error && (
              <div className="mb-3 p-2 bg-vscode-red/10 border border-vscode-red/30 rounded text-xs text-vscode-red">
                {task.error}
              </div>
            )}

            {/* Result preview */}
            {task.result && task.status === 'completed' && (
              <div className="mb-3 p-2 bg-vscode-bg rounded text-xs text-vscode-text-dim font-mono truncate">
                {typeof task.result === 'string' ? task.result : JSON.stringify(task.result).slice(0, 200)}
              </div>
            )}

            {/* Timestamps */}
            <div className="flex items-center gap-4 text-xs text-vscode-text-dim">
              <span>Created: {new Date(task.createdAt).toLocaleTimeString()}</span>
              {task.startedAt && <span>Started: {new Date(task.startedAt).toLocaleTimeString()}</span>}
              {task.completedAt && <span>Completed: {new Date(task.completedAt).toLocaleTimeString()}</span>}
              {task.metadata?.duration && (
                <span>Duration: {Math.round(task.metadata.duration / 1000)}s</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}