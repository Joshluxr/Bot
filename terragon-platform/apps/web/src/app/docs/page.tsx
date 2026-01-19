import Link from 'next/link';
import { Leaf, ArrowRight, Terminal, Zap, GitBranch, Box } from 'lucide-react';

const sections = [
  {
    title: 'Getting Started',
    description: 'Learn the basics of Terragon and set up your first task',
    href: '/docs/getting-started',
    icon: ArrowRight,
  },
  {
    title: 'Terry CLI',
    description: 'Use the command-line interface to manage tasks locally',
    href: '/docs/cli',
    icon: Terminal,
  },
  {
    title: 'Automations',
    description: 'Set up scheduled and event-triggered workflows',
    href: '/docs/automations',
    icon: Zap,
  },
  {
    title: 'Integrations',
    description: 'Connect with GitHub, Slack, and more',
    href: '/docs/integrations',
    icon: GitBranch,
  },
  {
    title: 'Sandboxes',
    description: 'Understand isolated development environments',
    href: '/docs/sandboxes',
    icon: Box,
  },
];

const quickLinks = [
  { title: 'Quick Start Guide', href: '/docs/getting-started' },
  { title: 'Install Terry CLI', href: '/docs/cli/installation' },
  { title: 'Create Your First Task', href: '/docs/getting-started/first-task' },
  { title: 'GitHub Integration', href: '/docs/integrations/github' },
  { title: 'API Reference', href: '/docs/api' },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container px-4 md:px-6 h-14 flex items-center">
          <Link href="/" className="flex items-center gap-2">
            <Leaf className="h-5 w-5 text-primary" />
            <span className="font-semibold">Terragon</span>
          </Link>
          <span className="mx-2 text-muted-foreground">/</span>
          <span className="text-muted-foreground">Documentation</span>
        </div>
      </header>

      <main className="container px-4 md:px-6 py-12">
        {/* Hero */}
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Terragon Documentation
          </h1>
          <p className="text-lg text-muted-foreground">
            Learn how to use Terragon to delegate coding tasks to AI agents.
            From setup to advanced automations, we've got you covered.
          </p>
        </div>

        {/* Search */}
        <div className="max-w-xl mx-auto mb-16">
          <div className="relative">
            <input
              type="text"
              placeholder="Search documentation..."
              className="w-full px-4 py-3 pl-12 rounded-xl border bg-card focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <svg
              className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Main Sections */}
        <div className="max-w-4xl mx-auto mb-16">
          <h2 className="text-2xl font-bold mb-6">Documentation</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {sections.map((section) => (
              <Link
                key={section.href}
                href={section.href}
                className="group flex items-start gap-4 p-6 rounded-xl border bg-card hover:shadow-md transition-all"
              >
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <section.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold group-hover:text-primary transition-colors">
                    {section.title}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {section.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Quick Links */}
        <div className="max-w-4xl mx-auto mb-16">
          <h2 className="text-2xl font-bold mb-6">Popular Pages</h2>
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {quickLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <ArrowRight className="h-4 w-4 text-primary" />
                <span className="text-sm">{link.title}</span>
              </Link>
            ))}
          </div>
        </div>

        {/* API Reference */}
        <div className="max-w-4xl mx-auto">
          <div className="rounded-xl border bg-card p-8">
            <h2 className="text-2xl font-bold mb-4">API Reference</h2>
            <p className="text-muted-foreground mb-6">
              Build integrations with the Terragon API. Full REST API documentation
              with examples in multiple languages.
            </p>
            <div className="flex gap-4">
              <Link
                href="/docs/api"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 transition-colors"
              >
                View API Docs
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/docs/api/authentication"
                className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg font-medium text-sm hover:bg-muted transition-colors"
              >
                Authentication Guide
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-16">
        <div className="container px-4 md:px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link href="/" className="hover:text-foreground">Home</Link>
            <Link href="/docs" className="hover:text-foreground">Docs</Link>
            <Link href="/docs/api" className="hover:text-foreground">API</Link>
          </div>
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} Terragon Labs
          </p>
        </div>
      </footer>
    </div>
  );
}
