import React from 'react';
import clsx from 'clsx';

interface Channel {
  id: string;
  type: string;
  name: string;
  enabled: boolean;
  config: Record<string, any>;
  status?: string;
  connected?: boolean;
  last_sync?: string;
}

const channelTypes = [
  { type: 'telegram', name: 'Telegram Bot', icon: '📱', description: 'Connect via Telegram bot' },
  { type: 'discord', name: 'Discord Bot', icon: '🎮', description: 'Connect via Discord server' },
  { type: 'feishu', name: 'Feishu Bot', icon: '📋', description: 'Connect via Feishu/Lark' },
  { type: 'webhook', name: 'Webhook', icon: '🔗', description: 'HTTP webhook integration' },
];

const channelIcons: Record<string, string> = {
  telegram: '📱',
  discord: '🎮',
  feishu: '📋',
  webhook: '🔗',
};

export function Channels() {
  const [channels, setChannels] = React.useState<Channel[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [selectedChannel, setSelectedChannel] = React.useState<Channel | null>(null);
  const [newChannel, setNewChannel] = React.useState({ type: 'webhook', name: '', config: {} as Record<string, any> });
  const [testResult, setTestResult] = React.useState<any>(null);

  React.useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/channels');
      const data = await res.json();
      if (data.success) {
        setChannels(data.channels);
      }
    } catch (error) {
      console.error('Failed to fetch channels:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChannel = async () => {
    if (!newChannel.name.trim()) return;
    try {
      const res = await fetch('http://localhost:8000/api/channels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newChannel),
      });
      const data = await res.json();
      if (data.success) {
        setChannels(prev => [...prev, data.channel]);
        setShowCreateModal(false);
        setNewChannel({ type: 'webhook', name: '', config: {} });
      }
    } catch (error) {
      console.error('Failed to create channel:', error);
    }
  };

  const handleDeleteChannel = async (channelId: string) => {
    if (!confirm('Are you sure you want to delete this channel?')) return;
    try {
      await fetch(`http://localhost:8000/api/channels/${channelId}`, { method: 'DELETE' });
      setChannels(prev => prev.filter(c => c.id !== channelId));
      if (selectedChannel?.id === channelId) {
        setSelectedChannel(null);
      }
    } catch (error) {
      console.error('Failed to delete channel:', error);
    }
  };

  const handleToggleChannel = async (channelId: string, enabled: boolean) => {
    try {
      const endpoint = enabled ? 'enable' : 'disable';
      const res = await fetch(`http://localhost:8000/api/channels/${channelId}/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setChannels(prev => prev.map(c => c.id === channelId ? data.channel : c));
        if (selectedChannel?.id === channelId) {
          setSelectedChannel(data.channel);
        }
      }
    } catch (error) {
      console.error('Failed to toggle channel:', error);
    }
  };

  const handleTestChannel = async (channelId: string) => {
    setTestResult(null);
    try {
      const res = await fetch(`http://localhost:8000/api/channels/${channelId}/test`, { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
    } catch (error) {
      setTestResult({ success: false, message: 'Test failed: ' + String(error) });
    }
  };

  const handleSaveCredentials = async (channelId: string, credentials: any) => {
    try {
      const res = await fetch(`http://localhost:8000/api/channels/${channelId}/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      const data = await res.json();
      if (data.success) {
        alert('Credentials saved successfully');
      }
    } catch (error) {
      console.error('Failed to save credentials:', error);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">Channel Integrations</h1>
            <p className="text-xs text-vscode-text-dim">
              Connect to Telegram, Discord, Feishu, and webhooks for remote control
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
          >
            + Add Channel
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Channel list */}
        <div className="w-80 border-r border-vscode-border flex flex-col overflow-hidden">
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light">
            <h2 className="text-xs font-medium text-vscode-text uppercase tracking-wide">
              Channels ({channels.length})
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">Loading...</div>
            ) : channels.length === 0 ? (
              <div className="p-4 text-center text-xs text-vscode-text-dim">
                No channels configured. Add one to get started.
              </div>
            ) : (
              <div className="divide-y divide-vscode-border">
                {channels.map(channel => (
                  <div
                    key={channel.id}
                    onClick={() => setSelectedChannel(channel)}
                    className={clsx(
                      'p-3 cursor-pointer hover:bg-vscode-bg-hover transition-colors',
                      selectedChannel?.id === channel.id && 'bg-vscode-bg-active'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{channelIcons[channel.type] || '📡'}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-vscode-text font-medium truncate">{channel.name}</div>
                          <div className="text-xs text-vscode-text-dim">{channel.type}</div>
                        </div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={channel.enabled}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleToggleChannel(channel.id, !channel.enabled);
                          }}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-vscode-border rounded-full peer peer-checked:bg-vscode-accent peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                      </label>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={clsx(
                        'w-2 h-2 rounded-full',
                        channel.connected ? 'bg-vscode-green' : 'bg-vscode-text-dim'
                      )}></span>
                      <span className="text-xs text-vscode-text-dim">
                        {channel.status || (channel.enabled ? 'Connected' : 'Disabled')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Channel detail */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedChannel ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-5xl mb-4">📡</div>
                <div className="text-vscode-text mb-2">Select a channel to view details</div>
                <div className="text-xs text-vscode-text-dim">
                  Configure Telegram, Discord, Feishu, or webhook integrations
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="max-w-2xl">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{channelIcons[selectedChannel.type] || '📡'}</span>
                    <div>
                      <h2 className="text-lg font-semibold text-vscode-text">{selectedChannel.name}</h2>
                      <p className="text-sm text-vscode-text-dim">{selectedChannel.type} channel</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteChannel(selectedChannel.id)}
                    className="px-3 py-1.5 text-xs text-vscode-red border border-vscode-red/30 rounded-sm hover:bg-vscode-red/20"
                  >
                    Delete
                  </button>
                </div>

                {/* Status */}
                <div className="mb-6 p-4 bg-vscode-bg-light border border-vscode-border rounded-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={clsx(
                        'w-3 h-3 rounded-full',
                        selectedChannel.connected ? 'bg-vscode-green animate-pulse' : 'bg-vscode-text-dim'
                      )}></span>
                      <div>
                        <div className="text-sm text-vscode-text font-medium">
                          {selectedChannel.status || (selectedChannel.enabled ? 'Connected' : 'Disabled')}
                        </div>
                        <div className="text-xs text-vscode-text-dim">
                          Last sync: {selectedChannel.last_sync || 'Never'}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleTestChannel(selectedChannel.id)}
                      className="px-3 py-1.5 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:border-vscode-accent"
                    >
                      Test Connection
                    </button>
                  </div>
                </div>

                {/* Test result */}
                {testResult && (
                  <div className={clsx(
                    'mb-6 p-4 rounded-sm border',
                    testResult.success
                      ? 'bg-vscode-green/10 border-vscode-green/30 text-vscode-green'
                      : 'bg-vscode-red/10 border-vscode-red/30 text-vscode-red'
                  )}>
                    <div className="text-sm">{testResult.message}</div>
                    {testResult.response_time_ms && (
                      <div className="text-xs mt-1">Response time: {testResult.response_time_ms}ms</div>
                    )}
                  </div>
                )}

                {/* Configuration */}
                <div className="mb-6">
                  <h3 className="text-xs text-vscode-text-dim uppercase tracking-wide mb-3">Configuration</h3>
                  <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4">
                    {selectedChannel.type === 'telegram' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Bot Username</label>
                          <input
                            type="text"
                            defaultValue={selectedChannel.config.bot_username || ''}
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="@your_bot"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Bot Token</label>
                          <input
                            type="password"
                            defaultValue=""
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="123456:ABC-DEF..."
                          />
                        </div>
                      </div>
                    )}
                    {selectedChannel.type === 'discord' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Server Name</label>
                          <input
                            type="text"
                            defaultValue={selectedChannel.config.server_name || ''}
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="My Server"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Bot Token</label>
                          <input
                            type="password"
                            defaultValue=""
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="Bot token"
                          />
                        </div>
                      </div>
                    )}
                    {selectedChannel.type === 'feishu' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">App Name</label>
                          <input
                            type="text"
                            defaultValue={selectedChannel.config.app_name || ''}
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="WOLF Bot"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">App ID</label>
                          <input
                            type="text"
                            defaultValue=""
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="cli_xxx"
                          />
                        </div>
                      </div>
                    )}
                    {selectedChannel.type === 'webhook' && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Inbound URL</label>
                          <input
                            type="text"
                            defaultValue={selectedChannel.config.inbound_url || ''}
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="https://your-domain.com/webhook"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-vscode-text-dim mb-1">Outbound URL</label>
                          <input
                            type="text"
                            defaultValue={selectedChannel.config.outbound_url || ''}
                            className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                            placeholder="https://target-endpoint.com/webhook"
                          />
                        </div>
                      </div>
                    )}
                    <button
                      onClick={() => handleSaveCredentials(selectedChannel.id, {})}
                      className="mt-4 px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
                    >
                      Save Configuration
                    </button>
                  </div>
                </div>

                {/* Commands */}
                {selectedChannel.config.commands && selectedChannel.config.commands.length > 0 && (
                  <div>
                    <h3 className="text-xs text-vscode-text-dim uppercase tracking-wide mb-3">Available Commands</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedChannel.config.commands.map((cmd: string) => (
                        <span
                          key={cmd}
                          className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm font-mono"
                        >
                          {cmd}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Channel Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm w-full max-w-md p-6">
            <h2 className="text-lg font-semibold text-vscode-text mb-4">Add Channel</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Channel Type</label>
                <select
                  value={newChannel.type}
                  onChange={(e) => setNewChannel({ ...newChannel, type: e.target.value })}
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                >
                  {channelTypes.map(ct => (
                    <option key={ct.type} value={ct.type}>{ct.icon} {ct.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Channel Name *</label>
                <input
                  type="text"
                  value={newChannel.name}
                  onChange={(e) => setNewChannel({ ...newChannel, name: e.target.value })}
                  placeholder="e.g., Production Telegram"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCreateChannel}
                disabled={!newChannel.name.trim()}
                className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Channel
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewChannel({ type: 'webhook', name: '', config: {} });
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