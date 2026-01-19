import { Server as SocketServer, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { WS_EVENTS } from '@terragon/shared';

interface AuthenticatedSocket extends Socket {
  userId?: string;
}

export function initializeSocketHandlers(io: SocketServer) {
  // Authentication middleware
  io.use((socket: AuthenticatedSocket, next) => {
    const token = socket.handshake.auth.token;

    if (!token) {
      return next(new Error('Authentication required'));
    }

    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as { id: string };
      socket.userId = decoded.id;
      next();
    } catch {
      next(new Error('Invalid token'));
    }
  });

  io.on('connection', (socket: AuthenticatedSocket) => {
    console.log(`Client connected: ${socket.id} (user: ${socket.userId})`);

    // Join user-specific room for targeted events
    if (socket.userId) {
      socket.join(`user:${socket.userId}`);
    }

    // Handle task subscription
    socket.on('subscribe:task', (taskId: string) => {
      socket.join(`task:${taskId}`);
      console.log(`Socket ${socket.id} subscribed to task:${taskId}`);
    });

    socket.on('unsubscribe:task', (taskId: string) => {
      socket.leave(`task:${taskId}`);
      console.log(`Socket ${socket.id} unsubscribed from task:${taskId}`);
    });

    socket.on('disconnect', () => {
      console.log(`Client disconnected: ${socket.id}`);
    });
  });

  console.log('WebSocket handlers initialized');
}

// Helper functions to emit events
export function emitTaskStarted(
  io: SocketServer,
  userId: string,
  taskId: string,
  sandboxId: string
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.TASK_STARTED, {
    type: WS_EVENTS.TASK_STARTED,
    taskId,
    sandboxId,
    timestamp: new Date(),
  });
}

export function emitTaskProgress(
  io: SocketServer,
  userId: string,
  taskId: string,
  progress: number,
  message: string
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.TASK_PROGRESS, {
    type: WS_EVENTS.TASK_PROGRESS,
    taskId,
    progress,
    message,
    timestamp: new Date(),
  });
}

export function emitTaskCompleted(
  io: SocketServer,
  userId: string,
  taskId: string,
  pullRequestUrl: string | null,
  executionTime: number,
  creditsUsed: number
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.TASK_COMPLETED, {
    type: WS_EVENTS.TASK_COMPLETED,
    taskId,
    pullRequestUrl,
    executionTime,
    creditsUsed,
    timestamp: new Date(),
  });
}

export function emitTaskFailed(
  io: SocketServer,
  userId: string,
  taskId: string,
  errorMessage: string
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.TASK_FAILED, {
    type: WS_EVENTS.TASK_FAILED,
    taskId,
    errorMessage,
    timestamp: new Date(),
  });
}

export function emitLog(
  io: SocketServer,
  userId: string,
  taskId: string,
  level: string,
  message: string
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.LOG, {
    type: WS_EVENTS.LOG,
    taskId,
    level,
    message,
    timestamp: new Date(),
  });
}

export function emitSandboxReady(
  io: SocketServer,
  userId: string,
  taskId: string,
  sandboxUrl: string
) {
  io.to(`user:${userId}`).to(`task:${taskId}`).emit(WS_EVENTS.SANDBOX_READY, {
    type: WS_EVENTS.SANDBOX_READY,
    taskId,
    sandboxUrl,
    timestamp: new Date(),
  });
}
