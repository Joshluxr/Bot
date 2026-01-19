import { Quote } from 'lucide-react';

const testimonials = [
  {
    quote: "Terragon has completely changed how I approach tedious coding tasks. I describe what I need, and come back to a ready PR.",
    author: 'Sarah C.',
    role: 'Senior Engineer',
    avatar: 'SC',
  },
  {
    quote: "The isolated sandbox approach is genius. I can run multiple experimental tasks without worrying about conflicts.",
    author: 'Marcus J.',
    role: 'Startup CTO',
    avatar: 'MJ',
  },
  {
    quote: "We've integrated Terragon into our CI/CD pipeline. Bug fixes that used to take hours now get done automatically.",
    author: 'Emily R.',
    role: 'Engineering Manager',
    avatar: 'ER',
  },
];

export function Testimonials() {
  return (
    <section className="py-16 md:py-24 border-t">
      <div className="container px-4 md:px-6">
        <div className="mx-auto max-w-2xl text-center mb-12">
          <h2 className="text-3xl font-bold tracking-tight mb-4">
            Loved by Developers
          </h2>
          <p className="text-lg text-muted-foreground">
            See what developers are saying about Terragon
          </p>
        </div>

        <div className="mx-auto max-w-4xl">
          <div className="grid gap-6 md:grid-cols-3">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="rounded-xl border bg-card p-6 shadow-sm">
                <Quote className="h-6 w-6 text-primary/30 mb-4" />
                <p className="text-sm leading-relaxed mb-6">
                  "{testimonial.quote}"
                </p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <p className="font-medium text-sm">{testimonial.author}</p>
                    <p className="text-xs text-muted-foreground">{testimonial.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
