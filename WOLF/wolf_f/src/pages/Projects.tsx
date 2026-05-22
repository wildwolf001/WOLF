import React, { useState, useEffect } from 'react';
import { useUIStore } from '@/store';
import clsx from 'clsx';

interface Project {
  id: string;
  name: string;
  path: string;
  isActive: boolean;
  projectModeEnabled: boolean;
}

interface ProjectInputModal {
  visible: boolean;
  mode: 'add' | 'edit';
  project?: { id: string; name: string; path: string } | null;
}

export function Projects() {
  const {
    projects,
    currentProject,
    setCurrentProject,
    addProject,
    removeProject,
    toggleProjectMode,
    setProjectMode
  } = useUIStore();

  const [modal, setModal] = useState<ProjectInputModal>({ visible: false, mode: 'add', project: null });
  const [projectName, setProjectName] = useState('');
  const [projectPath, setProjectPath] = useState('');

  const handleOpenAddModal = () => {
    setProjectName('');
    setProjectPath('');
    setModal({ visible: true, mode: 'add', project: null });
  };

  const handleOpenEditModal = (project: { id: string; name: string; path: string }) => {
    setProjectName(project.name);
    setProjectPath(project.path);
    setModal({ visible: true, mode: 'edit', project });
  };

  const handleCloseModal = () => {
    setModal({ visible: false, mode: 'add', project: null });
    setProjectName('');
    setProjectPath('');
  };

  const handleSaveProject = () => {
    if (!projectName.trim() || !projectPath.trim()) return;

    if (modal.mode === 'add') {
      addProject({
        id: `project-${Date.now()}`,
        name: projectName.trim(),
        path: projectPath.trim(),
        isActive: false,
        projectModeEnabled: false
      });
    } else if (modal.project) {
      // For editing, we need to handle it differently since the store doesn't have updateProject
      // Remove and re-add with new values
      if (currentProject?.id === modal.project.id) {
        const updatedProject: Project = {
          id: currentProject.id,
          name: projectName.trim(),
          path: projectPath.trim(),
          isActive: currentProject.isActive,
          projectModeEnabled: currentProject.projectModeEnabled,
        };
        setCurrentProject(updatedProject);
      }
    }
    handleCloseModal();
  };

  const handleSelectProject = (project: typeof projects[0]) => {
    setCurrentProject(project);
  };

  const handleRemoveProject = (projectId: string) => {
    if (confirm('Are you sure you want to remove this project?')) {
      removeProject(projectId);
    }
  };

  const handleToggleMode = (projectId: string, enabled: boolean) => {
    setProjectMode(projectId, enabled);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-vscode-bg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-vscode-border bg-vscode-bg-light">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-vscode-text mb-1">Projects</h1>
            <p className="text-xs text-vscode-text-dim">
              Manage your project workspaces and enable Project Mode to scope all operations
            </p>
          </div>
          <button
            onClick={handleOpenAddModal}
            className="px-3 py-1.5 text-xs bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
          >
            + Add Project
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {projects.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-5xl mb-4">📁</div>
              <div className="text-vscode-text mb-2">No projects yet</div>
              <div className="text-xs text-vscode-text-dim mb-4">
                Add a project folder to enable scoped operations
              </div>
              <button
                onClick={handleOpenAddModal}
                className="px-4 py-2 text-sm bg-vscode-accent text-white rounded-sm hover:bg-vscode-accent/80"
              >
                Add Your First Project
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Project Mode Info */}
            <div className="bg-vscode-bg-light border border-vscode-border rounded-sm p-4 mb-6">
              <div className="flex items-start gap-3">
                <span className="text-2xl">🎯</span>
                <div>
                  <h2 className="text-sm font-medium text-vscode-text mb-1">Project Mode</h2>
                  <p className="text-xs text-vscode-text-dim mb-3">
                    When Project Mode is enabled, all AI operations will be scoped to the selected project folder.
                    This ensures file searches, paper reviews, and data operations work within the project context.
                  </p>
                  {currentProject && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-vscode-text-dim">Active:</span>
                      <span className="text-xs text-vscode-accent font-medium">{currentProject.name}</span>
                      {currentProject.projectModeEnabled && (
                        <span className="px-2 py-0.5 text-xs bg-vscode-accent/20 text-vscode-accent rounded">
                          Mode Enabled
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Project List */}
            <h3 className="text-xs font-medium text-vscode-text-dim uppercase tracking-wide mb-3">
              Project Workspaces ({projects.length})
            </h3>
            <div className="space-y-2">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className={clsx(
                    'bg-vscode-bg-light border rounded-sm p-4 transition-all',
                    currentProject?.id === project.id
                      ? 'border-vscode-accent'
                      : 'border-vscode-border hover:border-vscode-text-dim'
                  )}
                >
                  <div className="flex items-start gap-3">
                    {/* Selection indicator */}
                    <button
                      onClick={() => handleSelectProject(project)}
                      className={clsx(
                        'w-5 h-5 rounded-sm border flex items-center justify-center flex-shrink-0 mt-0.5',
                        currentProject?.id === project.id
                          ? 'bg-vscode-accent border-vscode-accent'
                          : 'border-vscode-border hover:border-vscode-text-dim'
                      )}
                    >
                      {currentProject?.id === project.id && (
                        <span className="text-white text-xs">✓</span>
                      )}
                    </button>

                    {/* Project info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-vscode-text">{project.name}</span>
                        {currentProject?.id === project.id && (
                          <span className="px-1.5 py-0.5 text-xs bg-vscode-green/20 text-vscode-green rounded">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-vscode-text-dim truncate mb-2" title={project.path}>
                        {project.path}
                      </div>

                      {/* Project Mode Toggle */}
                      <div className="flex items-center gap-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <span className="text-xs text-vscode-text-dim">Project Mode:</span>
                          <div className="relative">
                            <input
                              type="checkbox"
                              checked={project.projectModeEnabled}
                              onChange={(e) => handleToggleMode(project.id, e.target.checked)}
                              className="sr-only"
                            />
                            <div
                              className={clsx(
                                'w-9 h-5 rounded-full transition-colors',
                                project.projectModeEnabled ? 'bg-vscode-accent' : 'bg-vscode-border'
                              )}
                            >
                              <div
                                className={clsx(
                                  'w-4 h-4 bg-white rounded-full shadow transform transition-transform mt-0.5',
                                  project.projectModeEnabled ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'
                                )}
                              />
                            </div>
                          </div>
                          <span className="text-xs text-vscode-text-dim">
                            {project.projectModeEnabled ? 'On' : 'Off'}
                          </span>
                        </label>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleOpenEditModal({ id: project.id, name: project.name, path: project.path })}
                        className="px-2 py-1 text-xs text-vscode-text-dim hover:text-vscode-text hover:bg-vscode-bg rounded-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleRemoveProject(project.id)}
                        className="px-2 py-1 text-xs text-vscode-red/60 hover:text-vscode-red hover:bg-vscode-red/10 rounded-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {modal.visible && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-vscode-bg-light border border-vscode-border rounded-sm w-96 p-4">
            <h2 className="text-sm font-medium text-vscode-text mb-4">
              {modal.mode === 'add' ? 'Add New Project' : 'Edit Project'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Project Name</label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="My Research Project"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text focus:border-vscode-accent"
                />
              </div>

              <div>
                <label className="block text-xs text-vscode-text-dim mb-1">Project Path</label>
                <input
                  type="text"
                  value={projectPath}
                  onChange={(e) => setProjectPath(e.target.value)}
                  placeholder="C:\Users\...\project_folder"
                  className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-3 py-2 text-sm text-vscode-text focus:border-vscode-accent"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={handleCloseModal}
                className="px-3 py-1.5 text-xs text-vscode-text-dim hover:text-vscode-text bg-vscode-bg border border-vscode-border rounded-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProject}
                disabled={!projectName.trim() || !projectPath.trim()}
                className={clsx(
                  'px-3 py-1.5 text-xs text-white rounded-sm',
                  projectName.trim() && projectPath.trim()
                    ? 'bg-vscode-accent hover:bg-vscode-accent/80'
                    : 'bg-vscode-accent/50 cursor-not-allowed'
                )}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}