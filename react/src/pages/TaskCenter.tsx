import React from 'react';
import clsx from 'clsx';
import { useTaskStore, useUIStore } from '@/store';

interface PlannedTask {
  id: string;
  subject: string;
  description: string;
  activeForm?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'deleted';
  blocks: string[];
  blockedBy: string[];
  owner?: string | null;
  created_at: number;
  metadata?: Record<string, any>;
}

interface TaskSummary {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
}

const STATUS_ICON: Record<string, string> = {
  in_progress: '\u25CF',
  pending: '\u25CB',
  completed: '\u2713',
  deleted: '\u2715',
};

const STATUS_COLOR: Record<string, string> = {
  in_progress: 'text-yellow-400',
  pending: 'text-gray-400',
  completed: 'text-green-400',
  deleted: 'text-red-400',
};

export function TaskCenter() {
  const [tasks, setTasks] = React.useState<PlannedTask[]>([]);
  const [summary, setSummary] = React.useState<TaskSummary>({ total: 0, pending: 0, in_progress: 0, completed: 0 });
  const [loading, setLoading] = React.useState(true);
  const { tokenUsage, tokenLimit } = useUIStore();

  const bgTasks = useTaskStore(s => {
    const all: Array<{id:string;name:string;description?:string;status:string;startedAt?:number;completedAt?:number;result?:any;error?:string}> = [];
    s.backgroundTasks.forEach(v => all.push(v));
    return all.sort((a,b) => (b.startedAt||0) - (a.startedAt||0));
  });

  const fetchTasks = React.useCallback(async () => {
    try {
      const res = await fetch('/api/tasks');
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
        setSummary(data.summary || { total: 0, pending: 0, in_progress: 0, completed: 0 });
      }
    } catch (e) {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const grouped = {
    in_progress: tasks.filter(t => t.status === 'in_progress'),
    pending: tasks.filter(t => t.status === 'pending'),
    completed: tasks.filter(t => t.status === 'completed'),
  };

  const hasBgTasks = bgTasks.length > 0;
  const hasPlannedTasks = tasks.length > 0;
  const runningBg = bgTasks.filter(t => t.status === 'running').length;
  const doneBg = bgTasks.filter(t => t.status === 'completed' || t.status === 'failed').length;
  const pct = tokenLimit > 0 ? Math.min(100, (tokenUsage / tokenLimit) * 100) : 0;

  const renderPlannedTask = (task: PlannedTask) => (
    <div
      key={task.id}
      className="p-3 bg-gray-800/50 border border-gray-700 rounded-sm hover:border-gray-600 transition-colors"
    >
      <div className="flex items-start gap-2">
        <span className={clsx('text-sm mt-0.5', STATUS_COLOR[task.status])}>
          {STATUS_ICON[task.status]}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx(
              'text-sm font-medium',
              task.status === 'completed' ? 'text-gray-500 line-through' : 'text-gray-200'
            )}>
              {task.subject}
            </span>
            {task.owner && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-700 rounded text-gray-400">
                {task.owner}
              </span>
            )}
          </div>
          {task.description && (
            <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{task.description}</div>
          )}
          {(task.blocks.length > 0 || task.blockedBy.length > 0) && (
            <div className="flex gap-2 mt-1 text-xs text-gray-600">
              {task.blockedBy.length > 0 && <span>waiting: #{task.blockedBy.join(', #')}</span>}
              {task.blocks.length > 0 && <span>blocks: #{task.blocks.join(', #')}</span>}
            </div>
          )}
        </div>
        <span className="text-xs text-gray-600 whitespace-nowrap">#{task.id}</span>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-gray-500 text-sm">Loading...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/50 flex items-center justify-between">
        <h1 className="text-sm font-semibold text-gray-200">Project Dashboard</h1>
        <div className="flex items-center gap-4 text-xs">
          {hasPlannedTasks && (
            <>
              <span className="text-yellow-400">{summary.in_progress} active</span>
              <span className="text-gray-400">{summary.pending} pending</span>
              <span className="text-green-400">{summary.completed} done</span>
              <span className="text-gray-600">|</span>
            </>
          )}
          {hasBgTasks && (
            <>
              <span className="text-blue-400">{runningBg} running</span>
              <span className="text-gray-400">{doneBg} finished</span>
              <span className="text-gray-600">|</span>
            </>
          )}
          <span className="text-gray-500">token</span>
          <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={clsx('h-full transition-all rounded-full',
                pct > 90 ? 'bg-red-500' : pct > 70 ? 'bg-yellow-500' : 'bg-green-500'
              )}
              style={{ width: `${Math.max(2, pct)}%` }}
            />
          </div>
          <span className="font-mono text-gray-400">{tokenUsage}/{tokenLimit}</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Empty state */}
        {!hasBgTasks && !hasPlannedTasks && (
          <div className="flex flex-col items-center justify-center py-12 gap-2">
            <span className="text-gray-500 text-sm">No activity yet</span>
            <span className="text-gray-600 text-xs text-center max-w-sm">
              When the AI starts working, tool executions will appear here in real-time.
              Complex tasks split with TaskCreate will show a structured progress board.
            </span>
          </div>
        )}

        {/* Running tools (live) */}
        {runningBg > 0 && (
          <div>
            <div className="text-xs font-medium text-blue-400 mb-2 uppercase tracking-wide">
              Live — {runningBg} running
            </div>
            <div className="space-y-1">
              {bgTasks.filter(t => t.status === 'running').map(t => (
                <div key={t.id} className="flex items-center gap-2 px-3 py-2 bg-gray-800/30 rounded text-xs">
                  <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                  <span className="font-medium text-gray-200">{t.name}</span>
                  <span className="text-gray-500 font-mono truncate">{t.description || ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Planned tasks — in progress */}
        {grouped.in_progress.length > 0 && (
          <div>
            <div className="text-xs font-medium text-yellow-400 mb-2 uppercase tracking-wide">
              Active
            </div>
            <div className="space-y-2">
              {grouped.in_progress.map(renderPlannedTask)}
            </div>
          </div>
        )}

        {/* Planned tasks — pending */}
        {grouped.pending.length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wide">
              Planned
            </div>
            <div className="space-y-2">
              {grouped.pending.map(renderPlannedTask)}
            </div>
          </div>
        )}

        {/* Planned tasks — completed */}
        {grouped.completed.length > 0 && (
          <div>
            <div className="text-xs font-medium text-green-400 mb-2 uppercase tracking-wide">
              Completed
            </div>
            <div className="space-y-2 opacity-60">
              {grouped.completed.slice(-10).map(renderPlannedTask)}
            </div>
          </div>
        )}

        {/* Completed tool history */}
        {doneBg > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
              Tool History — {doneBg} executions
            </div>
            <div className="space-y-0.5 opacity-50">
              {bgTasks.filter(t => t.status !== 'running').slice(0, 20).map(t => (
                <div key={t.id} className="flex items-center gap-2 px-2 py-0.5 text-xs">
                  <span className={clsx('w-1.5 h-1.5 rounded-full', t.status === 'completed' ? 'bg-green-400' : 'bg-red-400')} />
                  <span className="text-gray-400">{t.name}</span>
                  <span className="text-gray-600 font-mono truncate">{t.description || ''}</span>
                  <span className="text-gray-600 ml-auto">{t.status === 'completed' ? 'ok' : 'fail'}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
