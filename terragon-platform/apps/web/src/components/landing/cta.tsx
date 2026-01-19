import Link from 'next/link';
import { Button } from '@terragon/ui';
import { ArrowRight } from 'lucide-react';

export function CTA() {
  return (
    <section className="py-20 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Ready to Ship Faster?
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Join thousands of developers automating their workflow with AI agents.
            Start your free trial today.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/login">
                Get started for free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/docs">Read the docs</Link>
            </Button>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            No credit card required. 14-day free trial on all paid plans.
          </p>
        </div>
      </div>
    </section>
  );
}
