import { Router, Response, NextFunction } from 'express';
import Stripe from 'stripe';
import { prisma } from '@terragon/database';
import { AuthenticatedRequest } from '../middleware/auth';
import { BadRequestError } from '../middleware/error-handler';
import { PRICING } from '@terragon/shared';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

const router = Router();

// Get subscription status
router.get('/subscription', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const subscription = await prisma.subscription.findUnique({
      where: { userId: req.user!.id },
    });

    const user = await prisma.user.findUnique({
      where: { id: req.user!.id },
      select: { plan: true, credits: true },
    });

    res.json({
      success: true,
      data: {
        plan: user!.plan,
        credits: user!.credits,
        subscription: subscription ? {
          status: subscription.status,
          currentPeriodEnd: subscription.currentPeriodEnd,
          cancelAtPeriodEnd: subscription.cancelAtPeriodEnd,
        } : null,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Create checkout session
router.post('/checkout', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { plan, interval = 'monthly' } = req.body;

    if (!plan || !['CORE', 'PRO'].includes(plan)) {
      throw new BadRequestError('Invalid plan');
    }

    const priceConfig = PRICING[plan as keyof typeof PRICING];
    if (!priceConfig.stripePriceId) {
      throw new BadRequestError('Invalid plan');
    }

    const priceId = priceConfig.stripePriceId[interval as 'monthly' | 'yearly'];

    // Get or create Stripe customer
    let subscription = await prisma.subscription.findUnique({
      where: { userId: req.user!.id },
    });

    let customerId = subscription?.stripeCustomerId;

    if (!customerId) {
      const user = await prisma.user.findUnique({
        where: { id: req.user!.id },
      });

      const customer = await stripe.customers.create({
        email: user!.email,
        metadata: { userId: req.user!.id },
      });

      customerId = customer.id;

      await prisma.subscription.create({
        data: {
          userId: req.user!.id,
          stripeCustomerId: customerId,
          status: 'INACTIVE',
        },
      });
    }

    // Create checkout session
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${process.env.FRONTEND_URL}/dashboard/billing?success=true`,
      cancel_url: `${process.env.FRONTEND_URL}/dashboard/billing?cancelled=true`,
      metadata: {
        userId: req.user!.id,
        plan,
      },
    });

    res.json({
      success: true,
      data: { url: session.url },
    });
  } catch (error) {
    next(error);
  }
});

// Create customer portal session
router.post('/portal', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const subscription = await prisma.subscription.findUnique({
      where: { userId: req.user!.id },
    });

    if (!subscription?.stripeCustomerId) {
      throw new BadRequestError('No subscription found');
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: subscription.stripeCustomerId,
      return_url: `${process.env.FRONTEND_URL}/dashboard/billing`,
    });

    res.json({
      success: true,
      data: { url: session.url },
    });
  } catch (error) {
    next(error);
  }
});

// Get credit history
router.get('/credits/history', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { page = '1', pageSize = '20' } = req.query;
    const skip = (parseInt(page as string) - 1) * parseInt(pageSize as string);
    const take = Math.min(parseInt(pageSize as string), 100);

    const [history, total] = await Promise.all([
      prisma.creditHistory.findMany({
        where: { userId: req.user!.id },
        orderBy: { createdAt: 'desc' },
        skip,
        take,
      }),
      prisma.creditHistory.count({
        where: { userId: req.user!.id },
      }),
    ]);

    res.json({
      success: true,
      data: {
        items: history,
        total,
        page: parseInt(page as string),
        pageSize: take,
        hasMore: skip + take < total,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Purchase additional credits
router.post('/credits/purchase', async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
  try {
    const { amount } = req.body;

    if (!amount || amount < 100) {
      throw new BadRequestError('Minimum purchase is 100 credits');
    }

    // Get or create customer
    let subscription = await prisma.subscription.findUnique({
      where: { userId: req.user!.id },
    });

    let customerId = subscription?.stripeCustomerId;

    if (!customerId) {
      const user = await prisma.user.findUnique({
        where: { id: req.user!.id },
      });

      const customer = await stripe.customers.create({
        email: user!.email,
        metadata: { userId: req.user!.id },
      });

      customerId = customer.id;

      await prisma.subscription.create({
        data: {
          userId: req.user!.id,
          stripeCustomerId: customerId,
          status: 'INACTIVE',
        },
      });
    }

    // $0.10 per credit
    const priceInCents = amount * 10;

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'payment',
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: `${amount} Terragon Credits`,
              description: 'Credits for AI coding tasks',
            },
            unit_amount: priceInCents,
          },
          quantity: 1,
        },
      ],
      success_url: `${process.env.FRONTEND_URL}/dashboard/billing?credits_success=true`,
      cancel_url: `${process.env.FRONTEND_URL}/dashboard/billing?credits_cancelled=true`,
      metadata: {
        userId: req.user!.id,
        creditAmount: amount.toString(),
      },
    });

    res.json({
      success: true,
      data: { url: session.url },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
