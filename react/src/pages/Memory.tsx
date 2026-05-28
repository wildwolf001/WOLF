import React from 'react';
import { useSessionStore, type MemoryEntry, type MemoryType } from '@/store';
import clsx from 'clsx';
import { API_CONFIG, getApiUrl } from '@/config/api';

const typeColors: Record<MemoryType, string> = {
  user: 'bg-vscode-blue',
  feedback: 'bg-vscode-yellow',
  project: 'bg-vscode-green',
  reference: 'bg-vscode-purple',
};

const typeLabels: Record<MemoryType, string> = {
  user: 'User',
  feedback: 'Feedback',
  project: 'Project',
  reference: 'Reference',
};

const layerLabels: Record<string, string> = {
  working: 'Working',
  short_term: 'Short-Term',
  episodic: 'Episodic',
  semantic: 'Semantic',
  procedural: 'Procedural',
};

const layerColors: Record<string, string> = {
  working: '#569cd6',
  short_term: '#4ec9b0',
  episodic: '#dcdcaa',
  semantic: '#c586c0',
  procedural: '#f14c4c',
};

interface CognitiveData {
  total: number;
  cognitive_layers: Record<string, number>;
  score_distribution: Record<string, number>;
  decay_config: Record<string, { half_life_hours: number; half_life_days: number; weight_after_1d: number; weight_after_7d: number }>;
  top_importance: any[];
  memories: any[];
}

interface SystemStatus {
  server: string;
  subsystems: Record<string, { initialized: boolean; total?: number; doc_count?: number; [key: string]: any }>;
}

