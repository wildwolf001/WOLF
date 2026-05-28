import React from 'react';
import { useSessionStore, useUIStore, useTaskStore } from '@/store';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';

// Strip <think>...</think> blocks from text, return clean version
function stripThink(text: string): string {
  if (!text) return text;
  // Remove <think>...</think> including multiline content
  return text.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/\n{3,}/g, '\n\n').trim();
}

// Extract <think> content for display in Thinking panel
function extractThinkContent(text: string): string {
  if (!text) return '';
  const parts: string[] = [];
  const re = /<think>([\s\S]*?)<\/think>/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const t = m[1].trim();
    if (t) parts.push(t);
  }
  return parts.join('\n\n---\n\n');
}

interface AgentStatusEvent {
  agent: string;
  role: string;
  status: 'idle' | 'working' | 'analyzing';
  message: string;
}

export function UnifiedInput() {
  const [input, setInput] = React.useState('');
  const [isProcessing, setIsProcessing] = React.useState(false);
  const [selectedAgentRole, setSelectedAgentRole] = React.useState<string | null>(null);
  const [userChoiceOptions, setUserChoiceOptions] = React.useState<any>(null);
  const [streamingContent, setStreamingContent] = React.useState('');
  const [thinkingContent, setThinkingContent] = React.useState('');
  const [activeTool, setActiveTool] = React.useState<{ name: string; args: string } | null>(null);
  const streamingContentRef = React.useRef('');  // Use ref to track latest content
  const thinkingContentRef = React.useRef('');
  const logsEndRef = React.useRef<HTMLDivElement>(null);
  const chatEndRef = React.useRef<HTMLDivElement>(null);
  const eventSourceRef = React.useRef<EventSource | null>(null);
  const sessionIdRef = React.useRef<string | null>(null);  // Track current sessionId

  const {
    sessions,
    currentSessionId,
    addSession,
    setCurrentSession,
    addMessageToSession,
    addLogToSession,
    clearSessionLogs,
    deleteMessageFromSession,
    clearSessionMessages,
    getSession
  } = useSessionStore();

  const currentSession = currentSessionId ? getSession(currentSessionId) : null;
  const logs = currentSession?.logs || [];
  const messages = currentSession?.messages || [];

  // Compute historical thinking from all assistant messages
  const historicalThinking = React.useMemo(() => {
    const parts: string[] = [];
    for (const msg of messages) {
      if (!msg.isUser) {
        const th = extractThinkContent(msg.content);
        if (th) parts.push(th);
      }
    }
    return parts.join('\n\n---\n\n');
  }, [messages]);

  const displayThinking = thinkingContent || historicalThinking;

  React.useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamingContent, messages]);

  const setupEventListeners = (eventSource: EventSource, sessionId: string | null) => {
    // Update refs when setting up listeners
    sessionIdRef.current = sessionId;

    eventSource.addEventListener('thinking_start', (e) => {
      const data = JSON.parse(e.data);
      if (sessionId) addLogToSession(sessionId, `System: Started thinking (turn ${data.turn || 1})`, 'system');
    });

    eventSource.addEventListener('content', (e) => {
      const data = JSON.parse(e.data);
      const content = data.text || '';
      if (content) {
        // Accumulate raw content, then separate think from response
        const raw = streamingContentRef.current + content;
        streamingContentRef.current = raw;
        setStreamingContent(stripThink(raw));
        const th = extractThinkContent(raw);
        thinkingContentRef.current = th;
        setThinkingContent(th);
      }
    });

    eventSource.addEventListener('tool_start', (e) => {
      const data = JSON.parse(e.data);
      const toolName = data.tool || 'unknown';
      const toolCallId = data.tool_call_id || `tool-${Date.now()}`;
      const args = data.arguments || {};
      const argsPreview = typeof args === 'object' && args !== null
        ? (args.command || args.file_path || args.path || args.pattern || JSON.stringify(args).substring(0, 80))
        : '';
      setActiveTool({ name: toolName, args: argsPreview });
      // Auto-create background task so user sees activity in TaskCenter
      const { addBackgroundTask } = useTaskStore.getState();
      addBackgroundTask({
        id: toolCallId,
        name: toolName,
        description: argsPreview || undefined,
        status: 'running',
        progress: 0,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        startedAt: Date.now(),
      });
      if (sessionId) addLogToSession(sessionId, `[Tool] ${toolName}...`, 'log');
    });

    eventSource.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data);
      const toolName = data.tool || 'unknown';
      const toolCallId = data.tool_call_id || '';
      const success = data.success !== false;
      const result = data.result || '';
      const truncatedResult = typeof result === 'string' ? (result.length > 200 ? result.substring(0, 200) + '...' : result) : JSON.stringify(result).substring(0, 200);
      setActiveTool(null);
      // Update background task status
      if (toolCallId) {
        const { updateBackgroundTask } = useTaskStore.getState();
        updateBackgroundTask(toolCallId, {
          status: success ? 'completed' : 'failed',
          progress: 100,
          completedAt: Date.now(),
          updatedAt: Date.now(),
          result: truncatedResult,
          error: data.error || undefined,
        });
      }
      if (sessionId) addLogToSession(sessionId, `[Tool Result] ${toolName}: ${success ? 'OK' : 'FAILED'}\n${truncatedResult}`, 'log');
    });

    eventSource.addEventListener('thinking_complete', (e) => {
      const data = JSON.parse(e.data);
      const finalContent = streamingContentRef.current || 'Completed';
      const finalThinking = thinkingContentRef.current || '';
      const currentSessionId = sessionIdRef.current;
      if (currentSessionId) {
        addMessageToSession(currentSessionId, { sessionId: currentSessionId, agentRole: 'assistant', content: finalContent, isUser: false });
        if (finalThinking) {
          addLogToSession(currentSessionId, `[Thinking] ${finalThinking.substring(0, 200)}...`, 'system');
        }
        addLogToSession(currentSessionId, `[Complete] Turn ${data.turn || 'done'}`, 'system');
      }
      if (data.token_usage !== undefined) {
        const { updateTokenUsage } = useUIStore.getState();
        updateTokenUsage(data.token_usage, data.token_limit || 100000);
      }
      setStreamingContent('');
      setThinkingContent('');
      streamingContentRef.current = '';
      thinkingContentRef.current = '';
      setActiveTool(null);
      setIsProcessing(false);
      eventSource.close();
    });

    eventSource.addEventListener('keepalive', (e) => {
      // Heartbeat - no action needed
    });

    eventSource.addEventListener('error', (e: MessageEvent) => {
      // Only log error if we're still processing (unexpected close)
      if (isProcessing) {
        const currentSessionId = sessionIdRef.current;
        try {
          const data = JSON.parse(e.data);
          if (currentSessionId) addLogToSession(currentSessionId, `ERROR: ${data.error || 'Unknown error'}`, 'error');
        } catch {
          if (currentSessionId) addLogToSession(currentSessionId, `Connection closed`, 'error');
        }
        setIsProcessing(false);
        eventSource.close();
      }
    });

    eventSource.onerror = () => {
      // Only handle if still processing (normal close is ok)
      if (isProcessing) {
        const currentSessionId = sessionIdRef.current;
        if (currentSessionId) addLogToSession(currentSessionId, 'Connection error', 'error');
        setIsProcessing(false);
        eventSource.close();
      }
    };
  };

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing) return;
    const userMessage = input.trim();
    setInput('');
    setIsProcessing(true);
    setStreamingContent('');
    setThinkingContent('');
    streamingContentRef.current = '';
    thinkingContentRef.current = '';
    setSelectedAgentRole(null);
    setUserChoiceOptions(null);

    let sessionId = currentSessionId;
    if (!sessionId) {
      const newSession = addSession();
      setCurrentSession(newSession.id);
      sessionId = newSession.id;
    }

    addLogToSession(sessionId, `User: ${userMessage}`, 'user');
    addMessageToSession(sessionId, { sessionId, agentRole: 'user', content: userMessage, isUser: true });

    if (eventSourceRef.current) eventSourceRef.current.close();

    const encodedMessage = encodeURIComponent(userMessage);
    // History is loaded server-side via session_id — no need to pass it in URL
    const eventSource = new EventSource(`/api/stream?user_message=${encodedMessage}&workspace_id=${sessionId}&session_id=${sessionId}`);
    eventSourceRef.current = eventSource;

    setupEventListeners(eventSource, sessionId);
  };

  const handleStop = async () => {
    const sessionId = sessionIdRef.current || currentSessionId;
    if (!sessionId) return;
    try {
      await fetch(`/api/stream/cancel?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' });
    } catch {}
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsProcessing(false);
    setStreamingContent('');
    setThinkingContent('');
    setActiveTool(null);
    if (sessionId) addLogToSession(sessionId, 'User: Stopped', 'system');
  };

  const handleDeleteMessage = async (msgId: string) => {
    const sessionId = currentSessionId;
    if (!sessionId || !msgId) return;
    try {
      await fetch(`/api/sessions/${sessionId}/messages/${msgId}`, { method: 'DELETE' });
    } catch {}
    deleteMessageFromSession(sessionId, msgId);
  };

  const handleRollback = async (msgId: string) => {
    const sessionId = currentSessionId;
    if (!sessionId || !msgId) return;
    if (!confirm('Rollback to before this message? Messages from this point will be deleted.')) return;
    try {
      await fetch(`/api/sessions/${sessionId}/rollback?from_message_id=${msgId}`, { method: 'POST' });
    } catch {}
    // Reload page to refresh state
    window.location.reload();
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">WOLF AI</h1>
            <p className="text-xs text-vscode-text-dim">Describe what you need</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={currentSessionId || ''} onChange={(e) => setCurrentSession(e.target.value || null)} className="bg-vscode-bg border border-vscode-border rounded-sm px-2 py-1 text-xs">
              {sessions.map(session => (<option key={session.id} value={session.id}>{session.name}</option>))}
            </select>
            <button onClick={() => { const newSession = addSession(); setCurrentSession(newSession.id); }} className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm">+ New</button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-96 border-r border-vscode-border flex flex-col overflow-hidden">
          {/* Activity Log */}
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light flex items-center justify-between">
            <h2 className="text-xs font-medium text-vscode-text uppercase">Activity Log</h2>
            <button onClick={() => { if (currentSessionId) clearSessionLogs(currentSessionId); }} className="text-xs text-vscode-text-dim">Clear</button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 bg-vscode-bg">
            <div className="terminal-text text-xs space-y-1">
              {logs.map((log) => {
                const time = new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const colorClass = log.type === 'error' ? 'text-vscode-red' : log.type === 'user' ? 'text-vscode-blue' : log.type === 'system' ? 'text-vscode-yellow' : 'text-vscode-text-dim';
                return <div key={log.id} className={clsx('p-1 rounded', colorClass)}>{time} {log.message}</div>;
              })}
              <div ref={logsEndRef} />
            </div>
          </div>

          {/* Thinking Panel */}
          <div className="border-t border-vscode-border flex flex-col flex-1 overflow-hidden">
            <div className="p-2 border-b border-vscode-border bg-vscode-bg-light">
              <h2 className="text-xs font-medium text-vscode-text-dim uppercase">Thinking</h2>
            </div>
            <div className="flex-1 overflow-y-auto p-2 bg-vscode-bg">
              {displayThinking ? (
                <div className="text-xs text-vscode-text-dim whitespace-pre-wrap font-mono leading-relaxed">
                  {displayThinking}
                </div>
              ) : (
                <div className="text-xs text-vscode-text-dim italic">
                  {isProcessing ? 'Waiting for thinking...' : 'No thinking content yet'}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light flex items-center justify-between">
            <h2 className="text-xs font-medium text-vscode-text uppercase">Chat</h2>
            <button onClick={() => { if (currentSessionId) clearSessionMessages(currentSessionId); }} className="text-xs text-vscode-text-dim">Clear</button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 bg-vscode-bg">
            <div className="space-y-4">
              {messages.map((msg) => {
                const displayContent = msg.isUser ? msg.content : stripThink(msg.content);
                return (<div key={msg.id} className={clsx('group flex items-start gap-1', msg.isUser ? 'justify-end' : 'justify-start')}>
                  <div className={clsx('max-w-[80%] rounded-lg p-3 relative', msg.isUser ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-light border border-vscode-border')}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-vscode-text-dim capitalize">{msg.agentRole}</span>
                      <span className="hidden group-hover:flex items-center gap-1">
                        <button onClick={() => handleDeleteMessage(msg.id)} className="text-xs text-vscode-text-dim hover:text-vscode-red px-1" title="Delete message">✕</button>
                        {!msg.isUser && <button onClick={() => handleRollback(msg.id)} className="text-xs text-vscode-text-dim hover:text-vscode-yellow px-1" title="Rollback to here">↩</button>}
                      </span>
                    </div>
                    <ReactMarkdown className="text-sm whitespace-pre-wrap prose-sm max-w-none" components={{ code({ className, children }) { return <code className={className}>{children}</code>; }, pre({ children }) { return <pre className="mt-2 p-2 bg-vscode-bg rounded text-xs overflow-x-auto">{children}</pre>; } }}>{displayContent}</ReactMarkdown>
                  </div></div>);
              })}
              {streamingContent && (<div className="flex justify-start"><div className="max-w-[80%] rounded-lg p-3 bg-vscode-bg-light border border-vscode-border"><div className="text-xs text-vscode-text-dim mb-1">assistant</div><ReactMarkdown className="text-sm whitespace-pre-wrap prose-sm max-w-none">{streamingContent}</ReactMarkdown><div className="flex items-center gap-1 mt-2 text-vscode-yellow"><span className="animate-pulse">●</span><span className="text-xs">Thinking...</span></div></div></div>)}
              {isProcessing && !streamingContent && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] rounded-lg p-3 bg-vscode-bg-light border border-vscode-border">
                    <div className="flex items-center gap-2 text-gray-400">
                      <span className="animate-pulse">●</span>
                      <span className="text-sm">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>
          {userChoiceOptions && (<div className="p-4 bg-vscode-bg-light border-t border-vscode-border"><div className="text-sm mb-3">{userChoiceOptions.message}</div><div className="grid grid-cols-2 gap-2">{userChoiceOptions.options?.map((option: any) => (<button key={option.id} onClick={() => { setUserChoiceOptions(null); if (option.id === 'retry') handleSubmit(); }} className="p-3 text-left bg-vscode-bg border border-vscode-border rounded-sm hover:border-vscode-accent"><div className="text-sm font-medium">{option.label}</div><div className="text-xs text-vscode-text-dim">{option.description}</div></button>))}</div></div>)}
          <div className="p-4 bg-vscode-bg-light border-t border-vscode-border">
            <div className="flex gap-3">
              <div className="flex-1"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }} placeholder="Describe what you need..." className="w-full h-20 bg-vscode-bg border border-vscode-border rounded-sm p-3 text-sm resize-none focus:border-vscode-accent" disabled={isProcessing} /></div>
              {isProcessing ? (
                <button onClick={handleStop} className="px-6 rounded-sm text-sm font-medium self-end bg-vscode-red text-white hover:bg-red-700">⏹ Stop</button>
              ) : (
                <button onClick={handleSubmit} disabled={!input.trim()} className={clsx('px-6 rounded-sm text-sm font-medium self-end', input.trim() ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-hover text-vscode-text-dim')}>Send</button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}