import { Github, MessageSquare, Layers, Webhook } from 'lucide-react';

const integrations = [
  {
    name: 'GitHub',
    description: 'Connect repositories, auto-create branches and PRs',
    icon: Github,
    status: 'available',
  },
  {
    name: 'Slack',
    description: 'Trigger tasks and receive notifications',
    icon: MessageSquare,
    status: 'available',
  },
  {
    name: 'Linear',
    description: 'Sync with Linear issues and projects',
    icon: Layers,
    status: 'coming-soon',
  },
  {
    name: 'Jira',
    description: 'Create tasks from Jira tickets',
    icon: Webhook,
    status: 'coming-soon',
  },
];

export function Integrations() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center mb-12">
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            Integrations
          </h2>
          <p className="text-lg text-muted-foreground">
            Connect with your favorite tools and workflows
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          <div className="grid gap-4 sm:grid-cols-2">
            {integrations.map((integration) => (
              <div
                key={integration.name}
                className="rounded-xl border bg-card p-5 shadow-sm flex items-start gap-4"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                  <integration.icon className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{integration.name}</h3>
                    {integration.status === 'coming-soon' && (
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        Coming Soon
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {integration.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
