import React from 'react';
import clsx from 'clsx';
import { logsService, type BackendLog } from '@/services/logsService';

interface BackendLogsProps {
  maxHeight?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const levelColors: Record<string, string> = {
  debug: 'text-vscode-text-dim',
  info: 'text-vscode-blue',
  warn: 'text-vscode-yellow',
  error: 'text-vscode-red',
};

const sourceColors: Record<string, string> = {
  backend: 'bg-vscode-purple',
  agent: 'bg-vscode-blue',
  workflow: 'bg-vscode-green',
  tool: 'bg-vscode-orange',
  mcp: 'bg-vscode-cyan',
  query: 'bg-vscode-pink',
  tasks: 'bg-vscode-teal',
};

export function BackendLogs({ maxHeight = '400px', autoRefresh = true, refreshInterval = 2000 }: BackendLogsProps) {
  const [logs, setLogs] = React.useState<BackendLog[]>([]);
  const [filter, setFilter] = React.useState<'all' | 'debug' | 'info' | 'warn' | 'error'>('all');
  const [sourceFilter, setSourceFilter] = React.useState<'all' | 'backend' | 'agent' | 'workflow' | 'tool' | 'mcp' | 'query' | 'tasks'>('all');
  const [isConnected, setIsConnected] = React.useState(false);
  const [stats, setStats] = React.useState<{ size: number; lines: number } | null>(null);
  const logsEndRef = React.useRef<HTMLDivElement>(null);
  const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll for new logs
  React.useEffect(() => {
    const loadLogs = async () => {
      try {
        const { logs: newLogs } = await logsService.getLogs({}, 500);

        // Only update if we got new logs
        if (newLogs.length > 0) {
          setLogs(newLogs);
        }
        // If newLogs is empty, keep existing logs - don't clear them

        setIsConnected(true);

        // Get stats (non-blocking, ignore errors)
        try {
          const logStats = await logsService.getStats();
          setStats({ size: logStats.size, lines: logStats.lines });
        } catch {
          // Stats is optional, ignore
        }
      } catch (error) {
        console.error('Failed to load logs:', error);
        // Keep showing last logs on error - don't clear state
      }
    };

    // Initial load
    loadLogs();

    // Set up polling
    if (autoRefresh) {
      intervalRef.current = setInterval(loadLogs, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval]);

  // Auto-scroll to bottom
  React.useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Clear logs
  const handleClear = async () => {
    try {
      await logsService.clearLogs();
      setLogs([]);
      logsService.resetPosition();
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  };

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    if (filter !== 'all' && log.level !== filter) return false;
    if (sourceFilter !== 'all' && log.source !== sourceFilter) return false;
    return true;
  });

  return (
    <div className="flex flex-col overflow-hidden border-r border-vscode-border" style={{ height: maxHeight }}>
      {/* Header */}
      <div className="px-3 py-2 border-b border-vscode-border bg-vscode-bg-light flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-medium text-vscode-text uppercase">Backend Logs</h3>
          <span className={clsx(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-vscode-green animate-pulse' : 'bg-vscode-text-dim'
          )} />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="bg-vscode-bg border border-vscode-border rounded-sm px-1 py-0.5 text-xs text-vscode-text"
          >
            <option value="all">All</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warn">Warn</option>
            <option value="error">Error</option>
          </select>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as typeof sourceFilter)}
            className="bg-vscode-bg border border-vscode-border rounded-sm px-1 py-0.5 text-xs text-vscode-text"
          >
            <option value="all">All Sources</option>
            <option value="backend">Backend</option>
            <option value="agent">Agent</option>
            <option value="workflow">Workflow</option>
            <option value="tool">Tool</option>
            <option value="mcp">MCP</option>
            <option value="query">Query</option>
            <option value="tasks">Tasks</option>
          </select>
          <button
            onClick={handleClear}
            className="text-xs text-vscode-text-dim hover:text-vscode-text"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Log list */}
      <div className="flex-1 overflow-y-auto p-2 bg-vscode-bg font-mono text-xs">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-vscode-text-dim py-4">
            No logs yet
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className={clsx('p-1 rounded mb-1', levelColors[log.level])}
            >
              <div className="flex items-start gap-2">
                <span className="text-vscode-text-dim whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={clsx('px-1 py-0.5 rounded text-xs text-white', sourceColors[log.source])}>
                  {log.source}
                </span>
                <span className={clsx('px-1 py-0.5 rounded text-xs uppercase', levelColors[log.level])}>
                  {log.level}
                </span>
                <span className="flex-1 break-all">{log.message}</span>
              </div>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      {/* Footer */}
      <div className="px-3 py-1 border-t border-vscode-border bg-vscode-bg-light flex items-center justify-between text-xs text-vscode-text-dim">
        <span>{filteredLogs.length} logs</span>
        <span>Total: {logs.length}{stats ? ` | ${stats.lines} lines in log file` : ''}</span>
      </div>
    </div>
  );
}
