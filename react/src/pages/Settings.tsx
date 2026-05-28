import React from 'react';
import clsx from 'clsx';
import { configService, type QueryEngineConfig, type ToolConfig, type MCPServer } from '@/services/configService';
import { API_CONFIG } from '@/config/api';

interface EnvConfig {
  current_provider: string;
  providers: Record<string, {
    api_key_masked: string;
    has_api_key: boolean;
    group_id: string | null;
    model: string;
    api_key_env: string;
    model_env: string;
    group_id_env: string;
  }>;
  providers_list: Array<{
    id: string;
    name: string;
    requires_group_id: boolean;
  }>;
  env_path: string;
}

export function Settings() {
  const [envConfig, setEnvConfig] = React.useState<EnvConfig | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);

  // .env inline editor state
  const [showEnvEditor, setShowEnvEditor] = React.useState(false);
  const [envRawContent, setEnvRawContent] = React.useState('');
  const [envEditedContent, setEnvEditedContent] = React.useState('');

  // Storage paths state
  const [storagePaths, setStoragePaths] = React.useState<Record<string, string>>({});
  const [storagePathsStatus, setStoragePathsStatus] = React.useState<Record<string, any>>({});

  // Query Engine config state
  const [queryEngineConfig, setQueryEngineConfig] = React.useState<QueryEngineConfig>({
    max_turns: 10,
    max_tokens: 8000,
    temperature: 0.7,
    timeout: 120,
    stream: true,
    max_parallel_tools: 5,
    max_context_tokens: 100000,
    context_overflow_threshold: 0.9,
  });

  // Tool config state
  const [toolConfig, setToolConfig] = React.useState<ToolConfig>({
    max_concurrent_reads: 10,
    bash_enabled: true,
    edit_enabled: true,
    write_enabled: true,
    glob_enabled: true,
    grep_enabled: true,
    agent_enabled: true,
  });

  // MCP servers state
  const [mcpServers, setMcpServers] = React.useState<MCPServer[]>([]);
  const [newMcpServer, setNewMcpServer] = React.useState<Partial<MCPServer>>({
    name: '',
    type: 'stdio',
    command: '',
    args: [],
  });

  React.useEffect(() => {
    fetchEnvConfig();
    fetchStoragePaths();
    fetchNewConfig();
  }, []);

  // ========== Fetch .env config ==========

  const fetchEnvConfig = async () => {
    try {
      const response = await fetch(API_CONFIG.endpoints.configEnv);
      if (response.ok) {
        const data: EnvConfig = await response.json();
        setEnvConfig(data);
      }
    } catch (error) {
      console.error('Failed to fetch env config:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStoragePaths = async () => {
    try {
      const pathsResponse = await fetch('/api/config/storage-paths');
      if (pathsResponse.ok) {
        const pathsData = await pathsResponse.json();
        setStoragePaths(pathsData.paths || {});
      }

      const statusResponse = await fetch('/api/config/storage-paths/status');
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        setStoragePathsStatus(statusData.status || {});
      }
    } catch (error) {
      console.error('Failed to fetch storage paths:', error);
    }
  };

  const fetchNewConfig = async () => {
    try {
      const qeConfig = await configService.getQueryEngineConfig();
      setQueryEngineConfig(qeConfig);

      const tConfig = await configService.getToolConfig();
      setToolConfig(tConfig);

      const servers = await configService.getMCPServers();
      setMcpServers(servers);
    } catch (error) {
      console.error('Failed to fetch new config:', error);
    }
  };

  // ========== Provider switching via .env ==========

  const handleProviderChange = async (providerId: string) => {
    setSaving(true);
    try {
      const response = await fetch(API_CONFIG.endpoints.configEnvSwitchProvider, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: providerId })
      });
      if (response.ok) {
        await fetchEnvConfig();
      }
    } catch (error) {
      console.error('Failed to switch provider:', error);
    } finally {
      setSaving(false);
    }
  };

  // ========== Open .env file ==========

  const handleOpenEnv = async () => {
    try {
      const response = await fetch(API_CONFIG.endpoints.configEnvOpen, { method: 'POST' });
      const result = await response.json();
      if (result.status === 'error') {
        alert('Failed to open .env file: ' + result.message);
      }
    } catch (error) {
      console.error('Failed to open .env:', error);
    }
  };

  // ========== Inline edit .env ==========

  const handleOpenEnvEditor = async () => {
    try {
      const response = await fetch(API_CONFIG.endpoints.configEnvRaw);
      const data = await response.json();
      setEnvRawContent(data.content || '');
      setEnvEditedContent(data.content || '');
      setShowEnvEditor(true);
    } catch (error) {
      console.error('Failed to load .env content:', error);
    }
  };

  const handleSaveEnv = async () => {
    setSaving(true);
    try {
      const response = await fetch(API_CONFIG.endpoints.configEnv, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: envEditedContent })
      });
      if (response.ok) {
        setShowEnvEditor(false);
        await fetchEnvConfig();
      }
    } catch (error) {
      console.error('Failed to save .env:', error);
    } finally {
      setSaving(false);
    }
  };

  // ========== Storage path save ==========

  const handleSaveStoragePath = async (pathType: string, path: string) => {
    setSaving(true);
    try {
      const response = await fetch('/api/config/storage-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path_type: pathType, path })
      });
      if (response.ok) {
        await fetchStoragePaths();
        // If local_storage changed, memory dir was rebuilt — refresh env config too
        if (pathType === 'local_storage') {
          await fetchEnvConfig();
        }
      }
    } catch (error) {
      console.error('Failed to save storage path:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-vscode-text-dim">Loading configuration...</div>
      </div>
    );
  }

  const providers = envConfig?.providers_list || [];
  const currentProvider = envConfig?.current_provider || 'minimax';

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-lg font-semibold text-vscode-text mb-6">Settings</h1>

        {/* Current Provider (from .env) */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Current LLM Provider</h2>
            <p className="text-xs text-vscode-text-dim mt-1">
              Managed via <code className="text-vscode-accent">.env</code> file
              {envConfig?.env_path && (
                <span className="ml-2">({envConfig.env_path})</span>
              )}
            </p>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-4">
              <select
                value={currentProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                disabled={saving}
                className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text flex-1"
              >
                {providers.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div className="text-xs text-vscode-text-dim">
                {saving ? 'Saving...' : 'Saved'}
              </div>
            </div>

            {/* Show current provider status from .env */}
            {envConfig?.providers[currentProvider] && (
              <div className="mt-4 p-3 bg-vscode-bg rounded-sm border border-vscode-border">
                <div className="flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    envConfig.providers[currentProvider].has_api_key
                      ? 'bg-vscode-green'
                      : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {currentProvider.toUpperCase()} -
                  </span>
                  <span className="text-vscode-text font-mono">
                    {envConfig.providers[currentProvider].model || 'No model set'}
                  </span>
                  <span className="text-vscode-text-dim">
                    {envConfig.providers[currentProvider].has_api_key
                      ? ' - API Key configured'
                      : ' - No API Key'}
                  </span>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="mt-4 flex gap-3">
              <button
                onClick={handleOpenEnv}
                className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
              >
                Open .env File
              </button>
              <button
                onClick={handleOpenEnvEditor}
                className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover"
              >
                Edit .env Content
              </button>
            </div>
          </div>
        </div>

        {/* .env Inline Editor Modal */}
        {showEnvEditor && (
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
            <div className="px-4 py-3 border-b border-vscode-border flex items-center justify-between">
              <div>
                <h2 className="text-sm font-medium text-vscode-text">Edit .env File</h2>
                <p className="text-xs text-vscode-text-dim mt-1">
                  Changes take effect after saving. A backup (.env.bak) is created automatically.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveEnv}
                  disabled={saving}
                  className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={() => setShowEnvEditor(false)}
                  className="px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover"
                >
                  Cancel
                </button>
              </div>
            </div>
            <div className="p-4">
              <textarea
                value={envEditedContent}
                onChange={(e) => setEnvEditedContent(e.target.value)}
                className="w-full h-96 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text font-mono resize-vertical"
                spellCheck={false}
              />
            </div>
          </div>
        )}

        {/* Provider Configuration (read-only from .env) */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Provider Configuration</h2>
            <p className="text-xs text-vscode-text-dim mt-1">
              Read from <code className="text-vscode-accent">.env</code> file. Use the buttons above to edit.
            </p>
          </div>
          <div className="p-4 space-y-4">
            {providers.map(provider => {
              const info = envConfig?.providers[provider.id];
              const isActive = currentProvider === provider.id;

              return (
                <div
                  key={provider.id}
                  className={clsx(
                    'p-4 rounded-sm border',
                    isActive ? 'border-vscode-accent bg-vscode-bg' : 'border-vscode-border bg-vscode-bg-light'
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-vscode-text">{provider.name}</span>
                      {isActive && (
                        <span className="px-2 py-0.5 text-xs bg-vscode-accent text-white rounded-sm">Active</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        'w-2 h-2 rounded-full',
                        info?.has_api_key ? 'bg-vscode-green' : 'bg-vscode-text-dim'
                      )}></span>
                      <span className="text-xs text-vscode-text-dim">
                        {info?.has_api_key ? 'Configured' : 'Not configured'}
                      </span>
                    </div>
                  </div>

                  {/* API Key (read-only) */}
                  <div className="mb-2">
                    <span className="text-xs text-vscode-text-dim">API Key: </span>
                    <code className="text-xs text-vscode-text">
                      {info?.api_key_masked || 'Not set'}
                    </code>
                    <code className="text-xs text-vscode-text-dim ml-2">({info?.api_key_env || 'env var'})</code>
                  </div>

                  {/* Group ID (read-only, MiniMax only) */}
                  {provider.requires_group_id && (
                    <div className="mb-2">
                      <span className="text-xs text-vscode-text-dim">Group ID: </span>
                      <code className="text-xs text-vscode-text">
                        {info?.group_id || 'Not set'}
                      </code>
                      <code className="text-xs text-vscode-text-dim ml-2">({info?.group_id_env || 'env var'})</code>
                    </div>
                  )}

                  {/* Model (read-only) */}
                  <div>
                    <span className="text-xs text-vscode-text-dim">Model: </span>
                    <code className="text-xs text-vscode-text">
                      {info?.model || 'Not set'}
                    </code>
                    <code className="text-xs text-vscode-text-dim ml-2">({info?.model_env || 'env var'})</code>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Storage Paths Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Memory Storage Path</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Configure where memory files are stored</p>
          </div>
          <div className="p-4 space-y-4">
            {/* Local Storage Path */}
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">
                Storage Root Path (memory files saved to {'<path>'}/memory/)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={storagePaths.local_storage_path || ''}
                  onChange={(e) => setStoragePaths(prev => ({
                    ...prev,
                    local_storage_path: e.target.value
                  }))}
                  placeholder="./wolf_data"
                  className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                />
                <button
                  onClick={() => handleSaveStoragePath('local_storage', storagePaths.local_storage_path)}
                  disabled={saving || !storagePaths.local_storage_path}
                  className={clsx(
                    'px-3 py-1.5 text-xs rounded-sm',
                    storagePaths.local_storage_path
                      ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                      : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                  )}
                >
                  Save
                </button>
              </div>
              {storagePathsStatus.local_storage_path && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    storagePathsStatus.local_storage_path.exists ? 'bg-vscode-green' : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {storagePathsStatus.local_storage_path.exists
                      ? (storagePathsStatus.local_storage_path.is_writable ? 'Exists and writable' : 'Exists but not writable')
                      : 'Does not exist (will be created)'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Memory Management */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Memory Management</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Export and import your conversation memories locally</p>
          </div>
          <div className="p-4">
            <div className="space-y-4">
              <div>
                <div className="text-xs text-vscode-text-dim mb-2">
                  Export Memories - Download all conversations as a JSON file
                </div>
                <button
                  onClick={() => {
                    const { sessions } = (window as any).__WOLF_STORES__.sessionStore?.getState?.() || { sessions: [] };
                    if (sessions && sessions.length > 0) {
                      const dataStr = JSON.stringify(sessions, null, 2);
                      const blob = new Blob([dataStr], { type: 'application/json' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `wolf-memories-${new Date().toISOString().slice(0, 10)}.json`;
                      link.click();
                      URL.revokeObjectURL(url);
                    } else {
                      alert('No sessions to export');
                    }
                  }}
                  className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
                >
                  Export All Memories
                </button>
              </div>

              <div className="border-t border-vscode-border pt-4">
                <div className="text-xs text-vscode-text-dim mb-2">
                  Import Memories - Load conversations from a JSON file
                </div>
                <div className="flex gap-2">
                  <input
                    type="file"
                    id="memory-import"
                    accept=".json"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      try {
                        const text = await file.text();
                        const imported = JSON.parse(text);
                        if (!Array.isArray(imported)) {
                          throw new Error('Invalid format');
                        }
                        const event = new CustomEvent('wolf:import-memories', { detail: text });
                        window.dispatchEvent(event);
                        alert(`Successfully imported ${imported.length} session(s)`);
                      } catch (err) {
                        alert('Failed to import: Invalid JSON format');
                      }
                      e.target.value = '';
                    }}
                    className="hidden"
                  />
                  <label
                    htmlFor="memory-import"
                    className="px-4 py-2 text-sm bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover cursor-pointer"
                  >
                    Select JSON File
                  </label>
                </div>
              </div>

              <div className="border-t border-vscode-border pt-4">
                <div className="text-xs text-vscode-text-dim mb-2">
                  Current Sessions Info
                </div>
                <div className="text-xs text-vscode-text font-mono bg-vscode-bg p-2 rounded-sm">
                  {(window as any).__WOLF_STORES__?.sessionStore?.getState?.()?.sessions?.length || 0} sessions stored locally
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Query Engine Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Query Engine Configuration</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Configure how the query engine processes requests</p>
          </div>
          <div className="p-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Max Turns</label>
              <input
                type="number"
                value={queryEngineConfig.max_turns}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, max_turns: parseInt(e.target.value) || 10 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Max Tokens</label>
              <input
                type="number"
                value={queryEngineConfig.max_tokens}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, max_tokens: parseInt(e.target.value) || 8000 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={queryEngineConfig.temperature}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, temperature: parseFloat(e.target.value) || 0.7 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Timeout (seconds)</label>
              <input
                type="number"
                value={queryEngineConfig.timeout}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, timeout: parseFloat(e.target.value) || 120 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Max Parallel Tools</label>
              <input
                type="number"
                value={queryEngineConfig.max_parallel_tools}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, max_parallel_tools: parseInt(e.target.value) || 5 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">Max Context Tokens</label>
              <input
                type="number"
                value={queryEngineConfig.max_context_tokens}
                onChange={(e) => setQueryEngineConfig({ ...queryEngineConfig, max_context_tokens: parseInt(e.target.value) || 100000 })}
                onBlur={() => configService.updateQueryEngineConfig(queryEngineConfig)}
                className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
            </div>
          </div>
        </div>

        {/* Tool Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Tool Configuration</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Enable or disable specific tools</p>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Max Concurrent Reads</span>
              <input
                type="number"
                value={toolConfig.max_concurrent_reads}
                onChange={(e) => setToolConfig({ ...toolConfig, max_concurrent_reads: parseInt(e.target.value) || 10 })}
                onBlur={() => configService.updateToolConfig(toolConfig)}
                className="w-24 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1 text-sm text-vscode-text"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Bash Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.bash_enabled; setToolConfig({ ...toolConfig, bash_enabled: newVal }); configService.updateToolConfig({ bash_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.bash_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.bash_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Edit Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.edit_enabled; setToolConfig({ ...toolConfig, edit_enabled: newVal }); configService.updateToolConfig({ edit_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.edit_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.edit_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Write Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.write_enabled; setToolConfig({ ...toolConfig, write_enabled: newVal }); configService.updateToolConfig({ write_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.write_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.write_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Glob Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.glob_enabled; setToolConfig({ ...toolConfig, glob_enabled: newVal }); configService.updateToolConfig({ glob_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.glob_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.glob_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Grep Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.grep_enabled; setToolConfig({ ...toolConfig, grep_enabled: newVal }); configService.updateToolConfig({ grep_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.grep_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.grep_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-vscode-text">Agent Tool</span>
              <button
                onClick={() => { const newVal = !toolConfig.agent_enabled; setToolConfig({ ...toolConfig, agent_enabled: newVal }); configService.updateToolConfig({ agent_enabled: newVal }); }}
                className={clsx('px-3 py-1 text-xs rounded-sm', toolConfig.agent_enabled ? 'bg-vscode-green text-white' : 'bg-vscode-bg text-vscode-text-dim')}
              >
                {toolConfig.agent_enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          </div>
        </div>

        {/* MCP Servers Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">MCP Servers</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Configure Model Context Protocol servers</p>
          </div>
          <div className="p-4">
            {mcpServers.length > 0 ? (
              <div className="space-y-2 mb-4">
                {mcpServers.map((server, index) => (
                  <div key={index} className="flex items-center justify-between bg-vscode-bg rounded-sm p-3">
                    <div>
                      <div className="text-sm text-vscode-text font-medium">{server.name}</div>
                      <div className="text-xs text-vscode-text-dim">{server.type} {server.command ? `- ${server.command}` : server.url || ''}</div>
                    </div>
                    <button
                      onClick={async () => {
                        await configService.updateMCPServers('remove', server);
                        fetchNewConfig();
                      }}
                      className="px-2 py-1 text-xs bg-vscode-red/20 text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/30"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-vscode-text-dim mb-4">No MCP servers configured</div>
            )}

            <div className="border-t border-vscode-border pt-4">
              <div className="text-xs text-vscode-text-dim mb-2">Add MCP Server</div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Server Name"
                  value={newMcpServer.name || ''}
                  onChange={(e) => setNewMcpServer({ ...newMcpServer, name: e.target.value })}
                  className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                />
                <select
                  value={newMcpServer.type || 'stdio'}
                  onChange={(e) => setNewMcpServer({ ...newMcpServer, type: e.target.value })}
                  className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                >
                  <option value="stdio">Stdio</option>
                  <option value="sse">SSE</option>
                  <option value="http">HTTP</option>
                  <option value="ws">WebSocket</option>
                </select>
                <input
                  type="text"
                  placeholder="Command (for stdio)"
                  value={newMcpServer.command || ''}
                  onChange={(e) => setNewMcpServer({ ...newMcpServer, command: e.target.value })}
                  className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text col-span-2"
                />
                <input
                  type="text"
                  placeholder="URL (for sse/http/ws)"
                  value={newMcpServer.url || ''}
                  onChange={(e) => setNewMcpServer({ ...newMcpServer, url: e.target.value })}
                  className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text col-span-2"
                />
              </div>
              <button
                onClick={async () => {
                  if (newMcpServer.name) {
                    await configService.updateMCPServers('add', newMcpServer as MCPServer);
                    setNewMcpServer({ name: '', type: 'stdio', command: '', args: [], url: '' });
                    fetchNewConfig();
                  }
                }}
                disabled={!newMcpServer.name}
                className="mt-3 px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Server
              </button>
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">How It Works</h2>
          </div>
          <div className="p-4">
            <ol className="text-xs text-vscode-text-dim space-y-2 list-decimal list-inside">
              <li>LLM provider and API keys are configured in the <code className="text-vscode-accent">.env</code> file</li>
              <li>Click "Open .env File" to edit it in your default text editor</li>
              <li>Or click "Edit .env Content" to edit directly in the browser</li>
              <li>Changes take effect after saving and reloading the configuration</li>
              <li>Select your active LLM provider from the dropdown above</li>
              <li>Go to Dashboard and submit your request</li>
              <li>WOLF AI will process your request using the configured LLM</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
