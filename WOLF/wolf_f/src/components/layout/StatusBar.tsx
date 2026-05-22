import React from 'react';
import { wsService } from '@/services';

export function StatusBar() {
  const isConnected = wsService.isConnected();

  return (
    <footer className="flex items-center justify-between h-8 px-4 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1">
          <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
            {isConnected ? '●' : '○'}
          </span>
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span>WOLF AI</span>
        <span>v1.0.0</span>
      </div>
    </footer>
  );
}
