import chalk from 'chalk';
import ora from 'ora';
import { getTask, watchTask, Task } from '../api.js';
import { isAuthenticated } from '../config.js';

function formatStatus(status: Task['status']): string {
  const colors: Record<Task['status'], (text: string) => string> = {
    running: chalk.yellow,
    queued: chalk.blue,
    completed: chalk.green,
    failed: chalk.red,
    paused: chalk.gray,
  };
  return colors[status](status);
}

function clearLine(): void {
  process.stdout.write('\r\x1b[K');
}

export async function watch(taskId: string): Promise<void> {
  if (!isAuthenticated()) {
    console.log(chalk.red('Not authenticated. Run `terry login` first.'));
    process.exit(1);
  }

  const spinner = ora('Connecting to task...').start();

  try {
    const task = await getTask(taskId);
    spinner.stop();

    console.log('\n' + chalk.bold(task.title));
    console.log(chalk.dim('Repository: ') + chalk.cyan(task.repository.fullName));
    console.log(chalk.dim('Agent: ') + chalk.cyan(task.agent));
    console.log(chalk.dim('Status: ') + formatStatus(task.status));

    if (task.status === 'completed') {
      if (task.prUrl) {
        console.log(chalk.dim('PR: ') + chalk.underline(task.prUrl));
      }
      console.log(chalk.green('\nTask completed.\n'));
      return;
    }

    if (task.status === 'failed') {
      console.log(chalk.red('\nTask failed. Check logs for details.\n'));
      return;
    }

    console.log(chalk.dim('\nWatching for updates... (Ctrl+C to stop)\n'));

    let lastLog = '';
    let progress = task.progress || 0;

    const cleanup = await watchTask(taskId, (data: unknown) => {
      const update = data as {
        type: string;
        progress?: number;
        log?: string;
        status?: Task['status'];
        prUrl?: string;
      };

      if (update.type === 'progress' && update.progress !== undefined) {
        progress = update.progress;
        clearLine();
        const bar = '█'.repeat(Math.floor(progress / 5)) + '░'.repeat(20 - Math.floor(progress / 5));
        process.stdout.write(chalk.dim('Progress: ') + chalk.cyan(`[${bar}] ${progress}%`));
      }

      if (update.type === 'log' && update.log) {
        if (update.log !== lastLog) {
          clearLine();
          console.log(chalk.dim('> ') + update.log);
          lastLog = update.log;
        }
      }

      if (update.type === 'status' && update.status) {
        clearLine();
        console.log('\n' + chalk.dim('Status: ') + formatStatus(update.status));

        if (update.status === 'completed') {
          if (update.prUrl) {
            console.log(chalk.dim('PR: ') + chalk.underline(update.prUrl));
          }
          console.log(chalk.green('\nTask completed!\n'));
          cleanup();
          process.exit(0);
        }

        if (update.status === 'failed') {
          console.log(chalk.red('\nTask failed.\n'));
          cleanup();
          process.exit(1);
        }
      }
    });

    // Handle Ctrl+C
    process.on('SIGINT', () => {
      cleanup();
      console.log(chalk.dim('\n\nStopped watching.\n'));
      process.exit(0);
    });
  } catch (error) {
    spinner.fail(chalk.red('Failed to watch task'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
