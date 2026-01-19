import chalk from 'chalk';
import { store } from '../config.js';

interface ConfigOptions {
  get?: string;
  set?: string;
  list?: boolean;
}

export async function config(options: ConfigOptions): Promise<void> {
  if (options.list) {
    console.log(chalk.cyan('\nTerragon CLI Configuration\n'));

    const all = store.store;
    const entries = Object.entries(all);

    if (entries.length === 0) {
      console.log(chalk.dim('No configuration set.\n'));
      return;
    }

    for (const [key, value] of entries) {
      const displayValue = key === 'apiToken' ? '••••••••' : String(value);
      console.log(chalk.dim(key + ': ') + chalk.white(displayValue));
    }
    console.log('');
    return;
  }

  if (options.get) {
    const value = store.get(options.get as keyof typeof store.store);
    if (value === undefined) {
      console.log(chalk.red(`Config key '${options.get}' not found.`));
      process.exit(1);
    }

    const displayValue = options.get === 'apiToken' ? '••••••••' : String(value);
    console.log(displayValue);
    return;
  }

  if (options.set) {
    const [key, ...valueParts] = options.set.split('=');
    const value = valueParts.join('=');

    if (!key || !value) {
      console.log(chalk.red('Invalid format. Use: --set key=value'));
      process.exit(1);
    }

    const validKeys = ['apiUrl', 'defaultAgent'];
    if (!validKeys.includes(key) && key !== 'apiToken') {
      console.log(chalk.red(`Invalid config key. Valid keys: ${validKeys.join(', ')}`));
      process.exit(1);
    }

    store.set(key as keyof typeof store.store, value);
    console.log(chalk.green(`Set ${key} successfully.`));
    return;
  }

  // No options provided, show help
  console.log(chalk.cyan('\nTerragon CLI Configuration\n'));
  console.log('Usage:');
  console.log(chalk.dim('  terry config --list           ') + 'List all config values');
  console.log(chalk.dim('  terry config --get <key>      ') + 'Get a config value');
  console.log(chalk.dim('  terry config --set <key=value>') + 'Set a config value');
  console.log('\nAvailable keys:');
  console.log(chalk.dim('  apiUrl        ') + 'API base URL');
  console.log(chalk.dim('  defaultAgent  ') + 'Default AI agent');
  console.log('');
}
