# InsForge Adaptation: Concrete Implementation Guide

## What to Adapt (Priority Order)

### 1. Enhanced MCP Server (HIGH PRIORITY)
**Current State**: Terragon has a basic MCP server with only 2 tools (`SuggestFollowupTask`, `PermissionPrompt`)

**Adapt From InsForge**: Full backend operations via MCP

```
packages/mcp-server/src/
├── index.ts              # Main server (enhance existing)
├── tools/
│   ├── sandbox.ts        # Sandbox management tools
│   ├── database.ts       # Database query tools
│   ├── storage.ts        # File storage tools
│   ├── agent.ts          # Agent execution tools
│   └── github.ts         # GitHub integration tools
└── resources/
    └── docs.ts           # Documentation resources
```

### 2. PostgREST Integration (MEDIUM PRIORITY)
**Why**: Allow AI agents to create dynamic APIs without code changes

**Adapt From InsForge**: PostgREST service + API proxy

### 3. Serverless Functions Runtime (MEDIUM PRIORITY)
**Why**: Let users deploy custom backend logic

**Adapt From InsForge**: Deno-based function runtime

### 4. Schema Patterns (LOW PRIORITY)
**Why**: Provide AI agents with best-practice database patterns

**Adapt From InsForge**: Claude plugin with schema patterns

---

## Implementation Details

### 1. Enhanced MCP Server

#### File: `packages/mcp-server/src/tools/sandbox.ts`

```typescript
import { z } from "zod";

export const sandboxTools = [
  {
    name: "CreateSandbox",
    description: `Create a new development sandbox for code execution.

Use this when:
- User wants to run code in an isolated environment
- Need to test code changes safely
- Setting up a new development environment`,
    inputSchema: {
      type: "object",
      properties: {
        provider: {
          type: "string",
          enum: ["e2b", "daytona"],
          description: "Sandbox provider (e2b for cloud, daytona for local)",
        },
        size: {
          type: "string",
          enum: ["small", "medium", "large"],
          description: "Sandbox resource allocation",
        },
        template: {
          type: "string",
          description: "Base template/image for the sandbox",
        },
        timeout: {
          type: "number",
          description: "Sandbox timeout in minutes (default: 60)",
        },
      },
      required: ["provider"],
    },
  },
  {
    name: "ExecuteInSandbox",
    description: `Execute a command in an existing sandbox.

Use this when:
- Running build commands (npm install, cargo build, etc.)
- Executing tests
- Running scripts`,
    inputSchema: {
      type: "object",
      properties: {
        sandboxId: {
          type: "string",
          description: "ID of the target sandbox",
        },
        command: {
          type: "string",
          description: "Command to execute",
        },
        workingDir: {
          type: "string",
          description: "Working directory for command execution",
        },
        timeout: {
          type: "number",
          description: "Command timeout in seconds",
        },
      },
      required: ["sandboxId", "command"],
    },
  },
  {
    name: "GetSandboxStatus",
    description: "Get the current status of a sandbox",
    inputSchema: {
      type: "object",
      properties: {
        sandboxId: {
          type: "string",
          description: "ID of the sandbox to check",
        },
      },
      required: ["sandboxId"],
    },
  },
  {
    name: "StopSandbox",
    description: "Stop and clean up a sandbox",
    inputSchema: {
      type: "object",
      properties: {
        sandboxId: {
          type: "string",
          description: "ID of the sandbox to stop",
        },
        saveSnapshot: {
          type: "boolean",
          description: "Whether to save a snapshot before stopping",
        },
      },
      required: ["sandboxId"],
    },
  },
];
```

#### File: `packages/mcp-server/src/tools/database.ts`

```typescript
export const databaseTools = [
  {
    name: "QueryDatabase",
    description: `Execute a read-only SQL query against the database.

Use this when:
- Fetching data for analysis
- Checking existing records
- Generating reports

