import { MessageSquare, Cloud, GitPullRequest } from 'lucide-react';

const steps = [
  {
    icon: MessageSquare,
    title: 'Describe the Task',
    description: 'Select your repository and describe what you need done. Be as detailed or as brief as you like.',
  },
  {
    icon: Cloud,
    title: 'Agent Works in the Cloud',
    description: 'Your task runs in an isolated sandbox environment. The AI agent writes, tests, and iterates on the code.',
  },
  {
    icon: GitPullRequest,
    title: 'Review the Pull Request',
    description: 'When complete, a pull request is created automatically. Review the changes and merge when ready.',
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 md:py-32 bg-muted/30">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            How It Works
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Three simple steps to automate your development workflow
          </p>
        </div>

        <div className="mx-auto max-w-5xl">
          <div className="grid gap-8 md:grid-cols-3">
            {steps.map((step, index) => (
              <div key={step.title} className="relative">
                {/* Connector line */}
                {index < steps.length - 1 && (
                  <div className="hidden md:block absolute top-12 left-[calc(50%+3rem)] w-[calc(100%-6rem)] h-0.5 bg-border" />
                )}

                <div className="flex flex-col items-center text-center">
                  <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10 mb-6">
                    <step.icon className="h-10 w-10 text-primary" />
                  </div>
                  <div className="mb-2 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {index + 1}
                    </span>
                    <h3 className="text-xl font-semibold">{step.title}</h3>
                  </div>
                  <p className="text-muted-foreground">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
