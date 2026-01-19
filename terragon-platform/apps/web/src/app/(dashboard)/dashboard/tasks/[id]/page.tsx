'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
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
} from 'lucide-react';

// Mock task data
const mockTask = {
  id: '1',
  title: 'Add user authentication flow',
  description: 'Implement OAuth2 login with GitHub and Google providers. Include session management, protected routes, and user profile storage.',
  status: 'RUNNING',
  agentType: 'CLAUDE',
  repo: 'acme/frontend',
  repoUrl: 'https://github.com/acme/frontend',
  branch: 'main',
  targetBranch: 'feat/auth-flow',
  createdAt: '2024-01-15T10:30:00Z',
  startedAt: '2024-01-15T10:31:00Z',
  creditsUsed: 12,
  progress: 75,
  sandboxId: 'sbx_abc123',
};

// Mock logs
const mockLogs = [
  { timestamp: '10:31:00', level: 'INFO', message: 'Starting sandbox environment...' },
  { timestamp: '10:31:05', level: 'INFO', message: 'Sandbox ready. Cloning repository...' },
  { timestamp: '10:31:15', level: 'INFO', message: 'Repository cloned. Installing dependencies...' },
  { timestamp: '10:32:00', level: 'INFO', message: 'Dependencies installed. Starting agent...' },
  { timestamp: '10:32:05', level: 'INFO', message: 'Agent initialized with Claude Code' },
  { timestamp: '10:32:10', level: 'INFO', message: 'Reading project structure...' },
  { timestamp: '10:33:00', level: 'INFO', message: 'Creating auth provider component...' },
  { timestamp: '10:34:00', level: 'INFO', message: 'Implementing GitHub OAuth flow...' },
  { timestamp: '10:35:00', level: 'INFO', message: 'Adding session management...' },
  { timestamp: '10:36:00', level: 'INFO', message: 'Creating protected route wrapper...' },
  { timestamp: '10:37:00', level: 'WARN', message: 'TypeScript warning: implicit any type' },
  { timestamp: '10:37:05', level: 'INFO', message: 'Fixed type annotations' },
  { timestamp: '10:38:00', level: 'INFO', message: 'Running tests...' },
];

// Mock file changes
const mockChanges = [
  { path: 'src/lib/auth.ts', additions: 145, deletions: 0, status: 'added' },
  { path: 'src/components/AuthProvider.tsx', additions: 89, deletions: 0, status: 'added' },
  { path: 'src/hooks/useAuth.ts', additions: 45, deletions: 0, status: 'added' },
  { path: 'src/middleware.ts', additions: 32, deletions: 5, status: 'modified' },
  { path: 'src/app/api/auth/[...nextauth]/route.ts', additions: 67, deletions: 0, status: 'added' },
  { path: 'package.json', additions: 3, deletions: 0, status: 'modified' },
];

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
  };
  return (
    <Badge variant={variants[status] || 'secondary'} className="text-sm">
      {status.charAt(0) + status.slice(1).toLowerCase()}
    </Badge>
  );
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
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
    default:
      return 'text-muted-foreground';
  }
}

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const [logs, setLogs] = useState(mockLogs);

  // Simulate real-time log updates
  useEffect(() => {
    if (mockTask.status === 'RUNNING') {
      const interval = setInterval(() => {
        const newLog = {
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }).slice(0, 8),
          level: 'INFO',
          message: `Processing... ${Math.floor(Math.random() * 100)}%`,
        };
        setLogs((prev) => [...prev, newLog].slice(-50));
      }, 3000);

      return () => clearInterval(interval);
    }
  }, []);

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
              {getStatusIcon(mockTask.status)}
              <h1 className="text-2xl font-bold tracking-tight">{mockTask.title}</h1>
              {getStatusBadge(mockTask.status)}
            </div>
            <p className="text-muted-foreground mt-1">{mockTask.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {mockTask.status === 'RUNNING' && (
            <Button variant="destructive" size="sm">
              <StopCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {mockTask.status === 'FAILED' && (
            <Button variant="outline" size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <GitBranch className="h-4 w-4" />
              <span className="text-sm">Repository</span>
            </div>
            <Link
              href={mockTask.repoUrl}
              target="_blank"
              className="font-medium hover:text-primary flex items-center gap-1"
            >
              {mockTask.repo}
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
            <p className="font-medium">{mockTask.branch} → {mockTask.targetBranch}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Clock className="h-4 w-4" />
              <span className="text-sm">Started</span>
            </div>
            <p className="font-medium">{formatDate(mockTask.startedAt!)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-muted-foreground text-sm mb-1">Credits Used</div>
            <p className="text-2xl font-bold">{mockTask.creditsUsed}</p>
          </CardContent>
        </Card>
      </div>

      {/* Progress */}
      {mockTask.status === 'RUNNING' && mockTask.progress && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Progress</span>
              <span className="text-sm text-muted-foreground">{mockTask.progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${mockTask.progress}%` }}
              />
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
            Changes ({mockChanges.length})
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
                  {logs.map((log, index) => (
                    <div key={index} className="flex gap-4">
                      <span className="text-muted-foreground">[{log.timestamp}]</span>
                      <span className={`w-12 ${getLogLevelClass(log.level)}`}>
                        {log.level}
                      </span>
                      <span>{log.message}</span>
                    </div>
                  ))}
                  {mockTask.status === 'RUNNING' && (
                    <div className="flex items-center gap-2 text-muted-foreground">
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
              <div className="space-y-2">
                {mockChanges.map((change, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={change.status === 'added' ? 'success' : 'secondary'}
                        className="w-16 justify-center"
                      >
                        {change.status}
                      </Badge>
                      <span className="font-mono text-sm">{change.path}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-green-500">+{change.additions}</span>
                      {change.deletions > 0 && (
                        <span className="text-red-500">-{change.deletions}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* PR Link (when completed) */}
      {mockTask.status === 'COMPLETED' && (
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
                <Link href="#" target="_blank">
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
