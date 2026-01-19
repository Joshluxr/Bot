import { Router, Response, NextFunction } from 'express';
import { Octokit } from 'octokit';
import { prisma } from '@terragon/database';
import { AuthenticatedRequest } from '../middleware/auth';
import { BadRequestError, NotFoundError } from '../middleware/error-handler';

const router = Router();

// Get all integrations
router.get('/', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const integrations = await prisma.integration.findMany({
      where: { userId: req.user!.id },
      select: {
        id: true,
        type: true,
        name: true,
        isActive: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    res.json({
      success: true,
      data: integrations,
    });
  } catch (error) {
    next(error);
  }
});

// Get GitHub repositories
router.get('/github/repos', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: { githubToken: true },
    });

    if (!user?.githubToken) {
      throw new BadRequestError('GitHub not connected');
    }

    const octokit = new Octokit({ auth: user.githubToken });

    const { data: repos } = await octokit.rest.repos.listForAuthenticatedUser({
      sort: 'updated',
      per_page: 100,
    });

    const formattedRepos = repos.map((repo) => ({
      id: repo.id,
      name: repo.name,
      fullName: repo.full_name,
      private: repo.private,
      defaultBranch: repo.default_branch,
      url: repo.html_url,
      cloneUrl: repo.clone_url,
      description: repo.description,
      language: repo.language,
      updatedAt: repo.updated_at,
    }));

    res.json({
      success: true,
      data: formattedRepos,
    });
  } catch (error: any) {
    if (error.status === 401) {
      return next(new BadRequestError('GitHub token expired. Please reconnect.'));
    }
    next(error);
  }
});

// Get repository branches
router.get('/github/repos/:owner/:repo/branches', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { owner, repo } = req.params;

    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: { githubToken: true },
    });

    if (!user?.githubToken) {
      throw new BadRequestError('GitHub not connected');
    }

    const octokit = new Octokit({ auth: user.githubToken });

    const { data: branches } = await octokit.rest.repos.listBranches({
      owner,
      repo,
      per_page: 100,
    });

    res.json({
      success: true,
      data: branches.map((b) => ({
        name: b.name,
        protected: b.protected,
      })),
    });
  } catch (error) {
    next(error);
  }
});

// Connect Slack
router.post('/slack', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { webhookUrl, channel } = req.body;

    if (!webhookUrl) {
      throw new BadRequestError('Webhook URL is required');
    }

    // Validate webhook URL format
    if (!webhookUrl.startsWith('https://hooks.slack.com/')) {
      throw new BadRequestError('Invalid Slack webhook URL');
    }

    // Test the webhook
    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: 'Terragon integration connected successfully!',
        }),
      });

      if (!response.ok) {
        throw new Error('Webhook test failed');
      }
    } catch {
      throw new BadRequestError('Failed to verify Slack webhook');
    }

    // Save or update integration
    await prisma.integration.upsert({
      where: {
        userId_type: {
          userId: req.user!.id,
          type: 'SLACK',
        },
      },
      update: {
        accessToken: webhookUrl,
        config: { channel },
        isActive: true,
      },
      create: {
        userId: req.user!.id,
        type: 'SLACK',
        name: 'Slack',
        accessToken: webhookUrl,
        config: { channel },
      },
    });

    res.json({
      success: true,
      data: { message: 'Slack connected successfully' },
    });
  } catch (error) {
    next(error);
  }
});

// Disconnect integration
router.delete('/:type', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const type = req.params.type.toUpperCase();

    await prisma.integration.deleteMany({
      where: {
        userId: req.user!.id,
        type: type as any,
      },
    });

    res.json({
      success: true,
      data: { message: 'Integration disconnected' },
    });
  } catch (error) {
    next(error);
  }
});

// Toggle integration
router.patch('/:id/toggle', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const integration = await prisma.integration.findFirst({
      where: {
        id: req.params.id,
        userId: req.user!.id,
      },
    });

    if (!integration) {
      throw new NotFoundError('Integration not found');
    }

    await prisma.integration.update({
      where: { id: integration.id },
      data: { isActive: !integration.isActive },
    });

    res.json({
      success: true,
      data: { isActive: !integration.isActive },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
