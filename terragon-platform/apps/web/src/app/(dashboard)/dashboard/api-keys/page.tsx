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
  Plus,
  Key,
  Trash2,
  Copy,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react';
import { api, ApiKey } from '@/lib/api';
import { useSession } from 'next-auth/react';

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between p-4 rounded-lg border">
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div>
              <Skeleton className="h-5 w-32 mb-2" />
              <Skeleton className="h-4 w-48" />
            </div>
          </div>
          <Skeleton className="h-8 w-8" />
        </div>
      ))}
    </div>
  );
}

export default function ApiKeysPage() {
  const { data: session } = useSession();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpiry, setNewKeyExpiry] = useState<string>('');
  const [creating, setCreating] = useState(false);

  // Newly created key state
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<{ name: string; token: string } | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadApiKeys();
    }
  }, [session]);

  async function loadApiKeys() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getApiKeys();
      setApiKeys(data);
    } catch (err) {
      console.error('Failed to load API keys:', err);
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateKey() {
    if (!newKeyName.trim()) return;

    try {
      setCreating(true);
      const result = await api.createApiKey({
        name: newKeyName,
        expiresIn: newKeyExpiry ? parseInt(newKeyExpiry) : undefined,
      });
      setNewlyCreatedKey({ name: result.apiKey.name, token: result.token });
      setShowCreateDialog(false);
      setNewKeyName('');
      setNewKeyExpiry('');
      loadApiKeys();
    } catch (err) {
      console.error('Failed to create API key:', err);
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteKey(key: ApiKey) {
    if (!confirm(`Are you sure you want to delete the API key "${key.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.deleteApiKey(key.id);
      setApiKeys((prev) => prev.filter((k) => k.id !== key.id));
    } catch (err) {
      console.error('Failed to delete API key:', err);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground">
            Manage API keys for the Terry CLI and programmatic access.
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create API Key
        </Button>
      </div>

      {/* Newly Created Key Alert */}
      {newlyCreatedKey && (
        <Card className="border-green-500 bg-green-500/5">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <Key className="h-5 w-5 text-green-500" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-green-500">API Key Created</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Make sure to copy your API key now. You won&apos;t be able to see it again!
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-muted px-4 py-2 rounded-lg font-mono text-sm break-all">
                    {newlyCreatedKey.token}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(newlyCreatedKey.token)}
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setNewlyCreatedKey(null)}
              >
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error loading API keys</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={loadApiKeys} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* CLI Setup Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Using with Terry CLI</CardTitle>
          <CardDescription>
            Use your API key to authenticate the Terry CLI
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">1. Install the Terry CLI</p>
              <code className="block bg-muted px-4 py-2 rounded-lg font-mono text-sm">
                npm install -g @terragon/cli
              </code>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-2">2. Login with your API key</p>
              <code className="block bg-muted px-4 py-2 rounded-lg font-mono text-sm">
                terry login --token YOUR_API_KEY
              </code>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-2">3. Start creating tasks</p>
              <code className="block bg-muted px-4 py-2 rounded-lg font-mono text-sm">
                terry create --repo owner/repo --prompt &quot;Add a dark mode toggle&quot;
              </code>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* API Keys List */}
      <Card>
        <CardHeader>
          <CardTitle>Your API Keys</CardTitle>
          <CardDescription>
            {apiKeys.length} API key{apiKeys.length !== 1 ? 's' : ''} created
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <LoadingSkeleton />
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No API keys yet</p>
              <p className="text-sm">Create an API key to use with the Terry CLI</p>
              <Button className="mt-4" onClick={() => setShowCreateDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create API Key
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                      <Key className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium">{key.name}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <code className="font-mono">{key.key}</code>
                        <span>•</span>
                        <span>Created {formatDate(key.createdAt)}</span>
                        {key.lastUsedAt && (
                          <>
                            <span>•</span>
                            <span>Last used {formatDate(key.lastUsedAt)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {key.expiresAt && (
                      <Badge variant={new Date(key.expiresAt) < new Date() ? 'destructive' : 'secondary'}>
                        {new Date(key.expiresAt) < new Date() ? 'Expired' : `Expires ${formatDate(key.expiresAt)}`}
                      </Badge>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteKey(key)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>
              Create a new API key for CLI access or integrations.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Development, CI/CD"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A descriptive name to help you identify this key
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="expiry">Expiration (optional)</Label>
              <select
                id="expiry"
                value={newKeyExpiry}
                onChange={(e) => setNewKeyExpiry(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="">Never expires</option>
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
                <option value="365">1 year</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateKey} disabled={creating || !newKeyName.trim()}>
              {creating ? 'Creating...' : 'Create API Key'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