IMPORTANT: Only SELECT queries are allowed. For modifications, use dedicated tools.`,
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "SQL SELECT query to execute",
        },
        params: {
          type: "array",
          items: { type: "string" },
          description: "Query parameters for prepared statements",
        },
        limit: {
          type: "number",
          description: "Maximum rows to return (default: 100)",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "ListTables",
    description: "List all tables in the database with their schemas",
    inputSchema: {
      type: "object",
      properties: {
        schema: {
          type: "string",
          description: "Database schema to list (default: public)",
        },
        includeColumns: {
          type: "boolean",
          description: "Include column details",
        },
      },
    },
  },
  {
    name: "DescribeTable",
    description: "Get detailed information about a specific table",
    inputSchema: {
      type: "object",
      properties: {
        tableName: {
          type: "string",
          description: "Name of the table to describe",
        },
        includeIndexes: {
          type: "boolean",
          description: "Include index information",
        },
        includeForeignKeys: {
          type: "boolean",
          description: "Include foreign key relationships",
        },
      },
      required: ["tableName"],
    },
  },
];
```

#### File: `packages/mcp-server/src/tools/agent.ts`

```typescript
export const agentTools = [
  {
    name: "RunAgent",
    description: `Spawn an AI agent to perform a task.

Use this when:
- Delegating complex tasks to specialized agents
- Running parallel workloads
- Performing long-running operations

Available agent types:
- code-reviewer: Review code for quality and issues
- tester: Run and analyze tests
- researcher: Research technical topics
- debugger: Debug issues and analyze logs
- planner: Create implementation plans`,
    inputSchema: {
      type: "object",
      properties: {
        agentType: {
          type: "string",
          enum: ["code-reviewer", "tester", "researcher", "debugger", "planner"],
          description: "Type of agent to spawn",
        },
        task: {
          type: "string",
          description: "Task description for the agent",
        },
        context: {
          type: "object",
          description: "Additional context for the agent",
        },
        sandboxId: {
          type: "string",
          description: "Sandbox ID if agent needs code execution",
        },
        async: {
          type: "boolean",
          description: "Run agent asynchronously (default: false)",
        },
      },
      required: ["agentType", "task"],
    },
  },
  {
    name: "GetAgentStatus",
    description: "Check the status of a running agent task",
    inputSchema: {
      type: "object",
      properties: {
        taskId: {
          type: "string",
          description: "ID of the agent task",
        },
      },
      required: ["taskId"],
    },
  },
];
```

#### File: `packages/mcp-server/src/tools/storage.ts`

```typescript
export const storageTools = [
  {
    name: "UploadFile",
    description: `Upload a file to cloud storage (R2/S3).

Use this when:
- Storing user uploads
- Saving generated artifacts
- Backing up important files`,
    inputSchema: {
      type: "object",
      properties: {
        bucket: {
          type: "string",
          description: "Storage bucket name",
        },
        key: {
          type: "string",
          description: "File path/key in the bucket",
        },
        content: {
          type: "string",
          description: "File content (base64 for binary)",
        },
        contentType: {
          type: "string",
          description: "MIME type of the file",
        },
        isBase64: {
          type: "boolean",
          description: "Whether content is base64 encoded",
        },
      },
      required: ["bucket", "key", "content"],
    },
  },
  {
    name: "DownloadFile",
    description: "Download a file from cloud storage",
    inputSchema: {
      type: "object",
      properties: {
        bucket: {
          type: "string",
          description: "Storage bucket name",
        },
        key: {
          type: "string",
          description: "File path/key in the bucket",
        },
        asBase64: {
          type: "boolean",
          description: "Return content as base64 (for binary files)",
        },
      },
      required: ["bucket", "key"],
    },
  },
  {
    name: "ListFiles",
    description: "List files in a storage bucket",
    inputSchema: {
      type: "object",
      properties: {
        bucket: {
          type: "string",
          description: "Storage bucket name",
        },
        prefix: {
          type: "string",
          description: "Filter files by prefix/path",
        },
        limit: {
          type: "number",
          description: "Maximum files to return",
        },
      },
      required: ["bucket"],
    },
  },
  {
    name: "DeleteFile",
    description: "Delete a file from cloud storage",
    inputSchema: {
      type: "object",
      properties: {
        bucket: {
          type: "string",
          description: "Storage bucket name",
        },
        key: {
          type: "string",
          description: "File path/key to delete",
        },
      },
      required: ["bucket", "key"],
    },
  },
];
```

