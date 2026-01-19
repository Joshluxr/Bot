'use client';

import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Input,
  Label,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Checkbox,
} from '@terragon/ui';
import {
  ArrowLeft,
  Clock,
  GitBranch,
  MessageSquare,
  Webhook,
  Loader2,
} from 'lucide-react';
import Link from 'next/link';
import { api, AutomationTrigger, AutomationTask, Automation } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { GitHubRepo } from '@terragon/shared';

const TRIGGER_TYPES = [
  { value: 'schedule', label: 'Schedule', icon: Clock, description: 'Run on a cron schedule' },
  { value: 'github', label: 'GitHub Event', icon: GitBranch, description: 'Trigger on GitHub events' },
  { value: 'slack', label: 'Slack Message', icon: MessageSquare, description: 'Trigger from Slack' },
  { value: 'webhook', label: 'Webhook', icon: Webhook, description: 'Trigger via HTTP webhook' },
];

const GITHUB_EVENTS = [
  { value: 'push', label: 'Push' },
  { value: 'pull_request', label: 'Pull Request' },
  { value: 'issue', label: 'Issue' },
  { value: 'release', label: 'Release' },
  { value: 'issue_comment', label: 'Issue Comment' },
];

const AGENTS = [
  { value: 'claude', label: 'Claude Code' },
  { value: 'openai', label: 'OpenAI Codex' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'amp', label: 'Amp' },
  { value: 'opencode', label: 'OpenCode' },
];

const CRON_PRESETS = [
  { value: '0 9 * * *', label: 'Daily at 9 AM' },
  { value: '0 9 * * 1', label: 'Weekly on Monday at 9 AM' },
  { value: '0 0 1 * *', label: 'Monthly on the 1st' },
  { value: '0 */6 * * *', label: 'Every 6 hours' },
  { value: '*/30 * * * *', label: 'Every 30 minutes' },
];

