import { Router, Response, NextFunction } from 'express';
import { prisma } from '@terragon/database';
import { createTaskSchema, taskQuerySchema } from '@terragon/shared';
import { AuthenticatedRequest } from '../middleware/auth';
import { BadRequestError, NotFoundError, ForbiddenError } from '../middleware/error-handler';
import { taskQueue } from '../queues';
import { PLAN_LIMITS } from '@terragon/shared';
import { sandboxService } from '../services/sandbox';

const router = Router();

// List tasks
router.get('/', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const query = taskQuerySchema.parse(req.query);
    const { status, agentType, page, pageSize, sortBy, sortOrder } = query;

    const where: any = {
      userId: req.user!.id,
    };

    if (status) where.status = status;
    if (agentType) where.agentType = agentType;

    const [tasks, total] = await Promise.all([
      prisma.task.findMany({
        where,
        orderBy: { [sortBy]: sortOrder },
        skip: (page - 1) * pageSize,
        take: pageSize,
        include: {
          _count: {
            select: { logs: true },
          },
        },
      }),
      prisma.task.count({ where }),
    ]);

    res.json({
      success: true,
      data: {
        items: tasks,
        total,
        page,
        pageSize,
        hasMore: page * pageSize < total,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Get single task
router.get('/:id', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const task = await prisma.task.findUnique({
      where: { id: req.params.id },
      include: {
        logs: {
          orderBy: { timestamp: 'desc' },
          take: 100,
        },
        artifacts: true,
      },
    });

    if (!task) {
      throw new NotFoundError('Task not found');
    }

    if (task.userId !== req.user!.id) {
      throw new ForbiddenError('Not authorized to view this task');
    }

    res.json({
      success: true,
      data: task,
    });
  } catch (error) {
    next(error);
  }
});

// Create task
router.post('/', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const data = createTaskSchema.parse(req.body);

    // Check concurrent task limit
    const runningTasks = await prisma.task.count({
      where: {
        userId: req.user!.id,
        status: { in: ['PENDING', 'QUEUED', 'RUNNING'] },
      },
    });

    const planLimits = PLAN_LIMITS[req.user!.plan as keyof typeof PLAN_LIMITS];
    if (runningTasks >= planLimits.concurrentTasks) {
      throw new BadRequestError(
        `You have reached your concurrent task limit (${planLimits.concurrentTasks}). ` +
        'Wait for tasks to complete or upgrade your plan.'
      );
    }

    // Check credits
    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: { credits: true },
    });

    if (user!.credits <= 0) {
      throw new BadRequestError('Insufficient credits. Please add credits to continue.');
    }

    // Create task
    const task = await prisma.task.create({
      data: {
        ...data,
        userId: req.user!.id,
        status: 'PENDING',
      },
    });

    // Add to queue
    await taskQueue.add('process-task', {
      taskId: task.id,
      userId: req.user!.id,
    }, {
      jobId: task.id,
      priority: req.user!.plan === 'PRO' || req.user!.plan === 'ENTERPRISE' ? 1 : 2,
    });

    // Update status to QUEUED
    await prisma.task.update({
      where: { id: task.id },
      data: { status: 'QUEUED' },
    });

    res.status(201).json({
      success: true,
      data: { ...task, status: 'QUEUED' },
    });
  } catch (error) {
    next(error);
  }
});

// Cancel task
router.post('/:id/cancel', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const task = await prisma.task.findUnique({
      where: { id: req.params.id },
    });

    if (!task) {
      throw new NotFoundError('Task not found');
    }

    if (task.userId !== req.user!.id) {
      throw new ForbiddenError('Not authorized to cancel this task');
    }

    if (!['PENDING', 'QUEUED', 'RUNNING'].includes(task.status)) {
      throw new BadRequestError('Task cannot be cancelled');
    }

    // Remove from queue if queued
    if (task.status === 'QUEUED') {
      const job = await taskQueue.getJob(task.id);
      if (job) {
        await job.remove();
      }
    }

    // If running, terminate the sandbox
    if (task.status === 'RUNNING' && task.sandboxId) {
      try {
        await sandboxService.terminate(task.sandboxId);
      } catch (sandboxError) {
        // Log but don't fail the cancellation if sandbox termination fails
        console.error(`Failed to terminate sandbox ${task.sandboxId}:`, sandboxError);
      }
    }

    // Update status
    await prisma.task.update({
      where: { id: task.id },
      data: {
        status: 'CANCELLED',
        completedAt: new Date(),
      },
    });

    res.json({
      success: true,
      data: { message: 'Task cancelled' },
    });
  } catch (error) {
    next(error);
  }
});

// Get task logs
router.get('/:id/logs', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const task = await prisma.task.findUnique({
      where: { id: req.params.id },
      select: { userId: true },
    });

    if (!task) {
      throw new NotFoundError('Task not found');
    }

    if (task.userId !== req.user!.id) {
      throw new ForbiddenError('Not authorized to view this task');
    }

    const { cursor, limit = '50' } = req.query;
    const take = Math.min(parseInt(limit as string), 100);

    const logs = await prisma.taskLog.findMany({
      where: { taskId: req.params.id },
      orderBy: { timestamp: 'desc' },
      take,
      ...(cursor && {
        cursor: { id: cursor as string },
        skip: 1,
      }),
    });

    res.json({
      success: true,
      data: {
        logs,
        nextCursor: logs.length === take ? logs[logs.length - 1].id : null,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Retry failed task
router.post('/:id/retry', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const task = await prisma.task.findUnique({
      where: { id: req.params.id },
    });

    if (!task) {
      throw new NotFoundError('Task not found');
    }

    if (task.userId !== req.user!.id) {
      throw new ForbiddenError('Not authorized to retry this task');
    }

    if (task.status !== 'FAILED') {
      throw new BadRequestError('Only failed tasks can be retried');
    }

    // Reset task
    await prisma.task.update({
      where: { id: task.id },
      data: {
        status: 'QUEUED',
        errorMessage: null,
        startedAt: null,
        completedAt: null,
      },
    });

    // Add to queue
    await taskQueue.add('process-task', {
      taskId: task.id,
      userId: req.user!.id,
    }, {
      jobId: `${task.id}-retry-${Date.now()}`,
    });

    res.json({
      success: true,
      data: { message: 'Task queued for retry' },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
