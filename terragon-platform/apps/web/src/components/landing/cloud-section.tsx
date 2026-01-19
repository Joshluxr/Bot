import { Smartphone, Globe } from 'lucide-react';

export function CloudSection() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-6 mx-auto h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center">
            <Globe className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            Runs in the Cloud
          </h2>
          <p className="text-lg text-muted-foreground">
            Work from anywhere. Start tasks from your phone, tablet, or computer.
            Your agents run in the cloud so you don't need your dev machine.
          </p>

          {/* Mobile mockup */}
          <div className="mt-10 mx-auto max-w-xs">
            <div className="rounded-3xl border-4 border-foreground/10 bg-card p-2 shadow-xl">
              <div className="rounded-2xl bg-background p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Active Tasks</span>
                  <span className="text-xs text-muted-foreground">3 running</span>
                </div>
                <div className="space-y-2">
                  <div className="rounded-lg bg-muted/50 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                      <span className="text-xs font-medium">Add auth flow</span>
                    </div>
                    <div className="h-1 rounded-full bg-muted overflow-hidden">
                      <div className="h-full w-2/3 bg-primary rounded-full" />
                    </div>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                      <span className="text-xs font-medium">Fix pagination</span>
                    </div>
                    <div className="h-1 rounded-full bg-muted overflow-hidden">
                      <div className="h-full w-1/3 bg-primary rounded-full" />
                    </div>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                      <span className="text-xs font-medium">Refactor API</span>
                    </div>
                    <span className="text-xs text-muted-foreground">Queued</span>
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
