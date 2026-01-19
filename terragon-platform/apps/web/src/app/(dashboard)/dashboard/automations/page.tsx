'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Skeleton,
  Switch,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@terragon/ui';
import {
  Plus,
  Zap,
  Clock,
  GitBranch,
  MessageSquare,
  Webhook,
  MoreVertical,
  Play,
  Pause,
  Trash2,
  Pencil,
  History,
  AlertCircle,
} from 'lucide-react';
import { api, Automation, AutomationTrigger } from '@/lib/api';
import { useSession } from 'next-auth/react';

function getTriggerIcon(type: AutomationTrigger['type']) {
  switch (type) {
    case 'schedule':
      return <Clock className="h-4 w-4" />;
    case 'github':
      return <GitBranch className="h-4 w-4" />;
    case 'slack':
      return <MessageSquare className="h-4 w-4" />;
    case 'webhook':
      return <Webhook className="h-4 w-4" />;
    default:
      return <Zap className="h-4 w-4" />;
  }
}

function getTriggerLabel(trigger: AutomationTrigger): string {
  switch (trigger.type) {
    case 'schedule':
      return `Scheduled: ${trigger.cron}`;
    case 'github':
      return `GitHub: ${trigger.events.join(', ')}`;
    case 'slack':
      return `Slack${trigger.channel ? `: #${trigger.channel}` : ''}`;
    case 'webhook':
      return 'Webhook';
    default:
      return 'Unknown';
  }
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

function AutomationsLoadingSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-5 w-10" />
            </div>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-full mb-4" />
            <div className="flex items-center gap-2 mb-4">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 w-24" />
            </div>
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-8" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AutomationsPage() {
  const { data: session } = useSession();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadAutomations();
    }
  }, [session]);

  async function loadAutomations() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAutomations();
      setAutomations(data);
    } catch (err) {
      console.error('Failed to load automations:', err);
      setError(err instanceof Error ? err.message : 'Failed to load automations');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(automation: Automation) {
    try {
      setTogglingId(automation.id);
      if (automation.enabled) {
        await api.disableAutomation(automation.id);
      } else {
        await api.enableAutomation(automation.id);
      }
      setAutomations((prev) =>
        prev.map((a) => (a.id === automation.id ? { ...a, enabled: !a.enabled } : a))
      );
    } catch (err) {
      console.error('Failed to toggle automation:', err);
    } finally {
      setTogglingId(null);
    }
  }

  async function handleTrigger(automation: Automation) {
    try {
      await api.triggerAutomation(automation.id);
      // Could show a toast notification here
    } catch (err) {
      console.error('Failed to trigger automation:', err);
    }
  }

  async function handleDelete(automation: Automation) {
    if (!confirm(`Are you sure you want to delete "${automation.name}"?`)) {
      return;
    }
    try {
      await api.deleteAutomation(automation.id);
      setAutomations((prev) => prev.filter((a) => a.id !== automation.id));
    } catch (err) {
      console.error('Failed to delete automation:', err);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Automations</h1>
          <p className="text-muted-foreground">
            Set up automated tasks triggered by schedules, GitHub events, or webhooks.
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/automations/new">
            <Plus className="mr-2 h-4 w-4" />
            New Automation
          </Link>
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error loading automations</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={loadAutomations} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Content */}
      {loading ? (
        <AutomationsLoadingSkeleton />
      ) : automations.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <Zap className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No automations yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first automation to run tasks automatically based on triggers.
            </p>
            <Button asChild>
              <Link href="/dashboard/automations/new">
                <Plus className="mr-2 h-4 w-4" />
                Create Automation
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {automations.map((automation) => (
            <Card key={automation.id} className={!automation.enabled ? 'opacity-60' : ''}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{automation.name}</CardTitle>
                  <Switch
                    checked={automation.enabled}
                    onCheckedChange={() => handleToggle(automation)}
                    disabled={togglingId === automation.id}
                  />
                </div>
              </CardHeader>
              <CardContent>
                {automation.description && (
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {automation.description}
                  </p>
                )}

                <div className="flex items-center gap-2 mb-4">
                  {getTriggerIcon(automation.trigger.type)}
                  <span className="text-sm">{getTriggerLabel(automation.trigger)}</span>
                </div>

                <div className="flex items-center gap-2 mb-4">
                  <Badge variant="outline">{automation.task.agent}</Badge>
                  <span className="text-xs text-muted-foreground truncate">
                    {automation.task.repository}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-4">
                    <span>{automation.runCount} runs</span>
                    {automation.lastRunAt && (
                      <span>Last: {formatRelativeTime(automation.lastRunAt)}</span>
                    )}
                  </div>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleTrigger(automation)}>
                        <Play className="mr-2 h-4 w-4" />
                        Run Now
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href={`/dashboard/automations/${automation.id}`}>
                          <History className="mr-2 h-4 w-4" />
                          View Runs
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem asChild>
                        <Link href={`/dashboard/automations/${automation.id}/edit`}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleToggle(automation)}>
                        {automation.enabled ? (
                          <>
                            <Pause className="mr-2 h-4 w-4" />
                            Disable
                          </>
                        ) : (
                          <>
                            <Play className="mr-2 h-4 w-4" />
                            Enable
                          </>
                        )}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleDelete(automation)}
                        className="text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
