/**
 * Config Service
 * Provides backend configuration access via API
 */

import { API_CONFIG, getApiUrl } from '@/config/api';

export interface QueryEngineConfig {
  max_turns: number;
  max_tokens: number;
  temperature: number;
  timeout: number;
  stream: boolean;
  max_parallel_tools: number;
  max_context_tokens: number;
  context_overflow_threshold: number;
}

export interface ToolConfig {
  max_concurrent_reads: number;
  bash_enabled: boolean;
  edit_enabled: boolean;
  write_enabled: boolean;
  glob_enabled: boolean;
  grep_enabled: boolean;
  agent_enabled: boolean;
}

export interface MCPServer {
  name: string;
  type: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
}

export interface AllConfig {
  config: Record<string, any>;
  query_engine: QueryEngineConfig;
  tools: ToolConfig;
  providers: Record<string, any>;
  current_provider: string;
  storage_paths: Record<string, string>;
  mcp_servers: MCPServer[];
}

class ConfigService {
  /**
   * Get all configuration in one call
   */
  async getAllConfig(): Promise<AllConfig> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configAll));

    if (!response.ok) {
      throw new Error(`Failed to fetch config: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get Query Engine configuration
   */
  async getQueryEngineConfig(): Promise<QueryEngineConfig> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configQueryEngine));

    if (!response.ok) {
      throw new Error(`Failed to fetch Query Engine config: ${response.statusText}`);
    }

    const data = await response.json();
    return data.config;
  }

  /**
   * Update Query Engine configuration
   */
  async updateQueryEngineConfig(config: Partial<QueryEngineConfig>): Promise<QueryEngineConfig> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configQueryEngine), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to update Query Engine config: ${response.statusText}`);
    }

    const data = await response.json();
    return data.config;
  }

  /**
   * Get Tool configuration
   */
  async getToolConfig(): Promise<ToolConfig> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configTools));

    if (!response.ok) {
      throw new Error(`Failed to fetch Tool config: ${response.statusText}`);
    }

    const data = await response.json();
    return data.config;
  }

  /**
   * Update Tool configuration
   */
  async updateToolConfig(config: Partial<ToolConfig>): Promise<ToolConfig> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configTools), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to update Tool config: ${response.statusText}`);
    }

    const data = await response.json();
    return data.config;
  }

  /**
   * Get MCP Servers configuration
   */
  async getMCPServers(): Promise<MCPServer[]> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configMcpServers));

    if (!response.ok) {
      throw new Error(`Failed to fetch MCP servers: ${response.statusText}`);
    }

    const data = await response.json();
    return data.servers || [];
  }

  /**
   * Update MCP Servers configuration
   */
  async updateMCPServers(
    action: 'add' | 'remove' | 'set',
    server?: MCPServer
  ): Promise<MCPServer[]> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.configMcpServers), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, server }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update MCP servers: ${response.statusText}`);
    }

    const data = await response.json();
    return data.servers || [];
  }
}

// Export singleton instance
export const configService = new ConfigService();
