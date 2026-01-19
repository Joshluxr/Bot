import chalk from 'chalk';
import ora from 'ora';
import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';
import { pullTask, getTask } from '../api.js';
import { isAuthenticated } from '../config.js';

interface PullOptions {
  dir: string;
  force?: boolean;
}

export async function pull(taskId: string, options: PullOptions): Promise<void> {
  if (!isAuthenticated()) {
    console.log(chalk.red('Not authenticated. Run `terry login` first.'));
    process.exit(1);
  }

  const targetDir = resolve(options.dir);

  // Check if directory exists and has changes
  if (existsSync(targetDir) && !options.force) {
    try {
      const status = execSync('git status --porcelain', { cwd: targetDir }).toString();
      if (status.trim()) {
        console.log(chalk.red('\nLocal changes detected. Use --force to overwrite.\n'));
        process.exit(1);
      }
    } catch {
      // Not a git repo, that's fine
    }
  }

  const spinner = ora('Fetching task details...').start();

  try {
    const task = await getTask(taskId);
    spinner.text = `Pulling task: ${task.title}`;

    const pullData = await pullTask(taskId);
    spinner.text = 'Setting up local environment...';

    // Create directory if it doesn't exist
    if (!existsSync(targetDir)) {
      mkdirSync(targetDir, { recursive: true });
    }

    // Clone or fetch the repository
    const repoUrl = `https://github.com/${task.repository.fullName}.git`;
    const gitDir = join(targetDir, '.git');

    if (!existsSync(gitDir)) {
      spinner.text = 'Cloning repository...';
      execSync(`git clone ${repoUrl} .`, { cwd: targetDir, stdio: 'pipe' });
    } else {
      spinner.text = 'Fetching latest changes...';
      execSync('git fetch origin', { cwd: targetDir, stdio: 'pipe' });
    }

    // Checkout the task branch
    spinner.text = `Checking out branch: ${pullData.branch}`;
    try {
      execSync(`git checkout ${pullData.branch}`, { cwd: targetDir, stdio: 'pipe' });
    } catch {
      // Branch doesn't exist locally, create it
      execSync(`git checkout -b ${pullData.branch} origin/${pullData.branch}`, {
        cwd: targetDir,
        stdio: 'pipe',
      });
    }

    // Pull latest
    execSync('git pull', { cwd: targetDir, stdio: 'pipe' });

    spinner.succeed(chalk.green('Task pulled successfully'));
    console.log('\n' + chalk.dim('Directory: ') + chalk.cyan(targetDir));
    console.log(chalk.dim('Branch: ') + chalk.cyan(pullData.branch));
    console.log(chalk.dim('Commit: ') + chalk.cyan(pullData.commitHash.slice(0, 8)));
    console.log(chalk.dim('Files changed: ') + chalk.cyan(pullData.files.length));

    console.log(chalk.dim('\nRun `terry push ' + taskId + '` when you\'re done.\n'));
  } catch (error) {
    spinner.fail(chalk.red('Failed to pull task'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
