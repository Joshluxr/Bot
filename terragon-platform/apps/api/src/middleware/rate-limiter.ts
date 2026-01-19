import { Request, Response, NextFunction } from 'express';
import { Redis } from 'ioredis';
import { TooManyRequestsError } from './error-handler';

const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

const defaultConfig: RateLimitConfig = {
  windowMs: 60 * 1000, // 1 minute
  maxRequests: 100, // 100 requests per minute
};

const planLimits: Record<string, RateLimitConfig> = {
  FREE: { windowMs: 60 * 1000, maxRequests: 30 },
  CORE: { windowMs: 60 * 1000, maxRequests: 100 },
  PRO: { windowMs: 60 * 1000, maxRequests: 300 },
  ENTERPRISE: { windowMs: 60 * 1000, maxRequests: 1000 },
};

export async function rateLimiter(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    // Get user identifier (user ID or IP)
    const userId = (req as any).user?.id;
    const identifier = userId || req.ip || 'anonymous';
    const plan = (req as any).user?.plan || 'FREE';

    const config = planLimits[plan] || defaultConfig;
    const key = `ratelimit:${identifier}`;
    const now = Date.now();
    const windowStart = now - config.windowMs;

    // Remove old entries
    await redis.zremrangebyscore(key, 0, windowStart);

    // Count requests in window
    const requestCount = await redis.zcard(key);

    if (requestCount >= config.maxRequests) {
      const oldestRequest = await redis.zrange(key, 0, 0, 'WITHSCORES');
      const resetTime = oldestRequest.length > 1
        ? parseInt(oldestRequest[1]) + config.windowMs
        : now + config.windowMs;

      res.setHeader('X-RateLimit-Limit', config.maxRequests.toString());
      res.setHeader('X-RateLimit-Remaining', '0');
      res.setHeader('X-RateLimit-Reset', Math.ceil(resetTime / 1000).toString());

      throw new TooManyRequestsError('Rate limit exceeded');
    }

    // Add current request
    await redis.zadd(key, now, `${now}-${Math.random()}`);
    await redis.expire(key, Math.ceil(config.windowMs / 1000));

    // Set rate limit headers
    res.setHeader('X-RateLimit-Limit', config.maxRequests.toString());
    res.setHeader('X-RateLimit-Remaining', (config.maxRequests - requestCount - 1).toString());

    next();
  } catch (error) {
    if (error instanceof TooManyRequestsError) {
      return next(error);
    }
    // If Redis fails, allow the request but log the error
    console.error('Rate limiter error:', error);
    next();
  }
}
