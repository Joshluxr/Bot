import { Queue, Worker, Job } from 'bullmq';
import Redis from 'ioredis';
import { prisma } from '@terragon/database';
import { sandboxService } from './services/sandbox';
import { io } from './index';
import {
  emitTaskStarted,
  emitTaskProgress,
  emitTaskCompleted,
  emitTaskFailed,
  emitLog,
} from './socket';

// Redis connection
const redisConnection = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  maxRetriesPerRequest: null,
});

// Task processing queue
export const taskQueue = new Queue('tasks', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 1000,
    },
    removeOnComplete: 100,
    removeOnFail: 100,
  },
});

interface TaskJobData {
  taskId: string;
  userId: string;
}

export function initializeQueues() {
  // Task processing worker
  const taskWorker = new Worker<TaskJobData>(
    'tasks',
    async (job: Job<TaskJobData>) => {
      const { taskId, userId } = job.data;

      console.log(`Processing task ${taskId}`);

      try {
        // Update task status to RUNNING
        await prisma.task.update({
          where: { id: taskId },
          data: { status: 'RUNNING', startedAt: new Date() },
        });

        // Get task details
        const task = await prisma.task.findUnique({
          where: { id: taskId },
        });

        if (!task) {
          throw new Error('Task not found');
        }

        // Create sandbox
        const sandbox = await sandboxService.create({
          timeoutSeconds: 1800,
          envVars: {
            TASK_ID: taskId,
            REPO_URL: task.repoUrl,
            BRANCH: task.repoBranch,
          },
        });

        // Update task with sandbox ID
        await prisma.task.update({
          where: { id: taskId },
          data: { sandboxId: sandbox.id },
        });

        // Emit task started event
        emitTaskStarted(io, userId, taskId, sandbox.id);

        // Log: Starting
        await createLog(taskId, 'INFO', 'Task execution started');
        emitLog(io, userId, taskId, 'INFO', 'Task execution started');

        // Clone repository
        await createLog(taskId, 'INFO', `Cloning repository: ${task.repoUrl}`);
        emitLog(io, userId, taskId, 'INFO', `Cloning repository: ${task.repoUrl}`);
        await sandboxService.cloneRepository(sandbox.id, task.repoUrl, '/workspace');

        emitTaskProgress(io, userId, taskId, 20, 'Repository cloned');

        // Install dependencies
        await createLog(taskId, 'INFO', 'Installing dependencies...');
        emitLog(io, userId, taskId, 'INFO', 'Installing dependencies...');
        const installResult = await sandboxService.installDependencies(sandbox.id, '/workspace');

        if (installResult.stderr) {
          await createLog(taskId, 'WARN', `Dependency warnings: ${installResult.stderr}`);
        }

        emitTaskProgress(io, userId, taskId, 40, 'Dependencies installed');

        // Run the agent (mock for now - in production this would call the worker)
        await createLog(taskId, 'INFO', `Starting ${task.agentType} agent...`);
        emitLog(io, userId, taskId, 'INFO', `Starting ${task.agentType} agent...`);

        // Simulate agent work
        for (let i = 50; i <= 90; i += 10) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          emitTaskProgress(io, userId, taskId, i, `Agent working... ${i}%`);
        }

        await createLog(taskId, 'INFO', 'Agent completed task');
        emitLog(io, userId, taskId, 'INFO', 'Agent completed task');

        // Run tests
        await createLog(taskId, 'INFO', 'Running tests...');
        emitLog(io, userId, taskId, 'INFO', 'Running tests...');
        const testResult = await sandboxService.runTests(sandbox.id, '/workspace');

        if (testResult.exitCode !== 0) {
          await createLog(taskId, 'WARN', `Test warnings: ${testResult.stderr || testResult.stdout}`);
        }

        emitTaskProgress(io, userId, taskId, 95, 'Tests completed');

        // Calculate execution time
        const startTime = task.startedAt || new Date();
        const executionTime = Math.floor((Date.now() - startTime.getTime()) / 1000);

        // Calculate credits used (1 credit per minute of execution)
        const creditsUsed = Math.max(1, Math.ceil(executionTime / 60));

        // Update task as completed
        await prisma.task.update({
          where: { id: taskId },
          data: {
            status: 'COMPLETED',
            completedAt: new Date(),
            executionTime,
            creditsUsed,
          },
        });

        // Deduct credits from user
        await prisma.user.update({
          where: { id: userId },
          data: {
            credits: { decrement: creditsUsed },
          },
        });

        // Record credit usage
        await prisma.creditHistory.create({
          data: {
            userId,
            amount: -creditsUsed,
            type: 'USAGE',
            description: `Task: ${task.title}`,
            taskId,
          },
        });

        // Terminate sandbox
        await sandboxService.terminate(sandbox.id);

        await createLog(taskId, 'INFO', `Task completed successfully. Credits used: ${creditsUsed}`);
        emitLog(io, userId, taskId, 'INFO', `Task completed successfully. Credits used: ${creditsUsed}`);

        // Emit completed event
        emitTaskCompleted(io, userId, taskId, null, executionTime, creditsUsed);

        console.log(`Task ${taskId} completed successfully`);
      } catch (error) {
        console.error(`Task ${taskId} failed:`, error);

        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        // Update task as failed
        await prisma.task.update({
          where: { id: taskId },
          data: {
            status: 'FAILED',
            completedAt: new Date(),
            errorMessage,
          },
        });

        await createLog(taskId, 'ERROR', `Task failed: ${errorMessage}`);
        emitLog(io, userId, taskId, 'ERROR', `Task failed: ${errorMessage}`);
        emitTaskFailed(io, userId, taskId, errorMessage);

        throw error;
      }
    },
    {
      connection: redisConnection,
      concurrency: 5,
    }
  );

  taskWorker.on('completed', (job) => {
    console.log(`Job ${job.id} completed`);
  });

  taskWorker.on('failed', (job, error) => {
    console.error(`Job ${job?.id} failed:`, error);
  });

  console.log('Queue workers initialized');
}

async function createLog(taskId: string, level: string, message: string) {
  await prisma.taskLog.create({
    data: {
      taskId,
      level: level as 'DEBUG' | 'INFO' | 'WARN' | 'ERROR',
      message,
    },
  });
}
