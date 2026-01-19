import { ApiResponse, Task, User, PaginatedResponse, GitHubRepo } from '@terragon/shared';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

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
}

export const api = new ApiClient();