#### File: `packages/mcp-server/src/tools/github.ts`

```typescript
export const githubTools = [
  {
    name: "CreatePullRequest",
    description: `Create a GitHub Pull Request.

Use this when:
- Submitting code changes for review
- Proposing feature additions
- Submitting bug fixes`,
    inputSchema: {
      type: "object",
      properties: {
        owner: {
          type: "string",
          description: "Repository owner",
        },
        repo: {
          type: "string",
          description: "Repository name",
        },
        title: {
          type: "string",
          description: "PR title",
        },
        body: {
          type: "string",
          description: "PR description (markdown)",
        },
        head: {
          type: "string",
          description: "Source branch",
        },
        base: {
          type: "string",
          description: "Target branch (default: main)",
        },
        draft: {
          type: "boolean",
          description: "Create as draft PR",
        },
      },
      required: ["owner", "repo", "title", "head"],
    },
  },
  {
    name: "GetPullRequest",
    description: "Get details of a Pull Request",
    inputSchema: {
      type: "object",
      properties: {
        owner: { type: "string" },
        repo: { type: "string" },
        prNumber: { type: "number" },
      },
      required: ["owner", "repo", "prNumber"],
    },
  },
  {
    name: "ListPullRequests",
    description: "List Pull Requests for a repository",
    inputSchema: {
      type: "object",
      properties: {
        owner: { type: "string" },
        repo: { type: "string" },
        state: {
          type: "string",
          enum: ["open", "closed", "all"],
        },
        limit: { type: "number" },
      },
      required: ["owner", "repo"],
    },
  },
  {
    name: "CreateIssue",
    description: "Create a GitHub Issue",
    inputSchema: {
      type: "object",
      properties: {
        owner: { type: "string" },
        repo: { type: "string" },
        title: { type: "string" },
        body: { type: "string" },
        labels: {
          type: "array",
          items: { type: "string" },
        },
      },
      required: ["owner", "repo", "title"],
    },
  },
];
```

#### Updated: `packages/mcp-server/src/index.ts`

```typescript
#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { sandboxTools } from "./tools/sandbox.js";
import { databaseTools } from "./tools/database.js";
import { agentTools } from "./tools/agent.js";
import { storageTools } from "./tools/storage.js";
import { githubTools } from "./tools/github.js";

// Import handlers
import { handleSandboxTool } from "./handlers/sandbox.js";
import { handleDatabaseTool } from "./handlers/database.js";
import { handleAgentTool } from "./handlers/agent.js";
import { handleStorageTool } from "./handlers/storage.js";
import { handleGithubTool } from "./handlers/github.js";

const server = new Server(
  {
    name: "terragon-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  },
);

// Combine all tools
const allTools = [
  // Existing tools
  {
    name: "SuggestFollowupTask",
    description: "Suggest a follow-up task to the user...",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string", description: "Task title" },
        description: { type: "string", description: "Task description" },
      },
      required: ["title", "description"],
    },
  },
  // New tools from InsForge patterns
  ...sandboxTools,
  ...databaseTools,
  ...agentTools,
  ...storageTools,
  ...githubTools,
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: allTools,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Route to appropriate handler
  if (name.startsWith("Sandbox") || ["CreateSandbox", "ExecuteInSandbox", "GetSandboxStatus", "StopSandbox"].includes(name)) {
    return handleSandboxTool(name, args);
  }
  if (["QueryDatabase", "ListTables", "DescribeTable"].includes(name)) {
    return handleDatabaseTool(name, args);
  }
  if (["RunAgent", "GetAgentStatus"].includes(name)) {
    return handleAgentTool(name, args);
  }
  if (["UploadFile", "DownloadFile", "ListFiles", "DeleteFile"].includes(name)) {
    return handleStorageTool(name, args);
  }
  if (["CreatePullRequest", "GetPullRequest", "ListPullRequests", "CreateIssue"].includes(name)) {
    return handleGithubTool(name, args);
  }

  // Existing handlers
  if (name === "SuggestFollowupTask") {
    return {
      content: [{ type: "text", text: "✅ Task suggestion presented to the user." }],
    };
  }

  throw new Error(`Unknown tool: ${name}`);
});

// Resources for documentation
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "terragon://docs/getting-started",
      name: "Getting Started Guide",
      mimeType: "text/markdown",
    },
    {
      uri: "terragon://docs/api-reference",
      name: "API Reference",
      mimeType: "text/markdown",
    },
    {
      uri: "terragon://docs/sandbox-guide",
      name: "Sandbox Usage Guide",
      mimeType: "text/markdown",
    },
  ],
}));

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Terragon MCP server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

---

### 2. PostgREST Integration

#### File: `docker-compose.override.yml` (new)

```yaml
version: '3.8'

