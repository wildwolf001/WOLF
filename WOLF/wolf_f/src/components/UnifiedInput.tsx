import React from 'react';
import { useSessionStore } from '@/store';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';

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
  const logsEndRef = React.useRef<HTMLDivElement>(null);
  const chatEndRef = React.useRef<HTMLDivElement>(null);
  const eventSourceRef = React.useRef<EventSource | null>(null);

  const {
    sessions,
    currentSessionId,
    addSession,
    setCurrentSession,
    addMessageToSession,
    addLogToSession,
    clearSessionLogs,
    clearSessionMessages,
    getSession
  } = useSessionStore();

  const currentSession = currentSessionId ? getSession(currentSessionId) : null;
  const logs = currentSession?.logs || [];
  const messages = currentSession?.messages || [];

  React.useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamingContent, messages]);

  const handleSubmit = async () => {
    if (!input.trim() || isProcessing) return;
    const userMessage = input.trim();
    setInput('');
    setIsProcessing(true);
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
    const recentMessages = (currentSession?.messages || []).slice(-5);
    const historyParam = encodeURIComponent(JSON.stringify(recentMessages));
    const eventSource = new EventSource(`http://localhost:8000/api/stream/stream?user_message=${encodedMessage}&history=${historyParam}`);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('start', (e) => {
      const data = JSON.parse(e.data);
      if (sessionId) addLogToSession(sessionId, `System: ${data.message}`, 'system');
    });

    eventSource.addEventListener('agent_status', (e) => {
      const data: AgentStatusEvent = JSON.parse(e.data);
      if (sessionId) addLogToSession(sessionId, `${data.agent}: ${data.message}`, 'log');
    });

    eventSource.addEventListener('tool_start', (e) => {
      const data = JSON.parse(e.data);
      const toolName = data.tool || 'unknown';
      const argsStr = data.args ? JSON.stringify(data.args).substring(0, 100) : '';
      if (sessionId) addLogToSession(sessionId, `[Tool] ${toolName}(${argsStr})...`, 'log');
    });

    eventSource.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data);
      const toolName = data.tool || 'unknown';
      const result = data.result || '';
      const truncatedResult = result.length > 200 ? result.substring(0, 200) + '...' : result;
      if (sessionId) addLogToSession(sessionId, `[Tool Result] ${toolName}:\n${truncatedResult}`, 'log');
    });

    eventSource.addEventListener('content_delta', (e) => {
      const data = JSON.parse(e.data);
      const delta = data.delta || '';
      if (delta) setStreamingContent(prev => prev + delta);
    });

    eventSource.addEventListener('final_result', (e) => {
      const data = JSON.parse(e.data);
      if (sessionId) {
        setStreamingContent('');
        addMessageToSession(sessionId, { sessionId, agentRole: 'assistant', content: data.message || '', isUser: false });
      }
    });

    eventSource.addEventListener('error', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.type === 'user_choice') {
        setUserChoiceOptions(data);
        setIsProcessing(false);
        eventSource.close();
        return;
      }
      if (sessionId) addLogToSession(sessionId, `ERROR: ${data.message}`, 'error');
    });

    eventSource.addEventListener('done', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (sessionId) addLogToSession(sessionId, `[Complete] ${data.message}`, 'system');
      setStreamingContent('');
      eventSource.close();
      setIsProcessing(false);
    });

    eventSource.onerror = () => {
      if (sessionId) addLogToSession(sessionId, 'Connection error', 'error');
      eventSource.close();
      setIsProcessing(false);
    };
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
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="p-3 border-b border-vscode-border bg-vscode-bg-light flex items-center justify-between">
            <h2 className="text-xs font-medium text-vscode-text uppercase">Chat</h2>
            <button onClick={() => { if (currentSessionId) clearSessionMessages(currentSessionId); }} className="text-xs text-vscode-text-dim">Clear</button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 bg-vscode-bg">
            <div className="space-y-4">
              {messages.map((msg) => (<div key={msg.id} className={clsx('flex', msg.isUser ? 'justify-end' : 'justify-start')}><div className={clsx('max-w-[80%] rounded-lg p-3', msg.isUser ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-light border border-vscode-border')}><div className="text-xs text-vscode-text-dim mb-1 capitalize">{msg.agentRole}</div><ReactMarkdown className="text-sm whitespace-pre-wrap prose-sm max-w-none" components={{ code({ className, children }) { return <code className={className}>{children}</code>; }, pre({ children }) { return <pre className="mt-2 p-2 bg-vscode-bg rounded text-xs overflow-x-auto">{children}</pre>; } }}>{msg.content}</ReactMarkdown></div></div>))}
              {streamingContent && (<div className="flex justify-start"><div className="max-w-[80%] rounded-lg p-3 bg-vscode-bg-light border border-vscode-border"><div className="text-xs text-vscode-text-dim mb-1">assistant</div><ReactMarkdown className="text-sm whitespace-pre-wrap prose-sm max-w-none">{streamingContent}</ReactMarkdown><div className="flex items-center gap-1 mt-2 text-vscode-yellow"><span className="animate-pulse">●</span><span className="text-xs">Thinking...</span></div></div></div>)}
              {isProcessing && !streamingContent && (<div className="flex justify-start"><div className="max-w-[80%] rounded-lg p-3 bg-vscode-bg-light border border-vscode-border"><div className="flex items-center gap-2 text-vscode-yellow"><span className="animate-pulse">●</span><span>Processing...</span></div></div></div>)}
              <div ref={chatEndRef} />
            </div>
          </div>
          {userChoiceOptions && (<div className="p-4 bg-vscode-bg-light border-t border-vscode-border"><div className="text-sm mb-3">{userChoiceOptions.message}</div><div className="grid grid-cols-2 gap-2">{userChoiceOptions.options?.map((option: any) => (<button key={option.id} onClick={() => { setUserChoiceOptions(null); if (option.id === 'retry') handleSubmit(); }} className="p-3 text-left bg-vscode-bg border border-vscode-border rounded-sm hover:border-vscode-accent"><div className="text-sm font-medium">{option.label}</div><div className="text-xs text-vscode-text-dim">{option.description}</div></button>))}</div></div>)}
          <div className="p-4 bg-vscode-bg-light border-t border-vscode-border">
            <div className="flex gap-3">
              <div className="flex-1"><textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }} placeholder="Describe what you need..." className="w-full h-20 bg-vscode-bg border border-vscode-border rounded-sm p-3 text-sm resize-none focus:border-vscode-accent" disabled={isProcessing} /></div>
              <button onClick={handleSubmit} disabled={!input.trim() || isProcessing} className={clsx('px-6 rounded-sm text-sm font-medium self-end', input.trim() && !isProcessing ? 'bg-vscode-accent text-white' : 'bg-vscode-bg-hover text-vscode-text-dim')}>{isProcessing ? 'Processing...' : 'Send'}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}