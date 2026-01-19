import { Card, CardContent, Badge } from '@terragon/ui';
import { Github, Slack, Webhook } from 'lucide-react';

const integrations = [
  {
    name: 'GitHub',
    description: 'Connect your repositories, create PRs automatically',
    icon: Github,
    status: 'available',
  },
  {
    name: 'Slack',
    description: 'Get notifications and trigger tasks from Slack',
    icon: Slack,
    status: 'available',
  },
  {
    name: 'Linear',
    description: 'Sync with Linear issues and projects',
    icon: () => (
      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 12.5a9.5 9.5 0 1 1 19 0 9.5 9.5 0 0 1-19 0Zm9.5-7a7 7 0 1 0 0 14 7 7 0 0 0 0-14Z"/>
      </svg>
    ),
    status: 'coming-soon',
  },
  {
    name: 'Webhooks',
    description: 'Trigger tasks via webhooks from any service',
    icon: Webhook,
    status: 'available',
  },
];

export function Integrations() {
  return (
    <section className="py-20 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Integrations
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Connect with your existing tools and workflows
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          <div className="grid gap-4 sm:grid-cols-2">
            {integrations.map((integration) => (
              <Card key={integration.name}>
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                      <integration.icon className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{integration.name}</h3>
                        {integration.status === 'coming-soon' && (
                          <Badge variant="secondary">Coming Soon</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {integration.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
