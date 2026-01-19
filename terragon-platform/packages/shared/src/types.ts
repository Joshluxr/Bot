// ============================================================================
// USER TYPES
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string | null;
  avatarUrl: string | null;
  plan: Plan;
  credits: number;
  createdAt: Date;
}

export type Plan = 'FREE' | 'CORE' | 'PRO' | 'ENTERPRISE';

// ============================================================================
// TASK TYPES
// ============================================================================

export interface Task {
  id: string;
  userId: string;
  organizationId: string | null;
  title: string;
  description: string;
  repoUrl: string;
  repoBranch: string;
  targetBranch: string | null;
  agentType: AgentType;
  agentConfig: AgentConfig | null;
  status: TaskStatus;
  sandboxId: string | null;
  pullRequestUrl: string | null;
  errorMessage: string | null;
  creditsUsed: number;
  executionTime: number | null;
  createdAt: Date;
  startedAt: Date | null;
  completedAt: Date | null;
}

export type TaskStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type AgentType = 'CLAUDE' | 'OPENAI' | 'GEMINI' | 'CUSTOM';

export interface AgentConfig {
  model?: string;
  apiKey?: string;
  maxTokens?: number;
  temperature?: number;
  timeout?: number;
  customInstructions?: string;
}

export interface TaskLog {
  id: string;
  taskId: string;
  timestamp: Date;
  level: LogLevel;
  message: string;
  metadata?: Record<string, unknown>;
}

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

// ============================================================================
// SANDBOX TYPES
// ============================================================================

export interface Sandbox {
  id: string;
  taskId: string;
  status: SandboxStatus;
  url: string | null;
  startedAt: Date;
  terminatedAt: Date | null;
}

export type SandboxStatus = 'STARTING' | 'RUNNING' | 'STOPPING' | 'TERMINATED' | 'ERROR';

export interface SandboxConfig {
  cpu: number;
  memoryMb: number;
  timeoutSeconds: number;
  image?: string;
}

// ============================================================================
// INTEGRATION TYPES
// ============================================================================

export type IntegrationType = 'GITHUB' | 'SLACK' | 'LINEAR' | 'JIRA' | 'DISCORD';

export interface Integration {
  id: string;
  userId: string;
  type: IntegrationType;
  name: string;
  isActive: boolean;
  config?: Record<string, unknown>;
}

export interface GitHubRepo {
  id: number;
  name: string;
  fullName: string;
  private: boolean;
  defaultBranch: string;
  url: string;
  cloneUrl: string;
  description?: string | null;
  language?: string | null;
  updatedAt?: string;
}

// ============================================================================
// API TYPES
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ============================================================================
// WEBSOCKET TYPES
// ============================================================================

export type WebSocketEvent =
  | TaskStartedEvent
  | TaskProgressEvent
  | TaskCompletedEvent
  | TaskFailedEvent
  | LogEvent;

export interface TaskStartedEvent {
  type: 'TASK_STARTED';
  taskId: string;
  sandboxId: string;
  timestamp: Date;
}

export interface TaskProgressEvent {
  type: 'TASK_PROGRESS';
  taskId: string;
  progress: number;
  message: string;
  timestamp: Date;
}

export interface TaskCompletedEvent {
  type: 'TASK_COMPLETED';
  taskId: string;
  pullRequestUrl: string | null;
  executionTime: number;
  creditsUsed: number;
  timestamp: Date;
}

export interface TaskFailedEvent {
  type: 'TASK_FAILED';
  taskId: string;
  errorMessage: string;
  timestamp: Date;
}

export interface LogEvent {
  type: 'LOG';
  taskId: string;
  level: LogLevel;
  message: string;
  timestamp: Date;
}
