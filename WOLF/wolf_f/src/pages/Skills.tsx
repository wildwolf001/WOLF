import React, { useState } from 'react';
import clsx from 'clsx';
import { skillsApi } from '@/services/api';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  risk: string;
  source: string;
  enabled: boolean;
  triggers: string[];
  examples: string[];
  content?: string;
}

const categoryColors: Record<string, string> = {
  development: 'bg-vscode-blue/20 text-vscode-blue',
  research: 'bg-vscode-green/20 text-vscode-green',
  writing: 'bg-purple-500/20 text-purple-400',
  general: 'bg-vscode-text-dim/20 text-vscode-text-dim',
};

const riskColors: Record<string, string> = {
  safe: 'text-vscode-green',
  warning: 'text-vscode-yellow',
  danger: 'text-vscode-red',
};

const riskLabels: Record<string, string> = {
  safe: 'Safe',
  warning: 'Warning',
  danger: 'Danger',
};

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSkill, setNewSkill] = useState({
    name: '',
    description: '',
    category: 'general',
    risk: 'safe',
    triggers: '',
    examples: '',
  });

  React.useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    try {
      const response = await skillsApi.getAll();
      if (response.success && response.data) {
        setSkills(response.data as any[]);
      }
    } catch (error) {
      console.error('Failed to fetch skills:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSkill = async (skillId: string) => {
    try {
      const response = await skillsApi.toggle(skillId);
      if (response.success && response.data) {
        const updatedSkill = response.data as any;
        setSkills(prev => prev.map(s => s.id === skillId ? updatedSkill : s));
        if (selectedSkill?.id === skillId) {
          setSelectedSkill(updatedSkill);
        }
      }
    } catch (error) {
      console.error('Failed to toggle skill:', error);
    }
  };

  const handleDeleteSkill = async (skillId: string) => {
    if (!confirm('Are you sure you want to delete this skill?')) return;
    try {
      await skillsApi.delete(skillId);
      setSkills(prev => prev.filter(s => s.id !== skillId));
      if (selectedSkill?.id === skillId) {
        setSelectedSkill(null);
      }
    } catch (error) {
      console.error('Failed to delete skill:', error);
    }
  };

  const handleCreateSkill = async () => {
    if (!newSkill.name.trim() || !newSkill.description.trim()) return;
    try {
      const data = await skillsApi.create({
        name: newSkill.name,
        description: newSkill.description,
        category: newSkill.category,
        risk: newSkill.risk,
        triggers: newSkill.triggers.split(',').map(t => t.trim()).filter(Boolean),
        examples: newSkill.examples.split(',').map(e => e.trim()).filter(Boolean),
      });
      if (data.success && data.data) {
        setSkills(prev => [...prev, data.data as Skill]);
        setShowCreateModal(false);
        setNewSkill({ name: '', description: '', category: 'general', risk: 'safe', triggers: '', examples: '' });
      }
    } catch (error) {
      console.error('Failed to create skill:', error);
    }
  };

  const getSkillIcon = (category: string) => {
    switch (category) {
      case 'development': return '💻';
      case 'research': return '🔬';
      case 'writing': return '📝';
      default: return '🎯';
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">Skills & Plugins</h1>
            <p className="text-xs text-vscode-text-dim">
              Extend agent capabilities with skill plugins
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
          >
            + Create Skill
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Skills list */}
        <div className="w-96 border-r border-vscode-border flex flex-col overflow-hidden">
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light">
            <h2 className="text-xs font-medium text-vscode-text uppercase tracking-wide">
              Available Skills ({skills.length})
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">Loading...</div>
            ) : skills.length === 0 ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">
                No skills available
              </div>
            ) : (
              <div className="divide-y divide-vscode-border">
                {skills.map(skill => (
                  <div
                    key={skill.id}
                    onClick={() => setSelectedSkill(skill)}
                    className={clsx(
                      'p-3 cursor-pointer hover:bg-vscode-bg-hover transition-colors',
                      selectedSkill?.id === skill.id && 'bg-vscode-bg-active'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <span className="text-lg mt-0.5">{getSkillIcon(skill.category)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-vscode-text font-medium truncate">{skill.name}</span>
                            <span className={clsx('text-xs', riskColors[skill.risk])}>
                              {riskLabels[skill.risk]}
                            </span>
                          </div>
                          <div className="text-xs text-vscode-text-dim truncate mt-0.5">
                            {skill.description}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={clsx('px-1.5 py-0.5 text-xs rounded', categoryColors[skill.category] || categoryColors.general)}>
                              {skill.category}
                            </span>
                            <span className="text-xs text-vscode-text-dim">
                              {skill.triggers?.length || 0} triggers
                            </span>
                          </div>
                        </div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={skill.enabled}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleToggleSkill(skill.id);
                          }}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-vscode-border rounded-full peer peer-checked:bg-vscode-accent peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Skill detail */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedSkill ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-5xl mb-4">🎯</div>
                <div className="text-vscode-text mb-2">Select a skill to view details</div>
                <div className="text-xs text-vscode-text-dim max-w-md">
                  Skills extend WOLF AI's capabilities. Built-in skills include Bug Hunter, Code Review, Research, and more.
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-2xl">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <span className="text-4xl">{getSkillIcon(selectedSkill.category)}</span>
                    <div>
                      <h2 className="text-lg font-semibold text-vscode-text">{selectedSkill.name}</h2>
                      <p className="text-sm text-vscode-text-dim">{selectedSkill.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedSkill.source !== 'builtin' && (
                      <button
                        onClick={() => handleDeleteSkill(selectedSkill.id)}
                        className="px-3 py-1.5 text-xs text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/20"
                      >
                        Delete
                      </button>
                    )}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <span className="text-xs text-vscode-text-dim">Enabled</span>
                      <input
                        type="checkbox"
                        checked={selectedSkill.enabled}
                        onChange={() => handleToggleSkill(selectedSkill.id)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-vscode-border rounded-full peer peer-checked:bg-vscode-accent peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all relative"></div>
                    </label>
                  </div>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-3 bg-vscode-bg-light border border-vscode-border rounded-sm">
                    <div className="text-xs text-vscode-text-dim mb-1">Category</div>
                    <span className={clsx('px-2 py-1 text-xs rounded', categoryColors[selectedSkill.category] || categoryColors.general)}>
                      {selectedSkill.category}
                    </span>
                  </div>
                  <div className="p-3 bg-vscode-bg-light border border-vscode-border rounded-sm">
                    <div className="text-xs text-vscode-text-dim mb-1">Risk Level</div>
                    <span className={clsx('text-sm font-medium', riskColors[selectedSkill.risk])}>
                      {riskLabels[selectedSkill.risk]}
                    </span>
                  </div>
                  <div className="p-3 bg-vscode-bg-light border border-vscode-border rounded-sm">
                    <div className="text-xs text-vscode-text-dim mb-1">Source</div>
                    <span className="text-sm text-vscode-text capitalize">{selectedSkill.source}</span>
                  </div>
                </div>

                {/* Triggers */}
                <div className="mb-6">
                  <h3 className="text-xs text-vscode-text-dim uppercase tracking-wide mb-3">Triggers</h3>
                  <div className="flex flex-wrap gap-2">
                    {(selectedSkill.triggers || []).map((trigger, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm font-mono"
                      >
                        {trigger}
                      </span>
                    ))}
                    {(!selectedSkill.triggers || selectedSkill.triggers.length === 0) && (
                      <span className="text-xs text-vscode-text-dim">No triggers defined</span>
                    )}
                  </div>
                </div>

                {/* Examples */}
                <div className="mb-6">
                  <h3 className="text-xs text-vscode-text-dim uppercase tracking-wide mb-3">Examples</h3>
                  <div className="space-y-2">
                    {(selectedSkill.examples || []).map((example, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-vscode-bg-light border border-vscode-border rounded-sm text-sm text-vscode-text"
                      >
                        "{example}"
                      </div>
                    ))}
                    {(!selectedSkill.examples || selectedSkill.examples.length === 0) && (
                      <span className="text-xs text-vscode-text-dim">No examples defined</span>
                    )}
                  </div>
                </div>

                {/* Content preview */}
                {'content' in selectedSkill && selectedSkill.content && (
                  <div>
                    <h3 className="text-xs text-vscode-text-dim uppercase tracking-wide mb-3">Content</h3>
                    <div className="p-4 bg-vscode-bg-light border border-vscode-border rounded-sm text-sm text-vscode-text whitespace-pre-wrap font-mono max-h-96 overflow-y-auto">
                      {String(selectedSkill.content)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Skill Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-vscode-text mb-4">Create New Skill</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Name *</label>
                <input
                  type="text"
                  value={newSkill.name}
                  onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
                  placeholder="e.g., Database Expert"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Description *</label>
                <input
                  type="text"
                  value={newSkill.description}
                  onChange={(e) => setNewSkill({ ...newSkill, description: e.target.value })}
                  placeholder="What this skill does"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Category</label>
                  <select
                    value={newSkill.category}
                    onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value })}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                  >
                    <option value="general">General</option>
                    <option value="development">Development</option>
                    <option value="research">Research</option>
                    <option value="writing">Writing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-vscode-text-dim mb-1">Risk</label>
                  <select
                    value={newSkill.risk}
                    onChange={(e) => setNewSkill({ ...newSkill, risk: e.target.value })}
                    className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                  >
                    <option value="safe">Safe</option>
                    <option value="warning">Warning</option>
                    <option value="danger">Danger</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Triggers (comma-separated)</label>
                <input
                  type="text"
                  value={newSkill.triggers}
                  onChange={(e) => setNewSkill({ ...newSkill, triggers: e.target.value })}
                  placeholder="database, sql, query"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Examples (comma-separated)</label>
                <input
                  type="text"
                  value={newSkill.examples}
                  onChange={(e) => setNewSkill({ ...newSkill, examples: e.target.value })}
                  placeholder="Write a SQL query, Optimize database"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCreateSkill}
                disabled={!newSkill.name.trim() || !newSkill.description.trim()}
                className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Skill
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewSkill({ name: '', description: '', category: 'general', risk: 'safe', triggers: '', examples: '' });
                }}
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