import axios from 'axios';
import type { ApiResponse, PaginatedResponse } from '@/types/api';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.message || error.message || 'An error occurred';
    return Promise.reject(new Error(message));
  }
);

// Agents API
export const agentsApi = {
  getAll: () => api.get('/agents').then((res: any) => res.data as ApiResponse<unknown[]>),
  getById: (id: string) => api.get(`/agents/${id}`).then((res: any) => res.data as ApiResponse<unknown>),
  getStatus: (id: string) => api.get(`/agents/${id}/status`).then((res: any) => res.data as ApiResponse<{ status: string }>),
  sendMessage: (id: string, content: string) =>
    api.post(`/agents/${id}/chat`, { content }).then((res: any) => res.data as ApiResponse<unknown>),
  getHistory: (id: string) => api.get(`/agents/${id}/history`).then((res: any) => res.data as ApiResponse<unknown[]>),
};

// Tasks API
export const tasksApi = {
  getAll: (params?: { status?: string; page?: number; pageSize?: number }) =>
    api.get<PaginatedResponse<unknown>>('/tasks', { params }),
  getById: (id: string) => api.get<ApiResponse<unknown>>(`/tasks/${id}`),
  create: (task: unknown) => api.post<ApiResponse<unknown>>('/tasks', task),
  update: (id: string, task: unknown) => api.put<ApiResponse<unknown>>(`/tasks/${id}`, task),
  delete: (id: string) => api.delete<ApiResponse<void>>(`/tasks/${id}`),
  assign: (id: string, assigneeId: string) =>
    api.post<ApiResponse<unknown>>(`/tasks/${id}/assign`, { assigneeId }),
};

// Sessions API
export const sessionsApi = {
  getAll: () => api.get<ApiResponse<unknown[]>>('/sessions'),
  create: (title: string) => api.post<ApiResponse<unknown>>('/sessions', { title }),
  getById: (id: string) => api.get<ApiResponse<unknown>>(`/sessions/${id}`),
  delete: (id: string) => api.delete<ApiResponse<void>>(`/sessions/${id}`),
};

// Documents API
export const documentsApi = {
  getAll: (params?: { type?: string; taskId?: string }) =>
    api.get<PaginatedResponse<unknown>>('/documents', { params }),
  getById: (id: string) => api.get<ApiResponse<unknown>>(`/documents/${id}`),
  create: (doc: unknown) => api.post<ApiResponse<unknown>>('/documents', doc),
  update: (id: string, doc: unknown) => api.put<ApiResponse<unknown>>(`/documents/${id}`, doc),
  getVersions: (id: string) => api.get<ApiResponse<unknown[]>>(`/documents/${id}/versions`),
};

// Knowledge API
export const knowledgeApi = {
  search: (query: string, filters?: Record<string, unknown>) =>
    api.post<ApiResponse<unknown[]>>('/knowledge/search', { query, filters }),
  add: (entry: unknown) => api.post<ApiResponse<unknown>>('/knowledge', entry),
  delete: (id: string) => api.delete<ApiResponse<void>>(`/knowledge/${id}`),
};

// Skills API
export const skillsApi = {
  getAll: async () => {
    const res = await api.get('/skills');
    return (res as any).data as ApiResponse<unknown[]>;
  },
  getById: async (id: string) => {
    const res = await api.get(`/skills/${id}`);
    return (res as any).data as ApiResponse<unknown>;
  },
  create: async (skill: unknown) => {
    const res = await api.post('/skills', skill);
    return (res as any).data as ApiResponse<unknown>;
  },
  update: async (id: string, skill: unknown) => {
    const res = await api.put(`/skills/${id}`, skill);
    return (res as any).data as ApiResponse<unknown>;
  },
  delete: async (id: string) => {
    const res = await api.delete(`/skills/${id}`);
    return (res as any).data as ApiResponse<void>;
  },
  toggle: async (id: string) => {
    const res = await api.post(`/skills/${id}/toggle`);
    return (res as any).data as ApiResponse<unknown>;
  },
  match: async (query: string) => {
    const res = await api.post('/skills/match', { query });
    return (res as any).data as ApiResponse<unknown>;
  },
};

// Memory API
export const memoryApi = {
  getAll: (sessionId: string) =>
    api.get<ApiResponse<unknown[]>>('/memory/all', { params: { session_id: sessionId } }),
  create: (sessionId: string, memory: unknown) =>
    api.post<ApiResponse<unknown>>('/memory/', memory, { params: { session_id: sessionId } }),
  update: (sessionId: string, memoryId: string, updates: unknown) =>
    api.put<ApiResponse<unknown>>(`/memory/${memoryId}`, updates, { params: { session_id: sessionId } }),
  delete: (sessionId: string, memoryId: string) =>
    api.delete<ApiResponse<void>>(`/memory/${memoryId}`, { params: { session_id: sessionId } }),
  use: (sessionId: string, memoryId: string) =>
    api.post<ApiResponse<unknown>>(`/memory/${memoryId}/use`, {}, { params: { session_id: sessionId } }),
  search: (sessionId: string, query: string) =>
    api.get<ApiResponse<unknown[]>>('/memory/search', { params: { session_id: sessionId, query } }),
};

export default api;
