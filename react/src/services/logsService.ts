/**
 * Logs Service
 * Provides backend log access via file-based API
 */

import { API_CONFIG, getApiUrl } from '@/config/api';

export interface BackendLog {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: 'backend' | 'agent' | 'workflow' | 'tool' | 'mcp' | 'query' | 'tasks';
  location: string;
  message: string;
}

export interface LogFilters {
  level?: string;
  source?: string;
}

export interface LogStats {
  exists: boolean;
  size: number;
  lines: number;
  path: string;
  modified?: string;
}

interface LogsResponse {
  logs: BackendLog[];
  count: number;
  position: number;
  has_more: boolean;
}

class LogsService {
  private lastPosition = 0;

  /**
   * Get backend logs with optional filtering
   * Uses file-based polling with position tracking
   */
  async getLogs(filters: LogFilters = {}, limit: number = 500): Promise<{ logs: BackendLog[], position: number }> {
    const params = new URLSearchParams();
    params.append('last_position', this.lastPosition.toString());
    params.append('max_lines', limit.toString());

    const url = `${getApiUrl(API_CONFIG.endpoints.logs)}?${params}`;
    const response = await fetch(url);

    // Check content type before parsing
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text();
      throw new Error(`Invalid response: expected JSON, got ${contentType}. Status: ${response.status}. Body: ${text.substring(0, 200)}`);
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch logs: ${response.statusText}`);
    }

    const text = await response.text();

    let data: LogsResponse;
    try {
      data = JSON.parse(text);
    } catch (e) {
      throw new Error(`Invalid JSON response: ${text.substring(0, 200)}`);
    }

    // Always update position so we don't re-read same content
    this.lastPosition = data.position;

    // Filter logs in memory
    let logs = data.logs || [];
    if (filters.level) {
      logs = logs.filter(log => log.level === filters.level);
    }
    if (filters.source) {
      logs = logs.filter(log => log.source === filters.source);
    }

    return { logs, position: data.position };
  }

  /**
   * Reset position to read from beginning
   */
  resetPosition(): void {
    this.lastPosition = 0;
  }

  /**
   * Clear backend logs
   */
  async clearLogs(): Promise<void> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.logs), { method: 'DELETE' });

    if (!response.ok) {
      throw new Error(`Failed to clear logs: ${response.statusText}`);
    }
    this.lastPosition = 0;
  }

  /**
   * Get log statistics
   */
  async getStats(): Promise<LogStats> {
    const response = await fetch(getApiUrl(API_CONFIG.endpoints.logsStats));

    if (!response.ok) {
      throw new Error(`Failed to fetch log stats: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const logsService = new LogsService();
