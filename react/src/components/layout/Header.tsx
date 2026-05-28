import React from 'react';
import { useUIStore } from '@/store';

export function Header() {
  const { currentView } = useUIStore();

  const titles: Record<string, string> = {
    dashboard: 'Dashboard', tasks: 'Task Center', chat: 'Chat',
    knowledge: 'Knowledge Base', settings: 'Settings',
    memory: 'Memory', git: 'Git',
    channels: 'Channels', skills: 'Skills', projects: 'Projects',
    files: 'Files', results: 'Results',
  };

  return (
    <header className="h-10 px-4 flex items-center bg-vscode-bg-light border-b border-vscode-border">
      <h1 className="text-sm font-medium text-vscode-text">
        WOLF · {titles[currentView] || 'WOLF'}
      </h1>

      <div className="ml-auto flex items-center gap-2">
        <div className="flex items-center gap-2 px-2 py-1 bg-vscode-bg-hover rounded-sm">
          <div className="w-5 h-5 bg-vscode-accent rounded-sm flex items-center justify-center text-xs text-white font-medium">U</div>
          <span className="text-xs text-vscode-text">User</span>
        </div>
      </div>
    </header>
  );
}
