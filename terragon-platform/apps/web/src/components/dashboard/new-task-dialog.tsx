'use client';

import { useState, useEffect } from 'react';
import { X, GitBranch, ChevronDown, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { GitHubRepo } from '@terragon/shared';

interface NewTaskDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated?: () => void;
}

const agents = [
  { id: 'CLAUDE', name: 'Claude Code', description: 'Anthropic' },
  { id: 'OPENAI', name: 'GPT-4', description: 'OpenAI' },
  { id: 'GEMINI', name: 'Gemini', description: 'Google' },
  { id: 'CUSTOM', name: 'Custom', description: 'Your Agent' },
];

export function NewTaskDialog({ isOpen, onClose, onTaskCreated }: NewTaskDialogProps) {
  const { data: session } = useSession();
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [reposError, setReposError] = useState<string | null>(null);

  const [repository, setRepository] = useState('');
  const [branch, setBranch] = useState('main');
  const [agent, setAgent] = useState('CLAUDE');
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && session?.accessToken) {
      api.setToken(session.accessToken);
      loadRepos();
    }
  }, [isOpen, session]);

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

  const handleRepoChange = (repoValue: string) => {
    setRepository(repoValue);
    const selectedRepo = repos.find(r => r.fullName === repoValue);
    if (selectedRepo) {
      setBranch(selectedRepo.defaultBranch);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const selectedRepo = repos.find(r => r.fullName === repository);
      const repoUrl = selectedRepo?.cloneUrl || selectedRepo?.url || `https://github.com/${repository}`;

      await api.createTask({
        title: title || `Task for ${repository}`,
        description: prompt,
        repoUrl,
        repoBranch: branch,
        agentType: agent,
      });

      onClose();
      onTaskCreated?.();

      // Reset form
      setRepository('');
      setBranch('main');
      setAgent('CLAUDE');
      setTitle('');
      setPrompt('');
    } catch (err) {
      console.error('Failed to create task:', err);
      setSubmitError(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-lg mx-4 bg-card rounded-xl shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-card">
          <h2 className="text-lg font-semibold">New Task</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Error Message */}
          {submitError && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
              {submitError}
            </div>
          )}

          {/* Title */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Task Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Add user authentication flow"
              className="w-full px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Repository */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Repository
            </label>
            <div className="relative">
              <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              {loadingRepos ? (
                <div className="flex items-center justify-center w-full py-2 px-3 rounded-lg border bg-background">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-sm text-muted-foreground">Loading repositories...</span>
                </div>
              ) : reposError ? (
                <div className="flex items-center justify-between w-full py-2 px-3 rounded-lg border border-destructive">
                  <span className="text-sm text-destructive">{reposError}</span>
                  <button
                    type="button"
                    onClick={loadRepos}
                    className="text-sm text-primary hover:underline"
                  >
                    Retry
                  </button>
                </div>
              ) : repos.length === 0 ? (
                <div className="flex flex-col items-center justify-center w-full py-4 px-3 rounded-lg border">
                  <span className="text-sm text-muted-foreground mb-2">No repositories connected</span>
                  <a
                    href="/dashboard/integrations"
                    className="text-sm text-primary hover:underline"
                  >
                    Connect GitHub
                  </a>
                </div>
              ) : (
                <>
                  <select
                    value={repository}
                    onChange={(e) => handleRepoChange(e.target.value)}
                    required
                    className="w-full pl-10 pr-10 py-2 rounded-lg border bg-background appearance-none focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select a repository</option>
                    {repos.map((repo) => (
                      <option key={repo.id} value={repo.fullName}>
                        {repo.fullName} {repo.private ? '(private)' : ''}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                </>
              )}
            </div>
          </div>

          {/* Branch */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Base Branch
            </label>
            <input
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Agent */}
          <div>
            <label className="block text-sm font-medium mb-2">
              AI Agent
            </label>
            <div className="grid grid-cols-2 gap-2">
              {agents.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAgent(a.id)}
                  className={`flex flex-col items-start p-3 rounded-lg border text-left transition-colors ${
                    agent === a.id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  }`}
                >
                  <span className="text-sm font-medium">{a.name}</span>
                  <span className="text-xs text-muted-foreground">{a.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium mb-2">
              What would you like the agent to do?
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              required
              rows={4}
              placeholder="Describe your task in detail..."
              className="w-full px-3 py-2 rounded-lg border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Be specific about what you want. The agent will analyze your codebase and implement the task.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border rounded-lg font-medium text-sm hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !repository || !prompt || loadingRepos}
              className="flex-1 py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                'Create Task'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
