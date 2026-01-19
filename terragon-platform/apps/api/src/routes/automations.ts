import { Router, Response } from 'express';
import { z } from 'zod';
import { automationsService } from '../services/automations';
import { AuthenticatedRequest } from '../middleware/auth';
import { logger } from '@terragon/shared';

const router = Router();

// Validation schemas
const scheduleTriggerSchema = z.object({
  type: z.literal('schedule'),
  cron: z.string(),
  timezone: z.string().optional(),
});

const githubTriggerSchema = z.object({
  type: z.literal('github'),
  events: z.array(z.enum(['push', 'pull_request', 'issue', 'release', 'issue_comment'])),
  branches: z.array(z.string()).optional(),
  paths: z.array(z.string()).optional(),
});

const slackTriggerSchema = z.object({
  type: z.literal('slack'),
  channel: z.string().optional(),
  keywords: z.array(z.string()).optional(),
  mentionOnly: z.boolean().optional(),
});

const webhookTriggerSchema = z.object({
  type: z.literal('webhook'),
  secret: z.string().optional(),
});

const triggerSchema = z.discriminatedUnion('type', [
  scheduleTriggerSchema,
  githubTriggerSchema,
  slackTriggerSchema,
  webhookTriggerSchema,
]);

const createAutomationSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  enabled: z.boolean().default(true),
  trigger: triggerSchema,
  task: z.object({
    repository: z.string(),
    prompt: z.string().min(10),
    agent: z.enum(['claude', 'openai', 'gemini', 'amp', 'opencode']),
    branch: z.string().optional(),
  }),
});

const updateAutomationSchema = createAutomationSchema.partial();

const log = logger.child('automations');

// List automations
router.get('/', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const automations = await automationsService.list(userId);
    res.json({ automations });
  } catch (error) {
    log.error('Error listing automations', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get single automation
router.get('/:id', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const automation = await automationsService.get(id);
    if (!automation) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (automation.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    res.json({ automation });
  } catch (error) {
    log.error('Error getting automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

type CreateAutomationInput = z.infer<typeof createAutomationSchema>;
type UpdateAutomationInput = z.infer<typeof updateAutomationSchema>;

// Create automation
router.post('/', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const userId = req.user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createAutomationSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation failed',
        details: validation.error.errors,
      });
    }

    const data: CreateAutomationInput = validation.data;
    const automation = await automationsService.create(userId, {
      name: data.name,
      description: data.description,
      enabled: data.enabled,
      trigger: data.trigger,
      task: data.task,
    });
    res.status(201).json({ automation });
  } catch (error) {
    log.error('Error creating automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update automation
router.patch('/:id', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    const validation = updateAutomationSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation failed',
        details: validation.error.errors,
      });
    }

    const data: UpdateAutomationInput = validation.data;
    const automation = await automationsService.update(id, data);
    res.json({ automation });
  } catch (error) {
    log.error('Error updating automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete automation
router.delete('/:id', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    await automationsService.delete(id);
    res.status(204).send();
  } catch (error) {
    log.error('Error deleting automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Enable automation
router.post('/:id/enable', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    await automationsService.enable(id);
    const automation = await automationsService.get(id);
    res.json({ automation });
  } catch (error) {
    log.error('Error enabling automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Disable automation
router.post('/:id/disable', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    await automationsService.disable(id);
    const automation = await automationsService.get(id);
    res.json({ automation });
  } catch (error) {
    log.error('Error disabling automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Manually trigger automation
router.post('/:id/trigger', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    const run = await automationsService.triggerAutomation(id, 'manual');
    if (!run) {
      return res.status(400).json({ error: 'Failed to trigger automation' });
    }

    res.json({ run });
  } catch (error) {
    log.error('Error triggering automation', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get automation runs
router.get('/:id/runs', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { id } = req.params;
    const userId = req.user?.id;
    const limit = parseInt(req.query.limit as string) || 10;

    const existing = await automationsService.get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Automation not found' });
    }

    if (existing.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    const runs = await automationsService.getRuns(id, limit);
    res.json({ runs });
  } catch (error) {
    log.error('Error getting automation runs', { error });
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
