import { Box, GitBranch, Layers } from 'lucide-react';

export function IsolatedEnvironments() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          <div>
            <div className="mb-6 h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Layers className="h-6 w-6 text-primary" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight mb-4">
              Isolated Development Environments
            </h2>
            <p className="text-lg text-muted-foreground">
              Work on multiple tasks without conflicts. Each agent runs in an isolated
              environment to plan, build and test its work.
            </p>
          </div>

          {/* Visual representation */}
          <div className="relative">
            <div className="space-y-4">
              {/* Sandbox 1 */}
              <div className="rounded-xl border bg-card p-4 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                    <Box className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">Sandbox #1</div>
                    <div className="text-xs text-muted-foreground">feat/auth-flow</div>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs text-muted-foreground">Running</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" />
                  <span>acme/frontend</span>
                </div>
              </div>

              {/* Sandbox 2 */}
              <div className="rounded-xl border bg-card p-4 shadow-sm ml-8">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <Box className="h-5 w-5 text-purple-500" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">Sandbox #2</div>
                    <div className="text-xs text-muted-foreground">fix/pagination</div>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-xs text-muted-foreground">Running</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" />
                  <span>acme/frontend</span>
                </div>
              </div>

              {/* Sandbox 3 */}
              <div className="rounded-xl border bg-card p-4 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                    <Box className="h-5 w-5 text-orange-500" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">Sandbox #3</div>
                    <div className="text-xs text-muted-foreground">refactor/api</div>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5">
                    <div className="h-2 w-2 rounded-full bg-yellow-500" />
                    <span className="text-xs text-muted-foreground">Queued</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" />
                  <span>acme/backend</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
