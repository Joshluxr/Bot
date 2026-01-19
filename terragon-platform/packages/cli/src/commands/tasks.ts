import chalk from 'chalk';
import ora from 'ora';
import { table } from 'table';
import { listTasks, Task } from '../api.js';
import { isAuthenticated } from '../config.js';

interface TasksOptions {
  status?: string;
  repo?: string;
  limit?: string;
}

function formatStatus(status: Task['status']): string {
  const colors: Record<Task['status'], (text: string) => string> = {
    running: chalk.yellow,
    queued: chalk.blue,
    completed: chalk.green,
    failed: chalk.red,
    paused: chalk.gray,
  };
  const icons: Record<Task['status'], string> = {
    running: '●',
    queued: '○',
    completed: '✓',
    failed: '✗',
    paused: '◐',
  };
  return colors[status](`${icons[status]} ${status}`);
}

function formatProgress(task: Task): string {
  if (task.status === 'completed') return chalk.green('100%');
  if (task.status === 'failed') return chalk.red('---');
  if (task.status === 'queued') return chalk.blue('---');
  if (task.progress !== undefined) {
    return chalk.yellow(`${task.progress}%`);
  }
  return chalk.dim('---');
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + '…';
}

export async function tasks(options: TasksOptions): Promise<void> {
  if (!isAuthenticated()) {
    console.log(chalk.red('Not authenticated. Run `terry login` first.'));
    process.exit(1);
  }

  const spinner = ora('Fetching tasks...').start();

  try {
    const taskList = await listTasks({
      status: options.status,
      repo: options.repo,
      limit: options.limit ? parseInt(options.limit, 10) : 10,
    });

    spinner.stop();

    if (taskList.length === 0) {
      console.log(chalk.dim('\nNo tasks found.\n'));
      return;
    }

    const data = [
      [
        chalk.bold('ID'),
        chalk.bold('Title'),
        chalk.bold('Status'),
        chalk.bold('Progress'),
        chalk.bold('Repository'),
      ],
      ...taskList.map((task) => [
        chalk.dim(task.id.slice(0, 8)),
        truncate(task.title, 30),
        formatStatus(task.status),
        formatProgress(task),
        chalk.cyan(task.repository.fullName),
      ]),
    ];

    console.log('\n' + table(data, {
      border: {
        topBody: '',
        topJoin: '',
        topLeft: '',
        topRight: '',
        bottomBody: '',
        bottomJoin: '',
        bottomLeft: '',
        bottomRight: '',
        bodyLeft: '',
        bodyRight: '',
        bodyJoin: '  ',
        joinBody: '',
        joinLeft: '',
        joinRight: '',
        joinJoin: '',
      },
      drawHorizontalLine: () => false,
    }));

    console.log(chalk.dim(`Showing ${taskList.length} task(s)\n`));
  } catch (error) {
    spinner.fail(chalk.red('Failed to fetch tasks'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
