import React from 'react';
import { wsService } from '@/services';
import { useUIStore } from '@/store';

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

export function StatusBar() {
  const isConnected = wsService.isConnected();
  const { tokenUsage, tokenLimit } = useUIStore();

  const pct = tokenLimit > 0 ? Math.min(100, (tokenUsage / tokenLimit) * 100) : 0;
  const barColor =
    pct > 90 ? 'bg-red-500' :
    pct > 70 ? 'bg-yellow-500' :
    'bg-green-500';

  return (
    <footer className="flex items-center justify-between h-8 px-4 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
      {/* Left: connection + context bar */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
            {isConnected ? '●' : '○'}
          </span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>

        {/* Context progress bar */}
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">ctx</span>
          <div className="w-24 h-2.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all duration-300 rounded-full`}
              style={{ width: `${Math.max(2, pct)}%` }}
            />
          </div>
          <span className="font-mono text-gray-400">
            {formatTokens(tokenUsage)}/{formatTokens(tokenLimit)}
          </span>
        </div>
      </div>

      {/* Right: version */}
      <div className="flex items-center gap-4">
        <span>WOLF AI</span>
        <span>v1.0.0</span>
      </div>
    </footer>
  );
}
