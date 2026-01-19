'use client';

import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Badge,
  Skeleton,
  Progress,
} from '@terragon/ui';
import {
  CreditCard,
  Zap,
  Check,
  ExternalLink,
  AlertCircle,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from 'next-auth/react';
import { PRICING, PLAN_LIMITS } from '@terragon/shared';

interface SubscriptionData {
  plan: string;
  credits: number;
  subscription: {
    status: string;
    currentPeriodEnd: string;
    cancelAtPeriodEnd: boolean;
  } | null;
}

const PLANS = [
  {
    id: 'FREE',
    name: 'Free',
    price: 0,
    description: 'For getting started',
    features: [
      '100 credits/month',
      '1 concurrent task',
      'Basic agents',
      'GitHub integration',
    ],
  },
  {
    id: 'CORE',
    name: 'Core',
    price: 25,
    description: 'For individual developers',
    features: [
      '1,000 credits/month',
      '3 concurrent tasks',
      'All agents',
      'GitHub + Slack integration',
      'API access',
    ],
    popular: true,
  },
  {
    id: 'PRO',
    name: 'Pro',
    price: 50,
    description: 'For power users',
    features: [
      '5,000 credits/month',
      '10 concurrent tasks',
      'All agents',
      'All integrations',
      'Priority queue',
      'Custom agents',
    ],
  },
  {
    id: 'ENTERPRISE',
    name: 'Enterprise',
    price: null,
    description: 'For teams and organizations',
    features: [
      'Unlimited credits',
      '50+ concurrent tasks',
      'All features',
      'SSO',
      'Audit logs',
      'Dedicated support',
    ],
  },
];

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <Skeleton className="h-6 w-20 mb-4" />
              <Skeleton className="h-8 w-24 mb-2" />
              <Skeleton className="h-4 w-full mb-4" />
              {[1, 2, 3, 4].map((j) => (
                <Skeleton key={j} className="h-4 w-full mb-2" />
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function BillingPage() {
  const { data: session } = useSession();
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [openingPortal, setOpeningPortal] = useState(false);

  useEffect(() => {
    if (session?.accessToken) {
      api.setToken(session.accessToken);
      loadSubscription();
    }
  }, [session]);

  async function loadSubscription() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSubscription();
      setSubscription(data);
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpgrade(planId: string) {
    if (planId === 'ENTERPRISE') {
      window.location.href = 'mailto:sales@terragonlabs.com?subject=Enterprise Plan Inquiry';
      return;
    }

    try {
      setUpgrading(planId);
      const checkoutUrl = await api.createCheckoutSession(planId, 'monthly');
      window.location.href = checkoutUrl;
    } catch (err) {
      console.error('Failed to create checkout session:', err);
      setUpgrading(null);
    }
  }

  async function handleManageSubscription() {
    try {
      setOpeningPortal(true);
      const portalUrl = await api.createPortalSession();
      window.location.href = portalUrl;
    } catch (err) {
      console.error('Failed to open billing portal:', err);
      setOpeningPortal(false);
    }
  }

  const currentPlan = subscription?.plan || 'FREE';
  const planLimits = PLAN_LIMITS[currentPlan as keyof typeof PLAN_LIMITS];
  const creditsUsed = subscription?.credits || 0;
  const creditsLimit = planLimits?.monthlyCredits || 100;
  const creditsPercentage = creditsLimit === -1 ? 0 : Math.min(100, (creditsUsed / creditsLimit) * 100);

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
          <p className="text-muted-foreground">Manage your subscription and credits.</p>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and credits.</p>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-4 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error loading billing</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={loadSubscription} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Current Plan</CardTitle>
              <CardDescription>Your active subscription</CardDescription>
            </div>
            {subscription?.subscription && (
              <Button variant="outline" onClick={handleManageSubscription} disabled={openingPortal}>
                {openingPortal && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Manage Subscription
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-2xl font-bold">{currentPlan}</h3>
                <Badge variant={currentPlan === 'FREE' ? 'secondary' : 'default'}>
                  {currentPlan === 'FREE' ? 'Free Tier' : 'Active'}
                </Badge>
              </div>
              {subscription?.subscription && (
                <p className="text-sm text-muted-foreground mt-1">
                  {subscription.subscription.cancelAtPeriodEnd
                    ? `Cancels on ${formatDate(subscription.subscription.currentPeriodEnd)}`
                    : `Renews on ${formatDate(subscription.subscription.currentPeriodEnd)}`}
                </p>
              )}
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold">
                {creditsLimit === -1 ? 'Unlimited' : creditsUsed}
              </p>
              <p className="text-sm text-muted-foreground">
                {creditsLimit === -1 ? 'credits' : `of ${creditsLimit} credits used`}
              </p>
            </div>
          </div>

          {creditsLimit !== -1 && (
            <div className="space-y-2">
              <Progress value={creditsPercentage} className="h-2" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{creditsUsed} credits used</span>
                <span>{creditsLimit - creditsUsed} remaining</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Plans */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Available Plans</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => {
            const isCurrentPlan = plan.id === currentPlan;

            return (
              <Card
                key={plan.id}
                className={`relative ${plan.popular ? 'border-primary' : ''} ${
                  isCurrentPlan ? 'bg-muted/50' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge>Most Popular</Badge>
                  </div>
                )}
                <CardContent className="p-6">
                  <h3 className="font-semibold text-lg">{plan.name}</h3>
                  <div className="mt-2 mb-4">
                    {plan.price === null ? (
                      <span className="text-2xl font-bold">Custom</span>
                    ) : plan.price === 0 ? (
                      <span className="text-2xl font-bold">Free</span>
                    ) : (
                      <>
                        <span className="text-2xl font-bold">${plan.price}</span>
                        <span className="text-muted-foreground">/month</span>
                      </>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  {isCurrentPlan ? (
                    <Button variant="outline" className="w-full" disabled>
                      Current Plan
                    </Button>
                  ) : plan.id === 'ENTERPRISE' ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => handleUpgrade(plan.id)}
                    >
                      Contact Sales
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      className="w-full"
                      onClick={() => handleUpgrade(plan.id)}
                      disabled={upgrading === plan.id}
                    >
                      {upgrading === plan.id && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      {plan.price === 0 ? 'Downgrade' : 'Upgrade'}
                      <Zap className="ml-2 h-4 w-4" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* FAQ */}
      <Card>
        <CardHeader>
          <CardTitle>Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium">What are credits?</h4>
            <p className="text-sm text-muted-foreground">
              Credits are used to run tasks. Each minute of task execution costs 1 credit.
              Token usage from AI models also consumes credits based on the model used.
            </p>
          </div>
          <div>
            <h4 className="font-medium">What happens if I run out of credits?</h4>
            <p className="text-sm text-muted-foreground">
              Running tasks will be paused until your credits refresh at the start of the
              next billing period, or you upgrade your plan.
            </p>
          </div>
          <div>
            <h4 className="font-medium">Can I cancel anytime?</h4>
            <p className="text-sm text-muted-foreground">
              Yes, you can cancel your subscription at any time. You&apos;ll retain access to
              your current plan features until the end of your billing period.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