services:
  postgrest:
    image: postgrest/postgrest:v12.2.12
    container_name: terragon-postgrest
    restart: unless-stopped
    environment:
      PGRST_DB_URI: ${DATABASE_URL}
      PGRST_OPENAPI_SERVER_PROXY_URI: http://localhost:3001
      PGRST_DB_SCHEMA: user_data
      PGRST_DB_ANON_ROLE: anon
      PGRST_JWT_SECRET: ${AUTH_SECRET}
      PGRST_DB_CHANNEL_ENABLED: true
      PGRST_DB_CHANNEL: pgrst
    ports:
      - "3001:3000"
    depends_on:
      - postgres
    networks:
      - terragon-network
```

#### File: `packages/shared/src/db/user-data-schema.sql`

```sql
-- Schema for user-defined data (managed by PostgREST)
CREATE SCHEMA IF NOT EXISTS user_data;

-- Enable RLS
ALTER DEFAULT PRIVILEGES IN SCHEMA user_data GRANT ALL ON TABLES TO authenticated;

-- Base table for user data
CREATE TABLE IF NOT EXISTS user_data._meta_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES public.user(id) ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    schema_definition JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, table_name)
);

-- RLS policy
ALTER TABLE user_data._meta_tables ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only see their own tables"
    ON user_data._meta_tables
    FOR ALL
    USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Function to create user tables dynamically
CREATE OR REPLACE FUNCTION user_data.create_user_table(
    p_user_id TEXT,
    p_table_name TEXT,
    p_columns JSONB
) RETURNS void AS $$
DECLARE
    v_column JSONB;
    v_sql TEXT;
BEGIN
    -- Build CREATE TABLE statement
    v_sql := format('CREATE TABLE IF NOT EXISTS user_data.%I (', p_table_name);
    v_sql := v_sql || 'id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ';
    v_sql := v_sql || 'user_id TEXT NOT NULL, ';
    v_sql := v_sql || 'created_at TIMESTAMPTZ DEFAULT NOW(), ';
    v_sql := v_sql || 'updated_at TIMESTAMPTZ DEFAULT NOW()';

    FOR v_column IN SELECT * FROM jsonb_array_elements(p_columns)
    LOOP
        v_sql := v_sql || format(', %I %s',
            v_column->>'name',
            v_column->>'type');
    END LOOP;

    v_sql := v_sql || ')';

    EXECUTE v_sql;

    -- Enable RLS
    EXECUTE format('ALTER TABLE user_data.%I ENABLE ROW LEVEL SECURITY', p_table_name);

    -- Create RLS policy
    EXECUTE format('CREATE POLICY %I ON user_data.%I FOR ALL USING (user_id = current_setting(''request.jwt.claims'', true)::json->>''sub'')',
        'user_' || p_table_name || '_policy',
        p_table_name);

    -- Notify PostgREST to reload schema
    NOTIFY pgrst, 'reload schema';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### File: `apps/www/src/server-lib/postgrest-proxy.ts`

```typescript
import { NextRequest, NextResponse } from "next/server";

const POSTGREST_URL = process.env.POSTGREST_URL || "http://localhost:3001";

export async function proxyToPostgREST(
  request: NextRequest,
  path: string
): Promise<NextResponse> {
  const url = new URL(path, POSTGREST_URL);

  // Forward query params
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers();

  // Forward auth header
  const authHeader = request.headers.get("authorization");
  if (authHeader) {
    headers.set("Authorization", authHeader);
  }

  // Forward content type
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }

  // Add prefer header for count
  headers.set("Prefer", "count=exact");

  const response = await fetch(url.toString(), {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method)
      ? undefined
      : await request.text(),
  });

  const data = await response.json();

  return NextResponse.json(data, {
    status: response.status,
    headers: {
      "Content-Range": response.headers.get("Content-Range") || "",
    },
  });
}
```

