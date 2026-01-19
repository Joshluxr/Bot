import { Header } from '@/components/landing/header';
import { Hero } from '@/components/landing/hero';
import { HowItWorks } from '@/components/landing/how-it-works';
import { Agents } from '@/components/landing/agents';
import { CloudSection } from '@/components/landing/cloud-section';
import { IsolatedEnvironments } from '@/components/landing/isolated-environments';
import { Integrations } from '@/components/landing/integrations';
import { CLI } from '@/components/landing/cli';
import { Automations } from '@/components/landing/automations';
import { Testimonials } from '@/components/landing/testimonials';
import { Pricing } from '@/components/landing/pricing';
import { FAQ } from '@/components/landing/faq';
import { CTA } from '@/components/landing/cta';
import { Footer } from '@/components/landing/footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Hero />
        <HowItWorks />
        <Agents />
        <CloudSection />
        <IsolatedEnvironments />
        <Integrations />
        <CLI />
        <Automations />
        <Testimonials />
        <Pricing />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
