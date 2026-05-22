import React from 'react';

export function AgentTyping() {
  return (
    <div className="flex items-center gap-2 text-vscode-text-dim">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-vscode-yellow rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
        <span className="w-2 h-2 bg-vscode-yellow rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
        <span className="w-2 h-2 bg-vscode-yellow rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
      </div>
      <span className="text-xs">Agent is thinking...</span>
    </div>
  );
}