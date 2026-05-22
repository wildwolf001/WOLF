import React, { useState, useEffect } from 'react';
import clsx from 'clsx';

interface FileItem {
  name: string;
  path: string;
  is_directory: boolean;
  size: number;
  size_formatted: string;
  extension: string;
  modified_time: number;
  modified_time_formatted: string;
}

interface TreeNode {
  name: string;
  path: string;
  is_directory: boolean;
  size: number;
  extension: string;
  children?: TreeNode[];
  truncated?: boolean;
  error?: string;
}

export function Files() {
  const [currentPath, setCurrentPath] = useState<string>('');
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<any>(null);
  const [filePreviewLoading, setFilePreviewLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const [uploadTargetDir, setUploadTargetDir] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ success: boolean; message: string } | null>(null);

  // Initialize and fetch work directory
  useEffect(() => {
    const init = async () => {
      try {
        // Try to fetch work directory from config
        const workDirResponse = await fetch('http://localhost:8000/api/config/work-directory');
        if (workDirResponse.ok) {
          const workDirData = await workDirResponse.json();
          if (workDirData.work_directory) {
            setCurrentPath(workDirData.work_directory);
            setUploadTargetDir(workDirData.work_directory);
            loadTree(workDirData.work_directory);
            setInitialized(true);
            return;
          }
        }
      } catch (err) {
        console.error('Failed to fetch work directory:', err);
      }
      // Fallback to a default path if not configured
      const defaultPath = 'C:/Users/24040/Desktop/graduation/article';
      setCurrentPath(defaultPath);
      setUploadTargetDir(defaultPath);
      loadTree(defaultPath);
      setInitialized(true);
    };
    init();
  }, []);

  // Load file tree
  const loadTree = async (path: string, depth: number = 2) => {
    if (!path) return; // Guard against empty path
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/files/tree?path=${encodeURIComponent(path)}&max_depth=${depth}`);
      const data = await response.json();
      if (data.success && data.children) {
        setTree(data);
        setCurrentPath(path);
      } else {
        setError(data.error || 'Failed to load directory');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadTree(currentPath);
  }, []);

  // Load file content
  const loadFileContent = async (path: string) => {
    setFilePreviewLoading(true);
    setSelectedFile(path);
    try {
      const response = await fetch(`http://localhost:8000/api/files/read?path=${encodeURIComponent(path)}&offset=0&limit=500`);
      const data = await response.json();
      setFileContent(data);
    } catch (err) {
      setFileContent({ success: false, error: 'Failed to load file' });
    } finally {
      setFilePreviewLoading(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadResult(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_dir', uploadTargetDir || currentPath);

        const response = await fetch('http://localhost:8000/api/files/upload', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();

        if (!result.success) {
          setUploadResult({ success: false, message: `Failed to upload ${file.name}: ${result.error}` });
          break;
        }
      }

      setUploadResult({ success: true, message: 'Files uploaded successfully' });
      // Refresh tree
      loadTree(currentPath);
    } catch (err) {
      setUploadResult({ success: false, message: 'Upload failed' });
    } finally {
      setUploading(false);
      event.target.value = ''; // Reset input
    }
  };

  // Handle directory creation
  const handleCreateDirectory = async () => {
    const dirName = prompt('Enter directory name:');
    if (!dirName) return;

    try {
      const newPath = currentPath.endsWith('/') || currentPath.endsWith('\\')
        ? currentPath + dirName
        : currentPath + '/' + dirName;

      const response = await fetch(`http://localhost:8000/api/files/mkdir?path=${encodeURIComponent(newPath)}`, {
        method: 'POST',
      });
      const result = await response.json();

      if (result.success) {
        loadTree(currentPath);
      } else {
        alert('Failed to create directory: ' + result.error);
      }
    } catch (err) {
      alert('Failed to create directory');
    }
  };

  // Render tree node
  const renderTreeNode = (node: TreeNode, depth: number = 0) => {
    const hasChildren = node.children && node.children.length > 0;

    return (
      <div key={node.path} style={{ marginLeft: depth * 16 }}>
        <div
          className={clsx(
            'flex items-center gap-2 py-1 px-2 cursor-pointer rounded hover:bg-vscode-bg-hover',
            selectedFile === node.path && 'bg-vscode-bg-light'
          )}
          onClick={() => {
            if (node.is_directory) {
              // Toggle expand - just reload tree for now
              loadTree(node.path, 2);
            } else {
              loadFileContent(node.path);
            }
          }}
        >
          <span className="text-vscode-text-dim text-xs">
            {node.is_directory ? (hasChildren ? '📂' : '📁') : getFileIcon(node.extension)}
          </span>
          <span className="text-sm text-vscode-text flex-1 truncate">{node.name}</span>
          {!node.is_directory && (
            <span className="text-xs text-vscode-text-dim">{formatSize(node.size)}</span>
          )}
          {node.truncated && (
            <span className="text-xs text-vscode-accent" title="Click to expand">+</span>
          )}
        </div>
        {node.error && (
          <div className="text-xs text-vscode-red ml-8">{node.error}</div>
        )}
        {hasChildren && node.children!.map(child => renderTreeNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left panel: File tree */}
      <div className="w-80 border-r border-vscode-border flex flex-col">
        {/* Header */}
        <div className="p-3 border-b border-vscode-border bg-vscode-bg-light">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-medium text-vscode-text uppercase tracking-wide">Project Files</h2>
            <button
              onClick={() => loadTree(currentPath)}
              className="text-xs text-vscode-accent hover:underline"
            >
              Refresh
            </button>
          </div>
          {/* Current path */}
          <div className="text-xs text-vscode-text-dim mb-2 truncate" title={currentPath}>
            {currentPath}
          </div>
          {/* Path navigation */}
          <div className="flex gap-1">
            <button
              onClick={() => loadTree(currentPath)}
              className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover"
            >
              ↻
            </button>
            <button
              onClick={() => {
                const parent = currentPath.replace(/[/\\][^/\\]+$/, '');
                if (parent) loadTree(parent);
              }}
              className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover"
            >
              ↑
            </button>
            <button
              onClick={handleCreateDirectory}
              className="px-2 py-1 text-xs bg-vscode-bg border border-vscode-border rounded-sm hover:bg-vscode-bg-hover"
            >
              + Dir
            </button>
          </div>
        </div>

        {/* File tree */}
        <div className="flex-1 overflow-y-auto p-2">
          {loading && (
            <div className="text-center text-xs text-vscode-text-dim py-4">Loading...</div>
          )}
          {error && (
            <div className="text-center text-xs text-vscode-red py-4">{error}</div>
          )}
          {tree && !loading && (
            <div>
              {renderTreeNode(tree)}
            </div>
          )}
        </div>

        {/* Upload section */}
        <div className="p-3 border-t border-vscode-border bg-vscode-bg-light">
          <div className="mb-2">
            <label className="block text-xs text-vscode-text-dim mb-1">Target Directory</label>
            <input
              type="text"
              value={uploadTargetDir}
              onChange={(e) => setUploadTargetDir(e.target.value)}
              placeholder={currentPath}
              className="w-full bg-vscode-bg border border-vscode-border rounded-sm px-2 py-1 text-xs text-vscode-text"
            />
          </div>
          <label className={clsx(
            'block text-center px-4 py-2 text-sm bg-vscode-bg border border-vscode-border rounded-sm cursor-pointer hover:bg-vscode-bg-hover',
            uploading && 'opacity-50 cursor-not-allowed'
          )}>
            {uploading ? 'Uploading...' : 'Upload Files'}
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
          {uploadResult && (
            <div className={clsx(
              'mt-2 text-xs p-2 rounded',
              uploadResult.success ? 'bg-vscode-green/20 text-vscode-green' : 'bg-vscode-red/20 text-vscode-red'
            )}>
              {uploadResult.message}
            </div>
          )}
        </div>
      </div>

      {/* Right panel: File preview */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedFile && (
          <div className="flex-1 flex items-center justify-center text-vscode-text-dim text-sm">
            Click on a file to preview its contents
          </div>
        )}

        {selectedFile && filePreviewLoading && (
          <div className="flex-1 flex items-center justify-center text-vscode-text-dim text-sm">
            Loading file...
          </div>
        )}

        {selectedFile && fileContent && !filePreviewLoading && (
          <>
            {/* File header */}
            <div className="p-3 border-b border-vscode-border bg-vscode-bg-light">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-vscode-text">{fileContent.name || selectedFile.split(/[/\\]/).pop()}</h3>
                  <div className="text-xs text-vscode-text-dim mt-1">
                    {fileContent.size !== undefined && `${formatSize(fileContent.size)}`}
                    {fileContent.total_lines !== undefined && ` • ${fileContent.total_lines} lines`}
                    {fileContent.encoding && ` • ${fileContent.encoding}`}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-xs text-vscode-text-dim hover:text-vscode-text"
                >
                  ✕ Close
                </button>
              </div>
            </div>

            {/* File content */}
            <div className="flex-1 overflow-auto p-4 bg-vscode-bg">
              {fileContent.success === false ? (
                <div className="text-vscode-red text-sm">{fileContent.error}</div>
              ) : fileContent.content !== undefined ? (
                <pre className="text-xs font-mono text-vscode-text whitespace-pre-wrap break-all">
                  {fileContent.content}
                </pre>
              ) : fileContent.content !== undefined && fileContent.encoding === 'base64' ? (
                <div className="text-sm text-vscode-text-dim">
                  Binary file ({fileContent.extension}) - cannot display as text.
                  <br />
                  Size: {formatSize(fileContent.size)}
                  <br />
                  <button
                    onClick={() => loadFileContent(selectedFile)}
                    className="text-vscode-accent hover:underline mt-2"
                  >
                    View as base64
                  </button>
                </div>
              ) : (
                <div className="text-sm text-vscode-text-dim">
                  Unable to preview this file type.
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Helper functions
function getFileIcon(extension: string): string {
  const iconMap: Record<string, string> = {
    '.py': '🐍',
    '.js': '📜',
    '.ts': '📜',
    '.jsx': '⚛️',
    '.tsx': '⚛️',
    '.json': '📋',
    '.md': '📝',
    '.txt': '📄',
    '.html': '🌐',
    '.css': '🎨',
    '.pdf': '📕',
    '.png': '🖼️',
    '.jpg': '🖼️',
    '.jpeg': '🖼️',
    '.gif': '🖼️',
    '.svg': '🖼️',
    '.gitignore': '📛',
    '.env': '🔐',
    '.yaml': '⚙️',
    '.yml': '⚙️',
    '.xml': '📰',
    '.sql': '🗃️',
    '.sh': '📟',
    '.bat': '📟',
    '.ipynb': '📓',
  };
  return iconMap[extension] || '📄';
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}