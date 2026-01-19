import { Queue, Worker, Job } from 'bullmq';
import { Redis } from 'ioredis';
import { prisma } from '@terragon/database';
import { io } from '../index';
import { sandboxService } from '../services/sandbox';
import { agentRunner } from '../services/agent-runner';
import { PLAN_LIMITS, CREDIT_COSTS } from '@terragon/shared';

const connection = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: null,
});

// Task processing queue
export const taskQueue = new Queue('tasks', { connection });

// Worker for processing tasks
let taskWorker: Worker;

interface TaskJobData {
  taskId: string;
  userId: string;
}

export function initializeQueues() {
  taskWorker = new Worker<TaskJobData>(
    'tasks',
    async (job: Job<TaskJobData>) => {
      const { taskId, userId } = job.data;

      console.log(`Processing task ${taskId} for user ${userId}`);

      try {
        // Update task status
        await prisma.task.update({
          where: { id: taskId },
          data: {
            status: 'RUNNING',
            startedAt: new Date(),
          },
        });

        // Emit status update
        io.to(`user:${userId}`).emit('task:started', {
          taskId,
          sandboxId: null,
          timestamp: new Date(),
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

        // Get plan limits
        const planLimits = PLAN_LIMITS[task.user.plan as keyof typeof PLAN_LIMITS];

        // Create log entry
        await createLog(taskId, 'INFO', 'Starting sandbox environment...');

        // Create sandbox
        const sandbox = await sandboxService.create({
          cpu: planLimits.sandboxCpu,
          memoryMb: planLimits.sandboxMemoryMb,
          timeoutSeconds: planLimits.sandboxTimeout,
        });

        await prisma.task.update({
          where: { id: taskId },
          data: { sandboxId: sandbox.id },
        });

        io.to(`user:${userId}`).emit('sandbox:ready', {
          taskId,
          sandboxId: sandbox.id,
          timestamp: new Date(),
        });

        await createLog(taskId, 'INFO', `Sandbox ready (ID: ${sandbox.id})`);
        await createLog(taskId, 'INFO', 'Cloning repository...');

        // Clone repository
        await sandboxService.exec(sandbox.id, `git clone ${task.repoUrl} /workspace`);
        await sandboxService.exec(sandbox.id, `cd /workspace && git checkout ${task.repoBranch}`);

        await createLog(taskId, 'INFO', 'Repository cloned. Installing dependencies...');

        // Install dependencies (detect package manager)
        const hasYarnLock = await sandboxService.fileExists(sandbox.id, '/workspace/yarn.lock');
        const hasPnpmLock = await sandboxService.fileExists(sandbox.id, '/workspace/pnpm-lock.yaml');

        if (hasPnpmLock) {
          await sandboxService.exec(sandbox.id, 'cd /workspace && pnpm install');
        } else if (hasYarnLock) {
          await sandboxService.exec(sandbox.id, 'cd /workspace && yarn install');
        } else {
          await sandboxService.exec(sandbox.id, 'cd /workspace && npm install');
        }

        await createLog(taskId, 'INFO', 'Dependencies installed. Starting agent...');

        // Progress tracking
        const startTime = Date.now();
        let creditsUsed = 0;

        // Run agent
        const result = await agentRunner.run({
          sandboxId: sandbox.id,
          agentType: task.agentType,
          agentConfig: task.agentConfig as any,
          task: {
            title: task.title,
            description: task.description,
          },
          onLog: async (level, message) => {
            await createLog(taskId, level, message);
            io.to(`user:${userId}`).emit('log', {
              taskId,
              level,
              message,
              timestamp: new Date(),
            });
          },
          onProgress: async (progress) => {
            io.to(`user:${userId}`).emit('task:progress', {
              taskId,
              progress,
              timestamp: new Date(),
            });
          },
        });

        // Calculate credits used
        const executionTime = Math.ceil((Date.now() - startTime) / 1000 / 60); // minutes
        creditsUsed = executionTime * CREDIT_COSTS.SANDBOX_MINUTE;

        // Create branch and PR if changes were made
        let pullRequestUrl: string | null = null;

        if (result.hasChanges) {
          await createLog(taskId, 'INFO', 'Changes detected. Creating pull request...');

          const branchName = `terragon/${task.id.slice(0, 8)}`;

          await sandboxService.exec(sandbox.id, `cd /workspace && git checkout -b ${branchName}`);
          await sandboxService.exec(sandbox.id, `cd /workspace && git add -A`);
          await sandboxService.exec(
            sandbox.id,
            `cd /workspace && git commit -m "${task.title}\n\nGenerated by Terragon AI Agent"`
          );

          // Push branch (requires GitHub token)
          if (task.user.githubToken) {
            const repoUrl = task.repoUrl.replace(
              'https://github.com/',
              `https://${task.user.githubToken}@github.com/`
            );
            await sandboxService.exec(
              sandbox.id,
              `cd /workspace && git push ${repoUrl} ${branchName}`
            );

            // Create PR via GitHub API
            const { Octokit } = await import('octokit');
            const octokit = new Octokit({ auth: task.user.githubToken });

            const [owner, repo] = task.repoUrl
              .replace('https://github.com/', '')
              .replace('.git', '')
              .split('/');

            const { data: pr } = await octokit.rest.pulls.create({
              owner,
              repo,
              title: task.title,
              body: `## Summary\n\n${task.description}\n\n---\n\n*Generated by Terragon AI Agent*`,
              head: branchName,
              base: task.repoBranch,
            });

            pullRequestUrl = pr.html_url;
            await createLog(taskId, 'INFO', `Pull request created: ${pullRequestUrl}`);
          }
        } else {
          await createLog(taskId, 'INFO', 'No changes detected.');
        }

        // Cleanup sandbox
        await sandboxService.terminate(sandbox.id);

        // Update task
        await prisma.task.update({
          where: { id: taskId },
          data: {
            status: 'COMPLETED',
            completedAt: new Date(),
            pullRequestUrl,
            creditsUsed,
            executionTime: Math.ceil((Date.now() - startTime) / 1000),
          },
        });

        // Deduct credits
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

        // Emit completion
        io.to(`user:${userId}`).emit('task:completed', {
          taskId,
          pullRequestUrl,
          creditsUsed,
          executionTime: Math.ceil((Date.now() - startTime) / 1000),
          timestamp: new Date(),
        });

        // Send Slack notification if configured
        await sendSlackNotification(userId, task.title, 'completed', pullRequestUrl);

        return { success: true, pullRequestUrl };
      } catch (error: any) {
        console.error(`Task ${taskId} failed:`, error);

        // Update task status
        await prisma.task.update({
          where: { id: taskId },
          data: {
            status: 'FAILED',
            completedAt: new Date(),
            errorMessage: error.message,
          },
        });

        await createLog(taskId, 'ERROR', `Task failed: ${error.message}`);

        // Emit failure
        io.to(`user:${userId}`).emit('task:failed', {
          taskId,
          errorMessage: error.message,
          timestamp: new Date(),
        });

        // Send Slack notification
        const task = await prisma.task.findUnique({
          where: { id: taskId },
          select: { title: true },
        });

        if (task) {
          await sendSlackNotification(userId, task.title, 'failed');
        }

        throw error;
      }
    },
    {
      connection,
      concurrency: 5,
    }
  );

  taskWorker.on('completed', (job) => {
    console.log(`Task ${job.id} completed`);
  });

  taskWorker.on('failed', (job, err) => {
    console.error(`Task ${job?.id} failed:`, err);
  });

  console.log('Task queue initialized');
}

async function createLog(taskId: string, level: string, message: string) {
  await prisma.taskLog.create({
    data: {
      taskId,
      level: level as any,
      message,
    },
  });
}

async function sendSlackNotification(
  userId: string,
  taskTitle: string,
  status: 'completed' | 'failed',
  prUrl?: string | null
) {
  try {
    const integration = await prisma.integration.findFirst({
      where: {
        userId,
        type: 'SLACK',
        isActive: true,
      },
    });

    if (!integration?.accessToken) return;

    const emoji = status === 'completed' ? ':white_check_mark:' : ':x:';
    let text = `${emoji} Task "${taskTitle}" ${status}`;

    if (prUrl) {
      text += `\n<${prUrl}|View Pull Request>`;
    }

    await fetch(integration.accessToken, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  } catch (error) {
    console.error('Failed to send Slack notification:', error);
  }
}
