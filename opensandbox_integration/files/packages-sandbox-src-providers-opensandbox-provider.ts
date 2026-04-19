import {
  BackgroundCommandOptions,
  CreateSandboxOptions,
  ISandboxProvider,
  ISandboxSession,
} from "../types";
import {
  ConnectionConfig,
  Sandbox as OpenSandbox,
  type Sandbox as OpenSandboxInstance,
} from "@alibaba-group/opensandbox";
import path from "path";
import { retryAsync } from "@terragon/utils/retry";

const HOME_DIR = "root";
const REPO_DIR = "repo";
const DEFAULT_DIR = `/${HOME_DIR}`;

const OPEN_SANDBOX_DOMAIN =
  process.env.OPEN_SANDBOX_DOMAIN || "localhost:8080";
const OPEN_SANDBOX_API_KEY = process.env.OPEN_SANDBOX_API_KEY || "";
const OPEN_SANDBOX_PROTOCOL =
  (process.env.OPEN_SANDBOX_PROTOCOL as "http" | "https") || "http";
const OPEN_SANDBOX_IMAGE =
  process.env.OPEN_SANDBOX_IMAGE ||
  "opensandbox/code-interpreter:v1.0.2";
const OPEN_SANDBOX_USE_SERVER_PROXY =
  process.env.OPEN_SANDBOX_USE_SERVER_PROXY === "1" ||
  process.env.OPEN_SANDBOX_USE_SERVER_PROXY === "true";

const SANDBOX_TIMEOUT_SECONDS =
  parseInt(process.env.OPEN_SANDBOX_TIMEOUT_SECONDS || "", 10) || 60 * 45;

function buildConnectionConfig(): ConnectionConfig {
  return new ConnectionConfig({
    domain: OPEN_SANDBOX_DOMAIN,
    protocol: OPEN_SANDBOX_PROTOCOL,
    apiKey: OPEN_SANDBOX_API_KEY || undefined,
    useServerProxy: OPEN_SANDBOX_USE_SERVER_PROXY,
    requestTimeoutSeconds: Math.min(600, SANDBOX_TIMEOUT_SECONDS + 120),
  });
}

function envArrayToRecord(
  vars: Array<{ key: string; value: string }>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const { key, value } of vars) {
    out[key] = value;
  }
  return out;
}

function resolvePath(filePath: string, cwdRel: string): string {
  if (filePath.startsWith("/")) {
    return filePath;
  }
  const base = cwdRel.startsWith("/")
    ? cwdRel
    : path.posix.join(DEFAULT_DIR, cwdRel);
  return path.posix.join(base, filePath);
}

function executionToStdout(execution: {
  logs: { stdout: { text: string }[]; stderr: { text: string }[] };
  error?: { name: string; value: string; traceback: string[] };
}): string {
  return execution.logs.stdout.map((m) => m.text).join("");
}

function executionToStderr(execution: {
  logs: { stderr: { text: string }[] };
}): string {
  return execution.logs.stderr.map((m) => m.text).join("");
}

class OpenSandboxSession implements ISandboxSession {
  public readonly sandboxProvider = "opensandbox" as const;

  constructor(
    private sbx: OpenSandboxInstance,
    public readonly sandboxId: string,
  ) {}

  get homeDir(): string {
    return HOME_DIR;
  }

  get repoDir(): string {
    return REPO_DIR;
  }

  async hibernate(): Promise<void> {
    await this.sbx.pause();
  }

  async runCommand(
    command: string,
    options?: {
      env?: Record<string, string>;
      cwd?: string;
      timeoutMs?: number;
      onStdout?: (data: string) => void;
      onStderr?: (data: string) => void;
    },
  ): Promise<string> {
    const workDir = options?.cwd || REPO_DIR;
    const workingDirectory = workDir.startsWith("/")
      ? workDir
      : path.posix.join(DEFAULT_DIR, workDir);
    const timeoutSeconds =
      options?.timeoutMs && options.timeoutMs > 0
        ? Math.max(1, Math.ceil(options.timeoutMs / 1000))
        : undefined;

    const execution = await this.sbx.commands.run(
      command,
      {
        workingDirectory,
        timeoutSeconds,
      },
      {
        onStdout: options?.onStdout
          ? (m) => options.onStdout!(m.text)
          : undefined,
        onStderr: options?.onStderr
          ? (m) => options.onStderr!(m.text)
          : undefined,
      },
    );

    const stdout = executionToStdout(execution);
    const stderr = executionToStderr(execution);

    let exitCode: number | null = null;
    if (execution.id) {
      try {
        const status = await this.sbx.commands.getCommandStatus(execution.id);
        exitCode = status.exitCode ?? null;
      } catch {
        /* best-effort */
      }
    }

    if (execution.error) {
      const trace = execution.error.traceback?.join("\n") ?? "";
      throw new Error(
        `Command failed\n\nstdout:\n${stdout || "(empty)"}\nstderr:\n${stderr || "(empty)"}\nerror:\n${execution.error.name}: ${execution.error.value}\n${trace}`,
      );
    }

    if (exitCode !== null && exitCode !== 0) {
      throw new Error(
        `Command failed with exit code ${exitCode}\n\nstdout:\n${stdout || "(empty)"}\nstderr:\n${stderr || "(empty)"}`,
      );
    }

    return stdout;
  }

