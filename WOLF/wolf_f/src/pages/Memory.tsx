import React from 'react';
import { useSessionStore, type MemoryEntry, type MemoryType } from '@/store';
import clsx from 'clsx';

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

  // Load memories from API when session changes
  React.useEffect(() => {
    if (currentSessionId) {
      loadMemoriesFromAPI(currentSessionId);
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
      name: newMemory.name,
      description: newMemory.description,
      type: newMemory.type,
      content: newMemory.content,
      why: newMemory.why || undefined,
      howToApply: newMemory.howToApply || undefined,
    });
    setNewMemory({
      name: '',
      description: '',
      type: 'reference',
      content: '',
      why: '',
      howToApply: '',
    });
    setShowAddForm(false);
  };

  const handleUpdateMemory = async () => {
    if (!currentSessionId || !selectedMemory || !editForm.name?.trim()) return;
    await updateMemory(currentSessionId, selectedMemory.id, editForm);
    setIsEditing(false);
    setSelectedMemory(null);
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!currentSessionId) return;
    await deleteMemory(currentSessionId, memoryId);
    if (selectedMemory?.id === memoryId) {
      setSelectedMemory(null);
    }
  };

  const handleUseMemory = async (memory: MemoryEntry) => {
    if (!currentSessionId) return;
    await useMemory(currentSessionId, memory.id);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">Memory Management</h1>
            <p className="text-xs text-vscode-text-dim">
              Remember important context across conversations
            </p>
          </div>
          <button
            onClick={() => setShowAddForm(true)}
            className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
          >
            + Add Memory
          </button>
        </div>
      </div>

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
                  {session.name} ({session.memories?.length || 0} memories)
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel: Memory list */}
        <div className="w-96 border-r border-vscode-border flex flex-col overflow-hidden">
          {/* Filters */}
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
                className={clsx(
                  'px-2 py-1 text-xs rounded-sm',
                  filterType === 'all' ? 'bg-vscode-accent text-white' : 'bg-vscode-bg text-vscode-text-dim hover:bg-vscode-bg-hover'
                )}
              >
                All ({memories.length})
              </button>
              {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(type => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  className={clsx(
                    'px-2 py-1 text-xs rounded-sm capitalize',
                    filterType === type ? 'bg-vscode-accent text-white' : 'bg-vscode-bg text-vscode-text-dim hover:bg-vscode-bg-hover'
                  )}
                >
                  {typeLabels[type]} ({memories.filter(m => m.type === type).length})
                </button>
              ))}
            </div>
          </div>

          {/* Memory list */}
          <div className="flex-1 overflow-y-auto">
            {!currentSessionId ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">
                Select a session to view memories
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">
                {searchQuery || filterType !== 'all'
                  ? 'No memories match your filters'
                  : 'No memories yet. Add one or let the AI auto-extract from conversations.'}
              </div>
            ) : (
              <div className="divide-y divide-vscode-border">
                {filteredMemories.map(memory => (
                  <div
                    key={memory.id}
                    onClick={() => setSelectedMemory(memory)}
                    className={clsx(
                      'p-3 cursor-pointer hover:bg-vscode-bg-hover transition-colors',
                      selectedMemory?.id === memory.id && 'bg-vscode-bg-active'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={clsx('w-2 h-2 rounded-full mt-1.5', typeColors[memory.type])} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-vscode-text font-medium truncate">{memory.name}</div>
                        <div className="text-xs text-vscode-text-dim truncate">{memory.description || memory.content.slice(0, 50)}</div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-vscode-text-dim">
                            Used {memory.usageCount} times
                          </span>
                          <span className="text-xs text-vscode-text-dim">
                            {new Date(memory.updatedAt).toLocaleDateString()}
                          </span>
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
                <div className="text-5xl mb-4">🧠</div>
                <div className="text-vscode-text mb-2">Select a memory to view details</div>
                <div className="text-xs text-vscode-text-dim max-w-md">
                  Memories help the AI remember important context across conversations.
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
                  <input
                    type="text"
                    value={editForm.name || ''}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                  />
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Type</label>
                  <select
                    value={editForm.type || 'reference'}
                    onChange={(e) => setEditForm({ ...editForm, type: e.target.value as MemoryType })}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                  >
                    {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(t => (
                      <option key={t} value={t}>{typeLabels[t]}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Description</label>
                  <input
                    type="text"
                    value={editForm.description || ''}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                  />
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Content</label>
                  <textarea
                    value={editForm.content || ''}
                    onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                    rows={6}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Why (why is this important?)</label>
                  <textarea
                    value={editForm.why || ''}
                    onChange={(e) => setEditForm({ ...editForm, why: e.target.value })}
                    rows={2}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">How to Apply</label>
                  <textarea
                    value={editForm.howToApply || ''}
                    onChange={(e) => setEditForm({ ...editForm, howToApply: e.target.value })}
                    rows={2}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                  />
                </div>
                <div className="flex gap-2 pt-4">
                  <button
                    onClick={handleUpdateMemory}
                    className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
                  >
                    Save Changes
                  </button>
                  <button
                    onClick={() => { setIsEditing(false); setSelectedMemory(null); }}
                    className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-2xl">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className={clsx('px-2 py-1 text-xs font-medium text-white rounded-sm uppercase', typeColors[selectedMemory.type])}>
                      {typeLabels[selectedMemory.type]}
                    </span>
                    <h2 className="text-lg font-semibold text-vscode-text">{selectedMemory.name}</h2>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setEditForm(selectedMemory); setIsEditing(true); }}
                      className="px-3 py-1 text-xs bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteMemory(selectedMemory.id)}
                      className="px-3 py-1 text-xs bg-vscode-red/20 text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/30"
                    >
                      Delete
                    </button>
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
                  <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-4 whitespace-pre-wrap">
                    {selectedMemory.content}
                  </div>
                </div>

                {selectedMemory.why && (
                  <div className="mb-4">
                    <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">Why</div>
                    <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-3">
                      {selectedMemory.why}
                    </div>
                  </div>
                )}

                {selectedMemory.howToApply && (
                  <div className="mb-4">
                    <div className="text-xs text-vscode-text-dim uppercase tracking-wide mb-1">How to Apply</div>
                    <div className="text-sm text-vscode-text bg-vscode-bg-light border border-vscode-border rounded-sm p-3">
                      {selectedMemory.howToApply}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-6 text-xs text-vscode-text-dim pt-4 border-t border-vscode-border">
                  <span>Created: {new Date(selectedMemory.createdAt).toLocaleString()}</span>
                  <span>Updated: {new Date(selectedMemory.updatedAt).toLocaleString()}</span>
                  <span>Used: {selectedMemory.usageCount} times</span>
                  {selectedMemory.lastUsedAt && (
                    <span>Last used: {new Date(selectedMemory.lastUsedAt).toLocaleString()}</span>
                  )}
                </div>

                <div className="mt-4">
                  <button
                    onClick={() => handleUseMemory(selectedMemory)}
                    className="px-3 py-1.5 text-xs bg-vscode-accent/20 text-vscode-accent border border-vscode-accent/30 rounded-sm hover:bg-vscode-accent/30"
                  >
                    Mark as Used
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Memory Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-vscode-text mb-4">Add New Memory</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Name *</label>
                <input
                  type="text"
                  value={newMemory.name}
                  onChange={(e) => setNewMemory({ ...newMemory, name: e.target.value })}
                  placeholder="e.g., User prefers Python"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Type</label>
                <select
                  value={newMemory.type}
                  onChange={(e) => setNewMemory({ ...newMemory, type: e.target.value as MemoryType })}
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                >
                  {(['user', 'feedback', 'project', 'reference'] as MemoryType[]).map(t => (
                    <option key={t} value={t}>{typeLabels[t]}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Description</label>
                <input
                  type="text"
                  value={newMemory.description}
                  onChange={(e) => setNewMemory({ ...newMemory, description: e.target.value })}
                  placeholder="Brief description"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Content *</label>
                <textarea
                  value={newMemory.content}
                  onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                  rows={4}
                  placeholder="The actual memory content..."
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Why (why is this important?)</label>
                <textarea
                  value={newMemory.why}
                  onChange={(e) => setNewMemory({ ...newMemory, why: e.target.value })}
                  rows={2}
                  placeholder="Context about why this memory matters..."
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">How to Apply</label>
                <textarea
                  value={newMemory.howToApply}
                  onChange={(e) => setNewMemory({ ...newMemory, howToApply: e.target.value })}
                  rows={2}
                  placeholder="How should this memory be used?"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text resize-none"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleAddMemory}
                disabled={!newMemory.name.trim() || !newMemory.content.trim()}
                className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Memory
              </button>
              <button
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border text-vscode-text rounded-sm hover:bg-vscode-bg-hover"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
