import React from 'react';
import clsx from 'clsx';

interface Branch {
  name: string;
  active: boolean;
  remote: boolean;
  wolf_session: boolean;
  commits: number;
}

interface Commit {
  hash: string;
  short_hash: string;
  message: string;
  author: string;
  date: string;
}

interface DiffFile {
  status: string;
  file: string;
}

interface GitStatus {
  current_branch: string;
  has_changes: boolean;
  changed_count: number;
  ahead: number;
  behind: number;
  stat: string;
  git_available: boolean;
}

const statusColor: Record<string, string> = {
  'M': 'bg-vscode-yellow',
  'A': 'bg-vscode-green',
  'D': 'bg-vscode-red',
  'R': 'bg-vscode-blue',
  '??': 'bg-vscode-purple',
};

const statusLabel: Record<string, string> = {
  'M': 'Modified',
  'A': 'Added',
  'D': 'Deleted',
  'R': 'Renamed',
  '??': 'New',
};

export function GitPanel() {
  const [status, setStatus] = React.useState<GitStatus | null>(null);
  const [branches, setBranches] = React.useState<Branch[]>([]);
  const [commits, setCommits] = React.useState<Commit[]>([]);
  const [selectedCommit, setSelectedCommit] = React.useState<Commit | null>(null);
  const [diffData, setDiffData] = React.useState<{ diff: string; files: DiffFile[]; stat: string } | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([fetchStatus(), fetchBranches(), fetchCommits()]);
    setLoading(false);
  };

  const fetchStatus = async () => {
    try {
      const r = await fetch('/api/git/status');
      if (r.ok) setStatus(await r.json());
    } catch {}
  };

  const fetchBranches = async () => {
    try {
      const r = await fetch('/api/git/branches');
      if (r.ok) {
        const data = await r.json();
        setBranches(data.branches || []);
      }
    } catch {}
  };

  const fetchCommits = async (branch?: string) => {
    try {
      const url = branch ? `/api/git/log?branch=${encodeURIComponent(branch)}&limit=30` : '/api/git/log?limit=30';
      const r = await fetch(url);
      if (r.ok) {
        const data = await r.json();
        setCommits(data.commits || []);
      }
    } catch {}
  };

  const fetchDiff = async (commit: Commit) => {
    setSelectedCommit(commit);
    try {
      const r = await fetch(`/api/git/diff?commit=${commit.hash}`);
      if (r.ok) setDiffData(await r.json());
    } catch {}
  };

  const doAction = async (endpoint: string, body?: object) => {
    setActionLoading(endpoint);
    try {
      const r = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await r.json();
      if (r.ok) {
        await fetchAll();
        if (data.current_branch) {
          await fetchCommits(data.current_branch);
        }
      } else {
        alert(data.detail || data.message || 'Action failed');
      }
    } catch (e) {
      alert('Action failed: ' + String(e));
    } finally {
      setActionLoading(null);
    }
  };

  const handleRollback = async (commit: Commit, mode: 'soft' | 'hard') => {
    if (mode === 'hard' && !confirm(`Hard reset to "${commit.short_hash}"? All changes after this commit will be PERMANENTLY lost.`)) return;
    await doAction(`/api/git/rollback?commit=${commit.hash}&mode=${mode}`);
  };

  const handleAccept = async (branch: string) => {
    if (!confirm(`Merge "${branch}" into main?`)) return;
    await doAction(`/api/git/accept?branch=${encodeURIComponent(branch)}`);
  };

  const handleDiscard = async (branch: string) => {
    if (!confirm(`Permanently discard branch "${branch}"? All its commits will be lost.`)) return;
    await doAction(`/api/git/discard?branch=${encodeURIComponent(branch)}`);
  };

  const handleSwitch = async (branch: string) => {
    await doAction(`/api/git/switch?branch=${encodeURIComponent(branch)}`);
    await fetchCommits(branch);
  };

  const activeBranch = status?.current_branch || '';
  const hasActiveWolfSession = activeBranch.startsWith('wolf/');

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-vscode-text-dim">Loading git status...</div>
      </div>
    );
  }

  if (!status?.git_available) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4">📦</div>
          <div className="text-vscode-text mb-2">Git repository not detected</div>
          <div className="text-xs text-vscode-text-dim">WOLF auto-initializes git on first use. Refresh if the repo exists.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Top status bar */}
      <div className="px-4 py-2 border-b border-vscode-border bg-vscode-bg-light flex items-center gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className={clsx('w-2 h-2 rounded-full', hasActiveWolfSession ? 'bg-vscode-green' : 'bg-vscode-blue')} />
          <span className="text-vscode-text font-mono">{activeBranch}</span>
        </span>
        {status.ahead > 0 && (
          <span className="text-vscode-green">↑{status.ahead} ahead of main</span>
        )}
        {status.behind > 0 && (
          <span className="text-vscode-yellow">↓{status.behind} behind main</span>
        )}
        <span className="text-vscode-text-dim">{status.stat}</span>
        {status.changed_count > 0 && (
          <span className="text-vscode-yellow">{status.changed_count} file(s) changed</span>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Branches */}
        <div className="w-64 border-r border-vscode-border flex flex-col overflow-hidden bg-vscode-bg-light">
          <div className="p-3 border-b border-vscode-border">
            <h2 className="text-xs font-medium text-vscode-text uppercase">Branches</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {branches.map(b => (
              <div
                key={b.name}
                className={clsx(
                  'px-3 py-2 cursor-pointer hover:bg-vscode-bg-hover border-l-2',
                  b.active
                    ? 'border-l-vscode-accent bg-vscode-bg text-vscode-text'
                    : 'border-l-transparent text-vscode-text-dim'
                )}
                onClick={() => { fetchCommits(b.name); }}
              >
                <div className="flex items-center gap-1 text-xs">
                  <span className={clsx('w-1.5 h-1.5 rounded-full', b.active ? 'bg-vscode-green' : 'bg-vscode-text-dim')} />
                  <span className="font-mono truncate">{b.name}</span>
                  {b.wolf_session && <span className="text-vscode-accent text-xs ml-1">🐺</span>}
                </div>
                <div className="text-xs text-vscode-text-dim ml-2.5">{b.commits} commits</div>
              </div>
            ))}
          </div>

          {/* Actions */}
          {hasActiveWolfSession && (
            <div className="border-t border-vscode-border p-3 space-y-2">
              <button
                onClick={() => handleAccept(activeBranch)}
                disabled={actionLoading !== null}
                className="w-full px-3 py-1.5 text-xs bg-vscode-green text-white rounded-sm hover:bg-green-700 disabled:opacity-50"
              >
                ✓ Accept All Changes
              </button>
              <button
                onClick={() => handleDiscard(activeBranch)}
                disabled={actionLoading !== null}
                className="w-full px-3 py-1.5 text-xs bg-vscode-red/20 text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/30 disabled:opacity-50"
              >
                ✗ Discard Branch
              </button>
              <button
                onClick={() => handleSwitch('main')}
                disabled={actionLoading !== null}
                className="w-full px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover disabled:opacity-50"
              >
                ↺ Switch to main
              </button>
            </div>
          )}
        </div>

        {/* Center: Commit history */}
        <div className="flex-1 flex flex-col overflow-hidden border-r border-vscode-border">
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light">
            <h2 className="text-xs font-medium text-vscode-text uppercase">
              Commits {activeBranch && <span className="text-vscode-text-dim font-normal">— {activeBranch}</span>}
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {commits.length === 0 ? (
              <div className="text-xs text-vscode-text-dim p-4 text-center">No commits yet</div>
            ) : (
              <div className="space-y-1">
                {commits.map((commit, i) => (
                  <div
                    key={commit.hash}
                    onClick={() => fetchDiff(commit)}
                    className={clsx(
                      'p-2 rounded-sm cursor-pointer hover:bg-vscode-bg-hover transition-colors border-l-2',
                      selectedCommit?.hash === commit.hash
                        ? 'border-l-vscode-accent bg-vscode-bg'
                        : 'border-l-transparent'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-vscode-text font-mono">{commit.short_hash}</span>
                      <div className="flex items-center gap-1 opacity-0 hover:opacity-100">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRollback(commit, 'soft'); }}
                          className="px-1.5 py-0.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-yellow/20"
                          title="Soft reset — keep changes in working tree"
                        >
                          ↩ Soft
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRollback(commit, 'hard'); }}
                          className="px-1.5 py-0.5 text-xs bg-vscode-red/20 text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/30"
                          title="Hard reset — permanently discard changes"
                        >
                          ↩ Hard
                        </button>
                      </div>
                    </div>
                    <div className="text-sm text-vscode-text mt-0.5">{commit.message}</div>
                    <div className="text-xs text-vscode-text-dim mt-0.5">
                      {commit.date?.split(' ').slice(0, 2).join(' ')} · {commit.author}
                    </div>
                    {i < commits.length - 1 && (
                      <div className="ml-1.5 my-1 w-px h-3 bg-vscode-border" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Diff detail */}
        <div className="w-96 flex flex-col overflow-hidden bg-vscode-bg-light">
          <div className="p-3 border-b border-vscode-border">
            <h2 className="text-xs font-medium text-vscode-text uppercase">
              Diff {selectedCommit && <span className="text-vscode-text-dim font-mono font-normal">— {selectedCommit.short_hash}</span>}
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {!selectedCommit ? (
              <div className="text-xs text-vscode-text-dim text-center pt-8">
                Click a commit to see its changes
              </div>
            ) : !diffData ? (
              <div className="text-xs text-vscode-text-dim text-center pt-8">Loading diff...</div>
            ) : (
              <div className="space-y-3">
                {/* Files list */}
                {diffData.files.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs text-vscode-text-dim font-medium uppercase">Changed Files</div>
                    {diffData.files.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className={clsx('px-1 rounded text-white text-xs', statusColor[f.status] || 'bg-vscode-text-dim')}>
                          {f.status}
                        </span>
                        <span className="text-vscode-text font-mono">{f.file}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Diff content */}
                {diffData.diff && (
                  <div>
                    <div className="text-xs text-vscode-text-dim font-medium uppercase mb-1">Diff</div>
                    <pre className="text-xs text-vscode-text bg-vscode-bg p-2 rounded-sm overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed max-h-96">
                      {diffData.diff.split('\n').map((line, i) => {
                        let color = 'text-vscode-text';
                        if (line.startsWith('+')) color = 'text-vscode-green';
                        else if (line.startsWith('-')) color = 'text-vscode-red';
                        else if (line.startsWith('@@')) color = 'text-vscode-blue';
                        else if (line.startsWith('diff') || line.startsWith('index') || line.startsWith('---') || line.startsWith('+++'))
                          color = 'text-vscode-text-dim';
                        return <div key={i} className={color}>{line}</div>;
                      })}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
