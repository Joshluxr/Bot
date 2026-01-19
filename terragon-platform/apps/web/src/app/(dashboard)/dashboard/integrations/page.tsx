'use client';

import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Input,
  Label,
  Badge,
  Skeleton,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@terragon/ui';
import {
  Plug,
  Check,
  X,
  ExternalLink,
  AlertCircle,
  Loader2,
  MessageSquare,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';

interface Integration {
  id: string;
  type: string;
  name: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

const INTEGRATIONS = [
  {
    id: 'github',
    name: 'GitHub',
    description: 'Connect your GitHub repositories to create tasks and PRs',
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
      </svg>
    ),
    authType: 'oauth',
    connectUrl: '/api/auth/github',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Receive task notifications and trigger automations from Slack',
    icon: <MessageSquare className="h-8 w-8" />,
    authType: 'webhook',
  },
  {
    id: 'linear',
    name: 'Linear',
    description: 'Sync tasks with Linear issues',
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M1.04 11.28c-.17.3-.04.68.27.84l10.02 5.78c.3.17.68.04.84-.27l.64-1.12c.17-.3.04-.68-.27-.84L2.52 9.89c-.3-.17-.68-.04-.84.27l-.64 1.12zm.71 3.01c-.17.3-.04.68.27.84l7.08 4.08c.3.17.68.04.84-.27l.64-1.12c-.17-.3-.04-.68-.27-.84l-7.08-4.08c-.3-.17-.68-.04-.84.27l-.64 1.12zm21.21-2.01l-10.02-5.78c-.3-.17-.68-.04-.84.27l-.64 1.12c-.17.3-.04.68.27.84l10.02 5.78c.3.17.68.04.84-.27l.64-1.12c.17-.3.04-.68-.27-.84zm-.71-3.01l-7.08-4.08c-.3-.17-.68-.04-.84.27l-.64 1.12c-.17.3-.04.68.27.84l7.08 4.08c.3.17.68.04.84-.27l.64-1.12c.17-.3.04-.68-.27-.84z" />
      </svg>
    ),
    authType: 'oauth',
    comingSoon: true,
  },
  {
    id: 'jira',
    name: 'Jira',
    description: 'Sync tasks with Jira issues',
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M11.571 11.513H0a5.218 5.218 0 005.232 5.215h2.13v2.057A5.215 5.215 0 0012.575 24V12.518a1.005 1.005 0 00-1.004-1.005zm5.723-5.756H5.736a5.215 5.215 0 005.215 5.214h2.129v2.058a5.218 5.218 0 005.215 5.214V6.758a1.001 1.001 0 00-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 005.215 5.215h2.129v2.057A5.215 5.215 0 0024 12.483V1.005A1.005 1.005 0 0023.013 0z" />
      </svg>
    ),
    authType: 'oauth',
    comingSoon: true,
  },
];

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardContent className="flex items-start gap-4 p-6">
            <Skeleton className="h-12 w-12 rounded-lg" />
            <div className="flex-1">
              <Skeleton className="h-5 w-24 mb-2" />
              <Skeleton className="h-4 w-full mb-4" />
              <Skeleton className="h-9 w-24" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function IntegrationsPage() {
  const { data: session } = useSession();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Slack dialog
  const [showSlackDialog, setShowSlackDialog] = useState(false);
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('');
  const [slackChannel, setSlackChannel] = useState('');
  const [connectingSlack, setConnectingSlack] = useState(false);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadIntegrations();
    }
  }, [session]);

  async function loadIntegrations() {
    try {
      setLoading(true);
      setError(null);
      // The API returns integrations directly
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000'}/api/integrations`,
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );
      const data = await response.json();
      setIntegrations(data.data || []);
    } catch (err) {
      console.error('Failed to load integrations:', err);
      setError(err instanceof Error ? err.message : 'Failed to load integrations');
    } finally {
      setLoading(false);
    }
  }

  function isConnected(type: string): boolean {
    return integrations.some((i) => i.type === type.toUpperCase() && i.isActive);
  }

  async function handleConnectSlack() {
    if (!slackWebhookUrl) return;

    try {
      setConnectingSlack(true);
      await api.connectSlack(slackWebhookUrl, slackChannel || undefined);
      setShowSlackDialog(false);
      setSlackWebhookUrl('');
      setSlackChannel('');
      loadIntegrations();
    } catch (err) {
      console.error('Failed to connect Slack:', err);
    } finally {
      setConnectingSlack(false);
    }
  }

  function handleConnect(integration: (typeof INTEGRATIONS)[0]) {
    if (integration.comingSoon) return;

    if (integration.id === 'slack') {
      setShowSlackDialog(true);
    } else if (integration.authType === 'oauth' && integration.connectUrl) {
      // For OAuth integrations, redirect to the auth URL
      window.location.href = integration.connectUrl;
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="text-muted-foreground">
          Connect external services to enhance your workflow.
        </p>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error loading integrations</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={loadIntegrations} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Integrations Grid */}
      {loading ? (
        <LoadingSkeleton />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {INTEGRATIONS.map((integration) => {
            const connected = isConnected(integration.id);

            return (
              <Card key={integration.id} className={integration.comingSoon ? 'opacity-60' : ''}>
                <CardContent className="flex items-start gap-4 p-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                    {integration.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold">{integration.name}</h3>
                      {integration.comingSoon && (
                        <Badge variant="secondary">Coming Soon</Badge>
                      )}
                      {connected && (
                        <Badge variant="default" className="bg-green-500">
                          <Check className="mr-1 h-3 w-3" />
                          Connected
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      {integration.description}
                    </p>
                    {integration.comingSoon ? (
                      <Button variant="outline" disabled>
                        Coming Soon
                      </Button>
                    ) : connected ? (
                      <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm">
                          Configure
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive">
                          Disconnect
                        </Button>
                      </div>
                    ) : (
                      <Button onClick={() => handleConnect(integration)}>
                        <Plug className="mr-2 h-4 w-4" />
                        Connect
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* GitHub Connected Info */}
      {isConnected('github') && (
        <Card>
          <CardHeader>
            <CardTitle>GitHub Connection</CardTitle>
            <CardDescription>Your GitHub account is connected via OAuth</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              You signed in with GitHub, so your repositories are automatically available.
              Terragon can access your repositories to create tasks and pull requests.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Slack Dialog */}
      <Dialog open={showSlackDialog} onOpenChange={setShowSlackDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect Slack</DialogTitle>
            <DialogDescription>
              Enter your Slack webhook URL to receive notifications.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="webhookUrl">Webhook URL</Label>
              <Input
                id="webhookUrl"
                placeholder="https://hooks.slack.com/services/..."
                value={slackWebhookUrl}
                onChange={(e) => setSlackWebhookUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Create an incoming webhook in your Slack workspace settings.{' '}
                <a
                  href="https://api.slack.com/messaging/webhooks"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  Learn more
                  <ExternalLink className="inline ml-1 h-3 w-3" />
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="channel">Channel (optional)</Label>
              <Input
                id="channel"
                placeholder="#general"
                value={slackChannel}
                onChange={(e) => setSlackChannel(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Override the default channel configured in the webhook.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSlackDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleConnectSlack} disabled={connectingSlack || !slackWebhookUrl}>
              {connectingSlack && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Connect Slack
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
