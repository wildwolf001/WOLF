import React from 'react';
import { useChat, useAgent } from '@/hooks';
import { ChatMessage } from './ChatMessage';
import { AgentTyping } from './AgentTyping';
import { useChatStore, useSessionStore } from '@/store';
import clsx from 'clsx';

export function ChatWindow() {
  const { agents } = useAgent();
  const { messages, isTyping, sendMessage } = useChat();
  const [input, setInput] = React.useState('');
  const [selectedAgent, setSelectedAgent] = React.useState('main');
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Session management
  const { sessions, currentSessionId, setCurrentSession, addSession, deleteSession } = useSessionStore();

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Listen for memory import events
  React.useEffect(() => {
    const handleImport = (e: CustomEvent<string>) => {
      const { importSessions } = useSessionStore.getState();
      importSessions(e.detail);
    };
    window.addEventListener('wolf:import-memories', handleImport as EventListener);
    return () => window.removeEventListener('wolf:import-memories', handleImport as EventListener);
  }, []);

  const handleSend = () => {
    if (!input.trim()) return;
    // Send message to the selected agent
    sendMessage(input, selectedAgent);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewSession = () => {
    const session = addSession();
    setCurrentSession(session.id);
  };

  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this conversation? This cannot be undone.')) {
      deleteSession(id);
      if (currentSessionId === id) {
        const remaining = sessions.filter(s => s.id !== id);
        setCurrentSession(remaining.length > 0 ? remaining[0].id : null);
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Session selector */}
      <div className="h-10 px-4 flex items-center gap-2 bg-vscode-bg-light border-b border-vscode-border">
        <span className="text-xs text-vscode-text-dim">Session:</span>
        <select
          value={currentSessionId || ''}
          onChange={(e) => setCurrentSession(e.target.value || null)}
          className="bg-vscode-bg border border-vscode-border rounded-sm px-2 py-1 text-xs text-vscode-text max-w-[180px]"
        >
          {sessions.map(session => (
            <option key={session.id} value={session.id}>
              {session.name} ({session.messages.length})
            </option>
          ))}
        </select>
        <button
          onClick={handleNewSession}
          className="px-2 py-1 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
          title="New conversation"
        >
          + New
        </button>
        {currentSessionId && sessions.find(s => s.id === currentSessionId) && (
          <button
            onClick={(e) => handleDeleteSession(currentSessionId, e)}
            className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border text-vscode-text-dim rounded-sm hover:bg-vscode-red/20 hover:text-vscode-red"
            title="Delete conversation"
          >
            Delete
          </button>
        )}
        <div className="flex-1" />
        <span className="text-xs text-vscode-text-dim">Agent:</span>
        <select
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="bg-vscode-bg border border-vscode-border rounded-sm px-2 py-1 text-xs text-vscode-text"
        >
          {agents.map((agent) => (
            <option key={agent.id} value={agent.role}>
              {agent.name}
            </option>
          ))}
        </select>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="terminal-text text-vscode-text-dim mb-2">
                # Start a conversation
              </div>
              <div className="text-xs text-vscode-text-dim">
                Select an agent and type your message below
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isTyping && <AgentTyping />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 bg-vscode-bg-light border-t border-vscode-border">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
              className="w-full h-20 bg-vscode-bg border border-vscode-border rounded-sm p-3 text-sm text-vscode-text resize-none focus:border-vscode-accent"
              style={{ fontFamily: 'Consolas, Monaco, monospace' }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className={clsx(
              'px-4 rounded-sm text-xs font-medium transition-colors',
              input.trim()
                ? 'bg-vscode-accent text-white hover:bg-vscode-accent/80'
                : 'bg-vscode-bg-hover text-vscode-text-dim cursor-not-allowed'
            )}
          >
            Send
          </button>
        </div>

        <div className="mt-2 text-xs text-vscode-text-dim">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}