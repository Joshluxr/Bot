'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  ScrollArea,
  Skeleton,
} from '@terragon/ui';
import {
  ArrowLeft,
  ExternalLink,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  GitBranch,
  GitPullRequest,
  Terminal,
  FileCode,
  RefreshCw,
  StopCircle,
  AlertCircle,
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

function getStatusIcon(status: string) {
  switch (status) {
    case 'RUNNING':
      return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
    case 'QUEUED':
      return <Clock className="h-5 w-5 text-yellow-500" />;
    case 'COMPLETED':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'FAILED':
      return <XCircle className="h-5 w-5 text-red-500" />;
    case 'CANCELLED':
      return <AlertCircle className="h-5 w-5 text-gray-500" />;
    default:
      return <Clock className="h-5 w-5 text-gray-500" />;
  }
}

function getStatusBadge(status: string) {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
    RUNNING: 'default',
    QUEUED: 'warning',
    COMPLETED: 'success',
    FAILED: 'destructive',
    PENDING: 'secondary',
    CANCELLED: 'outline',
  };
  return (
    <Badge variant={variants[status] || 'secondary'} className="text-sm">
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </Badge>
  );
}

function formatDate(date: Date | string | null): string {
  if (!date) return 'N/A';
  return new Date(date).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatTimestamp(date: Date | string): string {
  return new Date(date).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

function getLogLevelClass(level: string) {
  switch (level) {
    case 'ERROR':
      return 'text-red-500';
    case 'WARN':
      return 'text-yellow-500';
    case 'INFO':
      return 'text-muted-foreground';
    case 'DEBUG':
      return 'text-blue-400';
    default:
      return 'text-muted-foreground';
  }
}

function extractRepoName(repoUrl: string): string {
  return repoUrl.split('/').slice(-2).join('/');
}

function TaskDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="flex-1">
          <Skeleton className="h-8 w-96 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="h-4 w-20 mb-2" />
              <Skeleton className="h-6 w-24" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardContent className="p-4">
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const { data: session } = useSession();
  const router = useRouter();
  const [task, setTask] = useState<TaskWithArtifacts | null>(null);
  const [logs, setLogs] = useState<TaskLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const loadTask = useCallback(async () => {
    try {
      setError(null);
      const taskData = await api.getTask(params.id);
      setTask(taskData as TaskWithArtifacts);

      if (taskData.status === 'RUNNING' || taskData.status === 'COMPLETED' || taskData.status === 'FAILED') {
        const logsData = await api.getTaskLogs(params.id);
        setLogs(logsData.logs.map(log => ({
          ...log,
          taskId: params.id,
          timestamp: new Date(log.timestamp),
        })) as TaskLog[]);
      }
    } catch (err) {
      console.error('Failed to load task:', err);
      setError(err instanceof Error ? err.message : 'Failed to load task');
    } finally {
      setLoading(false);
    }
  }, [params.id]);

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
          const taskData = await api.getTask(params.id);
          setTask(taskData as TaskWithArtifacts);

          if (taskData.status === 'RUNNING') {
            const logsData = await api.getTaskLogs(params.id);
            setLogs(logsData.logs.map(log => ({
              ...log,
              taskId: params.id,
              timestamp: new Date(log.timestamp),
            })) as TaskLog[]);
          }
        } catch (err) {
          console.error('Failed to refresh task:', err);
        }
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [session, task?.status, params.id]);

  const handleCancel = async () => {
    if (!task) return;

    try {
      setCancelling(true);
      await api.cancelTask(task.id);
      await loadTask();
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
    } catch (err) {
      console.error('Failed to retry task:', err);
      setError(err instanceof Error ? err.message : 'Failed to retry task');
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return <TaskDetailSkeleton />;
  }

  if (error && !task) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/tasks">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-6">
            <XCircle className="h-6 w-6 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error loading task</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" onClick={loadTask} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/tasks">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">Task not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const fileChanges = task.artifacts?.filter(a => a.type === 'file_change') || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/tasks">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              {getStatusIcon(task.status)}
              <h1 className="text-2xl font-bold tracking-tight">{task.title}</h1>
              {getStatusBadge(task.status)}
            </div>
            <p className="text-muted-foreground mt-1">{task.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {(task.status === 'RUNNING' || task.status === 'QUEUED') && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <StopCircle className="mr-2 h-4 w-4" />
              )}
              Cancel
            </Button>
          )}
          {task.status === 'FAILED' && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={retrying}
            >
              {retrying ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Retry
            </Button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <XCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Failed Task Error */}
      {task.status === 'FAILED' && task.errorMessage && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <XCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Task Failed</p>
                <p className="text-sm text-muted-foreground mt-1">{task.errorMessage}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <GitBranch className="h-4 w-4" />
              <span className="text-sm">Repository</span>
            </div>
            <Link
              href={task.repoUrl}
              target="_blank"
              className="font-medium hover:text-primary flex items-center gap-1"
            >
              {extractRepoName(task.repoUrl)}
              <ExternalLink className="h-3 w-3" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <GitBranch className="h-4 w-4" />
              <span className="text-sm">Branch</span>
            </div>
            <p className="font-medium">
              {task.repoBranch}
              {task.targetBranch && ` → ${task.targetBranch}`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Clock className="h-4 w-4" />
              <span className="text-sm">Started</span>
            </div>
            <p className="font-medium">{formatDate(task.startedAt)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-muted-foreground text-sm mb-1">Credits Used</div>
            <p className="text-2xl font-bold">{task.creditsUsed}</p>
          </CardContent>
        </Card>
      </div>

      {/* Execution Time */}
      {task.executionTime && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Execution Time</span>
              <span className="font-medium">
                {Math.floor(task.executionTime / 60)}m {task.executionTime % 60}s
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="logs" className="space-y-4">
        <TabsList>
          <TabsTrigger value="logs" className="flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Logs
          </TabsTrigger>
          <TabsTrigger value="changes" className="flex items-center gap-2">
            <FileCode className="h-4 w-4" />
            Changes ({fileChanges.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="logs">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Execution Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px] rounded-md border bg-muted/30 p-4">
                <div className="terminal-output space-y-1 font-mono text-sm">
                  {logs.length === 0 ? (
                    <div className="text-muted-foreground text-center py-8">
                      {task.status === 'QUEUED' || task.status === 'PENDING'
                        ? 'Waiting for task to start...'
                        : 'No logs available'}
                    </div>
                  ) : (
                    logs.map((log, index) => (
                      <div key={log.id || index} className="flex gap-4">
                        <span className="text-muted-foreground">
                          [{formatTimestamp(log.timestamp)}]
                        </span>
                        <span className={`w-12 ${getLogLevelClass(log.level)}`}>
                          {log.level}
                        </span>
                        <span>{log.message}</span>
                      </div>
                    ))
                  )}
                  {task.status === 'RUNNING' && (
                    <div className="flex items-center gap-2 text-muted-foreground mt-2">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span>Waiting for more output...</span>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="changes">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">File Changes</CardTitle>
            </CardHeader>
            <CardContent>
              {fileChanges.length === 0 ? (
                <div className="text-muted-foreground text-center py-8">
                  {task.status === 'COMPLETED'
                    ? 'No file changes recorded'
                    : 'File changes will appear here after the task completes'}
                </div>
              ) : (
                <div className="space-y-2">
                  {fileChanges.map((change, index) => {
                    const metadata = change.metadata as { additions?: number; deletions?: number; status?: string } | undefined;
                    return (
                      <div
                        key={change.id || index}
                        className="flex items-center justify-between p-3 rounded-lg border"
                      >
                        <div className="flex items-center gap-3">
                          <Badge
                            variant={metadata?.status === 'added' ? 'success' : 'secondary'}
                            className="w-16 justify-center"
                          >
                            {metadata?.status || 'modified'}
                          </Badge>
                          <span className="font-mono text-sm">{change.path}</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          {metadata?.additions !== undefined && (
                            <span className="text-green-500">+{metadata.additions}</span>
                          )}
                          {metadata?.deletions !== undefined && metadata.deletions > 0 && (
                            <span className="text-red-500">-{metadata.deletions}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* PR Link (when completed) */}
      {task.status === 'COMPLETED' && task.pullRequestUrl && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <GitPullRequest className="h-6 w-6 text-green-500" />
                <div>
                  <p className="font-semibold">Pull Request Created</p>
                  <p className="text-sm text-muted-foreground">
                    Your changes are ready for review
                  </p>
                </div>
              </div>
              <Button asChild>
                <Link href={task.pullRequestUrl} target="_blank">
                  View Pull Request
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
