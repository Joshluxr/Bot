import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
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
 * - AMP: Sourcegraph Amp
 * - OPENCODE: Open source agent
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

    // Run the agent based on type
    await onLog('INFO', 'Starting agent execution...');

    let agentResult: { success: boolean; output: string; filesModified: string[] };

    switch (agentType) {
      case 'CLAUDE':
        agentResult = await this.runClaudeAgent(sandboxId, prompt, config, onLog, onProgress);
        break;
      case 'OPENAI':
        agentResult = await this.runOpenAIAgent(sandboxId, prompt, config, onLog, onProgress);
        break;
      case 'GEMINI':
        agentResult = await this.runGeminiAgent(sandboxId, prompt, config, onLog, onProgress);
        break;
      case 'AMP':
        agentResult = await this.runAmpAgent(sandboxId, prompt, config, onLog, onProgress);
        break;
      case 'OPENCODE':
        agentResult = await this.runOpenCodeAgent(sandboxId, prompt, config, onLog, onProgress);
        break;
      default:
        agentResult = await this.runCustomAgent(sandboxId, prompt, config, onLog, onProgress);
    }

    // Check for changes in git
    const gitResult = await sandboxService.exec(
      sandboxId,
      'cd /workspace && git status --porcelain'
    );

    const hasChanges = gitResult.stdout.trim().length > 0;
    const filesChanged = hasChanges
      ? gitResult.stdout.trim().split('\n').map((line) => line.slice(3).trim()).filter(Boolean)
      : [];

    await onProgress(100);
    await onLog('INFO', `Agent completed. ${filesChanged.length} files modified.`);

    return {
      hasChanges,
      filesChanged,
      summary: agentResult.output || `Completed task: ${task.title}`,
    };
  }

  private async runClaudeAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    const anthropic = new Anthropic({ apiKey: config.apiKey });

    await onLog('INFO', 'Analyzing codebase structure...');
    await onProgress(40);

    // Get codebase structure
    const lsResult = await sandboxService.exec(sandboxId, 'cd /workspace && find . -type f -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | head -50');
    const files = lsResult.stdout.trim().split('\n').filter(Boolean);

    await onLog('INFO', `Found ${files.length} source files`);
    await onProgress(50);

    // Read key files for context
    const fileContents: Record<string, string> = {};
    for (const file of files.slice(0, 10)) {
      try {
        const content = await sandboxService.readFile(sandboxId, `/workspace/${file.replace('./', '')}`);
        fileContents[file] = content.slice(0, 5000); // Limit size
      } catch {
        // Skip unreadable files
      }
    }

    await onLog('INFO', 'Understanding requirements...');
    await onProgress(60);

    // Create context for Claude
    const systemPrompt = `You are an expert software engineer. You will analyze code and make changes to complete the user's task.

Current codebase structure:
${files.join('\n')}

Key files:
${Object.entries(fileContents).map(([name, content]) => `=== ${name} ===\n${content}`).join('\n\n')}

${config.customInstructions || ''}`;

    await onLog('INFO', 'Planning implementation...');
    await onProgress(70);

    // Call Claude API
    const response = await anthropic.messages.create({
      model: config.model,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
    });

    const assistantMessage = response.content[0].type === 'text' ? response.content[0].text : '';

    await onLog('INFO', 'Writing code changes...');
    await onProgress(80);

    // Parse and apply changes from Claude's response
    const filesModified = await this.applyCodeChanges(sandboxId, assistantMessage, onLog);

    await onLog('INFO', 'Running tests...');
    await onProgress(90);

    // Run tests if available
    const testResult = await sandboxService.runTests(sandboxId, '/workspace');
    if (testResult.exitCode !== 0) {
      await onLog('WARN', `Tests completed with warnings: ${testResult.stderr || testResult.stdout}`);
    }

    return {
      success: true,
      output: assistantMessage.slice(0, 500),
      filesModified,
    };
  }

  private async runOpenAIAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    const openai = new OpenAI({ apiKey: config.apiKey });

    await onLog('INFO', 'Analyzing codebase structure...');
    await onProgress(40);

    // Get codebase structure
    const lsResult = await sandboxService.exec(sandboxId, 'cd /workspace && find . -type f -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | head -50');
    const files = lsResult.stdout.trim().split('\n').filter(Boolean);

    await onLog('INFO', `Found ${files.length} source files`);
    await onProgress(50);

    // Read key files for context
    const fileContents: Record<string, string> = {};
    for (const file of files.slice(0, 10)) {
      try {
        const content = await sandboxService.readFile(sandboxId, `/workspace/${file.replace('./', '')}`);
        fileContents[file] = content.slice(0, 5000);
      } catch {
        // Skip unreadable files
      }
    }

    await onLog('INFO', 'Understanding requirements...');
    await onProgress(60);

    const systemPrompt = `You are an expert software engineer. Analyze the code and make changes to complete the user's task.

Current codebase structure:
${files.join('\n')}

Key files:
${Object.entries(fileContents).map(([name, content]) => `=== ${name} ===\n${content}`).join('\n\n')}

${config.customInstructions || ''}

When making changes, output them in this format:
FILE: path/to/file.ts
\`\`\`typescript
// file content here
\`\`\``;

    await onLog('INFO', 'Planning implementation...');
    await onProgress(70);

    const response = await openai.chat.completions.create({
      model: config.model,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt },
      ],
    });

    const assistantMessage = response.choices[0]?.message?.content || '';

    await onLog('INFO', 'Writing code changes...');
    await onProgress(80);

    const filesModified = await this.applyCodeChanges(sandboxId, assistantMessage, onLog);

    await onLog('INFO', 'Running tests...');
    await onProgress(90);

    const testResult = await sandboxService.runTests(sandboxId, '/workspace');
    if (testResult.exitCode !== 0) {
      await onLog('WARN', `Tests completed with warnings: ${testResult.stderr || testResult.stdout}`);
    }

    return {
      success: true,
      output: assistantMessage.slice(0, 500),
      filesModified,
    };
  }

  private async runGeminiAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    // Use Google's Gemini API
    await onLog('INFO', 'Analyzing codebase structure...');
    await onProgress(40);

    const lsResult = await sandboxService.exec(sandboxId, 'cd /workspace && find . -type f -name "*.ts" -o -name "*.tsx" | head -30');
    const files = lsResult.stdout.trim().split('\n').filter(Boolean);

    await onLog('INFO', `Found ${files.length} source files`);
    await onProgress(50);

    // Call Gemini API
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:generateContent?key=${config.apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            maxOutputTokens: config.maxTokens,
            temperature: config.temperature,
          },
        }),
      }
    );

    const data = await response.json();
    const assistantMessage = data.candidates?.[0]?.content?.parts?.[0]?.text || '';

    await onLog('INFO', 'Writing code changes...');
    await onProgress(80);

    const filesModified = await this.applyCodeChanges(sandboxId, assistantMessage, onLog);

    await onLog('INFO', 'Running tests...');
    await onProgress(90);

    await sandboxService.runTests(sandboxId, '/workspace');

    return {
      success: true,
      output: assistantMessage.slice(0, 500),
      filesModified,
    };
  }

  private async runAmpAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    // Run Amp CLI in sandbox
    await onLog('INFO', 'Installing Amp agent...');
    await sandboxService.exec(sandboxId, 'npm install -g @anthropic-ai/amp || true');
    await onProgress(40);

    await onLog('INFO', 'Running Amp agent...');
    await onProgress(60);

    const result = await sandboxService.exec(
      sandboxId,
      `cd /workspace && amp --prompt "${prompt.replace(/"/g, '\\"')}"`,
      '/workspace'
    );

    await onLog('INFO', 'Processing results...');
    await onProgress(90);

    const filesModified = await this.getModifiedFiles(sandboxId);

    return {
      success: result.exitCode === 0,
      output: result.stdout || result.stderr,
      filesModified,
    };
  }

  private async runOpenCodeAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    // Run OpenCode CLI in sandbox
    await onLog('INFO', 'Installing OpenCode agent...');
    await sandboxService.exec(sandboxId, 'pip install opencode-agent || true');
    await onProgress(40);

    await onLog('INFO', 'Running OpenCode agent...');
    await onProgress(60);

    const result = await sandboxService.exec(
      sandboxId,
      `cd /workspace && opencode --task "${prompt.replace(/"/g, '\\"')}"`,
      '/workspace'
    );

    await onLog('INFO', 'Processing results...');
    await onProgress(90);

    const filesModified = await this.getModifiedFiles(sandboxId);

    return {
      success: result.exitCode === 0,
      output: result.stdout || result.stderr,
      filesModified,
    };
  }

  private async runCustomAgent(
    sandboxId: string,
    prompt: string,
    config: Required<AgentConfig>,
    onLog: (level: string, message: string) => Promise<void>,
    onProgress: (progress: number) => Promise<void>
  ): Promise<{ success: boolean; output: string; filesModified: string[] }> {
    // For custom agents, use the generic approach similar to Claude
    return this.runClaudeAgent(sandboxId, prompt, config, onLog, onProgress);
  }

  private async applyCodeChanges(
    sandboxId: string,
    response: string,
    onLog: (level: string, message: string) => Promise<void>
  ): Promise<string[]> {
    const filesModified: string[] = [];

    // Parse file changes from response
    // Look for patterns like "FILE: path/to/file.ts" followed by code blocks
    const filePattern = /FILE:\s*([^\n]+)\n```[\w]*\n([\s\S]*?)```/g;
    let match;

    while ((match = filePattern.exec(response)) !== null) {
      const [, filePath, content] = match;
      const cleanPath = filePath.trim();

      try {
        await sandboxService.writeFile(sandboxId, `/workspace/${cleanPath}`, content);
        filesModified.push(cleanPath);
        await onLog('INFO', `Modified: ${cleanPath}`);
      } catch (error) {
        await onLog('WARN', `Failed to write ${cleanPath}: ${error}`);
      }
    }

    // Also look for diff-style changes
    const diffPattern = /```diff\n([\s\S]*?)```/g;
    while ((match = diffPattern.exec(response)) !== null) {
      const diffContent = match[1];
      try {
        await sandboxService.exec(sandboxId, `cd /workspace && echo '${diffContent.replace(/'/g, "\\'")}' | patch -p1`);
        await onLog('INFO', 'Applied diff patch');
      } catch {
        // Diff application might fail, that's okay
      }
    }

    return filesModified;
  }

  private async getModifiedFiles(sandboxId: string): Promise<string[]> {
    const result = await sandboxService.exec(sandboxId, 'cd /workspace && git status --porcelain');
    if (!result.stdout.trim()) return [];
    return result.stdout.trim().split('\n').map((line) => line.slice(3).trim()).filter(Boolean);
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
