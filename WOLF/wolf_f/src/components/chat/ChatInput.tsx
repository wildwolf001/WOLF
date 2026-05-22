import React, { useState, useEffect, KeyboardEvent } from 'react';
import { useChatStore } from '@/store';

interface ChatInputProps {
  onSend: (content: string, agentRole?: string) => void;
}

export function ChatInput({ onSend }: ChatInputProps) {
  const [input, setInput] = useState('');
  const { addToHistory, navigateHistory, resetHistoryIndex, messageHistory, historyIndex } = useChatStore();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    addToHistory(input.trim()); // Add to history before sending
    onSend(input.trim());
    setInput('');
    resetHistoryIndex();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Cmd/Ctrl + Z: Undo (navigate up in history - older messages)
    if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
      e.preventDefault();
      const previousMessage = navigateHistory('up');
      setInput(previousMessage);
      return;
    }

    // Arrow Up: Navigate to previous message in history
    if (e.key === 'ArrowUp' && input === '') {
      e.preventDefault();
      const previousMessage = navigateHistory('up');
      setInput(previousMessage);
      return;
    }

    // Arrow Down: Navigate to newer message in history
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const nextMessage = navigateHistory('down');
      setInput(nextMessage);
      return;
    }

    // Enter: Submit (only if input is not empty)
    if (e.key === 'Enter' && !e.shiftKey && input.trim()) {
      e.preventDefault();
      addToHistory(input.trim());
      onSend(input.trim());
      setInput('');
      resetHistoryIndex();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
    // Reset history index when user types (to start fresh from end)
    if (historyIndex !== -1) {
      resetHistoryIndex();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-3 border-t border-vscode-border bg-vscode-bg-light">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (↑/↓ to navigate history, ⌘Z to undo)"
          className="flex-1 px-3 py-2 bg-vscode-bg border border-vscode-border rounded-sm text-sm text-vscode-text focus:border-vscode-accent focus:outline-none"
          style={{ fontFamily: 'Consolas, Monaco, monospace' }}
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="px-4 py-2 bg-vscode-accent text-white text-xs rounded-sm hover:bg-vscode-accent/80 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          Send
        </button>
      </div>
    </form>
  );
}