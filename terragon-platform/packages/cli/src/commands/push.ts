import chalk from 'chalk';
import ora from 'ora';
import { input } from '@inquirer/prompts';
import { execSync } from 'child_process';
import { pushTask } from '../api.js';
import { isAuthenticated } from '../config.js';

interface PushOptions {
  message?: string;
}

export async function push(taskId: string, options: PushOptions): Promise<void> {
  if (!isAuthenticated()) {
    console.log(chalk.red('Not authenticated. Run `terry login` first.'));
    process.exit(1);
  }

  // Check for uncommitted changes
  try {
    const status = execSync('git status --porcelain').toString();
    if (status.trim()) {
      console.log(chalk.yellow('\nYou have uncommitted changes:\n'));
      console.log(chalk.dim(status));
    }
  } catch {
    console.log(chalk.red('Not in a git repository.'));
    process.exit(1);
  }

  let message = options.message;
  if (!message) {
    message = await input({
      message: 'Commit message:',
      default: 'Local changes from Terry CLI',
      validate: (value) => {
        if (!value.trim()) return 'Message is required';
        return true;
      },
    });
  }

  const spinner = ora('Preparing changes...').start();

  try {
    // Stage all changes
    execSync('git add -A', { stdio: 'pipe' });

    // Create a patch of the changes
    let patch = '';
    try {
      patch = execSync('git diff --cached').toString();
    } catch {
      spinner.info(chalk.yellow('No changes to push'));
      return;
    }

    if (!patch.trim()) {
      spinner.info(chalk.yellow('No changes to push'));
      return;
    }

    // Commit locally
    spinner.text = 'Committing changes...';
    execSync(`git commit -m "${message.replace(/"/g, '\\"')}"`, { stdio: 'pipe' });

    // Push to remote
    spinner.text = 'Pushing to Terragon...';
    const result = await pushTask(taskId, { message, patch });

    // Push to git remote
    spinner.text = 'Syncing with GitHub...';
    execSync('git push', { stdio: 'pipe' });

    spinner.succeed(chalk.green('Changes pushed successfully'));
    console.log('\n' + chalk.dim('Commit: ') + chalk.cyan(result.commitHash.slice(0, 8)));
    console.log(chalk.dim('\nThe task will continue with your changes.\n'));
  } catch (error) {
    spinner.fail(chalk.red('Failed to push changes'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
