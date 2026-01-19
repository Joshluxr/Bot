import { Terminal } from 'lucide-react';

export function CLI() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Terminal mockup */}
          <div className="order-2 lg:order-1">
            <div className="rounded-xl border bg-zinc-900 text-zinc-100 overflow-hidden shadow-2xl">
              {/* Terminal header */}
              <div className="flex items-center gap-2 border-b border-zinc-700 px-4 py-3">
                <div className="flex gap-1.5">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                </div>
                <span className="text-xs text-zinc-500">terry</span>
              </div>

              {/* Terminal content */}
              <div className="p-4 font-mono text-sm space-y-2">
                <div>
                  <span className="text-green-400">$</span>{' '}
                  <span className="text-zinc-300">terry tasks</span>
                </div>
                <div className="text-zinc-400">
                  <div className="flex gap-4">
                    <span className="text-yellow-400">●</span>
                    <span className="w-32 truncate">Add auth flow</span>
                    <span className="text-zinc-500">Running 75%</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-blue-400">●</span>
                    <span className="w-32 truncate">Fix pagination</span>
                    <span className="text-zinc-500">Queued</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-green-400">●</span>
                    <span className="w-32 truncate">Refactor API</span>
                    <span className="text-zinc-500">PR Ready</span>
                  </div>
                </div>
                <div className="pt-2">
                  <span className="text-green-400">$</span>{' '}
                  <span className="text-zinc-300">terry pull task-abc123</span>
                </div>
                <div className="text-zinc-400">
                  Pulling task to local environment...
                </div>
                <div className="text-green-400">
                  ✓ Task pulled successfully
                </div>
                <div className="pt-2">
                  <span className="text-green-400">$</span>{' '}
                  <span className="animate-pulse">▊</span>
                </div>
              </div>
            </div>
          </div>

          <div className="order-1 lg:order-2">
            <div className="mb-6 h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Terminal className="h-6 w-6 text-primary" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight mb-4">
              Terry CLI
            </h2>
            <p className="text-lg text-muted-foreground">
              Pull tasks to your local environment when they need your attention.
              Review changes, make edits, and push back to the cloud.
            </p>
            <div className="mt-6 space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <span>List and manage tasks from terminal</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <span>Pull task changes to local machine</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <span>MCP server for tool integrations</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
