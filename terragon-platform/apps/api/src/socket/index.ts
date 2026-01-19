import { Server as SocketServer, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';

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
      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as {
        id: string;
        email: string;
      };

      socket.userId = decoded.id;
      next();
    } catch (error) {
      next(new Error('Invalid token'));
    }
  });

  io.on('connection', (socket: AuthenticatedSocket) => {
    console.log(`User ${socket.userId} connected`);

    // Join user-specific room
    if (socket.userId) {
      socket.join(`user:${socket.userId}`);
    }

    // Subscribe to task updates
    socket.on('subscribe:task', (taskId: string) => {
      socket.join(`task:${taskId}`);
      console.log(`User ${socket.userId} subscribed to task ${taskId}`);
    });

    // Unsubscribe from task updates
    socket.on('unsubscribe:task', (taskId: string) => {
      socket.leave(`task:${taskId}`);
      console.log(`User ${socket.userId} unsubscribed from task ${taskId}`);
    });

    // Handle disconnect
    socket.on('disconnect', () => {
      console.log(`User ${socket.userId} disconnected`);
    });
  });

  console.log('Socket.io handlers initialized');
}
