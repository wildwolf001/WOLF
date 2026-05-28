import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { StatusBar } from '@/components/layout/StatusBar';
import { useUIStore } from '@/store';
import { useWebSocket } from '@/hooks';
import {
  Dashboard,
  TaskCenter,
  Memory,
  Settings,
  GitPanel,
  Observability,
} from '@/pages';

function App() {
  const { currentView, setCurrentView } = useUIStore();
  useWebSocket();

  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'memory', label: 'Memory' },
    { id: 'observability', label: 'Observability' },
    { id: 'git', label: 'Git' },
    { id: 'settings', label: 'Settings' },
  ] as const;

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':     return <Dashboard />;
      case 'tasks':          return <TaskCenter />;
      case 'memory':         return <Memory />;
      case 'observability':  return <Observability />;
      case 'settings':       return <Settings />;
      case 'git':            return <GitPanel />;
      default:               return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-vscode-bg text-vscode-text">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />

        <div className="h-9 bg-vscode-bg-light flex items-center border-b border-vscode-border">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setCurrentView(tab.id)}
              className={`h-full px-4 text-xs border-r border-vscode-border transition-colors ${
                currentView === tab.id
                  ? 'bg-vscode-bg text-vscode-text border-t-2 border-t-vscode-accent'
                  : 'bg-vscode-bg-light text-vscode-text-dim hover:bg-vscode-bg-hover'
              }`}
              style={{ paddingTop: '6px', display: 'flex', alignItems: 'center' }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
          {renderContent()}
        </div>

        <StatusBar />
      </div>
    </div>
  );
}

export default App;
