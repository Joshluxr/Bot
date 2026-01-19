#!/usr/bin/env node

import { Command } from 'commander';
import { login } from './commands/login.js';
import { tasks } from './commands/tasks.js';
import { pull } from './commands/pull.js';
import { push } from './commands/push.js';
import { create } from './commands/create.js';
import { watch } from './commands/watch.js';
import { config } from './commands/config.js';

const program = new Command();

program
  .name('terry')
  .description('Terry CLI - Manage Terragon tasks from your terminal')
  .version('0.1.0');

// Login command
program
  .command('login')
  .description('Authenticate with Terragon')
  .option('--token <token>', 'API token for authentication')
  .action(login);

// Tasks command
program
  .command('tasks')
  .description('List your tasks')
  .option('-s, --status <status>', 'Filter by status (running, queued, completed, failed)')
  .option('-r, --repo <repo>', 'Filter by repository')
  .option('-l, --limit <number>', 'Number of tasks to show', '10')
  .action(tasks);

// Pull command
program
  .command('pull <taskId>')
  .description('Pull a task to your local environment')
  .option('-d, --dir <directory>', 'Directory to pull to', '.')
  .option('-f, --force', 'Overwrite existing changes')
  .action(pull);

// Push command
program
  .command('push <taskId>')
  .description('Push local changes back to a task')
  .option('-m, --message <message>', 'Commit message for the changes')
  .action(push);

// Create command
program
  .command('create')
  .description('Create a new task')
  .option('-r, --repo <repo>', 'Repository (owner/name)')
  .option('-p, --prompt <prompt>', 'Task prompt/description')
  .option('-a, --agent <agent>', 'AI agent to use (claude, openai, gemini, amp, opencode)')
  .option('-b, --branch <branch>', 'Base branch')
  .action(create);

// Watch command
program
  .command('watch <taskId>')
  .description('Watch a task in real-time')
  .action(watch);

// Config command
program
  .command('config')
  .description('Manage CLI configuration')
  .option('--get <key>', 'Get a config value')
  .option('--set <key=value>', 'Set a config value')
  .option('--list', 'List all config values')
  .action(config);

program.parse();