---

### 3. Serverless Functions Runtime

#### File: `packages/functions-runtime/package.json`

```json
{
  "name": "@terragon/functions-runtime",
  "version": "0.1.0",
  "description": "Deno-based serverless function runtime",
  "type": "module",
  "scripts": {
    "start": "deno run --allow-net --allow-env --allow-read src/server.ts",
    "dev": "deno run --allow-net --allow-env --allow-read --watch src/server.ts"
  }
}
```

#### File: `packages/functions-runtime/src/server.ts` (Deno)

```typescript
// Deno serverless function runtime
// Based on InsForge's function execution model

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";

interface FunctionRequest {
  functionId: string;
  code: string;
  input: unknown;
  timeout?: number;
  env?: Record<string, string>;
}

interface FunctionResponse {
  success: boolean;
  output?: unknown;
  error?: string;
  duration: number;
}

const PORT = parseInt(Deno.env.get("PORT") || "7133");

async function executeFunction(req: FunctionRequest): Promise<FunctionResponse> {
  const startTime = performance.now();

  try {
    // Create isolated worker
    const workerCode = `
      const handler = ${req.code};

      self.onmessage = async (e) => {
        try {
          const result = await handler(e.data);
          self.postMessage({ success: true, result });
        } catch (error) {
          self.postMessage({ success: false, error: error.message });
        }
      };
    `;

    const blob = new Blob([workerCode], { type: "application/javascript" });
    const worker = new Worker(URL.createObjectURL(blob), { type: "module" });

    // Set up timeout
    const timeout = req.timeout || 30000;

    const result = await Promise.race([
      new Promise((resolve, reject) => {
        worker.onmessage = (e) => {
          if (e.data.success) {
            resolve(e.data.result);
          } else {
            reject(new Error(e.data.error));
          }
        };
        worker.onerror = (e) => reject(new Error(e.message));
        worker.postMessage(req.input);
      }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Function timeout")), timeout)
      ),
    ]);

    worker.terminate();

    return {
      success: true,
      output: result,
      duration: performance.now() - startTime,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
      duration: performance.now() - startTime,
    };
  }
}

async function handler(request: Request): Promise<Response> {
  const url = new URL(request.url);

  // Health check
  if (url.pathname === "/health") {
    return new Response(JSON.stringify({ status: "ok" }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // Execute function
  if (url.pathname === "/execute" && request.method === "POST") {
    try {
      const body = await request.json() as FunctionRequest;
      const result = await executeFunction(body);
      return new Response(JSON.stringify(result), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      return new Response(JSON.stringify({
        success: false,
        error: "Invalid request"
      }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  return new Response("Not Found", { status: 404 });
}

console.log(`Functions runtime listening on port ${PORT}`);
serve(handler, { port: PORT });
```

#### File: `packages/daemon/src/function-service.ts`

```typescript
import { CircuitBreaker } from "@terragon/utils/circuit-breaker";

const FUNCTIONS_RUNTIME_URL = process.env.FUNCTIONS_RUNTIME_URL || "http://localhost:7133";

const functionBreaker = new CircuitBreaker({
  name: "functions-runtime",
  failureThreshold: 5,
  recoveryTimeout: 30000,
});

export interface ExecuteFunctionOptions {
  functionId: string;
  code: string;
  input: unknown;
  timeout?: number;
  env?: Record<string, string>;
}

export interface FunctionResult {
  success: boolean;
  output?: unknown;
  error?: string;
  duration: number;
}

export async function executeFunction(
  options: ExecuteFunctionOptions
): Promise<FunctionResult> {
  return functionBreaker.execute(async () => {
    const response = await fetch(`${FUNCTIONS_RUNTIME_URL}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });

    if (!response.ok) {
      throw new Error(`Function execution failed: ${response.status}`);
    }

    return response.json() as Promise<FunctionResult>;
  });
}
```

---

## How It Works Together

```
┌────────────────────────────────────────────────────────────────────┐
│                         AI Agent (Claude)                          │
│                                                                    │
│  "Create a todo app with user authentication"                      │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             │ MCP Protocol
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Terragon MCP Server                             │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Tools:                                                        │ │
│  │  • CreateSandbox    → Spin up E2B/Daytona sandbox            │ │
│  │  • QueryDatabase    → Query PostgreSQL via Drizzle           │ │
│  │  • UploadFile       → Upload to R2/S3 storage                │ │
│  │  • CreatePullRequest → Create GitHub PR                      │ │
│  │  • RunAgent         → Delegate to specialized agents         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Sandbox      │ │   PostgreSQL    │ │   Functions     │
│   (E2B/Daytona) │ │   + PostgREST   │ │   Runtime       │
│                 │ │                 │ │   (Deno)        │
│ • Code exec     │ │ • Drizzle ORM   │ │                 │
│ • File I/O      │ │ • Dynamic APIs  │ │ • User code     │
│ • Git ops       │ │ • RLS policies  │ │ • Webhooks      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Flow Example: "Create a todo app"

