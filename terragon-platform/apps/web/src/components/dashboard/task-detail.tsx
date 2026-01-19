'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  X,
  GitBranch,
  Clock,
  ExternalLink,
  RotateCcw,
  StopCircle,
  Terminal,
  FileCode,
  Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { Task, TaskLog } from '@terragon/shared';

interface TaskWithArtifacts extends Task {
  logs?: TaskLog[];
  artifacts?: Array<{
    id: string;
    type: string;
    name: string;
    path: string;
    size: number;
    metadata?: Record<string, unknown>;
  }>;
}

interface TaskDetailProps {
  taskId: string;
  onClose: () => void;
  onTaskUpdated?: () => void;
}

function getStatusColor(status: string) {
  switch (status) {
    case 'RUNNING':
      return 'text-blue-500';
    case 'QUEUED':
      return 'text-yellow-500';
    case 'COMPLETED':
      return 'text-green-500';
    case 'FAILED':
      return 'text-red-500';
    case 'CANCELLED':
      return 'text-gray-500';
    default:
      return 'text-muted-foreground';
  }
}

function formatDate(dateString: string | Date | null) {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
}

function formatTimestamp(date: Date | string): string {
  return new Date(date).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

function extractRepoName(repoUrl: string): string {
  return repoUrl.split('/').slice(-2).join('/');
}

export function TaskDetail({ taskId, onClose, onTaskUpdated }: TaskDetailProps) {
  const { data: session } = useSession();
  const [task, setTask] = useState<TaskWithArtifacts | null>(null);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'logs' | 'files'>('logs');
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const loadTask = useCallback(async () => {
    try {
      setError(null);
      const taskData = await api.getTask(taskId);
      setTask(taskData as TaskWithArtifacts);

      if (taskData.status === 'RUNNING' || taskData.status === 'COMPLETED' || taskData.status === 'FAILED') {
        const logsData = await api.getTaskLogs(taskId);
        setLogs(logsData.logs.map(log => ({
          ...log,
          taskId,
          timestamp: new Date(log.timestamp),
        })) as TaskLog[]);
      }
    } catch (err) {
      console.error('Failed to load task:', err);
      setError(err instanceof Error ? err.message : 'Failed to load task');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadTask();
    }
  }, [session, loadTask]);

  useEffect(() => {
    if (!session?.accessToken || !task) return;

    if (task.status === 'RUNNING' || task.status === 'QUEUED') {
      const interval = setInterval(async () => {
        try {
          const taskData = await api.getTask(taskId);
          setTask(taskData as TaskWithArtifacts);

          if (taskData.status === 'RUNNING') {
            const logsData = await api.getTaskLogs(taskId);
            setLogs(logsData.logs.map(log => ({
              ...log,
              taskId,
              timestamp: new Date(log.timestamp),
            })) as TaskLog[]);
          }
        } catch (err) {
          console.error('Failed to refresh task:', err);
        }
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [session, task?.status, taskId]);

  const handleCancel = async () => {
    if (!task) return;

    try {
      setCancelling(true);
      await api.cancelTask(task.id);
      await loadTask();
      onTaskUpdated?.();
    } catch (err) {
      console.error('Failed to cancel task:', err);
      setError(err instanceof Error ? err.message : 'Failed to cancel task');
    } finally {
      setCancelling(false);
    }
  };

  const handleRetry = async () => {
    if (!task) return;

    try {
      setRetrying(true);
      await api.retryTask(task.id);
      await loadTask();
      onTaskUpdated?.();
    } catch (err) {
      console.error('Failed to retry task:', err);
      setError(err instanceof Error ? err.message : 'Failed to retry task');
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      </div>
    );
  }

  if (error && !task) {
    return (
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Error</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 text-destructive text-sm">{error}</div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Not Found</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4 text-muted-foreground text-sm">Task not found</div>
      </div>
    );
  }

  const fileChanges = task.artifacts?.filter(a => a.type === 'file_change') || [];

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
            {task.status.toLowerCase()}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Repository</span>
          <span className="text-sm flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            {extractRepoName(task.repoUrl)}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Branch</span>
          <span className="text-sm font-mono">{task.repoBranch}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Agent</span>
          <span className="text-sm capitalize">{task.agentType.toLowerCase()}</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Created</span>
          <span className="text-sm flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(task.createdAt)}
          </span>
        </div>

        {task.creditsUsed > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Credits Used</span>
            <span className="text-sm font-medium">{task.creditsUsed}</span>
          </div>
        )}

        {task.pullRequestUrl && (
          <a
            href={task.pullRequestUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            View Pull Request
          </a>
        )}

        {task.status === 'FAILED' && task.errorMessage && (
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            {task.errorMessage}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-b">
        <div className="flex gap-2">
          {(task.status === 'RUNNING' || task.status === 'QUEUED') && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 border border-destructive/50 text-destructive rounded-lg text-sm hover:bg-destructive/10 transition-colors disabled:opacity-50"
            >
              {cancelling ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <StopCircle className="h-4 w-4" />
              )}
              Cancel
            </button>
          )}
          {task.status === 'FAILED' && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 border rounded-lg text-sm hover:bg-muted transition-colors disabled:opacity-50"
            >
              {retrying ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Retry
            </button>
          )}
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
          Files ({fileChanges.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4 max-h-64 overflow-y-auto">
        {activeTab === 'logs' && (
          <div className="space-y-2 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="text-muted-foreground text-center py-4">
                {task.status === 'QUEUED' || task.status === 'PENDING'
                  ? 'Waiting for task to start...'
                  : 'No logs available'}
              </div>
            ) : (
              logs.map((log, i) => (
                <div key={log.id || i} className="flex gap-3">
                  <span className="text-muted-foreground flex-shrink-0">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span className={
                    log.level === 'ERROR' ? 'text-red-500' :
                    log.level === 'WARN' ? 'text-yellow-500' :
                    ''
                  }>
                    {log.message}
                  </span>
                </div>
              ))
            )}
            {task.status === 'RUNNING' && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Processing...</span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'files' && (
          <div className="space-y-2">
            {fileChanges.length === 0 ? (
              <div className="text-muted-foreground text-center py-4 text-sm">
                {task.status === 'COMPLETED'
                  ? 'No file changes recorded'
                  : 'File changes will appear here after the task completes'}
              </div>
            ) : (
              fileChanges.map((file, i) => {
                const metadata = file.metadata as { status?: string } | undefined;
                const status = metadata?.status || 'modified';
                return (
                  <div key={file.id || i} className="flex items-center gap-3 text-sm">
                    <span
                      className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        status === 'added'
                          ? 'bg-green-500/10 text-green-500'
                          : status === 'deleted'
                          ? 'bg-red-500/10 text-red-500'
                          : 'bg-yellow-500/10 text-yellow-500'
                      }`}
                    >
                      {status === 'added' ? '+' : status === 'deleted' ? '-' : 'M'}
                    </span>
                    <span className="font-mono truncate">{file.path}</span>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
