import { Router, Request, Response, NextFunction } from 'express';
import Stripe from 'stripe';
import express from 'express';
import { prisma } from '@terragon/database';
import { PLAN_LIMITS } from '@terragon/shared';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

const router = Router();

// Stripe webhook
router.post(
  '/stripe',
  express.raw({ type: 'application/json' }),
  async (req: Request, res: Response, next: NextFunction) => {
    const sig = req.headers['stripe-signature'] as string;

    let event: Stripe.Event;

    try {
      event = stripe.webhooks.constructEvent(
        req.body,
        sig,
        process.env.STRIPE_WEBHOOK_SECRET!
      );
    } catch (err: any) {
      console.error('Webhook signature verification failed:', err.message);
      return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    try {
      switch (event.type) {
        case 'checkout.session.completed': {
          const session = event.data.object as Stripe.Checkout.Session;
          const userId = session.metadata?.userId;
          const plan = session.metadata?.plan;
          const creditAmount = session.metadata?.creditAmount;

          if (creditAmount && userId) {
            // Credit purchase
            const amount = parseInt(creditAmount);
            await prisma.$transaction([
              prisma.user.update({
                where: { id: userId },
                data: { credits: { increment: amount } },
              }),
              prisma.creditHistory.create({
                data: {
                  userId,
                  amount,
                  type: 'PURCHASE',
                  description: `Purchased ${amount} credits`,
                },
              }),
            ]);
          } else if (plan && userId && session.subscription) {
            // Subscription created
            const subscription = await stripe.subscriptions.retrieve(
              session.subscription as string
            );

            await prisma.$transaction([
              prisma.subscription.update({
                where: { userId },
                data: {
                  stripeSubscriptionId: subscription.id,
                  stripePriceId: subscription.items.data[0].price.id,
                  status: 'ACTIVE',
                  plan: plan as any,
                  currentPeriodStart: new Date(subscription.current_period_start * 1000),
                  currentPeriodEnd: new Date(subscription.current_period_end * 1000),
                },
              }),
              prisma.user.update({
                where: { id: userId },
                data: {
                  plan: plan as any,
                  credits: PLAN_LIMITS[plan as keyof typeof PLAN_LIMITS].monthlyCredits,
                },
              }),
            ]);
          }
          break;
        }

        case 'customer.subscription.updated': {
          const subscription = event.data.object as Stripe.Subscription;
          const customerId = subscription.customer as string;

          const sub = await prisma.subscription.findUnique({
            where: { stripeCustomerId: customerId },
          });

          if (sub) {
            await prisma.subscription.update({
              where: { id: sub.id },
              data: {
                status: subscription.status === 'active' ? 'ACTIVE' : 'PAST_DUE',
                cancelAtPeriodEnd: subscription.cancel_at_period_end,
                currentPeriodEnd: new Date(subscription.current_period_end * 1000),
              },
            });
          }
          break;
        }

        case 'customer.subscription.deleted': {
          const subscription = event.data.object as Stripe.Subscription;
          const customerId = subscription.customer as string;

          const sub = await prisma.subscription.findUnique({
            where: { stripeCustomerId: customerId },
            include: { user: true },
          });

          if (sub) {
            await prisma.$transaction([
              prisma.subscription.update({
                where: { id: sub.id },
                data: { status: 'CANCELLED' },
              }),
              prisma.user.update({
                where: { id: sub.userId },
                data: { plan: 'FREE' },
              }),
            ]);
          }
          break;
        }

        case 'invoice.payment_failed': {
          const invoice = event.data.object as Stripe.Invoice;
          const customerId = invoice.customer as string;

          const sub = await prisma.subscription.findUnique({
            where: { stripeCustomerId: customerId },
          });

          if (sub) {
            await prisma.subscription.update({
              where: { id: sub.id },
              data: { status: 'PAST_DUE' },
            });
          }
          break;
        }

        default:
          console.log(`Unhandled event type: ${event.type}`);
      }

      res.json({ received: true });
    } catch (error) {
      console.error('Webhook processing error:', error);
      next(error);
    }
  }
);

// GitHub webhook (for automation triggers)
router.post('/github', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const event = req.headers['x-github-event'] as string;
    const payload = req.body;

    console.log(`GitHub webhook: ${event}`);

    // Handle different GitHub events
    switch (event) {
      case 'issues':
        if (payload.action === 'opened' || payload.action === 'labeled') {
          // TODO: Check for automations that trigger on issues
          console.log(`Issue ${payload.action}: ${payload.issue.title}`);
        }
        break;

      case 'push':
        console.log(`Push to ${payload.repository.full_name}:${payload.ref}`);
        break;

      default:
        console.log(`Unhandled GitHub event: ${event}`);
    }

    res.json({ received: true });
  } catch (error) {
    next(error);
  }
});

export default router;
