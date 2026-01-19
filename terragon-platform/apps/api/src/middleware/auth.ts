import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { prisma } from '@terragon/database';
import { UnauthorizedError } from './error-handler';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    plan: string;
  };
}

export async function authMiddleware(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
) {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      throw new UnauthorizedError('No authorization header');
    }

    // Check for Bearer token
    if (authHeader.startsWith('Bearer ')) {
      const token = authHeader.slice(7);

      // Verify JWT
      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as {
        id: string;
        email: string;
      };

      const user = await prisma.user.findUnique({
        where: { id: decoded.id },
        select: { id: true, email: true, plan: true },
      });

      if (!user) {
        throw new UnauthorizedError('User not found');
      }

      req.user = user;
      return next();
    }

    // Check for API key
    if (authHeader.startsWith('ApiKey ')) {
      const apiKey = authHeader.slice(7);

      const key = await prisma.apiKey.findUnique({
        where: { key: apiKey },
        include: {
          user: {
            select: { id: true, email: true, plan: true },
          },
        },
      });

      if (!key) {
        throw new UnauthorizedError('Invalid API key');
      }

      if (key.expiresAt && key.expiresAt < new Date()) {
        throw new UnauthorizedError('API key expired');
      }

      // Update last used
      await prisma.apiKey.update({
        where: { id: key.id },
        data: { lastUsed: new Date() },
      });

      req.user = key.user;
      return next();
    }

    throw new UnauthorizedError('Invalid authorization format');
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      return next(new UnauthorizedError('Invalid token'));
    }
    next(error);
  }
}

export function requirePlan(...plans: string[]) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new UnauthorizedError());
    }

    if (!plans.includes(req.user.plan)) {
      return res.status(403).json({
        success: false,
        error: {
          code: 'PLAN_REQUIRED',
          message: `This feature requires one of these plans: ${plans.join(', ')}`,
        },
      });
    }

    next();
  };
}
