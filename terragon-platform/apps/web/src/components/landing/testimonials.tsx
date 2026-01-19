import { Card, CardContent } from '@terragon/ui';
import { Avatar, AvatarFallback, AvatarImage } from '@terragon/ui';
import { Quote } from 'lucide-react';

const testimonials = [
  {
    quote: "Terragon has completely changed how I approach tedious coding tasks. I describe what I need, and come back to a ready PR. It's like having a tireless junior developer.",
    author: 'Sarah Chen',
    role: 'Senior Engineer at Vercel',
    avatar: 'SC',
  },
  {
    quote: "The isolated sandbox approach is genius. I can run multiple experimental tasks without worrying about conflicts. The quality of the generated code is impressive.",
    author: 'Marcus Johnson',
    role: 'CTO at StartupXYZ',
    avatar: 'MJ',
  },
  {
    quote: "We've integrated Terragon into our CI/CD pipeline. Bug fixes that used to take hours now get done automatically. Our velocity has increased significantly.",
    author: 'Emily Rodriguez',
    role: 'Engineering Manager at Stripe',
    avatar: 'ER',
  },
];

export function Testimonials() {
  return (
    <section className="py-20 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Loved by Developers
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            See what developers are saying about Terragon
          </p>
        </div>

        <div className="mx-auto max-w-5xl">
          <div className="grid gap-6 md:grid-cols-3">
            {testimonials.map((testimonial, index) => (
              <Card key={index}>
                <CardContent className="p-6">
                  <Quote className="h-8 w-8 text-primary/20 mb-4" />
                  <p className="text-sm leading-relaxed mb-6">
                    "{testimonial.quote}"
                  </p>
                  <div className="flex items-center gap-3">
                    <Avatar>
                      <AvatarFallback>{testimonial.avatar}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-sm">{testimonial.author}</p>
                      <p className="text-xs text-muted-foreground">{testimonial.role}</p>
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
