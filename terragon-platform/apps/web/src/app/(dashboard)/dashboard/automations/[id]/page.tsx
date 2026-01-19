'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Skeleton,
  Switch,
} from '@terragon/ui';
import {
  ArrowLeft,
  Clock,
  GitBranch,
  MessageSquare,
  Webhook,
  Play,
  Pencil,
  Trash2,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { api, Automation, AutomationRun, AutomationTrigger } from '@/lib/api';
import { useSession } from 'next-auth/react';

function getTriggerIcon(type: AutomationTrigger['type']) {
  switch (type) {
    case 'schedule':
      return <Clock className="h-5 w-5" />;
    case 'github':
      return <GitBranch className="h-5 w-5" />;
    case 'slack':
      return <MessageSquare className="h-5 w-5" />;
    case 'webhook':
      return <Webhook className="h-5 w-5" />;
  }
}

function getTriggerDetails(trigger: AutomationTrigger): string {
  switch (trigger.type) {
    case 'schedule':
      return `Cron: ${trigger.cron}${trigger.timezone ? ` (${trigger.timezone})` : ''}`;
    case 'github':
      return `Events: ${trigger.events.join(', ')}${trigger.branches?.length ? ` | Branches: ${trigger.branches.join(', ')}` : ''}`;
    case 'slack':
      return `${trigger.channel ? `Channel: ${trigger.channel}` : 'Any channel'}${trigger.keywords?.length ? ` | Keywords: ${trigger.keywords.join(', ')}` : ''}`;
    case 'webhook':
      return 'HTTP webhook endpoint';
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function AutomationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { data: session } = useSession();
  const automationId = params.id as string;

  const [automation, setAutomation] = useState<Automation | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadData();
    }
  }, [session, automationId]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [automationData, runsData] = await Promise.all([
        api.getAutomation(automationId),
        api.getAutomationRuns(automationId, 20),
      ]);
      setAutomation(automationData);
      setRuns(runsData);
    } catch (err) {
      console.error('Failed to load automation:', err);
      setError(err instanceof Error ? err.message : 'Failed to load automation');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle() {
    if (!automation) return;
    try {
      setToggling(true);
      if (automation.enabled) {
        await api.disableAutomation(automation.id);
      } else {
        await api.enableAutomation(automation.id);
      }
      setAutomation({ ...automation, enabled: !automation.enabled });
    } catch (err) {
      console.error('Failed to toggle automation:', err);
    } finally {
      setToggling(false);
    }
  }

  async function handleTrigger() {
    if (!automation) return;
    try {
      setTriggering(true);
      const run = await api.triggerAutomation(automation.id);
      setRuns([run, ...runs]);
    } catch (err) {
      console.error('Failed to trigger automation:', err);
    } finally {
      setTriggering(false);
    }
  }

  async function handleDelete() {
    if (!automation) return;
    if (!confirm(`Are you sure you want to delete "${automation.name}"?`)) return;

    try {
      setDeleting(true);
      await api.deleteAutomation(automation.id);
      router.push('/dashboard/automations');
    } catch (err) {
      console.error('Failed to delete automation:', err);
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error || !automation) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-4 p-6">
          <AlertCircle className="h-6 w-6 text-destructive" />
          <div>
            <p className="font-medium text-destructive">Failed to load automation</p>
            <p className="text-sm text-muted-foreground">{error || 'Automation not found'}</p>
          </div>
          <Button variant="outline" onClick={loadData} className="ml-auto">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/automations">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{automation.name}</h1>
              <Badge variant={automation.enabled ? 'default' : 'secondary'}>
                {automation.enabled ? 'Active' : 'Disabled'}
              </Badge>
            </div>
            {automation.description && (
              <p className="text-muted-foreground">{automation.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Switch checked={automation.enabled} onCheckedChange={handleToggle} disabled={toggling} />
          <Button variant="outline" onClick={handleTrigger} disabled={triggering}>
            {triggering ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run Now
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/dashboard/automations/${automation.id}/edit`}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
            {deleting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-4 w-4" />
            )}
            Delete
          </Button>
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Trigger Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {getTriggerIcon(automation.trigger.type)}
              Trigger
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm font-medium capitalize">{automation.trigger.type}</p>
              <p className="text-sm text-muted-foreground">
                {getTriggerDetails(automation.trigger)}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Task Card */}
        <Card>
          <CardHeader>
            <CardTitle>Task Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Repository</span>
                <span className="text-sm font-medium">{automation.task.repository}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Agent</span>
                <Badge variant="outline">{automation.task.agent}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Branch</span>
                <span className="text-sm font-medium">{automation.task.branch || 'main'}</span>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground mb-2">Prompt:</p>
              <p className="text-sm bg-muted p-3 rounded-lg">{automation.task.prompt}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Runs</p>
            <p className="text-2xl font-bold">{automation.runCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Last Run</p>
            <p className="text-2xl font-bold">
              {automation.lastRunAt ? formatDate(automation.lastRunAt) : 'Never'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Created</p>
            <p className="text-2xl font-bold">{formatDate(automation.createdAt)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No runs yet. Click &quot;Run Now&quot; to trigger this automation manually.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(run.status)}
                    <div>
                      <p className="font-medium capitalize">{run.status}</p>
                      <p className="text-sm text-muted-foreground">
                        Triggered by {run.triggeredBy} • {formatDate(run.createdAt)}
                      </p>
                    </div>
                  </div>
                  {run.taskId && (
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/dashboard/tasks/${run.taskId}`}>
                        View Task
                        <ExternalLink className="ml-2 h-3 w-3" />
                      </Link>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
