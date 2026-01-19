'use client';

import { GitBranch, Clock, ExternalLink } from 'lucide-react';

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

interface TaskListProps {
  tasks: Task[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function getStatusColor(status: Task['status']) {
  switch (status) {
    case 'running':
      return 'bg-yellow-500';
    case 'queued':
      return 'bg-blue-500';
    case 'completed':
      return 'bg-green-500';
    case 'failed':
      return 'bg-red-500';
  }
}

function formatTime(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export function TaskList({ tasks, selectedId, onSelect }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-8 text-center">
        <p className="text-muted-foreground">No tasks found</p>
        <p className="text-sm text-muted-foreground mt-1">
          Create a new task to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <button
          key={task.id}
          onClick={() => onSelect(task.id)}
          className={`w-full text-left rounded-xl border bg-card p-4 transition-all hover:shadow-md ${
            selectedId === task.id ? 'ring-2 ring-primary' : ''
          }`}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-3">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">{task.title}</h3>
              <div className="flex items-center gap-2 mt-1">
                <GitBranch className="h-3 w-3 text-muted-foreground" />
                <span className="text-xs text-muted-foreground truncate">
                  {task.repository.fullName}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span
                className={`h-2 w-2 rounded-full ${getStatusColor(task.status)} ${
                  task.status === 'running' ? 'animate-pulse' : ''
                }`}
              />
              <span className="text-xs text-muted-foreground capitalize">
                {task.status}
              </span>
            </div>
          </div>

          {/* Progress bar for running tasks */}
          {task.status === 'running' && task.progress !== undefined && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Progress</span>
                <span>{task.progress}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${task.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* PR Link for completed tasks */}
          {task.status === 'completed' && task.prUrl && (
            <div className="mb-3">
              <a
                href={task.prUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                View Pull Request
              </a>
            </div>
          )}

          {/* Error for failed tasks */}
          {task.status === 'failed' && task.error && (
            <div className="mb-3 p-2 rounded bg-red-500/10 text-red-500 text-xs">
              {task.error}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatTime(task.updatedAt)}
            </span>
            <span className="px-2 py-0.5 rounded bg-muted text-xs">
              {task.agent}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
