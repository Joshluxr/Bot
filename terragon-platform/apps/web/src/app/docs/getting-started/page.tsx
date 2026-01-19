import Link from 'next/link';
import { Leaf, ArrowLeft, ArrowRight, Check } from 'lucide-react';

export default function GettingStartedPage() {
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
          <span>Getting Started</span>
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
            <h1>Getting Started with Terragon</h1>

            <p className="lead">
              Terragon lets you delegate coding tasks to AI agents that work in isolated
              cloud environments. This guide will help you set up your first task in minutes.
            </p>

            <h2>Prerequisites</h2>
            <ul>
              <li>A GitHub account with at least one repository</li>
              <li>A Terragon account (free tier available)</li>
            </ul>

            <h2>Step 1: Connect GitHub</h2>
            <p>
              First, you'll need to connect your GitHub account to Terragon. This allows
              agents to clone your repositories and create pull requests.
            </p>
            <ol>
              <li>Go to <strong>Settings → Integrations</strong></li>
              <li>Click <strong>Connect GitHub</strong></li>
              <li>Authorize Terragon to access your repositories</li>
              <li>Select which repositories you want to use</li>
            </ol>

            <h2>Step 2: Create Your First Task</h2>
            <p>
              With GitHub connected, you're ready to create your first task.
            </p>
            <ol>
              <li>Click the <strong>New Task</strong> button in the dashboard</li>
              <li>Select a repository from your connected accounts</li>
              <li>Choose an AI agent (Claude Code recommended for beginners)</li>
              <li>Describe what you want the agent to do</li>
              <li>Click <strong>Create Task</strong></li>
            </ol>

            <div className="bg-muted rounded-lg p-4 my-6 not-prose">
              <h4 className="font-semibold mb-2">Example Prompts</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>"Add a user authentication system using NextAuth.js"</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>"Fix the pagination bug in the products list component"</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>"Refactor the API endpoints to use TypeScript"</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>"Add unit tests for the utils directory"</span>
                </li>
              </ul>
            </div>

            <h2>Step 3: Monitor Progress</h2>
            <p>
              Once your task is created, Terragon will:
            </p>
            <ol>
              <li>Spin up an isolated sandbox environment</li>
              <li>Clone your repository</li>
              <li>Analyze the codebase</li>
              <li>Plan and implement the changes</li>
              <li>Run tests (if available)</li>
              <li>Create a pull request</li>
            </ol>
            <p>
              You can monitor progress in real-time from the dashboard or use the Terry CLI
              to watch from your terminal.
            </p>

            <h2>Step 4: Review the Pull Request</h2>
            <p>
              When the agent completes the task, you'll receive a notification with a link
              to the pull request. Review the changes, leave comments, and merge when ready.
            </p>

            <h2>Next Steps</h2>
            <ul>
              <li>
                <Link href="/docs/cli">Install the Terry CLI</Link> for terminal-based task
                management
              </li>
              <li>
                <Link href="/docs/automations">Set up Automations</Link> to run tasks on a
                schedule
              </li>
              <li>
                <Link href="/docs/integrations/slack">Connect Slack</Link> to trigger tasks
                from messages
              </li>
            </ul>
          </article>

          {/* Navigation */}
          <div className="flex justify-between mt-12 pt-8 border-t">
            <Link
              href="/docs"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              Documentation
            </Link>
            <Link
              href="/docs/cli"
              className="flex items-center gap-2 text-sm text-primary hover:underline"
            >
              Terry CLI
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
