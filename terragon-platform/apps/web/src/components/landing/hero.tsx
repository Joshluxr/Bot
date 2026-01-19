import Link from 'next/link';
import { Button } from '@terragon/ui';
import { ArrowRight, Play, Sparkles } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative overflow-hidden py-20 md:py-32">
      {/* Background gradient */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(45%_40%_at_50%_60%,hsl(var(--primary)/0.1),transparent)]" />

      <div className="container">
        <div className="mx-auto max-w-4xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-sm">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>AI-powered development automation</span>
          </div>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
            Delegate coding tasks to{' '}
            <span className="text-primary">AI agents</span>
          </h1>

          <p className="mt-6 text-lg text-muted-foreground md:text-xl max-w-2xl mx-auto">
            Describe what you need, and let AI agents work autonomously in isolated
            cloud sandboxes. Get pull requests, not promises.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/login">
                Get started for free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#how-it-works">
                <Play className="mr-2 h-4 w-4" />
                See how it works
              </Link>
            </Button>
          </div>

          <p className="mt-4 text-sm text-muted-foreground">
            No credit card required. 14-day free trial.
          </p>
        </div>

        {/* Demo preview */}
        <div className="mt-16 mx-auto max-w-5xl">
          <div className="relative rounded-xl border bg-card shadow-2xl overflow-hidden">
            <div className="flex items-center gap-2 border-b bg-muted/50 px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <div className="h-3 w-3 rounded-full bg-green-500" />
              </div>
              <span className="text-sm text-muted-foreground">terragon.dev/dashboard</span>
            </div>
            <div className="p-6 bg-gradient-to-b from-background to-muted/20">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-sm font-medium">Running</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Add user authentication flow</p>
                  <div className="mt-3 h-2 rounded-full bg-primary/20 overflow-hidden">
                    <div className="h-full w-3/4 bg-primary rounded-full" />
                  </div>
                </div>
                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-2 w-2 rounded-full bg-blue-500" />
                    <span className="text-sm font-medium">Queued</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Fix pagination bug in dashboard</p>
                </div>
                <div className="rounded-lg border bg-card p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-2 w-2 rounded-full bg-green-500" />
                    <span className="text-sm font-medium">Completed</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Refactor API endpoints</p>
                  <p className="mt-2 text-xs text-primary">PR #142 ready for review</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