1. **Agent receives task** via MCP

2. **Agent uses `CreateSandbox`** tool
   - MCP server calls sandbox package
   - E2B sandbox spins up
   - Returns sandbox ID

3. **Agent uses `QueryDatabase`** to check existing schema
   - MCP server queries PostgreSQL
   - Returns table info

4. **Agent creates schema via sandbox**
   - Writes migration file
   - Runs `npx drizzle-kit push`

5. **Agent uses dynamic API via PostgREST**
   - Creates `todos` table in `user_data` schema
   - PostgREST auto-generates REST API
   - Frontend can call `/api/data/todos` directly

6. **Agent deploys serverless function** for webhooks
   - Writes function code
   - Registers with functions runtime
   - Function handles external webhooks

7. **Agent uses `CreatePullRequest`**
   - Commits changes to feature branch
   - Creates PR for review

---

## Implementation Order

### Week 1: Enhanced MCP Server
1. Create tool definitions (`tools/*.ts`)
2. Implement handlers (`handlers/*.ts`)
3. Update main server (`index.ts`)
4. Test with MCP inspector
5. Add to Claude config

### Week 2: PostgREST Integration
1. Add PostgREST to docker-compose
2. Create user_data schema
3. Implement API proxy in Next.js
4. Add dynamic table creation
5. Test with AI agent

### Week 3: Functions Runtime
1. Set up Deno runtime service
2. Implement execution isolation
3. Create function management API
4. Add to MCP tools
5. Test end-to-end

### Week 4: Polish & Documentation
1. Error handling improvements
2. Logging and observability
3. Security audit
4. Documentation
5. Integration tests

---

## Files to Create/Modify

### New Files
```
packages/mcp-server/src/
├── tools/
│   ├── sandbox.ts
│   ├── database.ts
│   ├── agent.ts
│   ├── storage.ts
│   └── github.ts
├── handlers/
│   ├── sandbox.ts
│   ├── database.ts
│   ├── agent.ts
│   ├── storage.ts
│   └── github.ts
└── resources/
    └── docs.ts

packages/functions-runtime/
├── package.json
├── deno.json
└── src/
    ├── server.ts
    └── worker-template.ts

packages/shared/src/db/
└── user-data-schema.sql

apps/www/src/
├── app/api/data/[...path]/route.ts  # PostgREST proxy
└── server-lib/postgrest-proxy.ts
```

### Modified Files
```
packages/mcp-server/src/index.ts     # Add new tools
packages/mcp-server/package.json     # Add dependencies
docker-compose.yml                   # Add PostgREST service
packages/daemon/src/index.ts         # Add function service
```

---

## Security Considerations

1. **MCP Tool Access Control**
   - Validate user permissions before executing tools
   - Rate limit tool calls
   - Audit log all operations

2. **PostgREST Security**
   - Row-Level Security (RLS) on all tables
   - JWT validation
   - Schema isolation per user

3. **Functions Runtime**
   - Worker isolation (Deno permissions)
   - Memory/CPU limits
   - Network restrictions
   - Timeout enforcement

4. **Database Access**
   - Read-only for QueryDatabase tool
   - Parameterized queries
   - Schema restrictions
