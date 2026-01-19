import { Worker, Job } from 'bullmq';
import { Redis } from 'ioredis';
import { Octokit } from 'octokit';
import dotenv from 'dotenv';
import { prisma } from '@terragon/database';
import { PLAN_LIMITS, CREDIT_COSTS } from '@terragon/shared';

dotenv.config();

const connection = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: null,
});

// Import services (these would be in a shared package in production)
import { sandboxService, SandboxConfig } from './services/sandbox';
import { agentRunner } from './services/agent-runner';

interface TaskJobData {
  taskId: string;
  userId: string;
}

const logger = {
  info: (jobId: string | undefined, message: string) => {
    if (process.env.NODE_ENV !== 'production') {
      console.log(`[Job ${jobId}] ${message}`);
    }
  },
  error: (jobId: string | undefined, message: string, error?: unknown) => {
    console.error(`[Job ${jobId}] ${message}`, error || '');
  },
};

logger.info(undefined, 'Starting Terragon Worker...');

const worker = new Worker<TaskJobData>(
  'tasks',
  async (job: Job<TaskJobData>) => {
    const { taskId, userId } = job.data;
    let sandboxId: string | null = null;

    logger.info(job.id, `Processing task ${taskId}`);

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

      // Get plan limits for timeout
      const planLimits = PLAN_LIMITS[task.user.plan as keyof typeof PLAN_LIMITS];
      const timeoutSeconds = planLimits.sandboxTimeoutMinutes * 60;

      // Create sandbox environment
      await createLog(taskId, 'INFO', 'Creating sandbox environment...');
      const sandboxConfig: SandboxConfig = {
        timeoutSeconds,
        envVars: {
          GITHUB_TOKEN: task.user.githubToken || '',
        },
      };

      const sandbox = await sandboxService.create(sandboxConfig);
      sandboxId = sandbox.id;

      // Update task with sandbox ID
      await prisma.task.update({
        where: { id: taskId },
        data: { sandboxId: sandbox.id },
      });

      await createLog(taskId, 'INFO', `Sandbox created: ${sandbox.id}`);

      // Clone repository
      await createLog(taskId, 'INFO', 'Cloning repository...');
      const repoUrl = task.repoUrl.includes('github.com')
        ? task.repoUrl
        : `https://github.com/${task.repoUrl}`;

      // Add auth token to URL for private repos
      const authRepoUrl = task.user.githubToken
        ? repoUrl.replace('https://', `https://${task.user.githubToken}@`)
        : repoUrl;

      await sandboxService.cloneRepository(sandbox.id, authRepoUrl, '/workspace');

      // Checkout the specified branch
      if (task.branch && task.branch !== 'main' && task.branch !== 'master') {
        await sandboxService.exec(sandbox.id, `cd /workspace && git checkout ${task.branch}`, '/workspace');
      }

      // Install dependencies
      await createLog(taskId, 'INFO', 'Installing dependencies...');
      const installResult = await sandboxService.installDependencies(sandbox.id, '/workspace');
      if (installResult.exitCode !== 0) {
        await createLog(taskId, 'WARN', `Dependency installation warning: ${installResult.stderr}`);
      }

      // Create a new branch for changes
      const branchName = `terragon/${task.id.slice(0, 8)}`;
      await sandboxService.exec(sandbox.id, `cd /workspace && git checkout -b ${branchName}`, '/workspace');
      await createLog(taskId, 'INFO', `Created branch: ${branchName}`);

      // Run the AI agent
      await createLog(taskId, 'INFO', `Starting ${task.agentType} agent...`);

      const agentResult = await agentRunner.run({
        sandboxId: sandbox.id,
        agentType: task.agentType,
        agentConfig: task.agentConfig as Record<string, unknown> | undefined,
        task: {
          title: task.title,
          description: task.description,
        },
        onLog: async (level: string, message: string) => {
          await createLog(taskId, level, message);
        },
        onProgress: async (progress: number) => {
          logger.info(job.id, `Progress: ${progress}%`);
        },
      });

      // Create PR if there are changes
      let pullRequestUrl: string | null = null;

      if (agentResult.hasChanges) {
        await createLog(taskId, 'INFO', 'Changes detected. Creating pull request...');

        // Commit changes
        await sandboxService.exec(
          sandbox.id,
          `cd /workspace && git add -A && git commit -m "feat: ${task.title}\n\nGenerated by Terragon AI Agent"`,
          '/workspace'
        );

        // Push branch
        await sandboxService.exec(
          sandbox.id,
          `cd /workspace && git push origin ${branchName}`,
          '/workspace'
        );

        // Create PR via GitHub API
        if (task.user.githubToken) {
          const octokit = new Octokit({ auth: task.user.githubToken });
          const [owner, repo] = task.repoUrl.replace('https://github.com/', '').replace('.git', '').split('/');

          const prResponse = await octokit.rest.pulls.create({
            owner,
            repo,
            title: task.title,
            body: `## Summary\n${task.description}\n\n## Changes\n${agentResult.filesChanged.map((f) => `- ${f}`).join('\n')}\n\n---\n*Generated by [Terragon](https://terragonlabs.com)*`,
            head: branchName,
            base: task.branch || 'main',
          });

          pullRequestUrl = prResponse.data.html_url;
          await createLog(taskId, 'INFO', `Pull request created: ${pullRequestUrl}`);
        }
      } else {
        await createLog(taskId, 'INFO', 'No changes were necessary.');
      }

      // Calculate execution time and credits
      const executionTime = Math.ceil((Date.now() - startTime) / 1000);
      const executionMinutes = Math.ceil(executionTime / 60);
      const creditsUsed = executionMinutes * CREDIT_COSTS.SANDBOX_MINUTE;

      // Terminate sandbox
      await sandboxService.terminate(sandbox.id);
      sandboxId = null;

      // Update task as completed
      await prisma.task.update({
        where: { id: taskId },
        data: {
          status: 'COMPLETED',
          completedAt: new Date(),
          pullRequestUrl,
          creditsUsed,
          executionTime,
          sandboxId: null,
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

      logger.info(job.id, `Task ${taskId} completed successfully`);

      return { success: true, pullRequestUrl, creditsUsed };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      logger.error(job.id, `Task ${taskId} failed:`, error);

      // Terminate sandbox if still running
      if (sandboxId) {
        try {
          await sandboxService.terminate(sandboxId);
        } catch {
          // Ignore sandbox termination errors during failure handling
        }
      }

      // Update task as failed
      await prisma.task.update({
        where: { id: taskId },
        data: {
          status: 'FAILED',
          completedAt: new Date(),
          errorMessage,
          sandboxId: null,
        },
      });

      await createLog(taskId, 'ERROR', `Task failed: ${errorMessage}`);

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
      level: level as 'INFO' | 'WARN' | 'ERROR' | 'DEBUG',
      message,
    },
  });
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
