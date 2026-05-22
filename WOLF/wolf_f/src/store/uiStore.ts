import { create } from 'zustand';

type ViewMode = 'dashboard' | 'tasks' | 'results' | 'documents' | 'knowledge' | 'settings' | 'files' | 'memory' | 'projects' | 'channels' | 'skills';

interface Project {
  id: string;
  name: string;
  path: string;
  isActive: boolean;
  projectModeEnabled: boolean;
}

interface UIStore {
  currentView: ViewMode;
  sidebarCollapsed: boolean;
  notifications: Notification[];
  currentProject: Project | null;
  projects: Project[];
  setCurrentView: (view: ViewMode) => void;
  toggleSidebar: () => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  setCurrentProject: (project: Project | null) => void;
  addProject: (project: Project) => void;
  removeProject: (id: string) => void;
  toggleProjectMode: (projectId: string) => void;
  setProjectMode: (projectId: string, enabled: boolean) => void;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: number;
}

export const useUIStore = create<UIStore>((set) => ({
  currentView: 'dashboard',
  sidebarCollapsed: false,
  notifications: [],
  currentProject: null,
  projects: [],

  setCurrentView: (view) => set({ currentView: view }),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...notification, id: `notif-${Date.now()}`, timestamp: Date.now() },
      ],
    })),

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  setCurrentProject: (project) =>
    set((state) => ({
      currentProject: project,
      projects: state.projects.map(p => ({
        ...p,
        isActive: p.id === project?.id
      }))
    })),

  addProject: (project) =>
    set((state) => ({
      projects: [...state.projects, project]
    })),

  removeProject: (id) =>
    set((state) => ({
      projects: state.projects.filter(p => p.id !== id),
      currentProject: state.currentProject?.id === id ? null : state.currentProject
    })),

  toggleProjectMode: (projectId) =>
    set((state) => ({
      projects: state.projects.map(p =>
        p.id === projectId ? { ...p, projectModeEnabled: !p.projectModeEnabled } : p
      ),
      currentProject: state.currentProject?.id === projectId
        ? { ...state.currentProject, projectModeEnabled: !state.currentProject.projectModeEnabled }
        : state.currentProject
    })),

  setProjectMode: (projectId, enabled) =>
    set((state) => ({
      projects: state.projects.map(p =>
        p.id === projectId ? { ...p, projectModeEnabled: enabled } : p
      ),
      currentProject: state.currentProject?.id === projectId
        ? { ...state.currentProject, projectModeEnabled: enabled }
        : state.currentProject
    })),
}));
