import React from 'react';
import { useUIStore } from '@/store';

export function Header() {
  const { currentView } = useUIStore();

  const titles: Record<string, string> = {
    dashboard: 'Dashboard',
    tasks: 'Task Center',
    chat: 'Chat',
    knowledge: 'Knowledge Base',
    settings: 'Settings',
    memory: 'Memory',
    channels: 'Channels',
    skills: 'Skills',
    projects: 'Projects',
    files: 'Files',
    results: 'Results',
  };

  return (
    <header className="h-10 px-4 flex items-center bg-vscode-bg-light border-b border-vscode-border">
      <h1 className="text-sm font-medium text-vscode-text">
        {titles[currentView] || 'WOLF'}
      </h1>

      <div className="ml-auto flex items-center gap-2">
        {/* Search */}
        <div className="flex items-center gap-1 px-2 py-1 bg-vscode-bg rounded-sm border border-vscode-border text-xs text-vscode-text-dim hover:border-vscode-accent transition-colors">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span>Search</span>
          <kbd className="px-1 bg-vscode-bg-lighter rounded text-vscode-text-dim">Ctrl+P</kbd>
        </div>

        {/* User */}
        <div className="flex items-center gap-2 px-2 py-1 bg-vscode-bg-hover rounded-sm">
          <div className="w-5 h-5 bg-vscode-accent rounded-sm flex items-center justify-center text-xs text-white font-medium">
            U
          </div>
          <span className="text-xs text-vscode-text">User</span>
        </div>
      </div>
    </header>
  );
}