import { input } from '@inquirer/prompts';
import chalk from 'chalk';
import ora from 'ora';
import { setApiToken, getApiUrl } from '../config.js';

interface LoginOptions {
  token?: string;
}

export async function login(options: LoginOptions): Promise<void> {
  let token = options.token;

  if (!token) {
    console.log(chalk.cyan('\nAuthenticate with Terragon\n'));
    console.log(
      chalk.dim('Get your API token from: ') +
        chalk.underline(`${getApiUrl()}/settings/tokens\n`)
    );

    token = await input({
      message: 'Enter your API token:',
      validate: (value) => {
        if (!value.trim()) return 'Token is required';
        if (value.length < 32) return 'Invalid token format';
        return true;
      },
    });
  }

  const spinner = ora('Validating token...').start();

  try {
    // Validate the token by making a test request
    const response = await fetch(`${getApiUrl()}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Invalid token');
    }

    const user = await response.json();
    setApiToken(token);

    spinner.succeed(chalk.green(`Logged in as ${user.name || user.email}`));
    console.log(chalk.dim('\nYou can now use terry commands to manage your tasks.\n'));
  } catch (error) {
    spinner.fail(chalk.red('Authentication failed'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
