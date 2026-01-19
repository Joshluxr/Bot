import Link from 'next/link';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@terragon/ui';
import {
  Plus,
  Search,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Filter,
} from 'lucide-react';

// Mock data
const tasks = [
  {
    id: '1',
    title: 'Add user authentication flow',
    description: 'Implement OAuth2 login with GitHub and Google providers',
    status: 'RUNNING',
    agentType: 'CLAUDE',
    repo: 'acme/frontend',
    branch: 'main',
    createdAt: '2024-01-15T10:30:00Z',
    startedAt: '2024-01-15T10:31:00Z',
    creditsUsed: 12,
    progress: 75,
  },
  {
    id: '2',
    title: 'Fix pagination bug in dashboard',
    description: 'Page numbers not updating correctly when switching pages',
    status: 'QUEUED',
    agentType: 'CLAUDE',
    repo: 'acme/frontend',
    branch: 'main',
    createdAt: '2024-01-15T09:00:00Z',
    creditsUsed: 0,
  },
  {
    id: '3',
    title: 'Refactor API endpoints',
    description: 'Convert REST endpoints to use proper HTTP methods and status codes',
    status: 'COMPLETED',
    agentType: 'OPENAI',
    repo: 'acme/backend',
    branch: 'main',
    createdAt: '2024-01-15T08:00:00Z',
    completedAt: '2024-01-15T08:45:00Z',
    creditsUsed: 23,
    prUrl: 'https://github.com/acme/backend/pull/142',
  },
  {
    id: '4',
    title: 'Add unit tests for auth module',
    description: 'Write comprehensive unit tests for the authentication module',
    status: 'FAILED',
    agentType: 'CLAUDE',
    repo: 'acme/backend',
    branch: 'main',
    createdAt: '2024-01-14T16:00:00Z',
    creditsUsed: 8,
    error: 'Test timeout exceeded after 30 minutes',
  },
  {
    id: '5',
    title: 'Update dependencies',
    description: 'Update all npm packages to their latest versions',
    status: 'COMPLETED',
    agentType: 'GEMINI',
    repo: 'acme/frontend',
    branch: 'develop',
    createdAt: '2024-01-14T14:00:00Z',
    completedAt: '2024-01-14T14:20:00Z',
    creditsUsed: 5,
    prUrl: 'https://github.com/acme/frontend/pull/89',
  },
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

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function TasksPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground">
            Manage and monitor your AI coding tasks
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/tasks/new">
            <Plus className="mr-2 h-4 w-4" />
            New Task
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search tasks..." className="pl-9" />
            </div>
            <Select defaultValue="all">
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="queued">Queued</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select defaultValue="all">
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Agent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Agents</SelectItem>
                <SelectItem value="claude">Claude</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="gemini">Gemini</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Task List */}
      <div className="space-y-4">
        {tasks.map((task) => (
          <Card key={task.id} className="hover:border-primary/30 transition-colors">
            <Link href={`/dashboard/tasks/${task.id}`}>
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1">
                    {getStatusIcon(task.status)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold truncate">{task.title}</h3>
                        {getStatusBadge(task.status)}
                        <Badge variant="outline">{task.agentType}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                        {task.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span>{task.repo}</span>
                        <span>•</span>
                        <span>{task.branch}</span>
                        <span>•</span>
                        <span>{formatDate(task.createdAt)}</span>
                        {task.creditsUsed > 0 && (
                          <>
                            <span>•</span>
                            <span>{task.creditsUsed} credits</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {task.status === 'RUNNING' && task.progress && (
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {task.progress}%
                        </span>
                      </div>
                    )}
                    {task.prUrl && (
                      <Badge variant="outline" className="text-primary">
                        PR Ready
                      </Badge>
                    )}
                  </div>
                </div>
              </CardContent>
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
