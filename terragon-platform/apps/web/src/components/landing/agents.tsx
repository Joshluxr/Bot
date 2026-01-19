import { Bot } from 'lucide-react';

const agents = [
  {
    name: 'Claude Code',
    description: "Anthropic's Claude - exceptional at understanding complex codebases",
    color: 'bg-orange-500',
  },
  {
    name: 'OpenAI Codex',
    description: "OpenAI's models optimized for code generation and debugging",
    color: 'bg-emerald-500',
  },
  {
    name: 'Gemini',
    description: "Google's AI with strong reasoning and multimodal capabilities",
    color: 'bg-blue-500',
  },
  {
    name: 'Amp',
    description: "Sourcegraph's AI agent built for large-scale code changes",
    color: 'bg-purple-500',
  },
  {
    name: 'OpenCode',
    description: "Open-source coding agent with customizable behavior",
    color: 'bg-pink-500',
  },
];

export function Agents() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center mb-12">
          <div className="mb-6 mx-auto h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            AI Coding Agents
          </h2>
          <p className="text-lg text-muted-foreground">
            Choose from leading AI models. Each agent runs autonomously in isolated sandboxes
            to plan, build, and test your code.
          </p>
        </div>

        <div className="mx-auto max-w-4xl">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <div
                key={agent.name}
                className="rounded-xl border bg-card p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={`h-3 w-3 rounded-full ${agent.color}`} />
                  <h3 className="font-semibold">{agent.name}</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  {agent.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
