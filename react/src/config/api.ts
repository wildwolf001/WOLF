/**
 * API Configuration
 * 统一管理后端API端点
 */

export const API_CONFIG = {
  // Base URL - 使用空字符串，通过代理转发
  BASE_URL: '',

  // API Endpoints
  endpoints: {
    // Stream / Query
    stream: '/api/stream',

    // Sessions
    sessions: '/api/sessions',

    // Files
    files: {
      read: '/api/files/read',
      write: '/api/files/write',
      edit: '/api/files/edit',
      glob: '/api/files/glob',
      grep: '/api/files/grep',
    },

    // Tools
    tools: {
      list: '/api/tools',
      execute: '/api/tools/execute',
    },

    // Memory
    memory: '/api/memory',
    memoryAll: '/api/memory/all',
    memoryStats: '/api/memory/stats',
    memorySync: '/api/memory/sync',

    // Config
    config: '/api/config',
    configAll: '/api/config/all',
    configQueryEngine: '/api/config/query-engine',
    configTools: '/api/config/tools',
    configMcpServers: '/api/config/mcp-servers',
    configEnv: '/api/config/env',
    configEnvRaw: '/api/config/env/raw',
    configEnvOpen: '/api/config/env/open',
    configEnvSwitchProvider: '/api/config/env/switch-provider',

    // Logs
    logs: '/api/logs/file',
    logsStream: '/api/logs/stream',
    logsStats: '/api/logs/stats',

    // System & Observability
    systemStatus: '/api/system/status',
    systemObservability: '/api/system/observability',
    systemMemoryCognitive: '/api/system/memory-cognitive',
    systemEvolution: '/api/system/evolution',
  },

  // WebSocket
  websocket: '/ws',
};

// Helper function to build full URL
export function getApiUrl(endpoint: string): string {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}

// SSE URL builder
export function getSSEUrl(userMessage: string): string {
  const encoded = encodeURIComponent(userMessage);
  return `${API_CONFIG.BASE_URL}${API_CONFIG.endpoints.stream}?user_message=${encoded}`;
}