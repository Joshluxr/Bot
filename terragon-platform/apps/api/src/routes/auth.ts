import { Router, Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { prisma } from '@terragon/database';
import { AuthenticatedRequest, authMiddleware } from '../middleware/auth';
import { BadRequestError } from '../middleware/error-handler';

const router = Router();

// Get current user
router.get('/me', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: {
        id: true,
        email: true,
        name: true,
        avatarUrl: true,
        plan: true,
        credits: true,
        createdAt: true,
      },
    });

    res.json({
      success: true,
      data: user,
    });
  } catch (error) {
    next(error);
  }
});

// Generate API key
router.post('/api-keys', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { name, expiresAt } = req.body;

    if (!name) {
      throw new BadRequestError('Name is required');
    }

    // Generate a random API key
    const key = `trg_${generateRandomString(32)}`;

    const apiKey = await prisma.apiKey.create({
      data: {
        name,
        key,
        userId: req.user!.id,
        expiresAt: expiresAt ? new Date(expiresAt) : null,
      },
    });

    res.json({
      success: true,
      data: {
        id: apiKey.id,
        name: apiKey.name,
        key: apiKey.key, // Only show full key on creation
        expiresAt: apiKey.expiresAt,
        createdAt: apiKey.createdAt,
      },
    });
  } catch (error) {
    next(error);
  }
});

// List API keys
router.get('/api-keys', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const apiKeys = await prisma.apiKey.findMany({
      where: { userId: req.user!.id },
      select: {
        id: true,
        name: true,
        key: true,
        lastUsed: true,
        expiresAt: true,
        createdAt: true,
      },
    });

    // Mask the keys
    const maskedKeys = apiKeys.map((k) => ({
      ...k,
      key: `${k.key.slice(0, 8)}...${k.key.slice(-4)}`,
    }));

    res.json({
      success: true,
      data: maskedKeys,
    });
  } catch (error) {
    next(error);
  }
});

// Delete API key
router.delete('/api-keys/:id', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    await prisma.apiKey.deleteMany({
      where: {
        id: req.params.id,
        userId: req.user!.id,
      },
    });

    res.json({
      success: true,
    });
  } catch (error) {
    next(error);
  }
});

// Get user settings
router.get('/settings', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: {
        id: true,
        email: true,
        name: true,
        avatarUrl: true,
        plan: true,
        credits: true,
        settings: true,
        createdAt: true,
      },
    });

    res.json({
      success: true,
      data: user,
    });
  } catch (error) {
    next(error);
  }
});

// Update user settings
router.patch('/settings', authMiddleware, async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { name, settings } = req.body;

    const updateData: any = {};

    if (name !== undefined) {
      updateData.name = name;
    }

    if (settings !== undefined) {
      // Merge with existing settings
      const currentUser = await prisma.user.findUnique({
        where: { id: req.user!.id },
        select: { settings: true },
      });

      updateData.settings = {
        ...(currentUser?.settings as object || {}),
        ...settings,
      };
    }

    const user = await prisma.user.update({
      where: { id: req.user!.id },
      data: updateData,
      select: {
        id: true,
        email: true,
        name: true,
        avatarUrl: true,
        plan: true,
        credits: true,
        settings: true,
        createdAt: true,
      },
    });

    res.json({
      success: true,
      data: user,
    });
  } catch (error) {
    next(error);
  }
});

// Exchange GitHub OAuth token for JWT
router.post('/github/callback', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { code } = req.body;

    if (!code) {
      throw new BadRequestError('Code is required');
    }

    // Exchange code for access token
    const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        client_id: process.env.GITHUB_CLIENT_ID,
        client_secret: process.env.GITHUB_CLIENT_SECRET,
        code,
      }),
    });

    const tokenData = await tokenResponse.json();

    if (tokenData.error) {
      throw new BadRequestError(tokenData.error_description || 'GitHub OAuth failed');
    }

    // Get user info from GitHub
    const userResponse = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
    });

    const githubUser = await userResponse.json();

    // Get user's email
    const emailResponse = await fetch('https://api.github.com/user/emails', {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
    });

    const emails = await emailResponse.json();
    const primaryEmail = emails.find((e: any) => e.primary)?.email || emails[0]?.email;

    // Find or create user
    let user = await prisma.user.findUnique({
      where: { githubId: githubUser.id.toString() },
    });

    if (!user) {
      user = await prisma.user.create({
        data: {
          email: primaryEmail,
          name: githubUser.name || githubUser.login,
          avatarUrl: githubUser.avatar_url,
          githubId: githubUser.id.toString(),
          githubToken: tokenData.access_token,
        },
      });
    } else {
      user = await prisma.user.update({
        where: { id: user.id },
        data: {
          githubToken: tokenData.access_token,
          avatarUrl: githubUser.avatar_url,
        },
      });
    }

    // Generate JWT
    const token = jwt.sign(
      { id: user.id, email: user.email },
      process.env.JWT_SECRET!,
      { expiresIn: '7d' }
    );

    res.json({
      success: true,
      data: {
        token,
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          avatarUrl: user.avatarUrl,
          plan: user.plan,
        },
      },
    });
  } catch (error) {
    next(error);
  }
});

function generateRandomString(length: number): string {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

export default router;
