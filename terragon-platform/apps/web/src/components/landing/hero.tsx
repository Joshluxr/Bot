import Link from 'next/link';
import { Button } from '@terragon/ui';

export function Hero() {
  return (
    <section className="py-16 md:py-24 lg:py-32">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Delegate coding tasks to AI background agents
          </h1>

          <p className="mt-6 text-lg text-muted-foreground md:text-xl max-w-2xl mx-auto">
            Describe what you need done. An AI agent works on your task in a cloud sandbox.
            When it's done, review and merge the pull request.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/login">Get started for free</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="https://docs.terragonlabs.com" target="_blank">
                Learn more
              </Link>
            </Button>
          </div>
        </div>

        {/* Demo/Screenshot Preview */}
        <div className="mt-16 mx-auto max-w-5xl">
          <div className="relative rounded-xl border bg-card shadow-2xl overflow-hidden">
            {/* Browser chrome */}
            <div className="flex items-center gap-2 border-b bg-muted/50 px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
              </div>
              <div className="flex-1 text-center">
                <span className="text-xs text-muted-foreground">app.terragon.dev</span>
              </div>
            </div>

            {/* Mock dashboard content */}
            <div className="p-6 space-y-4">
              {/* Task input area */}
              <div className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-primary text-sm font-medium">T</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">New Task</div>
                    <div className="text-xs text-muted-foreground">acme/frontend • main branch</div>
                  </div>
                </div>
                <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
                  Add user authentication with GitHub OAuth. Include login/logout buttons in the header and protect the /dashboard route.
                </div>
              </div>

              {/* Running tasks */}
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border bg-background p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                      <span className="text-sm font-medium">Running</span>
                    </div>
                    <span className="text-xs text-muted-foreground">Claude Code</span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">Refactor API endpoints</p>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div className="h-full w-3/4 bg-primary rounded-full" />
                  </div>
                </div>

                <div className="rounded-lg border bg-background p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      <span className="text-sm font-medium">Completed</span>
                    </div>
                    <span className="text-xs text-muted-foreground">OpenAI</span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">Fix pagination bug</p>
                  <div className="text-xs text-primary font-medium">PR #142 ready</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
