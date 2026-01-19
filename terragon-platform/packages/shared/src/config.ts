/**
 * Centralized configuration for Terragon platform
 * All environment variables and configurable values should be defined here
 */

function requireEnv(key: string, defaultValue?: string): string {
  const value = process.env[key] || defaultValue;
  if (!value && !defaultValue) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value!;
}

function optionalEnv(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

function numberEnv(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  if (isNaN(parsed)) return defaultValue;
  return parsed;
}

function booleanEnv(key: string, defaultValue: boolean): boolean {
  const value = process.env[key];
  if (!value) return defaultValue;
  return value.toLowerCase() === 'true' || value === '1';
}

// Server configuration
export const serverConfig = {
  port: numberEnv('PORT', 3001),
  host: optionalEnv('HOST', '0.0.0.0'),
  nodeEnv: optionalEnv('NODE_ENV', 'development'),
  isDevelopment: optionalEnv('NODE_ENV', 'development') === 'development',
  isProduction: optionalEnv('NODE_ENV', 'development') === 'production',
};

// Database configuration
export const databaseConfig = {
  url: requireEnv('DATABASE_URL', 'postgresql://localhost:5432/terragon'),
};

// Redis configuration
export const redisConfig = {
  url: optionalEnv('REDIS_URL', 'redis://localhost:6379'),
};

// Authentication configuration
export const authConfig = {
  jwtSecret: requireEnv('JWT_SECRET', 'development-secret-change-in-production'),
  jwtExpiresIn: optionalEnv('JWT_EXPIRES_IN', '7d'),
  nextAuthSecret: requireEnv('NEXTAUTH_SECRET', 'development-secret-change-in-production'),
  nextAuthUrl: optionalEnv('NEXTAUTH_URL', 'http://localhost:3000'),
};

// GitHub configuration
export const githubConfig = {
  clientId: requireEnv('GITHUB_CLIENT_ID', ''),
  clientSecret: requireEnv('GITHUB_CLIENT_SECRET', ''),
};

// AI Provider configuration
export const aiConfig = {
  anthropic: {
    apiKey: optionalEnv('ANTHROPIC_API_KEY', ''),
    model: optionalEnv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
  },
  openai: {
    apiKey: optionalEnv('OPENAI_API_KEY', ''),
    model: optionalEnv('OPENAI_MODEL', 'gpt-4o'),
  },
  google: {
    apiKey: optionalEnv('GOOGLE_API_KEY', ''),
    model: optionalEnv('GOOGLE_MODEL', 'gemini-2.0-flash'),
  },
  defaults: {
    maxTokens: numberEnv('AI_MAX_TOKENS', 8192),
    temperature: parseFloat(optionalEnv('AI_TEMPERATURE', '0.7')),
    timeout: numberEnv('AI_TIMEOUT_SECONDS', 1800),
  },
};

// E2B Sandbox configuration
export const sandboxConfig = {
  apiKey: optionalEnv('E2B_API_KEY', ''),
  enabled: booleanEnv('E2B_ENABLED', true),
};

// Stripe configuration
export const stripeConfig = {
  secretKey: requireEnv('STRIPE_SECRET_KEY', ''),
  webhookSecret: requireEnv('STRIPE_WEBHOOK_SECRET', ''),
  prices: {
    core: optionalEnv('STRIPE_PRICE_CORE', ''),
    pro: optionalEnv('STRIPE_PRICE_PRO', ''),
  },
};

// Rate limiting configuration
export const rateLimitConfig = {
  free: numberEnv('RATE_LIMIT_FREE', 30),
  core: numberEnv('RATE_LIMIT_CORE', 100),
  pro: numberEnv('RATE_LIMIT_PRO', 300),
  enterprise: numberEnv('RATE_LIMIT_ENTERPRISE', 1000),
  windowMs: numberEnv('RATE_LIMIT_WINDOW_MS', 60000),
};

// Worker configuration
export const workerConfig = {
  concurrency: numberEnv('WORKER_CONCURRENCY', 5),
};

// Logging configuration
export const logConfig = {
  level: optionalEnv('LOG_LEVEL', 'info') as 'debug' | 'info' | 'warn' | 'error',
};

// Credit pricing
export const creditConfig = {
  pricePerCredit: numberEnv('CREDIT_PRICE_CENTS', 10), // $0.10 per credit
};

// Application URLs
export const urlConfig = {
  frontendUrl: optionalEnv('FRONTEND_URL', 'http://localhost:3000'),
  apiUrl: optionalEnv('API_URL', 'http://localhost:3001'),
};

// Export all configs
export const config = {
  server: serverConfig,
  database: databaseConfig,
  redis: redisConfig,
  auth: authConfig,
  github: githubConfig,
  ai: aiConfig,
  sandbox: sandboxConfig,
  stripe: stripeConfig,
  rateLimit: rateLimitConfig,
  worker: workerConfig,
  log: logConfig,
  credit: creditConfig,
  url: urlConfig,
};

export default config;
