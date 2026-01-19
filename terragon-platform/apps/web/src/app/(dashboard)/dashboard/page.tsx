import Link from 'next/link';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@terragon/ui';
import {
  Plus,
  ArrowRight,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';

// Mock data - in production this would come from the API
const recentTasks = [
  {
    id: '1',
    title: 'Add user authentication flow',
    status: 'RUNNING',
    repo: 'acme/frontend',
    createdAt: '2 hours ago',
    progress: 75,
  },
  {
    id: '2',
    title: 'Fix pagination bug in dashboard',
    status: 'QUEUED',
    repo: 'acme/frontend',
    createdAt: '3 hours ago',
  },
  {
    id: '3',
    title: 'Refactor API endpoints',
    status: 'COMPLETED',
    repo: 'acme/backend',
    createdAt: '5 hours ago',
    prUrl: 'https://github.com/acme/backend/pull/142',
  },
  {
    id: '4',
    title: 'Add unit tests for auth module',
    status: 'FAILED',
    repo: 'acme/backend',
    createdAt: '1 day ago',
    error: 'Test timeout exceeded',
  },
];

const stats = [
  { label: 'Tasks This Month', value: 24 },
  { label: 'Completed', value: 18 },
  { label: 'Success Rate', value: '75%' },
  { label: 'Credits Used', value: 847 },
];

function getStatusIcon(status: string) {
  switch (status) {
    case 'RUNNING':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case 'QUEUED':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'COMPLETED':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'FAILED':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
}

function getStatusBadge(status: string) {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
    RUNNING: 'default',
    QUEUED: 'warning',
    COMPLETED: 'success',
    FAILED: 'destructive',
    PENDING: 'secondary',
  };
  return (
    <Badge variant={variants[status] || 'secondary'}>
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </Badge>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's an overview of your recent activity.
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/tasks/new">
            <Plus className="mr-2 h-4 w-4" />
            New Task
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Tasks */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Tasks</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/dashboard/tasks">
              View all
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentTasks.map((task) => (
              <Link
                key={task.id}
                href={`/dashboard/tasks/${task.id}`}
                className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {getStatusIcon(task.status)}
                  <div>
                    <p className="font-medium">{task.title}</p>
                    <p className="text-sm text-muted-foreground">
                      {task.repo} • {task.createdAt}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {task.status === 'RUNNING' && task.progress && (
                    <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                  )}
                  {getStatusBadge(task.status)}
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <Link href="/dashboard/tasks/new">
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Plus className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="font-semibold">Create New Task</p>
                <p className="text-sm text-muted-foreground">
                  Start a new AI-powered task
                </p>
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <Link href="/dashboard/integrations">
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <svg className="h-6 w-6 text-primary" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </div>
              <div>
                <p className="font-semibold">Connect GitHub</p>
                <p className="text-sm text-muted-foreground">
                  Link your repositories
                </p>
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <Link href="/docs">
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <svg className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div>
                <p className="font-semibold">Read the Docs</p>
                <p className="text-sm text-muted-foreground">
                  Learn how to use Terragon
                </p>
              </div>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
}
