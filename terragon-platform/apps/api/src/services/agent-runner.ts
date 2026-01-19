import { sandboxService } from './sandbox';

interface AgentConfig {
  model?: string;
  apiKey?: string;
  maxTokens?: number;
  temperature?: number;
  timeout?: number;
  customInstructions?: string;
}

interface AgentRunOptions {
  sandboxId: string;
  agentType: string;
  agentConfig?: AgentConfig;
  task: {
    title: string;
    description: string;
  };
  onLog: (level: string, message: string) => Promise<void>;
  onProgress: (progress: number) => Promise<void>;
}

interface AgentRunResult {
  hasChanges: boolean;
  filesChanged: string[];
  summary: string;
}

/**
 * Agent Runner Service
 *
 * This service manages the execution of AI coding agents inside sandboxes.
 * It supports multiple agent types:
 * - CLAUDE: Claude Code (Anthropic)
 * - OPENAI: GPT-4 with code generation
 * - GEMINI: Google Gemini
 * - CUSTOM: User-provided configuration
 */
class AgentRunner {
  async run(options: AgentRunOptions): Promise<AgentRunResult> {
    const { sandboxId, agentType, agentConfig, task, onLog, onProgress } = options;

    await onLog('INFO', `Initializing ${agentType} agent...`);
    await onProgress(10);

    // Get agent configuration
    const config = this.getAgentConfig(agentType, agentConfig);

    await onLog('INFO', `Using model: ${config.model}`);

    // Set up environment variables in sandbox
    await this.setupAgentEnvironment(sandboxId, agentType, config);
    await onProgress(20);

    // Create agent prompt
    const prompt = this.createAgentPrompt(task);
    await onLog('INFO', 'Agent prompt created');
    await onProgress(30);

    // Run the agent
    await onLog('INFO', 'Starting agent execution...');

    // In production, this would actually run the agent CLI
    // For Claude Code:
    // await sandboxService.exec(sandboxId, `claude-code "${prompt}"`);

    // Simulate agent execution with progress updates
    const steps = [
      { progress: 40, message: 'Analyzing codebase structure...' },
      { progress: 50, message: 'Understanding requirements...' },
      { progress: 60, message: 'Planning implementation...' },
      { progress: 70, message: 'Writing code changes...' },
      { progress: 80, message: 'Running tests...' },
      { progress: 90, message: 'Finalizing changes...' },
    ];

    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await onLog('INFO', step.message);
      await onProgress(step.progress);
    }

    // Check for changes
    const result = await sandboxService.exec(
      sandboxId,
      'cd /workspace && git status --porcelain'
    );

    const hasChanges = result.stdout.trim().length > 0;
    const filesChanged = hasChanges
      ? result.stdout.trim().split('\n').map((line) => line.slice(3))
      : [];

    await onProgress(100);
    await onLog('INFO', `Agent completed. ${filesChanged.length} files modified.`);

    return {
      hasChanges,
      filesChanged,
      summary: `Completed task: ${task.title}`,
    };
  }

  private getAgentConfig(agentType: string, userConfig?: AgentConfig): Required<AgentConfig> {
    const defaults: Record<string, Required<AgentConfig>> = {
      CLAUDE: {
        model: 'claude-sonnet-4-20250514',
        apiKey: process.env.ANTHROPIC_API_KEY || '',
        maxTokens: 8192,
        temperature: 0.7,
        timeout: 1800,
        customInstructions: '',
      },
      OPENAI: {
        model: 'gpt-4o',
        apiKey: process.env.OPENAI_API_KEY || '',
        maxTokens: 8192,
        temperature: 0.7,
        timeout: 1800,
        customInstructions: '',
      },
      GEMINI: {
        model: 'gemini-2.0-flash',
        apiKey: process.env.GOOGLE_API_KEY || '',
        maxTokens: 8192,
        temperature: 0.7,
        timeout: 1800,
        customInstructions: '',
      },
      CUSTOM: {
        model: 'custom',
        apiKey: '',
        maxTokens: 8192,
        temperature: 0.7,
        timeout: 1800,
        customInstructions: '',
      },
    };

    return {
      ...defaults[agentType] || defaults.CUSTOM,
      ...userConfig,
    } as Required<AgentConfig>;
  }

  private async setupAgentEnvironment(
    sandboxId: string,
    agentType: string,
    config: Required<AgentConfig>
  ): Promise<void> {
    // Set environment variables
    const envVars: Record<string, string> = {};

    switch (agentType) {
      case 'CLAUDE':
        envVars['ANTHROPIC_API_KEY'] = config.apiKey;
        break;
      case 'OPENAI':
        envVars['OPENAI_API_KEY'] = config.apiKey;
        break;
      case 'GEMINI':
        envVars['GOOGLE_API_KEY'] = config.apiKey;
        break;
    }

    // Write environment file
    const envContent = Object.entries(envVars)
      .map(([key, value]) => `export ${key}="${value}"`)
      .join('\n');

    await sandboxService.writeFile(sandboxId, '/workspace/.env', envContent);

    // Install agent CLI if needed
    switch (agentType) {
      case 'CLAUDE':
        await sandboxService.exec(
          sandboxId,
          'npm install -g @anthropic-ai/claude-code || true'
        );
        break;
      case 'OPENAI':
        await sandboxService.exec(
          sandboxId,
          'pip install openai-codegen || true'
        );
        break;
    }
  }

  private createAgentPrompt(task: { title: string; description: string }): string {
    return `
# Task: ${task.title}

## Description
${task.description}

## Instructions
1. Analyze the current codebase structure
2. Understand the requirements from the description
3. Plan your implementation approach
4. Make the necessary code changes
5. Run any available tests to verify your changes
6. If tests fail, fix the issues

## Important Notes
- Follow existing code style and conventions
- Add appropriate comments where necessary
- Do not break existing functionality
- Keep changes focused and minimal
`.trim();
  }
}

export const agentRunner = new AgentRunner();
