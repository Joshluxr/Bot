'use client';

import { useState } from 'react';
import {
  X,
  GitBranch,
  Clock,
  ExternalLink,
  Play,
  Pause,
  RotateCcw,
  Trash2,
  Terminal,
  FileCode,
} from 'lucide-react';

interface Task {
  id: string;
  title: string;
  status: 'running' | 'queued' | 'completed' | 'failed';
  progress?: number;
  repository: { fullName: string };
  branch: string;
  agent: string;
  prUrl?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

interface TaskDetailProps {
  task: Task;
  onClose: () => void;
}

// Mock logs for demonstration
const mockLogs = [
  { time: '10:32:15', message: 'Starting sandbox environment...' },
  { time: '10:32:18', message: 'Cloning repository...' },
  { time: '10:32:25', message: 'Installing dependencies...' },
  { time: '10:33:01', message: 'Analyzing codebase structure...' },
  { time: '10:33:45', message: 'Planning implementation approach...' },
  { time: '10:34:12', message: 'Creating new branch: feat/auth-flow' },
  { time: '10:34:15', message: 'Implementing authentication service...' },
  { time: '10:35:30', message: 'Adding login component...' },
  { time: '10:36:45', message: 'Writing tests...' },
];

// Mock files for demonstration
const mockFiles = [
  { path: 'src/services/auth.ts', status: 'added' as const },
  { path: 'src/components/Login.tsx', status: 'added' as const },
  { path: 'src/hooks/useAuth.ts', status: 'added' as const },
  { path: 'src/App.tsx', status: 'modified' as const },
  { path: 'package.json', status: 'modified' as const },
];

function getStatusColor(status: Task['status']) {
  switch (status) {
    case 'running':
      return 'text-yellow-500';
    case 'queued':
      return 'text-blue-500';
    case 'completed':
      return 'text-green-500';
    case 'failed':
      return 'text-red-500';
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString();
}

export function TaskDetail({ task, onClose }: TaskDetailProps) {
  const [activeTab, setActiveTab] = useState<'logs' | 'files'>('logs');

  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-semibold truncate">{task.title}</h2>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-muted"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Status & Info */}
      <div className="p-4 border-b space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Status</span>
          <span className={`text-sm font-medium capitalize ${getStatusColor(task.status)}`}>
            {task.status}
          </span>
        </div>

        {task.progress !== undefined && task.status === 'running' && (
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-muted-foreground">Progress</span>
              <span>{task.progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Repository</span>
          <span className="text-sm flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            {task.repository.fullName}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Branch</span>
          <span className="text-sm font-mono">{task.branch}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Agent</span>
          <span className="text-sm capitalize">{task.agent}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Created</span>
          <span className="text-sm flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(task.createdAt)}
          </span>
        </div>

        {task.prUrl && (
          <a
            href={task.prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            View Pull Request
          </a>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-b">
        <div className="flex gap-2">
          {task.status === 'running' && (
            <button className="flex-1 flex items-center justify-center gap-2 py-2 px-4 border rounded-lg text-sm hover:bg-muted transition-colors">
              <Pause className="h-4 w-4" />
              Pause
            </button>
          )}
          {task.status === 'queued' && (
            <button className="flex-1 flex items-center justify-center gap-2 py-2 px-4 border rounded-lg text-sm hover:bg-muted transition-colors">
              <Play className="h-4 w-4" />
              Start Now
            </button>
          )}
          {(task.status === 'failed' || task.status === 'completed') && (
            <button className="flex-1 flex items-center justify-center gap-2 py-2 px-4 border rounded-lg text-sm hover:bg-muted transition-colors">
              <RotateCcw className="h-4 w-4" />
              Retry
            </button>
          )}
          <button className="flex items-center justify-center gap-2 py-2 px-4 border border-red-500/30 text-red-500 rounded-lg text-sm hover:bg-red-500/10 transition-colors">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('logs')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
            activeTab === 'logs'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <Terminal className="h-4 w-4" />
          Logs
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
            activeTab === 'files'
              ? 'text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileCode className="h-4 w-4" />
          Files
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4 max-h-64 overflow-y-auto">
        {activeTab === 'logs' && (
          <div className="space-y-2 font-mono text-xs">
            {mockLogs.map((log, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-muted-foreground flex-shrink-0">{log.time}</span>
                <span>{log.message}</span>
              </div>
            ))}
            {task.status === 'running' && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <span className="animate-pulse">...</span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'files' && (
          <div className="space-y-2">
            {mockFiles.map((file, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span
                  className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    file.status === 'added'
                      ? 'bg-green-500/10 text-green-500'
                      : 'bg-yellow-500/10 text-yellow-500'
                  }`}
                >
                  {file.status === 'added' ? '+' : 'M'}
                </span>
                <span className="font-mono truncate">{file.path}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
