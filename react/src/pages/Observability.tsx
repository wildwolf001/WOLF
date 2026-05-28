import React from 'react';
import { API_CONFIG, getApiUrl } from '@/config/api';
import { useUIStore } from '@/store';
import clsx from 'clsx';

interface LLMStats {
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  by_model: Record<string, {
    calls: number;
    input: number;
    output: number;
    total_latency: number;
    failures: number;
    avg_latency_ms: number;
    success_rate: number;
  }>;
}

interface CostData {
  daily_input_tokens: number;
  daily_output_tokens: number;
  daily_cost: number;
  token_ratio: number;
  cost_ratio: number;
  alert: string;
  suggested_model: string | null;
}

interface SystemStatus {
  server: string;
  subsystems: Record<string, {
    initialized: boolean;
    total?: number;
    doc_count?: number;
    names?: string[];
    active_flags?: string[];
    [key: string]: any;
  }>;
}

const MODEL_COLORS: Record<string, string> = {
  'minimax': '#f14c4c',
  'deepseek': '#4ec9b0',
  'openai': '#569cd6',
  'anthropic': '#dcdcaa',
  'qwen': '#c586c0',
  'zhipu': '#569cd6',
  'moonshot': '#4ec9b0',
};

function getModelColor(model: string): string {
  for (const [key, color] of Object.entries(MODEL_COLORS)) {
    if (model.toLowerCase().includes(key)) return color;
  }
  return '#858585';
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

export function Observability() {
  const { tokenUsage, tokenLimit } = useUIStore();

  const [llmStats, setLlmStats] = React.useState<LLMStats | null>(null);
  const [costData, setCostData] = React.useState<CostData | null>(null);
  const [systemStatus, setSystemStatus] = React.useState<SystemStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [autoRefresh, setAutoRefresh] = React.useState(true);

  const fetchData = React.useCallback(async () => {
    try {
      const [obsRes, sysRes] = await Promise.all([
        fetch(getApiUrl(API_CONFIG.endpoints.systemObservability)),
        fetch(getApiUrl(API_CONFIG.endpoints.systemStatus)),
      ]);
      if (obsRes.ok) {
        const obsData = await obsRes.json();
        setLlmStats(obsData.llm_stats);
        setCostData(obsData.cost);
      }
      if (sysRes.ok) {
        const sysData = await sysRes.json();
        setSystemStatus(sysData);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 15s
  React.useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-vscode-text-dim">Loading observability data...</div>
      </div>
    );
  }

  const maxModelCalls = llmStats?.by_model ? Math.max(...Object.values(llmStats.by_model).map(m => m.calls), 1) : 1;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text">Observability Dashboard</h1>
            <p className="text-xs text-vscode-text-dim mt-1">LLM call traces, token usage, cost tracking, system health</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-vscode-text-dim">
              <input type="checkbox" checked={autoRefresh} onChange={() => setAutoRefresh(!autoRefresh)} className="accent-vscode-accent" />
              Auto-refresh (15s)
            </label>
            <button onClick={fetchData} className="px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover">Refresh</button>
          </div>
        </div>

        {/* System Subsystems Health */}
        {systemStatus && (
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-3">System Subsystems</h2>
            <div className="grid grid-cols-7 gap-3">
              {Object.entries(systemStatus.subsystems).map(([key, val]) => (
                <div key={key} className="text-center p-3 bg-vscode-bg rounded-sm">
                  <div className={clsx('w-3 h-3 rounded-full mx-auto mb-2', val.initialized ? 'bg-vscode-green' : 'bg-vscode-red')} />
                  <div className="text-xs text-vscode-text capitalize">{key.replace('_', ' ')}</div>
                  <div className="text-xs text-vscode-text-dim mt-0.5">
                    {val.doc_count !== undefined ? `${val.doc_count} docs` :
                     val.total !== undefined ? `${val.total} items` :
                     val.initialized ? 'OK' : 'OFF'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">
          {/* LLM Call Stats */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">LLM Call Statistics</h2>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-accent">{llmStats?.total_calls || 0}</div>
                <div className="text-xs text-vscode-text-dim">Total Calls</div>
              </div>
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-green">{formatTokens(llmStats?.total_input_tokens || 0)}</div>
                <div className="text-xs text-vscode-text-dim">Input Tokens</div>
              </div>
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-yellow">{formatTokens(llmStats?.total_output_tokens || 0)}</div>
                <div className="text-xs text-vscode-text-dim">Output Tokens</div>
              </div>
            </div>

            {/* Per-Model breakdown */}
            {llmStats?.by_model && Object.keys(llmStats.by_model).length > 0 && (
              <div className="space-y-3">
                {Object.entries(llmStats.by_model).map(([model, stats]) => {
                  const barWidth = Math.max(Math.round(stats.calls / maxModelCalls * 100), 3);
                  return (
                    <div key={model}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getModelColor(model) }} />
                          <span className="text-vscode-text font-medium">{model}</span>
                        </div>
                        <span className="text-vscode-text-dim">{stats.calls} calls</span>
                      </div>
                      <div className="h-2 bg-vscode-bg rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${barWidth}%`, backgroundColor: getModelColor(model) }} />
                      </div>
                      <div className="flex gap-4 mt-1 text-xs text-vscode-text-dim">
                        <span>{formatTokens(stats.input + stats.output)} tokens</span>
                        <span>{formatMs(stats.avg_latency_ms)} avg</span>
                        <span className={stats.success_rate < 90 ? 'text-vscode-red' : 'text-vscode-green'}>{stats.success_rate}% success</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {(!llmStats?.by_model || Object.keys(llmStats.by_model).length === 0) && (
              <div className="text-xs text-vscode-text-dim text-center py-8">No LLM calls recorded yet. Send a message in Dashboard to see stats.</div>
            )}
          </div>

          {/* Cost & Budget */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">Cost & Budget</h2>

            {costData ? (
              <>
                {/* Alert banner */}
                {costData.alert !== 'OK' && (
                  <div className={clsx('mb-3 p-3 rounded-sm text-xs', costData.alert === 'CRITICAL' ? 'bg-vscode-red/20 text-vscode-red border border-vscode-red/30' : 'bg-vscode-yellow/20 text-vscode-yellow border border-vscode-yellow/30')}>
                    {costData.alert === 'CRITICAL' ? 'Budget limit reached!' : 'Approaching budget limit'}
                    {costData.suggested_model && (
                      <span className="ml-2">— Consider switching to <span className="font-medium">{costData.suggested_model}</span></span>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-vscode-bg rounded-sm p-3">
                    <div className="text-2xl font-bold text-vscode-accent">${costData.daily_cost.toFixed(4)}</div>
                    <div className="text-xs text-vscode-text-dim">Today's Cost</div>
                  </div>
                  <div className="bg-vscode-bg rounded-sm p-3">
                    <div className="text-2xl font-bold text-vscode-purple">{formatTokens(costData.daily_input_tokens + costData.daily_output_tokens)}</div>
                    <div className="text-xs text-vscode-text-dim">Today's Tokens</div>
                  </div>
                </div>

                {/* Token usage bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-vscode-text-dim">Token Budget</span>
                    <span className={clsx('font-medium', costData.token_ratio >= 1 ? 'text-vscode-red' : costData.token_ratio >= 0.8 ? 'text-vscode-yellow' : 'text-vscode-text-dim')}>
                      {Math.round(costData.token_ratio * 100)}%
                    </span>
                  </div>
                  <div className="h-3 bg-vscode-bg rounded-full overflow-hidden">
                    <div
                      className={clsx('h-full rounded-full transition-all', costData.token_ratio >= 1 ? 'bg-vscode-red' : costData.token_ratio >= 0.8 ? 'bg-vscode-yellow' : 'bg-vscode-green')}
                      style={{ width: `${Math.min(costData.token_ratio * 100, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-vscode-text-dim mt-1">
                    <span>0</span>
                    <span>80% alert threshold</span>
                    <span>100%</span>
                  </div>
                </div>

                {/* Cost bar */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-vscode-text-dim">Cost Budget ($50/day)</span>
                    <span className={clsx('font-medium', costData.cost_ratio >= 1 ? 'text-vscode-red' : costData.cost_ratio >= 0.8 ? 'text-vscode-yellow' : 'text-vscode-text-dim')}>
                      {Math.round(costData.cost_ratio * 100)}%
                    </span>
                  </div>
                  <div className="h-3 bg-vscode-bg rounded-full overflow-hidden">
                    <div
                      className={clsx('h-full rounded-full transition-all', costData.cost_ratio >= 1 ? 'bg-vscode-red' : costData.cost_ratio >= 0.8 ? 'bg-vscode-yellow' : 'bg-vscode-green')}
                      style={{ width: `${Math.min(costData.cost_ratio * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="text-xs text-vscode-text-dim text-center py-8">Cost data unavailable</div>
            )}
          </div>
        </div>

        {/* Session Token Usage (from UI store) */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
          <h2 className="text-sm font-medium text-vscode-text mb-3">Current Session Token Usage</h2>
          <div className="flex items-center gap-4 mb-2">
            <span className="text-xs text-vscode-text-dim">Used:</span>
            <span className="text-sm text-vscode-text font-mono">{formatTokens(tokenUsage)} / {formatTokens(tokenLimit)}</span>
          </div>
          <div className="h-3 bg-vscode-bg rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full', tokenUsage / tokenLimit > 0.9 ? 'bg-vscode-red' : tokenUsage / tokenLimit > 0.7 ? 'bg-vscode-yellow' : 'bg-vscode-accent')}
              style={{ width: `${Math.min(tokenUsage / tokenLimit * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Agentic RAG Status */}
        {systemStatus?.subsystems?.vector_store && (
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-3">
              Agentic RAG Status
              <span className="text-xs text-vscode-text-dim font-normal ml-2">Vector + Knowledge Graph + Error Book</span>
            </h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-accent">{systemStatus.subsystems.vector_store.doc_count ?? 0}</div>
                <div className="text-xs text-vscode-text-dim">Vector Docs</div>
              </div>
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-purple">{systemStatus.subsystems.vector_store.kg_nodes ?? 0}</div>
                <div className="text-xs text-vscode-text-dim">KG Nodes</div>
              </div>
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-green">{systemStatus.subsystems.vector_store.kg_edges ?? 0}</div>
                <div className="text-xs text-vscode-text-dim">KG Edges</div>
              </div>
              <div className="bg-vscode-bg rounded-sm p-3 text-center">
                <div className="text-2xl font-bold text-vscode-yellow">{
                  systemStatus.subsystems.vector_store.error_book?.total_errors ?? 0
                }</div>
                <div className="text-xs text-vscode-text-dim">Errors Tracked</div>
              </div>
            </div>
            {/* Error Book detail */}
            {systemStatus.subsystems.vector_store.error_book && (
              <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                <div className="flex items-center justify-between bg-vscode-bg rounded-sm px-3 py-2">
                  <span className="text-vscode-text-dim">Resolution Rate</span>
                  <span className="text-vscode-green font-medium">{
                    systemStatus.subsystems.vector_store.error_book.resolution_rate ?? 0
                  }%</span>
                </div>
                <div className="flex items-center justify-between bg-vscode-bg rounded-sm px-3 py-2">
                  <span className="text-vscode-text-dim">Active Corrections</span>
                  <span className="text-vscode-blue font-medium">{
                    systemStatus.subsystems.vector_store.error_book.active_corrections ?? 0
                  }</span>
                </div>
                <div className="flex items-center justify-between bg-vscode-bg rounded-sm px-3 py-2">
                  <span className="text-vscode-text-dim">Error Patterns</span>
                  <span className="text-vscode-text font-medium">{
                    systemStatus.subsystems.vector_store.error_book.error_patterns ?? 0
                  }</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tool List from System Status */}
        {systemStatus?.subsystems?.tools?.names && (
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-3">
              Registered Tools
              <span className="text-xs text-vscode-text-dim font-normal ml-2">({systemStatus.subsystems.tools.total} total, including 7 RAG tools)</span>
            </h2>
            <div className="flex flex-wrap gap-2">
              {(systemStatus.subsystems.tools.names as string[]).map(name => (
                <span key={name} className={clsx(
                  'px-2 py-1 text-xs border rounded-sm font-mono',
                  name.startsWith('rag_') ? 'bg-vscode-accent/20 text-vscode-accent border-vscode-accent/30' : 'bg-vscode-bg border-vscode-border text-vscode-text'
                )}>{name}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
