import { Zap, Clock, GitBranch, MessageSquare } from 'lucide-react';

export function Automations() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          <div>
            <div className="mb-6 h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight mb-4">
              Automations
            </h2>
            <p className="text-lg text-muted-foreground mb-6">
              Recurring tasks or event-triggered workflows let you focus on what matters.
              Set up automations to run tasks on a schedule or in response to events.
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span>Schedule recurring tasks (daily, weekly)</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <GitBranch className="h-4 w-4 text-muted-foreground" />
                <span>Trigger on GitHub events (issues, PRs)</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <span>Trigger from Slack messages</span>
              </div>
            </div>
          </div>

          {/* Automation visual */}
          <div className="relative">
            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Daily Dependency Check</h3>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-xs text-muted-foreground">Active</span>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <div className="text-sm">
                    <span className="text-muted-foreground">Trigger:</span>{' '}
                    <span className="font-medium">Every day at 9:00 AM</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
                  <GitBranch className="h-4 w-4 text-muted-foreground" />
                  <div className="text-sm">
                    <span className="text-muted-foreground">Repository:</span>{' '}
                    <span className="font-medium">acme/frontend</span>
                  </div>
                </div>

                <div className="rounded-lg bg-muted/50 p-3">
                  <div className="text-sm text-muted-foreground mb-1">Task:</div>
                  <div className="text-sm">
                    Check for outdated dependencies and create a PR to update them if needed.
                  </div>
                </div>

                <div className="pt-2 border-t">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Last run: 2 hours ago</span>
                    <span>Next run: in 22 hours</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
