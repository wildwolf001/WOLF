import React from 'react';
import { useUIStore } from '@/store';

const navItems = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'memory', label: 'Memory' },
  { id: 'git', label: 'Git' },
  { id: 'settings', label: 'Settings' },
] as const;

export function Sidebar() {
  const { currentView, setCurrentView, currentProject } = useUIStore();

  return (
    <div className="flex flex-col bg-vscode-bg-light border-r border-vscode-border" style={{ width: '200px' }}>
      <div className="panel-header">
        <span className="text-vscode-text-dim uppercase tracking-wider text-xs">Navigation</span>
      </div>

      <nav className="flex-1 py-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={`flex items-center gap-3 w-full px-4 py-2 text-sm transition-colors ${
              currentView === item.id
                ? 'bg-vscode-bg-active text-vscode-text'
                : 'text-vscode-text-dim hover:bg-vscode-bg-hover hover:text-vscode-text'
            }`}
            style={{ borderLeft: currentView === item.id ? '2px solid #007acc' : '2px solid transparent' }}
          >
            <NavIcon id={item.id} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {currentProject && (
        <div className="p-3 border-t border-vscode-border">
          <div className="text-xs text-vscode-text-dim mb-1">Active Project</div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-vscode-green"></span>
            <span className="text-xs text-vscode-text truncate flex-1">{currentProject.name}</span>
          </div>
        </div>
      )}

      <div className="p-3 border-t border-vscode-border">
        <div className="text-xs text-vscode-text-dim">WOLF v2.0</div>
      </div>
    </div>
  );
}

function NavIcon({ id }: { id: string }) {
  const icons: Record<string, React.ReactNode> = {
    dashboard: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
      </svg>
    ),
    tasks: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    memory: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    git: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
      </svg>
    ),
    settings: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  };
  return <span className="flex-shrink-0">{icons[id] || null}</span>;
}
