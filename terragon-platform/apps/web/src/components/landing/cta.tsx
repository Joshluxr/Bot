import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export function CTA() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            Ready to Ship Faster?
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Start delegating coding tasks to AI agents today.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center justify-center bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-8 rounded-lg font-medium transition-colors"
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center justify-center border hover:bg-muted h-11 px-8 rounded-lg font-medium transition-colors"
            >
              Read the Docs
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
