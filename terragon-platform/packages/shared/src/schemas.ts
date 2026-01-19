import { z } from 'zod';

// ============================================================================
// AUTH SCHEMAS
// ============================================================================

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

// ============================================================================
// TASK SCHEMAS
// ============================================================================

export const createTaskSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200, 'Title too long'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  repoUrl: z.string().url('Invalid repository URL').regex(
    /^https:\/\/github\.com\/[\w-]+\/[\w.-]+$/,
    'Must be a valid GitHub repository URL'
  ),
  repoBranch: z.string().default('main'),
  agentType: z.enum(['CLAUDE', 'OPENAI', 'GEMINI', 'CUSTOM']).default('CLAUDE'),
  agentConfig: z.object({
    model: z.string().optional(),
    apiKey: z.string().optional(),
    maxTokens: z.number().optional(),
    temperature: z.number().min(0).max(2).optional(),
    timeout: z.number().min(60).max(3600).optional(),
    customInstructions: z.string().optional(),
  }).optional(),
  organizationId: z.string().optional(),
});

export const updateTaskSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  description: z.string().min(10).optional(),
  status: z.enum(['PENDING', 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED']).optional(),
});

export const taskQuerySchema = z.object({
  status: z.enum(['PENDING', 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED']).optional(),
  agentType: z.enum(['CLAUDE', 'OPENAI', 'GEMINI', 'CUSTOM']).optional(),
  page: z.coerce.number().min(1).default(1),
  pageSize: z.coerce.number().min(1).max(100).default(20),
  sortBy: z.enum(['createdAt', 'updatedAt', 'status']).default('createdAt'),
  sortOrder: z.enum(['asc', 'desc']).default('desc'),
});

// ============================================================================
// INTEGRATION SCHEMAS
// ============================================================================

export const githubIntegrationSchema = z.object({
  accessToken: z.string().min(1, 'Access token is required'),
});

export const slackIntegrationSchema = z.object({
  webhookUrl: z.string().url('Invalid webhook URL'),
  channel: z.string().optional(),
});

// ============================================================================
// API KEY SCHEMAS
// ============================================================================

export const createApiKeySchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  expiresAt: z.coerce.date().optional(),
});

// ============================================================================
// AUTOMATION SCHEMAS
// ============================================================================

export const createAutomationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  description: z.string().optional(),
  trigger: z.enum(['SCHEDULE', 'WEBHOOK', 'GITHUB_ISSUE', 'SLACK_MESSAGE', 'LINEAR_ISSUE']),
  triggerConfig: z.object({
    cron: z.string().optional(),
    webhookSecret: z.string().optional(),
    eventTypes: z.array(z.string()).optional(),
  }).optional(),
  taskTemplate: z.object({
    title: z.string(),
    description: z.string(),
    repoUrl: z.string().url(),
    agentType: z.enum(['CLAUDE', 'OPENAI', 'GEMINI', 'CUSTOM']),
  }),
});

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type CreateTaskInput = z.infer<typeof createTaskSchema>;
export type UpdateTaskInput = z.infer<typeof updateTaskSchema>;
export type TaskQueryInput = z.infer<typeof taskQuerySchema>;
export type CreateApiKeyInput = z.infer<typeof createApiKeySchema>;
export type CreateAutomationInput = z.infer<typeof createAutomationSchema>;
