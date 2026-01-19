// ============================================================================
// PLAN LIMITS
// ============================================================================

export const PLAN_LIMITS = {
  FREE: {
    concurrentTasks: 1,
    monthlyCredits: 100,
    sandboxTimeout: 300, // 5 minutes
    sandboxCpu: 1,
    sandboxMemoryMb: 512,
    features: ['basic_agents', 'github_integration'],
  },
  CORE: {
    concurrentTasks: 3,
    monthlyCredits: 1000,
    sandboxTimeout: 1800, // 30 minutes
    sandboxCpu: 2,
    sandboxMemoryMb: 2048,
    features: ['basic_agents', 'github_integration', 'slack_integration', 'api_access'],
  },
  PRO: {
    concurrentTasks: 10,
    monthlyCredits: 5000,
    sandboxTimeout: 3600, // 1 hour
    sandboxCpu: 4,
    sandboxMemoryMb: 4096,
    features: ['all_agents', 'all_integrations', 'api_access', 'priority_queue', 'custom_agents'],
  },
  ENTERPRISE: {
    concurrentTasks: 50,
    monthlyCredits: -1, // Unlimited
    sandboxTimeout: 7200, // 2 hours
    sandboxCpu: 8,
    sandboxMemoryMb: 8192,
    features: ['all_agents', 'all_integrations', 'api_access', 'priority_queue', 'custom_agents', 'sso', 'audit_logs'],
  },
} as const;

// ============================================================================
// PRICING
// ============================================================================

export const PRICING = {
  FREE: {
    monthly: 0,
    yearly: 0,
    stripePriceId: null,
  },
  CORE: {
    monthly: 25,
    yearly: 250,
    stripePriceId: {
      monthly: 'price_core_monthly',
      yearly: 'price_core_yearly',
    },
  },
  PRO: {
    monthly: 50,
    yearly: 500,
    stripePriceId: {
      monthly: 'price_pro_monthly',
      yearly: 'price_pro_yearly',
    },
  },
  ENTERPRISE: {
    monthly: null, // Custom pricing
    yearly: null,
    stripePriceId: null,
  },
} as const;

// ============================================================================
// CREDIT COSTS
// ============================================================================

export const CREDIT_COSTS = {
  SANDBOX_MINUTE: 1,
  CLAUDE_TOKEN_1K: 0.1,
  OPENAI_TOKEN_1K: 0.05,
  GEMINI_TOKEN_1K: 0.02,
} as const;

// ============================================================================
// AGENT CONFIGURATIONS
// ============================================================================

export const AGENT_CONFIGS = {
  CLAUDE: {
    name: 'Claude Code',
    description: 'Anthropic\'s Claude with coding capabilities',
    models: ['claude-sonnet-4-20250514', 'claude-opus-4-5-20251101'],
    defaultModel: 'claude-sonnet-4-20250514',
    icon: '/agents/claude.svg',
  },
  OPENAI: {
    name: 'OpenAI GPT-4',
    description: 'OpenAI\'s GPT-4 with code generation',
    models: ['gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini'],
    defaultModel: 'gpt-4o',
    icon: '/agents/openai.svg',
  },
  GEMINI: {
    name: 'Google Gemini',
    description: 'Google\'s Gemini AI model',
    models: ['gemini-2.0-flash', 'gemini-1.5-pro'],
    defaultModel: 'gemini-2.0-flash',
    icon: '/agents/gemini.svg',
  },
  CUSTOM: {
    name: 'Custom Agent',
    description: 'Bring your own agent configuration',
    models: [],
    defaultModel: null,
    icon: '/agents/custom.svg',
  },
} as const;

// ============================================================================
// TASK STATUS CONFIGS
// ============================================================================

export const TASK_STATUS_CONFIG = {
  PENDING: {
    label: 'Pending',
    color: 'gray',
    description: 'Task is waiting to be queued',
  },
  QUEUED: {
    label: 'Queued',
    color: 'yellow',
    description: 'Task is in the queue waiting to run',
  },
  RUNNING: {
    label: 'Running',
    color: 'blue',
    description: 'Task is currently being executed',
  },
  COMPLETED: {
    label: 'Completed',
    color: 'green',
    description: 'Task completed successfully',
  },
  FAILED: {
    label: 'Failed',
    color: 'red',
    description: 'Task failed to complete',
  },
  CANCELLED: {
    label: 'Cancelled',
    color: 'gray',
    description: 'Task was cancelled',
  },
} as const;

// ============================================================================
// API ENDPOINTS
// ============================================================================

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/auth/login',
    LOGOUT: '/api/auth/logout',
    REGISTER: '/api/auth/register',
    ME: '/api/auth/me',
    GITHUB: '/api/auth/github',
  },
  TASKS: {
    LIST: '/api/tasks',
    CREATE: '/api/tasks',
    GET: (id: string) => `/api/tasks/${id}`,
    UPDATE: (id: string) => `/api/tasks/${id}`,
    DELETE: (id: string) => `/api/tasks/${id}`,
    CANCEL: (id: string) => `/api/tasks/${id}/cancel`,
    LOGS: (id: string) => `/api/tasks/${id}/logs`,
  },
  INTEGRATIONS: {
    LIST: '/api/integrations',
    GITHUB: '/api/integrations/github',
    SLACK: '/api/integrations/slack',
    REPOS: '/api/integrations/github/repos',
  },
  BILLING: {
    SUBSCRIPTION: '/api/billing/subscription',
    CREDITS: '/api/billing/credits',
    INVOICES: '/api/billing/invoices',
  },
} as const;

// ============================================================================
// WEBSOCKET EVENTS
// ============================================================================

export const WS_EVENTS = {
  TASK_STARTED: 'TASK_STARTED',
  TASK_PROGRESS: 'TASK_PROGRESS',
  TASK_COMPLETED: 'TASK_COMPLETED',
  TASK_FAILED: 'TASK_FAILED',
  LOG: 'LOG',
  SANDBOX_READY: 'SANDBOX_READY',
  SANDBOX_TERMINATED: 'SANDBOX_TERMINATED',
} as const;
