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
  Switch,
  Skeleton,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Separator,
} from '@terragon/ui';
import {
  User,
  Bell,
  Shield,
  Palette,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { signOut } from 'next-auth/react';

interface UserSettings {
  defaultAgent?: string;
  theme?: 'light' | 'dark' | 'system';
  notifications?: {
    email?: boolean;
    slack?: boolean;
    taskStarted?: boolean;
    taskCompleted?: boolean;
    taskFailed?: boolean;
    weeklyDigest?: boolean;
    creditsLow?: boolean;
  };
}

interface UserData {
  id: string;
  email: string;
  name: string | null;
  avatarUrl: string | null;
  plan: string;
  credits: number;
  settings: UserSettings | null;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2, 3].map((i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

const AGENTS = [
  { value: 'claude', label: 'Claude Code' },
  { value: 'openai', label: 'OpenAI Codex' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'amp', label: 'Amp' },
  { value: 'opencode', label: 'OpenCode' },
];

export default function SettingsPage() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // User data
  const [user, setUser] = useState<UserData | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [defaultAgent, setDefaultAgent] = useState('claude');
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');

  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [slackNotifications, setSlackNotifications] = useState(true);
  const [notifyTaskStarted, setNotifyTaskStarted] = useState(false);
  const [notifyTaskCompleted, setNotifyTaskCompleted] = useState(true);
  const [notifyTaskFailed, setNotifyTaskFailed] = useState(true);
  const [notifyWeeklyDigest, setNotifyWeeklyDigest] = useState(true);
  const [notifyCreditsLow, setNotifyCreditsLow] = useState(true);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadSettings();
    }
  }, [session]);

  async function loadSettings() {
    try {
      setLoading(true);
      setError(null);

      const userData = await api.getMe();
      setUser(userData as UserData);

      // Initialize form with user data
      setName(userData.name || '');

      // Load settings with defaults
      const settings = (userData as UserData).settings || {};
      setDefaultAgent(settings.defaultAgent || 'claude');
      setTheme(settings.theme || 'system');

      const notifications = settings.notifications || {};
      setEmailNotifications(notifications.email ?? true);
      setSlackNotifications(notifications.slack ?? true);
      setNotifyTaskStarted(notifications.taskStarted ?? false);
      setNotifyTaskCompleted(notifications.taskCompleted ?? true);
      setNotifyTaskFailed(notifications.taskFailed ?? true);
      setNotifyWeeklyDigest(notifications.weeklyDigest ?? true);
      setNotifyCreditsLow(notifications.creditsLow ?? true);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    try {
      setSaving(true);
      setError(null);

      await api.updateUserSettings({
        name,
        notifications: {
          email: emailNotifications,
          slack: slackNotifications,
          taskCompleted: notifyTaskCompleted,
          taskFailed: notifyTaskFailed,
        },
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  async function handleSignOut() {
    await signOut({ callbackUrl: '/' });
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Manage your account settings and preferences.</p>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Manage your account settings and preferences.</p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : saved ? (
            <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={loadSettings} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Profile Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5" />
            <CardTitle>Profile</CardTitle>
          </div>
          <CardDescription>Your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            {user?.avatarUrl && (
              <img
                src={user.avatarUrl}
                alt={user.name || 'Avatar'}
                className="h-16 w-16 rounded-full"
              />
            )}
            <div>
              <p className="font-medium">{user?.name || 'Anonymous'}</p>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="name">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={user?.email || ''} disabled />
            <p className="text-xs text-muted-foreground">
              Email is linked to your GitHub account and cannot be changed here.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            <CardTitle>Preferences</CardTitle>
          </div>
          <CardDescription>Customize your experience</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Default AI Agent</Label>
            <Select value={defaultAgent} onValueChange={setDefaultAgent}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AGENTS.map((agent) => (
                  <SelectItem key={agent.value} value={agent.value}>
                    {agent.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              The default agent to use when creating new tasks
            </p>
          </div>

          <div className="space-y-2">
            <Label>Theme</Label>
            <Select value={theme} onValueChange={(v) => setTheme(v as typeof theme)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="dark">Dark</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            <CardTitle>Notifications</CardTitle>
          </div>
          <CardDescription>Configure how you want to be notified</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Notification Channels</h4>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-muted-foreground">Receive notifications via email</p>
              </div>
              <Switch
                checked={emailNotifications}
                onCheckedChange={setEmailNotifications}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Slack Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Receive notifications in Slack (requires integration)
                </p>
              </div>
              <Switch
                checked={slackNotifications}
                onCheckedChange={setSlackNotifications}
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h4 className="text-sm font-medium">Task Notifications</h4>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Task Started</p>
                <p className="text-sm text-muted-foreground">
                  Notify when a task starts execution
                </p>
              </div>
              <Switch
                checked={notifyTaskStarted}
                onCheckedChange={setNotifyTaskStarted}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Task Completed</p>
                <p className="text-sm text-muted-foreground">
                  Notify when a task completes successfully
                </p>
              </div>
              <Switch
                checked={notifyTaskCompleted}
                onCheckedChange={setNotifyTaskCompleted}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Task Failed</p>
                <p className="text-sm text-muted-foreground">
                  Notify when a task fails
                </p>
              </div>
              <Switch
                checked={notifyTaskFailed}
                onCheckedChange={setNotifyTaskFailed}
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h4 className="text-sm font-medium">Other Notifications</h4>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Weekly Digest</p>
                <p className="text-sm text-muted-foreground">
                  Receive a weekly summary of your activity
                </p>
              </div>
              <Switch
                checked={notifyWeeklyDigest}
                onCheckedChange={setNotifyWeeklyDigest}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Low Credits Warning</p>
                <p className="text-sm text-muted-foreground">
                  Notify when credits are running low
                </p>
              </div>
              <Switch
                checked={notifyCreditsLow}
                onCheckedChange={setNotifyCreditsLow}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-destructive" />
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
          </div>
          <CardDescription>Irreversible account actions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Sign Out</p>
              <p className="text-sm text-muted-foreground">Sign out of your account</p>
            </div>
            <Button variant="outline" onClick={handleSignOut}>
              Sign Out
            </Button>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Delete Account</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete your account and all data
              </p>
            </div>
            <Button variant="destructive" disabled>
              Delete Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