export default function NewAutomationPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(true);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [triggerType, setTriggerType] = useState<'schedule' | 'github' | 'slack' | 'webhook'>('schedule');

  // Schedule trigger
  const [cronExpression, setCronExpression] = useState('0 9 * * *');
  const [timezone, setTimezone] = useState('UTC');

  // GitHub trigger
  const [githubEvents, setGithubEvents] = useState<string[]>(['push']);
  const [githubBranches, setGithubBranches] = useState('');
  const [githubPaths, setGithubPaths] = useState('');

  // Slack trigger
  const [slackChannel, setSlackChannel] = useState('');
  const [slackKeywords, setSlackKeywords] = useState('');
  const [slackMentionOnly, setSlackMentionOnly] = useState(false);

  // Webhook trigger
  const [webhookSecret, setWebhookSecret] = useState('');

  // Task settings
  const [repository, setRepository] = useState('');
  const [prompt, setPrompt] = useState('');
  const [agent, setAgent] = useState('claude');
  const [branch, setBranch] = useState('main');

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadRepos();
    }
  }, [session]);

  async function loadRepos() {
    try {
      setReposLoading(true);
      const data = await api.getGitHubRepos();
      setRepos(data);
    } catch (err) {
      console.error('Failed to load repos:', err);
    } finally {
      setReposLoading(false);
    }
  }

  function buildTrigger(): AutomationTrigger {
    switch (triggerType) {
      case 'schedule':
        return { type: 'schedule', cron: cronExpression, timezone };
      case 'github':
        return {
          type: 'github',
          events: githubEvents as ('push' | 'pull_request' | 'issue' | 'release' | 'issue_comment')[],
          branches: githubBranches ? githubBranches.split(',').map((b) => b.trim()) : undefined,
          paths: githubPaths ? githubPaths.split(',').map((p) => p.trim()) : undefined,
        };
      case 'slack':
        return {
          type: 'slack',
          channel: slackChannel || undefined,
          keywords: slackKeywords ? slackKeywords.split(',').map((k) => k.trim()) : undefined,
          mentionOnly: slackMentionOnly,
        };
      case 'webhook':
        return { type: 'webhook', secret: webhookSecret || undefined };
      default:
        return { type: 'schedule', cron: cronExpression };
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!name || !repository || !prompt) {
      return;
    }

    try {
      setLoading(true);

      const automation = await api.createAutomation({
        name,
        description: description || undefined,
        enabled: true,
        trigger: buildTrigger(),
        task: {
          repository,
          prompt,
          agent,
          branch: branch || undefined,
        },
      });

      router.push('/dashboard/automations');
    } catch (err) {
      console.error('Failed to create automation:', err);
    } finally {
      setLoading(false);
    }
  }

  function toggleGithubEvent(event: string) {
    setGithubEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/automations">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Automation</h1>
          <p className="text-muted-foreground">
            Create an automated task that runs based on triggers.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>Give your automation a name and description.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Daily Code Review"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Describe what this automation does..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        {/* Trigger Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Trigger</CardTitle>
            <CardDescription>Choose what triggers this automation.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Trigger Type Selection */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {TRIGGER_TYPES.map((type) => (
                <div
                  key={type.value}
                  className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                    triggerType === type.value
                      ? 'border-primary bg-primary/5'
                      : 'hover:border-primary/50'
                  }`}
                  onClick={() => setTriggerType(type.value as typeof triggerType)}
                >
                  <type.icon className="h-5 w-5 mb-2" />
                  <p className="font-medium">{type.label}</p>
                  <p className="text-xs text-muted-foreground">{type.description}</p>
                </div>
              ))}
            </div>

            {/* Schedule Config */}
            {triggerType === 'schedule' && (
              <div className="space-y-4 pt-4 border-t">
                <div className="space-y-2">
                  <Label>Cron Expression</Label>
                  <div className="flex gap-2">
                    <Input
                      value={cronExpression}
                      onChange={(e) => setCronExpression(e.target.value)}
                      placeholder="0 9 * * *"
                      className="flex-1"
                    />
                    <Select value={cronExpression} onValueChange={setCronExpression}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Presets" />
                      </SelectTrigger>
                      <SelectContent>
                        {CRON_PRESETS.map((preset) => (
                          <SelectItem key={preset.value} value={preset.value}>
                            {preset.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Format: minute hour day-of-month month day-of-week
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Timezone</Label>
                  <Select value={timezone} onValueChange={setTimezone}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="UTC">UTC</SelectItem>
                      <SelectItem value="America/New_York">Eastern Time</SelectItem>
                      <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                      <SelectItem value="Europe/London">London</SelectItem>
                      <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {/* GitHub Config */}
            {triggerType === 'github' && (
              <div className="space-y-4 pt-4 border-t">
                <div className="space-y-2">
                  <Label>Events</Label>
                  <div className="flex flex-wrap gap-4">
                    {GITHUB_EVENTS.map((event) => (
                      <label key={event.value} className="flex items-center gap-2">
                        <Checkbox
                          checked={githubEvents.includes(event.value)}
                          onCheckedChange={() => toggleGithubEvent(event.value)}
                        />
                        <span className="text-sm">{event.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Branches (optional)</Label>
                  <Input
                    value={githubBranches}
                    onChange={(e) => setGithubBranches(e.target.value)}
                    placeholder="main, develop (comma-separated)"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Paths (optional)</Label>
                  <Input
                    value={githubPaths}
                    onChange={(e) => setGithubPaths(e.target.value)}
                    placeholder="src/**, tests/** (comma-separated)"
                  />
                </div>
              </div>
            )}

            {/* Slack Config */}
            {triggerType === 'slack' && (
              <div className="space-y-4 pt-4 border-t">
                <div className="space-y-2">
                  <Label>Channel (optional)</Label>
                  <Input
                    value={slackChannel}
                    onChange={(e) => setSlackChannel(e.target.value)}
                    placeholder="#engineering"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Keywords (optional)</Label>
                  <Input
                    value={slackKeywords}
                    onChange={(e) => setSlackKeywords(e.target.value)}
                    placeholder="bug, fix, urgent (comma-separated)"
                  />
                </div>
                <label className="flex items-center gap-2">
                  <Checkbox
                    checked={slackMentionOnly}
                    onCheckedChange={(checked) => setSlackMentionOnly(checked as boolean)}
                  />
                  <span className="text-sm">Only trigger when @mentioned</span>
                </label>
              </div>
            )}

            {/* Webhook Config */}
            {triggerType === 'webhook' && (
              <div className="space-y-4 pt-4 border-t">
                <div className="space-y-2">
                  <Label>Secret (optional)</Label>
                  <Input
                    type="password"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                    placeholder="Optional secret for webhook verification"
                  />
                  <p className="text-xs text-muted-foreground">
                    A unique webhook URL will be generated after creation.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Task Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Task Configuration</CardTitle>
            <CardDescription>Configure the task that runs when triggered.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Repository</Label>
              <Select value={repository} onValueChange={setRepository} disabled={reposLoading}>
                <SelectTrigger>
                  <SelectValue placeholder={reposLoading ? 'Loading repos...' : 'Select a repository'} />
                </SelectTrigger>
                <SelectContent>
                  {repos.map((repo) => (
                    <SelectItem key={repo.id} value={repo.fullName}>
                      {repo.fullName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Agent</Label>
              <Select value={agent} onValueChange={setAgent}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AGENTS.map((a) => (
                    <SelectItem key={a.value} value={a.value}>
                      {a.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Base Branch</Label>
              <Input
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
              />
            </div>

            <div className="space-y-2">
              <Label>Task Prompt</Label>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what the AI agent should do..."
                rows={4}
                required
              />
              <p className="text-xs text-muted-foreground">
                You can use variables like {'{event}'}, {'{branch}'}, {'{author}'} in your prompt.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <Button variant="outline" asChild>
            <Link href="/dashboard/automations">Cancel</Link>
          </Button>
          <Button type="submit" disabled={loading || !name || !repository || !prompt}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Automation
          </Button>
        </div>
      </form>
    </div>
  );
}
