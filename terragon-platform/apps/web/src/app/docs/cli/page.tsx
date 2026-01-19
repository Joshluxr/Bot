import Link from 'next/link';
import { Leaf, ArrowLeft, ArrowRight, Terminal } from 'lucide-react';

export default function CLIDocsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container px-4 md:px-6 h-14 flex items-center">
          <Link href="/" className="flex items-center gap-2">
            <Leaf className="h-5 w-5 text-primary" />
            <span className="font-semibold">Terragon</span>
          </Link>
          <span className="mx-2 text-muted-foreground">/</span>
          <Link href="/docs" className="text-muted-foreground hover:text-foreground">
            Documentation
          </Link>
          <span className="mx-2 text-muted-foreground">/</span>
          <span>Terry CLI</span>
        </div>
      </header>

      <div className="container px-4 md:px-6 py-12">
        <div className="max-w-3xl mx-auto">
          {/* Back link */}
          <Link
            href="/docs"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Documentation
          </Link>

          {/* Content */}
          <article className="prose prose-neutral dark:prose-invert max-w-none">
            <h1>Terry CLI</h1>

            <p className="lead">
              The Terry CLI lets you manage Terragon tasks from your terminal. List tasks,
              pull changes locally, push edits, and watch progress in real-time.
            </p>

            <h2>Installation</h2>
            <p>Install the Terry CLI globally using npm:</p>

            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden">
                <div className="flex items-center gap-2 border-b border-zinc-700 px-4 py-2">
                  <Terminal className="h-4 w-4 text-zinc-500" />
                  <span className="text-xs text-zinc-500">Terminal</span>
                </div>
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>npm install -g @terragon/cli</code>
                </pre>
              </div>
            </div>

            <h2>Authentication</h2>
            <p>
              Before using the CLI, you need to authenticate with your Terragon account:
            </p>

            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden">
                <div className="flex items-center gap-2 border-b border-zinc-700 px-4 py-2">
                  <Terminal className="h-4 w-4 text-zinc-500" />
                  <span className="text-xs text-zinc-500">Terminal</span>
                </div>
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>terry login</code>
                </pre>
              </div>
            </div>

            <p>
              You'll be prompted to enter your API token, which you can get from
              <strong> Settings → API Tokens</strong> in the web dashboard.
            </p>

            <h2>Commands</h2>

            <h3>List Tasks</h3>
            <p>View your recent tasks:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>{`terry tasks
terry tasks --status running
terry tasks --repo acme/frontend`}</code>
                </pre>
              </div>
            </div>

            <h3>Create Task</h3>
            <p>Create a new task from the terminal:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>{`terry create
terry create --repo acme/frontend --prompt "Add dark mode support"`}</code>
                </pre>
              </div>
            </div>

            <h3>Watch Task</h3>
            <p>Watch a task's progress in real-time:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>terry watch task_abc123</code>
                </pre>
              </div>
            </div>

            <h3>Pull Task</h3>
            <p>Pull a task's changes to your local machine:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>{`terry pull task_abc123
terry pull task_abc123 --dir ./my-project`}</code>
                </pre>
              </div>
            </div>

            <h3>Push Changes</h3>
            <p>After making local edits, push them back:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>terry push task_abc123 --message "Fixed edge case"</code>
                </pre>
              </div>
            </div>

            <h3>Configuration</h3>
            <p>Manage CLI settings:</p>
            <div className="not-prose">
              <div className="bg-zinc-900 text-zinc-100 rounded-lg overflow-hidden mb-4">
                <pre className="p-4 text-sm overflow-x-auto">
                  <code>{`terry config --list
terry config --set defaultAgent=openai`}</code>
                </pre>
              </div>
            </div>

            <h2>Configuration Options</h2>
            <table>
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Description</th>
                  <th>Default</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>apiUrl</code></td>
                  <td>API base URL</td>
                  <td><code>https://api.terragonlabs.com</code></td>
                </tr>
                <tr>
                  <td><code>defaultAgent</code></td>
                  <td>Default AI agent for new tasks</td>
                  <td><code>claude</code></td>
                </tr>
              </tbody>
            </table>

            <h2>Next Steps</h2>
            <ul>
              <li>
                <Link href="/docs/getting-started">Getting Started Guide</Link>
              </li>
              <li>
                <Link href="/docs/automations">Set up Automations</Link>
              </li>
            </ul>
          </article>

          {/* Navigation */}
          <div className="flex justify-between mt-12 pt-8 border-t">
            <Link
              href="/docs/getting-started"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Getting Started
            </Link>
            <Link
              href="/docs/automations"
              className="flex items-center gap-2 text-sm text-primary hover:underline"
            >
              Automations
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
