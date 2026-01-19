import Image from 'next/image';
import { Card, CardContent } from '@terragon/ui';

const agents = [
  {
    name: 'Claude Code',
    description: "Anthropic's Claude with deep coding capabilities",
    icon: '/agents/claude.svg',
    color: 'from-orange-500/20 to-orange-600/20',
  },
  {
    name: 'OpenAI GPT-4',
    description: "OpenAI's most capable model for code generation",
    icon: '/agents/openai.svg',
    color: 'from-green-500/20 to-green-600/20',
  },
  {
    name: 'Google Gemini',
    description: "Google's multimodal AI with coding expertise",
    icon: '/agents/gemini.svg',
    color: 'from-blue-500/20 to-blue-600/20',
  },
  {
    name: 'Custom Agent',
    description: 'Bring your own agent configuration and API keys',
    icon: '/agents/custom.svg',
    color: 'from-purple-500/20 to-purple-600/20',
  },
];

export function Agents() {
  return (
    <section className="py-20 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Choose Your AI Agent
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Work with the best AI coding assistants. Use your own API keys or our managed service.
          </p>
        </div>

        <div className="mx-auto max-w-4xl">
          <div className="grid gap-6 sm:grid-cols-2">
            {agents.map((agent) => (
              <Card key={agent.name} className="overflow-hidden">
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className={`flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${agent.color}`}>
                      <div className="h-8 w-8 rounded-lg bg-card flex items-center justify-center text-2xl font-bold">
                        {agent.name[0]}
                      </div>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">{agent.name}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        {agent.description}
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
