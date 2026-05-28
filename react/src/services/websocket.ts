import type { WSClientEvents, WSServerEvents } from '@/types/api';

type EventHandler<T> = (data: T) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Map<keyof WSServerEvents, Set<EventHandler<unknown>>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private sessionId = 'default';
  private conversationHistory: Array<{ role: string; content: string }> = [];

  connect(url?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = url || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        // Join session with our session_id
        this.emit('join-session', { sessionId: this.sessionId });
      };

      this.ws.onclose = (reason) => {
        console.log('WebSocket disconnected:', reason);
        this.ws = null;
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, ...data } = message;

          // Dispatch to handlers
          const eventHandlers = this.handlers.get(type as keyof WSServerEvents);
          eventHandlers?.forEach((handler) => handler(data));
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  emit<K extends keyof WSClientEvents>(event: K, data: WSClientEvents[K]) {
    this.send({ type: event, ...data });
  }

  on<K extends keyof WSServerEvents>(event: K, handler: EventHandler<WSServerEvents[K]>) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)?.add(handler as EventHandler<unknown>);
  }

  off<K extends keyof WSServerEvents>(event: K, handler: EventHandler<WSServerEvents[K]>) {
    this.handlers.get(event)?.delete(handler as EventHandler<unknown>);
  }

  // Subscribe to an event and return unsubscribe function
  subscribe<K extends keyof WSServerEvents>(event: K, handler: EventHandler<WSServerEvents[K]>): () => void {
    this.on(event, handler);
    return () => this.off(event, handler);
  }

  joinSession(sessionId: string) {
    this.sessionId = sessionId;
    this.conversationHistory = []; // Clear history when joining new session
    this.emit('join-session', { sessionId });
  }

  leaveSession(sessionId: string) {
    this.emit('leave-session', { sessionId });
  }

  sendToAgent(agentId: string, content: string, history?: Array<{ role: string; content: string }>) {
    // Pass history with the message
    const payload = {
      agentId,
      content,
      sessionId: this.sessionId,
      history: history || this.conversationHistory
    };
    console.log('[WS] sendToAgent payload:', JSON.stringify(payload, null, 2));
    this.emit('send-to-agent', payload);
  }

  processRequest(message: string, history?: Array<{ role: string; content: string }>) {
    // Pass history with the message
    this.emit('process-request', {
      message,
      sessionId: this.sessionId,
      history: history || this.conversationHistory
    });
  }

  // Add message to local conversation history
  addToHistory(role: 'user' | 'assistant', content: string) {
    this.conversationHistory.push({ role, content });
  }

  // Get conversation history
  getHistory() {
    return [...this.conversationHistory];
  }

  // Clear conversation history
  clearHistory() {
    this.conversationHistory = [];
  }

  createTask(task: unknown) {
    this.emit('create-task', { task });
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();