import { Worker, Job } from 'bullmq';
import { Redis } from 'ioredis';
import dotenv from 'dotenv';
import { prisma } from '@terragon/database';
import { PLAN_LIMITS, CREDIT_COSTS } from '@terragon/shared';

dotenv.config();

const connection = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: null,
});

interface TaskJobData {
  taskId: string;
  userId: string;
}

console.log('Starting Terragon Worker...');

const worker = new Worker<TaskJobData>(
  'tasks',
  async (job: Job<TaskJobData>) => {
    const { taskId, userId } = job.data;

    console.log(`[Job ${job.id}] Processing task ${taskId}`);

    try {
      // Update task status to RUNNING
      await prisma.task.update({
        where: { id: taskId },
        data: {
          status: 'RUNNING',
          startedAt: new Date(),
        },
      });

      // Get task details
      const task = await prisma.task.findUnique({
        where: { id: taskId },
        include: {
          user: {
            select: { plan: true, githubToken: true },
          },
        },
      });

      if (!task) {
        throw new Error('Task not found');
      }

      const startTime = Date.now();

      // Log: Starting
      await createLog(taskId, 'INFO', 'Starting task execution...');

      // Get plan limits
      const planLimits = PLAN_LIMITS[task.user.plan as keyof typeof PLAN_LIMITS];

      // Simulate sandbox creation and agent execution
      // In production, this would:
      // 1. Create an E2B sandbox or Docker container
      // 2. Clone the repository
      // 3. Run the AI agent (Claude Code, GPT-4, etc.)
      // 4. Commit changes and create PR

      await createLog(taskId, 'INFO', 'Creating sandbox environment...');
      await simulateDelay(2000);

      await createLog(taskId, 'INFO', 'Cloning repository...');
      await simulateDelay(3000);

      await createLog(taskId, 'INFO', 'Installing dependencies...');
      await simulateDelay(5000);

      await createLog(taskId, 'INFO', `Starting ${task.agentType} agent...`);
      await simulateDelay(2000);

      // Simulate agent work
      const agentSteps = [
        'Analyzing codebase structure...',
        'Understanding task requirements...',
        'Planning implementation approach...',
        'Writing code changes...',
        'Running tests...',
        'Reviewing changes...',
      ];

      for (let i = 0; i < agentSteps.length; i++) {
        await createLog(taskId, 'INFO', agentSteps[i]);
        await simulateDelay(3000 + Math.random() * 2000);

        // Update progress
        const progress = Math.round(((i + 1) / agentSteps.length) * 100);
        console.log(`[Job ${job.id}] Progress: ${progress}%`);
      }

      // Simulate PR creation
      const hasChanges = Math.random() > 0.1; // 90% chance of having changes
      let pullRequestUrl: string | null = null;

      if (hasChanges) {
        await createLog(taskId, 'INFO', 'Changes detected. Creating pull request...');
        await simulateDelay(2000);

        // In production, this would create an actual PR
        pullRequestUrl = `https://github.com/${task.repoUrl.replace('https://github.com/', '')}/pull/${Math.floor(Math.random() * 1000)}`;

        await createLog(taskId, 'INFO', `Pull request created: ${pullRequestUrl}`);
      } else {
        await createLog(taskId, 'INFO', 'No changes were necessary.');
      }

      // Calculate execution time and credits
      const executionTime = Math.ceil((Date.now() - startTime) / 1000);
      const executionMinutes = Math.ceil(executionTime / 60);
      const creditsUsed = executionMinutes * CREDIT_COSTS.SANDBOX_MINUTE;

      // Update task as completed
      await prisma.task.update({
        where: { id: taskId },
        data: {
          status: 'COMPLETED',
          completedAt: new Date(),
          pullRequestUrl,
          creditsUsed,
          executionTime,
        },
      });

      // Deduct credits from user
      await prisma.$transaction([
        prisma.user.update({
          where: { id: userId },
          data: { credits: { decrement: creditsUsed } },
        }),
        prisma.creditHistory.create({
          data: {
            userId,
            amount: -creditsUsed,
            type: 'USAGE',
            description: `Task: ${task.title}`,
            taskId,
          },
        }),
      ]);

      await createLog(taskId, 'INFO', `Task completed. ${creditsUsed} credits used.`);

      // Send notifications
      await sendNotifications(userId, task.title, 'completed', pullRequestUrl);

      console.log(`[Job ${job.id}] Task ${taskId} completed successfully`);

      return { success: true, pullRequestUrl, creditsUsed };
    } catch (error: any) {
      console.error(`[Job ${job.id}] Task ${taskId} failed:`, error);

      // Update task as failed
      await prisma.task.update({
        where: { id: taskId },
        data: {
          status: 'FAILED',
          completedAt: new Date(),
          errorMessage: error.message,
        },
      });

      await createLog(taskId, 'ERROR', `Task failed: ${error.message}`);

      // Get task title for notification
      const task = await prisma.task.findUnique({
        where: { id: taskId },
        select: { title: true },
      });

      if (task) {
        await sendNotifications(userId, task.title, 'failed');
      }

      throw error;
    }
  },
  {
    connection,
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || '5'),
    removeOnComplete: { count: 1000 },
    removeOnFail: { count: 5000 },
  }
);

worker.on('completed', (job) => {
  console.log(`[Worker] Job ${job.id} completed`);
});

worker.on('failed', (job, err) => {
  console.error(`[Worker] Job ${job?.id} failed:`, err.message);
});

worker.on('error', (err) => {
  console.error('[Worker] Error:', err);
});

console.log('Terragon Worker started. Waiting for jobs...');

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Received SIGTERM. Shutting down...');
  await worker.close();
  await connection.quit();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('Received SIGINT. Shutting down...');
  await worker.close();
  await connection.quit();
  process.exit(0);
});

// Helper functions
async function createLog(taskId: string, level: string, message: string) {
  await prisma.taskLog.create({
    data: {
      taskId,
      level: level as any,
      message,
    },
  });
}

async function simulateDelay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sendNotifications(
  userId: string,
  taskTitle: string,
  status: 'completed' | 'failed',
  prUrl?: string | null
) {
  try {
    // Send Slack notification if configured
    const slackIntegration = await prisma.integration.findFirst({
      where: {
        userId,
        type: 'SLACK',
        isActive: true,
      },
    });

    if (slackIntegration?.accessToken) {
      const emoji = status === 'completed' ? ':white_check_mark:' : ':x:';
      let text = `${emoji} Task "${taskTitle}" ${status}`;

      if (prUrl) {
        text += `\n<${prUrl}|View Pull Request>`;
      }

      await fetch(slackIntegration.accessToken, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      console.log(`[Notification] Slack notification sent for task: ${taskTitle}`);
    }
  } catch (error) {
    console.error('[Notification] Failed to send notification:', error);
  }
}
