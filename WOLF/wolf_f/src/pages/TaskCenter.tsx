import React, { useState } from 'react';
import { TaskBoard, BackgroundTasks } from '@/components/task';

type ViewMode = 'board' | 'background';

export function TaskCenter() {
  const [viewMode, setViewMode] = useState<ViewMode>('board');

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* View toggle */}
      <div className="px-4 py-3 border-b border-vscode-border bg-vscode-bg-light flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold text-vscode-text">Task Center</h1>
          <div className="flex gap-1">
            <button
              onClick={() => setViewMode('board')}
              className={`px-3 py-1 text-xs rounded-sm transition-colors ${
                viewMode === 'board'
                  ? 'bg-vscode-accent text-white'
                  : 'bg-vscode-bg text-vscode-text-dim hover:text-vscode-text'
              }`}
            >
              Task Board
            </button>
            <button
              onClick={() => setViewMode('background')}
              className={`px-3 py-1 text-xs rounded-sm transition-colors ${
                viewMode === 'background'
                  ? 'bg-vscode-accent text-white'
                  : 'bg-vscode-bg text-vscode-text-dim hover:text-vscode-text'
              }`}
            >
              Background Tasks
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'board' ? <TaskBoard /> : <BackgroundTasks />}
      </div>
    </div>
  );
}
