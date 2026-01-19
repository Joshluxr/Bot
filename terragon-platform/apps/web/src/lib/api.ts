import { ApiResponse, Task, User, PaginatedResponse, GitHubRepo } from '@terragon/shared';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

// Automation types
export interface Automation {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  trigger: AutomationTrigger;
  task: AutomationTask;
  lastRunAt: string | null;
  runCount: number;
  createdAt: string;
  updatedAt: string;
}

export type AutomationTrigger =
  | { type: 'schedule'; cron: string; timezone?: string }
  | { type: 'github'; events: string[]; branches?: string[]; paths?: string[] }
  | { type: 'slack'; channel?: string; keywords?: string[]; mentionOnly?: boolean }
  | { type: 'webhook'; secret?: string };

export interface AutomationTask {
  repository: string;
  prompt: string;
  agent: string;
  branch?: string;
}

export interface AutomationRun {
  id: string;
  automationId: string;
  taskId: string | null;
  triggeredBy: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
}

// API Key types
export interface ApiKey {
  id: string;
  name: string;
  key: string; // Masked key like "trg_abc1...xyz9"
  prefix: string; // Alias for backwards compatibility
  lastUsed: string | null;
  lastUsedAt: string | null; // Alias
  expiresAt: string | null;
  createdAt: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error?.message || 'Request failed');
    }

    return data;
  }

  // Auth
  async getMe(): Promise<User> {
    const response = await this.request<User>('/api/auth/me');
    return response.data!;
  }

  // Tasks
  async getTasks(params?: {
    status?: string;
    agentType?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PaginatedResponse<Task>> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.agentType) searchParams.set('agentType', params.agentType);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.pageSize) searchParams.set('pageSize', params.pageSize.toString());

    const response = await this.request<PaginatedResponse<Task>>(
      `/api/tasks?${searchParams.toString()}`
    );
    return response.data!;
  }

  async getTask(id: string): Promise<Task> {
    const response = await this.request<Task>(`/api/tasks/${id}`);
    return response.data!;
  }

  async createTask(data: {
    title: string;
    description: string;
    repoUrl: string;
    repoBranch?: string;
    agentType?: string;
  }): Promise<Task> {
    const response = await this.request<Task>('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data!;
  }

  async cancelTask(id: string): Promise<void> {
    await this.request(`/api/tasks/${id}/cancel`, { method: 'POST' });
  }

  async retryTask(id: string): Promise<void> {
    await this.request(`/api/tasks/${id}/retry`, { method: 'POST' });
  }

  async getTaskStats(): Promise<{
    stats: {
      tasksThisMonth: number;
      completed: number;
      successRate: string;
      creditsUsed: number;
    };
    recentTasks: Array<{
      id: string;
      title: string;
      status: string;
      repo: string;
      repoUrl: string;
      createdAt: string;
      pullRequestUrl: string | null;
      errorMessage: string | null;
    }>;
  }> {
    const response = await this.request<{
      stats: {
        tasksThisMonth: number;
        completed: number;
        successRate: string;
        creditsUsed: number;
      };
      recentTasks: Array<{
        id: string;
        title: string;
        status: string;
        repo: string;
        repoUrl: string;
        createdAt: string;
        pullRequestUrl: string | null;
        errorMessage: string | null;
      }>;
    }>('/api/tasks/stats');
    return response.data!;
  }

  async getTaskLogs(taskId: string, cursor?: string): Promise<{
    logs: Array<{
      id: string;
      timestamp: string;
      level: string;
      message: string;
    }>;
    nextCursor: string | null;
  }> {
    const params = new URLSearchParams();
    if (cursor) params.set('cursor', cursor);
    const response = await this.request<{
      logs: Array<{
        id: string;
        timestamp: string;
        level: string;
        message: string;
      }>;
      nextCursor: string | null;
    }>(`/api/tasks/${taskId}/logs?${params.toString()}`);
    return response.data!;
  }

  // Integrations
  async getGitHubRepos(): Promise<GitHubRepo[]> {
    const response = await this.request<GitHubRepo[]>('/api/integrations/github/repos');
    return response.data!;
  }

  async connectSlack(webhookUrl: string, channel?: string): Promise<void> {
    await this.request('/api/integrations/slack', {
      method: 'POST',
      body: JSON.stringify({ webhookUrl, channel }),
    });
  }

  // Billing
  async getSubscription(): Promise<{
    plan: string;
    credits: number;
    subscription: {
      status: string;
      currentPeriodEnd: string;
      cancelAtPeriodEnd: boolean;
    } | null;
  }> {
    const response = await this.request<any>('/api/billing/subscription');
    return response.data!;
  }

  async createCheckoutSession(plan: string, interval: 'monthly' | 'yearly'): Promise<string> {
    const response = await this.request<{ url: string }>('/api/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan, interval }),
    });
    return response.data!.url;
  }

  async createPortalSession(): Promise<string> {
    const response = await this.request<{ url: string }>('/api/billing/portal', {
      method: 'POST',
    });
    return response.data!.url;
  }

  // Automations
  async getAutomations(): Promise<Automation[]> {
    const response = await this.request<{ automations: Automation[] }>('/api/automations');
    return response.data?.automations || [];
  }

  async getAutomation(id: string): Promise<Automation> {
    const response = await this.request<{ automation: Automation }>(`/api/automations/${id}`);
    return response.data!.automation;
  }

  async createAutomation(data: {
    name: string;
    description?: string;
    enabled?: boolean;
    trigger: AutomationTrigger;
    task: AutomationTask;
  }): Promise<Automation> {
    const response = await this.request<{ automation: Automation }>('/api/automations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    return response.data!.automation;
  }

  async updateAutomation(id: string, data: Partial<{
    name: string;
    description: string;
    enabled: boolean;
    trigger: AutomationTrigger;
    task: AutomationTask;
  }>): Promise<Automation> {
    const response = await this.request<{ automation: Automation }>(`/api/automations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return response.data!.automation;
  }

  async deleteAutomation(id: string): Promise<void> {
    await this.request(`/api/automations/${id}`, { method: 'DELETE' });
  }

  async enableAutomation(id: string): Promise<Automation> {
    const response = await this.request<{ automation: Automation }>(`/api/automations/${id}/enable`, {
      method: 'POST',
    });
    return response.data!.automation;
  }

  async disableAutomation(id: string): Promise<Automation> {
    const response = await this.request<{ automation: Automation }>(`/api/automations/${id}/disable`, {
      method: 'POST',
    });
    return response.data!.automation;
  }

  async triggerAutomation(id: string): Promise<AutomationRun> {
    const response = await this.request<{ run: AutomationRun }>(`/api/automations/${id}/trigger`, {
      method: 'POST',
    });
    return response.data!.run;
  }

  async getAutomationRuns(id: string, limit?: number): Promise<AutomationRun[]> {
    const params = new URLSearchParams();
    if (limit) params.set('limit', limit.toString());
    const response = await this.request<{ runs: AutomationRun[] }>(
      `/api/automations/${id}/runs?${params.toString()}`
    );
    return response.data?.runs || [];
  }

  // API Keys
  async getApiKeys(): Promise<ApiKey[]> {
    const response = await this.request<ApiKey[]>('/api/auth/api-keys');
    return response.data || [];
  }

  async createApiKey(data: { name: string; expiresIn?: number }): Promise<{ apiKey: ApiKey; token: string }> {
    const response = await this.request<{ id: string; name: string; key: string; expiresAt: string | null; createdAt: string }>('/api/auth/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    const apiKeyData = response.data!;
    return {
      apiKey: {
        id: apiKeyData.id,
        name: apiKeyData.name,
        key: apiKeyData.key.slice(0, 8) + '...' + apiKeyData.key.slice(-4),
        prefix: apiKeyData.key.slice(0, 8),
        lastUsed: null,
        lastUsedAt: null,
        expiresAt: apiKeyData.expiresAt,
        createdAt: apiKeyData.createdAt,
      },
      token: apiKeyData.key,
    };
  }

  async deleteApiKey(id: string): Promise<void> {
    await this.request(`/api/auth/api-keys/${id}`, { method: 'DELETE' });
  }

  // User Settings
  async updateUserSettings(data: {
    name?: string;
    defaultAgent?: string;
    notifications?: {
      email?: boolean;
      slack?: boolean;
      taskCompleted?: boolean;
      taskFailed?: boolean;
    };
  }): Promise<User> {
    const response = await this.request<User>('/api/auth/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    return response.data!;
  }
}

export const api = new ApiClient();
