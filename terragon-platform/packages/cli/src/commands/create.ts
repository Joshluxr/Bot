import chalk from 'chalk';
import ora from 'ora';
import { input, select } from '@inquirer/prompts';
import { createTask } from '../api.js';
import { isAuthenticated, getDefaultAgent } from '../config.js';

interface CreateOptions {
  repo?: string;
  prompt?: string;
  agent?: string;
  branch?: string;
}

const AGENTS = [
  { name: 'Claude Code', value: 'claude' },
  { name: 'OpenAI Codex', value: 'openai' },
  { name: 'Gemini', value: 'gemini' },
  { name: 'Amp', value: 'amp' },
  { name: 'OpenCode', value: 'opencode' },
];

export async function create(options: CreateOptions): Promise<void> {
  if (!isAuthenticated()) {
    console.log(chalk.red('Not authenticated. Run `terry login` first.'));
    process.exit(1);
  }

  console.log(chalk.cyan('\nCreate a new task\n'));

  // Get repository
  let repo = options.repo;
  if (!repo) {
    repo = await input({
      message: 'Repository (owner/name):',
      validate: (value) => {
        if (!value.includes('/')) return 'Format: owner/name';
        return true;
      },
    });
  }

  // Get prompt
  let prompt = options.prompt;
  if (!prompt) {
    prompt = await input({
      message: 'What would you like the agent to do?',
      validate: (value) => {
        if (!value.trim()) return 'Prompt is required';
        if (value.length < 10) return 'Please provide more detail';
        return true;
      },
    });
  }

  // Get agent
  let agent = options.agent;
  if (!agent) {
    agent = await select({
      message: 'Select AI agent:',
      choices: AGENTS,
      default: getDefaultAgent(),
    });
  }

  // Get branch
  let branch = options.branch;
  if (!branch) {
    branch = await input({
      message: 'Base branch:',
      default: 'main',
    });
  }

  const spinner = ora('Creating task...').start();

  try {
    const task = await createTask({
      repository: repo,
      prompt,
      agent,
      branch,
    });

    spinner.succeed(chalk.green('Task created successfully'));
    console.log('\n' + chalk.dim('Task ID: ') + chalk.cyan(task.id));
    console.log(chalk.dim('Status: ') + chalk.yellow('queued'));
    console.log(chalk.dim('Agent: ') + chalk.cyan(agent));

    console.log(chalk.dim('\nWatch progress with: ') + chalk.cyan(`terry watch ${task.id}`));
    console.log(chalk.dim('Pull changes with: ') + chalk.cyan(`terry pull ${task.id}\n`));
  } catch (error) {
    spinner.fail(chalk.red('Failed to create task'));
    if (error instanceof Error) {
      console.error(chalk.dim(error.message));
    }
    process.exit(1);
  }
}
