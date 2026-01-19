import { Sandbox as E2BSandbox } from '@e2b/code-interpreter';
import { v4 as uuidv4 } from 'uuid';

export interface SandboxConfig {
  cpu?: number;
  memoryMb?: number;
  timeoutSeconds: number;
  template?: string;
  envVars?: Record<string, string>;
}

export interface Sandbox {
  id: string;
  status: 'starting' | 'running' | 'stopping' | 'terminated';
  url?: string;
  createdAt: Date;
}

export interface ExecResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export interface FileInfo {
  path: string;
  name: string;
  isDir: boolean;
  size: number;
}

/**
 * Sandbox Service - E2B Integration
 *
 * Manages isolated development environments using E2B.dev
 * Each sandbox runs in a secure microVM with full Linux environment
 */
class SandboxService {
  private sandboxes: Map<string, { sandbox: Sandbox; e2b?: E2BSandbox }> = new Map();
  private useE2B: boolean;

  constructor() {
    // Enable E2B if API key is available
    this.useE2B = !!process.env.E2B_API_KEY;
    if (!this.useE2B) {
      console.warn('E2B_API_KEY not set - running in mock mode');
    }
  }

  async create(config: SandboxConfig): Promise<Sandbox> {
    const id = `sbx_${uuidv4().replace(/-/g, '').slice(0, 12)}`;
    const timeoutMs = config.timeoutSeconds * 1000;

    const sandbox: Sandbox = {
      id,
      status: 'starting',
      createdAt: new Date(),
    };

    this.sandboxes.set(id, { sandbox });

    try {
      if (this.useE2B) {
        // Create E2B sandbox with code interpreter template
        const e2bSandbox = await E2BSandbox.create({
          timeoutMs,
          envVars: config.envVars,
        });

        sandbox.status = 'running';
        sandbox.url = `https://${e2bSandbox.getHost(3000)}`;
        this.sandboxes.set(id, { sandbox, e2b: e2bSandbox });

        console.log(`[E2B] Sandbox ${id} created - URL: ${sandbox.url}`);
      } else {
        // Mock mode for development
        sandbox.status = 'running';
        sandbox.url = `https://${id}.sandbox.terragon.local`;
        console.log(`[Mock] Sandbox ${id} created`);
      }

      // Set timeout for automatic termination
      setTimeout(() => {
        this.terminate(id).catch(console.error);
      }, timeoutMs);

      return sandbox;
    } catch (error) {
      sandbox.status = 'terminated';
      this.sandboxes.delete(id);
      throw new Error(`Failed to create sandbox: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async exec(sandboxId: string, command: string, cwd?: string): Promise<ExecResult> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    console.log(`[Sandbox ${sandboxId}] Executing: ${command}`);

    if (this.useE2B && entry.e2b) {
      try {
        const result = await entry.e2b.notebook.execCell(
          cwd ? `cd ${cwd} && ${command}` : command
        );

        const stdout = result.logs.stdout.join('\n');
        const stderr = result.logs.stderr.join('\n');

        return {
          stdout,
          stderr,
          exitCode: result.error ? 1 : 0,
        };
      } catch (error) {
        return {
          stdout: '',
          stderr: error instanceof Error ? error.message : 'Execution failed',
          exitCode: 1,
        };
      }
    }

    // Mock mode
    return {
      stdout: `[Mock] Executed: ${command}`,
      stderr: '',
      exitCode: 0,
    };
  }

  async writeFile(sandboxId: string, path: string, content: string): Promise<void> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    console.log(`[Sandbox ${sandboxId}] Writing file: ${path}`);

    if (this.useE2B && entry.e2b) {
      await entry.e2b.files.write(path, content);
    }
  }

  async readFile(sandboxId: string, path: string): Promise<string> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    console.log(`[Sandbox ${sandboxId}] Reading file: ${path}`);

    if (this.useE2B && entry.e2b) {
      return await entry.e2b.files.read(path);
    }

    return '';
  }

  async listFiles(sandboxId: string, path: string): Promise<FileInfo[]> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    if (this.useE2B && entry.e2b) {
      const files = await entry.e2b.files.list(path);
      return files.map((f) => ({
        path: `${path}/${f.name}`,
        name: f.name,
        isDir: f.type === 'dir',
        size: 0,
      }));
    }

    return [];
  }

  async fileExists(sandboxId: string, path: string): Promise<boolean> {
    try {
      await this.readFile(sandboxId, path);
      return true;
    } catch {
      return false;
    }
  }

  async uploadFile(
    sandboxId: string,
    localPath: string,
    remotePath: string
  ): Promise<void> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    console.log(`[Sandbox ${sandboxId}] Uploading: ${localPath} -> ${remotePath}`);

    if (this.useE2B && entry.e2b) {
      const fs = await import('fs/promises');
      const content = await fs.readFile(localPath, 'utf-8');
      await entry.e2b.files.write(remotePath, content);
    }
  }

  async cloneRepository(
    sandboxId: string,
    repoUrl: string,
    targetDir: string = '/home/user/repo'
  ): Promise<void> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    console.log(`[Sandbox ${sandboxId}] Cloning repository: ${repoUrl}`);

    await this.exec(sandboxId, `git clone ${repoUrl} ${targetDir}`);
  }

  async installDependencies(
    sandboxId: string,
    cwd: string = '/home/user/repo'
  ): Promise<ExecResult> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    // Detect package manager and install
    const hasPackageJson = await this.fileExists(sandboxId, `${cwd}/package.json`);
    const hasPyProject = await this.fileExists(sandboxId, `${cwd}/pyproject.toml`);
    const hasRequirements = await this.fileExists(sandboxId, `${cwd}/requirements.txt`);

    if (hasPackageJson) {
      const hasYarnLock = await this.fileExists(sandboxId, `${cwd}/yarn.lock`);
      const hasPnpmLock = await this.fileExists(sandboxId, `${cwd}/pnpm-lock.yaml`);

      if (hasPnpmLock) {
        return this.exec(sandboxId, 'pnpm install', cwd);
      } else if (hasYarnLock) {
        return this.exec(sandboxId, 'yarn install', cwd);
      } else {
        return this.exec(sandboxId, 'npm install', cwd);
      }
    }

    if (hasPyProject) {
      return this.exec(sandboxId, 'pip install -e .', cwd);
    }

    if (hasRequirements) {
      return this.exec(sandboxId, 'pip install -r requirements.txt', cwd);
    }

    return { stdout: 'No dependencies to install', stderr: '', exitCode: 0 };
  }

  async runTests(
    sandboxId: string,
    cwd: string = '/home/user/repo'
  ): Promise<ExecResult> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry || entry.sandbox.status !== 'running') {
      throw new Error(`Sandbox ${sandboxId} not available`);
    }

    // Detect test framework and run
    const hasPackageJson = await this.fileExists(sandboxId, `${cwd}/package.json`);
    const hasPytest = await this.fileExists(sandboxId, `${cwd}/pytest.ini`);

    if (hasPackageJson) {
      return this.exec(sandboxId, 'npm test', cwd);
    }

    if (hasPytest || (await this.fileExists(sandboxId, `${cwd}/tests`))) {
      return this.exec(sandboxId, 'pytest', cwd);
    }

    return { stdout: 'No tests found', stderr: '', exitCode: 0 };
  }

  async terminate(sandboxId: string): Promise<void> {
    const entry = this.sandboxes.get(sandboxId);

    if (!entry) {
      console.log(`Sandbox ${sandboxId} already terminated or not found`);
      return;
    }

    entry.sandbox.status = 'stopping';

    try {
      if (this.useE2B && entry.e2b) {
        await entry.e2b.kill();
      }
    } catch (error) {
      console.error(`Error terminating E2B sandbox: ${error}`);
    }

    entry.sandbox.status = 'terminated';
    this.sandboxes.delete(sandboxId);

    console.log(`[Sandbox ${sandboxId}] Terminated`);
  }

  async getStatus(sandboxId: string): Promise<Sandbox | null> {
    const entry = this.sandboxes.get(sandboxId);
    return entry?.sandbox || null;
  }

  async getActiveSandboxes(): Promise<Sandbox[]> {
    return Array.from(this.sandboxes.values())
      .map((e) => e.sandbox)
      .filter((s) => s.status === 'running');
  }
}

export const sandboxService = new SandboxService();
