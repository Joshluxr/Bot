import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@terragon/ui';

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
    answer: 'We support Claude Code (Anthropic), GPT-4 (OpenAI), Gemini (Google), and custom configurations. You can use your own API keys or our managed service.',
  },
  {
    question: 'How are credits calculated?',
    answer: 'Credits are based on sandbox runtime (1 credit per minute) plus AI API usage. Most simple tasks use 5-20 credits. Complex tasks may use more.',
  },
  {
    question: 'Can I use my own API keys?',
    answer: 'Yes! On Pro and Enterprise plans, you can bring your own API keys for Claude, OpenAI, or other providers. This can reduce costs for high-volume usage.',
  },
  {
    question: 'What happens if a task fails?',
    answer: "If a task fails, you'll see the error logs and can retry. Failed tasks don't count against your concurrent task limit. You only pay for successful sandbox time.",
  },
  {
    question: 'Do you support monorepos?',
    answer: 'Yes! You can specify the working directory within your repository. The agent will work within that context.',
  },
  {
    question: 'Can I cancel the trial at any time?',
    answer: 'Absolutely. You can cancel your trial or subscription at any time. No credit card is required to start.',
  },
];

export function FAQ() {
  return (
    <section className="py-20 md:py-32 bg-muted/30">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Everything you need to know about Terragon
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, index) => (
              <AccordionItem key={index} value={`item-${index}`}>
                <AccordionTrigger className="text-left">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
