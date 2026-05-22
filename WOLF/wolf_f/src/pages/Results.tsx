import React from 'react';
import { useSessionStore } from '@/store';
import ReactMarkdown from 'react-markdown';

export function Results() {
  const { sessions, currentSessionId, setCurrentSession } = useSessionStore();

  // Safely get session - handle case where session might not have taskResults
  const currentSession = React.useMemo(() => {
    const session = sessions.find(s => s.id === currentSessionId);
    if (session && !('taskResults' in session)) {
      (session as any).taskResults = [];
    }
    return session;
  }, [sessions, currentSessionId]);

  const taskResults = currentSession?.taskResults ?? [];
  const finalReport = (currentSession as any)?.finalReport;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <h1 className="text-lg font-semibold text-vscode-text mb-1">Task Results</h1>
        <p className="text-xs text-vscode-text-dim">
          View the execution results of your tasks
        </p>
      </div>

      {/* Final Report Section */}
      {finalReport && (
        <div className="px-6 py-4 border-b border-vscode-accent bg-vscode-bg-light">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-medium text-vscode-accent">Final Report</span>
            <span className="text-xs text-vscode-text-dim">— synthesized from all agents</span>
          </div>
          <div className="bg-vscode-bg border border-vscode-border rounded-sm p-4 max-h-96 overflow-y-auto">
            <ReactMarkdown className="text-sm text-vscode-text whitespace-pre-wrap">
              {finalReport}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Session selector */}
      <div className="px-6 py-3 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center gap-3">
          <span className="text-xs text-vscode-text-dim">Session:</span>
          <select
            value={currentSessionId || ''}
            onChange={(e) => setCurrentSession(e.target.value || null)}
            className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1 text-sm text-vscode-text"
          >
            {sessions.length === 0 ? (
              <option value="">No sessions</option>
            ) : (
              sessions.map(session => (
                <option key={session.id} value={session.id}>
                  {session.name} ({(session as any).taskResults?.length ?? 0} results)
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Results list */}
      <div className="flex-1 overflow-y-auto p-6">
        {!currentSessionId ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-4">📋</div>
              <div className="text-vscode-text mb-2">No session selected</div>
              <div className="text-xs text-vscode-text-dim">
                Select a session from the dropdown above
              </div>
            </div>
          </div>
        ) : taskResults.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-4">📋</div>
              <div className="text-vscode-text mb-2">No task results yet</div>
              <div className="text-xs text-vscode-text-dim">
                Go to Dashboard and submit a request to see results here
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {taskResults.map((result: any, idx: number) => (
              <div
                key={result.task_id || idx}
                className="bg-vscode-bg-light border border-vscode-border rounded-sm overflow-hidden"
              >
                {/* Result header */}
                <div className="px-4 py-3 bg-vscode-bg border-b border-vscode-border flex items-center gap-3">
                  <span className="px-2 py-1 text-xs font-medium bg-vscode-accent text-white rounded-sm uppercase">
                    {result.type || 'unknown'}
                  </span>
                  <span className="text-sm text-vscode-text font-medium flex-1">
                    {result.title || 'Untitled Task'}
                  </span>
                  <span className="text-xs text-vscode-text-dim">
                    Task #{idx + 1}
                  </span>
                </div>

                {/* Result content */}
                <div className="p-4">
                  <div className="text-xs text-vscode-text-dim mb-2 uppercase tracking-wide">
                    Result
                  </div>
                  <div className="text-sm text-vscode-text whitespace-pre-wrap font-mono bg-vscode-bg p-4 rounded-sm border border-vscode-border max-h-96 overflow-y-auto">
                    {result.result || 'No result content returned'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}