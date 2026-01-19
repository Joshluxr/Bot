'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const faqs = [
  {
    question: 'How does Terragon work?',
    answer: 'Terragon connects to your GitHub repository, spins up an isolated cloud sandbox, and runs an AI coding agent to complete your task. The agent writes code, runs tests, and creates a pull request when done.',
  },
  {
    question: 'Is my code secure?',
    answer: 'Yes. Each task runs in an isolated sandbox environment. Your code and credentials are encrypted at rest and in transit. Sandboxes are ephemeral and destroyed after task completion.',
  },
  {
    question: 'What AI models do you support?',
    answer: 'We support Claude Code (Anthropic), OpenAI, Gemini (Google), Amp, OpenCode, and custom configurations. You can use your own API keys or our managed service.',
  },
  {
    question: 'What happens if a task fails?',
    answer: "If a task fails, you'll see the error logs and can retry. You can also pull the task to your local environment using the Terry CLI to debug and fix issues.",
  },
  {
    question: 'Can I use my own API keys?',
    answer: 'Yes! You can bring your own API keys for Claude, OpenAI, or other providers. This can reduce costs for high-volume usage.',
  },
  {
    question: 'Do you support monorepos?',
    answer: 'Yes! You can specify the working directory within your repository. The agent will work within that context.',
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center mb-12">
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            FAQ
          </h2>
          <p className="text-lg text-muted-foreground">
            Everything you need to know about Terragon
          </p>
        </div>

        <div className="mx-auto max-w-2xl">
          <div className="space-y-2">
            {faqs.map((faq, index) => (
              <div key={index} className="rounded-lg border bg-card">
                <button
                  onClick={() => setOpenIndex(openIndex === index ? null : index)}
                  className="w-full flex items-center justify-between p-4 text-left"
                >
                  <span className="font-medium">{faq.question}</span>
                  <ChevronDown
                    className={`h-4 w-4 text-muted-foreground transition-transform ${
                      openIndex === index ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openIndex === index && (
                  <div className="px-4 pb-4 text-sm text-muted-foreground">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
