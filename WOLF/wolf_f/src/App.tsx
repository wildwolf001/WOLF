import clsx from 'clsx';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { useUIStore } from '@/store';
import { useWebSocket } from '@/hooks';
import {
  Dashboard,
  TaskCenter,
  Results,
  Knowledge,
  Settings,
  Files,
  Memory,
  // Team, // DEPRECATED: removed multi-agent team page
  Channels,
  Skills,
  Projects,
} from '@/pages';

function App() {
  const { currentView, setCurrentView } = useUIStore();
  useWebSocket();

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'tasks':
        return <TaskCenter />;
      case 'results':
        return <Results />;
      case 'knowledge':
        return <Knowledge />;
      case 'settings':
        return <Settings />;
      case 'files':
        return <Files />;
      case 'memory':
        return <Memory />;
      // DEPRECATED: 'team' and 'chat' pages removed - single agent mode
      case 'channels':
        return <Channels />;
      case 'skills':
        return <Skills />;
      case 'projects':
        return <Projects />;
      default:
        return <Dashboard />;
    }
  };

  // DEPRECATED: tabs array simplified - 'team' tab removed
  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'tasks', label: 'Task Center' },
    { id: 'results', label: 'Results' },
    { id: 'memory', label: 'Memory' },
    // DEPRECATED: 'team' and 'chat' tabs removed - single agent mode
    { id: 'channels', label: 'Channels' },
    { id: 'skills', label: 'Skills' },
    { id: 'files', label: 'Projects' },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-vscode-bg text-vscode-text">
      {/* Sidebar with navigation */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header />

        {/* Tab bar */}
        <div className="h-9 bg-vscode-bg-light flex items-center border-b border-vscode-border">
          {tabs.map((tab) => (
            <TabItem
              key={tab.id}
              label={tab.label}
              active={currentView === tab.id}
              onClick={() => setCurrentView(tab.id as typeof currentView)}
            />
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
          {renderContent()}
        </div>

        {/* Status bar */}
        <StatusBar />
      </div>
    </div>
  );
}

function TabItem({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'h-full px-4 text-xs border-r border-vscode-border transition-colors',
        active
          ? 'bg-vscode-bg text-vscode-text border-t-2 border-t-vscode-accent'
          : 'bg-vscode-bg-light text-vscode-text-dim hover:bg-vscode-bg-hover'
      )}
      style={{ paddingTop: '6px', display: 'flex', alignItems: 'center' }}
    >
      {label}
    </button>
  );
}

function StatusBar() {
  return (
    <div className="h-6 bg-vscode-accent flex items-center px-2 text-xs text-white">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-400"></span>
          Ready
        </span>
        <span>main</span>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <span>UTF-8</span>
        <span>JavaScript</span>
        <span>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    </div>
  );
}

export default App;