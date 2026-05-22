import React from 'react';
import clsx from 'clsx';

interface Provider {
  id: string;
  name: string;
  models: string[];
  requires_group_id: boolean;
  api_key_label: string;
  group_id_label: string | null;
}

interface ProviderConfig {
  api_key: string | null;
  group_id: string | null;
  model: string;
  has_api_key: boolean;
}

interface ConfigResponse {
  current_provider: string;
  config: {
    current_provider: string;
    providers: Record<string, ProviderConfig>;
  };
}

const DEFAULT_PROVIDERS: Provider[] = [
  {
    id: 'minimax',
    name: 'MiniMax',
    models: ['MiniMax-M2.7'],
    requires_group_id: true,
    api_key_label: 'MiniMax API Key',
    group_id_label: 'MiniMax Group ID'
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    models: ['deepseek-chat', 'deepseek-coder'],
    requires_group_id: false,
    api_key_label: 'DeepSeek API Key',
    group_id_label: null
  },
  {
    id: 'qwen',
    name: 'Qwen (Alibaba)',
    models: ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    requires_group_id: false,
    api_key_label: 'Qwen API Key',
    group_id_label: null
  },
  {
    id: 'openai',
    name: 'OpenAI',
    models: ['gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
    requires_group_id: false,
    api_key_label: 'OpenAI API Key',
    group_id_label: null
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
    requires_group_id: false,
    api_key_label: 'Anthropic API Key',
    group_id_label: null
  },
  {
    id: 'zhipu',
    name: 'Zhipu AI (智谱)',
    models: ['glm-4', 'glm-4-flash', 'glm-3-turbo'],
    requires_group_id: false,
    api_key_label: 'Zhipu API Key',
    group_id_label: null
  },
  {
    id: 'moonshot',
    name: 'Moonshot (月之暗面)',
    models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
    requires_group_id: false,
    api_key_label: 'Moonshot API Key',
    group_id_label: null
  }
];

export function Settings() {
  const [currentProvider, setCurrentProvider] = React.useState('minimax');
  const [providerConfigs, setProviderConfigs] = React.useState<Record<string, ProviderConfig>>({});
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [testing, setTesting] = React.useState<string | null>(null);
  const [testResult, setTestResult] = React.useState<{ success: boolean; message: string } | null>(null);

  // Storage paths state
  const [storagePaths, setStoragePaths] = React.useState<Record<string, string>>({});
  const [storagePathsStatus, setStoragePathsStatus] = React.useState<Record<string, any>>({});

  // Work directory state
  const [workDirectory, setWorkDirectory] = React.useState<string>('');
  const [workDirectoryStatus, setWorkDirectoryStatus] = React.useState<Record<string, any> | null>(null);

  // Permission modes state
  const [currentMode, setCurrentMode] = React.useState<{id: string; name: string; icon: string; level: number} | null>(null);
  const [permissionModes, setPermissionModes] = React.useState<any[]>([]);

  // Form state for each provider
  const [formState, setFormState] = React.useState<Record<string, {
    api_key: string;
    group_id: string;
    model: string;
  }>>({});

  React.useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/config/config');
      if (response.ok) {
        const data: ConfigResponse = await response.json();
        setCurrentProvider(data.current_provider);
        setProviderConfigs(data.config.providers || {});

        // Initialize form state for each provider
        const initialFormState: Record<string, any> = {};
        for (const provider of DEFAULT_PROVIDERS) {
          const providerConfig = data.config.providers?.[provider.id] || {};
          initialFormState[provider.id] = {
            api_key: providerConfig.api_key?.replace('***', '') || '',
            group_id: providerConfig.group_id || '',
            model: providerConfig.model || provider.models[0]
          };
        }
        setFormState(initialFormState);
      }

      // Fetch storage paths
      const pathsResponse = await fetch('http://localhost:8000/api/config/storage-paths');
      if (pathsResponse.ok) {
        const pathsData = await pathsResponse.json();
        setStoragePaths(pathsData.paths || {});
      }

      // Fetch storage paths status
      const statusResponse = await fetch('http://localhost:8000/api/config/storage-paths/status');
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        setStoragePathsStatus(statusData.status || {});
      }

      // Fetch work directory
      const workDirResponse = await fetch('http://localhost:8000/api/config/work-directory');
      if (workDirResponse.ok) {
        const workDirData = await workDirResponse.json();
        setWorkDirectory(workDirData.work_directory || '');
      }

      // Fetch work directory status
      const workDirStatusResponse = await fetch('http://localhost:8000/api/config/work-directory/status');
      if (workDirStatusResponse.ok) {
        const workDirStatusData = await workDirStatusResponse.json();
        setWorkDirectoryStatus(workDirStatusData.status || null);
      }

      // Fetch permission modes
      const permResponse = await fetch('http://localhost:8000/api/permissions/modes');
      if (permResponse.ok) {
        const permData = await permResponse.json();
        setPermissionModes(permData.modes || []);
      }

      // Fetch current permission
      const currentPermResponse = await fetch('http://localhost:8000/api/permissions/current');
      if (currentPermResponse.ok) {
        const currentPermData = await currentPermResponse.json();
        if (currentPermData.current_mode) {
          setCurrentMode(currentPermData.current_mode);
        }
      }
    } catch (error) {
      console.error('Failed to fetch config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = async (providerId: string) => {
    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/config/provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: providerId })
      });
      if (response.ok) {
        await fetchConfig();
      }
    } catch (error) {
      console.error('Failed to set provider:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKey = async (providerId: string) => {
    const form = formState[providerId];
    if (!form?.api_key) return;

    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/config/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          api_key: form.api_key,
          group_id: form.group_id || undefined
        })
      });
      if (response.ok) {
        await fetchConfig();
      }
    } catch (error) {
      console.error('Failed to save API key:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleTestApiKey = async (providerId: string) => {
    const form = formState[providerId];
    if (!form?.api_key) return;

    setTesting(providerId);
    setTestResult(null);
    try {
      const response = await fetch('http://localhost:8000/api/config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          api_key: form.api_key,
          group_id: form.group_id || undefined,
          model: form.model || undefined
        })
      });
      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({ success: false, message: String(error) });
    } finally {
      setTesting(null);
    }
  };

  const handleModelChange = async (providerId: string, model: string) => {
    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/config/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: providerId, model })
      });
      if (response.ok) {
        await fetchConfig();
      }
    } catch (error) {
      console.error('Failed to set model:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleSwitchPermissionMode = async (modeId: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/permissions/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode_id: modeId })
      });
      const data = await response.json();
      if (data.success && data.mode) {
        setCurrentMode(data.mode);
        alert(`Switched to ${data.mode.name} mode`);
      }
    } catch (error) {
      console.error('Failed to switch permission mode:', error);
    }
  };

  const updateFormState = (providerId: string, field: 'api_key' | 'group_id' | 'model', value: string) => {
    setFormState(prev => ({
      ...prev,
      [providerId]: {
        ...prev[providerId],
        [field]: value
      }
    }));
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-vscode-text-dim">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-lg font-semibold text-vscode-text mb-6">Settings</h1>

        {/* Current Provider */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Current LLM Provider</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Select and configure your LLM provider</p>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-4">
              <select
                value={currentProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                disabled={saving}
                className="bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text flex-1"
              >
                {DEFAULT_PROVIDERS.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <div className="text-xs text-vscode-text-dim">
                {saving ? 'Saving...' : 'Saved'}
              </div>
            </div>

            {/* Show current provider config */}
            {providerConfigs[currentProvider] && (
              <div className="mt-4 p-3 bg-vscode-bg rounded-sm border border-vscode-border">
                <div className="flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    providerConfigs[currentProvider].has_api_key
                      ? 'bg-vscode-green'
                      : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {currentProvider.toUpperCase()} -
                  </span>
                  <span className="text-vscode-text font-mono">
                    {providerConfigs[currentProvider].model || 'No model selected'}
                  </span>
                  <span className="text-vscode-text-dim">
                    {providerConfigs[currentProvider].has_api_key
                      ? ' - API Key configured'
                      : ' - No API Key'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Provider Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Provider Configuration</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Configure API keys for different LLM providers</p>
          </div>
          <div className="p-4 space-y-6">
            {DEFAULT_PROVIDERS.map(provider => {
              const providerConfig = providerConfigs?.[provider.id];
              const form = formState[provider.id] || { api_key: '', group_id: '', model: provider.models[0] };
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
                        providerConfig?.has_api_key ? 'bg-vscode-green' : 'bg-vscode-text-dim'
                      )}></span>
                      <span className="text-xs text-vscode-text-dim">
                        {providerConfig?.has_api_key ? 'Configured' : 'Not configured'}
                      </span>
                    </div>
                  </div>

                  {/* API Key */}
                  <div className="mb-3">
                    <label className="block text-xs text-vscode-text-dim mb-1">
                      {provider.api_key_label}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={form.api_key}
                        onChange={(e) => updateFormState(provider.id, 'api_key', e.target.value)}
                        placeholder={providerConfig?.has_api_key ? '••••••••' : 'Enter API key'}
                        className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                      />
                      <button
                        onClick={() => handleSaveApiKey(provider.id)}
                        disabled={saving || !form.api_key}
                        className={clsx(
                          'px-3 py-1.5 text-xs rounded-sm',
                          form.api_key
                            ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                            : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                        )}
                      >
                        Save
                      </button>
                      <button
                        onClick={() => handleTestApiKey(provider.id)}
                        disabled={testing !== null || !form.api_key}
                        className={clsx(
                          'px-3 py-1.5 text-xs rounded-sm border border-vscode-border',
                          form.api_key
                            ? 'hover:bg-vscode-bg-hover'
                            : 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {testing === provider.id ? 'Testing...' : 'Test'}
                      </button>
                    </div>
                  </div>

                  {/* Group ID (for MiniMax) */}
                  {provider.requires_group_id && (
                    <div className="mb-3">
                      <label className="block text-xs text-vscode-text-dim mb-1">
                        {provider.group_id_label}
                      </label>
                      <input
                        type="text"
                        value={form.group_id}
                        onChange={(e) => updateFormState(provider.id, 'group_id', e.target.value)}
                        placeholder="Enter Group ID"
                        className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                      />
                    </div>
                  )}

                  {/* Model Selection */}
                  <div>
                    <label className="block text-xs text-vscode-text-dim mb-1">
                      Model
                    </label>
                    <select
                      value={form.model || provider.models[0]}
                      onChange={(e) => handleModelChange(provider.id, e.target.value)}
                      disabled={saving}
                      className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                    >
                      {provider.models.map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>

                  {/* Test Result */}
                  {testResult && testing === null && (
                    <div className={clsx(
                      'mt-3 p-2 rounded-sm text-xs',
                      testResult.success ? 'bg-vscode-green/20 text-vscode-green' : 'bg-vscode-red/20 text-vscode-red'
                    )}>
                      {testResult.message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Storage Paths Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Local Storage Paths</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Configure where files are stored locally</p>
          </div>
          <div className="p-4 space-y-4">
            {/* Local Storage Path */}
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">
                Local Storage Root Path
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
                  onClick={async () => {
                    setSaving(true);
                    try {
                      const response = await fetch('http://localhost:8000/api/config/storage-path', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          path_type: 'local_storage',
                          path: storagePaths.local_storage_path
                        })
                      });
                      if (response.ok) {
                        await fetchConfig();
                      }
                    } catch (error) {
                      console.error('Failed to save storage path:', error);
                    } finally {
                      setSaving(false);
                    }
                  }}
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

            {/* Knowledge Base Path */}
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">
                Knowledge Base Path
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={storagePaths.knowledge_base_path || ''}
                  onChange={(e) => setStoragePaths(prev => ({
                    ...prev,
                    knowledge_base_path: e.target.value
                  }))}
                  placeholder="./wolf_data/knowledge"
                  className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                />
                <button
                  onClick={async () => {
                    setSaving(true);
                    try {
                      const response = await fetch('http://localhost:8000/api/config/storage-path', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          path_type: 'knowledge_base',
                          path: storagePaths.knowledge_base_path
                        })
                      });
                      if (response.ok) {
                        await fetchConfig();
                      }
                    } catch (error) {
                      console.error('Failed to save storage path:', error);
                    } finally {
                      setSaving(false);
                    }
                  }}
                  disabled={saving || !storagePaths.knowledge_base_path}
                  className={clsx(
                    'px-3 py-1.5 text-xs rounded-sm',
                    storagePaths.knowledge_base_path
                      ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                      : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                  )}
                >
                  Save
                </button>
              </div>
              {storagePathsStatus.knowledge_base_path && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    storagePathsStatus.knowledge_base_path.exists ? 'bg-vscode-green' : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {storagePathsStatus.knowledge_base_path.exists
                      ? (storagePathsStatus.knowledge_base_path.is_writable ? 'Exists and writable' : 'Exists but not writable')
                      : 'Does not exist (will be created)'}
                  </span>
                </div>
              )}
            </div>

            {/* Sessions Path */}
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">
                Sessions History Path
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={storagePaths.sessions_path || ''}
                  onChange={(e) => setStoragePaths(prev => ({
                    ...prev,
                    sessions_path: e.target.value
                  }))}
                  placeholder="./wolf_data/sessions"
                  className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                />
                <button
                  onClick={async () => {
                    setSaving(true);
                    try {
                      const response = await fetch('http://localhost:8000/api/config/storage-path', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          path_type: 'sessions',
                          path: storagePaths.sessions_path
                        })
                      });
                      if (response.ok) {
                        await fetchConfig();
                      }
                    } catch (error) {
                      console.error('Failed to save storage path:', error);
                    } finally {
                      setSaving(false);
                    }
                  }}
                  disabled={saving || !storagePaths.sessions_path}
                  className={clsx(
                    'px-3 py-1.5 text-xs rounded-sm',
                    storagePaths.sessions_path
                      ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                      : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                  )}
                >
                  Save
                </button>
              </div>
              {storagePathsStatus.sessions_path && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    storagePathsStatus.sessions_path.exists ? 'bg-vscode-green' : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {storagePathsStatus.sessions_path.exists
                      ? (storagePathsStatus.sessions_path.is_writable ? 'Exists and writable' : 'Exists but not writable')
                      : 'Does not exist (will be created)'}
                  </span>
                </div>
              )}
            </div>

            {/* Upload Path */}
            <div>
              <label className="block text-xs text-vscode-text-dim mb-1">
                Upload Files Path
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={storagePaths.upload_path || ''}
                  onChange={(e) => setStoragePaths(prev => ({
                    ...prev,
                    upload_path: e.target.value
                  }))}
                  placeholder="./wolf_data/uploads"
                  className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
                />
                <button
                  onClick={async () => {
                    setSaving(true);
                    try {
                      const response = await fetch('http://localhost:8000/api/config/storage-path', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          path_type: 'upload',
                          path: storagePaths.upload_path
                        })
                      });
                      if (response.ok) {
                        await fetchConfig();
                      }
                    } catch (error) {
                      console.error('Failed to save storage path:', error);
                    } finally {
                      setSaving(false);
                    }
                  }}
                  disabled={saving || !storagePaths.upload_path}
                  className={clsx(
                    'px-3 py-1.5 text-xs rounded-sm',
                    storagePaths.upload_path
                      ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                      : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                  )}
                >
                  Save
                </button>
              </div>
              {storagePathsStatus.upload_path && (
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <span className={clsx(
                    'w-2 h-2 rounded-full',
                    storagePathsStatus.upload_path.exists ? 'bg-vscode-green' : 'bg-vscode-red'
                  )}></span>
                  <span className="text-vscode-text-dim">
                    {storagePathsStatus.upload_path.exists
                      ? (storagePathsStatus.upload_path.is_writable ? 'Exists and writable' : 'Exists but not writable')
                      : 'Does not exist (will be created)'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Work Directory Configuration */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Work Directory</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Set the default directory for file operations (Agent will search/read files from here)</p>
          </div>
          <div className="p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={workDirectory}
                onChange={(e) => setWorkDirectory(e.target.value)}
                placeholder="C:\Users\24040\Desktop\graduation\article"
                className="flex-1 bg-vscode-bg border border-vscode-border rounded-sm px-3 py-1.5 text-sm text-vscode-text"
              />
              <button
                onClick={async () => {
                  setSaving(true);
                  try {
                    const response = await fetch('http://localhost:8000/api/config/work-directory', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ path: workDirectory })
                    });
                    const result = await response.json();
                    if (result.success) {
                      await fetchConfig();
                    } else {
                      alert('Failed to set work directory: ' + result.error);
                    }
                  } catch (error) {
                    console.error('Failed to save work directory:', error);
                  } finally {
                    setSaving(false);
                  }
                }}
                disabled={saving}
                className={clsx(
                  'px-4 py-1.5 text-xs rounded-sm',
                  workDirectory
                    ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                    : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
                )}
              >
                Save
              </button>
            </div>
            {workDirectoryStatus && (
              <div className="mt-2 flex items-center gap-2">
                <span className={clsx(
                  'w-2 h-2 rounded-full',
                  workDirectoryStatus.set
                    ? (workDirectoryStatus.exists ? 'bg-vscode-green' : 'bg-vscode-red')
                    : 'bg-vscode-text-dim'
                )}></span>
                <span className="text-xs text-vscode-text-dim">
                  {workDirectoryStatus.set
                    ? (workDirectoryStatus.exists
                        ? (workDirectoryStatus.is_writable ? 'Directory ready' : 'Directory exists but not writable')
                        : 'Directory does not exist')
                    : 'Not configured'}
                </span>
              </div>
            )}
            <div className="mt-3 text-xs text-vscode-text-dim">
              <p>Example: C:\Users\24040\Desktop\graduation\article</p>
              <p className="mt-1">When configured, Agent can automatically search and read files from this directory.</p>
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
                        // Store will be updated via the session store
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

        {/* Permission Modes */}
        <div className="bg-vscode-bg-light border border-vscode-border rounded-sm mb-6">
          <div className="px-4 py-3 border-b border-vscode-border">
            <h2 className="text-sm font-medium text-vscode-text">Permission Mode</h2>
            <p className="text-xs text-vscode-text-dim mt-1">Control what operations are available based on your permission level</p>
          </div>
          <div className="p-4">
            <div className="space-y-3" id="permission-modes">
              {permissionModes.map(mode => (
                <div
                  key={mode.id}
                  className={clsx(
                    'flex items-center justify-between p-3 rounded-sm border transition-colors cursor-pointer',
                    currentMode?.id === mode.id
                      ? 'border-vscode-accent bg-vscode-bg'
                      : 'border-vscode-border bg-vscode-bg-light hover:border-vscode-accent'
                  )}
                  onClick={() => handleSwitchPermissionMode(mode.id)}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{mode.icon}</span>
                    <div>
                      <div className="text-sm text-vscode-text font-medium">{mode.name}</div>
                      <div className="text-xs text-vscode-text-dim">{mode.description}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-vscode-text-dim">Level {mode.level}</span>
                    {currentMode?.id === mode.id && (
                      <span className="px-2 py-0.5 text-xs bg-vscode-accent text-white rounded-sm">Active</span>
                    )}
                  </div>
                </div>
              ))}
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
              <li>Select and configure your preferred LLM provider above</li>
              <li>Enter your API key and save it securely</li>
              <li>Click "Test" to verify your API key works</li>
              <li>Select a model from the available options</li>
              <li>Go to Dashboard and submit your request</li>
              <li>WOLF AI will process your request using the configured LLM</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}