  async runBackgroundCommand(
    command: string,
    options?: BackgroundCommandOptions,
  ): Promise<void> {
    const workDirPath = path.posix.join(DEFAULT_DIR, REPO_DIR);
    const timeoutSeconds =
      options?.timeoutMs && options.timeoutMs > 0
        ? Math.max(1, Math.ceil(options.timeoutMs / 1000))
        : undefined;

    await this.sbx.commands.run(
      command,
      {
        workingDirectory: workDirPath,
        background: true,
        timeoutSeconds,
      },
      {
        onStdout: options?.onOutput
          ? (m) => options.onOutput!(m.text)
          : undefined,
        onStderr: options?.onOutput
          ? (m) => options.onOutput!(m.text)
          : undefined,
      },
    );
  }

  async shutdown(): Promise<void> {
    try {
      await this.sbx.kill();
    } finally {
      await this.sbx.close().catch(() => {});
    }
  }

  async readTextFile(filePath: string): Promise<string> {
    const full = resolvePath(filePath, REPO_DIR);
    return await this.sbx.files.readFile(full);
  }

  async writeTextFile(filePath: string, content: string): Promise<void> {
    const full = resolvePath(filePath, REPO_DIR);
    const dir = path.posix.dirname(full);
    if (dir !== "/" && dir !== ".") {
      await this.sbx.files.createDirectories([{ path: dir, mode: 0o755 }]);
    }
    await this.sbx.files.writeFiles([
      { path: full, data: content, mode: 0o644 },
    ]);
  }

  async writeFile(filePath: string, content: Uint8Array): Promise<void> {
    const full = resolvePath(filePath, REPO_DIR);
    const dir = path.posix.dirname(full);
    if (dir !== "/" && dir !== ".") {
      await this.sbx.files.createDirectories([{ path: dir, mode: 0o755 }]);
    }
    await this.sbx.files.writeFiles([
      { path: full, data: content, mode: 0o644 },
    ]);
  }
}

async function connectWithRetry(
  sandboxId: string,
  config: ConnectionConfig,
): Promise<OpenSandboxInstance> {
  return await retryAsync(
    async () =>
      OpenSandbox.connect({
        sandboxId,
        connectionConfig: config,
      }),
    {
      label: `opensandbox connect ${sandboxId}`,
      maxAttempts: 4,
      delayMs: 1500,
    },
  );
}

export class OpenSandboxProvider implements ISandboxProvider {
  async getSandboxOrNull(sandboxId: string): Promise<ISandboxSession | null> {
    const config = buildConnectionConfig().withTransportIfMissing();
    try {
      const sbx = await connectWithRetry(sandboxId, config);
      const info = await sbx.getInfo();
      if (info.status.state === "Paused") {
        const resumed = await sbx.resume();
        await sbx.close().catch(() => {});
        return new OpenSandboxSession(resumed, sandboxId);
      }
      return new OpenSandboxSession(sbx, sandboxId);
    } catch (e) {
      console.warn(`[opensandbox] Failed to resume ${sandboxId}:`, e);
      await config.closeTransport().catch(() => {});
      return null;
    }
  }

  async getOrCreateSandbox(
    sandboxId: string | null,
    options: CreateSandboxOptions,
  ): Promise<ISandboxSession> {
    const baseConfig = buildConnectionConfig().withTransportIfMissing();

    if (sandboxId) {
      const session = await this.getSandboxOrNull(sandboxId);
      if (session) {
        return session;
      }
      throw new Error(`OpenSandbox ${sandboxId} not found`);
    }

    const env = envArrayToRecord(options.environmentVariables ?? []);

    let sbx: OpenSandboxInstance | null = null;
    try {
      sbx = await retryAsync(
        async () =>
          OpenSandbox.create({
            connectionConfig: baseConfig,
            image: OPEN_SANDBOX_IMAGE,
            env,
            timeoutSeconds: SANDBOX_TIMEOUT_SECONDS,
            readyTimeoutSeconds: 120,
          }),
        {
          label: "opensandbox create",
          maxAttempts: 3,
          delayMs: 2000,
        },
      );
      return new OpenSandboxSession(sbx, sbx.id);
    } catch (err) {
      if (sbx) {
        try {
          await sbx.kill();
        } catch {
          /* ignore */
        }
        await sbx.close().catch(() => {});
      } else {
        await baseConfig.closeTransport().catch(() => {});
      }
      throw err;
    }
  }

  async hibernateById(sandboxId: string): Promise<void> {
    const config = buildConnectionConfig().withTransportIfMissing();
    try {
      const sbx = await connectWithRetry(sandboxId, config);
      try {
        await sbx.pause();
      } finally {
        await sbx.close();
      }
    } catch (e) {
      console.error(`[opensandbox] hibernate failed for ${sandboxId}:`, e);
      await config.closeTransport().catch(() => {});
      throw e;
    }
  }

  async extendLife(sandboxId: string): Promise<void> {
    const config = buildConnectionConfig().withTransportIfMissing();
    try {
      const sbx = await connectWithRetry(sandboxId, config);
      try {
        await sbx.renew(SANDBOX_TIMEOUT_SECONDS);
      } finally {
        await sbx.close();
      }
    } catch (e) {
      console.warn(`[opensandbox] renew failed for ${sandboxId}:`, e);
      await config.closeTransport().catch(() => {});
    }
  }
}