export function Memory() {
  const {
    sessions,
    currentSessionId,
    setCurrentSession,
    getMemories,
    addMemory,
    updateMemory,
    deleteMemory,
    useMemory,
    getRelevantMemories,
    loadMemoriesFromAPI,
  } = useSessionStore();

  const currentSession = sessions.find(s => s.id === currentSessionId);
  const memories = currentSessionId ? getMemories(currentSessionId) : [];
  const relevantMemories = currentSessionId ? getRelevantMemories(currentSessionId, 10) : [];

  const [activeView, setActiveView] = React.useState<'dashboard' | 'list' | 'detail'>('dashboard');

  React.useEffect(() => {
    if (currentSessionId) {
      loadMemoriesFromAPI(currentSessionId);
      fetchMemoryStats();
      fetchCognitiveData();
      fetchSystemStatus();
    }
  }, [currentSessionId]);

  const [filterType, setFilterType] = React.useState<MemoryType | 'all'>('all');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedMemory, setSelectedMemory] = React.useState<MemoryEntry | null>(null);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editForm, setEditForm] = React.useState<Partial<MemoryEntry>>({});
  const [showAddForm, setShowAddForm] = React.useState(false);
  const [newMemory, setNewMemory] = React.useState({
    name: '',
    description: '',
    type: 'reference' as MemoryType,
    content: '',
    why: '',
    howToApply: '',
  });

  const [memoryStats, setMemoryStats] = React.useState({
    total: 0,
    by_type: { user: 0, feedback: 0, project: 0, reference: 0 },
    avg_usage: 0,
    total_usage: 0,
  });
  const [syncStatus, setSyncStatus] = React.useState<'synced' | 'syncing' | 'error'>('synced');

  const [cognitiveData, setCognitiveData] = React.useState<CognitiveData | null>(null);
  const [systemStatus, setSystemStatus] = React.useState<SystemStatus | null>(null);

  const fetchMemoryStats = async () => {
    if (!currentSessionId) return;
    try {
      const response = await fetch(`${getApiUrl(API_CONFIG.endpoints.memoryStats)}?session_id=${currentSessionId}`);
      if (response.ok) {
        const data = await response.json();
        setMemoryStats(data);
      }
    } catch { /* ignore */ }
  };

  const fetchCognitiveData = async () => {
    if (!currentSessionId) return;
    try {
      const response = await fetch(`${getApiUrl(API_CONFIG.endpoints.systemMemoryCognitive)}?session_id=${currentSessionId}`);
      if (response.ok) {
        const data = await response.json();
        setCognitiveData(data);
      }
    } catch { /* ignore */ }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(getApiUrl(API_CONFIG.endpoints.systemStatus));
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data);
      }
    } catch { /* ignore */ }
  };

  const handleSyncWithBackend = async () => {
    if (!currentSessionId) return;
    setSyncStatus('syncing');
    try {
      const currentMemories = memories.map(m => ({
        id: m.id, name: m.name, description: m.description, type: m.type,
        content: m.content, why: m.why, howToApply: m.howToApply,
        createdAt: m.createdAt, updatedAt: m.updatedAt,
        usageCount: m.usageCount, lastUsedAt: m.lastUsedAt,
      }));
      const response = await fetch(`${getApiUrl(API_CONFIG.endpoints.memorySync)}?session_id=${currentSessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentMemories),
      });
      if (response.ok) { setSyncStatus('synced'); fetchMemoryStats(); fetchCognitiveData(); }
      else { setSyncStatus('error'); }
    } catch { setSyncStatus('error'); }
  };

  const filteredMemories = memories.filter(m => {
    const matchesType = filterType === 'all' || m.type === filterType;
    const matchesSearch = searchQuery === '' ||
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const handleAddMemory = async () => {
    if (!currentSessionId || !newMemory.name.trim()) return;
    await addMemory(currentSessionId, {
      name: newMemory.name, description: newMemory.description,
      type: newMemory.type, content: newMemory.content,
      why: newMemory.why || undefined, howToApply: newMemory.howToApply || undefined,
    });
    setNewMemory({ name: '', description: '', type: 'reference', content: '', why: '', howToApply: '' });
    setShowAddForm(false);
  };

  const handleUpdateMemory = async () => {
    if (!currentSessionId || !selectedMemory || !editForm.name?.trim()) return;
    await updateMemory(currentSessionId, selectedMemory.id, editForm);
    setIsEditing(false); setSelectedMemory(null);
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!currentSessionId) return;
    await deleteMemory(currentSessionId, memoryId);
    if (selectedMemory?.id === memoryId) setSelectedMemory(null);
  };

  const handleUseMemory = async (memory: MemoryEntry) => {
    if (!currentSessionId) return;
    await useMemory(currentSessionId, memory.id);
  };

  // ============== Dashboard View ==============
  const renderDashboard = () => (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-vscode-text">Memory Dashboard</h1>
          <div className="flex gap-2">
            <button onClick={() => setActiveView('list')} className="px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover">List View</button>
            <button onClick={() => setShowAddForm(true)} className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80">+ Add Memory</button>
          </div>
        </div>

        {/* System Status Bar */}
        {systemStatus && (
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(systemStatus.subsystems).slice(0, 5).map(([key, val]) => (
              <div key={key} className="bg-vscode-bg-light border border-vscode-border rounded-sm p-3 text-center">
                <div className={clsx('w-2 h-2 rounded-full mx-auto mb-1', val.initialized ? 'bg-vscode-green' : 'bg-vscode-red')} />
                <div className="text-xs text-vscode-text capitalize">{key.replace('_', ' ')}</div>
                <div className="text-xs text-vscode-text-dim">{val.initialized ? (val.doc_count ?? val.total ?? '✓') : '✗'}</div>
              </div>
            ))}
          </div>
        )}

        {/* Top Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <div className="text-3xl font-bold text-vscode-accent">{memoryStats.total}</div>
            <div className="text-xs text-vscode-text-dim mt-1">Total Memories</div>
          </div>
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <div className="text-3xl font-bold text-vscode-green">{memoryStats.total_usage}</div>
            <div className="text-xs text-vscode-text-dim mt-1">Total Usage Count</div>
          </div>
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <div className="text-3xl font-bold text-vscode-yellow">{memoryStats.avg_usage.toFixed(1)}</div>
            <div className="text-xs text-vscode-text-dim mt-1">Avg Usage / Memory</div>
          </div>
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <div className="text-3xl font-bold text-vscode-purple">{relevantMemories.length}</div>
            <div className="text-xs text-vscode-text-dim mt-1">Relevant (top 10)</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Memory by Type - Pie-style bars */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">Memory Distribution by Type</h2>
            <div className="space-y-3">
              {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(type => {
                const count = memoryStats.by_type[type] || 0;
                const pct = memoryStats.total ? Math.round(count / memoryStats.total * 100) : 0;
                return (
                  <div key={type}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <div className="flex items-center gap-2">
                        <span className={clsx('w-2.5 h-2.5 rounded-full', typeColors[type])} />
                        <span className="text-vscode-text">{typeLabels[type]}</span>
                      </div>
                      <span className="text-vscode-text-dim">{count} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-vscode-bg rounded-full overflow-hidden">
                      <div className={clsx('h-full rounded-full transition-all', typeColors[type])} style={{ width: `${Math.max(pct, 2)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cognitive Layers */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">Cognitive Layers <span className="text-xs text-vscode-text-dim font-normal">(ZenBrain 5-Layer)</span></h2>
            {cognitiveData ? (
              <div className="space-y-3">
                {Object.entries(layerLabels).map(([layer, label]) => {
                  const count = cognitiveData.cognitive_layers[layer] || 0;
                  const pct = cognitiveData.total ? Math.round(count / cognitiveData.total * 100) : 0;
                  return (
                    <div key={layer}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: layerColors[layer] }} />
                          <span className="text-vscode-text">{label}</span>
                        </div>
                        <span className="text-vscode-text-dim">{count}</span>
                      </div>
                      <div className="h-2 bg-vscode-bg rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(pct, 3)}%`, backgroundColor: layerColors[layer] }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-vscode-text-dim">Loading...</div>
            )}
          </div>

          {/* Importance Scores */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">Importance Score Distribution</h2>
            {cognitiveData ? (
              <div className="space-y-3">
                {[
                  { key: 'keep', label: 'Keep (>= 0.6)', color: '#4ec9b0' },
                  { key: 'review', label: 'Review (0.3-0.6)', color: '#dcdcaa' },
                  { key: 'archive', label: 'Archive (0.1-0.3)', color: '#569cd6' },
                  { key: 'delete', label: 'Prune (< 0.1)', color: '#f14c4c' },
                ].map(item => {
                  const count = cognitiveData.score_distribution[item.key] || 0;
                  const pct = cognitiveData.total ? Math.round(count / cognitiveData.total * 100) : 0;
                  return (
                    <div key={item.key}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-vscode-text">{item.label}</span>
                        <span className="text-vscode-text-dim">{count} ({pct}%)</span>
                      </div>
                      <div className="h-2 bg-vscode-bg rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: item.color }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-vscode-text-dim">Loading...</div>
            )}
          </div>

          {/* Decay Configuration */}
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">Ebbinghaus Decay <span className="text-xs text-vscode-text-dim font-normal">(Half-Life by Type)</span></h2>
            {cognitiveData?.decay_config ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-vscode-text-dim border-b border-vscode-border">
                      <th className="text-left py-1.5">Type</th>
                      <th className="text-right py-1.5">Half-Life</th>
                      <th className="text-right py-1.5">After 1d</th>
                      <th className="text-right py-1.5">After 7d</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(cognitiveData.decay_config).map(([type, cfg]) => (
                      <tr key={type} className="border-b border-vscode-border/30">
                        <td className="py-1.5 text-vscode-text capitalize">{type}</td>
                        <td className="py-1.5 text-right text-vscode-text-dim">{cfg.half_life_days}d</td>
                        <td className="py-1.5 text-right text-vscode-text-dim">{cfg.weight_after_1d.toFixed(2)}</td>
                        <td className="py-1.5 text-right text-vscode-text-dim">{cfg.weight_after_7d.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-vscode-text-dim">Loading...</div>
            )}
            <div className="mt-3 p-2 bg-vscode-bg rounded-sm text-xs text-vscode-text-dim">
              Weight = initial × e<sup>-t/half_life</sup>. Memories decay at different rates based on type.
            </div>
          </div>
        </div>

        {/* Top Importance Memories */}
        {cognitiveData?.top_importance && cognitiveData.top_importance.length > 0 && (
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-3">Top Importance Memories</h2>
            <div className="grid grid-cols-1 gap-2">
              {cognitiveData.top_importance.slice(0, 5).map((m: any, i: number) => (
                <div key={i} className="flex items-center gap-3 bg-vscode-bg rounded-sm p-3">
                  <span className={clsx('w-2 h-2 rounded-full', typeColors[m.memory_type as MemoryType] || 'bg-vscode-text-dim')} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-vscode-text truncate">{m.name}</div>
                    <div className="text-xs text-vscode-text-dim truncate">{m.content?.slice(0, 80)}</div>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-vscode-text-dim capitalize">{m.cognitive_layer?.replace('_', ' ')}</span>
                    <span className="text-vscode-yellow font-medium">{m.importance_score?.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // ============== List View ==============
  const renderListView = () => (
    <div className="flex-1 flex overflow-hidden">
      {/* Left panel: Memory list */}
      <div className="w-96 border-r border-vscode-border flex flex-col overflow-hidden">
        <div className="p-3 border-b border-vscode-border space-y-2">
          <input
            type="text"
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-xs text-vscode-text"
          />
          <div className="flex gap-1 flex-wrap">
            <button
              onClick={() => setFilterType('all')}
              className={clsx('px-2 py-1 text-xs rounded-sm', filterType === 'all' ? 'bg-vscode-accent text-white' : 'bg-vscode-bg text-vscode-text-dim hover:bg-vscode-bg-hover')}
            >
              All ({memories.length})
            </button>
            {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(type => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={clsx('px-2 py-1 text-xs rounded-sm capitalize', filterType === type ? 'bg-vscode-accent text-white' : 'bg-vscode-bg text-vscode-text-dim hover:bg-vscode-bg-hover')}
              >
                {typeLabels[type]} ({memories.filter(m => m.type === type).length})
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!currentSessionId ? (
            <div className="p-4 text-center text-xs text-vscode-text-dim">Select a session to view memories</div>
          ) : filteredMemories.length === 0 ? (
            <div className="p-4 text-center text-xs text-vscode-text-dim">
              {searchQuery || filterType !== 'all' ? 'No memories match your filters' : 'No memories yet.'}
            </div>
          ) : (
            <div className="divide-y divide-vscode-border">
              {filteredMemories.map(memory => (
                <div
                  key={memory.id}
                  onClick={() => { setSelectedMemory(memory); setActiveView('detail'); }}
                  className={clsx('p-3 cursor-pointer hover:bg-vscode-bg-hover transition-colors', selectedMemory?.id === memory.id && 'bg-vscode-bg-active')}
                >
                  <div className="flex items-start gap-2">
                    <span className={clsx('w-2 h-2 rounded-full mt-1.5', typeColors[memory.type])} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-vscode-text font-medium truncate">{memory.name}</div>
                      <div className="text-xs text-vscode-text-dim truncate">{memory.description || memory.content.slice(0, 50)}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-vscode-text-dim">Used {memory.usageCount} times</span>
                        <span className="text-xs text-vscode-text-dim">{new Date(memory.updatedAt).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right panel: Memory detail */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedMemory ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-4">{String.fromCodePoint(0x1F9E0)}</div>
              <div className="text-vscode-text mb-2">Select a memory to view details</div>
              <div className="text-xs text-vscode-text-dim max-w-md">
                Click on a memory to see its full content and usage information.
              </div>
            </div>
          </div>
        ) : isEditing ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl space-y-4">
              <h2 className="text-lg font-semibold text-vscode-text">Edit Memory</h2>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Name</label>
                <input type="text" value={editForm.name || ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Type</label>
                <select value={editForm.type || 'reference'} onChange={(e) => setEditForm({ ...editForm, type: e.target.value as MemoryType })} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text">
                  {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(t => <option key={t} value={t}>{typeLabels[t]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Description</label>
                <input type="text" value={editForm.description || ''} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Content</label>
                <textarea value={editForm.content || ''} onChange={(e) => setEditForm({ ...editForm, content: e.target.value })} rows={6} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Why</label>
                <textarea value={editForm.why || ''} onChange={(e) => setEditForm({ ...editForm, why: e.target.value })} rows={2} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">How to Apply</label>
                <textarea value={editForm.howToApply || ''} onChange={(e) => setEditForm({ ...editForm, howToApply: e.target.value })} rows={2} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
              <div className="flex gap-2 pt-4">
                <button onClick={handleUpdateMemory} className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80">Save Changes</button>
                <button onClick={() => { setIsEditing(false); setSelectedMemory(null); }} className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover">Cancel</button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className={clsx('px-2 py-1 text-xs font-medium text-white rounded-sm uppercase', typeColors[selectedMemory.type])}>{typeLabels[selectedMemory.type]}</span>
                  <h2 className="text-lg font-semibold text-vscode-text">{selectedMemory.name}</h2>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditForm(selectedMemory); setIsEditing(true); }} className="px-3 py-1 text-xs bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover">Edit</button>
                  <button onClick={() => handleDeleteMemory(selectedMemory.id)} className="px-3 py-1 text-xs bg-vscode-red/20 text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/30">Delete</button>
                </div>
              </div>
              {selectedMemory.description && (
                <div className="mb-4">
                  <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">Description</div>
                  <div className="text-sm text-vscode-text">{selectedMemory.description}</div>
                </div>
              )}
              <div className="mb-4">
                <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">Content</div>
                <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-4 whitespace-pre-wrap">{selectedMemory.content}</div>
              </div>
              {selectedMemory.why && (
                <div className="mb-4">
                  <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">Why</div>
                  <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-3">{selectedMemory.why}</div>
                </div>
              )}
              {selectedMemory.howToApply && (
                <div className="mb-4">
                  <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">How to Apply</div>
                  <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-3">{selectedMemory.howToApply}</div>
                </div>
              )}
              <div className="flex items-center gap-6 text-xs text-vscode-text-dim pt-4 border-t border-vscode-border">
                <span>Created: {new Date(selectedMemory.createdAt).toLocaleString()}</span>
                <span>Updated: {new Date(selectedMemory.updatedAt).toLocaleString()}</span>
                <span>Used: {selectedMemory.usageCount} times</span>
                {selectedMemory.lastUsedAt && <span>Last used: {new Date(selectedMemory.lastUsedAt).toLocaleString()}</span>}
              </div>
              <div className="mt-4">
                <button onClick={() => handleUseMemory(selectedMemory)} className="px-3 py-1.5 text-xs bg-vscode-accent/20 text-vscode-accent border border-vscode-accent/30 rounded-sm hover:bg-vscode-accent/30">Mark as Used</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">Memory Management</h1>
            <p className="text-xs text-vscode-text-dim">
              {activeView === 'dashboard' ? 'Cognitive memory dashboard with importance scoring & decay tracking' :
               activeView === 'list' ? 'Browse and manage all memories' : 'Memory detail view'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View Switcher */}
            <div className="flex bg-vscode-bg border border-vscode-border rounded-sm">
              <button onClick={() => setActiveView('dashboard')} className={clsx('px-3 py-1 text-xs', activeView === 'dashboard' ? 'bg-vscode-accent text-white' : 'text-vscode-text-dim hover:text-vscode-text')}>Dashboard</button>
              <button onClick={() => setActiveView('list')} className={clsx('px-3 py-1 text-xs border-l border-vscode-border', activeView === 'list' ? 'bg-vscode-accent text-white' : 'text-vscode-text-dim hover:text-vscode-text')}>List</button>
            </div>
            {/* Sync Status */}
            <div className="flex items-center gap-2 text-xs">
              <span className={clsx('w-2 h-2 rounded-full', syncStatus === 'synced' ? 'bg-vscode-green' : syncStatus === 'syncing' ? 'bg-vscode-yellow animate-pulse' : 'bg-vscode-red')} />
              <span className="text-vscode-text-dim">{syncStatus === 'synced' ? 'Synced' : syncStatus === 'syncing' ? 'Syncing...' : 'Sync Error'}</span>
            </div>
            <button onClick={handleSyncWithBackend} disabled={syncStatus === 'syncing'} className="px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover disabled:opacity-50">Sync</button>
          </div>
        </div>
      </div>

      {/* Session selector */}
      <div className="px-6 py-2 border-b border-vscode-border bg-vscode-bg-light flex items-center gap-3">
        <span className="text-xs text-vscode-text-dim">Session:</span>
        <select value={currentSessionId || ''} onChange={(e) => setCurrentSession(e.target.value || null)} className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1 text-sm text-vscode-text">
          <option value="">None</option>
          {sessions.map(s => <option key={s.id} value={s.id}>{s.name} ({s.memories?.length || 0})</option>)}
        </select>
      </div>

      {/* Content */}
      {activeView === 'dashboard' ? renderDashboard() : activeView === 'list' ? renderListView() : renderListView()}

      {/* Add Memory Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-vscode-text mb-4">Add New Memory</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Name *</label>
                <input type="text" value={newMemory.name} onChange={(e) => setNewMemory({ ...newMemory, name: e.target.value })} placeholder="e.g., User prefers Python" className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Type</label>
                <select value={newMemory.type} onChange={(e) => setNewMemory({ ...newMemory, type: e.target.value as MemoryType })} className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text">
                  {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(t => <option key={t} value={t}>{typeLabels[t]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Description</label>
                <input type="text" value={newMemory.description} onChange={(e) => setNewMemory({ ...newMemory, description: e.target.value })} placeholder="Brief description" className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Content *</label>
                <textarea value={newMemory.content} onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })} rows={4} placeholder="The actual memory content..." className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Why</label>
                <textarea value={newMemory.why} onChange={(e) => setNewMemory({ ...newMemory, why: e.target.value })} rows={2} placeholder="Why this memory matters..." className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">How to Apply</label>
                <textarea value={newMemory.howToApply} onChange={(e) => setNewMemory({ ...newMemory, howToApply: e.target.value })} rows={2} placeholder="How should this memory be used?" className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none" />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button onClick={handleAddMemory} disabled={!newMemory.name.trim() || !newMemory.content.trim()} className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed">Add Memory</button>
              <button onClick={() => setShowAddForm(false)} className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
