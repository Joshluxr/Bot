import {
  Cloud,
  GitBranch,
  Terminal,
  Clock,
  Shield,
  Zap,
  Layers,
  Bell
} from 'lucide-react';

const features = [
  {
    icon: Cloud,
    title: 'Isolated Sandboxes',
    description: 'Each task runs in its own isolated cloud environment. No conflicts, no interference.',
  },
  {
    icon: GitBranch,
    title: 'Automatic PRs',
    description: 'Changes are automatically committed and pushed. Pull requests created for review.',
  },
  {
    icon: Terminal,
    title: 'Real-time Logs',
    description: 'Watch your agent work in real-time. Stream logs and terminal output as it happens.',
  },
  {
    icon: Clock,
    title: 'Task Scheduling',
    description: 'Queue tasks and let them run when you want. Set up recurring automations.',
  },
  {
    icon: Shield,
    title: 'Secure by Design',
    description: 'Your code and credentials are encrypted. Sandboxes are isolated and ephemeral.',
  },
  {
    icon: Zap,
    title: 'Fast Execution',
    description: 'Optimized infrastructure for quick sandbox startup and agent execution.',
  },
  {
    icon: Layers,
    title: 'Multiple Tasks',
    description: 'Run multiple tasks in parallel. Each gets dedicated resources.',
  },
  {
    icon: Bell,
    title: 'Notifications',
    description: 'Get notified via Slack, email, or webhooks when tasks complete.',
  },
];

export function Features() {
  return (
    <section id="features" className="py-20 md:py-32 bg-muted/30">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Everything You Need
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Powerful features to automate your development workflow
          </p>
        </div>

        <div className="mx-auto max-w-6xl">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-xl border bg-card p-6 transition-colors hover:border-primary/50"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
