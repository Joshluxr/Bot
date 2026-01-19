'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from '@terragon/ui';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { GitHubRepo } from '@terragon/shared';

export default function NewTaskPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [reposError, setReposError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    repoUrl: '',
    repoBranch: 'main',
    agentType: 'CLAUDE',
  });

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadRepos();
    }
  }, [session]);

  async function loadRepos() {
    try {
      setLoadingRepos(true);
      setReposError(null);
      const repoList = await api.getGitHubRepos();
      setRepos(repoList);
    } catch (err) {
      console.error('Failed to load repositories:', err);
      setReposError(err instanceof Error ? err.message : 'Failed to load repositories');
    } finally {
      setLoadingRepos(false);
    }
  }

  const handleRepoChange = (repoUrl: string) => {
    const selectedRepo = repos.find(r => r.cloneUrl === repoUrl || r.url === repoUrl);
    setFormData({
      ...formData,
      repoUrl,
      repoBranch: selectedRepo?.defaultBranch || 'main',
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await api.createTask({
        title: formData.title,
        description: formData.description,
        repoUrl: formData.repoUrl,
        repoBranch: formData.repoBranch,
        agentType: formData.agentType,
      });

      router.push('/dashboard/tasks');
    } catch (err) {
      console.error('Failed to create task:', err);
      setSubmitError(err instanceof Error ? err.message : 'Failed to create task');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/tasks">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Task</h1>
          <p className="text-muted-foreground">
            Create a new AI-powered coding task
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Task Details</CardTitle>
            <CardDescription>
              Describe what you want the AI agent to do
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Submit Error */}
            {submitError && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <p className="text-sm">{submitError}</p>
              </div>
            )}

            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                placeholder="e.g., Add user authentication flow"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                required
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe what you want done in detail. The more context you provide, the better the results."
                rows={6}
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                required
              />
              <p className="text-xs text-muted-foreground">
                Tip: Include specific file names, function names, or requirements
                for best results.
              </p>
            </div>

            {/* Repository */}
            <div className="space-y-2">
              <Label htmlFor="repo">Repository</Label>
              {loadingRepos ? (
                <Skeleton className="h-10 w-full" />
              ) : reposError ? (
                <div className="flex items-center justify-between p-3 rounded-md border border-destructive">
                  <span className="text-sm text-destructive">{reposError}</span>
                  <Button variant="outline" size="sm" onClick={loadRepos}>
                    Retry
                  </Button>
                </div>
              ) : repos.length === 0 ? (
                <div className="p-4 rounded-md border text-center">
                  <p className="text-muted-foreground mb-2">
                    No repositories connected
                  </p>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/dashboard/integrations">Connect GitHub</Link>
                  </Button>
                </div>
              ) : (
                <Select
                  value={formData.repoUrl}
                  onValueChange={handleRepoChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a repository" />
                  </SelectTrigger>
                  <SelectContent>
                    {repos.map((repo) => (
                      <SelectItem key={repo.id} value={repo.cloneUrl || repo.url}>
                        <div className="flex items-center gap-2">
                          <span>{repo.fullName}</span>
                          {repo.private && (
                            <span className="text-xs text-muted-foreground">(private)</span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                Don&apos;t see your repo?{' '}
                <Link href="/dashboard/integrations" className="text-primary hover:underline">
                  Connect more repositories
                </Link>
              </p>
            </div>

            {/* Branch */}
            <div className="space-y-2">
              <Label htmlFor="branch">Branch</Label>
              <Input
                id="branch"
                placeholder="main"
                value={formData.repoBranch}
                onChange={(e) =>
                  setFormData({ ...formData, repoBranch: e.target.value })
                }
              />
            </div>

            {/* Agent Type */}
            <div className="space-y-2">
              <Label htmlFor="agent">AI Agent</Label>
              <Select
                value={formData.agentType}
                onValueChange={(value) =>
                  setFormData({ ...formData, agentType: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CLAUDE">
                    Claude Code (Anthropic)
                  </SelectItem>
                  <SelectItem value="OPENAI">
                    GPT-4 (OpenAI)
                  </SelectItem>
                  <SelectItem value="GEMINI">
                    Gemini (Google)
                  </SelectItem>
                  <SelectItem value="CUSTOM">
                    Custom Agent
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Credit Estimate */}
        <Card className="mt-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Estimated Credits</p>
                <p className="text-sm text-muted-foreground">
                  Based on typical task complexity
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold">15-30</p>
                <p className="text-sm text-muted-foreground">credits</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-end gap-4 mt-6">
          <Button variant="outline" type="button" asChild>
            <Link href="/dashboard/tasks">Cancel</Link>
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting || !formData.repoUrl || !formData.title || !formData.description}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Task'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
