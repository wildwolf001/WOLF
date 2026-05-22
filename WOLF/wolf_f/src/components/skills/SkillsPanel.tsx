import React, { useState, useEffect } from 'react';
import { api } from '@/services';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  risk: 'safe' | 'warning' | 'danger';
  source: 'builtin' | 'custom' | 'community';
  enabled: boolean;
  triggers: string[];
  examples: string[];
}

interface SkillInvocation {
  id: string;
  skillId: string;
  skillName: string;
  action: string;
  result: string;
  time: Date;
}

const RISK_COLORS = {
  safe: 'text-green-400',
  warning: 'text-yellow-400',
  danger: 'text-red-400',
};

const CATEGORY_ICONS: Record<string, string> = {
  development: '⚙️',
  research: '🔬',
  writing: '📝',
  general: '🎯',
};

export function SkillsPanel() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [invocations, setInvocations] = useState<SkillInvocation[]>([]);
  const [activeTab, setActiveTab] = useState<'skills' | 'history'>('skills');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSkills();
    // Simulate some invocations for demo
    addDemoInvocations();
  }, []);

  const loadSkills = async () => {
    try {
      const res = await api.get('/skills');
      const response = (res as any).data;
      if (response.success && response.data) {
        setSkills(response.data as any[]);
      }
    } catch (error) {
      console.error('Failed to load skills:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSkill = async (skillId: string) => {
    try {
      const res = await api.post(`/skills/${skillId}/toggle`);
      const response = (res as any).data;
      if (response.success) {
        setSkills(skills.map(s =>
          s.id === skillId ? { ...s, enabled: !s.enabled } : s
        ));
      }
    } catch (error) {
      console.error('Failed to toggle skill:', error);
    }
  };

  const addDemoInvocations = () => {
    // Demo invocations to show how skill calls would appear
    const demos: SkillInvocation[] = [
      {
        id: '1',
        skillId: 'skill-research',
        skillName: 'Research',
        action: 'Analyzed project structure',
        result: 'Found 6 source files',
        time: new Date(Date.now() - 300000),
      },
      {
        id: '2',
        skillId: 'skill-code-review',
        skillName: 'Code Review',
        action: 'Reviewed main.py',
        result: 'Found 2 issues',
        time: new Date(Date.now() - 600000),
      },
      {
        id: '3',
        skillId: 'skill-write',
        skillName: 'Technical Writing',
        action: 'Generated documentation',
        result: 'Created README.md',
        time: new Date(Date.now() - 900000),
      },
    ];
    setInvocations(demos);
  };

  const categories = [...new Set(skills.map(s => s.category))];
  const filteredSkills = selectedCategory
    ? skills.filter(s => s.category === selectedCategory)
    : skills;

  const enabledCount = skills.filter(s => s.enabled).length;

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <div className="animate-pulse text-gray-400">Loading skills...</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            🎯 Skills
            <span className="text-sm text-gray-400 font-normal">
              ({enabledCount}/{skills.length} enabled)
            </span>
          </h3>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('skills')}
            className={`px-3 py-1 text-xs rounded ${
              activeTab === 'skills'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Skills
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1 text-xs rounded ${
              activeTab === 'history'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            History
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'skills' ? (
        <>
          {/* Category filters */}
          <div className="p-2 border-b border-gray-700 flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-2 py-1 text-xs rounded ${
                !selectedCategory
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              All
            </button>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                  selectedCategory === cat
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {CATEGORY_ICONS[cat] || '📁'} {cat}
              </button>
            ))}
          </div>

          {/* Skills list */}
          <div className="max-h-96 overflow-y-auto">
            {filteredSkills.map(skill => (
              <div
                key={skill.id}
                className="p-3 border-b border-gray-700 last:border-b-0 hover:bg-gray-750"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white truncate">
                        {skill.name}
                      </span>
                      <span className={`text-xs ${RISK_COLORS[skill.risk]}`}>
                        {skill.risk === 'danger' && '⚠️'}
                        {skill.risk === 'warning' && '⚡'}
                      </span>
                      {skill.source === 'builtin' && (
                        <span className="text-xs text-gray-500">builtin</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                      {skill.description}
                    </p>
                    {skill.triggers.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {skill.triggers.slice(0, 4).map(t => (
                          <span
                            key={t}
                            className="px-1.5 py-0.5 text-xs bg-gray-700 text-gray-300 rounded"
                          >
                            {t}
                          </span>
                        ))}
                        {skill.triggers.length > 4 && (
                          <span className="text-xs text-gray-500">
                            +{skill.triggers.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {/* Toggle switch */}
                  <button
                    onClick={() => toggleSkill(skill.id)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      skill.enabled ? 'bg-green-600' : 'bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        skill.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        /* History tab */
        <div className="max-h-96 overflow-y-auto">
          {invocations.length === 0 ? (
            <div className="p-4 text-center text-gray-400 text-sm">
              No skill invocations yet
            </div>
          ) : (
            invocations.map(inv => (
              <div key={inv.id} className="p-3 border-b border-gray-700 last:border-b-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">
                    {inv.skillName}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTime(inv.time)}
                  </span>
                </div>
                <p className="text-sm text-gray-300 mt-1">{inv.action}</p>
                <p className="text-xs text-gray-500 mt-1">→ {inv.result}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}
