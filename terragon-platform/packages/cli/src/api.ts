import { getApiToken, getApiUrl } from './config.js';

export interface Task {
  id: string;
  title: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'paused';
  repository: {
    owner: string;
    name: string;
    fullName: string;
  };
  branch: string;
  agent: string;
  progress?: number;
  prUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskInput {
  repository: string;
  prompt: string;
  agent?: string;
  branch?: string;
}

export interface ApiError {
  message: string;
  code: string;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getApiToken();
  if (!token) {
    throw new Error('Not authenticated. Run `terry login` first.');
  }

  const url = `${getApiUrl()}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = (await response.json()) as ApiError;
    throw new Error(error.message || `API error: ${response.status}`);
  }

  return response.json();
}

export async function listTasks(options: {
  status?: string;
  repo?: string;
  limit?: number;
}): Promise<Task[]> {
  const params = new URLSearchParams();
  if (options.status) params.set('status', options.status);
  if (options.repo) params.set('repo', options.repo);
  if (options.limit) params.set('limit', String(options.limit));

  return apiRequest<Task[]>(`/tasks?${params.toString()}`);
}

export async function getTask(taskId: string): Promise<Task> {
  return apiRequest<Task>(`/tasks/${taskId}`);
}

export async function createTask(input: CreateTaskInput): Promise<Task> {
  return apiRequest<Task>('/tasks', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function pullTask(taskId: string): Promise<{
  branch: string;
  commitHash: string;
  files: string[];
}> {
  return apiRequest(`/tasks/${taskId}/pull`, {
    method: 'POST',
  });
}

export async function pushTask(
  taskId: string,
  changes: { message: string; patch: string }
): Promise<{ commitHash: string }> {
  return apiRequest(`/tasks/${taskId}/push`, {
    method: 'POST',
    body: JSON.stringify(changes),
  });
}

export async function watchTask(
  taskId: string,
  onUpdate: (data: unknown) => void
): Promise<() => void> {
  const token = getApiToken();
  if (!token) {
    throw new Error('Not authenticated. Run `terry login` first.');
  }

  const wsUrl = getApiUrl().replace('https://', 'wss://').replace('http://', 'ws://');
  const ws = new WebSocket(`${wsUrl}/tasks/${taskId}/stream?token=${token}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  };

  return () => ws.close();
}
