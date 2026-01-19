import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import { createServer } from 'http';
import { Server as SocketServer } from 'socket.io';
import dotenv from 'dotenv';

import { errorHandler } from './middleware/error-handler';
import { authMiddleware } from './middleware/auth';
import { rateLimiter } from './middleware/rate-limiter';

import authRoutes from './routes/auth';
import taskRoutes from './routes/tasks';
import integrationRoutes from './routes/integrations';
import billingRoutes from './routes/billing';
import webhookRoutes from './routes/webhooks';

import { initializeQueues } from './queues';
import { initializeSocketHandlers } from './socket';

dotenv.config();

const app = express();
const httpServer = createServer(app);
const io = new SocketServer(httpServer, {
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    methods: ['GET', 'POST'],
  },
});

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true,
}));
app.use(morgan('combined'));
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Webhooks (raw body needed for Stripe)
app.use('/api/webhooks', webhookRoutes);

// Rate limiting
app.use('/api', rateLimiter);

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/tasks', authMiddleware, taskRoutes);
app.use('/api/integrations', authMiddleware, integrationRoutes);
app.use('/api/billing', authMiddleware, billingRoutes);

// Error handling
app.use(errorHandler);

// Initialize queues and socket handlers
initializeQueues();
initializeSocketHandlers(io);

// Start server
const PORT = process.env.PORT || 4000;

httpServer.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`);
  console.log(`WebSocket server ready`);
});

export { io };
